#!/usr/bin/env python3
"""Seed what flatten.py claims to do, and check it does.

    python3 tools/test_flatten.py      # needs Blender at $BLENDER or the macOS default

Known meshes, written as STL by this script, with the answer fixed before the tool ran:

- a box whose top is a grid jittered by up to 0.15 mm: the top comes out flat (one height,
  to 1 micron), no vertex moves more than the tolerance, the sides do not move, the mesh
  stays closed;
- the same top jittered by up to 1 mm, past a 0.3 mm tolerance: left alone, and said so;
- a cylinder (96 sides) and a sphere (64 x 32): nothing moves — a curve is never flattened
  into facets;
- a shallow dome, 0.2 mm high over 40 mm — inside the tolerance, but curved on purpose:
  kept, and said so;
- a dense top waving smoothly by 0.15 mm (two bumps, not a quadric — the ghost's folds, where
  the first version made 0.3 mm facets): kept;
- a coarse top, one corner raised 0.2 mm (a face modelled slightly warped): flattened;
- a top jittered by 0.15 mm on a deliberate 5 degree slope: flat, and still at 5 degrees — the
  snap to an axis (within 1 degree) must not swallow a real slope;
- a box whose bottom is tilted 1.5 degrees, with --bed: the bottom comes out flat, at
  Z = 0, and the tilt is reported;
- two planks, the second 0.2 mm higher behind a vertical wall — relief under the tolerance:
  kept (an edge sharper than --edge-deg bounds a face; flattening across it would erase it);
- the same 0.2 mm rise as a 20 degree bevel (0.55 mm wide) — a chamfer a plank's edge has:
  kept (the first distance-grown version flattened the chest's bevels away);
- the whole box tilted 1 degree with its top jittered, --bed: laid level FIRST, then
  flattened — the top at one height, nothing held (flattening first snapped the sides upright
  while the box was still tilted, and 87 vertices could not follow);
- the output path equal to the input: refused, exit 1, the input untouched.
"""
import json, math, os, random, struct, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flatten.py")


def stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"test_flatten".ljust(80, b" ")); f.write(struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<3f", 0, 0, 0))
            for p in t:
                f.write(struct.pack("<3f", *p))
            f.write(b"\0\0")


def read(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    out = []
    for k in range(n):
        v = struct.unpack("<9f", data[84 + 50 * k + 12: 84 + 50 * k + 48])
        out.append([tuple(v[0:3]), tuple(v[3:6]), tuple(v[6:9])])
    return out


def grid_box(w, d, h, n, top=lambda x, y: 0.0, bottom=lambda x, y: 0.0):
    """A closed box w x d x h (mm): top and bottom are n x n grids displaced by top()/bottom(),
    the four sides are strips sharing the grids' border vertices exactly."""
    def p(i, j, z0, f):
        x, y = w * i / n, d * j / n
        return (x, y, z0 + f(x, y))
    tris = []
    for i in range(n):
        for j in range(n):
            a, b, c, e = p(i, j, h, top), p(i + 1, j, h, top), p(i + 1, j + 1, h, top), p(i, j + 1, h, top)
            tris += [[a, b, c], [a, c, e]]                                   # top, facing up
            a, b, c, e = p(i, j, 0, bottom), p(i + 1, j, 0, bottom), p(i + 1, j + 1, 0, bottom), p(i, j + 1, 0, bottom)
            tris += [[a, c, b], [a, e, c]]                                   # bottom, facing down
    ring = [(i, 0) for i in range(n)] + [(n, j) for j in range(n)] + \
           [(n - i, n) for i in range(n)] + [(0, n - j) for j in range(n)]
    for k in range(len(ring)):
        (i0, j0), (i1, j1) = ring[k], ring[(k + 1) % len(ring)]
        lo0, lo1 = p(i0, j0, 0, bottom), p(i1, j1, 0, bottom)
        hi0, hi1 = p(i0, j0, h, top), p(i1, j1, h, top)
        tris += [[lo0, lo1, hi1], [lo0, hi1, hi0]]                           # sides, facing out
    return tris


def step_box(w, d, h, dz, run=0.0):
    """A closed box whose top has two planks, the right one dz higher, joined by a wall from
    x = w/2 to x = w/2 + run: vertical when run = 0 (a step), slanted otherwise (a bevel)."""
    m = w / 2
    A = [(0, 0, 0), (w, 0, 0), (w, d, 0), (0, d, 0)]                         # bottom
    fl = [(0, 0, h), (m, 0, h), (m, d, h), (0, d, h)]                       # left plank top
    fr = [(m + run, 0, h + dz), (w, 0, h + dz), (w, d, h + dz), (m + run, d, h + dz)]   # right plank top
    q = lambda a, b, c, e: [[a, b, c], [a, c, e]]
    tris = q(A[0], A[3], A[2], A[1])                                        # bottom, down
    tris += q(fl[0], fl[1], fl[2], fl[3]) + q(fr[0], fr[1], fr[2], fr[3])   # tops, up
    tris += q(fl[1], fr[0], fr[3], fl[2])                                   # the step's wall, facing -x
    tris += q(A[0], A[1], fr[1], fr[0]) + [[A[0], fr[0], fl[1]], [A[0], fl[1], fl[0]]]      # front (y = 0)
    tris += q(A[2], A[3], fl[3], fl[2]) + [[A[2], fl[2], fr[3]], [A[2], fr[3], fr[2]]]      # back (y = d)
    tris += q(A[3], A[0], fl[0], fl[3]) + q(A[1], A[2], fr[2], fr[1])                       # left, right
    return tris


def cylinder(r, h, n):
    tris = []
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * ((k + 1) % n) / n      # the seam closes on the same floats
        p0, p1 = (r * math.cos(a0), r * math.sin(a0)), (r * math.cos(a1), r * math.sin(a1))
        tris += [[(*p0, 0.0), (*p1, 0.0), (*p1, h)], [(*p0, 0.0), (*p1, h), (*p0, h)]]
        tris += [[(0.0, 0.0, h), (*p0, h), (*p1, h)], [(0.0, 0.0, 0.0), (*p1, 0.0), (*p0, 0.0)]]
    return tris


def sphere(r, nu, nv):
    def p(i, j):
        if j == 0:
            return (0.0, 0.0, 2 * r)                     # the poles written once, so they are shared
        if j == nv:
            return (0.0, 0.0, 0.0)
        th, ph = 2 * math.pi * (i % nu) / nu, math.pi * j / nv
        return (r * math.sin(ph) * math.cos(th), r * math.sin(ph) * math.sin(th), r + r * math.cos(ph))
    tris = []
    for i in range(nu):
        for j in range(nv):
            a, b, c, e = p(i, j), p(i + 1, j), p(i + 1, j + 1), p(i, j + 1)
            if j < nv - 1:                       # (a, e, c): degenerate only at the bottom pole
                tris.append([a, e, c])
            if j > 0:                            # (b, a, c): degenerate only at the top pole
                tris.append([b, a, c])
    return tris


def run(src, out, *extra):
    rep = out + ".json"
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", TOOL, "--",
                        src, "--out", out, "--json", rep, *extra], capture_output=True, text=True)
    data = json.load(open(rep)) if os.path.exists(rep) else None
    return r.returncode, data, r.stdout + r.stderr


def moved(a, b):
    """Largest distance between the same vertex before and after (triangles keep their order)."""
    return max(math.dist(p, q) for ta, tb in zip(a, b) for p, q in zip(ta, tb))


checks = []


def check(name, ok, got):
    checks.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {name}  ({got})")


