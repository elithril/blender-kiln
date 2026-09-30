# Mushroom Cluster — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: stylized
- Mode: auto
- Storage: compact
- 3D backend: HF Spaces (tencent/Hunyuan3D-2)
- Environment: macOS arm64, 24 GB unified, Blender 5.2.2 LTS via Blender Lab MCP, gradio_client 2.7.1 (~/.hunyuan3d/venv), gltf-transform + gltfpack present

## Brief
A cluster of three stylized fantasy mushrooms with spotted caps, for a forest scene.
- Assumed real size: 0.5 m tall (not given in brief)

## Reference Image
- Path: concept.png (generated), concept_clean.png (grass/pebble painted out)
- Brief enrichment: red conical caps with raised cream spots, cream underside, tall slender cream stems, three heights (tall left, mid centre, short right)
- Edit: FLUX added a grass tuft and a pebble at the base despite the prompt. Painted to white (non-warm pixels in rows 680-805, everything below row 805) before 3D generation — rule 9, no ground from AI.
- Visual comparison: close match (shape)

## Prompts (copy-paste ready)
- Concept art: "a cluster of three stylized fantasy mushrooms of different heights growing from one small base, red caps with white spots, thick cream stems, hand-painted stylized game prop, centered, isolated on a plain white background, three-quarter view, single object, no ground, no grass" (source: flux-schnell, black-forest-labs/FLUX.1-schnell, seed=42, 1024x1024, 4 steps)
- Hunyuan3D params: endpoint=/shape_generation, steps=30, guidance_scale=5.0, seed=1234, octree_resolution=256, check_box_rembg=True, num_chunks=8000, randomize_seed=False
- Model reported by Space: tencent/Hunyuan3D-2/hunyuan3d-dit-v2-0

## Source
- Method: AI (FLUX concept -> Hunyuan3D shape)
- HF Space: https://huggingface.co/spaces/tencent/Hunyuan3D-2 (RUNNING, 22.7 s wall)
- HF account used for quota: current user's saved token (account announced in session)

## Pipeline
- Scene: factory startup scene (Cube, Camera, Light, no .blend) -> default Cube removed (rule 6 exception). Importer's "world" empty removed after unparenting (import artifact).
- Import: hunyuan_raw.glb, 11.4 MB, 414,826 faces, 1 island, bbox 1.97 x 1.22 x 1.95 (normalised) -> scaled to 0.504 x 0.312 x 0.500 m, origin at base centre, renamed SM_MushroomCluster / SM_MushroomCluster_Mesh
- Cleanup: merge by distance 0.1 mm (7,862 verts), recalc normals, remove loose (0), dissolve degenerate (204 faces), manifold check: 5 fused edges + 7 open edges at 4 sub-3 mm² spots under caps -> 14 faces deleted and holes filled -> 0 fused / 0 open. 398,879 faces.
- Poly check: 398,879 tris vs 1.5-5K -> ~80x over. Decimate previews (linked copies, modifier unapplied): 10K / 5K / 3K. AWAITING USER CHOICE (rule 6).
- Texturing: pending
- Optimize: pending
- Export: pending

## Licenses
- FLUX.1-schnell output: Apache-2.0 model
- Hunyuan3D-2: Tencent Hunyuan 3D Community License — territory excludes the EU, UK and South Korea. User is France-based: flag before commercial/production use.

## Checkpoint
- Last completed step: CLEANUP (decimate gate open)
- Timestamp: 2026-09-30 ~22:00 CEST
