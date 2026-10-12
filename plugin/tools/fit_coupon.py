"""A test print for a peg in a hole: the clearance measured on the printer, not assumed.

    blender -b --factory-startup --python-exit-code 1 --python tools/fit_coupon.py -- \\
        --out DIR [--peg-mm 4.0] [--depth-mm 3.5] [--clear-mm 0.1 0.2 0.3] [--chamfer-mm 0.5]

The clearance of a joint (print.md, § Like the photo rule 9) is a usual value, not one
measured here, and the sources disagree on what 0.2 mm is: a slip fit per side for some, a
total over the diameter for others. Printed parts also come out 0.1-0.3 mm larger than the
model. This writes two STLs (mm) that answer it for one printer:

- `fit_holes.stl`, a plate --depth-mm thick laid flat, with one diamond hole per clearance:
  the peg's side plus twice the clearance (the clearance is per face). Then one more hole at
  the middle clearance with a 45 degree lead-in chamfer --chamfer-mm deep on the bed face:
  the first layer is squashed outward (the "elephant's foot") and closes a hole that opens
  on the bed. Hole n is marked by n dots, engraved 0.6 mm on the top face;
- `fit_peg.stl`, a wall standing on the bed with the peg sticking out sideways, a square
  turned 45 degrees: the same shape and the same way of printing as a peg kiln models on an
  upright part (its lower faces at 45 degrees, no support).

The peg goes into each hole by hand: the tightest hole it enters is the clearance to model
with. Diamond pegs only, FDM only. Every hole is checked to the micron before writing, and
both parts must be closed solids; exit 0, 1 on an error.
"""
import json, math, os, sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import print_check as pc                                          # noqa: E402

PITCH, MARGIN, DOT_R, DOT_DEPTH = 12.0, 5.0, 0.75, 0.6


def args():
    p = pc.Parser(prog="fit_coupon.py")
    p.add_argument("--out", required=True, help="a folder; fit_holes.stl and fit_peg.stl are written there")
    p.add_argument("--peg-mm", type=float, default=4.0, help="the side of the diamond peg")
    p.add_argument("--depth-mm", type=float, default=3.5, help="the plate's thickness: how deep the peg goes")
    p.add_argument("--clear-mm", type=float, nargs="+", default=[0.1, 0.2, 0.3], help="per face")
    p.add_argument("--chamfer-mm", type=float, default=0.5, help="the lead-in on the extra hole (0: none)")
    p.add_argument("--json")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = p.parse_args(argv)
    if a.peg_mm < 2 or a.depth_mm < 1.5 or min(a.clear_mm) < 0 or a.chamfer_mm < 0:
        pc.die("peg >= 2 mm, depth >= 1.5 mm, clearances and chamfer >= 0")
    return a


def obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box(name, lo, hi):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=[h - l for l, h in zip(lo, hi)], verts=bm.verts)
    bmesh.ops.translate(bm, vec=[(l + h) / 2 for l, h in zip(lo, hi)], verts=bm.verts)
    return obj(name, bm)


def prism(name, side_lo, side_hi, z0, z1, centre, segments=4, axis="Z"):
    """A frustum along Z from z0 to z1: a diamond (corners on the axes) for 4 segments, a
    square side going from side_lo to side_hi; a round dot for more segments (side = diameter)."""
    k = 1 / math.sqrt(2) if segments == 4 else 0.5
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=side_lo * k, radius2=side_hi * k,
                          depth=z1 - z0)
    bmesh.ops.translate(bm, vec=(0, 0, (z0 + z1) / 2), verts=bm.verts)
    if axis == "-Y":                     # the peg: along -Y, a corner up and a corner down
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    bmesh.ops.translate(bm, vec=centre, verts=bm.verts)
    return obj(name, bm)


def boolean(target, cutter, op):
    m = target.modifiers.new("b", "BOOLEAN")
    m.operation, m.solver, m.object = op, "EXACT", cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(cutter)


def arrays(ob):
    me = ob.data
    me.calc_loop_triangles()
    V = np.array([v.co for v in me.vertices], dtype=float)
    F = np.array([t.vertices for t in me.loop_triangles], dtype=np.int64)
    return V, F


def closed(V, F):
    t, _, nparts, _ = pc.topology(V, F)
    return nparts == 1 and t["open_edges"] == 0 and t["nonmanifold_edges"] == 0 and t["inconsistent_edges"] == 0


