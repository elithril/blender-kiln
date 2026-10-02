# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (props 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modeling in Blender (no marketplace, no AI generation) — imposed by the brief
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (up to date), telemetry off
- Scene at start: untouched factory scene (Cube, Light, Camera, no .blend) → Cube removed (rule 6 exception)

## Reference Image
- Path: /private/tmp/kiln-bench/ref-kiln-v14/ref-lantern-template/refs/Lantern_01.png (394x1023, RGBA, transparent bg)
- Template: refs/trellis/lantern_trellis.glb (TRELLIS.2 of the same photo) — used ONLY to measure proportions
  (`tools/template_profile.py`, review/profile.json); its mesh and texture are not shipped.

### Assumptions (one photo cannot say)
- Real size: total height 0.36 m with the bail raised (body ≈ 0.26 m, Feuerhand-276-class hurricane lantern). Assumed, not given.
- Camera elevation ≈ 10° (tank bottom-rim ellipse minor/major ≈ 0.19), azimuth 0 (front-on, both tubes symmetric).
- Back and underside: not shown by the photo. Back = mirror of the front (guard wires crossed on both sides); the fuel cap and wick knob exist only where the photo shows them (front-right / right).

### Inventory (from 3x crops, before modeling) — part, and how it meets
- tank: turned font, widest at the foot (r≈5.9 cm), tapering up, two embossed ribs, rolled foot, domed top     → SM_HurricaneLantern_Tank
- fuel cap: short knurl-less cylinder r≈1.3 cm on the dome, front-right, SEATED into the dome                      → _FuelCap, on Tank
- burner neck: collar r≈2.0 cm, z 5.5-8 cm, bead at the foot, RISES OUT OF the tank dome                           → _BurnerNeck, on Tank
- wick knob: small disc r≈0.6 cm on a spindle, right side (+X), spindle INSERTED into the neck                    → _WickKnob, on BurnerNeck
- burner + wick: dome inside the globe, faintly visible through the smoked glass                                  → _Burner, on BurnerNeck
- globe seat: shallow dish r≈3.3-3.6 cm under the glass, SITS ON the neck                                         → _GlobeSeat
- globe: smoked dark glass, egg-shaped, widest r≈4.2 cm at z≈11-12 cm, frosted specks — its own material           → _Globe, seated in GlobeSeat, top INSIDE GlobeCollar
- guard wires: two wires crossing diagonally over the globe (front and back), ends INTO the collar rim and the seat → _GuardWires
- globe frame rods: horizontal wire rods from each tube to the seat ring at z≈8.3 cm; right one Z-bent             → _FrameRods, ends INTO tubes and seat
- left clip: narrow U wire loop on the inner side of the left tube, z≈9.6-12.4 cm, legs INTO the tube             → _TubeClip
- globe collar: bronze cup band over the top of the glass, z≈15.3-17.7 cm, r≈3.4                                 → _GlobeCollar, under Bell
- bell / air chamber: flare from r≈4.2 (z≈18) to a cylinder r≈3.2 (z 20.7-23.4) with a bead at z≈20.8          → _Bell
- vent ring: r≈2.2 cm, z 23.1-23.9 cm, dark rectangular vent slots all round                                      → _VentRing, between Bell and Lid
- lid (hat): wide disc r≈3.6 cm with rolled rim, z 23.9-25.6, raised boss r≈2.45 to z≈26                        → _Lid
- top loop: pentagon-shaped wire loop, its foot HINGED in a small tube lying on the lid boss                      → _TopLoop + _Hinge, on Lid
- side air tubes: two round tubes r≈0.75 cm at x≈±6, bottom elbow ENTERS the tank top, top elbow ENTERS the chamber at z≈21 → _Tube_L / _Tube_R
- bail: wire r≈1.75 mm (template), arched to z=36 cm, ends bent inward and INSERTED into the tubes at z≈19.5      → _Bail
- materials: ONE aged bronze/brass metal for every metal part (patina, tarnish, grime = layers within it), ONE smoked glass

