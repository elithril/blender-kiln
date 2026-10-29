# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (web/game GLB)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling (brief: no marketplace model, no AI generation)
- Output: /private/tmp/kiln-bench/v300final-lab/ref-ammo-box/work/generated-assets/ammo-box/
- Environment: Blender 5.2.2 LTS (/Applications/Blender.app), macOS 26.6.1; MCP = official Blender Lab MCP
  (get_objects_summary / screenshots), live Blender holds Blender's untouched factory scene (Cube, Camera,
  Light, no file) → build headless from scripts in this folder, look in the live Blender + headless review renders.

## Reference Image
- Visual comparison: close match (shape, parts, stencil, palette hue); gaps listed under Rounds v3/final
- Path: /private/tmp/kiln-bench/v300final-lab/ref-ammo-box/refs/ammo_box.png (1024×1015, RGBA, alpha cut-out already — no cut-out needed)
- Camera (measured on the silhouette, orthographic solve of the top edges): elevation ≈ 14°, azimuth ≈ 55° toward +X
  (long stencilled face = front −Y, latch end = +X). Visible perspective (far left edge 630 px vs near corner 730 px).
- Measured ratios: L/H ≈ 1.57, W/H ≈ 0.53 → matches a US M19A1 7.62 mm can.
- ASSUMPTION (auto mode, photo has no scale): real size 0.28 m L × 0.095 m W × 0.18 m H (body+lid, handle folded).
- Unseen sides (kept plain and closed, no invention): back long face (+Y), hinge end (−X), underside.
- Palette (sRGB, 10/50/90th pct; the render is dim, lit from upper right — hue/contrast only, luminance is an alarm):
  front panel [9,11,7]/[11,12,9]/[12,14,11]; lid top [52,50,43]/[56,57,51]/[62,63,58];
  strap rust [41,32,21]/[54,36,27]/[75,42,32]; end body [20,22,9]/[21,23,11]/[29,26,15];
  latch lever [21,20,10]/[28,24,13]/[45,31,20]; lid lip [38,40,32]/[44,45,38]/[85,61,54]; stencil yellow median [58,44,11].
- Brief enrichment — inventory (from 2× crops, refwork/crop_*.png):
  - body: rectangular steel can, softly rounded vertical corners and bottom edges, olive paint, darker grimy front panel → SM_AmmoBox_Body
  - lid: slightly larger than body, flat top, rolled (round) lip along the long edges, skirt overlapping the body top → SM_AmmoBox_Lid, RESTS on Body
  - lid end flange (+X): flat flange strip on the lid's latch end → part of Lid
  - handle: flat rusted steel strap along the lid's long axis, left end lifted on its wire → SM_AmmoBox_Handle, HOOKED by wires
  - handle wires: two wire loops, each hooked through a bracket and the strap end (left one standing up, right one lying) → SM_AmmoBox_HandleWire_L/R, ENTER bracket + strap
  - handle brackets: two low rectangular clip plates on the lid top → SM_AmmoBox_HandleBracket_L/R, WELDED on Lid
  - latch hinge plate: horizontal riveted strip (5 rivets) across the +X end just under the lid → SM_AmmoBox_LatchHinge, WELDED to Body end
  - latch lever: vertical plate with chamfered corners hanging from the hinge, large circular dimple in its upper half → SM_AmmoBox_LatchLever, HINGED on LatchHinge
  - catch: horizontal strip with two raised ears at the lever's foot → SM_AmmoBox_LatchCatch, WELDED to Body end
  - bail wire: U-shaped wire hanging from the two ears, below the catch → SM_AmmoBox_LatchBail, ENTERS the ears
  - hinge wire: short wire hook down the left side of the hinge plate → SM_AmmoBox_HingeWire, ENTERS LatchHinge
  - stencil: yellow text "200 CARTRIGES / 7.62 MM, M 08 / CARTONS • M31" on the front panel → texture on Body (not geometry)
  - materials: ONE physical material — olive-painted steel, worn to smooth orange-brown rust on edges, lip, strap, latch parts; dark grime blotches on front

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Generation params: none (scripted)

