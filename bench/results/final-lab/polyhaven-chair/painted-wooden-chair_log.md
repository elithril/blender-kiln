# Painted Wooden Chair — Production Log

## Config
- Type: prop
- Brief: realistic wooden chair for a farmhouse kitchen
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris)
- Style: realistic
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Visual comparison: N/A

## Source
- Method: marketplace (PolyHaven only, per brief — no AI, no Sketchfab)
- Access: PolyHaven public API from Bash (the Lab MCP has no PolyHaven tools), User-Agent `blender-kiln`
- Asset: Painted Wooden Chair 01 — https://polyhaven.com/a/painted_wooden_chair_01
- Author: Kuutti Siitonen
- Why this asset: its tags are `farmhouse`, `kitchen`, `dining`, `wood`, and its size is standard (0.43×0.54×0.96 m).
  Other candidates: painted_wooden_chair_02 (1,246 tris, 1.26 m tall back), gallinera_chair, WoodenChair_01 (gothic, 2.27 m).
- Download: glTF 1k (diffuse, ARM, normal GL; 1024²)

## Pipeline
- Scene: Blender factory scene (Cube/Camera/Light, no .blend) — default Cube removed (rule 6 exception)
- Import: 724 tris, 1,024 verts, bbox 0.432×0.540×0.956 m, 1 material. Scale correct (1 unit = 1 m)
- Rename: painted_wooden_chair_01 → SM_PaintedWoodenChair / SM_PaintedWoodenChair_Mesh; material → M_PaintedWood
- Cleanup: merge by distance 0.1 mm (−614 verts, the glTF split-seam duplicates → 410 verts, now watertight: 0 boundary, 0 fused edges);
  normals recalculated (max corner-normal deviation vs source 0.03°, no flips); loose 0; degenerate 0;
  origin moved to the base centre (offset −1.5 mm X, +30.7 mm Y, −0.7 mm Z); transforms applied; 3 orphan data-blocks purged
- Poly budget: 724 tris — BELOW the balanced range (1.5–5K). Not a problem for the asset; no decimation needed or proposed
- Texturing: skipped — the asset ships with PBR maps (base colour, roughness/metal, normal)
- Material audit (rule 19): Image Texture → Principled BSDF, Separate Color (G=rough, B=metal), Normal Map. No procedural nodes, nothing lost at export.
  The source glTF has no occlusion channel, so none is exported
- Optimize (auto default, individual steps, geometry untouched): gltf-transform resize 1024 → webp → draco
  494.2 KB → 219.7 KB (−56 %). Draco needs a decoder on the client (e.g. three.js DRACOLoader)
- Verification: final GLB re-imported — 724 tris, 0.432×0.540×0.957 m, 3 WebP textures at 1024² decoded; checked visually, then removed
- Export: GLB, 219.7 KB, 724 tris, Y-up

## Files
- painted-wooden-chair_original.glb — 494.2 KB (pre-optimize)
- painted-wooden-chair_final.glb — 219.7 KB (WebP + Draco)
- painted-wooden-chair.blend — textures packed
- painted-wooden-chair_log.md

## Licenses
- Painted Wooden Chair 01 (model + textures): CC0 — Source: Poly Haven (polyhaven.com), via the public API. Author Kuutti Siitonen. No attribution required; API ToS 2.5 asks for visible credit to Poly Haven.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30
