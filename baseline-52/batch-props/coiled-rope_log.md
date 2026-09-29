# Coiled Rope — Production Log

## Source Brief
"Stylized coiled hemp rope lying flat on the floor, spiral coil with a loose trailing end" — batch blacksmith-workshop

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: lightweight (prop range 300-1.5K tris)
- Style: stylized
- Mode: auto (batch runner)
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python, bmesh sweep along an Archimedean spiral)
- Params: rope radius 12 mm, 6 sides, twisting ring phase 0.55 rad/step (facets read as rope lay), coil r 0.035 → 0.175 m, pitch 27 mm (~5.2 turns, no self-intersection), 14-point S-curved trailing end; smooth shading

## Pipeline
- Import: implicit (scripted), 1 object SM_CoiledRope, 1,292 tris, bbox 0.40 x 0.63 x 0.024 m
- Cleanup: 1,292 → 1,292 tris; transforms applied, merge by distance (0), normals recalculated, loose removed (0), degenerate dissolve; 0 non-manifold edges (closed tube with end caps)
- Origin: first export had the origin at the coil centre, 0.14 m off the bounds centre because of the tail. Recentred mesh to bounds XY centre, base at z = 0, then re-exported _final (_original keeps the coil-centre pivot)
- Poly check: 1,292 tris — within lightweight range (upper end), no decimate
- Texturing: M_Fabric_HempRope (#b08a5a, rough 0.95)
- Material audit: all materials glTF compatible
- Optimize: preset none (skipped)
- Export: GLB, 24.4 KB, 1,292 tris, export_apply=False, no modifiers; verified with gltf-transform inspect
- Note: screenshot is loosely framed. view_selected did not zoom closer on this flat object, but the coil is legible

## Licenses
- All geometry and materials authored in-session: no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29T16:17
