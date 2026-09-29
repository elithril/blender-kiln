# Painted Wooden Chair — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop range 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Brief: realistic wooden chair for a farmhouse kitchen; source from PolyHaven only (no AI, no Sketchfab)

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: N/A (marketplace source)
- Hunyuan3D params: N/A

## Source
- Method: marketplace
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_01
- Selection: best tag match for the brief ("farmhouse", "kitchen", "dining", "wood", "painted")
  among 23 PolyHaven furniture models tagged chair
- Download: PolyHaven public API (api.polyhaven.com / dl.polyhaven.org), glTF 1k
  (diffuse, ARM, normal GL). **Deviation:** the connected MCP was the official Blender Lab
  server, which has no PolyHaven tools, so the files were fetched with curl rather than
  download_polyhaven_asset. Same files, same license.
- Environment: Blender 5.2.2 LTS

## Pipeline
- Import: 724 tris, 1024 verts, 491.6 kB (_original.glb), bbox 0.435 x 0.540 x 0.956 m
  (world X x Y x Z). Front already at -Y, up +Z.
- Rename: painted_wooden_chair_01 -> SM_PaintedWoodenChair, mesh -> SM_PaintedWoodenChair_Mesh,
  material -> M_PaintedWoodenChair
- Cleanup: 724 -> 724 tris. Operations: transforms applied (already identity), origin moved to
  center of base (shift -0.0015, +0.0307, -0.0007 m), loose geometry 0, degenerate faces 0,
  orphans purged. Default startup Cube hidden (not deleted) and excluded from the export.
- Cleanup NOT applied, by decision: **merge by distance** (rule 10). The 614 "doubles" are the
  authored hard-edge / UV-seam splits of the glTF. Merging them was tried and measured:
  903 of 2172 face corners moved > 5 deg from the source normals (max 86 deg), and it was
  visible as smeared shading on the seat and legs. Restoring the normals with a Data Transfer
  modifier made it worse (1134 corners > 1 deg). Reverted to the original unwelded mesh data.
  The exporter re-splits seams anyway (1072 verts in the final).
- Recalculate normals: skipped as a no-op. A dry run measured 0 faces flipped.
- Poly check: 724 tris is BELOW the balanced prop range (1.5-5K). Soft range, not blocking.
  Detail is carried by the normal map. No geometry added.
- Material audit (rule 19): Principled BSDF + image textures only, no procedural nodes.
  Colorspaces: diffuse sRGB, ARM and normal Non-Color. AO channel of the ARM map is not exported
  as occlusionTexture (same as the PolyHaven source glTF).
- Texturing: skipped (full PBR set from source)
- Optimize: skipped (interactive step, not run; offered to the user)
- Export: GLB, export_apply=False, Y-up, no Draco. 493.1 kB, 724 tris, 1072 verts.
  gltf-transform validate: 0 errors.

## Files (compact)
- painted-wooden-chair_original.glb — PolyHaven glTF 1k packed as-is (491.6 kB)
- painted-wooden-chair_final.glb — 493.1 kB
- painted-wooden-chair.blend — 571.5 kB
- painted-wooden-chair_log.md

## Licenses
- Painted Wooden Chair 01 by Kuutti Siitonen, PolyHaven: CC0 (no attribution required)

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 16:27
