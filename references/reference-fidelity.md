# Reference Fidelity — when the user gives an image

Load this whenever a brief comes with a reference image and the asset is built by
script. It is the cheap half of what image-to-code pipelines spend dozens of vision
passes on: **measure the image instead of eyeballing it**, and spend the model's
attention only on what measuring cannot settle.

Why it exists — measured on 2026-09-30 against Poly Haven's `Lantern_01` preview
(`bench/results/ref-compare/`): kiln's scripted lantern matched the reference's
likeness for $1.90, but shipped a top loop resting *on* the cap instead of inserted
into it, a pointed bail peak where the reference dips, no vent slots, one floating
part, and one generic noise texture shared by 19 parts over a single UV atlas. An
image-to-code tool matched it better on those points at ~5x the cost. Every step
below answers one of those defects, and each snippet was run on Blender 5.2.2.

## 1. Inventory the details before modeling

List every identity-defining detail visible in the image, and the part it belongs
to — in the log, before the first line of geometry. A detail with no part is a
detail that will be forgotten.

```
- top loop: pentagon wire, legs INSERTED into the cap          → SM_<Asset>_TopLoop, parent Cap
- bail: wide wire arch, shallow DIP at the peak, ends hooked in the air tubes → Bail
- vent slots: dark rectangular slots under the cap, all around → Chimney
- globe: clear glass, faint frosting and scratches             → Globe (its own material)
```

Write *how* parts meet ("inserted", "hooked", "welded", "resting") — that is what
step 3 checks.

## 2. Measure the silhouette

The reference's own pixels give proportions in millimetres. For a turned object
(lantern, bottle, vase, barrel) the profile is usable directly as a lathe profile.
Take the **core width** — the opaque run through the vertical axis — not the full
width, which at the top of a lantern measures the bail, not the body.

```python
import bpy, numpy as np
def core_profile(path, height_m):
    """[(height_m, core_width_m)] from the bottom up. Needs an alpha channel."""
    im = bpy.data.images.load(path, check_existing=True); w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]   # rows are bottom-up
    mask = px[..., 3] > 0.5
    rows = np.where(mask.any(1))[0]; top, bot = rows.min(), rows.max()
    cx = int(np.median(np.where(mask[rows])[1]))                          # the vertical axis
    mpp = height_m / (bot - top + 1); out = []
    for y in range(top, bot + 1):
        r = mask[y]
        if not r[cx]:
            out.append(((bot - y) * mpp, 0.0)); continue
        a = b = cx
        while a > 0 and r[a - 1]: a -= 1
        while b < w - 1 and r[b + 1]: b += 1
        out.append(((bot - y) * mpp, (b - a + 1) * mpp))
    return out[::-1]                                                      # bottom-up, as documented
```

`height_m` is the one number you choose (brief, or a real-world size). An opaque
reference needs a mask first — key out the corner colour.

## 3. Check that every part is attached

Measure surface to surface with a BVH — vertex-to-vertex distances overstate gaps
on coarse meshes (measured: 2.86 mm by vertices, under 0.5 mm by surface, for the
same loop). Anything above 0.5 mm from every other part floats.

```python
import bpy, bmesh
from mathutils.bvhtree import BVHTree
def floating_parts(objs, tol=0.0005):
    dg = bpy.context.evaluated_depsgraph_get(); data = {}
    for o in objs:
        bm = bmesh.new(); bm.from_object(o, dg); bm.transform(o.matrix_world)
        data[o.name] = (BVHTree.FromBMesh(bm), [v.co.copy() for v in bm.verts]); bm.free()
    out = []
    for n, (_, pts) in data.items():
        d, m = min((min(t.find_nearest(p)[3] for p in pts), k) for k, (t, _) in data.items() if k != n)
        if d > tol:
            out.append((n, m, round(d * 1000, 2)))                       # name, nearest, mm
    return out
```

Contact is not insertion: a loop that touches its cap at one point passes this
check and still reads wrong. Step 1's "inserted" is checked in step 5, by eye.

## 4. Materials from the reference, not from memory

**One material per visually distinct region** of the inventory — glass, the body's
patina, wire, soot — never one material for every metal part. And **one texture set
per major part**: a single Smart UV atlas over 19 parts left the tank 14 % of it.

Sample each region's colour from the image:

```python
def region_colour(path, x, y, w, h):
    """Median opaque colour of a crop (x, y from the TOP-left, in pixels) → (srgb, linear)."""
    im = bpy.data.images.load(path, check_existing=True); W, H = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]
    c = px[y:y + h, x:x + w].reshape(-1, 4); c = c[c[:, 3] > 0.5][:, :3]
    s = np.median(c, axis=0)
    return s, np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
```

Feed the **linear** value to Principled BSDF. Then three rules the bench measured:

- **A photographed metal's colour is its patina's, and patina is not metal.** The
  lantern's tank measures sRGB (0.14, 0.12, 0.10). Put that on a surface with
  Metallic 0.85 and it renders as a grey mirror of the environment. Patina:
  measured colour, Metallic ~0.2, Roughness ~0.65. Only the worn edges are metal:
  bright bronze, Metallic 1, Roughness ~0.3.
- **Wear follows curvature — thresholded by percentile, on the part itself.**
  Cycles' Pointiness spans only 0.48–0.57 on a coarse mesh (measured on the tank),
  so a fixed threshold of 0.52 or 0.56 lands anywhere. Bake Pointiness, take the
  part's 90th and 99th percentiles as the ramp's ends, and multiply by a fine noise
  so edges wear in patches, not as a ruled line. Cavities darken with AO (distance
  ~1 cm for a hand-sized prop).
- **Bake colour through an Emission shader into a float image.** A DIFFUSE bake of a
  metallic surface comes out near-black; a byte sRGB target shifts the value. Baked
  this way, a flat texel returns the measured patina exactly (0.0174 against 0.0176
  linear). Compose base colour, roughness and metallic from the baked masks, then
  bake nothing procedural into the export (rule 19).

## 5. Review against the reference — twice, at most

Render an **orthographic front view framed like the reference** and put the two side
by side: once after modeling, once after texturing. Look for what the inventory
listed — insertion, dips, slots, glass — and fix what is missing. **Two correction
rounds at most**: the image-to-code tool that ran eight vision passes spent ~5x the
cost for the same likeness. Log each round: what differed, what changed.
