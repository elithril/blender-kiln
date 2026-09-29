# Villager — Production Log

## Config
- Type: character (rigged, T-pose rest)
- Target: glTF (GLB), web game
- Tier: lightweight (3-8K tris soft range)
- Style: low-poly
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.7 (protocol 11, up to date), macOS arm64

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python), chosen by the brief
- Body: Skin modifier over a 30-vertex T-pose skeleton (arms branch from an upper-chest node — branching them
  from the mid-chest node produced 3 disconnected islands), then Subdivision level 1, both applied, flat shaded
- Parts: head (UV sphere 10x8), nose, eyes, hair shell, straw hat (brim + crown), tunic skirt, belt, buckle —
  joined into one skinned mesh `SK_Villager`

## Pipeline
- Import: implicit (scripted). 1,013 faces / 2,014 tris / 1,037 verts, bbox 1.572 x 0.500 x 1.872 m
  (1.87 m includes the hat; wingspan 1.57 m)
- Pose check (rule 13): T-pose by construction. Arm-axis angle measured at **0.04 deg**.
  NOTE: the SKILL.md shoulder-to-hand snippet reported **-43.4 deg** on this mesh — a false A-pose reading.
  In a true T-pose the arms lie at ~0.75·H, so the "torso width" slice at 0.75·H picks up the arm itself and the
  "shoulder" lands near the hand tip. Measured the axis along the arm instead.
- Cleanup: merge by distance (0 merged), recalc normals, remove loose (0), degenerate dissolve (none),
  grounded (-0.018 m), transforms applied, Smart UV project, orphans purged.
  24 non-manifold edges = the open belt band (deliberate, sits against the body)
- Poly check: 2,014 tris — **below** the lightweight soft range (3-8K). Consistent with the low-poly style; not padded
- Texturing: skipped (scripted with materials) — 9 Principled BSDF flat-value materials:
  M_Fabric_Tunic_Green, M_Fabric_Trousers_Brown, M_Leather_Boots_Dark, M_Skin_Villager, M_Eye_Dark,
  M_Hair_Brown, M_Straw_Hat, M_Leather_Belt, M_Metal_Buckle. Material audit: all glTF compatible
- Rig selection (rule 26): 1,037 verts / 19 deform bones = **54.6 verts/bone**.
  DEVIATION from the PHASE 5c table (700-3,000 verts -> Rigify basic human, 35 deform): hand-built 20-bone rig
  (Root non-deform + 19 deform). Reason: web-game target wants a clean, flat, engine-friendly hierarchy with no
  control/mechanism bones; density is well above the 20 verts/bone floor either way.
  Bones: Root, Hips, Spine, Chest, Neck, Head, Shoulder/UpperArm/LowerArm/Hand _L/_R,
  UpperLeg/LowerLeg/Foot _L/_R. `_L/_R` suffixes instead of `.L/.R` because three.js strips dots from node names.
- Skinning: ARMATURE_AUTO for the body. Auto weights left 104 accessory verts unweighted (hat brim, skirt, belt,
  buckle), so accessories were bound explicitly: head parts -> Head 1.0, belt/buckle -> Hips 1.0, skirt blended
  Hips/UpperLeg by side and height. Then limit 4 influences, clean <0.01, normalize.
  Verified: 0 dead deform bones, max 4 influences, 0 unweighted, 0 non-normalized
- Deformation test: arms down 65 deg, elbows 40 deg, leg step, head turn — volume held, head/hat attached. Reset to rest
- Rig validator (characters.md): no warnings
- Optimize: not run (interactive step). Proposed: meshopt or Draco via gltf-transform (no textures to compress)
- Export: GLB, export_apply=False, skins on, export_def_bones=False (keeps Root at origin as a joint for root motion),
  no animations (none authored). **238.6 kB, 2,014 tris, 1 skin / 20 joints, 9 primitives**
- gltf-transform validate: 0 errors, 1 warning NODE_SKINNED_MESH_NON_ROOT (standard for Blender exports, armature
  is at identity so harmless), infos: unused TEXCOORD_0 (no textures yet)

## Files (compact)
- villager_final.glb — 238.6 kB
- villager.blend — full history (no `_original` file: scripted asset, nothing was imported)
- villager_log.md

## Licenses
- All geometry and materials authored in-session by script. No third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 16:12
