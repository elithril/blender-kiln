#!/usr/bin/env python3
"""Seed what fidelity_check.py claims to measure, and check it does.

    python3 tools/test_fidelity_check.py            # needs Blender at $BLENDER or the macOS default

Every session reviewing against a reference trusts this tool's numbers, so it gets
the same treatment as verify_docs.py: known inputs, known answers. No network — the
test writes its own tiny HDRI. Cases:

- a model measured against its own render: IoU near 1, no shape gap;
- the same model 20 % wider: the width gap is reported, and close to +20 %;
- a texture that is not loaded: refused, exit 1 — it would render black;
- a .blend: measured, with the warning that the shipped file is what counts;
- --max-tris: a guide, not a cap — under twice the limit listed last and kept, past it a
  reduction proposed; silent below;
- a metal with a dark base colour: reported — it renders as a black mirror (lantern v7);
  the same colour as non-metal, and a bright metal, silent;
- --view and --azimuth on a 2 x 1 x 1 box: 2:1 from the front, 1:1 from the side or at 90°,
  and 2.12:1 at 45° (2 cos 45° + sin 45°) — the 3/4 view most product photos are.
"""
import json, os, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fidelity_check.py")

BUILD = r'''
import bpy, sys, math
d = sys.argv[sys.argv.index("--") + 1]
def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
def vase(sx=1.0):
    fresh()
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.1, depth=0.3, location=(0, 0, 0.15))
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.1, radius2=0.03, depth=0.15, location=(0, 0, 0.375))
    for o in bpy.context.scene.objects:
        o.scale.x = sx
    m = bpy.data.materials.new("m"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.4, 0.2, 0.1, 1)
    for o in bpy.context.scene.objects:
        o.data.materials.append(m)
def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB")
# the HDRI: a small flat-grey Radiance file
img = bpy.data.images.new("env", 16, 8, float_buffer=True)
img.pixels = [0.8, 0.8, 0.8, 1.0] * (16 * 8)
img.filepath_raw = f"{d}/env.hdr"; img.file_format = "HDR"; img.save()
vase(1.0); export(f"{d}/vase.glb"); bpy.ops.wm.save_as_mainfile(filepath=f"{d}/vase.blend")
vase(1.2); export(f"{d}/vase_wide.glb")
# the reference: the vase's own silhouette, front, orthographic, alpha — as a photo would be
vase(1.0)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.scene.collection.objects.link(cam)
cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.46
cam.location = (0, -2, 0.225); cam.rotation_euler = (math.pi / 2, 0, 0); bpy.context.scene.camera = cam
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 512; sc.render.image_settings.color_mode = "RGBA"
sc.render.filepath = f"{d}/ref.png"; bpy.ops.render.render(write_still=True)
# a model whose texture points nowhere
fresh(); bpy.ops.mesh.primitive_cube_add(); o = bpy.context.object
m = bpy.data.materials.new("lost"); m.use_nodes = True
t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.new("lost", 8, 8)
t.image.source = "FILE"; t.image.filepath = "/nonexistent/lost.png"; o.data.materials.append(m)
bpy.ops.wm.save_as_mainfile(filepath=f"{d}/lost.blend")
# metals: a dark metal — textured, as a bake ships, through the GLB — must be reported; the
# same base colour as non-metal, and a bright metal, must not
def metal_vase(name, base, metallic):
    vase(1.0)
    m = bpy.data.materials["m"]; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    img = bpy.data.images.new(name, 8, 8); img.pixels = [*base, 1.0] * 64
    img.filepath_raw = f"{d}/{name}.png"; img.file_format = "PNG"; img.save()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = metallic
    export(f"{d}/{name}.glb")
metal_vase("dark_metal", (0.05, 0.04, 0.03), 1.0)
metal_vase("dark_paint", (0.05, 0.04, 0.03), 0.0)
metal_vase("bright_metal", (0.45, 0.35, 0.20), 1.0)
# a 2 x 1 x 1 box: 2 m along X, so front is 2:1 and left is 1:1
fresh(); bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5)); bpy.context.object.scale = (2, 1, 1)
bpy.ops.object.transform_apply(scale=True); export(f"{d}/box.glb")
'''


def blender(*a, check=True):
    r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1", *a],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"blender failed ({r.returncode}):\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


