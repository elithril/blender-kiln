"""SM_Forge, the blender-kiln logo as a low-poly 3D asset, scripted by the kiln pipeline.

Run: blender -b --factory-startup --python-exit-code 1 --python build_forge.py
Writes forge.blend and forge_original.glb here. 1 unit = 1 m, origin at the centre of the base, front -Y.
Reading of the logo: a rough slab of slate stones, two stacked faceted drums, a glowing ember seam
between the drums and the flared lip, a molten pool in the mouth, an orange crystal flame on top.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
rnd = random.Random(7)  # deterministic facets

for ob in list(bpy.data.objects):  # factory scene only (rule 6 exception)
    bpy.data.objects.remove(ob, do_unlink=True)


def mat(name, color, rough=0.85, emit=None, strength=0.0, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


M_STONE = mat("M_Forge_Slate", srgb("343c62"), 0.8)
M_STONE_DARK = mat("M_Forge_SlateDark", srgb("262c4a"), 0.86)
M_EMBER = mat("M_Forge_Ember", srgb("ff4a0a"), 0.6, srgb("ff4a0a"), 2.5)
M_MOLTEN = mat("M_Forge_Molten", srgb("ff9a2a"), 0.4, srgb("ff8a1e"), 3.0)
M_CRYSTAL = mat("M_Forge_Crystal", srgb("ff6a24"), 0.3, srgb("ff5a18"), 1.6)
M_CRYSTAL_TIP = mat("M_Forge_CrystalTip", srgb("ffb04a"), 0.3, srgb("ffa53a"), 2.2)


def link(name, bm, material):
    me = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob


def drum(name, r_out, r_in, z0, h, seg, jitter, material, flare=0.0):
    """A faceted ring (r_in > 0) or solid drum (r_in == 0), each vertex nudged so the facets read hand-cut."""
    bm = bmesh.new()
    rings = []
    for k, (r, z) in enumerate([(r_out, z0), (r_out + flare, z0 + h)]):
        rings.append([bm.verts.new(Vector((
            math.cos(a) * r * (1 + rnd.uniform(-jitter, jitter)),
            math.sin(a) * r * (1 + rnd.uniform(-jitter, jitter)),
            z + rnd.uniform(-jitter, jitter) * h))) for a in (2 * math.pi * i / seg + rnd.uniform(-0.08, 0.08) for i in range(seg))])
    outer_bot, outer_top = rings
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((outer_bot[i], outer_bot[j], outer_top[j], outer_top[i]))
    if r_in > 0:
        inner_top = [bm.verts.new(Vector((math.cos(2 * math.pi * i / seg) * r_in, math.sin(2 * math.pi * i / seg) * r_in, z0 + h * 0.92))) for i in range(seg)]
        inner_bot = [bm.verts.new(Vector((math.cos(2 * math.pi * i / seg) * r_in, math.sin(2 * math.pi * i / seg) * r_in, z0 + h * 0.15))) for i in range(seg)]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((outer_top[i], outer_top[j], inner_top[j], inner_top[i]))
            bm.faces.new((inner_top[i], inner_top[j], inner_bot[j], inner_bot[i]))
            bm.faces.new((inner_bot[i], inner_bot[j], outer_bot[j], outer_bot[i]))
    else:
        bm.faces.new(outer_top)
        bm.faces.new(list(reversed(outer_bot)))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    return link(name, bm, material)


def disc(name, r, z, seg, material, dome=0.0):
    bm = bmesh.new()
    c = bm.verts.new(Vector((0, 0, z + dome)))
    ring = [bm.verts.new(Vector((math.cos(2 * math.pi * i / seg) * r, math.sin(2 * math.pi * i / seg) * r, z))) for i in range(seg)]
    for i in range(seg):
        bm.faces.new((c, ring[i], ring[(i + 1) % seg]))
    return link(name, bm, material)


def slab():
    """The base: a ring of rough slate stones, each its own faceted block."""
    bm = bmesh.new()
    n = 9
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n - 0.05
        r0, r1 = 0.30, 0.62 + rnd.uniform(-0.04, 0.05)
        h = 0.10 + rnd.uniform(-0.015, 0.02)
        pts = []
        for r in (r0, r1):
            for a in (a0, (a0 + a1) / 2, a1):
                pts.append((math.cos(a) * r, math.sin(a) * r))
        bot = [bm.verts.new(Vector((x, y, 0))) for x, y in pts]
        top = [bm.verts.new(Vector((x * 0.97, y * 0.97, h + rnd.uniform(-0.02, 0.02)))) for x, y in pts]
        order = [0, 1, 2, 5, 4, 3]
        bm.faces.new([top[k] for k in order])
        bm.faces.new([bot[k] for k in reversed(order)])
        for a, b in zip(order, order[1:] + order[:1]):
            bm.faces.new((bot[a], bot[b], top[b], top[a]))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    return link("SM_Forge_Base", bm, M_STONE_DARK)


def shard(name, r, h, lean, twist, material, z=0.6, offset=(0, 0)):
    """One faceted crystal shard: 5 sides, a waist, a leaning tip, like the logo's flame."""
    bm = bmesh.new()
    seg = 5
    base = [bm.verts.new(Vector((offset[0] + math.cos(2 * math.pi * i / seg + twist) * r * (1 + rnd.uniform(-0.15, 0.15)),
                                 offset[1] + math.sin(2 * math.pi * i / seg + twist) * r * (1 + rnd.uniform(-0.15, 0.15)), 0))) for i in range(seg)]
    mid = [bm.verts.new(Vector((offset[0] + (v.co.x - offset[0]) * 1.08 + lean[0] * 0.4, offset[1] + (v.co.y - offset[1]) * 1.08 + lean[1] * 0.4,
                                h * 0.42 + rnd.uniform(-0.04, 0.04)))) for v in base]
    tip = bm.verts.new(Vector((offset[0] + lean[0], offset[1] + lean[1], h)))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((base[i], base[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], tip))
    bm.faces.new(list(reversed(base)))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    ob = link(name, bm, material)
    ob.location.z = z
    return ob


