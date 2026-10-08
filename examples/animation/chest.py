"""Model, rig and animate the showcase treasure chest.

    blender --background --factory-startup --python-exit-code 1 --python chest.py -- <out_dir>

Planks, a barrel lid of staves with closed ends, iron corners, bands, rivets, handles, a lock
and a hasp, and a heap of gold inside. Textured with two Poly Haven CC0 scans (rough_wood,
rusty_metal_04), downloaded once into <out_dir>/tex. One bone per rigid part (Body, Lid, Hasp),
each weighted 100% so parts move as solids; every rotation's sign is measured on the rig before
it is used (references/animation.md, rule 4); an exact 96-frame loop (rule 5).
Writes chest.blend, chest.glb (rest) and chest_open.glb (looping).
"""
import json
import math
import os
import random
import sys
import urllib.request

import bmesh
import bpy
from mathutils import Vector

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1])  # absolute: a relative image path breaks once the .blend is saved
TEX = os.path.join(OUT, "tex")
os.makedirs(TEX, exist_ok=True)
for asset in ("rough_wood", "rusty_metal_04"):  # Poly Haven, CC0: fetched, not shipped in the repo
    files = None
    for m in ("Diffuse", "Rough", "nor_gl"):
        dst = os.path.join(TEX, f"{asset}_{m}.jpg")
        if os.path.exists(dst):
            continue
        if files is None:
            req = urllib.request.Request(f"https://api.polyhaven.com/files/{asset}", headers={"User-Agent": "blender-kiln"})
            files = json.load(urllib.request.urlopen(req, timeout=30))
        req = urllib.request.Request(files[m]["1k"]["jpg"]["url"], headers={"User-Agent": "blender-kiln"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
            f.write(r.read())
for ob in list(bpy.data.objects):  # factory scene only (rule 6 exception)
    bpy.data.objects.remove(ob, do_unlink=True)

W, D, H = 0.62, 0.40, 0.30           # body outside
T = 0.022                            # board thickness
LR = D / 2 + 0.006                   # lid radius (barrel lid)
HINGE = Vector((0, D / 2, H))


# ---------- materials: scans, box-projected ----------
def scan_mat(name, base, tint=(1, 1, 1), metal=0.0, rough_mul=1.0, scale=2.0, turn=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale)
    mp.inputs["Rotation"].default_value = (0, 0, turn)  # grain along the boards
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])

    def img(suffix, color):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(TEX, f"{base}_{suffix}.jpg"))
        n.image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n
    c, r, nn = img("Diffuse", True), img("Rough", False), img("nor_gl", False)
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(c.outputs["Color"], mix.inputs["A"]); mix.inputs["B"].default_value = (*tint, 1)
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    nt.links.new(r.outputs["Color"], bsdf.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 1.0
    nt.links.new(nn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = metal
    return m


WOOD = scan_mat("M_Chest_Wood", "rough_wood", tint=(0.66, 0.40, 0.22), scale=1.6, turn=math.pi / 2)
IRON = scan_mat("M_Chest_Iron", "rusty_metal_04", tint=(0.55, 0.55, 0.58), metal=0.85, scale=3.0)
GOLD = bpy.data.materials.new("M_Chest_Gold"); GOLD.use_nodes = True
g = next(n for n in GOLD.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
g.inputs["Base Color"].default_value = (0.86, 0.55, 0.16, 1); g.inputs["Metallic"].default_value = 1.0; g.inputs["Roughness"].default_value = 0.34
g.inputs["Emission Color"].default_value = (1.0, 0.55, 0.12, 1); g.inputs["Emission Strength"].default_value = 0.08  # a hint of glow: more and the heap burns out to a flat disc under studio light
DARK = bpy.data.materials.new("M_Chest_Inside"); DARK.use_nodes = True
dk = next(n for n in DARK.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
dk.inputs["Base Color"].default_value = (0.05, 0.03, 0.02, 1); dk.inputs["Roughness"].default_value = 0.95

parts = []


def finish(ob, mat, bone, bevel=0.0):
    ob.data.materials.append(mat)
    if bevel:
        mod = ob.modifiers.new("Bevel", "BEVEL"); mod.width = bevel; mod.segments = 2; mod.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier=mod.name)
    ob["bone"] = bone
    parts.append(ob)
    return ob


def cube(name, loc, size, mat, bone, bevel=0.003, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    ob = bpy.context.object; ob.name = name; ob.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(ob, mat, bone, bevel)


def cyl(name, loc, r, depth, mat, bone, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    ob = bpy.context.object; ob.name = name
    return finish(ob, mat, bone, 0.0)


def sphere(name, loc, r, mat, bone):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=5, radius=r, location=loc)
    ob = bpy.context.object; ob.name = name
    return finish(ob, mat, bone)


# ---------- body: boards, hollow, with a floor ----------
nb = 4
bh = H / nb
for i in range(nb):  # front and back walls, horizontal boards with small gaps
    z = bh * (i + 0.5)
    for side, y in (("Front", -D / 2 + T / 2), ("Back", D / 2 - T / 2)):
        cube(f"SM_Chest_{side}Board_{i + 1}", (0, y, z), (W, T, bh - 0.003), WOOD, "Body", 0.004)
for i in range(nb):  # end walls
    z = bh * (i + 0.5)
    for side, x in (("Left", -W / 2 + T / 2), ("Right", W / 2 - T / 2)):
        cube(f"SM_Chest_{side}Board_{i + 1}", (x, 0, z), (T, D - 2 * T, bh - 0.003), WOOD, "Body", 0.004)
cube("SM_Chest_Floor", (0, 0, T / 2), (W - 2 * T, D - 2 * T, T), WOOD, "Body", 0.0)
cube("SM_Chest_Inside", (0, 0, H * 0.62), (W - 2 * T - 0.002, D - 2 * T - 0.002, 0.004), DARK, "Body", 0.0)

# treasure inside: a heap of coins and a few loose ones (seen when the lid is open)
rnd = random.Random(3)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=(0, 0, H * 0.62))
mound = bpy.context.object; mound.name = "SM_Chest_GoldMound"; mound.scale = (W / 2 - T - 0.01, D / 2 - T - 0.01, 0.075)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
finish(mound, GOLD, "Body")
for k in range(72):
    a = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(0, 0.17) ** 0.8
    x, y = math.cos(a) * rr * 1.25, math.sin(a) * rr * 0.62
    hz = H * 0.62 + 0.075 * math.sqrt(max(0.0, 1 - (x / (W / 2 - T)) ** 2 - (y / (D / 2 - T)) ** 2)) + rnd.uniform(0, 0.006)  # the heap crests just above the rim
    cyl(f"SM_Chest_Coin_{k + 1:02d}", (x, y, hz), 0.016, 0.003, GOLD, "Body",
        rot=(rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 0), verts=12)

# iron: corner brackets, two bands round the body, rivets, side handles
for x in (-W / 2, W / 2):
    for y in (-D / 2, D / 2):
        sx = 1 if x > 0 else -1; sy = 1 if y > 0 else -1
        cube(f"SM_Chest_Corner_{'R' if sx > 0 else 'L'}{'B' if sy > 0 else 'F'}", (x - sx * 0.018, y - sy * 0.018, H / 2),
             (0.05, 0.05, H + 0.004), IRON, "Body", 0.004)
for i, x in enumerate((-0.17, 0.17)):
    cube(f"SM_Chest_BandFront_{i + 1}", (x, -D / 2 - 0.004, H / 2), (0.045, 0.008, H + 0.004), IRON, "Body", 0.002)
    cube(f"SM_Chest_BandBack_{i + 1}", (x, D / 2 + 0.004, H / 2), (0.045, 0.008, H + 0.004), IRON, "Body", 0.002)
    for z in (0.04, H / 2, H - 0.04):
        sphere(f"SM_Chest_Rivet_F{i}{z:.2f}", (x, -D / 2 - 0.01, z), 0.006, IRON, "Body")
cube("SM_Chest_BandBottom", (0, 0, 0.012), (W + 0.012, D + 0.012, 0.024), IRON, "Body", 0.003)
for x in (-W / 2 - 0.012, W / 2 + 0.012):
    sx = 1 if x > 0 else -1
    bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.006, major_segments=20, minor_segments=8,
                                     location=(x + sx * 0.012, 0, H * 0.62), rotation=(0, math.radians(90), 0))
    h = bpy.context.object; h.name = f"SM_Chest_Handle_{'R' if sx > 0 else 'L'}"; h.scale = (1, 1, 1)
    bm = bmesh.new(); bm.from_mesh(h.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < -0.005], context="VERTS")  # half ring, hanging
    bm.to_mesh(h.data); bm.free()
    finish(h, IRON, "Body")
    cube(f"SM_Chest_HandlePlate_{'R' if sx > 0 else 'L'}", (x + sx * 0.002, 0, H * 0.66), (0.006, 0.11, 0.05), IRON, "Body", 0.002)
cube("SM_Chest_LockPlate", (0, -D / 2 - 0.007, H - 0.05), (0.09, 0.008, 0.08), IRON, "Body", 0.003)
cyl("SM_Chest_Keyhole", (0, -D / 2 - 0.012, H - 0.06), 0.008, 0.004, DARK, "Body", rot=(math.radians(90), 0, 0), verts=12)


# ---------- lid: a barrel of staves, iron straps, the hasp ----------
nst = 7
for k in range(nst):  # staves around the half barrel
    a0 = math.pi * k / nst + 0.004; a1 = math.pi * (k + 1) / nst - 0.004
    am = (a0 + a1) / 2
    width = 2 * LR * math.sin((a1 - a0) / 2)
    cy = -math.cos(am) * (LR - T / 2); cz = H + math.sin(am) * (LR - T / 2)
    cube(f"SM_Chest_LidStave_{k + 1}", (0, cy, cz), (W, width, T), WOOD, "Lid", 0.003, rot=(math.pi / 2 - am, 0, 0))
for x, side in ((-W / 2 + T / 2, "L"), (W / 2 - T / 2, "R")):  # lid ends: closed half discs, built as such
    me = bpy.data.meshes.new(f"SM_Chest_LidEnd_{side}"); bm = bmesh.new()
    arc = [(0, -math.cos(math.pi * k / 24) * (LR - 0.004), H + math.sin(math.pi * k / 24) * (LR - 0.004)) for k in range(25)]
    face = bm.faces.new([bm.verts.new((x - T / 2, y, z)) for _, y, z in arc])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(T, 0, 0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    e = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(e)
    finish(e, WOOD, "Lid")
for i, x in enumerate((-0.17, 0.17)):  # straps following the barrel
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=LR + 0.006, depth=0.045, location=(x, 0, H), rotation=(0, math.radians(90), 0))
    s = bpy.context.object; s.name = f"SM_Chest_LidStrap_{i + 1}"
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bm = bmesh.new(); bm.from_mesh(s.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.x) > 0.9], context="FACES")
    inner = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    bmesh.ops.translate(bm, vec=(0, 0, 0), verts=[v for v in inner["geom"] if isinstance(v, bmesh.types.BMVert)])
    bm.to_mesh(s.data); bm.free()
    sol = s.modifiers.new("Solidify", "SOLIDIFY"); sol.thickness = 0.006
    bpy.context.view_layer.objects.active = s; bpy.ops.object.modifier_apply(modifier=sol.name)
    finish(s, IRON, "Lid")
    for k in range(5):
        am = math.pi * (k + 0.5) / 5
        sphere(f"SM_Chest_LidRivet_{i}{k}", (x, -math.cos(am) * (LR + 0.012), H + math.sin(am) * (LR + 0.012)), 0.006, IRON, "Lid")
