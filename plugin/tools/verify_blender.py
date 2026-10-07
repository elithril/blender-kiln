#!/usr/bin/env python3
"""Re-check, inside Blender, the findings that needed Blender to establish.

Run through Blender, never as plain Python:

    blender --background --factory-startup --python-exit-code 1 --python tools/verify_blender.py

Every check corresponds to a bug this repository actually shipped. They exist to
notice when a Blender release makes one of them wrong again.
"""
import json
import math
import re
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
failures: list[str] = []
notes: list[str] = []

# Blender announces removals through DeprecationWarning. The first CI run buried
# "'Material.use_nodes' is expected to be removed in Blender 6.0" in the log,
# where it would have sat until 6.0 broke the docs. Collect them and fail.
import warnings
_deprecations: list[str] = []
warnings.simplefilter("always", DeprecationWarning)
_orig_showwarning = warnings.showwarning


def _capture(message, category, filename, lineno, file=None, line=None):
    if issubclass(category, DeprecationWarning):
        _deprecations.append(str(message))
    _orig_showwarning(message, category, filename, lineno, file, line)


warnings.showwarning = _capture


def fail(check, msg):
    failures.append(f"{check}: {msg}")


def ok(msg):
    notes.append(msg)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ── 1. Documented Blender API still exists.
# references/characters.md once told readers to use Action.fcurves, removed in
# 4.4+, and the error names nothing relevant.
reset()
bpy.ops.mesh.primitive_cube_add()
o = bpy.context.object
o.location = (0, 0, 0); o.keyframe_insert("location", frame=1)
o.location = (0, 1, 0); o.keyframe_insert("location", frame=24)
act = o.animation_data.action
if hasattr(act, "fcurves"):
    ok("api: Action.fcurves is back — the channelbag walk in characters.md can be simplified")
else:
    reached = sum(1 for lay in act.layers for st in lay.strips
                  for slot in act.slots if st.channelbag(slot)
                  for _ in st.channelbag(slot).fcurves)
    if reached != 3:
        fail("api", f"channelbag walk reached {reached} F-curves, expected 3 — "
                    f"the documented path in characters.md no longer works")
    else:
        ok("api: channelbag walk reaches all 3 F-curves")

# ── 2. Every bpy attribute quoted in the docs is real.
# use_gtao and use_bloom were silently skipped by hasattr guards after EEVEE Next
# removed them, and BLENDER_EEVEE_NEXT no longer exists in 5.0.
engines = [i.identifier for i in
           bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
docs = "\n".join(p.read_text() for p in
                 [ROOT / "SKILL.md"] + sorted((ROOT / "references").glob("*.md")))
for ident in sorted(set(re.findall(r"\bBLENDER_[A-Z_]+\b", docs))):
    if ident not in engines:
        fail("engines", f"docs name render engine {ident}, which does not exist: {engines}")
else:
    ok(f"engines: available = {engines}")

scene = bpy.context.scene
for attr in sorted(set(re.findall(r"scene\.eevee\.(\w+)", docs))):
    if not hasattr(scene.eevee, attr):
        fail("eevee", f"docs use scene.eevee.{attr}, which no longer exists")

mat = bpy.data.materials.new("probe")   # node_tree is present by default in 5.x
bsdf = mat.node_tree.nodes["Principled BSDF"]
sockets = {i.name for i in bsdf.inputs}
# Only inputs reached through a variable that IS the Principled node. A bare
# `inputs["..."]` also matches Normal Map, Mix and Material Output sockets —
# Color, Fac, Shader and Surface all tripped this before it was narrowed.
for name in sorted(set(re.findall(
        r"(?:bsdf|principled)\.inputs\[[\"']([\w ]+)[\"']\]", docs, re.I))):
    if name not in sockets:
        fail("bsdf", f"docs use Principled input {name!r}, which no longer exists")
else:
    ok("bsdf: every Principled socket named in the docs exists")

# ── 3. Rig tiers still match what Rigify generates.
# PHASE 5c routes on these numbers; if Rigify changes them the routing is wrong.
bpy.ops.preferences.addon_enable(module="rigify")
TIERS = {"armature_basic_human_metarig_add": 35, "armature_human_metarig_add": 160}
for op_name, expected in TIERS.items():
    reset()
    bpy.ops.preferences.addon_enable(module="rigify")
    getattr(bpy.ops.object, op_name)()
    bpy.ops.pose.rigify_generate()
    rig = bpy.context.object
    deform = sum(1 for b in rig.data.bones if b.use_deform)
    if deform != expected:
        fail("rigtiers", f"{op_name} now yields {deform} deform bones, "
                         f"PHASE 5c in SKILL.md says {expected}")
    else:
        ok(f"rigtiers: {op_name} = {deform} deform bones")
    # A fresh rig must still default to IK, or the documented trap is stale.
    parents = [pb for pb in rig.pose.bones if "IK_FK" in pb.keys()]
    if parents and any(pb["IK_FK"] != 0.0 for pb in parents):
        ok("ikfk: limbs no longer default to IK — the warning in characters.md is stale")

# ── 4. Geometry nodes still need the modifier applied before export.
# Rule 18's exception exists because export_apply=False writes the base mesh.
reset()
bpy.ops.mesh.primitive_plane_add(size=4)
ground = bpy.context.object
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.12, depth=0.5, location=(0, 0, -10))
inst = bpy.context.object
mod = ground.modifiers.new("GN", "NODES")
ng = bpy.data.node_groups.new("gn", "GeometryNodeTree")
mod.node_group = ng
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
n = ng.nodes
gin, gout = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
try:
    dist = n.new("GeometryNodeDistributePointsOnFaces")
    ins = n.new("GeometryNodeInstanceOnPoints")
    obj = n.new("GeometryNodeObjectInfo")
    real = n.new("GeometryNodeRealizeInstances")
