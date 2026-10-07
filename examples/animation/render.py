"""Render an animated GLB to PNG frames under the gallery's studio light.

    blender --background --factory-startup --python-exit-code 1 --python render.py -- \\
        <clip.glb> <out_dir> [--res 480] [--step 2] [--samples 48]

The camera is fixed on the gallery's 3/4 orbit and framed on the clip's whole
motion — every frame's silhouette, not the rest pose — so a jump or a run stays
in shot. Frames land as <out_dir>/0000.png ...; `showcase.sh` turns them into a
looping WebP.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gallery"))
import studio as S  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
clip, out = Path(argv[0]), Path(argv[1])
opt = dict(zip(argv[2::2], argv[3::2]))
res, step, samples = int(opt.get("--res", 480)), int(opt.get("--step", 2)), int(opt.get("--samples", 48))
elev = float(opt.get("--elev", 0.50))
margin = float(opt.get("--margin", 1.25))
out.mkdir(parents=True, exist_ok=True)

S.reset()
bpy.ops.import_scene.gltf(filepath=str(clip))
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
# the glTF importer adds an Icosphere as the bones' display shape: not part of the subject
shapes = {pb.custom_shape for o in scene.objects if o.type == 'ARMATURE' for pb in o.pose.bones if pb.custom_shape}
meshes = [o for o in scene.objects if o.type == 'MESH' and o not in shapes]
for o in shapes: o.hide_render = True
f0, f1 = (int(x) for x in arm.animation_data.action.frame_range)

# Every corner the mesh reaches during the clip.
corners = []
for f in range(f0, f1 + 1, 3):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    for m in meshes:
        e = m.evaluated_get(dg)
        corners += [e.matrix_world @ v.co for v in list(e.data.vertices)[::4]]
lo = Vector([min(c[i] for c in corners) for i in range(3)])
hi = Vector([max(c[i] for c in corners) for i in range(3)])
size = max(hi - lo)

S.backdrop(scene, world_col=S.GROUND if hasattr(S, 'GROUND') else None, radius=size * 40, strength=0.9)
ground = scene.objects["ground"]
ground.location.z = lo.z
S.three_point(scene, size)

# The gallery's 3/4 orbit, fitted on the points the mesh actually reaches during the clip
# (a box's corners project wider than the silhouette and left subjects small).
center = (lo + hi) / 2
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 72.0
cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam); scene.camera = cam
azim = -0.95
d = Vector((math.cos(elev) * math.cos(azim), math.cos(elev) * math.sin(azim), math.sin(elev)))
fov = 2.0 * math.atan(cam_d.sensor_width / (2.0 * cam_d.lens))
right = d.cross(Vector((0, 0, 1))).normalized(); up = right.cross(d).normalized()
proj_r = [(c - center).dot(right) for c in corners]; proj_u = [(c - center).dot(up) for c in corners]
mid = center + right * (max(proj_r) + min(proj_r)) / 2 + up * (max(proj_u) + min(proj_u)) / 2
half = max(max(proj_r) - min(proj_r), max(proj_u) - min(proj_u)) / 2
depth = max((c - mid).dot(d) for c in corners)
cam.location = mid + d * ((half * margin) / math.tan(fov / 2.0) + depth)
cam.rotation_euler = (mid - cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()

n = 0
for f in range(f0, f1 + 1, step):
    scene.frame_set(f)
    S.render(scene, str(out / f"{n:04d}.png"), res=res, samples=samples, exposure=0.8)
    n += 1
print(f"RENDERED {n} frames of {clip.name} ({f1 - f0 + 1} in the clip, every {step})")
