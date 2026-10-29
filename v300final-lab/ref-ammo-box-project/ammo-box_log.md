# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (GLB), web output `web/ammo-box_final.glb`
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto (standing answer: yes to every optional step; version before each kept)
- Storage: compact (intermediates kept and listed at hand-over — nobody to answer the cleanup question)
- 3D backend: none — scripted modelling in Blender (brief: no marketplace, no AI)
- Live view (Kiln Studio): off — unattended bench run, nobody to open the URL
- Output folder: /private/tmp/kiln-bench/v300final-lab/ref-ammo-box-project/work/generated-assets/ammo-box/
- Environment: macOS 26.6.1, Apple M4 Pro; Blender 5.2.2 LTS (open, factory scene, no file) via the
  official Blender Lab MCP (`mcp__blender__*`); gltf-transform + gltfpack present; PIL absent
  (image work done in Blender's Python).
- Factory scene at start (Camera, Cube, Light, no .blend): the build runs headless with
  `read_factory_settings(use_empty=True)`; the factory Cube is removed when the built .blend is
  opened in the live Blender (rule 6 exception, logged here).

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-lab/ref-ammo-box-project/refs/ammo_box.png (1024×1015 RGBA, already cut out)
- Subject: US M19A1-style .30 cal steel ammunition can, olive-drab paint, heavily rusted, closed lid.
- Assumptions (auto mode, nobody to ask):
  - Real size: usual M19A1 can, 273 (L) × 95 (W) × 184 (H) mm incl. lid — no scale in the photo.
  - Camera: 3/4 view of the long (stencilled) side as front (-Y) and the latch end (+X).
    Azimuth ≈ 52° (from the long/end edge ratio 682/330 px with L/W = 2.87), elevation ≈ 15°
    (estimate from the top edges' slope; no horizontal circle visible — an estimate, not a measure).
    Perspective is visible (near vertical edge 730 px vs far 630 px).
  - Unseen sides: back long side (+Y), hinge end (-X), underside. Kept plain and closed —
    no hinge, no markings invented there.
- Visual comparison: close match — parts, proportions and placement match; the front carries the photo's own stencil and wear (projection); remaining differences listed under Rounds and Photo projection.

### Inventory (from 2–3× crops in `crops/`)
- body: closed steel box, rounded vertical corners and bottom edges        → SM_AmmoBox_Body
- lid: flat top, rolled bead all round its rim, resting ON the body top    → SM_AmmoBox_Lid
- lid end flange at +X: raised strip with 5 dimples on top, skirt down the end wall → Lid
- raised flat strip across the lid's -X end                               → Lid
- handle strap: flat steel strap ~150 × 24 mm, -X end lifted ~28 mm on its wire, +X end resting → SM_AmmoBox_HandleStrap
- handle wires (2): U-loops, HOOKED through the brackets and through the strap ends → SM_AmmoBox_HandleWire_L / _R
- handle brackets (2): small pressed plates welded flat on the lid        → SM_AmmoBox_HandleBracket_L / _R
- hinge strip on the lid's end skirt: 5 domed rivets                      → SM_AmmoBox_LatchHinge
- latch lever: plate hanging from the hinge strip, round hole Ø≈44 mm, shoulders at top, bottom tab bent out → SM_AmmoBox_LatchLever
- recessed disc seen through the lever hole (ring edge on the end wall)   → Body
- catch bracket: bent plate WELDED on the body end, side lugs             → SM_AmmoBox_LatchCatch
- bail: rectangular wire loop HOOKED in the catch lugs, hanging, swung slightly out → SM_AmmoBox_LatchBail
- small vertical wire at the near corner from the lid bead to the hinge strip → SM_AmmoBox_LidWire
- stencil: "200 CARTRIGES / 7.62 MM,  M08 / CARTONS • M31", yellow, DIN-like condensed font,
  on a near-black repainted patch on the front; copied as the photo spells it ("CARTRIGES") → Body texture
- wear: rust on every edge, the lid end strip, hinge, lever, handle; pitted grey-pink flaking
  band on the front's upper third; (the dark band on the lid under the strap is the strap's cast shadow — not painted)   → material layers

### Palette (photo sRGB, 10th / 50th / 90th luminance percentiles)
- lid top paint: 0.125,0.133,0.106 / 0.133,0.141,0.114 / 0.204,0.165,0.129 (lighter patch 0.227,0.235,0.212)
- front dark patch: 0.043,0.051,0.043 / 0.071,0.071,0.063 / 0.090,0.086,0.082
- front worn band: 0.067,0.067,0.055 / 0.075,0.078,0.071 / 0.145,0.125,0.125
- end wall paint: 0.078,0.082,0.039 / 0.082,0.086,0.047 / 0.086,0.094,0.047
- rust (hinge strip): 0.208,0.118,0.075 / 0.267,0.141,0.098 / 0.318,0.184,0.114
- rust (lid end strip): 0.278,0.180,0.133 / 0.294,0.208,0.153 / 0.388,0.243,0.145
- stencil yellow (median of saturated pixels): 0.212,0.161,0.043
- The photo is underexposed (front paint at 0.07 sRGB is darker than any paint's albedo): base colours
  keep the palette's hue and ratios at a gain of ~2.2 in sRGB, to be checked by fidelity_check.

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Generation params: none — scripted

## Source
- Method: scripted modelling (Blender Python, headless build script `scripts/build_ammo_box.py`)
- Textures: Poly Haven `green_metal_rust` (paint base) and `rust_coarse_01` (rust wear), chosen
  against the photo's crops (thumbnails in `crops/ph/`)

## Pipeline
- [1] CONFIG + [2] BRIEF: done — brief reformulated as: realistic M19A1-style rusted OD-green ammo can,
  closed, strap handle on the lid, lever latch + wire bail on the +X end, yellow stencil on the front;
  balanced tier, GLB.
- [3] SOURCE: scripted (brief), Poly Haven CC0 scans for the materials.

- [4] IMPORT (scripted, built at size): `scripts/build_geo.py` → `versions/ammo-box_v1_geo.blend`.
  12 parts (SM_AmmoBox_*), 3,632 tris, 295.6 × 104.0 × 214.8 mm (length incl. latch+bail; height incl.
  the lifted handle; body+lid 182 mm), base at z = 0. Looked at: live Blender (framed 3/4) + `review/v1/`.
  The live Blender's factory scene (Cube) was replaced by opening this .blend (rule 6 exception).
- [5] CLEANUP (`scripts/cleanup.py`): transforms applied, merge 1e-5 (0 merged), normals recalculated,
  0 loose, 0 degenerate, fused edges 0, open edges 0 on every part. 3,632 tris — in the balanced range.
- Rounds (reference image), `review/front/`:
  - v1 (geometry, flat colours, measured on the .blend, az 52 / el 15): silhouette IoU 0.873; band 1
    (top) -30 % width, band 5 (bottom) +32 % — the overlay shows a perspective wedge (photo's near
    corner 730 px vs far 630 px: a perspective camera, the tool renders ortho), not a part.
    Camera re-read on the box's four edge slopes (end 0.22, long 0.405 = sin el / tan az, tan az · sin el):
    el ≈ 17.4°, az ≈ 53.6°, L/W = 2.87 (matches the assumed 273/95). Measured on the photo, not chosen by
    score — later rounds use az 54 / el 17. 32 joints looked at (`review/front/joints_sheet.png`):
    bail ends inside the catch ears, wires through the strap rolls and bracket bridges, rivets seated.
    Material numbers: saturation low in every band (0.23–0.29 vs 0.29–0.42) → texturing.
  - v2 (first texture, `scripts/build_tex.py`, 512 bake, GLB, az 54 / el 17): IoU 0.873 (shape unchanged).
    Diagnostic perspective fits (`scripts/box_fit.py`, `scripts/model_fit.py`, `review/fitdiag_v2/`): a plain
    box fits the photo at 0.945–0.950 for any W/L 0.33–0.42 and H/L 0.62–0.70 (one photo cannot separate depth
    from elevation; the model's 0.35 / 0.67 is on that plateau); the model's own hull fits 0.953 (az 48, el 19,
    0.8 m) with a tight outline → no geometry change. photo_project's own bounded fit: 0.931 (az 47.5, el 18.7).
    By eye (side_by_side): rust far below the photo's on edges, hardware, front worn band.
  - v3 = round 1, ONE change, rust coverage (rust_body 0.12→0.30, lid 0.18→0.25, hardware 0.62→0.85,
    wires 0.80→0.95, worn band +0.30→+0.55, edge gain 1.3→2.0): hardware/edges/front worn band now rust.
    Next largest: band 1 highlights 0.342 vs 0 — the lid reads grey-white (glossy paint). Kept.
  - v4 = round 2, ONE change, paint roughness 0.42–0.68 → 0.66–0.86 (old OD paint is matte): band-1
    highlights gone from the gap list, lid reads green as in the photo. Kept. Round cap reached.
  - Remaining, said not fixed: front worn band more orange than the photo's grey-pink mottling; saturation of
    bands 4–5 below the photo's (0.27 vs 0.42); luminance ~3× the photo's everywhere (the photo is
    underexposed — alarm, not target); stencil reads 7.3 mm low on the v3 face measure (perspective/elevation).
  - v5 (shape, needed by the optional projection — its camera fit refused v4 at 0.931): the tool's own
    silhouette overlay (`scripts/pp_overlay.py`, `review/fitdiag_v2/pp_overlay*.png`) showed two parts placed
    off the photo, which squeezed the fitted box: the bail swung 25° out, past the end face (photo: hanging
    close to the end, inside the outline) → 8°; the handle's lifted end 28 mm above the lid (photo ≈ 18 mm)
    → 18 mm. Tool fit from az 54 / el 17: 0.918 → 0.973 (az 50.8, el 18.1, 1.17 m). Re-baked at 1024 with
    the round-2 material unchanged. fidelity_check on `_original.glb`: silhouette IoU 0.873 → 0.918; band 1
    -15 % (was -31 %), band 5 +19 % (perspective wedge). uv_check 0 FAIL / 0 WARN, no floating part.
    v4 kept as `versions/ammo-box_v4_original.glb` / `versions/ammo-box_v4.blend`. 3,632 tris,
    286.2 × 104.0 × 204.8 mm.
- [5b] TEXTURING (final, 1024): one painted-steel shader for every part (`M_Metal_PaintedSteel_*_Procedural`,
  kept in the .blend with a fake user): Poly Haven `green_metal_rust` (tinted to OD 0.26,0.28,0.17 sRGB) +
  `rust_coarse_01` (tinted 0.45,0.24,0.14; grey-pink film 0.30,0.25,0.22 on the front's worn area), rust
  masked by Bevel-node edges, AO cavities and noise, per-part rust amount; dark repaint patch + yellow
  stencil (DIN Condensed Bold rendered to `textures/stencil_mask.png`, placed from the photo's text,
  perspective-corrected). Baked (Cycles, Emission for colour/roughness, tangent NORMAL) to two texture sets:
  Body (T_AmmoBox_Body_*) and Parts (T_AmmoBox_Parts_*, one atlas for lid + hardware + wires), each
  BaseColor (byte sRGB) / Roughness / Normal 1024 PNG. Metallic 0 (paint and rust are non-metals; no bare
  steel visible in the photo). Normal mean (0.5, 0.5, 1.0). uv_check: 12 meshes, 0 FAIL, 0 WARN.
  Attachment (BVH, 0.5 mm): no floating part. → `ammo-box.blend`, `ammo-box_original.glb` (v5: 5.47 MB).
  Final measure of `_original.glb`: IoU 0.873; gaps listed are the perspective bands + light-dependent lum.
  Looked at: live Blender, two opposite 3/4 views (material shading); `review/v4_final/` (q2, q4, top, under).

- Photo projection (optional, pre-approved by the standing answer; after the last round, shape final):
  `photo_project.py --view front --azimuth 54 --elevation 17 --erase-stencil '#806117'` on v5
  `_original.glb` → `review/project/`. Fitted IoU 0.973 (az 50.8, el 18.1, 1.17 m). Exposure gain 4.76
  (warned > 2 stops: that is the deliberate ×2.2 sRGB ≈ ×4.8 linear brightening of the underexposed photo's
  palette, so consistent). Photo-view SSIM 0.468 → 0.548, ΔE76 23.29 → 21.19 (partly circular). Trusted 13 %
  of texels (Body 17.8 %, Parts 7.7 %), touched 24 %; scripted stencil erased on 18,143 texels, kept on 483 unseen.
  Excluded: none. other_angles.png: back and lid unchanged; front now the photo's stencil, dark patch and flaking.
  Defects seen: a small remnant of the scripted stencil at the far left before "CARTONS" (outside the trusted
  zone); the "7" of "7.62" faded at the trust edge. Kept: projected = final. Before: `ammo-box_original.glb`,
  `versions/ammo-box_v5_before-projection.blend`. After: `ammo-box_projected.glb`; `ammo-box.blend` now holds the
  projected base colours (`*_BaseColor_Projected`, packed), the scripted ones kept with a fake user.

- [6] OPTIMIZE (auto, glTF): material audit (rule 19, map level): both materials export baseColor +
  metallicRoughness + normal textures, no procedural node on an exported material. gltf-transform as separate
  steps (rule 20): resize 1024 → WebP q90 → Draco. Final (projected): 5,509,836 → 386,816 bytes.
  Before-projection version: 5,465,592 → 382,808 bytes. Draco needs a decoder on the client.
  `ammo-box_preview.glb` = uncompressed copy of the projected GLB (extensionsUsed empty: opens in Quick Look).
- [7] EXPORT: `web/ammo-box_final.glb` (GLB, 386.8 kB, 3,632 tris, 12 meshes, Draco + WebP), measured as shipped:
  silhouette IoU 0.918 (az 54 / el 17, ortho), uv_check 0 FAIL / 0 WARN; renders `review/final/`.
  Saturation of bands 3–5 dropped after the projection (0.27 → 0.22, photo 0.37–0.42) — the projection
  brings the photo's dim, desaturated light into the base colour (documented limit). `ammo-box.blend` saved
  (save_version 0). studio.py checks: no WARN (triangles in range, 0.29 × 0.10 × 0.20 m, on the ground).
  Kiln Studio not started (unattended run).
- Files: root — ammo-box.blend, ammo-box_log.md, ammo-box_original.glb (before projection), ammo-box_projected.glb,
  ammo-box_preview.glb; web/ — ammo-box_final.glb, ammo-box_final_before-projection.glb. Intermediates kept
  (compact mode, nobody to answer the cleanup question): versions/ (v1–v5 .blend + GLBs), review/, crops/,
  textures/ (scans, bakes, stencil mask), scripts/.

## Licenses
- Reference image: user-provided.
- Poly Haven `green_metal_rust`, `rust_coarse_01`: CC0. Source: Poly Haven (polyhaven.com), via the public API.
- Font: macOS system font "DIN Condensed Bold" — used only to rasterise the stencil into the baked texture
  (no font file ships). 

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22 19:37
