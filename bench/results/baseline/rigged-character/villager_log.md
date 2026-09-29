# Villager — Production Log

## Config
- Type: character (rigged, web game)
- Target: glTF (GLB)
- Tier: lightweight (character soft range 3-8K tris)
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
- Method: scripted modeling (Blender Python, bmesh lofts + primitives), Blender 5.0.1
- Parts (23, joined into SK_Villager): legs, boot shafts + feet, tunic with skirt flare,
  belt, pouch, neck, head, hair cap, nose, eyes, sleeves, forearms, mitten hands + thumbs
- Pose: T-pose by construction; edge loops at shoulders, elbows, wrists, hips, knees, ankles

## Pipeline
- Import: implicit (scripted). 828 verts, 773 faces, 1,554 tris, bbox 1.60 x 0.34 x 1.82 m
- Pose measurement: 0.4 deg (T-pose). NOTE: the PHASE 4 snippet reported -70 deg on
  this T-pose — its 0.75*H torso slice crosses the horizontal arms, so "torso width" became
  the hand extent. Re-measured with the torso restricted to |x| < 0.25.
- Wingspan/height: 1.60 / 1.82 m (0.88) — stylised short arms, pose itself is horizontal
- Cleanup: merge doubles (0 merged), recalc normals, remove loose, dissolve degenerate,
  apply transforms, origin at base centre (0,0,0), flat shading, orphans purged.
  12 non-manifold edges = open rim of the hair cap (deliberate, hidden by the head).
- Poly check: 1,554 tris — below the lightweight range, not above; no decimation.
- Rig selection (rule 26): 828 verts -> 700-3,000 band -> Rigify basic human.
  Metarig fitted by hand; breast.L/R and pelvis.L/R removed (no geometry to carry them).
  Generated rig: 212 bones, 31 deform -> 26.7 verts/deform bone.
- Skinning: ARMATURE_AUTO. 0 dead bones. Heat weighting failed on belt + pouch
  (48 verts unweighted) -> weights copied from 4 nearest tunic vertices (inverse distance).
  Then clean <0.01, limit 4 influences (41 weights limited), normalize all.
- Deform hierarchy fix: Rigify parents DEF-thigh/DEF-shoulder/DEF-upper_arm to ORG bones,
  so a deform-only glTF export produced 7 root joints. Re-parented to DEF-spine /
  DEF-spine.003 / DEF-shoulder; DEF-shoulder given a world Copy Transforms to ORG-shoulder
  (it had none). Deformation under a test pose unchanged (max diff 6.9e-7 m).
- Pose test (FK): 764/828 verts move, head stays attached, volume held.
  IK_FK restored to Rigify default (0 = IK) after the test.
- Rig validator: clean except expected note (212 bones / 31 deform -> export_def_bones=True).
- Texturing: skipped — procedural flat colors (Principled BSDF values only), 6 materials:
  M_Fabric_Tunic_Green, M_Fabric_Trousers_Brown, M_Leather_Dark, M_Skin_Villager,
  M_Hair_Chestnut, M_Eye_Dark. Backface culling on (glTF doubleSided=false). No UVs.
- Material export audit: all Principled, no procedural / Color Ramp nodes.
- Optimize: not run (interactive step, proposed at the end)
- Export: GLB, export_apply=False, export_def_bones=True, skins on, no Draco.
  160,696 bytes, 1,554 tris, 3,092 GPU verts (flat-shading normal splits), 31 joints, 1 root.
- Round-trip verified in headless Blender: 31 joints / root DEF-spine, 3,092 verts,
  31 groups, 0 unweighted, max 4 influences, height 1.817 m, posed joints move the skin.

## Scene contents (.blend)
- SK_Villager (mesh), SK_Villager_Rig (Rigify control rig), SK_Villager_Metarig (hidden,
  kept to regenerate the rig), WGT-rig_* widget objects (Rigify control shapes)
- Removed: factory-default Cube (8 verts) from the startup scene

## Licenses
- All geometry and materials: original, scripted in this session. No third-party assets.
- Rigify: built-in Blender add-on (GPL); generated rig data carries no licence restriction.

## Checkpoint
- Last completed step: EXPORT (optimize pending user choice)
- Timestamp: 2026-09-29 15:14
