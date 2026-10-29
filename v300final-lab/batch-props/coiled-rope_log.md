# Coiled Rope — Production Log

## Source Brief (batch)
"Stylized coil of hemp rope lying flat on the floor, a few stacked turns and a loose end"
Batch: blacksmith-workshop (batch-manifest.yaml) — scene "a blacksmith's workshop", palette warm browns + iron grey.

## Config
- Type: prop
- Target: glTF (web)
- Tier: lightweight (props 300-1.5K tris, soft)
- Style: stylized
- Mode: auto (batch runner, no prompts)
- Storage: compact
- Blender: 5.2.2 LTS, live session via the Blender Lab MCP

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)

## Source
- Method: scripted (Blender Python, bmesh sweep)

## Pipeline
- Brief: assumed size — rope Ø 27 mm, coil Ø ~0.27 m, 4 stacked turns (~0.11 m high), loose end trailing ~0.2 m on the floor. One continuous rope; each turn flat, stepping up one diameter over its last 60°.

- Source/Import: scripted build (_scripts/build_coiled_rope.py) — 1 part SM_CoiledRope_Rope under empty SM_CoiledRope: one 8-sided tube swept along a 3.48 m path (84 samples, 18 per turn), ring phase turned 22.5° per ring with flat shading so the facets spiral like the rope's lay, tip flared 18 %. v1: the loose end left the top turn where the turn below was still climbing to that level — samples 24.9 mm apart for a 27 mm rope — and the flared tip sat 2.3 mm under the floor; v2: the end keeps climbing one step before dropping outside the coil, tip flattened at z=0 → minimum clearance 27.5 mm (≥ 27), min z 0.000. 1,344 tris, 674 verts, 0.340 × 0.470 × 0.136 m (world-space vertices; the trailing end makes the box asymmetric — origin at the coil centre on the floor). Framed screenshot (3/4): OK.

- Cleanup: 1,344 → 1,344 tris (1 part). Transforms identity; weld 1e-4: 0 merged; normals outward; 0 loose; no degenerate faces; manifold: 0 fused, 0 open edges; origin at the coil centre on the floor; names SM_CoiledRope / _Rope / _Rope_Mesh; 0 orphans; 0 empty slots. Poly budget: 1,344 tris, inside lightweight (300-1.5K, near the top: the length of rope a 4-turn coil needs). No decimation.

- Texturing: skipped (scripted, palette material assigned at build) — M_Fabric_Hemp (#b08a58, rough 0.9) on the whole rope; the lay is suggested by the twisted flat facets, no texture. Looked from two opposite three-quarters (front-left, back-right): OK.

- Optimize: preset resize-1k-webp-draco as separate gltf-transform steps (resize/webp no-ops: no image textures), validator exit 0 after each; 95,036 B (_original) → 9,856 B (web/_final, Draco) = −90 %. Draco needs a decoder on the client. Preview: coiled-rope_preview.glb = copy of _original, extensionsUsed [] checked. Stage files in _stages/.

- Export: glTF/GLB, export_apply=False, material audit passed (1 Principled BSDF material). web/coiled-rope_final.glb 9.6 KB, 1,344 tris, 1 mesh. .blend saved. Final look: review_renders on the final GLB → review/ (q1, q3, top, under): reads as a stacked rope coil, end trailing on the floor.
## Licenses
- All geometry and materials authored in this session (scripted): no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-22T14:45:44+02:00