except Exception as e:
    fail("gnnodes", f"a node type the flow prescribes is gone: {e}")
else:
    ok("gnnodes: all four prescribed node types exist")
    dist.inputs["Density"].default_value = 12.0
    obj.inputs["Object"].default_value = inst
    L = ng.links.new
    L(gin.outputs[0], dist.inputs["Mesh"])
    L(dist.outputs["Points"], ins.inputs["Points"])
    L(obj.outputs["Geometry"], ins.inputs["Instance"])
    L(ins.outputs["Instances"], real.inputs["Geometry"])
    L(real.outputs["Geometry"], gout.inputs[0])
    bpy.context.view_layer.update()

    def glb_tris(path):
        d = Path(path).read_bytes()
        import struct
        ln = struct.unpack("<I", d[12:16])[0]
        j = json.loads(d[20:20 + ln])
        return sum(j["accessors"][p["indices"]]["count"] // 3
                   for m in j.get("meshes", []) for p in m["primitives"])

    def export(path, apply_=False):
        bpy.ops.object.select_all(action="DESELECT")
        ground.select_set(True); bpy.context.view_layer.objects.active = ground
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB",
                                  use_selection=True, export_apply=apply_)
        return glb_tris(path)

    live = export("/tmp/_gn_live.glb")
    bpy.ops.object.select_all(action="DESELECT")
    ground.select_set(True); bpy.context.view_layer.objects.active = ground
    bpy.ops.object.modifier_apply(modifier="GN")
    real_tris = sum(len(p.vertices) - 2 for p in ground.data.polygons)
    applied = export("/tmp/_gn_applied.glb")
    if applied < real_tris * 0.95:
        fail("gnexport", f"applying the modifier gave {applied} tris for {real_tris} in the mesh")
    elif live >= real_tris * 0.5:
        ok("gnexport: export_apply=False now carries GN output — rule 18's exception is stale")
    else:
        ok(f"gnexport: live modifier exports {live} tris, applied exports {applied} — "
           f"rule 18's exception still needed")

# ── 5. USDZ still exports natively, and still needs convert_world_material off.
reset()
bpy.ops.mesh.primitive_monkey_add()
try:
    bpy.ops.wm.usd_export(filepath="/tmp/_probe.usdz", export_materials=True,
                          convert_world_material=False)
    import zipfile
    names = zipfile.ZipFile("/tmp/_probe.usdz").namelist()
    bad = [x for x in names if Path(x).suffix.lower() not in ("", ".usdc", ".usda", ".png", ".jpg", ".jpeg")]
    if bad:
        fail("usdz", f"archive holds files the USDZ spec does not admit: {bad}")
    else:
        ok(f"usdz: native export produces a conforming archive ({len(names)} entries)")
except Exception as e:
    fail("usdz", f"native export failed, export-targets.md prescribes it: {e}")

