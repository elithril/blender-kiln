"""Rig the showcase cat to references/characters.md § Animation-ready skeleton.

    blender --background --factory-startup --python-exit-code 1 --python rig_cat.py -- <in.glb> <out.glb>

The mesh ("Cat" by madtrollstudio, CC BY 3.0) is a 1,856-vertex low-poly export with
every edge split. It goes through rule 10's weld first (466 vertices, shading kept),
then gets a 26-bone skeleton whose joints sit at the bends — found as the centroid of
each leg's vertices in thin horizontal slices — and automatic weights.
"""
import sys
from pathlib import Path

import bmesh  # noqa: F401 — used by the rule 10 code exec'd below
import bpy
import numpy as np
from mathutils import Vector

src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
DOC = Path(__file__).resolve().parents[2] / "plugin" / "references" / "validation-checklist.md"
text = DOC.read_text()
exec(text[text.index("def weld_keep_shading"):text.index("```", text.index("def weld_keep_shading"))])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
m = next(o for o in bpy.data.objects if o.type == 'MESH')
for o in list(bpy.data.objects):
    if o != m:
        bpy.data.objects.remove(o)
merged = weld_keep_shading(m)                       # rule 10: applies transforms, keeps normals
print(f"rig_cat: welded {merged} duplicate vertices -> {len(m.data.vertices)}")

V = np.array([v.co[:] for v in m.data.vertices])
FRONT_Y, BACK_Y = -0.322, 0.352                     # paw rows of this mesh (it faces -Y)


def leg(sx, y, z, band=0.03):
    q = V[(np.sign(V[:, 0]) == sx) & (np.abs(V[:, 1] - y) < 0.09) & (np.abs(V[:, 2] - z) < band)]
    return Vector(q.mean(0)) if len(q) else Vector((0.06 * sx, y, z))


J, parent = {}, {}
spine = [Vector((0, 0.30, 0.42)), Vector((0, 0.12, 0.43)), Vector((0, -0.05, 0.43)),
         Vector((0, -0.22, 0.44)), Vector((0, -0.31, 0.52)), Vector((0, -0.40, 0.56)), Vector((0, -0.47, 0.55))]
for name, a, b, p in zip(["Hips", "Spine", "Spine1", "Neck", "Head", "HeadTop_End"], spine, spine[1:],
                         [None, "Hips", "Spine", "Spine1", "Neck", "Head"]):
    J[name], parent[name] = (a, b), p
tail = [Vector((0, 0.36, 0.45)), Vector((0, 0.37, 0.55)), Vector((0, 0.36, 0.65)), Vector((0, 0.34, 0.74)), Vector((0, 0.31, 0.83))]
for i in range(4):
    J[f"Tail{i + 1}"], parent[f"Tail{i + 1}"] = (tail[i], tail[i + 1]), ("Hips" if i == 0 else f"Tail{i}")
for side, sx in (("Left", 1), ("Right", -1)):
    hip, knee, hock, paw = Vector((0.06 * sx, 0.32, 0.38)), leg(sx, BACK_Y, 0.22), leg(sx, BACK_Y, 0.10), leg(sx, BACK_Y, 0.03, 0.02)
    sh, elbow, wrist, fpaw = Vector((0.06 * sx, -0.24, 0.40)), leg(sx, FRONT_Y, 0.22), leg(sx, FRONT_Y, 0.09), leg(sx, FRONT_Y, 0.03, 0.02)
    toe, fing = paw + Vector((0, -0.04, -0.02)), fpaw + Vector((0, -0.04, -0.02))
    for n, (a, b, p) in {"UpLeg": (hip, knee, "Hips"), "Leg": (knee, hock, "UpLeg"), "Foot": (hock, paw, "Leg"),
                         "ToeBase": (paw, toe, "Foot"), "Arm": (sh, elbow, "Spine1"), "ForeArm": (elbow, wrist, "Arm"),
                         "Hand": (wrist, fpaw, "ForeArm"), "Fingers": (fpaw, fing, "Hand")}.items():
        J[side + n], parent[side + n] = (a, b), (p if p in ("Hips", "Spine1") else side + p)

ad = bpy.data.armatures.new("CatRig"); arm = bpy.data.objects.new("CatRig", ad)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
for n, (h, t) in J.items():
    b = ad.edit_bones.new(n); b.head, b.tail = h, t
for n, p in parent.items():
    if p:
        ad.edit_bones[n].parent = ad.edit_bones[p]
for n in ("Spine", "Spine1", "Neck", "Head", "HeadTop_End", "Tail2", "Tail3", "Tail4"):
    ad.edit_bones[n].use_connect = True
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT'); m.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
dead = [g.name for g in m.vertex_groups if not any(x.group == g.index and x.weight > 0.01 for v in m.data.vertices for x in v.groups)]
print(f"rig_cat: {len(ad.bones)} bones, {len(m.data.vertices) / len(ad.bones):.1f} vertices per bone, {len(dead)} dead")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=dst, use_selection=True)
