# Cat Mascot — Production Log

## Config
- Type: character (quadruped) — Target: glTF (GLB) — Tier: lightweight — Style: stylized — Mode: auto — Storage: compact
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 14, up to date)

## Reference Image
- none — Visual comparison: N/A

## Source
- Method: scripted modeling (Blender Python), no marketplace, no AI generation
- Factory scene: default Cube removed (rule 6 exception); Camera and Light left untouched

## Pipeline
- Model (`scripts/01_model.py`): body = union of ellipsoids/sphere chains (torso, chest, belly, neck, big head, cheeks, muzzle,
  4 short legs with paws, 6-point curled tail) → voxel remesh 15.5 mm → smooth ×4 → one watertight blob.
  Face parts (big eyes: white / green iris / pupil / glint; nose; pointed ears + pink inner ear) are separate shells.
- Colour: body colour is a blended vertex colour (`Col` → glTF COLOR_0) feeding M_Cat_Body: orange fur, tabby bands on the back,
  forehead marks, rings on the tail, cream muzzle / bib / belly / socks / tail tip. Face parts set to white COLOR_0 so viewers that
  multiply vertex colours don't darken them (they were black after the join — fixed).
- Cleanup: transforms applied, weld 1e-4 (0 merged — remesh output is already welded), normals recalculated, 0 non-manifold, 0 loose.
- Rig (`scripts/02_cleanup_rig.py`): hand-built 26-deform-bone animation-ready skeleton (Hips→Spine→Spine1→Neck→Head(+HeadTop_End),
  {Left,Right}{Arm,ForeArm,Hand,Fingers}, {Left,Right}{UpLeg,Leg,Foot,ToeBase}, Tail1..5). Automatic weights on the blob,
  limited to 4 influences + normalised; face parts weighted 100 % to Head and joined.
  5,092 verts / 26 deform bones = 196 verts/bone (rule 26 OK), 0 dead bones, 0 unweighted verts, max 4 influences.
  Validator: only 🟡 "root bone is Hips, expected Root" (kept: Hips is the motion root the quadruped tool drives).
- Pose test at ~40° (legs, neck, spine, tail): volume held, face parts follow the head, no tear (body has no split vertices).
- Animate: `tools/quadruped.py --motions idle,walk` (scripted, route for four-legged idle/walk; UniMate not used).
  - Walk: 32 frames @ 24 fps = 1.333 s, lateral-sequence gait, leg extension 0.912 (≤ 0.95), stance speed spread 0.00,
    **root speed 0.058 m/s** — move the cat at this speed on the page for the paws not to skate.
  - Idle: 48 frames @ 24 fps = 2.0 s, breathing + head glance + tail sway, leg extension 0.926.
  - Both actions merged onto one rig as NLA tracks "Idle" and "Walk", exported with export_animation_mode=NLA_TRACKS.
  - glTF loop closure: a closing key at frame P (= frame 0) added so the clip duration is exactly P/24 s and the player's wrap
    is seamless (without it, the last→first step happens in 0 s). Measured in the GLB: seam 0, largest real per-key step 0.059.
  - Quaternion sign continuity fixed in the GLB (`scripts/quat_continuity.py`, 123 keys flipped; same rotations).
- Material export audit (rule 19): all Principled BSDF with plain values + one Color Attribute node → nothing procedural lost.
- Optimize: gltf-transform draco — 429.6 KB → 130.5 KB (−70 %). No textures, so no resize/WebP. Geometry untouched.
- Export: cat-mascot_final.glb, 130.5 KB, 10,128 tris (body 7,896 + eyes/ears/nose 2,232), 27 joints, 2 animations (Idle, Walk).
  Round-trip import in headless Blender: both clips present and deform the mesh.
- Poly budget: 10.1K tris vs lightweight character 3-8K — 1.27× the top, within the soft 2× (spent on the round body and the eye spheres). Not decimated.
- Bbox: 0.27 × 0.76 × 0.58 m (W × L × H incl. upright tail).

## Licenses
- All geometry, materials and animation authored in this session (scripted). kiln tools/quadruped.py used to generate the cycles.
  No third-party assets.

## Files (compact)
- cat-mascot_original.glb (uncompressed), cat-mascot_final.glb (Draco), cat-mascot.blend, cat-mascot_log.md, scripts/

## Checkpoint
- Last completed step: EXPORT — 2026-10-21
