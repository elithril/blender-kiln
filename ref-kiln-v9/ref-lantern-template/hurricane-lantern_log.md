# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modeling (Blender 5.2.2 LTS, blender-mcp addon 1.8, protocol 13)

## Reference Image
- Path: bench/runs/_refs/Lantern_01.png (394×1023, alpha)
- Proportions template: bench/runs/_refs/trellis/lantern_trellis.glb (TRELLIS.2) — measured with
  tools/template_profile.py only; its mesh and texture are NOT shipped.
- Assumptions (auto mode, not asked): real height 30.0 cm to the bail top (usual size, photo has no
  scale); camera elevation ~10° (bell rim ellipse reads 8°, base 16°, nearest mid-height kept);
  front view, azimuth 0. Back and underside are not visible: built by rotational symmetry (invented).

### Inventory (from 2–4× crops, before modeling)
- tank (fount): drum r 4.9→4.2 cm over 0–3.3 cm, bottom bead, two rolled ribs, domed shoulder to 3.9 → SM_HurricaneLantern_Tank
- filler cap: short cylinder with rim, on the shoulder front-right, drip stain below → Tank_FillerCap, INSERTED into shoulder
- burner neck: r ~1.7 cm, 4.0–6.0 cm → Burner, rising from the tank
- globe gallery: cup r 1.7→3.1 cm, 6.0–7.6 cm, holds the globe bottom → Gallery, on the burner
- wick raiser: horizontal rod to the right at ~5.9 cm ending in a vertical ring by the right tube → WickRod
- globe: clear smoky glass, frosted specks, bulb r 3.48 max at ~9.3 cm, 7.2–12.8 cm → Globe (own material)
- globe collar/plate: metal band r ~2.8, 12.6–14.2 cm, neck to the bell → Collar, globe INSERTED in it
- guard wires: two tilted wire loops crossing as an X front and back, gallery rim → collar rim → GuardWire_01/02, ends WELDED to gallery and collar
- lift rods: horizontal wires from gallery rim out to each tube, turned up along it → LiftRod_L/R
- bell / hood: flared skirt r 3.5 at 15.3 cm, then cylinder r 2.7 to 19 cm with a bead at ~17.3 → Hood
- chimney: band r ~2.0 cm, 19.3–20.3 cm, dark rectangular VENT SLOTS all round → Chimney
- cap: disc r 2.95 cm at ~20.6 with raised stepped dome to ~21.4 → Cap
- top loop: closed PENTAGON wire on a horizontal HINGE BARREL, legs INSERTED in the barrel; barrel resting on the cap → TopLoop + TopHinge
- side air tubes: two, ±X, ~1.4 cm radial × 1.1 cm deep, leaning out (centre 4.4 at 16 cm → 5.5 at 6 cm), bottom bent INTO the tank shoulder, top bent INTO the hood at ~17 cm → Tube_L/R
- bail: wire arch ~2.4 mm, centre line traced from pixels (r 4.9 at 17.7 → 0 at 29.9), small raised HUMP at the peak (not a dip), ends HOOKED into the tubes' outer top bends → Bail

### Palette sampled (10th / 50th / 90th percentile, sRGB)
- tank #17120f / #27211c / #45382d — hood #120d0a / #251d17 / #4e3f31 — bell rim highlights to #76685c
- cap #201b18 / #332f2d / #545352 (greyer, dusty) — tubes #120d0a / #2c1e16 / #5d3f2e (warmer)
- bail wire #16100a / #362719 / #7d6648 — glass #141313 / #1d1c1c / #3a3735 (neutral, dark interior)

### Template measures used (tools/template_profile.py, --height 0.30, 50 bands)
Tank r 4.90→4.23 (0–3.3 cm), shoulder 3.36 at 3.9 · burner 1.85→1.50 (4.5–5.7) · gallery 2.7–3.0 (6.3–7.5)
· globe 3.48 max at 9.3, 2.0 neck at 14.7 · bell skirt 3.51 at 15.3 · hood 2.73→2.61 (16–19) · chimney 1.96
· cap 2.92 at 20.7 · loop to 24.3 · tubes centre 4.4 (16 cm) → 5.5 (6 cm) · bail 5.0–5.3 at 18–19, apex 29.7.
Bail centre line traced from the photo's pixels (wire Ø 2.4 mm measured), widened toward the template at its foot.

## Prompts (copy-paste ready)
- Concept art: none (user image)
- Hunyuan3D params: N/A — no AI generation. TRELLIS.2 mesh used as a measuring template only.

## Source
- Method: scripted modeling (scripts/build.py lathe + sweep, scripts/materials.py, scripts/bake.py, scripts/export.py)
- Marketplace: none

## Pipeline
- Build: 20 parts + root empty SM_HurricaneLantern, origin at the base centre, 1 unit = 1 m
- Dimensions: 12.0 × 9.9 × 30.0 cm (assumed real height 30 cm)
- Factory Cube removed (untouched factory scene, rule 6 exception)
- Triangles: 9,964 — tier top 5,000, under 2× (10,000). Kept at construction (segment counts), no decimation:
  64-segment globe (glass rule), 32-segment tank/hood/cap, tubes 10 sides, wires 6 sides.