cube("SM_Chest_LidRim", (0, -D / 2 - 0.004, H + 0.012), (W + 0.01, 0.012, 0.026), IRON, "Lid", 0.003)
hasp = cube("SM_Chest_Hasp", (0, -D / 2 - 0.016, H - 0.02), (0.05, 0.008, 0.075), IRON, "Hasp", 0.003)
sphere("SM_Chest_HaspRivet", (0, -D / 2 - 0.022, H - 0.035), 0.007, GOLD, "Hasp")
for x in (-0.2, 0.2):  # back hinges
    cyl(f"SM_Chest_Hinge_{'L' if x < 0 else 'R'}", (x, D / 2 + 0.01, H), 0.012, 0.07, IRON, "Body", rot=(0, math.radians(90), 0), verts=12)

# ---------- UVs: box projection per part, so the scans keep their scale ----------
for ob in parts:
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=0.6, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")

# ---------- rig: one bone per rigid group, 100% weights (rigid parts move as solids) ----------
ad = bpy.data.armatures.new("SK_Chest"); arm = bpy.data.objects.new("SK_Chest", ad); bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
b = ad.edit_bones.new("Body"); b.head, b.tail = (0, 0, 0), (0, 0, H)
l = ad.edit_bones.new("Lid"); l.head, l.tail = HINGE, HINGE + Vector((0, -D, 0)); l.parent = b
hp = ad.edit_bones.new("Hasp"); hp.head = Vector((0, -D / 2 - 0.016, H + 0.015)); hp.tail = hp.head + Vector((0, 0, -0.08)); hp.parent = l
bpy.ops.object.mode_set(mode="OBJECT")
for ob in parts:
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vg = ob.vertex_groups.new(name=ob["bone"]); vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
bpy.ops.object.select_all(action="DESELECT")
for ob in parts: ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
mesh = bpy.context.object; mesh.name = "SM_Chest"; mesh.data.name = "SM_Chest_Mesh"
# rule 10: merge by distance, normals outward, flat-ish shading kept on boards
bm = bmesh.new(); bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh.data); bm.free()
mesh.data.shade_smooth(); mesh.data.set_sharp_from_angle(angle=math.radians(40))
mesh.parent = arm; mesh.modifiers.new("Armature", "ARMATURE").object = arm

