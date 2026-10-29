# Chibi Child — Production Log

## Config
- Type: character (biped, humanoid)
- Target: glTF (web game)
- Tier: lightweight (hero/character 3-8K tris, soft)
- Style: stylized (chibi)
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling (brief: no marketplace, no AI generation)
- Live view: off (autonomous auto run, nobody watching a Studio page)
- Rigging + animation: yes — rig, then a looping walk
- Output: /private/tmp/kiln-bench/v300final-ahujasid/humanoid-chibi-rig-walk/work/generated-assets/chibi-child/
- Environment: Blender 5.2.2 LTS, mcp-for-blender addon 1.8 (protocol 14, up to date); SkinTokens installed (tested version); Kimodo presets present (22 motions)

## Reference Image
- Path: none
- Brief enrichment: assumptions (auto mode) — height ~0.95 m, head ~45% of height, T-pose for rigging, simple clothes as colour regions on the skin (T-shirt, shorts, shoes), hair cap, big eyes with highlights, eyelids, cheeks
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted, no reference)

## Source
- Method: scripted (Blender Python) — metaball body as ONE skin, voxel remesh, QuadriFlow; eyes/hair/lids separate rigid objects

## Pipeline
- CONFIG/BRIEF: brief confirmed as "stylised chibi child, big round head, short arms and legs, T-pose, web glTF, lightweight tier, rig + looping walk". Factory scene found (Cube, Camera, Light, no file) — Cube removed before building (rule 6 exception).
- SOURCE: scripted — scripts/build_skin.py (25 metaball elements, stiffness 2, threshold 0.6; surface = 0.575 x radius, measured) → mesh → voxel remesh 5 mm (59,546 verts, 1 island, 0 non-manifold) → QuadriFlow 3,000 faces. QuadriFlow cancelled on the voxel skin ("needs to be manifold") although bmesh found 0 non-manifold / 0 boundary and merge 1e-5 removed 0; a Collapse pass to 20% of the session's own voxel skin first made it finish (build method, logged). Skin: 3,010 quads.
- SOURCE: scripts/build_parts.py — clothes as material regions on the ONE skin, hems cut by bisect planes (sole 18 mm, shoe 88 mm, shorts 150-255 mm, shirt to 475 mm, sleeves |x| 0.20 m); separate rigid parts: hair (parametric cap, fringe zig-zag, 14 mm solidify) + tuft, eyes (flattened ellipsoids, 35% out of the skin) with two emissive highlights each lit from +X, upper eyelid shells (x1.085, open = turned 75° back into the head), mouth (half torus), cheeks (sunk pink discs). First pass had staircase hems and fringe (per-quad assignment) — redone with planes / parametric edge; hair edge lowered to the nape.
- IMPORT (scripted, implicit): 0.70 x 0.38 x 0.90 m, T-pose by construction (shoulder→hand 0°), front -Y, left +X. Names SK_ChibiChild (+ _Mesh), parts SK_ChibiChild_*; materials M_*.
- CLEANUP (scripts/cleanup.py, all 14 parts): transforms applied, merge 1e-5 → 0 merged (skin smooth-shaded, no split normals to keep), 0 loose, degenerate dissolve, normals recalculated; 0 fused, 0 open/non-manifold edges on every part. Ground: lowest point to Z=0 (shift 0.4 mm). Size 0.70 x 0.42 x 0.97 m (tuft included). Orphans cleaned, mesh data renamed {Object}_Mesh.
- Poly check: 11,378 tris against lightweight 3-8K = 1.4x the top, under 2x → kept, not cut (rule 4/6): skin 6,702 (3,353 verts), hair 2,016, eyes+lids+highlights ~2,000, cheeks+mouth+tuft ~700.
- TEXTURING: skipped — scripted with materials assigned (Principled values only: M_Skin_Chibi, M_Fabric_Shirt, M_Fabric_Shorts, M_Rubber_Shoe, M_Rubber_Sole, M_Hair_Brown, M_Eye_Dark, M_Eye_Highlight (emissive), M_Mouth, M_Skin_Blush). Material export audit: 0 non-Principled nodes. No image textures, so no UVs needed.
- Saved chibi-child.blend; rig input work/chibi-child_static.glb (224.7 kB).
- RIG: route = humanoid → tools/autorig.py (SkinTokens, installed, tested version), --body humanoid, 44.3 s. 24 deform bones (Hips, Spine, Spine1, Spine2, Neck, Head, Left/RightEyelid, Shoulder/Arm/ForeArm/Hand, UpLeg/Leg/Foot/ToeBase x2); rule 26: 3,626 GLB verts / 24 = 151 verts per bone; 0 dead bones, max 4 influences, 0 unweighted, 0 skin on lids; hair, tuft, eyes, highlights, mouth, cheeks 100% to Head, lids to their bone. Bent pose (thigh 60°/-40°, knees 75°, arms 45°, forearm 75°, Spine1 20°, neck 30°): widest tear 0.0 mm over 273 seam vertex pairs; skin holds together. Validator: only "root bone named Hips, expected Root" — kept (kiln/Mixamo names the presets need). Output work/rig/chibi-child_static_rigged.glb + .blend.
- ANIMATE: route = kiln-named humanoid + "walk" in presets.py list → tools/presets.py animate --motion walk --loop. Take A: walk_loop 32 frames / 1.03 s (one stride), slide 0.6 mm/s, floor 0.0 mm, arms in body 14.8 mm², seam 1.24x (over the 1.2x target). Take B: walk_loop 2.17 s (two strides), slide 0.6, floor 0.0, arms 164 mm², seam 0.76x → KEPT (all four targets: <50 mm/s, <5 mm, <500 mm², ≤1.2x). Root speed for the game: 0.36 m/s (presets' loop record).
- ANIMATE edits (Blender, on take B): the in-place loop stood 0.375 m in front of the origin and 0.043 m to the side → Hips location keys offset in the bone's rest frame (animation.md rule 1), loop centre now (0.000, 0.000); closing key 52 == key 0 (max diff 0.0); lowest skin point 0.8-1.1 mm over the whole loop. The travelling take "walk" (1.42 m, seam 9.2x, not a loop) dropped from the deliverable (it stays in work/animB/). Blink NOT added: measured lid coverage stayed ≤ 16% at every angle (±60..180°) — the lid shells copy the eye's flattened ellipsoid, which does not stay on the eye when turned; lid shells and LeftEyelid/RightEyelid bones removed (864 tris, would be dead weight). Other face parts stay 100% on Head.
- Matcap review (tools/review_renders.py, rest, q1/q3/front/back/top/under + close-ups neck, armpit, crotch, face — review/rest/): skin continuous, no groove at neck/shoulders/hips; one small faceted notch at the crotch (QuadriFlow pole), left. Mid-walk (frames 6/13/32/39, live Blender): legs and arms readable, no tear.
- Final clip measured on chibi-child_original.glb (motion_measure.py, --rig): walk_loop 53 keys, 2.17 s @ 24 fps, slide 7.0 mm/s (import resampled 30 → 24 fps; was 0.6), floor 0.0 mm, arms in body 162 mm², seam 0.71x. Skin through skin mean 3,777 mm² / worst 12,170 mm², mostly each leg on itself (~1,650-1,700 mm² per leg: knee fold of the short, chubby legs) — reported, not fixed.
- OPTIMIZE: no image textures (WebP step not applicable); gltf-transform draco (individual step, rule 20) → 366.8 KB → 108.1 KB (-71%). Geometry untouched. chibi-child_preview.glb = copy of _original (no Draco, no WebP: opens in macOS Quick Look; extensionsUsed none).
- EXPORT: material audit 0 non-Principled nodes; export_apply=False, skins + animations, deform bones only. web/chibi-child_final.glb: 108.1 KB, 10,514 tris (12 meshes, 10 materials), 22 joints, 1 clip walk_loop (0-52 @ 24 fps, 2.17 s, key 52 = key 0). Re-imported headless: skin moves 0.24 m at frame 13, seam 0.0, zmin 1 mm, centred on origin. Studio checks: tris 31% over the lightweight top (noted, kept), height 0.97 m vs 1.75 m adult (on purpose: a child), on ground OK, Draco OK. .blend saved (chibi-child.blend = final rigged + animated scene; work/chibi-child_build.blend = static build).
- Intermediates kept (compact mode, auto run, nobody to ask): work/ (static GLB, rig/, anim/ take A, animB/ take B with both clips + measures + provenance, build .blend), review/ (rest matcap + colour, final colour), scripts/.

## Licenses
- Walk motion: NVIDIA Kimodo (Kimodo-SOMA-RP-v1.1) preset clip, take B — Licensed by NVIDIA Corporation under the NVIDIA Open Model License; commercial use allowed. Retarget (tools/retarget.py) adapted from image-to-3dlab, Apache-2.0
- SkinTokens (VAST-AI): code and checkpoints MIT; kiln's Mac patch Apache-2.0 (image-to-3dlab)
- Model: original work built in this session by scripted modelling — no third-party asset, no attribution needed

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-23
