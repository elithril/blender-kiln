# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop range 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, official Blender Lab MCP (no marketplace/generation tools, not needed)

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted modeling (Blender Python via execute_blender_code)
- Scene: untouched factory scene. The default Cube was removed before building (rule 6 exception). Two orphan
  factory materials with no users ("Dots Stroke", "Material") were purged during the orphans step.
- Design: square medieval hanging lantern
  - SM_IronLantern (empty, root, origin = centre of base)
  - _Base (bevelled tray), _Posts (4 corner posts), _Glass (4 inset panes), _Bars (mid bar + band per face)
  - _TopFrame, _Roof (4-sided pyramid), _Chimney + _ChimneyCap, _Ring (vertical hanging ring)
  - _Candle + _Flame inside the cage
- Every part is its own object; nothing was joined-and-welded across parts

## Pipeline
- Import: implicit (scripted), 11 mesh parts, 1,888 tris, bbox 0.188 × 0.188 × 0.429 m
- Cleanup: 1,888 → 1,888 tris. Merge by distance (0 merged), degenerate dissolve, remove loose,
  recalc normals, fused edges 0 / open edges 0 on every part, transforms applied, orphans purged
- Texturing: skipped (scripted with materials assigned). Principled BSDF values only
  - M_Metal_WroughtIron: base (0.045, 0.040, 0.036), metallic 1.0, roughness 0.55 — base, posts, bars, frame, roof, chimney, ring
  - M_Glass_Amber: base (1.0, 0.85, 0.55), transmission 1.0, IOR 1.45, roughness 0.05 — glass panes
  - M_Wax_Candle: base (0.93, 0.86, 0.70), roughness 0.6
  - M_Flame_Emissive: emission (1.0, 0.55, 0.12), strength 6
- Material export audit: 4/4 Principled-only, no procedural nodes
- Export: GLB, export_apply=False, Y-up, no Draco at export → iron-lantern_original.glb 68.7 KB
- Optimize: no textures, so resize and WebP had nothing to do; gltf-transform draco → iron-lantern_final.glb 19.75 KB (−71%)
  - Extensions: KHR_draco_mesh_compression (required: client needs a Draco decoder),
    KHR_materials_transmission, KHR_materials_ior, KHR_materials_emissive_strength
- Verification: final GLB re-imported in a scratch scene (then discarded) — 1,888 tris, 0.188 × 0.188 × 0.429 m,
  12 nodes, 4 materials. gltf-validator was not run (npx could not resolve the executable)
- Screenshots: the Blender splash screen covered the viewport, so the rule 2 screenshots were taken with
  render.opengl of the framed viewport (two opposite angles) instead of an area screenshot

## Licenses
- All geometry and materials authored in this session — no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 20:14
