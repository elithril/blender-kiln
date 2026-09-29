# Water Bucket — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized wooden water bucket (quench bucket), tapered staves, two iron hoops, iron bail handle, water surface inside"

## Config
- Type: prop
- Target: glTF (GLB, web)
- Tier: lightweight (prop 300-1.5K tris)
- Style: stylized
- Mode: batch (auto)
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)
- Hunyuan3D params: N/A

## Source
- Method: scripted (bmesh in execute_blender_code, Blender 5.2.2 LTS)
- Parts: SM_WaterBucket (empty root) → Body (16-stave tapered shell, 16 mm wall, inner floor), Hoop_01/02 (flattened iron bands at z 0.07 / 0.25), Ear_01/02 (wooden lugs), Handle (iron bail arc, capped), Water (16-sided disc at z 0.26)

## Pipeline
- Scene clear: previous asset's objects and orphan datablocks removed (no read_homefile); Camera/Light kept
- Import: implicit (scripted), 898 tris, bbox 0.349 × 0.321 × 0.468 m (body 0.32 m tall, Ø 0.32 m at rim)
- Cleanup: 898 → 898 tris. Merge 0, loose 0, degenerate dissolve, normals recalculated, fused edges 0. Open edges: 16 on Water only (a single-sided disc, by design); all other parts closed
- Poly budget: 898 tris, inside lightweight prop range, no decimation
- Texturing: procedural Principled BSDF values — Body outer staves alternate M_Wood_Warm #8a5a36 / M_Wood_Dark #5e3b22 (rim, inner wall, floors dark); Hoops + Handle: M_Metal_Iron #5a5c5e m1.0 r0.55; Ears: M_Wood_Dark; Water: M_Water_Stylized #3f6f82 r0.1 (opaque)
- Material export audit: all GLTF compatible
- Optimize: resize 1024 → webp q90 → draco (individual steps). 45,188 B → 9,884 B (−78%). No textures: the saving is Draco. Draco needs a decoder on the client.
- Export: GLB, 9,884 B, 898 tris, gltf-transform validate: no errors, no warnings

## Licenses
- All geometry and materials created from scratch in this session — no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T18:10:35Z
- Duration (measured): 73s
