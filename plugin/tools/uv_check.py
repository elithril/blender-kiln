"""Check a model's UVs before a texture goes on them, or before it ships with one.

    blender -b --factory-startup --python-exit-code 1 --python tools/uv_check.py -- \\
        MODEL [MODEL ...] [--grid 512] [--json report.json]

The October 2026 sessions unwrapped every skin with Smart UV Project and none could say
whether the result was usable: there was no UV check, and a UV defect on one corner of a
model had already passed every count (SKILL.md rule 2). This reads each mesh's active UV map:

- missing: a mesh with no UV map whose material samples an image texture — FAIL (it renders
  that texture's first texel); without a texture (flat colours, vertex colours) it is only said;
- collapsed: faces whose UV area is under 1 % of what their 3D area asks at the mesh's median
  density — a texture smears across them — FAIL past 1 % of the surface;
- overlap: texels covered by two faces or more, rasterised on a --grid square — right for a
  tiled or mirrored material, wrong for a bake (two places share one texel) — WARN past 2 %;
- stretch: the share of the surface whose texel density is off the median by more than 2x in
  area (1.4x across) — WARN past 10 %;
- flipped: faces whose UVs wind the other way (a mirrored island: a normal map reads its
  slopes reversed there) — WARN past 2 %;
- outside: faces with a UV outside the 0-1 tile — WARN (a bake only fills 0-1);
- used: the share of the 0-1 tile the faces cover — reported.

MODEL: GLB/glTF, .blend or OBJ, in metres. Exit 0 when nothing FAILs, 1 otherwise (and on an
error). Prints one line per mesh and a JSON report with --json.
"""
import json, os, sys

import bpy
import numpy as np

COLLAPSED, OVERLAP, STRETCH, FLIPPED = 0.01, 0.02, 0.10, 0.02


def die(msg):
    print(f"uv_check: {msg}", file=sys.stderr)
    sys.exit(1)


def args():
    import argparse
    p = argparse.ArgumentParser(prog="uv_check.py")
    p.add_argument("models", nargs="+")
    p.add_argument("--grid", type=int, default=512, help="texels per side for the overlap count")
    p.add_argument("--json")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    for m in a.models:
        if not os.path.isfile(m):
            die(f"no such file: {m}")
    return a


def load(path):
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".blend":
        with bpy.data.libraries.load(path) as (src, dst):
            dst.objects = list(src.objects)
        for o in dst.objects:
            if o is not None:
                bpy.context.scene.collection.objects.link(o)
    else:
        die(f"{path}: GLB/glTF, OBJ or .blend")
    shapes = {pb.custom_shape for o in bpy.data.objects if o.type == "ARMATURE" and o.pose
              for pb in o.pose.bones if pb.custom_shape}
    return [o for o in bpy.data.objects if o not in before and o.type == "MESH" and o not in shapes
            and not any(c.name.startswith("glTF_not_exported") for c in o.users_collection)]


def textured(o):
    return any(n.type == "TEX_IMAGE" and n.image for s in o.material_slots if s.material and s.material.node_tree
               for n in s.material.node_tree.nodes)


def raster(tris, grid):
    """How many triangles cover each texel centre of the 0-1 tile (strictly inside: shared edges count once)."""
    count = np.zeros((grid, grid), dtype=np.uint16)
    for t in tris:
        lo = np.clip(np.floor(t.min(axis=0) * grid - 0.5), 0, grid - 1).astype(int)
        hi = np.clip(np.ceil(t.max(axis=0) * grid - 0.5), 0, grid - 1).astype(int)
        if (t.max(axis=0) < 0).any() or (t.min(axis=0) > 1).any():
            continue
        xs = (np.arange(lo[0], hi[0] + 1) + 0.5) / grid
        ys = (np.arange(lo[1], hi[1] + 1) + 0.5) / grid
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        (x0, y0), (x1, y1), (x2, y2) = t
        d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(d) < 1e-14:
            continue
        a = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / d
        b = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / d
        inside = (a > 1e-9) & (b > 1e-9) & (1 - a - b > 1e-9)
        count[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1] += inside.astype(np.uint16)
    return count


