# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modelling (Blender 5.2.2 LTS via blender-mcp, addon 1.8, up to date). No marketplace, no AI generation.
- Scene: factory scene. The default Cube was removed before building (rule 6 exception). Camera and Light were kept, then hidden.

## Reference Image
- Path: refs/Lantern_01.png (394×1023, alpha)
- Proportions template: refs/trellis/lantern_trellis.glb (TRELLIS.2). Used only for measurements, through `tools/template_profile.py` plus front/side/top slices and renders (review/profile.json, review/template_*.png). Its mesh and texture are NOT shipped.
- Assumptions (one photo cannot settle these):
  - Real height 30.0 cm with the bail raised (usual size for a hurricane lantern). No size was given.
  - Camera elevation ≈ 12°, read on the cap rim ellipse. Azimuth 0° (front-on).
  - Back and underside: no view was provided, so they are inferred as rotationally symmetric. The tank bottom is flat.
- Inventory, from 3× crops (review/crops/) and ticked at the final review:
  - [x] Tank (font): rolled bottom bead, two stepped bands, flat domed shoulder → Tank
  - [x] Filler cap: front-right on the shoulder, stacked rims, flat top, set INTO the dome → FillerCap. Placed from the photo; the template put it dead front.
  - [x] Burner collar + neck, globe seat dish with rolled rim → Burner
  - [x] Wick holder + dark flame spreader visible through the glass → WickTube, FlameSpreader
  - [x] Globe: one smooth 64-segment shell, SMOKED dark glass with frost specks, sits inside the dish and enters the hood → Globe
  - [x] Guard: top ring round the globe shoulder, wires crossing in an X front and back, ends entering the dish rim → GuardRing, GuardWire_01–04
  - [x] Hood (bell): flared skirt, straight drum with beads → Hood
  - [x] Vent band under the cap: dark slots between 8 posts → Chimney, VentPost_01–08
  - [x] Cap: wide disc with rolled rim, raised tier, boss → Cap
  - [x] Top loop: closed PENTAGON wire through a hinge barrel lying on the boss → TopLoop, Hinge. Corners stay corners, not a teardrop.
  - [x] Air tubes: enter the hood drum horizontally, tight top elbow, slant outward down the sides, wide lower bend ENTERING the tank shoulder with the section unchanged (no foot) → AirTube_L/R
  - [x] Bail: wide arch with a small HUMP at the peak and concave shoulders, ends hooked into the tube top elbows → Bail
  - [x] Globe lift lever (left tube → under the dish → step up → right tube), latch bracket on the left tube → LiftLever, Latch
  - [x] Wick-raiser rod from the collar with a ring hung on its end → WickRod, WickRing
- Visual comparison: close match on shape and parts. Partial match on surface (see Review).

## Palette (sampled from the photo, 10/50/90th luminance percentiles, sRGB)
- tank #18120d / #2a231e / #514234 · hood #1c1510 / #2f251e / #53473d · tubes #130e0b / #2d1f17 / #5f412f
- globe #121111 / #1b1a19 / #3c3430 → dark smoked glass
- Metal base colour: physical brass reflectance, not the photo's lit value. Patina #453a31 → #5a4c3e → #6b5a47, worn brass #9c7d55. Measured base median 0.27–0.30 (the doc's real brass is 0.30).

## Source
- Method: scripted (scripts/build_lantern.py). Lathed profiles from the template radii. Tubes, wires, bail and loop are round sections swept along smooth centripetal Catmull-Rom curves; the loop is a filleted polygon. Cylindrical UVs on turned parts. UV strips on swept parts are cut into islands every 5 cm.

