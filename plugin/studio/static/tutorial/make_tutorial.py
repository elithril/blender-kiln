"""Build Kiln Studio's tutorial models: the barrel after Claude's (simulated) change, and a
lantern in four build stages. blender -b --factory-startup --python make_tutorial.py -- OUT"""
import sys, math, bpy, bmesh
from mathutils import Vector
OUT = sys.argv[sys.argv.index("--") + 1]
SRC = sys.argv[sys.argv.index("--") + 2]

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def export(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True)

# ── the barrel, after: iron hoops 1.8x taller and 8 mm proud ──
clear()
bpy.ops.import_scene.gltf(filepath=SRC)
ob = next(o for o in bpy.data.objects if o.type == "MESH")
iron = next(i for i, m in enumerate(ob.data.materials) if "Iron" in m.name)
bm = bmesh.new(); bm.from_mesh(ob.data)
verts = {v for f in bm.faces if f.material_index == iron for v in f.verts}
zs = sorted(v.co.z for v in verts)
clusters, cur = [], [zs[0]]
for z in zs[1:]:
    (cur.append(z) if z - cur[-1] < 0.03 else (clusters.append(cur), cur := [z]))
clusters.append(cur)
centers = [(min(c) + max(c)) / 2 for c in clusters]
for v in verts:
    c = min(centers, key=lambda x: abs(x - v.co.z))
    v.co.z = c + (v.co.z - c) * 2.6
    r = Vector((v.co.x, v.co.y, 0))
    if r.length > 1e-6:
        v.co += r.normalized() * 0.015
bm.to_mesh(ob.data); bm.free()
export(f"{OUT}/barrel_after.glb", [ob])

# ── the lantern, in four stages ──
def mat(name, rgb, metal=0.0, rough=0.6, alpha=1.0, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED" if hasattr(m, "surface_render_method") else m.surface_render_method
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 4
    return m

CLAY = None
def part(kind, name, loc, scale, mats_key, **kw):
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    elif kind == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(vertices=kw.get("v", 16), radius=0.5, depth=1, location=loc)
    elif kind == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.5, radius2=0.08, depth=1, location=loc, rotation=(0, 0, math.pi / 4))
    elif kind == "torus":
        bpy.ops.mesh.primitive_torus_add(major_radius=kw["R"], minor_radius=kw["r"], location=loc, rotation=(math.pi / 2, 0, 0))
    o = bpy.context.object; o.name = name; o.scale = scale; o["mk"] = mats_key
    bpy.ops.object.transform_apply(scale=True)
    return o

def lantern(stage):
    clear()
    objs = []
    H = 0.30
    if stage == 0:   # blockout: body, roof, ring
        objs += [part("cube", "Body", (0, 0, H / 2), (0.18, 0.18, H), "iron"),
                 part("cone", "Roof", (0, 0, H + 0.05), (0.27, 0.27, 0.10), "iron"),
                 part("torus", "Ring", (0, 0, H + 0.14), (1, 1, 1), "iron", R=0.035, r=0.008)]
    else:
        objs += [part("cube", "Base", (0, 0, 0.012), (0.22, 0.22, 0.024), "iron"),
                 part("cube", "Top", (0, 0, H), (0.22, 0.22, 0.02), "iron"),
                 part("cone", "Roof", (0, 0, H + 0.06), (0.27, 0.27, 0.10), "iron"),
                 part("torus", "Ring", (0, 0, H + 0.15), (1, 1, 1), "iron", R=0.035, r=0.008)]
        for i, (x, y) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
            objs.append(part("cube", f"Post{i}", (x * 0.1, y * 0.1, H / 2), (0.018, 0.018, H), "iron"))
        for i, (x, y, sx, sy) in enumerate(((0.1, 0, 0.004, 0.18), (-0.1, 0, 0.004, 0.18), (0, 0.1, 0.18, 0.004), (0, -0.1, 0.18, 0.004))):
            objs.append(part("cube", f"Glass{i}", (x, y, H / 2), (sx, sy, H - 0.04), "glass"))
        objs.append(part("cyl", "Candle", (0, 0, 0.09), (0.06, 0.06, 0.14), "wax"))
        objs.append(part("cone", "Flame", (0, 0, 0.19), (0.025, 0.025, 0.05), "flame"))
    if stage >= 2:
        M = {"iron": mat("M_Iron", (0.06, 0.06, 0.065), metal=1, rough=0.45), "glass": mat("M_Glass", (0.7, 0.8, 0.85), rough=0.05, alpha=0.25),
             "wax": mat("M_Wax", (0.92, 0.88, 0.78), rough=0.7), "flame": mat("M_Flame", (1, 0.6, 0.2), emit=(1, 0.55, 0.15))}
    else:
        M = {k: mat(f"M_Clay_{k}", (0.6, 0.6, 0.62)) for k in ("iron", "glass", "wax", "flame")}
    for o in objs:
        o.data.materials.append(M[o["mk"]])
        if stage == 3 and o["mk"] == "iron" and o.name.startswith(("Base", "Top", "Post")):
            md = o.modifiers.new("Bevel", "BEVEL"); md.width = 0.003; md.segments = 2
    return objs

for i, name in enumerate(("blockout", "details", "materials", "final")):
    export(f"{OUT}/lantern_{i + 1}_{name}.glb", lantern(i))
print("TUTORIAL OK")
