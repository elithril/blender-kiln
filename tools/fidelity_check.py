"""Measure how far a model is from its reference image — shape and material, in numbers.

    blender -b --factory-startup --python-exit-code 1 --python tools/fidelity_check.py -- \\
        --reference ref.png --model asset.blend|asset.glb --hdri studio.hdr --out review/ \\
        [--view front|back|left|right|top] [--elevation DEG] [--azimuth DEG] [--samples 64] [--max-tris 5000]

One reference image per call. A reference shot from the side or from above is measured
with --view set to where that camera stood; run once per view the user provided.

Renders the model twice from the front, orthographic — a flat silhouette, and a colour
render under a studio HDRI — scales it to the reference's height, and compares:

- shape: silhouette IoU, and per height band the width difference (full and core);
- material, per band: luminance, saturation, warmth (R−B), highlight share, texture
  detail (high-pass energy) and value spread — luminance and highlights depend on the
  photo's unknown light, so they are alarms, not targets;
- the model's own materials: metal whose base colour is too dark to be physical, a
  metallic mask in scattered hard-edged islands (camouflage), metal painted mostly as
  non-metal, and a surface too clean for the photo (grain, per band);
- joints: every end of a long part that touches another, rendered up close to be looked at.

Prints one JSON line (`FIDELITY {...}`) and a ranked list of the largest gaps, and writes
`overlay.png` (red: reference only, cyan: model only) and `side_by_side.png` into --out.

Why: a session reviewing by eye over-corrected twice on the bench — too bright and
blotchy, then grey and flat. These are the numbers that showed it. They are only as good
as the match between the two views: the reference's camera and light are unknown, so
read differences of a few percent as noise, and large ones as the fix list.
"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Matrix, Vector

BANDS = 5
VIEW = "front"
ELEVATION = 0.0
AZIMUTH = 0.0


def args():
    a = sys.argv[sys.argv.index("--") + 1:]
    o = {"samples": "64"}
    for k, v in zip(a[::2], a[1::2]):
        o[k.lstrip("-")] = v
    for k in ("reference", "model", "hdri", "out"):
        if k not in o:
            sys.exit(f"fidelity_check: missing --{k}")
    if o.get("view", "front") not in ("front", "back", "left", "right", "top"):
        sys.exit("fidelity_check: --view is front, back, left, right or top")
    global VIEW, ELEVATION, AZIMUTH
    VIEW = o.get("view", "front")
    ELEVATION = float(o.get("elevation", 0))
    AZIMUTH = float(o.get("azimuth", 0))
    os.makedirs(o["out"], exist_ok=True)
    return o


def open_model(path):
    if path.lower().endswith((".glb", ".gltf")):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    for o in sc.objects:
        if o.type in ("CAMERA", "LIGHT"):
            o.hide_render = True
    shapes = {pb.custom_shape for a in sc.objects if a.type == "ARMATURE" for pb in a.pose.bones if pb.custom_shape}
    meshes = [o for o in sc.objects if o.type == "MESH" and o not in shapes and not o.hide_render]
    if not meshes:
        sys.exit("fidelity_check: no renderable mesh in the model")
    # A texture that is not loaded renders black and every material number lies — the
    # bench's first measure of a lantern did exactly that. Refuse rather than measure it.
    missing = sorted({n.image.name for o in meshes for sl in o.material_slots if sl.material and sl.material.node_tree
                      for n in sl.material.node_tree.nodes
                      if n.type == "TEX_IMAGE" and n.image and not n.image.has_data and not n.image.packed_file
                      and not os.path.exists(bpy.path.abspath(n.image.filepath))})
    if missing:
        sys.exit(f"fidelity_check: textures not loaded, pack them first (bpy.ops.file.pack_all()): {missing}")
    dg = bpy.context.evaluated_depsgraph_get()
    tris = sum(sum(len(pl.vertices) - 2 for pl in o.evaluated_get(dg).data.polygons) for o in meshes)
    cs = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(c[i] for c in cs) for i in range(3)])
    hi = Vector([max(c[i] for c in cs) for i in range(3)])
    return sc, lo, hi, tris, meshes


DARK_METAL = 0.15
CONFETTI_SOFT, CONFETTI_LARGEST = 0.60, 0.5
# Calibrated on ONE truth: the real Lantern_01's brass averages 0.63; v8, v9 and v10, which
# read grey or dull, 0.20-0.57. A warning about what light does, not a share to reach.
MOSTLY_PAINTED = 0.5
# Grain, model over photo, per band. ONE truth again, and a narrow margin: the real
# Lantern_01 0.52-0.84, the image-to-code lantern 0.38+, v10 0.31+; v8 and v11, which read
# dull or new, 0.21-0.22 on the tank.
TOO_CLEAN = 0.28


def _image_channel(sock):
    """The image behind a socket, the channel that feeds it (glTF packs metallic in B), and
    any constant factor on the way (the glTF importer puts metallicFactor in a Math node)."""
    if not sock.is_linked:
        return None, 0, 1.0
    link, ch, k = sock.links[0], 0, 1.0
    while link.from_node.type != "TEX_IMAGE":
        n = link.from_node
        if n.type == "SEPARATE_COLOR":
            ch = list(n.outputs).index(link.from_socket)
        elif n.type == "MATH" and n.operation == "MULTIPLY":
            k *= next((i.default_value for i in n.inputs[:2] if not i.is_linked), 1.0)
        inputs = [i for i in n.inputs if i.is_linked]
        if not inputs:
            return None, 0, 1.0
        link = inputs[0].links[0]
    return link.from_node.image, ch, k


def _texels(im, size=128):
    c = im.copy(); c.scale(size, size)
    a = np.array(c.pixels[:], dtype=np.float32).reshape(size, size, -1)
    bpy.data.images.remove(c)
    return a


def mask_shape(met):
    """A metallic mask's shape: the share of in-between texels (0.15-0.85: soft transitions)
    and the largest connected island's share of the metal (one region, or scattered).

    Read on a 256 grid. Calibrated on the real Lantern_01 (one region: 99 %, 43 % soft),
    v8 (scattered, 19-85 %, but 74-99 % soft: reads smooth) and v9 (3-40 %, 32-52 % soft:
    camouflage). A mean jump between texels was tried first and dropped: it counts edges,
    not their hardness — a hard 8-texel checker read 0.109, the real brass 0.117."""
    soft = float(((met > 0.15) & (met < 0.85)).mean())
    m = met > 0.5; lab = np.zeros(m.shape, np.int32); n, sizes = 0, []
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0]:
            continue
        n += 1; lab[y0, x0] = n; stack, cnt = [(y0, x0)], 0
        while stack:
            y, x = stack.pop(); cnt += 1
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < m.shape[0] and 0 <= xx < m.shape[1] and m[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; stack.append((yy, xx))
        sizes.append(cnt)
    return soft, (max(sizes) / m.sum() if sizes else 1.0)


def dark_metals(meshes):
    """Metallic texels whose base colour is too dark: physically impossible, they render black.

    In the metal/roughness workflow a metal's base colour IS its reflectance. Darkening it to
    paint age gives a black mirror under any light — the bench's lantern v7 measured 0.02-0.15
    on its metal (sRGB luminance) and rendered 23 % darker than the real asset, while matching
    the photo's luminance: the photo's own light was darker, and the session tuned to it. The
    real aged brass (Poly Haven Lantern_01): 0.30 median, 0.25 for its darkest tenth, and only
    its rust and soot painted as NON-metal. (Its metallic share is no target: quoted as
    "48 %", a session thresholded a noise to reach it — see mask_shape.)
    """
    rows, seen = [], set()
    for m in {sl.material for o in meshes for sl in o.material_slots if sl.material and sl.material.node_tree}:
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b is None or m.name in seen:
            continue
        seen.add(m.name)
        mi, mch, mk = _image_channel(b.inputs["Metallic"])
        bi, _, _ = _image_channel(b.inputs["Base Color"])
        if any(im and not im.size[0] for im in (mi, bi)):      # .size loads it; has_data stays False until then
            continue
        met = _texels(mi)[..., mch] * mk if mi else np.full((128, 128), b.inputs["Metallic"].default_value)
        if bi:
            base = _texels(bi)[..., :3]
            if bi.is_float:                       # float images hold linear values; bytes hold sRGB
                base = np.where(base <= 0.0031308, base * 12.92, 1.055 * np.power(np.clip(base, 0, None), 1 / 2.4) - 0.055)
        else:
            lin = np.array(b.inputs["Base Color"].default_value[:3])
            base = np.broadcast_to(np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055), (128, 128, 3))
        k = met > 0.8
        row = dict(material=m.name, metal_share=float(k.mean()))
        if mi:                                    # the mask's shape, on a finer grid than the colour check
            fine = _texels(mi, 256)[..., mch] * mk
            if 0.05 < (fine > 0.5).mean() < 0.95:
                row["mask_soft"], row["mask_largest"] = mask_shape(fine)
                row["mask_mean"] = float(fine.mean())
        if k.mean() >= 0.05:
            row["base_median"] = float(np.median((base @ np.array([0.2126, 0.7152, 0.0722]))[k]))
        if "base_median" in row or "mask_soft" in row:
            rows.append(row)
    return rows


def contact_ends(meshes, tol=0.0005):
    """Ends of elongated parts (tubes, rods, legs, handles) that touch another part.

    A joint is where a part must ENTER another, or sit on a shaped foot — a flat cut resting
    on a curved surface touches at one point and passes every distance check: lantern v10's
    air tubes did, and read as unconnected. No threshold can judge it (the real Lantern_01's
    tubes lift 8.6 mm off the tank too, under a sheet-metal foot), so the tool renders each
    one up close and the session LOOKS. Loose parts are the connected pieces of the model."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new()
    for ob in meshes:
        m = ob.evaluated_get(dg).to_mesh(); m.transform(ob.matrix_world); bm.from_mesh(m)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.verts.ensure_lookup_table(); comp = [-1] * len(bm.verts); n = 0
    for v in bm.verts:
        if comp[v.index] >= 0:
            continue
        stack = [v]
        while stack:
            x = stack.pop()
            if comp[x.index] >= 0:
                continue
            comp[x.index] = n
            stack.extend(e.other_vert(x) for e in x.link_edges)
        n += 1
    parts = {}
    for f in bm.faces:
        parts.setdefault(comp[f.verts[0].index], []).append(f)
    parts = {k: fs for k, fs in parts.items() if len(fs) >= 10}     # a plain 8-sided rod has 10

    def tree(faces):
        b = bmesh.new()
        for f in faces:
            try:
                b.faces.new([b.verts.new(v.co) for v in f.verts])
            except ValueError:
                pass
        return BVHTree.FromBMesh(b)
    ends = []
    for k, fs in parts.items():
        P = np.array([v.co[:] for v in {v for f in fs for v in f.verts}])
        c = P.mean(0); ax = np.linalg.svd(P - c, full_matrices=False)[2][0]
        t = (P - c) @ ax; L = float(t.max() - t.min())
        rad = float(np.sqrt(np.median(np.sum(((P - c) - np.outer(t, ax)) ** 2, 1))))
        if L < 4 * rad:
            continue
        trees = {j: tree(g) for j, g in parts.items() if j != k}
        if not trees:                              # a single part: nothing to join
            continue
        for sel in (t < t.min() + 0.04 * L, t > t.max() - 0.04 * L):
            E = P[sel]
            near = [(min(tr.find_nearest(Vector(q))[3] for q in E), j) for j, tr in trees.items()]
            d, j = min(near)
            if d <= tol:
                pair = [[v.co.copy() for v in f.verts] for f in fs + parts[j]]
                ends.append(dict(at=E.mean(0), axis=ax, radius=rad, faces=pair))
    return ends


