# Reference Fidelity — when the user gives an image

Load this whenever a brief comes with a reference image and the asset is built by
script. **Measure the image instead of eyeballing it**, and spend attention only on
what measuring cannot settle. Every number below is a tool threshold or a method
setting — none is a value to reach on a particular object. The photo is the only
source of what this asset looks like.

**Scale the procedure to the asset.** Every step costs turns:

| Tier / use | Steps |
|---|---|
| lightweight, background prop | § 1 inventory, § 3 attachment, one § 5 measure of the shipped file |
| balanced (default) | all of § 1–5, two correction rounds |
| detailed, hero asset, character | all of it, plus the extra views of § 1, each measured |

## 1. Inventory the details before modeling

List every identity-defining detail visible in the image, and the part it belongs
to — in the log, before the first line of geometry. A detail with no part is a
detail that will be forgotten.

```
- handle: closed wire loop, legs INSERTED into the lid          → SM_<Asset>_Handle, parent Lid
- rim: rolled lip, slightly thicker than the wall                → Body
- vents: dark slots under the lid, all around                    → Lid
- window: glass, tint and frosting AS THE PHOTO SHOWS            → Window (its own material)
```

Write *how* parts meet ("inserted", "hooked", "welded", "resting") — that is what
step 3 checks. **Inventory from enlarged crops, not the whole image**: at full size a
small part reads as something it is not; a 3x crop shows what it is.

**Before modeling, settle what one photo cannot say:**

- **More views, when the object deserves it** — a hero asset, a character, anything whose
  back or underside will be seen. Ask for a side and a top view; each one given is
  measured in step 5 with its own `--view`. Parts no view shows are inventions: say which.
- **The real size.** A photo has no scale. Ask; otherwise take the object's usual size
  and log it as an assumption. Never leave it implicit: an unstated size drifts by tens of
  percent and nothing flags it.
- **The camera's elevation.** A photo taken from above shows the top of every circle as an
  ellipse, whose minor/major ratio is sin θ. Read θ on the widest rim you can see; step 5
  renders at that elevation. Ignoring it inflates every stacked disc.

## 2. Measure the silhouette

**When a 3D template exists, measure it instead** — a generated mesh of the same photo
(TRELLIS.2, see `ai-generation.md`) or a scan. A photo bends proportions; the template
holds them. `tools/template_profile.py` scales it to the real height, fits the axis on the
foot, and prints per height the turned radius (what to lathe) and what stands around it —
tubes, guards, handles — with its distance from the axis and angular coverage:

```bash
blender -b --factory-startup --python-exit-code 1 --python <skill>/tools/template_profile.py -- \
  --template template.glb --height <real height, m> --bands 40 --json profile.json
```

`--height` is the object's REAL height — asked, or the usual size stated as an assumption
(§ 1). The template cannot give it: a generated mesh is always 1 m tall.

**Model from the measures, never from the template's surface**: it is faceted, its
texture smeared, and its thin parts break when decimated. Proportions come from the
template — **heights AND widths, and where the parts around stand** (their distance from
the axis). Widths read off the photo's pixels instead are narrowed by its perspective.
Materials and small details still come from the photo (§ 4).

Without a template, the reference's own pixels give proportions in millimetres. For a turned object
(bottle, vase, barrel, lamp) the profile is usable directly as a lathe profile.
Take the **core width** — the opaque run through the vertical axis — not the full
width, which measures whatever stands around the body (a handle, a bail).

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
control points drift, and a guessed curve misses the shape of its peak:

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
spline: straight segments between the traced points read as kinks. Where the wire meets
another part the trace catches that part — stop the range above it.

## 3. Check that every part is attached

Measure surface to surface with a BVH — vertex-to-vertex distances overstate gaps on
coarse meshes. Anything above 0.5 mm from every other part floats.

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

