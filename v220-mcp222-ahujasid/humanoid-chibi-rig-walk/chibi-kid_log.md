# Chibi Kid — Production Log

## Config
- Type: character (biped, rigged + animated)
- Target: glTF (GLB), web game
- Tier: lightweight (character 3-8K tris)
- Style: stylized
- Mode: auto
- Storage: compact

## Reference Image
- Path: none (brief only)
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Brief: "A stylised chibi child for a web game — big round head, short arms and legs — rigged, with a walk cycle that loops."
- No concept art, no AI generation (brief asked for scripted modelling)

## Source
- Method: scripted modelling (Blender 5.2.2 LTS, blender-mcp addon 1.8), scripts in `scripts/`
  - `01_model.py` mesh + materials · `02_rig.py` weld, armature, weights · `03_walk.py` walk cycle
  - `04_measure.py` walk measurements · `validate_rig.py` rig validator · `check_glb.py` GLB skin/clip check
- Factory scene: the default Cube was removed (rule 6 exception); Light and Camera kept.

## Pipeline
- Model: one mesh `SK_ChibiKid` (24 shells: head, hair, ears, eyes, cheeks, mouth, body, neck, legs,
  shoes, arms, hands), T-pose, facing -Y, feet at z=0. Height 1.108 m (hair tuft), head ~45% of it.
  3,341 verts, 3,620 faces, 6,548 tris — inside the lightweight character range.
- Cleanup: transforms applied, merge-by-distance 1e-4 (0 merged — shells built welded),
  shells oriented outwards (0 inward), 40 boundary edges = intentional open hair rim, orphans purged.
- Texturing: procedural Principled BSDF values only (no textures): M_Skin, M_Hair, M_Shirt, M_Shorts,
  M_Socks, M_Shoe, M_Sole, M_Eye, M_EyeShine, M_Cheek. Material audit: all Principled → Output,
  no procedural nodes. Backface culling on except M_Hair (open shell).
- Rig: hand-built, Mixamo names. 21 bones, 19 deform (Root and HeadTop_End non-deform).
  175.8 verts per deform bone, 0 dead bones, max 2 influences per vertex, 0 unweighted vertices.
  Weights procedural per part (smooth blends at knees, elbows, wrists, ankles, spine); head parts rigid.
  Rig validator: no warnings.
- Animation: `A_ChibiKid_Walk`, in place, 24 frames @ 24 fps = 1.0 s per cycle (2 steps).
  Feet solved by 2-bone IK per frame, baked to FK. Duty 60%, stride 0.14 m, foot lift 4.1 cm.
  Measured: max leg extension 93.1%; planted foot moves back 0.0097 m/frame on both feet
  → **root speed 0.233 m/s** (move the character at this speed to avoid foot skating);
  lowest sole 0.0 m (no ground penetration); hands ≥ 4.8 cm from the body; frame 24 == frame 0 exactly.
  Rotation signs measured before use. Keys 0..23 plus a closing key at 24 (= key 0), Cycles modifier,
  scene playback 0..23 → seamless in Blender; GLB clip 25 keys / 1.000 s, first key == last key.
- Optimize: gltf-transform draco (individual step, rule 20) — 240.5 KB → 68.3 KB (−72%).
  No textures, so no resize/webp. Requires a Draco decoder on the client (three.js DRACOLoader).
- Export: GLB, 6,548 tris, 3,493 verts in file, 19 joints, 1 clip. Round-trip import of the final
  verified (verts/tris/groups/clip range/pose).

## Licenses
- All geometry, materials and animation created from scratch by script for this project — no third-party assets.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