# ── 5b. Rule 10's weld keeps the shading, and a welded mesh does not tear when posed.
# validation-checklist.md and characters.md ship both as code; run that code itself,
# so the docs cannot drift from what works. A low-poly cat weighted with its split
# edges opened 12.5 cm at the first pose; a plain merge re-smoothed it (26.7% -> 94.5%
# of corners bent > 5°).
def _doc_code(path, start, end):
    text = (ROOT / "references" / path).read_text()
    text = text[text.index(start):text.index(end)]
    for block in re.findall(r"```python\n(.*?)```", text, re.S):
        exec(block, globals())


def _split_tube():
    import bmesh
    reset()
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.1, depth=2, location=(0, 0, 1))
    tube = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(tube.data)
    side = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6]
    bmesh.ops.subdivide_edges(bm, edges=side, cuts=9, use_grid_fill=True)
    bmesh.ops.split_edges(bm, edges=bm.edges[:])          # what a flat-shaded export does:
    for f in bm.faces:                                     # faces marked smooth, the facets
        f.smooth = True                                    # come from the split alone
    bm.to_mesh(tube.data); bm.free()
    arm_data = bpy.data.armatures.new("probe"); arm = bpy.data.objects.new("probe", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    a = arm_data.edit_bones.new("Upper"); a.head, a.tail = (0, 0, 2), (0, 0, 1)
    b = arm_data.edit_bones.new("Lower"); b.head, b.tail = (0, 0, 1), (0, 0, 0); b.parent = a; b.use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')
    return tube, arm


def _weight_and_bend(tube, arm):
    bpy.ops.object.select_all(action='DESELECT'); tube.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    arm.pose.bones["Lower"].rotation_mode = 'XYZ'
    arm.pose.bones["Lower"].rotation_euler.x = math.radians(45)
    bpy.context.view_layer.update()
    return widest_tear(tube)


def _bent(me):
    me.update()
    n = [math.degrees(math.acos(max(-1.0, min(1.0, me.loops[i].normal.dot(p.normal)))))
         for p in me.polygons for i in p.loop_indices]
    return sum(x > 5 for x in n) / len(n)


try:
    _doc_code("validation-checklist.md", "### Merge by Distance", "### Recalculate Normals")
    _doc_code("characters.md", "### Animation-ready skeleton", "### Rigify from Python")
    tube, arm = _split_tube()
    as_shipped = _weight_and_bend(tube, arm)
    tube, arm = _split_tube()
    shading_before = _bent(tube.data)
    import bmesh
    plain = tube.data.copy(); bm = bmesh.new(); bm.from_mesh(plain)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); bm.to_mesh(plain); bm.free()
    shading_plain = _bent(plain)
    weld_keep_shading(tube)
    shading_kept = _bent(tube.data)
    welded = _weight_and_bend(tube, arm)
    if as_shipped < 1e-3:
        fail("weld", f"a split mesh weighted as shipped no longer tears ({as_shipped:.4f} m): "
                     "the weld-before-rig step may be unnecessary now")
    elif welded > 1e-6:
        fail("weld", f"the rule 10 weld leaves a {welded:.4f} m tear on a posed split tube")
    elif abs(shading_kept - shading_before) > 0.01 or shading_plain - shading_before < 0.5:
        fail("weld", f"shading: before {shading_before:.0%}, plain merge {shading_plain:.0%}, "
                     f"weld_keep_shading {shading_kept:.0%} — the doc's claim no longer holds")
    else:
        ok(f"weld: split tube tears {as_shipped:.3f} m as shipped, 0 welded; corners bent "
           f"{shading_before:.0%} -> plain merge {shading_plain:.0%}, normals kept {shading_kept:.0%}")
except Exception as e:
    fail("weld", f"the weld or pose-test code in the docs does not run: {e}")