Contact is not insertion: a part that touches another at one point passes this check
and still reads wrong. **A part that joins another ENTERS it** — its end runs past the
surface by at least its own radius, its section unchanged, with at most a small fillet
where it meets. A foot, a flange or a saddle only when the photo shows one clearly, and
then judged against the same crop of the photo. Never a flat cut resting on a curve, and
never a tube widened or flattened to make a foot — it reads as a tongue. No distance can
judge a joint, so `fidelity_check.py` renders every end of a long part that touches
another — the two parts alone, flat grey, two views, in `review/joints/` — and **each one
is looked at before the inventory line is ticked**.

## 4. Materials from the reference, not from memory

**One material per PHYSICAL material** — the body's metal is one metal, the glass
another, a different alloy another only if the photo shows one. Wear, patina and soot are
layers WITHIN that material, not materials of their own: one material per part makes
every part read as a different alloy. **Texture sets may still be per major part** — one
UV atlas over many parts starves the large ones — but baked from that one shader.

Sample each region's **range**, not only its median — the surface lives between a dark
and a light that the image shows:

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

Convert to linear (`s/12.92` below 0.04045, `((s+0.055)/1.055)**2.4` above) before
Principled. **The base colour comes from this palette** — the photo's own dark, mid and
light — not from a figure about the material in general.

**Start from a scanned texture set whenever the material family has one** — rust, chipped
or worn paint, galvanised or corroded metal, wood, plaster, stone, fabric. Procedural
noise makes a smear where a scan has flakes, pits, runs and chips; that is the difference
between "dirty" and "rust". Poly Haven's textures are CC0, free, and reachable without a
key (`https://api.polyhaven.com/assets?type=textures&categories=metal` lists them with
their tags). **Look before choosing**: each one has a thumbnail at
`https://cdn.polyhaven.com/asset_img/thumbs/<id>.png?width=256&height=256` — open it next
to the photo's crop of that region, and keep the one whose surface reads like it.

```python
import bpy, json, os, sys, urllib.request

UA = {"User-Agent": "blender-kiln"}              # Poly Haven ToS 2.4: a unique User-Agent

def fetch_texture_set(asset_id, folder, res="1k"):
    """Download a Poly Haven texture set (CC0): colour, roughness, OpenGL normal, AO.
    Returns {channel: path}. Credit 'Poly Haven (polyhaven.com)' in the asset log (ToS 2.5)."""
    req = urllib.request.Request(f"https://api.polyhaven.com/files/{asset_id}", headers=UA)
    files = json.load(urllib.request.urlopen(req))
    os.makedirs(folder, exist_ok=True); out = {}
    for ch, key in (("color", "Diffuse"), ("rough", "Rough"), ("normal", "nor_gl"), ("ao", "AO")):
        if key not in files:
            continue
        url = files[key][res]["jpg"]["url"]; path = os.path.join(folder, os.path.basename(url))
        if not os.path.exists(path):
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(path, "wb") as f:
                f.write(r.read())
        out[ch] = path
    return out

def scanned_layer(nt, maps, scale=4.0, tint=None):
    """Nodes that read a scanned set by box projection on the object's coordinates, so it
    needs no UVs while you build; bake it to the asset's UVs before export. Returns the
    colour, roughness and normal output sockets. `tint`: a linear RGB to multiply the
    colour toward (the photo's palette), or None."""
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale,) * 3; nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def tex(path, data):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True)
        t.projection = "BOX"; t.projection_blend = 0.2
        if data:
            t.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"]); return t
    col = tex(maps["color"], False).outputs["Color"]
    if tint is not None:
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0; mix.inputs["B"].default_value = (*tint, 1)
        nt.links.new(col, mix.inputs["A"]); col = mix.outputs["Result"]
    rough = tex(maps["rough"], True).outputs["Color"]
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tex(maps["normal"], True).outputs["Color"], nm.inputs["Color"])
    return col, rough, nm.outputs["Normal"]
```

