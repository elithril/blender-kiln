"""The review sheet: the model as a viewer will see it, six views on one image — what each review
round of references/review-rounds.md looks at.

    blender -b --factory-startup --python-exit-code 1 --python tools/review_sheet.py -- \\
        MODEL --out SHEET.png [--res 900] [--close top|X,Y,Z,SIZE]

- front, both three-quarters, side, back, and a close-up — by default the top 45 % of the model
  (a character's head, a lantern's cap); --close X,Y,Z,SIZE (mm) aims it elsewhere;
- a studio light (key, fill, rim) on a dark floor, EEVEE, Khronos PBR Neutral, perspective: the
  colours, materials and finish a person judges, which the orthographic matcap/colour renders of
  tools/review_renders.py are not made for (those check the geometry);
- a rigged model is shown in its REST pose and framed on its vertices: framed on its active clip, a
  walk that travels left the character a few pixels in a corner (kiln's mascot, 2026-10-28);
- each tile's framing is checked: a subject whose projected box covers under 1 % of it is an error, exit 1.

Writes SHEET.png (3 x 2 tiles) and SHEET_{view}.png; prints SHEET <path> and one VIEW line per tile.
"""
import math, os, sys

import bpy
import numpy as np
from mathutils import Vector

VIEWS = (("front", -90, 9), ("q_left", -55, 13), ("q_right", -125, 13),
         ("side", 0, 7), ("back", 120, 14))          # (name, azimuth deg — the front is -Y, elevation deg)


def args():
    a = sys.argv[sys.argv.index("--") + 1:]
    o = {"res": 900, "close": "top", "models": []}
    i = 0
    while i < len(a):
        if a[i] in ("--out", "--res", "--close"):
            o[a[i][2:]] = a[i + 1]; i += 2
        else:
            o["models"].append(a[i]); i += 1
    if not o["models"] or "out" not in o:
        sys.exit("review_sheet: MODEL ... --out SHEET.png")
    o["res"] = int(o["res"])
    missing = [m for m in o["models"] if not os.path.isfile(m)]
    if missing:
        sys.exit(f"review_sheet: no such file: {', '.join(missing)}")
    return o


def load(paths):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for p in paths:
        if p.lower().endswith(".blend"):
            with bpy.data.libraries.load(p) as (src, dst):
                dst.objects = list(src.objects)
            for ob in dst.objects:
                if ob is not None and ob.type in ("MESH", "ARMATURE", "EMPTY"):
                    bpy.context.scene.collection.objects.link(ob)
        else:
            bpy.ops.import_scene.gltf(filepath=p)
    for arm in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
        arm.data.pose_position = "REST"
        for pb in arm.pose.bones:
            if pb.custom_shape:
                pb.custom_shape.hide_render = True
    bpy.context.view_layer.update()


def vertices():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    shapes = {pb.custom_shape for a in bpy.data.objects if a.type == "ARMATURE" for pb in a.pose.bones if pb.custom_shape}
    for o in bpy.data.objects:
        if o.type != "MESH" or o in shapes or o.hide_render:
            continue
        e = o.evaluated_get(dg); me = e.to_mesh()
        pts += [e.matrix_world @ v.co for v in me.vertices]
        e.to_mesh_clear()
    if not pts:
        sys.exit("review_sheet: no mesh to show")
    return np.array([p[:] for p in pts])


def studio(sc, size, centre):
    world = bpy.data.worlds.new("review"); sc.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.014, 0.022, 1); bg.inputs["Strength"].default_value = 0.42
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=max(200.0, size * 60), fill_type="NGON",
                                      location=(centre.x, centre.y, 0.0))
    g = bpy.context.object; g.name = "review_floor"
    m = bpy.data.materials.new("review_floor"); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.006, 0.008, 0.013, 1); b.inputs["Roughness"].default_value = 0.62
    g.data.materials.append(m)
    s = max(size, 0.35); k = (s / 0.9) ** 2
    for name, energy, sz, loc, rot, col in (
            ("key", 115 * k, 3.2 * s, (2.6 * s, -2.2 * s, 3.1 * s), (0.85, 0.18, 0.86), (1.0, 0.97, 0.93)),
            ("fill", 26 * k, 4.5 * s, (-3.0 * s, -1.7 * s, 1.5 * s), (1.16, -0.1, -1.05), (0.82, 0.88, 1.0)),
            ("rim", 72 * k, 2.0 * s, (-1.4 * s, 3.0 * s, 2.4 * s), (1.05, 0.05, -2.65), (0.90, 0.94, 1.0))):
        l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.size = sz; l.color = col
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
        o.location = Vector(loc) + Vector((centre.x, centre.y, 0)); o.rotation_euler = rot


