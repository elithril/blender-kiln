# Water Bucket — Production Log

## Source Brief (batch)
"Stylized wooden quench bucket: tapered staves, two iron hoops, iron bail handle, filled with water"
Batch: blacksmith-workshop (batch-manifest.yaml) — scene "a blacksmith's workshop", palette warm browns + iron grey.

## Config
- Type: prop
- Target: glTF (web)
- Tier: lightweight (props 300-1.5K tris, soft)
- Style: stylized
- Mode: auto (batch runner, no prompts)
- Storage: compact
- Blender: 5.2.2 LTS, live session via the Blender Lab MCP

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)

## Source
- Method: scripted (Blender Python, bmesh lathe/sweep)

## Pipeline
- Brief: assumed size — 0.30 m tall body, Ø 0.25 m base flaring to Ø 0.30 m at the rim, slight belly; 16 staves alternating two wood tones; 2 iron hoops; iron bail with a wooden grip, resting tilted 25°; water surface 6 cm under the rim.

- Source/Import: scripted build (_scripts/build_water_bucket.py) — 9 parts under empty SM_WaterBucket: Body (16-seg lathe, closed wall + floor, staves alternating M_Wood_Warm / M_Wood_Dark), Hoop_01-02 (ring sections entering the wall 3 mm), Water (disc, edge enters the inner wall 2 mm, surface z 0.24), Lug_01-02, Bail (20-seg sweep, ends hooked into the lugs, tilted 25° back), Grip. 828 tris, 426 verts, 0.331 × 0.308 × 0.428 m (world-space vertices; bail top z 0.415), min z 0.000. Previous asset's datablocks removed (batch rule 30). Framed screenshot (3/4): OK.

- Cleanup: 828 → 828 tris (9 parts). Transforms identity; weld 1e-4: 0 merged; normals outward; 0 loose; no degenerate faces; manifold: 0 fused, 0 open edges on every part; origin at the base centre (box centre 0,0); names SM_WaterBucket_* / *_Mesh; 0 orphans; 0 empty slots. Poly budget: 828 tris, inside lightweight (300-1.5K). No decimation. Note: lugs overlap the top hoop by 4 mm — reads as an ear riveted over the band, kept.

- Texturing: skipped (scripted, palette materials assigned at build) — zones: Body staves alternating M_Wood_Warm / M_Wood_Dark, floor M_Wood_Warm; Hoops, Lugs, Bail → M_Metal_Iron (#5c5f63, metallic 0.9, rough 0.5); Grip → M_Wood_Dark; Water → M_Water_Still (#2e4650, rough 0.08, opaque). Principled values only. Looked from two opposite angles (front-left from above, back-right from low): OK.

- Optimize: preset resize-1k-webp-draco as separate gltf-transform steps (resize/webp no-ops: no image textures), validator exit 0 after each; 49,596 B (_original) → 14,664 B (web/_final, Draco) = −70 %. Draco needs a decoder on the client. Preview: water-bucket_preview.glb = copy of _original, extensionsUsed [] checked. Stage files in _stages/.

- Export: glTF/GLB, export_apply=False, material audit passed (4 Principled BSDF materials, no procedural nodes). web/water-bucket_final.glb 14.3 KB, 828 tris, 8 meshes (Body = 2 primitives, one per wood tone). .blend saved. Final look: review_renders on the final GLB → review/ (q1, q3, top, under): reads correctly, bail seated in the lugs, water inside the rim.
## Licenses
- All geometry and materials authored in this session (scripted): no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-22T14:43:35+02:00
