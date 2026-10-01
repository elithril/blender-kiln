"""Read a turned object's real profile off a 3D template — a generated mesh, a scan.

    blender -b --factory-startup --python-exit-code 1 --python tools/template_profile.py -- \\
        --template trellis.glb --height <real height, m> [--bands 40] [--json out.json]

A photo bends proportions: a camera 15° above makes every disc's top an ellipse and every
base taller than it is — the bench's lanterns came out with bases 13-30 % off reading the
photo alone. A generated mesh of the same photo (TRELLIS.2) holds the proportions in 3D —
0.952 against the real object from five sides, where scripted reconstructions reached
0.86-0.90 — but its surface is unusable as an asset (facets, smeared texture, broken wires
once decimated). So measure it, and model clean from the measures.

The template is scaled to --height (a generated mesh is always 1 m tall), its axis fitted
on the foot's circle, then cut by horizontal planes. Per band, the radial
distances of the cut are grouped into clusters: the first is the body (its outer radius
is the profile to lathe), the next are what stands around it — tubes, a guard, a bail —
with their distance from the axis. Prints one line per band and, with --json, writes them.
"""
import bpy, bmesh, json, math, sys
import numpy as np
from mathutils import Vector


ROUND = 0.75                                # share of 36 sectors: a part turned about the axis


def args():
    a = sys.argv[sys.argv.index("--") + 1:]
    o = {"bands": "40"}
    for k, v in zip(a[::2], a[1::2]):
        o[k.lstrip("-")] = v
    if "template" not in o or "height" not in o:
        sys.exit("template_profile: --template and --height (metres, the real object's) are required")
    return o


def joined_mesh(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    sc = bpy.context.scene
    shapes = {pb.custom_shape for a in sc.objects if a.type == "ARMATURE" for pb in a.pose.bones if pb.custom_shape}
    bm = bmesh.new()
    for ob in [o for o in sc.objects if o.type == "MESH" and o not in shapes]:
        m = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        m.transform(ob.matrix_world)
        bm.from_mesh(m)
    if not bm.verts:
        sys.exit("template_profile: no mesh in the template")
    return bm


def clusters(r, ang, gap):
    """Group a cut's points by distance from the axis; each group with its angular coverage
    — a turned part goes all the way round, a tube or a wire covers a few degrees."""
    k = np.argsort(r); r, ang = r[k], ang[k]; out, start = [], 0
    for i in range(1, len(r) + 1):
        if i == len(r) or r[i] - r[i - 1] > gap:
            sec = (ang[start:i] / (2 * math.pi) * 36).astype(int) % 36
            bins = np.unique(sec)
            # A wire touching a turned part joins its group; it covers a few sectors only,
            # so the turned radius is the median of the sectors' outer radii, not the max.
            outer = np.median([r[start:i][sec == b].max() for b in bins])
            out.append(dict(r_in=float(r[start]), r_out=float(r[i - 1]), r_turned=float(outer), round=len(bins) / 36))
            start = i
    return out


def section(bm, z):
    cut = bm.copy()
    res = bmesh.ops.bisect_plane(cut, geom=cut.verts[:] + cut.edges[:] + cut.faces[:],
                                 plane_co=(0, 0, z), plane_no=(0, 0, 1), dist=1e-7)
    pts = np.array([v.co[:2] for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]).reshape(-1, 2)
    cut.free()
    return pts


def main():
    o = args()
    H, n = float(o["height"]), int(o["bands"])
    bm = joined_mesh(o["template"])
    co = np.array([v.co[:] for v in bm.verts])
    z0, z1 = co[:, 2].min(), co[:, 2].max()
    s = H / (z1 - z0)
    for v in bm.verts:
        v.co = (v.co - Vector((0, 0, z0))) * s
    co = np.array([v.co[:] for v in bm.verts])
    gap = 0.008 * H                         # 2.4 mm on a 30 cm lantern
    # The axis: the foot's circle. A bounding-box centre is pulled by anything else reaching
    # the floor (a tube, a leg): start from the median, keep the cut's points that go all
    # the way round, and fit their circle (algebraic least squares).
    low = co[co[:, 2] < 0.08 * H]
    ax = np.median(low[:, :2], 0)
    for _ in range(2):
        pts = section(bm, 0.04 * H)
        d = pts - ax; r = np.hypot(d[:, 0], d[:, 1])
        ring = [q for q in clusters(r, np.arctan2(d[:, 1], d[:, 0]) % (2 * math.pi), gap) if q["round"] >= ROUND]
        if not ring:
            break
        q = ring[-1]; k = (r >= q["r_in"]) & (r <= q["r_out"])
        x, y = pts[k, 0], pts[k, 1]
        A = np.c_[2 * x, 2 * y, np.ones_like(x)]
        cx, cy, _ = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
        ax = np.array([cx, cy])
    rows = []
    for i in range(n):
        z = (i + 0.5) * H / n
        pts = section(bm, z)
        if len(pts) < 3:
            rows.append(dict(z=z, parts=[])); continue
        d = pts - ax
        rows.append(dict(z=z, parts=clusters(np.hypot(d[:, 0], d[:, 1]), np.arctan2(d[:, 1], d[:, 0]) % (2 * math.pi), gap)))
    print(f"template scaled x{s:.3f} to {H * 100:.1f} cm · axis at ({ax[0]:+.4f}, {ax[1]:+.4f}) m")
    print("height (cm)  turned (outer radius, cm)   around it: radius from the axis (cm) · coverage")
    for row in reversed(rows):
        turned = [q for q in row["parts"] if q["round"] >= ROUND]
        rest = [q for q in row["parts"] if q["round"] < ROUND]
        t = f"{turned[-1]['r_turned'] * 100:6.2f}" + (f" (shell from {turned[-1]['r_in'] * 100:.2f})"
             if turned[-1]["r_out"] - turned[-1]["r_in"] < 0.004 * H else "") + (
             f" + reaching {turned[-1]['r_out'] * 100:.1f}" if turned[-1]["r_out"] - turned[-1]["r_turned"] > 0.01 * H else ""
             ) if turned else "     —"
        print(f"{row['z'] * 100:9.1f}  {t:<28}  " + "  ".join(
            f"{q['r_in'] * 100:.1f}–{q['r_out'] * 100:.1f} · {q['round']:.0%}" for q in rest))
    if "json" in o:
        json.dump(dict(height_m=H, scale=s, bands=rows), open(o["json"], "w"), indent=1)


main()
