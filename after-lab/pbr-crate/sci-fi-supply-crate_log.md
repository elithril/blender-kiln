# Sci-Fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, official Blender Lab MCP (no marketplace tools → PolyHaven public API from Bash)

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted (bmesh via execute_blender_code)
- Scene: untouched factory scene — factory Cube removed (rule 6 exception); Camera and Light kept, used for the check renders, not exported
- Parts (parented to SM_SciFiCrate, origin at centre of base):
  - SM_SciFiCrate — bevelled body 0.80×0.55×0.49 m, recessed panels inset on all 6 faces
  - SM_SciFiCrate_Band — lid seam band
  - SM_SciFiCrate_CornerRails — 4 vertical edge rails
  - SM_SciFiCrate_CornerCaps — 8 corner caps (bottom ones are the feet)
  - SM_SciFiCrate_Handles — one handle per short side (±X): back plate, 2 stand-offs, 12-segment grip bar
  - SM_SciFiCrate_StatusLight — emissive strip on the front (-Y); an addition not in the brief

## Pipeline
- Import: scripted, 920 faces / 1,832 tris, bbox 0.954 × 0.582 × 0.516 m (X includes handles)
- Cleanup: 920 → 920 faces; merge by distance (0 merged), recalc normals, remove loose, degenerate dissolve; 0 fused edges, 0 open edges; transforms identity; 0 orphans
- UV: world-space box projection per face (body 1 m tile, steel parts 0.5 m tile)
- Texturing: zones [body: M_Metal_BluePlate ← blue_metal_plate; band/rails/caps/handles: M_Metal_SteelPlate ← metal_plate_02; status strip: M_Emissive_Cyan (flat values, emission 4.0)]
  - Maps 1K JPG: diff (sRGB), nor_gl (Non-Color → Normal Map), arm (Non-Color → Separate Color: G roughness, B metallic)
  - AO channel (arm R) not wired — glTF occlusion needs the glTF Material Output group; left out
  - Backface culling on (closed meshes → doubleSided false)
- Material export audit: all 3 materials Principled, no procedural nodes, no modifiers
- Optimize: gltf-transform webp → draco (individual steps, rule 20); 3.07 MB → 388 KB (-87%); no resize (1K is below balanced cap 2048); final GLB re-imported and rendered, no visible difference
- Export: GLB, 388 KB, 1,832 tris, gltf-transform validate: 0 errors. Requires EXT_texture_webp + KHR_draco_mesh_compression (client needs a Draco decoder)
- Storage: textures packed into the .blend, downloaded textures/ folder removed (compact)

## Licenses
- blue_metal_plate (Rob Tuytel): CC0 — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 (Rob Tuytel): CC0 — https://polyhaven.com/a/metal_plate_02
- Source: Poly Haven (polyhaven.com), via the public API

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 20:25
