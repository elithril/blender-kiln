"""The mascot's walk_loop with its new hammer, 1920x1080 at 30 fps, on a warm seamless sweep.
    blender -b --factory-startup --python-exit-code 1 --python walk_render.py -- GLB OUTDIR [CLIP] [AZIM]"""
import bpy, math, os, sys
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
glb, out = a[0], a[1]; clip = a[2] if len(a) > 2 else "walk_loop"; azim = float(a[3]) if len(a) > 3 else -0.55
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=glb)
arm = next(o for o in sc.objects if o.type == "ARMATURE")
act = next(x for x in bpy.data.actions if x.name.split("_Armature")[0].split(".")[0] == clip or x.name == clip or x.name.startswith(clip + "_"))
ad = arm.animation_data or arm.animation_data_create()
for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
ad.action = act
try:
    ad.action_slot = act.slots[0]
except Exception:
    pass
f0, f1 = [int(round(v)) for v in act.frame_range]
sc.render.fps = 24; sc.frame_start, sc.frame_end = f0, f1 - 1   # the closing key equals the first: a seamless loop
print("ACTION", act.name, f0, f1)
def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1,)
# warm sweep: floor + curved back wall in one mesh
bpy.ops.mesh.primitive_plane_add(size=1)
sw = bpy.context.object; sw.name = "sweep"
me = sw.data; import bmesh
bm = bmesh.new(); W, D, H, R = 40, 10, 12, 1.6
pts = [(-D, 0)] + [(R * math.sin(t) , R - R * math.cos(t)) for t in [i / 12 * math.pi / 2 for i in range(13)]] + [(R, H)]
rows = []
for y, z in pts:
    rows.append([bm.verts.new((x, y + 2.2, z)) for x in (-W / 2, W / 2)])
for r0, r1 in zip(rows, rows[1:]):
    bm.faces.new((r0[0], r0[1], r1[1], r1[0]))
bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
m = bpy.data.materials.new("sweep"); m.use_nodes = True
b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = srgb("d9c6ad"); b.inputs["Roughness"].default_value = 0.75
me.materials.append(m)
w = bpy.data.worlds.new("w"); sc.world = w
w.node_tree.nodes["Background"].inputs["Color"].default_value = srgb("f2e6d6")
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
for name, e, size, loc, col in (("key", 420, 2.6, (2.2, -2.6, 2.9), "fff1e0"), ("fill", 120, 4.0, (-3.0, -2.0, 1.6), "dfe8ff"),
                                 ("rim", 260, 1.6, (-1.2, 2.0, 2.4), "ffd2a6")):
    l = bpy.data.lights.new(name, "AREA"); l.energy = e; l.size = size; l.color = srgb(col)[:3]
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.55)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
cd = bpy.data.cameras.new("cam"); cd.lens = 50
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
dg = bpy.context.evaluated_depsgraph_get(); lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for fr in range(f0, f1, 4):
    sc.frame_set(fr); dg = bpy.context.evaluated_depsgraph_get()
    for o in sc.objects:
        if o.type == "MESH" and o.name.startswith("SK_"):
            e = o.evaluated_get(dg); mm = e.to_mesh()
            for v in list(mm.vertices)[::7]:
                w = e.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
            e.to_mesh_clear()
sc.frame_set(f0); print("BOUNDS", tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi))
SH = float(os.environ.get("SHIFT", "0.0"))
T = Vector(((lo.x + hi.x) / 2 + SH, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2)); el = 0.10
dist = ((hi.z - lo.z) * float(os.environ.get("MARGIN", "1.25")) / 2) / math.tan(math.atan(10.125 / 50))
cam.location = T + Vector((math.cos(el) * math.cos(azim - math.pi / 2), math.cos(el) * math.sin(azim - math.pi / 2), math.sin(el))) * dist
cam.rotation_euler = (T - cam.location).to_track_quat("-Z", "Y").to_euler()
body = sc.objects["SK_KilnSmith"]; base = cam.location.copy(); c0 = None
for fr in range(f0, f1):
    sc.frame_set(fr); dg = bpy.context.evaluated_depsgraph_get(); e = body.evaluated_get(dg); mm = e.to_mesh()
    vs = [e.matrix_world @ v.co for v in mm.vertices]; e.to_mesh_clear()
    c = Vector((sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs), 0))
    c0 = c0 or c
    cam.location = base + Vector((c.x - c0.x, c.y - c0.y, 0)); cam.keyframe_insert("location", frame=fr)
sc.frame_set(f0)
print("TRAVEL", round((c - c0).length, 3))
sc.render.engine = "BLENDER_EEVEE"; sc.eevee.taa_render_samples = 64
try: sc.eevee.use_raytracing = True
except Exception: pass
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
try: sc.view_settings.view_transform = "AgX"
except TypeError: pass
sc.render.image_settings.file_format = "PNG"
os.makedirs(out, exist_ok=True); sc.render.filepath = os.path.join(out, "f_")
if os.environ.get("TEST"): sc.frame_end = sc.frame_start + int(os.environ["TEST"]) - 1
bpy.ops.render.render(animation=True)
print("WALK_OK", out, sc.frame_end - sc.frame_start + 1)
