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

**Wires, handles and bails: trace their centre line and use it as the curve.** Guessed
control points drift — kiln's first bail sat 1.8–2.3 % of the height off the reference,
with a pointed peak where it dips. Traced from the pixels, the same bail lands within
0.7 mm of an image-to-code tool's hand-measured points:

```python
def trace_wire(path, height_m, y_from, y_to, side=+1):
    """Centre line of the outermost thin run on one side of the axis, one point per row,
    between two fractions of the height from the TOP. [(x_m from axis, z_m from base)]."""
    im = bpy.data.images.load(path, check_existing=True); w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    m = px[..., 3] > 0.5
    rows = np.where(m.any(1))[0]; top, bot = rows.min(), rows.max(); mpp = height_m / (bot - top + 1)
    cx = int(np.median(np.where(m[rows])[1]))
    pts = []
    for y in range(int(top + y_from * (bot - top)), int(top + y_to * (bot - top))):
        xs = np.where(m[y])[0]; xs = xs[xs > cx] if side > 0 else xs[xs < cx]
        if not len(xs): continue
        edge = xs.max() if side > 0 else xs.min(); run = [edge]; on = set(xs)
        while (edge - side * len(run)) in on: run.append(edge - side * len(run))
        pts.append(((np.mean(run) - cx) * mpp * side, (bot - y) * mpp))
    return pts
```

Thin every ~10th point and feed them to a curve (Blender: a poly spline converted to a
NURBS/Bezier, or points through a `Curve` object with a bevel for the wire's measured
thickness). Where the wire meets another part the trace catches that part — stop the
range above it.

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

Sample each region's **range**, not only its median — blotches live between a dark and a
light that the image shows. Measured on the lantern's tank: `#120f0c` / `#241e19` / `#4b3f33`.

```python
def region_palette(path, x, y, w, h):
    """Dark / mid / light sRGB colours of a crop (x, y from the TOP-left): the 10th, 50th and
    90th luminance percentiles, each averaged over a small window."""
    im = bpy.data.images.load(path, check_existing=True); W, H = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]
    c = px[y:y + h, x:x + w].reshape(-1, 4); c = c[c[:, 3] > 0.5][:, :3]
    order = np.argsort(c @ np.array([0.2126, 0.7152, 0.0722])); k = max(1, len(c) // 40)
    at = lambda q: np.median(c[order[max(0, int(q * (len(c) - 1)) - k): int(q * (len(c) - 1)) + k + 1]], axis=0)
    return {q: at(q) for q in (0.1, 0.5, 0.9)}
```

