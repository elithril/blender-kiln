# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft; up to 10K reported, not cut)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling in Blender (user: no marketplace, no AI)
- Output folder: /private/tmp/kiln-bench/v300v18/ref-lantern/work/generated-assets/hurricane-lantern
- Live view (Kiln Studio): off — auto mode, unattended run
- Environment: Blender 5.2.2 LTS, MCP for Blender addon 1.8 (protocol 14, up to date); libraries:
  polyhaven on, sketchfab off, polypizza off; generators all off. Build runs headless
  (`Blender -b --factory-startup`, reproducible script); the open Blender (factory scene, unsaved) is used to look.

## Reference Image
- Path: /private/tmp/kiln-bench/v300v18/ref-lantern/refs/Lantern_01.png (394×1023, alpha cut-out already present)
- Assumptions (auto mode, one photo):
  - Real size: total height to the bail's top 0.36 m (body base→cap top ≈ 0.26 m, the usual
    size of a Feuerhand-276-type hurricane lantern). 0.352 mm per image pixel.
  - Camera elevation: 18°, read on the fount's bottom rim (r 56.5 mm, ellipse minor ≈ 18 mm →
    asin(0.32)). Silhouette heights converted z_real = (z_img − 17 mm) / cos 18°.
    Under every wide rim (bell, burner tray, fount shoulder) the photo's outline is that rim's
    ellipse, not the part below — read that way.
  - Azimuth 0: the two air tubes are symmetric left/right (±X), the filler cap is front-right.
  - Unseen: the back and underside. Kept plain and closed; the wire guard is continued round the
    back as the same X pattern (its dark wires show through the glass).
- Brief enrichment (from 3× crops): see Inventory.
- Visual comparison: pending

## Intent (before the first primitive)
- Palette (sRGB, sampled dark / mid / light):
  - main — aged bronze-brass sheet: (19,15,12) / (38,30,24) / (85,67,52); warm, R>G>B
  - secondary — wire brass, a little yellower and brighter: (29,21,14) / (52,39,23) / (104,76,48)
  - glass — smoked neutral grey, alpha ≈ 0.9: (17,16,16) / (28,27,26) / (59,55,52) + frost specks
  - accent — grey-blue tarnish patches (cool lit spots on bell, collar, fount)
  - soot — burner inside the globe, near black, non-metal
- Materials: M_Metal_AgedBrass (sheet parts, metal, roughness 0.3–0.7), M_Metal_BrassWire
  (bail, handle, guard, levers; metal, smoother), M_Glass_Smoked (dark grey, rough 0.1, coat,
  frost). Soot and fuel stain are layers inside M_Metal_AgedBrass (non-metal crust, minority).
- Finishes: rolled beads on every rim (cap, bell, collar, tray, fount); fount ribs; seam line
  along each air tube; vents under the cap; wear lighter on edges/beads, patina dark in cavities,
  faint vertical streaks; a fuel stain run under the filler cap.
- Metal texture: procedural (no Poly Haven aged-brass set; metal_plate_02 looked at — right smudges
  but its plate seams would print lines on turned parts). 3D fields baked to the UVs, composited in numpy.

## Inventory (from 3× crops; how parts meet)
1. Fount (tank): wide drum r 56.5 → 51.5 mm, rolled bottom bead, 2 ribs, domed shoulder rising to the burner seat → SM_..._Fount
2. Filler cap: small stacked cylinder (r ≈ 12 mm, 2 rings + flat top) on the shoulder, front-right; SITS INTO the shoulder → Fount
3. Fuel stain: dark run on the fount wall under the filler cap → texture layer
4. Burner neck: cylinder r ≈ 20 mm on the fount's top, ENTERS it → Burner
5. Burner tray (globe seat): cup r 33.5 mm with a rolled rim; glass rests IN it → Burner
6. Burner cone + flame spreader: dark sooty dome and slotted tab inside the globe → Burner (soot)
7. Wick knob: rod from the burner neck to the right, ending in a disc seen edge-on → Burner
8. Globe: barrel glass r 34 → 41.5 → 33 mm, smoked, frosted → Glass
9. Globe collar (top globe plate): band r 32–34 mm with rolled bead, globe top INSIDE it → Chamber
10. Bell: flared skirt r 32 → 42 mm with rolled rim, over the collar → Chamber
11. Air chamber: cylinder r 31.5 mm above the bell → Chamber
12. Vent gallery: short ring r 23 mm with dark slots under the cap → Chamber
13. Cap: thin disc r 35 mm, rolled edge, stepped dome on top → Cap
14. Cap handle: pentagonal wire loop, legs HOOKED under a strap clip on the cap top → Handle
15. Air tubes ×2: Ø16.5 mm, splayed ~5.6° (wider at the bottom), seam line along; top elbow ENTERS the
    chamber at z ≈ 206 mm; bottom elbow ENTERS the fount shoulder → Tube_L / Tube_R