with tempfile.TemporaryDirectory() as d:
    random.seed(7)
    jit = {}
    def jitter(amp):
        def f(x, y):
            k = (round(x, 6), round(y, 6), amp)
            if k not in jit:
                jit[k] = random.uniform(-amp, amp)
            return jit[k]
        return f

    # 1. a top jittered by 0.15 mm, tolerance 0.3: flat, nothing past the tolerance, sides kept
    src = grid_box(40, 40, 20, 8, top=jitter(0.15))
    stl(f"{d}/jit.stl", src)
    rc, r, log = run(f"{d}/jit.stl", f"{d}/jit_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/jit_out.stl") if rc in (0, 3) else []
    tops = [p[2] for t in out for p in t if p[2] > 10]
    check("jittered top: exit 0", rc == 0, (rc, log[-300:] if rc else ""))
    check("jittered top: one height, to 1 micron", bool(tops) and max(tops) - min(tops) < 1e-3,
          round(max(tops) - min(tops), 6) if tops else None)
    check("jittered top: no vertex moved past the tolerance", bool(out) and moved(src, out) <= 0.3 + 1e-4,
          round(moved(src, out), 4) if out else None)
    bottoms = [p[2] for t in out for p in t if p[2] < 10]
    check("jittered top: the bottom did not move", bool(bottoms) and max(abs(z) for z in bottoms) < 1e-4,
          max(abs(z) for z in bottoms) if bottoms else None)
    check("jittered top: still closed (report)", r is not None and r["after"]["open_edges"] == 0
          and r["after"]["nonmanifold_edges"] == 0, r and r.get("after"))

    # 2. the same top jittered by 1 mm, tolerance 0.3: left alone, said so
    src = grid_box(40, 40, 20, 8, top=jitter(1.0))
    stl(f"{d}/rough.stl", src)
    rc, r, log = run(f"{d}/rough.stl", f"{d}/rough_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/rough_out.stl") if rc in (0, 3) else []
    check("1 mm jitter past a 0.3 mm tolerance: nothing moves", bool(out) and moved(src, out) < 1e-4,
          round(moved(src, out), 4) if out else (rc, log[-200:]))
    check("1 mm jitter: reported as past the tolerance", r is not None and r["regions_past_tolerance"] >= 1,
          r and r.get("regions_past_tolerance"))

    # 3. curves are never flattened
    for name, tris in (("cylinder", cylinder(20, 30, 96)), ("sphere", sphere(20, 64, 32))):
        stl(f"{d}/{name}.stl", tris)
        rc, r, log = run(f"{d}/{name}.stl", f"{d}/{name}_out.stl", "--tol-mm", "0.3")
        out = read(f"{d}/{name}_out.stl") if rc in (0, 3) else []
        check(f"{name}: nothing moves", bool(out) and moved(tris, out) < 1e-4,
              round(moved(tris, out), 5) if out else (rc, log[-200:]))

    # 4. a shallow dome, 0.2 mm over 40 mm: inside the tolerance, curved on purpose — kept
    dome = lambda x, y: 0.2 * (1 - ((x - 20) ** 2 + (y - 20) ** 2) / 800)
    src = grid_box(40, 40, 20, 16, top=dome)
    stl(f"{d}/dome.stl", src)
    rc, r, log = run(f"{d}/dome.stl", f"{d}/dome_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/dome_out.stl") if rc in (0, 3) else []
    check("shallow dome: kept", bool(out) and moved(src, out) < 1e-4, round(moved(src, out), 4) if out else (rc, log[-200:]))
    check("shallow dome: reported as curved", r is not None and r["regions_curved"] >= 1, r and r.get("regions_curved"))

    # 4a. a smooth wave, dense: a shape, not noise — kept
    wave = lambda x, y: 0.15 * math.sin(2 * math.pi * x / 20) * math.sin(2 * math.pi * y / 20)
    src = grid_box(40, 40, 20, 16, top=wave)
    stl(f"{d}/wave.stl", src)
    rc, r, log = run(f"{d}/wave.stl", f"{d}/wave_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/wave_out.stl") if rc in (0, 3) else []
    check("smooth 0.15 mm wave, dense: nothing moves", bool(out) and moved(src, out) < 1e-4,
          round(moved(src, out), 4) if out else (rc, log[-200:]))

    # 4c. a coarse top with one corner raised 0.2 mm: modelled warped — flattened
    src = grid_box(40, 40, 20, 1, top=lambda x, y: 0.2 if (x > 39 and y > 39) else 0.0)
    stl(f"{d}/warp.stl", src)
    rc, r, log = run(f"{d}/warp.stl", f"{d}/warp_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/warp_out.stl") if rc in (0, 3) else []
    tops = [p[2] for t in out for p in t if p[2] > 10]
    check("coarse top, one corner raised 0.2 mm: flat", bool(tops) and max(tops) - min(tops) < 1e-3,
          round(max(tops) - min(tops), 4) if tops else (rc, log[-200:]))

    # 4b. a deliberate 5 degree slope, jittered: flattened on its slope, not snapped level
    slope = math.tan(math.radians(5))
    src = grid_box(40, 40, 20, 8, top=lambda x, y, j=jitter(0.1): x * slope + j(x, y))
    stl(f"{d}/slope.stl", src)
    rc, r, log = run(f"{d}/slope.stl", f"{d}/slope_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/slope_out.stl") if rc in (0, 3) else []
    top = [p for t in out for p in t if p[2] > 10]
    resid = max(abs(p[2] - 20 - p[0] * slope) for p in top) if top else None
    check("5 degree slope: flat and still at 5 degrees (within 0.1 mm of the slope)", resid is not None and resid < 0.1,
          round(resid, 4) if resid is not None else (rc, log[-200:]))

    # 5. a bottom tilted 1.5 degrees, --bed: flat on Z = 0, the tilt reported
    tilt = math.tan(math.radians(1.5))
    src = grid_box(40, 40, 20, 4, bottom=lambda x, y: x * tilt)
    stl(f"{d}/tilt.stl", src)
    rc, r, log = run(f"{d}/tilt.stl", f"{d}/tilt_out.stl", "--tol-mm", "0.3", "--bed")
    out = read(f"{d}/tilt_out.stl") if rc in (0, 3) else []
    zmin = min(p[2] for t in out for p in t) if out else None
    low = [p for t in out for p in t if p[2] < zmin + 0.5] if out else []
    check("tilted bottom, --bed: lowest point at Z = 0", zmin is not None and abs(zmin) < 1e-4, zmin)
    check("tilted bottom, --bed: the bottom flat on the bed", bool(low) and max(p[2] for p in low) < 1e-3,
          max(p[2] for p in low) if low else (rc, log[-200:]))
    check("tilted bottom, --bed: tilt reported near 1.5 degrees", r is not None and abs(r["bed_rotation_deg"] - 1.5) < 0.1,
          r and r.get("bed_rotation_deg"))

    # 5b. a 0.2 mm step between two planks: relief under the tolerance, kept
    src = step_box(40, 40, 20, 0.2)
    stl(f"{d}/step.stl", src)
    rc, r, log = run(f"{d}/step.stl", f"{d}/step_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/step_out.stl") if rc in (0, 3) else []
    check("0.2 mm step between planks: kept", bool(out) and moved(src, out) < 1e-4,
          round(moved(src, out), 4) if out else (rc, log[-200:]))

    # 5c. a 0.2 mm bevel at 20 degrees: a chamfer, kept
    src = step_box(40, 40, 20, 0.2, run=0.2 / math.tan(math.radians(20)))
    stl(f"{d}/bevel.stl", src)
    rc, r, log = run(f"{d}/bevel.stl", f"{d}/bevel_out.stl", "--tol-mm", "0.3")
    out = read(f"{d}/bevel_out.stl") if rc in (0, 3) else []
    check("0.2 mm bevel at 20 degrees: kept", bool(out) and moved(src, out) < 1e-4,
          round(moved(src, out), 4) if out else (rc, log[-200:]))

    # 5d. the whole box tilted, top jittered, --bed: level first, then flat
    a = math.radians(1.0); ca, sa = math.cos(a), math.sin(a)
    rot = {}
    def R(p):
        if p not in rot:
            rot[p] = (30 + (p[0] - 30) * ca + (p[2] - 12.5) * sa, p[1], 12.5 - (p[0] - 30) * sa + (p[2] - 12.5) * ca)
        return rot[p]
    src = [[R(p) for p in t] for t in grid_box(60, 40, 25, 12, top=jitter(0.15))]
    stl(f"{d}/tilted.stl", src)
    rc, r, log = run(f"{d}/tilted.stl", f"{d}/tilted_out.stl", "--tol-mm", "0.3", "--bed")
    out = read(f"{d}/tilted_out.stl") if rc in (0, 3) else []
    tops = [p[2] for t in out for p in t if p[2] > 12]
    check("tilted box, --bed: top at one height (to 1 micron)", bool(tops) and max(tops) - min(tops) < 1e-3,
          round(max(tops) - min(tops), 4) if tops else (rc, log[-200:]))
    check("tilted box, --bed: nothing held", r is not None and r["vertices_held"] == 0, r and r.get("vertices_held"))

    # 6. never over the input
    before = open(f"{d}/jit.stl", "rb").read()
    rc, r, log = run(f"{d}/jit.stl", f"{d}/jit.stl")
    check("output = input: refused, exit 1, input untouched", rc == 1 and open(f"{d}/jit.stl", "rb").read() == before,
          (rc, log.strip().splitlines()[-1:] if log else ""))

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