## Source
- Method: scripted (Blender Python, scripts/build.py), headless Blender 5.2.2

## Pipeline
- [1] CONFIG + [2] BRIEF: done — assumptions above (size, unseen sides, camera).
- [3] SOURCE: scripted (brief). scripts/build.py — 12 parts parented to empty SM_AmmoBox, each with its mesh SM_..._Mesh.
- [4] IMPORT (implicit, scripted): 2,556 tris; world-vertex size 0.289 × 0.102 × 0.2025 m (handle raised; body+lid 0.180 m), z min 0.000 (on the ground).
  Measure v1 (review/front, .blend, elev 14 az 55): silhouette IoU 0.901; band 1 width -16 %, band 5 +32 % — overlay shows keystone
  (photo's close, high perspective camera: red top both sides, cyan bottom both sides) → not a geometry gap, shape kept. face IoU 0 (stencil not yet textured).
  Joints looked at (review/front/joints_sheet.png): lid lip ended in a flat disc out of the rounded corner → tapered into the corner (fixed);
  handle strap floated 0.78 mm above its bracket → lowered 1.2 mm, now 0.1 mm (fixed). All 12 parts attached ≤ 0.5 mm (BVH, build.py ATTACH lines).
  Live Blender: its untouched factory scene (Cube, Camera, Light) replaced by opening ammo-box.blend — logged per rule 6. Looked at: review/v1/ matcap q2/q4/right/top + live viewport.

- [5] CLEANUP (scripts/cleanup.py): per part transforms applied → merge 0.1 mm keeping corner normals (0 merged) → normals out → loose 0 →
  degenerate dissolve → fused edges 0, open edges 0 on all 12 → origin = centre of base (root SM_AmmoBox at 0, z min 0) → naming OK (SM_/_Mesh/M_)
  → orphans purged → materials: one slot each (fixed: the lever's boolean had left an empty slot first) → 3,036 tris (balanced prop 1.5–5K: in range).
  Looked at: live viewport from the back three-quarter, face orientation on (no back faces). Studio live snapshot: cleanup.
- [5b] TEXTURING (scripts/texture.py): one physical material (olive-painted steel worn to rust), 3 texture sets baked
  (Body, Lid, Hardware atlas of 10 parts): scanned green_metal_rust (paint, box-projected, tint ×[0.85,0.69,0.62] → palette mid sRGB 58,64,40)
  + rust_coarse_01 (tint → sRGB 98,56,36), rust masked by distance to the part's box edges + AO cavities, noise only breaking the border;
  dark grime on the long faces; stencil from measured word boxes (homography of the photo's front face → X/Z; 3 lines, cap 20 mm), font Blender built-in.
  Bake: Cycles Metal GPU, Emission → float → sRGB bytes (colour), roughness → ORM (R 1, G rough, B 0 metal), NORMAL tangent. Procedural source kept as M_*_Source (fake user).
- Rounds (reference image, fidelity_check front, elev 14, az 55, studio_small_09):
  - v1 (512 px review bake): silhouette 0.899; face 0.00 (photo's 'detail' 0.4 % of face, at the top — a lid shadow, no part); sat 0.22–0.25 vs ref 0.37–0.42
    in every band (real gap); lum/highlights high (light-dependent alarms). Look: rust only a thin even outline on every edge; front lacks the
    photo's big dark blotches and broad rust zones. → change ONE thing for v2: wear distribution (edge ramp 16→32 mm, broad noise ×1.35 at scale 4,
    grime threshold 0.50→0.40 and darker, sRGB 15,17,12).
  - v2: silhouette 0.899; band 5 warm +0.076 (was on target), sat 3/4 bands −0.13..−0.14 (closing from −0.24), band 1 highlights 0.31 → 0.12.
    Look: front now has the photo's dark centre (kept); rust overshot — a regular, too-wide frame on every body edge. → v3, same one thing,
    half-way back: edge ramp 32→24 mm, broad noise ×1.35→×1.15, fine breakup 0.55→0.8 (border irregular). Last round (cap: 3 measures) —
    v3 baked at 1024 / 32 samples and measured on the shipped _final.glb.
  - v3 (final bake 1024 px / 32 samples → ammo-box_original.glb): looked at review/v3 colour q2 + q4 (two opposite angles) + top/under, and the
    live Material Preview. Rust border irregular, front dark centre kept, stencil intact. Measure 3 = the shipped _final.glb (see EXPORT).
  - UV check (tools/uv_check.py on _original.glb): 12 meshes, 0 FAIL, 0 WARN (overlap 0 %, collapsed 0 %).
  - Material export audit (rule 19, map level): each of 3 materials → baseColorTexture + metallicRoughnessTexture + normalTexture filled;
    9 images; no procedural node connected to an exported material. Exporter warning "more than one tex image" = rough+metal from one ORM image: harmless.
    AO and displacement maps of the scans not shipped (baked into colour / normal deliberately).
  - FINAL measure (3rd, on web/ammo-box_final.glb, 64 samples): silhouette 0.899 (keystone of the photo's perspective, bands 1/5, unchanged since v1 — not geometry);
    sat −0.10..−0.16 in bands 2–5 (rust/paint less saturated than the photo); band 5 warm +0.056; band 1 highlights 0.26 (lid paint reads glossy under
    the studio softbox — light-dependent alarm); face 0.00 (the photo's only 'detail' is a 0.3 % dark mark at the top). Stopped at the round cap.
  - Inventory ticked on crops vs review/final + side_by_side: body ✓, lid + rolled lips ✓, lid end flange ✓, strap (left end lifted) ✓, 2 wire loops ✓,
    2 brackets ✓, hinge strip + 5 rivets ✓, lever + round dimple ✓ (dimple reads shallower than the photo's deep recess), catch + 2 ears ✓, bail ✓,
    hinge wire ✓, stencil 3 lines ✓, one painted-steel material with rust ✓.
- [6] OPTIMIZE (auto, glTF): gltf-transform resize 1024 (no-op, already 1024) → webp → draco, separate steps (rule 20); no geometry touched.
  7.27 MB → 254 KB (−96.5 %). ammo-box_preview.glb = copy of _original.glb (extensionsUsed: none → opens in macOS Quick Look).
- [7] EXPORT: web/ammo-box_final.glb, 254 KB, 3,036 tris, 12 meshes, glTF 2.0 + KHR_draco_mesh_compression + EXT_texture_webp (needs a Draco decoder).
  export_apply False (rule 18; no modifiers / geometry nodes left). .blend saved with all images packed (procedural sources M_*_Source kept, fake user).
  Studio: live view ended; `studio.py checks ammo-box`: all ok, 1 licence note (credit Poly Haven; font OFL). Removed the session's misplaced
  ammo-box/ammo-box/ammo-box_live.glb (snapshot path one level too deep).
  Kept beyond compact's set (auto mode, nobody to ask): scripts/ (rebuild: build → cleanup → texture → export), textures/ (baked PNGs + CC0 sources,
  also packed in the .blend), refwork/ (crops, thumbnails), hdri/, review/ (incl. intermediate round_v1.glb, round_v2.glb ≈ 5 MB).

## Licenses
- Reference image: user-provided
- Stencil font: Blender's built-in font (bfont / Inter, SIL OFL 1.1), rasterised into the texture
- Poly Haven texture sets (CC0) — green_metal_rust (base paint), rust_coarse_01 (rust wear). Source: Poly Haven (polyhaven.com), via the public API

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22 15:55
