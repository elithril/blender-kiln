# Wooden Stool — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized three-legged wooden workshop stool, round thick seat, splayed legs, one iron band ring brace"

## Config
- Type: prop (furniture)
- Target: glTF (gltf-web)
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
- Method: scripted (Blender Python, bmesh), shared helpers in ../kiln_helpers.py
- Parts: SM_WoodenStool_Seat (M_Wood), SM_WoodenStool_Legs (M_WoodDark, 3 splayed legs, flat feet, through-tenons 2 mm proud of the seat top), SM_WoodenStool_Brace (M_Iron, ring on the legs' centre-line at 16 cm)

## Pipeline
- Scene: factory scene detected (Cube, Camera, Light, unsaved) → factory Cube removed before building; Camera/Light kept, not exported
- Import: implicit (scripted) — bbox 0.354 × 0.357 × 0.457 m, base at z=0, origin at centre of base
- Cleanup: 528 → 528 tris; transforms applied, 0 vertices merged, normals recalculated, 0 loose, 0 fused edges, 0 non-manifold edges
- Poly budget: 528 tris — inside lightweight prop range (Seat 156, Legs 84, Brace 288)
- Texturing: skipped — procedural palette materials assigned at creation (flat Principled BSDF values)
- Material audit (rule 19): OK — no procedural nodes
- Optimize: resize 1024 → webp q90 → draco (individual steps). No textures, so resize/webp are no-ops. 19.4 KB → 4.9 KB. Draco needs a decoder on the client.
- Export: GLB, 4.9 KB, 528 tris, 3 meshes, 3 materials (M_Wood, M_WoodDark, M_Iron); no UVs (flat colour materials)

## Files
- wooden-stool_original.glb, wooden-stool_final.glb, wooden-stool.blend, wooden-stool_screenshot.png, wooden-stool_log.md

## Licenses
- All geometry and materials authored in-session; no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
