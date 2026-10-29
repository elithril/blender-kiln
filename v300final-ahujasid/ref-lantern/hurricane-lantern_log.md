# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft; up to 10K reported, never blocked)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modeling (user: no marketplace, no AI)
- Environment: Blender 5.2.2 LTS via mcp-for-blender (addon 1.8, protocol 14, up to date); Poly Haven on, Sketchfab/Poly Pizza off; no generators
- Scene at start: untouched factory scene (Cube, Camera, Light, unsaved) → Cube removed before building (rule 6 exception)
- Live view: Kiln Studio http://127.0.0.1:4841/ (project root = work/)
- Output: /private/tmp/kiln-bench/v300persp-ahujasid/ref-lantern/work/generated-assets/hurricane-lantern/

## Reference Image
- Path: /private/tmp/kiln-bench/v300persp-ahujasid/ref-lantern/refs/Lantern_01.png (394×1023 RGBA, already cut out)
- Assumptions (auto mode, not asked):
  - Real size: 0.36 m total height with the bail upright (Feuerhand-276-type hurricane lantern, body ≈ 0.26 m). Scale 0.352 mm/px.
  - Camera elevation: ≈15° (top cap ellipse ≈ 0.30 minor/major → 17°, tank bottom ≈ 0.39 → 23°; mid-height ≈ 15°). Azimuth 0 (frontal).
  - Single view: back and underside unseen → kept plain and closed, mirrored from the front where the part is turned. Filler cap placed front-right as seen; nothing invented at the back.
- Silhouette (px from top → width): bail peak 0; handle loop 192–290 (94 px wide); top cap 288–336 (200); vent ring 336–356 (133); chimney 360–444 (180); bell skirt 444–508 (≈225); neck 510–530 (165); globe top collar 535–580 (181); globe 585–770 (235 max at ≈680); glass seat dish 750–790 (190); burner collar 790–840 (130–180); tank 845–1023 (320 max at ≈960); side tubes Ø≈46 px, centres ±155 px from axis, splaying slightly outward downward; bail span ≈350 px at its ends.
- Inventory (part, how it meets):
  - fuel tank: squat drum, domed shoulder, 2 beads on the side, rolled bottom edge → SM_HurricaneLantern_Tank
  - filler cap: short cylinder with lip, sits ON tank shoulder front-right (inserted) → _FillerCap
  - burner collar + glass seat dish: cylinder on tank top, dish holding the globe → _Burner
  - wick-raiser rod: thin rod from burner to the right, small ring knob at its end → _WickKnob
  - glass globe: ovoid, dark smoky glass, frosted speckles; burner wick holder seen inside → _Globe (own material)
  - globe guard: wires crossing in an X over the globe, ends INSERTED into top collar and bottom dish → _Guard
  - globe lift lever: horizontal wires from the dish to each side tube, small hooked loop on the left tube, bent lever on the right → _Lever
  - globe top collar + neck → _Chimney
  - bell / deflector skirt: flared, beaded edge → _Chimney
  - chimney body: cylinder with a bead; side tubes ENTER it through elbows → _Chimney
  - vent ring with slots under the top cap → _Chimney
  - top cap: stepped disc (2 steps) → _Cap
  - top carry loop: pentagonal wire loop, legs INSERTED into a small clip on the cap → _TopHandle
  - side tubes ×2: round tubes, upper elbow INTO chimney body, lower elbow INTO tank shoulder → _Tubes
  - bail: tall wire arch, small hump at the peak, ends HOOKED into the upper elbows' outer side → _Bail
- Palette (sRGB, dark/mid/light of crops): tank 22,16,12 / 37,30,25 / 72,58,46; tubes 18,12,9 / 45,31,23 / 95,65,46; bell 31,25,20 / 51,40,33 / 100,89,79 (blue-grey patina patches); glass 19,18,18 / 29,28,28 / 61,56,54; wires 27,20,14 / 52,37,23 / 108,76,48.
- Materials: ONE metal (aged bronze-finished steel, darker patina + blue-grey worn patches as layers within it), ONE glass (dark smoked, frosted specks).
- Brief (confirmed in auto mode): a realistic game-ready hurricane (Feuerhand-style) kerosene lantern, 0.36 m tall with the bail up, aged dark bronze metal, dark smoked glass globe, all parts above, glTF, balanced tier.

## Prompts (copy-paste ready)
- Concept art: none (source: user image)

## Source
- Method: scripted (Blender Python, via MCP)

