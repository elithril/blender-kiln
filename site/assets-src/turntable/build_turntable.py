"""SM_Turntable, scripted by the kiln pipeline (headless Blender 5.2.2, --factory-startup).

Run: blender -b --factory-startup --python-exit-code 1 --python build_turntable.py
Writes turntable.blend, turntable_original.glb and review renders into this folder.
Origin: centre of the base, on the ground. 1 unit = 1 m. Front: -Y.
"""
import math
import os

import bmesh
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
R_DISC, H_DISC = 0.30, 0.03
R_BASE, H_BASE = 0.25, 0.02
SEG = 96
TEX = 1024

# factory scene: Cube, Camera, Light only -> remove the Cube (rule 6 exception), keep nothing else
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)


def cylinder(name, r, h, z0):
    me = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=SEG, radius1=r, radius2=r, depth=h)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, z0 + h / 2))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bevel(ob, width, segments):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width, m.segments, m.limit_method = width, segments, "ANGLE"
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)  # real geometry, so rule 18 holds


disc = cylinder("SM_Turntable_Disc", R_DISC, H_DISC, H_BASE)
base = cylinder("SM_Turntable_Base", R_BASE, H_BASE, 0.0)
bevel(disc, 0.003, 2)
bevel(base, 0.002, 1)

# ---- top face texture: scanned rubber grain (Poly Haven rubberized_track, CC0), tinted charcoal,
#      degree ring painted on: a tick every 5 deg, long every 30 deg, an orange index at 0 deg (front, -Y)


def load(name):
    img = bpy.data.images.load(os.path.join(WORK, name))
    img.colorspace_settings.name = "Non-Color"
    a = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], img.channels)
    return a[..., :3]


def tile(a, n):  # n x n repeats, back to TEX px (fine grain on a 60 cm disc)
    t = np.tile(a, (n, n, 1))
    step = t.shape[0] // TEX
    return t[::step, ::step][:TEX, :TEX]


diff = tile(load("rubber_Diffuse.jpg"), 3)
rough = tile(load("rubber_Rough.jpg"), 3)
nor = tile(load("rubber_nor_gl.jpg"), 3)

lum = diff.mean(axis=2)
lum = (lum - lum.mean()) / (lum.std() + 1e-6)
charcoal = np.array([0.045, 0.045, 0.047])          # linear
col = charcoal[None, None, :] * (1 + 0.18 * lum[..., None])

yy, xx = np.mgrid[0:TEX, 0:TEX]
u = (xx + 0.5) / TEX * 2 - 1                         # -1..1 across the top face
v = (yy + 0.5) / TEX * 2 - 1
rr = np.hypot(u, v)
ang = (np.degrees(np.arctan2(u, -v)) + 360) % 360    # 0 deg at -Y (front)

grey = np.array([0.42, 0.42, 0.42])
for d in range(0, 360, 5):
    long = d % 30 == 0
    r0 = 0.86 if long else 0.905
    da = np.abs(((ang - d) + 180) % 360 - 180) * np.pi / 180 * rr  # arc distance, in disc radii
    w = 0.0042 if long else 0.0026
    m = (da < w) & (rr > r0) & (rr < 0.955)
    col[m] = grey
    rough[m] = 0.55
idx = (np.abs(((ang - 0) + 180) % 360 - 180) * np.pi / 180 * rr < 0.009) & (rr > 0.78) & (rr < 0.955)
orange = np.array([0.672, 0.205, 0.025])             # #d67e2c in linear
col[idx] = orange
ring = (np.abs(rr - 0.965) < 0.0022)
col[ring] = grey * 0.7


def image(name, rgb, srgb):
    img = bpy.data.images.new(name, TEX, TEX, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    px = np.ones((TEX, TEX, 4), dtype=np.float32)
    px[..., :3] = np.clip(rgb, 0, 1) if not srgb else np.clip(rgb, 0, 1) ** (1 / 2.2)  # linear -> sRGB bytes
    img.pixels[:] = px.ravel()
    path = os.path.join(WORK, f"{name}.png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    img.filepath = path
    return img


img_col = image("T_Turntable_Top_BaseColor", col, True)
img_rough = image("T_Turntable_Top_Roughness", np.repeat(rough.mean(axis=2, keepdims=True), 3, 2) * 0.55 + 0.38, False)
img_nor = image("T_Turntable_Top_Normal", nor, False)


def principled(name, color, metal, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = roughness
    return mat, bsdf


rubber, b = principled("M_Turntable_Rubber", charcoal, 0.0, 0.8)
nt = rubber.node_tree


def tex(img):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = img
    return n


t_col, t_rough, t_nor = tex(img_col), tex(img_rough), tex(img_nor)
nt.links.new(t_col.outputs["Color"], b.inputs["Base Color"])
sep = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(t_rough.outputs["Color"], sep.inputs["Color"])
nt.links.new(sep.outputs["Red"], b.inputs["Roughness"])
nm = nt.nodes.new("ShaderNodeNormalMap")
nm.inputs["Strength"].default_value = 0.6
nt.links.new(t_nor.outputs["Color"], nm.inputs["Color"])
nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])

alu, _ = principled("M_Turntable_Aluminium", (0.62, 0.62, 0.63), 1.0, 0.32)
base_mat, _ = principled("M_Turntable_Base", (0.018, 0.018, 0.019), 0.0, 0.55)

# disc: top faces -> rubber (planar UV over the disc), everything else -> aluminium
disc.data.materials.append(alu)
disc.data.materials.append(rubber)
base.data.materials.append(base_mat)
bm = bmesh.new()
bm.from_mesh(disc.data)
uv = bm.loops.layers.uv.verify()
top_z = max(v.co.z for v in bm.verts)
for f in bm.faces:
    is_top = f.normal.z > 0.99 and abs(f.calc_center_median().z - top_z) < 1e-4
    f.material_index = 1 if is_top else 0
    for lp in f.loops:
        lp[uv].uv = (lp.vert.co.x / (2 * R_DISC) + 0.5, lp.vert.co.y / (2 * R_DISC) + 0.5)
bm.to_mesh(disc.data)
bm.free()

# rule 10: transforms applied (none set), merge by distance, normals consistent
for ob in (disc, base):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.shade_smooth()
    ob.data.set_sharp_from_angle(angle=math.radians(35))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "turntable.blend"))

# stats for the log
for ob in (disc, base):
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    bb = [ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box]
    dims = [max(c[i] for c in bb) - min(c[i] for c in bb) for i in range(3)]
    print(f"STAT {ob.name} tris={tris} dims={[round(d, 4) for d in dims]} zmin={min(c.z for c in bb):.4f}")

bpy.ops.export_scene.gltf(
    filepath=os.path.join(HERE, "turntable_original.glb"),
    export_format="GLB", export_apply=False, export_yup=True,
)
print("EXPORTED", os.path.getsize(os.path.join(HERE, "turntable_original.glb")))
