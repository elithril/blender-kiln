# Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB, web)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact

## Reference Image
- Path: none (source is a generated GLB)
- Visual comparison: close match. Front, back, three-quarter and close-up renders of the low-poly compared against the original

## Source
- Method: repair of a user-provided generated GLB (TRELLIS output, trimesh writer)
- Input: refs/trellis/lantern_trellis.glb → copied unchanged to lantern_original.glb
- No marketplace and no new AI generation, as the brief required

## Pipeline
- Import: 191,520 tris, 194,358 verts, 11.4 MB, bbox 0.42 × 0.34 × 1.00 m (unit-normalized), 1 material, 2 × 1024 PNG (baseColor, metallicRoughness)
- Diagnosis: 13,611 fused edges (>2 faces, from zero-thickness folded sheets), 10,234 open edges, UV-split vertices (194K → 84K after an exact weld). Blender's Collapse decimate stalled at 74.5K tris on it
- Factory Cube removed (untouched startup scene)
- Thin parts (rule: never decimate): the bail (Ø ≈ 10 mm at source scale) and the top hanger loop (Ø ≈ 8 mm) were rebuilt as round-bevel curves along centrelines measured from the source vertices. The bail ends enter the side tubes. Their faces were removed from the body before decimation
- Body: exact weld, then degenerate dissolve, then Solidify 3 mm and voxel remesh 1.5 mm → one closed manifold shell (0 fused, 0 open). Specks under 50 verts removed (144 verts). Collapse decimate to 5,600 tris
- Join body + wires → 6,940 tris, 3,290 verts. Weld 1e-5 (12 merged), normals recalculated, smooth by angle 50°
- Final topology: 0 fused, 0 open, 0 loose
- UV: Smart UV Project (60°) + pack, margin 0.004
- Bake (Cycles, selected→active, cage 6 mm, max ray 30 mm) from the original mesh at 1024²: base colour (emission), metallic/roughness (emission of the original packed map, G = rough, B = metal), tangent normal. 32% of normal-map texels sampled back faces of the generator's double-sided sheets and were flipped to face outward
- Scale: uniformly ×0.36 → 0.152 × 0.121 × 0.358 m (assumption: the generator normalizes to 1 m; a real hurricane lantern is ~0.36 m with the bail up). Origin at the centre of the base, transforms applied
- Material: M_Lantern, Principled BSDF + 3 image textures, no procedural nodes (rule 19 audit passed), single-sided
- Optimize: gltf-transform resize 1024 → webp q90 → draco (individual steps, rule 20). 3.88 MB (raw export) → 0.91 MB
- Export: lantern_final.glb, 0.91 MB, 6,940 tris, Draco + WebP, tangents included. gltf-transform validate: 0 errors (only infos: Draco not validated, 1 unused bufferView)
- Overall: 11.4 MB / 191,520 tris → 0.91 MB / 6,940 tris (−92% size, −96.4% tris)

## Poly budget
- 6,940 tris vs balanced top 5,000: 1.39×, inside the 2× soft margin. 1,340 of them are the two wire curves, 5,600 the body

## Files (compact)
- lantern_original.glb: untouched source
- lantern_final.glb: game-ready web asset
- lantern.blend: SM_Lantern (final), HP_Lantern_BakeSource (original mesh, hidden), CRV_Lantern_Bail / CRV_Lantern_Hanger (editable curves, hidden), textures packed
- lantern_log.md

## Notes for the client
- Draco needs a decoder at runtime (three.js: DRACOLoader)
- WebP textures need a browser with WebP support (all current ones)

## Licenses
- Source mesh: user-provided TRELLIS output (licence as per the user's generation terms; TRELLIS code is MIT)
- No third-party textures or assets added

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21 15:14
