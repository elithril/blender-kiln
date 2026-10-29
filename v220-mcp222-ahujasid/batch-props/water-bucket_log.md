# Water Bucket — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized wooden quench bucket, tapered staves, two iron hoops, iron bail handle, water inside"

## Config
- Type: prop
- Target: glTF (gltf-web)
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
- Method: scripted (Blender Python, bmesh), shared helpers in ../kiln_helpers.py
- Parts: SM_WaterBucket_Staves (14 tapered staves, 18 mm walls, 6 mm grooves, alternating M_Wood / M_WoodDark, ±7 mm rim variation), SM_WaterBucket_Bottom (M_WoodDark, set 4 mm into the staves), SM_WaterBucket_Hoops (M_Iron, 2 bands), SM_WaterBucket_Lugs (M_Iron pivot pins), SM_WaterBucket_Bail (M_Iron, round 11 mm handle, ends inside the pins), SM_WaterBucket_Water (M_Water, 6.5 cm below rim)

## Pipeline
- Scene cleared between assets by removing datablocks (no read_homefile)
- Import: implicit (scripted) — bbox 0.371 × 0.341 × 0.440 m (body 0.34 m Ø × 0.32 m, bail up to 0.44 m), base at z=0, origin centre of base
- Cleanup: 1,300 → 1,300 tris; transforms applied, 0 merged, normals recalculated, 0 loose, 0 fused, 0 non-manifold edges
- Poly budget: 1,300 tris — inside lightweight prop range (Hoops 448, Bail 300, Staves 280, Bottom 108, Water 108, Lugs 56)
- Texturing: skipped — procedural palette materials assigned at creation
- Material audit (rule 19): OK
- Optimize: resize 1024 → webp q90 → draco. No textures. 53.7 KB → 10.6 KB. Draco needs a decoder on the client.
- Export: GLB, 10.6 KB, 1,300 tris, 6 meshes, 4 materials (M_Wood, M_WoodDark, M_Iron, M_Water); no UVs. Water is opaque glossy (stylized), not transmissive.

## Files
- water-bucket_original.glb, water-bucket_final.glb, water-bucket.blend, water-bucket_screenshot.png, water-bucket_log.md

## Licenses
- All geometry and materials authored in-session; no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