## Pipeline
- [1] CONFIG + [2] BRIEF: done — assumptions above.
- [3] SOURCE: scripted build, scripts/build_lantern.py (lathe profiles from the measured silhouette, curves for tubes and wires, bail from the traced centre line, NURBS order 4). 21 parts parented to SM_HurricaneLantern_Tank, one metal + one glass material.
- Rounds (reference image, fidelity_check --view front --elevation 15 --azimuth 0, studio_small_09 HDRI):
  - v1: silhouette IoU 0.867 (bands 0.25 [bail/loop, thin] / 0.78 / 0.89 / 0.89 / 0.93; body widths within +1–4 %, base +4 % = perspective), face IoU 0.72 (f 0.94, offset -1.1 mm); 12,612 tris (>2× tier). Materials untextured: too warm/saturated (expected, [5b] pending). Joints (11) looked at: bail hooks into elbows, lever/wick rods enter dish/collar, guard ends hidden in collar/dish; guard wires grazed the glass near the top. Carry loop came out round → fillet 3.5 → 1.5 mm.
  - v2 changes (geometry, one set): upper elbows +4 mm, wick rod shortened to the tube, filler cap enlarged, guard offset 3.0 → 3.6 mm; segment counts lowered on my own build (tank 36, chimney/cap 36, burner 28, tubes 12 sides, wires 6) → 9,772 tris (balanced 1.5–5K: +95 %, under 2×, reported, not reduced — globe kept at 64 segments). Measured after texturing.

