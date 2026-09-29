# Wooden Stool — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized three-legged round wooden workshop stool, thick seat, splayed legs, cross rungs"

## Config
- Type: prop (furniture)
- Target: glTF (GLB, web)
- Tier: lightweight (prop 300-1.5K tris)
- Style: stylized
- Mode: auto (batch runner)
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python, bmesh primitives)
- Parts: SM_WoodenStool_Seat (16-seg disc, 2-segment chamfered rims, r=0.18 m, 5 cm thick),
  SM_WoodenStool_Leg01-03 (8-seg tapered, splayed 0.11→0.20 m radius),
  SM_WoodenStool_Rung01-03 (8-seg, z=0.16 m, triangle between legs)

## Pipeline
- Import: implicit (scripted), 7 objects, 356 tris, bbox 0.383 × 0.399 × 0.470 m — plausible stool height
- Cleanup: 356 → 356 tris. Merge by distance: 0 merged. Degenerate dissolve: none. Loose: 0.
  Normals recalculated. Non-manifold edges: 0. Transforms applied. 9 leg-foot vertices clamped to z=0
  (tilted leg caps dipped 4 mm below floor). Smart-project UVs added. Flat shading (stylized).
- Poly budget: 356 tris — inside lightweight prop range (300-1.5K). No decimation.
- Texturing: procedural palette — seat: M_Wood (#8B5A2B, rough 0.75); legs + rungs: M_WoodDark (#5C3A1E, rough 0.8)
- Material export audit: M_Wood OK, M_WoodDark OK (Principled BSDF only, no procedural nodes)
- Optimize: preset none — skipped (no textures, 28 KB)
- Export: GLB, 28,988 bytes (28.3 KB), 356 tris, export_apply=False, Y-up. Verified with gltf-transform inspect: 7 meshes, 2 materials, 0 textures.
- Note: materials export doubleSided (Blender backface culling off) — harmless on closed meshes.

## Files
- wooden-stool_original.glb (22.9 KB, pre-cleanup) │ wooden-stool_final.glb (28.3 KB) │ wooden-stool.blend │ wooden-stool_screenshot.png

## Licenses
- All geometry and materials authored in-session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29
