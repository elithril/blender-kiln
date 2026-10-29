# Sci-fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (web GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted (brief: "model it by script")
- Live view: on (Kiln Studio)
- Environment: macOS, Blender 5.2.2 LTS via the official Blender Lab MCP (no marketplace tools → PolyHaven public API from Bash); gltf-transform + gltfpack present
- Output: /private/tmp/kiln-bench/v300final-lab/pbr-crate/work/generated-assets/scifi-supply-crate

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Brief (confirmed, auto mode — assumptions stated)
- Sci-fi supply crate, realistic, about 0.90 m long × 0.60 m deep × 0.55 m tall (assumed usual size of a two-person crate)
- Chamfered steel body with a lid seam, inset side panels
- Reinforced corners: 8 bolted steel corner caps wrapping each corner
- A handle on each side: read as one recessed bar handle on each end (±X) — the two sides a crate is carried by
- Sci-fi details: two front latches, a small emissive status strip, four rubber feet
- Textures: PolyHaven CC0 PBR — painted metal body, worn steel corners/handles, rubber grips/feet

## Prompts (copy-paste ready)
- N/A (scripted, no AI)

## Source
- Method: scripted (Blender Python)

## Pipeline
- CONFIG/BRIEF: brief captured from the command line, auto mode, assumptions above
- SOURCE: create from scratch, scripted (the brief asks for it; hard-surface prop = clean separated parts). Script: scripts/build_crate.py

- Import (scripted, built in place): removed the factory-startup Cube (untouched factory scene, rule 6). 4 objects SM_Crate_Body/Frame/Rubber/StatusLight in collection SM_ScifiSupplyCrate, 2,066 faces / 4,196 tris, bbox 1.008 × 0.603 × 0.571 m (handles included; body 0.89 × 0.59 × 0.57 m), stands on z=0, origin at base centre, transforms identity. v1 recessed panels too shallow to read (8.6° slope smoothed) → v2 two-step inset with a 45° step. Viewed front-left and back-right (solid + cavity).
- Cleanup: 2,066 → 2,066 faces (4,196 tris, balanced prop 1.5-5K: in range). Weld 1e-4 m keeping shading per object, normals out, loose 0, degenerate 0. First weld fused 96 edges (handle elbow spheres coincident with bar rings) → elbow radius 11.5 mm in the script, rebuilt: fused 0, open 0, loose 0 on all 4 meshes. Transforms identity, origin base centre, meshes renamed SM_*_Mesh, orphans purged. Script: scripts/cleanup.py. Handle close-up viewed.
- Texturing (Strategy 1, PolyHaven via public API — the Lab MCP has no PolyHaven tools; maps 1k JPG, graph hand-built: diffuse sRGB → Base Color, ARM Non-Color → G roughness / B metallic / R occlusion via glTF Material Output, nor_gl → Normal Map). UVs: world-scale box projection per face (scripts/texture.py). Zones: [body base+lid: green_metal_rust as M_Metal_PaintedOlive, 1.0 m/tile], [corner caps, posts, bolts, handles, latches, light housing: metal_plate_02 as M_Metal_WornSteel, 0.35 m/tile — 0.7 m read as wood grain, tightened], [lid seal, grips, feet: rubber_tiles as M_Rubber_Black, 2.0 m/tile so tile seams don't land on small parts], [status strip: M_Light_Cyan, values only, emissive 4]. Thumbnails checked against blue_metal_plate, painted_metal_shutter, metal_plate, container_side, rusty_painted_metal.
- Material audit (map level, _original.glb): all 3 PBR materials fill baseColorTexture + metallicRoughnessTexture + normalTexture + occlusionTexture; emissive via KHR_materials_emissive_strength. Displacement not downloaded (no glTF slot). Exporter warning "more than one tex image used for a texture" = ORM from one image, single shared sampler: no loss.
- UV check (checks/uv_check.json): 0 FAIL, 4 WARN — overlap / outside 0-1 by design (tiled, no bake); collapsed 0 %, stretch 0 %, flipped 0 %.
- Looked at: material preview front-left, back-right (opposite), corner close-up.
- Rig/animate: skipped (static prop)
- Optimize (auto, rule 20 separate steps): gltf-transform resize 1024 → webp q90 → draco. 3.99 MB (_original) → 1.08 MB → 963 KB → 797 KB web/scifi-supply-crate_final.glb (−80 %). Geometry untouched. Draco needs a decoder on the client. _preview.glb = copy of _original (no Draco, no WebP: extensionsUsed only KHR_materials_emissive_strength). Final re-rendered headless (review/final_colour_q1/q3/under.png): textures and emissive intact.
- Export: glTF/GLB. web/scifi-supply-crate_final.glb 797 KB, 4,196 tris / 2,066 faces, 4 meshes, 4 materials; export_apply=False (no modifiers, nothing procedural). Root: _original.glb 3.99 MB, _preview.glb 3.99 MB, .blend (textures linked from textures/), log. Studio checks: all ok, no WARN. Geometry is the session's own script (scripts/build_crate.py, cleanup.py, texture.py).
- Intermediates kept (compact storage, auto mode — nobody to confirm a deletion): optimize/ (_resized.glb 1.08 MB, _webp.glb 963 KB), textures/thumbs + textures/api (search material), review/, checks/.

## Licenses
- green_metal_rust, metal_plate_02, rubber_tiles: CC0 — Source: Poly Haven (polyhaven.com), via the public API (https://polyhaven.com/a/green_metal_rust, /a/metal_plate_02, /a/rubber_tiles)

## Checkpoint
- Last completed step: [7] EXPORT
- Timestamp: 2026-10-22 14:30
