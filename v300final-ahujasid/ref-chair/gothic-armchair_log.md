# Gothic Armchair — Production Log

## Config
- Type: prop (furniture)
- Target: glTF (game asset)
- Tier: balanced (prop 1.5-5K tris, soft; up to 10K where it shows — ornate openwork)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modeling (user's brief: no marketplace, no AI generation)
- Blender: 5.2.2 LTS via mcp-for-blender (addon 1.8, protocol 14), factory scene (Cube removed, rule 6 exception)
- Live view: off (auto run, nobody watching the browser; Auto-open links false)
- Output: /private/tmp/kiln-bench/v300final-ahujasid/ref-chair/work/generated-assets/gothic-armchair/

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-ahujasid/ref-chair/refs/WoodenChair_01.png (335x1024, alpha cut-out already present)
- Camera (estimated): azimuth ~15 deg from the chair's front toward the viewer's LEFT, elevation ~15 deg,
  mild perspective (back plane reads 0.89x the front: back legs floor->seat 245 px vs front 275 px).
- Assumptions (auto mode, not asked):
  - Real size: seat height 0.465 m (usual dining/arm-chair seat). Everything else scaled from pixels:
    front leg centres 0.37 m apart, back posts 0.34 m (back slightly narrower, measured), leg depth 0.42 m,
    total height ~1.74 m (to finial tips), arch springing 1.29 m, arch apex 1.59 m, arms 0.66-0.70 m.
  - Views: only one 3/4 front-left view. UNSEEN and kept plain: the back of the back panel (tracery is
    see-through so it is the same openwork), the chair's left side apron (assumed same as the visible right
    side), the back apron/rail (plain), the underside of the seat (flat).
- Brief enrichment — inventory (part / how it meets):
  - back posts: square ~45 mm, floor to 1.58 m, continuous with back legs; a column of small round beads on the
    front face from arm level to the top → SM_GothicArmchair_PostL/R (beads in the post mesh)
  - finials: square cap plate, collar, 4 curled fleur-de-lis leaves, pointed bud on top; SIT on the cap → Finial_L/R
  - back frame: lancet (pointed) arch frame, moulded, its stiles TOUCH the posts' inner faces; apex ~ cap height;
    open background between arch and posts → BackFrame
  - tracery: teardrop (pointed ring) with mullion from its tip to the arch apex and two short spokes to the arch;
    quatrefoil of 4 rings inside it; carved 4-petal flower boss at its centre (proud of the face); a broad
    segmental band below; lower register of 2 pointed arches each split into 2 lancets by mullions with small
    cusps; bottom rail just above the seat → BackTracery (all bars ENTER the frame)
  - seat: flat board with moulded, overhanging edge → Seat
  - aprons: front and sides under the seat, scalloped cusped arches with pendant drops (3 per side) → Apron_*
  - front legs: square block at apron level, turned shaft with rings and twisted reeds, square block at the
    stretcher, round bun foot → LegFL/FR
  - arm supports: turned columns above the seat over the front legs, plinth, reeds, rings → ArmColumn_L/R
  - arms: curved rail from back post sweeping out then forward, ending in a rounded knob over the column; ENTERS
    the post → Arm_L/R
  - stretchers: box stretchers near the floor (front, both sides, back), square chamfered, ENTER the leg blocks
    → Stretchers
  - material: one wood — dark reddish-brown walnut-like, satin, darker in recesses, lighter worn edges
- Visual comparison: close match on parts and proportions (every inventory line present); colour slightly cooler/greyer than the photo

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Generation params: none (scripted)

## Source
- Method: scripted (Blender Python), script kept in scripts/build.py

