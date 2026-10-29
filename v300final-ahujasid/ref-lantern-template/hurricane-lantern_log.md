# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (game asset)
- Tier: balanced (prop 1.5-5K tris, soft; up to 10K reported, not cut)
- Style: realistic
- Mode: auto
- Storage: compact
- Backend: none — scripted modelling (brief: no marketplace, no AI generation)
- Live view: off (auto run, nobody watching the Studio page)
- Output: /private/tmp/kiln-bench/v300final-ahujasid/ref-lantern-template/work/generated-assets/hurricane-lantern
- Environment: macOS, Apple M4 Pro; Blender 5.2.2 LTS, MCP addon 1.8 (protocol 14, up to date); gltf-transform + gltfpack present
- Scene at start: Blender factory scene (Cube, Camera, Light, unsaved) → Cube removed before building (rule 6 exception)

## Reference Image
- Visual comparison: close match (proportions from the template, parts and materials from the photo)
- Path: refs/Lantern_01.png (394×1023, RGBA — already cut out, no cut-out step needed)
- Template: refs/trellis/lantern_trellis.glb — profile measured only (`review/template_profile.json`), mesh and texture NOT shipped
- Assumptions (auto mode, not asked):
  - Real size: 0.36 m total height with the bail raised (Feuerhand-276 class lantern; body to cap top ~0.25 m)
  - Camera elevation: ~15° (cap ellipse minor/major ≈ 0.21 → 12°, fount bottom ≈ 0.39 → 23°; rim nearest mid-height used), azimuth 0 (front view)
  - Unseen back: plain, closed, mirrored from the front where the part is turned; the filler cap and the oil streak are front-only
- Scale: 0.352 mm/px (1023 px = 0.36 m)

### Inventory (from 3× crops `review/crops/`)
- fount: squat cylinder r≈5.8 cm, 0-4.5 cm, rolled bottom bead, 2 pressed ribs on its side, domed shoulder up to the burner → SM_HurricaneLantern_Fount
- filler cap: short screw cap r≈1.1 cm on the shoulder front-right, rim + flat top, INSERTED into the shoulder; dark oil streak running down from it (texture) → SM_HurricaneLantern_FillerCap
- burner: turned neck r≈1.9-2.4 cm (5-7.4 cm) seated IN the fount top, flaring into the globe seat (gallery cup r≈3.4, 7.4-8.6 cm, rolled lip) → SM_HurricaneLantern_Burner
- wick knob: small vertical disc r≈0.8 cm on a shaft that ENTERS the burner, right side (+X) at z≈6.5 → SM_HurricaneLantern_WickKnob
- globe: glass, ovoid r max≈4.15 cm at z≈11.5, 8.3-17.8 cm, neck r≈2.5 at the top; smoked near-black, frosted specks, burner faintly visible → SM_HurricaneLantern_Globe (own material)
- guard wires: thin brass wires crossing in an X over the globe, helical, from the chimney skirt to the gallery, ends INSERTED in both → SM_HurricaneLantern_GuardWires
- lift lever: horizontal wire rods at z≈8 from the gallery to each tube, a bent hook lever on the right, a small U clip on the left tube → SM_HurricaneLantern_LiftLever
- air tubes: two tubes Ø≈1.6 cm, centre r≈5.3 cm at the top → ≈6.2 cm at the bottom; top bend into a horizontal arm ENTERING the chimney at z≈20.5; bottom bend ENTERING the fount shoulder at z≈5.5, with a flat gusset at the joint → SM_HurricaneLantern_Tubes
- chimney (upper air chamber): cylinder r≈3.2 cm, 19.3-23.3 cm, one bead at ≈20.3, flaring bell skirt to r≈4.1 at 18.3 with rolled edge → SM_HurricaneLantern_Chimney
- vent neck: r≈2.4 cm, 23.3-24.4 cm, dark rectangular slots all around → Chimney
- cap: flat disc r≈3.6 cm at ≈24.7, rolled rim, raised stepped centre to ≈25.7 → SM_HurricaneLantern_Cap
- top ring: pentagonal wire loop ≈3.4 cm wide, 25.6-29.2 cm, its foot HOOKED in a small clip on the cap → SM_HurricaneLantern_TopRing
- bail: wire Ø≈2.8 mm, apex at 36 cm with a small kink, arching down in the front plane; ends HOOKED into ears on the tube tops at z≈19.5, x≈±6 cm → SM_HurricaneLantern_Bail
- Materials: ONE metal (dark aged bronze: wear lighter brass on edges/wires, tarnish darker and rougher, grime in cavities) + ONE glass (smoked)
- Palette (sRGB, 10/50/90 %): fount (24,18,14)/(39,32,28)/(73,57,45) · bell (18,13,10)/(37,28,22)/(75,58,43) · tube (15,10,7)/(37,26,20)/(85,58,41) · wires (25,18,12)/(48,35,22)/(101,73,47) · cap top (33,28,25)/(52,49,47)/(85,84,82) · globe (16,15,15)/(26,25,25)/(66,59,56)

