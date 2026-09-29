# Coiled Rope — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized coil of thick hemp rope lying flat, a few stacked loops, one loose end"

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
- Method: scripted (Blender 5.0.1 Python). Helix sweep, 3.5 turns, coil radius 0.17 m, rope Ø 4 cm, 16 samples/turn,
  hexagonal cross-section twisted 20°/sample to suggest strands, plus a 10-sample loose tail descending to the floor.
  Built directly as mesh (no curve object, no modifier)
- Parts: SM_CoiledRope (single mesh)

## Pipeline
- Import: implicit (scripted). 800 tris, bbox 0.45 × 0.54 × 0.18 m (coil ~0.38 m Ø; tail extends the footprint)
- Cleanup: 800 → 800 tris. Merge by distance (0), recalc normals, remove loose (0), degenerate dissolve (0). Transforms applied, base at z=0, origin at coil centre. Smooth by angle 60° (smooth tube, flat end caps), no modifier. Within tier, no decimate.
- Texturing: skipped — M_Fabric_Rope assigned at creation
- Material export audit: OK (Principled BSDF only)
- UVs: none generated (flat-colour material)
- Optimize: preset resize-1k-webp-draco → resize/webp no-op (no textures); gltf-transform draco: 19.63 KB → 4.66 KB (−76%)
- Export: GLB, 4.66 KB, 800 tris

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T15:19
