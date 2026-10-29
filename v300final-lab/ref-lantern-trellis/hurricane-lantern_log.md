# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (game asset)
- Tier: balanced (prop 1.5–5K tris, soft; 2× top = 10K)
- Style: realistic
- Mode: auto
- Storage: compact
- Backend: none at runtime — starting mesh given by the user (TRELLIS.2, generated locally from the reference)
- Decimation to the balanced budget: approved in advance by the user (raw TRELLIS file kept)
- Output: /private/tmp/kiln-bench/v300final-lab/ref-lantern-trellis/work/generated-assets/hurricane-lantern
- Environment: Blender 5.2.2 LTS, official Blender Lab MCP (no marketplace / look tools); gltf-transform + gltfpack present.
  Live Blender held the untouched factory scene (Cube, Camera, Light, no file): Cube removed before building (rule 6).
- Live view (Kiln Studio): off — unattended auto run.

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-lab/ref-lantern-trellis/refs/Lantern_01.png (394×1023, alpha cut-out already)
- Brief: finish the TRELLIS.2 hurricane lantern as a realistic game prop; keep its shape; match the reference's size, materials and colours.
- Assumptions (auto mode, not asked):
  - Real size: 0.36 m total height with the bail raised (Feuerhand-276-class hurricane lantern: ~0.26–0.29 m body, ~0.14 m wide). Width then follows from the mesh proportions.
  - Camera elevation: ~10° above (the cap's and fount's top ellipses are thin), azimuth 0 (front-on; the filler cap sits front-right).
  - Unseen sides (back, underside): not shown in the photo; kept as TRELLIS made them, plain.
- Inventory (from 2× crops):
  - bail: thin wire, round arc with a small kink/peak at the top, legs hooked into the side-guard tubes at mid-height → thin, never decimated
  - top loop: small pentagon-shaped wire loop standing on the cap → thin
  - cap: flat round disc with rolled rim, small boss on top; vent ring below it (dark slots) → body
  - chimney/air chamber: stepped bell, wide flared skirt → body
  - globe: dark smoked glass, egg/barrel shape, frosted specks → own material (glass)
  - globe cage: two crossing wires diagonal over the globe + lifting lever → thin
  - burner/gallery: round dish under the globe, wick-knob shaft on the right → body
  - side guards: two vertical tubes (~1 cm), curving into the fount at bottom and into the air chamber at top; small hooks at ~70 % height → body (tubes, enter the fount and chamber)
  - fount: wide drum, ribbed (2–3 horizontal ribs), slightly tapered, domed top; filler cap front-right (short cylinder, flat lid); a dark drip/stain running down below it
  - materials: ONE metal (aged bronze-brown painted/tarnished steel: dark brown cavities, warm bronze highlights, worn bright edges), ONE glass (dark smoked, slightly blue-grey, frosted specks)

## Prompts (copy-paste ready)
- Concept art: none — user image
- Generation params: TRELLIS.2, local, by the user (settings not given)

## Source
- Method: AI (TRELLIS.2, local, user-provided GLB) → cleanup + decimation + re-texturing
- Raw file: refs/trellis/lantern_trellis.glb, copied as hurricane-lantern_trellis-raw.glb (kept, untouched)

## Pipeline
- BRIEF: done — assumptions above.
- SOURCE: user-provided TRELLIS.2 mesh (no marketplace search, no generation run).
- Import: 191,520 tris / 194,358 verts (84,458 welded), 1 mesh, 1 material (TRELLIS base colour + metal/rough 1024²), 1.0 m tall (generator default) → scaled ×0.360 to 0.36 m; bbox 0.151 × 0.121 × 0.360 m, base on z = 0. Renamed SM_HurricaneLantern_HP (kept hidden in the .blend as bake source).
  Topology: one connected blob, 13,738 fused (>2-face) edges, 10,218 open edges → not shippable as is.
  Measured (template_profile.py, 48 bands): globe 8.6–14.6 cm (r ≈ 4.1 cm), guards r 4.6–7.5 cm, chamber 15–25 cm, cap disc r 3.53 cm at 24.4–25.0 cm, top loop 25.6–29.2 cm, bail to 35.98 cm. Photo wires: bail 8 px ≈ 2.8 mm, top loop ≈ 2.4 mm (0.352 mm/px at 0.36 m).