### Template profile (0.36 m), turned radius cm by height cm
fount 5.86@0.4 · 5.58@2.2 · 4.98@4.0 · 3.18@5.0 · burner 1.83@6.7 · seat 3.37@7.6 · globe 3.91@9.4, 4.17@11.2, 4.03@13.1, 3.45@14.8, 2.45@17.5 · skirt 4.11@18.4 · chimney 3.2-3.3@19.3-22.1 · neck 2.37@23.8 · cap 3.51@24.8 · ring top 29.2 · bail top 35.5. Tubes centre 5.2@19.3 → 6.6@7.6, Ø≈1.7.

## Prompts (copy-paste ready)
- None — scripted from the user's photo (source: user image)

## Source
- Method: scripted modelling in Blender (user's choice in the brief; marketplace and AI excluded)

## Pipeline
- BRIEF: confirmed by the brief itself (auto mode); assumptions above
- SOURCE/IMPORT (scripted, `scripts/build_lantern.py`): 13 parts, lathe profiles (32 seg metal, 64 seg glass, cylindrical UVs) + swept tubes/wires (centripetal Catmull-Rom, parallel-transport frames). 9,972 tris after round 1 (balanced top 5K: 2.0× — spent on round turned parts, 64-seg globe, wires; reported, not cut — the build itself sets the count). World size on the vertices 0.146 × 0.117 × 0.361 m, base on z=0, origins at the base centre
- Rounds (reference image, `review/front/`, elevation 15°, azimuth 0):
  - v1 (grey, placeholder materials): silhouette IoU 0.801, face IoU 0.60 (f 0.89, offset +2.3 / -1.1 mm). Gaps: lower tubes/base wider (+6-7 %, expected from the photo's perspective — kept, template widths), bail arch ~3 % wider than the photo. Tool flagged 11,708 tris > 2× tier
  - changed for v2: bail upper arch narrowed 3.5 % (ramped in above z 0.22 m); counts trimmed in the build (tube/wire sampling, hidden profile points) → 9,972 tris (≤ 2× tier, no decimation); by eye at close range: vent slots made shallower/narrower (read as battlements), fount ribs softened (read as stacked lumps)
  - v2 (textured, measured on `hurricane-lantern_original.glb`): silhouette IoU 0.808, face IoU 0.63 (f, offset +0.6 % / -0.3 %). 9,972 tris. Gaps: band 2 width +6 % (cap/chimney, the template's widths — kept), band 1 warm +0.07, lum/highlights higher (light-dependent: alarms only). Side by side: metal too rough and matte vs the photo's glossy bronze with dark reflections, tarnish blotchy up close; vent slots not dark; glass lighter and speckled (8.6 % specks) vs the photo's smoked near-black
  - changed for v3: metal roughness lowered (mean ≈0.45 → ≈0.3) and tarnish contrast softened; vent slot faces marked as cavities (grime). Glass (independent material, recipe compliance): darker (22,23,26), alpha 0.84 → 0.90, specks thinned to ~3 %
- CLEANUP (`scripts/cleanup_checks.py`): merge 1e-5 m (5 verts merged on wire seams), normals recalculated, 0 loose, 0 fused edges, 0 open edges on every part; transforms identity. Attachment (`scripts/attach_check.py`, BVH + insertion parity): every part touches (≤0.5 mm) or enters another — 0 floating
- TEXTURING (`scripts/tex_bake.py`, `scripts/tex_compose.py`): one metal M_Metal_AgedBronze over 12 parts, one UV atlas (cylindrical UVs on turned parts and tubes, planar on caps/boxes, packed), and M_Glass_Smoked on the globe. Base: Poly Haven `rusty_metal_sheet` (CC0, thumbnail compared with the fount/bell crops — mottled tarnish, no plate seams; `metal_plate_02` rejected for its seams), box-projected at ×3, tinted to the photo palette: tarnish (72,57,47)↔(118,96,78) sRGB, all metal; brass wear (165,128,82) on per-part 90-99.5th percentile convexity × noise (wires and bail: uniformly handled brass); non-metal grime (28,23,20) in cavities/AO (21 % of texels, minority); dark glossy oil run under the filler cap; vent slots painted as openings. Roughness its own field (scan + grime − wear), ≈0.17-0.45. Relief: scan + pits + dents through Bump → baked tangent NORMAL. Glass: smoked (22,23,26), alpha 0.90, ~6 % frost specks in blotches, roughness 0.10, clear coat. Bakes: Cycles Emission probes to float, composed in numpy, written as byte PNG (sRGB colour, Non-Color data), 1024 metal / 512 glass, packed in the .blend
  - UV check (`tools/uv_check.py` on the GLB): first pass FAIL (vent slot walls collapsed 2.5 %) + flipped caps → fixed in the build (planar caps after normals, slot UVs pulled inward); now 0 FAIL, 1 WARN (Tubes flipped 2.6 %, at the sharp bottom bends — left, a normal map of fine pits only)
  - Rounds:
  - v3 (final measured round, `hurricane-lantern_original.glb`): silhouette IoU 0.808, face IoU 0.56 (offset +0.3 % / -0.3 %). Metal now reads as the photo's glossy dark bronze. Remaining: band 2 width +6 % (template widths, kept), highlights/lum higher (light-dependent, alarms), band 1 texture detail +0.05, glass rim brighter than the photo
  - inventory tick on close-ups after v3: vent slots read grey (not dark) → painted as openings; oil run read pale → oil film made dark and glossy over the metal. No other change (round cap reached)

- OPTIMIZE (auto, gltf-transform, separate steps — rule 20): resize 1024 → WebP q90 → Draco; validator exit 0 after each, 0 errors (tangents exported: no generated-tangent warnings). 4.54 MB (`_original.glb`) → 474 KB (`web/hurricane-lantern_final.glb`, −90 %). Needs a Draco decoder and WebP support on the client. `hurricane-lantern_preview.glb` = copy of `_original` (no Draco, no WebP: opens in Quick Look and in engines without Draco)
- EXPORT: material audit clean (2 materials, Principled only, image textures only, all packed, Non-Color on data maps), transforms identity, no modifiers, names SM_/M_/T_. `web/hurricane-lantern_final.glb`: 13 meshes, 9,972 tris, 2 materials (metal OPAQUE, glass BLEND + KHR_materials_clearcoat), 4 textures ≤1024, single-sided; 0.146 × 0.117 × 0.361 m, on the ground. .blend saved
  - Final measure on the shipped `_final.glb`: silhouette IoU 0.808 (rounds 0.801 → 0.808 → 0.808 → 0.808), face IoU 0.54; side-by-side identical to the .blend render (no colour lost in export). UV check 0 FAIL, 1 WARN (Tubes flipped 2.6 %)
  - Studio checks: no WARN; notes: triangles 2× the tier (kept, round parts and wires), licences
- Inventory tick (final, crops vs close renders): fount ✓ (ribs subtle, rolled bottom) · filler cap ✓ + oil run ✓ (dark glossy) · burner + gallery ✓ · wick knob ✓ · globe ✓ shape; colour darker than v1 but its rim reflections read brighter than the photo's · guard wires ✓ (X on the front) · lift lever ✓ (rods, right hook, left clip — simplified) · tubes ✓ (arm into chimney, end into shoulder, gusset) · chimney + skirt + bead ✓ · vent slots ✓ (dark after the fix) · cap ✓ · top ring ✓ (through the clip) · bail ✓ (hooked into ears on the tubes)
- Known gaps, not chased (round cap reached): band 2 width +6 % (template widths kept over the photo's perspective); glass rim highlights brighter than the photo; lum/highlights higher under the review HDRI (light-dependent)
- Unseen in the photo (invented plainly): the back and the sides — turned parts mirrored, no filler cap or oil run at the back
- Intermediates kept (auto mode, nobody to ask; compact cleanup is offered at hand-over): `opt_tmp/` (resize and WebP stages, 5.4 MB), `textures/bake/*.npy` (probe bakes, ~75 MB), `textures/*.png` (composed maps, also packed in the .blend), `textures/thumbs/`, `review/`, `scripts/`

## Licenses
- Reference photo and TRELLIS template: user-provided, used for measurement only, not shipped
- rusty_metal_sheet (Amal Kumar), Poly Haven: CC0 — Source: Poly Haven (polyhaven.com), via the public API
- studio_small_09 HDRI, Poly Haven: CC0 — review renders only, not shipped

## Checkpoint
- Last completed step: [7] EXPORT (pipeline complete)
- Timestamp: 2026-10-23