Convert to linear (`s/12.92` below 0.04045, `((s+0.055)/1.055)**2.4` above) before Principled.
Then build the surface the way the image-to-code tool did — its lantern out-read kiln's
v3 on texture detail (0.031 against 0.022 for the reference's 0.032):

- **Independent fields, never one derived from another.** Colour: multi-octave noise
  (three scales, e.g. 4 / 13 / 48 over the part) mixing the palette's dark and mid, with
  sparse bright wear specks toward its light. Roughness: *its own* noise, over a range
  (0.16–0.64 there), not the colour's inverse. Relief: fine pits plus broad dents. Cavity:
  AO. A single noise driving all four reads as the flat, blotchy "camouflage" of kiln's v1.
- **Give grime a direction.** Streaks run along a turned part's profile — vertical on a
  lathe. That needs **cylindrical UVs on turned parts** (u around, v along the height), not
  Smart UV Project, whose islands scatter any direction.
- **Metal can be metal.** The image-to-code lantern is Metallic 0.92 all over with a dark,
  warm colour field, and reads right; kiln's v3 split patina (Metallic ~0.2) from worn
  edges (Metallic 1) and also reads right. What fails is a *dark colour at high metallic
  without warmth*: it mirrors a grey studio. Choose either, and let `tools/fidelity_check.py`
  judge saturation, warmth and highlights.
- **Wear follows curvature — thresholded by percentile, on the part itself.** Cycles'
  Pointiness spans only 0.48–0.57 on a coarse mesh (measured on the tank), so a fixed
  threshold lands anywhere. Bake Pointiness, take the part's 90th and 99th percentiles as
  the ramp's ends, multiply by noise so edges wear in patches.
- **Bake colour through an Emission shader into a float image.** A DIFFUSE bake of a
  metallic surface comes out near-black; a byte sRGB target shifts the value. Baked this
  way a flat texel returns the sampled colour exactly (0.0174 against 0.0176 linear).
- **Relief ships as a normal map.** glTF has no bump. Wire the height field through a Bump
  node, bake type NORMAL, tangent space, into a Non-Color float image, and connect it
  through a Normal Map node — measured: mean (0.5, 0.5, 1) as a flat surface should be,
  and the export carries `normalTexture`.
- **Glass, the recipe that read right:** smooth shell (≥ 64 segments), roughness ~0.1, a
  clear coat (Principled *Coat* weight 1), alpha ~0.65, and a **frost texture** — sparse
  bright specks from high-frequency noise, gathered by a broad blotch field — in colour and
  alpha. Neutral tint unless the reference shows one.

Pack every generated image into the .blend (`bpy.ops.file.pack_all()`) before measuring or
exporting: an unpacked texture renders black, and `fidelity_check.py` now refuses it.

## 5. Review against the reference — measured, twice at most

Judging by eye over-corrects: on the bench, a first lantern came out too bright and
blotchy, its fix grey and flat — saturation 0.17 where the reference measures 0.33,
texture detail at a third of it. Measure instead. `tools/fidelity_check.py` renders the
model front-on, orthographic, as a silhouette and under a studio HDRI, scales it to the
reference's height and prints the gaps, largest first:

```bash
UA="blender-kiln"                                   # Poly Haven ToS: a unique User-Agent
curl -s -A "$UA" https://api.polyhaven.com/files/studio_small_09 \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['hdri']['1k']['hdr']['url'])" \
  | xargs curl -s -A "$UA" -o studio_small_09_1k.hdr
blender -b --factory-startup --python-exit-code 1 --python <skill>/tools/fidelity_check.py -- \
  --reference ref.png --model asset.blend --hdri studio_small_09_1k.hdr --out review/ \\
  --max-tris 5000                                    # the tier's top: rule 4 is reported, not blocked
```

It writes `overlay.png` (red: reference only, cyan: model only) and `side_by_side.png`,
and one `FIDELITY {...}` JSON line: silhouette IoU overall and per height band, width and
core-width differences per band, and per band the material numbers — luminance,
saturation, warmth (R−B), highlight share, texture detail, value spread. Look at both
images, then fix the listed gaps.

Read it with its limits, measured on the lantern:

- **The reference's camera and light are unknown.** A frontal orthographic render cannot
  match a slightly high perspective shot at the base; a few percent is noise.
- **Thin parts wreck band IoU.** A 2-px wire off by one pixel scores 0.2–0.4. Use the
  overlay for wires, loops and handles; trust IoU for bodies.
- **Two correction rounds at most**, each logged: what the numbers said, what changed.
  The image-to-code tool that ran eight vision passes spent ~5x the cost for a likeness
  this loop reaches.

## 6. What the measured lantern taught — general rules

- **Measure the thickness of thin parts from the pixels too**, not only the body. Tubes,
  wires and handles were guessed thin and set inboard; they were the largest silhouette
  gap (IoU 0.72 → the red bands of the overlay).
- **Model how parts meet as the inventory says**: an open loop whose legs enter the cap
  is not a closed ring on a clip.
- **Curved glass needs ≥ 64 segments and one smooth shell.** At 264 faces, a uniform
  semi-transparent globe shows its facets as bands, its back faces blending through.
  Take the frosting from the reference as an alpha/roughness texture; keep the tint
  neutral unless the reference shows one.
- **Metal must read warm and specular where it is worn.** Check saturation, warmth and
  highlights against the reference numbers, not against memory — a patina can be dark
  and still saturated.
