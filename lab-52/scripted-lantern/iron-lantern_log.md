# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Brief: "A hanging iron lantern with a glass cage and a ring on top, for a medieval inn."
- Concept art: none (scripted from brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted modeling (Blender Python via official Blender Lab MCP, Blender 5.2.2 LTS)
- HF Space: N/A
- Marketplace: N/A

## Build
Square wrought-iron lantern, 0.20 x 0.20 x 0.478 m, origin at centre of base, parts parented to empty `SM_IronLantern`:

| Object | Tris | Material |
|---|---:|---|
| SM_IronLantern_Base (stepped plinth) | 80 | M_Metal_WroughtIron |
| SM_IronLantern_Frame (4 posts, 3 bands, 8 cage bars) | 1,000 | M_Metal_WroughtIron |
| SM_IronLantern_Glass (4 panes) | 48 | M_Glass_Amber |
| SM_IronLantern_Roof (eave + pyramid) | 86 | M_Metal_WroughtIron |
| SM_IronLantern_Cap (finial) | 148 | M_Metal_WroughtIron |
| SM_IronLantern_Ring (vertical torus) | 640 | M_Metal_WroughtIron |
| SM_IronLantern_CandleHolder | 60 | M_Metal_WroughtIron |
| SM_IronLantern_Candle | 60 | M_Wax_Candle |
| SM_IronLantern_Flame | 168 | M_Emissive_Flame |

- Base, Frame, Roof: 1-segment bevel (1.2 mm) applied as a modelling step so the glTF carries it (rule 18 exports the base mesh).

## Pipeline
- Import: implicit (scripted), 2,290 tris, bbox 0.20 x 0.20 x 0.478 m
- Cleanup: merge by distance (Frame -96 verts, Roof -4 verts, others 0), recalc normals, remove loose, degenerate dissolve (none found), transforms applied (Ring rotation baked), orphans purged (3 data-blocks)
- Non-manifold: Frame 80 edges, Roof 4 edges — coincident faces where overlapping boxes meet, merged. Render-only prop, not watertight; no visible artefact in viewport.
- Poly check: 2,290 tris, inside balanced range — no decimate proposed
- Texturing: skipped — procedural Principled values only (no image textures)
  - M_Metal_WroughtIron: base (0.045, 0.042, 0.04), metallic 0.85, roughness 0.55
  - M_Glass_Amber: base (0.95, 0.62, 0.22), alpha 0.35, roughness 0.08, BLENDED → glTF alphaMode BLEND
  - M_Wax_Candle: base (0.85, 0.78, 0.62), roughness 0.6
  - M_Emissive_Flame: emission (1.0, 0.5, 0.1) strength 6 → KHR_materials_emissive_strength
- Material export audit: all 4 materials Principled-only, no procedural/Color Ramp nodes
- Optimize: not run (proposed to user; file already 92.7 kB)
- Export: GLB, 92.7 kB, 2,290 tris, export_apply=False, no Draco — verified with `gltf-transform inspect`

## Notes
- Compact storage: no separate `_original.glb` — for a scripted asset there is no imported original; the .blend holds the full build.
- Default scene Cube deleted; Camera and Light kept in the .blend, excluded from export (use_selection).
- No UVs on box/cone parts (only the torus has TEXCOORD_0) — fine for value-only materials, needed before any image texturing.

## Licenses
- All geometry and materials authored in-session: no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 16:20
