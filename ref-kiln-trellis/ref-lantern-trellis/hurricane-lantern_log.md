# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris)
- Style: realistic
- Mode: auto
- Storage: compact
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (protocol 13, up to date), Apple M4 Pro (Metal GPU bakes)

## Reference Image
- Path: bench/runs/_refs/Lantern_01.png (394×1023 RGBA, front view, ~12° elevation)
- Brief enrichment / inventory (ticked at the final review, against an enlarged crop):
  - top loop: closed pentagon wire inserted into the cap → **partial**: present, but its lower-left side was lost in decimation (it reads as an open hook)
  - bail: wide wire arch with a small peak, ends hooked into the tops of the air tubes → **present**
  - vent slots under the cap → **partial** (dark openings kept from TRELLIS, no crisp slots)
  - globe: smoky dark glass, frosted specks → **present** (separate material; frost is fainter than the reference's, the clear-coat highlight is stronger)
  - guard wires: X cross over the globe, front and back → **partial** (thin, broken in places)
  - air tubes / side frame, lever hooks → **present**
  - filler cap on the tank (front-right) → **absent**: not in the TRELLIS mesh, not invented
- Assumptions (auto mode, not asked):
  - real size: **0.30 m total height, bail raised** (usual hurricane lantern; the photo has no scale) → 0.126 × 0.099 × 0.300 m
  - camera elevation: 12°, read at the bell rim near mid-height; azimuth 0 (front)
  - no side/top views were provided: the back and underside are TRELLIS's guess
- Visual comparison: **partial match**. Shape close (silhouette IoU 0.80, which is what a real object scores against its own photo); colour close after correction; fine detail below the reference.

## Prompts (copy-paste ready)
- Concept art: none (user image)
- Generation: TRELLIS.2, run locally by the user from the reference image (params not recorded in the input)

## Source
- Method: AI (TRELLIS.2, local) — supplied raw mesh, kept as the shape
- Input: bench/runs/_refs/trellis/lantern_trellis.glb, copied unchanged to `hurricane-lantern_original.glb`

## Pipeline
- Import: 191,520 tris, 194,358 verts, 11.4 MB, 1024² baseColor + metallicRoughness. Y-up, 1.000 m tall.
  Scaled ×0.30 to 0.30 m, origin at the centre of the base, transforms applied, renamed SM_HurricaneLantern.
  Default Cube removed (untouched factory scene, rule 6 exception).
- Cleanup (high-poly):
  - merge by distance (0.02 mm): 109,963 seam-duplicate verts merged
  - loose verts and edges removed, degenerate dissolve (188,933 faces left), normals recalculated
  - fused edges (> 2 faces): **13,613 in the raw TRELLIS output itself** (measured with an exact merge), so they come from TRELLIS, not from cleanup. The raw mesh is made of open double sheets with fans of up to 13 faces on one edge.
- Glass split: the globe faces were picked geometrically from the radial profile (z 0.0745–0.1265 m, within the globe's measured radius, then majority-smoothed) → material M_Glass_Smoked. The guard wires stay metal.
- Decimation (pre-approved, original kept): 188,933 → **5,070 tris** (−97.3%). What was tried, in order:
  1. Blender Decimate (Collapse): stalled at 74K and faceted the shape → rejected
  2. gltfpack, normal mode: stalled at ~33K whatever the error limit (the topology locks it) → rejected
  3. Voxel remesh at 0.5 mm: the open, inconsistent shells broke inside/outside, and the tank, globe and tubes vanished → rejected
  4. Blender Decimate after splitting the fused edges: garbage → rejected
  5. gltfpack aggressive (-sa) on the whole mesh: body fine, but every thin wire gone even at 9.5K → rejected
  6. **Kept:** per-part simplification. Wires were picked out per vertex by the shape of a 3 mm neighbourhood (PCA, second axis < 0.95 mm), plus a location rule for the bail (above z 0.2135, and its thin legs). Each part was then simplified separately with gltfpack -sa: body 147,134 → 2,528 (×0.022), wires 12,865 → 1,390 (×0.11), glass 28,934 → 818 (×0.025).
  - Glass then rebuilt as a smooth lathe shell (64 segments × 13 rings = 1,664 tris) on TRELLIS's own measured globe profile (radius 30.1–34.6 mm, z 73.5–127.6 mm), per the glass recipe (≥ 64 segments). The faceted 818-tri globe was dropped.
  - Low-poly: the 1,086 fused edges inherited from TRELLIS were split (no edge has > 2 faces now, and the geometry is unchanged: this separates the sheets, it does not rebuild them). 443 faces were re-oriented outward by a visibility test. Open edges remain (open sheet metal, as in the source) — fine for a game prop, not watertight.
  - Final: 5,070 tris, 0 fused edges, 0 degenerate faces, 0 ngons. **+1.4% above the tier's 5,000 top (alert threshold +50%), reported, not blocked (rule 4).**
- UVs: Smart UV Project on the metal (60°, margin 0.006), cylindrical UV on the glass (u around, v up).
- Bake (Cycles GPU, selected-to-active from the high-poly, cage 3 mm, ray 10 mm, 2048²):
  - base colour by Emission into float, then converted to sRGB bytes (no black-colour export)
  - metallic/roughness by Emission (G = roughness, B = metallic), Non-Color
  - normal, tangent space. First bake had 50% inverted texels: TRELLIS's sheets face both ways. Fixed by orienting each high-poly face to its nearest low-poly face (88,130 flipped on the hidden bake copy only), then re-baking. **Compromise:** texels still pointing inward (6.8% of the atlas) were reset to a flat normal.
  - bake misses: 0.06% of the metal area (slivers)
- Texturing / materials:
  - M_Metal_AgedBronze (body + wires): baked TRELLIS colour, desaturated in two halfway steps (×0.85, ×0.85 chroma), plus a dark patina (#17130f-ish soot) driven by baked AO and the source's own dark blotches, painted as NON-metal (metallic × (1 − 0.6·grime), roughness + 0.18·grime). Metal share > 0.5: 76% of texels; metal base-colour luminance median 0.25 (above the 0.15 floor).
  - M_Glass_Smoked: Principled, metallic 0, roughness 0.1, coat 1.0 (coat roughness 0.05), IOR 1.5, alpha 0.80–0.9 from a 512² frost texture (sparse speckles gathered by a broad blotch field, neutral dark #13 grey from the reference's glass palette #161514 / #1f1e1d / #443f3d), BLEND.
- Review (tools/fidelity_check.py, front, ortho, elevation 12°, studio_small_09 HDRI, 32 samples). Two correction rounds:
  - r1: IoU 0.803. Large black patches on the metal (inverted normal map). Glass too clear. Band 2 saturation 0.466 vs reference 0.330.
  - r2 (normal fix, glass darker, chroma ×0.85): black patches gone. Saturation 0.44–0.49 vs 0.33–0.35, too golden.
  - r3 (chroma ×0.85 again, AO/blotch patina as non-metal, more frost): saturation gaps closed. Warmth within +0.03. Stopped here (two-round cap).
  - **final, measured on the shipped `_final.glb`:** IoU 0.803, the same as r3. Remaining gaps: band 4 highlights 0.052 vs 0.006 (the glass clear-coat reflection; light-dependent, not tuned); band 1 lum +0.09 (the bail, few pixels); texture detail 0.019–0.031 vs 0.029–0.040 (expected after −97% geometry); band 2 core width −13% (cap / top loop region).
- Optimize (auto preset, rule 20 steps, no geometry change): export 6.72 MB → resize 1024 (3.53 MB) → WebP (957 KB) → Draco (**598 KB**, −91%). **Draco needs a decoder on the client** (KHR_draco_mesh_compression, EXT_texture_webp required).
- Export: glTF 2.0 GLB, export_apply=False, Y-up, tangents exported (MikkTSpace). Material audit (rule 19): Principled + image textures only, all packed.
  gltf-transform validate: **0 errors, 0 warnings**. Infos only: Draco unvalidated, tangent unused on the glass primitive, 2 unused bufferViews.
  Re-imported in Blender: 5,070 tris, 0.126 × 0.099 × 0.300 m, screenshots from two opposite angles OK.

## Files (compact)
- hurricane-lantern_original.glb — the TRELLIS input, unchanged (11.4 MB)
- hurricane-lantern_final.glb — shipped asset (598 KB)
- hurricane-lantern.blend — the low-poly + the hidden high-poly (bake source, normals re-oriented) + the TRELLIS material (17.5 MB)
- hurricane-lantern_log.md — this file
- review/ — side_by_side.png + overlay.png for r1, r2, r3, final (kept as evidence, ~3 MB; not in the strict compact list)

## Licenses
- TRELLIS.2 (Microsoft): MIT. Caveat: its usual pipeline also pulls DINOv3 (Meta licence) and RMBG-2.0 (**CC BY-NC 4.0, non-commercial**). Check which background-removal step the local run used before any commercial use.
- Reference image Lantern_01 (Poly Haven): CC0
- HDRI studio_small_09 (Poly Haven): CC0, review only, not shipped
- gltfpack / meshoptimizer: MIT · glTF-Transform: MIT
- No paid service or credit used

## Checkpoint
- Last completed step: EXPORT (+ log)
- Timestamp: 2026-10-01 10:29
