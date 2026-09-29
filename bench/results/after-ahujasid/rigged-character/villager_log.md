# Villager — Production Log

## Config
- Type: character (rigged, for animation)
- Target: glTF (GLB), web game
- Tier: lightweight (character soft range 3-8K tris)
- Style: low-poly
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.7 (up to date), gltf-transform + gltfpack present

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted modeling (Blender Python) — chosen by the brief. The skill recommends AI for characters; the brief overrode it.
- Scene: Blender factory scene (Cube, Camera, Light, no .blend) — factory Cube removed before building (rule 6 exception). Camera and Light untouched.
- Build: 19 parts (tunic, neck, belt, pouch, head, hair shell, nose, eyes x2, legs x2, boots x2, sleeves x2, hands x2, thumbs x2), lofted rings with loops at shoulders, elbows, wrists, hips, knees, ankles. Flat shading. Joined into one skinned mesh `SK_Villager`.
- Pose: T-pose by construction. Measured arm axis 0.0 deg (centroids of arm cross-sections at x=0.22 and x=0.62), wingspan 1.71 m for 1.77 m height.
  - Note: the skill's shoulder-to-hand formula (PHASE 4) reported -14.9 deg on this mesh. On a T-posed body its 0.75·H slice (1.327 m) falls inside the horizontal arms, so it takes the forearm as the "torso edge". Cross-section centroids were used instead.

## Pipeline
- Import: 787 faces / 1,238 tris, 668 verts, bbox 1.71 x 0.285 x 1.769 m, origin at feet centre
- Cleanup: 0 vertices merged, 0 degenerate, 0 loose, 0 fused edges, 28 open edges (hair shell rim + thumb bases, hidden, expected), 0 n-gons, transforms applied, orphans purged
- Poly alert: 1,238 tris is BELOW the lightweight character range (3-8K). Consistent with the low-poly style; not changed (rule 4).
- Texturing: skipped — scripted, 7 flat Principled BSDF materials assigned from creation (no UVs, no textures)
  - M_Skin_Villager, M_Fabric_Tunic_Green, M_Fabric_Pants_Brown, M_Leather_Boots_Dark, M_Leather_Belt_Brown, M_Hair_Brown, M_Eye_Dark
- Rig (rule 26 gate): 668 verts < 700 → hand-built rig. 20 bones: `Root` (non-deforming, at the origin) + 19 deforming (Hips, Spine, Chest, Neck, Head, Shoulder/UpperArm/LowerArm/Hand _L/_R, UpperLeg/LowerLeg/Foot _L/_R). 35 verts per deform bone.
  - Skinning: automatic weights, then 8 unweighted vertices (the pouch, a separate island) assigned by hand to Hips. Nearest-bone put them on UpperLeg_L, which would swing them with the thigh. Cleaned < 0.01, limited to 4 influences, normalised.
  - Verified: 0 dead deform bones, max 4 influences/vertex, 0 unweighted; belt and tunic hem carry Hips/Spine weight only.
  - Test pose (arms lowered, forearm bent, thigh forward + knee bent, head turned, spine bent): 534/668 verts moved, no tearing, volume held. Pose reset to rest.
  - characters.md validator: 0 warnings.
- Material audit (rule 19): all 7 Principled, flat values, no procedural nodes
- Export original: villager_original.glb, 127.4 kB, 20 joints, no `neutral_bone`, no animations (rig only, as briefed)
- Optimize (auto preset): no textures, so WebP/resize were no-ops; Draco via `gltf-transform draco` → 127.4 kB → 20.7 kB (-84%). Client needs a Draco decoder (e.g. DRACOLoader in Three.js). Geometry not simplified.
- Validation: `gltf-transform validate` exit 0 on both files, 0 errors. Warning NODE_SKINNED_MESH_NON_ROOT (mesh under armature node — harmless for a skinned mesh). The Draco file adds severity-2 notices (Draco extension not validatable, compressed bufferViews flagged "unused").
- Round trip: both GLBs re-imported headless in Blender → 1,238 tris, 20 bones, 0 unweighted, same bbox, 7 materials.
- Export: glTF/GLB, villager_final.glb 20.7 kB, 1,238 tris

## Files (compact)
- villager_original.glb (127.4 kB), villager_final.glb (20.7 kB, Draco), villager.blend (129.5 kB, saved before Draco), villager_log.md

## Licenses
- All geometry and materials authored in-session by script. No external assets, textures or generated images.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-09-29 20:06
