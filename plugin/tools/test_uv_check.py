#!/usr/bin/env python3
"""Check uv_check.py finds what it says, and stays quiet on clean UVs.

    python3 tools/test_uv_check.py      # needs Blender at $BLENDER or the macOS default

- a sphere unwrapped by Smart UV Project, with an image texture, as .blend and as GLB: ok,
  no WARN — a check that fires on correct UVs is worse than none;
- no UV map and a plain material: ok, said; no UV map and an image texture: FAIL, exit 1;
- every face's UVs stacked on one square: overlap WARN;
- a fifth of the faces collapsed to a point: FAIL, exit 1;
- the upper half's UVs three times wider: stretch WARN;
- the right half's UVs mirrored: flipped WARN;
- a missing file: exit 1, no traceback.
"""
import json, os, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uv_check.py")

MAKE = """
import bpy, sys
out, kind = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
if kind.startswith("nouv"):
    bpy.ops.mesh.primitive_cube_add(size=0.2)
    o = bpy.context.object
    while o.data.uv_layers:
        o.data.uv_layers.remove(o.data.uv_layers[0])
else:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.1)
    o = bpy.context.object
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.152, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
me = o.data
m = bpy.data.materials.new("M"); m.use_nodes = True
if kind in ("good", "stacked", "collapsed", "stretched", "flipped", "nouv_tex"):
    img = bpy.data.images.new("T", 8, 8)
    tex = m.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
me.materials.append(m)
if me.uv_layers:
    uv = me.uv_layers.active.data
    for p in me.polygons:
        c = p.center
        for k, li in enumerate(p.loop_indices):
            u, v = uv[li].uv
            if kind == "stacked":
                uv[li].uv = ((0.1, 0.1), (0.9, 0.1), (0.5, 0.9))[k % 3]
            elif kind == "collapsed" and p.index % 5 == 0:
                uv[li].uv = (0.5, 0.5)
            elif kind == "stretched" and c.z > 0:
                uv[li].uv = (0.5 + (u - 0.5) * 3, v)
            elif kind == "flipped" and c.x > 0:
                uv[li].uv = (1 - u, v)
if out.endswith(".glb"):
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB")
else:
    bpy.data.images["T"].pack() if "T" in bpy.data.images else None
    bpy.ops.wm.save_as_mainfile(filepath=out)
"""


def make(d, kind, ext=".blend"):
    open(f"{d}/make.py", "w").write(MAKE)
    out = f"{d}/{kind}{ext}"
    subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", f"{d}/make.py",
                    "--", out, kind], capture_output=True, text=True)
    return out


def run(*extra):
    p = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", TOOL, "--", *extra],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


checks = []
def check(name, ok, got=""):
    checks.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"   got: {got}"))


def report(d, path):
    rc, log = run(path, "--json", f"{d}/r.json")
    try:
        r = json.load(open(f"{d}/r.json"))[0]
    except (OSError, ValueError, IndexError):
        r = {}
    return rc, log, r


with tempfile.TemporaryDirectory() as d:
    for ext in (".blend", ".glb"):
        rc, log, r = report(d, make(d, "good", ext))
        check(f"Smart UV Project sphere ({ext}): ok, no WARN", rc == 0 and r.get("status") == "ok", (rc, r, log[-300:]))
    rc, log, r = report(d, make(d, "nouv_plain"))
    check("no UV, plain material: ok, said", rc == 0 and r.get("status") == "ok" and r.get("uv") is None, (rc, r))
    rc, log, r = report(d, make(d, "nouv_tex"))
    check("no UV, image texture: FAIL, exit 1", rc == 1 and r.get("status") == "FAIL", (rc, r, log[-300:]))
    rc, log, r = report(d, make(d, "stacked"))
    check("UVs stacked on one square: overlap WARN", rc == 0 and r.get("status") == "WARN" and r.get("overlap", 0) > 0.5,
          (rc, r))
    rc, log, r = report(d, make(d, "collapsed"))
    check("a fifth of the faces collapsed: FAIL, exit 1", rc == 1 and r.get("collapsed", 0) > 0.1, (rc, r))
    rc, log, r = report(d, make(d, "stretched"))
    check("upper half three times wider: stretch WARN", rc == 0 and r.get("stretch", 0) > 0.3 and r.get("status") == "WARN",
          (rc, r))
    rc, log, r = report(d, make(d, "flipped"))
    check("right half mirrored: flipped WARN", rc == 0 and r.get("flipped", 0) > 0.3 and r.get("status") == "WARN", (rc, r))
    rc, log = run(f"{d}/none.glb")
    check("missing file: exit 1, no traceback", rc == 1 and "no such file" in log and "Traceback" not in log, (rc, log[-200:]))

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
