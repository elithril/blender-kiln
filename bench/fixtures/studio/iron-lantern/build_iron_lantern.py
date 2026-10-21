# Iron lantern — scripted build (kiln). Run inside Blender: exec(open(path).read())
# 1 unit = 1 m, origin at centre of base, front -Y, up +Z.
import bpy, bmesh, math
from mathutils import Matrix, Vector

NAME = "SM_IronLantern"

# --- rule 6 exception: Blender's untouched factory scene → remove the Cube only
cube = bpy.data.objects.get("Cube")
if cube and cube.type == 'MESH' and len(cube.data.polygons) == 6 and not bpy.data.filepath:
    bpy.data.objects.remove(cube, do_unlink=True)
    print("removed factory Cube")

# --- rerun safety: clear only what this script made
for o in [o for o in bpy.data.objects if o.name.startswith(NAME)]:
    bpy.data.objects.remove(o, do_unlink=True)
for m in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(m)

coll = bpy.context.scene.collection

# --- materials (Principled values only; looked up by type, not name)
def material(name, color, metallic=0.0, rough=0.5, transmission=0.0, ior=1.45,
             emission=None, strength=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    mat.diffuse_color = (*color, 1.0)
    return mat

M_IRON  = material("M_Metal_WroughtIron", (0.055, 0.050, 0.046), metallic=0.85, rough=0.55)
M_GLASS = material("M_Glass_Amber", (1.0, 0.70, 0.32), rough=0.05, transmission=1.0, ior=1.5)
M_WAX   = material("M_Wax_Candle", (0.90, 0.84, 0.68), rough=0.6)
M_FLAME = material("M_Emissive_Flame", (1.0, 0.62, 0.18), rough=0.5,
                   emission=(1.0, 0.55, 0.15), strength=6.0)

# --- bmesh helpers: each returns a bmesh already placed in object space
def bm_box(sx, sy, sz, loc, bevel=0.0, seg=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=seg,
                        affect='EDGES', profile=0.5, clamp_overlap=True)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return bm

def bm_cone(r1, r2, depth, segs, z0, rot=0.0, cap_top=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=r1, radius2=r2, depth=depth)
    if rot:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot, 3, 'Z'))
    bmesh.ops.translate(bm, vec=(0, 0, z0 + depth / 2), verts=bm.verts)
    return bm

