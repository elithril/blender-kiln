# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Decimation: approved in advance by the brief (original file kept)
- Environment: Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 13, up to date), gltf-transform present

## Reference Image
- Path: <repo>/bench/runs/_refs/Lantern_01.png (394x1023, alpha)
- Assumptions (one photo cannot say them):
  - Real size: 0.30 m overall height, bail raised (usual hurricane lantern size). Not given by the brief.
  - Camera elevation: 8 deg, read on the bell-bottom and gallery ellipses (minor/major ~0.09-0.12), fixed before measuring. Azimuth 0 (frontal).
  - No side/top views supplied: the back is TRELLIS.2's invention, unverified.
- Inventory (from 2x crops), and how parts meet:
  - top loop: closed pentagon wire on a hinge clip, sitting on the cap -> Wire (TopLoop)
  - cap: stepped disc, wide brim; vent slots, dark, all round the chimney -> Body
  - bell / chimney: dark bronze, horizontal ridge band -> Body
  - air tubes: two side tubes, bell to tank, square bends -> Body
  - bail: wide wire arch, small kink at the peak, ends hooked onto the tube tops -> Wire (Bail)
  - globe: smoky neutral glass, frost specks -> Globe (own material)
  - wire guard: two tilted rings crossing in an X front and back, two side posts -> Wire
  - burner gallery, wick lever (right), small bracket (left tube) -> Body
  - tank: ribbed, filler cap front right -> Body
- Final inventory tick (side_by_side.png): all present. Tubes read flatter and more jagged than the reference's round tubes (decimation of the TRELLIS tubes).
- Visual comparison: partial-to-close match (shape kept from TRELLIS.2, materials pulled toward the reference)

## Prompts (copy-paste ready)
- Concept art: none (user image)
- Generation: TRELLIS.2, local, made by the user; params not known to this session

## Source
- Method: AI (TRELLIS.2, local) — user-supplied raw generation
- File: <repo>/bench/runs/_refs/trellis/lantern_trellis.glb

## Pipeline
- Scene: Blender factory scene (Cube, Camera, Light, no .blend) -> factory Cube removed (rule 6 exception). Camera and Light left, not exported.
- Import: 191,520 faces, 194,358 verts, 1 material (base colour + metal/rough 1024 px), bbox 0.42 x 0.34 x 1.00 (TRELLIS unit height), 11.4 MB
- Scale: x0.30, origin at base centre -> 0.126 x 0.101 x 0.300 m
- High-poly cleanup: merge by distance (109,963 seam verts), loose removed, degenerate dissolve, 2 specks removed. Measured: 13,777 fused edges (>2 faces) and 10,181 open edges — the generator's overlapping thin shells (visible as cracks on the bell). Recalc normals flipped 93,631 faces (inconsistent orientation). Kept only as the bake source, hidden in collection "Source".
- Low-poly build (no fused edge survives):
  - Body: high-poly minus bail, loop and globe zone -> Solidify 1 mm -> voxel remesh 0.6 mm (a plain voxel remesh deleted the single-sided tank and tubes; the solidify closes them) -> islands < 500 verts dropped (filler cap, burner disc, left bracket kept) -> decimate collapse 2 passes 460,820 -> 40,000 -> 2,600 tris. + simple burner (120 tris). Fused 0, open 0.
  - Thin parts never decimated (rule): bail and pentagon loop traced from the high-poly's vertices (angular binning, outermost run), rebuilt as NURBS curves with round bevel (bail r 1.5 mm, loop r 1.4 mm); bail's left end below z 0.192 mirrored from the right (hidden by the tube in the trace). Guard: two tilted rings fitted to the high-poly points (centre z 0.096, +-26 mm tilt, 5 mm off the glass), bent outward near +-X to meet the side posts (traced, r 47.7 -> 39.7 mm). Fused 0, open 0.
  - Globe: 64-segment smooth lathe on the high-poly's measured shell profile (r 26.5 -> 35 -> 19.8 mm, z 0.065-0.148), open ends tucked into gallery and bell (128 open rim edges, intended).
  - Attachment (BVH, 0.5 mm): every part within 0.16 mm of another; rings meet posts, posts meet body.
