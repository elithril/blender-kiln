# Mushroom Cluster — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Backend: HF Spaces — tencent/Hunyuan3D-2 (stage RUNNING, zero-a10g)
- Blender 5.0.1, blender-mcp addon 1.7 (protocol 11, up to date)

## Reference Image
- Path: concept.jpg (generated), concept_input.png (watermark masked white, fed to Hunyuan3D)
- Brief enrichment: three mushrooms side by side, red domed caps with white spots, tapered cream stems, brown flared bases
- Visual comparison: close match on shape (3 mushrooms, cap/stem/base proportions). Heights nearly equal, as in the concept.

## Prompts (copy-paste ready)
- Concept art: "A cluster of three stylized fantasy mushrooms of different heights growing together, tall medium and small, red rounded caps with white spots, thick cream-colored stems, joined at the base, single object, hand-painted game asset style, centered, isolated on a plain solid white background, no ground, no shadow, no environment, three-quarter view" (source: pollinations, seed=42, 1024 requested / 768 returned, EXIF says model "sana" despite model=flux)
- Concept iterations: v2 attempt refused with HTTP 402 Payment Required (twice) — not pursued (rule 5)
- Hunyuan3D params: endpoint=/shape_generation, steps=30, guidance_scale=5.0, seed=1234, randomize_seed=False,
  octree_resolution=256, num_chunks=8000, check_box_rembg=True

## Source
- Method: AI (image → 3D)
- HF Space: https://huggingface.co/spaces/tencent/Hunyuan3D-2
- /generation_all (shape+texture) failed server-side: AppError 'NameError' → fell back to /shape_generation (untextured)
- gradio_client 2.7.1: /shape_generation result[0] is a dict ({'value': path, ...}), not a path string

## Pipeline
- Import: 355,324 tris, 177,664 verts, 9.9 MB (mushroom-cluster_original.glb), trimesh generator, no materials, no UVs
  - raw bbox 1.96 × 0.745 × 1.566 → scaled uniformly to 0.50 m tall (assumption) → 0.626 × 0.238 × 0.500 m
  - parent empty "world" removed, renamed SM_MushroomCluster / SM_MushroomCluster_Mesh, origin at base center
- Cleanup: 355,324 → 342,513 faces; merge by distance −4,780 verts; degenerate dissolve; 0 loose; 1 island; 0 non-manifold edges; shade smooth
- Poly check: 342,513 tris vs 1.5-5K → ~68× over → decimate PROPOSED (preview at ratio 0.01314 → 4,528 tris), awaiting user
- Texturing: pending
- Optimize: pending
- Export: pending

## Licenses
- Concept image: Pollinations.ai generated image (watermark masked)
- 3D mesh: Tencent Hunyuan3D-2 output — Tencent Hunyuan Community License (note: excludes EU, UK, South Korea territories — check before commercial use in France)

## Checkpoint
- Last completed step: CLEANUP 1-10, decimate preview (modifier "Decimate_Preview" live, not applied)
- Timestamp: 2026-09-29 15:05
