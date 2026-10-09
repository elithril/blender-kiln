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
- slivers (parts under 1e-3 mm3) neither hold a part they cross nor lower the bed;
- a reference with no volume is a FAIL with no NaN; an open reference's volume is not compared;
- --height-mm 0 or negative, or a flat model to scale: exit 1, no Python trace;
- a dense cone held by its apex alone, 0.2 mm off the cube: not floating (no sampling);
- binary STL with a "solid" header and a count of 0, or trailing bytes; ASCII STL;
- a slicer that is not executable, or hangs past --slicer-timeout: exit 1, no Python trace;
- with PrusaSlicer: the closed cube is manifold, the open one is not; found by name on the PATH.
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


def stl(path, tris, header=b"test_print_check", count=None, trailing=b""):
    with open(path, "wb") as f:
        f.write(header.ljust(80, b" ")); f.write(struct.pack("<I", len(tris) if count is None else count))
        for t in tris:
            f.write(struct.pack("<3f", 0, 0, 0))
            for p in t:
                f.write(struct.pack("<3f", *p))
            f.write(b"\0\0")
        f.write(trailing)


def ascii_stl(path, tris):
    with open(path, "w") as f:
        f.write("solid test\n")
        for t in tris:
            f.write("  facet normal 0 0 0\n    outer loop\n")
            for p in t:
                f.write(f"      vertex {p[0]} {p[1]} {p[2]}\n")
            f.write("    endloop\n  endfacet\n")
        f.write("endsolid test\n")


def cone(apex, length, radius, rings, segments, gap_to_first_ring):
    """A closed cone along +x, apex first; its first ring starts `gap_to_first_ring` behind the
    apex so that the apex is the only vertex near whatever it points at. Dense on purpose."""
    import math
    ax, ay, az = apex
    xs = [ax + gap_to_first_ring + (length - gap_to_first_ring) * k / (rings - 1) for k in range(rings)]
    ring = [[(x, ay + radius * (x - ax) / length * math.cos(2 * math.pi * j / segments),
              az + radius * (x - ax) / length * math.sin(2 * math.pi * j / segments)) for j in range(segments)]
            for x in xs]
    base = (ax + length, ay, az)
    tris = []
    for j in range(segments):
        k = (j + 1) % segments
        tris.append([apex, ring[0][k], ring[0][j]])
        for r in range(rings - 1):
            tris += [[ring[r][j], ring[r][k], ring[r + 1][k]], [ring[r][j], ring[r + 1][k], ring[r + 1][j]]]
        tris.append([base, ring[-1][j], ring[-1][k]])
    # outward winding: flip everything if the signed volume came out negative
    v6 = sum(a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
             for a, b, c in tris)
    return tris if v6 > 0 else [t[::-1] for t in tris]