def bm_sphere(r, loc, scale=(1, 1, 1), u=12, v=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return bm

def bm_torus(R, r, loc, segs=24, rsegs=8):
    """Torus standing in the XZ plane (a hanging ring seen from the front)."""
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ring = []
        for j in range(rsegs):
            b = 2 * math.pi * j / rsegs
            d = R + r * math.cos(b)
            ring.append(bm.verts.new((d * math.cos(a), r * math.sin(b), d * math.sin(a))))
        rings.append(ring)
    for i in range(segs):
        for j in range(rsegs):
            a, b = rings[i], rings[(i + 1) % segs]
            bm.faces.new((a[j], b[j], b[(j + 1) % rsegs], a[(j + 1) % rsegs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return bm

def make(name, bms, mat, smooth_angle=35.0, parent=None):
    """Join bmeshes into one object, one material, smooth by angle."""
    me = bpy.data.meshes.new(name + "_Mesh")
    out = bmesh.new()
    for bm in bms:
        tmp = bpy.data.meshes.new("_tmp"); bm.to_mesh(tmp); bm.free()
        out.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    out.to_mesh(me); out.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    me.materials.append(mat)
    # smooth by angle, sharp edges kept (no modifier → nothing lost at export)
    for p in me.polygons:
        p.use_smooth = True
    bm = bmesh.new(); bm.from_mesh(me)
    lim = math.radians(smooth_angle)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > lim:
            e.smooth = False
    bm.to_mesh(me); bm.free()
    if parent:
        ob.parent = parent
    return ob

# --- dimensions (m)
W      = 0.20    # base tray width
T_BASE = 0.025   # tray thickness
H_TOP  = 0.275   # top of the cage frame
P      = 0.088   # post centre offset from axis
PS     = 0.016   # post section
G      = 0.081   # glass plane offset

root = bpy.data.objects.new(NAME, None)
root.empty_display_type = 'PLAIN_AXES'; root.empty_display_size = 0.1
coll.objects.link(root)

# Base tray + small lip ring + candle dish
base = [bm_box(W, W, T_BASE, (0, 0, T_BASE / 2), bevel=0.005, seg=2),
        bm_box(W - 0.03, W - 0.03, 0.006, (0, 0, -0.003 + 0.0), bevel=0.002, seg=1),
        bm_cone(0.042, 0.040, 0.008, 16, T_BASE),
        bm_cone(0.026, 0.026, 0.010, 12, T_BASE + 0.008)]
# the lip ring under the tray would sit below the origin: lift everything 6 mm instead
for bm in base:
    bmesh.ops.translate(bm, vec=(0, 0, 0.006), verts=bm.verts)
LIFT = 0.006
base_ob = make(NAME + "_Base", base, M_IRON, parent=root)

# Frame: 4 posts, bottom + top bands, one cross per face
z0, z1 = T_BASE + LIFT, H_TOP + LIFT
frame = []
for sx in (-1, 1):
    for sy in (-1, 1):
        frame.append(bm_box(PS, PS, z1 - z0 + 0.004, (sx * P, sy * P, (z0 + z1) / 2), bevel=0.003, seg=2))
BAND = 0.012
for zc in (z0 + 0.010, z1 - 0.010):
    for s in (-1, 1):
        frame.append(bm_box(2 * P, BAND * 0.8, BAND, (0, s * P, zc), bevel=0.002, seg=1))
        frame.append(bm_box(BAND * 0.8, 2 * P, BAND, (s * P, 0, zc), bevel=0.002, seg=1))
zm = (z0 + z1) / 2
BAR = 0.008
for s in (-1, 1):
    frame.append(bm_box(BAR, BAR, z1 - z0 - 0.02, (0, s * P, zm), bevel=0.0015, seg=1))
    frame.append(bm_box(BAR, BAR, z1 - z0 - 0.02, (s * P, 0, zm), bevel=0.0015, seg=1))
    frame.append(bm_box(2 * P, BAR, BAR, (0, s * P, zm), bevel=0.0015, seg=1))
    frame.append(bm_box(BAR, 2 * P, BAR, (s * P, 0, zm), bevel=0.0015, seg=1))
frame_ob = make(NAME + "_Frame", frame, M_IRON, parent=root)

# Glass: 4 amber panes just inside the bars
gh = z1 - z0 - 0.024
glass = []
for s in (-1, 1):
    glass.append(bm_box(2 * G, 0.003, gh, (0, s * G, zm)))
    glass.append(bm_box(0.003, 2 * G - 0.004, gh, (s * G, 0, zm)))
glass_ob = make(NAME + "_Glass", glass, M_GLASS, parent=root)

# Roof: flared square frustum, eave plate, chimney, cap, corner finials
R_EAVE = 0.128  # half-width of the roof at the eaves
roof = [bm_box(2 * R_EAVE, 2 * R_EAVE, 0.010, (0, 0, z1 + 0.005), bevel=0.003, seg=1),
        bm_cone(R_EAVE * math.sqrt(2) * 0.97, 0.034 * math.sqrt(2), 0.085, 4, z1 + 0.010, rot=math.pi / 4),
        bm_cone(0.030, 0.030, 0.040, 12, z1 + 0.085),
        bm_cone(0.046, 0.044, 0.008, 12, z1 + 0.120),
        bm_cone(0.044, 0.004, 0.034, 12, z1 + 0.124)]  # overlaps the rim: coincident rims fuse on weld
for sx in (-1, 1):
    for sy in (-1, 1):
        roof.append(bm_sphere(0.011, (sx * (R_EAVE - 0.006), sy * (R_EAVE - 0.006), z1 + 0.010), u=10, v=6))
roof_ob = make(NAME + "_Roof", roof, M_IRON, parent=root)

# Hanging ring: knob through the cap tip, ring standing in XZ
cap_tip = z1 + 0.158
RING_R, RING_T = 0.036, 0.007
ring = [bm_cone(0.009, 0.007, 0.016, 10, cap_tip - 0.010),
        bm_torus(RING_R, RING_T, (0, 0, cap_tip + 0.004 + RING_R), segs=24, rsegs=8)]
ring_ob = make(NAME + "_Ring", ring, M_IRON, smooth_angle=60, parent=root)

# Candle + flame
cz = T_BASE + LIFT + 0.018
candle_ob = make(NAME + "_Candle", [bm_cone(0.022, 0.021, 0.075, 16, cz),
                                    bm_cone(0.0015, 0.0015, 0.010, 6, cz + 0.075)],
                 M_WAX, parent=root)
flame_ob = make(NAME + "_Flame", [bm_sphere(0.010, (0, 0, cz + 0.095), scale=(1, 1, 2.0), u=12, v=8)],
                M_FLAME, smooth_angle=80, parent=root)

parts = [o for o in coll.objects if o.name.startswith(NAME) and o.type == 'MESH']
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in parts)
ws = [o.matrix_world @ v.co for o in parts for v in o.data.vertices]
mn = Vector((min(v.x for v in ws), min(v.y for v in ws), min(v.z for v in ws)))
mx = Vector((max(v.x for v in ws), max(v.y for v in ws), max(v.z for v in ws)))
print("objects:", sorted(o.name for o in coll.objects))
print(f"parts {len(parts)}, tris {tris}, size {mx.x-mn.x:.3f} x {mx.y-mn.y:.3f} x {mx.z-mn.z:.3f} m, zmin {mn.z:.4f}")
