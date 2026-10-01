# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft range up to 2x)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modeling (Blender 5.2.2 LTS, blender-mcp addon 1.8, protocol 13) — no marketplace, no AI generation

## Reference Image
- Visual comparison: **close match** on shape and parts; partial on surface (metal lighter and cleaner, globe glossier than the photo)
- Path: bench/runs/_refs/Lantern_01.png (394x1023, alpha)
- Template: bench/runs/_refs/trellis/lantern_trellis.glb (TRELLIS.2 of the same photo) — MEASURED ONLY
  (`tools/template_profile.py --height 0.30 --bands 60` → review/profile.json, plus scripts/probe_template.py
  for the tubes' and bail's positions). Its mesh and texture are not shipped.

### Assumptions (one photo cannot say) — auto mode, not blocked on
- Real size: **0.30 m overall, bail raised** (usual hurricane-lantern size, not given). Body to cap top ~21.7 cm, tank Ø ~9.9 cm.
- Camera elevation: **12°** — read on rim ellipses: collar ~7°, globe tray ~10°, bell lip ~14° (the rim nearest mid-height);
  the base ellipses open more (close camera). Azimuth 0 (tubes symmetric in the photo).
- No side/top/back view: the guard's back X, the tank's back and underside and the sides of lever/catch are inventions.
- Tubes and bail: the template puts them ~6 % further from the axis than the photo's pixels (photo tube centre 4.5 cm at
  z 12, template 4.85; bail 4.9 vs 5.45 at z 18) while the body widths agree within 1 %. Template positions used (skill § 2).

### Inventory (from 3x crops, review/crops/) — part, and how it meets
- top loop: closed PENTAGON wire, apex up, bottom bar held in a hinge clip on the cap top → TopLoop, bar INSIDE LoopClip, clip ENTERS Cap
- cap: wide thin flange (r ~2.95) with rolled edge, raised rounded tier, small top plate → Cap
- vent band: dark rectangular slots all round, under the cap → VentBand (recessed slots), enters Chimney and Cap
- chimney: straight r 2.65, horizontal bead at ~17.4 cm, rounded shoulder at ~19 cm → Chimney
- bell: flares to a rolled lip r ~3.6 at ~15.2 cm → Chimney
- globe collar: dark neck r 2.05 under the bell, collar r 2.6, bright rolled rim r ~2.95 at ~12.9 cm → Chimney
- globe: egg-shaped glass, widest r 3.48 at ~9.5 cm, DARK smoked grey, frosted specks in patches → Globe (own material), ends inside tray and collar
- guard: two wires crossing in an X in front (crossing ~9 cm, right of centre), ends hooked in collar rim and tray rim → Guard, ends ENTER the rims
- tray: dish with rolled rim r ~3.2 at ~7.7 cm holding the globe → Burner
- burner head: dark wick holder visible through the glass → BurnerHead, stands in the tray
- burner neck: column r ~1.8 from tank to tray, flange where it sits on the tank → Burner, enters Tank
- tank: r 4.9 with a rolled foot bead, slight taper, two embossed rings, rounded shoulder → Tank
- filler cap: front-right on the shoulder, ribbed cylinder, rim + recessed top; dark kerosene drip running down below it → FillerCap ENTERS Tank
- air tubes x2 (±X): arm INSERTED into the chimney at ~17 cm, elbow, leg leaning out (r 4.45 → 5.4), lower elbow bending down-in onto
  the tank shoulder on a flared foot; seam line along the front → Tube_L/R, enter Chimney and Tank
- bail: wide wire arch, rounded HUMP at the peak, ends bent inward and hooked into the tubes' top elbows → Bail, ends ENTER the tubes
- right lift lever: wire from the tray rim, right, up a diagonal, hooked on the right tube at ~8.3 cm → Lever, enters Burner and Tube_R
- left catch: narrow U spring clip on the left tube's inner side (7.7-10.3 cm) → Catch, enters Tube_L
- left rod: horizontal tube→tray at ~6.9 cm → Rod_L; right rod at ~6.0 cm, burner neck → right tube, ring eye at its end → Rod_R + Eye