def camera(sc, pts, azim, elev, margin=1.08, lens=72.0):
    for o in [o for o in sc.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o)
    cd = bpy.data.cameras.new("review_cam"); cd.lens = lens
    cam = bpy.data.objects.new("review_cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    lo, hi = pts.min(0), pts.max(0); c = Vector(((lo + hi) / 2).tolist())
    d = Vector((math.cos(elev) * math.cos(azim), math.cos(elev) * math.sin(azim), math.sin(elev)))
    right = d.cross(Vector((0, 0, 1))).normalized(); up = right.cross(d).normalized()
    rel = pts - np.array(c[:])
    half = max(np.abs(rel @ np.array(right[:])).max(), np.abs(rel @ np.array(up[:])).max())
    depth = (rel @ np.array(d[:])).max()
    fov = 2 * math.atan(cd.sensor_width / (2 * lens))
    cam.location = c + d * ((half * margin) / math.tan(fov / 2) + depth)
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()


def render(sc, path, res):
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = path
    sc.eevee.taa_render_samples = 48
    for attr, val in (("use_shadows", True), ("use_raytracing", True)):
        if hasattr(sc.eevee, attr):
            setattr(sc.eevee, attr, val)
    try:                                   # a dynamic enum: its items cannot be listed from bl_rna
        sc.view_settings.view_transform = "Khronos PBR Neutral"
    except TypeError:
        sc.view_settings.view_transform = "Standard"
    bpy.ops.render.render(write_still=True)


def coverage(sc, pts):
    """Share of the frame the subject's projected box covers — an empty or misplaced model reads ~0."""
    from bpy_extras.object_utils import world_to_camera_view
    sel = pts[:: max(1, len(pts) // 4000)]
    uv = np.array([world_to_camera_view(sc, sc.camera, Vector(p.tolist()))[:2] for p in sel])
    uv = np.clip(uv, 0, 1)
    return float(np.prod(uv.max(0) - uv.min(0)))


def main():
    o = args()
    load(o["models"])
    sc = bpy.context.scene
    pts = vertices()
    lo, hi = pts.min(0), pts.max(0)
    size = float(np.linalg.norm(hi - lo))
    studio(sc, size, Vector(((lo + hi) / 2).tolist()))
    if o["close"] == "top":
        close = pts[pts[:, 2] >= hi[2] - 0.45 * (hi[2] - lo[2])]
    else:
        x, y, z, s = (float(v) / 1000 for v in o["close"].split(","))
        close = np.array([[x - s / 2, y - s / 2, z - s / 2], [x + s / 2, y + s / 2, z + s / 2]])
    out = o["out"]; base = out[:-4] if out.endswith(".png") else out
    paths, bad = [], []
    for name, az, el in VIEWS + (("close", -72, 8),):
        camera(sc, close if name == "close" else pts, math.radians(az), math.radians(el),
               margin=1.15 if name == "close" else 1.08)
        p = f"{base}_{name}.png"; render(sc, p, o["res"]); paths.append(p)
        cov = coverage(sc, pts)
        print(f"VIEW {name} {p} subject {cov * 100:.0f} %")
        if cov < 0.01:
            bad.append(name)
    tiles = []
    for p in paths:
        im = bpy.data.images.load(p); w, h = im.size
        tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)); bpy.data.images.remove(im)
    sheet = np.concatenate([np.concatenate(tiles[3:], 1), np.concatenate(tiles[:3], 1)], 0)  # bottom-up rows
    img = bpy.data.images.new("review_sheet", w * 3, h * 2, alpha=True)
    img.pixels.foreach_set(sheet.ravel()); img.filepath_raw = base + ".png"; img.file_format = "PNG"; img.save()
    print(f"SHEET {base}.png")
    if bad:
        sys.exit(f"review_sheet: nothing in view on {', '.join(bad)} — check the model's place and size")


main()
