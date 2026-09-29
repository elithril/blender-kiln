# Farmhouse Chair — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, official Blender Lab MCP (no marketplace tools → PolyHaven public API from Bash), macOS 26.6.1, Apple M4 Pro, 24 GB unified memory

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- None — marketplace sourcing, no AI generation (per brief)

## Source
- Method: marketplace (PolyHaven only, per brief)
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_01
- Search: `api.polyhaven.com/assets?type=models&categories=furniture`, filtered on chair/stool (24 hits)
- Why this one: the only hit tagged both `farmhouse` and `kitchen` (also `dining`, `wood`, `painted`); chair-height 0.96 m. Runner-up `painted_wooden_chair_02` (farmhouse/dining, 1,246 tris) is 1.26 m tall, which is unusual for a kitchen chair
- Resolution: 2K glTF (balanced tier = 1K-2K). Files: `.gltf` 2,785 B, `.bin` 37,112 B, diff 540,489 B, nor_gl 499,193 B, arm 452,527 B. All sizes match the API

## Pipeline
- Scene: Blender's untouched factory scene (Camera, Cube, Light, no .blend) → factory Cube removed (rule 6 exception). Camera and Light kept
- Import: 724 faces / 724 tris, 1,024 verts, bbox 0.432 × 0.540 × 0.956 m (scale correct, no conversion needed)
- Rename: `painted_wooden_chair_01` → `SM_FarmhouseChair` / `SM_FarmhouseChair_Mesh`; material → `M_Wood_PaintedFarmhouse`; images → `T_FarmhouseChair_D`, `_N`, `_ORM`
- Cleanup: 1,024 → 410 verts (614 merged), 724 → 724 faces
  - Merge by distance 0.0001 **with `use_sharp_edge_from_normals=True`** (193 sharp edges marked)
  - **Defect found and fixed:** a plain merge (no sharp option) destroyed the source's custom split normals. The result was faceted streaks across the seat planks and back splat, while every count still passed (0 fused, 0 open edges). Detected by a pixel A/B against a fresh import of the source, same camera: 53,506 px differed. A Data Transfer of custom normals did not fix it (129,628 px). Merging with the sharp-edges option did: **0 px**
  - Recalc normals: **not applied blind.** On the source it shifted shading (10,547 px), and a bmesh winding check found 0 faces to flip, so the authored normals were kept. Rule 10 is satisfied by that verification, not by running the operator (deviation from the checklist, stated here)
  - Loose: 0. Degenerate: none. Manifold: 0 fused edges, 0 open edges
  - Transforms applied. Origin set to the centre of the base (shift of −0.0015, +0.0307, −0.0007 m)
  - Orphans purged. No empty slots, no missing textures
- Poly check: 724 tris, **below** the balanced prop range (1.5-5K). Alert only (rule 4): the source is authored low-poly and reads fine at prop distance. No decimation proposed
- Texturing: skipped — PolyHaven PBR set (baseColor, normal GL, ARM → metallic/roughness), Principled BSDF, albedo avg ≈ (0.71, 0.68, 0.64) = cream paint
- Material audit (rule 19): clean — no procedural nodes, no Color Ramp, textures ≤ 2048. The source has no occlusion map and is doubleSided, same as the export
- Optimize (auto preset, balanced): no resize (2048 = tier cap) → `gltf-transform webp --quality 90` → `gltf-transform draco`. 1.53 MB → 1.03 MB (−33%). Clients need a Draco decoder, and the file requires `EXT_texture_webp`
- Export verification: `_final.glb` re-imported (Draco + WebP decode) → 724 tris, bbox 0.432 × 0.540 × 0.956 m. Pixel A/B vs source: 428 / 810,000 px over 8/255 (0.05%), mean 0.16/255 (compression noise)
- Screenshots (viewport OpenGL render — the Blender splash screen covers the area screenshot): import, cleanup front/back, final front/back, A/B close-ups

## Files
- `farmhouse-chair_original.glb` — 1,533,728 B (Blender export, JPEG textures, before optimize)
- `farmhouse-chair_final.glb` — 1,029,828 B (WebP + Draco)
- `farmhouse-chair.blend` — 1,590,976 B (textures packed)
- `farmhouse-chair_log.md`

## Licenses
- Painted Wooden Chair 01 — CC0 1.0 (public domain), author Kuutti Siitonen. No attribution required
- Source: Poly Haven (polyhaven.com), via the public API (ToS 2.5 credit; User-Agent `blender-kiln`, ToS 2.4)

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 20:20
