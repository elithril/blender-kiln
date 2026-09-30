# Coiled Rope — Production Log

## Source Brief
Batch "blacksmith-workshop": a blacksmith's workshop. Asset brief: "Thick hemp rope coiled flat on the floor in stacked
turns, one loose end trailing, ~0.40 m across". Palette: warm browns and iron grey.

## Config
- Type: prop
- Target: glTF (web)
- Tier: lightweight (prop 300-1.5K tris, soft)
- Style: stylized
- Mode: auto (batch runner)
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted)

## Source
- Method: scripted. A path was built in Python: layer 1 spirals out on the floor (r 0.05 → 0.19 m, 3.9 turns),
  then climbs for one turn into layer 1's grooves. Layer 2 spirals inward (r 0.172 → 0.09 m). The loose end lifts over the coil,
  drops to the floor and trails out (Catmull-Rom). A 6-sided section was swept along it with parallel-transport frames, twisted one facet
  per 11 cm to suggest strands. The rope is 36 mm thick and 6.34 m long.
- Single object `SM_CoiledRope` / `SM_CoiledRope_Mesh` (one continuous rope, so one part).

## Pipeline
- Scene: cleared by removing the previous asset's datablocks. Camera and Light kept, not exported.
- Import: implicit (scripted). 1,388 tris. bbox 0.397 × 0.665 × 0.106 m: the coil is 0.40 m across as briefed,
  and the trailing end carries the long axis to 0.665 m. Origin at the bbox base centre, which includes the tail, so it sits
  ~0.13 m off the coil centre.
- Cleanup: 1,388 → 1,388 tris. Merge 0, loose 0, degenerate dissolve, normals recalculated, fused edges 0, open edges 0 (capped).
  The mesh is not welded to itself anywhere. In the climb from layer 1 to layer 2, the tube passes up to ~5 mm into the turn below it
  (estimated from the path geometry, not measured on the mesh). It is not visible in the viewport.
- Poly check: 1,388 tris, inside lightweight range (upper end) → no decimation.
- Texturing: skipped. M_Fabric_Hemp (#A7804F, rough 0.95) was assigned when the mesh was built. Flat shading, kept on purpose so the twist reads.
- Material export audit (rule 19): all glTF compatible.
- Optimize: resize-1k-webp-draco (resize and webp are no-ops, since there are no textures). 74.2 KB → 7.1 KB (−90%). The client needs a Draco decoder.
- Export: GLB, 7.1 KB, 1,388 tris. gltf-transform validate: 0 errors, 0 warnings.
- Screenshots: two angles checked (40° from above, 12° low side), saved coiled-rope_screenshot.png.

## Licenses
- All geometry and materials authored in-session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30