## Pipeline
- Import: implicit (scripted). 31 parts under the root empty SM_HurricaneLantern, collection Props_HurricaneLantern. Bbox 12.6 × 10.0 × 30.1 cm, origin at the base centre, min z = 0.
- Attachment: BVH check, nothing floating. The three ">0.5 mm" flags (flame spreader, globe, bail) are parts INSERTED into their neighbour. All 16 joint renders (review/r3_final/joints/) were looked at: every part enters its neighbour with its section unchanged.
- Cleanup: merged 0, loose 0, fused (>2 faces) edges 0, open edges 164 (the open globe shell by design, plus small fans). Transforms applied, names follow `SM_HurricaneLantern_<Part>` / `_Mesh`.
- Poly count: 9,208 tris. That is +84% over the tier top: under 2×, so reported, not cut. The triangles go to round parts: globe 64 segments, tubes 16 sides, turned bodies 36 segments. A first build at 17.5K was reduced by rebuilding at lower density (my own construction parameters), not by decimating.
- Texturing: one procedural aged-brass shader (M_Metal_AgedBrass, kept in the .blend with a fake user) baked into two texture sets so both read as one metal: Body (tank, burner, hood, chimney, cap, filler cap…) and Frame (tubes, bail, loop, guard, lever…). Smoked glass (M_Glass_Smoked) baked separately.
  - Independent fields: 3-octave patina noise + faint vertical streaks. Edge wear from per-part convexity percentiles (90th/99th) × noise, plus sparse bright specks. AO cavity. Crust (non-metal, a minority) in cavities. Roughness from its own noise, with fine circumferential scratches. Relief = Voronoi pits + broad dents → baked tangent normal map.
  - Colour baked through Emission into float, converted to sRGB bytes before export. Roughness and metallic are Non-Color.
  - Exported materials: M_Metal_AgedBrass_Body, M_Metal_AgedBrass_Frame, M_Glass_Smoked_Baked (alpha BLEND, clearcoat 1, roughness 0.1).
  - Material export audit: clean. Only Principled + image textures, max 1024.
- Optimize (auto, glTF preset, individual steps, rule 20): resize 1024 → WebP q90 → Draco (pos 14 / normal 10 / uv 12). 4.52 MB → 435 KB (−90%). Geometry untouched. **Draco needs a decoder on the client.**
- Export: hurricane-lantern_final.glb, 435 KB, 9,208 tris, 31 meshes, 3 materials, 7 textures (1024² WebP).

## Review (reference-fidelity § 5, front, elevation 12°, studio_small_09 HDRI)
| Measure | What the numbers said | What changed after it |
|---|---|---|
| 1 (round1.glb) | IoU 0.798. Frame metallic averaging 0.26: the Frame atlas was only 26 % used. Bands 2/5 too saturated (0.43 vs 0.33) and too warm, grain 13–27 % of the photo's | Frame UVs chunked + packed with rotation (92 % used). Patina greyer and blotchier (tighter ramp) |
| 2 (round2.glb) | IoU 0.798. Saturation now near the photo (band 3 slightly low). Band 5 (tank) bright with little detail (0.012 vs 0.029) | Finish layer: glossier roughness range (half-way) + fine circumferential scratches. Glass frost denser, alpha 0.72 → 0.80 |
| 3 (final GLB, as shipped) | IoU 0.798. Detail up (band 2 0.031 vs 0.040, band 5 0.015 vs 0.029). Band 5 still reads too bright under the studio light (lum 0.33 vs 0.15, highlights 0.13 vs 0.007) | — stopped: two correction rounds is the limit |

- Silhouette: the lower tubes sit about 10 % wider than the photo (band 5). This is intentional: widths come from the template, not the photo's perspective (§ 2).
- **Known remaining gaps** (not fixed, round limit reached):
  - The tank reads cleaner and brighter than the photo under the studio HDRI. The glossier finish of round 3 raised its highlights. The next step would be grime on the tank's lower half: darker, rougher patina, still metal.
  - The globe's frost is sparser and the glass clearer than the photo's heavily frosted smoked globe.
  - Thin wires are slightly less saturated than the photo (band 1 sat 0.40 vs 0.52).

## Files (compact)
- hurricane-lantern_original.glb (4.52 MB, pre-optimize export)
- hurricane-lantern_final.glb (435 KB)
- hurricane-lantern.blend (full history, procedural materials, textures packed)
- hurricane-lantern_log.md
- scripts/ (build, materials, bake, cleanup/export: reproducible) and review/ (measures, renders, crops, HDRI) kept as working files. Intermediate review GLBs deleted.

## Licenses
- Reference photo Lantern_01 and TRELLIS.2 template: user-provided, used as reference / for measurement only, not shipped.
- studio_small_09 HDRI: Poly Haven, CC0. Review lighting only, not shipped.
- All geometry and textures: original, scripted for this asset.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-01 15:52
