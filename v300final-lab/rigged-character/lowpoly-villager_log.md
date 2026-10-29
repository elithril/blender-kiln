# Low-poly Villager — Production Log

## Config
- Type: character (humanoid biped)
- Target: glTF (web game)
- Tier: lightweight (character 3-8K tris)
- Style: low-poly
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling (requested)
- Rig: yes → T-pose (rule 13)
- Live view: off (benchmark-style auto run, nobody watching a browser)
- Output: /private/tmp/kiln-bench/v300final-lab/rigged-character/work/generated-assets/lowpoly-villager/
- Environment: Blender 5.2.2 LTS via the official Blender Lab MCP; SkinTokens (tools/autorig.py) installed, tested version

## Reference Image
- Path: none
- Brief enrichment: assumptions (auto mode) — adult villager ~1.75 m, simple tunic with belt, trousers, boots, short hair; faceted flat-shaded look, palette materials only
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)

## Source
- Method: scripted (Blender Python)

## Pipeline
- CONFIG/BRIEF: brief confirmed as above (auto mode, assumptions stated)
- Source: factory scene (Cube, Camera, Light, no .blend) — Cube removed before building (rule 6). Script scripts/build_villager.py: one skin from a Skin-modifier skeleton (21 nodes, T-pose) + Subdivision level 1, applied; flat shading; materials by region (skin, hair, tunic, belt, pants, boots). Eyes = separate object SK_Villager_Eyes (2 boxes, ray-cast onto the face). v1 (1,428 tris) read as a mannequin (thin head merged with neck, thin limbs, eyes buried) → v2: wider radii, separate jaw/head nodes, eyes ray-cast: kept.
- Import: scripted, in Blender. SK_Villager 588 verts / 586 faces / 1,172 tris; eyes 24 tris. Box X -0.786..0.786, Y -0.128..0.141, Z 0..1.778 m (1.78 m tall, feet on Z=0). Pose: arm centreline +0.1 deg both sides → T-pose (the reference 'torso width at 0.75 H' snippet read -52.6 deg: at this height the slice cuts the arms themselves — artifact, centreline used). Wingspan 1.57 m / height 1.78 m.
- Cleanup: transforms applied; weld 1e-4 with normals kept → 0 merged (Skin modifier output already welded); normals consistent; loose removed 0; degenerate 0; fused edges 0, open edges 0 (closed skin); origin at base centre; 6 orphan blocks purged; no empty slots. Poly: 1,196 tris total — BELOW the lightweight character range (3-8K): soft range, kept on purpose for a faceted low-poly look; no decimation.
- Texturing: skipped — scripted with flat Principled materials (7: M_Villager_Skin/Hair/Tunic/Belt/Pants/Boots/Eyes), no image textures, no UVs needed.
- Rig: rule 26 — 588 welded skin verts → budget ~29 deform bones. Humanoid + SkinTokens installed (autorig.py status exit 0) → `autorig.py rig --asset lowpoly-villager.blend --object SK_Villager --body humanoid --out rig/` (54 s). Result: 22 bones, all deform, Mixamo names (Hips…Head, Left/Right Shoulder/Arm/ForeArm/Hand, UpLeg/Leg/Foot/ToeBase); 26.7 verts/bone; dead bones 0; max influences 4; unweighted 0; eyes → 100% Head. Validator: only 🟡 root bone 'Hips' (kept: Mixamo name expected by tools/presets.py). Weights symmetric (LeftArm/RightArm 16 verts each, forearms 24 each). Bent pose (thighs 60° fwd, knees 75°, arms 45° fwd, elbows 75°, Spine1 20°, Neck 30°) looked at in matcap and colour: no tear, head attached, eyes follow. Rest pose reset = T-pose. Duplicate .001 materials from the rig round-trip remapped onto the originals; mesh data renamed SK_Villager_Mesh / SK_Villager_Eyes_Mesh.
- Animate: not requested — skipped (rig ready for tools/presets.py: walk, run, idle…).
- Optimize: no textures (WebP step n/a). Backface culling on (closed skin → doubleSided false). Draco via gltf-transform draco (q pos 14, normal 10): 127.3 KB → 23.3 KB (-82%). Preview = copy of original (no Draco, no WebP: extensionsUsed none).
- Export: material audit clean (no procedural nodes, all Principled). glTF GLB, export_apply=False, skins on, export_def_bones, no animations. web/lowpoly-villager_final.glb 23.3 KB, 1,196 tris (body 1,172 + eyes 24), 22 joints, 7 materials, 1.78 m, on the ground. Headless review renders of the final GLB (review/, matcap + colour, q1/q3/front/back + face close-up): loads, decodes, correct. Note: eye boxes sit partly inside the face (visible as dark eyes in colour). studio.py checks: no WARN (triangles below tier = note).

## Licenses
- Model: built from scratch in this session — no third-party assets
- SkinTokens (auto-rig): MIT code and checkpoints; kiln patch Apache-2.0

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22 14:38
