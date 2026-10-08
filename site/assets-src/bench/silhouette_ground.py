"""The Measure step's silhouette overlay has a pure black ground: put it on the page's grey.
Blends by darkness, so anti-aliased edges fade into the grey instead of keeping a black rim.
    blender -b --factory-startup --python-exit-code 1 --python silhouette_ground.py -- <in.png> <out.png>"""
import sys
import bpy
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
img = bpy.data.images.load(a[0]); w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
g = 64 / 255
k = np.clip(px[..., :3].max(axis=2) / 0.35, 0, 1)[..., None]  # 0 on black, 1 on any colour
px[..., :3] = px[..., :3] * k + g * (1 - k)
out = bpy.data.images.new("o", w, h, alpha=False); out.pixels[:] = px.ravel()
out.filepath_raw = a[1]; out.file_format = "PNG"; out.save()
