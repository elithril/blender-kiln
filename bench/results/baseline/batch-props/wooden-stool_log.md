# Wooden Stool — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized three-legged round wooden stool, slightly splayed legs, one iron ring brace between legs"

## Config
- Type: prop (furniture)
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
- Method: scripted (Blender 5.0.1 Python, bmesh primitives)
- Parts: SM_WoodenStool (empty root) > Seat, Leg_01..03, Ring

## Pipeline
- Import: implicit (scripted). 5 mesh parts, 560 tris, bbox 0.38 × 0.38 × 0.50 m (seat height 0.50 m — plausible for a low workshop stool)
- Cleanup: 560 → 560 tris. Merge by distance (0 merged), recalc normals, remove loose (0), degenerate dissolve (0). Transforms identity (geometry built in world space), base at z=0 (legs shifted +2.4 mm after splay). Smooth by angle 35° written as sharp edges, no modifier. Poly budget: within tier, no decimate.
- Texturing: skipped — procedural palette materials assigned at creation. Seat: M_Wood_Warm; legs: M_Wood_Dark; ring: M_Metal_Iron
- Material export audit: OK (Principled BSDF only, no procedural nodes, no modifiers)
- UVs: none generated (flat-colour materials do not need them). Add UVs before any future texturing
- Optimize: preset resize-1k-webp-draco → resize/webp no-op (no textures); gltf-transform draco: 21.07 KB → 6.56 KB (−69%)
- Export: GLB, 6.56 KB, 560 tris

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T15:17
