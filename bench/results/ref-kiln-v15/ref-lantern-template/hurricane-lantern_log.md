# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (1.5–5K tris soft range)
- Style: realistic
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.8 (up to date), macOS, Cycles GPU (Metal)

## Reference Image
- Path: refs/Lantern_01.png (394×1023, transparent background)
- Template: refs/trellis/lantern_trellis.glb (TRELLIS.2). Used ONLY for measurements (tools/template_profile.py → review/profile.json); its mesh and texture are not shipped
- Assumptions (single photo): real height 35 cm with the bail raised (≈28 cm to the top of the hanging loop, a Feuerhand-276-class lantern); camera elevation 15° (read on the chimney skirt's lip, the rim nearest mid-height), azimuth 0°. Back and underside are not shown in the photo: they are lathed/mirrored continuations, no invented details
- Inventory (parts and how they meet), ticked at the final review against crops:
  - [x] Font (base): drum with rolled foot and two ribs, domed shoulder → SM_HurricaneLantern_Font
  - [x] Filler cap: two-ring knurled cap, front-right of the dome, seated in it → FillerCap
  - [x] Fuel stain running down from the filler cap → baked in the Body texture
  - [x] Burner collar with flange, globe gallery dish with rolled rim, burner cone and wick plate inside → Burner
  - [x] Smoked glass globe, egg-shaped, sits in the dish and under the top collar → Globe (own material)
  - [x] Globe guard: helical wires crossing in an X at front and back, entering the dish rim and the top collar → GlobeGuard
  - [x] Chimney: top collar, flared bell skirt with lip, ring bead, upper bell, vented neck (8 dark slots), cap disc with raised step → Chimney
  - [x] Side tubes: bend over and ENTER the upper bell; bottom bends ENTER the font's shoulder; raised seam along each tube → Tube_L / Tube_R
  - [x] Bail: traced centre line from the photo, peaked top, ends HOOKED into the tubes' outer sides → Bail
  - [x] Hanging loop: wire loop with legs folded INTO a clip on the cap → TopLoop. Partial: reads as an 8-sided loop, the photo's is closer to 5–6 sides
  - [x] Right globe-lift lever: crank from the dish into the tube, pin ring outside the tube → Lever_R
  - [x] Wick rod from the burner collar with an eye ring (front-right, low) → WickRod
  - [x] Left lift clip (hairpin on the tube), cross rod tube→dish, strap tube→burner collar → Lever_L
- Visual comparison: close match on proportions and parts; partial match on surface. The photo's metal is darker and more scratched, and its glass is more frosted and opaque

## Prompts (copy-paste ready)
- None (scripted modelling — no concept art, no AI generation)

## Source
- Method: scripted modelling (Blender Python): scripts/build_geometry.py, cleanup.py, materials.py, bake.py
- Lathes: Font 32 seg, Burner 28, Chimney 32, Globe 64, FillerCap 24. Sweeps (own parallel-transport tube builder, filleted arcs, Catmull-Rom for the traced bail): tubes 16 sides, wires 6–8 sides

## Pipeline
- Scene: factory startup scene (Cube, Camera, Light, no .blend) — the default Cube was removed before building
- Import: scripted; 13 objects SM_HurricaneLantern_*; overall 13.2 × 11.5 × 34.9 cm, origin at base centre, 1 unit = 1 m
- Cleanup: merge by distance 0.1 mm (Bail 3, WickRod 1 vertex), recalc normals, no loose geometry, dissolve degenerate, fused edges 0 (16 found on GlobeGuard in the first pass from coincident wire ends, fixed by staggering the ends by 7°). Open edges by design: Globe (open both ends), Burner (bottom ring hidden inside the font), the pin/eye rings' seams
- Poly count: 12,314 tris, about 2.5× the balanced tier's top of 5,000. Biggest shares: Chimney ≈2.5K, Font/Burner/Globe ≈1.5K each, tubes ≈1.2K, guard wires ≈1.1K. Not reduced — see the proposal in the session report
- Texturing: one physical metal (aged bronze/brass) in two texture sets (Body, Frame), plus smoked glass
  - Base: Poly Haven `metal_plate_02` scan (colour luminance, roughness, normal), box-projected, mapped onto a palette sampled from the photo (patina dark/mid, brass), lifted to physical metal reflectance
  - Wear: convexity per vertex, thresholded at each part's own 90th–99.5th percentile, broken by noise → brass on rims, beads and tube seams
  - Tarnish (stays metal): AO cavities + undersides. Crust (non-metal): faint vertical streaks only. Fuel stain: dark glossy film. Vents: face-corner mask
  - Glass: dark blue-grey, alpha 0.72→0.97 on frost, frost specks gathered by a blotch field, clear coat
  - Baked to UVs (cylindrical UVs at real scale, packed per set): BaseColor (Emission → float → sRGB byte), ORM (G rough, B metal), tangent-space Normal; 1024² (glass 512²)
- Review (tools/fidelity_check.py, front, elevation 15°, studio_small_09):
  - r0 (untextured .blend): IoU 0.76; tubes ~half a tube-width too far out, bell skirt too wide, bail too wide, loop too high → tubes moved in 0.45–0.5 cm, skirt −0.2 cm, bail x scale 1.055 → 1.0, loop −0.3 cm
  - r1 (_original.glb): IoU 0.85; Frame metal mostly non-metal (cavity grime was crust), band-2 core +11%, metal lighter and more matte than the photo → cavities became tarnish, streaks the only crust, roughness 0.36–0.62 → 0.30–0.52, palette slightly warmer, cap/bell radii halfway toward the template (−0.08 cm). Note: two material changes in this round, not one
  - r2 (final, _final.glb): IoU 0.847; band-2 core +9% (left, two rounds used). The "Frame mostly non-metal 0.36" flag is an atlas artefact: per-UV sampling gives metallic ≈1.0 on every frame part, and the average is pulled down by ~63% empty atlas space. Luminance +0.09–0.11 and highlights: light-dependent alarms, not targets
  - 18 joint renders inspected (review/r*/joints/): every end enters its partner part with an unchanged section
- Material export audit: 3 shipped materials, Principled + image textures only, no procedural nodes; source shaders kept in the .blend (fake user)
- Optimize: gltf-transform resize 1024 → webp → draco (individual steps, rule 20). 3.94 MB → 229 KB (−94%). Draco needs a decoder on the client
- Export: hurricane-lantern_final.glb, 229 KB, 12,314 tris, 13 meshes, 3 materials, 8 textures (1024 WebP; glass 512)

## Files
- hurricane-lantern_original.glb (3.94 MB, pre-optimize), hurricane-lantern_final.glb (229 KB), hurricane-lantern.blend (scans, bakes and HDRI packed), this log
- scripts/ (build, cleanup, materials, bake), review/ (template profile, crops, palette, fidelity renders r0–r2, joints)
- The downloaded scan folder textures/ was removed after it was packed into the .blend

## Licenses
- metal_plate_02 texture set: CC0 — Source: Poly Haven (polyhaven.com), via the public API
- studio_small_09 HDRI (review lighting only, not shipped): CC0 — Poly Haven (polyhaven.com)
- TRELLIS.2 template: measurement only, nothing of it shipped
- Geometry, textures, scripts: original work of this session

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-01 20:35