def render_joints(sc, ends, out, centre):
    """Two close renders of every contact end, into out/: the two parts in contact ONLY, in
    flat grey (Workbench) — a joint is judged on its shape, and anything else in the frame
    hid it (a lantern's guard wires behind its tubes). From outside the object, and 60° round."""
    os.makedirs(out, exist_ok=True)
    hidden = [ob for ob in sc.objects if ob.type == "MESH" and not ob.hide_render]
    for ob in hidden:
        ob.hide_render = True
    cam = bpy.data.objects.new("_joint_cam", bpy.data.cameras.new("_joint_cam")); sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = "ORTHO"
    sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = sc.render.resolution_y = 420
    files = []
    for i, e in enumerate(ends):
        me = bpy.data.meshes.new(f"_joint_{i}"); verts, polys = [], []
        for f in e["faces"]:
            polys.append(list(range(len(verts), len(verts) + len(f)))); verts.extend(f)
        me.from_pydata(verts, [], polys); me.update()
        ob = bpy.data.objects.new(me.name, me); sc.collection.objects.link(ob)
        at = Vector(e["at"]); cam.data.ortho_scale = max(6 * e["radius"], 0.01)
        out_dir = at - centre; out_dir.z = 0
        if out_dir.length < 1e-4:
            out_dir = Vector((0, -1, 0))
        out_dir.normalize()
        for name, turn in (("a", 0.0), ("b", math.radians(60))):
            d = out_dir.copy(); d.rotate(Matrix.Rotation(turn, 3, "Z")); d.z = 0.35; d.normalize()
            cam.location = at + d * 1.0; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = os.path.join(out, f"joint_{i + 1:02d}{name}.png")
            bpy.ops.render.render(write_still=True); files.append(sc.render.filepath)
        bpy.data.objects.remove(ob)
    for ob in hidden:
        ob.hide_render = False
    return files