- Cleanup (decimation pre-approved by the user; thin parts rebuilt, never decimated):
  - Body = HP minus bail, top loop and globe zone (glass + cage wires + inner burner). Tried: voxel remesh → lost the fount (level-set sign leaks through TRELLIS holes) — undone; octree remesh → 13,817 fused edges — undone; unsigned point volume → closed but hollow thin walls (inner faces eat budget, wire ends find no metal) — undone.
    Kept: surface samples → 0.8 mm voxel grid → closing 1.6 mm → 3D flood fill from outside ∩ per-height enclosed fill → solid (1,027 cm³) → Points to Volume → 1.07M faces → Collapse 600K/60K/15K/5,200 tris. 0 fused, 0 open.
  - Rebuilt as round curves on traced centrelines: bail Ø 2.8 mm (traced from the mesh, apex at 35.84 cm, hooks into the guard corners), top loop Ø 2.4 mm (pentagon), 4 globe-cage wires Ø 1.8 mm (two crossing diagonals front, two behind; photo-traced angles −62°→56°). Burner (seen through the glass) as a small lathe.
  - Glass globe: one smooth 64-segment lathe of the measured profile (13 rings), cylindrical UVs; open rims hidden in collar and dish (128 open edges by design).
  - Attachment (BVH + ray parity on the closed body): bail ends 4.5–4.6 mm inside the guards, top loop 4.2–4.8 mm into the cap boss, cage wires 1.0–2.2 mm into collar and dish (≥ their 0.9 mm radius), glass rims 64/64 inside both. Nothing floats (> 0.5 mm): none.
  - Joined: SM_HurricaneLantern (body + top loop + cage wires + burner, 7,084 tris), SM_HurricaneLantern_Bail (1,228 tris, origin at the hook pivot z 0.2025 so it can swing, parented), SM_HurricaneLantern_Glass (1,536 tris, parented). Weld 1e-4 (48 / 16 / 0 verts), normals recalculated, loose 0, degenerate dissolved, transforms applied, origin at base centre. Shade smooth, 911 sharp edges (> 62°; 35° marked 3,034 on the dented decimated body and would read faceted).
  - Size (world vertices): 0.152 × 0.121 × 0.360 m, base at z = 0.
  - Poly count: 9,848 tris — balanced prop range 1.5–5K, under 2× its top; the excess is the 64-segment glass (1,536) and round wires (~2,900). Reported, not cut (tier rule).