Then: the **base layer** is the set that matches the region's main surface (the paint, the
bare metal), **tinted** toward the photo's palette mid (`tint`); the **wear layer** is a
second set (rust, bare metal) **masked by the form** — curvature for edges, AO for
cavities and seams, with noise only breaking the mask's border, never making it. Scale
each set to the asset's real size (a scan covers roughly a metre; a 30 cm part repeats it
a few times). Box projection needs no UVs while you build; **bake** the result to the
asset's UVs (the Emission bake below, then `to_srgb_byte`) before export — glTF carries
textures, not node trees. Credit `Source: Poly Haven (polyhaven.com), via the public API`
in the asset log (ToS 2.5). No set fits a material (polished brass, a specific alloy)?
Build it procedurally as below.

Building it procedurally, or adding to a scanned base:

- **Colour, roughness and metal vary TOGETHER, in the same places.** That is what makes a
  surface read aged rather than new: cavities and the undersides of rims darker, rougher
  and duller; edges and handled spots lighter, smoother, barer. Each field has its own
  noise on top (never one noise driving all four — that reads as camouflage), but they
  share the same places of wear. A surface where only the colour varies, over a uniform
  roughness, reads clean however its colour is mottled.
- **Independent fields, at three scales.** Colour: multi-octave noise (e.g. 4 / 13 / 48
  over the part) between the palette's dark and mid, with sparse light wear toward its
  light. Roughness: its own noise, over a real range, not the colour's inverse. Relief:
  fine pits plus broad dents. Cavity: AO.
- **Add ageing ONE layer at a time**, the one the photo shows most, then measure. Several
  layers added at once smear into each other and the surface loses the very grain they
  were meant to give.
- **Give grime a direction — faintly.** Streaks run along a turned part's profile —
  vertical on a lathe. That needs **cylindrical UVs on turned parts** (u around, v along
  the height), not Smart UV Project, whose islands scatter any direction. They modulate
  the surface; regular stripes read as wood grain.
- **A metal's base colour is its reflectance — it cannot be dark.** Darkened to paint age,
  a metal becomes a black mirror under any light. Tarnish and patina STAY METAL, darker and
  rougher; only crusts — thick rust, soot, caked dirt — are non-metal, on a minority of the
  surface. A non-metal reflects WHITE: a metal painted mostly as non-metal patina reads
  grey under a studio light. `fidelity_check.py` reports a metal below a physical floor,
  and a metal painted mostly as non-metal.
- **The bare metal is ONE region following the form, with soft edges — never a thresholded
  noise**, which scatters it into islands and reads as camouflage. How much is bare is no
  target: it sits where the form wears and fades into the patina. `fidelity_check.py`
  reports a metallic mask both scattered and hard-edged.
- **Wear follows curvature — thresholded by percentile, on the part itself.** Cycles'
  Pointiness spans a narrow range on a coarse mesh, so a fixed threshold lands anywhere.
  Bake Pointiness, take the part's 90th and 99th percentiles as the ramp's ends, multiply
  by noise so edges wear in patches.
- **Bake colour through an Emission shader into a float image — and convert it before
  export (next rule), always both.** A DIFFUSE bake of a metallic surface comes out
  near-black; a byte sRGB target shifts the value. Baked this way a flat texel returns
  the sampled colour exactly — but shipped as is, it exports black.
- **Convert a float bake to sRGB bytes before export — or the colour ships black.**
  Measured on Blender 5.2.2: the glTF exporter writes a linear float base-colour image
  into the PNG *without* the sRGB transfer — linear 0.2 lands as byte 51 instead of 124,
  and reads back as 0.03. Converted first, the byte is 124 and the re-imported value 0.202:

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
- **Glass:** smooth shell (≥ 64 segments), roughness ~0.1, a clear coat (Principled *Coat*
  weight 1), and a **frost texture** — sparse bright specks from high-frequency noise,
  gathered by a broad blotch field — in colour and alpha. **Tint, darkness and opacity from
  the photo**, sampled like any region: a dark smoked glass is a dark tinted glass, never
  clear by default.

