#!/usr/bin/env python3
"""Seed what print_check.py claims to find, and check it does.

    python3 tools/test_print_check.py      # needs Blender at $BLENDER or the macOS default;
                                           # PrusaSlicer at $PRUSASLICER for the slicer cases

Known meshes, known answers, written as STL by this script — no Blender needed to build
them, no network. Cases:

- a closed 20 mm cube: PASS, exit 0, one closed part, nothing to report;
- the same cube with its top missing: FAIL, exit 3, 4 open edges;
- two cubes crossing each other: the crossing is reported, both held, PASS; with --parts 1, FAIL;
- a cube and a second one hanging 10 mm above it: FAIL, one floating part;
- a raised cube 0.2 mm beside another: held in FDM (an extrusion bridges it), floating in
  resin; 1 mm beside: floating in FDM too, with its gap reported;
- a hollow cube (inner shell reversed): the cavity is enclosed, not inverted — PASS;
- the closed cube with every normal reversed: FAIL, inverted;
- a 0.4 mm wall: most faces under the FDM minimum, none for the 20 mm cube;
- overhang: the raised cube's underside is reported, a cube's bottom on the bed is not;
- --reference: the crossing cubes against themselves, no loss; one of them alone against
  both — the MANIFOLD union that dropped half the object — FAIL; two end pillars against
  the full block: same bounding box, a quarter of the volume — FAIL on volume alone;
- --height-mm scales: the cube read at 50 mm is 50 mm;
- a missing file: exit 1;
- with PrusaSlicer: the closed cube is manifold, the open one is not.
"""
import json, os, struct, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
SLICER = os.environ.get("PRUSASLICER", "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "print_check.py")

QUADS = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]   # outward


def box(x0, y0, z0, x1, y1, z1, skip=(), flip=False):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    tris = []
    for k, (a, b, c, d) in enumerate(QUADS):
        if k in skip:
            continue
        for t in ((a, b, c), (a, c, d)):
            tris.append([v[i] for i in (t[::-1] if flip else t)])
    return tris


def stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"test_print_check".ljust(80, b" ")); f.write(struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<3f", 0, 0, 0))
            for p in t:
                f.write(struct.pack("<3f", *p))
            f.write(b"\0\0")


def run(model, *extra):
    r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", TOOL, "--", model, *extra], capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines() if l.startswith("PRINT_CHECK ")), None)
    return r.returncode, (json.loads(line[len("PRINT_CHECK "):]) if line else None), r


with tempfile.TemporaryDirectory() as d:
    stl(f"{d}/cube.stl", box(0, 0, 0, 20, 20, 20))
    stl(f"{d}/open.stl", box(0, 0, 0, 20, 20, 20, skip=(1,)))
    stl(f"{d}/crossing.stl", box(0, 0, 0, 20, 20, 20) + box(10, 10, 5, 30, 30, 25))
    stl(f"{d}/floating.stl", box(0, 0, 0, 20, 20, 20) + box(5, 5, 30, 15, 15, 40))
    stl(f"{d}/beside.stl", box(0, 0, 0, 20, 20, 20) + box(20.2, 0, 5, 30, 20, 25))   # 0.2 mm off the side
    stl(f"{d}/apart.stl", box(0, 0, 0, 20, 20, 20) + box(21, 0, 5, 30, 20, 25))      # 1 mm off
    stl(f"{d}/hollow.stl", box(0, 0, 0, 20, 20, 20) + box(5, 5, 5, 15, 15, 15, flip=True))
    stl(f"{d}/inverted.stl", box(0, 0, 0, 20, 20, 20, flip=True))
    stl(f"{d}/wall.stl", box(0, 0, 0, 20, 0.4, 20))
    stl(f"{d}/half.stl", box(0, 0, 0, 20, 20, 20))
    stl(f"{d}/block.stl", box(0, 0, 0, 40, 20, 20))
    stl(f"{d}/pillars.stl", box(0, 0, 0, 5, 20, 20) + box(35, 0, 0, 40, 20, 20))   # same box, 1/4 of it
    checks = []

    def check(name, ok, got):
        checks.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {name}  ({got})")

    rc, r, _ = run(f"{d}/cube.stl", "--process", "fdm")
    check("closed cube: PASS, exit 0", rc == 0 and r["verdict"] == "PASS", (rc, r and r["fails"]))
    check("closed cube: 1 closed part, 0 open, 0 non-manifold, consistent",
          (r["parts"], r["closed_parts"], r["open_edges"], r["nonmanifold_edges"], r["inconsistent_edges"],
           r["nonmanifold_vertices"]) == (1, 1, 0, 0, 0, 0), (r["parts"], r["open_edges"]))
    check("closed cube: volume 8000 mm3, no thin wall, no overhang",
          abs(r["volume_mm3"] - 8000) < 1e-3 and r["thickness"]["faces_thin_pct"] == 0 and r["overhang_area_pct"] == 0,
          (r["volume_mm3"], r["thickness"]["faces_thin_pct"], r["overhang_area_pct"]))

    rc, r, _ = run(f"{d}/open.stl", "--process", "fdm")
    check("open cube: FAIL, exit 3, 4 open edges", rc == 3 and r["open_edges"] == 4 and r["closed_parts"] == 0,
          (rc, r["open_edges"]))

    rc, r, _ = run(f"{d}/crossing.stl", "--process", "fdm")
    check("crossing cubes: 2 parts, crossing reported, none floating",
          r["parts"] == 2 and r["intersecting_part_pairs"] == 1 and r["floating_parts"] == 0
          and any("crossing" in w for w in r["warnings"]), (r["parts"], r["intersecting_part_pairs"], r["floating_parts"]))
    check("crossing cubes: PASS (a slicer merges them)", rc == 0, (rc, r["fails"]))
    rc, r, _ = run(f"{d}/crossing.stl", "--process", "fdm", "--parts", "1")
    check("crossing cubes with --parts 1: FAIL", rc == 3 and any("expected 1" in f for f in r["fails"]), rc)

    rc, r, _ = run(f"{d}/floating.stl", "--process", "fdm")
    check("cube + hanging cube: FAIL, 1 floating part", rc == 3 and r["floating_parts"] == 1, (rc, r["floating_parts"]))

    rc, r, _ = run(f"{d}/beside.stl", "--process", "fdm")
    check("raised cube 0.2 mm beside the other, FDM: fused by the extrusion, held", rc == 0 and r["floating_parts"] == 0,
          (rc, r["floating_parts"]))
    rc, r, _ = run(f"{d}/beside.stl", "--process", "resin")
    check("the same in resin: floating", rc == 3 and r["floating_parts"] == 1, (rc, r["floating_parts"]))
    rc, r, _ = run(f"{d}/apart.stl", "--process", "fdm")
    check("raised cube 1 mm beside, FDM: floating, gap reported",
          rc == 3 and r["floating_parts"] == 1 and abs(r["floating"][0]["gap_to_other_part_mm"] - 1) < 1e-3,
          (rc, r["floating"]))

    rc, r, _ = run(f"{d}/hollow.stl", "--process", "resin")
    check("hollow cube: a cavity, not inverted, PASS",
          rc == 0 and r["cavities"] == 1 and r["inverted_parts"] == 0 and abs(r["volume_mm3"] - 7000) < 1e-3,
          (rc, r["cavities"], r["inverted_parts"], r["volume_mm3"]))

    rc, r, _ = run(f"{d}/inverted.stl", "--process", "fdm")
    check("reversed cube: FAIL, inverted", rc == 3 and r["inverted_parts"] == 1, (rc, r["inverted_parts"]))

    rc, r, _ = run(f"{d}/wall.stl", "--process", "fdm")
    check("0.4 mm wall, FDM: most faces under 0.8 mm", r["thickness"]["area_thin_pct"] > 90,
          r["thickness"])
    rc, r, _ = run(f"{d}/wall.stl", "--process", "resin")
    check("0.4 mm wall, resin: still under 0.5 mm", r["thickness"]["area_thin_pct"] > 90, r["thickness"]["area_thin_pct"])

    rc, r, _ = run(f"{d}/crossing.stl", "--process", "fdm")
    # the upper cube's 20 x 20 underside, 5 mm above the bed, over 2 x 2400 mm2 of surface;
    # the lower cube's underside is on the bed and does not count
    check("crossing cubes: the raised underside overhangs, the bed does not",
          abs(r["overhang_area_pct"] - 100 * 400 / 4800) < 0.01, (r["overhang_area_pct"], round(100 * 400 / 4800, 2)))

    rc, r, _ = run(f"{d}/crossing.stl", "--process", "fdm", "--reference", f"{d}/crossing.stl")
    check("reference = itself: no loss, ratio 1", rc == 0 and abs(r["reference"]["volume_ratio"] - 1) < 1e-6,
          r["reference"]["volume_ratio"])
    rc, r, _ = run(f"{d}/half.stl", "--process", "fdm", "--reference", f"{d}/crossing.stl")
    check("one cube vs the two: closed and manifold, yet FAIL for the loss",
          rc == 3 and r["open_edges"] == 0 and any("lost material" in f or "dimensions differ" in f for f in r["fails"]),
          (rc, r["reference"]["dims_diff_pct"], r["reference"]["volume_ratio"]))

    rc, r, _ = run(f"{d}/pillars.stl", "--process", "fdm", "--reference", f"{d}/block.stl")
    check("two end pillars vs the block: same dimensions, FAIL on volume",
          rc == 3 and r["reference"]["dims_diff_pct"] == [0.0, 0.0, 0.0] and any("lost material" in f for f in r["fails"]),
          (rc, r["reference"]["volume_ratio"]))

    rc, r, _ = run(f"{d}/cube.stl", "--process", "fdm", "--height-mm", "50")
    check("--height-mm 50: 50 mm on every side", r["dims_mm"] == [50.0, 50.0, 50.0], r["dims_mm"])

    rc, r, p = run(f"{d}/nothing.stl", "--process", "fdm")
    check("missing file: exit 1, no verdict", rc == 1 and r is None, rc)
    rc, r, p = run(f"{d}/cube.stl")
    check("missing --process: exit 1", rc == 1 and r is None, rc)

    if os.path.exists(SLICER):
        rc, r, _ = run(f"{d}/cube.stl", "--process", "fdm", "--slicer", SLICER)
        check("slicer, closed cube: manifold, 1 part, sliced, PASS",
              rc == 0 and r["slicer"]["manifold"] == "yes" and r["slicer"]["number_of_parts"] == 1 and r["slicer"]["gcode"],
              r["slicer"])
        rc, r, _ = run(f"{d}/open.stl", "--process", "fdm", "--slicer", SLICER)
        check("slicer, open cube: manifold = no", rc == 3 and r["slicer"]["manifold"] == "no", r["slicer"]["manifold"])
    else:
        print(f"SKIP  slicer cases: no PrusaSlicer at {SLICER}")

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
