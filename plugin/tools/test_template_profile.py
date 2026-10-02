#!/usr/bin/env python3
"""Seed what template_profile.py claims to read off a 3D template, and check it does.

    python3 tools/test_template_profile.py          # needs Blender at $BLENDER or the macOS default

A known turned part, built 1 m tall like a generated mesh, read back at 0.30 m:

- a cylinder of radius 0.10 m (0.030 at scale) under a cone: the turned radius per band;
- a rod standing 0.15 m from the axis (0.045): listed apart, a few sectors of coverage;
- a rod pressed against the cylinder: it joins the cylinder's group, and the turned radius
  must stay the cylinder's — the case where taking the group's max read a lantern's guard
  wire as its glass (5.65 cm for 3.9).
"""
import json, os, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template_profile.py")

BUILD = r'''
import bpy, sys
d = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.10, depth=0.5, location=(0, 0, 0.25))
bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.10, radius2=0.0, depth=0.5, location=(0, 0, 0.75))
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.006, depth=0.5, location=(0.15, 0, 0.25))
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.006, depth=0.5, location=(0, 0.104, 0.25))
bpy.ops.export_scene.gltf(filepath=f"{d}/part.glb", export_format="GLB")
'''

with tempfile.TemporaryDirectory() as d:
    open(f"{d}/build.py", "w").write(BUILD)
    subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", f"{d}/build.py", "--", d],
                   check=True, capture_output=True)
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", TOOL, "--",
                        "--template", f"{d}/part.glb", "--height", "0.30", "--bands", "10", "--json", f"{d}/p.json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"template_profile failed ({r.returncode}):\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    bands = json.load(open(f"{d}/p.json"))["bands"]
    checks = []

    def check(name, ok, got):
        checks.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {name}  ({got})")

    turned = lambda b: [q for q in b["parts"] if q["round"] >= 0.75]
    low = bands[2]                                         # z = 0.075 m: cylinder and both rods
    t = turned(low)
    check("cylinder: turned radius 0.030 m at scale", bool(t) and abs(t[-1]["r_turned"] - 0.030) < 0.001,
          round(t[-1]["r_turned"], 4) if t else None)
    rods = [q for q in low["parts"] if q["round"] < 0.75]
    check("free rod: apart, at 0.045 m, few sectors", any(abs((q["r_in"] + q["r_out"]) / 2 - 0.045) < 0.002
                                                          and q["round"] < 0.2 for q in rods),
          [(round(q["r_in"], 4), round(q["r_out"], 4), round(q["round"], 2)) for q in rods])
    check("pressed rod: joins the group, turned radius unchanged",
          bool(t) and t[-1]["r_out"] > 0.032 and abs(t[-1]["r_turned"] - 0.030) < 0.001,
          (round(t[-1]["r_out"], 4), round(t[-1]["r_turned"], 4)) if t else None)
    cone = turned(bands[7])                                # z = 0.225 m: cone at 0.55 of its height
    want = 0.030 * (1 - (0.225 - 0.15) / 0.15)
    check(f"cone: radius {want:.4f} m halfway up", bool(cone) and abs(cone[-1]["r_turned"] - want) < 0.0015,
          round(cone[-1]["r_turned"], 4) if cone else None)

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
