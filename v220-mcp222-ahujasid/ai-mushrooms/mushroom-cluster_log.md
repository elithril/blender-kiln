# Mushroom Cluster — Production Log

## Config
- Type: prop
- Brief: a cluster of three stylized fantasy mushrooms with spotted caps, for a forest scene
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: stylized
- Mode: auto, with the standing answer "take the recommended option at every choice"
- Storage: compact
- 3D backend: HF Spaces (MCP-native generators all off: hunyuan3d, hyper3d, meshy, tripo)
- Environment: Blender 5.2.2 LTS, addon 1.8 (protocol 14, up to date), Apple M4 Pro, 24 GB unified,
  gradio_client 2.7.1 in ~/.hunyuan3d/venv, gltf-transform 4.3.0, gltfpack present
- HF account used for Space calls: `elithril` (saved token on this machine; kept over anonymous for the larger quota)

## Reference Image
- Path: none supplied. Concept generated with FLUX.1-schnell, packed in the .blend as `concept.png`
- Concept defects: grass tuft and drop shadow under the subject (rule 11). Not regenerated, to protect the
  ZeroGPU quota for the 3D call. Cleaned locally instead: keep-list of cap red / stem cream / brown outline
  pixels, gap closing across the stems, small components dropped. Result packed as `concept_clean.png`
- Visual comparison: close match. Two tall spotted mushrooms on intertwined stems plus a small button
  mushroom at the base (the third mushroom). The concept's grass hid the stem bases, so the generated base was
  re-grounded (see Cleanup)

## Prompts (copy-paste ready)
- Concept art (source: FLUX.1-schnell, seed 42, 1024x1024, 4 steps):
  "a cluster of three stylized fantasy mushrooms growing together from one small base, tall, medium and small,
  red caps with white spots, cream stems, hand-painted game asset style, centered, isolated on a plain white
  background, three-quarter view, single object, no ground, no grass, no shadow"
- Hunyuan3D params: endpoint /shape_generation, steps=30, guidance_scale=5.0, seed=1234 (randomize off),
  octree_resolution=256, check_box_rembg=True, num_chunks=8000. Model hunyuan3d-dit-v2-0.
  Input: concept_clean.png

## Source
- Method: AI (image → 3D)
- HF Space: https://huggingface.co/spaces/tencent/Hunyuan3D-2 (stage RUNNING at the time of the call)
- Concept Space: https://huggingface.co/spaces/black-forest-labs/FLUX.1-schnell
- Scripts: scripts/concept.py, scripts/shape.py, scripts/zones.py (zone classification)

## Pipeline
- Scene: Blender factory scene. Default Cube removed (rule 6 exception), Camera and Light kept
- Import: 287,394 tris, 143,717 verts, parented to a `world` empty (unparented and removed). Scaled to
  0.45 m tall (assumed size: the brief gives none), origin at the centre of the base. Renamed SM_MushroomCluster
- Cleanup (high-poly):
  - weld at 1e-5: 609 verts merged and 1,219 degenerate faces collapsed, so shading was not restored
    (smooth AI mesh, shade smooth)
  - debris: 11 floating islands, 141 verts, deleted (recommended)
  - 1 fused edge (3 faces): faces removed and the hole filled, giving 0 fused and 0 open edges
  - ground plate: a ~4 mm flange under the stems, cut at z=4 mm, holes capped (rule 9; recommended)
  - floating base: the fused trunk hung 2.8-3.5 cm above the ground except under a narrow left foot. The
    bottom 10 cm were stretched smoothly to the ground, button excluded (recommended)
- Decimate (recommended, applied): Collapse 283,842 → 8,000 tris on a copy. 0 open and 0 fused edges, before
  and after. The cap tip dropped 4 mm (0.450 → 0.446 m). 8K is above the balanced prop's 5K top but within 2×;
  the extra triangles go into the round caps and the gill ridges. High-poly kept hidden in the .blend
  (SM_MushroomCluster_High) as the bake source
- Texturing (strategy 2, stylized, baked):
  - zones on the high-poly: stem (flood fill from low stem seeds, with the downward-facing undersides as the
    barrier), gills (normal.z < -0.2 above 8 cm), caps (rest), spots (cap vertices raised > 0.8 mm above a
    40-pass Laplacian-smoothed surface, grown 2 rings), button (fitted sphere r 18.8 mm, red with 3 dots)
  - palette (linear): cap (0.80, 0.13, 0.05), spots (0.98, 0.93, 0.80), gills (0.93, 0.82, 0.62),
    stem (0.86, 0.72, 0.52)
  - UVs: seams on the zone boundaries, Minimum Stretch unwrap, concave pack. 6 islands (2 cap discs, 2 gill
    rings, trunk, button), face-area ratio 0.36-1.7× median for the middle 90%
  - bakes: high → low, base colour (DIFFUSE colour pass) and tangent normal, 1024², cage 4 mm, margin 16 px
  - material: M_Mushroom_Stylized, Principled BSDF, roughness 0.55, metallic 0, backface culling (closed mesh)
- Material export audit: pass. Principled only, no procedural nodes, base colour sRGB, normal Non-Color;
  both maps reached glTF slots (baseColorTexture, normalTexture)
- Optimize (auto preset, separate steps, no geometry change): resize 1024 → WebP q90 → Draco.
  1.24 MB → 165 KB (−87%). Needs a Draco decoder and WebP support on the client
- Export: mushroom-cluster_final.glb, 164,756 bytes, 8,000 tris / 4,240 verts, 0.358 × 0.224 × 0.446 m,
  single material, single-sided. gltf-transform validate: no errors, no warnings. Re-imported in Blender and
  compared from two opposite angles: matches

## Files (compact)
- mushroom-cluster_original.glb: raw Hunyuan3D output (7.8 MB)
- mushroom-cluster_final.glb: shipping asset (165 KB)
- mushroom-cluster.blend: high- and low-poly, both concepts and the baked textures packed
- mushroom-cluster_log.md: this file. scripts/: the generation and zoning scripts

## Licenses
- FLUX.1-schnell (concept image): Apache-2.0
- Hunyuan3D-2 (mesh): Tencent Hunyuan 3D 2.0 Community License. Its territory excludes the European Union,
  the United Kingdom and South Korea, and use above 1M monthly active users needs a separate licence from
  Tencent. Check this before shipping commercially from those territories
- No marketplace assets or textures used

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21 16:48