tris = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
print(f"STAT tris={tris} dims={[round(v, 3) for v in mesh.dimensions]}")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "chest.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "chest.glb"), export_format="GLB", export_apply=False)


# ---------- animation: measured signs, anticipation, pop with overshoot, glow, slam, bounce ----------
for p in arm.pose.bones: p.rotation_mode = "XYZ"


def up_sign(bone, probe):
    pb, pr = arm.pose.bones[bone], arm.pose.bones[probe]
    bpy.context.view_layer.update(); z0 = (arm.matrix_world @ pr.tail).z
    pb.rotation_euler = (0.2, 0, 0); bpy.context.view_layer.update()
    z1 = (arm.matrix_world @ pr.tail).z; pb.rotation_euler = (0, 0, 0)
    return 1 if z1 > z0 else -1


def out_sign(bone):  # +1 if a positive X rotation swings the hasp's tail outward (towards -Y)
    pb = arm.pose.bones[bone]
    bpy.context.view_layer.update(); y0 = (arm.matrix_world @ pb.tail).y
    pb.rotation_euler = (0.2, 0, 0); bpy.context.view_layer.update()
    y1 = (arm.matrix_world @ pb.tail).y; pb.rotation_euler = (0, 0, 0)
    return 1 if y1 < y0 else -1


