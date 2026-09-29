# Sci-fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Blender: 5.0.1, blender-mcp addon 1.7 (protocol 11, up to date)

## Brief
Sci-fi supply crate with reinforced corners and a handle on each side.
Interpretation: one handle on each short end (±X), the classic crate layout.

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python / bmesh), 3 separate parts
  - SM_SupplyCrate_Body: 0.80 x 0.55 x 0.50 m box, 12 mm bevel (2 seg), recessed 12 mm panel on every face
  - SM_SupplyCrate_Corners: 8 closed corner caps, 13 cm, 12 mm proud, chamfered outer vertex
  - SM_SupplyCrate_Handles: 2 tubular grips (Ø26 mm, 28 cm span) on standoffs + mounting plates, one per short end

## Pipeline
- Import: implicit (scripted). 964 tris, bbox 0.936 x 0.574 x 0.524 m (handles add 6.8 cm per end), origin at centre of base, base at z=0
- Cleanup: 964 -> 964 tris. Merge by distance 0 verts, loose 0, degenerate dissolve, normals recalculated, non-manifold edges 0, transforms identity/applied
- Poly budget: 964 tris, under the balanced prop range (1.5-5K). Soft range, not blocking
- UVs: box projection in world metres / texture real-world size (body /2.5 m, steel /2.0 m) -> life-size tiling, Mapping scale 1
- Texturing (PolyHaven via download_polyhaven_asset + set_texture, 1k jpg):
  - Body: blue_metal_plate -> M_Metal_PaintedBlue (Diffuse, Rough, nor_gl, Displacement)
  - Corners + Handles: metal_plate_02 -> M_Metal_WornSteel (Diffuse, Rough, Metal, nor_gl, Displacement), shared material
  - Backface culling on (closed meshes -> doubleSided false in glTF)
- Material export audit: all Principled BSDF, no procedural nodes, no color ramps, all textures ≤2048.
  Warning: the Displacement node is not exported to glTF. The normal map carries the surface detail.
- Optimize: not run yet (interactive step, awaiting choice)
- Export: GLB, 4.13 MB (4,128,884 bytes), 964 tris, 3 meshes, 2 materials, 6 images; export_apply=False, no Draco.
  Verified with gltf-transform inspect.

## Files (compact)
- sci-fi-supply-crate_final.glb
- sci-fi-supply-crate.blend (textures packed)
- sci-fi-supply-crate_log.md
- No separate _original.glb: the asset was scripted, so the .blend is the source of truth

## Licenses
- blue_metal_plate — Rob Tuytel, Poly Haven, CC0 — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 — Rob Tuytel, Poly Haven, CC0 — https://polyhaven.com/a/metal_plate_02
- Geometry: original, scripted in this session

## Checkpoint
- Last completed step: EXPORT (OPTIMIZE pending user choice)
- Timestamp: 2026-09-29 15:08
