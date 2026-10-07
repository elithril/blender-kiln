"""Model, rig and animate the showcase props: a desk lamp and a treasure chest.

    blender --background --factory-startup --python-exit-code 1 --python props.py -- <out_dir>

Each rigid part is weighted 100% to one bone, so parts move as solids. Every rotation's
sign is measured on the rig before it is used (references/animation.md § Rules for
scripted animation, rule 4) — both animations were approved on their first render.
Writes lamp.glb / chest.glb (rest) and lamp_look.glb / chest_open.glb (looping).
"""
import bpy, bmesh, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gallery"))
import studio as S

out = sys.argv[sys.argv.index("--") + 1]


def part(name, mesh_fn, mat, bone):
    mesh_fn(); o = bpy.context.object; o.name = name
    o.data.materials.append(mat); o["bone"] = bone
    return o


def rigid_rig(parts, bones, name):
    """bones: [(name, head, tail, parent)] ; parts carry o['bone']."""
    ad = bpy.data.armatures.new(name); arm = bpy.data.objects.new(name, ad); bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    for n, h, t, p in bones:
        b = ad.edit_bones.new(n); b.head, b.tail = h, t
        if p: b.parent = ad.edit_bones[p]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in parts:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        vg = o.vertex_groups.new(name=o["bone"]); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
    body = bpy.context.object; body.name = name + "_mesh"
    body.parent = arm; body.modifiers.new("Armature", 'ARMATURE').object = arm
    return arm, body


def export(path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True)


# ── desk lamp ───────────────────────────────────────────────────────────────
S.reset()
metal = S.mat("lamp_red", S.srgb("#B8322A"), rough=0.35, metal=0.6)
steel = S.mat("steel", S.srgb("#9AA0A6"), rough=0.3, metal=1.0)
bulb = S.mat("bulb", S.srgb("#FFF4D6"), rough=0.2, emit=S.srgb("#FFE7B0"), emit_str=4.0)
B0, J1, J2, J3 = Vector((0, 0, 0.04)), Vector((0, 0, 0.06)), Vector((0, 0.10, 0.36)), Vector((0, -0.12, 0.58))
parts = [
    part("base", lambda: bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.14, depth=0.04, location=(0, 0, 0.02)), metal, "Base"),
    part("pivot", lambda: bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.035, depth=0.05, location=(0, 0, 0.06)), steel, "Base"),
]
def rod(a, b, r):
    d = b - a; bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r, depth=d.length, location=(a + b) / 2)
    bpy.context.object.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
parts += [part("arm_low", lambda: rod(J1, J2, 0.016), metal, "ArmLow"),
          part("elbow", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.028, location=J2), steel, "ArmLow"),
          part("arm_up", lambda: rod(J2, J3, 0.014), metal, "ArmUp"),
          part("neck", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.024, location=J3), steel, "Head")]
def shade():
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.11, radius2=0.035, depth=0.14, end_fill_type='NOTHING',
                                    location=J3 + Vector((0, -0.07, -0.05)))
    o = bpy.context.object; o.rotation_euler = (math.radians(-60), 0, 0)
    o.modifiers.new("solid", 'SOLIDIFY').thickness = 0.006; bpy.ops.object.modifier_apply(modifier="solid")
parts += [part("shade", shade, metal, "Head"),
          part("bulb", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.035, location=J3 + Vector((0, -0.11, -0.08))), bulb, "Head")]
lamp, _ = rigid_rig(parts, [("Base", B0, J1, None), ("ArmLow", J1, J2, "Base"), ("ArmUp", J2, J3, "ArmLow"),
                            ("Head", J3, J3 + Vector((0, -0.12, -0.07)), "ArmUp")], "Lamp")
export(f"{out}/lamp.glb"); print("MADE lamp")

# ── treasure chest ──────────────────────────────────────────────────────────
S.reset()
wood = S.mat("wood", S.srgb("#7A4A25"), rough=0.7)
iron = S.mat("iron", S.srgb("#3D3F44"), rough=0.45, metal=0.9)
gold = S.mat("gold", S.srgb("#D9A441"), rough=0.3, metal=1.0)
W, D, H = 0.60, 0.40, 0.30
HINGE = Vector((0, D / 2, H))
def box(loc, size):
    bpy.ops.mesh.primitive_cube_add(location=loc); bpy.context.object.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
def lid():
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=D / 2, depth=W, location=(0, 0, H))
    o = bpy.context.object; o.rotation_euler = (0, math.radians(90), 0)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x > 1e-4], context='VERTS')   # half-cylinder, curved top
    bm.to_mesh(o.data); bm.free()
parts = [part("body", lambda: box((0, 0, H / 2), (W, D, H)), wood, "Body")]
for x in (-0.22, 0.22):
    parts.append(part(f"band{x}", lambda x=x: box((x, 0, H / 2), (0.04, D + 0.01, H + 0.005)), iron, "Body"))
parts += [part("lid", lid, wood, "Lid"),
          part("lock", lambda: box((0, -D / 2 - 0.01, H - 0.02), (0.07, 0.03, 0.09)), gold, "Lid")]