- [4] IMPORT (implicit, scripted): 21 objects SM_HurricaneLantern_* (data-blocks *_Mesh), parented to SM_HurricaneLantern_Tank, origin = centre of base (0,0,0); world bbox on vertices 0.135 × 0.113 × 0.357 m (1 unit = 1 m), standing on z = 0.
- [5] CLEANUP (in scripts/build_lantern.py): transforms applied; merge 0.01 mm (no shading normals to keep: sharp edges set on the mesh at 35°, wires 75°); degenerate dissolve; loose removed; normals recalculated + outward check; fused edges 0 on every part. Open edges only at hidden ends inside other parts (globe ends in collar/dish, burner collar in tank, chimney collar bottom on globe, cap inner edge, vent liner, filler cap base) — intentional, not visible. Orphans removed (the vent boolean's cutter slot removed from the chimney).
  - Found and fixed: curve ROUND bevel at resolution 0 made 4-sided (square) wires → own parallel-transport sweep (wires 6 sides, tubes 12), bail resampled by arc length from a NURBS order 4.
  - Poly: 9,920 tris (balanced prop 1.5–5K: +98 %, under 2×, reported; spent on the 64-segment globe 1.66K, the chimney with vents 1.9K, the tank 1.37K). Trimmed my own build parameters only (collinear profile points, wire resolution) — no decimation.

- [5b] TEXTURING (scripts/texture_lantern.py → scripts/bake_lantern.py, headless):
  - Scan choice: Poly Haven thumbnails looked at against the photo (metal_plate_02, rusty_metal_sheet, blue_metal_plate, rusty_metal_04, metal_plate). metal_plate_02 read closest but its panel seams repeat every 0.33 m → a seam grid on a 36 cm lantern; switched to rusty_metal_sheet (2k, seamless), used as a VALUE field (luminance → photo palette dark→mid) and its blue-grey zones as the patina mask, so its rust hue never reaches the bronze. Box projection, 5× (0.4 m tile).
  - M_Metal_AgedBronze (one physical material): palette dark/mid/light sRGB 0.24,0.19,0.15 / 0.44,0.34,0.25 / 0.74,0.58,0.40 (metal stays metal); bare wear on convex edges from a curvature attribute per part (90th→99th percentile), broken by noise; cavities darker; faint vertical grime streaks; blue-grey patina non-metal (rough 0.82) on up-facing surfaces, minority; roughness its own field 0.22–0.48; relief = scan normal ×0.45 + fine pits → baked tangent normal (mean 0.5,0.5,1.0).
  - M_Glass_Smoked: dark slate glass sRGB ≈ 0.17,0.18,0.20, alpha 0.72–0.90, frost specks gathered by blotches in colour + alpha; single 64-seg shell, blended, double-sided.
  - Rounds (materials, front 15°): v2 procedural: IoU 0.872, metal too light/saturated (sat +0.16, warm +0.06–0.12) → v3 darker less saturated palette, roughness down, finer scan: sat within ±0.03, warm within ±0.02 on bands 2–5; tank detail 0.014 vs 0.029 (flatter than the photo — left, cap reached). Glass read black-mirror vs the photo's smoky grey → last change (glass only): lighter slate tint, more frost, lower opacity. Measured on the GLB at EXPORT.
  - Baked (Cycles, 8 spp, margin 6): T_HurricaneLantern_Metal_BaseColor/Roughness/Metallic/Normal 2048 (one atlas for the 20 metal parts, Smart UV 60°, islands averaged), T_HurricaneLantern_Glass_BaseColor 1024 (RGBA, alpha baked). Float bakes converted to byte (colour → sRGB). Procedural versions kept in the .blend as *_Procedural (fake user).
  - Looked at: two opposite three-quarters + close-up of tank/filler cap — no seams, no smears.

- [6] OPTIMIZE (auto, glTF): gltf-transform resize 1024 → webp q90 → draco, as separate steps (rule 20, no `optimize`). 9.65 MB → 1.18 MB (−88 %); geometry untouched. hurricane-lantern_preview.glb = byte copy of _original (no Draco, no WebP, extensionsUsed none) — opens in Quick Look. Draco needs a decoder on the client (three.js DRACOLoader).
- [7] EXPORT: web/hurricane-lantern_final.glb │ 1.18 MB │ 9,920 tris, 21 meshes │ GLB (Draco + WebP 1024). Source at root: hurricane-lantern_original.glb (9.65 MB, PNG 2048 metal / 1024 glass), .blend, log.
  - Material audit (rule 19), map level: metal → baseColorTexture + metallicRoughnessTexture (packed) + normalTexture; glass → baseColorTexture with alpha, alphaMode BLEND. No procedural node on a shipped material (procedural copies kept in the .blend only). Exporter warning "more than one tex image for a texture" = roughness+metallic packed into one texture, default samplers — nothing lost.
  - uv_check on the GLB: 21 meshes, 0 FAIL, 0 WARN (0 overlap / stretch / collapsed / flipped).
  - Final measure, ON THE SHIPPED _final.glb (front, 15°, 64 spp): silhouette IoU 0.872 (bands 0.25 thin bail+loop / 0.81 / 0.89 / 0.89 / 0.94), face IoU 0.59 (f 0.85); sat/warm within ±0.03 on bands 2–5; texture detail about half the photo's on the tank and chimney (0.013–0.016 vs 0.029–0.030). The tool's "metal in scattered islands" alarm checked: inside the UV islands metallic mean 0.885, 90 % > 0.5 (patina ≈10 %, non-metal by design) — the alarm reads the atlas's unused texels (≈0) between islands, not the surface.
  - Kiln Studio checks: no WARN; notes = triangles (+98 %, reported), Draco decoder, licences.
- Inventory, ticked on the final side-by-side:
  - tank (beads, rolled bottom, domed shoulder) ✓ · filler cap ✓ (a little narrower/taller than the photo's squat cap) · burner collar + seat dish ✓ · wick-raiser rod + knob ✓ · glass globe smoky + frost ✓ · guard X wires ✓ · lift-lever wires ✓ (simplified loop/hook) · globe collar + neck ✓ · bell skirt ✓ · chimney body + bead ✓ · vent slots ✓ · stepped top cap ✓ · pentagonal carry loop ✓ (corners softer than the photo's) · side tubes with both elbows entering ✓ · bail hooked into the elbows ✓
  - ✗ not reproduced: the dark drip stain under the filler cap and the photo's streaky high-contrast wear (the metal is flatter than the photo — residual, round cap reached). Optional next step: tools/photo_project.py (propose only, rule 6).
- Visual comparison: close match (shape, parts, palette); surface wear flatter than the photo.
- Files kept beyond compact (auto mode, nobody to ask — listed, not deleted): review/ (crops, renders, fidelity, joints, opt/resized.glb 3.7 MB, opt/webp.glb 1.5 MB, bake.log, studio HDRI 1.6 MB), textures/ (baked PNGs — also packed in the .blend — and the Poly Haven scans), scripts/ (build, texture, bake — reproducible).

## Licenses
- Reference image: user-provided
- Geometry and materials: created in-session
- rusty_metal_sheet texture set (Amal Kumar): CC0 — Source: Poly Haven (polyhaven.com), via the public API
- studio_small_09 HDRI (review renders only, not shipped): CC0 — Poly Haven

## Checkpoint
- Last completed step: [7] EXPORT — web/hurricane-lantern_final.glb shipped, measured; Studio live view closed
- Timestamp: 2026-10-23
