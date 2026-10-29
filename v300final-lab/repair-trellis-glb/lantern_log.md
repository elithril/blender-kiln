# Lantern — Production Log

## Config
- Type: prop
- Target: glTF (web, game-ready)
- Tier: balanced (prop 1.5-5K tris; 2× top = 10K)
- Style: realistic
- Mode: auto
- Storage: compact
- Backend: none (repair of an existing generated GLB — no marketplace, no new AI generation)
- Live view: Kiln Studio http://127.0.0.1:4859/ (no auto-open)
- Environment: Blender 5.2.2 LTS (official Blender Lab MCP, interactive), gltf-transform + gltfpack on PATH

## Reference Image
- Path: none — the input GLB is the reference (keep its shape and look)
- Brief enrichment: none
- Visual comparison: N/A (compared against the source GLB instead)

## Prompts (copy-paste ready)
- None — no generation in this session. Source GLB was produced earlier by TRELLIS (trimesh exporter).

## Source
- Method: AI (pre-existing TRELLIS output, user-supplied)
- File: /private/tmp/kiln-bench/v300final-lab/repair-trellis-glb/refs/trellis/lantern_trellis.glb (11.4 MB, left untouched)
- Source stats: 191,520 tris, 194,358 verts, 1 material (baseColor + metallicRoughness PNG 1024²), bbox 0.42 × 1.00 × 0.33 m (glTF Y-up), no animation
- Brief: "make it game-ready for the web; keep its shape and its look; decimation to the balanced budget approved in advance (keep the original file)."
- Assumptions (auto mode): TRELLIS normalizes to a 1 m box, so the 1.00 m height is a generator artefact, not a real size — decided at IMPORT after looking at the model.

## Pipeline
- [1] CONFIG + [2] BRIEF: done. Factory scene in Blender (Cube/Camera/Light, no .blend) — Cube removed before import (rule 6 exception).
- [3] SOURCE: user's TRELLIS GLB, nothing searched or generated.

- [4] IMPORT: geometry_0 → SM_Lantern (later SM_Lantern_High, kept hidden in the .blend). 191,520 faces, 1 material, bbox 0.42 × 0.33 × 1.00 m. Hurricane (kerosene) lantern: base fount, two side tubes, glass globe with guard wires, hood, chimney cap with a small top ring, wire bail.
  - Scale: TRELLIS normalizes to a 1 m box → ASSUMPTION (auto mode): real height 0.38 m with the bail up (a standard hurricane lantern), uniform ×0.38 → 0.160 × 0.127 × 0.380 m. Origin at the centre of the base, bottom at z = 0.
  - Look: review/source_{colour,matcap}_{q1,q3,top,under}.png (review_renders.py; the live Blender viewport was blocked by its splash screen).
- [5] CLEANUP: source health (welded at 1e-6 m): 84,467 verts, 189,146 faces, 13,732 fused edges (>2 faces), 10,220 open edges, 4,119 edges with opposite winding, 2 debris islands (5 and 4 verts). 59 % of sampled vertices have another surface within 2 mm: the whole lantern is a thin double-walled sheet (≈1–1.5 mm walls), not a solid.
  - Direct voxel remesh (0.6 mm) of the source: closed but perforated (genus ≈ 4,777, 765 islands) → rejected.
  - Kept recipe: weld 1e-6 → Solidify 0.8 mm, offset 0 (centred, so the bad winding does not matter) → voxel remesh 0.4 mm → 2,430,616 quads, 0 open / 0 fused, genus 198, 38 islands → removed 36 islands that were inside the main shell or under 100 verts (4,756 verts).
  - Decimate (approved in the brief), Collapse, triangulate: tried 6,000 and 9,000 tris — both 0 open / 0 fused. 6K showed pin-holes on the base and coarser wires; 9K kept bail, top ring and guard wires intact → kept 9,000 tris / 4,110 verts (balanced prop tier 1.5–5K; 9K is under 2× the top, extra triangles spent on the wires and round parts). Open edges 10,220 → 0, fused 13,732 → 0 (fewer than before, not more).
  - Low-poly deviation from the remesh: median 0.15 mm, p99 0.61 mm, max 1.52 mm. The voxel pass adds ≈0.4 mm per side to sheet and wire thickness (Solidify 0.8 mm centred).
  - Recalc normals: 0 faces flipped (closed shell, consistent). Loose 0, degenerate 0. Transforms applied (loc 0, scale 1). Shade smooth by angle 40°. Material single-sided (closed shell).
  - Removed: factory Cube; temporary TMP_Remesh / TMP_Low6000 (re-creatable with the recipe above, not kept: 2.4M faces).
