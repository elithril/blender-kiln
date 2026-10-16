"""Seed each defect measure.py claims to catch, and assert it is caught.

    python3 bench/test_measure.py            # needs Blender at $BLENDER or the macOS default

Two rigged fixtures are built in Blender and exported to GLB: a healthy arm,
and the same arm with the defects the bench exists for — a deform bone that
drives nothing, and vertices with no weight. A loose edge is not seeded: the
glTF exporter drops loose edges by default, so a shipped GLB cannot carry one. A mesh-only
fixture carries the geometry defects: a fin sharing one edge between three
faces, and an asset floating 0.5 m above the ground.

The newer measures have theirs. Two box-and-cylinder bipeds, rigid-weighted, kiln's bone
names: a healthy one, and the same with a chibi belly hanging in front of the thighs — the
bent pose (thighs 60° forward) drives the thighs through it (skin_intersect.py). A clip
fixture: a walk whose last key repeats the first, a drift whose last key does not, an idle
that turns an eyelid bone (clips, loop closure, blink). The transcript signals (signals.py)
and the bone-name resolver are checked on seeded inputs, outside Blender.
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

def biped(belly):
    """Rigid parts with gaps at every joint: bending them crosses nothing, unless a belly
    hangs where the thighs go."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.object.armature_add(location=(0, 0, 0))
    rig = bpy.context.object; rig.name = "SK_Kid"
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    eb.remove(eb[0])
    def bone(n, h, t, p=None):
        b = eb.new(n); b.head = h; b.tail = t
        if p: b.parent = eb[p]
        return b
    bone("Hips", (0, 0, 0.53), (0, 0, 0.62))
    bone("Spine", (0, 0, 0.62), (0, 0, 0.75), "Hips")
    bone("Neck", (0, 0, 0.92), (0, 0, 0.96), "Spine")
    bone("Head", (0, 0, 0.96), (0, 0, 1.1), "Neck")
    for sx, sd in ((1, "Left"), (-1, "Right")):
        bone(sd + "UpLeg", (0.08 * sx, 0, 0.53), (0.08 * sx, 0, 0.30), "Hips")
        bone(sd + "Leg", (0.08 * sx, 0, 0.295), (0.08 * sx, 0, 0.08), sd + "UpLeg")
        bone(sd + "Foot", (0.08 * sx, 0, 0.07), (0.08 * sx, -0.1, 0.02), sd + "Leg")
        bone(sd + "Arm", (0.18 * sx, 0, 0.86), (0.33 * sx, 0, 0.86), "Spine")
        bone(sd + "ForeArm", (0.34 * sx, 0, 0.86), (0.48 * sx, 0, 0.86), sd + "Arm")   # 4 cm gaps
    bpy.ops.object.mode_set(mode="OBJECT")
    bm = bmesh.new(); parts = []
    def box(lo, hi, b):
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]:
            v.co = [(lo[i] + hi[i]) / 2 + v.co[i] * (hi[i] - lo[i]) for i in range(3)]
        parts.append((r["verts"], b))
    def cyl(a, z0, z1, r_, b, axis="Z"):
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r_, radius2=r_, depth=abs(z1 - z0))
        for v in r["verts"]:
            x, y, z = v.co
            if axis == "Z":
                v.co = (a[0] + x, a[1] + y, (z0 + z1) / 2 + z)
            else:  # along X
                v.co = ((z0 + z1) / 2 + z, a[1] + y, a[2] + x)
        parts.append((r["verts"], b))
    box((-0.15, -0.08, 0.60), (0.15, 0.08, 0.90), "Spine")
    box((-0.10, -0.10, 0.99), (0.10, 0.10, 1.15), "Head")
    if belly:
        box((-0.15, -0.25, 0.40), (0.15, -0.12, 0.55), "Spine")
    for sx, sd in ((1, "Left"), (-1, "Right")):
        cyl((0.08 * sx, 0), 0.35, 0.51, 0.04, sd + "UpLeg")
        cyl((0.08 * sx, 0), 0.09, 0.24, 0.035, sd + "Leg")
        box((0.08 * sx - 0.03, -0.11, 0.0), (0.08 * sx + 0.03, 0.03, 0.05), sd + "Foot")
        lo, hi = sorted((0.20 * sx, 0.30 * sx)); cyl((0, 0, 0.86), lo, hi, 0.03, sd + "Arm", "X")
        lo, hi = sorted((0.38 * sx, 0.48 * sx)); cyl((0, 0, 0.86), lo, hi, 0.028, sd + "ForeArm", "X")
    bm.verts.index_update()
    owner = {}
    for vs, b in parts:
        for v in vs:
            owner[v.index] = b
    me = bpy.data.meshes.new("SM_Kid_Mesh"); bm.to_mesh(me); bm.free()
    body = bpy.data.objects.new("SM_Kid", me); bpy.context.scene.collection.objects.link(body)
    for b in sorted(set(owner.values())):
        g = body.vertex_groups.new(name=b)
        g.add([i for i, o in owner.items() if o == b], 1.0, "REPLACE")
    body.parent = rig
    body.modifiers.new("Armature", "ARMATURE").object = rig
    bpy.ops.export_scene.gltf(filepath=f"{out}/biped_{'belly' if belly else 'good'}.glb", export_format="GLB")