- Cleanup (low): merge by distance, recalc normals, remove loose, degenerate dissolve, transforms applied, origin base centre. Smooth-by-angle (40 deg) applied as geometry, not left as a GN modifier (rule 18). Sharp edges cleared on wires.
- Poly count: 6,092 tris (body 2,720, wire 2,092, glass 1,280) — 22% above the balanced prop range's 5,000. Alert only (rule 4), under the 50% threshold. The overshoot is the wire curves.
- UVs: Smart UV Project per part. Shortcut vs reference-fidelity § 4 (cylindrical UVs on turned parts): the colour is transferred from the source, not painted procedurally along the profile, so island direction does not matter here.
- Texturing (bake from high-poly, Cycles, selected-to-active, cage 2 mm):
  - Base colour via Emission into float -> converted to sRGB bytes before export.
  - Metal/roughness via Emission (TRELLIS packed G=rough, B=metal) -> ORM byte image (R=1).
  - Normal (tangent): first bakes showed silver patches — inconsistent high-poly normals. Fix: bake source copy with each face oriented to the nearest low-poly normal; 29% of body texels with z<0.55 (sideways rays into the inner walls) flattened to (0.5,0.5,1).
  - Glass: Principled, roughness 0.1, Coat 1, IOR 1.5, blend, double-sided; frost (fine specks x broad blotches) baked into one RGBA sRGB 512 px texture; neutral tint sampled from the reference (globe sRGB 0.06/0.10/0.21 dark/mid/light).
  - Textures: Body 1024 (BaseColor, ORM, N), Wire 512, Glass 512. All packed.
- Material export audit (rule 19): all 3 materials OK — no procedural nodes, no colour ramps, no float images, all packed.
- Review (fidelity_check.py on the shipped _final.glb, studio_small_09 HDRI, elevation 8, azimuth 0):
  - Measure 1: IoU 0.715. Widths +9-15% (TRELLIS proportions — kept per brief, never rescaled). Saturation bell/tank 0.52 vs 0.33, warmth +0.08/+0.09; glass clearer than the reference.
    -> Correction 1 (halfway): body+wire chroma x0.75 at constant luminance; glass alpha median 0.63 -> 0.75.
  - Measure 2: bell sat 0.41, tank in range; top band (wire) fell to 0.43 vs 0.52.
    -> Correction 2 (last): wire chroma restored (x1/0.75), body chroma x0.9.
  - Measure 3 (final): IoU 0.715. Sat per band (model/ref): 0.545/0.523, 0.405/0.330, 0.307/0.354, 0.218/0.262, 0.376/0.327. Warmth still +0.04-0.05 on bell, tank and top. Detail matches except bell (0.030 vs 0.040). Highlights and luminance higher (light-dependent alarms, not tuned). Metal base median 0.258 (body), 0.373 (wire), above the 0.15 floor.
- Optimize (auto, glTF default preset, individual steps — rule 20): resize 1024 cap -> WebP q90 -> Draco. 3.88 MB -> 0.74 MB (-81%). Draco needs a decoder on the client.
- Export: hurricane-lantern_final.glb, 737,744 bytes, 6,092 tris, 3 meshes under root SM_HurricaneLantern, KHR_materials_clearcoat + KHR_draco_mesh_compression + EXT_texture_webp. gltf-transform validate: no errors (warnings: generated tangent space, unused buffer views).

## Files (compact)
- hurricane-lantern_original.glb — untouched TRELLIS.2 file (11.4 MB)
- hurricane-lantern_final.glb — shipped asset
- hurricane-lantern.blend — full history: high-poly bake source, editable curve sources (collection "Source", hidden)
- hurricane-lantern_log.md — this log
- review/ — overlay.png, side_by_side.png, fidelity_final.txt (kept beyond compact's four files, for review)

## Licenses
- Reference image Lantern_01: Poly Haven, CC0
- Raw mesh: user's own TRELLIS.2 generation (TRELLIS.2 model licence not checked this session — verify before commercial use)
- HDRI studio_small_09 (review only, not shipped): Poly Haven, CC0

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-01 10:49