- [5b] TEXTURING (look kept by baking from the source, nothing new painted): Smart UV Project 66°, packed CONCAVE with margin 0.0015 → 1,454 islands, 46.6 % of the tile used (first pack had 24.6 %: repacked and re-baked). Texel density 1.75 texels/mm² vs 2.37 on the source atlas (74 %) at 1024.
  - Cycles, selected-to-active, cage extrusion 3 mm, max ray 6 mm, 16 samples, margin 4 px:
    - T_Lantern_BaseColor (1024, sRGB) ← source baseColor via emission;
    - T_Lantern_MetallicRoughness (1024, linear) ← source metallicRoughness via emission (G roughness mean 0.43, B metal mean 0.997 — as the source);
    - T_Lantern_Normal (1024, tangent) ← NOT from the source (its flipped faces gave 25 % of texels tilted past 90°) but from the clean 0.4 mm remesh, rebuilt for the bake and removed after.
  - uv_check on lantern_original.glb: used 46.6 %, overlap 0.2 %, stretch 0 %, collapsed 0 %, flipped 0 % → 0 FAIL, 0 WARN.
  - Look: EEVEE comparison (review/eevee_compare.py — Workbench ignores normal maps) review/ev2*_{tmp_source,lantern_original}.png, two opposite sides: close match. Without the normal map the low-poly read flat (review/ev_tmp_low_nonormal.png) → normal map kept. Known difference: a few silver wear flecks on the thin wires (bail, globe guards) where the source is plain copper (bleed at small UV islands).
  - Workbench views: review/cleanup_{colour,matcap}_{q1,q3,top,under}.png.
- [6] OPTIMIZE (auto, no geometry change): lantern_original.glb (re-exported with tangents for the baked normal map, MikkTSpace) 4.31 MB → resize 1024 (no-op, already 1024) → WebP q90 → Draco (gltf-transform, separate steps, never `optimize`) → web/lantern_final.glb 0.93 MB (−79 %; −92 % against the 11.43 MB TRELLIS file). Draco needs a decoder on the client (three.js DRACOLoader). lantern_preview.glb = copy of _original (no Draco, no WebP: opens in macOS Quick Look); its extensionsUsed: none.
- [7] EXPORT: glTF 2.0, export_apply False, selection SM_Lantern only (SM_Lantern_High stays in the .blend). Material audit: M_Lantern — Principled BSDF + 3 image textures, no procedural node → 0 warnings. gltf-transform validate on _final: 0 errors, 0 warnings. web/lantern_final.glb: 925 KB, 9,000 tris, 12,595 verts, 1 material, 3 × 1024 WebP (base colour, metallic-roughness, normal), single-sided. EEVEE render of the shipped file: review/final*_lantern_final.png — decodes and matches the source.
  - Studio checks: no WARN. Note: 9,000 tris is 80 % above the balanced prop range (1.5–5K), under 2× its top; spent on the bail, top ring, guard wires and round body.
  - .blend saved (lantern.blend: SM_Lantern + hidden SM_Lantern_High, baked images packed). No .blend1.
  - Intermediates kept (compact mode, auto run — nobody to confirm a deletion): review/ (89 MB: renders, tmp_*.glb incl. tmp_source.glb = a copy of the source, eevee_compare.py), textures/ (3.8 MB: PNGs of the FIRST bake, on the 24.6 % UV pack — stale, not the shipped maps; the shipped maps are packed in lantern.blend and inside the GLBs).

## Licenses
- lantern_trellis.glb: user-supplied, generated with TRELLIS (MIT-licensed model); output owned by the user.

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22