- Texturing (strategy: keep the AI texture — TRELLIS's own photo-derived colour/metal/rough — baked to the new UVs and graded to the photo; no Poly Haven set used for the surface):
  - UVs: Smart UV Project (66°) on body + bail as one atlas, packed; glass cylindrical. uv_check: ok on all three (overlap 0 %, stretch 0 %, collapsed 0 %, flipped 0 %).
  - Bake (Cycles GPU, selected-to-active from SM_HurricaneLantern_HP, extrusion 3 mm, max ray 10 mm, 1024²): colour and metal/rough via Emission into float images, normal tangent-space.
    First normal bake inverted on ~half the islands: the TRELLIS mesh winds 46 % of its faces the wrong way — fixed on the bake source only (custom normals cleared, 88,620 of 191,520 HP faces flipped to agree with the low-poly), re-baked: mean blue 0.92. Wire islands (bail, loop, cage) set to a flat normal (TRELLIS's lumpy wires).
  - Zones / materials: M_Metal_AgedBronze (body, guards, chamber, cap, burner, all wires — one physical metal; T_HurricaneLantern_BaseColor sRGB bytes, T_HurricaneLantern_MR G=rough B=metal, T_HurricaneLantern_N), M_Glass_Smoked (globe; T_HurricaneLantern_Glass_D 1024×256 RGBA: smoked base + frost specks gathered by a blotch field, alpha-blended, roughness 0.2, backface culling).
  - Photo palette (sRGB dark / mid / light): fount (20,15,11)/(36,30,25)/(68,55,44) sat 0.36; chamber (18,13,10)/(38,29,23)/(78,60,45) sat 0.43; guard (19,14,11)/(45,31,23)/(95,64,47) sat 0.50; bail mid (49,34,20) sat 0.53; glass (21,20,19)/(29,27,25)/(74,61,42).
    TRELLIS colour: mean (103,75,48), sat 0.53, R:G:B 1 : 0.73 : 0.47 (photo 1 : 0.83 : 0.69) — graded with channel gains (1, 1.11, 1.33) and a luminance target.
- Rounds (fidelity_check, front, elevation 10°, studio_small_09):
  - v1 (azimuth 0): silhouette 0.797, face 0.60 (f 0.88, offset −2.3 mm). Guards +9/+13 % wide in bands 4–5 while the core matched (+2–4 %), filler cap left of centre vs right in the photo → the photo's camera is turned: azimuth read from the filler cap (model −0.4 cm, photo +1.4 cm on a ~4 cm radius) = −26°, consistent with the guards' cos 26° = 0.90. Measure correction, not a model change.
  - v1 re-measured at azimuth −26° (fixed from here): silhouette 0.839, face 0.63. Band 1 width −11 % / core −35 % = bail and top loop (thin, foreshortened in the guard plane) — read on the overlay, not chased.
  - v2: changed ONE material — the glass (was clear + clear-coat mirror, band-4 highlights 0.039 vs 0.006): base (30,31,34), alpha 0.88, roughness 0.2, no coat, specks ×1.7 and brighter → highlights 0.014, reads as the photo's smoked frosted globe. Kept.
  - v3: changed ONE material — the metal's tarnish (even matte mid-brown vs the photo's deep glossy tarnish with sharp highlights): base luminance 0.24 → 0.20 (above the 0.15 metal floor; median measured 0.20), roughness ×0.75 (median 0.47 → 0.35). Band luminance now 0.17/0.19/0.12/0.14/0.14 vs photo 0.16/0.17/0.17/0.12/0.15 (alarm only); face IoU 0.62 → 0.52 because the glossier metal reflects the HDRI's dark areas as "dark marks" (light-dependent). Kept — by eye closer to the photo.
  - Cap reached (two correction rounds). Gaps left: photo highlights warmer/more golden (band-1 warmth 0.10 vs 0.07, sat 0.52 vs 0.42); photo glass a little lighter blue-grey; drip stain under the filler cap only as TRELLIS baked it; vent slots under the cap partly closed by the solid body (normal map carries them).
  - Joints: 8 rendered (review/front/joints/) and looked at — every cage wire enters the collar or dish rim, section unchanged.
  - Looks: two opposite three-quarter views in Material Preview after texturing — no unbaked or black areas.

- Optimize (auto, glTF defaults, separate steps — no simplify): hurricane-lantern_original.glb 3,564 KB → resize 1024 (already 1024) → WebP q90 → Draco → web/hurricane-lantern_final.glb 576 KB (−84 %). gltf-transform validate: PASS on original, preview and final. Preview = copy of _original (no Draco/WebP; extensionsUsed empty).
  Fixed before the final export: an empty KHR_materials_clearcoat left on the glass (coat 0) removed; metal set single-sided (closed meshes).
- Export: glTF/GLB, web/hurricane-lantern_final.glb, 576 KB, 9,848 tris (body 7,084 · bail 1,228 · glass 1,536), 3 meshes / 2 materials / 4 textures (3 × 1024² + 1024×256), export_apply off, material audit clean. Height 0.3598 m, base on the ground.
  Final measure ON THE SHIPPED FILE (front, el. 10°, az. −26°): silhouette 0.839, face 0.54, metal base median 0.197 (> 0.15 floor) — same as round 3, Draco/WebP changed nothing visible.
  Headless review of the final (review/final/: matcap + colour, q1/q3/top/under, close-ups on the bail hook, top loop, cage): clean; underside plain and closed (unseen in the photo).
  Studio checks: all ok (size, ground, textures, compression, licences); no WARN.
- Inventory at the final review (crop vs render):
  - bail: thin wire arch with a small peak, hooked into the guard corners — present, right
  - top loop: pentagon wire loop on the cap — present; reads slightly more pointed than the photo's
  - cap: disc with rim and boss; vent ring — present; the vent slots are shallower (filled by the solid body, carried by the normal map)
  - chimney / air chamber with flared skirt — present, right
  - globe: dark smoked frosted glass — present, right tone; photo slightly lighter blue-grey
  - globe cage: two crossing diagonal wires — present, right (the photo's lift lever not rebuilt)
  - burner dish + wick knob — present (from TRELLIS)
  - side guards with small hooks — present; hooks are TRELLIS blobs at this budget
  - fount: ribbed drum, filler cap front-right, drip stain — present; ribs softer than the photo, stain as TRELLIS baked it
  - one metal, one glass — yes
- Visual comparison: close match in shape and proportions; partial-to-close match in materials (tone and gloss right, highlights less golden than the photo).

## Licenses
- studio_small_09 HDRI (review lighting only, not shipped): CC0 — Source: Poly Haven (polyhaven.com), via the public API
- TRELLIS.2 output: generated by the user locally (TRELLIS.2 code/weights MIT); reference image provided by the user.

## Checkpoint
- Last completed step: [7] EXPORT (pipeline complete)
- Timestamp: 2026-10-22 17:45
