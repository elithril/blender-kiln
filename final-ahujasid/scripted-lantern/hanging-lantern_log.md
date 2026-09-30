# Hanging Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 13, up to date)

## Brief
A hanging iron lantern with a glass cage and a ring on top, for a medieval inn.
- Assumed real size (no reference given): ~0.49 m tall including the ring, 0.22 m wide at the roof.
- Addition not in the brief: a wax candle with an emissive flame inside the cage.

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no AI)
- Hunyuan3D params: N/A

## Source
- Method: scripted modeling (bmesh + primitives via execute_blender_code), as requested by the brief
- Scene: Blender factory scene — default Cube removed before building (rule 6 exception); Camera and Light kept, not exported

## Parts (collection Props_Medieval, parented to empty SM_HangingLantern)
| Object | Tris | Material |
|---|---:|---|
| SM_HangingLantern_Base (foot + tray) | 88 | M_Metal_WroughtIron |
| SM_HangingLantern_Frame (4 posts + top/bottom rails) | 528 | M_Metal_WroughtIron |
| SM_HangingLantern_CageBars (2 vertical + 1 band per side) | 144 | M_Metal_WroughtIron |
| SM_HangingLantern_Glass (4 panes, 3 mm) | 48 | M_Glass_Clear |
| SM_HangingLantern_Roof (rim, pyramid, chimney, cap) | 176 | M_Metal_WroughtIron |
| SM_HangingLantern_Knob | 168 | M_Metal_WroughtIron |
| SM_HangingLantern_Ring (vertical torus, R 36 mm) | 640 | M_Metal_WroughtIron |
| SM_HangingLantern_Candle | 60 | M_Wax_Candle |
| SM_HangingLantern_Flame | 168 | M_Emissive_Flame |

Attachments: posts embedded 5 mm in base and roof rim; ring passes through the knob; knob embedded in the chimney cap; candle rests on the tray.

## Pipeline
- Import: implicit (scripted). bbox 0.22 × 0.22 × 0.486 m, base at z=0, origin at base centre
- Cleanup: merge by distance, remove loose, dissolve degenerate, recalc normals on every part.
  Frame had 8 fused edges (side rails ended flush on the cross rails → 16 verts welded into
  internal faces); rebuilt with side rails overlapping 3 mm instead → 0 fused edges on all parts.
  Transforms applied (identity on all parts). Orphans purged (3 data-blocks).
- Texturing: skipped — scripted asset with flat Principled materials (stylized):
  - M_Metal_WroughtIron: base (0.030, 0.026, 0.022) linear, metallic 0.85, roughness 0.55
  - M_Glass_Clear: warm tint (0.62, 0.58, 0.42), alpha 0.22, roughness 0.1, coat 1.0 → glTF BLEND + KHR_materials_clearcoat
  - M_Wax_Candle: (0.80, 0.70, 0.50), roughness 0.6
  - M_Emissive_Flame: emission (1.0, 0.5, 0.1) strength 4 → KHR_materials_emissive_strength
- Material audit (rule 19): 4/4 Principled, no procedural nodes
- Poly count: 2,020 tris — inside the balanced range, no decimation proposed
- Optimize: no textures, so resize/WebP not applicable; Draco only → 85.4 KB → 15.0 KB (−82%).
  Draco requires a decoder on the client (KHR_draco_mesh_compression is required).
- Export: GLB, 15.0 KB, 2,020 tris, 9 meshes, 4 materials. gltf-transform validate: 0 errors, 0 warnings.

## Files
- hanging-lantern_original.glb (85.4 KB, uncompressed)
- hanging-lantern_final.glb (15.0 KB, Draco)
- hanging-lantern.blend
- hanging-lantern_log.md

## Licenses
- All geometry and materials authored in this session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30 21:27
