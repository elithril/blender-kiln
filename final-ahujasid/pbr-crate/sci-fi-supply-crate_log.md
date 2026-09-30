# Sci-Fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop range 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 13, up to date), PolyHaven enabled

## Brief
"A sci-fi supply crate with reinforced corners and a handle on each side."
Assumptions (auto mode, not confirmed by the user):
- Size ~0.8 x 0.55 x 0.5 m body (final bbox below)
- "a handle on each side" = one handle on each of the two short ends (±X), the usual crate layout.
  All four sides would be the alternative reading.

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no concept)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python via execute_blender_code)
- Parts (each a separate object, parented to empty `SM_SciFiCrate`):
  - `SM_SciFiCrate_Body`: bevelled shell, recessed panel on all six faces
  - `SM_SciFiCrate_Bands`: two steel bands wrapping the crate (base and lid line)
  - `SM_SciFiCrate_Corners`: 8 solid bevelled corner caps with a raised boss on each outer face
  - `SM_SciFiCrate_Handles`: U-grip (curve → mesh) + 2 mount blocks on each end
  - `SM_SciFiCrate_Details`: label plate and 2 latches on each long side
- Scene prep: factory scene detected (Cube, Camera, Light, no .blend loaded). Default Cube removed
  (rule 6 exception). Camera and Light left untouched.

## Pipeline
- Build: 4,700 tris first pass. The first corners were 3 plates per corner. Merge-by-distance welded
  the touching plates and left 80 fused edges (>2 faces), so the corners were rebuilt as one solid cap each.
- Cleanup: merge by distance, dissolve degenerate, remove loose, recalc normals on every part;
  fused edges 0, non-manifold edges 0 on all parts. Transforms are identity (built in world space).
  Origin = centre of base, base at z = 0. Sharp edges set from 35°; smooth shading elsewhere.
- UVs: box projection in world metres, scaled by 1/texture real-world size so the PolyHaven
  tiling is baked into the UVs (Mapping nodes left at 1.0, so glTF needs no texture transform)
- Texturing (PolyHaven PBR via download_polyhaven_asset + set_texture, 1k JPG):
  - Body: `blue_metal_plate` → `M_Metal_PaintedBlue` (2.5 m texture, UV x0.4)
  - Corners, bands, handles, latches/plates: `metal_plate_02` → `M_Metal_WornSteel` (2 m texture, UV x0.5)
  - Tried first and dropped: `green_metal_rust` on the body. The blue reads cleaner and more sci-fi.
    PolyHaven had no clean brushed/bare steel; `metal_plate_02` (worn, some rust) was the closest metallic.
- Material export audit: no procedural nodes, no colour ramps, all Principled BSDF, all images
  1024², colour spaces sRGB/Non-Color correct. The Displacement maps do not export to glTF
  (normal maps cover the relief).
- Final bbox: 0.987 x 0.582 x 0.524 m (X includes the handles; the corner caps span 0.824 x 0.574 m)
- Export: `sci-fi-supply-crate_original.glb`, 4.24 MB, 3,740 tris, 5 meshes, 2 materials,
  export_apply=False, no Draco
- Optimize (auto preset, individual gltf-transform 4.3.0 steps, no `optimize`):
  resize 1024 → webp q90 → draco. 4.24 MB → 0.70 MB (-83%). Geometry untouched.
  Draco needs a decoder on the client; WebP textures need EXT_texture_webp support.
- Verification: the final GLB was re-imported into Blender. 5 meshes, same face counts, both
  materials textured. Checked by screenshot, then the check import was removed.

## Files (compact)
- sci-fi-supply-crate_original.glb — 4,236,752 B
- sci-fi-supply-crate_final.glb — 704,872 B
- sci-fi-supply-crate.blend — 4,548,232 B (PolyHaven images packed)
- sci-fi-supply-crate_log.md

## Licenses
- blue_metal_plate by Rob Tuytel — CC0 — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 by Rob Tuytel — CC0 — https://polyhaven.com/a/metal_plate_02
- green_metal_rust by Rob Tuytel — CC0 — https://polyhaven.com/a/green_metal_rust (downloaded, not in final)
- Geometry: original, scripted in this session

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30 21:38
