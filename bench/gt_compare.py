"""Score a model against the reference's GROUND-TRUTH 3D model, from every side. Bench only.

    blender -b --factory-startup --python-exit-code 1 --python bench/gt_compare.py -- \\
        --truth truth.gltf --model a.glb [--model b.glb ...] --label a --label b [--out dir]

A session never sees the truth: it works from a photo, as a user would. This is the
marking scheme, not an input — it answers what a single photo cannot: the back, the
sides and the top, the real size, and proportions a camera angle distorts. On Poly Haven
references the truth is the asset itself (CC0), fetched through the public API.

Per view (front, back, left, right, top): silhouette IoU after scaling to the truth's
height. Then absolute height against the truth, and the base's share of the height —
the proportion a slightly high photo inflates (measured: kiln's lanterns 13-30 % taller
bases than the truth).
"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector

VIEWS = ["front", "back", "left", "right", "top"]


def args():
    a = sys.argv[sys.argv.index("--") + 1:]
    o = {"model": [], "label": [], "out": "/tmp/gt_compare"}
    for k, v in zip(a[::2], a[1::2]):
        k = k.lstrip("-")
        o[k].append(v) if isinstance(o.get(k), list) else o.__setitem__(k, v)
    if "truth" not in o or not o["model"] or len(o["model"]) != len(o["label"]):
        sys.exit("gt_compare: --truth, and one --label per --model")
    os.makedirs(o["out"], exist_ok=True)
    return o


def silhouettes(path, out_prefix, yaw_deg=0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.lower().endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    if yaw_deg:
        # A model may face another way than the truth — a crate long in X where the truth is
        # long in Y. Turn it about the vertical before comparing; main() keeps the best yaw.
        piv = bpy.data.objects.new("_yaw", None); sc.collection.objects.link(piv)
        for ob in [o for o in sc.objects if o.parent is None and o is not piv]:
            ob.parent = piv
        piv.rotation_euler = (0, 0, math.radians(yaw_deg)); bpy.context.view_layer.update()
    for ob in sc.objects:
        if ob.type in ("CAMERA", "LIGHT"):
            ob.hide_render = True
    shapes = {pb.custom_shape for a in sc.objects if a.type == "ARMATURE" for pb in a.pose.bones if pb.custom_shape}
    meshes = [ob for ob in sc.objects if ob.type == "MESH" and ob not in shapes and not ob.hide_render]
    cs = [ob.matrix_world @ Vector(c) for ob in meshes for c in ob.bound_box]
    lo = Vector([min(c[i] for c in cs) for i in range(3)]); hi = Vector([max(c[i] for c in cs) for i in range(3)])
    ctr, H, size = (lo + hi) / 2, hi.z - lo.z, hi - lo
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"
    sc.render.engine = "BLENDER_WORKBENCH"; sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 512; sc.render.image_settings.color_mode = "RGBA"
    poses = {"front": (Vector((0, -3 * H, 0)), (math.pi / 2, 0, 0)),
             "back": (Vector((0, 3 * H, 0)), (math.pi / 2, 0, math.pi)),
             "left": (Vector((-3 * H, 0, 0)), (math.pi / 2, 0, -math.pi / 2)),
             "right": (Vector((3 * H, 0, 0)), (math.pi / 2, 0, math.pi / 2)),
             "top": (Vector((0, 0, 3 * H)), (0, 0, 0))}
    files = {}
    for v in VIEWS:
        off, rot = poses[v]
        cam.location = ctr + off; cam.rotation_euler = rot
        cam.data.ortho_scale = (max(size.x, size.y) if v == "top" else max(H, size.x, size.y)) * 1.02
        sc.render.filepath = files[v] = f"{out_prefix}_{v}.png"
        bpy.ops.render.render(write_still=True)
    return files, float(H)


def mask(p):
    im = bpy.data.images.load(p, check_existing=False); w, h = im.size
    m = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1][..., 3] > 0.5
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def fit(m, H):
    h, w = m.shape; W = max(1, round(w * H / h))
    return m[(np.arange(H) * h / H).astype(int)][:, (np.arange(W) * w / W).astype(int)]


def iou(a, b):
    W = max(a.shape[1], b.shape[1])
    pad = lambda x: np.pad(x, ((0, 0), ((W - x.shape[1]) // 2, W - x.shape[1] - (W - x.shape[1]) // 2)))
    A, B = pad(a), pad(b)
    return float((A & B).sum() / (A | B).sum())


def base_share(m):
    """Height of the base (widest bottom part) as a share of the whole, from a side view."""
    H = m.shape[0]; cx = int(np.median(np.where(m)[1])); core = []
    for r in m[::-1]:
        if not r[cx]: core.append(0); continue
        a = b = cx
        while a > 0 and r[a - 1]: a -= 1
        while b < len(r) - 1 and r[b + 1]: b += 1
        core.append(b - a + 1)
    core = np.array(core, float); w = np.percentile(core[:int(0.25 * H)], 90)
    return next(i for i in range(int(0.02 * H), H) if core[i] < 0.75 * w) / H


def main():
    o = args()
    tfiles, tH = silhouettes(o["truth"], os.path.join(o["out"], "truth"))
    tm = {v: mask(f) for v, f in tfiles.items()}
    rows = {}
    for path, label in zip(o["model"], o["label"]):
        best = None
        for yaw in (0, 90, 180, 270):
            files, H = silhouettes(path, os.path.join(o["out"], f"{label}_y{yaw}"), yaw)
            per = {v: iou(tm[v], fit(mask(files[v]), tm[v].shape[0])) for v in VIEWS}
            mean = float(np.mean(list(per.values())))
            if best is None or mean > best[0]:
                best = (mean, yaw, per, files, H)
        mean, yaw, per, files, H = best
        rows[label] = dict(views=per, mean_iou=mean, yaw=yaw, height_m=H,
                           height_vs_truth=H / tH - 1, base_share=base_share(mask(files["front"])))
    truth_base = base_share(tm["front"])
    print("GT " + json.dumps(dict(truth_height_m=tH, truth_base_share=truth_base, models=rows)))
    print(f"\ntruth: {tH * 100:.1f} cm, base {truth_base:.1%} of the height")
    print(f"{'model':10} " + " ".join(f"{v:>6}" for v in VIEWS) + "   mean  yaw   height        base")
    for label, r in rows.items():
        print(f"{label:10} " + " ".join(f"{r['views'][v]:6.3f}" for v in VIEWS)
              + f"  {r['mean_iou']:.3f} {r['yaw']:>4}°  {r['height_m'] * 100:5.1f} cm {r['height_vs_truth']:+.0%}  "
                f"{r['base_share']:.1%} ({r['base_share'] / truth_base - 1:+.0%})")


main()
