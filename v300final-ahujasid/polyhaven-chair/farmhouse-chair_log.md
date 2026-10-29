# Farmhouse Chair — Production Log

## Config
- Type: prop (furniture)
- Target: glTF (web)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Backend: none — marketplace (PolyHaven only; no AI, no Sketchfab, per brief)
- Environment: macOS arm64 (Apple M4 Pro), Blender 5.2.2 LTS, mcp-for-blender addon 1.8 (protocol 14, up to date), gltf-transform + gltfpack present
- Live view: off (unattended auto run)

## Brief
- Realistic wooden chair for a farmhouse kitchen. Assumed real size: kitchen/dining chair, seat ~0.45 m, total height ~0.85-1.0 m.

## Reference Image
- Path: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- N/A (marketplace)

## Source
- Method: marketplace (PolyHaven, preflight: polyhaven on, sketchfab/polypizza off; no AI per brief)
- Marketplace: https://polyhaven.com/a/painted_wooden_chair_02 — "Painted Wooden Chair 02" by Kirill Sannikov
- Candidates seen: painted_wooden_chair_02 (chosen: ladder-back, worn paint over visible wood grain, tagged farmhouse/dining), painted_wooden_chair_01 (white, kitchen-tagged, runner-up), WoodenChair_01 (gothic, rejected), Rockingchair_01 (rocking, rejected)
- Downloaded at 1k (web target)

## Pipeline
- [1-2] CONFIG/BRIEF: done. Scene was Blender's untouched factory scene (Cube, Camera, Light, unsaved): factory Cube removed (rule 6 exception).
- [3] SOURCE: done — PolyHaven painted_wooden_chair_02 imported (1k).
- [4] IMPORT: 780 verts, 634 faces, 1,246 tris, 1 material, 1 UV map. Arrived 0.640 x 0.662 x 1.264 m, rotated -90 deg Z, with a Geometry Nodes "Auto Smooth" + Weighted Normal modifier (shading only). Seat top at 0.58 m — oversized for a kitchen chair (usual 0.43-0.48 m). ASSUMPTION (auto mode): uniform scale x0.793 so the seat sits at 0.46 m -> 0.507 x 0.525 x 1.002 m. Renamed SM_FarmhouseChair / SM_FarmhouseChair_Mesh, material M_Wood_PaintedWeathered, textures T_FarmhouseChair_BaseColor/_N/_R (packed in the .blend). Looked at 4 angles: clean, front faces -Y.
- [5] CLEANUP: 1,246 -> 1,246 tris (no geometry change). Shading modifiers applied (GN output exists only as modifier result, rule 18 exception; procedural version not needed — pure shading). Transforms applied, merge by distance 1e-4: 0 merged, custom normals kept; 0 loose, 0 degenerate; fused edges 0, winding consistent (no flip needed); 298 open edges = hidden open ends of the game-res source, left as authored. Origin at base centre, on ground (min z 0). Orphans removed (Cube mesh, Material, Dots Stroke, Auto Smooth group). Tier balanced prop 1.5-5K: 1,246 tris, just under — no reduction proposed.
- [5b] TEXTURING: skipped — marketplace PBR set (base colour, roughness, normal). Material audit: Principled BSDF + image textures, identity mapping, no procedural nodes -> exports intact. uv_check: 0 FAIL, WARN flipped 21.0 % (mirrored islands, author's layout), stretch 22.4 %, overlap 0 %, collapsed 0 %, used 82 %.

- [6] OPTIMIZE: gltf-transform resize 1024 -> webp q90 -> draco (separate steps, rule 20; no simplify). 6,391,932 B (_original.glb) -> 3,589,600 (resize) -> 748,144 (webp) -> 715,700 B web/farmhouse-chair_final.glb (-89 %). Geometry untouched (1,246 tris). _preview.glb = copy of _original (no Draco/WebP, extensionsUsed none — opens in macOS Quick Look). Final checked headless (review_renders colour + matcap, q1/q3/top/under): Draco decodes 986 verts, textures intact.
- [7] EXPORT: glTF binary, web/farmhouse-chair_final.glb, 715,700 B, 1,246 tris, 1 material (3 WebP 1024 maps), Draco (client needs a decoder). export_apply=False (no modifiers left). Material audit passed. studio.py checks: no WARN (note: 1,246 tris slightly under the balanced 1.5-5K range — fine). .blend saved (textures packed).
- Files: farmhouse-chair.blend, farmhouse-chair_original.glb, farmhouse-chair_preview.glb, web/farmhouse-chair_final.glb, this log. Kept for the user to decide (compact mode, nobody to ask in auto): .work/ (resized.glb, webp.glb, review/ renders).

## Licenses
- painted_wooden_chair_02 (mesh + diffuse/normal/roughness 1k textures): CC0 — Kirill Sannikov / Poly Haven. Source: Poly Haven (polyhaven.com), via the MCP for Blender integration

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22 20:03
