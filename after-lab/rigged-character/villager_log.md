# Villager — Production Log

## Config
- Type: character (humanoid NPC, rigged)
- Target: glTF (GLB), web game
- Tier: lightweight (character soft range 3-8K tris)
- Style: low-poly
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS via the official Blender Lab MCP

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted modeling requested)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python)
- Body: Skin modifier over a 22-node T-pose skeleton graph → applied → symmetrized +X→-X → Subdivision level 1 applied
- Parts: hair cap (UV-sphere shell), nose, eyes, belt + buckle (band ray-cast onto the torso), joined into one skinned mesh
- Factory scene: default Cube removed (rule 6 exception); Camera and Light left untouched and not exported

## Pipeline
- Import: scripted, no import. Object SK_Villager / SK_Villager_Mesh, collection Characters_NPC
- Pose (rule 13): shoulder→hand angle measured at -6.3 deg → T-pose, no conversion
- Dimensions: 1.47 (wingspan) × 0.28 × 1.67 m; wingspan/height = 0.88 (short stylised arms)
- Cleanup: 791 verts / 762 faces / 1,514 tris; merge doubles 0, degenerate 0, loose 0, normals recalculated,
  fused edges 0, open edges 46 (hair cap rim + belt band, intentional), transforms applied, feet on z=0, origin at base
- Poly budget: 1,514 tris — below the lightweight character range (3-8K); not an issue for low-poly
- Texturing: skipped (scripted with materials). 7 flat Principled BSDF materials, no image textures, no UVs:
  M_Skin_Villager, M_Fabric_Tunic_Green, M_Fabric_Trousers_Brown, M_Leather_Boots_Dark,
  M_Leather_Belt_Tan, M_Hair_Brown, M_Eye_Dark. Backface culling on (single-sided in glTF)
- Rig selection (rule 26): body = 686 connected verts (+105 in accessory islands) → < 700 tier → hand-built rig.
  SK_Villager_Armature: 20 bones, 19 deform + Root (non-deform, at origin):
  Root > Hips > Spine > Chest > Neck > Head; Chest > Shoulder_L/R > UpperArm > LowerArm > Hand;
  Hips > UpperLeg_L/R > LowerLeg > Foot. 36 body verts per deform bone
- Skinning: ARMATURE_AUTO on body; 40 accessory verts came out unweighted → bound rigidly
  (hair/eyes/nose → Head, belt/buckle → Hips). Clean < 0.01, limit 4 influences, normalize all.
  Verified: 0 dead groups, 0 unweighted, max 4 influences, weight sums = 1.0, validator 0 warnings
- Deformation test: arms down, elbow, thigh forward + knee, head turn, spine lean → 611/791 verts moved,
  head attached, knee bends correctly; pose cleared back to rest before export
- Material audit (rule 19): all 7 materials glTF-compatible, no procedural nodes
- Optimize: gltf-transform draco (q-position 14, q-normal 10), no textures so no resize/webp;
  154.4 KB → 22.8 KB (-85%). Requires a Draco decoder client-side (three.js DRACOLoader)
- Export: GLB, skinned, 1 mesh / 7 primitives, 1,514 tris, 20 joints, no animations.
  gltf-transform validate: 0 errors on both files (info: NODE_SKINNED_MESH_NON_ROOT, standard for Blender)
- Round-trip: villager_final.glb re-imported → 20 bones, 1,514 tris, 0 unweighted verts, arm pose deforms

## Licenses
- All geometry and materials: original, created by script in this session — no third-party resources

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 20:31
