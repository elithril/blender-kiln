# Wooden Stool — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized three-legged blacksmith's stool, round thick wooden seat, splayed legs, one iron band ring bracing the legs"

## Config
- Type: prop (furniture)
- Target: glTF (GLB, web)
- Tier: lightweight (prop 300-1.5K tris)
- Style: stylized
- Mode: batch (auto)
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)
- Hunyuan3D params: N/A

## Source
- Method: scripted (bmesh in execute_blender_code, Blender 5.2.2 LTS)
- Parts: SM_WoodenStool (empty root) → Seat (16-sided disc, bevelled rim), Leg_01..03 (8-sided tapered, splayed 120°), Band (iron ring, 24×6)

## Pipeline
- Scene: factory scene detected (Cube/Camera/Light, no .blend) → default Cube removed (rule 6 exception); Camera and Light kept, excluded from export
- Import: implicit (scripted), 560 tris, bbox 0.388 × 0.411 × 0.484 m
- Cleanup: 560 → 560 tris. Merge by distance 0 verts, loose 0, degenerate dissolve, normals recalculated, fused edges 0, open edges 0, transforms identity, base moved to z=0 (legs were 4.3 mm below floor)
- Poly budget: 560 tris, inside lightweight prop range, no decimation
- Texturing: procedural Principled BSDF values (palette) — Seat: M_Wood_Warm #8a5a36 r0.8; Legs: M_Wood_Dark #5e3b22 r0.85; Band: M_Metal_Iron #5a5c5e m1.0 r0.55
- Material export audit: all GLTF compatible (Principled only, no procedural nodes)
- Optimize: resize 1024 → webp q90 → draco (individual steps). 31,100 B → 6,652 B (−79%). No textures, so resize/webp were no-ops; the saving is Draco. Draco needs a decoder on the client.
- Export: GLB, 6,652 B, 560 tris, gltf-transform validate: no errors, no warnings
- Note: no UVs exported (value-only materials need none)

## Licenses
- All geometry and materials created from scratch in this session — no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T18:09:22Z
- Duration (measured): 102s
