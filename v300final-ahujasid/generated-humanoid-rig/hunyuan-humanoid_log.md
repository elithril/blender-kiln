# Hunyuan Humanoid — Production Log

## Config
- Type: character (humanoid biped)
- Target: glTF
- Tier: balanced
- Style: stylized
- Mode: auto
- Storage: compact
- 3D Backend: none (user's own generated mesh; no marketplace, no new AI generation)
- Live view: off (unattended auto run — Studio command given in hand-over)
- Output: /private/tmp/kiln-bench/v300final-ahujasid/generated-humanoid-rig/work/generated-assets/hunyuan-humanoid/

## Brief
"Rig this character for animation" — user-provided Hunyuan3D-2 generated humanoid, keep its shape
(no reshaping, no regeneration), rig it, export glTF.
Assumptions (auto mode): real size = a stylised adult figure ~1.7 m if the import scale is
unitless; front = -Y; no animation clips requested (rig only, [5d] skipped).

## Reference Image
- Path: none (mesh supplied directly)
- Visual comparison: N/A

## Prompts (copy-paste ready)
- None — no generation in this session. Source generated upstream by Hunyuan3D-2.

## Source
- Method: user-provided AI mesh (Hunyuan3D-2 demo output)
- File: /private/tmp/kiln-bench/v300final-ahujasid/generated-humanoid-rig/refs/hunyuan/hunyuan_demo_1.glb (720,764 bytes)

## Pipeline
- Config/Brief: done. Environment: Blender 5.2.2 LTS via mcp-for-blender (protocol 14, up to date); SkinTokens installed (autorig status exit 0).
- Source: user file, no search, no generation.

- Import: 19,996 verts / 40,000 tris, one mesh `geometry_0` under an importer empty `world` (unparented, empty removed), no UVs, no textures (white mesh). Factory Cube removed from the untouched factory scene (rule 6 exception). Renamed SK_HunyuanHumanoid / SK_HunyuanHumanoid_Mesh. Size 0.734 x 0.593 x 1.084 m — kept 1:1 (a chibi child figure ~1.08 m tall; assumption, auto mode). Faces -Y (face seen in front view).
- Pose (rule 13): measured shoulder->hand. Left arm -58.9 deg (arm down, I-pose range); right arm akimbo -50.2 deg with the hand FUSED into the hip. NOT converted to T-pose: the brief says "keep its shape", and the fused hand cannot be lifted without cutting the mesh (destructive, rule 6). Rigged in its as-generated pose — the route characters.md measured on this exact mesh (SkinTokens, --allow-missing RightHand).
- Cleanup: transforms applied; merge by distance 1e-4 → 0 merged (already welded), normals kept; normals made consistent; loose 0; degenerate 0; fused edges 0, open edges 0 (closed), 1 island; origin moved to base centre (z min 0.000). 40,000 → 40,000 tris. Poly check: balanced character tier 8-20K tris → 40K = exactly 2x the top, not past it: reported, no decimate proposed (and the brief says keep the shape). Orphan material removed.
- Texturing [5b]: skipped by choice — rig-only brief, no reference colours, no UVs. One neutral Principled material M_HunyuanHumanoid_Clay (base 0.80/0.78/0.75, rough 0.6) assigned so the glTF has a defined material. Texturing offered as follow-up.

- Rig [5c]: route = generated humanoid → tools/autorig.py rig (SkinTokens, status exit 0), --body humanoid, 52.4 s. Rule 26: 19,996 welded verts / 28 deform bones = 714 verts/bone (tool reports 4,285 on the 119,980 split-corner export it read). 28 bones, Mixamo/kiln names, root Hips; full arm chains both sides incl. RightHand + 3 finger bones (no --allow-missing needed this run, unlike the run documented in characters.md). Dead bones 0, max influences 4, unweighted 0, 18 speck islands cleaned.
  Weld check: split corner copies carried identical weights (max diff 0) → rigged mesh re-welded 119,980 → 19,996 verts, flat shading kept (use_smooth off, as the source imports). Bone display icosphere (importer artefact) removed.
  Validator: only "🟡 root bone named 'Hips', expected 'Root'" — kept on purpose (kiln/Mixamo skeleton; presets.py and retargeting expect Hips).
  Bent pose (thigh -60, knee 75, arm -45 fwd, elbow 75, Spine1 20, neck 30): skin holds, nothing detaches. Edge stretch: 429 edges >2x of 60k, worst 23x at the RIGHT HAND fused into the hip (hand/forearm/upleg/hips weights mix there) — inherent to the generated mesh; ~1 cm pinch under the chin where the 50 deg head pitch meets the right shoulder (no neck on the chibi). Rest pose restored, drift 9e-8 m.
- Animate [5d]: skipped — not requested.

- Optimize [6]: no textures (no WebP step); Draco via `gltf-transform draco` (no optimize/simplify, rule 20): 5.77 MB → 245 KB (−95.8%). Size of the uncompressed file is the flat shading: the source GLB carries POSITION only, so glTF shades it flat and every corner is split (119,978 GPU verts) — kept, it is the source's look.
- Export [7]: material audit pass (Principled only). glTF, export_apply=False, skins on, deform bones only.
  - web/hunyuan-humanoid_final.glb — 245,280 B, Draco (needs a Draco decoder client-side), 40,000 tris, 1 skin, 28 joints; gltf-transform validate: 0 errors, 0 warnings.
  - hunyuan-humanoid_original.glb — 5,769,552 B, rigged, uncompressed (pre-optimize export).
  - hunyuan-humanoid_preview.glb — copy of _original, no Draco/WebP (extensionsUsed: none) — opens in macOS Quick Look.
  - hunyuan-humanoid.blend — scene: SK_HunyuanHumanoid (skinned) + SK_HunyuanHumanoid_Armature, rest pose.
  - Intermediates kept (compact, auto mode, nobody to answer): SK_HunyuanHumanoid.glb (cleaned mesh fed to autorig, 3.4 MB), rig/ (autorig's raw rigged .glb + .blend).

## Licenses
- hunyuan_demo_1.glb: output of Tencent Hunyuan3D-2 — Tencent Hunyuan Community License (territory excludes EU, UK, South Korea; >100M MAU needs a licence). Provided by the user.
- SkinTokens (auto-rig): MIT code and checkpoints; kiln Mac patch Apache-2.0.

## Checkpoint
- Last completed step: [7] EXPORT
- Timestamp: 2026-10-23 10:12
