# Wooden Chair (Gothic high-back armchair) — Production Log

## Config
- Type: prop (furniture)
- Target: glTF (game asset)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling in Blender 5.2.2 (user's open Blender, untouched factory scene, via the Blender Lab MCP)
- Output: /private/tmp/kiln-bench/v300final-lab/ref-chair/work/generated-assets/wooden-chair/

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-lab/ref-chair/refs/WoodenChair_01.png (335x1024 RGBA, already cut out)
- Brief enrichment (from 3x crops in crops/):
  - Gothic throne-style armchair, very tall narrow back, straight (no rake)
  - 2 square back posts floor-to-top, beaded (row of studs) on the front face      → SM_WoodenChair_Post_L/R
  - Fleur / acorn finial with 4 leaves on each post, on a small cap block            → Finial_L/R, sits ON post top (inserted)
  - Back panel: pointed lancet arch frame springing from the stiles beside the posts → Panel_Frame, stiles touch posts
  - Tracery: quatrefoil roundel with a 4-petal carved flower boss in the centre      → Tracery (strokes), Flower boss inserted in roundel
  - Inner pointed arch over roundel; transom under roundel                           → Tracery
  - Lower tracery: two pointed sub-arches, 4 small lancets, 3 mullions with spur cusps → Tracery, mullions enter bottom rail
  - Back bottom rail just above the seat                                             → Panel_Frame
  - Seat: board with moulded, overhanging front/side edge                            → Seat, resting on aprons/legs, posts pass through
  - Apron under seat, front + sides: cusped arcade (3 arches) cut in its lower edge  → Apron_F/L/R (+ plain back rail), tenoned into legs
  - Front legs: square blocks + turned shaft with rings, small bun feet              → Leg_FL/FR
  - Arm supports above the seat: square base block, turned/fluted column             → ArmPost_L/R, continue the front legs
  - Arms: curved, flaring outward, ending in a rounded scroll knob over the column   → Arm_L/R, enter the back post, knob on column
  - Box stretchers low near the floor (front, back, sides)                           → Stretchers, enter legs
  - Material: one physical material — dark reddish-brown stained wood, satin; mottled, darker in cavities
- Assumptions (auto mode, one photo):
  - Real size: overall height 1.63 m to finial tip, seat height 0.46 m, front width 0.46 m, back 0.38 m (trapezoid seat read from the different side offsets of front/back legs), depth ~0.45 m. Read from pixel ratios at the back plane (~1.77 mm/px), seat height assumed.
  - Camera: elevation ~20 deg (seat top and feet offsets), azimuth ~ -12 deg (the chair's -X side is seen, image left).
  - Unseen: back of the chair and its right side — kept plain and symmetric; the pierced tracery is the same from behind (seen-through). No side or top view given.
- Palette sampled (sRGB, 10/50/90 pct): seat (61,47,45)/(130,93,80)/(137,98,85); posts (77,55,51)/(90,70,69)/(99,83,79); legs (56,40,38)/(78,71,68)/(101,92,88); overall mean (92,73,69)
- Visual comparison: close match on parts and proportions; partial on fine carving (see inventory tick below)

## Prompts (copy-paste ready)
- Concept art: none (user image)

## Source
- Method: scripted (Blender Python), no marketplace, no AI

## Pipeline
- CONFIG/BRIEF: Blender 5.2.2 connected (Blender Lab MCP), untouched factory scene (Cube/Camera/Light, no file). Kiln Studio live view at http://127.0.0.1:4854/.
- SOURCE: factory Cube removed (rule 6 exception, logged). Scripted build `scripts/build_chair.py` (v1 kept as `scripts/build_chair_v1.py`): 81 parts in collection WoodenChair_Parts — boxes with 1-segment chamfers, lathed legs/columns/finials (16 sides, finial 12), swept tracery strokes (rect section), extruded cut-outs (lancet arch frame, cusped apron arcades), beads as 6-sided studs. 8,652 tris (balanced top 5K: +73 %, under 2x — spent on turned legs/columns 1.6K, arms 1.0K, tracery ~2.4K, finials 1.0K; not cut).
- TEXTURING: Smart UV Project (60 deg, margin 0.003) + pack: uv_check ok — used 45.3 %, overlap 0, stretch 0, collapsed 0, flipped 0. Material M_Wood_DarkStained: Poly Haven dark_wood (2k, CC0) projected triplanar on object coords (grain along Z on the sides, along Y on the tops, 0.6 tile/m = real scale), its luminance kept (contrast ^0.8) and the hue set to the photo's mid sRGB (104,75,66); broad mottling noise x0.82-1.12; AO (6 cm) darkens cavities to x0.45 and roughens them; relief = scan displacement through Bump (0.35). Baked (Cycles GPU, 32 samples, 2048) through Emission -> float -> sRGB bytes (colour), roughness (data), tangent NORMAL; final M_Wood_DarkStained_Baked = Principled + 3 image textures; procedural kept with a fake user. Renders front 3/4, back 3/4 and a tracery close-up looked at. Material audit: clean.
- Rounds (reference image), fidelity_check front, elevation 20, azimuth -12 (sign checked: +12 gives IoU 0.37, -12 gives 0.59 — the photo sees the chair's -X side), 16 samples, untextured:
  - v1: silhouette 0.588, face 0.46 (f 0.83, offset -10.6 mm); bands 2 and 5 +10 % too wide; legs' turned section too high. Changed: widths x0.92 (post_x 0.165->0.153, leg_x 0.205->0.19, opening 0.105->0.097, posts 0.05->0.046), seat edge follows the legs, turned shaft lowered to 0.10-0.26 m.
  - v2 (textured `_original.glb`, 32 samples): silhouette 0.572, face 0.48 (f -, offset -0.6 %/-0.6 %); band 4 width -4 % (seat narrowed too far), under-arm opening 47 % of the photo's (arms too low/flat), see-through specks at the head-arch apex and between the flower petals the photo does not have; material: warmth +0.03, saturation in range, highlights 0 vs 0.12 at the base (alarm only), and by eye the photo's varnish is glossier. Changed: leg_x 0.19->0.197 (half-way back), arm 15 mm higher with a smoother sweep (6 subdivisions), head key lengthened over the apex, a disc behind the flower; ONE material change: roughness range 0.38-0.62 -> 0.26-0.48.
  - v3 (textured `_original.glb`): silhouette 0.602 (up from 0.572), face 0.48; the under-arm gap is closed, band 4 width -3 %, highlights 0.025 vs 0.122 at the base (alarm), band 2 saturation +0.08, warmth +0.03. Two correction rounds done — cap reached, kept. Joints (review/front/joints/) looked at: every end enters its neighbour; the lancet apexes show a small mitre notch.
  - bake fix (not a round): the v3 normal map was flat (std 0.003, 2.7 KB WebP) — Bump distance 0.8 mm -> 4 mm, strength 0.35 -> 1.0, normal re-baked (std 0.033); `_original.glb` re-exported.
  - final measure on the shipped `web/wooden-chair_final.glb`: silhouette 0.601, face 0.48 — same as v3, the export changed nothing visible; colour renders correctly (not black).
- Inventory tick (final, crops of the photo vs side_by_side / close-up):
  - back posts square, floor to top: present, right
  - beaded moulding on the posts: present (6-sided studs on the outer front arris); smaller and sparser than the photo's
  - finials: present, 4-leaf flame finial on a cap — the photo's is a 3-lobed fleur-de-lis, close but not identical
  - lancet arch frame on stiles: present, right
  - quatrefoil roundel + carved 4-petal flower boss: present, right
  - head arch over the roundel: present; the photo's trefoil cusps inside it are not modelled
  - transom, two sub-arches, 4 lancets, 3 mullions with spurs: present; the photo's hooked cusps on the sub-arches are not modelled
  - back bottom rail: present, right
  - seat with moulded overhanging edge + moulding strip: present, right
  - apron arcade, 3 arches front / 2 per side: present; cusps simpler than the photo's
  - front legs: blocks + turned shaft + bun feet: present, right
  - arm supports (base block + turned column): present; the photo's column is fluted, mine is plain turned
  - arms flaring out to a scroll knob: present; the photo's arm curls down more and its scroll is larger
  - low box stretchers: present, right
  - one material, dark reddish-brown satin wood: present (saturation +0.07, warmth +0.03 vs photo; highlights lower — light-dependent)
  - unseen (invented, kept plain): back faces of the posts and panel, the right side
- OPTIMIZE (auto, glTF): gltf-transform resize 1024 -> webp q90 -> draco, separate steps (rule 20; no simplify). 11.0 MB `_original.glb` (2048 PNG) -> 521 KB `web/wooden-chair_final.glb` (-95 %); Draco needs a decoder on the client. `wooden-chair_preview.glb` = copy of `_original` (extensionsUsed: none — opens in macOS Quick Look). Geometry untouched.
- EXPORT: glTF 2.0 binary, Y-up, export_apply False, one mesh SM_WoodenChair, one material M_Wood_DarkStained_Baked (baseColor, metallicRoughness, normal; 1024 WebP in final). Material audit: clean. 8,568 tris, 5,090 faces, 0.478 x 0.462 x 1.632 m, standing on the ground. .blend saved (packed textures, parts collection + procedural material kept with fake users). Kiln Studio: live view closed; checks: no WARN (notes: original kept at 2048 by design, licences listed).
- Attachment (BVH, surface-or-inside): 0 floating parts after v2 build.
- IMPORT (scripted, implicit) + CLEANUP: 81 parts joined into one mesh SM_WoodenChair (one draw call for the game); parts kept in the .blend as collection WoodenChair_Parts (fake user, not in the scene). Merge by distance 1e-4 per part only (64 verts; a global merge fused coincident spur bases — 12 edges >2 faces — so it was not used), degenerate dissolve, loose removed, 19 ngons triangulated, normals recalculated, shading set after the weld: all faces smooth + 4,650 sharp edges (> 35 deg). Fused edges 0; open edges 432 = the hidden bases of the bead studs, inside the posts (not watertight by design). Transforms identity, origin at the base centre, 0.464 x 0.462 x 1.632 m, min z 0 (on the ground). 5,058 faces / 8,524 tris (balanced 1.5-5K, +70 %, < 2x: reported, not cut). Viewport screenshot framed on SM_WoodenChair.
- Assumption update: camera azimuth -12 in fidelity_check's convention (camera on the chair's -X side).

## Licenses
- Reference image: provided by user
- Poly Haven 'Dark Wood' (dark_wood) texture set, 2k: CC0 — Source: Poly Haven (polyhaven.com), via the public API (Dario Barresi, Dimitrios Savva, Rico Cilliers)
- Poly Haven 'Studio Small 09' HDRI (review renders only, not shipped): CC0 — Poly Haven (polyhaven.com)

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22 16:12

## Intermediate files (compact storage, auto mode: kept, listed for the user to decide)
- crops/ (reference crops, texture thumbnails), review/wip/ (work renders, test GLBs), review/front/ (fidelity measures, joints), review/final/ (review renders of the final), scripts/ (build, cleanup, texture scripts), textures/ (baked PNGs 2048 + Poly Haven sources), review/studio_small_09_1k.hdr
