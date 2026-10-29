# Fantasy Mushroom Cluster — Production Log

## Config
- Type: prop
- Target: glTF (web/)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: stylized
- Mode: auto (standing answer: take the recommended option at every choice)
- Storage: compact
- 3D backend: hf-spaces (TRELLIS.2 first)
- Output: /private/tmp/kiln-bench/v300final-lab/ai-mushrooms/work/generated-assets/fantasy-mushroom-cluster
- Environment: macOS, Apple M4 Pro 24 GB unified; Blender 5.2.2 LTS via the official Blender Lab MCP; gradio_client 2.7.1 (venv); gltf-transform + gltfpack present
- Spaces (2026-10-23): microsoft/TRELLIS.2 RUNNING, trellis-community/TRELLIS RUNNING, black-forest-labs/FLUX.1-schnell RUNNING, stabilityai/TripoSR RUNTIME_ERROR
- HF account used for Space quota: the user's saved account (anonymous offered; recommended account kept — anonymous 2 min quota too small)

## Brief
- Three stylized fantasy mushrooms, spotted caps, grouped as one cluster on a small shared base, for a forest scene.
- Assumptions (auto mode): tallest mushroom 0.40 m; cluster footprint ~0.35-0.45 m; front -Y, origin centre of base, base on Z=0. No ground/environment generated (rule 9).

## Reference Image
- Path: source/concept.png (FLUX.1-schnell), cut-out source/concept_cutout.png
- Scale: 693 px total height = 0.40 m (assumption) -> 0.577 mm/px. Camera elevation ~10 deg (estimate from the drop-shadow ellipse, ratio ~0.15), azimuth 0 (model laid out to read as the concept from the front, -Y)
- Palette sampled (sRGB 10/50/90 %): cap red 251,78,36 / 252,84,40 / 252,91,43; cap rim dark 160,35,25 / 176,49,33; spots 253,245,198; stem 240,192,138 / 253,221,168 / 255,228,176; gills 147,97,53 / 175,123,79 / 213,165,113; moss 84,107,24 / 107,131,36 / 136,165,41; bead 245,62,37
- Inventory (part, how it meets):
  - large mushroom: tall rounded-cone cap R~0.10 H~0.20 leaning left ~9 deg, ~10 big cream spots, darker rim -> SM_..._CapLarge; thick cream stem r~0.025-0.03, ENTERS the cap underside and the moss -> SM_..._StemLarge
  - medium mushroom: dome cap R~0.063 H~0.09, smaller spots, in front of the large one -> CapMedium; stem r~0.02 enters cap + moss -> StemMedium
  - small/front mushroom: dome cap R~0.068 H~0.075 tilted right and toward the camera, gills visible -> CapSmall; curved stem r~0.022 -> StemSmall
  - gills: radial lines, tan, darker toward the stem -> underside of every cap (same mesh, own UV band)
  - moss clump: spiky green lobes, flat underside, holds all three stems -> SM_..._Moss
  - tiny red spotted bead on the front of the moss, resting on it -> SM_..._Bead
  - unseen: the back of the cluster (concept shows the front only) — kept plain: moss lobes and spots continue around, nothing invented
- Visual comparison: pending (fidelity_check after build)

## Prompts (copy-paste ready)
- Concept art: "a cluster of three stylized fantasy mushrooms growing together from one small mossy clump, one tall, one medium, one small, red caps with large white spots, cream stems, stylized 3D game asset, soft smooth shading, no outlines, no ink lines, centered, isolated on a plain white background, three-quarter view, single object, no ground, no shadow" (source: flux-schnell, seed 42, 1024x1024, 4 steps)
- Cut-out: tools/cutout.swift (macOS Vision, local) -> source/concept_cutout.png; drop shadow removed, clean
- Generation params attempted: microsoft/TRELLIS.2 /image_to_3d seed=42 resolution=1024 (then 512), /extract_glb decimation_target=100000 texture_size=1024; trellis-community/TRELLIS /generate_and_extract_glb seed=42 mesh_simplify=0.95 texture_size=1024