def check(o, grid):
    me = o.data
    r = dict(object=o.name, faces=len(me.polygons), uv=None, status="ok", notes=[])
    if not me.uv_layers:
        r["uv"] = None
        if textured(o):
            r["status"] = "FAIL"; r["notes"].append("no UV map, and its material samples an image texture")
        else:
            r["notes"].append("no UV map (no image texture needs one)")
        return r
    uv = me.uv_layers.active or me.uv_layers[0]
    r["uv"] = uv.name
    me.calc_loop_triangles()
    lt = me.loop_triangles
    n = len(lt)
    if n == 0:
        return r
    loops = np.zeros(n * 3, dtype=np.int64); lt.foreach_get("loops", loops)
    verts = np.zeros(n * 3, dtype=np.int64); lt.foreach_get("vertices", verts)
    U = np.zeros(len(me.loops) * 2); uv.data.foreach_get("uv", U); U = U.reshape(-1, 2)[loops].reshape(n, 3, 2)
    M = np.array(o.matrix_world)
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    P = (co @ M[:3, :3].T + M[:3, 3])[verts].reshape(n, 3, 3)
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    e1, e2 = U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]
    signed = 0.5 * (e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    a2 = np.abs(signed)
    real = a3 > 1e-12
    total = a3[real].sum()
    if total <= 0:
        return r
    dens = a2[real] / a3[real]
    order = np.argsort(dens); cum = np.cumsum(a3[real][order])
    median = dens[order][np.searchsorted(cum, cum[-1] / 2)]
    if median <= 0:
        r["status"] = "FAIL"; r["notes"].append("every face's UVs are collapsed"); r["collapsed"] = 1.0
        return r
    rel = dens / median
    w = a3[real] / total
    r["collapsed"] = round(float(w[rel < 0.01].sum()), 4)
    r["stretch"] = round(float(w[(rel > 2) | (rel < 0.5)].sum()), 4)
    # flipped: the minority winding, by surface
    pos, neg = w[signed[real] > 0].sum(), w[signed[real] < 0].sum()
    r["flipped"] = round(float(min(pos, neg)), 4)
    r["outside"] = round(float(((U < -1e-6) | (U > 1 + 1e-6)).any(axis=(1, 2)).mean()), 4)
    cnt = raster(U[real], grid)
    used = (cnt > 0).sum()
    r["used"] = round(float(used / grid ** 2), 4)
    r["overlap"] = round(float((cnt > 1).sum() / used), 4) if used else 0.0
    if r["collapsed"] > COLLAPSED:
        r["status"] = "FAIL"
        r["notes"].append(f"collapsed UVs on {100 * r['collapsed']:.1f} % of the surface: a texture smears there")
    warn = []
    if r["overlap"] > OVERLAP:
        warn.append(f"overlap {100 * r['overlap']:.1f} % of the used texels — fine tiled or mirrored, wrong for a bake")
    if r["stretch"] > STRETCH:
        warn.append(f"stretch: {100 * r['stretch']:.1f} % of the surface off the median density by more than 2x")
    if r["flipped"] > FLIPPED:
        warn.append(f"flipped: {100 * r['flipped']:.1f} % of the surface winds the other way (a normal map reads it reversed)")
    if r["outside"] > 0:
        warn.append(f"outside the 0-1 tile: {100 * r['outside']:.1f} % of the faces (a bake fills 0-1 only)")
    if warn and r["status"] == "ok":
        r["status"] = "WARN"
    r["notes"] += warn
    return r


def main():
    a = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    meshes = [o for m in a.models for o in load(m)]
    if not meshes:
        die("no mesh in the model(s)")
    report = [check(o, a.grid) for o in meshes]
    for r in report:
        figures = ", ".join(f"{k} {100 * r[k]:.1f} %" for k in ("used", "overlap", "stretch", "collapsed", "flipped")
                            if k in r)
        print(f"{r['status']:4} {r['object']} ({r['faces']} faces, UV {r['uv'] or 'none'})"
              + (f": {figures}" if figures else "") + "".join(f"\n       {n}" for n in r["notes"]))
    fails = sum(r["status"] == "FAIL" for r in report)
    print(f"uv_check: {len(report)} mesh(es), {fails} FAIL, {sum(r['status'] == 'WARN' for r in report)} WARN")
    if a.json:
        json.dump(report, open(a.json, "w"), indent=1)
    sys.exit(1 if fails else 0)


try:
    main()
except SystemExit:
    raise
except Exception as e:                                     # fail loud: --python-exit-code turns this into 1
    die(f"{type(e).__name__}: {e}")
