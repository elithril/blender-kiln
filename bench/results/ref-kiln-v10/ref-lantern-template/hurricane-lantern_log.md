# Hurricane Lantern — Production Log

## Config
- Type: prop · Target: glTF · Tier: balanced (1.5-5K tris, soft) · Style: realistic · Mode: auto · Storage: compact
- Method: scripted modeling (Blender 5.2.2 LTS, blender-mcp addon 1.8) — no marketplace, no AI generation

## Reference Image
- Path: bench/runs/_refs/Lantern_01.png (394x1023, alpha)
- Template: bench/runs/_refs/trellis/lantern_trellis.glb (TRELLIS.2) — measured with tools/template_profile.py and a slice script (work/tube_trace.py); proportions only, mesh and texture NOT shipped
- Assumptions (auto mode, not asked): real height 29.4 cm (usual hurricane lantern ~30 cm); camera elevation ~12° read on the cap/tank rims; azimuth 0 (tubes left/right, filler cap front-right); single view — back and underside are inferred, mirror of the front.

### Inventory (from 2.5x crops: work/crop_top|mid|bot.png)
- fount/tank: flared drum, bottom bead, two ribs (z~2.0 / 3.1 cm), domed shoulder into neck → SM_Lantern_Tank
- filler cap: short cylinder on shoulder, front-right, dark oil streak running down below it → SM_Lantern_FillerCap (resting/screwed on Tank)
- burner neck + wick rod with ring knob to the right → SM_Lantern_Burner, SM_Lantern_WickRod (inserted in Burner)
- gallery cup holding the globe bottom → part of Burner
- globe: barrel/egg glass, smoky dark, frosted specks, narrows to a neck inside the hood → SM_Lantern_Globe (own glass material)
- globe guard: bottom ring + top collar band + 4 diagonal wires crossing as an X on front and back → SM_Lantern_Guard (welded to rings), SM_Lantern_GlobeCollar
- lift levers: left horizontal wire tube→ring, small hook clip on left tube; right bent lever with a small ring at the tube → part of SM_Lantern_Guard
- hood: conical skirt with rolled lip, cylinder with groove where tubes enter, rounded shoulder → SM_Lantern_Hood
- chimney with rectangular vent slots, dark interior → part of Hood, SM_Lantern_ChimneyInner
- cap: wide brim with rolled edge, stepped dome, two steps → part of Hood
- top loop: closed pentagon wire, apex up, on a hinge clip in the cap centre → SM_Lantern_TopLoop, SM_Lantern_Hinge (INSERTED/clipped into cap)
- air tubes: 2, oval section ~1.3 cm, enter the tank shoulder through a flattened foot, rise, converge slightly, bend in at z~16.9 into the hood groove → SM_Lantern_AirTubes (inserted both ends)
- bail: thin wire arch, ends hooked into eyes on the tubes' outer side at z~17, shallow dip at the peak → SM_Lantern_Bail, eyes in SM_Lantern_AirTubes

### Measures (template, cm, radius from axis)
- tank 4.9 @0 → 4.66 @1.0 → 4.4 @2.2 → 4.3 @3.1 → shoulder 3.6 @3.7 → 2.2 @4.3 → neck 1.82 @4.6-4.9 → burner 1.45 @5.7
- gallery 2.6-2.9 @6.0-6.3; globe 2.47 @6.6 → 3.43 @8.7 → 3.13 @11.3 → 2.6 @13.1 → neck 2.0 @14.0-14.6
- hood skirt lip 3.56 @14.8 → cylinder 2.67 @15.7-18.4 → chimney 1.9 @19.0-20.0 → cap 2.87 @20.1, 2.1 @20.4, top @21.0
- top loop 21.0-24.0, widest ±1.4 @22.5; bail peak 29.4, ±5.3 @17.2, ±4.3 @23.2, ±2.75 @27.7
- tubes centre x 5.35 @5.2-6.8 → 4.9 @10.5 → 4.45 @14.2 → 4.25 @15.8, bend in @16.9 to the hood; width 1.4-1.5 cm in X

### Palette (sRGB, 10/50/90th luminance percentile)
- tank #16110d / #26201b / #46392e (sat 0.33) · hood #130e0b / #261e18 / #513f2f (0.42)
- tubes #110c09 / #291d15 / #593d2d (0.48) · bail/wire #1b140e / #342517 / #6c4c30 (0.54)
- cap top #221d1a / #363231 / #555554 (0.11, greyer) · filler #2b2928 (0.07) · glass #111010 / #191918 / #37312c (0.05, neutral)

## Source
- Method: scripted (work/build_lib.py, work/build_parts.py — lathes from the template profile, sweeps along traced centre lines)
- Bail centre line: template slices, cross-checked on the photo's pixels (half-width 4.5 cm at z 21 both ways)
- Factory scene: the default Cube was removed (untouched factory scene, rule 6 exception)

