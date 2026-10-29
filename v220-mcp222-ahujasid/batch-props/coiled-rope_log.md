# Coiled Rope — Production Log

## Source Brief
- Batch: blacksmith-workshop — "A blacksmith's workshop"
- Asset brief: "Stylized coiled hemp rope lying flat on the floor, a few stacked loops, loose end trailing"

## Config
- Type: prop
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
- Part: SM_CoiledRope (M_Rope), one swept tube, 26 mm diameter, 4.56 m long: short tucked start tail on the floor, 4 hand-coiled loops (radius 0.15 m with ±1 cm wobble, constant pitch 27 mm), free end that runs level until it clears the stack, then eases down to the floor and trails in an S curve. Ends taper to 82%.

## Pipeline
- Scene cleared between assets by removing datablocks (no read_homefile)
- Import: implicit (scripted) — bbox 0.734 × 0.445 × 0.134 m (coil ≈ 0.33 m Ø), base at z=0, origin at the coil's centre of base
- Iteration 1: free end kinked where it dropped off the stack → rebuilt as a single bezier that stays level until clear of the coil
- Iteration 2: BVH self-intersection check found 370 overlapping face pairs (flattening the top loop squeezed the loops below 2r apart) → rebuilt with a constant-pitch helix; re-check 0 overlapping pairs
- Cleanup: 2,092 → 2,092 tris; transforms applied, 0 merged, normals recalculated, 0 loose, 0 fused, 0 non-manifold
- Poly budget: 2,092 tris — ⚠️ above the lightweight prop range (1.5K), under 2× (3K): kept per soft-range rule. All of it is the 8-sided round section along 4.56 m of rope (131 rings × 8 × 2). 6 sides would bring it to ~1.55K at the cost of a visibly polygonal silhouette.
- Texturing: skipped — procedural palette material (flat hemp tan). No twisted-strand detail: that would need a baked normal map or ~5× the triangles; noted for a balanced-tier redo.
- Material audit (rule 19): OK
- Optimize: resize 1024 → webp q90 → draco. No textures. 37.9 KB → 7.8 KB. Draco needs a decoder on the client.
- Export: GLB, 7.8 KB, 2,092 tris, 1 mesh, 1 material (M_Rope); no UVs

## Files
- coiled-rope_original.glb, coiled-rope_final.glb, coiled-rope.blend, coiled-rope_screenshot.png, coiled-rope_log.md

## Licenses
- All geometry and materials authored in-session; no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