# ── 5c. The quadruped walk stays measured: legs bent, paws in step, loop exact.
# tools/quadruped.py replaced text-to-motion for four-legged locomotion; its first
# cycle locked the legs at 101% of their length and moved the hips forward instead of
# up. Run it on a synthetic quadruped built here, so no asset is downloaded.
def _synthetic_quadruped(path):
    reset()
    def seg(a, b, r):
        d = b - a
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=r, depth=d.length, location=(a + b) / 2)
        o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); return o
    V = lambda x, y, z: Vector((x, y, z))
    bones, parts = [], []
    def add(name, a, b, parent, r=0.03):
        bones.append((name, a, b, parent)); o = seg(a, b, r); o["bone"] = name; parts.append(o)
    add("Hips", V(0, 0.25, 0.40), V(0, 0.05, 0.40), None, 0.08)
    add("Spine1", V(0, 0.05, 0.40), V(0, -0.20, 0.42), "Hips", 0.08)
    add("Neck", V(0, -0.20, 0.42), V(0, -0.28, 0.52), "Spine1", 0.04)
    add("Head", V(0, -0.28, 0.52), V(0, -0.38, 0.55), "Neck", 0.05)
    for s, x in (("Left", 0.07), ("Right", -0.07)):
        add(f"{s}UpLeg", V(x, 0.24, 0.36), V(x, 0.20, 0.22), "Hips")
        add(f"{s}Leg", V(x, 0.20, 0.22), V(x, 0.25, 0.08), f"{s}UpLeg")
        add(f"{s}Foot", V(x, 0.25, 0.08), V(x, 0.23, 0.01), f"{s}Leg", 0.025)
        add(f"{s}Arm", V(x, -0.18, 0.36), V(x, -0.20, 0.20), "Spine1")
        add(f"{s}ForeArm", V(x, -0.20, 0.20), V(x, -0.19, 0.07), f"{s}Arm")
        add(f"{s}Hand", V(x, -0.19, 0.07), V(x, -0.21, 0.01), f"{s}ForeArm", 0.025)
    ad = bpy.data.armatures.new("quad"); arm = bpy.data.objects.new("quad", ad); bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    for n, a, b, p in bones:
        eb = ad.edit_bones.new(n); eb.head, eb.tail = a, b
        if p: eb.parent = ad.edit_bones[p]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in parts:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        o.vertex_groups.new(name=o["bone"]).add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
    body = bpy.context.object; body.parent = arm; body.modifiers.new("Armature", 'ARMATURE').object = arm
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.export_scene.gltf(filepath=path, use_selection=True)


try:
    from mathutils import Vector
    sys.path.insert(0, str(ROOT / "tools"))
    import quadruped as Q
    _synthetic_quadruped("/tmp/_quad.glb")
    sc, arm, m = Q.make("/tmp/_quad.glb", "/tmp", "walk", 32, Q.walk, 0.11, 0.15)
    if m["frames"] != 32:
        fail("quadruped", f"walk has {m['frames']} frames, not 32 — the seam repeats a frame")
    elif m["extension"] > Q.MAX_EXTENSION:
        fail("quadruped", f"legs straighten to {m['extension']:.0%} of their length (limit {Q.MAX_EXTENSION:.0%})")
    elif m["root_speed_m_s"] <= 0 or m["stance_speed_spread"] > 0.10:
        fail("quadruped", f"planted paws are out of step: speed {m['root_speed_m_s']} m/s, spread {m['stance_speed_spread']}")
    else:
        ok(f"quadruped: walk on a synthetic rig — legs <= {m['extension']:.0%}, paws in step "
           f"({m['root_speed_m_s']} m/s, spread {m['stance_speed_spread']}), {m['frames']} frames")
except Exception as e:
    fail("quadruped", f"tools/quadruped.py does not run on a template-named rig: {e}")

# ── 5d. Bone-parented parts survive skin-only pipelines; generated clips loop.
# A Quaternius dragon's eyes hung off a bone by parenting: UniMate kept the skin and left
# them floating. And UniMate's clips seam at 2.4-8.5x their own frame step.
import subprocess
def _blender_tool(script, *args):
    r = subprocess.run([bpy.app.binary_path, "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", str(ROOT / "tools" / script), "--", *args], capture_output=True, text=True)
    return r.returncode, r.stdout

