# Water Bucket — Production Log

## Source Brief
Batch "blacksmith-workshop": a blacksmith's workshop. Asset brief: "Staved wooden water bucket, slightly tapered,
two iron hoops, iron bail handle, filled with water, ~0.30 m tall". Palette: warm browns and iron grey.

## Config
- Type: prop
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
- Concept art: none (scripted)

## Source
- Method: scripted (bmesh via execute_blender_code, Blender 5.2.2 LTS, official Lab MCP)
- Hierarchy: empty `SM_WaterBucket` → Staves (12 staves with 0.6° gaps and staggered tops), Bottom, Water,
  Hoop_01, Hoop_02, Lug_01, Lug_02, Handle

## Pipeline
- Scene: cleared by removing the previous asset's datablocks (not with read_homefile). Camera and Light kept, not exported.
- Import: implicit (scripted). 590 tris, bbox 0.345 × 0.313 × 0.437 m. The body is 0.30 m tall, and the handle arc reaches 0.437 m.
- Cleanup: 590 → 590 tris. Merge 0, loose 0, degenerate dissolve, normals recalculated, fused edges 0.
  Open edges: 12, on the Water surface only. It is a single-sided disc by design, and not a defect.
  Transforms baked, origin at centre of base.
- Poly check: 590 tris, inside lightweight range → no decimation.
- Texturing: skipped. Materials were assigned when the parts were built: staves + bottom M_Wood_Warm (#8A5A32), hoops + lugs + handle
  M_Metal_Iron (#4B4E53, metallic 0.9, rough 0.5), water M_Water_Still (#2F4A58, rough 0.08).
  The lugs were first built in wood_dark. They were switched to iron because the manifest lists [wood, iron, water] for this asset.
- Material export audit (rule 19): all glTF compatible.
- Optimize: resize-1k-webp-draco (resize and webp are no-ops, since there are no textures). 21.9 KB → 8.9 KB (−59%). The client needs a Draco decoder.
- Export: GLB, 8.9 KB, 590 tris, 8 meshes. gltf-transform validate: 0 errors, 0 warnings.
- Screenshots: two angles checked (front 3/4 from above, back low angle), saved water-bucket_screenshot.png.

## Licenses
- All geometry and materials authored in-session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30
