# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modeling (brief: no marketplace, no AI generation)
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 13, up to date)

## Reference Image
- Path: <repo>/bench/runs/_refs/Lantern_01.png (394x1023, RGBA, transparent background)
- Single view, front, slight 3/4 none (side tubes symmetric about the axis) -> azimuth 0
- Camera elevation: read on the rims — cap brim ~10 deg, bell rim ~12 deg (24/119 px), tank bottom ~24 deg
  (close perspective camera). Review elevation fixed BEFORE modeling at 12 deg (rim nearest mid-height).
- Real size: ASSUMPTION — no scale given. Overall height with the bail raised = 0.358 m
  (body without bail/loop ~0.255 m, tank diameter ~0.117 m). Scale 0.365 mm/px.
- Back, sides and underside: not shown by the photo. Back is assumed rotationally symmetric
  (turned parts) and mirror-symmetric (tubes, bail); filler cap placement on the back is unknown -> one filler cap, front-right, as seen.

### Inventory (from 2-3x crops in review/crop_*.png)
- top loop: closed PENTAGON wire (apex up), its bottom edge runs THROUGH a horizontal hinge barrel lying on the cap top -> SM_Lantern_TopLoop + SM_Lantern_TopHinge, on Cap
- cap: flat stepped top — small raised dome, step ring, wide flared brim with a rolled edge -> SM_Lantern_Cap
- vent band: short cylinder under the brim with dark rectangular slots all around -> SM_Lantern_Hood (cut by boolean), dark interior SM_Lantern_VentCore
- hood: cylinder with a groove band, flaring to a bell skirt above the globe; side tubes ENTER it -> SM_Lantern_Hood
- globe collar: neck under the bell, widening into a beaded rim that holds the globe top -> SM_Lantern_Collar
- globe: barrel-shaped glass, dark smoky, frosted specks and scratches -> SM_Lantern_Globe (own material)
- globe guard: two crossing wires (an X at the front) wrapped round the globe, collar to dish -> SM_Lantern_GuardA / GuardB
- globe seat: dish ring under the globe, on the burner neck -> SM_Lantern_Burner
- burner neck: short cylinder with a flange, rising from the tank dome -> SM_Lantern_Burner
- side air tubes x2: thick tubes, bend into the hood at the top, splay slightly downward, bend inward into the tank dome at the bottom -> SM_Lantern_TubeL / TubeR
- bail: wide wire arch, ROUNDED peak (traced: no dip on this image), ends HOOKED into the outer side of the tubes at the hood level -> SM_Lantern_Bail
- globe brackets: "]"-shaped wires from each tube to the globe seat dish -> SM_Lantern_BracketL / BracketR
- lift lever: rod from an eye ring on the right tube toward the burner -> SM_Lantern_LiftLever
- tank: cylinder tapering out toward the bottom, 2 rolled ribs + bottom bead, low domed top -> SM_Lantern_Tank
- filler cap: small knurled cap on the tank top, front-right (~19 deg), drip stain running down below it -> SM_Lantern_FillerCap (+ stain in the tank texture)

### Palette sampled (rendered sRGB, dark / mid / light = 10/50/90th luminance percentiles)
- tank #17120e / #26201b / #4a3c2e (sat 0.32)
- hood #120d0a / #261d17 / #4d3a2c (sat 0.39)
- tubes #110c09 / #2a1d16 / #5b3e2c (sat 0.47)
- cap #201b18 / #34302e / #555453 (sat 0.18, greyer — dust)
- wire (bail) #18120c / #2f2315 / #62462c (sat 0.48)
- glass #0f0e0e / #171616 / #433d39 (sat 0.07-0.09, neutral dark)

## Prompts (copy-paste ready)
- Concept art: none (source: user image)

## Source
- Method: scripted (Blender Python, lathe profiles measured from the reference pixels, wires traced)

## Pipeline
- Scene: Blender factory scene (Cube, Camera, Light, no .blend loaded) — factory Cube removed before building (rule 6 exception). Camera and Light left untouched, not exported.
- Build: 18 separate parts in collection "Lantern"; turned parts lathed from the measured core profile
  (cylindrical UVs: u around, v along the profile), wires as NURBS/filleted curves beveled round and converted to mesh.
  Bail traced from the pixels and symmetrised (L/R average). Vent slots: 8 cut by an EXACT boolean into the vent band.
- Attachment (§3, BVH surface distance, inside counts as attached): 0 floating parts. Bail ends, brackets and tubes are inserted into their hosts.
- Cleanup: merge by distance (0 removed), recalc normals, remove loose, dissolve degenerate, fused edges 0 on every part;
  open edges only on the globe rims (128, intentional — hidden in the collar and the dish). Transforms applied, origin = base centre (z=0).
- Dimensions (bbox): 0.139 x 0.118 x 0.354 m (W x D x H, bail up). Tank diameter 0.118 m.
- Poly count: 9,514 tris — ABOVE the balanced prop range (1.5-5K) by +90% (rule 4: reported, not blocked).
  Heaviest: Hood 1,502 (vent boolean), Tank 1,152, Globe 1,152 (64 segments, per the glass rule). No decimation proposed-and-applied;
  a reduction to ~6K is possible by dropping turned parts to 24 segments — ask if wanted.
