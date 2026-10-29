# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (web/glb)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling (user's brief: no marketplace, no AI)
- Live view: off (benchmark auto run, no Studio)
- Output: /private/tmp/kiln-bench/v300final-ahujasid/ref-ammo-box/work/generated-assets/ammo-box/
- Blender: 5.2.2 LTS, MCP for Blender addon 1.8 (protocol 14), up to date. Scene was the untouched factory scene (Cube, Light, Camera, unsaved) — Cube removed before building (rule 6 exception).

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-ahujasid/ref-ammo-box/refs/ammo_box.png (1024×1015, alpha cut-out already)
- Identified as: M19A1-style .30 cal / 7.62 mm steel ammo can, olive-drab paint, heavy rust.
- Assumptions (auto mode, stated):
  - Real size: M19A1 usual size, 0.276 L × 0.096 W × 0.180 H m (body + lid, handle folded adds ~1 cm). Photo ratios measured: W/L ≈ 0.33, H/L ≈ 0.61–0.65 — consistent.
  - Camera: elevation ≈ 13°, azimuth ≈ 55° toward +X — read on the lid's two top edges (slopes 0.31 and 0.156; sin e = √(0.31·0.156)).
  - Orientation: lettered long face = front (−Y); latch end = +X.
  - Unseen: back long face, −X end (hinge end on a real can), underside → kept plain and closed; no hinge invented.
