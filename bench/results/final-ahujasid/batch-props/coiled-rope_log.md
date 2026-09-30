# Coiled Rope — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized coil of thick hemp rope lying flat, a few stacked loops, one loose end"

## Config
- Type: prop
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
- Method: scripted (Blender Python bmesh sweep along a path, Blender 5.2.2 LTS)

## Pipeline
- Import: implicit (scripted). 1 object SM_CoiledRope: 9-sided tube (Ø 44 mm) swept along a 3.5-turn helix (radius 0.15 → 0.13 m, loops stacked) plus a 0.36 m loose end curving out on the floor. 3-lobe profile advancing one vertex per ring suggests the strand twist. Bbox 0.46 × 0.55 × 0.19 m
- Cleanup: 1,418 → 1,418 tris. Merge by distance (0), recalc normals, remove loose (0), degenerate dissolve, manifold check (fused 0, open 0 — both ends capped). Origin moved to centre of base bounds (lowest vertex was 2 mm below floor after the twist was strengthened — corrected to z = 0). Smooth shading
- Poly budget: 1,418 tris — inside the lightweight prop range (300-1.5K), near its top
- Texturing: skipped — procedural M_Fabric_Hemp (#a88457, roughness 0.95) assigned at creation
- Material export audit: clean
- Optimize: resize-1k-webp-draco — no textures, only Draco had effect. 26,676 B → 6,140 B (−77%). Client needs a Draco decoder.
- Export: GLB, coiled-rope_final.glb, 6,140 B, 1,418 tris
- Screenshots: two opposite angles checked; coiled-rope_screenshot.png saved
- Known limitation: the strand twist reads as a gentle lumpiness at this density, not as distinct strands. A normal map baked from a denser twist would sharpen it without adding triangles

## Licenses
- All geometry and materials created from scratch in this session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30T19:50:52Z
- Duration (measured): 94s
