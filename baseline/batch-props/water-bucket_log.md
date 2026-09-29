# Water Bucket — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized wooden stave bucket, slightly tapered, two iron hoops, iron bail handle, water surface inside"

## Config
- Type: prop
- Target: glTF-web (GLB)
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
- Method: scripted (Blender 5.0.1 Python, bmesh lathe/spin, 12 segments = faceted stave look)
- Parts: SM_WaterBucket (empty root) > Body, Hoop_01..02, Ear_01..02, Handle, Water

## Pipeline
- Import: implicit (scripted). 7 mesh parts, 522 tris, overall bbox 0.35 × 0.33 × 0.43 m (body 0.32 Ø × 0.30 m, handle raised)
- Cleanup: 522 → 522 tris. Merge by distance (0), recalc normals, remove loose (0), degenerate dissolve (0). Transforms identity, base at z=0. Smooth by angle 35° as sharp edges, no modifier. Within tier, no decimate.
- Texturing: skipped — palette materials at creation. Body: M_Wood_Warm; hoops, ears, handle: M_Metal_Iron; water: M_Liquid_Water
- Material export audit: OK (Principled BSDF only, no procedural nodes, no modifiers)
- UVs: none generated (flat-colour materials). Add UVs before any future texturing
- Optimize: preset resize-1k-webp-draco → resize/webp no-op (no textures); gltf-transform draco: 22.14 KB → 7.87 KB (−64%)
- Export: GLB, 7.87 KB, 522 tris

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T15:18
