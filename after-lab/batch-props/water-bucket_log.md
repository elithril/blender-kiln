# Water Bucket — Production Log

## Source Brief
Batch `blacksmith-workshop`: "Stylized wooden stave water bucket with two iron hoops and an iron bail handle, filled with water"

## Config
- Type: prop
- Target: glTF (GLB, web)
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

## Source
- Method: scripted (Blender Python, bmesh)
- Blender 5.2.2 LTS, driven through the official Blender Lab MCP

## Pipeline
- Scene cleared by removing datablocks (Camera/Light kept, excluded from export)
- Build: 7 objects — SM_WaterBucket_Staves (12 tapered planks, r 0.13 → 0.16 m, 18 mm wall), _Bottom, _Water (disc at z 0.24), _Hoop_01/_02 (iron bands), _Ears (rim lugs), _Handle (bail arc, 16 segments)
- Import: 834 tris, bbox 0.354 × 0.322 × 0.45 m (0.30 m body + handle), origin at base centre
- Cleanup: merge 0, loose 0, degenerate dissolve, normals recalculated, fused edges 0 on all parts, transforms applied. Water disc: 24 open edges by design (single surface); its normal came out facing down after recalc and was flipped up. No decimation.
- Iteration: the first build used a 0.006 rad gap between staves and showed a see-through slit from the front; rebuilt at 0.0008 rad (~0.2 mm, still above the 0.1 mm merge threshold, so staves stay separate and nothing welds)
- Texturing: procedural Principled BSDF from palette — staves/bottom: M_Wood_WarmBrown, hoops/ears/handle: M_Metal_WroughtIron, water: M_Liquid_Water (#2f3d40, r 0.1, water entry added to the palette by the wizard)
- Material export audit: clean
- Optimize: resize-1k-webp-draco (individual steps; resize/webp no-op, no textures) → 43.6 KB → 9.3 KB (−79%). Draco needs a decoder client-side.
- Export: GLB, export_apply=False, 9.3 KB, 834 tris; gltf-transform validate: no errors, no warnings
- Screenshots: OpenGL viewport render, two opposite angles (az 30°/el 30°, az 210°/el 15°)

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29
