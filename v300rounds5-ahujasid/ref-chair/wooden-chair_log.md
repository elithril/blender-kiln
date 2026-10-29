# Wooden Chair (Gothic high-back armchair) — Production Log

## Config
- Type: prop (furniture)
- Target: glTF (game asset)
- Tier: balanced (prop 1.5–5K tris; up to 2× = 10K acceptable when spent where it shows)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling in Blender (brief: no marketplace, no AI generation)
- Blender: 5.2.2 LTS, mcp-for-blender addon 1.8 (protocol 14, up to date); Poly Haven library on
- Live scene at start: Blender's untouched factory scene (Cube, Camera, Light, no .blend) → Cube removed before building (rule 6 exception)
- Output: /private/tmp/kiln-bench/v300rounds5-ahujasid/ref-chair/work/generated-assets/wooden-chair/

## Reference Image
- Path: /private/tmp/kiln-bench/v300rounds5-ahujasid/ref-chair/refs/WoodenChair_01.png (335×1024, clean alpha — no cutout needed)
- Camera: three-quarter from the FRONT-LEFT (azimuth ≈ -30°, we see the left side of the seat and the outer face of the left arm), elevation ≈ 12° (read on the seat: its top shows as a thin parallelogram)
- Brief enrichment (inventory, from 3× crops in review/crops/):
  - back posts: 2 square posts, floor to ~1.50 m, a row of small round beads on the front and outer faces → SM_WoodenChair_BackPost_L/R
  - finials: square cap plate on each post, then a tulip / fleur-de-lis finial (central pointed bud, 4 leaves curling outward) → Finial_L/R, INSERTED on the cap
  - back frame: two stiles beside the posts, rising into a pointed (Gothic) arch, peak ≈ post-top height → BackTracery (frame)
  - upper tracery: pointed teardrop loop inside the arch, a short bar joining its tip to the arch peak, a spandrel spike each side, quatrefoil of 4 interlocking rings, a carved 4-petal rosette with a central boss on the crossing → BackTracery
  - mid rail: horizontal moulded rail under the quatrefoil → BackTracery
  - lower tracery: 3 vertical mullions (the centre one wider) → 4 lancets with pointed cusped heads under the mid rail → BackTracery
  - lower back rail: moulded rail a few cm above the seat, between the posts → BackRail
  - seat: thick plank with a rounded moulded overhanging lip, reddish-brown, the lightest wood surface → Seat
  - aprons: front apron with a cusped Gothic arcade (4 arches, pendant cusps); sides assumed the same with 3 arches; back apron plain (unseen) → Apron_F/L/R/B, entering the legs
  - front legs: square block under the seat (apron joins), ring collars, fluted column with slightly twisted flutes, ring collars, square block (stretchers join), bun foot → FrontLeg_L/R
  - back legs: the back posts continue to the floor, square, with a chamfered block and foot at the bottom → BackPost_L/R
  - stretchers: low box stretcher (front, two sides, back), square section with chamfered top edges, entering the leg blocks → Stretcher_F/B/L/R
  - arm supports: square plinth on the seat, turned fluted baluster with ring collars → ArmSupport_L/R
  - armrests: curved, from the back post (entering it) sweeping down and forward, ending in a round moulded knob/pad over the support → Armrest_L/R
