"""Render a shipped GLB, re-imported, for the human half of the bench.

    blender --background --factory-startup --python-exit-code 1 --python bench/render.py -- <file.glb> <out.png>

Numbers catch what can be counted; a lantern whose grille reads as a solid
block counts fine. Two views side by side — 3/4 front and 3/4 back — lit by the
gallery's studio rig, so every brief is judged under the same light.
"""
import bpy, math, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "gallery"))
import studio as S

argv = sys.argv[sys.argv.index("--") + 1:]
glb, out = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
scene = bpy.context.scene
arms = [o for o in scene.objects if o.type == 'ARMATURE']
shapes = {pb.custom_shape for a in arms for pb in a.pose.bones if pb.custom_shape}
for s in shapes:
    s.hide_render = True
meshes = [o for o in scene.objects if o.type == 'MESH' and o not in shapes]
if not meshes:
    sys.exit(f"no mesh in {glb}")

corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(c[i] for c in corners) for i in range(3)])
hi = Vector([max(c[i] for c in corners) for i in range(3)])
# frame() fits one object's bound_box; a two-vertex proxy spans every mesh.
me = bpy.data.meshes.new("bench_bounds")
me.from_pydata([lo, hi], [], [])
proxy = bpy.data.objects.new("bench_bounds", me)
scene.collection.objects.link(proxy)
proxy.hide_render = True

size = max((hi - lo).length, 0.05)
S.backdrop(scene)
S.three_point(scene, size)

tiles = []
for i, azim in enumerate((-0.62, -0.62 + math.pi)):
    for o in [o for o in scene.objects if o.type == 'CAMERA']:
        bpy.data.objects.remove(o)
    S.frame(scene, proxy, azim=azim)
    p = out.replace(".png", f"_{i}.png")
    S.render(scene, p, res=700, samples=48)
    tiles.append(p)

# Stitch the two views into one image.
imgs = [bpy.data.images.load(p) for p in tiles]
w, h = imgs[0].size
sheet = bpy.data.images.new("sheet", w * 2, h, alpha=True)
px = [0.0] * (w * 2 * h * 4)
for k, im in enumerate(imgs):
    src = list(im.pixels)
    for y in range(h):
        row = src[y * w * 4:(y + 1) * w * 4]
        start = (y * w * 2 + k * w) * 4
        px[start:start + w * 4] = row
sheet.pixels = px
sheet.filepath_raw = out
sheet.file_format = 'PNG'
sheet.save()
for p in tiles:
    os.remove(p)
print("BENCH_RENDER", out)
