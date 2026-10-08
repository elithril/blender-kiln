"""Bench sheets on the site: paint their empty grid cells (pure black fill) in the page's grey.

    blender -b --factory-startup --python-exit-code 1 --python fill_empty_cells.py -- <in.png> <out.png> [r g b]

Only large pure-black areas and the white gutters (rows or columns more than 60 % pure white) change: a pixel is repainted when it is black and at least 98 % of its
61 x 61 neighbourhood is black too, so dark renders, labels and thin black details stay as published.
Prints the share of the sheet that was repainted.
"""
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
src, dst = a[0], a[1]
nums = [x for x in a[2:] if not x.startswith('--')]
fill = [int(x) / 255 for x in (nums[:3] if len(nums) >= 3 else (0x2e, 0x2e, 0x2e))]

img = bpy.data.images.load(src)
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
black = (px[..., :3].max(axis=2) < 1.5 / 255).astype(np.float32)

k = 30  # half window: 61 px, taller than any label bar (~33 px), smaller than any empty cell
ii = np.pad(black, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
y0 = np.clip(np.arange(h) - k, 0, h); y1 = np.clip(np.arange(h) + k + 1, 0, h)
x0 = np.clip(np.arange(w) - k, 0, w); x1 = np.clip(np.arange(w) + k + 1, 0, w)
area = (2 * k + 1) ** 2  # outside the image counts as not black, so a bar along an edge cannot fill a window
s = ii[y1][:, x1] - ii[y0][:, x1] - ii[y1][:, x0] + ii[y0][:, x0]
mask = (black > 0) & (s >= 0.98 * area)
# grow the mask over the window so a cell's edge pixels go too
mi = np.pad(mask.astype(np.float32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
near = (mi[y1][:, x1] - mi[y0][:, x1] - mi[y1][:, x0] + mi[y0][:, x0]) > 0
mask = near & (black > 0)
if '--white' in a:  # also large pure-white areas (an empty cell painted white)
    wh = (px[..., :3].min(axis=2) > 250 / 255).astype(np.float32)
    wi = np.pad(wh, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ws = wi[y1][:, x1] - wi[y0][:, x1] - wi[y1][:, x0] + wi[y0][:, x0]
    wm = (wh > 0) & (ws >= 0.98 * area)
    wmi = np.pad(wm.astype(np.float32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    mask = mask | (((wmi[y1][:, x1] - wmi[y0][:, x1] - wmi[y1][:, x0] + wmi[y0][:, x0]) > 0) & (wh > 0))

# the sheets' white gutters: full-width or full-height runs of pure white, at most 24 px thick
white = px[..., :3].min(axis=2) > 250 / 255
rows = white.mean(axis=1) > 0.6
cols = white.mean(axis=0) > 0.6
gut = (rows[:, None] | cols[None, :]) & white
mask = mask | gut
px[mask, 0], px[mask, 1], px[mask, 2] = fill
out = bpy.data.images.new("out", w, h, alpha=False)
out.pixels[:] = px.ravel()
out.filepath_raw = dst
out.file_format = "PNG"
out.save()
print(f"FILLED {mask.mean() * 100:.1f}% of {w}x{h}")
