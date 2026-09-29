# Farmhouse Chair — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop/furniture 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Output: generated-assets/farmhouse-chair/

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: N/A (marketplace sourcing, no AI generation per brief)
- Hunyuan3D params: N/A

## Source
- Method: marketplace (PolyHaven only — AI generation and Sketchfab excluded by brief)
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_01 (by Kuutti Siitonen)
- Search: "wooden kitchen chair farmhouse", models, top 10. Picked #1 in auto mode:
  tagged farmhouse / kitchen / dining, 0.43 × 0.54 × 0.96 m.
- Download: via blender-mcp `download_polyhaven_asset`, .blend import, 2k textures
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.7 (protocol 11, up to date)

## Pipeline
- Scene prep: untouched factory scene (Cube, Camera, Light, no .blend loaded) —
  default Cube removed (rule 6 exception). Camera and Light kept, not exported.
- Import: 380 faces / 724 tris / 410 verts, bbox 0.432 × 0.540 × 0.956 m, scale 1.
  Renamed `painted_wooden_chair_01` → `SM_FarmhouseChair`, mesh `Box.041` →
  `SM_FarmhouseChair_Mesh`, material → `M_PaintedWood_Farmhouse`, images → `T_FarmhouseChair_{D,N,R,M}`.
- Cleanup: 380 → 380 faces. Merge by distance 0 merged; normals recalculated;
  0 loose; 0 degenerate; manifold: 0 fused edges, 0 open edges; transforms applied;
  mesh shifted (-0.0015, +0.0307, -0.0007) m so the origin sits at the bottom centre;
  orphans purged (factory `Material`, `Dots Stroke`, Cube mesh).
- Poly check: 724 tris — below the balanced range (1.5-5K). No action (alert only above +50%).
- Material audit: Principled BSDF, image textures only, no procedural / Color Ramp;
  Mapping node is identity. Metallic map was uniformly 0.0 (measured min = max = 0),
  replaced by constant Metallic = 0 — visually identical, one 2K map dropped.
- Texturing: skipped — PolyHaven PBR set (diffuse, normal GL, roughness).
- Optimize (auto preset, individual steps, rule 20): no resize (2048 = balanced cap)
  → `gltf-transform webp --quality 90` → `gltf-transform draco`.
  16.18 MB → 1.06 MB (-93%). Geometry untouched (724 tris). Draco needs a decoder client-side.
- Export: GLB, export_apply=False, Y-up, tangents exported (first pass without tangents
  raised MESH_PRIMITIVE_GENERATED_TANGENT_SPACE; re-exported with tangents).
  `farmhouse-chair_final.glb` 1.06 MB, 724 tris. glTF validator: 0 errors, 0 warnings
  (infos: Draco extension not validatable, one unused bufferView left by Draco).
- Known cosmetic: two texture names inside the GLB keep the source file names
  (`painted_wooden_chair_01_diff_2k`, `_rough_2k`) — the exporter names passthrough JPGs by file.

## Files (compact)
- farmhouse-chair_original.glb — 16.16 MB, as imported (renamed, before cleanup)
- farmhouse-chair_final.glb — 1.06 MB
- farmhouse-chair.blend — 4.84 MB, textures packed (sources were in a temp dir)
- farmhouse-chair_log.md

## Licenses
- painted_wooden_chair_01 (model + textures): CC0 1.0, by Kuutti Siitonen,
  Source: Poly Haven (polyhaven.com). No attribution required.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 19:55
