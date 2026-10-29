# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (game asset)
- Tier: balanced (prop 1.5–5K tris, soft; up to 10K when spent on round parts / wires)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none run this session — the user supplied a local TRELLIS.2 generation as the starting mesh
- Decimation to the balanced budget: approved in advance by the user (original kept)
- Live view (Kiln Studio): off — auto run, nobody to watch; Studio offered at the hand-over
- Output: /private/tmp/kiln-bench/v300final-ahujasid/ref-lantern-trellis/work/generated-assets/hurricane-lantern/
- Environment: Blender 5.2.2 LTS (MCP addon protocol 14, up to date), Poly Haven library on, gltf-transform + gltfpack present.
  The open Blender held only the untouched factory scene (Cube, Camera, Light, no file): heavy steps run headless
  (`--factory-startup`, `read_factory_settings(use_empty=True)`), the live Blender is used to look.

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-ahujasid/ref-lantern-trellis/refs/Lantern_01.png (394×1023, RGBA, already cut out)
- Brief enrichment (inventory, from the photo):
  - bail: tall wire loop, pointed/arched top, legs hooked into the side tubes near their top → part of the mesh (thin part)
  - top cap: domed chimney cap with a flat disc top and a small pentagonal wire ring handle → mesh (thin part: ring)
  - chimney / upper bell: flared metal bell over the globe → mesh
  - side tubes: two vertical air tubes (round section) left/right, bent outward at the top, into the tank at the bottom → mesh
  - globe: dark smoked glass, egg-shaped, frosted specks, between bell and tank → mesh, its own material (glass)
  - globe guard: thin crossed wires over the globe → mesh (thin part)
  - lift lever: wire lever on the right side, bottom of the globe → mesh (thin part)
  - tank / fount: wide cylindrical base with rolled rings, filler cap on the front-right → mesh
  - burner/wick knob: small disc on the front at the globe's foot → mesh
  - materials: ONE worn dark bronze/brass metal (bare highlights on edges, darker patina in cavities) + dark smoked glass
- Unseen: the back. TRELLIS invented it; kept as generated, plain.
- Real size (assumption, auto mode): 0.38 m tall bail raised (a Feuerhand-276-class hurricane lantern; body ≈ 0.27 m).
- Camera elevation: slightly above (rims read as shallow ellipses); measured in the review step.
- Visual comparison: pending

## Prompts (copy-paste ready)
- Concept art: none (source: user image)
- Generation params: backend=TRELLIS.2 local, made by the user before the session (settings not recorded)

## Source
- Method: AI (TRELLIS.2, local, user-supplied) — repaired and finished, shape kept as the brief asks
- File: refs/trellis/lantern_trellis.glb (11.4 MB, 191,520 tris, 194,358 verts, baseColor + metallicRoughness PNGs)

