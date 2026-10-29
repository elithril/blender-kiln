# Cat Mascot — Production Log

## Config
- Type: character (quadruped mascot)
- Target: glTF (GLB, web)
- Tier: lightweight (hero/character 3-8K tris, soft)
- Style: stylized
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling (brief: no marketplace, no AI)
- Live view (Kiln Studio): off — unattended auto run
- Output: /private/tmp/kiln-bench/v300final-ahujasid/cat-mascot-walk-idle/work/generated-assets/cat-mascot/
- Environment: Blender 5.2.2 LTS, mcp-for-blender addon 1.8 (protocol 14, up to date); gltf-transform + gltfpack on PATH

## Brief
Stylised cat mascot for a website: chubby body, big eyes, pointed ears, long tail. Rigged,
two looping clips (walk, idle) in one GLB. Assumptions (auto mode): ~0.40 m tall standing on
all fours, facing -Y, ginger fur with cream muzzle/belly/paws/tail tip, pink nose, ear insides,
blush and paw pads; eyes, eyelids, nose separate objects on the head / lid bones.

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- N/A (scripted)

## Source
- Method: scripted (Blender Python), one metaball skin + voxel remesh + QuadriFlow, per characters.md § An animated creature

## Pipeline
- CONFIG/BRIEF: done. Live Blender = untouched factory scene (Cube, Camera, Light). Build runs in headless Blender (scripts/), live Blender used to look.
- SOURCE: scripted, scripts/build_cat.py. Skin = one metaball family (body, chest, belly, head, cheeks, muzzle, 4 legs, 35-ball tail) -> voxel remesh 3.5 mm -> smooth -> QuadriFlow (3,113 quads). Vertex colours (Col): ginger, darker tabby stripes, cream muzzle/bib/belly/paws/tail tip, pink blush and paw pads.
  Rounds: v1 ears unioned into the skin came out folded + an ear-tip snap grabbed a tail vertex (spike); v2 ears reshaped to a cone profile still read as tubes at ~1 cm quads; v3 ears = separate cupped flaps (pink inside), sunk 2 cm into the head, bound 100 % to ear bones — deviation from "one skin" logged here on purpose. Eyes: v1 bulging -> sunk to ~40 % out; v2 pupils square (sphere pole up) -> pole along the gaze, round. Lids: hemisphere rim showed under the eyes -> 80 deg cap, open at 140 deg.
- IMPORT (scripted, implicit): 13 objects: SK_CatMascot skin (3,115 verts) + SM_Cat{Left,Right}{Eye,EyeShine1,EyeShine2,Eyelid,Ear}, SM_CatNose, SM_CatMouth. Bbox 0.261 x 0.665 x 0.488 m (tail included), min Z -1.5 mm. 9,526 tris. Character pose: quadruped natural standing pose (rule 13: no T-pose for a quadruped). Looked at: 3/4, front, side, back-3/4 + face close-up in the live Blender (material).
- CLEANUP (scripts/rig_cat.py): transforms applied (identity), merge by distance 1e-4 m: 12 vertices merged (smooth-shaded skin, no custom normals to keep), 0 loose, degenerate dissolve, normals recalculated; skin 0 fused / 0 open edges (closed). Lifted 1.46 mm so the paws stand at Z = 0. Size 0.261 x 0.669 x 0.500 m (tail and ears included; ~0.40 m to the top of the head) — 1 unit = 1 m. Poly: 9,526 tris vs lightweight 3-8K: above the top, below 2x (16K) -> kept, reported. Skin 6,226 tris, eyes 2 x 504, lids, ears, highlights, nose, mouth the rest. Origin at world origin, under the body.
- TEXTURING: skipped (scripted, materials assigned at build): M_CatFur (Principled, base colour = Color Attribute "Col"), M_CatEyeWhite/Iris/Pupil, M_CatEyeHighlight (emissive), M_CatLid, M_CatNose, M_CatMouth. No procedural textures.
- RIG: quadruped kiln built -> hand-built Mixamo-named skeleton (pipeline-rig-animate table). 32 bones, 31 deform (Hips, Spine, Spine1, Neck, Head [+HeadTop_End non-deform], 4 x 4 leg bones, Tail1-6, LeftEar/RightEar, LeftEyelid/RightEyelid). Rule 26: 3,115 welded skin verts / 27 skin bones = 115 verts per deform bone. Skin: automatic weights with lid and ear bones off; limited to 4 influences, normalised. Eyes, highlights, nose, mouth 100 % Head; lids 100 % their lid bone; ears 100 % their ear bone.
  Checks: dead bones 0; skin verts on lid/ear bones 0; unweighted 0; max influences 4; validator: only YELLOW "root bone named 'Hips', expected 'Root'" (kept: quadruped.py drives Hips). Bent pose (hip, knee, shoulder, elbow, spine, neck, tail ~30-50 deg): widest tear 0.0 mm, looked at (solid, 4 views) — smooth.
  Blink sign measured with a ray grid over each eye: lid bone X +140 deg -> 100 % covered both eyes (-140 -> 45 %): --blink X:140.
