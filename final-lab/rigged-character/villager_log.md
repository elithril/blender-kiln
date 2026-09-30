# Villager — Production Log

## Config
- Type: character (rigged, for animation in a web game)
- Target: glTF (GLB)
- Tier: lightweight (character range 3-8K tris)
- Style: low-poly
- Mode: auto
- Storage: compact
- MCP: official Blender Lab MCP, Blender 5.2.2 LTS

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from the text brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted modeling (Blender Python, bmesh lofts + primitives), as requested
- Scene: Blender factory scene. The default Cube was removed (rule 6 exception). Camera and Light were left in place and are not exported.

## Pipeline
- Build: 21 parts (tunic, belt, buckle, neck, head, hair, nose, eyes, ears, legs, boots, arms, hands, thumbs), all modeled in T-pose, front -Y, 1 unit = 1 m
- Review fixes: the hair fringe covered the eyes, so the hair line was raised and the eyes made smaller. The top of the trouser legs poked through the tunic below the belt, so the leg top was pulled in.
- Cleanup: merge by distance (0 merged), degenerate dissolve, normals recalculated, transforms applied, origin at the base between the feet (0,0,0). Fused edges: 0. N-gons: 0. 40 open edges by design: the belt band and the hair rim.
- Mesh: SK_Villager — 662 verts, 1,206 tris, bbox 1.64 x 0.32 x 1.758 m
- Poly check: 1,206 tris is BELOW the lightweight range (3-8K). This was intentional for the low-poly style and to stay under the 700-vertex rig gate. Not above range, so no decimation question.
- Pose (rule 13): built as a T-pose. The arm bones are horizontal (0 deg) and the wingspan is 1.64 m for a height of 1.76 m. The standard shoulder-to-hand snippet reported -17.1 deg. That is a measurement artifact, not the pose: in a true T-pose the 0.75·H slice cuts through the arm, so the snippet takes a forearm vertex as the shoulder.
- Rig gate (rule 26): 662 verts, which is under 700, so a hand-built rig of 12-20 bones. Result: 19 deform bones, 34.8 verts per bone.
  - Bones: Root (non-deforming, at the origin) > Hips > Spine > Chest > Neck > Head; Shoulder/UpperArm/LowerArm/Hand _L/_R; UpperLeg/LowerLeg/Foot _L/_R
  - Rolls: arms point Z up, legs and spine point Z to -Y. The knee is offset 1 cm forward so IK bends the right way.
- Skinning: weights are computed by script, not with ARMATURE_AUTO. Each part may only follow a set list of bones (head parts: Head only; buckle: Hips; tunic: Hips/Spine/Chest/Shoulders, plus weaker UpperArm and UpperLeg). Weight is inverse distance to each bone segment, power 8, at most 3 influences, pruned below 0.03, then normalized. This avoids the known heat-weighting gap on disconnected parts (belt, buckle, eyes).
  - Checks: dead deform bones 0 of 19. Max influences per vertex 3. Vertices not fully weighted 0. validate_character_rig(): no warnings.
  - Test pose (arms down 55 deg, elbow bent 60 deg, knee raised 40/-60 deg, spine 10 deg, head turned 25 deg) checked from two angles: no tearing, head attached, volume held. Reset to rest (T-pose) before export.
- Texturing: 8 flat Principled BSDF materials, no image textures: M_Fabric_Tunic, M_Fabric_Trousers, M_Leather_Boots, M_Leather_Belt, M_Metal_Brass, M_Skin, M_Hair, M_Eyes. No UV textures needed.
- Material audit (rule 19): 8/8 Principled, 0 procedural nodes.
- Export: villager_original.glb, 121.5 kB (export_apply=False, skins on, no animations, no Draco)
- Optimize: no textures, so resize and WebP had nothing to do. Draco only (gltf-transform draco): 121.5 kB to 21.0 kB (-83%).
- Validation: gltf-transform validate exits 0 on both _original and _final. 1 skin, 20 joints (Root + 19), no neutral_bone. 1 mesh, 8 primitives, 1,206 tris.
- Notes for integration:
  - _final.glb needs a Draco decoder on the client (Three.js: DRACOLoader). _original.glb has no compression if you prefer no decoder.
  - The mesh has 8 primitives (one per material), so 8 draw calls.
  - Materials export as doubleSided because Blender backface culling is off. The open hair rim needs it.
  - No animation clips are included. The rig is ready for keyframing or for retargeting from a T-pose source.

## Licenses
- All geometry and materials were created from scratch in this session. No third-party assets.

## Files (compact)
- villager_original.glb, villager_final.glb, villager.blend, villager_log.md

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-30 22:16
