"""The Print section's pictures: each printed object photographed, and kiln's preview of it, framed alike.

    uvx --with pillow --with numpy --with scipy python -I site/assets-src/print/make_print.py \\
        <photos dir> <print package dir> site/public/assets/img/print

<photos dir> holds the five shots as JPEG (IMG_2390 ... IMG_2395, converted from the iPhone's HEIC with
`sips -s format jpeg`); <print package dir> is what was sent to the printer on 2026-10-13: one folder
per object with its STLs and kiln's preview (apercu-*.png). Each photo is cropped square with the
object's base at the same height; the cold shot of the lighthouse gets the white balance of the others.
Each preview is cut out of its flat background and framed to its photo, so switching views keeps the
object in place.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

photos, package, out = (Path(a) for a in sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
SIDE, BASE = 900, 0.92  # tile size; every object's base lands at 92% of its tile

# read on the 1400 px wide shots: centre x, base y, crop side; the box shares one side, so one scale
PHOTOS = {"windmill": ("IMG_2390", 620, 838, 700), "forge": ("IMG_2392", 602, 732, 680),
          "lighthouse": ("IMG_2393", 601, 703, 600), "box": ("IMG_2395", 644, 895, 840),
          "box-open": ("IMG_2394", 623, 823, 840)}
# the lighthouse's shot is cold: gains that bring its white PLA (above the table) to the other shots' tint
GAIN = {"lighthouse": np.array([1.078, 0.997, 0.938])}
# where the object sits in its photo tile, as fractions: top of its bounding box, horizontal centre
FRAME = {"windmill": (0.054, 0.461), "forge": (0.153, 0.5), "lighthouse": (0.268, 0.502), "box": (0.158, 0.499)}
PREVIEWS = {"windmill": "1-moulin/apercu-moulin.png", "forge": "3-forge/apercu-forge.png",
            "lighthouse": "2-phare/apercu-phare.png", "box": "4-boite/apercu-boite.png"}
NOW = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def save(im, name, prompt):
    im.save(out / f"{name}.webp", "WEBP", quality=82, method=6)
    (out / f"{name}.webp.json").write_text(json.dumps({"prompt": prompt, "createdAt": NOW}, indent=2) + "\n")


def photo(name, shot, cx, by, s):
    im = Image.open(photos / f"{shot}.jpg").convert("RGB")
    k = im.width / 1400
    cy = by - (BASE - 0.5) * s
    h = s * k / 2
    tile = im.crop((round(cx * k - h), round(cy * k - h), round(cx * k + h), round(cy * k + h))).resize((SIDE, SIDE), Image.LANCZOS)
    if name in GAIN:
        tile = Image.fromarray(np.clip(np.asarray(tile, dtype=float) * GAIN[name], 0, 255).round().astype(np.uint8))
    note = ", white balance matched to the other shots" if name in GAIN else ""
    save(tile, f"{name}-photo", f"Photographed: the PLA print of kiln's {name.replace('-', ' ')} as it came off a Bambu Lab P1S, "
         f"no touch-up; {shot} (iPhone), cropped square by site/assets-src/print/make_print.py{note}.")


def cutout(path):
    """RGBA of a preview: its flat background, reached from the border, made transparent; a soft edge."""
    a = np.asarray(Image.open(path).convert("RGBA")).astype(float)
    if a[..., 3].min() < 255:  # rendered with a transparent film already
        return a
    bg = a[2, 2, :3]
    dist = np.abs(a[..., :3] - bg).sum(2)
    lab, _ = ndimage.label(dist < 6)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    back = np.isin(lab, list(edge))
    ring = ndimage.binary_dilation(back) & ~back  # the antialiased pixels against the background
    alpha = np.where(back, 0.0, 1.0)
    alpha[ring] = np.clip(dist[ring] / 60, 0, 1)
    rgb = a[..., :3]
    with np.errstate(divide="ignore", invalid="ignore"):
        un = (rgb - (1 - alpha[..., None]) * bg) / alpha[..., None]
    rgb = np.where(ring[..., None] & (alpha[..., None] > 0), np.clip(un, 0, 255), rgb)
    return np.dstack([rgb, alpha * 255])


def preview(name, rel):
    a = cutout(package / rel)
    ys, xs = np.nonzero(a[..., 3] > 8)
    top, bot, left, right = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    ftop, fcx = FRAME[name]
    scale = (BASE - ftop) * SIDE / (bot - top)
    obj = Image.fromarray(a[top:bot, left:right].round().astype(np.uint8), "RGBA")
    obj = obj.resize((round((right - left) * scale), round((bot - top) * scale)), Image.LANCZOS)
    tile = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    tile.alpha_composite(obj, (round(fcx * SIDE - obj.width / 2), round(ftop * SIDE)))
    save(tile, f"{name}-model", f"Rendered by kiln: the preview sent with the STLs to the printer on 2026-10-13 ({rel}), "
         "its flat background keyed out and framed to the photo by site/assets-src/print/make_print.py.")


for n, args in PHOTOS.items():
    photo(n, *args)
for n, rel in PREVIEWS.items():
    preview(n, rel)
print(sorted(p.name for p in out.glob("*.webp")))
