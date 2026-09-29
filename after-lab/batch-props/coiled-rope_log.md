# Coiled Rope — Production Log

## Source Brief
Batch `blacksmith-workshop`: "Stylized coiled hemp rope lying flat, a few spiral turns with a loose end"

## Config
- Type: prop
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
- Method: scripted (Blender Python, bmesh tube swept along a path)
- Blender 5.2.2 LTS, driven through the official Blender Lab MCP

## Pipeline
- Scene cleared by removing datablocks (Camera/Light kept, excluded from export)
- Build: 1 object, SM_CoiledRope — flat Archimedean spiral, 5 turns (r 0.045 → 0.175 m), rope Ø 26 mm, loose tail of 8 × 0.04 m curling outward. The hexagonal cross-section rotates 0.5 rad per ring, so under flat shading it reads as twisted strands with no texture needed
- Import: 1,028 tris, bbox 0.546 × 0.417 × 0.026 m, rests on z = 0, origin moved to the XY centre of the bounds
- Cleanup: merge 0, loose 0, degenerate dissolve, normals recalculated, fused edges 0, open edges 0 (both ends capped), transforms applied. No decimation
- Texturing: procedural Principled BSDF — M_Fabric_Hemp (#a07a4a, roughness 0.95)
- Material export audit: clean
- Optimize: resize-1k-webp-draco (individual steps; resize/webp no-op, no textures) → 56.5 KB → 5.6 KB (−90%). Draco needs a decoder client-side.
- Export: GLB, export_apply=False, 5.6 KB, 1,028 tris; gltf-transform validate: no errors, no warnings
- Screenshots: OpenGL viewport render, two opposite angles (az 30°/el 40°, az 210°/el 20°)

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29