- Texturing: one material + one texture set per major part (Tank, Hood, Cap, Collar, Burner, FillerCap, TubeL, TubeR: base colour,
  roughness, metallic, normal); Glass: RGBA base (alpha frost); all wires share M_Lantern_WireBrass (values only).
  Procedural sources kept in the .blend as M_*_Proc (fake user): independent colour / roughness / relief fields, 3-octave grime with
  vertical streaks, curvature wear thresholded at the part's own 90th/99th percentiles, drip stain under the filler (UV band).
  Baked through Emission into float images, converted to sRGB bytes before export; normals baked tangent-space. Final bake 1024
  (Tank, Hood, Tubes, Glass) / 512 (Cap, Collar, Burner, FillerCap). All images packed.
- Material export audit: 0 procedural nodes in any exported material; base colours sRGB 8-bit; data maps Non-Color.

### Review (§5) — 3 measures, 2 correction rounds; fidelity_check.py, front, elevation 12 deg, azimuth 0, studio_small_09 HDRI
- m1 (.blend, 512 bakes): IoU 0.807. Gaps: base band width +11% (tube bottoms bent too high), filler cap too small/too far back
  (invisible from the front), wire too warm (+0.09), detail ~half (0.016-0.021 vs 0.030-0.040), glass highlights 0.054 vs 0.006,
  tubes 99% metal (wear threshold degenerate on uniform curvature).
  -> round 1: tube bottoms re-routed, filler moved to r=128 px / 17 deg and enlarged, bail resolution halved (1,244 -> 620 tris),
     metal base +15% (toward the 0.30 physical median), wire desaturated, glass darker/more opaque, micro colour + scratches, bump x1.4,
     wear threshold floored.
- m2 (.blend): IoU 0.824, band 5 width fixed (+11% -> under the 8% threshold). Remaining: detail low, glass highlights, grime too blotchy/grey,
  tubes copper. Normal map std only ~0.01-0.02.
  -> round 2: grime softer & browner, smaller blotches; tubes darker, 50% grime; pits/scratches sharper (bump distance x2);
     glass roughness 0.18, alpha >= 0.8; filler lid lowered.
- m3 (SHIPPED hurricane-lantern_final.glb, 64 samples): IoU 0.824; bands 0.29 / 0.75 / 0.88 / 0.83 / 0.87; widths within +2..+7%
  except band 1 (thin bail/loop, IoU not meaningful there). Saturation bands 2-3-5: 0.32/0.36/0.33 vs ref 0.33/0.35/0.33 — matched.
  Colour survived export (no black base colour). OPEN GAPS, not closed (round limit reached):
  texture detail 0.014-0.024 vs ref 0.029-0.040 (surfaces read cleaner than the photo); glass band saturation 0.17 vs 0.26 and
  highlights 0.053 vs 0.006 (glass reads clearer and glossier than the reference's smoky frosted globe);
  luminance +0.07..0.09 (light-dependent alarm, not tuned).

### Inventory tick (enlarged crops of review/m3/side_by_side.png vs reference)
- top loop pentagon on hinge barrel: present, right
- cap stepped dome + brim: present, right
- vent slots: present in geometry, barely visible from the front (in the brim's shadow) — weaker than the reference's dark slots
- hood + groove + bell skirt: present, right
- collar with bead: present, right
- globe: present; reads clearer/glossier than the reference (open gap)
- guard wires crossing in an X: present, right
- seat dish + burner neck: present, right
- side tubes: present; bottom joint simplified — no flat sheet-metal flange where the tube meets the tank
- bail, rounded peak, hooked into the tubes: present, right
- globe brackets L/R: present
- lift lever + eye ring: present (eye smaller than the reference)
- tank, ribs, bottom bead: present; tank reads a little short against the photo (its close camera stretches the base) — not refitted, by rule
- filler cap: present, front-right; narrower/taller than the reference's squat lid
- drip stain under the filler: present, faint
- Visual comparison: close match on proportions and parts; partial match on surface detail and glass

## Optimize (auto preset, individual steps — rule 20)
- gltf-transform resize 1024 -> webp -> draco: 22.63 MB -> 1.64 MB (-93%). Geometry untouched. Draco + WebP need decoder support on the client
  (KHR_draco_mesh_compression, EXT_texture_webp are REQUIRED extensions).

## Export
- hurricane-lantern_original.glb: 22.6 MB (PNG textures, uncompressed) — export_apply=False, +Y up
- hurricane-lantern_final.glb: 1.64 MB, 9,514 tris, 18 meshes, 10 materials, GLB
- hurricane-lantern.blend: full history, procedural sources, packed bakes

## Licenses
- Reference image Lantern_01.png: provided by the user (Poly Haven Lantern_01 preview, CC0) — used as visual reference only
- studio_small_09 HDRI (review lighting only, not shipped): Poly Haven, CC0
- All geometry and textures: generated in this session, no third-party assets

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-01 11:15
