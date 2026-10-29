# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (GLB), web/ output
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto (standing answer: yes to every optional step — run it, keep the version before)
- Storage: compact
- 3D backend: none — scripted modelling in Blender 5.2.2 LTS (MCP for Blender addon 1.8, protocol 14)
- Environment: macOS 26.6.1, Apple M4 Pro; gltf-transform + gltfpack present; Python 3.14 (no PIL — image work done in Blender's Python)
- Live view: Kiln Studio http://127.0.0.1:4840/ (--no-open)
- Scene at start: Blender factory scene (Cube, Camera, Light, unsaved) → Cube removed before building (rule 6 exception), Camera and Light kept

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-ahujasid/ref-ammo-box-project/refs/ammo_box.png (1024×1015, RGBA, background already transparent — no cut-out needed)
- Visual comparison: partial match — shape, parts and stencil close; the photo is rustier and darker (latch end, lower front)
- Subject: US M19A1-type (.30 cal / 7.62 mm) steel ammunition can, olive-drab paint, heavily rusted, yellow stencil.
- Assumptions (auto mode, nobody to ask):
  - Real size: usual M19A1 size, 0.279 m long × 0.095 m deep × 0.178 m tall (lid closed, handle down).
  - Camera: 3/4 view from the front-right, azimuth ≈ 52° (read from the ratio of the long side to the latch end, with the real L/W), elevation ≈ 16° (read on the top face's edges: 13° on the long edge, 19° on the end edge — perspective; mean taken). Fixed before modelling.
  - Unseen: back long side, hinge end (-X), underside. Kept plain and closed (no hinge invented beyond a plain lid skirt), listed as unseen.
- Inventory (from 2–3× crops in crops/):
  - body: steel box, small-radius vertical corners, rounded bottom edges → SM_AmmoBox_Body
  - lid: flat top, skirt ~25 mm overlapping the body OUTSIDE (rests on body), rolled/rounded top edge → SM_AmmoBox_Lid
  - handle: flat steel strap ~22 mm wide along the lid's length, back end lifted, front end resting; each end held by a wire bail → SM_AmmoBox_Handle (strap + bails), bails HOOKED through the brackets
  - handle brackets: two small flat plates welded on the lid, rolled edge holding the bail → SM_AmmoBox_HandleBrackets, WELDED on lid
  - latch end (+X): riveted hinge strip on the lid skirt (5 rivets) → SM_AmmoBox_LatchHinge, WELDED on lid skirt
  - latch lever: tall plate, chamfered corners, round hole Ø≈45 mm (the body shows through, darker green), hinged at top → SM_AmmoBox_LatchLever, HINGED on the hinge strip
  - catch tab: bracket with a rolled knuckle at the bottom of the end face → SM_AmmoBox_CatchTab, WELDED on body
  - catch bail: rectangular wire U hanging from the catch tab → SM_AmmoBox_CatchBail, HOOKED in tab knuckle
  - lid hook wire: wire from the lid's corner down to the lever's hinge on the left of the end → SM_AmmoBox_LidWire, INSERTED in lid skirt and hinge strip
  - stencil: yellow DIN-style text on the front long side, 3 lines: "200 CARTRIGES / 7.62 MM,   M08 / CARTONS • M31" (as written on the photo, spelling kept) → paint on Body
  - finish: olive-drab paint (very dark green), rust brown on every edge, the lid skirt, the handle and all latch hardware; black weathered patches on the front side under the lettering → one painted-steel material with rust/paint layers (rust is a layer of the same steel)

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Generation params: none (scripted)

## Source
- Method: scripted (Blender Python), from the reference image
- Build script: scripts/build_ammo_box.py

## Pipeline
- BRIEF: confirmed in auto mode with the assumptions above.
- Palette (photo sRGB, 10/50/90 %): paint green lid (31,31,22)/(39,36,26)/(52,53,47), end (20,21,11)/(22,23,12)/(55,33,19); dark patch front (9,11,7)/(11,12,9)/(13,15,13); rust lid skirt (21,16,13)/(67,38,27)/(85,49,30); handle (43,32,21)/(54,38,26)/(77,45,32); stencil median (58,44,11). The photo is underexposed (brightest surface ~85/255): hues kept, exposure lifted by one uniform linear gain (assumption).
- Texture sets chosen (thumbnails vs crops, crops/montage.png): base green_metal_rust (olive paint), wear rust_coarse_01 (brown rust). Rejected: rusty_metal_02/sheet (orange-on-white), metal_plate_02 (panelled), rusty_painted_metal (corrugated).
- SOURCE/IMPORT: scripted, scripts/build_ammo_box.py, 12 objects under empty SM_AmmoBox: Body, Lid, HandleBrackets, Handle, HandleBail1/2, LatchHinge (5 rivets), LatchLever (Ø40 mm hole, exact boolean), CatchTabs, CatchBail, LidWire. 2,452 tris. World size 0.288 × 0.095 × 0.204 m (lid top 0.171 m, the lifted handle reaches 0.204), on the ground (min z 0.000). Sharp edges marked > 35° (786), wires all smooth.
- Attachment (§ 3): BVH check, no part floats (only Body/Lid read 2.9/1.5 mm: their top verts sit inside each other's solid — the body enters the lid by 4 mm). 22 joints rendered (review/front_geo/joints/, montage joints_montage.png) and looked at: bails pass through knuckles and strap rolls, plates sit on their faces.
- Rounds (reference image): v1 geometry (untextured .blend, az 52 / el 16, ortho): silhouette 0.883, per band 0.75/0.94/0.96/0.88/0.79; band 1 −23 % and band 5 +26 % are the photo's perspective (converging verticals, near corner larger) — dimensions kept, not tuned to it. Face 0 (no texture yet).
- Cleanup: 11 meshes, 1,180 → 1,180 faces (2,452 tris), transforms applied, merge by distance 1e-5 keeping the corner normals (32 verts merged, all on the filleted wire corners, no face collapsed), normals recalculated, 0 loose, 0 non-manifold, 0 open, 0 fused edges. Origin = centre of base (root empty at 0,0,0). Tier balanced prop 1.5–5K: 2,452 tris, in range.
- Texturing v2 (scripts/texture_ammo_box.py; review bake 1024 shell / 512 hardware): procedural shader built once, M_AmmoBox_Steel_Shell_Procedural / _Hardware_Procedural (kept in the .blend, fake user): green_metal_rust paint + rust_coarse_01 rust, box-projected on object coords, normalised to luminance (hue from the photo's palette only — v1 multiplied the scan's own green in: shell mean sRGB (17,19,5), fixed before measuring), rust masked by Bevel-node edges + AO cavities + upper band + noise border, black weathering field on the long sides, stencil from textures/stencil_mask.png (DIN Alternate Bold, layout measured on the photo) on the front only, worn by noise and eaten by rust. Roughness own fields; metallic 0 (paint + rust crust are dielectric). Baked (Emission → float → sRGB bytes; NORMAL tangent) to M_AmmoBox_Steel_Shell / _Hardware. Smart UV per set (shell: Body+Lid, hardware: 9 parts).
- Round v2 (review/v2.glb, az 52 / el 16): silhouette 0.883; sat per band 0.116/0.126/0.154/0.110/0.107 vs photo 0.286/0.323/0.392/0.372/0.423; warm 0.027/0.023/… vs 0.058; lum 0.36–0.15 vs 0.17–0.08 (light-dependent, alarm only). Face 0 (photo detail 0.3 % of the face, the hole's shadow — not a gap). Biggest: rust coverage (photo rust-brown nearly everywhere).
- Round v3 (changed ONE thing: rust coverage — Bevel radius 3→5 mm, upper band 0.35→0.5 from z 0.095, shell bias 0→0.12): sat bands 1–2 0.177/0.189 (from 0.116/0.126), warm 0.048/0.042 (photo 0.058) — kept. Bands 3–5 unchanged (0.166/0.113/0.108): the paint reads grey and glossy.
- Round v4 (changed ONE thing: the paint layer — palette half-way to the darker end-face sample (17,18,8)/(27,28,13)/(46,46,28), roughness 0.42–0.72 → 0.55–0.80): sat bands 0.178/0.183/0.146/0.099/0.093 — the lower bands it targeted got WORSE (0.113/0.108 → 0.099/0.093), the rougher paint scatters a grey sheen; spread closer (0.10 vs 0.13). UNDONE → v3 materials ship. Two correction rounds done (cap).
- Gaps left (by eye on side_by_side.png, not closed within the cap): the latch end is cleaner olive than the photo's rust-brown; the lower front reads grey-olive where the photo is near-black; lid top glossier. Silhouette gaps (band 1 −23 %, band 5 +27 %) are the photo's perspective vs the ortho measure.
- Texturing final: v3 shader baked at 2048 (shell) / 1024 (hardware), 32 samples; means sRGB shell (23,17,10), hardware (33,18,11). uv_check on the baked GLB: 11 meshes, 0 FAIL, 0 WARN (shell atlas 73 % used, no overlap/stretch/collapse/flip). Looked at from 4 sides (two opposite 3/4, latch end, underside): stencil front only, rust on edges/upper band/hardware; the back carries the same black weathering field (unseen side — invented, kept plain otherwise).
- Zones: Body+Lid → M_AmmoBox_Steel_Shell (T_AmmoBox_Shell_BaseColor/Roughness/Normal), 9 hardware parts → M_AmmoBox_Steel_Hardware (T_AmmoBox_Hardware_*), both from the one painted-steel shader.
- Material audit (rule 19): 2 assigned materials, Principled only, 6 packed byte images (colour sRGB, roughness/normal Non-Color), no procedural node assigned — compatible. Procedural sources kept unassigned in the .blend.
- Optimize (auto, rule 20 individual steps): ammo-box_original.glb 10.15 MB → resize 1024 4.26 MB → WebP q90 434 KB → Draco web/ammo-box_final.glb 346.8 KB (−96.6 %). Geometry untouched (2,452 tris). ammo-box_preview.glb = copy of _original (no Draco, no WebP: extensionsUsed none) — the one that opens in macOS Quick Look. Draco needs a decoder on the client.
- Final measure (web/ammo-box_final.glb, 64 samples): silhouette 0.883, sat 0.176/0.189/0.165/0.114/0.110, warm 0.048/0.042/0.029/0.019/0.020 — same as v3: no colour lost on export. No metal flags.
- Inventory ticked on side_by_side (photo | final): body ✓, lid with overhanging skirt ✓, handle strap lifted at the back end ✓, 2 brackets ✓, 2 bails ✓, riveted hinge strip 5 rivets ✓, lever with Ø40 hole ✓, catch tabs ✓, catch bail ✓, lid wire ✓, stencil 3 lines ✓ (bolder than the photo's), rust on edges/hardware ✓ (less than the photo on the latch end), black patch ✓ (less dark).
- Photo projection (optional, standing yes): tools/photo_project.py on web/ammo-box_final.glb, az 52 / el 16, --exclude Handle + HandleBail1/2 (the strap is placed by eye). At the default guard it REFUSED: fitted IoU 0.934 < 0.95 (camera az 52.3, el 20.7, roll −0.5, 2.43 m). Proportion diagnosis (review/rounds/propfit_diag, test copies only, model unchanged): length ×0.90 → 0.940, height ×1.10 → 0.934, depth ×1.10/1.15/1.25 → 0.944/0.939/0.935; none reaches 0.95, and each pulls the camera away from the photo's reading — remaining mismatch read as the photo's close-camera perspective, shape kept. Run 1 with --min-iou 0.93 and --erase-stencil '#5B4716': only 56 stencil texels erased → double marking (review/rounds/project_try1). Run 2 with the baked stencil's sampled colour '#34270A': 19,321 texels erased where the photo is used, 74,155 kept where unseen; exposure gain 0.81; trusted 15.9 %, touched 31.3 %; from the photo's view SSIM 0.643 → 0.679, ΔE76 13.11 → 12.04 (partly circular). other_angles.png: the photo's text lands soft and misregistered ("7.62" reads "2.62", "CARTONS" fades at the trust edge), the lever outline ghosts on the end face. Verdict: the scripted version stays the deliverable; the projected one ships as web/ammo-box_final_projected.glb (254.8 KB) for comparison.
- Export: web/ammo-box_final.glb 346.8 KB, 2,452 tris, 11 meshes, 2 materials, glTF/GLB (Draco + WebP 1024), export_apply off. Root: ammo-box_original.glb 10.15 MB, ammo-box_preview.glb 10.15 MB (Quick Look), ammo-box.blend (procedural materials kept, textures packed). Studio checks: all ok, no WARN (licence note only).
- Storage (compact, auto, nobody to answer → kept and listed): review/ (rounds v2–v4 GLBs, fidelity renders, projection outputs, diagnostic variants ~90 MB), crops/, textures/ (CC0 sources + stencil mask), scripts/.

## Licenses
- Reference image: user-provided
- Textures: green_metal_rust, rust_coarse_01 — CC0, Source: Poly Haven (polyhaven.com), via the public API
- HDRI (review only, not shipped): studio_small_09 — CC0, Poly Haven
- Font: DIN Alternate Bold (macOS system font) — used only to rasterise the stencil into the baked texture; the font file is not shipped

## Checkpoint
- Last completed step: [7] EXPORT (done)
- Timestamp: 2026-10-23 11:25
