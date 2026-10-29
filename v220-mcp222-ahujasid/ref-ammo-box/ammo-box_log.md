# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modeling in Blender 5.2.2 LTS (blender-mcp addon 1.8, protocol 14) — no marketplace model, no AI generation (brief)

## Reference Image
- Path: /private/tmp/kiln-bench/v220-mcp222-ahujasid/ref-ammo-box/refs/ammo_box.png (1024x1015, alpha)
- Single 3/4 view only. Back, left end and underside are not shown: they are modelled as plain
  continuations of what is visible (back = front without stencil, left end = plain wall). Stated as invention.

### Camera & proportions (measured, before modelling)
- 7 visible box corners fitted with a pinhole camera (scripts/camfit.py), two fits (principal point
  free / fixed): W/L = 0.455-0.467, H/L = 0.74-0.78. Camera elevation ~20 deg, azimuth ~47 deg toward
  the latch end (+X), long lens on a strong 3-point perspective (verticals converge downward).
- **Real size — assumption** (photo has no scale): length 0.30 m, matching a common US steel ammo can;
  width and height from the measured ratios → **0.30 x 0.14 x 0.23 m** (L x W x H incl. lid).
  Note: a real M2A1 can is lower (H/L ~0.62); the reference is taller, and the reference wins.

### Inventory (before geometry)
- body: tall rectangular steel can, rounded vertical corners, painted olive drab, heavy rust wear   → SM_AmmoBox_Body
- lid: flat top, skirt folded down over the body top, overhangs body by a few mm, rolled top edges  → SM_AmmoBox_Lid (rests on Body)
- stencil: 4 lines yellow "200 CARTRIGES / 7.62 MM,  M 08 / CARTONS  M31" on the long side          → texture layer on Body (front, -Y)
- carry handle: flat steel strap lying along the lid's length                                        → SM_AmmoBox_HandleStrap
- handle clips: two stamped rectangular plates welded on the lid, one per strap end                  → SM_AmmoBox_HandleClips (welded to Lid)
- handle wires: two wire loops, legs INSERTED into the clips, hooked through the strap's rolled ends  → SM_AmmoBox_HandleWires
- hinge band: horizontal plate across the top of the latch end, row of 5 rivet domes                 → SM_AmmoBox_HingeBand (welded to Body)
- lid wire: wire hook on the left of the latch end, from the lid skirt down into the hinge band      → SM_AmmoBox_LidWire
- latch lever: vertical plate, rounded/chamfered corners, large round hole, lies flat on the end     → SM_AmmoBox_LatchLever (rests on Body)
- seal disc: circular embossed disc seen through the lever's hole                                    → part of SM_AmmoBox_LatchLever group (Body face)
- lower hinge: bent bracket with two knuckle tabs at the lever's foot                                → SM_AmmoBox_LatchHinge (welded to Body)
- bail: rectangular U wire hanging from the two knuckles                                             → SM_AmmoBox_LatchBail (legs INSERTED into the knuckles)

## Materials (sampled from the reference, scripts/palette.py)
- Photo is a dim render: luminances are low everywhere; hues are taken from it, albedo kept physical.
- lid paint mid sRGB (0.227, 0.231, 0.208) — olive grey-green; side paint in shade (0.043, 0.047, 0.035)
- end face (0.086, 0.090, 0.047) — olive, yellow-green
- rust on handle / rivet band: sRGB (0.224, 0.149, 0.114) / (0.267, 0.145, 0.098) — warm brown-orange
- stencil yellow: sRGB median (0.235, 0.176, 0.043) — mustard
- One physical material: painted steel, with rust as a layer within it (more rust on hardware).

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Hunyuan3D params: n/a (scripted)

## Source
- Method: scripted
- Textures: Poly Haven `green_metal_rust` (paint) and `rusty_metal_sheet` (rust), 1k, CC0

## Pipeline
- Scene: Blender factory scene (Cube, Camera, Light) — default Cube removed before building (rule 6 exception).
- Build (scripts/build.py): 11 objects, all parented to SM_AmmoBox_Body, origin at centre of base, 1 unit = 1 m.
  bbox 0.314 x 0.149 x 0.240 m (lid overhang + latch hardware included).
