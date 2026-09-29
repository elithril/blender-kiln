# Sci-Fi Supply Crate — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop range 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.7 (protocol 11, up to date), PolyHaven integration enabled

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Brief: "A sci-fi supply crate with reinforced corners and a handle on each side."
- Concept art: none (scripted, no reference)

## Source
- Method: scripted (Blender Python via execute_blender_code), as the brief asked
- Scene: untouched factory scene. Default `Cube` removed before building (rule 6 exception). Camera and Light kept.

## Build
- SM_SciFiCrate_Body — 1.00 x 0.60 x 0.55 m box, inset recessed panel on each face (7 cm rim, 1.2 cm recess), bevelled silhouette edges. 156 tris
- SM_SciFiCrate_Corner_01..08 — solid 14 cm corner blocks standing 2 cm proud of the body, chamfered outer corner, one bolt head per outer face. 140 tris each
- SM_SciFiCrate_Handle_01/02 — one per X side: two mounting plates, swept U-bar (r 1.2 cm, 6 cm reach), grip sleeve. 484 tris each
- First corner attempt (three overlapping plates) produced internal geometry and a broken silhouette; rebuilt as solid blocks before texturing.

## Pipeline
- Import: implicit (scripted). 11 objects, 2,244 tris, overall 1.154 x 0.656 x 0.606 m (body 0.99 x 0.59 x 0.54 m; handles and corners account for the rest). Origin at base centre; asset raised 0.028 m so its lowest point (bottom bolts) sits at z = 0.
- Cleanup: 2,244 -> 2,244 tris. Merge by distance 0.1 mm: 0 verts merged. Degenerate dissolve, loose removal: 0. Normals recalculated. Fused edges (>2 faces): 0 on every object. Open edges: 0. Transforms already identity. 80 n-gons (bolt caps, handle end caps, corner chamfers) triangulated so the exporter could compute tangents; tri count unchanged.
- UVs: box projection at real-world scale (1 UV unit = the texture's real-world size: 2.5 m body, 2.0 m trim); Mapping nodes left at scale 1.
- Texturing (PolyHaven, strategy 1, via download_polyhaven_asset + set_texture):
  - Body: blue_metal_plate 2k -> M_Metal_PaintedBlue (Diffuse, Rough, nor_gl, Displacement)
  - Corners + handles: metal_plate_02 1k -> M_Metal_WornSteel (Diffuse, Rough, Metal, nor_gl, Displacement), one material shared by all 10 trim objects
  - Colourspaces checked: Diffuse sRGB, all other maps Non-Color. Images renamed T_Metal_*_{D,R,N,M,H} and packed into the .blend.
  - Screenshots from two opposite angles in Material Preview: no stretching or seams visible.
- Material export audit: both materials Principled BSDF, no procedural nodes, no colour ramps, no texture above 2048. Warning: Displacement (height) maps are not carried by glTF. They stay in the .blend only.
- Export: `_original.glb` 8,464,956 B (8.1 MiB), export_apply=False, tangents on. gltf-transform validate: 0 errors, 0 warnings.
- Optimize (auto preset, individual steps, rule 20): no resize (all textures <= 2048, the balanced cap) -> `gltf-transform webp --quality 90` -> `gltf-transform draco`. 8,464,956 B -> 1,100,628 B (-87%). Validate: 0 errors, 0 warnings; infos only (validator cannot check KHR_draco_mesh_compression; unused bufferViews left by Draco).
- Verification: `_final.glb` re-imported into a scratch scene: 11 meshes, 2,244 tris, 1.154 x 0.656 x 0.606 m, 2 materials, 6 images, renders correctly. Scratch scene then removed.
- Final: `sci-fi-supply-crate_final.glb`, 1.05 MiB, 2,244 tris. Needs a Draco decoder and EXT_texture_webp support on the client.

## Files (compact)
- sci-fi-supply-crate_original.glb
- sci-fi-supply-crate_final.glb
- sci-fi-supply-crate.blend (textures packed; Displacement maps kept here)
- sci-fi-supply-crate_log.md
- Removed: sci-fi-supply-crate.blend1 (Blender's automatic save backup)

## Licenses
- blue_metal_plate — Poly Haven, Rob Tuytel, CC0 — https://polyhaven.com/a/blue_metal_plate
- metal_plate_02 — Poly Haven, Rob Tuytel, CC0 — https://polyhaven.com/a/metal_plate_02
- Geometry: scripted in this session, no third-party assets

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 20:01
