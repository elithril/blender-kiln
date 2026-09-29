# Water Bucket — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized wooden stave bucket, tapered, two iron hoops, iron bail handle, filled with water"

## Config
- Type: prop
- Target: glTF (GLB, web)
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
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python, bmesh)
- Parts: SM_WaterBucket_Staves (12 separate tapered staves, r 0.13→0.16 m, 1.8 cm wall, ±8 mm stylized height variation),
  SM_WaterBucket_Base (12-seg disc embedded in staves), SM_WaterBucket_Water (16-seg disc at z=0.25 m),
  SM_WaterBucket_Hoop01/02 (flat bands at z=0.06/0.26 m, 16 seg), SM_WaterBucket_Ear01/02 (lugs),
  SM_WaterBucket_Handle (half-ellipse bail, 14 seg × 6 sides)

## Pipeline
- Import: implicit (scripted), 8 objects, 704 tris, bbox 0.353 × 0.326 × 0.441 m (0.32 m body + bail) — plausible bucket size
- Cleanup: 704 → 704 tris. Merge by distance: 0. Degenerate: none. Loose: 0. Normals recalculated.
  Non-manifold edges: 0. Transforms applied. Smart-project UVs added. Flat shading (stylized).
- Poly budget: 704 tris — inside lightweight prop range (300-1.5K). No decimation.
- Texturing: procedural palette — staves + base: M_Wood (#8B5A2B, rough 0.75); hoops, ears, handle: M_Iron
  (#4A4A4F, metallic 1.0, rough 0.45); water: M_Water (#2E3A40, rough 0.05)
- Material export audit: M_Wood, M_Iron, M_Water — OK (Principled BSDF only, no procedural nodes)
- Optimize: preset none — skipped (no textures, 47 KB)
- Export: GLB, 48,452 bytes (47.3 KB), 704 tris, export_apply=False, Y-up. Verified with gltf-transform inspect.
- Note: water is an opaque dark disc (no transmission) — reads as water in stylized style; glTF engines will not refract it.

## Files
- water-bucket_original.glb (36.9 KB, pre-cleanup) │ water-bucket_final.glb (47.3 KB) │ water-bucket.blend │ water-bucket_screenshot.png

## Licenses
- All geometry and materials authored in-session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29
