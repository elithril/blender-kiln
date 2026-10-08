"""Render an animated GLB under the quality bench's light, for the site's Animate section.

    blender -b --factory-startup --python-exit-code 1 --python render_bench.py -- \\
        <clip.glb> <out_dir> --hdri <studio_small_09_1k.hdr> [--res 600] [--samples 32]

Same light as every bench sheet on the site (Poly Haven studio_small_09, CC0), camera ~15° above
on a 3/4 orbit, framed on the whole motion. The film is transparent with a shadow catcher, so each
frame keeps its contact shadow and lands on the page's own #404040 floor with no frame around it.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
clip, out = Path(argv[0]), Path(argv[1])
opt = dict(zip(argv[2::2], argv[3::2]))
res, samples = int(opt.get("--res", 600)), int(opt.get("--samples", 32))
hdri = opt["--hdri"]
out.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(clip))
scene = bpy.context.scene
arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)
shapes = {pb.custom_shape for o in scene.objects if o.type == "ARMATURE" for pb in o.pose.bones if pb.custom_shape}
meshes = [o for o in scene.objects if o.type == "MESH" and o not in shapes]
for o in shapes:
    o.hide_render = True
act = None
for o in scene.objects:
    if o.animation_data and o.animation_data.action:
        act = o.animation_data.action
        break
f0, f1 = (int(x) for x in act.frame_range)

corners = []
for f in range(f0, f1 + 1, 2):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    for m in meshes:
        e = m.evaluated_get(dg)
        corners += [e.matrix_world @ v.co for v in list(e.data.vertices)[::3]]
lo = Vector([min(c[i] for c in corners) for i in range(3)])
hi = Vector([max(c[i] for c in corners) for i in range(3)])
size = max(hi - lo)

# the bench's light
world = bpy.data.worlds.new("W")
scene.world = world
nt = world.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(hdri)
bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
bg.inputs["Strength"].default_value = 1.0
nt.links.new(env.outputs["Color"], bg.inputs["Color"])

# a floor that only catches shadows
bpy.ops.mesh.primitive_plane_add(size=size * 30, location=(0, 0, lo.z))
floor = bpy.context.active_object
floor.is_shadow_catcher = True

try:
    scene.render.engine = "CYCLES"
except TypeError as e:
    print(e)
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = res
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.exposure = 0.0

# ~15° above, 3/4 orbit, framed on every point the mesh reaches
cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 72.0
cam = bpy.data.objects.new("cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam
elev, azim = math.radians(15), -0.95
d = Vector((math.cos(elev) * math.cos(azim), math.cos(elev) * math.sin(azim), math.sin(elev)))
fov = 2.0 * math.atan(cam_d.sensor_width / (2.0 * cam_d.lens))
right = d.cross(Vector((0, 0, 1))).normalized()
up = right.cross(d).normalized()
center = (lo + hi) / 2
pr = [(c - center).dot(right) for c in corners]
pu = [(c - center).dot(up) for c in corners]
mid = center + right * (max(pr) + min(pr)) / 2 + up * (max(pu) + min(pu)) / 2
half = max(max(pr) - min(pr), max(pu) - min(pu)) / 2
depth = max((c - mid).dot(d) for c in corners)
cam.location = mid + d * ((half * 1.22) / math.tan(fov / 2.0) + depth)
cam.rotation_euler = (mid - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()

n = 0
for f in range(f0, f1 + 1):
    scene.frame_set(f)
    scene.render.filepath = str(out / f"{n:04d}.png")
    bpy.ops.render.render(write_still=True)
    n += 1
print(f"RENDERED {n} frames of {clip.name}")
