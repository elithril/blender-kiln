# Bayonet Box — Production Log

## Config
- Type: prop
- Target: STL (print), two parts: base and lid; plain GLB preview in web/
- Print: FDM, 0.4 mm nozzle, one colour; ~60 mm across
- Tier: balanced (screen budget only; a print is not decimated to it)
- Style: stylized
- Mode: auto
- Storage: compact
- 3D backend: none — scripted (Blender 5.2.2 headless, `--factory-startup` + `read_factory_settings(use_empty=True)`)
- Environment: macOS 26.6.1, Apple M4 Pro; Blender 5.2.2 LTS; Blender Lab MCP connected (factory scene: Cube, Camera, Light, no file); PrusaSlicer 2.9.6
- Mechanical-part notice (print.md § Scope): a lid that must lock belongs in a CAD tool. Standing answer given in the brief: carry on, lid accepted at decorative precision, user will print a test piece first. Logged as the answer.

## Reference Image
- Path: none
- Visual comparison: N/A

## Brief (reformulated, auto mode — assumptions)
- Round box, 60 mm outer diameter (the lid's grip ribs add 0.8 mm a side → 61.6 mm across the ribs).
- Base: 39 mm tall, Ø60 body with a 45° bottom chamfer, two V-groove bands, a 54 mm neck (wall 1.8 mm) carrying 3 lugs at 120°, cavity Ø50.4 × 37 mm deep, floor 2 mm.
- Lid: 12 mm tall, 3 mm top plate, skirt slides over the neck (0.3 mm radial clearance), 3 L-slots: vertical entry from the rim, then a 30° channel turning clockwise (seen from above) to lock, with a small detent bump before the end stop. 21 vertical grip ribs; a missing rib marks each entry, an engraved triangle under each lug on the base marks where to push.
- Height asked "about 60 mm across" = the diameter; assembled height 42 mm (assumption).
- Clearances 0.3 mm a face — not measured: test print `test/test_bayonet_*.stl` first.
- Paint regions: none (one colour, no painting asked).
- Print orientation: base upright on its bottom; lid upside down, on its flat top.

## Prompts (copy-paste ready)
- N/A (scripted, no AI)

## Source
- Method: scripted (lathe profiles + exact unions, Blender Python)

## Pipeline
- CONFIG/BRIEF: done, assumptions above.
- SOURCE/IMPORT (scripted print: one step): `scripts/build.py`, headless Blender 5.2.2. Base = one lathe profile (120 steps, 3°; sagitta 0.01 mm) + 3 lugs (45° flanks, sunk 0.3 mm into the neck) by EXACT union, 3 engraved triangles (0.75–0.8 mm deep) by EXACT difference. Lid = lathe + 3 channels and 3 entry slots (EXACT differences), 3 detent bumps and 21 ribs (EXACT unions, sunk 0.3 mm). Features placed half a lathe step off the meridians. Non-manifold count 0 after every boolean; triangulated before export (0 after). Objects: SM_BayonetBox_Base 60.0 × 60.0 × 39.0 mm, zmin 0; SM_BayonetBox_Lid 61.6 × 60.8 × 11.7 mm (vertices, world). Height read as: "60 mm across" = diameter; assembled height 42 mm.
- Live Blender (Lab MCP): factory scene untouched (Cube, Camera, Light, no file) → Cube removed, logged; the two parts appended there for the look only — built and saved headless.
- Round 1: lid PASS with 1.19 % of faces < 0.8 mm — the ribs' top corners lay exactly on the 0.6 mm top chamfer (0.01 mm slivers). Changed one thing: rib top end 41.7 → 41.5 mm. Round 2: 0.08 % of faces (0.0 % of area), 3 faces = one per detent bump where its ramp meets the groove bottom (ray-edge reading, not a wall). Kept.
- CLEANUP (print variant): no merge, no degenerate dissolve (model built closed); step 5 = print_check on the STLs (below); transforms applied (lid print copy rotated 180° about X and set on Z=0); no decimation (8k tris total).
- TEXTURING: skipped — scripted with material assigned; STL carries none. Preview material M_PLA_Terracotta (one filament, no paint regions).
- Look: review/assembled_colour_{q1,q3,front,under}.png, review/base_matcap_{q1,q3,top,under}.png, review/lid_matcap_{q1,q3,top,under}.png, review/lid_detent_matcap_close{1,2}.png (inside the skirt, slot → channel); live Blender viewport, framed on the base.
- Print orientation: base upright on its chamfered bottom (cavity open up, lugs with 45° flanks grow from the neck); lid upside down on its flat top (skirt up, channels with 45° flanks, slots open at the rim). Zero supports for both (slicer).
- Print check, one line per printed part (PrusaSlicer 2.9.6, FDM):
  - base: PASS, 60.0 × 60.0 × 39.0 mm, 1 part, supports no (sliced clean), overhang 0.0 %, smallest scale 44 %, reference volume 0.9998, warnings none
  - lid: PASS, 61.6 × 60.8 × 11.7 mm, 1 part, supports no, overhang 0.0 %, smallest scale 54 %, reference volume 0.978 (the slots), warnings 0.08 % faces < 0.8 mm (detent ramp edges)
  - test_bayonet_neck: PASS, 60.0 × 60.0 × 10.2 mm, 1 part, supports no, smallest scale 67 %, no reference (one intersect of the PASSing base)
  - test_bayonet_lid: PASS, 61.6 × 60.8 × 11.7 mm, 1 part, supports no, smallest scale 54 %, no reference (lid with Ø48 centre opened)
- Clearances: 0.3 mm a face on the neck, the lugs and the slots; detent 0.15 mm interference. Not measured — test pieces first.
- OPTIMIZE: skipped (print).
- EXPORT: print/bayonet-box_print_base.stl (4,208 tris, 206 kB), print/bayonet-box_print_lid.stl (3,650 tris, 178 kB), test/test_bayonet_neck.stl, test/test_bayonet_lid.stl, STL global_scale 1000 (mm); 3MF not written: the 3MF extension is not installed (export_mesh.threemf → KeyError). Preview web/bayonet-box_final.glb (plain, no Draco/WebP, assembled + locked, 378 kB). print/PRINT.md = hand-over. bayonet-box.blend saved (save_version 0, no .blend1). References: bayonet-box_base_parts.blend, bayonet-box_lid_parts.blend.
- Intermediates kept (auto, nobody to answer): review/*.png, check/*.json|txt, scripts/build.py.

## Licenses
- All geometry authored in this session: no third-party resource.

## Checkpoint
- Last completed step: [7] EXPORT + print check (PASS ×4)
- Timestamp: 2026-10-22