def anim():
    """walk: last key = first. drift: it does not. idle: an eyelid bone closes and opens."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, 0, 0.1))
    body = bpy.context.object; body.name = "SM_Blob"
    bpy.ops.object.armature_add(location=(0, 0, 0))
    rig = bpy.context.object; rig.name = "SK_Blob"
    bpy.ops.object.mode_set(mode="EDIT")
    rig.data.edit_bones[0].name = "Root"
    lid = rig.data.edit_bones.new("LeftEyelid"); lid.head = (0, -0.1, 0.15); lid.tail = (0, -0.1, 0.2)
    lid.parent = rig.data.edit_bones["Root"]
    bpy.ops.object.mode_set(mode="OBJECT")
    body.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    rig.animation_data_create()
    def clip(name, keys, bone="Root"):
        act = bpy.data.actions.new(name)
        rig.animation_data.action = act
        pb = rig.pose.bones[bone]; pb.rotation_mode = "XYZ"
        for f, deg in keys:
            pb.rotation_euler = (math.radians(deg), 0, 0)
            pb.keyframe_insert("rotation_euler", frame=f)
        pb.rotation_euler = (0, 0, 0)
        tr = rig.animation_data.nla_tracks.new(); tr.name = name
        tr.strips.new(name, int(keys[0][0]), act)
        rig.animation_data.action = None
    clip("walk", [(0, 0), (6, 20), (12, 0), (18, -20), (24, 0)])
    clip("drift", [(0, 0), (6, 20), (12, 0), (18, -20), (24, -30)])
    clip("idle", [(0, 0), (10, 0), (13, 70), (16, 0), (36, 0)], bone="LeftEyelid")
    bpy.ops.export_scene.gltf(filepath=f"{out}/anim.glb", export_format="GLB",
                              export_animations=True, export_animation_mode="NLA_TRACKS")

import math
arm(False); arm(True); fin(); biped(False); biped(True); anim()
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
    good, bad, fin, kid, kid_belly, clipsf = (measure(os.path.join(d, f)) for f in (
        "arm_good.glb", "arm_bad.glb", "fin.glb", "biped_good.glb", "biped_belly.glb", "anim.glb"))
    # signals.py on a seeded transcript
    sys.path.insert(0, HERE)
    import signals, skin_intersect
    tr = os.path.join(d, "transcript.jsonl")
    def ev(kind, block):
        return json.dumps({"type": kind, "message": {"content": [block]}})
    lines = [
        ev("assistant", {"type": "tool_use", "name": "Read", "input": {"file_path": "/x/skill/tools/quadruped.py"}}),
        ev("assistant", {"type": "tool_use", "name": "Bash", "input": {"command":
            "blender -b --python /x/skill/tools/autorig.py -- --mesh kid.glb"}}),
        ev("assistant", {"type": "tool_use", "name": "mcp__blender__execute_blender_code", "input": {"code":
            "bpy.context.space_data.shading.light = 'MATCAP'"}}),
        ev("assistant", {"type": "text", "text": "Both hands came out fused into mittens; I kept them as one bone each."}),
        ev("user", {"type": "tool_result", "content": "...\nVERDICT FAIL"}),
        ev("assistant", {"type": "tool_use", "name": "Bash", "input": {"command":
            "blender -b --python /x/skill/tools/print_check.py -- a.stl --process fdm"}}),
        ev("user", {"type": "tool_result", "content": [{"type": "text", "text": "VERDICT PASS"}]}),
    ]
    open(tr, "w").write("\n".join(lines) + "\n")
    sig = signals.signals(tr, "Done. Shall I project the photo's markings onto the model?")
    open(tr, "w").write(lines[0] + "\n")
    quiet = signals.signals(tr, "Done.")

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

# skin_intersect.py — bent pose
kb, kbb = kid["rigs"][0]["bent"], kid_belly["rigs"][0]["bent"]
check("bent pose: kiln's names resolved, biped, every limb posed",
      kb.get("status") == "ok" and kb["posture"] == "biped" and len(kb["posed_bones"]) >= 8, kb)
check("bent pose: healthy rig crosses nothing", kb["self_mm2"] == 0 and kb["rest_self_mm2"] == 0,
      (kb["self_mm2"], kb["rest_self_mm2"]))
check("seeded: thighs driven through a belly caught as inter-part",
      kbb["inter_mm2"] > 100 and kbb["inter_pct"] > 0.5 and kbb["fold_mm2"] == 0,
      (kbb["inter_mm2"], kbb["inter_pct"], kbb["fold_mm2"], kbb["by_part_mm2"]))
check("one skin: one skinned mesh", kid["single_skin"] and kid["skinned_mesh_objects"] == 1,
      kid["skinned_mesh_objects"])
check("resolver: Rigify DEF- names", skin_intersect.resolve({
    "DEF-spine": None, "DEF-thigh.L": "DEF-spine", "DEF-shin.L": "DEF-thigh.L", "DEF-thigh.R": "DEF-spine",
    "DEF-spine.004": "DEF-spine", "DEF-upper_arm.L": "DEF-spine"}) == {
    "Hips": "DEF-spine", "LeftUpLeg": "DEF-thigh.L", "RightUpLeg": "DEF-thigh.R", "LeftLeg": "DEF-shin.L",
    "Neck": "DEF-spine.004", "LeftArm": "DEF-upper_arm.L"}, "Rigify")
# clips
cl = {c["name"]: c for c in clipsf["clips"]}
check("clips: three named clips read from the file", set(cl) == {"walk", "drift", "idle"}, sorted(cl))
check("clips: a walk whose last key repeats the first closes", cl["walk"]["loop_closes"] is True,
      cl["walk"]["seam"])
check("seeded: a clip ending 30° away does not close", cl["drift"]["loop_closes"] is False
      and cl["drift"]["seam"]["rotation_deg"] > 25, cl["drift"]["seam"])
check("clips: an eyelid that turns is a blink; a walk is not",
      cl["idle"]["blink"] == ["LeftEyelid.rotation"] and not cl["walk"]["blink"] and clipsf["blink"],
      (cl["idle"]["blink"], cl["walk"]["blink"]))
# signals.py
check("signals: a Read of a tool is not a run; autorig run is the rig route",
      sig["rig_route"] == "autorig (SkinTokens)" and not sig["quadruped_tool"], sig["rig_route"])
check("signals: matcap check, projection proposed, ended on a question",
      sig["matcap_check"] and sig["projection"]["proposed"] and not sig["projection"]["ran"]
      and sig["ended_on_question"], (sig["matcap_check"], sig["projection"], sig["ended_on_question"]))
check("signals: fused hand said; print_check verdicts in order",
      sig["fused_hand"]["mentions"] == 1 and sig["print_check"]["verdicts"] == ["FAIL", "PASS"]
      and sig["print_check"]["runs"] == 1, (sig["fused_hand"], sig["print_check"]))
check("signals: negative control — nothing proposed, no route",
      not quiet["projection"]["proposed"] and quiet["rig_route"] is None and not quiet["ended_on_question"], quiet)

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