def crystal():
    shard("SM_Forge_Flame", 0.20, 0.72, (-0.04, 0.10), 0.3, M_CRYSTAL, z=0.56)
    shard("SM_Forge_FlameLeft", 0.10, 0.36, (-0.10, 0.02), 1.1, M_CRYSTAL_TIP, z=0.56, offset=(-0.16, -0.05))
    shard("SM_Forge_FlameRight", 0.09, 0.30, (0.10, 0.04), 2.0, M_CRYSTAL_TIP, z=0.56, offset=(0.17, -0.02))


slab()
drum("SM_Forge_DrumLow", 0.46, 0, 0.10, 0.18, 11, 0.03, M_STONE, flare=-0.02)
drum("SM_Forge_SeamLow", 0.40, 0, 0.27, 0.05, 14, 0.0, M_EMBER)     # ember glowing through the gap between the drums
drum("SM_Forge_DrumHigh", 0.44, 0, 0.31, 0.15, 11, 0.03, M_STONE, flare=-0.02)
drum("SM_Forge_SeamHigh", 0.39, 0, 0.45, 0.06, 14, 0.0, M_EMBER)    # and between the drums and the lip
drum("SM_Forge_Lip", 0.50, 0.31, 0.50, 0.11, 12, 0.03, M_STONE, flare=0.05)
disc("SM_Forge_Pool", 0.32, 0.565, 12, M_MOLTEN, dome=0.02)       # molten pool in the mouth
crystal()

# rule 10: transforms applied, merged, normals outward, flat shading kept (low-poly facets)
for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ob.select_set(False)
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free()
    for p in ob.data.polygons:
        p.use_smooth = False

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "forge.blend"))
tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == "MESH" for p in o.data.polygons)
zs = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.type == "MESH" for c in o.bound_box]
print(f"STAT tris={tris} height={max(zs) - min(zs):.3f} zmin={min(zs):.3f}")
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "forge_original.glb"), export_format="GLB", export_apply=False, export_yup=True)
print("EXPORTED", os.path.getsize(os.path.join(HERE, "forge_original.glb")))