for x in (-0.22, 0.22):
    def strap(x=x):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=D / 2 + 0.008, depth=0.04, location=(x, 0, H))
        o = bpy.context.object; o.rotation_euler = (0, math.radians(90), 0)
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x > 1e-4], context='VERTS'); bm.to_mesh(o.data); bm.free()
    parts.append(part(f"strap{x}", strap, iron, "Lid"))
chest, _ = rigid_rig(parts, [("Body", Vector((0, 0, 0)), Vector((0, 0, H)), None),
                             ("Lid", HINGE, HINGE + Vector((0, -D, 0)), "Body")], "Chest")
export(f"{out}/chest.glb"); print("MADE chest")


# ── animation ─────────────────────────────────────────────────────────────
from mathutils import Euler


def load_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=path)
    sc = bpy.context.scene; sc.render.fps = 24
    arm = next(o for o in sc.objects if o.type == 'ARMATURE')
    for p in arm.pose.bones: p.rotation_mode = 'XYZ'
    return sc, arm


def up_sign(arm, bone, axis, probe):
    """+1 if a positive rotation of `bone` about its local `axis` raises `probe`'s tail."""
    pb, pr = arm.pose.bones[bone], arm.pose.bones[probe]
    bpy.context.view_layer.update(); z0 = (arm.matrix_world @ pr.tail).z
    e = [0.0, 0.0, 0.0]; e[axis] = 0.2; pb.rotation_euler = e; bpy.context.view_layer.update()
    z1 = (arm.matrix_world @ pr.tail).z; pb.rotation_euler = (0, 0, 0)
    return 1 if z1 > z0 else -1


def ease_back(x, s=1.70158):          # overshoots then settles: a lid that pops open
    x = max(0.0, min(1.0, x)) - 1; return x * x * ((s + 1) * x + s) + 1


def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def finish(sc, arm, P, name):
    sc.frame_start, sc.frame_end = 0, P - 1
    arm.animation_data.action.name = name
    bpy.ops.export_scene.gltf(filepath=f"{out}/{name}.glb", export_animations=True, export_force_sampling=True)
    print(f"BAKED {name}: {P} frames")


# ── lamp: looks left, peers down, looks right, nods — 4 s loop ──────────────
sc, arm = load_rig(f"{out}/lamp.glb"); PB = arm.pose.bones; arm.animation_data_create()
s_low, s_up, s_head = (up_sign(arm, "ArmLow", 0, "Head"), up_sign(arm, "ArmUp", 0, "Head"), up_sign(arm, "Head", 0, "Head"))
print("SIGNS lamp", s_low, s_up, s_head)
P = 96
for f in range(P):
    n = f / P; w = 2 * math.pi * n
    yaw = 0.7 * math.sin(w)                                   # base turns left then right
    peer = smooth((n - 0.20) / 0.10) * (1 - smooth((n - 0.40) / 0.10))   # leans in to look at something
    nod = math.sin(2 * math.pi * min(1, max(0, (n - 0.70) / 0.15))) * (0.70 <= n <= 0.85)
    PB["Base"].rotation_euler = (0, yaw, 0)
    PB["ArmLow"].rotation_euler = (s_low * (-0.30 * peer + 0.05 * math.sin(2 * w)), 0, 0)
    PB["ArmUp"].rotation_euler = (s_up * (0.35 * peer), 0, 0)
    PB["Head"].rotation_euler = (s_head * (-0.25 * peer + 0.30 * nod + 0.06 * math.sin(3 * w)), 0, 0.25 * math.sin(w + 0.6))
    for b in ("Base", "ArmLow", "ArmUp", "Head"): PB[b].keyframe_insert("rotation_euler", frame=f)
finish(sc, arm, P, "lamp_look")

# ── chest: anticipation, pops open with overshoot, holds, slams shut with a bounce — 3 s loop ──
sc, arm = load_rig(f"{out}/chest.glb"); PB = arm.pose.bones; arm.animation_data_create()
s_lid = up_sign(arm, "Lid", 0, "Lid"); print("SIGN chest", s_lid)
OPEN = math.radians(105)
P = 72
for f in range(P):
    n = f / P
    if n < 0.10:   a = 0.06 * math.sin(math.pi * n / 0.10)                         # lid jiggles: something inside
    elif n < 0.35: a = OPEN * ease_back((n - 0.10) / 0.25)                           # pops open, overshoots
    elif n < 0.60: a = OPEN                                                          # holds
    elif n < 0.72: a = OPEN * (1 - smooth((n - 0.60) / 0.12) ** 2)                   # falls shut, accelerating
    elif n < 0.82: a = 0.10 * math.sin(math.pi * (n - 0.72) / 0.10)                  # bounces once
    else:          a = 0.0
    PB["Lid"].rotation_euler = (s_lid * a, 0, 0); PB["Lid"].keyframe_insert("rotation_euler", frame=f)
    PB["Body"].rotation_euler = (0, 0, 0.015 * math.sin(math.pi * (n - 0.72) / 0.10) if 0.72 <= n < 0.82 else 0)
    PB["Body"].keyframe_insert("rotation_euler", frame=f)
finish(sc, arm, P, "chest_open")
