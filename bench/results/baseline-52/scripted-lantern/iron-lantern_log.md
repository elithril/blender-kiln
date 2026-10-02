# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.7 (protocol 11, up to date), Apple M4 Pro

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Brief: "A hanging iron lantern with a glass cage and a ring on top, for a medieval inn."
- Concept art: none (scripted from the brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted modeling (Blender Python / bmesh). No marketplace, no AI generation.
- Parts (all separate objects, collection `Props_Medieval`):
  - SM_IronLantern_Base: flared square foot + bevelled plate (88 tris)
  - SM_IronLantern_Frame: 4 corner posts, 3 horizontal bands, 8 cage bars (1,056 tris)
  - SM_IronLantern_Glass: 4 panes, an open-ended box inset behind the bars (8 tris)
  - SM_IronLantern_Roof: eave plate, 4-sided pyramid, chimney cap (132 tris)
  - SM_IronLantern_Ring: neck + vertical torus hanging ring (428 tris)
  - SM_IronLantern_Candle: wax candle (60 tris)
  - SM_IronLantern_Flame: emissive flame (168 tris)

## Pipeline
- Import: implicit (scripted). 7 objects, 1,940 tris, bbox 0.235 x 0.235 x 0.518 m
- Cleanup: 1,940 -> 1,940 tris. Merge by distance (0 merged), recalculate normals,
  remove loose (0), degenerate dissolve (none), transforms applied, all part origins at the
  asset's base centre (world origin), orphans purged (3 data-blocks).
  Non-manifold: 0 on every part except Glass (8 open edges at top and bottom, intentional).
- UVs: Smart UV Project on every part (angle 66 deg, margin 0.02). Added so the asset can be textured later.
- Texturing: skipped (scripted with flat Principled BSDF materials):
  - M_Metal_WroughtIron: base (0.055, 0.05, 0.045), metallic 0.85, roughness 0.55
  - M_Glass_Amber: base (0.95, 0.82, 0.55), alpha 0.3, roughness 0.05, BLEND, double-sided
  - M_Wax_Candle: base (0.92, 0.86, 0.72), roughness 0.6
  - M_Emissive_Flame: emission (1.0, 0.55, 0.12), strength 6 (KHR_materials_emissive_strength)
- Material export audit: passed. Principled BSDF only, no procedural nodes, no image textures.
- Optimize: skipped. The GLB is 127 KB with no textures, so Draco/meshopt is optional.
- Export: GLB, 127,496 bytes, 1,940 tris, export_apply=False, no Draco.
  Checked with gltf-transform inspect: 7 meshes, 7 nodes, 4 materials, glass alphaMode BLEND.

## Files
- iron-lantern_final.glb
- iron-lantern.blend
- iron-lantern_log.md

## Licenses
- All geometry and materials were made in this session. No third-party resources used.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 15:52
