# Lantern — Production Log

## Config
- Type: prop
- Target: glTF (web, game-ready)
- Tier: balanced (prop 1.5-5K tris, soft; up to 10K when spent on thin parts)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none (repair of an existing AI GLB; no marketplace, no new generation)
- Decimation: approved in advance by the user, original kept

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A — reference is the source GLB itself (keep shape and look)

## Prompts (copy-paste ready)
- N/A (no generation in this session)

## Source
- Method: AI (TRELLIS), user-provided file
- File: /private/tmp/kiln-bench/v300final-ahujasid/repair-trellis-glb/refs/trellis/lantern_trellis.glb (untouched)
- Inspect: generator trimesh, 1 mesh, 191,520 tris, 194,358 verts, 1 material (baseColor + metallicRoughness PNG 1024²), 11.4 MB, bbox 0.42 × 1.00 × 0.33 (glTF Y-up)

## Pipeline
- CONFIG/BRIEF: confirmed (auto). Env: Blender 5.2.2 LTS via MCP (addon proto 14, up to date), gltf-transform, gltfpack.
- SOURCE: user file, no search, no generation.
- Import: 191,520 faces, 1 mesh, 1 material; bbox 0.42 × 0.34 × 1.00 m (TRELLIS unit box). Factory Cube removed (untouched factory scene). Renamed SM_Lantern / SM_Lantern_Mesh / M_Lantern.
  - ASSUMPTION (auto mode): real size = 0.38 m tall with bail raised (hurricane lantern) → scaled ×0.38, applied; origin at base centre, base on z=0. Final 0.160 × 0.127 × 0.380 m.
- Cleanup diagnosis: as-imported weld (1e-8…1e-5) → 13,732 fused edges (up to 13 faces/edge), 10,220 open; 0 duplicate faces. Glass globe + wire guard are self-crossing thin sheets → not repairable by weld.
- Cleanup tries (all from untouched copy SM_Lantern_High, kept hidden as bake source):
  - voxel 0.6 mm → closed (0/0) but genus 4,778, Collapse stalled at 75,802 tris — undone
  - voxel 1.0 mm → 0/0, 9,000 tris, but glass globe became a perforated shell holding 6,675 of the 9,000 tris — undone
  - cut glass zone after remesh + fill holes → 64 fused / 485 open — undone; cut before remesh → genus up, Collapse stalled at 25,210 — undone
  - KEPT: solid lathe plug fitted to the measured globe profile (r 32→44→34 mm, z 0.086–0.170, 0.3 mm inside the glass) joined to the high, voxel remesh 1.0 mm (bail wire ≈3 mm = 3 voxels), 2 sub-20-face/inside shells dropped, 3 shells kept, Collapse decimate (pre-approved) 489,720 → 9,000 tris. fused 0, open 0, degenerate 0. Smooth by angle 40°.
  - Deviation vs high (1 mm remesh version): median 0.38 mm. Visible: bail, top loop, frame tubes, filler cap, guard wires (as relief on globe) intact; small lumps on font top / hood from TRELLIS surface flakes; base grooves to come back via normal bake.
- Texturing: original look carried over by bake from SM_Lantern_High (Cycles, selected-to-active, cage 4 mm, ray 10 mm, margin 8 px), 1 material M_Lantern_Baked (Principled BSDF):
  - UVs: Smart UV Project 66°, pack CONCAVE margin 0.003 → used 39.0 % (28.7 % before repack); uv_check: overlap 0 %, stretch 0 %, collapsed 0 %, flipped 0 % — 0 FAIL, 0 WARN
  - baseColor 1024² (emission of TRELLIS Image_0), metallicRoughness 1024² (emission of Image_1: G rough, B metal), normal 1024² tangent
  - Normal bake fault found and fixed: 84,115 of 191,520 TRELLIS faces pointed inward → silvery patches; bake copy flipped to face the low surface, custom normals cleared, re-baked → matches original from both sides
  - Material audit: Principled only, no procedural nodes, no texture > 2048 → OK
- Fault found at OPTIMIZE review and fixed: after the UV repack the re-baked images were packed, so img.save() did not write them; the first export carried the first bake's textures on the new UVs (black blotches in the headless colour render). Rewritten from the live buffers, re-exported, reviewed clean.
- Optimize: gltf-transform resize 1024 → webp q90 → draco (separate steps, rule 20). lantern_original.glb 3.90 MB → web/lantern_final.glb 0.63 MB (−84 %). Source TRELLIS GLB was 11.4 MB. lantern_preview.glb = copy of _original (no Draco, no WebP; opens in Quick Look).
- Review (headless, review_renders.py, final GLB): colour + matcap q1, q3, top, under — clean; Draco decodes (11,238 verts / 9,000 tris).
- Export: glTF/GLB, export_apply=False, Y-up, material audit OK. web/lantern_final.glb 0.63 MB, 9,000 tris, Draco + WebP (needs DRACOLoader client-side). Studio checks: 0 WARN (note: 9,000 tris = 1.8× balanced top, within 2× allowance).
- Files: lantern.blend (SM_Lantern + hidden SM_Lantern_High bake source), lantern_original.glb, lantern_preview.glb, web/lantern_final.glb, this log.
- Intermediates kept (auto mode, nobody to confirm deletion — compact mode would remove them): intermediate/ (lantern_resized.glb, lantern_webp.glb, review/ renders, scripts/), bake/ (3 PNGs, also packed in the .blend).
- Poly check: 9,000 tris vs balanced prop 1.5–5K → 1.8× top, within the 2× allowance; spent on bail, guard wires, frame tubes and round sections.

## Licenses
- lantern_trellis.glb: user-provided, generated with TRELLIS (MIT model licence); output owned by user

## Checkpoint
- Last completed step: EXPORT (done)
- Timestamp: 2026-10-23
