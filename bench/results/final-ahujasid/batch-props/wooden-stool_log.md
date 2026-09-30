# Wooden Stool — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized three-legged wooden workshop stool, round thick seat, splayed legs, one iron ring brace"

## Config
- Type: prop (furniture)
- Target: glTF (web)
- Tier: lightweight (prop 300-1.5K tris)
- Style: stylized
- Mode: auto (batch runner)
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)

## Source
- Method: scripted (Blender Python, Blender 5.2.2 LTS)

## Pipeline
- Import: implicit (scripted). 5 objects: SM_WoodenStool_Seat, SM_WoodenStool_Leg_01..03, SM_WoodenStool_Brace. Bbox ~0.40 × 0.36 × 0.45 m (seat top at 0.45 m)
- Cleanup: 584 → 584 tris. Merge by distance (0 merged), recalc normals, remove loose (0), degenerate dissolve, manifold check (fused edges 0, open edges 0), transforms applied, origin at world origin = centre of base
- Texturing: skipped — procedural Principled BSDF materials assigned at creation. Seat: M_Wood_Warm (#8a5a34), legs: M_Wood_Dark (#5e3a22), brace: M_Metal_Iron (#5a5d61, metallic 1.0)
- Material export audit: clean (Principled BSDF only, no procedural nodes)
- Optimize: resize-1k-webp-draco — no textures, so only Draco had effect. 40,996 B → 8,036 B (−80%). Client needs a Draco decoder.
- Export: GLB, wooden-stool_final.glb, 8,036 B, 584 tris
- Screenshots: two opposite angles checked in viewport; wooden-stool_screenshot.png saved

## Licenses
- All geometry and materials created from scratch in this session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30T19:48:01Z
- Duration (measured): 91s
