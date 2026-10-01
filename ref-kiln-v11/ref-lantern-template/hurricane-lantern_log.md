# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft up to 10K)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modeling (Blender 5.2.2 LTS, blender-mcp addon 1.8, protocol 13)

## Reference Image
- Path: <repo>/bench/runs/_refs/Lantern_01.png (394x1023, alpha)
- Template: <repo>/bench/runs/_refs/trellis/lantern_trellis.glb
  (TRELLIS.2) — measured with tools/template_profile.py only; its mesh and texture are NOT shipped.
  Profile: review/profile.json

### Assumptions (one photo cannot say)
- Real size: **0.30 m overall, bail raised as photographed** (usual hurricane-lantern size; not given).
  Body base-to-cap-top ~21.7 cm, base diameter ~9.8 cm.
- Camera: elevation ~12 deg (read on the globe-tray rim ellipse at mid-height, minor/major ~0.2),
  azimuth 0 (air tubes symmetric at +-5.0 cm in the photo).
- No side, top or back view was given: the back of the globe guard, the back of the tank and the
  underside are inventions mirrored from the front (see inventory).

### Inventory (from 3x crops in review/crops/), part, how it meets
- top loop: closed PENTAGON wire (apex up), bottom edge is a hinge clip on the cap top → SM_HurricaneLantern_TopLoop, hinge INSERTED into a clip on Cap
- cap: wide thin flange (r 2.95 cm), raised stepped top tier, flat top plate → Cap
- vent band: dark rectangular slots all round under the cap, on a necked band (r ~2.0-2.2) → Chimney
- chimney/bell: straight chimney r 2.65, a horizontal bead at ~17.4 cm, flaring bell down to r 3.5 lip at ~15.3 cm with a rolled rim → Chimney
- globe collar: dark neck under the bell (r 2.1), collar r 2.7, bright rim ring r 2.9 at ~13 cm → Chimney
- globe: egg-shaped glass, widest r 3.45 at ~9.5-10 cm, dark smoky grey, heavy frosting/specks, scratches → Globe (own material)
- globe guard: two wires crossing in an X in front (crossing ~9 cm), ends hooked into the collar rim and the tray rim; back X mirrored (invention) → Guard
- tray: globe sits in a dish with a rim r 2.9 at ~7.1 cm, narrowing to the burner → Body (turned)
- burner neck: column r 1.5-1.85 between tray and tank, a flange where it sits on the tank → Body
- tank: r 4.9 at the bottom with a rolled foot bead, slight taper, two embossed rings on the side, domed shoulder up to the burner → Body
- filler cap: short cylinder r 1.1 on the tank shoulder, front-right (~18 deg), recessed top disc; dark kerosene drip stain running down below it → FillerCap, sits on a foot shaped to the shoulder
- air tubes x2 (+-X): horizontal arm INSERTED into the chimney at ~17.4 cm, elbow, leg leaning out to r ~5.0, lower elbow landing on the tank shoulder on a saddle foot; raised seam along the tube → Tubes
- bail: wide wire arch, raised rounded HUMP at the peak (not a point, not a dip), ends bent inward and HOOKED into the tube elbows at ~16.3 cm → Bail
- lift lever (right): wire from the tray rim, out, up a diagonal, across into a clip on the right tube (~8.3 cm) → Lever
- left catch: elongated U spring clip on the left tube's inner side (9.3-10.6 cm), and a horizontal rod tube→tray at ~7.0 cm → Lever
- right rod + eye: horizontal rod from the burner neck (~6.0 cm) to the right tube, a small ring eye at its end → Lever

### Palette sampled (dark / mid / light, sRGB, 10/50/90th luminance percentile)
- tank #17120e #27211c #47392e · bell #19120e #2f251e #594c41 · chimney #100c09 #231a13 #564433
- cap #1f1a17 #33302e #555452 (greyer: tarnish) · tubes #150f0c #2d1f18 #5f402f · wires #18120c #302317 #64462c
- globe #141313 #1d1d1c #3c3735 (neutral smoky grey) · collar #0c0907 #251d17 #8f8376
- Reading: ONE physical metal (tarnished brass/bronze) everywhere — photo values are dark because the metal
  reflects a dark studio; base colour kept at a real reflectance (§ 4), patina stays metal. Glass is the second material.

## Pipeline
- Scene: untouched factory scene (Cube, Camera, Light; no .blend loaded) → Cube removed before building.
- Visual comparison: **close match** on shape and parts; material reads warmer/cleaner than the reference (see Review).

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Hunyuan3D params: n/a (scripted modeling, no AI generation)

