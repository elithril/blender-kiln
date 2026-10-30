"""The real before hammer morphing into the real after one (same 624 vertices), on Blender's grey, 30 fps.
    blender -b --factory-startup --python-exit-code 1 --python hammer_morph.py -- BEFORE_GLB AFTER_GLB OUTDIR"""
import bpy, math, os, sys
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a[0])
before = [v.co.copy() for v in bpy.data.objects["SK_KilnSmith_Hammer"].data.vertices]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=a[1])
h = bpy.data.objects["SK_KilnSmith_Hammer"]
assert len(h.data.vertices) == len(before)
h.shape_key_add(name="after", from_mix=False)
k = h.shape_key_add(name="before", from_mix=False)
for i, co in enumerate(before): k.data[i].co = co
arm = next(o for o in sc.objects if o.type == "ARMATURE")
idle = next(x for x in bpy.data.actions if x.name.startswith("idle"))
ad = arm.animation_data or arm.animation_data_create()
for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
ad.action = idle
try: ad.action_slot = idle.slots[0]
except Exception: pass
F0, HOLD, MORPH = 1, 10, 26
sc.render.fps = 30; sc.frame_start, sc.frame_end = F0, F0 + HOLD * 2 + MORPH - 1
# the idle pose frozen at its first frame: only the hammer changes
idle_f = int(idle.frame_range[0])
fc_owner = ad
ad.action = None
sc.frame_set(F0)
ad.action = idle
arm.animation_data.action_extrapolation = "HOLD"
for o in sc.objects: o.hide_render = o.hide_render
k.value = 1.0; k.keyframe_insert("value", frame=F0 + HOLD)
k.value = 0.0; k.keyframe_insert("value", frame=F0 + HOLD + MORPH)
# freeze the armature on the idle's first frame
sc.frame_set(idle_f)
for pb in arm.pose.bones:
    pb.keyframe_insert("location", frame=F0); pb.keyframe_insert("rotation_quaternion", frame=F0); pb.keyframe_insert("scale", frame=F0)
ad.action = None
for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
# frame on both hammers and the hand, posed
def bounds(val):
    k.value = val; sc.frame_set(F0); dg = bpy.context.evaluated_depsgraph_get()
    e = h.evaluated_get(dg); m = e.to_mesh(); vs = [e.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear(); return vs
vs = bounds(1.0) + bounds(0.0); k.value = 1.0
lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
body = bpy.data.objects["SK_KilnSmith"]
dg = bpy.context.evaluated_depsgraph_get(); e = body.evaluated_get(dg); m = e.to_mesh(); bv = [e.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear()
blo = Vector([min(v[i] for v in bv) for i in range(3)]); bhi = Vector([max(v[i] for v in bv) for i in range(3)])
print("HAMMER", tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi), "BODY", tuple(round(x, 3) for x in blo), tuple(round(x, 3) for x in bhi))
T = Vector(((blo.x + bhi.x) / 2, (blo.y + bhi.y) / 2, float(__import__("os").environ.get("TZ_", "0.56"))))
def srgb(hx):
    c = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1,)
w = bpy.data.worlds.new("w"); sc.world = w
w.node_tree.nodes["Background"].inputs["Color"].default_value = srgb("3d3d3d"); w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
for name, e_, size, loc in (("key", 300, 2.0, (1.6, -2.4, 2.4)), ("fill", 90, 3.0, (-2.4, -1.6, 1.2)), ("rim", 200, 1.4, (-1.0, 1.8, 2.0))):
    l = bpy.data.lights.new(name, "AREA"); l.energy = e_; l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
cd = bpy.data.cameras.new("cam"); cd.lens = 50; cd.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
az, el = float(os.environ.get("AZ", "-0.95")), 0.12
span = float(os.environ.get("SPAN", "1.8"))
dist = (span / 2) / math.tan(math.atan(18 / 50))
cam.location = T + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * dist
cam.rotation_euler = (T - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "BLENDER_EEVEE"; sc.eevee.taa_render_samples = 64
sc.render.resolution_x, sc.render.resolution_y = 1140, 760
try: sc.view_settings.view_transform = "AgX"
except TypeError: pass
out = a[2]; os.makedirs(out, exist_ok=True); sc.render.filepath = os.path.join(out, "h_")
if os.environ.get("TEST"): sc.frame_start = sc.frame_end = int(os.environ["TEST"])
bpy.ops.render.render(animation=True)
print("MORPH_OK", sc.frame_end - sc.frame_start + 1)
