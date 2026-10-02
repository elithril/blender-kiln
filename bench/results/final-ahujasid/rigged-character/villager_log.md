# Villager — Production Log

## Config
- Type: character (rigged, for animation in a web game)
- Target: glTF (GLB)
- Tier: lightweight (character soft range 3-8K tris)
- Style: low-poly
- Mode: auto
- Storage: compact
- Blender: 5.2.2 LTS, blender-mcp addon 1.8 (protocol 13, up to date)

## Reference Image
- Path: none
- Brief enrichment: none, brief only
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted modelling requested)
- Hunyuan3D params: N/A

## Source
- Method: scripted modelling (Blender Python, bmesh lofts + boxes), requested in the brief
- Scene: Blender factory scene; the default `Cube` was removed before building (rule 6 exception). Camera and Light left untouched.

## Pipeline
- Modelling: 24 parts (torso/tunic, neck, head, hair cap, eyes, nose, sleeves, wrists, hands, thumbs,
  trousers, boot shafts, boot feet, belt, buckle, pouch), T-pose, front −Y, feet on z = 0.
  Loops placed at the elbows (0.41/0.46/0.51 m) and knees (0.56/0.50/0.44 m) for deformation.
  Flat shading.
- Cleanup (per part): merge by distance 0.1 mm, degenerate dissolve, remove loose,
  recalc normals. 0 fused edges. Transforms at identity. Origin = centre of base.
  Open boundaries left on purpose, all hidden or single-sided by design: sleeve and trouser
  tops (inside the torso), hair rim, belt band. Materials are double-sided in the GLB.
- Joined into one skinned mesh `SK_Villager` (625 verts, 530 faces, 1,104 tris) — a single skin
  is the web-game convention. 7 materials → 7 primitives.
- Poly check: 1,104 tris, below the 3-8K lightweight character range. Not out of range
  (rule 4 alerts only when over), and in keeping with the low-poly style.
- Dimensions (get_object_info): 1.66 × 0.31 × 1.80 m (X wingspan × Y depth × Z height).
- Pose (rule 13): the SKILL's shoulder→hand snippet returned −90°. That is an artifact on this
  figure: its 0.75 H torso slice (1.35 m) cuts through the T-posed arm, whose underside is at
  1.325 m. Measured instead along the arm (upper-arm ring at |x| = 0.30 m → hand):
  **−0.9° both sides = T-pose**. Wingspan 1.66 m / height 1.80 m.
- Texturing: procedural Principled BSDF values only, no textures (low-poly style).
  Material audit (rule 19): every material is Principled BSDF + Output only, so nothing is lost on export.
  M_Villager_Skin, _Tunic (green), _Trousers (brown), _Leather (boots, belt, pouch), _Hair, _Eyes,
  _Buckle (metallic 0.9).

## Rig (rule 26)
- Measured first: 625 vertices / 20 → budget 31 deform bones. < 700 verts → hand-built rig.
- `SK_Villager_Armature`: 20 bones, 19 deforming, **32.9 verts per deform bone**.
  - `Root` (non-deform, at origin, on the ground) → `Hips` → `Spine` → `Chest` → `Neck` → `Head`
  - `Shoulder_L/R` → `UpperArm_L/R` → `LowerArm_L/R` → `Hand_L/R` (roll: local Z up)
  - `Thigh_L/R` → `Shin_L/R` → `Foot_L/R` (knee pre-bent 1 cm forward for IK)
  - Bone collections: `DEF`, `ROOT`.
- Skinning: weights computed in script, not `ARMATURE_AUTO`. Automatic weights skip disconnected
  parts (belt, buckle, pouch, eyes). Method: project each vertex onto its part's bone chain and
  blend linearly across a band at each joint (limbs 5 cm, wrist 3 cm, torso 6 cm). Head parts are
  rigid on Head, belt/pouch on Hips, boot feet on Foot. The tunic skirt follows the thighs up to 60 %,
  and the shoulder tops blend into Shoulder_L/R. Max 4 influences, normalised.
- Verification: 0 dead deform bones, 0 unweighted vertices, max 3 influences per vertex,
  `validate_character_rig` clean. Test pose (arm down, elbow 70°, hip −45°, knee 60°,
  spine and head turn) moved 560/625 vertices. Joints held their volume (screenshot checked),
  then reset to rest.
- No animation clips included (brief: "ready for animation"). The rest pose is the T-pose.
- glTF exports constraints and IK neither, so none were added. Animate in the engine or in Blender with keyframes.

## Export / Optimize
- `villager_original.glb`: 112.9 KB — export_apply=False, skins on, all 20 bones as joints
  (export_def_bones=False, so that the non-deforming Root ships for root motion).
  Khronos validator: 0 errors, 1 warning, NODE_SKINNED_MESH_NON_ROOT (standard for Blender
  skinned exports; the armature is at identity, so no effect). No `neutral_bone`.
- Optimize (auto, rule 20 individual steps): no textures, so resize/WebP do not apply →
  `gltf-transform draco` → `villager_final.glb` **18.3 KB (−84 %)**. Validator 0 errors
  (it cannot inspect Draco buffers — so it was verified by re-import instead).
- Re-import check, headless Blender, both GLBs: 20 bones, 20 groups, 2,112 split verts, 1,104 tris,
  0 unweighted. Rotating Thigh_L 40° moves the same 339 vertices in each file.
- Client needs a Draco decoder (three.js DRACOLoader). `villager_original.glb` loads without one.

## Deviations
- One stray scratch file written by mistake to `/tmp/null` (a shell redirect) during validation. Deleted straight away.

## Licenses
- All geometry and materials created from scratch in this session — no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30 21:45
