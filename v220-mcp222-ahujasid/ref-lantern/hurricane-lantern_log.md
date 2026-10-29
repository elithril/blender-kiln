# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modelling in Blender 5.2.2 LTS (blender-mcp addon 1.8) — no marketplace, no AI generation
- Scene: Blender factory scene. The default Cube was removed before building; the factory Light was hidden, not deleted

## Reference Image
- Path: /private/tmp/kiln-bench/v220-mcp222-ahujasid/ref-lantern/refs/Lantern_01.png (394×1023, alpha)
- Real size: **assumed**, none given. A Feuerhand-276-type lantern: base Ø 128 mm, 268 mm to the lid top,
  384 mm with the bail raised. Scale 0.40 mm/px; z = (958 − row) × 0.40 mm (row 958 = projected centre of the base)
- Camera: front-on, slightly high perspective. Ellipse ratios read 9° at the lid, 16° mid-height, 24° at the base;
  16° used for the review renders, fixed before modelling
- Views: single photo. The back of the lantern is not shown; the back follows the front (turned parts are
  rotationally symmetric, the frame mirrored)
- Visual comparison: **close match** (shape, parts and layout). The material is a partial match, darker and
  cooler than the first pass but smoother than the photo's hammered sheet

### Inventory (from 2–3× crops), ticked at the final review
| Detail | Part | How it meets | Final |
|---|---|---|---|
| Ribbed fount, rolled bottom bead, domed shoulder | SM_Lantern_Fount | base | ✅ |
| Filler cap, front-right on the shoulder | SM_Lantern_FillerCap | inserted in shoulder | ✅ |
| Wick-adjust knob + shaft, in front of right tube | SM_Lantern_WickKnob | shaft inserted in burner collar | ✅ |
| Burner collar ring + neck | SM_Lantern_BurnerCollar | resting/inserted in fount | ✅ |
| Globe seat dish with rolled lip | SM_Lantern_GlobeSeat | on burner neck | ✅ |
| Burner dome + wick (seen through glass) | SM_Lantern_Burner / _Wick | inside seat | ✅ |
| Smoked, frosted glass globe | SM_Lantern_Globe | ends inserted in seat and collar | ✅ |
| Crossed guard wires over the globe | SM_Lantern_GuardWires (4 helices) | ends in seat lip and collar lip | ✅ |
| Upper globe collar with lip | SM_Lantern_GlobeCollar | inserted in hood | ✅ |
| Bell hood with rolled skirt and band | SM_Lantern_Hood | — | ✅ |
| Slotted vent ring under the lid | SM_Lantern_VentRing (drum + 10 tabs) | between hood and lid | ✅ |
| Brimmed, two-tier lid | SM_Lantern_Lid | on vent ring | ✅ |
| Pentagon wire ring in a strap clip | SM_Lantern_TopRing + _HandleClip | bottom edge through the clip | ✅ |
| Two flared side tubes, arms into hood, feet into fount | SM_Lantern_Tube_L / _R | inserted both ends | ✅ |
| Tall pointed bail (traced centre line) | SM_Lantern_Bail | ends hooked into the tubes | ✅ |
| Lift rods, lift lever (R), bracket loop (L) | SM_Lantern_LiftLinkage | tube ↔ seat | ✅ (approximate shapes) |
| Raised seam bead along the tubes | — | — | ❌ not modelled |
| Drip stain under the filler cap | — | — | ❌ not reproduced |
| Hammered / dented sheet surface | normal map (scan + dents) | — | ~ weaker than the photo |

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Hunyuan3D params: N/A (scripted)

## Source
- Method: scripted modelling. Profiles were measured from the reference's alpha (core width per row), the bail
  centre line traced row by row, then lathed (32 segments; globe 64) or swept as round-bevelled curves.
- Scripts: scripts/build_lantern.py (geometry), materials.py (source shaders), cleanup.py (rule 10),
  bake.py (UV pack + bake), export.py (hierarchy, audit, GLB), review_shot.py

## Pipeline
- Build: 19 parts parented under the empty SM_Lantern. Origin at the base centre, front −Y, up +Z.
  World bbox 0.157 × 0.128 × 0.384 m (X × Y × Z)
- Attachment (§3): no part floats. Every part within 0.5 mm of another, or (tubes, bail, vent ring, knob)
  measured as inserted by triangle overlap
- Cleanup: transforms applied; merge by distance keeping shading (wire-cap duplicates: tubes 24, bail 12,
  guard wires 48, linkage 48, knob 12); normals recalculated; loose removed. 0 fused edges. Open edges only
  on the globe's two rims (128), both hidden inside the seat and collar. A fused-edge defect on the top ring
  (7 edges, overlapping start/end caps) was fixed by making the ring a cyclic curve
