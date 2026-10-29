# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (game asset)
- Tier: balanced
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling in Blender (user brief: no marketplace, no AI)
- Blender: 5.2.2 LTS, official Blender Lab MCP (live Blender held only the untouched factory scene)
- Output: /private/tmp/kiln-bench/v300final-lab/ref-lantern/work/generated-assets/hurricane-lantern/

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-lab/ref-lantern/refs/Lantern_01.png (394x1023, has alpha — no cut-out needed)
- Assumptions (auto mode, one photo):
  - Real size: 0.36 m from base to top of the cap loop, ~0.45 m with the bail up (large storm lantern). Scale 0.435 mm/px.
  - Camera elevation: ~20 deg, read on the tank's bottom rim ellipse (semi-minor/major ~0.34) and the cap's top ellipse (~0.30). Azimuth 0 (front view).
  - Back, sides and underside are unseen: kept plain and closed, mirrored from the front where the part is symmetric (tubes, guard wires).
- Inventory (from 2.3x crops, review/crops/):
  - tank (font): wide drum, lower band wider (r 160 px) with a bead, upper band r 150, shallow domed shoulder  → SM_Lantern_Tank
  - filler cap: two-tier knurled screw cap on the shoulder, front-right                                         → SM_Lantern_FillerCap, INSERTED in the shoulder
  - burner neck: cylinder with a collar resting on the shoulder                                                 → SM_Lantern_Burner
  - globe holder (gallery): flaring cup ring the globe sits in                                                  → SM_Lantern_Gallery, on the burner
  - globe: barrel/egg glass, dark smoked blue-grey, frosted specks, own material                               → SM_Lantern_Globe, seated in gallery and top collar
  - globe guard: thin crossed wires (X on the front) from the top collar to the gallery                         → SM_Lantern_Guard, ends inserted in both rings
  - top collar + hood: narrow collar over the globe, bell skirt with rolled rim, cylinder with a bead band       → SM_Lantern_Hood
  - cap: wide flat disc with rolled rim, stepped dome, dark vent slots under it                                 → SM_Lantern_Cap
  - cap loop: pentagonal wire loop, legs INSERTED in a small bracket on the cap top                              → SM_Lantern_CapLoop
  - side air tubes (x2): round tubes, top end ENTERS the hood band horizontally, run down outside the globe, bottom end ENTERS the tank shoulder → SM_Lantern_Tube_L / _R
  - bail: big wire handle, apex above the cap loop, ends HOOKED into the tubes' outer side at hood level         → SM_Lantern_Bail
  - lift lever (right): bent wire from the gallery out to the right tube                                        → SM_Lantern_LiftLever
  - wire clip (left): narrow U clip on the left tube's inner side                                                → SM_Lantern_Clip
  - side rod + ring (right): thin rod from the burner to a ring on the right tube                               → SM_Lantern_WickRod
- Materials seen: ONE metal — antique bronze/brass, dark brown patina with copper/brass highlights on edges; ONE glass — dark smoked blue-grey with frosting specks.
- Visual comparison: close match on proportions, parts and palette; partial on surface finish (see known deviations)
- Inventory, ticked at the final review (crops vs render, review/front/side_by_side.png):
  - [x] tank: lower wide band + bead, upper band, rolled rim, domed shoulder
  - [~] filler cap: present, inserted in the shoulder — sits lower/smaller than the photo's
  - [x] burner neck + collar
  - [x] gallery cup
  - [x] globe: smoked dark glass, own material — [~] frost specks denser than the photo
  - [x] guard: crossed wires (X on the front), ends inside collar and gallery (joints looked at)
  - [x] hood: top collar, bell skirt with rolled rim, bead band, cylinder; vent recess
  - [x] cap: wide brim, stepped dome
  - [x] cap loop: pentagonal wire, legs into the bracket
  - [x] side air tubes x2: top ENTERS the hood band, bottom run into the burner collar (joints looked at)
  - [x] bail: traced, ends at the tubes' outer side — symmetric (photo leans slightly right)
  - [x] lift lever (right), wire clip (left), wick rod + thumbwheel (right)
  - Unseen in the photo (back, underside): plain and closed, parts mirrored by symmetry.

## Prompts (copy-paste ready)
- Concept art: none (user image)

## Source
- Method: scripted (Blender Python, lathe profiles + curve tubes/wires)

