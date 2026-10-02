# Fantasy Mushroom Cluster — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- 3D backend: HF Spaces (tencent/Hunyuan3D-2)
- MCP: official Blender Lab MCP (Blender 5.2.2 LTS) — skill's blender-mcp tool names mapped: get_scene_info → get_objects_summary, get_viewport_screenshot → get_screenshot_of_area_as_image, get_object_info → execute_blender_code bbox read

## Reference Image
- Path: concept.jpg (generated) → concept_clean.png (edited, used for generation)
- Brief enrichment: red caps with white spots, beige/cream stems with bulbous collar, three mushrooms side by side
- Edit: Pollinations output contained a grass base + watermark (rule 9/11). Bottom rows (y≥484) painted white, near-neutral grey backdrop pushed to white, subject shifted down 70 px to centre. Done in Blender image API (no PIL in venv).
- Visual comparison: close match on silhouette (3 mushrooms, caps, collared stems). All three are similar heights, as in the concept (the brief did not ask for varied heights).

## Prompts (copy-paste ready)
- Concept art: "three stylized fantasy mushrooms growing together as a cluster, red caps with white spots, cream stems, different heights, hand-painted game asset style, single object centered, full view, isolated on pure white background, no ground, no shadow, no grass, 3/4 view" (source: pollinations, seed=42, 1024 requested → 768x768 returned)
- Concept iterations: ["product render of three cartoon fantasy toadstool mushrooms joined at the base, one tall, one medium, one small, glossy red caps with white spots, cream white stems, stylized hand-painted game prop, floating, isolated on plain solid white background, nothing else, no grass, no ground, no soil, no text" — seeds 7, 101: HTTP 402 Payment Required from Pollinations, NOT pursued (rule 5)]
- Hunyuan3D params: steps=30, guidance_scale=5.0, seed=1234, randomize_seed=False, octree_resolution=256, num_chunks=8000, check_box_rembg=True, endpoint=/shape_generation
  - /generation_all (textured) first → Space-side AppError 'NameError'. Fell back to /shape_generation. Space: https://huggingface.co/spaces/tencent/Hunyuan3D-2
  - Space reported shapegen model: tencent/Hunyuan3D-2/hunyuan3d-dit-v2-0

## Source
- Method: AI (image → 3D)
- HF Space: https://huggingface.co/spaces/tencent/Hunyuan3D-2

## Pipeline
- Import: 287,488 faces / 143,750 verts, 8.1 MB, raw bbox 1.966 × 0.918 × 0.992 m (Hunyuan unit-normalised)
- Scale: normalised to 0.5 m tall (ASSUMPTION — oversized fantasy toadstools; adjust if scene scale differs) → 0.991 × 0.463 × 0.500 m, origin at base centre, transforms applied
- Naming: geometry_0 → SM_FantasyMushroomCluster / SM_FantasyMushroomCluster_Mesh; unparented from importer empty "world" (empty kept, not exported)
- Default Cube: hidden (viewport + render), not deleted
- Cleanup: 287,488 → 280,573 faces (281,672 tris). Merge by distance: 2,603 verts. Loose/degenerate: 305 verts / 1,709 faces removed. Normals recalculated. Non-manifold edges: 0. Islands: 1 main + 3 fragments (~1 cm, 34-44 verts each, near base) — NOT removed, pending user choice
- Poly check: 281,672 tris vs 5K max → ~56× over range. Decimate previews built (PREVIEW_Decimate_5k, PREVIEW_Decimate_10k, modifiers unapplied). AWAITING USER CHOICE (rule 6)
- Texturing: pending (untextured — Space texture step failed)
- Optimize: pending
- Export: pending

## Licenses
- Concept art: Pollinations.ai generated image (free tier) — check Pollinations terms for commercial use
- Mesh: Hunyuan3D-2 output — Tencent Hunyuan 3D 2.0 Community License (excludes EU, UK, South Korea territories — relevant, user is in France; review before commercial use)

## Checkpoint
- Last completed step: CLEANUP (non-destructive) — decimate decision pending
- Timestamp: 2026-09-29 16:24
