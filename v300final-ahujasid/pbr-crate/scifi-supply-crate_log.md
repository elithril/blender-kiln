# Sci-fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (web)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Backend: none — scripted (Blender 5.2.2 LTS via mcp-for-blender, addon 1.8, protocol 14)
- Output: /private/tmp/kiln-bench/v300final-ahujasid/pbr-crate/work/generated-assets/scifi-supply-crate

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A
- Assumptions (auto mode): size ~0.80 x 0.55 x 0.50 m (W x D x H); 8 reinforced corner caps;
  recessed side panels with one handle on each short side (left/right, ±X); lid seam band; 4 feet.

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)

## Source
- Method: scripted (Blender Python, live MCP session)

## Pipeline
- Brief: "A sci-fi supply crate with reinforced corners and a handle on each side." — confirmed (auto)
- Source: scripted in the live Blender (factory scene: default Cube removed, rule 6; Camera/Light left, not exported).
  Parts: SM_ScifiCrate_Base (bevelled hull, recessed side panels), _Lid (recessed top, raised plate),
  _SeamBand (dark gasket), _Corners (8 chamfered caps with recessed plates + 4 vertical edge rails),
  _Handles (2 bent bars on mounting plates, ±X), _StatusLight (emissive strip, lid front).
  Box-mapped UVs at world scale (1 UV unit = 1 m). Smooth by angle 35°. v1→v2: cap plates + edge rails added, handles centred on panels.
- Import: 1480 tris (822 faces), 6 objects, bbox 0.90 x 0.57 x 0.515 m (0.82 m wide without handles), on ground (corner feet), no modifiers

- Cleanup: 1480 → 1480 tris, operations: transforms applied (all identity), merge by distance 1e-4 keeping split normals
  (32 verts merged on the handle tube caps; 64 open edges → 0), recalc normals, remove loose (0), dissolve degenerate,
  manifold check: 0 fused / 0 open on every part; origin = base centre (0,0,0), min z 0.000; world bbox on vertices
  0.904 x 0.574 x 0.515 m; orphans purged (factory Cube mesh); materials: 4, no empty slots.
  Poly check: 1480 tris vs balanced prop 1.5-5K — at the bottom of the band, no reduction.
- Texturing: strategy 1 (zones = parts; PolyHaven via import_asset, 1k JPG)
  - hull (Base, Lid): M_Metal_BluePaintedPlate ← PolyHaven blue_metal_plate (Diffuse, Rough, nor_gl), 2.5 m real size
  - corners + rails + handles: M_Metal_WornSteelPlate ← PolyHaven metal_plate_02 (Diffuse, Rough, Metal, nor_gl), 2 m real size
  - seam gasket: M_Metal_DarkSeam (flat, metallic 0.8, rough 0.6); status strip: M_Emissive_Status (cyan, strength 6)
  - server made one material copy per object → merged to one per family; Mapping at identity, life-size scale baked
    into the box-mapped UVs (/2.5, /2.0); Displacement maps dropped deliberately (no glTF slot; normal map carries relief);
    images renamed T_BluePaintedPlate_*, T_WornSteelPlate_*, packed in the .blend; colourspaces sRGB / Non-Color checked
  - looked (material shading): three-quarter front-right, back-right, back, left — no stretch, consistent texel scale
  - uv_check on _original.glb: 0 FAIL, 6 WARN (overlap / outside 0-1 = tiled world-scale box mapping, expected; no bake)
- Material audit (rule 19): Principled only, no procedural nodes, no modifiers. Map level: base + metallicRoughness + normal
  filled on both PBR materials (Rough+Metal packed into one MR image — the exporter's "more than one tex image" warning,
  same sampler, harmless); emissive kept (KHR_materials_emissive_strength). Backface culling on (closed meshes, single-sided).
- Optimize: gltf-transform resize 1024 → webp q90 → draco (q pos 14 / nor 10 / uv 12), separate steps (rule 20);
  4.15 MB → 0.70 MB (−83 %). Geometry untouched. Preview = copy of _original (no Draco, no WebP).
- Export: glTF/GLB, web/scifi-supply-crate_final.glb 0.70 MB, 1480 tris, 6 meshes, 4 materials, 6 textures ≤1024;
  export_apply=False, camera/light excluded. Headless review render of _final (q1/q3/top/under, matcap + colour): decodes and
  matches the Blender view. Studio checks: no WARN (note: 1480 tris, just under the balanced band).

## Licenses
- blue_metal_plate — Poly Haven, Rob Tuytel, CC0 — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 — Poly Haven, Rob Tuytel, CC0 — https://polyhaven.com/a/metal_plate_02
- Geometry: scripted in this session, CC0-equivalent (no third-party mesh)

## Checkpoint
- Last completed step: [7] EXPORT
- Timestamp: 2026-10-22 20:10