## Pipeline
- BRIEF: inventory + assumptions above (2026-10-22)
- SOURCE: scripted modeling chosen by the brief (no marketplace, no AI). scripts/build.py builds 16 parts
  (SM_GothicArmchair_*), one material M_Wood_Walnut. Measure: tools/fidelity_check.py --view front
  --elevation 15 --azimuth -15 (camera on the viewer's left), HDRI studio_small_09 (Poly Haven, CC0).
- Rounds (reference image, openwork → judged on proportions + side_by_side, silhouette IoU is information):
  - v1: 13,132 tris first build → 10,380 (beads 36→12 tris, arm/finial density). silhouette 0.531, face iou 0.45
    (f 0.84, offset -39 mm). Gaps: teardrop too small/straight-sided, quatrefoil small, lower lancets too low,
    arms low with arm end-cap showing past the knob (joint sheet), finial leaves closed, 2.08x tier top.
    Joints sheet looked at (35): tracery Y/T joints enter, rails/stretchers enter blocks; arm end fixed in v2.
  - v2: changed tracery (pointed-arch teardrop + round bottom, quatrefoil r 45 mm, band and lancets raised),
    arms (front raised to 0.69 m, sweep out to 0.236 m, larger knob forward of the column, tube ends inside it),
    finial leaves flared; lathe 24→20 sides → 9,852 tris. Measured: silhouette 0.523, face iou 0.37 (f 0.70,
    offset -34 mm) — face flags are tracery openings, too coarse at this scale to rank (alarm, not judge);
    side_by_side: parts and proportions match. Black spots in the render traced by ray-cast to COPLANAR front
    faces (stile/rail, crossing tracery bars of equal depth) → v3.
  - v3: crossing bars given staggered depths (rail +8 mm, mullions +3..+5 mm, rings alternate), beads shaded
    smooth, inner lancet feet 1 mm apart (were sharing vertices → 1 fused edge). Measured on the final GLB.
- Import: scripted (implicit). 16 parts, 9,852 tris, 0.517 x 0.528 x 1.715 m, on the ground, centred (0, -0.002)
- Cleanup: weld 1e-4 with normals kept (0 merged), recalc normals (0 flipped), 0 loose, 0 degenerate, 0 fused,
  0 non-manifold, transforms applied, origin = centre of base, names SM_/_Mesh, orphans cleaned, 1 material.
  Attachment (BVH): finials enter caps 2 mm, arms enter posts, stiles enter posts 2 mm, boss sinks into rings;
  seat flagged by the vertex test only (corner vertices) — legs/posts meet its faces. Poly: 9,852 = 1.97x the
  balanced prop top (5K) — kept: in tracery 2.5K, turned legs/columns 2.6K, beads/posts 1.3K, arms 1.4K.
- Texturing: one physical material M_Wood_Walnut on all 16 parts. Palette sampled from the photo (sRGB 10/50/90 %:
  posts (75,55,52)/(89,71,70)/(106,85,80), legs (52,38,35)/(86,68,64)/(114,86,78), lit seat (129,92,78)).
  Base: Poly Haven dark_wood 2k (CC0), chosen against the photo crop over wood_table_001 / rosewood_veneer1 (too
  glossy, orange) and fine_grained_wood (grey); projected along each part's grain (posts, legs, frame, tracery
  vertical; seat/rails/aprons along X; arms along Y), contrast 0.6, saturation 0.5, tint (1.22,1.71,2.08) to the
  palette mid. Wear (one layer): cavities darkened x0.45..1 and +0.15 rougher from a baked AO (4 cm). Relief:
  scan height through Bump → baked tangent normal map. UVs: one atlas, Smart UV 66 deg, concave pack, 4 px margin,
  48 % used, 854 px/m at 2048 (427 px/m after the 1024 WebP pass); uv_check 0 FAIL 0 WARN. Baked headless
  (scripts/tex_bake.py): T_GothicArmchair_BaseColor (emission → float → sRGB byte), _Roughness, _Normal, 2048.
  Source shaders kept in the .blend (M_Wood_Walnut_Src_V/HX/HY, fake user) for re-bakes.
  Material round: first bake read grey/streaky (weathered) vs the photo's warm satin → contrast 1→0.6, sat
  0.35→0.5 (half-way). Mean base colour of used texels sRGB (78,61,59) vs photo mid (88,69,66), roughness 0.49.
  Looked at: two opposite angles + seat/arms close-up, material shading.
  - v3 (final measure, on web/gothic-armchair_final.glb): silhouette 0.523, face iou 0.457 (f 0.836, offset -34 mm);
    black spots gone; luminance per band 0.27-0.31 vs photo 0.29-0.32. Remaining gap (cap of 3 measures reached,
    not corrected): saturation 0.17-0.20 vs 0.23-0.28 and warmth 0.055 vs 0.075-0.104 — the wood reads a little
    cooler/greyer than the photo's reddish brown (next fix: SAT 0.5→~0.7 and a warmer tint, then re-bake).
    Smaller shape differences: photo's lancet cusps are spikier, apron arches deeper, finial bud rounder.
- Material audit (rule 19): M_Wood_Walnut, 1 Principled, no procedural nodes; GLB read back: baseColorTexture,
  metallicRoughnessTexture, normalTexture filled, 3 images, 16 meshes, 1 material.
- Export: gothic-armchair_original.glb 12.02 MB (PNG 2048, no Draco), export_apply=False.
- Optimize (auto, rule 20 steps): gltf-transform resize 1024 → webp q90 → draco: web/gothic-armchair_final.glb
  449 KB (-96 %), 9,852 tris, EXT_texture_webp + KHR_draco_mesh_compression (client needs a Draco decoder).
  gothic-armchair_preview.glb = copy of _original (no Draco/WebP) — opens in macOS Quick Look.
- Studio checks: no WARN (notes: tris 97 % over the tier top, licences listed).
- Intermediates kept (auto, nobody to answer — compact cleanup to propose): review/rounds/{v1,v2,uv}.glb,
  review/front/ (renders, joints), review/crops/, textures/ (bakes as PNG + Poly Haven sources, also packed in .blend).

## Licenses
- Reference image: user-provided, used as reference only
- dark_wood texture set (diffuse, rough, displacement, 2k): CC0 — Source: Poly Haven (polyhaven.com), via the public API
- studio_small_09 HDRI (review renders only, not shipped): CC0 — Poly Haven (polyhaven.com)

## Checkpoint
- Last completed step: [7] EXPORT (pipeline complete)
- Timestamp: 2026-10-22
