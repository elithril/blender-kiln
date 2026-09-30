"""Measure how far a model is from its reference image — shape and material, in numbers.

    blender -b --factory-startup --python-exit-code 1 --python tools/fidelity_check.py -- \\
        --reference ref.png --model asset.blend|asset.glb --hdri studio.hdr --out review/ [--samples 64]

Renders the model twice from the front, orthographic — a flat silhouette, and a colour
render under a studio HDRI — scales it to the reference's height, and compares:

- shape: silhouette IoU, and per height band the width difference (full and core);
- material, per band: luminance, saturation, warmth (R−B), highlight share, texture
  detail (high-pass energy) and value spread.

Prints one JSON line (`FIDELITY {...}`) and a ranked list of the largest gaps, and writes
`overlay.png` (red: reference only, cyan: model only) and `side_by_side.png` into --out.

Why: a session reviewing by eye over-corrected twice on the bench — too bright and
blotchy, then grey and flat. These are the numbers that showed it. They are only as good
as the match between the two views: the reference's camera and light are unknown, so
read differences of a few percent as noise, and large ones as the fix list.
"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector

BANDS = 5


def args():
    a = sys.argv[sys.argv.index("--") + 1:]
    o = {"samples": "64"}
    for k, v in zip(a[::2], a[1::2]):
        o[k.lstrip("-")] = v
    for k in ("reference", "model", "hdri", "out"):
        if k not in o:
            sys.exit(f"fidelity_check: missing --{k}")
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
    cs = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(c[i] for c in cs) for i in range(3)])
    hi = Vector([max(c[i] for c in cs) for i in range(3)])
    return sc, lo, hi


def render(sc, lo, hi, path, engine, hdri=None, samples=64):
    ctr, H = (lo + hi) / 2, hi.z - lo.z
    cam = bpy.data.objects.get("_fidelity_cam")
    if cam is None:
        cam = bpy.data.objects.new("_fidelity_cam", bpy.data.cameras.new("_fidelity_cam"))
        sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = H * 1.02
    cam.location = ctr + Vector((0, -3 * H, 0)); cam.rotation_euler = (math.pi / 2, 0, 0)   # front, -Y looking +Y
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
    H, out = a.shape[0], []
    for i in range(BANDS):
        k = np.zeros_like(m); k[i * H // BANDS:(i + 1) * H // BANDS] = True; k &= e
        L = lum[k]
        out.append(None if L.size < 50 else dict(
            lum=float(L.mean()), sat=float(sat[k].mean()),
            warm=float((rgb[..., 0] - rgb[..., 2])[k].mean()),
            highlights=float((L > 0.55).mean()), detail=float(hp[k].mean()),
            spread=float(np.percentile(L, 95) - np.percentile(L, 5))))
    return out


def save(arr, path):
    arr = np.ascontiguousarray(arr[::-1])
    img = bpy.data.images.new(os.path.basename(path), arr.shape[1], arr.shape[0], alpha=True)
    img.pixels = arr.ravel().tolist(); img.filepath_raw = path; img.file_format = "PNG"; img.save()


def main():
    o = args()
    sc, lo, hi = open_model(o["model"])
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

    gaps = []
    for b in shape:
        if b["iou"] < 0.8:
            gaps.append((1 - b["iou"], f"band {b['band']}/{BANDS} (1 = top): silhouette IoU {b['iou']:.2f}, "
                                      f"width {b['full_width']:+.0%}, core {b['core_width']:+.0%}"))
    for i, (r, m) in enumerate(zip(mref, mmod)):
        if not r or not m:
            continue
        for k, tol in (("sat", 0.06), ("warm", 0.02), ("detail", 0.008), ("lum", 0.03), ("highlights", 0.008)):
            d = m[k] - r[k]
            if abs(d) > tol:
                gaps.append((abs(d) / tol / 10, f"band {i + 1}: {k} {m[k]:.3f} vs reference {r[k]:.3f} ({d:+.3f})"))
    gaps.sort(key=lambda g: -g[0])

    ov = np.zeros((H, W, 4), np.float32); ov[..., 3] = 1
    ov[..., 0] = R * 0.95; ov[..., 1] = M * 0.85; ov[..., 2] = M * 0.95
    save(ov, os.path.join(o["out"], "overlay.png"))
    bg = lambda a: np.concatenate([a[..., :3] * a[..., 3:4] + 0.25 * (1 - a[..., 3:4]), np.ones_like(a[..., :1])], -1)
    save(np.concatenate([bg(pad_to(ref, W)), np.ones((H, 12, 4), np.float32), bg(pad_to(mod_c, W))], 1),
         os.path.join(o["out"], "side_by_side.png"))

    print("FIDELITY " + json.dumps(dict(iou=iou, shape=shape, material=dict(reference=mref, model=mmod),
                                        gaps=[g[1] for g in gaps])))
    print(f"\nsilhouette IoU {iou:.3f} — largest gaps first:")
    for _, g in gaps[:12]:
        print("  -", g)
    if not gaps:
        print("  - none above tolerance")


main()
