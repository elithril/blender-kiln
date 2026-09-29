# Coiled Rope — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized coil of thick hemp rope lying flat, stacked loops, loose tail end"

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
- Method: scripted (Blender Python, bmesh tube sweep with rotation-minimising frames)
- Parts: SM_CoiledRope — single swept tube: 3 stacked helical loops (r≈0.15 m, rope Ø 4.4 cm,
  ±8 mm radius wobble), then a cubic-Bézier tail dropping to the floor. 59 rings × 9 sides,
  3-strand twist baked as ±12 % radius modulation. Rope length ≈ 3.27 m. Smooth shading.

## Pipeline
- Import: implicit (scripted), 1 object, 1,058 tris, bbox 0.700 × 0.414 × 0.169 m (coil Ø ≈ 0.36 m, tail extends +X)
- Origin: world origin at the coil centre, on the floor — not at bbox centre, because the tail makes the bbox asymmetric
- Cleanup: 1,058 → 1,058 tris. Merge by distance: 0. Degenerate: none. Loose: 0. Normals recalculated.
  Non-manifold edges: 0. Transforms applied. Smart-project UVs added.
- Poly budget: 1,058 tris — inside lightweight prop range (300-1.5K). No decimation.
- Texturing: procedural palette — M_Rope (#B08A5A, rough 0.9)
- Material export audit: M_Rope OK (Principled BSDF only)
- Optimize: preset none — skipped (no textures, 35 KB)
- Export: GLB, 35,356 bytes (34.5 KB), 1,058 tris, export_apply=False, Y-up. Verified with gltf-transform inspect.
- Note: the twist is geometric and subtle at 9 sides; a normal map would sharpen strands but is outside the procedural palette.

## Files
- coiled-rope_original.glb (19.7 KB, pre-cleanup) │ coiled-rope_final.glb (34.5 KB) │ coiled-rope.blend │ coiled-rope_screenshot.png

## Licenses
- All geometry and materials authored in-session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29