- RIG round 2 (after matcap review): lids sat UNDER the eyes (open rotation sign wrong: -140 deg about the side axis turns the pole down) -> +140, upper lids; blink re-measured: X -135/-140 -> 100 % covered, +140 -> 45 %. Ears thickened (0.38 -> 0.55 depth ratio). Tail bones re-rolled (local Z in the tail's plane) so the wave sways sideways instead of pitching; elbows moved 5 mm back.
- ANIMATE: tools/quadruped.py --motions idle,walk --blink X:-135 (scripted, deterministic, exact loops; frames 0..P with key P = key 0).
  walk: 32 frames @24 fps (1.33 s), leg extension 0.922 (<= 0.95, vs rest pose), stride 0.079 x body (tool shortened from 0.11), hips -11 % of a leg, root speed 0.035 m/s, stance speed spread 0.00, ears trail head 4 frames, tail tip trails root 4 frames, 1 blink.
  idle: 48 frames (2.0 s), extension 0.909, ears lag 3 frames, tail tip lag 10 frames, 3 blinks (one double).
  Skin through skin (BVH face overlap, every 2nd frame): 0 mm2 at rest, 0 in walk, 0 in idle. Looked at: walk strip (material) 8 frames, legs at frames 2/10/18/26 (solid) — no crease or tear seen.
  Matcap review (tools/review_renders.py, review/matcap/): rest q1, q3, front, top, under + close-ups. Kept on purpose: the ear flaps meet the head with a visible contact line (separate parts), the separate eyes' contact line with the skin.
- OPTIMIZE: no textures (WebP step n/a); gltf-transform draco (separate step, rule 20; no simplify): cat-mascot_original.glb 440.2 KB -> web/cat-mascot_final.glb 147.7 KB (-66 %). Geometry untouched. cat-mascot_preview.glb = copy of _original (no Draco, no WebP: extensionsUsed = KHR_materials_emissive_strength only).
- EXPORT: material audit before glTF: all Principled BSDF; fur/ears base colour from Color Attribute -> COLOR_0 present on skin + ears; highlights emissive (KHR_materials_emissive_strength); no procedural/image textures. export_apply off. GLB: 1 skin, 32 joints, 13 meshes, 8 materials, clips idle (0-2.000 s, 49 keys) and walk (0-1.333 s, 33 keys), closing key = key 0. Final: web/cat-mascot_final.glb 147.7 KB, 9,526 tris, Draco (needs a decoder on the client, three.js DRACOLoader).
  cat-mascot.blend: scene CatMascot_Rest (build + rig, procedural source) and CatMascot_Animated (the shipped GLB with both clips as NLA tracks). No .blend1.
  studio.py checks: notes only — tris 19 % above the lightweight top (kept), 0.50 m tall to the ear tips (a ~0.40 m mascot cat; on purpose), origin under the body not under the bbox centre (on purpose: the tail shifts the box), Draco ok.
  Intermediates kept (auto, nobody to ask): cat-mascot_build.blend, cat-mascot_rigged.glb, anim/, review/, scripts/.

## Licenses
- All geometry, materials and animation: created in this session (no third-party resources)

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-23 11:35
