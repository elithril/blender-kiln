# Stylized Owl — Production Log

## Config
- Type: character (creature, winged)
- Target: glTF (web)
- Tier: lightweight (character 3-8K tris)
- Style: stylized
- Mode: auto
- Storage: compact
- Backend: none — scripted modelling (brief forbids marketplace and AI)
- Live view: on (Kiln Studio, --no-open)
- Environment: macOS, Apple M4 Pro (24 GB unified), Blender 5.2.2 LTS via the official Blender Lab MCP, gltf-transform + gltfpack present, SkinTokens installed (not used: kiln-built creature)
- Scene at start: untouched factory scene (Cube, Camera, Light) — Cube removed before building (rule 6 exception)

## Brief (confirmed, auto)
Stylised cartoon owl for a website, standing upright, big head with large eyes, ear tufts, beak,
round belly with a lighter feather patch, two wings at its sides, small feet. One looping clip:
wings flapping. Assumptions: height 0.30 m (a small owl, 1 unit = 1 m), front -Y, origin at the
base centre, wings held at rest folded against the body, flap opens them sideways and up.

## Reference Image
- Path: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- none (scripted)

## Source
- Method: scripted (Blender Python). Body = ONE skin (overlapping ellipsoid volumes + one voxel remesh),
  eyes/beak/feet separate rigid parts (characters.md § An animated creature).
- Rig: will be rigged and animated (wing flap). Animation route: hand keys on a small hand-built
  rig — UniMate is non-commercial (CC BY-NC 4.0) and a 3.2 GB install, unsuitable for a website asset in auto mode.

## Pipeline
- Source (scripted, scripts/build_skin.py + owl_parts.py): skin = 8 overlapping ellipsoids (body, head, 2 ear tufts, 2 wings, 2 shoulder joins), one voxel remesh at 3.5 mm -> 26,034 verts. Rigid parts: 2 eyes, 2 upper eyelid shells (1.085 x eye radius, 1.2 mm), 4 glints, beak, feet (6 toes).
  Rounds: v1 eyes flush in the head, wings bridged to the body, body above feet -> v2 eyes 2 cm proud, body lowered -> v3 lid edge smoothed (bisect) -> v4 wing/tuft tilt sign was inverted (wing tops pointed outward), fixed; body x-radius 86->81 mm so wings hang 9 mm off the body without fusing. Kept v4. Renders: review/v1..v4_source.png
- Import (scripted, implicit): measured on world-space vertices 0.268 x 0.195 x 0.314 m (W x D x H), lowest point Z = 0 (feet), origin at base centre, front -Y. Names SK_Owl (skin), SM_Owl_* (rigid parts), data-blocks *_Mesh. Pose (rule 13): a bird — wings hang folded at the sides as rest pose; hand-built rig, so no T-pose conversion needed.
- Cleanup: skin 26,040 voxel quads -> QuadriFlow 3,001 quads / 2,999 verts (0 non-manifold, 0 fused edges, one component). QuadriFlow refused the voxel mesh ("needs to be manifold…") although bmesh found no open/non-manifold edge or vertex and a 1e-5 merge removed 0 verts; it ran after a Collapse decimate (0.5, then 0.85) — logged as part of the build method (session-built mesh, lightweight tier asked by the brief). All parts: transforms applied, merge 1e-5, degenerate dissolve, loose removed, normals recalculated. Render: review/v5_cleanup.png (matcap, 4 views)