try:
    # rigid part: a cube parented to the synthetic quadruped's Head bone
    _synthetic_quadruped("/tmp/_quad.glb")
    reset(); bpy.ops.import_scene.gltf(filepath="/tmp/_quad.glb")
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    bpy.ops.mesh.primitive_cube_add(size=0.04, location=(0, -0.40, 0.58)); cube = bpy.context.object; cube.name = "Eye"
    mw = cube.matrix_world.copy(); cube.parent = arm; cube.parent_type = 'BONE'; cube.parent_bone = "Head"; cube.matrix_world = mw
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.export_scene.gltf(filepath="/tmp/_quad_eye.glb", use_selection=True)
    code, out = _blender_tool("bind_rigid_parts.py", "/tmp/_quad_eye.glb", "/tmp/_quad_bound.glb")
    reset(); bpy.ops.import_scene.gltf(filepath="/tmp/_quad_bound.glb")
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    body = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    # the eye's own vertices, found once at rest and followed by index
    bpy.context.view_layer.update(); e = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    eye = [i for i, v in enumerate(e.data.vertices) if ((e.matrix_world @ v.co) - Vector((0, -0.40, 0.58))).length < 0.04]
    def eye_gap():
        bpy.context.view_layer.update(); e = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        c = sum((e.matrix_world @ e.data.vertices[i].co for i in eye), Vector()) / max(len(eye), 1)
        return (c - arm.matrix_world @ arm.pose.bones["Head"].head).length
    g0 = eye_gap(); arm.pose.bones["Head"].rotation_mode = 'XYZ'; arm.pose.bones["Head"].rotation_euler = (0.6, 0, 0.4); g1 = eye_gap()
    if "1 rigid part(s)" not in out or len(eye) < 8 or abs(g1 - g0) > 1e-4:
        fail("rigidparts", f"a bone-parented part was not folded in, or does not follow its bone (gap {g0:.4f} -> {g1:.4f})")
    elif "posture quadruped" not in out:
        fail("posture", "the synthetic quadruped is not recognised as one — the UniMate routing guard would not fire")
    else:
        ok(f"rigidparts: a bone-parented part follows its bone once folded in ({g0:.3f} m either way); posture: quadruped recognised")
    # loop: a joint swinging with a 13-frame period, starting at its peak, cut at 48 frames — mid-swing
    reset()
    ad = bpy.data.armatures.new("osc"); arm = bpy.data.objects.new("osc", ad); bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    a = ad.edit_bones.new("Root"); a.head, a.tail = (0, 0, 0), (0, 0, 1)
    b = ad.edit_bones.new("Arm"); b.head, b.tail = (0, 0, 1), (0, 0, 2); b.parent = a
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, 0, 1.5)); m = bpy.context.object
    m.vertex_groups.new(name="Arm").add(list(range(8)), 1.0, 'REPLACE'); m.parent = arm; m.modifiers.new("A", 'ARMATURE').object = arm
    arm.animation_data_create(); pb = arm.pose.bones["Arm"]; pb.rotation_mode = 'QUATERNION'
    from mathutils import Euler
    for f in range(48):
        pb.rotation_quaternion = Euler((0.6 * math.cos(2 * math.pi * f / 13), 0, 0)).to_quaternion(); pb.keyframe_insert("rotation_quaternion", frame=f)
        arm.pose.bones["Root"].rotation_mode = 'QUATERNION'; arm.pose.bones["Root"].keyframe_insert("rotation_quaternion", frame=f)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.export_scene.gltf(filepath="/tmp/_osc.glb", use_selection=True, export_animations=True)
    code, out = _blender_tool("motion_loop.py", "--out", "/tmp/_osc_loop.glb", "/tmp/_osc.glb")
    rec = [json.loads(l.split("motion_loop: ", 1)[1]) for l in out.splitlines() if l.startswith("motion_loop: {")]
    if code or not rec:
        fail("loop", f"motion_loop.py found no loop in a clean 13-frame oscillation (exit {code})")
    elif rec[0]["seam"] > 1.2 or rec[0]["seam_raw"] < 2:
        fail("loop", f"seam {rec[0]['seam_raw']}x raw -> {rec[0]['seam']}x looped; expected a raw seam > 2x closing to <= 1.2x")
    else:
        ok(f"loop: a 13-frame swing cut at 48 frames seams {rec[0]['seam_raw']}x raw, {rec[0]['seam']}x looped "
           f"({rec[0]['frames']} frames kept)")
except Exception as e:
    fail("rigidparts/loop", f"bind_rigid_parts.py or motion_loop.py does not run: {e}")

# ── 6. Nothing the checks touched is on a removal path.
if _deprecations:
    for d in sorted(set(_deprecations)):
        fail("deprecated", f"{d} — reached by the docs or the gallery scripts")
else:
    ok("deprecated: nothing reached is scheduled for removal")

print("── verify_blender")
for x in notes:
    print(f"  ok   {x}")
for x in failures:
    print(f"  FAIL {x}")
print(f"── {len(failures)} failure(s)")
sys.exit(1 if failures else 0)
