"""Rule 2 review: render the .blend from two opposite angles under a neutral studio light (EEVEE)."""
import math, os, sys, bpy
HERE = os.path.dirname(bpy.data.filepath)
glb = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
sc = bpy.context.scene
if glb:  # review the shipped file, not the .blend (rule: measure the file that ships)
    for ob in list(bpy.data.objects): bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=glb)
try: sc.render.engine = "BLENDER_EEVEE"
except TypeError as e: print(e); sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 900, 600
w = bpy.data.worlds.new("W"); sc.world = w; w.color = (0.05, 0.05, 0.05)
for name, loc, e in (("Key", (-1.2, -1.0, 1.6), 110), ("Fill", (1.4, -0.6, 0.9), 35), ("Rim", (0.3, 1.5, 1.2), 70)):
    l = bpy.data.lights.new(name, "AREA"); l.energy = e; l.size = 1.2
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    d = -o.location; o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
out = os.path.join(HERE, "work", "review")
os.makedirs(out, exist_ok=True)
tag = "glb" if glb else "blend"
for i, az in enumerate((-30, 150)):
    a = math.radians(az); el = math.radians(28); dist = 1.45
    cam.location = (math.sin(a) * dist * math.cos(el), -math.cos(a) * dist * math.cos(el), 0.04 + dist * math.sin(el))
    d = (cam.location * -1); d.z += 0.04
    cam.rotation_euler = (-(cam.location) + __import__("mathutils").Vector((0, 0, 0.04))).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out, f"{tag}-{i}.png")
    bpy.ops.render.render(write_still=True)
print("RENDERED", out)
