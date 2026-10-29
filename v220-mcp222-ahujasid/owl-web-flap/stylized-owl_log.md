# Stylized Owl — Production Log

## Config
- Type: character (winged)
- Target: glTF (GLB), web
- Tier: lightweight (character 3-8K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Environment: Blender 5.2.2 LTS, MCP addon 1.8 (up to date), macOS arm64, gltf-transform 4.3.0

## Reference Image
- Path: none
- Visual comparison: N/A

## Prompts
- None. Built by scripted modeling, as the brief asked (no marketplace, no AI generation)

## Source
- Method: scripted (bmesh primitives: UV spheres and cones), scripts in `scripts/`
  - `build_owl.py`: 34 parts (body, belly, head, ear tufts, eye discs/iris/pupil/glint, beak,
    6 toes, 5 belly chevrons, tail, 2 swept wings + 6 primary feathers)
  - `rig_owl.py`: weights, join, weld, rig
  - `anim_owl.py`: flap cycle
- Scene: Blender's untouched factory scene. The default Cube was removed (rule 6 exception).
  Camera and Light were kept.

## Pipeline
- Build: 34 parts. All transforms applied before joining
- Cleanup: joined into SK_Owl, merged 8 doubles (coincident cone tips), custom normals kept
  (faces unchanged), normals recalculated, loose geometry removed, orphans purged
- Result: 2,311 verts │ 2,595 faces │ 4,502 tris │ 0.566 × 0.209 × 0.335 m (W×D×H), feet at z≈0
- Materials (Principled BSDF values only, no textures):
  M_Feather_Brown, M_Feather_Dark, M_Feather_Cream, M_EyeDisc_Cream, M_Eye_Amber,
  M_Eye_Pupil, M_Beak_Orange. Export audit: 0 procedural nodes
- Rig: hand-built RIG_Owl with 7 deform bones (Root, Body, Head, Wing_{L,R}_{Upper,Lower}).
  330 verts per bone, 0 dead bones. Rigid parts are weighted 100% to one bone. The wing
  blends Upper→Lower between 38% and 62% of its span, and the primaries sit on Lower.
  The toes are on Root, so the feet stay planted.
- Animation: A_Owl_Flap, 24 frames at 24 fps (0.958 s), keys 0..23, linear, loops exactly
  - Upper wing −35°..+65° (sin). The tip lags by 0.9 rad (±22°), giving follow-through
  - Body bobs 5 mm, rising on the downstroke. The head counter-nods 3°
  - Signs measured: the left wing raises about −Y, the right about +Y
  - Seam step 0.047 m ≤ largest in-cycle step 0.052 m, so the loop is seamless
- Optimize: gltf-transform draco only (no textures, so nothing to resize or convert to WebP).
  146.2 KB → 32.0 KB (−78%)
- Export: GLB with skin and 1 animation. 4,502 tris, 7 primitives.
  Round-trip import after Draco: mesh, materials and animation all intact

## Files (compact)
- stylized-owl_original.glb (146.2 KB), stylized-owl_final.glb (32.0 KB, Draco),
  stylized-owl.blend, stylized-owl_log.md, scripts/

## Licenses
- All geometry and materials created from scratch. No third-party assets

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