def render(sc, lo, hi, path, engine, hdri=None, samples=64):
    ctr, H = (lo + hi) / 2, hi.z - lo.z
    cam = bpy.data.objects.get("_fidelity_cam")
    if cam is None:
        cam = bpy.data.objects.new("_fidelity_cam", bpy.data.cameras.new("_fidelity_cam"))
        sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    # Blender's front is -Y looking +Y. A view names where the camera stands.
    size = (hi - lo)
    offset, rot, frame_h = {
        "front": (Vector((0, -3 * H, 0)), (math.pi / 2, 0, 0), H),
        "back":  (Vector((0, 3 * H, 0)), (math.pi / 2, 0, math.pi), H),
        "left":  (Vector((-3 * H, 0, 0)), (math.pi / 2, 0, -math.pi / 2), H),
        "right": (Vector((3 * H, 0, 0)), (math.pi / 2, 0, math.pi / 2), H),
        "top":   (Vector((0, 0, 3 * H)), (0, 0, 0), max(size.x, size.y)),
    }[VIEW]
    # Frame the larger of what this view shows: height, and the width across the view.
    # Height alone clipped anything wider than tall — a 2 x 1 x 1 box measured 1:1 from the front.
    across = {"front": size.x, "back": size.x, "left": size.y, "right": size.y}.get(VIEW, 0)
    cam.data.ortho_scale = max(frame_h, size.x, size.y) * 1.02 if VIEW == "top" else max(frame_h, across) * 1.02
    cam.location = ctr + offset; cam.rotation_euler = rot
    if (ELEVATION or AZIMUTH) and VIEW != "top":
        # Orbit the camera around the object's centre: AZIMUTH turns it toward the object's
        # right (+X seen from the front) — most product photos are 3/4 views — and ELEVATION
        # tilts it down: a photo taken from above shows every disc's top as an ellipse, and a
        # level render compared with it reads those discs as taller than they are.
        e, a = math.radians(ELEVATION), math.radians(AZIMUTH)
        d = (cam.location - ctr)
        hx, hy = d.x, d.y
        hx, hy = hx * math.cos(a) - hy * math.sin(a), hx * math.sin(a) + hy * math.cos(a)
        horiz = Vector((hx, hy, 0)).normalized() * d.length
        cam.location = ctr + horiz * math.cos(e) + Vector((0, 0, d.length * math.sin(e)))
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    # Frame what this camera actually sees: project the bounding box's eight corners onto
    # its image plane. Rules per view clipped anything wider than tall once already.
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    corners = [inv @ Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    xs, ys = [c.x for c in corners], [c.y for c in corners]
    cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.04
    shift = cam.matrix_world.to_3x3() @ Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
    cam.location = cam.location + shift
    sc.render.engine = engine
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 768
    sc.render.image_settings.color_mode = "RGBA"
    if hdri:
        w = bpy.data.worlds.new("_fidelity_hdri"); sc.world = w          # node tree is always on in 5.x
        env = w.node_tree.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdri)
        w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
        sc.cycles.samples = samples; sc.cycles.device = "CPU"
        sc.view_settings.view_transform = "Standard"                                     # like a plain photo
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def load(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]            # top row first
    m = a[..., 3] > 0.5
    if not m.any():
        sys.exit(f"fidelity_check: {path} has no opaque pixel — a reference needs alpha")
    ys, xs = np.where(m)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def fit(a, H):
    h, w = a.shape[:2]; W = max(1, round(w * H / h))
    return a[(np.arange(H) * h / H).astype(int)][:, (np.arange(W) * w / W).astype(int)]