## Pipeline
- Import: 191,520 tris / 194,358 verts, raw box 0.42×0.335×1.00 (Y-up glTF → Z-up), one material (TRELLIS baseColor + metallicRoughness 1024 PNG), 5 islands, 154,118 open edges (split at UV seams); welded at 1e-6 → 10,220 open + 13,732 fused edges (TRELLIS self-touching surface). Scaled uniformly to 0.38 m tall (assumption) → 159.9 × 127.3 × 380.0 mm. Renamed SM_HurricaneLantern / SM_HurricaneLantern_Mesh. Live Blender: factory Cube removed (untouched factory scene, rule 6 exception).
- Cleanup (shape kept, surface rebuilt — fused edges cannot ship):
  - tried: voxel remesh 0.5 mm alone → closed but porous (χ −14,068, genus ≈ 7,000: TRELLIS's thin walls perforate); Collapse stalled at 136K tris and threw spikes (height 578 mm). Undone.
  - kept: weld 1e-6 → Solidify 1.0 mm (offset 0, walls ±0.5 mm; wires ≈ +1 mm thicker) → voxel remesh 0.6 mm (1.06M faces, χ −88, closed) → dropped 6 fragments < 150 verts and 1 shell inside the body, kept 1 outside part → Collapse in ×0.25 steps → **9,000 tris, 4,412 verts, 0 open, 0 fused, 0 loose**. Recalc normals, smooth shading, 1,801 edges sharp (> 70°).
  - Budget: 9,000 tris vs balanced prop 1.5–5K → 1.8× the top, inside the 2× allowance; spent on the bail, ring, guard wires, lever and side tubes (thin parts — Collapse at 5K would crumple them, per the measured precedent). Decimation pre-approved by the user; original kept (refs/ untouched, `_original.glb` at export).
  - Origin at the centre of the base, base on the ground (shift −0.38 mm z). Final size 159.8 × 127.7 × 380.6 mm (W × D × H).
  - Looked (live Blender, solid + wireframe, front / back / 3⁄4 / under): bail, ring, guard wires, lever continuous; surface keeps TRELLIS's lumps (base rim wobbles).
  - Revised in TEXTURING: the remesh is a hollow shell (its cavity open to the outside), 42 % of faces were interior walls (black AO, wasted UVs). Cleanup now decimates to 40K, deletes 16,701 faces no ray from outside reaches (160 directions), then Collapses to **9,000 visible tris, 5,278 verts, 0 fused, 1,934 open edges** (cut where the interior was removed — inside openings, not visible from outside: checked with backface culling; materials are double-sided). Size 159.9 × 128.2 × 380.9 mm.
- Texturing:
  - UVs: Smart UV Project 66°, margin 0.003, concave repack → uv_check ok: used 32.7 %, overlap 0 %, stretch 0 %, collapsed 0 %, flipped 0 %. (Tried merging tiny islands + conformal unwrap: FAIL, overlap 23–74 %, collapsed 29–31 % — undone.)
  - Zones: 2 materials — M_Metal_AgedBronze (8,393 faces), M_Glass_Smoked (607 faces: inner envelope of the globe between z 100–162 mm, label cleaned of islands < 40 / < 25 faces).
  - TRELLIS texture: all bronze, glass painted as metal, metallic ≈ 1 everywhere → its colour is kept only as relative variation; palette from the photo (photo_palette.json): metal dark/mid/light sRGB (0.20,0.155,0.12)/(0.31,0.245,0.19)/(0.52,0.42,0.30), kept above the 0.15 metal floor (median 0.265); non-metal crust (0.085,0.066,0.05) in cavities (AO p75–p97, 5.7 %); bare edge wear from pointiness p90–p99.5 × scan patches; roughness scan + TRELLIS ± edges / crust (median 0.40).
  - Scan: Poly Haven rusty_metal_04 (CC0, Amal Kumar), chosen against the tank crop over metal_plate_02 (panel seams), rusty_metal_sheet, blue_metal_plate; used for luminance detail, roughness, metal patches and height (bump), box-projected at 2.5/m, baked.
  - Glass: smoked tint sRGB (0.10,0.10,0.108) alpha 0.80, frost specks 2.8 % (noise 900 gathered by blotches 40) lighter / alpha 0.95 / rougher; metallic 0, alphaMode BLEND.
  - Normal: tried the TRELLIS normals (flipped on some parts → wrong tilt), then the 0.6 mm remesh (TRELLIS's shell gaps became slots → cracks), then a 1.6 mm-solidify / 1 mm remesh (still creases the photo does not have). Kept: scan relief only on the metal, high-poly (gap-closed, smoothed) normal on the glass.
  - Maps (1024, PNG, packed): hurricane-lantern_basecolor (sRGB, alpha = glass), _metalrough (G rough, B metal), _normal (tangent, OpenGL). Material audit OK: Principled + images only.
- Rounds (reference image; front, ortho, elevation 8° read on the cap and base ellipses ≈ 0.13 minor/major, azimuth 0, HDRI studio_small_09):
  - v1: silhouette 0.787, face iou 0.63, f 0.90 (offset 0 / −2.4 mm). Base +14 % (perspective, expected — not narrowed). Material: model warmer (R−B 0.09–0.13 vs 0.03–0.06), brighter and more highlights (light-dependent). Next: metal chroma −45 % (one change).
  - v2 (chroma 0.55): silhouette 0.787, face iou 0.67. Warmth now 0.02–0.07 vs 0.03–0.06 (closed), but saturation 0.18–0.25 vs 0.26–0.52 (overshot; saturation holds across lights). Highlights still 3–8× the photo's (light-dependent, not tuned). Next: chroma half-way back, 0.78.
  - v3 (chroma 0.78, final): silhouette 0.787, face iou 0.63, f ≈ 0.90. Per band (photo/model) sat 0.33/0.32, 0.35/0.33, 0.26/0.23, 0.33/0.31; warm 0.059/0.073, 0.061/0.068, 0.034/0.030, 0.053/0.078 — closed within the noise. Band 1 (bail, mostly background) sat 0.52/0.34: thin wire, not trusted. Lum 1.2–1.6× and highlights 2–8× the photo's: light-dependent (photo's dark studio unknown), not tuned. Kept. Round cap reached (2 corrections).
- Inventory at the final review (crop vs crop):
  - bail, pointed top, legs into the tubes — present, right
  - top cap + pentagonal ring — present, right
  - bell / chimney — present; TRELLIS's bell is less flared and lumpier than the photo's (shape kept as asked)
  - side tubes — present, right
  - smoked frosted globe — present; tint right, frost specks coarser than the photo's
  - crossed guard wires — present, right
  - lift lever (left) — present, right
  - tank with rolled rings — present; rings soft (TRELLIS)
  - filler cap — partial: TRELLIS made it a low bump at the front instead of the photo's front-right cap (shape kept as asked)
  - one metal + one glass — right
- Visual comparison: close match on silhouette, palette and materials; partial on the bell flare, tank rings and filler cap, which come from the TRELLIS shape the brief keeps.
- Optimize: gltf-transform resize 1024 → webp q90 → draco (separate steps, no `optimize`); 3.55 MB → 0.47 MB (−87 %). Geometry untouched by this phase.
- Export: glTF. web/hurricane-lantern_final.glb 0.47 MB, 9,000 tris, Draco + WebP (needs a Draco decoder); hurricane-lantern_original.glb 3.55 MB and hurricane-lantern_preview.glb (a copy: no extensions, opens in Quick Look and in engines without Draco). Materials: M_Metal_AgedBronze (OPAQUE), M_Glass_Smoked (BLEND), double-sided, 3 shared 1024 maps. Material audit OK before export; export_apply False.
  - Last measure, on the shipped _final.glb: silhouette 0.787, face iou 0.634, f 0.900 — identical to v3 (the export changed nothing). uv_check ok (32.6 % used, 0 overlap / stretch / collapsed / flipped). Re-imported in the live Blender: on the ground, 0.16 × 0.13 × 0.38 m, 0 non-manifold. Review renders (matcap + colour, q1 / q3 / top / under) in review/renders/.
  - Kiln Studio checks: no WARN; notes: 9,000 tris (1.8× the tier's top, spent on wires and tubes), licences listed.
- Working files kept (auto mode, nobody to answer — proposed for deletion in the hand-over): hurricane-lantern_import.blend, _clean.blend, _bake.blend, scratch_remesh05.blend, scratch_clean_6000.blend, scratch_clean_9000.blend, scratch_uvtest.glb, scratch_opt/, review/scratch_review.glb, textures/bake/*.exr, textures/*.png, textures/polyhaven/, textures/thumbs/.
- rusty_metal_04 texture set: CC0 — Source: Poly Haven (polyhaven.com), via the public API (author Amal Kumar)
- studio_small_09 HDRI (review renders only, not shipped): CC0 — Poly Haven
- Reference image Lantern_01.png: user-supplied
- TRELLIS.2 output: user-generated (TRELLIS.2 code/weights MIT, Microsoft)

## Checkpoint
- Last completed step: [7] EXPORT (web/hurricane-lantern_final.glb, _original.glb, _preview.glb, hurricane-lantern.blend)
- Timestamp: 2026-10-23
