# Wooden Stool — Production Log

## Source Brief
Batch `blacksmith-workshop`: "Stylized three-legged wooden blacksmith's stool, round thick seat, splayed legs, one iron ring brace"

## Config
- Type: prop (furniture)
- Target: glTF (GLB, web)
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

## Source
- Method: scripted (Blender Python, bmesh primitives)
- Blender 5.2.2 LTS, driven through the official Blender Lab MCP

## Pipeline
- Scene: factory start-up scene detected (Cube, Camera, Light, no .blend) → Cube removed (rule 6 exception). Camera and Light kept, excluded from export.
- Build: 5 objects — SM_WoodenStool_Seat (20-sided disc, bevelled rim), SM_WoodenStool_Leg_01..03 (8-sided tapered, splayed 0.10 → 0.20 m), SM_WoodenStool_Brace (iron ring, z 0.17 m)
- Import: 608 tris, bbox 0.39 × 0.40 × 0.48 m (seat height 0.48 m — plausible stool), origin at base centre under the seat axis
- Cleanup: merge by distance 0 verts, loose 0, degenerate dissolve, normals recalculated, fused edges 0, open edges 0, transforms applied on all parts. No decimation (608 tris within range)
- Texturing: procedural Principled BSDF from palette — seat: M_Wood_WarmBrown (#7a4a28, r 0.8), legs: M_Wood_DarkBrown (#4e2e18, r 0.85), brace: M_Metal_WroughtIron (#5a5c60, metallic 1.0, r 0.55)
- Material export audit: clean (no procedural nodes, Principled only)
- Optimize: resize-1k-webp-draco (individual gltf-transform steps; resize/webp no-op, no textures) → 37.5 KB → 7.0 KB (−81%). Draco needs a decoder client-side.
- Export: GLB, export_apply=False, 7.0 KB, 608 tris; gltf-transform validate: no errors
- Screenshots: OpenGL viewport render (the Blender splash screen covered the live viewport), checked from two opposite angles (az 30°/el 20° and az 210°/el 35°)

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29
