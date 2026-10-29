# Fox Figurine — Production Log

## Config
- Type: prop (stylised animal figure)
- Target: STL (print), one STL per colour + 3MF if possible; plain GLB preview in web/
- Tier: balanced (screen budget, not applied to a print — validation-checklist print variant)
- Style: stylized
- Mode: auto
- Storage: compact
- Print: FDM, 0.4 mm nozzle, 80 mm tall assembled (ears included), 4 filaments: orange, white, black, dark brown — printed together as ONE multi-colour figure
- 3D backend: none — scripted (brief: no marketplace, no AI)
- Environment: Blender 5.2.2 LTS (MCP addon 1.8, protocol 14, up to date), PrusaSlicer.app present
- Live Blender: untouched factory scene (Cube, Camera, Light). Build runs headless from a script in scripts/; the live Blender is used only to look.

## Reference Image
- Path: none
- Brief enrichment: N/A
- Visual comparison: N/A

## Brief (confirmed, auto)
Stylised sitting fox, ~80 mm tall to the ear tips, upright on its haunches, front legs straight, big tail wrapped round the front of the feet on one side, pointed muzzle, tall ears.
Colour regions (assumption, auto mode):
- orange: body, head, tail, back of the ears, hind legs
- white: chest bib, muzzle and cheeks, tail tip, inner ears
- dark brown: front-leg "socks" and paws, ear tips
- black: eyes, nose
Method (print.md § Figures): metaball families per region, modelled at 10× (≈0.8 m), thin parts (ears) as closed meshes, one voxel remesh, flat cut at Z=0, colour parts cut by booleans in priority order (black → white → dark brown → orange = remainder), scaled ×0.1 before STL export.

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)

## Source
- Method: scripted (Blender Python, headless)

## Pipeline
- SOURCE/IMPORT v1 (scripts/build_fox.py, headless 7 s): metaballs at 10x (body+head one family, legs, tail), 2 lofted ear meshes; voxel 0.003 (0.3 mm printed), flat cut Z=0 → 305,562 tris; scaled ×0.09938 → 80.00 mm. Parts: black 3,438 / white 38,328 / brown 35,122 / orange 241,954 tris, all 0 non-manifold; volumes 0.06 + 4.66 + 2.40 + 42.15 = 49.26 cm3 = solid 49.26 cm3 (no overlap, no gap). Factory Cube removed from the live Blender to look (rule 6 exception).
  Look v1: reads as a fox. Faults: inner-ear cutter reached into the skull (white patch beside the ear), eyes small, left hind foot a ball. → v2: inner ear from t=0.30, eyes 6×3.2 mm, hind feet longer and flatter, ears 0.2 mm thicker.
- v2: same pipeline; white patch gone, hind foot reads as a foot. print_check solid vs body_parts.blend: PASS (52.5 × 56.5 × 80.0 mm, volume ratio 0.9996). First solid STL was 0 triangles — hide_render left on (print.md rule 9 trap); fixed in the script.
- v2 assembly print_check: FAIL — orange 3, white 1 edges shared by 3+ faces in the STL (Blender counted 0); black SCALE 91 % (ellipsoid inlays thin at their rim).
- v3: eyes as elliptic prisms along the surface normal (2 mm deep, straight walls), nose = muzzle tip cut square across its axis, every part triangulated (BEAUTY) before export → assembly PASS (slicer: Collapsing overhang, Low bed adhesion); with --supports --brim-mm 5: PASS, no stability warning. Islands: a 1,002-face white crumb on the left front paw (tail-tip cutter).
- v4: tail-tip cutter moved off the paw (crumb gone, close render); 4× volume-preserving Laplacian after the remesh. Review renders (matcap + colour, q1/q3/top/under): toothed creases at leg/haunch and tail/body; a brown disc under the tail from the right hind-toe cutter.
- v5: tail and hind feet in the body family (melt into the haunch), front legs 1.7 mm forward, tail front 2.7 mm forward, right hind-toe cutter dropped (foot under the tail). Creases still toothed.
- v6: front legs in the body family too (one skin) — teeth unchanged → not a family gap.
- v7: metaball resolution 2× finer (object scale 0.5, coords ×2: resolution is in object space, measured 12,218 → 49,418 faces on one ball) — teeth unchanged; the uncut solid shows them too → the voxel staircase at grazing silhouettes, not the colour cut.
- v8 (trial, undone): voxel 0.2 mm printed — teeth halved (∝ voxel), but 697,894 tris and orange 1 non-manifold edge → back to 0.3 mm (print.md: 0.35 passed on an 80 mm figure); teeth ≈ 0.15 mm in hidden creases, under one 0.2 mm layer. Kept: v7 geometry.
- CLEANUP (print variant: no merge, no tier decimation; print_check is the count): reference rebuilt with each piece flat-cut on its own and exact-duplicate vertices of the metaball mesh welded at 1e-7 m (reference only) — it read 4 non-manifold edges before. Solid vs fox-figurine_body_parts.blend: PASS, 52.8 × 59.3 × 80.0 mm, dims diff ≤ 0.01 %, volume ratio 0.9997. Islands: white 4 (bib+muzzle, tail tip, 2 inner ears), brown 5 (2 socks, 2 ear tips, left hind toe), black 3 (2 eyes, nose), orange 1 — no crumb. Looked (live Blender, 3/4, back 3/4, left, top): clean.
- Triangles: 310,876 solid; parts orange 255,332 / white 38,040 / brown 36,794 / black 4,448 (screen tier not applied to a print).
- OPTIMIZE: skipped (print). Preview web/fox-figurine_final.glb exported plain (no Draco, no WebP; extensionsUsed none), 4 meshes, Principled values only (audit: no procedural node).
- EXPORT: STL ×4 (global_scale 1000, mm) in print/; data-blocks renamed SM_FoxFigurine_{Colour}_Mesh. PrusaSlicer `-m --export-3mf` wrote 4 separate objects and dropped each to the bed (black part 46 mm down) → replaced by scripts/make_3mf.py: ONE object, 4 volumes (extruders orange 1, white 2, brown 3, black 4); PrusaSlicer --info: 52.8 × 59.3 × 80.0 mm, manifold yes, 334,614 facets, 13 parts, volume 50,462 mm3.
- Print orientation: as modelled, flat base (Z=0 cut under haunches, paws, tail) on the bed, face up — zero-support orientation does not exist for the chin/muzzle; this one keeps every visible face off the bed.
- Print check, solid: PASS, 52.8 × 59.3 × 80.0 mm, 1 part, vs reference dims ≤ 0.01 %, volume 0.9997, overhangs 5.32 %, smallest scale 25 %.
- Print check, assembly (orange+white+brown+black, PrusaSlicer 2.9 sliced): without supports PASS with "Collapsing overhang, Low bed adhesion"; with --supports --brim-mm 5: PASS, supports yes (from the slice), brim 5 mm, smallest scale 86 % (set by white — inner ears), overlap 0. Per part: orange 1 island, white 4, brown 5, black 3, all closed, 0 open / 0 non-manifold.
- .blend: fox-figurine.blend (colour parts + hidden solid), fox-figurine_body_parts.blend (reference), save_version 0 — no .blend1.
- Kept intermediates (auto, compact: listed, not deleted): review/ (v4, v7 renders, review/fox-figurine_solid.stl, check_*.json), scripts/.

## Licenses
- All geometry scripted in this session: no third-party resource.

## Checkpoint
- Last completed step: EXPORT + print check (PASS)
- Timestamp: 2026-10-23
