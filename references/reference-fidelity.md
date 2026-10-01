# Reference Fidelity — when the user gives an image

Load this whenever a brief comes with a reference image and the asset is built by
script. It is the cheap half of what image-to-code pipelines spend dozens of vision
passes on: **measure the image instead of eyeballing it**, and spend the model's
attention only on what measuring cannot settle.

**Scale the procedure to the asset.** Every step below costs turns: a lantern went from
$1.90 to $3.52 once all of them ran. Match the effort to what the asset is for:

| Tier / use | Steps |
|---|---|
| lightweight, background prop | § 1 inventory, § 3 attachment, one § 5 measure of the shipped file |
| balanced (default) | all of § 1–5, two correction rounds |
| detailed, hero asset, character | all of it, plus the extra views of § 1, each measured |

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
step 3 checks. **Inventory from enlarged crops, not the whole image**: at full-image size
the lantern's top loop read as two legs entering the cap; a 3x crop shows a closed
pentagon on a hinge clip — and the review had praised the wrong version.

**Before modeling, settle what one photo cannot say:**

- **More views, when the object deserves it** — a hero asset, a character, anything whose
  back or underside will be seen. Ask for a side and a top view; each one given is
  measured in step 5 with its own `--view`. Parts no view shows are inventions: say which.
- **The real size.** A photo has no scale. Ask; otherwise take the object's usual size
  (a hurricane lantern is ~30 cm) and log it as an assumption. Measured: five
  reconstructions of one lantern, 23–52 % too tall, none of them saying so.
- **The camera's elevation.** A photo taken from above shows the top of every circle as an
  ellipse, whose minor/major ratio is sin θ. Read θ on the widest rim you can see; step 5
  renders at that elevation. Ignoring it inflates every stacked disc: fitted to a ~15°
  photo, a lantern's base grew 30 % taller than the real one's.

## 2. Measure the silhouette

**When a 3D template exists, measure it instead** — a generated mesh of the same photo
(TRELLIS.2, see `ai-generation.md`) or a scan. A photo bends proportions; the template
holds them. `tools/template_profile.py` scales it to the real height, fits the axis on the
foot, and prints per height the turned radius (what to lathe) and what stands around it —
tubes, guard, bail — with its distance from the axis and angular coverage:

```bash
blender -b --factory-startup --python-exit-code 1 --python <skill>/tools/template_profile.py -- \
  --template trellis.glb --height 0.294 --bands 40 --json profile.json
```

Measured on the bench's lantern: the TRELLIS.2 mesh read this way is within **0.6 mm**
of the real object's profile (median, 1.6 mm at worst, 27 heights); the best photo-read
reconstruction was at 1.1 mm and **9.7 mm** at worst, at the tank-to-burner step a 15°
camera hides. **Model from the measures, never from the template's surface**: it is
faceted, its texture smeared, and its thin parts break when decimated. Proportions come
from the template; materials still come from the photo (§ 4).

Without a template, the reference's own pixels give proportions in millimetres. For a turned object
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

Thin every ~10th point and feed them to a **smooth** curve — a NURBS spline of order 3–4 or
Bezier points with `AUTO` handles, beveled to the wire's measured thickness. Never a poly
spline: straight segments between the traced points read as kinks — a bail built that way
showed angular shoulders the reference does not have. Where the wire meets another part the trace catches that part — stop the
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
- **A metal's base colour is its reflectance — it cannot be dark.** Age is painted as
  NON-metal: rust, soot and dirt at Metallic 0, bare metal at 1, bright. The real Lantern_01
  is 46 % metallic, and its metal's base colour is 0.30 (sRGB luminance, median; 0.25 for the
  darkest tenth). Kiln's v7 was 100 % metal at 0.07–0.15 and rendered as near-black bronze,
  23 % darker than the real object under the same light. The image-to-code lantern, 100 %
  metal at 0.18, reads close (−3 %). `tools/fidelity_check.py` reports any material whose
  metallic texels sit below **0.15** — calibrated on those three, with no false alarm on the
  bench's truths (lantern, crate, chair) or on TRELLIS.2's output.