- Texturing: one source metal shader (M_Lantern_Metal_Src, kept in the .blend):
  - Base: Poly Haven `rusty_metal_sheet` scan (box-projected), with roughness and normal from the scan.
  - Base colours on the photo's palette: tarnish sRGB (0.33, 0.26, 0.20), bare brass (0.56, 0.43, 0.30),
    non-metal soot crust (0.075, 0.06, 0.05).
  - Bare metal follows the form (pointiness + upward faces, AO-gated). The crust sits in cavities (AO) and
    along vertical runs. Colour, roughness and relief are independent fields.
  - Thin parts (bail, wires, ring, linkage, tubes) carry a per-object edge-wear weight; on a wire, curvature
    says nothing about wear.
  - Glass: smoked (sRGB 0.17, 0.18, 0.20) with frost specks in colour and alpha (0.72–0.95), roughness
    0.08–0.45, clear coat.
  - Baked at 1024 (Cycles, 32 spp) to three texture sets: Body (12 turned parts), Frame (tubes + wires),
    Glass. Base colour converted float → sRGB bytes before export.
- Material audit (rule 19): 3 Principled materials, image textures only, no procedural nodes left
- Optimize (auto preset, rule 20, individual steps): gltf-transform resize 1024 → webp → draco.
  5.67 MB → 0.32 MB (−94%). Geometry untouched. Draco needs a decoder on the client
  (KHR_draco_mesh_compression, EXT_texture_webp required)
- Export: hurricane-lantern_final.glb, 316,868 bytes, 10,012 triangles, 19 meshes, 3 materials

### Measured reviews (tools/fidelity_check.py, front, elevation 16°, studio_small_09)
| Pass | IoU | What it said | What changed |
|---|---|---|---|
| r0 (.blend, flat bronze) | 0.791 | 12,592 tris (>2× tier); warm +0.14–0.15 in bands 2–5; band 4 core +12% | globe r ×0.955 (globe + wires measured 236 px); profiles thinned, wires 6-sided → 10,020 tris |
| r1 (.blend, aged shader) | 0.797 | warm +0.07–0.09, surface too bright and brassy vs the photo's cooler tarnish | tarnish cooler/darker, less bare brass |
| r2 (.blend) | 0.797 | warm gap roughly halved; top band (wires) all bare brass | per-object edge-wear weight on thin parts. Extended to the tubes after the 2-angle look showed them reading polished |
| final (_final.glb, shipped) | 0.796 | metal mask "scattered islands", ~46–49% non-metal by texel | **3rd correction, past the 2-round guideline**: crust limited to cavities + vertical runs, flakes/blotches moved into the (metal) tarnish, tarnish saturation toward the palette |
| final #2 (_final.glb, shipped) | 0.796 | base colour median 0.27–0.29 (above the 0.15 floor, not black); remaining flags below | stopped |

Remaining gaps, not chased:
- Width +7–9% in the lowest two bands. Largely the photo's perspective: an orthographic render cannot match
  a high close camera at the base.
- The tool still flags the Body metal mask as "scattered islands" (16% transitional texels). By surface area
  the body is 73% metal and the frame 61%. The lathe pole caps over-weight hidden texels (fount underside,
  hood underside) in a texel count.
- Warmth +0.03–0.06 in bands 2, 3 and 5. Fine detail is lower than the photo's hammered sheet (detail −0.017
  to −0.029).

### Poly budget (rule 4)
10,012 tris = 2.0× the balanced prop tier's top (5K). They go to round shapes (32-segment turned parts,
64-segment globe) and the wires. Proposal, not applied (rule 6): a ~5K variant by lathing at 20–24 segments,
globe at 48, and 4-sided wires. The poly count was not reduced in auto mode.

## Licenses
- Poly Haven `rusty_metal_sheet` texture set (1k): CC0. Source: Poly Haven (polyhaven.com), via the public API
- Poly Haven `studio_small_09` HDRI (1k): CC0. Used only for review renders, not shipped
- Reference image Lantern_01.png: user-provided
- All geometry and baked textures: made in this session

## Files (compact)
- hurricane-lantern_original.glb: export before optimize (5.67 MB)
- hurricane-lantern_final.glb: shipped (317 KB, Draco + WebP)
- hurricane-lantern.blend: full history; source shaders kept (fake user), textures packed
- hurricane-lantern_log.md: this log
- scripts/, textures/ (baked PNGs + scan set), review/ (crops, measure outputs, joint renders)

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21 12:50
