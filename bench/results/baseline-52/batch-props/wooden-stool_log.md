# Wooden Stool — Production Log

## Source Brief
"Stylized three-legged wooden workshop stool, round thick seat, splayed legs, iron ring brace between legs" — batch blacksmith-workshop

## Config
- Type: prop (furniture)
- Target: glTF (GLB)
- Tier: lightweight (prop range 300-1.5K tris)
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
- Parts: SM_WoodenStool_Seat (16-side disc, 2-segment edge bevel), SM_WoodenStool_Leg_01..03 (8-side tapered, splayed), SM_WoodenStool_Brace (torus 24x6)

## Pipeline
- Import: implicit (scripted), 5 objects, 560 tris, bbox 0.394 x 0.413 x 0.460 m (plausible stool height)
- Cleanup: 560 → 560 tris; transforms applied, merge by distance (0 merged), normals recalculated, loose removed (0), degenerate dissolve; 0 non-manifold edges; origin = world origin at centre of base (min z = 0.0)
- Poly check: 560 tris — within lightweight range, no decimate
- Texturing: palette procedural — Seat + Legs: M_Wood_Warm (#8a5a34, rough 0.8); Brace: M_Metal_Iron (#4a4c50, metallic 1.0, rough 0.55)
- Material audit: all materials glTF compatible (Principled BSDF only, no procedural nodes)
- Optimize: preset none (skipped)
- Export: GLB, 34.9 KB, 560 tris, export_apply=False, no modifiers present; verified with gltf-transform inspect (5 meshes, 2 materials)
- Note: Leg and Seat have no UVs (primitives created via bmesh without UV layer) — not needed for flat procedural materials

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T16:15