- Texturing (strategy 2, procedural Principled values only, glTF-safe): skin = ONE material M_Owl_Feathers reading a smooth colour attribute "Col" (exported as COLOR_0): brown #9A6440 base, dark #68402A wings/tufts, cream #F2DDB8 facial disc + belly, blended by analytic fields. First try assigned zones per face -> staircased edges on 6 mm quads (review/v6_texture.png), replaced. Eyes rebuilt with their pole on the gaze (8 deg outward) so pupil #120C0A / iris #F6B631 / rim #B5691C are clean latitude bands; glints emissive white; lids M_Owl_Feather_Brown; beak + feet M_Owl_Beak #E9A53B. No image textures, no UVs -> uv_check / WebP not applicable. Renders: review/v7_texture.png (EEVEE: front, 3/4, back, back 3/4).
- Rebuild after the first pose test: wings raised 105 deg pulled thin webs from the wing's inner face to the body (review/v8_pose_up.png) — the voxel remesh had fused wing and body where the gap was ~9 mm. Wing moved out (centre x 106->110 mm, tilt 14->16 deg): gap ~12 mm, webs gone (review/v10_pose_up.png). Rigid parts lowered in resolution (lids 2,412 -> 1,048 tris each, eyes 1,472 -> 720). Re-cleaned: skin 3,040 quads / 3,042 verts, 0 non-manifold, 0 fused (QuadriFlow again only after a 0.5 Collapse). Total 10,526 tris = 1.3x the lightweight top (8K), under 2x: kept — 6,080 in the skin (wings and shoulders bend), 2,096 in the two lid shells, 1,440 eyes, 480 feet.
- Rig: hand-built, 13 deform bones (Root, Hips, Spine, Neck, Head, Left/Right Arm-ForeArm-Hand per wing, Left/RightEyelid), Mixamo-style names. Route: kiln-built non-humanoid creature -> hand-built (SkinTokens is for humanoids / meshes kiln did not build). Rule 26: 3,042 welded verts / 13 = 234 verts per bone. Weights analytic (wing lobes by distance to their ellipsoids, blended along the wing chain; body by height Hips->Spine->Neck->Head; wing-root body to Spine), max 4 influences, normalised. Rigid parts 100% to one bone (eyes, glints, beak -> Head; lids -> Eyelid bones; feet -> Root). Dead bones 0; validator: no warning. Signs measured (rule 4): left wing raises with a negative turn about world Y, right with positive; lids close with +103 deg about bone Y. Pose test 105/15/10 deg + lids closed: clean (review/v10_pose_up.png).
- Animate (scripts/animate.py, hand keys — UniMate not used: CC BY-NC weights unsuitable for a website asset, 3.2 GB install): action A_Owl_Flap, 24 fps, 3 flaps in 60 frames (2.5 s), keys 0..60 with key 60 == key 0, Blender playback 0..59. Arm 6->105 deg, slow up-stroke (55%) / fast down-stroke (45%), forearm and hand trail the arm, 8 deg forward sweep on the down-stroke, body bob 6 mm after each down-stroke (feet on Root at Z = 0 every frame), head counter-pitch +-1.5 deg. One blink (frames 34-42: 3 closing, 1 held, 4 opening; lids -18 deg open -> 106 deg closed). Measured: seam 0.000 mm, per-frame vertex step median 26.8 mm, max 49.6 mm (wing tip, down-stroke), step across the seam 13.8 mm (in range). Fixes in review: glints floated over the closed lids (flattened onto the eye, inside the shell); open lids raised 18 deg (sleepy look). Renders: review/v11_flap_strip.png, review/v12_blink.png.
- Matcap review (mandatory): rest + frames 6/12, close on the shoulder (review/v13_*.png, v14_*). Left on purpose: a soft crease under the wing root on the up-stroke (frame 6) — root weights smoothed (8 passes) gave no visible change, kept; contact lines where eyes, lids and beak meet the face (separate rigid parts). Rig re-checked: 0 dead bones, max 4 influences, 0 unweighted.
- Optimize: no image textures (resize/WebP not applicable); Draco (gltf-transform draco, position 14 bits, normal 10) 357.6 KB -> 80.5 KB (-77%). Client needs a Draco decoder (three.js DRACOLoader). stylized-owl_preview.glb = copy of _original (no Draco/WebP, extensionsUsed empty) for Mac Quick Look.
- Export: GLB, export_apply=False, skins + animation, deform bones only; material audit: 7 materials, all Principled, no procedural node, no empty slot. gltf-transform validate exit 0 on original, preview, final. Headless round trip of web/stylized-owl_final.glb: 10,526 tris, 3,042 skin verts, clip A_Owl_Flap 0-60 (2.5 s), seam 0.000 mm, wingspan 0.471 m at the top of the stroke — identical to _original. Renders review/final/ + review/final_sheet.png. Studio checks: notes only (tris 31% over 8K, 0.31 m by design, origin 11 mm behind the bbox centre because beak/eyes protrude). Rest pose in the file has the lids at their modelled height; the clip holds them 18 deg higher.
- Files: web/stylized-owl_final.glb (site), stylized-owl_original.glb, stylized-owl_preview.glb, stylized-owl.blend, scripts/, review/. Compact storage, auto mode: intermediates kept and listed, nothing deleted.
- Log repair: a replacement at CLEANUP dropped the "## Licenses" heading, so the TEXTURING..EXPORT lines were not written at their phase although the Checkpoint advanced; they were restored at the end of the run from the session's measurements.

## Licenses
- All geometry and materials: made in this session (scripted), no third-party resources.

## Checkpoint
- Last completed step: [7] EXPORT
- Timestamp: 2026-10-22
