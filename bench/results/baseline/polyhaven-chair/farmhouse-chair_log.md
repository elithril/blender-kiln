# Farmhouse Chair — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop/furniture 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: N/A
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (marketplace source, no AI)
- Hunyuan3D params: N/A

## Source
- Method: marketplace (PolyHaven only — AI and Sketchfab excluded by brief)
- Search: "wooden chair farmhouse kitchen", models, top 10 reviewed
- Picked: Painted Wooden Chair 01 (`painted_wooden_chair_01`), by Kuutti Siitonen
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_01
- Why: only result tagged both farmhouse and kitchen; dining-chair proportions (0.96 m tall);
  distressed white paint over wood, slatted seat, square legs, stretchers
- Resolution: 2k textures (web target)

## Pipeline
- Environment: Blender 5.0.1, blender-mcp addon 1.7 (protocol 11, up to date), PolyHaven enabled
- Import: 380 faces / 724 tris / 410 verts, 24 mesh islands, bbox 0.432 x 0.540 x 0.956 m
- Rename: `painted_wooden_chair_01` -> `SM_FarmhouseChair` / `SM_FarmhouseChair_Mesh`,
  material -> `M_Wood_PaintedWhite`, images -> `T_FarmhouseChair_{BaseColor,M,R,N}`
- Texture packing: the addon's temp download dir was already deleted, so BaseColor could not be
  packed from its path. Re-downloaded the original 2k JPEG from the PolyHaven CDN
  (api.polyhaven.com/files) and packed it; M, R, N were already packed.
- Cleanup (measured before running): 0 duplicate verts, 0 loose, 0 degenerate, 0 non-manifold,
  recalc would flip 0 faces. Canonical sequence run anyway: 410 -> 410 verts, 380 -> 380 faces,
  custom split normals preserved. Transforms applied (were identity). Origin set to base center
  (geometry shifted 0.0015, -0.0307, 0.0007 m). Orphan purge removed 1 unused data-block.
- Poly check: 724 tris, BELOW the balanced range (1.5-5K). Alert only, no action — low count
  comes from the source; the detail lives in the 2k normal map.
- Texturing: skipped (full PBR set shipped with the asset)
- Material audit (rule 19): OK — Principled BSDF + image textures only, identity Mapping node,
  no procedural nodes, no textures > 2048
- Optimize: not run yet (interactive step) — see below
- Export: GLB, export_apply=False, selection only (default scene Cube hidden, not exported)
  - final: 16,158,204 B, 724 tris, 1 node, 1 material
  - image breakdown: normal PNG 13.1 MB (EXR source re-encoded losslessly), ORM PNG 2.5 MB,
    base color JPEG 0.54 MB
  - Known cosmetic: base color image is named `diff_2k` inside the GLB (taken from the file path)

## Licenses
- Painted Wooden Chair 01 model + textures: CC0 (PolyHaven, Kuutti Siitonen) — no attribution required

## Checkpoint
- Last completed step: EXPORT (unoptimized); OPTIMIZE pending user choice
- Timestamp: 2026-09-29 15:04
