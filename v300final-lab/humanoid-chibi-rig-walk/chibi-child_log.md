# Chibi Child — Production Log

## Config
- Type: character (humanoid biped, rigged + animated)
- Target: glTF (web game)
- Tier: lightweight (character 3-8K tris)
- Style: stylized (chibi)
- Mode: auto
- Storage: compact
- Backend: none — scripted modelling (brief: no marketplace, no AI)
- Live view: Kiln Studio http://127.0.0.1:4856/ (--no-open)
- Environment: macOS Apple Silicon 24 GB; Blender 5.2.2 via official Blender Lab MCP; gltf-transform + gltfpack present; SkinTokens auto-rig installed (tested version)

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Brief (confirmed, auto mode)
Stylised chibi child for a web game: big round head (~40 % of height), short arms and legs, ~1.0 m tall (assumption: brief gives no size), T-pose (rule 13), front -Y, origin at feet. One welded skin (metaballs + voxel remesh + QuadriFlow) carrying shirt / shorts / shoes / skin materials; hair, eyes, cheeks separate rigid parts. Rig with tools/autorig.py (SkinTokens), animate walk with tools/presets.py --loop.
Assumptions: no eyelids/blink (preset walk has no blink channel); clothing read by colour regions on the skin.

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)

## Source
- Method: scripted (Blender Python, metaballs → voxel remesh → QuadriFlow)

## Pipeline
- CONFIG + BRIEF: done. Factory scene found (Cube, Camera, Light, no .blend): Cube to be removed before building (rule 6 exception).

- SOURCE (scripted): scripts/build_body.py — 12 metaball elements (head, neck, torso, hips, legs, T-pose arms, mitten hands, shoes; one family = one skin), 5 mm voxel remesh, flat soles, QuadriFlow 2,460 faces (2,462 verts). scripts/build_details.py — skin bisected at the colour borders, materials by region (skin / shirt / shorts / shoes), Smart UV; separate eyes (+2 emissive highlights each), cheeks, mouth (placed by ray-cast on the face), parametric hair shell (pointed bangs, smooth hairline) + tuft. v1 hair cut by vertex deletion had a stepped edge and bead-like fringe → rebuilt parametric (kept v2). Total 8,138 tris (skin 5,114; hair 1,948). Review renders: review/build/.
- IMPORT (scripted, implicit): world-space vertex bbox 0.725 × 0.426 × 1.073 m (1.073 incl. tuft; skin 0.97 m), min Z = 0, origin (0,0,0) at the feet centre, front -Y. Names SK_ChibiChild (+ _EyeL/_EyeR/_CheekL/_CheekR/_Mouth/_Hair), data-blocks *_Mesh. Pose (rule 13): shoulder→hand -0.3° = T-pose.
- CLEANUP: transforms applied, merge by distance 1e-4 (first-pass counts lost to a reporting error in my script; a second pass merged 0 on every part), normals recalculated outward (skin signed volume +0.048 m³), loose removed, degenerate dissolved; fused edges 0, open edges 0 on every part; no empty material slots; orphans purged. 9 materials, Principled BSDF values only. Poly: 8,138 tris vs lightweight 3-8K → 2 % over the top, under 2× → kept (skin 5,114, hair 1,948, eyes 776, cheeks+mouth 300). Review: review/build/ (matcap + colour, q1/q3/front/back).
- RIG: route humanoid → tools/autorig.py (SkinTokens, installed tested version), 43.7 s. Rule 26: 2,559 welded skin verts (3,501 after glTF seam split) / 22 deform bones = 159 verts/bone. Bones: Hips, Spine, Spine1, Spine2, Neck, Head, L/R Shoulder-Arm-ForeArm-Hand, L/R UpLeg-Leg-Foot-ToeBase. Dead bones 0, max influences 4, unweighted 0, weight transfer 0.0 mm, 2 speck islands cleaned. Eyes, cheeks, mouth, hair 100 % to Head. Validator (characters.md): no warning. Bent pose (thigh 60°, knee 75°, arm 45° fwd, elbow 75°, Spine1 20°, neck 30°): widest tear 0.0 mm over 804 split-vertex groups; matcap review/bent/ — volume held, no collapse. Files: rig/chibi-child_rigged.glb + .blend; checker scripts/rig_check.py.
- ANIMATE: route kiln-named humanoid + preset → tools/presets.py walk --loop (NVIDIA Kimodo clips, retarget with kiln's fixes). Take A: walk_loop slide 2.5 mm/s, below floor 0.0 mm, arms in body 0.0 mm², seam 1.23× a step (misses ≤ 1.2×) → take B: walk_loop slide 2.5 mm/s · 0.0 mm · 0.0 mm² · seam 0.76× (all targets met), 65 frames + closing key, 2.17 s, two strides, root speed 0.429 m/s (move the character at this speed in-game so the feet do not skate), arm swing capped 24°, hips lowered 19 mm. Kept take B (anim_takeB/); take A kept in anim/ for comparison. Clips in file: walk (whole 4 s take, travelling, not a loop) and walk_loop (in place, seamless). Matcap frames review/walk/ — stride, heel lift, arm swing read; skin holds at hips and knees. No blink (presets carry none; no eyelids built).
- OPTIMIZE: material audit — 9 Principled materials, values only, no procedural node, no texture (WebP step: nothing to convert). chibi-child_original.glb 413.8 KB → gltf-transform draco → web/chibi-child_final.glb 158.1 KB (−62 %); gltf-transform validate: 0 errors, 0 warnings. chibi-child_preview.glb = copy of original (extensionsUsed: none — opens in macOS Quick Look). Draco final re-imported and rendered mid-walk (review/final/): skinning intact.
- EXPORT: glTF binary, 8,138 tris, 22 joints, 9 materials, clips walk (4.0 s, travelling) + walk_loop (2.17 s, in place, seamless). export_apply off (rule 18). chibi-child.blend saved: collection Rigged_Animated (armature on walk_loop, playback 0-51) + Build_Unrigged (hidden, the scripted build). Studio live view closed; studio checks: triangles 2 % over the lightweight top (note), height 1.07 m (on purpose: chibi child), on the ground OK.
- Intermediates kept (compact, auto mode, nobody to ask): rig/ (unrigged input GLB, rigged GLB + .blend), anim/ (take A), anim_takeB/ (take B + measures/provenance JSON), review/ (renders, posed_test.glb), scripts/.

## Licenses
- Model: built from scratch in this session — no third-party asset
- Walk motion: NVIDIA Kimodo (Kimodo-SOMA-RP-v1.1) preset walk_b — Licensed by NVIDIA Corporation under the NVIDIA Open Model License; NVIDIA claims no ownership of outputs; commercial use allowed
- Retarget code (tools/retarget.py): adapted from image-to-3dlab, Apache-2.0
- SkinTokens (VAST-AI): code and checkpoints MIT; kiln's Mac patch Apache-2.0 (image-to-3dlab)

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22
