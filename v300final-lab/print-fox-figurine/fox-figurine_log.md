# Fox Figurine — Production Log

## Config
- Type: prop (stylised figure: sitting fox)
- Target: STL (print), one STL per colour; GLB preview (plain) for the colour plan
- Print: FDM, 0.4 mm nozzle, 80 mm tall assembled (ears included), 4 filaments: orange, white, black, dark brown
- Tier: balanced (print: no tier decimation)
- Style: stylized
- Mode: auto
- Storage: compact
- 3D backend: none — scripted (user's order: no marketplace, no AI)
- Live view / Kiln Studio: off (auto run, nobody watching; the Studio is offered at hand-over)
- Environment: Blender 5.2.2 LTS (/Applications/Blender.app), Blender Lab MCP connected (factory scene: Cube, Camera, Light, no file), PrusaSlicer.app present
- Output folder: /private/tmp/kiln-bench/v300final-lab/print-fox-figurine/work/generated-assets/fox-figurine

## Brief (confirmed, auto mode — assumptions)
Stylised sitting fox, 80 mm tall to the ear tips, seen from the front (-Y): pear-shaped sitting body,
big head with pointed snout and large upright ears, two straight front legs, haunches with hind paws,
a bushy tail curled round the right side onto the base.
Colour plan (one closed part per filament, flush inlays, together = the figure):
- black: eyes, nose, ear tips
- white: chest bib, muzzle/cheeks, tail tip
- dark brown: inner ears, front "socks" and hind paws
- orange: the rest
Assumptions: height counts the ears; the figure sits directly on the bed (no plinth); printed upright.

## Reference Image
- Path: none — Visual comparison: N/A

## Prompts
- none (scripted)

## Source
- Method: scripted, print.md § Figures — metaball families at 10× (0.8 m model), mesh ears, one voxel remesh, colour parts cut by booleans, scaled ×0.1 at export

## Pipeline
- Model built at 10x (0.73-0.76 m) — print.md § Figures rule 1 exception (metaball resolution); scaled to 80 mm at export.
- Shape rounds (headless, scripts/build_shape.py, review/vN/sheet_matcap.png; each 0 non-manifold edges after remesh 3 mm model = 0.3 mm print):
  - v1: 249k tris. Legs thin rods, long ringed neck, small head, spike ears, horizontal banding (metaball res 5 mm).
  - v2: res 3 mm + smoothing, bigger head, thicker legs. Legs vanished — buried in a fatter chest (fields add); ears splayed.
  - v3: belly slimmed, legs/paws forward, ears apart, 3 smoothing passes on the remeshed solid. Reads as a fox; mouse-like cheeks, drooping snout.
  - v4: lower flat cheeks, nose bridge, snout level. Kept; ear-base tabs and a short snout left.

  - v5: longer snout, ear bases tucked; ear tilt sign fixed (ears leaned inward, tips at x ±31 mm model → ±119 mm). Kept.
- Import (scripted, built at size ×10): solid 289,146 tris, 0 non-manifold; scaled ×0.10923 → 53.2 × 56.5 × 80.0 mm (vertices, world space), base at Z = 0.
- Colour parts (scripts/build_colours.py, EXACT booleans, material TRANSFER, priority black > white > brown > orange, uncut tools):
  black 6,616 tris / 5 islands (eyes, nose, 2 ear tips); white 44,412 / 2 (bib+muzzle, tail tip);
  brown 47,020 / 4 (inner ears, socks merged with hind paws per side); orange 254,596 / 1 — 8 crumbs dropped (0.0–0.29 mm³). 0 non-manifold edges each.
- [5] CLEANUP (print variant: no merge at print scale, no tier decimation; 810,872 tris total kept — voxel skin):
  - Solid vs reference: first FAIL — dims 4.4 % off. Cause: reference parts went below Z=0 (body −30 mm, tail −13 mm at 10x), solid flat-cut, tool scales the reference to height. Reference re-saved with the same flat cut → PASS: dims diff 0.29/0.19/0.0 %, volume ratio 1.009, overhang 8.96 %, SCALE 28 %.
  - Assembly first FAIL: STL edges shared by 4 faces (orange 10, white 6, brown 10) while Blender counted 0. Tried: tool separation (jaw tool shortened 1 mm off the nose — kept; hind-paw brown removed — undone; sock tool widened 0.052→0.065 — kept): moved the edges, did not clear them. Cause: float32 near-duplicate vertices from the EXACT boolean. Fix: weld at 0.001 mm per part after scaling (14–94 verts per part) + dissolve degenerate + triangulate → 0 in every STL.
  - Part tris after fix: orange 253,070 (1 part), white 43,080 (2), black 6,588 (5), brown 49,056 (4: sock+hind paw ×2, inner ears ×2).
- Print check, assembly (PrusaSlicer 2.9, FDM defaults): PASS, 53.2 × 56.5 × 80.0 mm, union 1 part, overlap 0 mm³, union 62,835 mm³; supports no — sliced clean without supports; overhangs 8.71 %; smallest scale 88 % (set by brown: inner-ear inlays); no thin area at 100 %.
- Orientation: upright, on its flat seat/paws/tail base (Z=0); the only face on the bed is the base.
- 3MF: extension not installed (export_mesh.threemf → KeyError) — STLs only.
- Texturing: preview materials only (print carries no colour): M_FoxOrange, M_FoxWhite, M_FoxBlack, M_FoxBrown, flat Principled.
- Review v5 colour (front, q1, q3, right): review/v5/sheet_colour.png.

- [6] OPTIMIZE: skipped (print). GLB preview exported plain: web/fox-figurine_final.glb, 26.3 MB, no Draco/WebP (extensionsUsed: none), 4 meshes.
- [7] EXPORT: print/fox-figurine_print_{orange,white,black,brown}.stl (mm, global_scale 1000), 12.7 / 2.2 / 0.33 / 2.5 MB; print/PRINT.md; .blend saved (fox-figurine.blend, save_version 0, no .blend1).
  Reference: fox-figurine_solid_parts.blend (parts before remesh, cut at Z=0, 10x). work/: fox_solid.blend, fox_solid_print.stl, check JSONs — intermediates kept (auto mode, nobody to ask), listed in hand-over.
- Final look: review/final/sheet_colour.png (q1, q3, top, under), STL matcap close-ups (face: smooth; leg/body crease: 0.3 mm voxel serration, hidden between legs — noted, not fixed). Live Blender (Lab MCP): fox-figurine.blend opened in place of the untouched factory scene, screenshot taken.
- Not done: 3MF (extension not installed); Kiln Studio not started (auto run).

## Licenses
- All geometry scripted in this session: no third-party resource.

## Checkpoint
- Last completed step: [7] EXPORT + print_check PASS (assembly) — done
- Timestamp: 2026-10-22
