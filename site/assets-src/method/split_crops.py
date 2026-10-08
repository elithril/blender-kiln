"""Split the session's crop montage (how-it-works panel 1) into its separate crops.
   blender -b --factory-startup --python-exit-code 1 --python split_crops.py -- <panel.png> <out_dir>"""
import os, sys
from collections import deque
import bpy
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
img = bpy.data.images.load(a[0]); w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
d = np.abs(px[..., :3] - 64 / 255).max(axis=2)
fg = d > 5 / 255
seen = np.zeros_like(fg); boxes = []
for y in range(h):
    for x in range(w):
        if fg[y, x] and not seen[y, x]:
            q = deque([(y, x)]); seen[y, x] = True; y0 = y1 = y; x0 = x1 = x; n = 0
            while q:
                cy, cx = q.popleft(); n += 1
                y0, y1, x0, x1 = min(y0, cy), max(y1, cy), min(x0, cx), max(x1, cx)
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < h and 0 <= nx < w and fg[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
            if n > 2500: boxes.append((x0, y0, x1, y1, n))
os.makedirs(a[1], exist_ok=True)
for i, (x0, y0, x1, y1, n) in enumerate(sorted(boxes, key=lambda b: (b[1] // 40, b[0]))):
    c = px[y0:y1 + 1, x0:x1 + 1].copy(); c[..., 3] = 1
    o = bpy.data.images.new(f"c{i}", c.shape[1], c.shape[0], alpha=True)
    o.pixels[:] = c[::-1].ravel(); o.filepath_raw = os.path.join(a[1], f"crop-{i + 1}.png"); o.file_format = "PNG"; o.save()
    print(f"CROP {i + 1} {x1 - x0 + 1}x{y1 - y0 + 1} at {x0},{y0} px={n}")
