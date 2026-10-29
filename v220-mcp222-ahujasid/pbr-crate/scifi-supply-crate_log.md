# Sci-Fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, MCP addon 1.8 (protocol 14, up to date), PolyHaven on

## Brief
Sci-fi supply crate with reinforced corners and a handle on each side.
Interpretation: 0.80 × 0.50 × 0.45 m metal crate body with recessed panels on five faces;
reinforced frame (8 corner caps + 12 edge rails); two carry handles, one on each end (±X);
four lid latches (two front, two back); cyan emissive status strip on the front panel.

## Reference Image
- Path: none
- Visual comparison: N/A

## Source
- Method: scripted (Blender Python, bmesh + bevel modifiers applied + bezier-curve handle bars)
- Factory scene: the default Cube was removed before building (untouched factory scene)

## Pipeline
- Parts (all parented to empty `SM_SciFiCrate`, origin = centre of base):
  - SM_SciFiCrate_Body — 148 tris — M_Metal_PaintedBlue
  - SM_SciFiCrate_Corners — 1,504 tris — M_Metal_DarkSteel
  - SM_SciFiCrate_Rails — 1,296 tris — M_Metal_DarkSteel
  - SM_SciFiCrate_Handles — 1,104 tris — M_Metal_DarkSteel
  - SM_SciFiCrate_Latches — 864 tris — M_Metal_DarkSteel
  - SM_SciFiCrate_Light — 44 tris — M_Emissive_StatusCyan
- Cleanup: transforms applied; merge by distance 1e-4 (56 verts merged on handle-bar end caps,
  24 degenerate cap faces collapsed; other parts 0); normals recalculated outward; loose / degenerate
  none; fused edges 0, open edges 0 on every part; shade smooth by angle 35°; no live modifiers
- Total: 4,960 tris, at the top of the balanced range (bevelled corners and handle tubes take most)
- Bounding box: 1.009 × 0.528 × 0.470 m (handles included; body 0.80 × 0.50 × 0.45), resting on z = 0
- UVs: world-scale box projection, 1 UV unit = texture's real-world size (2.5 m body, 2 m steel)
- Texturing (PolyHaven PBR, 2k source):
  - Body: blue_metal_plate → M_Metal_PaintedBlue (Diffuse, Rough, nor_gl; metallic 0)
  - Frame, handles, latches: metal_plate_02 → M_Metal_DarkSteel (Diffuse, Rough, Metal, nor_gl)
  - Status strip: M_Emissive_StatusCyan (Principled, emission 4.0, no textures)
  - Displacement maps removed (glTF has no slot); textures packed into the .blend
- Export audit: no procedural nodes; all Principled BSDF. Exporter warning "More than one shader
  node tex image used for a texture" = Metal + Rough packed into one metallicRoughness texture (expected)
- Backface culling on (closed meshes → not double-sided)
- Optimize (auto preset): gltf-transform resize 1024 → webp q90 → draco (individual steps, no simplify)
  16,272,552 B → 711,048 B (−95.6%). Geometry unchanged (4,960 tris). Draco needs a decoder on the client.
- Verification: final GLB re-imported in Blender — 4,960 tris, 3 materials, all maps present;
  looked at from two opposite angles, matches the .blend

## Files
- scifi-supply-crate_original.glb — 16.3 MB (2k textures, uncompressed)
- scifi-supply-crate_final.glb — 711 KB (1024 WebP, Draco)
- scifi-supply-crate.blend — 13.2 MB (textures packed)
- scifi-supply-crate_log.md

## Licenses
- blue_metal_plate — Rob Tuytel, Poly Haven, CC0 — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 — Rob Tuytel, Poly Haven, CC0 — https://polyhaven.com/a/metal_plate_02
- Geometry: scripted in this session, no third-party assets

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
