# Bayonet Box — Production Log

## Config
- Type: prop
- Target: STL (print) — two parts, box and lid; preview GLB for viewing
- Tier: balanced (screen budget not applied to a print)
- Style: stylized
- Mode: auto (unattended)
- Storage: compact
- Print: FDM, 0.4 mm nozzle, one colour, ~60 mm across
- Backend: none — scripted modelling
- Live view: off (unattended run, no one to watch Kiln Studio)

## Brief
Small round box, ~60 mm diameter, bayonet lid (push down and twist to lock).
- Mechanical-part notice (print.md § Scope): a lid that must close belongs in a CAD tool.
  Standing answer from the user, given in advance: carry on, lid accepted at decorative
  precision, any test piece will be printed first. → Built in Blender, decorative precision.
- Design assumptions (auto mode):
  - Box: Ø60 body, 32 mm to the shoulder, neck Ø53.4 to 43.5 mm, bore Ø49.4, floor 2 mm,
    neck wall 2.0 mm. Decorative V-band at 6–7.6 mm, 0.5 mm elephant-foot chamfer.
  - 3 lugs on the neck at 120°: 6 mm wide, 1.2 mm proud, 45° underside (grows from the neck).
  - Lid: skirt Ø60 outer / Ø54 inner, 12 mm, top 2.5 mm; lid sits on the box shoulder.
    3 L-grooves inside the skirt: entry slot open at the mouth, 30° channel turning
    clockwise (seen from above) to close; channel floor at 45° matching the lug, ramping
    up 0.45 mm toward the closed end so the twist pulls the lid tight (snug wedge lock).
  - 24 vertical grip ribs on the lid skirt (0.8 mm proud, 45° ends) — stylized grip.
  - Clearance 0.3 mm per face everywhere (not measured on this printer).
  - Height asked: "60 mm across" is the diameter; assembled height 46.5 mm.
- Paint plan: none — one colour, no regions asked.

## Reference Image
- Path: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- None (no AI)

## Source
- Method: scripted (Blender Python, lathe + sweeps + EXACT booleans)

## Pipeline
- CONFIG/BRIEF: done. Blender 5.2.2 LTS live via MCP (addon 1.8, up to date), factory scene.

- SOURCE/IMPORT (scripted, build_bayonet_box.py, headless Blender 5.2.2, 1.6 s): lathe 128 segments
  (sagitta 0.009 mm), flat n-gon caps; lugs and ribs swept, EXACT unions; grooves EXACT
  differences (slot + ramped channel ×3). Non-manifold 0 after every boolean. Cutter edges
  ≥ 0.23° off the lathe meridians. SM_BayonetBox 1,609 faces, 60 × 60 × 43.5 mm, on ground;
  SM_BayonetLid 1,233 faces, 61.6 × 61.6 × 14.5 mm (ribs 0.8 proud), seated at 32 mm, locked.
  References saved: bayonet-box_box_parts.blend (lathe + lugs), bayonet-box_lid_parts.blend
  (lathe + ribs, before grooves). Factory Cube: headless run started from an empty factory
  scene; the live Blender (untouched factory scene) then opened bayonet-box.blend to look.
  Look: assembly 4 views, box alone (lugs visible on neck), lid from below (3 L-grooves visible).
- CLEANUP (print variant, validation-checklist § print): merge and degenerate-dissolve skipped
  (built closed); transforms identity, origin bottom centre; names SM_BayonetBox / SM_BayonetLid,
  meshes *_Mesh; materials M_Box_Teal, M_Lid_Coral (preview only). Triangulated per part before
  export (BEAUTY). Manifold verdict = print_check on the STL (below). No decimation (print).
- OPTIMIZE: skipped (print). Preview web/bayonet-box_final.glb, plain glTF, assembled & locked.
- Export: STL mm (global_scale 1000). 3MF extension not installed → STL only.
  Print orientation: box upright on its base (lugs' 45° undersides grow from the neck);
  lid flipped onto its flat top (bed-edge 0.8 mm chamfer; groove floors at 45°, no bridges).
- Print check, one line per printed part (PrusaSlicer 2.9.x, FDM default profile):
  - box: PASS, 60.0 × 60.0 × 43.5 mm, 1 part, 3,548 tris, supports no (sliced clean), overhang 0 %,
    smallest scale 40 %, vs reference volume 1.00, warnings none
  - lid: PASS, 61.6 × 61.6 × 14.5 mm, 1 part, 3,420 tris, supports no, overhang 0 %,
    smallest scale 46 %, vs reference 0.98 (grooves cut), warning 0.06 % faces under 0.8 mm
    (0.0 % area) = 0.05 mm ledge where slot ceiling meets channel ceiling, seen on close render,
    under one layer — kept
  - test/test_box_neck_ring: PASS, 60 × 60 × 13.5 mm, 40 %
  - test/test_lid_skirt_ring: PASS, 61.6 × 61.6 × 7.0 mm, 67 %
- Mechanism path check (checks/path_check.py, EXACT intersect box ∩ moved lid): push-in at the
  entry 6 → 0.2 mm above seat: 0.000 mm³; twist seated 30° → 15°: 0.000; 7.5°: 0.006; 3°: 0.153;
  locked: 0.258 mm³ total for 3 lugs = the ramp's designed wedge (~0.02–0.03 mm interference).
- Review renders (tools/review_renders.py): review/box_matcap_*, lid_matcap_* (+2 close-ups at the
  thin spots), assembled_colour_q1/q3. Live look in Blender: assembly, box, lid from below.
- Clearance 0.3 mm/face is NOT measured on the user's printer — test rings written in print/test/.
  fit_coupon.py not used: it makes pegs, not a bayonet; the rings are the joint's real test.
- Kiln Studio: not started (unattended run).
- Intermediates kept (auto, nobody to ask): build/export scripts, checks/, review/, *_parts.blend.

## Licenses
- All geometry original, scripted in this session — no third-party resources.

## Checkpoint
- Last completed step: [7] EXPORT + print_check (PASS both parts) — pipeline complete
- Timestamp: 2026-10-23