- Cleanup (scripts/cleanup.py): transforms applied, weld keeping shading (120 verts merged, all on wires/band),
  normals recalculated, 0 loose, 0 boundary edges; 1 fused edge in HingeBand (band/tab overlap) split → 0 fused.
- Attachment (BVH, 0.5 mm): every part touches another. Body↔Lid and Lid report 4.5 / 1.9 mm "floats" by
  vertex sampling only — the body runs up inside the lid skirt (interpenetrating), so they are joined.
  Joint renders (review/*/joints, 25) looked at: bail legs enter the knuckles, handle wires enter clips and
  strap rolls, lid wire curls into the band tab.
- Texturing (scripts/materials.py → scripts/bake.py): one painted-steel shader group (NG_AmmoBox_PaintedSteel),
  Poly Haven scans box-projected: green_metal_rust (paint, tinted to the photo's olive) + rusty_metal_sheet
  (rust, tinted to the photo's brown); rust mask from form (bevel-normal edges, AO cavities) + broad patches
  biased high + faint vertical streaks, noise only on the border; stencil = rendered text mask on the front.
  Two texture sets baked from that one shader: Shell 2048 (body, lid), Hardware 1024 (bias +0.38 rust).
  Colour via Emission bake → sRGB bytes; roughness; tangent normal (mean 0.501, 0.5, 1.0). Metallic 0 (paint/rust).
- Tris: 3,456 (balanced prop 1.5-5K) — 1,496 of them in the three round wire parts (handle wires, bail, lid wire).

## Review (tools/fidelity_check.py, elevation 20, azimuth 47, studio_small_09)
- Round 1 (first bake): IoU 0.917. Paint too light and too saturated green vs the photo's dark olive → paint
  tint darkened half-way (multiply 0.42/0.40/0.32, 30 % toward dark olive).
- Round 2: IoU 0.917, paint now dark but too clean/grey; largest gap = rust coverage → wider edge wear,
  more broad patches biased to the upper walls (photo: rust stains high, dark paint low), streaks kept faint
  after they read as wood grain.
- Final, on ammo-box_final.glb (shipped file): IoU 0.917. Shape gaps are the photo's strong 3-point
  perspective vs an orthographic render (bottom band +24 %, top band -12 %), not a modelling error — the
  proportions come from the 7-corner camera fit. Remaining material gap: the model is lighter and
  less rusty than the photo (sat -0.11 to -0.22 per band); luminance is light-dependent (photo dim).
- Inventory at final review: body ✓, lid with overhanging skirt ✓ (skirt shallower than photo), stencil ✓
  (3 lines, same text; Blender's default font, lighter than the photo's DIN-like face), handle strap ✓ (lies
  flat; the photo's is propped up on one wire), 2 clips ✓, handle wires ✓, hinge band + 5 rivets ✓,
  lid wire ✓, latch lever with round window ✓, seal disc ✓, lower hinge knuckles ✓, bail ✓.
- Visual comparison: close match on proportions and parts; partial match on weathering (cleaner than photo).

## Optimize
- gltf-transform resize 1024 → webp q90 → draco (individual steps, rule 20; no simplify).
- 8.99 MB → 0.28 MB (-96.8 %). Draco needs a decoder on the client (three.js DRACOLoader, Babylon, Unity glTFast...).

## Export
- ammo-box_original.glb 8.99 MB (2048/1024 PNG) | ammo-box_final.glb 0.28 MB (1024 WebP, Draco) | 3,456 tris | glTF 2.0
- ammo-box.blend 12.2 MB — packed textures, procedural source materials (*_Src), node group, StencilScene.

## Licenses
- green_metal_rust, rusty_metal_sheet textures, studio_small_09 HDRI (review only): CC0 — Source: Poly Haven
  (polyhaven.com), via the public API.
- Geometry, stencil, shader: original, scripted for this asset.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21 13:05
