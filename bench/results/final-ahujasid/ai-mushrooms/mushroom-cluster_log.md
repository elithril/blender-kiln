# Mushroom Cluster — Production Log

## Config
- Type: prop
- Target: glTF
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Backend: HF Spaces (HF account `elithril`, saved token — announced)

## Reference Image
- Path: work/concept.png (generated), cleaned to work/concept_clean.png
- Brief enrichment: red caps with cream spots, cream stems, tall conical cap + two smaller rounded caps, stems converging at one base
- Assumed size: tallest mushroom 0.40 m (not given in brief)

## Prompts (copy-paste ready)
- Concept art: "a cluster of three stylized fantasy mushrooms growing together from one small base, one tall, one medium, one small, red caps with white spots, cream stems, stylized hand-painted game asset, 3D render, centered, isolated on a plain white background, three-quarter view, single object, no ground, no grass, no shadow" (source: flux-schnell, seed=42, 1024x1024, 4 steps)
- Concept iterations: none. SHORTCUT: FLUX added grass, a pebble and a 4th tiny mushroom despite the prompt; instead of regenerating (ZeroGPU quota), green pixels and everything below y=832 were painted white locally (rule 9: no ground).
- Hunyuan3D params: endpoint=/shape_generation (/generation_all broken server-side), steps=30, guidance_scale=5.0, seed=1234, randomize_seed=False, octree_resolution=256, check_box_rembg=True, num_chunks=8000; model hunyuan3d-dit-v2-0

## Source
- Method: AI
- HF Space: https://huggingface.co/spaces/tencent/Hunyuan3D-2
- Concept Space: https://huggingface.co/spaces/black-forest-labs/FLUX.1-schnell

## Pipeline
- Scene: factory scene (Cube, Camera, Light, no .blend) — Cube removed. glTF importer root empty "world" removed after unparenting.
- Import: 293,620 faces, 8.0 MB, raw bbox 1.632x0.957x1.957 → scaled to 0.334x0.196x0.400 m, origin at base centre, faces -Y
- Cleanup (non-destructive): merge by distance -6,569 verts; normals recalculated; 811 loose verts removed; dissolve degenerate -4,645 faces → 275,835 tris; fused edges 0, open edges 0; 3 islands (main 274,651 / 1,152 / 32 faces)
- PENDING user choice: decimate target, stray islands

## Licenses
- FLUX.1-schnell output: Apache-2.0 model
- Hunyuan3D-2: Tencent Hunyuan 3D Community License (excludes EU, UK, South Korea territories)

## Checkpoint
- Last completed step: CLEANUP (non-destructive), awaiting decimate decision
- Timestamp: 2026-09-30 21:30