## Source
- Method: scripted modeling — `scripts/build.py` (+ `geo_lib.py`: lathe and sweep with their own UVs)
- Template: TRELLIS.2 mesh measured only (`tools/template_profile.py --height 0.30 --bands 50` → `review/profile.json`); not shipped
- Heights from the template, widths/details from the photo's pixels (core profile, traced bail), inventory from 3x crops

## Pipeline
- Build: 23 parts under one root empty `HurricaneLantern` (origin = base centre, 1 BU = 1 m)
  - turned (lathe, 32-40 around, globe 64): Tank, Burner(+tray), BurnerHead, Chimney(collar+bell+chimney), VentBand (6 recessed slots), Cap, FillerCap
  - swept (parallel-transport tubes): Tube_L/R (16 sides, raised seam, flared saddle foot entering the tank shoulder), Bail (8 sides, traced, peak hump),
    TopLoop (closed pentagon through LoopClip on LoopClipPlate), Guard_0-3 (two X's, front + back), Lever, Catch, Rod_L, Rod_R, Eye
- Import: implicit (scripted). bbox 0.1165 x 0.099 x 0.2985 m (get_object_info: Tank Ø 0.099 x 0.0442, Bail top 0.2985)
- Cleanup (`scripts/cleanup.py`): merge by distance (welded the closed TopLoop/Eye seams, 7 coincident fillet verts on Lever), remove loose,
  degenerate dissolve, manifold: 0 fused edges; normals recalculated on closed meshes only — all 21 closed meshes positive volume (outward);
  open by design: Globe (both ends hidden in tray/collar, 100 % radially outward) and VentBand (ends hidden); transforms applied
  (FillerCap); orphans purged. Attachment (BVH, 0.5 mm): no floating part (Rod_R flagged 0.98 mm = vertex sampling of a 2-ring rod
  that starts 3 mm inside the burner neck — inserted). Joint renders (review/m*/joints/) looked at: every end enters its part or sits on a foot.
- Poly count: **12,418 tris** — 2.5x the balanced prop top (5K). Where they go: turned body ~5.0K (32-40 sides), globe 1.8K (64 sides,
  per glass rule), tubes 1.3K (16 sides), wires ~3.5K. Reduction PROPOSED, not applied (rule 6 — see Open points).
- Texturing (`scripts/materials.py`): one procedural brass shader (M_Src_Brass, kept in the .blend) baked into two texture sets
  (Body, Frame) so every part is the same metal; frosted glass (M_Src_Glass) baked into its own set.
  Fields: 3-octave patina colour + dark-patina blotches + faint vertical streaks; grey tarnish rising toward the cap;
  edge wear from a Bevel-normal mask x noise patches (convex only, via AO) + sparse bright specks; crust (non-metal, minority) from the
  part's own cavities (local AO) and the foot; kerosene drip below the filler cap; cavity darkening from AO; roughness its own noise;
  relief = pits + dents + fine horizontal scratches, baked to a tangent normal map; pits and scratches also in colour.
  Glass: smoky neutral grey, frost specks gathered by blotches in colour + alpha, roughness 0.07-0.42, coat 1, alpha 0.72-0.95, BLEND, double-sided.
  Bake: Emission → float images → sRGB bytes (base colour), MetalRough packed (G rough, B metal), Normal; empty atlas texels filled with
  the set's mean (coverage Body 80 %, Frame 23 %, Glass 34 %) so no black non-metal bleeds into thin islands at low mips. 1024 px.
- Material export audit (rule 19): shipping materials are Image Texture / UV Map / Separate Color / Normal Map / Principled only.
- Export: `hurricane-lantern_original.glb` 4.67 MB (PNG 1024, export_apply=False)
- Optimize (auto preset, individual steps, rule 20): gltf-transform resize 1024 → webp → draco:
  4.67 MB → **325 KB (-93 %)** `hurricane-lantern_final.glb`. Needs EXT_texture_webp + KHR_draco_mesh_compression (Draco decoder on the client).

## Review (reference-fidelity § 5, studio_small_09 HDRI, front, elevation 12 deg, azimuth 0)
- m1 (.blend, shape only): IoU 0.832. Band 2 (18-24 cm) core +17 %. Row-by-row core widths: everything above 18.8 cm ~0.35 cm high,
  tube arms ~0.4 cm high, bell lip ~0.25 cm high, collar 0.2-0.3 cm wide. Base-band differences = the photo's steeper perspective at the
  bottom (not changed). → Fix 1: top section -0.35 cm, arms -0.25 cm, bell -0.25 cm, collar slimmer; clip given a foot plate.
- m2 (GLB, 512 bakes): IoU 0.849, band 2 core +3.5 %. Frame metallic 0.22, Body 67 % metal (global-AO crust on wires next to other parts);
  saturation low in every band (0.17-0.27 vs 0.26-0.35); base detail 0.013 vs 0.029; globe clear and light. → Fix 2 (half-way):
  crust from local AO only, darker/more saturated patina with dark blotches, more wear, pits/scratches in colour, smokier denser frost, ragged drip.
- m3 (final GLB, 1024): IoU 0.849; band saturation 0.34/0.39/0.24 vs 0.33/0.35/0.26 (bands 2-4 close). Frame "metallic 0.23" traced to the
  tool averaging over the whole texture — the Frame atlas covers 23 %; covered texels are metal. Filled the empty atlas (mip hygiene).
- m4, m5: **verification-only re-measures of the shipped file** after (a) the atlas fill and (b) the bail-hump fix — beyond the skill's
  "three measures"; no correction was made from them. m5 (shipped file): IoU 0.849, Frame metal 1.00, Body 0.96, metal base-colour
  median 0.26-0.27 (real aged brass 0.30, alarm < 0.15).
- Remaining gaps (logged, not tuned — correction rounds used up): base band warmer and more saturated than the photo
  (sat 0.46 vs 0.33, warm 0.13 vs 0.05) and too clean (detail 0.016 vs 0.029): the tank reads as cleaner warm bronze where the
  reference is dark, grimy, greyer. Luminance/highlights higher everywhere — light-dependent, not tuned.

### Inventory ticked (final crops, review/m4/tick_sheet.png + bail close-up)
- [x] top loop: closed pentagon, apex up, bar through a hinge clip on a foot plate on the cap
- [x] cap: flange + stepped tiers (tiers flatter than the photo's)
- [x] vent band: 6 dark recessed slots all round
- [x] chimney / bead / bell flare / collar / bright rim ring
- [x] globe: egg-shaped, smoky grey, frosted specks (frost finer and more uniform than the photo's blotches)
- [x] guard: two wires crossing in an X in front, ends in collar rim and tray rim; back X = invention
- [x] tray, burner neck + flange, burner head visible through the glass
- [x] tank: foot bead, two embossed rings, domed shoulder
- [x] filler cap front-right with recessed top; drip stain below it (straighter than the photo's)
- [x] air tubes: arms entering the chimney, legs leaning out, lower elbows entering the tank shoulder on a flared foot, seam ridge
- [x] bail: traced arch, ends hooked into the tubes; peak HUMP — failed at first tick (pointed: 9 mm resampling), fixed and re-checked
- [x] right lift lever, left spring catch, left rod, right rod + eye
- Inventions (no view shows them): the back of the guard (mirrored X), the tank's back and underside (turned, plain), the lever/catch sides.

## Shortcuts / deviations (stated, per instructions)
- Real size and camera elevation are assumptions (0.30 m; 12 deg) — no side/top view was available.
- 5 fidelity runs instead of 3: runs 4-5 verify the shipped file after non-tuning fixes (atlas fill, bail hump), no correction from them.
- Normals: recalculated only on closed meshes; the two open shells are verified outward by construction instead.
- Optimize: textures were already 1024, so `resize` was a no-op step kept for the canonical sequence.

## Open points (for the user)
- Triangle count 12,418 (2.5x tier top). Options, none applied: drop the back guard X (invention, -620), body lathes 32→24 sides
  (-1.2K, visible facets close up), globe 64→48 (-450, against the glass rule). Say which, or keep.
- Optional third look round on the tank: greyer/darker patina, more grime, rougher — the measured gap above.

## Licenses
- Reference image Lantern_01.png: Poly Haven preview (CC0) — reference only, not shipped
- TRELLIS.2 template: measured only, not shipped
- studio_small_09 HDRI (Poly Haven, CC0): review lighting only, not shipped
- Shipped geometry and textures: created in this session (scripted + procedural bakes)

## Files (compact)
- hurricane-lantern_original.glb (4.67 MB) · hurricane-lantern_final.glb (325 KB) · hurricane-lantern.blend (procedural sources kept, fake user)
- scripts/ (build, geo_lib, materials, run_all, cleanup, export, check_normals, compare, fid_summary) · review/ (crops, profile, m1-m5 renders)
- Removed (own intermediates, compact mode): review/m2/review.glb, hurricane-lantern.blend1

## Checkpoint
- Last completed step: EXPORT (+ OPTIMIZE), shipped file verified
- Timestamp: 2026-10-01 13:15
