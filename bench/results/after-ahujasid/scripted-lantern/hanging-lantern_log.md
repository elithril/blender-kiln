# Hanging Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.7 (protocol 11, up to date), Apple M4 Pro

## Brief
A hanging iron lantern with a glass cage and a ring on top, for a medieval inn.
Interpretation: square wrought-iron lantern — stepped base, 4 corner posts, 3 horizontal
bands, 2 vertical cage rods per face, amber glass box, overhanging plate + pyramid roof,
chimney + cap, vertical hanging ring with collar, candle on a dish with an emissive flame.

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)
- Hunyuan3D params: N/A

## Source
- Method: scripted (bmesh via execute_blender_code), no marketplace, no AI
- Scene: factory startup scene (Cube, Camera, Light, no .blend) — default Cube removed (rule 6 exception). Camera and Light left in place, not exported.

## Pipeline
- Build: 8 parts parented to empty `SM_HangingLantern` (origin = base center, Z up, front -Y)
  - Base 216 · Frame 1,120 · Glass 12 · Roof 208 · Ring 484 · CandleDish 60 · Candle 72 · Flame 100 tris
- Import: implicit (scripted). 2,272 tris, bbox 0.24 × 0.24 × 0.5435 m (get_object_info verified on Base and Ring)
- Cleanup: 2,272 → 2,272 tris. Merge by distance 0 verts, loose 0, degenerate dissolve, normals recalculated,
  fused edges (>2 faces) 0 on every part, open edges 0, transforms identity, orphans purged (2 blocks)
- UVs: bmesh `calc_uvs=True` produced NO UV layer (it only fills an existing layer) — caught during cleanup.
  Ring UVs set analytically (torus u/v); other 7 parts Smart UV Project (66°, margin 0.02). 0 zero-area UV faces.
- Texturing: skipped — scripted asset, value-only Principled materials from creation:
  M_Metal_WroughtIron (5 parts), M_Glass_Amber (alpha 0.3 → glTF BLEND), M_Wax_Candle, M_Emissive_Flame (strength 6 → KHR_materials_emissive_strength)
- Material audit (rule 19): all 4 materials Principled-only, no procedural nodes → OK
- Optimize: no textures (resize/WebP not applicable) → `gltf-transform draco` only: 147.57 KB → 19.8 KB (−86.6%). Requires a Draco decoder client-side.
- Export: GLB, export_apply=False, Y-up. Final 19.8 KB, 2,272 tris, 8 meshes.
  Round-trip verified: headless re-import of _final.glb → 8 meshes, 2,272 tris, same bbox, 4 materials.

## Files
- hanging-lantern_original.glb (147.6 KB)
- hanging-lantern_final.glb (19.8 KB, Draco)
- hanging-lantern.blend (146.9 KB)
- hanging-lantern_log.md

## Licenses
- All geometry and materials authored in this session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 19:51
