# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop: 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Environment: Blender 5.0.1, blender-mcp addon 1.7 (protocol 11, up to date)

## Brief
Hanging iron lantern with a glass cage and a ring on top, for a medieval inn.
Interpretation: square wrought-iron cage (base tray, 4 corner posts, top/bottom/mid rails,
centre bar per side = 4 panes per face), amber glass panes, pyramid roof with finial and cap,
vertical hanging ring, candle on a dish with an emissive flame inside.

## Reference Image
- Path: none
- Brief enrichment: N/A
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)
- Hunyuan3D params: N/A

## Source
- Method: scripted modeling (Blender Python via execute_blender_code)
- Marketplace / AI: none (per brief)

## Pipeline
- Build: 7 objects, all origins at world origin = centre of base bottom, transforms applied,
  bevels/solidify applied during modelling (no live modifiers), smooth-by-angle 35° stored in mesh data.
  - First build had a bug: the bevel was applied before the scale, so the thin bars got
    ~0.05 mm bevels, and merge-by-distance collapsed them (Frame 1120 → 480 verts).
    Rebuilt with scale applied first; the Frame now merges only 8 coincident verts (1120 → 1112, tris unchanged).
- Cleanup: merge by distance (0.1 mm), recalc normals, remove loose (0), degenerate dissolve,
  smart UV project, orphan purge (default "Material", "Dots Stroke", temp meshes).
  Default startup Cube (8 verts) removed before building.
- Parts (tris): Base 216 │ Frame 2160 │ Glass 32 │ Roof 544 │ Ring 384 │ Candle 396 │ Flame 168
- Total: 3,900 tris (inside balanced range)
- Bbox: 0.236 × 0.236 × 0.500 m (ring top at 0.50 m)
- Texturing: skipped — scripted with Principled BSDF materials from creation
  - M_Iron_Wrought: base (0.035,0.033,0.032), metallic 0.85, roughness 0.6
  - M_Glass_Amber: base (0.95,0.72,0.38), alpha 0.35, roughness 0.08, blended
  - M_Wax_Candle: base (0.86,0.78,0.6), roughness 0.55
  - M_Flame_Emissive: emission (1,0.55,0.12) strength 6
- Material export audit: all 4 materials are Principled BSDF → Output only; no procedural nodes, no textures.
- Optimize: skipped (no textures, 142 kB, 3.9K tris — gltf-transform/gltfpack gains marginal). Offered to user.
- Export: GLB, 142,296 bytes, 3,900 tris, export_apply=False, Y-up.
  Verified by reading the GLB JSON: 7 nodes, bbox matches, glass alphaMode BLEND,
  flame uses KHR_materials_emissive_strength.
  _original.glb and _final.glb are identical (no optimization step).

## Licenses
- All geometry and materials authored from scratch in this session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29