- Inventory (from 2× crops review/crops/*.png):
  - body: rectangular steel can, rounded vertical corners/edges, olive paint, rust on edges → SM_AmmoBox_Body
  - lid: overlapping skirt ~12 mm, rolled bead on the long top edges, flat top → SM_AmmoBox_Lid, RESTING on body (skirt overlaps body)
  - carry handle: flat steel strap ~130×25×3 mm, -X end lifted on its standing bail, +X end resting on bracket → SM_AmmoBox_Handle, wires HOOKED through bracket slots
  - handle brackets: two small flat plates with folded tabs on the lid, 120 mm apart → SM_AmmoBox_HandleBracket_L/R, WELDED to lid (enter lid top)
  - handle bails: two wire loops, ends inserted in brackets → SM_AmmoBox_HandleBail_L/R
  - rivet strip: horizontal plate under lid on +X end, 5 domed rivets → SM_AmmoBox_RivetStrip, welded to body end
  - latch lever: vertical plate, chamfered corners, large dished circular recess (~38 mm) → SM_AmmoBox_Latch, hinged at bottom
  - latch hinge knuckles: two rolled tabs left/right at latch bottom → SM_AmmoBox_LatchHinge, welded to body end
  - lower bail wire: U wire hanging from the knuckles across the end face → SM_AmmoBox_LatchBail, ends INSERTED in knuckles
  - upper-left wire: from lid skirt down to rivet strip left end → SM_AmmoBox_LidWire, ends inserted
  - end panel: raised panel on the +X end around the latch → part of Body
  - stencil text, yellow: "200 CARTRIGES / 7.62 MM, M?08 / CARTONS • M31" (as in photo, misspelling kept) → painted layer in body texture
- Palette (linear, 10/50/90 pct): paint dark 0.035,0.039,0.027 / mid side 0.106,0.114,0.118 / end green 0.082,0.090,0.043; rust 0.102,0.067,0.047 / 0.318,0.180,0.106 / 0.369,0.231,0.141; stencil yellow ≈ 0.231,0.176,0.059
- Visual comparison: (pending)

## Prompts (copy-paste ready)
- N/A — scripted, no generation. Concept: user image.

## Source
- Method: scripted modelling (Blender Python via MCP), recommended for a hard-surface box prop and chosen by the user's brief.

## Pipeline
- CONFIG/BRIEF: done 2026-10-22 — assumptions above.
- SOURCE/IMPORT (scripted, scripts/build_geometry.py): 11 objects, 4,636 tris, bbox 0.281 × 0.105 × 0.203 m (handle raised), base on z=0. Parts per inventory; lid plateau and beads are overlapping shells (a boolean union on them collapsed the lid — replaced). v1→v1b: rivet row raised above the latch plate, plate top 150 mm, opening centre 119 mm (photo: rivets above the plate). Attachment check (BVH): every part ≤ 0.06 mm from its neighbour; wires' ends run into knuckles / lid / brackets.
- CLEANUP (scripts/cleanup_uv.py): transforms identity on every part (asserted), merge 0.05 mm → 34 verts merged (wire curve seams only), 0 loose, 0 fused edges, normals recalculated; shade smooth with sharp edges > 35° marked on sheet parts, > 70° on wires. 4,636 tris — inside balanced prop range (1.5–5K), no reduction. UVs: Body alone (set A), Lid+Handle+Brackets+RivetStrip+Latch+LatchHinge packed together (set B), Smart UV 50°, margin 0.01. Stencil mask rendered from text (scripts/text_mask.py → textures/stencil_front_mask.png, 2048×1261, front face X/Z mapped).
- TEXTURING (scripts/material.py → scripts/bake.py): one physical material M_AmmoBox_PaintedSteel (Cycles: green_metal_rust tinted to the photo's olive, rust_coarse_01 tinted to the photo's rust, wear mask = Bevel-edge + AO cavity + per-part bias + end face + top band, broken by noise; stencil mask on the front face, worn by rust + fine noise). Baked to UVs, 1024: colour via Emission into float → sRGB byte, roughness, tangent normal → M_AmmoBox_PaintedSteel_Body (set A) and _Parts (set B). Wires: M_AmmoBox_WireSteel, values only. Metallic 0 throughout (paint and rust crust are non-metal; no bare steel in the photo).
- Rounds (reference image, fidelity_check front, elev 13°, azim 55°, ortho):
  - v1: silhouette 0.906 (band 5 +42 % width = the photo's close perspective camera vs ortho render, not geometry — left as is); face 0.00 (a 0.3 % dark spot, the dished opening's shadow; not a missing part). Material: rust too light/orange, paint light, wire pale (sat 0.25–0.31 vs 0.29–0.42).
  - v2: changed palette only (paint mid 0.046,0.054,0.038; rust 0.20,0.11,0.065; wire 0.13,0.068,0.036; end-face rust 0.55→0.38) → sat still −0.09…−0.15; surfaces washed by dielectric specular, lid top greyed by the fade term. Kept.
  - v3: Specular IOR level 0.5→0.3, fade restricted to side walls, end-face rust 0.38→0.15 → lid top green as in photo, sat band 3–4 −0.13…−0.15 (light-dependent residue), band 5 −0.24: end face overshot (too clean). Kept, end-face term restored half-way (0.26, x-end 0.2) for the final bake; measured on the shipped file below.
  - final (shipped bake): end-face rust 0.26, x-end 0.2; UV check on ammo-box_original.glb: 0 FAIL, 0 WARN (wires carry no UVs — value-only material; their curve UVs were removed). Material audit (rule 19): shipped materials are Principled + Image + Normal Map only, images packed; glTF carries baseColor, metallicRoughness, normal, KHR_materials_specular 0.6. Looked at from two opposite 3/4 views: back plain and closed, as logged.
  - Remaining known gap: the photo's front face carries heavier grey/rust blotching than the model; the face measure sees no openings (none exist).
- Optimize: gltf-transform 4.3.0, resize 1024 → webp q90 → draco (separate steps, no `optimize`): 5.61 MB → 373 KB (−93 %). ammo-box_preview.glb = copy of _original (no Draco/WebP, extensionsUsed: KHR_materials_specular only — opens in Quick Look).
- Export: glTF/GLB, web/ammo-box_final.glb 373 KB, 4,632 tris, 11 meshes, 3 materials, 6 textures 1024² WebP; export_apply off; Y-up. Body 0.28 × 0.10 × 0.17 m on ground; overall 0.281 × 0.105 × 0.203 m with the lifted handle.
- Final measure on the shipped _final.glb: silhouette IoU 0.907 (band 5 = perspective, see v1); sat −0.07…−0.15 (light-dependent residue), face 0.00 (opening shadow, no missing part). Inventory ticked on crops: body, lid skirt + beads, lifted strap, 2 brackets, 2 bails, rivet strip ×5, latch plate + opening, 2 knuckles, lower bail, upper-left wire, end panel, stencil — all present.
- Visual comparison: close match on shape, parts and palette; lighter weathering on the front face than the photo.
- Intermediates kept (auto mode, nobody to answer): review/glb/ammo-box_v1–v3.glb, review/opt/{resized,webp}.glb, review/front/ renders.

## Licenses
- green_metal_rust (Poly Haven, CC0) — Source: Poly Haven (polyhaven.com), via the public API
- rust_coarse_01 (Poly Haven, CC0) — Source: Poly Haven (polyhaven.com), via the public API
- Reference image: user-provided
- Stencil glyphs: rasterised from macOS 'DIN Alternate Bold' into the baked texture (pixels only, no font file shipped)

## Checkpoint
- Last completed step: [7] EXPORT (done)
- Timestamp: 2026-10-22 22:30
