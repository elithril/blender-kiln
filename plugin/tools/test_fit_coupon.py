#!/usr/bin/env python3
"""Check fit_coupon.py writes what it says.

    python3 tools/test_fit_coupon.py      # needs Blender at $BLENDER or the macOS default

- the defaults: exit 0, two STLs, holes 4.2 / 4.4 / 4.6 mm and a fourth at 4.4 with a 0.5 mm
  lead-in (5.4 mm on the bed face), the peg 4.0 mm and 4.5 mm long — each read back from
  the STL, not from the tool's own report;
- both parts are one closed solid, the plate is --depth-mm thick and lies on Z = 0;
- other values (a 6 mm peg, one clearance, no chamfer): one hole, 6.3 mm, no lead-in;
- a negative clearance: refused, exit 1, nothing written;
- --shape round, an 8 mm peg 6 mm deep: holes 8.2 / 8.4 / 8.6 mm across the flats and 8.4
  with the lead-in (9.4 on the bed face), the peg standing on its base, 8.0 mm at its corners
  and 7 mm long — read back from the STLs.
"""
import json, math, os, struct, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fit_coupon.py")


def read(path):
    data = open(path, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    return [[struct.unpack("<3f", data[84 + 50 * k + 12 + 12 * i: 84 + 50 * k + 24 + 12 * i]) for i in range(3)]
            for k in range(n)]


def run(out, *extra):
    p = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", TOOL, "--",
                        "--out", out, "--json", f"{out}/r.json", *extra], capture_output=True, text=True)
    r = json.load(open(f"{out}/r.json")) if os.path.exists(f"{out}/r.json") else None
    return p.returncode, r, p.stdout + p.stderr


def closed(tris):
    """Every edge in exactly two triangles, walked once each way: one closed, coherent shell."""
    q = lambda p: tuple(round(c, 4) for c in p)
    half = {}
    for t in tris:
        for i in range(3):
            e = (q(t[i]), q(t[(i + 1) % 3]))
            half[e] = half.get(e, 0) + 1
    return all(v == 1 and half.get((b, a)) == 1 for (a, b), v in half.items())


def hole_side(tris, x, y, z, reach):
    """The diamond hole's side where a plane at height z cuts the plate, round centre (x, y)."""
    best = 0.0
    for t in tris:
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            if (a[2] - z) * (b[2] - z) < 0:
                s = (z - a[2]) / (b[2] - a[2])
                d = abs(a[0] + (b[0] - a[0]) * s - x) + abs(a[1] + (b[1] - a[1]) * s - y)
                if best < d < reach:
                    best = d
    return best * math.sqrt(2)


checks = []
def check(name, ok, got=""):
    checks.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"   got: {got}"))


with tempfile.TemporaryDirectory() as d:
    # 1. defaults
    rc, r, log = run(f"{d}/a")
    check("defaults: exit 0, a report", rc == 0 and r is not None, (rc, log[-300:]))
    plate = read(f"{d}/a/fit_holes.stl") if rc == 0 else []
    peg = read(f"{d}/a/fit_peg.stl") if rc == 0 else []
    check("plate: one closed shell", plate and closed(plate))
    check("peg: one closed shell", peg and closed(peg))
    zs = [p[2] for t in plate for p in t]
    check("plate: on Z = 0, 3.5 mm thick", zs and abs(min(zs)) < 1e-4 and abs(max(zs) - 3.5) < 1e-4,
          zs and (min(zs), max(zs)))
    if r:
        want = [(4.2, 4.2), (4.4, 4.4), (4.6, 4.6), (4.4, 5.4)]
        for i, (mid, bed) in enumerate(want):
            x, y = r["holes"][i]["centre_mm"]                     # where it is from the report, its size from the STL
            m, b = hole_side(plate, x, y, 1.75, 6), hole_side(plate, x, y, 0.001, 6)
            check(f"hole {i + 1}: {mid} mm through, {bed} mm on the bed face", abs(m - mid) < 2e-3 and abs(b - bed) < 5e-3,
                  (round(m, 4), round(b, 4)))
    tip = [p for t in peg for p in t if p[1] < -1e-4]
    if tip:
        side = (max(p[2] for p in tip) - min(p[2] for p in tip)) / math.sqrt(2)
        check("peg: 4.0 mm, 4.5 mm long, its lower corner above the bed",
              abs(side - 4.0) < 1e-3 and abs(-min(p[1] for p in tip) - 4.5) < 1e-3 and min(p[2] for p in tip) > 1,
              (round(side, 4), min(p[1] for p in tip)))
    else:
        check("peg: sticks out", False)

    # 2. other values
    rc, r, log = run(f"{d}/b", "--peg-mm", "6", "--clear-mm", "0.15", "--chamfer-mm", "0")
    check("6 mm peg, one clearance, no chamfer: one hole of 6.3 mm",
          rc == 0 and len(r["holes"]) == 1 and r["holes"][0]["side_mm"] == 6.3
          and abs(r["holes"][0]["measured_bed_side_mm"] - 6.3) < 1e-3, (rc, r and r["holes"], log[-200:]))

    # 2b. round, standing up
    rc, r, log = run(f"{d}/r", "--shape", "round", "--peg-mm", "8", "--depth-mm", "6")
    check("round: exit 0, a report", rc == 0 and r is not None and r.get("shape") == "round", (rc, log[-300:]))
    if rc == 0:
        plate, peg = read(f"{d}/r/fit_holes.stl"), read(f"{d}/r/fit_peg.stl")
        check("round: plate and peg closed shells", closed(plate) and closed(peg))
        cos = math.cos(math.pi / 64)
        def across(tris, x, y, z):
            best = 0.0
            for t in tris:
                for i in range(3):
                    a, b = t[i], t[(i + 1) % 3]
                    if (a[2] - z) * (b[2] - z) < 0:
                        s_ = (z - a[2]) / (b[2] - a[2])
                        dd = math.hypot(a[0] + (b[0] - a[0]) * s_ - x, a[1] + (b[1] - a[1]) * s_ - y)
                        if best < dd < 6:
                            best = dd
            return 2 * best * cos
        for i, (mid, bed) in enumerate([(8.2, 8.2), (8.4, 8.4), (8.6, 8.6), (8.4, 9.4)]):
            x, y = r["holes"][i]["centre_mm"]
            m, b = across(plate, x, y, 3.0), across(plate, x, y, 0.001)
            check(f"round hole {i + 1}: {mid} mm across the flats, {bed} on the bed face",
                  abs(m - mid) < 2e-3 and abs(b - bed) < 1e-2, (round(m, 4), round(b, 4)))
        top = [p for t in peg for p in t if p[2] > 2.0 + 1e-4]
        dia = 2 * max(math.hypot(p[0], p[1]) for p in top)
        check("round peg: 8.0 mm at its corners, 7 mm above its 2 mm base",
              abs(dia - 8.0) < 2e-3 and abs(max(p[2] for p in top) - 9.0) < 1e-3, (round(dia, 4), max(p[2] for p in top)))

    # 3. refused
    rc, r, log = run(f"{d}/c", "--clear-mm", "-0.1")
    check("negative clearance: exit 1, nothing written", rc == 1 and not os.path.exists(f"{d}/c/fit_holes.stl"),
          (rc, log[-200:]))

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