def pad_to(a, W):
    d = W - a.shape[1]
    return np.pad(a, ((0, 0), (d // 2, d - d // 2)) + ((0, 0),) * (a.ndim - 2))


def widths(m):
    full, core = [], []
    cx = m.shape[1] // 2
    for r in m:
        xs = np.where(r)[0]
        full.append(xs.max() - xs.min() + 1 if len(xs) else 0)
        if not r[cx]:
            core.append(0); continue
        a = b = cx
        while a > 0 and r[a - 1]: a -= 1
        while b < len(r) - 1 and r[b + 1]: b += 1
        core.append(b - a + 1)
    return np.array(full, float), np.array(core, float)


def blur(x, k=4):
    c = np.pad(np.cumsum(np.cumsum(np.pad(x, k, mode="edge"), 0), 1), ((1, 0), (1, 0)))
    n = 2 * k + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)


def material(a):
    rgb, m = a[..., :3], a[..., 3] > 0.5
    e = m.copy(); e[1:] &= m[:-1]; e[:-1] &= m[1:]; e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    hp = np.abs(lum - blur(lum))
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    # Grain: the surface's fine variation inside solid areas, relative to their brightness —
    # deep inside the mask (6 px), so silhouettes and wire edges do not count, and divided by
    # the band's mean so the photo's exposure does not either. A clean-looking metal has
    # none: lantern v11 read new at 20 % of its photo's grain on the tank, v8 dull at 31 %;
    # the real object renders at 74 %, the image-to-code lantern 79 %, v10 57 %.
    deep = m.copy()
    for _ in range(6):
        deep[1:] &= deep[:-1].copy(); deep[:-1] &= deep[1:].copy(); deep[:, 1:] &= deep[:, :-1].copy(); deep[:, :-1] &= deep[:, 1:].copy()
    fine = lum - blur(lum, 2)
    H, out = a.shape[0], []
    for i in range(BANDS):
        k = np.zeros_like(m); k[i * H // BANDS:(i + 1) * H // BANDS] = True
        kd = k & deep; k &= e
        L = lum[k]
        out.append(None if L.size < 50 else dict(
            lum=float(L.mean()), sat=float(sat[k].mean()),
            warm=float((rgb[..., 0] - rgb[..., 2])[k].mean()),
            highlights=float((L > 0.55).mean()), detail=float(hp[k].mean()),
            spread=float(np.percentile(L, 95) - np.percentile(L, 5)),
            grain=float(fine[kd].std() / max(lum[kd].mean(), 1e-4)) if kd.sum() >= 200 else None))
    return out


def save(arr, path):
    arr = np.ascontiguousarray(arr[::-1])
    img = bpy.data.images.new(os.path.basename(path), arr.shape[1], arr.shape[0], alpha=True)
    img.pixels = arr.ravel().tolist(); img.filepath_raw = path; img.file_format = "PNG"; img.save()


def main():
    o = args()
    if not o["model"].lower().endswith((".glb", ".gltf")):
        print("fidelity_check: WARNING — measuring a .blend. The final measure must be of the exported "
              "GLB: an export can change what you see (a linear float texture ships black).")
    sc, lo, hi, tris, meshes = open_model(o["model"])
    nmesh, metals = len(meshes), dark_metals(meshes)
    sil, col = os.path.join(o["out"], "_silhouette.png"), os.path.join(o["out"], "_colour.png")
    render(sc, lo, hi, sil, "BLENDER_WORKBENCH")
    render(sc, lo, hi, col, "CYCLES", hdri=o["hdri"], samples=int(o["samples"]))

    ref = load(o["reference"]); H = ref.shape[0]
    mod_s, mod_c = fit(load(sil), H), fit(load(col), H)
    W = max(ref.shape[1], mod_s.shape[1], mod_c.shape[1])
    R, M = pad_to(ref[..., 3] > 0.5, W), pad_to(mod_s[..., 3] > 0.5, W)
    iou = float((R & M).sum() / (R | M).sum())
    rf, rc = widths(R); mf, mc = widths(M)
    shape = []
    for i in range(BANDS):
        s = slice(i * H // BANDS, (i + 1) * H // BANDS)
        bi = (R[s] & M[s]).sum() / max((R[s] | M[s]).sum(), 1)
        shape.append(dict(band=i + 1, iou=float(bi),
                          full_width=float((mf[s].mean() - rf[s].mean()) / max(rf[s].mean(), 1)),
                          core_width=float((mc[s].mean() - rc[s].mean()) / max(rc[s].mean(), 1))))
    mref, mmod = material(ref), material(mod_c)

    # Shape gaps are LOCAL: a band whose width is off, or a band clearly wrong. Overall IoU
    # is not a target — the real Lantern_01 scores ~0.80 against its own photo, and the
    # bench's version that pushed it to 0.898 was the worst against the real object.
    # Band IoU alone is not a gap either: a 2-px wire off by a pixel scores 0.2-0.4.
    gaps = []
    body = max(rc.max(), 1)
    for i, b in enumerate(shape):
        # A band with no solid body at the axis (wires, a loop, a handle) has a meaningless
        # core width — it measures the hole of the loop. Judge it by its full width only.
        sl = slice(i * H // BANDS, (i + 1) * H // BANDS)
        solid = rc[sl].mean() > 0.15 * body
        off = max(abs(b["full_width"]), abs(b["core_width"]) if solid else 0.0)
        if off > 0.08 or (solid and b["iou"] < 0.5):
            gaps.append((off * 4 + max(0.0, 0.5 - b["iou"]),
                         f"band {b['band']}/{BANDS} (1 = top): width {b['full_width']:+.0%}, core "
                         f"{b['core_width']:+.0%}, IoU {b['iou']:.2f} — check the overlay there"))
    for i, (r, m) in enumerate(zip(mref, mmod)):
        if not r or not m:
            continue
        # Tolerances from the bench's calibration: the real Lantern_01, measured against its
        # own preview under this HDRI, reads luminance +0.05 and highlights +0.010 — the light,
        # not the object. Saturation and detail held (0.33/0.32, 0.028/0.032).
        # Luminance and highlights are ALARMS, never targets: the photo's light is unknown.
        # Lantern v7 matched the photo's luminance to 0.003 and was 23 % darker than the real
        # object under this HDRI — the real one is 28 % brighter than its own photo here. The
        # material's own numbers (dark_metals) are what light cannot move.
        for k, tol in (("sat", 0.06), ("warm", 0.025), ("detail", 0.008), ("lum", 0.07), ("highlights", 0.02)):
            d = m[k] - r[k]
            if abs(d) > tol:
                note = " — light-dependent: check the material, do not tune to it" if k in ("lum", "highlights") else ""
                gaps.append((abs(d) / tol / 10, f"band {i + 1}: {k} {m[k]:.3f} vs reference {r[k]:.3f} ({d:+.3f}){note}"))
    for i, (r, m) in enumerate(zip(mref, mmod)):
        if r and m and r.get("grain") and m.get("grain") is not None and m["grain"] < TOO_CLEAN * r["grain"]:
            gaps.append((5, f"band {i + 1}: the surface reads too clean — grain {m['grain'] / r['grain']:.0%} of the photo's. "
                            f"Age is a layer inside the material: darker in cavities and under rims (AO), worn light on "
                            f"edges, fine pits and dents in the relief"))
    for r in metals:
        if r.get("mask_soft", 1) < CONFETTI_SOFT and r.get("mask_largest", 1) < CONFETTI_LARGEST:
            gaps.append((7, f"material {r['material']}: metal in scattered hard-edged islands (largest {r['mask_largest']:.0%} of "
                            f"the metal, {r['mask_soft']:.0%} of texels in between) — reads as camouflage. Wear is one "
                            f"region following the form (edges, handled parts) with soft transitions; never a thresholded noise"))
        if r.get("mask_mean", 1.0) < MOSTLY_PAINTED:
            gaps.append((6, f"material {r['material']}: most of this metal is painted as non-metal (metallic {r['mask_mean']:.2f} "
                            f"on average) — a non-metal reflects white, and the part reads grey. Keep tarnish and patina "
                            f"metallic (darker, rougher); only crusts — thick rust, soot, dirt — are non-metal"))
        if r.get("base_median", 1.0) < DARK_METAL:
            gaps.append((8, f"material {r['material']}: metal with a base colour of {r['base_median']:.2f} (sRGB luminance, "
                            f"median over its {r['metal_share']:.0%} metallic texels; below {DARK_METAL}) — a black mirror under "
                            f"any light. Brighten the metal, and paint rust, soot and dirt as NON-metal (real aged brass: 0.30) — where the form wears, one soft region, not a share to reach"))
    # The tier's range is a guide, not a cap (rule 4). Listed last, as information: ranked
    # first, it read as the top defect and a session spent its review cutting round parts.
    # A reduction is proposed only past twice the tier's top.
    if "max-tris" in o and tris > int(o["max-tris"]):
        top = int(o["max-tris"]); far = tris > 2 * top
        gaps.append((10 if far else -1, f"{tris:,} triangles, above the tier's {top:,} (+{tris / top - 1:.0%}) — "
                     + ("over twice the range: propose a reduction (rule 6)" if far
                        else "within reason: report it and where they go (round parts, wires), do not cut")))
    gaps.sort(key=lambda g: -g[0])

    ov = np.zeros((H, W, 4), np.float32); ov[..., 3] = 1
    ov[..., 0] = R * 0.95; ov[..., 1] = M * 0.85; ov[..., 2] = M * 0.95
    save(ov, os.path.join(o["out"], "overlay.png"))
    bg = lambda a: np.concatenate([a[..., :3] * a[..., 3:4] + 0.25 * (1 - a[..., 3:4]), np.ones_like(a[..., :1])], -1)
    save(np.concatenate([bg(pad_to(ref, W)), np.ones((H, 12, 4), np.float32), bg(pad_to(mod_c, W))], 1),
         os.path.join(o["out"], "side_by_side.png"))

    ends = contact_ends(meshes)
    joints = render_joints(sc, ends, os.path.join(o["out"], "joints"), (lo + hi) / 2) if ends else []
    print("FIDELITY " + json.dumps(dict(tris=tris, meshes=nmesh, iou=iou, shape=shape, material=dict(reference=mref, model=mmod), metals=metals,
                                        joints=joints, gaps=[g[1] for g in gaps])))
    print(f"\n{tris:,} tris in {nmesh} meshes · silhouette IoU {iou:.3f} (information, not a target: "
          f"a real object scores ~0.80 against its own photo) — gaps to close, largest first:")
    for _, g in gaps[:12]:
        print("  -", g)
    if not gaps:
        print("  - none above tolerance")
    if joints:
        print(f"\n{len(ends)} joints where a long part ends on another — LOOK at each ({o['out']}/joints/, two views):"
              " it must enter the other part or sit on a shaped foot; a flat cut resting on a curve reads unconnected")


main()
