# Sci-Fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop range 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from text brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python via MCP, Blender 5.2.2 LTS, addon 1.7)
- Parts (24 objects, all parented to SM_SupplyCrate, collection Props_SciFi):
  shell 0.80 x 0.55 x 0.50 m (bevelled), lid band, base skirt, 8 corner caps,
  4 vertical edge rails, 2 side handles (bevelled bezier U-bar + 2 mount plates each, on ±X),
  2 front latches across the lid seam, 1 emissive status light strip (front, -Y)

## Pipeline
- Import: implicit (scripted). 1,952 tris, assembly bbox 0.989 x 0.582 x 0.516 m
  (shell 0.80 x 0.55 x 0.50 m; width includes handles), base at z=0, origin at centre of base
- Cleanup: 1,952 → 1,952 tris. Merge by distance (32 verts merged, handle curve seams),
  recalc normals, remove loose (0), degenerate dissolve (0), non-manifold edges 0,
  transforms identity, orphans purged. Assembly raised 8 mm so the bottom corner caps sit on z=0
- UVs: world-space box projection, scaled to each texture's real-world size
  (2.5 m shell, 2.0 m hardware) → life-sized texel density, Mapping scale 1
- Texturing (PolyHaven, 2K JPG, via download_polyhaven_asset + set_texture):
  - Shell → M_Metal_PaintedBlue ← blue_metal_plate (Diffuse, Rough, nor_gl, Displacement)
  - Corner caps, rails, bands, handles, mounts, latches → M_Metal_WornSteel ← metal_plate_02
    (Diffuse, Rough, Metal, nor_gl, Displacement)
  - Status light → M_Emissive_StatusCyan (flat Principled, emission strength 4)
- Material audit (rule 19): all Principled BSDF, no procedural nodes, all images ≤ 2048.
  Map-level result in exported GLB: baseColor + metallicRoughness + normal filled for both metals;
  emissive factor + KHR_materials_emissive_strength for the light.
  Lost on purpose: Displacement maps (glTF has no slot). Exporter warning
  "More than one shader node tex image used for a texture" = Metal + Rough packed into one
  metallicRoughness PNG (7.3 MB)
- Optimize: not run — proposed to user (interactive step)
- Export: GLB, 15.5 MB, 1,952 tris, 24 meshes, 6 textures (2048²), no Draco

## Files
- sci-fi-supply-crate_final.glb (15.5 MB)
- sci-fi-supply-crate.blend (13.3 MB, images packed)
- sci-fi-supply-crate_log.md
- No _original.glb: scripted asset, there is no source file to keep

## Licenses
- blue_metal_plate — Rob Tuytel, Poly Haven, CC0 — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 — Rob Tuytel, Poly Haven, CC0 — https://polyhaven.com/a/metal_plate_02
- Geometry: original, scripted in this session

## Checkpoint
- Last completed step: EXPORT (optimize pending user choice)
- Timestamp: 2026-09-29