### Measures
- Template (`template_profile.py --height 0.36`): tank r 5.87 (z 0.4) → 5.35 (z 3.4); neck r 1.9-2.2 (z 5.6-7.1);
  globe r 3.87 (9.4) 4.10 (10.1) 4.19 (10.9) 4.16 (11.6) 4.14 (12.4) 4.02 (13.1) 3.83 (13.9) 3.55 (14.6) 3.43 (15.4);
  bell r 4.19 at z 18.4; tubes outer x 7.57 (z 7) → 6.66 (z 20); bail centre r 6.55 (20.6) 6.3 (22.1) 6.05 (23.6)
  5.8 (25.1) 5.6 (26.6) 5.3 (28.1) 5.05 (29.6) 4.8 (31.1) 4.4 (32.6) 3.95 (33.4) 3.2 (34.1) 1.7 (34.9) 0 (35.8); bail Ø 3.5 mm.
- Template weak above z 22 (lid region): lid/vent/boss radii from the photo pixels (0.352 mm/px at 0.36 m).
- Palette (photo, linear): metal mid ≈ (0.027, 0.016, 0.012), light q0.98 ≈ (0.20-0.29, 0.13-0.20, 0.08-0.13) — warm
  bronze hue; the photo's darkness is the environment, so metal base colour keeps that hue at physical reflectance.
  Glass: mid ≈ 0.012 neutral, frost specks ≈ 0.13-0.15.

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Hunyuan3D params: N/A (scripted modeling, imposed by the brief)

## Source
- Method: scripted (Blender Python: `scripts/build.py` lathe + swept-tube library, `scripts/materials.py` procedural → bake)
- Marketplace / AI: none. TRELLIS template measured only, never imported into the asset file.

## Pipeline
- Build: 24 parts under root empty `SM_HurricaneLantern` (collection `HurricaneLantern`), origin at the centre of the base.
- Attachment: BVH + inside test — every end inserted (tubes into tank and chamber, bail ends into tubes, rods/clip into tubes and seat,
  spindle into neck, cap into dome, guard wires into collar rim and seat). Joint renders looked at (review/r1/joints/, review/final/joints/):
  all enter; the hinge lies on the lid boss, as in the photo.
- Cleanup: merge by distance 0.1 mm (3 verts, TubeClip), degenerate dissolve, loose removed (0), normals recalculated,
  fused edges 0 everywhere; open edges only where intended (glass shell 128, hidden openings in Bell 32 / BurnerNeck 32).
  Transforms applied (FuelCap, WickKnob). Orphans purged.
- Texturing: 1 physical metal (aged bronze/brass) + 1 smoked glass. Procedural shaders kept in the .blend
  (`M_Metal_AgedBrass_Procedural`, `M_Glass_Smoked_Procedural`, fake users) and baked (Cycles, 16 spp) per texture set:
  Base / Top / Tubes 1024², Wires 512², Glass 1024² → BaseColor (emission bake, float → sRGB byte), ORM (G rough, B metal), Normal (tangent).
  Fields: 3-scale colour noise between palette dark/mid; wear on convex edges (per-part 88th–99th percentile curvature) in broad soft
  patches; grime from cavity + AO + faint vertical streaks along cylindrical UVs; non-metal soot crust only in the deepest grime and the
  drip under the fuel cap; independent roughness noise; relief = dents + pits + fine u-scratches baked to normal.
  Glass: dark neutral tint, frost specks gathered by a blotch field (colour + alpha), roughness 0.08, clear coat 1, alpha BLEND.
