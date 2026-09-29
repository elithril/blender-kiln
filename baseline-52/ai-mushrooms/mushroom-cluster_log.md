# Mushroom Cluster — Production Log

## Config
- Type: prop
- Target: glTF
- Tier: balanced (prop 1.5-5K tris)
- Style: stylized
- Mode: auto
- Storage: compact

## Reference Image
- Path: mushroom-cluster_concept.png (edited from mushroom-cluster_concept_raw.png)
- Brief enrichment: volva bulbs at stem bases, cream gills, mossy patch (unwanted, see below)
- Visual comparison: close match on shape; the three heights are near-uniform (brief implied a cluster, not graded heights)

## Prompts (copy-paste ready)
- Concept art: "stylized fantasy mushroom cluster, three mushrooms of different heights growing together from one small base, red caps with white spots, cream stems, hand-painted game asset, single object, centered, full view, isolated on plain solid white background, no ground, no shadow" (source: pollinations, model=turbo, seed=42, 768x768)
- Concept iterations: raw image had moss/wood base, grey bg and watermark. Regeneration blocked (Pollinations 429 then 402 on every model), so the image was cropped (rows 100-590) and padded to 768x768 white with sips instead
- Hunyuan3D params: steps=30, guidance_scale=5.0, seed=1234, octree_resolution=256, num_chunks=8000, rembg=True, randomize_seed=False, endpoint=/shape_generation

## Source
- Method: AI (image to 3D)
- HF Space: https://huggingface.co/spaces/tencent/Hunyuan3D-2 (stage RUNNING, model hunyuan3d-dit-v2-0)
- Failures: caption text-to-3D disabled on Space ("Text to 3D is disable"); /generation_all -> AppError 'NameError' (texgen broken), so shape only
- Note: gradio_client 2.7.1 returns result[0] as {'value': path, '__type__': 'update'}, not a path string

## Pipeline
- Import: 357,588 faces, 9.9 MB, bbox 1.967x1.292x1.226 (arbitrary units) -> normalised to 0.802x0.527x0.500 m, origin at base centre
- Cleanup: 357,588 -> 353,604 faces; merged 1,529 verts; 0 loose; 0 non-manifold edges; 1 island; normals recalculated; transforms applied
- Texturing: strategy 2 (procedural Principled, per-face zones) — M_MushroomCap_Red, M_MushroomSpot_White (60 spots), M_MushroomStem_Cream (stems+gills), M_MushroomBulb_Brown, M_Moss_Green (back mound)
- Decimate: PENDING USER CHOICE (preview modifier present, not applied): 5K -> 5,008 tris, 10K -> 10,018 tris
- Optimize: pending
- Export: pending

## Licenses
- Concept image: Pollinations.ai generated
- 3D mesh: Tencent Hunyuan3D-2 (Tencent Hunyuan Community License)

## Checkpoint
- Last completed step: TEXTURING (zones), awaiting decimate decision
- Timestamp: 2026-09-29
