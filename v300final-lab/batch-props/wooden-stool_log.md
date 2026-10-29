# Wooden Stool — Production Log

## Source Brief (batch)
"Stylized three-legged wooden blacksmith's stool: thick round seat, splayed tapered legs, a stretcher ring"
Batch: blacksmith-workshop (batch-manifest.yaml) — scene "a blacksmith's workshop", palette warm browns + iron grey.

## Config
- Type: prop (furniture)
- Target: glTF (web)
- Tier: lightweight (props 300-1.5K tris, soft)
- Style: stylized
- Mode: auto (batch runner, no prompts)
- Storage: compact
- Blender: 5.2.2 LTS, live session via the Blender Lab MCP (factory scene, no .blend loaded)

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)

## Source
- Method: scripted (Blender Python, bmesh lathe/sweep)

## Pipeline
- Brief: assumed size — seat height 0.45 m, seat Ø 0.34 m (a typical low workshop stool); 3 legs splayed to a 0.36 m footprint; 3 rungs at 0.15 m.
- Source/Import: scripted build (_scripts/build_wooden_stool.py) — 7 parts under empty SM_WoodenStool: Seat (24-seg lathe, chamfered), Leg_01-03 (10-seg tapered rods, feet sawn flat at z=0 after a first build sat 3.6 mm below the floor), Rung_01-03 (8-seg). 408 tris, 218 verts, 0.350 × 0.369 × 0.450 m (world-space vertices), min z 0.000. Factory Cube removed before building (rule 6); factory Camera and Light kept, not exported. Framed screenshot (3/4 view): OK.

- Cleanup: 408 → 408 tris (7 parts). Transforms identity (built in place); weld 1e-4: 0 vertices merged; normals recalculated outward; 0 loose; degenerate dissolve: none; manifold: 0 fused, 0 open edges on every part; origin at the seat axis on the floor (the tripod's box centre sits 14 mm toward +Y — the asymmetric leg layout, expected); names SM_WoodenStool_* / *_Mesh; 0 orphans; 0 empty material slots. Poly budget: 408 tris, inside lightweight (300-1.5K). No decimation.

- Texturing: skipped (scripted, palette materials assigned at build) — zones: Seat → M_Wood_Warm (#8a5a32, rough 0.75); Legs + Rungs → M_Wood_Dark (#5a3820, rough 0.8). Principled BSDF values only, no image textures. UVs: Smart UV Project per part (no texture uses them; uv_check not needed). Looked from two opposite three-quarters (front-left, back-right): OK.

- Optimize: preset resize-1k-webp-draco as separate gltf-transform steps (resize and webp are no-ops: no image textures), validator exit 0 after each; 28,808 B (_original) → 9,396 B (web/_final, Draco) = −67 %. Draco needs a decoder on the client. Preview: wooden-stool_preview.glb = copy of _original (no Draco, no WebP — opens in macOS Quick Look); extensionsUsed [] checked. Stage files kept in _stages/ (listed in hand-over).

- Export: glTF/GLB, export_apply=False, material audit passed (2 Principled BSDF materials, no procedural nodes). web/wooden-stool_final.glb 9.2 KB, 408 tris, 7 meshes. .blend saved (wooden-stool.blend, save_version 0). Final look: tools/review_renders.py on the final GLB → review/ (q1, q3, top): stool reads correctly, legs on the floor, rungs enter the legs.
## Licenses
- All geometry and materials authored in this session (scripted): no third-party resources. Yours to license.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-22T14:42:14+02:00