def width_at(V, F, x, y, z, reach):
    """The hole's side measured where a plane at height z cuts it: the largest |dx|+|dy| of the
    section's points round the hole centre, i.e. half the diamond's diagonal, back to a side."""
    best = 0.0
    for tri in V[F]:
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            if (a[2] - z) * (b[2] - z) < 0:
                p = a + (b - a) * (z - a[2]) / (b[2] - a[2])
                d = abs(p[0] - x) + abs(p[1] - y)
                if best < d < reach + 1:   # this hole's own wall, not the plate's outline
                    best = d
    return best * math.sqrt(2)


def main():
    a = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(a.out, exist_ok=True)
    holes = [(c, 0.0) for c in a.clear_mm]
    if a.chamfer_mm > 0:
        holes.append((sorted(a.clear_mm)[len(a.clear_mm) // 2], a.chamfer_mm))
    reach = (a.peg_mm + 2 * max(a.clear_mm) + 2 * a.chamfer_mm) / math.sqrt(2)   # half a diagonal
    pitch = max(PITCH, 2 * reach + 3)
    W, cy = pitch * len(holes), MARGIN + reach
    H = cy + reach + 2 + 2 * DOT_R + MARGIN / 2
    T = a.depth_mm

    plate = box("FitHoles", (0, 0, 0), (W, H, T))
    report = []
    for i, (c, ch) in enumerate(holes):
        x, s = pitch * (i + 0.5), a.peg_mm + 2 * c
        boolean(plate, prism(f"h{i}", s, s, -1, T + 1, (x, cy, 0)), "DIFFERENCE")
        if ch:
            boolean(plate, prism(f"c{i}", s + 4 * ch, s, -ch, ch, (x, cy, 0)), "DIFFERENCE")
        for d in range(i + 1):
            dx = (d - i / 2) * (2 * DOT_R + 1.2)
            boolean(plate, prism(f"d{i}{d}", 2 * DOT_R, 2 * DOT_R, T - DOT_DEPTH, T + 1, (x + dx, H - MARGIN / 2 - DOT_R, 0),
                                 segments=24), "DIFFERENCE")
        report.append(dict(hole=i + 1, dots=i + 1, clearance_mm=c, side_mm=round(s, 3), chamfer_mm=ch,
                           centre_mm=[round(x, 4), round(cy, 4)]))
    V, F = arrays(plate)
    for r, (c, ch) in zip(report, holes):
        x = pitch * (r["hole"] - 0.5)
        r["measured_side_mm"] = round(width_at(V, F, x, cy, T / 2, reach), 4)
        r["measured_bed_side_mm"] = round(width_at(V, F, x, cy, 0.01, reach), 4)
        want_bed = r["side_mm"] + 2 * ch - 0.02 if ch else r["side_mm"]
        if abs(r["measured_side_mm"] - r["side_mm"]) > 1e-3 or abs(r["measured_bed_side_mm"] - want_bed) > 1e-3:
            pc.die(f"hole {r['hole']}: modelled {r['measured_side_mm']} / {r['measured_bed_side_mm']} mm, "
                   f"wanted {r['side_mm']} / {want_bed:.3f}")
    if not closed(V, F):
        pc.die("the plate is not a closed solid")
    pc.write_stl(os.path.join(a.out, "fit_holes.stl"), V, F)

    # the peg: a wall standing on the bed, the diamond out of its face along -Y, as on an upright part
    reach_p = a.peg_mm / math.sqrt(2)
    zc = 3 + reach_p                                       # its lower corner 3 mm above the bed
    wall = box("FitPeg", (-pitch / 2, 0, 0), (pitch / 2, 12, zc + reach_p + 3))   # 12 deep: a 6 mm wall read "Low bed adhesion"
    boolean(wall, prism("p", a.peg_mm, a.peg_mm, 0, a.depth_mm + 1 + 0.5, (0, 0.5, zc), axis="-Y"), "UNION")
    Vp, Fp = arrays(wall)
    if not closed(Vp, Fp):
        pc.die("the peg is not a closed solid")
    tip = Vp[Vp[:, 1] < -1e-6]
    side = (tip[:, 2].max() - tip[:, 2].min()) / math.sqrt(2)
    if abs(side - a.peg_mm) > 1e-3 or abs(-tip[:, 1].min() - (a.depth_mm + 1)) > 1e-3:
        pc.die(f"peg modelled {side:.4f} mm, {-tip[:, 1].min():.4f} long")
    pc.write_stl(os.path.join(a.out, "fit_peg.stl"), Vp, Fp)

    out = dict(peg_side_mm=a.peg_mm, peg_length_mm=a.depth_mm + 1, plate_mm=[round(W, 2), round(H, 2), T],
               holes=report)
    print(json.dumps(out, indent=1))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)


try:
    main()
except SystemExit:
    raise
except Exception as e:                                     # fail loud: --python-exit-code turns this into 1
    pc.die(f"{type(e).__name__}: {e}")
