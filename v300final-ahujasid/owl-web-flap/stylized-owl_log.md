# Stylized Owl — Production Log

## Config
- Type: character (bird, winged)
- Target: glTF (web)
- Tier: lightweight (character 3-8K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modeling (brief: no marketplace, no AI)
- Output: /private/tmp/kiln-bench/v300final-ahujasid/owl-web-flap/work/generated-assets/stylized-owl
- Environment: Blender 5.2.2 LTS via mcp-for-blender (addon 1.8, protocol 14, up to date)

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Brief (confirmed, auto mode)
Stylised cartoon owl for a website, ~0.30 m tall standing on a branch-less base (feet on Z=0),
big head with large eyes + highlights, eyelids, ear tufts, beak, belly patch, two wings that
flap in a seamless looping clip. Rigged (wings), not a biped → no T-pose (rule 13 targets bipeds;
wings are rest-folded half open so they can flap).
Assumptions: real size 0.30 m; clip "Flap" 24 fps, exact loop.

## Prompts (copy-paste ready)
- Concept art: none (scripted from brief)

## Source
- Method: scripted (Blender Python), body one skin (metaballs + voxel remesh), eyes/lids/beak/wings separate

## Pipeline
- CONFIG/BRIEF: factory scene found (Cube, Camera, Light, unsaved) → Cube removed (rule 6 exception)

- SOURCE/IMPORT (scripted, scripts/build_owl.py): v1 metaballs — toes, tufts, tail came out
  detached and QuadriFlow refused the skin → dropped. v2 overlapping ellipsoids + voxel 2.5 mm +
  QuadriFlow: per-face region colours read as staircases, back grooves 4-7 mm between the
  stacked torso/shoulder/head volumes. v3 (kept): one superellipsoid body+head (p 2.7) + tufts,
  tail, legs, 6 toes → voxel 2.5 mm, smooth ×14, QuadriFlow → 2,194 v / 4,384 tris, back profile
  monotonic; regions as soft vertex colours (COLOR_0) in one material M_Owl_Body.
  Wings: 5 ellipsoids each → voxel 1.8 mm → QuadriFlow 650 tris, rest hanging at the sides.
  Eyes 30 mm radius, 57 % out of the skin, 2 emissive glints each; upper lid shells 1.09 × eye
  radius (open = tilted back 55°); beak teardrop.
  Total 12 objects, 8,316 tris (lightweight character 3-8K: +4 %, spent on the eyes/lids),
  bbox 0.195 × 0.190 × 0.327 m, lowest point Z = 0.000.
- CLEANUP (scripts/cleanup_owl.py): transforms applied, merge 1e-4 m (0 merged), degenerate
  dissolve, loose removed, normals recalculated (signed volume > 0 on every part); 12 meshes,
  0 fused / 0 open edges; origins at (0,0,0) = centre of base; body on ground; orphans purged;
  .blend saved. Poly: 8,316 tris vs 3-8K → within 2× top, no reduction proposed.
- TEXTURING: skipped (scripted, materials assigned at build). 9 Principled materials, values
  only; M_Owl_Body = Color Attribute "Col" → Base Color (exports as COLOR_0). No image
  textures, so no UV bake/uv_check needed.
- RIG (scripts/rig_owl.py): winged, kiln-built, not a humanoid/quadruped → hand-built rig
  SK_StylizedOwl_Armature: Root (non-deform) → Body → LeftWing/LeftWingTip, RightWing/RightWingTip,
  LeftEyelid, RightEyelid = 7 deform bones. Rule 26: skin 2,194 v welded; 4,182 v total / 7 =
  597 verts/bone. Explicit weights: body skin, eyes, glints, beak 100 % Body (rigid, no fold);
  lids 100 % to their lid bone; wings blended shoulder→tip (smoothstep 35-75 % of length).
  Dead bones 0, unweighted 0, max 2 influences. (Bug fixed: zero-weight cleanup first left 127
  wing vertices unweighted.)
- ANIMATE (scripts/animate_owl.py): route = wings → UniMate per animation.md, NOT used: its
  weights are CC BY-NC 4.0 (a website may be commercial) and it needs a 3.2 GB install that must be
  asked; a wing flap is a periodic rotation of two rigid-ish chains, so hand keys (articulated
  route) — commercial-safe, no install. Signs measured (rule 4): LeftWing +0.3 rad → tip −50 mm
  outward (raise = −), RightWing +52 mm (raise = +); lids +0.3 → +3.6 mm toward the eye front
  (close = +). Clip A_StylizedOwl_Flap: 48 frames @ 24 fps = 2 s, 3 flaps (16 f each: 60 % slow
  upstroke to 125°, 40 % fast downstroke, C1 turns), wing tips trail the shoulder by 9 % of a flap,
  body rises 0-6 mm on the downstroke (never below the ground) and leans back 3° at the top, one
  blink f28-36 (3 closing, 1 held, 4 opening, 150°). Keyed every frame 0..48, key 48 = key 0
  (rule 5), playback range 0-47. v1 raise 100° read timid (wings stop at horizontal) and the
  glints poked through the closed lid → raise 125°, glints moved onto the eye surface, lid
  1.09 → 1.13 × eye radius.
- REVIEW (matcap mandatory, tools/review_renders.py on _original.glb, review/): round 1 found
  ragged primary-feather tips on the voxel+QuadriFlow wings (325 faces) and the face-disc colour
  bleeding onto the side of the head; round 2 (thicker feathers, 412 faces) still ragged → wings
  rebuilt as a directly sculpted ellipsoid (36×10, poles on the thickness, 3 scalloped feather
  lobes, 360 faces, no remesh); disc colour limited to front-facing normals (0.3-0.6). Round 3:
  body skin smooth in matcap (no groove, no crease), wings clean at rest and mid-flap.
  Left on purpose: the wing's contact line on the body side; sawtooth edges of the soft colour
  regions (vertex colours across quads, read as ruffled feathers).
- EXPORT original: stylized-owl_original.glb 281.6 kB, 8,312 tris, 12 meshes + 8-joint skin,
  clip A_StylizedOwl_Flap 49 keys 0-2.0 s (closing key = first), COLOR_0 on the body; material
  audit: 9/9 Principled, nothing lost. export_apply=False.
- OPTIMIZE (auto): no textures → WebP step n/a; gltf-transform draco (alone, rule 20; no
  simplify) → web/stylized-owl_final.glb 288.4 → 63.9 kB (−78 %), 8,312 tris, skin + 49-key clip
  intact, extensionsUsed [KHR_draco_mesh_compression]. stylized-owl_preview.glb = copy of
  _original (no Draco/WebP, extensionsUsed none) for macOS Quick Look.
- EXPORT: .blend saved (stylized-owl.blend, save_version 0). Studio live view closed; studio checks:
  0 WARN; notes = 8,312 tris (+4 % over lightweight 8K, kept: eyes/lids), height 0.33 m (on
  purpose: an owl, not a human), on ground, Draco on final.
- Files kept (compact, auto mode — nobody to confirm a cleanup): _original.glb, web/_final.glb,
  _preview.glb, .blend, log; plus working files scripts/ (build, cleanup, rig, animate, export)
  and review/ (matcap + colour renders) — removable on request.

## Licenses
- No outside resources: geometry, materials and animation all scripted in this session (scripts/).

## Checkpoint
- Last completed step: [7] EXPORT (pipeline complete)
- Timestamp: 2026-10-23