## Source
- Attempt 1 (AI, brief's choice): FAILED — ZeroGPU quota.
  - https://huggingface.co/spaces/microsoft/TRELLIS.2 (account): "120s requested vs. 149s left", reset in ~23:54 (x3, at 1024 and 512)
  - https://huggingface.co/spaces/trellis-community/TRELLIS (account): same refusal
  - TRELLIS.2 anonymous (token=False): "120s requested vs. 0s left" (x2)
  - https://huggingface.co/spaces/stabilityai/TripoSR: RUNTIME_ERROR, skipped
  - No quota consumed by the refused calls; nothing paid (rule 5). Another Space URL can be given later (rule 8).
- Decision (auto, recommended option): scripted modelling in Blender from the FLUX concept as reference image (ai-generation.md § When the quota is spent, option 3; stylized prop -> scripted). Rejected: wait 24 h, Hunyuan3D (licence excludes EU, on request only), local TRELLIS.2 (31 GB install unasked), paid PRO (rule 5).
- Method: scripted (Blender Python), reference = source/concept.png

## Pipeline
- Build (scripted, scripts/build.py, in the live Blender — factory scene only; factory Cube removed before building, Camera/Light left untouched): 8 parts parented to empty SM_FantasyMushroomCluster — StemLarge/Medium/Small (bezier tubes, enter moss + cap), CapLarge/Medium/Small (lathe, closed, gills underside), Bead, Moss (7 icosphere lobes + 200 three-sided tufts). One 1024 atlas T_FantasyMushroomCluster_BaseColor painted by numpy (cap gradient + 3D-placed spots, radial gills, stem gradient, moss gradient strip); materials M_Mushroom_Stylized, M_Moss_Stylized (same image, image textures only — glTF-safe)
- v1: moss shown grey (vertex colours only) and faceted -> moss colour moved into the atlas, lobes smooth + tufts
- v2 bug: icosphere vertex-set diff collapsed 6 of 7 lobes; fixed with the op's returned verts, subdivisions=3
- Round 1 (v2, fidelity_check front, elev 10, az 0, .blend): silhouette 0.772; bands 0.78/0.86/0.68/0.74/0.82; widths -9/-15/-19/-4/+18 %; 5,928 tris (+19 % over 5K, in moss tufts — reported, not cut). Gaps: front-right mushroom too far left/low/small; moss too wide on the left; stems thin; tall cap lean. Face block (dark marks) not meaningful here: the photo's details are light spots
  - changed for round 2 (half-way): small mushroom +8 mm X, +10 mm Z, R 68->75 mm; stems +15 %; tall cap lean 9->12 deg, R 102->107 mm; left moss lobes pulled in 8-16 mm
- Round 2 (v3): silhouette 0.837 (from 0.772); widths -5/-11/-5/-1/+7 %. Kept. Side-by-side: medium mushroom hidden behind the tall cap (concept: clearly in front); spots much smaller than the concept's
  - changed for round 3: medium mushroom 58 mm forward (y -0.012 -> -0.070); spot radii ~+25 % (material: one change)
- Round 3 (v4, last — two correction rounds): silhouette 0.835 (held); widths -5/-11/-5/-1/+7 %. Medium mushroom now in front as in the concept, spots larger. Kept. Remaining known differences: concept's tall cap rim flares lower on the left; concept moss is a soft fur, ours lobes + spikes; stems straighter than the concept's
- Joints: 3 stem->cap / stem->moss joints rendered (review/front/joints/) and looked at; all stem tops measured inside their caps; under view shows no stem foot below the moss
- Inventory ticked at final review: 3 mushrooms with spotted caps ✔, tall cap leaning left ✔, medium in front ✔, front-right tilted with gills ✔, stems entering caps+moss ✔, spiky moss ✔, bead ✔. Back side unseen in the concept: plain moss + spots continue, nothing invented
- Visual comparison: close match (stylized reinterpretation of the concept)
- [4] IMPORT: implicit (scripted). 0.323 x 0.277 x 0.401 m, base on Z=0, centred XY, 1 unit = 1 m; names SM_FantasyMushroomCluster_{part}, data SM_..._{part}_Mesh
- [5] CLEANUP (scripts/cleanup.py): transforms applied, merge 1e-4 -> 0 merged (built welded), loose 0, degenerate 0, fused edges 0 on every part, open edges 600 = the 200 tuft bases on the moss (by design, not a watertight asset). Poly: 5,928 tris vs balanced 1.5-5K (+19 %, under 2x) — kept, 2,840 in the moss (lobes + tufts), caps 2,272, stems 648, bead 168. No decimate proposed (below 2x)
- UV check (tools/uv_check.py): first run 4 FAIL (stem end-cap fans collapsed, moss 1-D gradient UVs) -> fixed (wedge UVs on hidden stem ends, moss v spread within its uniform band) -> 0 FAIL, 6 WARN (moss overlap/flip by design: gradient lookup, no bake/normal map; stem hidden end wedges; cap/bead pole stretch 12-15 %)
- [5b] TEXTURING: skipped — scripted with materials + painted atlas assigned (T_FantasyMushroomCluster_BaseColor 1024, sRGB bytes, packed)
- Material export audit (rule 19): Principled only, one packed 1024 sRGB byte image, no procedural nodes — glTF-safe. No modifiers on any part (export_apply=False, rule 18). Mesh data renamed SM_..._Mesh (.001 suffixes from rebuilds removed)
- [6] OPTIMIZE (auto, glTF): fantasy-mushroom-cluster_original.glb 399 KB -> gltf-transform resize 1024 -> webp q90 -> draco -> web/fantasy-mushroom-cluster_final.glb 75.8 KB (-81 %). fantasy-mushroom-cluster_preview.glb = copy of _original (no Draco, no WebP: extensionsUsed [] — opens in Quick Look). No simplify / decimate / LOD. Intermediates (review/tmp resized/webp GLBs) deleted — compact storage, recommended option taken under the standing answer
- [7] EXPORT: web/fantasy-mushroom-cluster_final.glb, 75.8 KB, 5,928 tris, 8 meshes, 2 materials, 1 WebP texture 1024, KHR_draco_mesh_compression + EXT_texture_webp (needs a Draco decoder, e.g. three.js DRACOLoader). Final measure on the shipped file: silhouette 0.836 (rounds 0.771 -> 0.837 -> 0.835 -> 0.836); review renders of _final (q1, q3, top, under) in review/final — colours intact. studio.py checks: no WARN (notes: tris +19 %, Draco decoder, licences)
- Viewport look: the live Blender's splash screen covered the viewport capture, so every look was rendered headless with tools/review_renders.py and fidelity_check.py (review/v1, v2, v3, final, front)

## Licenses
- Concept image: FLUX.1-schnell output (Apache-2.0 model), generated this session
- Cut-out: macOS Vision (Apple system framework, run locally on the user's Mac — no third-party licence on the output)
- Review HDRI: studio_small_09 (Poly Haven, CC0) — review renders only, not in the asset. Source: Poly Haven (polyhaven.com), via the public API
- Geometry and texture: scripted this session (scripts/build.py) — no outside asset

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-23
