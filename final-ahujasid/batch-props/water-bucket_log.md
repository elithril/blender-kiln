# Water Bucket — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized wooden stave bucket, slightly tapered, two iron hoops, iron handle, filled with water"

## Config
- Type: prop
- Target: glTF (web)
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

## Source
- Method: scripted (Blender Python bmesh, Blender 5.2.2 LTS)

## Pipeline
- Import: implicit (scripted). 8 objects: SM_WaterBucket_Staves (12 slats with 1.2° gaps), _Bottom, _Hoop_01/02, _Handle, _Lug_01/02, _Water. Bbox 0.37 × 0.34 × 0.46 m (rim 0.32 m, handle apex ~0.46 m); base Ø 0.27 m, top Ø 0.33 m
- Cleanup: 866 → 866 tris. Merge by distance (0), recalc normals, remove loose (0), degenerate dissolve, manifold check: fused edges 0 on all parts; open edges 24 on SM_WaterBucket_Water only (single-sided water disc, intended). Transforms applied, origin = centre of base
- Texturing: skipped — procedural Principled BSDF assigned at creation. Staves M_Wood_Warm, bottom M_Wood_Dark, hoops/handle/lugs M_Metal_Iron, water M_Liquid_Water (#2f4a52, roughness 0.08)
- Material export audit: clean
- Optimize: resize-1k-webp-draco — no textures, only Draco had effect. 45,640 B → 10,352 B (−77%). Client needs a Draco decoder.
- Export: GLB, water-bucket_final.glb, 10,352 B, 866 tris
- Screenshots: two angles (front 28°, back/top 50°) checked; water-bucket_screenshot.png saved
- Note: the hoops' inner faces sit flush on the staves' outer faces (hidden, not fused — separate objects)

## Licenses
- All geometry and materials created from scratch in this session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30T19:49:18Z
- Duration (measured): 77s
