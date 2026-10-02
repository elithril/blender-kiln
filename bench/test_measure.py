"""Seed each defect measure.py claims to catch, and assert it is caught.

    python3 bench/test_measure.py            # needs Blender at $BLENDER or the macOS default

Two rigged fixtures are built in Blender and exported to GLB: a healthy arm,
and the same arm with the defects the bench exists for — a deform bone that
drives nothing, and vertices with no weight. A loose edge is not seeded: the
glTF exporter drops loose edges by default, so a shipped GLB cannot carry one. A mesh-only
fixture carries the geometry defects: a fin sharing one edge between three
faces, and an asset floating 0.5 m above the ground.
"""
import json, os, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
HERE = os.path.dirname(os.path.abspath(__file__))

BUILD = r'''
import bpy, bmesh, sys
out = sys.argv[sys.argv.index("--") + 1]

def arm(defects):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, depth=2.0, location=(0, 0, 1))
    body = bpy.context.object
    body.name = "SM_Arm"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.subdivide(number_cuts=10)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.armature_add(location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "SK_Arm"
    bpy.ops.object.mode_set(mode="EDIT")
    root = rig.data.edit_bones[0]; root.name = "Root"; root.head = (0, 0, -0.2); root.tail = (0, 0, 0)
    b0 = rig.data.edit_bones.new("upper"); b0.head = (0, 0, 0); b0.tail = (0, 0, 1); b0.parent = root
    b1 = rig.data.edit_bones.new("lower"); b1.head = (0, 0, 1); b1.tail = (0, 0, 2); b1.parent = b0
    if defects:
        b2 = rig.data.edit_bones.new("orphan"); b2.head = (1, 0, 0); b2.tail = (1, 0, 0.5); b2.parent = root
    bpy.ops.object.mode_set(mode="OBJECT")
    body.select_set(True); rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    if defects:
        # The orphan bone is far from the mesh; envelope weights leave it empty.
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        top = [v.index for v in body.data.vertices if v.co.z > 0.8]
        for g in body.vertex_groups:
            g.remove(top)
        # Bone heat reaches even a distant bone (measured: 1,497 vertices), so
        # empty the orphan's group explicitly to make it drive nothing.
        orphan = body.vertex_groups["orphan"]
        orphan.remove([v.index for v in body.data.vertices])
    else:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    # The root sits below the mesh and gets no weight: a healthy anchor.
    body.vertex_groups["Root"].remove([v.index for v in body.data.vertices]) if "Root" in body.vertex_groups else None
    bpy.ops.export_scene.gltf(filepath=f"{out}/arm_{'bad' if defects else 'good'}.glb",
                              export_format="GLB", export_apply=False)

def fin():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new("SM_Fin_Mesh")
    bm = bmesh.new()
    a = bm.verts.new((0, 0, 0.5)); b = bm.verts.new((1, 0, 0.5))
    for p in [(0.5, 1, 0.5), (0.5, -1, 0.5), (0.5, 0, 1.5)]:
        bm.faces.new((a, b, bm.verts.new(p)))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("SM_Fin", me)
    bpy.context.scene.collection.objects.link(o)
    bpy.ops.export_scene.gltf(filepath=f"{out}/fin.glb", export_format="GLB")

arm(False); arm(True); fin()
'''


def blender(*args):
    r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"blender failed ({r.returncode}):\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def measure(glb):
    outp = blender("--python", os.path.join(HERE, "measure.py"), "--", glb)
    line = next((l for l in outp.splitlines() if l.startswith("BENCH_JSON ")), None)
    if line is None:
        sys.exit(f"no BENCH_JSON line for {glb}:\n{outp[-2000:]}")
    return json.loads(line[len("BENCH_JSON "):])


with tempfile.TemporaryDirectory() as d:
    script = os.path.join(d, "build.py")
    open(script, "w").write(BUILD)
    blender("--python", script, "--", d)
    good, bad, fin = (measure(os.path.join(d, f)) for f in ("arm_good.glb", "arm_bad.glb", "fin.glb"))

checks = []
def check(name, ok, got):
    checks.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  ({got})")

g, b = good["rigs"][0], bad["rigs"][0]
check("healthy rig: an unweighted Root is not a dead bone", g["deform_bones_without_influence"] == 0, g)
check("healthy rig: no unweighted vertex", g["unweighted_verts"] == 0, g["unweighted_verts"])
check("healthy rig: closed mesh after weld", good["boundary_edges"] == 0 and good["non_manifold_edges"] == 0,
      (good["boundary_edges"], good["non_manifold_edges"]))
check("healthy rig: sits on the ground", abs(good["z_min_m"]) < 1e-3, good["z_min_m"])
check("seeded: dead deform bone caught", b["deform_bones_without_influence"] >= 1, b["deform_bones_without_influence"])
check("seeded: unweighted vertices caught", b["unweighted_verts"] > 0, b["unweighted_verts"])
check("seeded: unweighted vertices survive export as neutral_bone", b["neutral_bone"], b["neutral_bone"])
check("seeded: unweighted skin tears under the probe", b["stretch_max"] > g["stretch_max"],
      (g["stretch_max"], b["stretch_max"]))
check("seeded: edge shared by three faces caught", fin["non_manifold_edges"] >= 1, fin["non_manifold_edges"])
check("seeded: floating asset caught", fin["z_min_m"] > 0.4, fin["z_min_m"])

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