## Pipeline
- Build: 13 meshes under empty SM_Lantern, 9,738 tris. First build was 12,618, then cut by lowering segment and sample counts (no decimation). That is 1.95x the balanced tier's top (5K), within the 2x tolerance. Where they go: globe (64 segments, smooth glass) 1.7K, hood 2.0K, tank 1.4K, tubes 1.4K, wires 3K.
- Attachment (BVH, surface to surface, tol 0.5 mm): first pass found burner 1.0 mm, chimney liner 2.0 mm and wick rod 1.5 mm off. Fixed; final pass has no floating part.
- Cleanup: merge by distance 0, loose 0, fused edges 0. Normals recalculated on closed meshes. Open shells by design: globe, hood, collar, burner, chimney liner (double-sided). Transforms applied, origin at the base centre.
- Texturing: one material and one texture set per region. Tank, hood (cap top greyer), air tubes (UV islands packed), burner, globe collar and filler cap each get BaseColor (Emission float bake converted to sRGB bytes), an ORM image (G roughness, B metallic) and a Normal map (Bump → tangent NORMAL bake). The fields are independent: 3-octave patina colour, sparse specks, vertical grime streaks, horizontal scratches. Metal is one soft region driven by convexity (90th-99th percentile of each part), a broad noise and the grime. A hand-placed oil drip runs from the filler cap (UV-space paint). Glass: frost specks in colour and alpha, alpha 0.68, clear coat 1, BLEND. Wires, hinge and wick rod use value-only brass; the chimney interior uses soot.
- Material audit (rule 19): only Principled / Image / Separate Color / Normal Map nodes remain. No modifiers.
- Export: hurricane-lantern_original.glb 19.8 MB (PNG). bbox 0.1206 x 0.2938 x 0.0986 m
- Optimize (auto, rule 20 individual steps): resize 1024 → webp → draco = hurricane-lantern_final.glb 1.51 MB (-92%). Draco needs a decoder client-side. WebP checked: base-colour high-pass 0.032 → 0.031, so no visible loss.

## Review (tools/fidelity_check.py, front, elevation 12°, azimuth 0, studio_small_09, 32 spp)
| measure | IoU | sat (bands 2-5, model/ref) | warm R-B (model/ref) | detail | note |
|---|---|---|---|---|---|
| r1 .blend | 0.797 | 0.40-0.42 / 0.26-0.35 | 0.12-0.13 / 0.03-0.06 | 0.037-0.041 / 0.029-0.040 | too warm, copper, specular |
| r2 .blend | 0.797 | 0.23-0.30 / 0.26-0.35 | 0.05-0.08 / 0.03-0.06 | 0.032-0.039 | read khaki-grey and matte by eye |
| r3 **final.glb** | 0.797 | 0.23-0.30 / 0.26-0.35 | 0.05-0.08 / 0.03-0.06 | 0.024-0.031 / 0.029-0.040 | shipped file |
- Round 1 → 2: metal base colour desaturated about halfway, (0.40,0.29,0.18)-(0.58,0.43,0.27) → (0.34,0.28,0.21)-(0.47,0.39,0.29). Patina roughness raised to 0.30-0.68. Glass darker, alpha 0.5 → 0.68.
- Round 2 → 3: metal hue moved to the photo's red-brown highlight (#593d2d ratio), now (0.37,0.27,0.20)-(0.50,0.36,0.26). Patina glossier (0.22-0.50), metal bias -0.10, filler cap darker and larger (r 1.2 cm, top z 4.77).
- Shape: full width +5.5 to +7.5 % on every band, core width within ±4 %. The photo reads narrower than the TRELLIS.2 template over the whole height; the template was kept as the proportion source, as the brief asked, and nothing was rescaled. Band 1 (bail and loop, thin wires) IoU 0.19 is expected for wires.
- Luminance +35-70 % and highlights 4-5 % against 0.6-1.7 % depend on the light. They were not tuned (§ 6).
- Metal checks: no base colour below 0.15 (median 0.34), no camouflage flag.
- Stopped after two correction rounds (§ 5).

### Inventory ticked on 2x crops (review/r3-final/crop_*_cmp.png)
- top loop pentagon on hinge ✓ · vent slots ✓ · stepped cap ✓ · hood skirt, groove, tubes entering ✓
- bail hooked in eyes on the tubes ✓ (eyes small) · guard X wires + bottom ring ✓ · lift levers L/R + ring ✓ · wick rod + ring knob ✓
- tank ribs and bead ✓ · oil drip ~ (present at 22°, faint in the front view)
- globe collar band ~ (taller and more prominent than the photo's) · tube feet ✗ (the photo's flared foot on the tank is not modelled; tubes are inserted plainly)
- glass frost ✗ weak: specks are baked but the globe reads clear (alpha sd 0.014)
- filler cap ~ (plain grey cap, the photo's has a bright rim)
- patina ~ less contrast between dark patina and bright worn edges than the photo, and less fine detail in the shipped GLB (0.024-0.031 vs 0.029-0.040)

## Reference Image — verdict
- Visual comparison: close match on proportions and parts; partial on surface (frost, edge-wear contrast)

## Licenses
- All geometry and textures: original, scripted procedurally in this session (no third-party asset)
- TRELLIS.2 template: used for measurements only, not shipped
- HDRI studio_small_09 (Poly Haven, CC0): review lighting only, not shipped

## Checkpoint
- Last completed step: EXPORT (hurricane-lantern_final.glb)
- Timestamp: 2026-10-01
