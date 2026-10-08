"""Rule 2 review: render a GLB or .blend from two opposite angles, dark studio, bloom-free EEVEE.
   blender -b --factory-startup --python-exit-code 1 --python review.py -- <file> <out_prefix>"""
import math, sys
import bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], a[1]
if src.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=src)
else:
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
try: sc.render.engine = "BLENDER_EEVEE"
except TypeError: sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x = sc.render.resolution_y = 700
w = bpy.data.worlds.new("W"); sc.world = w; w.color = (0.006, 0.005, 0.005)
for name, loc, e in (("Key", (-1.6, -1.4, 2.2), 260), ("Rim", (1.2, 1.8, 1.6), 160)):
    l = bpy.data.lights.new(name, "AREA"); l.energy = e; l.size = 1.5
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (-o.location).to_track_quat("-Z", "Y").to_euler()
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
for i, az in enumerate((-35, 145)):
    r, el = 3.4, math.radians(20)
    t = Vector((0, 0, 0.6))
    cam.location = t + Vector((math.sin(math.radians(az)) * r * math.cos(el), -math.cos(math.radians(az)) * r * math.cos(el), r * math.sin(el)))
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}-{i}.png"
    bpy.ops.render.render(write_still=True)
