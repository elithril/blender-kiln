# Farmhouse Chair — Production Log

## Config
- Type: prop (furniture)
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Output: /private/tmp/kiln-bench/v220-mcp222-ahujasid/polyhaven-chair/work/generated-assets/farmhouse-chair
- Environment: Blender 5.2.2 LTS, MCP addon 1.8 (up to date, protocol 14); PolyHaven on, Sketchfab/Poly Pizza off, all generators off

## Reference Image
- Path: none
- Brief enrichment: N/A
- Visual comparison: N/A

## Prompts (copy-paste ready)
- None: the user restricted sourcing to PolyHaven (no AI generation, no Sketchfab)

## Source
- Method: marketplace
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_01 (Painted Wooden Chair 01, Kuutti Siitonen)
- Search "wooden chair" (models): the pick is tagged farmhouse / kitchen / dining, a distressed white
  painted chair with a slatted seat, decorative back splat, square legs and stretchers.
  Runner-up painted_wooden_chair_02 (also tagged farmhouse) was passed over because it lists 1.26 m tall.
- Resolution downloaded: 1k (matches the 1024 web cap)

## Pipeline
- Scene: untouched factory scene; default Cube removed (rule 6 exception). Camera and Light kept.
- Import: 380 faces / 724 tris, 410 verts, bbox 0.432 x 0.540 x 0.956 m (true scale, no rescale needed)
- Rename: painted_wooden_chair_01 → SM_FarmhouseChair / SM_FarmhouseChair_Mesh;
  material → M_Wood_PaintedWhite_Worn; images → T_FarmhouseChair_{D,M,N,R}
- Cleanup: 380 → 380 faces. Doubles @1e-4: 0. Loose verts/edges: 0. Degenerate faces: 0.
  Open edges: 0, fused (>2 faces) edges: 0. Normals recalculated: 0 faces flipped.
  Transforms already identity. Origin moved to base centre (geometry offset by +0.0015, −0.0307, +0.0007 m). Orphans purged.
- Poly check: 724 tris, below the balanced range (1.5-5K). Soft range, no action: a square-legged
  chair needs no more; surface detail is carried by the PBR textures.
- Texturing: skipped. The asset ships a PolyHaven PBR set (diffuse, roughness, metallic, GL normal).
  The metallic map is entirely 0 (painted wood).
- Material export audit: no procedural nodes, no Color Ramp, Principled BSDF present. Passed.
- Optimize (auto default, rule 20 individual steps): gltf-transform resize 1024 → webp → draco.
  4.20 MB → 195 KB (−95.3%). Geometry untouched (724 tris). Draco needs a decoder on the client.
- Verification: final GLB re-imported in Blender. Draco decodes, 724 tris, 3 x 1024² textures,
  bbox 0.432 x 0.540 x 0.956 m, looks identical from front and back.
- Export: GLB, farmhouse-chair_final.glb, 195,484 bytes, 724 tris, 1 mesh, 1 material (doubleSided)

## Files
- farmhouse-chair_original.glb: 4,196,664 bytes (as imported, renamed, before cleanup)
- farmhouse-chair_final.glb: 195,484 bytes (WebP + Draco)
- farmhouse-chair.blend: recovery point (textures packed)
- farmhouse-chair_log.md

## Licenses
- Painted Wooden Chair 01 (model + textures), Kuutti Siitonen / Poly Haven: CC0 1.0, no attribution required

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