def measure(d, model, *extra, check=True):
    out = os.path.join(d, "out_" + os.path.basename(model) + "_".join(extra).replace("-", ""))
    r = blender("--python", TOOL, "--", "--reference", f"{d}/ref.png", "--model", model,
                "--hdri", f"{d}/env.hdr", "--out", out, "--samples", "2", *extra, check=check)
    line = next((l for l in r.stdout.splitlines() if l.startswith("FIDELITY ")), None)
    return r, (json.loads(line[len("FIDELITY "):]) if line else None), out


with tempfile.TemporaryDirectory() as d:
    open(f"{d}/build.py", "w").write(BUILD)
    blender("--python", f"{d}/build.py", "--", d)
    checks = []

    def check(name, ok, got):
        checks.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {name}  ({got})")

    _, same, _ = measure(d, f"{d}/vase.glb")
    shape_gaps = [g for g in same["gaps"] if g.startswith("band") and "width" in g]
    check("model vs its own render: IoU near 1", same["iou"] > 0.95, round(same["iou"], 3))
    check("model vs its own render: no shape gap", not shape_gaps, shape_gaps)

    _, wide, _ = measure(d, f"{d}/vase_wide.glb")
    body = [b for b in wide["shape"] if b["band"] >= 3]
    mean_w = sum(b["full_width"] for b in body) / len(body)
    check("20 % wider: width gap reported", any("width +" in g for g in wide["gaps"]), wide["gaps"][:2])
    check("20 % wider: measured close to +20 %", 0.15 < mean_w < 0.25, round(mean_w, 3))

    r, _, _ = measure(d, f"{d}/lost.blend", check=False)
    check("unloaded texture: refused with exit 1", r.returncode == 1 and "textures not loaded" in (r.stdout + r.stderr),
          r.returncode)

    r, blend, _ = measure(d, f"{d}/vase.blend")
    check("a .blend: warned that the shipped file counts", "WARNING" in r.stdout and blend is not None,
          "WARNING" in r.stdout)

    _, over, _ = measure(d, f"{d}/vase.glb", "--max-tris", "10")
    _, under, _ = measure(d, f"{d}/vase.glb", "--max-tris", "100000")
    check("--max-tris: reported above the limit", any("triangles, above" in g for g in over["gaps"]), over["tris"])
    check("--max-tris: silent below it", not any("triangles, above" in g for g in under["gaps"]), under["tris"])
    check("--max-tris: past 2x, a reduction proposed", any("propose a reduction" in g for g in over["gaps"]), over["tris"])
    _, near, _ = measure(d, f"{d}/vase.glb", "--max-tris", str(int(over["tris"] / 1.5)))
    tri = [g for g in near["gaps"] if "triangles, above" in g]
    check("--max-tris: under 2x, listed last, not to cut",
          bool(tri) and "do not cut" in tri[0] and near["gaps"][-1] == tri[0], tri)

    for name, flagged in (("dark_metal", True), ("dark_paint", False), ("bright_metal", False)):
        _, r, _ = measure(d, f"{d}/{name}.glb")
        hit = [g for g in r["gaps"] if "black mirror" in g]
        check(f"{name}: dark-metal gap {'reported' if flagged else 'silent'}", bool(hit) == flagged,
              [round(m["base_median"], 3) for m in r["metals"]])

    for label, extra, want in (("--view front", ("--view", "front"), 2.0),
                               ("--view left", ("--view", "left"), 1.0),
                               ("--azimuth 90", ("--azimuth", "90"), 1.0),
                               ("--azimuth 45", ("--azimuth", "45"), 2 * 0.7071 + 0.7071)):
        view = label.replace("--", "").replace(" ", "_")
        _, _, out = measure(d, f"{d}/box.glb", *extra)
        probe = f"{d}/probe_{view}.py"
        open(probe, "w").write(
            "import bpy, numpy as np\n"
            f"im = bpy.data.images.load('{out}/_silhouette.png'); w, h = im.size\n"
            "m = np.array(im.pixels[:]).reshape(h, w, 4)[..., 3] > 0.5\n"
            "ys, xs = np.where(m); print('ASPECT', (np.ptp(xs) + 1) / (np.ptp(ys) + 1))\n")
        a = float(next(l for l in blender("--python", probe).stdout.splitlines() if l.startswith("ASPECT")).split()[1])
        check(f"{label}: 2x1x1 box silhouette {want:.2f}:1", abs(a - want) < 0.08, round(a, 2))

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