- Attachment (§ 3, BVH surface): 17 parts within 0.5 mm. Collar, Chimney, TopLoop read 0.56–1.18 mm by vertices
  but INTERSECT their neighbours (BVH overlap: collar×globe 76, collar×hood 48, chimney×cap 72, chimney×hood 64,
  loop×hinge 12 triangle pairs) — inserted, not floating. Fixed on the way: hood opening (0.5 mm gap to the collar
  neck), chimney base, hinge barrel ends capped (loop legs entered through open ends), wick rod 0.4 mm short.
- Cleanup: transforms applied (FillerCap), merge by distance 1e-5, degenerate dissolve, loose removed (0),
  recalc normals would flip 0 faces, fused edges 0 on every part. Open edges only at embedded ends, globe rims,
  vent slots. 1 orphan mesh removed.
- Texturing: one material + texture set per major part (Tank, Burner, Collar, Hood, Chimney, Cap, FillerCap, Tube_L,
  Tube_R, Globe), cylindrical / along-the-path UVs. Independent fields: colour (3 octaves), wear/metal mask, roughness,
  relief (pits + dents + scratches) → Emission bakes into float images, converted to sRGB bytes before export (§ 4);
  relief baked to a tangent normal map (mean 0.5, 0.5, 1.0). Glass: 64 segments, coat 1, roughness ~0.09, frost
  specks in colour + alpha (mean 0.65), neutral tint. Wires M_Brass_Wire and M_Soot (vents): values only.
  1024 px (Burner, Collar, Chimney, FillerCap 512). Procedural sources kept in the .blend as M_*_Proc (fake user).
- Export audit (rule 19): no procedural node in any exported material. export_apply=False (rule 18).
- Optimize (auto preset, individual steps, rule 20): resize 1024 → WebP → Draco. 22.45 MB → 1.67 MB (−93 %).
  Draco needs a decoder on the client. Metallic survives WebP within 2.4 points (probed on both files).
- Export: hurricane-lantern_final.glb, 1.67 MB, 9,964 tris, 20 meshes, 29 WebP textures, KHR_materials_clearcoat.

## Review (fidelity_check.py, front, elevation 10°, azimuth 0, studio_small_09)
| Measure | File | IoU | Notes |
|---|---|---|---|
| 1 | review-1 (512) | 0.785 | 10,184 tris (2.04×); bands 4–5 width +9/+11 % (tubes splay); big bright-copper blotches, highlights +0.04 |
| 2 | review-2 (512) | 0.814 | round 1: tubes moved half-way in, tris trimmed, finer/softer wear, metal +10 %, filler cap taller |
| 3 | _final (1024) | 0.814 | round 2: tube foot lower and tighter, scratches in colour, tube palette less orange |
| 4 | _final (1024) | 0.814 | **one over the 3-measure budget**: a bug fix, not a correction round, see below |

- Bug, mine: round 2 re-weighted the wear field (mean 0.625 → 0.55) without shifting its thresholds. The first
  final bake came out at 3 % metal, base luminance 0.05. Caught in the bake stats before measuring; thresholds fixed.
- Measure 3 → 4: the tool counts metal at > 0.8. My 0.14-wide wear ramp left most bare areas half-metal (0.5–0.8),
  so the fully-metal share read 6–14 %. Ramp narrowed to 0.05, same centre: 10–30 % fully metal, bare-metal base
  0.27–0.31 (target 0.30). Still under the real object's ~48 % fully-metal share. Left as is (budget).
- Remaining gaps, final file: band 5 width +9 % (tube splay where template and photo disagree by ~4 mm; the template
  was kept per § 2, half-way correction applied); saturation −0.07 in bands 2 and 4; detail −0.011 in band 2;
  luminance +0.08–0.10 and highlights +0.04 (light-dependent, not tuned).
- Not applied: "Specular IOR Level 0.35" on the bronze lived only in the procedural material; the baked rebuild
  uses Principled defaults, so it was never measured or shipped.

### Inventory tick (2× crops of the final render vs the reference)
- top loop pentagon on hinge barrel ✓ · bail with raised hump ✓ (subtle) · vent slots ✓ · cap step ✓
- hood bead + flared skirt ✓ · globe frost ✓ (reads clearer than the reference's smoky glass) · guard X ✓
- lift rods ✓ · wick rod + eye ✓ (small, barely visible front-on) · tubes bent into tank and hood ✓
- tank ribs + bottom bead ✓ · filler cap ✓ (sits lower and smaller than in the photo)
- drip stain under the filler ✗ (not built)
- wear look ✗ — blocky copper patches over grey-brown grime. The reference reads as continuous dark bronze with
  soft worn highlights. This is the largest remaining visual gap.
- back / underside: invented by symmetry (no view given)

## Visual comparison
- Verdict: partial match — proportions and parts close; surface wear pattern clearly different.

## Licenses
- Reference photo Lantern_01.png: Poly Haven (CC0), used as a reference only.
- TRELLIS.2 template: measured only, nothing of it shipped. HDRI studio_small_09 (Poly Haven, CC0): review only.
- Shipped geometry and textures: made in this session, no third-party content.

## Checkpoint
- Last completed step: EXPORT (+ final review)
- Timestamp: 2026-10-01