- **Wear follows curvature — thresholded by percentile, on the part itself.** Cycles'
  Pointiness spans only 0.48–0.57 on a coarse mesh (measured on the tank), so a fixed
  threshold lands anywhere. Bake Pointiness, take the part's 90th and 99th percentiles as
  the ramp's ends, multiply by noise so edges wear in patches.
- **Bake colour through an Emission shader into a float image — and convert it before
  export (next rule), always both.** A DIFFUSE bake of a metallic surface comes out
  near-black; a byte sRGB target shifts the value. Baked this way a flat texel returns
  the sampled colour exactly (0.0174 against 0.0176 linear) — but shipped as is, it
  exports black. This rule without the next one produced the worst lantern of the bench.
- **Convert a float bake to sRGB bytes before export — or the colour ships black.**
  Measured on Blender 5.2.2: the glTF exporter writes a linear float base-colour image
  into the PNG *without* the sRGB transfer — linear 0.2 lands as byte 51 instead of 124,
  and reads back as 0.03. A lantern reviewed at saturation 0.30 shipped at 0.12, its base
  colour near black, its metal a grey mirror. Converted first, the byte is 124 and the
  re-imported value 0.202:

```python
def to_srgb_byte(float_img):
    """A byte sRGB copy of a linear float image — what the glTF exporter writes correctly."""
    w, h = float_img.size
    lin = np.array(float_img.pixels[:], dtype=np.float32).reshape(-1, 4)
    rgb = np.clip(lin[:, :3], 0, 1)
    enc = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    out = bpy.data.images.new(float_img.name + "_sRGB", w, h, alpha=True, float_buffer=False)
    out.colorspace_settings.name = "sRGB"
    out.pixels = np.concatenate([enc, lin[:, 3:4]], 1).ravel().tolist()   # byte pixels are the encoded values
    out.pack()
    return out
```

  Swap it into the Image Texture node that feeds Base Color before exporting. Non-Color
  maps (roughness, metallic, normal) are data and export correctly as they are.
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
# --max-tris: the tier's top (rule 4: reported last, a reduction proposed only past 2x). --view/--elevation: where the photo's camera stood (§1)
blender -b --factory-startup --python-exit-code 1 --python <skill>/tools/fidelity_check.py -- \
  --reference ref.png --model asset_final.glb --hdri studio_small_09_1k.hdr --out review/ \
  --max-tris 5000 --view front --elevation 12 --azimuth 0
