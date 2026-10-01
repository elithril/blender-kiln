# Gothic Wooden Chair — Production Log

## Config
- Type: prop (furniture — Gothic high-back armchair / throne)
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact (original + final + .blend + log; working scripts, textures and review renders kept in sub-folders)
- Environment: macOS arm64 (24 GB unified), Blender 5.2.2 LTS, blender-mcp addon 1.8 (up to date, telemetry off), gltf-transform + gltfpack present
- Scene: Blender factory scene (Cube, Camera, Light, no .blend loaded). The factory Cube was removed before building (rule 6 exception); Camera and Light left untouched.

## Reference Image
- Path: /private/tmp/kiln-bench/ref-kiln-v15gen/ref-chair/refs/WoodenChair_01.png (335×1024, alpha)
- Camera read from the image, fixed before modelling: **elevation ≈ 20°** (front feet 80–90 px below the rear feet, seat top visible); **azimuth ≈ −17°** (the chair's left side, image left, is visible; the rear posts sit ~71 px left of the front legs). Near-orthographic: the posts stay vertical.
- **Real size, assumed** (one photo has no scale): seat height 0.46 m. The measured ratio gives an overall height of 1.61 m. Shipped bbox is **0.47 × 0.53 × 1.61 m** (W × D × H).
- Depth (front leg → rear post 0.42 m) cannot be separated from the azimuth in one photo. It is an assumption.
- **Not visible in the photo, so invented:** the back of the back panel (made two-sided, same tracery), the post backs (no beads), the underside, the rear apron (plain board), the right side apron (mirror of the left).
- Side and top views would settle the depth and the back. None were given, and auto mode did not block on them.

### Inventory (from 3× crops, before modelling) — ticked at the final review
| Detail | Part | How it meets | Final |
|---|---|---|---|
| 2 tall square rear posts, chamfered | RearPost_L/R | run floor → 1.43 m; the back panel enters them | ✓ |
| Square cap plate + tulip finial (4 curled leaves + turned bud) | PostCap, Finial | sits on the post top, leaves rooted in the neck | ✓ (photo's leaves are a little more fleur-de-lis) |
| Bead row in a groove on the post front faces | PostBeads | beads half-embedded between two fillets | ✓ |
| Pointed (lancet) arch frame, stiles down to the back rail | BackArch | stiles enter the posts (4 mm) and the rail | ✓ |
| Stem from the arch apex to the teardrop apex | BackStem | enters both | ✓ |
| Teardrop (vesica) wrapping a circle | BackTeardrop | circle tangent to and entering the stiles | ✓ |
| Cusped spurs between the teardrop and the arch | BackSpurs | enter both | ✓ |
| Quatrefoil (4 ring lobes) | BackQuatrefoil | lobes enter the teardrop ring | ✓ (photo's lobes slightly larger) |
| 4+4-petal flower boss, proud | BackFlower | sits proud on the lobe crossing | ✓ |
| Arched band under the circle, with a pendant cusp | BackBand | ends enter the stiles | ✓ |
| Two pointed arches, each over two round lancets, spikes up into the band | BackArcade | spring from the mullions/stiles | ✓ |
| 3 mullions with diamond cusps, half-cusps on the stiles | BackMullions | enter the rail and the arcade | ✓ |
| Moulded back rail just above the seat (gap visible in the photo) | BackRail(+Lip) | between the posts | ✓ |
| Thick seat, moulded front/side edge, tapered toward the back | Seat, SeatMoulding | legs and posts pass through it | ✓ |
| Front apron with 4 cusped round arches; side aprons with 3 | ApronFront/Side | between the leg blocks | ✓ (photo's arches read deeper/rounder) |
| Front legs: bun foot, square block, turned shaft with ring stacks, square apron block | FrontLeg* | one column through the seat | ✓ (the shaft's **fluting was not modelled**) |
| Arm supports: square block on the seat, turned column | FrontLegTurned, ArmBlock | continuation of the front leg | ✓ (fluting not modelled) |
| Curved arms bowing outward, rounded knuckle cap | Arm, ArmKnuckle | arm enters the post and the knuckle | ✓ (photo's arm is a bit thicker and scrolls more) |
| Low box stretcher (front, sides, rear) | Stretcher* | ends enter the foot blocks/posts | ✓ |
| Rear posts' square foot blocks | RearFoot | post enters the block | ✓ |

Joints: `fidelity_check.py` rendered every end of a long part that touches another (`review/*/joints/`, contact sheet at `review/round1/joints_sheet_a.png`). I looked at all of them: every part enters its host with its section unchanged. No flat cuts or flared feet.

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Hunyuan3D params: N/A (scripted modelling, as the brief required)

## Source
- Method: **scripted modelling** in Blender Python. No marketplace, no AI generation.
- Scripts: `scripts/kiln_geo.py` (sweep / lathe / box / slab builders, each writing its own world-scaled UVs with the grain along the part), `scripts/build_chair.py` (all 44 parts), `scripts/material.py`, `scripts/cleanup_export.py`.

## Pipeline
- Build: 44 separate parts in collection `GothicChair_Parts`, all sharing one material. They are kept in the .blend (hidden), which is the editable version.
- Export mesh: the parts are joined into one game mesh, **SM_GothicChair** / SM_GothicChair_Mesh (one mesh, one material, one draw call).
- Cleanup (per part, before the join): merge by distance 0.1 mm (10 verts), remove loose (0), dissolve degenerate, recalculate normals. Transforms are identity, origin at the floor centre.
  - Manifold check on the joined mesh: **fused edges 0, open edges 0** (watertight).
- Material export audit: no procedural nodes, all images packed. **OK**.
- Triangles: **9,908**, about 2× the balanced top of 5,000 (within the soft limit, not cut). Where they go:
  - bead rows: 1.3k
  - quatrefoil + arcade + teardrop tracery: 2.4k
  - turned legs and arm supports: 1.2k
  - finials: 1.3k
  - arms and knuckles: 1.2k
- Texturing (zone: whole chair, one physical material): **M_Wood_Mahogany**, built from the Poly Haven `dark_wood` scan (CC0).
  - It was chosen by comparing its thumbnail with the photo: fine straight mahogany grain, satin finish.
  - Base colour: the scan desaturated to 55% of its chroma variation, then scaled to a mean of sRGB (0.33, 0.237, 0.214). The photo palette, sampled over the whole chair, is dark 0.22/0.16/0.15, mid 0.36/0.28/0.27, light 0.51/0.38/0.33. The mid includes sheen, so the albedo was set a little darker and redder.
  - Roughness: the scan remapped to 0.24–0.44 (satin).
  - Normal map: the scan's own (OpenGL), strength 0.7.
  - All UVs are tiling (1 texture tile = 0.5 m), wrap REPEAT, with grain along each part's length. This is used instead of a baked atlas, so the 1024 textures keep their grain at full density on a 1.6 m object.
- Optimize (auto preset, separate steps per rule 20): resize 1024 (already 1024) → WebP → Draco. **3.29 MB → 238.5 KB (−93%)**.
  - Draco needs a decoder on the client (three.js `DRACOLoader`, Babylon built-in).
  - The normal map stays 1024 WebP. The source scan's relief is very subtle (std 0.005), and WebP keeps std ≈ 0.0035.
- Export: GLB, `export_apply=False`, Y-up, backface culling on (doubleSided false, the mesh is closed). `gltf-transform validate`: **no errors, no warnings**.

### Review — measured (`tools/fidelity_check.py`, front, elev 20, az −17, studio_small_09 HDRI)
| Measure | IoU | What the numbers said | What changed |
|---|---|---|---|
| round 0 (`_original.glb`) | 0.640 | Width +9 / +13 / +13 % (bands 4, 2, 5). Apron core +124% (the cap triangulator had **filled the cusped openings**). Black blotches in the render. Highlights ≈ 0. | — |
| round 1 | 0.688 | Width now +5–9 %. Black blotches still there. Joints all enter correctly. | Apron rebuilt column by column (concave cut-outs can't be filled). Sweep caps get UVs from the profile. **Width −5% on X** (half-way). |
| round 2 | 0.674 | Blotches gone. Sheen visible. Sat bands 1–2 +0.08–0.09 (bands 3–5 matched). | Blotches came from **coplanar overlapping tracery faces** (bars the same depth as the frame they enter): depths stepped 24/21/18/16 mm, cusps proud at 27 mm. Arch band widened, arms raised and bowed out, bigger knuckles and finials. **Material: roughness 0.36–0.60 → 0.24–0.44.** |
| round 3, beyond the two-round limit (logged) | — | — | Base-colour target chroma moved half-way (B 0.205 → 0.214), since only bands 1–2 were over. Then cosmetic: the two arcade arches no longer share an end cap, the side lobes are 1 mm shallower, and the centre mullion covers the arches' meeting point. |
| **final (`_final.glb`, shipped file)** | **0.674** | Sat band 2 +0.068 (was +0.09). Warm band 4 −0.028. Width bands 4–5 +6 / +9 %. Highlights still below the photo (depends on the light, not tuned to). | Stopped here. |

- Visual comparison: **close match**. Same parts, proportions, tracery program and colour family.
- Known differences:
  - No fluting on the turned shafts.
  - The tracery has no double-line mouldings.
  - The apron arches are a little shallower than the photo's.
  - The arms are slightly thinner.
  - The photo's upper back reads a touch greyer.

## Licenses
- Poly Haven `dark_wood` texture set (diffuse, roughness, normal GL, 1k): **CC0**. Source: Poly Haven (polyhaven.com), via the public API.
- Poly Haven `studio_small_09` HDRI (review renders only, not shipped): **CC0**. Source: Poly Haven (polyhaven.com), via the public API.
- Geometry: scripted in this session, no third-party meshes.

## Files
- `gothic-wooden-chair_final.glb`: 238.5 KB, 9,908 tris, 1 mesh, 1 material (3 × 1024 WebP), Draco
- `gothic-wooden-chair_original.glb`: 3.29 MB, the uncompressed export (PNG/JPEG textures)
- `gothic-wooden-chair.blend`: 44 editable parts (hidden collection `GothicChair_Parts`) plus the joined export mesh. Textures packed, review camera/world `REV_*`.
- `scripts/`, `textures/` (tinted maps + Poly Haven sources), `review/` (crops, renders, fidelity rounds, joint renders)

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-01 20:55
