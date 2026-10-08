"""Place a clean transparent render in the exact framing of its version's sheet tile.

    blender -b --factory-startup --python-exit-code 1 --python match_frame.py -- <render.png> <keyed_tile.png> <out.png>

Both come from the same object; the sheet tile is cropped tighter. Matching the alpha bounding box's
width and top edge gives the scale and offset, so swapping v10 (keyed from its sheet) for v11 (a fresh
render) in the flip-book does not jump. Output has the tile's size, transparent where the render is.
"""
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]


def load(p):
    im = bpy.data.images.load(p)
    w, h = im.size
    return im, np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]  # top-down


def bbox(px):
    ys, xs = np.where(px[..., 3] > 0.5)
    return xs.min(), xs.max(), ys.min()


fim, F = load(a[0])
_, K = load(a[1])
fx0, fx1, fy0 = bbox(F)
kx0, kx1, ky0 = bbox(K)
s = (kx1 - kx0) / (fx1 - fx0)
fh, fw = F.shape[:2]
fim.scale(max(1, round(fw * s)), max(1, round(fh * s)))
S = np.array(fim.pixels[:], dtype=np.float32).reshape(fim.size[1], fim.size[0], 4)[::-1]
ox, oy = round(kx0 - fx0 * s), round(ky0 - fy0 * s)
kh, kw = K.shape[:2]
out = np.zeros((kh, kw, 4), dtype=np.float32)
ys0, xs0 = max(0, oy), max(0, ox)
ys1, xs1 = min(kh, oy + S.shape[0]), min(kw, ox + S.shape[1])
out[ys0:ys1, xs0:xs1] = S[ys0 - oy:ys1 - oy, xs0 - ox:xs1 - ox]
img = bpy.data.images.new("o", kw, kh, alpha=True)
img.pixels[:] = out[::-1].ravel()
img.filepath_raw = a[2]
img.file_format = "PNG"
img.save()
print(f"MATCHED scale {s:.3f} offset {ox},{oy}")
