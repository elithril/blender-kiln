# Painted Wooden Chair — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop/furniture 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Brief: "A realistic wooden chair for a farmhouse kitchen." Source restricted to PolyHaven — no AI generation, no Sketchfab.

## Environment
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 13, up to date), telemetry off
- PolyHaven integration: enabled
- Scene at start: untouched factory scene (Cube, Camera, Light, no .blend loaded) → factory Cube removed before import (rule 6 exception). Orphan purges then removed the factory `Material`, `Dots Stroke` and Cube mesh data-blocks.

## Reference Image
- Path: none
- Brief enrichment: N/A
- Visual comparison: N/A

## Prompts (copy-paste ready)
- None — marketplace asset, no generation.

## Source
- Method: marketplace (PolyHaven, via the blender-mcp integration)
- Search: "wooden kitchen chair farmhouse", models, 10 results. Picked #1.
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_01 — "Painted Wooden Chair 01" by Kuutti Siitonen
- Why: tagged farmhouse / kitchen / dining; distressed white-painted wood chair with slatted seat, decorative back splat, square legs and stretchers; real-world size 0.43 × 0.54 × 0.96 m.
- Download: 1k textures (web/glTF cap), imported from PolyHaven's .blend

## Pipeline
- Import: 380 faces / 724 tris / 410 verts, bbox 0.432 × 0.540 × 0.956 m (1 unit = 1 m ✓). Front faces -Y ✓ (backrest verts mean y = +0.27).
  Renamed `painted_wooden_chair_01` → `SM_PaintedWoodenChair`, mesh → `SM_PaintedWoodenChair_Mesh`, material → `M_PaintedWood`.
- Cleanup: 380 → 380 faces. Diagnosis before changes: 0 doubles at 0.1 mm, 0 loose, 0 degenerate, 0 fused edges (>2 faces), 0 open edges (watertight). Merge by distance (0 removed), recalc normals (0 faces flipped), remove loose, dissolve degenerate — all no-ops. Transforms applied; origin moved to centre of base (bbox was offset 1.5 mm in X, 30 mm in Y, -0.7 mm in Z). Custom split normals kept.
- Poly budget: 724 tris is **below** the balanced range (1.5-5K). Alert only (rule 4); no action — the chair's geometry is simple boxes and the detail sits in the normal map.
- Texturing: skipped — the asset ships a full PBR set (diffuse, roughness, metallic, OpenGL normal), wired to a Principled BSDF.
- Material export audit: no procedural nodes, no Color Ramp, Principled BSDF present, identity Mapping node, textures 1024². glTF exporter packs separate metallic + roughness images into one metallicRoughness texture (its "more than one tex image" warning is that merge).
- Optimize (auto default, individual steps, rule 20): `gltf-transform resize 1024` → `webp` → `draco`. 4.20 MB → 195.5 KB (−95.3%). Geometry untouched. **Draco needs a decoder on the client.**
- Validation: `gltf-transform validate` → no errors, no warnings (info only: Draco extension not validatable, one unused bufferView). Headless re-import: 724 tris, 0.4317 × 0.5398 × 0.9565 m, 1 material, 3 textures 1024². Visual re-import in viewport: correct.
- Export: GLB, 195.5 KB, 724 tris (380 faces)

## Files (compact)
- `painted-wooden-chair_original.glb` — 4.20 MB, as imported (renamed, before cleanup)
- `painted-wooden-chair_final.glb` — 195.5 KB, WebP + Draco
- `painted-wooden-chair.blend` — 1.38 MB, textures packed
- `painted-wooden-chair_log.md` — this file
- `_clean.glb` intermediate deleted (compact mode)

## Licenses
- Painted Wooden Chair 01 (model + textures): CC0 1.0, by Kuutti Siitonen. Source: Poly Haven (polyhaven.com), via the blender-mcp PolyHaven integration. No attribution required.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30 21:32
