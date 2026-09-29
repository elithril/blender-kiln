# Farmhouse Chair — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: N/A (marketplace sourcing, no AI generation per brief)
- Hunyuan3D params: N/A

## Source
- Method: marketplace
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_01 (Painted Wooden Chair 01, by Kuutti Siitonen)
- Search: PolyHaven models, "wooden kitchen chair farmhouse" → result #1 of 10 (tags: farmhouse, kitchen, dining)
- Download: 2k, imported from .blend (Blender 5.2.2 LTS, blender-mcp addon 1.7)

## Pipeline
- Import: 380 faces / 724 tris / 410 verts, bbox 0.432 × 0.540 × 0.956 m (matches PolyHaven's published size)
  - Renamed: painted_wooden_chair_01 → SM_FarmhouseChair, Box.041 → SM_FarmhouseChair_Mesh,
    material → M_Wood_PaintedWhite, images → T_FarmhouseChair_{D,M,R,N}
  - Tier alert: 724 tris is BELOW the balanced range (1.5-5K). Soft range, not blocking —
    detail is carried by the 2K normal map.
- Cleanup: 380 → 380 faces. Pre-measured: 0 doubles, 0 loose, 0 degenerate, 0 non-manifold edges,
  0 faces needing a flip. Ran merge-by-distance (0 removed), recalc normals, remove loose,
  dissolve degenerate, apply transforms. Custom split normals preserved (max deviation 2.7e-5).
  Geometry re-centred so the base centre sits at the origin (offset -0.0015, +0.0307, -0.0007 m).
  Orphans purged (3 data blocks, incl. default cube material).
- Material audit: Principled BSDF only, no procedural/Color Ramp nodes, all maps ≤ 2048.
  Note: metallic map is uniformly 0.0 (kept as-is; harmless).
- Texturing: skipped — full PBR set from source (diffuse, metallic, roughness, normal GL).
- Optimize: PENDING user choice. Candidates measured (not yet applied):
  - WebP q90 @2K: 15.41 MB → 1.04 MB (-93%), 724 tris, validator clean
  - resize 1K + WebP q90 + Draco: 15.41 MB → 0.29 MB (-98%), 724 tris, validator clean
- Export: GLB, 15.41 MB, 724 tris (unoptimized). export_apply=False, Y-up, no Draco.

## Files (compact)
- farmhouse-chair_original.glb — as imported, before cleanup (15.41 MB)
- farmhouse-chair_final.glb — cleaned (15.41 MB, unoptimized pending OPTIMIZE choice)
- farmhouse-chair.blend — textures packed (4.62 MB)
- farmhouse-chair_log.md

## Licenses
- Painted Wooden Chair 01 (model + textures): CC0 — Poly Haven, Kuutti Siitonen. No attribution required.

## Checkpoint
- Last completed step: EXPORT (unoptimized); OPTIMIZE awaiting choice
- Timestamp: 2026-09-29 16:02