## Pipeline
- Config/Brief: done — brief restated in the session, assumptions above.
- Source/Import (scripted): factory Cube removed (rule 6 exception, untouched factory scene). 20 parts in collection "Lantern": lathe profiles measured from the photo's rows (32 segments, globe 64), tubes/wires swept along filleted or Catmull-Rom centre lines. 0.173 x 0.145 x 0.445 m, base on z=0. First build 13,468 tris -> resampled bail/tubes/wires (my own mesh, no user geometry) -> 9,856 tris (balanced prop 1.5-5K; within 2x: the triangles are in the 64-seg globe, the turned body and the round tubes/wires).
- Attachment (BVH, >0.5 mm): no floating part; LoopBracket/Cap, WickRod/Tube_R read 0.95-1.57 mm because their ends are buried inside the other part (inserted, no vertex near the surface).
- Rounds (reference image, fidelity_check --view front --elevation 12 --azimuth 0):
  - v1: silhouette 0.793, face 0.667 (f 0.941, offset -5.6 mm), untextured placeholder bronze. Gaps: tubes' top elbow and bottom run too low; band 5 width +11%; vent band under cap too large (271%). Colours too warm/saturated/bright (texturing phase).
  - v2: silhouette 0.816, face 0.680 (offset -0.9%). Changed: tubes' top elbow raised to row 420 and bottom run rising into the burner collar; tank r -2%; bail r 4.0 -> 4.8 px (measured 9-11 px wide); vent recess tightened. Kept. Remaining: upper body ~1% low (close perspective camera vs ortho, not copied into the geometry); photo's bail leans right — kept symmetric on purpose.
  - v3 (textured, 1024 bake): silhouette 0.816, face 0.650. Material per band (model/photo): lum 0.17-0.20 / 0.12-0.17, sat 0.22-0.40 / 0.26-0.52, warm 0.02-0.09 / 0.03-0.10 — close. Metal base median 0.218 (floor 0.15), wear one region (largest 99%). Largest material gap: globe too see-through (face 'extra' at 62% = background through the glass; band 3 spread 0.25 vs 0.40). Texture detail low (0.012-0.021 vs 0.030-0.040) — left for now (one problem per round).
  - v4 (correction 2, glass only): glass alpha 0.86 -> 0.95, more/brighter frost specks. Silhouette 0.816, face 0.650; the see-through 'extra' at 62% is gone (kept). Overshoot: specks now too dense and even ('starfield') vs the photo's sparse patchy speckle. Cap of two correction rounds reached: NOT corrected further, listed as a known deviation.
  - Known deviations at the cap: glass speckle too dense; metal flatter/less glossy than the photo (texture detail 0.012-0.021 vs 0.030-0.040); filler cap sits lower/smaller than the photo's (photo: larger, front-right, above the rim); upper body ~1% low (perspective); bail symmetric (photo leans right).

- Texturing: UVs rebuilt at physical scale (cylindrical on turned parts: u around, v along — grime runs down), metal atlas = average island scale + pack (one 0-1 tile); globe its own tile. uv_check: 20 meshes, 0 FAIL, 0 WARN. Scanned set: Poly Haven searched (metal category + brass/bronze/copper/tarnish tags); metal_plate_02 nearest but carries panel seams, no bronze set exists -> procedural antique bronze from the photo palette (sRGB dark 0.20/0.165/0.13, mid 0.31/0.255/0.195, wear 0.56/0.45/0.31, crust 0.055/0.045/0.036): 3-scale mottling, edge wear from Bevel-vs-normal (one form-following region), non-metal crust from AO + faint vertical streaks (minority), own roughness field, fine pits + dents relief -> baked (Cycles, Emission into float, converted to sRGB bytes; normal tangent bake). Glass: smoked blue-grey, speck frost in colour+alpha, bump -> normal, coat 1, alpha BLENDED. Procedural sources kept in the .blend (M_Lantern_Bronze_Proc, M_Lantern_Glass_Proc, fake user). Textures: textures/lantern_bronze_{basecolor,roughness,metallic,normal}.png, lantern_glass_{basecolor(+alpha),roughness,normal}.png, packed.
- Cleanup: 9,920 -> 9,920 tris, 20 parts. Transforms applied (rule 10 order), merge 1e-5 m: 0 merged, 0 loose, 0 fused (>2 faces), 0 open edges; normals recalculated outward; sharp edges re-marked (>35 deg turned parts, >50 deg wires). 0.169 x 0.142 x 0.445 m, base on z=0, origin at base centre. Materials: M_Lantern_Bronze, M_Lantern_Glass. Poly: 9,920 within 2x of the balanced prop top (5K): kept.
- Final measure (shipped file web/hurricane-lantern_final.glb): silhouette 0.816, face 0.652 (f 0.919), 2 meshes, 9,920 tris; metal base median 0.218 sRGB (floor 0.15); identical to the .blend's numbers — nothing lost at export.
- Joints: 11 joints rendered (review/front/joints/, sheets review/joints_sheet*.png), each looked at: guard ends inside collar/gallery, lever into the gallery rim, wick rod into burner and tube, tube runs into the burner collar — no flat cut on a curve, no flared foot.
- Export: material audit (rule 19) on the shipped materials: clean (all image-based Principled, power-of-2). Export copy joins the 19 metal parts into SM_Lantern (+ child SM_Lantern_Globe) = 2 meshes / 2 materials; the .blend keeps the parts. export_apply=False. hurricane-lantern_original.glb 3.74 MB (PNG textures: bronze 1024, glass 512), Khronos validate OK; alphaMode glass BLEND, bronze OPAQUE; KHR_materials_clearcoat.
- Optimize: gltf-transform resize 1024 -> webp q90 -> draco (q pos 14 / nrm 10 / uv 12), separate steps (rule 20): 3.74 MB -> 0.28 MB (-93%), validate OK at each step. web/hurricane-lantern_final.glb (Draco + WebP: needs a Draco decoder on the client). hurricane-lantern_preview.glb = copy of _original (no Draco, no WebP — opens in macOS Quick Look).
- Files kept (compact; auto mode, nobody to answer -> intermediates kept and listed): review/opt/{resized,webp}.glb, textures/ (baked PNGs + unused metal_plate_02 1k set + thumbnails), review/ (crops, renders, HDRI), scripts/.

## Licenses
- Reference image: user-provided
- studio_small_09 HDRI (review renders only, not shipped): CC0, Source: Poly Haven (polyhaven.com), via the public API
- metal_plate_02 texture set: CC0, Poly Haven — downloaded for evaluation, NOT used in the asset
- All shipped geometry and textures: made in this session (scripted + procedural bakes), no third-party content

## Checkpoint
- Last completed step: [7] EXPORT (OPTIMIZE done; final measured)
- Timestamp: 2026-10-22 15:10
