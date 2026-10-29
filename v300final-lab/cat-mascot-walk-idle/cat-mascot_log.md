# Cat Mascot — Production Log

## Config
- Type: character (quadruped mascot)
- Target: glTF (web)
- Tier: lightweight (hero 3-8K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Backend: none — scripted modelling (user's choice: no marketplace, no AI)
- Rigged: yes — quadruped, natural standing pose (rule 13), clips walk + idle looping, one GLB
- Environment: macOS arm64, 24 GB unified; Blender 5.2.2 LTS via the Blender Lab MCP; gltf-transform + gltfpack present

## Reference Image
- Path: none
- Brief enrichment: assumptions (auto mode) — ~0.40 m tall, front -Y; orange body, cream muzzle/belly/paws, pink nose/inner ears/cheeks/pads; big eyes with highlights and blinking upper lids; tail raised and long
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from the brief)

## Source
- Method: scripted (metaballs one skin + voxel remesh + QuadriFlow; eyes, lids, nose separate rigid parts)

## Pipeline
- CONFIG/BRIEF: brief restated with assumptions above; factory scene detected (Cube, Camera, Light, no file)
- Source: factory Cube removed (rule 6 exception). Skin = one metaball family (torso, belly, chest, rump, neck, wide head, sunk cheeks, muzzle, chin, 4 short legs as ball chains, paws, haunches, 41-point Bezier tail) + 2 flattened cone ears, joined, voxel remesh 2.5 mm, smooth x4 → 109,610 faces, 0.250 x 0.576 x 0.461 m, on the ground. Script: scripts/build_skin.py
- Import: scripted (in Blender). Renamed SK_CatMascot_Skin / SK_CatMascot_Skin_Mesh; 1 unit = 1 m; origin at world origin under the body, lowest vertex Z = 0
- Cleanup: 109,610 voxel faces → merge 1e-5 (0 merged) → QuadriFlow 3,400 target, symmetric, seed 0 → 3,240 quads (6,480 tris), 3,242 verts; weld 1e-4 (0), normals recalculated, 0 loose, 0 degenerate; fused edges 0, open edges 0 (closed skin). Size 0.250 x 0.575 x 0.458 m. Script: scripts/cleanup_retopo.py. Matcap review: review/cleanup/
- Charm parts (scripts/build_parts.py): eyes r 28 mm, pole forward (pupil < 23°, iris < 57°, white), ~52 % out of the skin (60 % bulged on this round head); 2 emissive highlight lenses per eye, same light side; upper lids = hemispherical shells 1.085 r, 1.2 mm, open tilt 70° back (50° read sleepy); nose (rounded triangle), mouth (bevelled curve → mesh, projected on the skin)
- Texturing: v1 one flat material per face region → stair-stepped borders (review/texture/v1_*); v2/v3 one 1024 base-colour map rasterised from smooth 3D fields onto Smart-UV islands (scripts/paint_skin.py): orange fur, tabby back stripes, forehead stripes, tail rings, cream muzzle/bib/belly/paws/tail tip, pink inner ears, cheek blush, paw pads; dilated 4 px; packed in the .blend. uv_check: skin ok (overlap 0 %, collapsed 0 %, stretch 0.1 %); Mouth WARN overlap (curve UVs, flat colour, no texture: irrelevant). Other materials Principled values only. Reviewed from q1/q2/q3/front/under (review/texture/)
- Poly count: 9,396 tris total (skin 6,480; eyes 1,440; lids 960; nose 168; mouth 156; highlights 192) — above lightweight's 8K top, under 2x: kept, reported (rule 4)
- Rig (scripts/build_rig.py, checks scripts/check_rig.py): hand-built Mixamo-named quadruped (characters.md § Animation-ready skeleton) — Hips→Spine→Spine1→Neck→Head(→HeadTop_End), {L,R}Arm→ForeArm→Hand(→Fingers), {L,R}UpLeg→Leg→Foot(→ToeBase), Tail1-5, {L,R}Ear, {L,R}Eyelid; 31 bones, 26 deform. Rule 26: 3,242 skin verts / 26 = 124.7 verts per deform bone; 0 dead bones; max 4 influences; 0 unweighted; 0 skin vertices on lid bones (lids kept out of the automatic weights)
- Weights: automatic (heat) on the welded skin; ear bones reached 15 cm down the skull (603 verts, w up to 0.86) → faded below the ear root, given back to Head (252/225 verts). Eyes, highlights, nose, mouth 100 % Head; each lid 100 % its lid bone; joined into one skinned mesh SK_CatMascot (4,736 verts, 8 materials)
- Fixed-pose bend test (self-intersecting skin face pairs): rest 0, shoulders 30° 0, hips 30° 0, neck 30° down 0, tail 50° aside 0; elbows 75°: auto 44 → 16, knees 75°: auto 63 → 55 after weight smoothing (all six leg groups x15; lower-only x6 gave 35/63, x15 34/62). Knees at 75° still fold: left on purpose, the walk bends far less — measured on the clip below
- Validator: clean except yellow "root bone named Hips" (Mixamo convention, required by quadruped.py)
- Eyelid closing sign (rule 4, rays over 0.75 r of each eye): +X 120°/140°/160° → 100 % covered, rest 0 %; -140° 91 % (goes round through the head). Blink: X:150
- Material audit (rule 19): 8 materials, all Principled, 1 image (1024), no procedural node — glTF-safe
- Rigged GLB for animation: anim/cat-mascot_rigged.glb (528 kB, intermediate)
- Rig round 2: fore chain stood at 95 % of its length at rest → elbows bent back (rest 91 %), knees forward (84 %); elbows-75° test 16 → 0 pairs, knees 55 → 62
- Animate: tools/quadruped.py (quadruped route; never UniMate), --blink X:150. Default start cut the stride to 0.079 of the body (2.5 cm, 0.031 m/s: a shuffle) — the tool measures extension against the leg's rest reach. Probed stride/crouch: 0.11/0.15 → ext 0.91; 0.14/0.15 → 0.929; 0.13/0.12 → 0.950 (at the limit). Kept --stride 0.13 --crouch 0.14:
  - walk: 32 frames (+ closing key 32 = 0), 24 fps, legs ≤ 93.1 %, root speed 0.050 m/s (move the character at this speed for no foot skate), stance spread 0.0, ear lag 4 frames, tail tip lag 6, 1 blink
  - idle: 48 frames (+ closing key), legs ≤ 92.2 %, ear lag 1, tail tip lag 8, 3 blinks (one double)
  - one GLB, clips "idle" and "walk": anim/cat-mascot_rigged_animated.glb
- Motion review (scripts/review_motion.py, review/motion/): skin through skin on every 2nd frame of both clips = 0 face pairs; lowest point 0.0 mm (walk) / +0.1 mm (idle) — nothing under the floor; contact sheets walk_sheet.png, idle_matcap_sheet.png; blinks seen closed (walk f20, idle f31)
- Matcap before delivery (review/matcap/): rest q1/q3 + close-ups nape, shoulder, tail root, ear base, face — clean. Left on purpose: the lid shell's thin rim above each eye (reads as a lid crease), slight facets near the ear tips (QuadriFlow at ~10 mm); knees bent 75° fold (55-62 pairs) but the clips never bend that far
- Optimize (auto, rule 20 — separate steps, no simplify): gltf-transform webp q90 (616 → 486 kB; texture already 1024) → draco (→ 185 kB, -70 %). Geometry untouched. cat-mascot_preview.glb = copy of _original (no Draco/WebP: opens in macOS Quick Look; extensionsUsed checked)
- Export: glTF 2.0 binary, web/cat-mascot_final.glb 185 kB, 9,396 tris, 5,756 vertices, 1 skinned mesh (8 primitives), 31 joints, clips idle (48 f, 2.0 s) + walk (32 f, 1.33 s) at 24 fps, closing key = first key; export_apply off (rule 18); material audit clean (rule 19). Round-trip import OK (Draco + WebP decode, both actions). Studio checks: no WARN; notes — tris 17 % over lightweight (kept, rule 4), 0.46 m tall (a cat, on purpose)
- .blend: cat-mascot.blend — final rig + skinned mesh + idle/walk as NLA tracks; build sources in excluded collections CatSource (metaballs, ear cones) and CatBuild (unrigged skin and parts)
- Storage (compact, auto mode — nobody to answer, intermediates kept and listed): anim/ (cat-mascot_rigged.glb, cat-mascot_rigged_animated.glb, quadruped-report.json), review/ (renders), scripts/ (the build, reproducible)
- Source rounds: v1 ears landed at the origin (copied before matrix_world update) and the muzzle read dog-like → v2 update() before copy, muzzle/cheeks pulled back; v3 ears 10% larger. Reviewed in matcap (review/source/)

## Licenses
- All geometry and materials: created in-session by script — no third-party resources

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22 18:39