```

**Most product photos are 3/4 views: set `--azimuth`** — degrees the camera turns toward
the object's right (+X seen from the front). Read it like the elevation, before modeling:
from which side the photo sees the object, and how much. Measured on Poly Haven's
ammo_box against its own 3/4 preview: IoU 0.573 rendered level from the side, 0.925 at
azimuth 50°, elevation 20°. Without it, a 3/4 photo cannot be measured at all.

**Close the listed gaps; never push the score.** The real object itself scores ~0.80 IoU
against its own photo — the camera, the lens and the light differ. A reconstruction above
that has started copying the photo's perspective: the lantern that reached 0.898 against
the photo was the *worst* against the real object from every side. Fix the gaps the tool
lists — a band whose width is off by more than 8 %, a clearly wrong part — and stop.

**The last measure is of the file that ships — `_final.glb`, not the `.blend`.** A session
validated its lantern at saturation 0.30 in the .blend; the GLB it shipped read 0.12,
because the export had dropped the colour's transfer (§ 4). Only the shipped file is what
the user gets.

One call per reference view, **at the elevation you read on the ellipses — fixed before
modeling, never chosen by the score.** Picking the angle at which the model being built
scores best is circular: on the bench a session tried 10 / 15 / 20°, kept 20° because its
model fitted there, and shipped a base 27 % flatter than the real one. With a close
camera the ellipses open toward the bottom (read 9° at the cap, 12° at the bell, 24° at the
base on one photo): take the rim nearest mid-height. And never rescale the whole model to
raise the score — that same session narrowed every width by 5.7 %. **Never fit the model to a mismatched
view** — on the bench, the version that scored best against the photo (0.898, frontal)
was the *worst* against the real object seen from every side, because it had copied
the photo's perspective into the geometry.

It writes `overlay.png` (red: reference only, cyan: model only) and `side_by_side.png`,
and one `FIDELITY {...}` JSON line: silhouette IoU overall and per height band, width and
core-width differences per band, and per band the material numbers — luminance,
saturation, warmth (R−B), highlight share, texture detail, value spread. Look at both
images, then fix the listed gaps.

Read it with its limits, measured on the lantern:

- **The reference's camera and light are unknown.** A frontal orthographic render cannot
  match a slightly high perspective shot at the base; a few percent is noise.
- **Openwork is judged on proportions and by eye, not by silhouette.** A chair seen from
  the side is posts and rails: its silhouette overlaps nothing whatever its accuracy
  (0.12–0.16 for every orientation of a good reconstruction). For chairs, frames, lattices,
  cages: compare width, depth and height ratios and the heights of key features (seat,
  arms) against the reference, and look at the side-by-side.
- **Thin parts wreck band IoU.** A 2-px wire off by one pixel scores 0.2–0.4. Use the
  overlay for wires, loops and handles; trust IoU for bodies.
- **Two correction rounds at most — three measures in all**, each logged: what the numbers
  said, what changed. At 16–32 samples and 512 px bakes during review; 1024 only for the
  final bake. Eight measures and ten bakes took one session to 105 turns and $5.63.
- **Tick the inventory at the final review**, line by line, on an enlarged crop of the
  reference next to the same crop of the render: present and right, or not. A lantern's
  pentagon loop, listed in its own inventory, came out a rounded teardrop that no number
  flagged — numbers see silhouettes and colours, not whether a detail is still there.
- **Correct half-way.** A gap is a direction, not a dose: one session moved saturation
  from 0.17 straight to 0.38 for a target of 0.33. Move halfway, measure, finish.
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
- **Know which numbers depend on the light.** Poly Haven's own Lantern_01, measured with
  its own textures under the tool's HDRI against its own preview, reads saturation 0.33
  for 0.32 — reliable — but luminance +0.05 and highlights 2.5 % for 1.5 %: the HDRI is
  not the preview's. So **saturation, detail and shape are targets; luminance and
  highlights are only alarms when far off.** A reconstruction at 2.5 % highlights matched
  the real object, not "too reflective".
- **Never tune luminance to the photo.** Lantern v7 matched the photo's luminance to 0.003
  — and was 23 % darker than the real object under the tool's light, because the real one
  renders 28 % brighter there than in its own photo. The photo's light is unknown, so a
  match proves nothing; when luminance is off, fix the MATERIAL (dark metal, base colour
  range), never the number. Warmth over luminance is no way out either: it held on the
  brass and broke on the painted crate (0.18 rendered for 0.50 in the photo), where a
  dielectric's white sheen under a softbox dilutes the colour.
- **Fine detail is what reads as real.** At 0.022–0.024 texture detail against the
  reference's 0.032 (the real asset measures 0.028 under the same light), surfaces read
  clean and new. Add it as **fine features** — scratches (thin lines along the part's u
  direction), pits, edge nicks — **never by raising the relief's amplitude**: a session that
  did reached the reference's detail number with a surface that read as lumpy cast iron,
  and had to undo it. The number is a proxy; the look decides.
- **Metal must read warm and specular where it is worn.** Check saturation, warmth and
  highlights against the reference numbers, not against memory — a patina can be dark
  and still saturated.