s_lid, s_hasp = up_sign("Lid", "Lid"), out_sign("Hasp")
print("SIGNS", s_lid, s_hasp)


def ease_back(x, s=2.2):
    x = max(0.0, min(1.0, x)) - 1; return x * x * ((s + 1) * x + s) + 1


def sm(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


OPEN = math.radians(108)
P = 96                                   # 4 s at 24 fps, exact loop: frames 0..P-1 (rule 5)
sc = bpy.context.scene; sc.render.fps = 24; sc.frame_start, sc.frame_end = 0, P - 1
arm.animation_data_create()
PB = arm.pose.bones
for f in range(P):
    n = f / P
    hasp = 0.0; body_sq = 0.0
    if n < 0.06:   lid = 0.0; hasp = 1.4 * sm(n / 0.06)                                  # hasp flips up
    elif n < 0.16: lid = 0.05 * math.sin(math.pi * (n - 0.06) / 0.05) * (1 if n < 0.11 else -0.5); hasp = 1.4  # lid rattles: something inside
    elif n < 0.40: lid = OPEN * ease_back((n - 0.16) / 0.24); hasp = 1.4 * (1 - sm((n - 0.16) / 0.1)) + 0.2  # pops open, overshoots
    elif n < 0.66: lid = OPEN + 0.02 * math.sin(2 * math.pi * (n - 0.40) / 0.26); hasp = 0.2              # held, breathing
    elif n < 0.76: lid = OPEN * (1 - sm((n - 0.66) / 0.10) ** 2); hasp = 0.2 + 0.3 * sm((n - 0.66) / 0.1) # falls shut, accelerating
    elif n < 0.86: lid = 0.09 * math.sin(math.pi * (n - 0.76) / 0.10); body_sq = math.sin(math.pi * (n - 0.76) / 0.10); hasp = 0.5 * (1 - sm((n - 0.76) / 0.1))  # bounce
    else:          lid = 0.0; hasp = 0.0
    PB["Lid"].rotation_euler = (s_lid * lid, 0, 0); PB["Lid"].keyframe_insert("rotation_euler", frame=f)
    PB["Hasp"].rotation_euler = (s_hasp * hasp, 0, 0); PB["Hasp"].keyframe_insert("rotation_euler", frame=f)
    PB["Body"].scale = (1 + 0.02 * body_sq, 1 + 0.02 * body_sq, 1 - 0.035 * body_sq); PB["Body"].keyframe_insert("scale", frame=f)
arm.animation_data.action.name = "chest_open"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "chest.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "chest_open.glb"), export_format="GLB",
                          export_apply=False, export_animations=True, export_force_sampling=True)
# fail loudly if the scans did not make it into the file: glTF export drops an unresolved image silently
with open(os.path.join(OUT, "chest_open.glb"), "rb") as f:
    f.seek(12); n = int.from_bytes(f.read(4), "little"); f.read(4); gltf = json.loads(f.read(n))
sizes = [i.size[0] for i in bpy.data.images if i.source == "FILE"]
assert len(gltf.get("images", [])) >= 6 and min(sizes) >= 512, f"textures lost in export: {len(gltf.get('images', []))} images, sizes {sizes}"
print("EXPORTED", os.path.getsize(os.path.join(OUT, "chest_open.glb")))
