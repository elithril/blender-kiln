# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Brief: hanging iron lantern with a glass cage and a ring on top, for a medieval inn

## Reference Image
- Path: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- None — scripted modelling, no concept art, no AI generation

## Source
- Method: scripted (Blender 5.2.2 LTS Python, bmesh), blender-mcp addon 1.8
- Scripts: scripts/build_lantern.py (rebuilds the asset from scratch), scripts/cleanup_check.py
- Scene prep: removed the factory-default Cube (untouched startup scene); Camera and Light kept, not exported

## Design
- Square lantern, 0.232 × 0.232 × 0.586 m, origin at the base centre (lowest point z = 0), front -Y
- Parts (each a separate object, parented to empty SM_IronLantern):
  Base (drop finial + tray), Posts (4 corner bars), Bands (closed square rings at the bottom, middle and top),
  CageBars (2 round bars per side, outside the glass), Glass (4 panes, edges buried in posts/bands),
  Roof (lip, pyramid, chimney, cap, knob), Ring (vertical torus threaded through the knob),
  CandleDish (dish + pricket), Candle, Flame
- Hanging point: top of the ring, z ≈ 0.586 m

## Pipeline
- Import: implicit (scripted), 10 meshes + 1 empty, 4,004 tris, bbox 0.232 × 0.232 × 0.586 m
- Cleanup: merge by distance 1e-5 (0 merged), loose 0, degenerate dissolve, fused edges 0, open edges 0 on every part;
  transforms identity; normals recalculated; sharp edges from angle (no modifiers, nothing to apply)
  - Fix during cleanup: first build welded the band boxes into 12 fused (>2-face) edges → bands rebuilt as single closed rings
- Texturing: skipped (scripted, flat Principled materials assigned per part)
  - M_Metal_WroughtIron: base (0.045, 0.042, 0.040), metallic 1, roughness 0.62
  - M_Glass_Amber: base (1.0, 0.86, 0.62), alpha 0.35 (glTF alphaMode BLEND), roughness 0.1 — alpha rather than
    transmission so the candle shows in every glTF viewer
  - M_Wax_Candle: base (0.86, 0.78, 0.60), roughness 0.45
  - M_Emissive_Flame: emission (1.0, 0.55, 0.15) × 6 (KHR_materials_emissive_strength)
- Material audit (rule 19): all Principled, no procedural nodes → nothing lost on export
- Poly budget: 4,004 tris — inside balanced range. Biggest: bands 864, candle dish 664, ring 512
- Optimize: gltf-transform draco only (no textures → no resize/webp), 105.1 KB → 23.1 KB (−78%).
  Draco needs a decoder on the client (three.js DRACOLoader etc.)
- Export: GLB, iron-lantern_final.glb 23.1 KB, 4,004 tris; re-import verified (11 nodes, 4,004 faces, looks identical)

## Files
- iron-lantern_original.glb (105.1 KB, uncompressed)
- iron-lantern_final.glb (23.1 KB, Draco)
- iron-lantern.blend
- iron-lantern_log.md, scripts/

## Licenses
- All geometry and materials authored in this session — no external resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
