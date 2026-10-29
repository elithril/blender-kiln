# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 14, up to date)

## Reference Image
- Path: /private/tmp/kiln-bench/v220-mcp222-ahujasid/ref-lantern-template/refs/Lantern_01.png (394x1023, alpha)
- Template: refs/trellis/lantern_trellis.glb (TRELLIS.2). Used only to measure proportions with
  tools/template_profile.py (review/profile.json). Its mesh and texture are not in the shipped asset.
- Assumptions (auto mode, nothing asked):
  - Real height 38 cm with the bail raised (usual size of a Feuerhand-type hurricane lantern)
  - Camera elevation ~10° (read on the cap brim's ellipse), azimuth 0 (front view)
  - Single view: the back and underside are inferred from the front and the template (guard wires
    behind the globe mirror the front X; fount underside flat)
- Inventory (from 2-3x crops, review/crop_*.png). How each part joins is in brackets:
  - bail: 3 mm wire, centre line traced from the pixels, small peak at the top → SM_Lantern_Bail [ends turn in and enter the side tubes at 21 cm]
  - top handle: pentagon wire loop, 2.6 mm → SM_Lantern_Handle [bottom bar runs through a clip on the cap]
  - cap: stepped disc lid, brim r 3.95 cm → SM_Lantern_Cap [rests on the vent ring]
  - vent ring: dark slots all around, under the cap → SM_Lantern_Hood (8 boolean pockets)
  - air chamber with bead ring, bell hood flaring to r 4.5 cm, globe collar lip → SM_Lantern_Hood
  - side air tubes, Ø 1.75 cm, top elbow into the chamber, bottom elbow into the fount → SM_Lantern_Tubes [both ends inserted]
  - globe: smoked, frosted glass, egg-shaped, max r 4.4 cm → SM_Lantern_Globe [ends hidden in the collar lip and the gallery]
  - globe guard: crossed wires (X front, X back) → SM_Lantern_Guard [ends inserted in the gallery rim and the collar lip]
  - gallery dish, burner neck and wick burner → SM_Lantern_Burner
  - globe-lift arms (both sides), crank on the right, wire clip on the left tube → SM_Lantern_Lever [ends inserted in the gallery and the tubes]
  - fount: rolled bottom rim, rib, stepped dome top → SM_Lantern_Fount
  - filler cap, front-right on the fount shoulder → SM_Lantern_FillerCap [base sunk into the dome]
- Palette (region_palette, sRGB 10/50/90 %): fount (0.09,0.07,0.06)/(0.15,0.13,0.11)/(0.27,0.22,0.18);
  chamber (0.07,0.05,0.04)/(0.15,0.11,0.08)/(0.31,0.24,0.17); glass (0.06,0.055,0.055)/(0.086,0.086,0.082)/(0.22,0.20,0.19)
- Visual comparison: close match for shape and parts; partial match for the metal surface (see Review)

## Prompts (copy-paste ready)
- Concept art: none (user image)
- Hunyuan3D params: N/A (scripted)

## Source
- Method: scripted modelling (Blender Python through MCP): lathed profiles + circle sweeps along
  smooth Bezier paths. Scripts: scripts/build.py, materials.py, bake.py, export.py, run_all.py
- Marketplace / AI generation: none
- Factory scene: the default Cube was removed before building (untouched factory scene, no .blend loaded)

## Pipeline
- Import (scripted, in place): 11 meshes under root empty SM_Lantern, bbox 0.146 x 0.124 x 0.380 m, base at z = 0
- Cleanup: transforms applied, 0 doubles to merge, 0 loose, 0 fused edges, normals recalculated
- Polycount: 10,692 tris — 2.1x the balanced prop range top (5K). Where they go: glass globe 64
  segments (1,536), side tubes 16 sides (1,464), lathed metal parts at 32 segments (~4,800),
  wires (bail, guard, handle, lever, ~2,900). Already reduced from 14,084 during build (lathes 40→32,
  coarser sweeps). Further reduction is PROPOSED, not applied (rule 6): e.g. globe 64→48 and tube
  16→12 sides would bring it near 9K at some cost to roundness up close.
- Texturing: procedural sources baked to UVs (Cycles, Emission bakes into float images, converted to sRGB bytes)
  - M_Lantern_Metal (one aged bronze for every metal part): base colour from the photo's palette,
    lifted above the metal floor (tarnish stays metallic); bare bronze on convex rims (per-part
    90-99th percentile convexity, broken by noise); non-metal crusts only in cavities (AO + concavity);
    roughness with its own noise; vertical streaks; normal map from fine pits + broad dents.
    Textures: BaseColor, ORM (G roughness, B metallic), Normal — 2048 baked, 1024 shipped
  - M_Lantern_Glass: smoked grey-blue glass, frost specks gathered by a blotch field in colour and
    alpha, roughness 0.28, coat 0.35, alpha BLEND. Texture 1024
  - Procedural sources kept in the .blend as M_Lantern_Metal_Src / M_Lantern_Glass_Src (fake user)
- Review (tools/fidelity_check.py, front, elevation 10°, studio_small_09 HDRI; two correction rounds):
  - r0: IoU 0.849. Gaps: warmth/saturation too high (bands 2, 3, 5); overlay showed tube elbows ~0.7 cm high
  - r1 fix: palette desaturated and darkened; both tube elbows lowered. Result IoU 0.855, warmth/sat gaps closed
  - r2 fix: glass looked like a black mirror vs the photo's grey frosted glass → lighter tint, roughness
    0.1→0.28, coat 1→0.35, denser frost; filler cap moved out to the fount's front rim
  - final (measured on hurricane-lantern_final.glb): IoU 0.855; per band IoU 0.26 (bail wire, thin
    parts), 0.79, 0.91, 0.89, 0.87; widths within 8 % except band 5 full width +7.6 % (perspective at the base)
  - Still open (stopped at the two-round limit): surface detail is about half the photo's (scratches,
    blotchy dark patina missing), and the model reads lighter than the photo under the studio light
    (luminance is light-dependent: an alarm, not a target); the filler cap reads smaller than in the photo
  - Joints: all 16 (r0) / 12 (final) joint renders inspected — every long part enters the part it joins
- Optimize: gltf-transform resize 1024 → webp → draco (individual steps, rule 20):
  12.19 MB → 0.49 MB (−96 %). Draco needs a decoder on the client
- Export: GLB, export_apply=False, Y-up; materials audited (Principled + image textures only)

## Files
- hurricane-lantern_original.glb — 12.19 MB, PNG textures (2048 metal, 1024 glass)
- hurricane-lantern_final.glb — 0.49 MB, WebP 1024, Draco
- hurricane-lantern.blend — full scene, procedural sources, packed bakes
- review/ — crops, template profile, fidelity renders per round, joint renders, HDRI
- scripts/ — the full reproducible build

## Licenses
- Reference photo and TRELLIS template: supplied by the user (template used for measurement only)
- studio_small_09 HDRI (review renders only, not shipped): CC0 — Source: Poly Haven (polyhaven.com), via the public API
- No other third-party assets; all geometry and textures generated in this session

## Checkpoint
- Last completed step: EXPORT (final GLB measured)
- Timestamp: 2026-10-21 13:45