### Palette sampled (dark / mid / light, sRGB, 10/50/90th luminance percentile)
- tank #18120d #201a15 #3a2c22 · tank right #1e1915 #282623 #54473a · bell #16100d #2a221c #493629
- chimney #0f0b08 #251b13 #5c4834 · cap #26211d #383533 #575757 (greyer: tarnish) · tubes #100c09 #251a14 #4f382a
- bail #1b140e #342517 #6c4c30 · collar #0b0806 #1b1510 #826c5a · filler top #160e08 #292623 #564734
- globe #0f0f0f #181717 #3f3834 (neutral, dark smoked grey)
- Reading: ONE physical metal (aged brass) everywhere, glass the second. The photo's metal is dark because it reflects a dark
  studio; base colour kept at a real reflectance (skill § 4: ~0.30 luminance), tarnish/patina stay metal; hue/saturation
  from the palette (warm brown, sat ~0.3; cap and tank's right side greyer).

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Hunyuan3D params: n/a (scripted modeling, no AI generation)

## Source
- Method: scripted modeling — `scripts/build.py` (+ `geo_lib.py`: lathe and sweep with parametric UVs, fillets, Catmull-Rom)
- Template: TRELLIS.2 mesh measured only (heights, widths, tube/bail positions); never imported into the asset scene, not shipped
- Note: the previous run's log (v11) was read for lessons before starting; none of its scripts were reused

## Pipeline
- Scene: untouched factory scene (Cube, Camera, Light; no .blend loaded) → Cube removed before building (rule 6 exception), logged.
- Build: 20 parts under the root empty `HurricaneLantern` (origin = base centre, 1 BU = 1 m, front -Y), names SM_HurricaneLantern_*.
  Turned (32 around; globe 64, burner head 16, filler 20): Tank, Burner (neck + tray), BurnerHead, Wick, Globe, Chimney (collar + bell + bead),
  VentBand (6 recessed, flat-shaded slots), Cap, FillerCap. Swept: Tube_L/R (16 sides, flared saddle foot entering the shoulder), Bail (traced
  arch, rounded hump, ends hooked into the tube elbows), TopLoop (closed pentagon through the LoopClip tab on its foot plate), Guard (2 X's),
  Lever, Catch, Rod_L, Rod_R, Eye (hangs from Rod_R).
- Import: implicit (scripted). bbox 12.17 x 9.92 x 29.95 cm (tubes outer ±6.09, tank Ø 9.92, bail top 29.95; world bounds of all parts).
- Cleanup (`scripts/cleanup.py`): merge by distance (0 merged), loose/degenerate 0, transforms applied (Wick, clip plate scales).
  18 closed meshes: 0 non-manifold edges, all positive signed volume (outward, none flipped). Open by design: Globe (ends hidden in tray and
  collar) and VentBand (bottom ring hidden in the chimney), built outward.
- Attachment (`scripts/checks.py`, BVH surface + inside test): no floating part. Joint renders looked at (review/m1, m3, m4 joints):
  m1 found Rod_R stopping 1.6 mm short of the tube and the lever's start coming out inside the tray cavity → fixed (rod into the tube, eye
  hung from the rod, lever start inside the tray's wall, Rod_L end deeper in the burner). m4: every end enters its host (rods 3-6 mm deep,
  ray parity); joints 09/10 are the two flat ends of the hinge clip's rolled tab, embedded in its foot plate — correct for a rolled tab.
- Poly count: **10,852 tris** — 2.17x the balanced prop top (5K). Where: turned body 5.4K (32 around), globe 1.5K (64, glass rule),
  tubes 1.3K (16 sides), wires 2.6K. Reduced from a first 14.3K by pruning flat profile runs and wire samples (shape kept). Further
  reduction PROPOSED, not applied (rule 6) — see Open points.
- Texturing (`scripts/materials.py`, `bake.py`, `atlas.py`): ONE procedural brass (M_Src_Brass, fake user in the .blend) baked into three
  texture sets — Body (tank group), Top (chimney group), Frame (tubes + wires) — so every part is the same metal; smoked glass (M_Src_Glass)
  baked into its own set. UVs: parametric (u around, v along) per part, packed by real surface (Body/Top ~47 px/cm at 1024, Frame 75 px/cm,
  long wires compressed along their length).
  Fields: 3-scale patina noise (dark/mid from the palette, base colour at a real reflectance), grey tarnish blotches + cap greyer, dark
  blotches, faint vertical streaks, edge wear from per-part curvature percentiles (p90→p99; p75→max where rings quantise; wires uniform
  0.55) x noise patches + bright specks, ~1 mm grain, pits and scratches in colour, AO cavity darkening, crust (non-metal, minority) from
  local AO and the foot, kerosene drip below the filler (soft wavy film, glossy, still metal); roughness its own noise + fine field;
  relief = dents + pits + scratches + fine noise + the tubes' front seam, baked to a tangent normal map.
  Glass: smoked grey from the palette, frost specks gathered by blotches in colour + alpha (0.85-1), roughness 0.16-0.46, coat 0.6, BLEND.
  Bake: Emission → float → **sRGB bytes** for base colour; MetalRough packed (G rough, B metal); tangent Normal; empty texels mean-filled.
  1024 px, 32 samples, final. All images packed.
- Material export audit (rule 19): shipping materials M_Brass_Body / M_Brass_Top / M_Brass_Frame / M_Glass use Image Texture, UV Map,
  Separate Color, Normal Map, Principled only. GLB checked: 3 OPAQUE brass with base/MR/normal, M_Glass BLEND + KHR_materials_clearcoat,
  one TEXCOORD (the shader-only 'Param' UV is lifted out for export, kept in the .blend).
- Export: `hurricane-lantern_original.glb` 11.8 MB (PNG 1024, export_apply=False, no modifiers)
- Optimize (auto preset, individual steps, rule 20): gltf-transform resize 1024 (no-op, already 1024) → webp → draco:
  11.8 MB → **691 KB (-94 %)** `hurricane-lantern_final.glb`. Requires EXT_texture_webp + KHR_draco_mesh_compression (Draco decoder on the client).

## Review (reference-fidelity § 5 — studio_small_09 HDRI, front, elevation 12°)
- **Azimuth correction (stated):** I assumed azimuth 0 before modeling (tubes symmetric). m1 showed tubes and bail outside the photo while
  the body matched within 1-3 %. The photo/template ratio of the parts standing at ±X (tubes 4.5/4.85, bail 4.9/5.45, 4.23/4.5) is cos A
  → **A ≈ 22°**; the filler cap seen 1.3 cm right of the axis gives the sign (+, camera toward the right). Read from the geometry, not
  chosen by score; m2-m4 measured at azimuth 22°. The filler cap and drip moved from -60° (photo read at A=0) to the template's -38°.
- m1 (512 bakes, az 0): IoU 0.787. Tubes/bail cyan outside (→ azimuth), lower elbows too tight, base warm 0.106 vs 0.053, sat 0.40 vs 0.33,
  grain 33-50 % of the photo. Joints: Rod_R short, lever start in the cavity. → Fix 1: joints, wider lower elbow, filler -38°; patina
  greyer and less saturated, more contrast, darker blotches; wires more worn; glass rougher, frostier.
- m2 (512, az 22): IoU 0.815, band widths within ±2 % (base +6.5 %: the close camera's perspective there). Base warm 0.075 / sat 0.305 (ref
  0.053 / 0.327); bands 2 and 4 overshot low in saturation (0.21 / 0.20 vs 0.33 / 0.26); base grain 28 %. → Fix 2 (last round): body atlas
  split in two (texel density x2), warmer patina with tarnish kept to the cap, fine colour/roughness/relief grain, soft wavy drip, frostier glass.
- m3 (shipped file, 1024): IoU 0.815; saturation per band 0.40 / 0.29 / 0.38 / 0.23 / 0.36 vs 0.52 / 0.33 / 0.35 / 0.26 / 0.33;
  metal base colour medians 0.24-0.27 (real aged brass ~0.30, alarm < 0.15), metal 85-99 % per set, metallic mask one region (largest 99.9 %).
- m4: **verification-only** re-measure of the shipped file after the rod-end fix (geometry only, no material change) — beyond the skill's
  three measures; no correction made from it. Same numbers as m3 (IoU 0.815).
- **Remaining gaps (logged, not tuned — correction rounds used up):**
  - base band reads too clean: grain 24 % of the photo's (tool line 28 %), detail 0.016 vs 0.029 — it FELL from m2's 28 % despite the
    added fine fields. Not verified why; the WebP step smoothing sub-mm detail is a hypothesis, not checked.
  - base band warmth overshot: 0.092 vs 0.053 (m2 0.075).
  - top band (wires) saturation 0.40 vs 0.52.
  - by eye: metal lighter/browner/smoother than the photo's dark grimy bronze; globe glossier, frost fainter than the photo's dense speckle.
  - luminance +0.04-0.09 and highlights in bands 4-5 high: light-dependent, not tuned (skill § 6).

### Inventory ticked (final side-by-side review/m4/side_by_side.png, crops review/crops/)
- [x] top loop: closed pentagon, apex up, bottom bar through a rolled tab on a foot plate on the cap
- [x] cap: flange with rolled edge, raised tier, top plate (tiers slightly flatter than the photo's)
- [x] vent band: 6 recessed dark slots all round
- [x] chimney / bead / rounded shoulder · [x] bell flare + rolled lip · [x] collar, dark neck, bright rim
- [x] globe: egg-shaped, dark smoked grey, frost specks — present, but fainter and glossier than the photo (gap above)
- [x] guard: two wires crossing in an X in front, ends in collar rim and tray rim; back X = invention (wires meet in a V at the top rim)
- [x] tray with rolled rim, burner neck + flange, burner head and flat wick visible through the glass
- [x] tank: foot bead, two embossed rings, rounded shoulder
- [x] filler cap front-right, ribbed, rim + recessed top; kerosene drip below it
- [x] air tubes: arms into the chimney, legs leaning out, lower elbows onto the shoulder on a flared foot; seam only in the normal map (faint)
- [x] bail: traced arch, rounded hump at the peak, ends hooked into the tube elbows
- [x] right lift lever, left U catch, left rod, right rod + hanging eye
- Inventions (no view shows them): guard's back X, tank's back and underside, sides of lever/catch.

## Shortcuts / deviations (stated)
- Real size (0.30 m) and camera elevation (12°) are assumptions; the azimuth was misread at 0 before modeling and corrected after m1 (above).
- 4 fidelity runs instead of 3: m4 only verifies the shipped file after a geometry-only joint fix.
- The rod-end fix was applied by moving the rods' end vertices in the scene (UVs untouched, no re-bake); `build.py` carries the same values,
  but re-running the whole chain would re-pack the Frame atlas slightly differently (rod lengths feed the packer) and re-bake.
- Normals: recalculated by signed volume on closed meshes; the two open shells are outward by construction.
- Review bakes at 512 px / 16 samples; only the final bake at 1024 / 32.

## Open points (for the user)
- Triangle count 10,852 (2.17x the tier top) — propose, none applied: drop the guard's back X (invention, -448), body lathes 32→24 around
  (-1.3K, facets visible up close), globe 64→48 (-380, against the glass rule), wires 6→5 sides (-400). Say which, or keep.
- Optional third look round on the surface (tank grime/grain, warmth; denser globe frost) — the measured gaps above.

## Licenses
- Reference image Lantern_01.png: Poly Haven preview (CC0) — reference only, not shipped
- TRELLIS.2 template: measured only, not shipped
- studio_small_09 HDRI (Poly Haven, CC0, local copy bench/runs/_refs/hdri): review lighting only, not shipped
- Shipped geometry and textures: created in this session (scripted + procedural bakes)

## Files (compact)
- hurricane-lantern_original.glb (11.8 MB) · hurricane-lantern_final.glb (691 KB) · hurricane-lantern.blend (13.1 MB, procedural sources kept)
- scripts/ (build, geo_lib, cleanup, checks, atlas, materials, bake, export, preview, run_all, crops, measure_photo, probe_template, sheet)
- review/ (crops, profile.json, lookdev renders, m1-m4 fidelity renders and joints)
- Removed (own intermediates, compact mode): review/m1/review.glb, review/m2/review.glb, optimize steps 1.glb/2.glb, hurricane-lantern.blend1

## Checkpoint
- Last completed step: EXPORT (+ OPTIMIZE), shipped file measured (m3, m4)
- Timestamp: 2026-10-01 15:20
