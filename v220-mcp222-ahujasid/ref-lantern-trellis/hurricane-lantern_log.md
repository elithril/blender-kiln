# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Decimation: approved in advance by the user (original TRELLIS file kept untouched)

## Reference Image
- Path: /private/tmp/kiln-bench/v220-mcp222-ahujasid/ref-lantern-trellis/refs/Lantern_01.png
- Brief enrichment: Feuerhand-style hurricane lantern — wire bail with a small peak, its ends
  entering the tops of the two side frame tubes; pentagonal wire loop on the top cap (legs
  inserted into the cap); stepped chimney/bell; dark smoked frosted globe; guard wires crossing
  in an X front and back, with rings at the top and bottom of the globe and a horizontal bar out to
  each frame tube; side lift lever; ribbed fount; filler cap front-right.
- Assumptions (not given): real height **0.36 m with the bail raised** (usual size of a #276-type
  lantern); camera elevation ≈ 8° (read on the base rim ellipse), azimuth 0°.
- Visual comparison: **close match** on shape and parts. Silhouette IoU 0.79. The metal is a
  lighter, less contrasted bronze than the photo's under a studio light.

## Source
- Method: AI (user-supplied TRELLIS.2 local generation, kept as the shape)
- Raw file: refs/trellis/lantern_trellis.glb (191,520 tris, 1 m tall, one material, untouched)

## Pipeline
- Import: 191,520 faces, 0.42 × 0.34 × 1.0 m → scaled ×0.36 to 0.152 × 0.121 × 0.36 m, origin at base centre.
  The factory Cube was removed (untouched factory scene).
- Cleanup:
  - Merged 109,900 split vertices. The raw mesh had 13,739 fused and 10,216 open edges, and its
    faces were randomly wound across two layers ~1 mm apart.
  - Removed 210 floating fragments (debris inside the globe). The filler cap was kept.
  - Cut out the bail, the top loop and the glass band. They are rebuilt below.
  - Edge-collapse decimation stalled at 52K because of the fused edges. A plain voxel remesh lost
    the open shells. What worked: solidify 1.2 mm, then voxel remesh at 0.5 mm, giving a manifold
    shell. Then decimate to 80K, delete the 24K faces no outside ray reaches (the hidden inner
    wall), and decimate to 6K. Filled 316 pin-holes. Light Laplacian smoothing on the fount only.
    Result: 0 fused edges.
  - Thin parts rebuilt, never decimated:
    - Bail: 3.3 mm wire. Centreline measured from 40 slices of the high-poly; ends inserted into the tube tops.
    - Top loop: 2.4 mm wire, from 24 slices; legs inserted into the cap.
    - Guard: 1.8 mm wire, following the photo's pattern. Four helices (an X front and back), top and
      bottom rings, and two bars running into the frame tubes.
  - Glass: new lathe shell, 64 segments × 14 rings, from the high-poly's sector-median radius
    profile (r 3.1 → 4.17 → 3.3 cm, z 0.079–0.154 m). It sits inside both collars.
- Texturing (bake from the TRELLIS high-poly, 2048, Cycles, selected-to-active):
  - Base colour: emission bake of TRELLIS's colour, remapped to the photo's palette. Luminance
    quantiles go to the photo's dark/mid/light (lin. 0.067 / 0.135 / 0.277), with chroma toward the
    photo's bronze. Empty texels are push-pull filled. Exported as an sRGB byte image (no float black-out).
  - Roughness: TRELLIS roughness, remapped to 0.28–0.85 (+0.08 tarnish in round 2).
  - Normal: tangent-space bake. 55% of the texels came out inverted (TRELLIS winding), so they were
    flipped toward the low-poly normal and eased 40% toward flat.
  - Wires: share the metal material through a representative 18-px patch of the atlas, so the
    metal is one material and one draw call.
  - Glass: M_LanternGlass, dark smoked tint (lin. 0.022/0.025/0.030), sparse frost specks in colour
    and alpha (0.90–1.0), roughness 0.18, clear coat 1, alpha BLEND, backface culling.
- Review (fidelity_check.py, front, elevation 8°):
  - Round 0: dark-metal flag (0.09). Large black patches from the inverted normal bake. 15% UV coverage.
  - Round 1: re-unwrapped to 50% coverage, re-baked, normals fixed, empty texels filled. Black
    patches gone. Saturation now about half the photo's.
  - Round 2: chroma ×1.9 overshot (warm +0.14). Corrected halfway to ×1.4, with the tarnish
    darkened ×0.7 and +0.08 rough.
  - Final, on the shipped `_final.glb`: IoU 0.79. Remaining listed gaps:
    - base width +14% and lower frame +9% vs the photo. Kept: this is the TRELLIS shape, and a
      slightly high, close camera shrinks the base in the photo;
    - bail-band saturation −0.16 (thin wires);
    - warmth +0.05–0.07;
    - luminance and highlights are light-dependent alarms only.
- Materials: M_LanternMetal (base colour, metallic-roughness, normal; metallic 1.0) and M_LanternGlass.
  The export audit found no procedural nodes; every image is packed.
- Poly count: **9,895 tris** (body 6,000 incl. filler cap and lever; glass 1,664; guard 1,224;
  bail 620; top loop 428). That is ~2× the balanced top. The extra goes to round parts and wires,
  within the soft range.
- Optimize: gltf-transform resize 1024 → webp q90 → draco, as separate steps.
  8.56 MB → 463 KB (−95%). Draco needs a decoder on the client.
- Export: hurricane-lantern_final.glb, 463 KB, 9,895 tris, 2 meshes (SM_HurricaneLantern +
  child SM_HurricaneLantern_Glass), Y-up, metres.
- Known limits:
  - TRELLIS's crinkled surface and its invented paler wear on the back stay visible in close-ups.
  - The body keeps ~2.7K open edges where hidden interior faces were removed. Not watertight
    (the material is double-sided).

## Files (compact)
- hurricane-lantern_original.glb — pre-optimize export (2048 PNG textures)
- hurricane-lantern_final.glb — shipped
- hurricane-lantern.blend — full history (hidden HP_HurricaneLantern bake source, packed textures)
- hurricane-lantern_log.md

## Licenses
- TRELLIS.2 output supplied by the user (TRELLIS.2: MIT. Its background-removal and encoder
  models' licences depend on how it was run locally. Not verified here.)
- studio_small_09 HDRI, review only, not shipped: CC0. Source: Poly Haven (polyhaven.com), via the public API.
- No paid service used.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21 13:33
