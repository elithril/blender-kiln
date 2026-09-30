# Sci-Fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, official Blender Lab MCP (no PolyHaven MCP tools → PolyHaven public API from Bash), macOS arm64

## Brief
"A sci-fi supply crate with reinforced corners and a handle on each side." Modelled by script, textured with PolyHaven PBR.
- Assumption: "a handle on each side" = one handle on each of the two short ends (±X), the usual layout for a two-person crate.
- Assumption: size ≈ 0.93 × 0.58 × 0.55 m (body 0.80 × 0.55 × 0.50 m plus corners, handles and feet).

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted (bpy + bmesh)
- Parts (all parented to empty `SM_SciFiSupplyCrate`, origin at centre of base):
  - `SM_SciFiCrate_Body`: box with recessed panels inset on the 4 sides and the top (84 tris)
  - `SM_SciFiCrate_LidBand`: raised rim at the lid line (44 tris)
  - `SM_SciFiCrate_Corners`: 8 bevelled corner caps + 4 vertical corner posts (1,296 tris)
  - `SM_SciFiCrate_Handles`: 2 handle bars, each with 2 mount blocks, on the ±X ends (424 tris)
  - `SM_SciFiCrate_Rubber`: handle grips + 4 feet (168 tris)
  - `SM_SciFiCrate_StatusLight`: emissive strip on the front and back of the lid band (24 tris)
- The factory Cube was removed before building (untouched factory scene, rule 6 exception).

## Pipeline
- Import: implicit (scripted), 2,040 tris, bbox 0.926 × 0.580 × 0.545 m
- Cleanup: 2,040 → 2,040 tris. Merge by distance 0, loose 0, degenerate dissolve, normals recalculated. Fused edges (>2 faces) 0, open edges 0 on every part. Transforms at identity.
- UVs: box projection in world metres, scaled by each texture's real-world size (PolyHaven dimensions: blue_metal_plate 2.5 m, metal_plate 0.5 m, rubber_tiles 2.0 m). Sharp edges > 30°, smooth elsewhere.
- Texturing (Strategy 1, zones by part):
  - Body + lid band → `M_Metal_PaintedBlue` (blue_metal_plate)
  - Corners + handle bars/mounts → `M_Metal_TreadPlate` (metal_plate, diamond tread)
  - Grips + feet → `M_Rubber_Black` (rubber_tiles, metallic forced to 0)
  - Status strip → `M_Emissive_Status` (flat Principled, emission cyan ×4, exported as KHR_materials_emissive_strength)
  - Maps used per material: Diffuse, nor_gl, ARM. ARM wired as R → glTF Occlusion (via the exporter's own `glTF Material Output` group), G → Roughness, B → Metallic. AO and Displacement single maps not downloaded: displacement has no glTF slot.
  - Exported slots confirmed in the GLB: baseColor, normal, metallicRoughness and occlusion on all 3 textured materials.
  - The exporter's "More than one shader node tex image used for a texture" warning comes from the ARM image feeding both occlusion and metallicRoughness. No map was lost.
- Material audit (rule 19): no procedural nodes, all Principled BSDF, no texture > 2048.
- Optimize (auto, individual steps, rule 20): `gltf-transform resize 1024` → `webp` → `draco`. 5,819,056 B → 454,076 B (−92.2%). Draco needs a decoder on the client.
- Validation: `gltf-transform validate` exit 0 on both `_original.glb` and `_final.glb`. Final GLB re-imported into a throwaway scene: 2,040 tris, same bbox, textures and emission present, renders from 2 sides matched the Blender scene (then removed).
- Export: GLB, 454,076 B, 2,040 tris, 6 meshes, 4 materials, 9 WebP textures at 1024².

## Incidents
- The first round-trip import of the final GLB failed with `KeyError: 'Iridescence Factor'`. Cause: I had hand-built a `glTF Material Output` group with only an Occlusion socket, and the glTF importer reuses any group with that name. Fix: replaced it with `io_scene_gltf2.blender.com.material_helpers.create_settings_group`, re-exported, re-optimized, re-validated. The failed partial import was removed from the file.
- The Blender splash screen covered the viewport, so the visual checks are OpenGL viewport renders from an aimed camera instead of viewport screenshots.

## Files (compact)
- `scifi-supply-crate_original.glb`: raw Blender export, 5.8 MB
- `scifi-supply-crate_final.glb`: optimized, 0.45 MB
- `scifi-supply-crate.blend`: full scene, textures linked relatively from `textures/`
- `textures/`: 9 PolyHaven 1K JPGs, needed by the .blend
- `scifi-supply-crate_log.md`: this log

## Licenses
- blue_metal_plate: CC0, author Rob Tuytel, https://polyhaven.com/a/blue_metal_plate
- metal_plate: CC0, author Rob Tuytel, https://polyhaven.com/a/metal_plate
- rubber_tiles: CC0, author Amal Kumar, https://polyhaven.com/a/rubber_tiles
- Source: Poly Haven (polyhaven.com), via the public API (User-Agent `blender-kiln`)
- Geometry: original, scripted in this session

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30 22:09