16. Bail: big wire loop, dip at the top centre, ends HOOKED into eyes on the tubes' outer side below the top elbow → Bail
17. Wire guard: two wires crossing in an X in front of the globe (and behind), from collar to tray → Guard
18. Globe-lift lever, right: bent wire from the tray out to the right tube, hooked through a guide ring → Lever
19. Left lift link: narrow wire staple on the left tube's inner side + horizontal rod from the left tube to the tray → Lever

## Prompts (copy-paste ready)
- Concept art: none (user image)

## Source
- Method: scripted (Blender Python, headless), from the reference image

## Pipeline
- [1] CONFIG: done — environment scan (Blender 5.2.2, MCP up to date, polyhaven on)
- [2] BRIEF: done — "Rebuild the hurricane lantern of Lantern_01.png as a realistic game prop, glTF,
  balanced, auto, compact, scripted only; match proportions, parts, materials and colours."
  Assumptions above (0.36 m, 18°, az 0, back unseen).
- [3] SOURCE: done — creation, scripted (user's choice in the brief: no marketplace, no AI). Method:
  lathe profiles from the measured silhouette (§ 2), swept tubes/wires on traced or measured
  centrelines, one script `scripts/build_lantern.py` run headless. Metal base colours kept above
  fidelity_check's floor (sRGB luminance 0.15): patina ≈ 0.27, cavities ≈ 0.19, worn edges ≈ 0.45.

- [4] IMPORT (scripted, implicit): 24 parts built by scripts/build_lantern.py, 10,704 tris,
  0.14 × 0.11 × 0.36 m, on the ground, origin at base centre. Factory Cube removed from the open
  Blender (untouched factory scene, rule 6), geometry imported there to look: front/3-4/right/back read right.
- [5] CLEANUP (in scripts/texture_lantern.py): transforms applied, merge 0.01 mm → 0 verts merged
  (built welded), 0 degenerate, 0 loose, 0 fused edges; glass open shell (its 2 rims) by design.
  Attachment (BVH): every part ≤ 0.5 mm from another or passing into it (wick shaft, bail eyes:
  vertex check read 0.8–1.0 mm but they pass through their hosts — confirmed by overlap).
  Joined into 4 game meshes: SM_HurricaneLantern (metal, 6,576), _Wire (1,884), _Bail (708, origin on
  its hinge axis z 0.186 m), _Glass (1,536); children parented to the body. Total 10,704 tris:
  balanced prop top is 5K, this is 2.14× — spent on round parts and wires; trimmed in the rounds
  rather than decimated (thin parts are never decimated).
- [5b] TEXTURING: metal UVs by Smart UV Project; glass cylindrical UVs. Metal: fields baked 1024
  (AO cavity 10 mm, AO-inside edges 3.5 mm, 6 noises, position, normal) → numpy composite → 
  T_HurricaneLantern_BaseColor (sRGB byte), _MetalRough (G rough, B metal), _Normal (pits + dents
  bump, tangent). Layers: mottled patina, cavity dark/rough, grey tarnish (up-facing bias),
  edge wear by AO-inside percentile 88–99 × noise, faint vertical streaks, fuel stain under filler
  cap (glossy), soot non-metal in the burner tray and under the bell, dark vent slots.
  Glass: frost generated in UV space (specks gathered by blotches) in colour + alpha.
  Wire: values only. Material audit clean (no procedural node left), all images packed.
- Rounds (reference image), elevation 18°, azimuth 0, studio_small_09:
  - v1 (review/round1.glb): silhouette IoU 0.868, bands 0.25/0.80/0.89/0.89/0.92 (band 1 = wires),
    widths within ±5 % below the bail; face IoU 0.65 (f 0.887, offset -1.1 mm); band 1 warm 0.27 vs 0.10.
    Joints (4) looked at: clip into cap dome, staple hooked into tube, lift rod into tray — correct.
- Review round 1 (review/round1.png, round1_clay.png, front/side_by_side.png; fresh reviewer + mine):
  1. side_by_side, glass: clear and glossy with white snow patches; photo is dark smoky blue-grey,
     fine sparse specks → glass base (34,37,41), alpha 0.9, specks finer/sparser, no blur fattening
  2. side_by_side, globe upper half narrow (overlay red at z 135–150) → upper glass profile +1 mm (shape round 1)
  3. overlay, tube elbows: top bend has no inner radius, bottom bend too low/steep (red fills both
     inner corners) → top fillet R 8 → 13, bottom end flatter (to r 34, z 44), R 18 (shape round 1)
  4. side_by_side, filler cap small and hidden behind the neck → r 12 → 13, out to 45 mm, top 57 mm
  5. side_by_side, tank front: pale pixelated stripe = my fuel stain at roughness 0.2 mirroring the
     studio → darker (52,42,34), roughness 0.34, soft edges
  6. close-up / side_by_side: bail and handle bright saturated gold, stray colour → wire (96,78,58), rough 0.5
  7. colour tiles: the collar band bright yellow brass — the AO-inside edge mask reads the 0.8 mm shell
     as an edge everywhere → edge wear from baked Pointiness (curvature), percentile 90–99.5
  8. (mine) 10,704 tris, 2.14× the tier top → guard 22 → 15 samples, bail side every 5th point,
     handle/staple fewer arc points (build density, not a decimation)
  Detail, next round (same metal region, one change per round): tank lighter and more washed out
  than the photo's near-black bronze; little wear on the cap top.
  Underside not shown by the sheets — checked in the headless review renders (under view) next round.
  - v2 (review/round2.glb): silhouette IoU 0.880 (+0.012), face IoU 0.66 (f up); changed: tube elbows,
    upper glass, filler cap, glass/wire/stain materials, edge mask; kept. Normal map std 0.006 — relief invisible.
- Review round 2 (review/round2*.png; fresh reviewer: nothing blocking, "would show as is"; mine: one):
  1. (mine, side_by_side) metal reads flat orange-brown and matte; photo near-black bronze with crisp
     polished highlights → palette darker/neutral DARK (58,47,40) MID (84,66,52), base roughness 0.40 → 0.30,
     tarnish less biased to up-faces (tank top read grey) — the one metal change this round
  2. side_by_side, glass clean and very glossy → roughness 0.08 → 0.16, coat roughness 0.15, specks ×2
  3. side_by_side, filler cap barely reads → r 13 → 13.5, top 57 → 59
  4. bail peak angular/wavy vs the photo's rounded hump → keep every traced top point, peak point dropped
  5. (mine) last trims to ≤ 10K: burner cone one ring, filler cap 20 → 16 sides, knob 16 → 12, eyes 12 → 8
  Next round (metal, one change each): relief/grain (normal map too weak), bright worn edges + drip streaks.
  Underside checked (review/renders/r2_colour_under.png): closed, rimmed, textured.
  - v3 (review/round3.glb): silhouette IoU 0.880 (=), face IoU 0.68 (+0.02); changed palette/roughness,
    glass finish, filler cap, bail hump, trims (10,068 tris); kept.
- Review round 3 (review/round3*.png, front/sbs_bottom.png; fresh reviewer: 2 blocking; mine: same 2):
  1. BLOCKING glass reads opaque ceramic; photo smoky but see-through (burner, dish, back wires visible),
     its sparkle is glints from a hammered surface → alpha 0.90 → 0.70, base darker, hammered normal map
     (height bumps gathered by blotches) for the glints, albedo specks down
  2. BLOCKING metal: no fine grain/scratches; cool blotches → this round: grain (normal map ×6 strength +
     horizontal hairline scratches, matching fine roughness/colour grain). Warm tone + brass edges next round
  3. sbs_bottom: goblet stem under the globe; photo a wide open dish on a short neck → burner reshaped:
     neck r 20.5 to z 66 with a bayonet bead, flat dish r 21 → 35.6 (shape round 2, the last)
  4. filler cap tall and narrow; photo squat and wide, flat lid → r 14, top 54.5 (shape round 2)
  5. collar a tall straight sleeve; photo a rounded dome narrowing to a thin band → band to 156, dome to 168
  6. close-up: vent ring reads as a pale grey band (tarnish on the bars) → gallery kept patina, slots darker
     and narrower; bail hump straight segments → Catmull-Rom subdivision on the hump
  7. tubes "slightly thick": measured Ø16.5 mm from the photo (47 px) — kept, argued
  8. bail brighter/yellower than the photo → wire (86,68,48)
  Underside: checked in round 2 (renders/r2_colour_under.png).
  - v4a: grain applied at bump distance 1.8 mm, scratches 0.6 → normal std 0.15: read as bark / lumpy
    casting (§ 4's warning) — undone halfway: distance 0.5 mm, scratches 0.25, colour grain 0.10 → std 0.034.
  - v4 (review/round4.glb): silhouette IoU 0.880 (=), face IoU 0.72 (+0.04 on v3); 9,892 tris (< 2× top,
    no reduction to propose); kept. Shape rounds now closed (2 of 2 used).
- Review round 4 (review/round4*.png; fresh reviewer: 3 blocking; mine: tone + glass):
  1. BLOCKING metal reads cold gunmetal; photo warm bronze-copper with brown mids → warm palette
     DARK (64,48,36) MID (92,68,48) WORN (180,136,84), tarnish warm (98,90,80) and rarer — this round's metal change
  2. BLOCKING grain heavy and even (stucco) → next round (same region), halve again
  3. BLOCKING glass frosted, nearly opaque, burner hidden → alpha 0.68 → 0.55, base (24,26,29), glint slope 0.12 → 0.07
  4. bail brighter/yellower than the body → wire (78,60,44), rough 0.45; thickness measured 2.8 mm, kept
  5. filler cap reads centred → φ -73° → -64° (x 20 mm), assembly
  6. vents a thin band, 7. tank ribs faint — details, left (finishes judged acceptable at game distance)
  8. side tile: bail edge-on reads as a spike — correct geometry, kept
  - v5 (review/round5.glb): silhouette IoU 0.881, face IoU 0.66 (−0.06: the clearer glass now shows the
    burner and the background through it, which the face block counts as details — glass is the photo's
    "smoky but see-through", kept; shape unchanged). Side_by_side: warm bronze now reads like the photo.
- Review round 5 (review/round5*.png, front/sbs_cap.png; fresh reviewer: 2 blocking):
  1. BLOCKING grain coarse, even, procedural → this round's metal change: bump distance 0.5 → 0.3 mm,
     scratch weight 0.25 → 0.12, colour grain 0.10 → 0.06
     ("too orange" — round 4's reviewer said "cold gunmetal": the swing § 5 warns of; tone left as is)
  2. BLOCKING filler cap small, low, hidden (3rd reviewer to say so). Crop shows why: the photo's fount
     has a tall domed shoulder (silhouette sides: r 51 @ z 40, 49.6 @ 43, 47 @ 47.4) rising into the burner
     seat, the cap sitting up on it, lid seen from above; mine rose 7 mm. Inventory line 1 ("domed shoulder
     rising to the burner seat") not met — a build error, not a reshape for the score → dome rebuilt to
     z 57, burner seat/bead raised 6 mm, wick shaft to z 63, cap moved onto the dome (radial 39, φ -64°)
     with a wide flat lid r 15, top 61; fuel stain ring follows it
  3. glass bluer and clearer than the photo (round 3: too opaque) → halfway: alpha 0.55 → 0.61, base neutral (26,27,28)
  4. bail lighter/golden → wire (70,54,40), rough 0.5
  5. globe "band", 6. vents shallow — details, left
  Tris: + dome rows, − guard sample and burner cone ring → kept under 10K.
  - v6 (review/round6.glb): silhouette IoU 0.884 (+0.003), face IoU 0.67; 9,940 tris; normal std 0.018; kept.
    The fount dome and the cap on it now read like the photo's crop.
- Review round 6 (review/round6*.png; fresh reviewer: nothing blocking, "would show as is"; mine: none blocking).
  Cheap details fixed before the confirming reading:
  1. filler cap still a thimble → wider and lower: body r 14.5, lid r 16.5, top z 58.5, radial 41 at φ -60°
  2. fount too clean, no grime in recesses or drips → one ageing layer: cavity weight 0.75 → 0.95 (p3–p70),
     drip streaks on the fount wall (darkening 0.14 → 0.30 below z 40 mm)
  3. bail crest sharper than the photo's soft hump → 2 smoothing passes on the crest points
  Left as details: vents read as a band (painted slots), cap dome a little low, tube-into-fount joint
  checked by the attachment test (passes through the dome) — looked at in the final look.
  - v7 (review/round7.glb): silhouette IoU 0.883 (−0.001, kept), face 0.66; 9,972 tris.
- Review round 7 (review/round7*.png; two fresh reviewers, both: 2 blocking — not a clean reading):
  1. BLOCKING (A, B) fount: pale grey-white blotches (the grey tarnish layer) read as mould/smears;
     photo has dark grime and streaks → tarnish weight 0.70 → 0.35, rarer (threshold 0.78–0.92)
  2. BLOCKING (B; A detail) orange-copper cast; photo darker brown bronze → palette halfway between
     v4 (cold) and v5 (orange): DARK (60,46,36) MID (86,64,46) WORN (168,128,82). One colour change:
     palette + tarnish share, roughness/grain untouched.
  3. (A blocking, B detail) filler cap small/hidden: measured on side_by_side, same width (~28 mm)
     and height as the photo's; the photo's lid top is near-black and pops → dark lid top
     (52,52,55), metal, rough 0.55 — same colour change
  Details left: tubes "slightly thick" (measured), cap dome low, vents painted, globe sides, extra guard frame
  (not seen in the photo crops — not invented).
  - v8 (review/round8.glb): silhouette IoU 0.883, face 0.64; 9,972 tris; uv_check 0 FAIL 0 WARN.
- Review round 8 (review/round8*.png; fresh reviewer: 1 blocking) — the cap for a prop (8). Shipped, open items listed:
  1. (blocking for this reviewer) tone still orange-copper and wear too even vs the photo's darker brown
     with directional grime — the tone swung across reviewers (r4 cold, r5/r7/r8 orange); not changed past the cap
  2. vents painted, not holes; cap dome single tier (photo: two tiers); 3. glass a little light/even;
  4. fount beads shallow; 5. filler cap's dark lid can read as an open cup; 6. tubes measured Ø16.5 mm,
     bail 2.8 mm — kept; 7. bell skirt slightly narrow.
  After the rounds: metal UVs packed (pack_islands after Smart UV, 46 % → more of the tile used),
  same 3D fields rebaked — content unchanged, measured again below.
- [6] OPTIMIZE (auto, glTF): hurricane-lantern_original.glb 5.33 MB (exported with tangents; material
  audit clean; every map in its glTF slot: metal baseColor + metallicRoughness + normal, glass baseColor
  (alpha BLEND) + normal, wire factors) → gltf-transform resize 1024 → webp q90 → draco, separate steps
  (rule 20) → web/hurricane-lantern_final.glb 627 KB (−88 %). Geometry untouched, 9,972 tris.
  hurricane-lantern_preview.glb = copy of _original (no Draco, no WebP: opens in Quick Look; extensionsUsed none).
  gltf-transform validate on _final: 0 errors, 0 warnings (2 tangent warnings fixed by export_tangents);
  info only: Draco not validated, unused TEXCOORD_0 on the untextured wire/bail.
- [7] EXPORT: web/hurricane-lantern_final.glb, 627 KB, 9,972 tris, 4 meshes (SM_HurricaneLantern +
  _Wire, _Bail [pivot on its hinge, z 0.186 m], _Glass, parented), 3 materials, glTF 2.0 Y-up,
  export_apply False (rule 18), tangents on. 0.14 × 0.11 × 0.36 m, on the ground, origin base centre.
  Final measure ON THE SHIPPED FILE: silhouette IoU 0.883 (same as the .blend — nothing lost on export),
  face IoU 0.63. Rule 2: shipped file re-imported in the open Blender and looked at from two opposite
  three-quarters; headless review renders (review/renders/final_*) q1/q3/top/under in colour + matcap.
  .blend saved by the headless build (save_version 0, no .blend1).
- Inventory ticked on the final side_by_side: 1 fount ✓ · 2 filler cap ✓ · 3 fuel stain ✓ (faint) ·
  4 burner neck ✓ · 5 tray/dish ✓ · 6 cone + spreader ✓ (seen through the glass) · 7 wick knob ✓ ·
  8 globe ✓ · 9 collar ✓ · 10 bell ✓ · 11 chamber ✓ · 12 vents ~ (painted slots, not holes) · 13 cap ✓
  (single-tier dome) · 14 handle + clip ✓ · 15 tubes ✓ (seam line along them NOT modelled) · 16 bail ✓ ·
  17 guard ✓ · 18 lever ✓ · 19 staple + lift rod ✓
- Visual comparison: close match in shape (silhouette 0.883); materials partial — see open items, round 8.
- Storage (compact, auto, nobody to ask): intermediates kept and listed for the user — review/ (191 MB:
  round GLBs, sheets, fidelity runs), ref/ (crops, masks, traces), tex/ (HDRI, thumbnails), scripts/.
- Kiln Studio: not started (Live view off, unattended run).

## Licenses
- Reference image: user-provided (Lantern_01.png)
- Geometry and all textures: generated by this session's scripts (procedural, no third-party texture)
- studio_small_09 HDRI (review lighting only, not shipped): CC0, Source: Poly Haven (polyhaven.com), via the public API
- Poly Haven thumbnails looked at (metal_plate_02, metal_plate, rusty_metal_03, rusty_metal_sheet): CC0, not used

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-29 15:13
