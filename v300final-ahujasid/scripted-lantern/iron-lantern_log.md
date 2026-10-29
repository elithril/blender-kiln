# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (web)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Backend: none — scripted modelling in Blender 5.2.2 (live, MCP addon 1.8, protocol 14)

## Brief
- Hanging iron lantern for a medieval inn: square iron cage, 4 glass panes, pyramid roof + chimney cap, hanging ring on top. Candle + flame inside (added so it reads as a lantern).
- Assumptions (auto mode): overall height ~0.42 m incl. ring, body ~0.18 m wide; origin = centre of base; front = -Y.

## Reference Image
- Path: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- N/A (no AI generation)

## Source
- Method: scripted (user's choice in the brief: no marketplace, no AI)

## Pipeline
- CONFIG/BRIEF: scene was Blender's untouched factory scene (Cube, Camera, Light, no .blend) — Cube removed before building (rule 6 exception).
- Source/Import: scripted build (build_lantern.py), 32 parts, 1,756 tris, bbox 0.225 x 0.225 x 0.50 m, standing on z=0, origin centre of base. Height 0.50 m vs 0.42 assumed (ring + chimney) — kept. look(angles) OK: ring seated on knob, bars/band on all 4 faces.
- Cleanup: 1,756 → 1,756 tris; merge 1e-5 (0 merged), normals recalculated, 0 loose, 0 degenerate, 0 fused / 0 open edges, transforms identity, all origins at base centre, bbox 0.225 x 0.225 x 0.503 m (vertices, world), orphans removed, 5 materials, all parts named SM_IronLantern_*. Fix: weld restored pre-recalc corner normals → checker shading on the ring; custom normals cleared, round parts shaded smooth by angle 40°; signed volume > 0 on all parts. Poly check: in balanced tier, no decimation.
- Texturing: skipped (scripted, materials assigned per part). Zones: iron frame/posts/bars/roof/foot → M_Iron_Wrought (0.045 grey, metal 0.75, rough 0.55); band/roof lip/chimney cap/ring/candle tray → M_Iron_Worn (0.11 warm grey, metal 0.85, rough 0.4); 4 panes → M_Glass_Amber (alpha 0.32, BLEND, rough 0.05 — alpha rather than transmission so every glTF viewer shows it see-through); candle → M_Wax_Candle; flame → M_Flame_Emissive (emission 6, KHR_materials_emissive_strength). Export audit: Principled only, 0 procedural nodes, 0 modifiers. uv_check: 32 meshes, 0 FAIL, 0 WARN (no UV maps — no image textures). Review renders (review_renders.py, matcap + colour, q1/q3/top/under) from _original.glb: OK.
- Optimize: gltf-transform draco (no textures → no resize/WebP step), 92.5 KB → 31.2 KB (−66%). Preview = copy of _original (no Draco/WebP, opens in Quick Look). No simplify/decimate.
- Export: glTF/GLB, web/iron-lantern_final.glb 31.2 KB, 1,756 tris, 32 meshes, 5 materials; export_apply=False, Y-up. Re-import check: 32 meshes, 1,756 tris, z 0–0.503 m. .blend saved (save_version 0). Studio checks: triangles/size/ground/compression ok.

## Licenses
- All geometry and materials authored in-session: no third-party resources.

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22
