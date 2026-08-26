#!/usr/bin/env python3
"""Re-check, inside Blender, the findings that needed Blender to establish.

Run through Blender, never as plain Python:

    blender --background --factory-startup --python tools/verify_blender.py

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

mat = bpy.data.materials.new("probe"); mat.use_nodes = True
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

print("── verify_blender")
for x in notes:
    print(f"  ok   {x}")
for x in failures:
    print(f"  FAIL {x}")
print(f"── {len(failures)} failure(s)")
sys.exit(1 if failures else 0)
