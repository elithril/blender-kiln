# Low-Poly Villager — Production Log

## Config
- Type: character (rigged, web game)
- Target: glTF (GLB)
- Tier: lightweight
- Style: low-poly
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python / bmesh), Blender 5.2.2 LTS via Blender Lab MCP
- Parts built separately (16): Torso, Belt, Neck, Head, Hair, Nose, Eye_L/R, Arm_L/R, Hand_L/R, Leg_L/R, Boot_L/R — 8-sided lathed tubes with edge loops at elbows/knees/waist/chest, boxes for hands/boots/eyes/nose
- Pose: T-pose, measured arm axis 0.0 deg (L) / 0.0 deg (R)
  - Note: the SKILL.md shoulder-to-hand recipe returned -90 deg here — its 0.75*H torso slice
    intersects the arms/hands on this short-torso stylised figure (arms at 0.78*H), so "torso width"
    became the hand. Re-measured on shoulder/hand centroids instead.
  - Wingspan 1.36 m vs height 1.78 m: stylised proportions, the "wingspan ≈ height" heuristic does not apply.

## Pipeline
- Import: implicit (scripted). 720 tris, 392 verts, bbox 1.36 x 0.29 x 1.78 m, origin at base centre (0,0,0), front -Y
- Cleanup: 720 -> 720 tris. merge by distance (0 removed), remove loose (0), dissolve degenerate, recalc normals, apply transforms (all identity). Parts joined into SK_Villager after weighting; 15 orphaned per-part mesh datablocks from the join removed.
  - Leg top rings pulled in (r 0.09 -> 0.075, 16 verts) to stop them poking through the tunic at the hip.
- Poly budget: 720 tris is BELOW the lightweight character range (3-8K). Intentional for low-poly style; not above range, so no decimate proposal.
- Texturing: skipped — scripted with Principled BSDF flat colours: M_Skin_Villager, M_Fabric_Tunic, M_Fabric_Pants, M_Leather_Boots, M_Leather_Belt, M_Hair_Brown, M_Eyes_Dark. Backface culling on (closed mesh -> doubleSided false).
- Material export audit: 7/7 Principled, 0 procedural nodes, 0 empty slots.
- Rig: hand-built, SK_Villager_Armature, 18 bones (17 deform + non-deforming Root at origin)
  - Rig selection: 392 verts < 700 -> hand-built tier. 23.1 verts per deform bone.
  - Bones: Root > Hips > Spine > Chest > Neck > Head; Chest > UpperArm/LowerArm/Hand _L/_R; Hips > UpperLeg/LowerLeg/Foot _L/_R
  - Weights: explicit, not ARMATURE_AUTO. Per-part candidate bones (no cross-limb bleed), inverse distance^6 to bone segment, pruned < 0.05, max 4, normalised. Rigid parts (head, hair, eyes, nose, hands, boots) on a single bone.
  - Verified: dead deform bones 0, deform bones without group 0, unweighted verts 0, max influences 3, weight sums 1.0-1.0, validate_character_rig() -> no warnings.
  - Pose test (arms down, elbow bent, knee raised, spine/neck/head rotated) inspected in viewport, then reset to rest.
- Optimize: skipped (73 kB, no textures). Options on offer: gltf-transform draco / meshopt. gltfpack simplify NOT recommended (720 tris already).
- Export: GLB, 73.0 kB, 720 tris, 1 skin / 18 joints, 1 mesh / 7 primitives, JOINTS_0+WEIGHTS_0, no animations. Verified with gltf-transform inspect.

## Files
- low-poly-villager_original.glb (46.8 kB) — 16 static parts, pre-rig
- low-poly-villager_final.glb (73.0 kB) — skinned, rigged
- low-poly-villager.blend — full scene (factory Cube left in file, hidden; Camera/Light untouched)
- low-poly-villager_log.md

## Licenses
- All geometry and materials authored in-session by script: no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 16:36
