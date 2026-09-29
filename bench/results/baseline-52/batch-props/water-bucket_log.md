# Water Bucket — Production Log

## Source Brief
"Stylized wooden quench bucket, tapered staves, two iron hoops, iron bail handle, water inside" — batch blacksmith-workshop

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: lightweight (prop range 300-1.5K tris)
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
- Method: scripted (Blender Python, bmesh revolve + sweep)
- Parts: SM_WaterBucket_Body (14-sided tapered shell, 15 mm wall, flat facets read as staves), SM_WaterBucket_Hoop_01/02 (iron bands at z 0.06 / 0.235), SM_WaterBucket_Handle (swept bail arc, 6 sides), SM_WaterBucket_Ear_01/02 (wooden lugs), SM_WaterBucket_Water (disc at z 0.24)

## Pipeline
- Import: implicit (scripted), 7 objects, 768 tris, bbox 0.365 x 0.345 x 0.460 m with the handle raised (body 0.34 x 0.33 x 0.30 m)
- Cleanup: 768 → 768 tris; transforms applied, merge by distance (0), normals recalculated, loose removed (0), degenerate dissolve; origin at centre of base (min z = 0.0)
- Non-manifold: 14 open edges on SM_WaterBucket_Water — intended (single-sided water plane); all other parts closed
- Poly check: 768 tris — within lightweight range, no decimate
- Texturing: Body + Ears: M_Wood_Dark (#5e3b22, rough 0.85); Hoops + Handle: M_Metal_Iron (#4a4c50, metallic 1.0, rough 0.55); Water: M_Water_Still (#2c4a5a, rough 0.1)
- Material audit: all materials glTF compatible
- Optimize: preset none (skipped)
- Export: GLB, 38.6 KB, 768 tris, export_apply=False, no modifiers; verified with gltf-transform inspect
- Note: no UV layers (flat procedural materials don't need them)

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T16:16
