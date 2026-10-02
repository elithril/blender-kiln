# Iron Lantern — Production Log

## Config
- Type: prop (hanging lantern, medieval inn)
- Target: glTF (GLB)
- Tier: balanced (prop range 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Blender 5.2.2 LTS, official Blender Lab MCP

## Reference Image
- Path: none
- Brief enrichment: none (text brief only)
- Visual comparison: N/A
- Assumed real size (no reference): 0.21 x 0.21 x 0.43 m overall (ring top at 0.4345 m, roof eave 0.21 m)

## Prompts (copy-paste ready)
- Concept art: none — scripted modeling on explicit request (no marketplace, no AI generation)

## Source
- Method: scripted (Blender Python) — `scripts/build_lantern.py`, re-runnable (clears and rebuilds the `Lantern` collection)
- Factory scene: default Cube removed before building (rule 6 exception). Default unused data-blocks
  (`Material`, `Dots Stroke`) and join leftovers dropped by the orphan purge. Camera and Light kept.

## Parts (14 objects, collection `Lantern`, all origins at base centre = world origin)
| Object | Material | Tris |
|---|---|---:|
| SM_Lantern_Finial (drop under the base) | M_Iron_Wrought | 22 |
| SM_Lantern_Base (two stepped plates) | M_Iron_Wrought | 216 |
| SM_Lantern_Posts (4 corner posts) | M_Iron_Wrought | 432 |
| SM_Lantern_Bands (bottom / mid / top rings) | M_Iron_Worn | 672 |
| SM_Lantern_CageBars (2 rods per face) | M_Iron_Wrought | 224 |
| SM_Lantern_Glass (4 panes) | M_Glass_Amber | 48 |
| SM_Lantern_Roof (eave + flared pyramid) | M_Iron_Wrought | 216 |
| SM_Lantern_Cap (chimney + lid) | M_Iron_Wrought | 376 |
| SM_Lantern_Eye (loop on the lid) | M_Iron_Wrought | 256 |
| SM_Lantern_Ring (threaded through the eye) | M_Iron_Worn | 640 |
| SM_Lantern_CandleDish | M_Iron_Wrought | 408 |
| SM_Lantern_Candle | M_Candle_Wax | 188 |
| SM_Lantern_Wick | M_Candle_Wick | 20 |
| SM_Lantern_Flame | M_Flame (emissive, strength 6) | 168 |

How parts meet: glass panes span post to post, inside the band thickness; cage rods pass over the
bands; roof sits on the top band; cap is sunk 4 mm into the roof apex; eye sits 2.5 mm into the lid;
ring's lower tube rests inside the eye's hole (interlocked links, perpendicular planes); candle stands
in the dish on the base.

## Pipeline
- Import: implicit (scripted), 3,886 tris, bbox 0.21 x 0.21 x 0.4345 m, min z = 0
- Cleanup: merge by distance (0.05 mm), degenerate dissolve, loose removal, normals recalculated,
  transforms applied, 0 edges with >2 faces, 0 boundary edges, 0 live modifiers.
  - Iteration 1: bands built from 4 overlapping boxes → merge welded corners into 120 fused edges.
    Rebuilt as one closed square ring per band (1.5 mm proud of the posts to avoid z-fighting).
  - `shade_auto_smooth` adds a Smooth-by-Angle GN modifier that `export_apply=False` would drop;
    replaced with `shade_smooth_by_angle` (sharp edges written into the mesh).
  - All bevels applied in the build — no modifier reaches the export (rule 18).
- Texturing: procedural Principled values only (stylized), no image textures.
  Glass: alpha 0.18, roughness 0.06, coat 1, blended, double-sided (first pass at alpha 0.32 read milky).
  Material audit: 6 materials, all Principled, 0 procedural nodes.
- Optimize: gltf-transform draco, 186.4 KB → 30.5 KB (−84%). No textures, so resize/WebP not applicable.
- Export: GLB, 30.5 KB, 3,886 tris, 14 meshes, 6 materials.
  Extensions: KHR_materials_clearcoat, KHR_materials_emissive_strength, KHR_draco_mesh_compression (required — client needs a Draco decoder).

## Notes
- SM_Lantern_Bands has no UV map (built vertex by vertex); harmless with value-only materials,
  add one before any texture work.
- Poly count 3,886 — inside the balanced prop range, no decimation proposed.

## Licenses
- All geometry and materials authored in this session — no third-party resources.

## Files
- iron-lantern_original.glb (186.4 KB) — uncompressed export
- iron-lantern_final.glb (30.5 KB) — Draco
- iron-lantern.blend (157.9 KB)
- scripts/build_lantern.py — build script

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30
