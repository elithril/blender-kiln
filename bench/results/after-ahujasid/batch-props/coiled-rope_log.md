# Coiled Rope — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized coiled hemp rope lying flat, spiral coil of thick rope with a loose tail end"

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
- Method: scripted (bmesh sweep in execute_blender_code, Blender 5.2.2 LTS)
- Parts: SM_CoiledRope (empty root) → Coil: one hexagonal tube (Ø 36 mm) swept along a 4-turn flat Archimedean spiral (inner r 0.05 m, pitch 37.5 mm) plus a 0.3 m curling tail; parallel-transport frames with a twist of 6 turns/m for a faceted, stylized strand look. Rope length 3.46 m, ends capped

## Pipeline
- Scene clear: previous asset's objects and orphan datablocks removed (no read_homefile); Camera/Light kept
- Import: implicit (scripted), 1,304 tris, bbox 0.559 × 0.499 × 0.036 m
- Cleanup: 1,304 → 1,304 tris. Merge 0, loose 0, degenerate dissolve, normals recalculated, fused edges 0, open edges 0 (closed tube)
- Origin: centre of the coil at ground level (the tail extends toward +X); transforms identity
- Poly budget: 1,304 tris, inside lightweight prop range (upper end), no decimation
- Texturing: procedural Principled BSDF — M_Fabric_Hemp #b08a5a r0.95
- Material export audit: all GLTF compatible
- Optimize: resize 1024 → webp q90 → draco (individual steps). 71,480 B → 6,956 B (−90%). No textures: the saving is Draco. Draco needs a decoder on the client.
- Export: GLB, 6,956 B, 1,304 tris, gltf-transform validate: no errors, no warnings

## Licenses
- All geometry and materials created from scratch in this session — no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T18:11:27Z
- Duration (measured): 52s
