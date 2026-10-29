# Mushroom Cluster — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced
- Style: stylized
- Mode: auto (standing answer: every proposed choice takes the recommended option)
- Storage: compact
- 3D backend: hf-spaces (microsoft/TRELLIS.2, stage RUNNING 2026-10-26)
- Environment: macOS arm64, 24 GB unified; Blender 5.2.2 LTS, mcp-for-blender addon 1.8 up to date; gradio_client 2.7.1 in ~/.hunyuan3d/venv; gltf-transform + gltfpack present
- HF account: Space calls use the locally saved token of account `elithril` (free ZeroGPU quota)
- Live view: off (unattended run, nobody to open Studio)

## Brief
- A cluster of three stylized fantasy mushrooms with spotted caps (red caps, white spots, pale stems), three heights, joined at one base, for a forest scene. No ground generated (rule 9).
- Assumed real size: cluster ~0.35 m tall (tallest mushroom), ~0.35 m wide.

## Reference Image
- Path: none from the user — concept generated from the brief

## Prompts (copy-paste ready)
- Concept art: "a cluster of three stylized fantasy mushrooms growing from one shared base, one tall, one medium, one small, red rounded caps with large white spots, smooth pale cream stems, hand-painted game asset style, soft even lighting, no outlines, centered, isolated on a plain white background, three-quarter view, single object, no ground, no grass, no shadow" (source: flux-schnell, seed 42, 1024², 4 steps)
- Concept iterations: none. FLUX added grass despite the prompt → cut out with macOS Vision (tools/cutout.swift), grass keyed out by colour (scripts/key_grass.py: 21,484 green px + 3,084 white fringe px removed) — chosen over a re-roll to save the ZeroGPU quota for TRELLIS.2 (rule 9: no ground)
- Generation params: backend=microsoft/TRELLIS.2 Space, seed=0, resolution=1024, sampler defaults (ss 7.5/0.7/12, shape 7.5/0.5/12, tex 1.0/0.0/12), extract_glb decimation_target=100000 (Space minimum), texture_size=2048; input had alpha → RMBG-2.0 not used

## Source
- Method: AI (image → 3D)
- HF Space: https://huggingface.co/spaces/microsoft/TRELLIS.2 — 89 s, mushroom-cluster_raw.glb 4.17 MB
- Concept Space: https://huggingface.co/spaces/black-forest-labs/FLUX.1-schnell