def run(model, *extra, env=None):
    r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", TOOL, "--", model, *extra], capture_output=True, text=True, env=env)
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

    # ── what a code review found: each case failed before its fix ──────────────────────────
    # a sliver (5.7e-4 mm3, under EMPTY_MM3) crossing a cube that hangs 10 mm over another:
    # the sliver holds nothing, the hanging cube still floats
    stl(f"{d}/sliver_touch.stl", box(0, 0, 0, 20, 20, 20) + box(5, 5, 30, 15, 15, 40)
        + box(10, 10, 35, 25, 12, 35.00002))
    rc, r, _ = run(f"{d}/sliver_touch.stl", "--process", "fdm")
    check("hanging cube crossing a sliver: still floating, FAIL",
          rc == 3 and r["floating_parts"] == 1 and r["empty_parts"] == 1, (rc, r["floating_parts"], r["empty_parts"]))

    # a flat sliver 1 mm under the cube does not lower the bed
    stl(f"{d}/sliver_under.stl", box(0, 0, 0, 20, 20, 20) + box(0, 0, -1, 5, 5, -0.99998))
    rc, r, _ = run(f"{d}/sliver_under.stl", "--process", "fdm")
    check("cube over a sliver 1 mm below: on the bed, no overhang, PASS",
          rc == 0 and r["floating_parts"] == 0 and r["overhang_area_pct"] == 0 and r["empty_parts"] == 1,
          (rc, r["floating_parts"], r["overhang_area_pct"]))

    # a reference with no volume — a closed, two-sided triangle: said, never a NaN
    tri = [(0, 0, 0), (20, 0, 0), (0, 20, 0)]
    stl(f"{d}/speck.stl", [tri, tri[::-1]])
    rc, r, p = run(f"{d}/cube.stl", "--process", "fdm", "--reference", f"{d}/speck.stl")
    line = next((l for l in p.stdout.splitlines() if l.startswith("PRINT_CHECK ")), "")
    check("reference with no volume: FAIL said so, no NaN in the JSON",
          rc == 3 and "NaN" not in line and r["reference"]["volume_ratio"] is None
          and any("no volume" in f for f in r["fails"]), (rc, r and r["reference"], r and r["fails"]))

    # an open reference voxelises to a shell: its volume is not compared
    stl(f"{d}/block_open.stl", box(0, 0, 0, 40, 20, 20, skip=(1,)))
    rc, r, _ = run(f"{d}/pillars.stl", "--process", "fdm", "--reference", f"{d}/block_open.stl")
    check("pillars vs an OPEN block: volume not compared, said so",
          r["reference"]["volume_compared"] is False and any("reference is open" in w for w in r["warnings"]),
          (rc, r["reference"], r["warnings"]))

    # --height-mm must be a height
    for h in ("-10", "0"):
        rc, r, p = run(f"{d}/cube.stl", "--process", "fdm", "--height-mm", h)
        check(f"--height-mm {h}: exit 1, no verdict, no traceback",
              rc == 1 and r is None and "Traceback" not in p.stderr and "height" in p.stderr, (rc, p.stderr[-200:]))
    stl(f"{d}/flat.stl", [[(0, 0, 0), (10, 0, 0), (10, 10, 0)], [(0, 0, 0), (10, 10, 0), (0, 10, 0)]])
    rc, r, p = run(f"{d}/flat.stl", "--process", "fdm", "--height-mm", "10")
    check("flat model with --height-mm: exit 1, said flat, no traceback",
          rc == 1 and "Traceback" not in p.stderr and "flat" in p.stderr, (rc, p.stderr[-200:]))

    # a dense raised cone whose apex alone comes 0.2 mm from the cube's side: one vertex in
    # 20,002 holds it, and sampling 4,000 of them misses it
    stl(f"{d}/cone.stl", box(0, 0, 0, 20, 20, 20) + cone((20.2, 10, 15), 9.8, 5, 100, 200, 0.8))
    rc, r, _ = run(f"{d}/cone.stl", "--process", "fdm")
    check("cone held by its apex alone (0.2 mm off, FDM): not floating",
          r["floating_parts"] == 0 and r["parts"] == 2 and r["open_edges"] == 0 and r["inverted_parts"] == 0,
          (rc, r["parts"], r["open_edges"], r["floating_parts"], r["floating"]))

    # binary STL that only the exact size test rejected
    cube = box(0, 0, 0, 20, 20, 20)
    stl(f"{d}/solid_header.stl", cube, header=b"solid exported by a CAD tool", count=0)
    rc, r, p = run(f"{d}/solid_header.stl", "--process", "fdm")
    check("binary STL, header 'solid', count field 0: read, 12 triangles, PASS",
          rc == 0 and r["triangles"] == 12, (rc, r and r["triangles"], p.stderr[-200:]))
    stl(f"{d}/trailing.stl", cube, trailing=b"\0" * 7)
    rc, r, p = run(f"{d}/trailing.stl", "--process", "fdm")
    check("binary STL with 7 trailing bytes: read, PASS", rc == 0 and r["triangles"] == 12, (rc, p.stderr[-200:]))
    ascii_stl(f"{d}/ascii.stl", cube)
    rc, r, _ = run(f"{d}/ascii.stl", "--process", "fdm")
    check("ASCII STL cube: PASS, 12 triangles", rc == 0 and r["triangles"] == 12, (rc, r and r["triangles"]))

    # a slicer that cannot run, or never answers: an error, not a Python trace
    fake = f"{d}/not_executable_slicer"
    open(fake, "w").write("#!/bin/sh\n")
    rc, r, p = run(f"{d}/cube.stl", "--process", "fdm", "--slicer", fake)
    check("slicer not executable: exit 1, no traceback",
          rc == 1 and "Traceback" not in p.stderr and "slicer" in p.stderr, (rc, p.stderr[-300:]))
    slow = f"{d}/slow_slicer"
    open(slow, "w").write("#!/bin/sh\nsleep 30\n"); os.chmod(slow, 0o755)
    rc, r, p = run(f"{d}/cube.stl", "--process", "fdm", "--slicer", slow, "--slicer-timeout", "2")
    check("slicer that hangs, --slicer-timeout 2: exit 1, 'timed out', no traceback",
          rc == 1 and "Traceback" not in p.stderr and "timed out" in p.stderr, (rc, p.stderr[-300:]))

    # --supports: the slice is asked with automatic supports, and the verdict says so. A fake PrusaSlicer
    # reports a floating part unless --support-material is on its command line (on the real one, the
    # black cat of the ghost figurine: Floating object part without, a clean slice with, 2026-10-09)
    fake = f"{d}/fake_prusaslicer"
    open(fake, "w").write("""#!/bin/sh
case " $* " in
  *" --info "*) echo "manifold = yes"; echo "number_of_parts =  1"; exit 0 ;;
esac
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
[ -n "$out" ] && : > "$out"
case " $* " in
  *" --support-material "*) exit 0 ;;
  *) printf 'print warning: Detected print stability issues:\n\nmodel\nFloating object part, Collapsing overhang\n'; exit 0 ;;
esac
"""); os.chmod(fake, 0o755)
    rc, r, p = run(f"{d}/cube.stl", "--process", "fdm", "--slicer", fake)
    check("slicer reports a floating part, no --supports: FAIL",
          rc == 3 and r["slicer"]["floating_count"] == 1 and not r["slicer"]["supports"], (rc, p.stderr[-200:]))
    rc, r, p = run(f"{d}/cube.stl", "--process", "fdm", "--slicer", fake, "--supports")
    check("same with --supports: sliced with supports, PASS, said in the warnings",
          rc == 0 and r["slicer"]["floating_count"] == 0 and r["slicer"]["supports"]
          and any("--supports" in w for w in r["warnings"]), (rc, r and r["warnings"], p.stderr[-200:]))

    if os.path.exists(SLICER):
        # by name, from the PATH, like any command
        bindir = f"{d}/bin"; os.makedirs(bindir)
        os.symlink(SLICER, f"{bindir}/prusa-slicer-on-path")
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""))
        rc, r, p = run(f"{d}/cube.stl", "--process", "fdm", "--slicer", "prusa-slicer-on-path", env=env)
        check("slicer named on the PATH: found, manifold, PASS",
              rc == 0 and r and r["slicer"]["manifold"] == "yes", (rc, p.stderr[-200:]))

        rc, r, _ = run(f"{d}/cube.stl", "--process", "fdm", "--slicer", SLICER)
        check("slicer, closed cube: manifold, 1 part, sliced, PASS",
              rc == 0 and r["slicer"]["manifold"] == "yes" and r["slicer"]["number_of_parts"] == 1 and r["slicer"]["gcode"],
              r["slicer"])
        # binary STLs with all-zero normals: PrusaSlicer 2.9.6 refused to load a 10 x 10 x 40 box written
        # that way ("Loading of a model file failed"); print_check now writes the facet normals itself
        stl(f"{d}/post.stl", box(0, 0, 0, 10, 10, 40))
        rc, r, p = run(f"{d}/post.stl", "--process", "fdm", "--slicer", SLICER)
        check("slicer, 10 x 10 x 40 post (zero normals in the input): loaded, manifold, PASS",
              rc == 0 and r["slicer"]["manifold"] == "yes", (rc, r and r["slicer"], p.stderr[-200:]))
        rc, r, _ = run(f"{d}/open.stl", "--process", "fdm", "--slicer", SLICER)
        check("slicer, open cube: manifold = no", rc == 3 and r["slicer"]["manifold"] == "no", r["slicer"]["manifold"])
    else:
        print(f"SKIP  slicer cases: no PrusaSlicer at {SLICER}")

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
