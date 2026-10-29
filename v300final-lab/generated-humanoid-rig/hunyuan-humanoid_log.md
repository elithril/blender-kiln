# Hunyuan Humanoid — Production Log

## Config
- Type: character (biped, chibi girl) — rig for animation
- Target: glTF (web/)
- Tier: balanced (character 8-20K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Backend: none — the user's existing mesh; no marketplace, no new AI generation
- Environment: Blender 5.2.2 LTS, official Blender Lab MCP (factory scene, no .blend open); SkinTokens auto-rig installed (tested version)
- Live view: off (Kiln Studio not started — auto run, nobody to watch)

## Reference Image
- Path: none (the mesh is the reference)
- Brief enrichment: chibi girl with bangs and two pigtails, overalls with a heart bib over a short-sleeved shirt, shorts, ankle boots; right hand on hip (akimbo), left arm hanging
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none
- Generation params: Hunyuan3D-2 demo output, given by the user (`refs/hunyuan/hunyuan_demo_1.glb`) — not regenerated

## Source
- Method: user-provided AI mesh (Hunyuan3D-2)

## Pipeline
- [1] CONFIG / [2] BRIEF — 2026-10-22: brief taken as given. Assumptions (auto mode): real height kept at the file's 1.084 m (a chibi child; within plausible range, scale not changed); facing -Y (checked on renders).
- Removed Blender's untouched factory Cube before import (rule 6 exception). Camera and Light left.
- [3] SOURCE: user mesh, copied unchanged as `hunyuan-humanoid_original.glb`.
- [4] Import: 40,000 tris (all triangles), 19,996 verts, no UVs, no material, no normals (flat). bbox 0.734 × 0.593 × 1.084 m. Importer's `world` empty removed (mesh unparented, transform kept). Renamed `SK_HunyuanHumanoid` / `SK_HunyuanHumanoid_Mesh`. Translated so the base centre sits at the origin, feet on z=0 (no scale, no rotation).
  - Pose measured (rule 13): left arm shoulder ≈ (0.17, 0.53) → hand ≈ (0.29, 0.31): **-61°, I-pose**. Right arm akimbo, **hand fused into the hip** (z ≈ 0.35). Widest X points are the pigtails, not the hands (excluded).
  - **Not converted to T-pose**: the brief says "keep its shape", and the right hand is fused to the hip — a conversion needs cutting it free (rule 6, never silent). Rigged in its own pose; SkinTokens is the route measured on this exact mesh (characters.md § Learned auto-rig).
  - Look: review/import/ (matcap front, q1, q3, left — headless, the live viewport was covered by Blender's splash screen).
- [5] Cleanup: 40,000 → 40,000 faces. Transforms applied; merge by distance 1e-4 → 0 merged (already welded); normals recalculated outward (signed volume +0.0914 m³); loose 0; degenerate 0; **1 island, 0 open edges, 0 fused edges** (closed manifold). Shade smooth (flag only — source had no normals, imported flat). Orphans purged.
  - Poly count: 40,000 tris = exactly 2× the balanced character top (20K) — not past it, kept (and the brief keeps the shape). No decimation proposed.
- [5b] Texturing: **held back**. White mesh, no UVs. A neutral `M_Clay_Neutral` (Principled, flat values) assigned so the glTF has a defined material. Painting regions (hair, skin, overalls, boots) on a single fused generated mesh is out of the brief's scope (rig, keep shape); offered as a follow-up.

- [5c] Rig — 2026-10-22 18:16: route = SkinTokens (`tools/autorig.py rig --body humanoid`, status exit 0, tested version), on the welded clean mesh. 46.8 s.
  - Rule 26: 19,996 verts / 28 deform bones = **714 verts/bone**; 0 dead bones; max 4 influences; 0 unweighted; 16 speck islands cleaned (31 weights). All required bones present this run — **RightHand included** (the earlier kiln measurement of this mesh had it missing; SkinTokens is not repeatable).
  - Skeleton (kiln/Mixamo names): Hips → Spine → Spine1 → Spine2 → Neck → Head; Left/Right Shoulder → Arm → ForeArm → Hand → Fingers → Fingers2 → Fingers3; Left/Right UpLeg → Leg → Foot → ToeBase.
  - Bent pose (thigh 60° fwd, knee 75°, arm 45° fwd, elbow 75°, Spine1 20°, neck 30°; `scripts/bent_pose.py`): **22,422 mm² new skin-through-skin** (legs 10,622, arms 6,550, body 5,251), **widest tear 0 mm**. kiln's reference on this mesh: SkinTokens 20,917, Rigify basic human 50,680. Look: review/bent/ (matcap q1, left) — head on, no tears; the right hand, fused to the hip, stays at the hip while the forearm stretches (mesh limit).
  - Validator (characters.md): no warning; root `Hips` (kiln convention), 28 bones all deforming.
  - Importer's bone-shape Icosphere removed; duplicated material folded back into M_Clay_Neutral. Clean unrigged mesh kept in the excluded collection `Stage_Clean_Unrigged` of the .blend.
- [5d] Animate: not asked — skipped. Route available: `tools/presets.py` (kiln-named humanoid).

- [6] Optimize — 2026-10-22 18:17: no textures (WebP step n/a); Draco level 6 on the web output via Blender's exporter (no `gltf-transform optimize`, rule 20). 1,130,488 B (rigged, uncompressed) → **183,944 B** (−84 %). Draco needs a decoder on the client. Geometry untouched (40,000 tris).
- [7] Export — glTF: material audit OK (M_Clay_Neutral, Principled, nothing lost); `export_apply=False`, skins on, `export_def_bones=True`, no animation.
  - `web/hunyuan-humanoid_final.glb` 183,944 B — KHR_draco_mesh_compression, 1 skin / 28 joints, no `neutral_bone`. `gltf-transform validate`: 0 errors, 0 warnings. Round trip: 19,996 verts, 40,000 tris, 28 bones, 0 unweighted, max 4 influences, height 1.0837 m, feet at z=0.
  - `hunyuan-humanoid_preview.glb` / `hunyuan-humanoid_rigged.glb` 1,130,488 B — no extensions (opens in macOS Quick Look).
  - Look: review/final/ (matcap + colour, q1 and q3) — shape as imported, rest pose intact.
  - .blend saved (`hunyuan-humanoid.blend`: SK_HunyuanHumanoid + SK_HunyuanHumanoid_Armature; clean unrigged stage in excluded collection).
  - Kept (auto mode, nobody to answer — listed for the end-of-session cleanup): `hunyuan-humanoid_clean.glb`, `rig/` (autorig .blend + raw rigged GLB), `review/`, `scripts/` (bent_pose.py, roundtrip.py).

## Licenses
- hunyuan_demo_1.glb: output of Tencent Hunyuan3D-2 — Tencent Hunyuan Community License (not valid in the EU, UK, South Korea; >1M MAU needs a separate licence). Provided by the user.
- SkinTokens (auto-rig): MIT code and checkpoints; kiln Mac patch Apache-2.0.

## Checkpoint
- Last completed step: [7] EXPORT
- Timestamp: 2026-10-22 18:18