## Pipeline
- Scene: Blender factory startup (no .blend, Cube/Camera/Light only) → default Cube removed (rule 6 exception); live Blender used for the build
- Import: 95,331 tris (one mesh, 1 material, 2× 2048² textures: base colour + ORM), 4.17 MB, bbox 0.965 × 0.56 × 1.002 m, centred on origin (0.5 m below ground). Importer's parent empty `world` removed (transform kept). Renamed SM_MushroomCluster / SM_MushroomCluster_Mesh, material M_MushroomCluster_Baked. Topology: 39,284 boundary edges (UV-split vertices), 1 non-manifold. Look: 3 caps read clearly; a few grass blades baked in at the base (concept residue)
- Cleanup (raw re-imported once: a first 1e-4 weld showed the collapse came from the mesh, not the threshold): transforms applied → weld 1e-6 m (24,840 vertices merged; 469 degenerate TRELLIS triangles collapsed, so the split normals were not restored — TRELLIS shading is smooth anyway) → normals recalculated → 3 loose/degenerate faces removed → 25 floating grass islands deleted (2,066 faces, debris — recommended option taken) → 3,543 green-textured faces (grass blades fused onto the stem bases, sampled from the base-colour texture) deleted → 515 interior faces deleted → sliver faces on fused edges deleted until fused = 0 (hole fills that re-created fused edges were undone). Result 95,331 → 88,450 tris, fused 0, open 724 (2.5 m total, mostly at stem bases — tiny holes, not watertight, fine for a screen prop)
- Scale: 1.002 m (TRELLIS default) → 0.35 m tall (brief assumption); bbox 0.34 × 0.20 × 0.35 m; origin at base centre, on ground; transforms applied
- Poly check: 88,450 tris vs balanced prop 1.5–5K (2× = 10K) → decimate proposed; standing answer → recommended option taken: Collapse (triangulate) to 9,000 tris — inside 2× the top, spent on round caps. Before/after looked at (front, three-quarter, back, low angle): silhouette and spots kept. After: 8,999 tris, fused 0, open 613 (≤ 724 before → decimation passes). get_scene_info reports 16 non-manifold = bowtie verts on hole rims, no edge shared by > 2 faces
- Naming: SM_MushroomCluster / SM_MushroomCluster_Mesh, M_MushroomCluster_Baked, T_MushroomCluster_BaseColor, T_MushroomCluster_ORM; orphans purged
- Texturing [5b]: triggered by tools/uv_check — the TRELLIS atlas (0 % overlap on the raw) read 86.9 % overlap after the Collapse decimate (vertices dragged across UV seams). Fix (recommended, taken): new UVs on the 9K mesh + base colour rebaked in Cycles (Diffuse colour pass, selected-to-active) from the raw TRELLIS surface minus its grass faces, scaled/aligned to the low-poly (offset < 0.7 mm; low→high distance p99 1.1 mm, max 1.6 mm)
  - Bake 1: extrusion 6 mm / ray 30 mm → middle cap picked up the gill side (beige, red blotches); rebaked at 1.5 mm / 4 mm → clean
  - UV attempts: Smart UV 66° → 27.6 % used; angle-based unwrap on island seams → FAIL (34 % collapsed, 96 % stretched), undone; voxel remesh 0.8 mm + Collapse as a new low-poly → crumpled, and the big mushroom was dropped as a separate island, undone. Kept: Smart UV 66°, packed concave + rotate, margin 0.002 → uv_check WARN: used 47.9 %, overlap 4.2 % (Collapse's folded slivers, 1,908 edges > 120° — not visible in renders), stretch 0 %, collapsed 0 %, flipped 0 %
  - Material rebuilt: M_MushroomCluster = Principled, base colour T_MushroomCluster_BaseColor (2048², packed in the .blend and saved as PNG), roughness 0.9 constant, metallic 0 (the TRELLIS ORM read roughness 0.91 ± 0.07, metallic 0.02 ± 0.06 — flat, so not baked)
  - Look after texturing: two opposite three-quarters + top + under → caps red with white spots everywhere, stems cream; faint grey-green tint left at the stem bases (grass colour in the source texture)
- Final mesh: 8,991 tris, 0 edges shared by > 2 faces, 637 boundary edges (small holes at stem bases), 0.34 × 0.20 × 0.35 m, on ground
- Optimize: gltf-transform, separate steps (rule 20): resize 1024 (4.25 → 2.27 MB) → WebP q90 (→ 693 KB) → Draco (→ 279 KB, −93 %). Geometry untouched. mushroom-cluster_preview.glb = copy of _original (no Draco, no WebP; extensionsUsed none) for Mac Quick Look
- Export: GLB, material audit OK (Principled only, no procedural nodes), export_apply=False; web/mushroom-cluster_final.glb 279 KB, 8,991 tris, 1 material, 1 × 1024² WebP; re-rendered headless from two opposite three-quarters (review/) → matches the Blender views. studio.py checks: no WARN (notes: tris 80 % above the 5K tier top, within 2×; licences)
- Files kept for hand-over (auto mode, nobody to answer — not deleted): concept.webp/.png, concept_cutout.png, concept_nograss.png, mushroom-cluster_raw.glb, T_MushroomCluster_BaseColor.png (2048 bake), scripts/step1_resized.glb, scripts/step2_webp.glb, review/*.png

## Licenses
- FLUX.1-schnell concept image: Apache-2.0
- TRELLIS.2 output: MIT (DINOv3 encoder under Meta's DINOv3 licence; RMBG-2.0 not used, input had alpha)
- macOS Vision cut-out: local system framework

## Checkpoint
- Last completed step: [7] EXPORT — done (web/mushroom-cluster_final.glb, .blend saved)
- Timestamp: 2026-10-26
