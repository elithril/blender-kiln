# Wooden Stool — Production Log

## Source Brief
Batch "blacksmith-workshop": a blacksmith's workshop. Asset brief: "Three-legged round workshop stool,
thick bevelled seat, splayed legs joined by stretchers, ~0.45 m tall". Palette: warm browns and iron grey.

## Config
- Type: prop (furniture)
- Target: glTF (web)
- Tier: lightweight (prop 300-1.5K tris, soft)
- Style: stylized
- Mode: auto (batch runner)
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference requested)

## Source
- Method: scripted (bmesh primitives via execute_blender_code, Blender 5.2.2 LTS, official Lab MCP)
- Hierarchy: empty `SM_WoodenStool` → Seat, Leg_01-03, Stretcher_01-03 (separate objects)

## Pipeline
- Scene: factory scene detected — default Cube removed (rule 6 exception). Camera and Light kept and left out of the export.
- Import: implicit (scripted). 332 tris, bbox 0.350 × 0.369 × 0.454 m (1 unit = 1 m, expected ~0.45 m tall ✓)
- Cleanup: 332 → 332 tris. Merge by distance 0, loose 0, degenerate dissolve, normals recalculated,
  fused edges 0, open edges 0 on every part. Transforms baked into the mesh data, origin at centre of base (feet on z=0).
- Poly check: 332 tris, inside lightweight range → no decimation.
- Texturing: skipped. Materials were assigned when the parts were built: seat + legs M_Wood_Warm (#8A5A32, rough 0.8),
  stretchers M_Wood_Dark (#5A3820, rough 0.85). Flat Principled BSDF values only.
- Material export audit (rule 19): all glTF compatible, no procedural nodes.
- Optimize: resize-1k-webp-draco (resize and webp are no-ops, since there are no textures). 10.5 KB → 7.0 KB (−33%) with Draco.
  The client needs a Draco decoder.
- Export: GLB, 7.0 KB, 332 tris, 7 meshes. gltf-transform validate: 0 errors, 0 warnings.
- Screenshots: two angles checked in the viewport (front 3/4 and back 3/4), final saved as wooden-stool_screenshot.png.

## Licenses
- All geometry and materials authored in-session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30