- Material audit (rule 19): shipped materials image-only Principled, no procedural nodes, no empty slots, all images packed.
- Export: `hurricane-lantern_original.glb` 9.97 MB (UVWorld helper UV + bake attributes stripped at export), validator 0 errors.
- Optimize (auto, rule 20 — individual steps): resize ≤1024 → WebP → Draco → `hurricane-lantern_final.glb` **459 KB (−95%)**,
  validator 0 errors. Needs EXT_texture_webp + KHR_draco_mesh_compression decoders on the client.
- Final: 24 meshes, **12,018 tris**, 5 materials (4 texture sets of the one metal + glass), bbox 0.139 × 0.116 × 0.360 m.

## Triangle budget (rule 4 — reported, not cut)
12,018 tris = 2.4× the balanced prop tier's top (5K). Where they go: glass 1,536 (64 segments, required for a clean transparent shell),
bail 1,228, bell 1,120, tank 1,088, tubes 1,080, collar 832, lid 768, guard wires 944, top loop 464 — round parts and wires.
**Reduction proposal (not applied, needs your choice):** bail/top loop/guard wires 8→6 sides and coarser bail sampling (≈ −900),
small turned parts 32→24 segments (neck, seat, collar, vent, cap ≈ −700), tube bends 4→3 steps (≈ −200) → ≈ 10.2K. Or a gltfpack LOD1.
No decimation was run (thin wires break under it).

## Review (fidelity_check.py, front, elevation 10°, azimuth 0, studio_small_09)
- R1: IoU 0.712. Widths +9…+15 % in every band (tubes a whole tube-width outside the photo; template is ~10 % wider than the photo
  at tubes/tank, matches at the globe). Metal sat 0.50 vs 0.33, warm 0.13 vs 0.06 (copper-orange).
  → tubes + bail moved halfway toward the photo; patina palette made more neutral (one material change); leaner tessellation.
- R2: IoU 0.779. Body sat/warm gap closed. Widths +8/+9 % (bands 2-3), tank foot cyan outside.
  → tubes/bail another half-step in, tank radii −2.5 %; wires given more bare-brass wear (band 1 sat 0.35 vs 0.52).
- R3 = final, measured on the shipped `_final.glb`: **IoU 0.813**, band widths within +6 %; band 1 sat 0.41 vs 0.52.
  Remaining, logged not chased (2 correction rounds max): band 2 core +17 % (tube top elbows merge into the chamber core);
  tank surface grain 23 % of the photo's (model reads cleaner — next layer to add: dark grime blotches/drips on the tank);
  glass highlights higher than the photo (light-dependent; glass reads more mirror-like and less milky than the photo).

### Inventory tick (crop vs render, final)
- tank ✓ (ribs, rolled foot; cleaner than photo) · fuel cap ✓ (reads slightly smaller/lower than the photo) · burner neck ✓ · wick knob ✓
- globe seat ✓ · globe ✓ (smoked + frost; less milky than the photo) · guard wires ✓ crossed front and back · frame rods ✓ (right one Z-bent)
- left tube clip ✓ · globe collar ✓ · bell + bead ✓ · vent ring with slots ✓ · lid + boss ✓ · top pentagon loop + hinge ✓
- side tubes ✓ · bail with apex notch ✓ · burner inside globe ✓ (barely visible, as in the photo)
- Visual comparison: **close match** (parts, proportions, palette); surface ageing lighter than the photo.

## Licenses
- Reference photo + TRELLIS.2 template: provided by the user (measurement only, nothing shipped from them).
- studio_small_09 HDRI (review lighting only, not shipped): Poly Haven, CC0.
- All geometry and textures: generated in this session by script — no third-party assets.

## Files (compact)
- hurricane-lantern_original.glb, hurricane-lantern_final.glb, hurricane-lantern.blend (procedural materials + bake setup), this log.
- Working files kept: scripts/ (build, materials, montage), review/ (crops, profile.json, fidelity renders r1-r3 + final, HDRI).

## Checkpoint
- Last completed step: EXPORT (final GLB measured)
- Timestamp: 2026-10-01 16:30
