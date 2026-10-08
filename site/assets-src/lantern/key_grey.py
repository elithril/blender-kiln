"""Cut a bench render out of its flat #404040 ground (for v1..v10, whose GLBs were never kept).

    blender -b --factory-startup --python-exit-code 1 --python key_grey.py -- <tile.png> <out.png>

fidelity_check rendered every version on a transparent film; the sheets then composited it over a
flat #404040. Only pixels connected, through near-grey pixels, to the border or to a perfectly flat grey patch count as ground, so dark
bronze inside the object is never punched out. Edge alpha comes from the colour's distance to the
ground, and the colour is un-composited (F = (C - (1 - a) G) / a), so no grey halo is left.
"""
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
img = bpy.data.images.load(a[0])
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]
G = np.array([64, 64, 64], dtype=np.float32) / 255
d = np.abs(px - G).max(axis=2)

near = d < 6 / 255
# seeds: the border, plus any patch of perfectly flat grey (a 9x9 window within 2/255), which a
# rendered surface never is: that catches the ground enclosed by the bail and the guard
flat = (d < 2 / 255).astype(np.float32)
ii = np.pad(flat, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
k = 4
y0 = np.clip(np.arange(h) - k, 0, h); y1 = np.clip(np.arange(h) + k + 1, 0, h)
x0 = np.clip(np.arange(w) - k, 0, w); x1 = np.clip(np.arange(w) + k + 1, 0, w)
win = ii[y1][:, x1] - ii[y0][:, x1] - ii[y1][:, x0] + ii[y0][:, x0]
ground = (win >= (2 * k + 1) ** 2) & near
ground[0, :] |= near[0, :]; ground[-1, :] |= near[-1, :]; ground[:, 0] |= near[:, 0]; ground[:, -1] |= near[:, -1]
while True:  # flood fill through near-grey pixels, by dilation
    g = ground.copy()
    g[1:, :] |= ground[:-1, :]; g[:-1, :] |= ground[1:, :]; g[:, 1:] |= ground[:, :-1]; g[:, :-1] |= ground[:, 1:]
    g &= near
    if (g == ground).all():
        break
    ground = g

# soft edge: pixels touching the ground get alpha from their distance to grey
touch = ground.copy()
touch[1:, :] |= ground[:-1, :]; touch[:-1, :] |= ground[1:, :]; touch[:, 1:] |= ground[:, :-1]; touch[:, :-1] |= ground[:, 1:]
alpha = np.ones((h, w), dtype=np.float32)
alpha[ground] = 0
edge = touch & ~ground
alpha[edge] = np.clip(d[edge] / (40 / 255), 0.15, 1)
fg = px.copy()
k = alpha[..., None]
fg = np.where(k > 0, np.clip((px - (1 - k) * G) / np.maximum(k, 1e-3), 0, 1), 0)

out = bpy.data.images.new("o", w, h, alpha=True)
o = np.dstack([fg, alpha]).astype(np.float32)
out.pixels[:] = o.ravel()
out.filepath_raw = a[1]
out.file_format = "PNG"
out.save()
print(f"KEYED ground {ground.mean() * 100:.1f}% edge {edge.sum()} px")