Pack every generated image into the .blend (`bpy.ops.file.pack_all()`) before measuring or
exporting: an unpacked texture renders black, and `fidelity_check.py` refuses it.

## 5. Review against the reference — measured, twice at most

Judging by eye over-corrects — too bright and blotchy, then grey and flat. Measure
instead. `tools/fidelity_check.py` renders the model front-on, orthographic, as a
silhouette and under a studio HDRI, scales it to the reference's height and prints the
gaps, largest first:

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
from which side the photo sees the object, and how much. Without it, a 3/4 photo cannot be
measured at all.

**Close the listed gaps; never push the score.** A real object scores well under a
perfect IoU against its own photo — the camera, the lens and the light differ. A
reconstruction pushed past that has started copying the photo's perspective into the
geometry, and is worse from every other side. Fix the gaps the tool lists — a band whose
width is off by more than 8 %, a clearly wrong part — and stop.

**The last measure is of the file that ships — `_final.glb`, not the `.blend`.** An
export can change what you see (§ 4: a float colour ships black). Only the shipped file is
what the user gets.

One call per reference view, **at the elevation you read on the ellipses — fixed before
modeling, never chosen by the score.** Picking the angle at which the model being built
scores best is circular. With a close camera the ellipses open toward the bottom: take the
rim nearest mid-height. Never rescale the whole model to raise the score.

It writes `overlay.png` (red: reference only, cyan: model only) and `side_by_side.png`,
and one `FIDELITY {...}` JSON line: silhouette IoU overall and per height band, width and
core-width differences per band, and per band the material numbers — luminance,
saturation, warmth (R−B), highlight share, texture detail, grain, value spread. Look at
both images, then fix the listed gaps.

Read it with its limits:

- **The reference's camera and light are unknown.** A frontal orthographic render cannot
  match a slightly high perspective shot at the base; a few percent is noise.
- **Know which numbers depend on the light.** Saturation, grain and shape hold across
  lights; **luminance and highlights depend on the photo's unknown light: alarms, never
  targets.** When luminance is off, fix the MATERIAL (dark metal, the palette), never the
  number — matching a photo's luminance under a different light proves nothing.
- **Openwork is judged on proportions and by eye, not by silhouette.** A chair seen from
  the side is posts and rails: its silhouette overlaps little whatever its accuracy. For
  chairs, frames, lattices, cages: compare width, depth and height ratios and the heights
  of key features against the reference, and look at the side-by-side.
- **Thin parts wreck band IoU.** A 2-px wire off by one pixel scores very low. Use the
  overlay for wires, loops and handles; trust IoU for bodies.
- **Two correction rounds at most — three measures in all**, each logged: what the numbers
  said, what changed. **One material problem per round** — the largest the review shows —
  then measure again; fixing several at once regresses the surface while every fix reads
  "applied". At 16–32 samples and 512 px bakes during review; 1024 only for the final bake.
- **Tick the inventory at the final review**, line by line, on an enlarged crop of the
  reference next to the same crop of the render: present and right, or not. Numbers see
  silhouettes and colours, not whether a detail is still there.
- **Correct half-way.** A gap is a direction, not a dose. Move halfway, measure, finish.

## 6. General rules

- **Measure the thickness of thin parts from the pixels too**, not only the body. Tubes,
  wires and handles guessed thin and set inboard are the largest silhouette gap.
- **Model how parts meet as the inventory says**: an open loop whose legs enter a cap is
  not a closed ring on a clip.
- **Round parts need enough sides to stay round up close**: 16 or more around a tube, 32
  or more round a turned body, shade smooth; the triangle range is a guide, not a cap.
- **Curved glass needs ≥ 64 segments and one smooth shell**, or a semi-transparent shell
  shows its facets as bands, its back faces blending through.
- **Fine detail is what reads as real.** Add it as **fine features** — scratches (thin
  lines along the part's u direction), pits, edge nicks — **never by raising the relief's
  amplitude**, which reads as lumpy cast metal. The number is a proxy; the look decides.
