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
- Method: scripted (Blender Python via official Blender Lab MCP, Blender 5.2.2 LTS)
- Parts (31 objects, parented to empty `SM_SciFiCrate`): Body, 5 raised panels (±X, ±Y, +Z),
  8 corner caps, 4 vertical edge rails, lid band, 2 rubber skids,
  2 handles (one per short side ±X: 2 brackets + 2 arms + 1 bar each)

## Pipeline
- Import: implicit (scripted) — 1,042 faces / 1,972 tris, bbox 1.04 × 0.62 × 0.59 m
- Cleanup: 1,048 → 1,048 verts. Merge by distance (0 merged), remove loose (0),
  dissolve degenerate, recalc normals, 0 non-manifold edges, transforms applied,
  base moved to z=0, orphans purged (3 data-blocks)
- UVs: world-scale cube projection (cube_size 1.0 m)
- Texturing (PolyHaven PBR, 1k JPG, hand-built Principled graph):
  - Body + panels → `M_Metal_PaintedPanel` ← blue_metal_plate (diff, nor_gl, arm)
  - Corners, rails, lid band, handle brackets/arms → `M_Metal_Steel` ← metal_plate_02 (diff, nor_gl, arm)
  - Handle bars + skids → `M_Rubber_Black`, flat Principled values (no PolyHaven rubber
    texture fit: only rubber_tiles / rubberized_track exist)
  - ARM wired as G → Roughness, B → Metallic. R (AO) deliberately NOT wired → no
    occlusionTexture in the GLB. Displacement maps not downloaded (no glTF slot).
- Material audit (map level): no procedural nodes; GLB verified to contain
  baseColorTexture + metallicRoughnessTexture + normalTexture for both textured
  materials. Exporter warning "More than one shader node tex image used for a texture"
  observed; GLB inspection shows no slot lost.
- Optimize: skipped (not run) — offered to user
- Export: GLB, 3,094,272 bytes (≈3.1 MB, dominated by 6 embedded 1k JPGs), 1,972 tris,
  export_apply=False, Y-up, no Draco

## Deviations from canonical skill path
- Official Blender Lab MCP in use, not blender-mcp: no get_scene_info /
  get_viewport_screenshot / PolyHaven integration tools. Replaced by
  execute_blender_code, render_viewport_to_path, and direct PolyHaven public API (curl).
- No `set_texture`: node graph hand-built, colorspaces set explicitly (Non-Color on N and ARM).
- Compact storage: no separate `_original.glb` — for a scripted asset there is no
  imported original; the .blend holds the full history. Images packed into the .blend.

## Licenses
- blue_metal_plate — PolyHaven, CC0, author Rob Tuytel — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 — PolyHaven, CC0, author Rob Tuytel — https://polyhaven.com/a/metal_plate_02
- Geometry: original, scripted in this session

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 16:30
