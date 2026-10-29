# Gothic Armchair (SM_GothicArmchair) — Production Log

## Config
- Type: prop (furniture)
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 14, up to date)

## Reference Image
- Path: /private/tmp/kiln-bench/v220-mcp222-ahujasid/ref-chair/refs/WoodenChair_01.png (335×1024, alpha)
- Camera read from the photo: about 20° elevation (seat-top ellipse), about 15° toward the chair's left (azimuth −15), with mild perspective (back plane about 0.84× the front plane).
- Assumed real size (none given): 1.80 m overall, seat 0.475 m, footprint 0.52 × 0.48 m, arms about 0.70–0.77 m.
- Brief enrichment / inventory (part → how it meets):
  - [x] 2 square back posts that are also the back legs, with a carved bead row on the front and outer faces → BackPost_L/R, PostBeads (beads sit on the post faces)
  - [x] Post caps + fleur-de-lis finials (bud + 4 curling leaves) → PostCap, Finial, FinialLeaves (inserted into the cap and bulb)
  - [x] Pointed Gothic arch frame between the posts → BackArchFrame (stiles inserted into the rail, touching the posts)
  - [x] Teardrop inner arch with inward cusps → BackTracery
  - [x] Quatrefoil in a circular enclosure, central 4-petal rosette → BackTracery, Rosette, RosetteBoss
  - [x] Horizontal band, Y-tracery (2 large and 4 small pointed arches), 3 slender balusters with mid spikes → BackTracery (balusters inserted into the rail and arches)
  - [x] Lower back rail → BackRail (inserted into the posts)
  - [x] Curved armrests with a round knob end → Arm_L/R (swept), ArmKnob_L/R (the arm enters the post at the back and the knob at the front)
  - [x] Turned, reeded arm supports with rings and a square base on the seat → ArmSupport_L/R (the base enters the seat)
  - [x] Seat board with a moulded edge → Seat, SeatMoulding
  - [x] Aprons with cusped arch cut-outs (front and sides), plain back apron → Apron_* (enter the legs)
  - [x] Turned front legs: bun foot, square stretcher block, reeded shaft, rings, square top block → FrontLeg_L/R
  - [x] Low box stretchers on all four sides → Stretcher_* (enter the legs)
  - [x] One material: dark reddish-brown wood with a satin finish → M_Wood_DarkWalnut
- Visual comparison: close match (same parts and layout; the tracery is simplified, see notes)

## Prompts (copy-paste ready)
- Concept art: none (user image)
- Hunyuan3D params: n/a (scripted)

## Source
- Method: scripted modelling (Blender Python, bmesh). Scripts are in `scripts/` (build_chair.py, material.py, cleanup.py, export.py)
- No marketplace model and no AI generation.

## Pipeline
- Build: 32 parts in collection `SM_GothicArmchair_Parts`, made of lathes (legs, supports, finials, knobs), swept sections (tracery, arms, moulding, leaves) and boxes. Every part was checked for attachment (BVH distance plus an inside test), and the 64 joints rendered by fidelity_check were looked at: all are insertions.
- Cleanup: merge by distance (1e-5, on exact duplicates only), dissolve degenerate, remove loose, recalc normals, sharp edges marked from 40°. Fused edges: 0. Transforms: identity. Base at z = 0. The pivot is the world origin; the bounding-box centre is at y −0.015.
  - PostBeads: 132 open 4-face studs whose backs are buried in the posts (528 boundary edges, by design and invisible).
- Texturing: one material, UV-mapped, with grain (U) running along each part (lathe: along the height; sweep: along the path; boxes: along the longest axis); 1 UV unit = 1 m = one texture tile.
  - Base colour: Poly Haven `black_walnut_veneer_02` diffuse, tinted to the photo's palette (target sRGB 0.34/0.25/0.225, grain contrast ×1.8) → `T_GothicArmchair_Wood_BaseColor` (8-bit sRGB).
  - Roughness and OpenGL normal (strength 1.0) from the same set. Metallic 0.
  - Reference palette sampled from the photo (sRGB, p10/p50/p90): seat 0.24/0.19/0.18 · 0.48/0.36/0.32 · 0.53/0.38/0.32; posts 0.23/0.18/0.19 · 0.33/0.24/0.22 · 0.39/0.32/0.31.
  - First candidate `dark_wood` was rejected because it is a plank texture and the photo shows a solid seat board.
- Review (fidelity_check.py, front view, elevation 20, azimuth −15, studio_small_09 HDRI):
  - Round 1: IoU 0.460. Gaps: top bands +10/+15% wide; texture saturation +0.08; quatrefoil too small; apron arches too shallow; narrow finial leaves. Fixed: quatrefoil enclosure r 0.122 → 0.135 with bigger lobes, Y-tracery added, apron arches deepened, leaves broadened, tint less saturated, end-cap UVs taken from the section axes.
  - Round 2: IoU 0.454. Saturation gap closed. Detail −0.017 on the seat/legs → grain contrast ×1.8, normal strength 0.8 → 1.0.
  - Final (`_final.glb`): IoU 0.454. Detail −0.015, warmth −0.03 (band 4), top bands +12/+16% wide.
  - Not fixed: the photo's perspective makes the back plane about 16% narrower than the front, and that perspective was not copied into the geometry. Highlights (0 vs 0.12) depend on the light and were not tuned.
- Optimize: gltf-transform resize 1024 → webp q90 → draco (individual steps, no simplify). 3.0 MB → 404 KB (−87%). Draco needs a decoder on the client.
- Export: GLB, export_apply=False, single mesh `SM_GothicArmchair` with 1 material (`M_Wood_DarkWalnut`) and 3 textures at 1024² (base colour, metallicRoughness, normal); 7,808 tris, 9,310 verts.
  - Triangles: +56% over the balanced top, under 2×. They go to round parts (16-sided lathes, 32-segment enclosure ring, quatrefoil lobes) and the tracery ribbons. Reported, not cut.

## Files
- gothic-armchair_original.glb — 3.0 MB, uncompressed
- gothic-armchair_final.glb — 404 KB, webp + draco
- gothic-armchair.blend — separate parts plus the joined export copy (hidden collection), textures packed
- review/ — reference crops, round1/round2/final overlays and side-by-sides, final joint renders, HDRI

## Licenses
- Poly Haven `black_walnut_veneer_02` texture set: CC0. Source: Poly Haven (polyhaven.com), via the public API.
- Poly Haven `studio_small_09` HDRI (review only, not shipped): CC0.
- Reference image: supplied by the user (used as reference only, not shipped).

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
