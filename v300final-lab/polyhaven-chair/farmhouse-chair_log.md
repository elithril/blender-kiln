# Farmhouse Chair — Production Log

## Config
- Type: prop (furniture)
- Target: glTF (web/)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D Backend: none (marketplace only — user excluded AI generation and Sketchfab)
- Live view: off (auto bench run, nobody to watch)
- Output: /private/tmp/kiln-bench/v300final-lab/polyhaven-chair/work/generated-assets/farmhouse-chair
- Environment: Blender 5.2.2 LTS, official Blender Lab MCP (no marketplace tools → PolyHaven public API from Bash)

## Reference Image
- Path: none
- Brief enrichment: N/A
- Visual comparison: N/A

## Prompts (copy-paste ready)
- None (no AI generation)

## Source
- Method: marketplace (PolyHaven only, per brief)
- Search: api.polyhaven.com/assets?type=models&categories=furniture, 25 seat candidates; shortlist:
  painted_wooden_chair_01 (724 tris, tags farmhouse/kitchen/dining), painted_wooden_chair_02 (1,246 tris, 1.26 m, farmhouse),
  gallinera_chair (11,560), WoodenChair_01 (19,992, gothic/victorian)
- Picked (auto mode): painted_wooden_chair_01 — https://polyhaven.com/a/painted_wooden_chair_01
  "distressed white farmhouse piece with slatted seat, decorative back splat, square legs and simple stretchers", author Kuutti Siitonen
- Files: gltf 1k (diff, nor_gl, arm 1K jpg + .bin), md5 of all 5 files verified against the API
- Poly note: 724 tris is BELOW the balanced prop range (1.5-5K) — alert only (rule 4); a chair this simple reads fine at 724, the 1K PBR maps carry the detail

## Pipeline
- Brief: realistic wooden chair, farmhouse kitchen, prop, glTF, balanced, auto, compact, PolyHaven only
- Import: 724 faces (all tris), 1,024 verts, 1 material, 1 UV map; world bbox (vertices) 0.432 x 0.540 x 0.956 m, z min -0.0007 (on ground); matches PolyHaven 432x540x956 mm. Factory Cube removed (untouched factory scene, rule 6). Renamed SM_FarmhouseChair / SM_FarmhouseChair_Mesh, M_Wood_PaintedWhite, images T_FarmhouseChair_*. Front = -Y. Looked (material, 3/4 front): textures read correctly
- Cleanup: 724 → 724 faces (tris 724). Transforms applied; merge by distance 1e-4 m with corner normals kept: 1,024 → 410 verts (614 merged), bent corners 16.8% → 16.8%; normals made consistent; 0 loose; 0 degenerate; manifold: 0 fused, 0 open (closed after weld; 1,032 open before = split UV/normal seams). Origin moved to centre of base (mesh shift -0.0015, +0.0307, -0.0007 m), z min 0. Dims 0.432 x 0.540 x 0.957 m. Orphans purged. 1 slot, no missing texture. Poly: 724 tris, below balanced prop range — kept (rule 4). Looked front 3/4 and back 3/4 (material)
- Texturing: skipped — asset ships with its PolyHaven PBR set (diff, nor_gl, arm 1K) on M_Wood_PaintedWhite. Importer had dropped the ARM red (occlusion) channel: reconnected via a 'glTF Material Output' group → occlusionTexture exported (shares the ARM image). uv_check on final: 0 FAIL, 0 WARN, used 85.6 %, overlap/stretch/collapsed/flipped 0.0 %
- Optimize: gltf-transform resize 1024 (no-op, already 1K) → webp q90 → draco (pos 14, nor 10, uv 12), separate steps (rule 20); no simplify. 494,048 B → 360,472 B (-27 %); 724 tris unchanged. Preview = copy of _original (extensionsUsed: none, JPEG) for Quick Look. Final rendered headless (review_renders, colour q1 + q3): intact
- Export: glTF/GLB, web/farmhouse-chair_final.glb 360 KB, 724 tris, 1 mesh, 1 material (baseColor, normal, occlusion, metallicRoughness, WebP 1024), Draco + WebP (client needs a Draco decoder). Material audit: 0 procedural nodes, Principled BSDF. export_apply=False, Y-up. Origin at base centre, bbox 0.432 x 0.540 x 0.956 m
- Files: farmhouse-chair.blend, farmhouse-chair_original.glb, farmhouse-chair_preview.glb, web/farmhouse-chair_final.glb, src/ (PolyHaven download). Intermediates kept for the user to decide (auto mode, compact): opt/farmhouse-chair_resized.glb, opt/farmhouse-chair_webp.glb, opt/review/*.png

## Licenses
- painted_wooden_chair_01 (model + textures): CC0 1.0, by Kuutti Siitonen. Source: Poly Haven (polyhaven.com), via the public API (ToS 2.5 credit)

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22 14:31