- Unseen in the photo (kept plain, closed, not invented): the back face of the back (tracery is pierced so it reads the same from behind), the back apron, the right side apron (assumed like the left), the underside of the seat.
- Visual comparison: close match — silhouette IoU 0.478 and face-detail IoU 0.41 on the shipped _final.glb (photo's camera: elevation 23°, azimuth -13°, ortho); every inventory line present (ticked below)

## Assumptions (auto mode — stated, not asked)
- Real size: overall height 1.67 m (finial tip), seat height 0.475 m, seat 0.58 m wide × 0.53 m deep, armrests ≈ 0.67–0.73 m. Usual size for a Gothic hall chair; the photo has no scale. Ratio seat/back-post height measured on the left back post: 0.296 of the height.
- Only one view given; side and back are inferred from furniture convention (box stretcher, symmetric).
- Export textures: one baked atlas, 1024 WebP shipped (kiln's glTF default), 2048 kept in _original.

## Intent (before the first primitive)
- Palette (sampled from the photo, sRGB): wood dark 0.19/0.17/0.15 (cavities, legs' shadow side) · wood mid 0.40/0.30/0.27 (frame) · seat mid 0.50/0.36/0.30 (worn, lit top) · highlight 0.54/0.47/0.45 (polished edges of arms and lip). Grey-violet cast on the carved frame = grime in the carving; warmer, redder where hands and bodies wear it.
- Materials: the photo shows ONE physical material — a dark-stained hardwood (walnut/mahogany-like). Following reference-fidelity § 4 (one material per physical material; the brief asks to match the reference) it is one wood shader, M_Wood_DarkStain, whose layers are: scanned wood grain (Poly Haven, CC0) tinted to the palette, cavity grime (AO), edge/hand wear (lighter, smoother). The "three materials" guideline of review-rounds is overruled by the photo: there is no metal, fabric or glass on this chair.
- Finishes: bevels on every block, rail and board edge; wear where hands go (armrest tops, knobs, seat front lip); grime in the tracery and carvings; a detail at each end — finials on the posts, knobs on the arms, bun feet on the front legs, beads on the posts.

## Prompts (copy-paste ready)
- Concept art: none (source: user image)

## Source
- Method: scripted modelling (Blender Python), from the reference image

## Pipeline
- Source: scripted (scripts/build_chair.py, run in the live Blender — its factory Cube removed, logged). 22 parts in collection WoodenChair_Parts, each with a 'Grain' UV (v along the wood grain), one material M_Wood_DarkStain (flat palette mid until texturing).
- v1: first build at 0.58 m wide — WRONG: measuring the four feet in the photo (floor rectangle) gave W ≈ 0.21 H, D ≈ 0.18 H, camera azimuth ≈ 13° toward the chair's left, elevation ≈ 23° (sin e from the floor rectangle; the seat's own parallelogram gives 19–23°). Rebuilt narrow: legs 0.34 m apart. Height corrected to 1.62 m from the back post (seat = 0.294 H at 0.475 m).
- Import (scripted, implicit): 22 objects, SM_WoodenChair_* names, on the ground, 1 unit = 1 m. Topology: 0 non-manifold; 2×132 boundary edges = the open bases of the post beads, buried 1.5 mm in the post face (invisible, kept). Attachment (BVH): every part enters a neighbour (arms → posts, posts → seat corners, mullions → rail, stretchers → leg blocks).
- Poly budget: v2 11,472 tris → trimmed by construction (ring/arch segment counts, 6-/4-sided sections on thin tracery and thorns, 5-sided beads, 12-sided knobs) to 9,928 tris = 2.0× the balanced tier's 5K top — spent on the tracery (1,522 faces), turned legs and supports, finials. Within the "up to 2×" allowance; reported, not decimated.
- Rounds (reference image, fidelity_check, --view front --elevation 23 --azimuth -13, ortho; the azimuth sign was checked on the render: -13 puts the back posts LEFT of the front legs as in the photo, +13 right — one run at +13 discarded):
  - v2: silhouette 0.462, face 0.32 (f 0.73). Side-by-side: the lower back was read WRONG — no mid rail and no pointed lancets in the photo but round-arched geometric tracery; quatrefoil taller than wide; rosette ~0.12 m wide. Rebuilt as a build error (not a reshape): big arch A stile-to-stile carrying the teardrop, two arches B with crown thorns, four interlaced arches C, three tapering mullions with thorns at 0.75 m; elliptical teardrop (rx 0.12, rz 0.15); rings dx ±0.058, dz ±0.08, r 0.05; rosette petals to ±0.06.
  - v3: silhouette 0.460, face 0.28. Gaps: back posts ~27 px right of the photo's (chair too shallow), seat edge half the photo's thickness, posts/legs thin, finial short, arm knobs inside the photo's.
  - Correction round 1 → v4: depth leg-to-post 0.30 → 0.37 m, seat 32 → 40 mm, posts 42 → 46 mm, front legs ×1.08, finial ×1.2 tall, arms flare 15 mm. Silhouette 0.476, face 0.33 (kept).
  - Correction round 2 → v5: depth 0.37 → 0.40 m (half-way; the rest of the back's leftward shift is the photo's perspective — depth lines converge left — not copied into the geometry), lower back rail raised for the photo's 4 cm see-through gap above the seat, arm supports + knobs 2 cm out / 1.2 cm forward (the photo's overhang). Silhouette 0.488, face 0.37 (f up). Kept. Proportions now frozen (2 correction rounds).
  - Remaining listed gaps, argued: "detail at 83 %/62 % +8 % across" = background seen through the right side under the seat and behind the right arm — the photo's perspective shows more of it; band 2 width +11 % = the posts' perspective offset above; highlights = light-dependent (untextured).
- Cleanup (scripts/cleanup.py, every part): transforms identity (built in world space), merge 1e-5 m → 0 merged, 0 loose, 0 degenerate, normals recalculated outward, 0 fused edges, orphans purged. 9,928 → 9,928 tris. No geometry changed → no new look needed (rule 2). .blend saved (save_version 0).
- Texturing: scripts/texture_bake.py — parts joined (copy) into SM_WoodenChair (parts kept hidden in the .blend with the procedural source material M_Wood_DarkStain_Src); atlas UV Smart Project 66° + pack; source shader = Poly Haven dark_wood (2×2 m scan) on the per-part 'Grain' UV (grain along each part), its luminance carrying the photo's mid colour (+25 % scan hue), broad noise, AO grime toward grey-violet, bevel-node edge wear + seat/arm-top wear (lighter, smoother), roughness 0.46–0.66 satin; baked EMIT colour / EMIT roughness / tangent NORMAL at 2048, float → byte sRGB, packed; shipped material = image textures only. Bug found and fixed: bake target node deselected by an `is not` comparison → black bakes. uv_check: used 41.9 %, overlap 0.6 %, 0 collapsed/flipped — 0 FAIL, 0 WARN. Look (live Blender, two opposite 3/4): textured, reads as wood.
- Review round 1 (review/round1.png, round1_clay.png, front/side_by_side.png; fresh reviewer + mine):
  1. side_by_side, under the seat (blocking): the front arcade sits recessed on the leg axis and too shallow → reads as a ragged dark band; → move the aprons flush with the leg faces, deepen the arches (band 0.415, pendants 0.345). (The black is the shadowed inside of the side aprons seen through the arches — normals checked: signed volume positive.)
  2. q_left, seat (blocking): edge reads as a square slab; the photo has a rounded moulded lip → add a bullnose moulding round the front and sides.
  3. side_by_side, seat/frame (blocking, material): plank-like coarse high-contrast grain → grain 3× finer, contrast down (ratio^0.55). Colour (too orange/light: band 2 sat 0.34 vs 0.24) is the same material region → next round, one material change per round.
  4. front/q tiles, arms (blocking): thin rails, small knob → arm section 4 × 4.4 cm, bigger knob (r 0.036) overhanging forward.
  5. close, tracery (detail): the vertical bar runs through the inside of the teardrop; the photo has it only from the teardrop tip to the arch apex → shorten.
  6. close, posts (detail): beads barely visible → larger beads (r 6 mm, 5 mm high).
  7. front, arm supports (detail): flutes too shallow to read → depth 0.2 → 0.32.
  - Argued, not changed: "make the lower lancets pointed" — the 3× crop (review/crops/lower_tracery.png) shows ROUND arches; kept. Finial fleur-de-lis (detail) → round 2.
 0.444 × 0.495 × 1.641 m (W × D × H, finial tip 1.62 m + arm knobs/flare).

## Licenses
- Reference image: user-provided
- dark_wood texture set (diffuse, roughness, normal GL, AO; 2k) — CC0, Poly Haven (polyhaven.com), via the public API; authors Dario Barresi, Dimitrios Savva, Rico Cilliers. Used as the grain source, baked into the asset's own textures.
- fine_grained_wood (2k) — CC0, Poly Haven (polyhaven.com), author Rob Tuytel. Downloaded and compared; not used in the final shader.
- studio_small_09 HDRI (1k) — CC0, Poly Haven (polyhaven.com). Review renders only, not shipped.
- Geometry: scripted in this session (scripts/build_chair.py) — no third-party mesh.

## Checkpoint
- Last completed step: [7] EXPORT — done (web/wooden-chair_final.glb, wooden-chair_original.glb, wooden-chair_preview.glb, wooden-chair.blend)
- Timestamp: 2026-10-28 21:20
