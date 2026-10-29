# Villager — Production Log

## Config
- Type: character (rigged, animation-ready)
- Target: glTF (web game)
- Tier: lightweight (character range 3-8K tris)
- Style: low-poly, faceted (flat shading)
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted modelling from the brief)
- Hunyuan3D params: N/A

## Source
- Method: scripted (Blender Python, `scripts/build_villager.py`)
- Environment: Blender 5.2.2 LTS, MCP addon 1.8 (protocol 14, up to date)
- Factory scene: default `Cube` removed before building (rule 6 exception); Camera and Light kept

## Design
- 1.75 m villager (1.83 m with the straw hat), T-pose built in: arms horizontal at z 1.385 m
  (shoulder-to-hand angle 0°), palms down, thumbs forward, feet at shoulder width
- Parts (30 closed islands, one mesh `SK_Villager`): head + nose, eyes, ears, hair shell + fringe,
  straw hat (brim, crown, band), green tunic, linen collar, belt + brass buckle + pouch,
  linen sleeves, hands + thumbs, trousers, boots + soles
- Materials (Principled BSDF values only, backface culling on): M_Skin, M_Fabric_Linen,
  M_Fabric_Tunic, M_Fabric_Trousers, M_Leather_Brown, M_Leather_Dark, M_Straw_Hat,
  M_Hair_Brown, M_Eye_Dark, M_Metal_Brass

## Pipeline
- Import: implicit (scripted). 782 verts, 622 faces, 1,396 tris, bbox 1.60 x 0.39 x 1.83 m, base at z = 0
- Cleanup: transforms applied, weld (rule 10, normals kept): 0 merged; normals recalculated;
  0 loose; 0 degenerate; fused edges 0; open edges 60 (rims of hat band, collar, belt, by design)
- Poly count: 1,396 tris, below the lightweight character range (3-8K). Intentional for the
  low-poly style; no reduction proposed or needed
- Texturing: skipped (scripted, flat materials assigned at creation)
- Rig selection (rule 26): 782 verts / 20 = budget ~39 deform bones. Hand-built skeleton,
  22 deform + 1 non-deform `Root` at the origin, Mixamo-style names (Hips, Spine, Spine1, Spine2,
  Neck, Head, Left/Right Shoulder, Arm, ForeArm, Hand, UpLeg, Leg, Foot, ToeBase) for
  retargeting in web engines. 35.5 verts/deform bone. Chosen over Rigify's basic human
  (35 bones, 22 verts/bone, Rigify names) for name compatibility with motion libraries.
- Skinning: positional weights (`scripts/rig_villager.py`), not automatic weights, because the
  mesh is 30 disconnected islands; weights blend smoothly across each joint, side taken from
  each island, hat/hair/face locked to Head, skirt follows the thighs at 50%.
  Result: 0 dead bones, 0 unweighted verts, max 4 influences, normalised.
- Rig validator (characters.md): clean
- Stress pose (`scripts/pose_test.py`: arms -60°, elbows 40°, stride 40°/knee 50°, spine and
  head twist): no tearing; one bug found and fixed (hat brim was picking up arm weights).
  Worst compression at the back of the bent knee (edge ratio 0.23) and armpit (0.34), as expected.
- Material audit: all glTF-compatible
- Optimize: no textures (resize/WebP not applicable); Draco via `gltf-transform draco`:
  141.7 KB -> 23.8 KB (-83%). Needs a Draco decoder on the client (three.js DRACOLoader).
- Export: GLB, 1,396 tris, 10 primitives (one per material), 23 joints.
  `gltf-transform validate`: 0 errors (warnings: skinned mesh not at root, which is standard for
  Blender exports; Draco extension unsupported by the validator; unused buffer views).
  Re-import in headless Blender: 23 bones, 1,396 tris, 23 vertex groups, 0 unweighted, 10 materials.
- Animations: none (not requested). Rest pose = T-pose.

## Files
- villager_original.glb (141.7 KB, uncompressed)
- villager_final.glb (23.8 KB, Draco)
- villager.blend
- scripts/ (build, rig, pose test, verify)

## Licenses
- All geometry and materials created from scratch in this session: no third-party resources.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
