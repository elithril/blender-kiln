# Hurricane Lantern — Production Log

## Config
- Type: prop
- Target: glTF (GLB), game asset
- Tier: balanced (props 1.5–5K tris soft range; up to 2× when spent where it shows)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling in Blender (brief: no marketplace, no AI generation)
- Environment: macOS arm64 (Apple M4 Pro), Blender 5.2.2 LTS (/Applications/Blender.app), Blender Lab MCP connected
  (factory scene: Cube, Camera, Light, no file), gltf-transform + gltfpack present
- Live view: Kiln Studio http://127.0.0.1:4855/ (project root = work/)
- Output: /private/tmp/kiln-bench/v300final-lab/ref-lantern-template/work/generated-assets/lantern/

## Reference Image
- Path: /private/tmp/kiln-bench/v300final-lab/ref-lantern-template/refs/Lantern_01.png (394×1023, alpha cut-out already present)
- Template: refs/trellis/lantern_trellis.glb (TRELLIS.2) — proportions only, measured with
  tools/template_profile.py → review/template_profile.json. Mesh and texture NOT shipped.
- Assumptions (auto mode, nobody to ask):
  - Real size: 0.36 m total height with the bail raised (body to cap top ≈ 0.26 m, the usual
    size of a 276-type hurricane lantern). Assumption, not a measure.
  - Camera elevation ≈ 15° (estimate from the cap lid and globe-cup ellipses, minor/major ≈ 0.2–0.25),
    azimuth 0 (front-on; the side tubes appear symmetric left/right).
  - Unseen: the back. Kept plain and mirrored from the front (tubes, bail, guard are symmetric);
    fill cap and wick knob exist only where the photo shows them (front-right).
- Brief enrichment (inventory, from 3× crops — review/crops/):
  - bail: one thin wire, pointed (pinched) peak, legs hooked INTO small eyes on the outer side of each tube at ~20 cm → SM_Lantern_Bail
  - top ring handle: pentagon-shaped wire loop, its base pinned by a small hinge strap on the lid → SM_Lantern_TopHandle (inserted into the lid strap)
  - lid: wide flat disc with rolled rim + raised central dome + smaller top step → SM_Lantern_Cap
  - chimney: short cylinder under the lid with a ring of slot vents (dark) → SM_Lantern_Cap (same part, vents as geometry slots)
  - air chamber: cylinder with a bead ring, flaring to a bell (skirt) at ~18 cm → SM_Lantern_Chamber
  - side tubes: two thick air tubes (≈1.5 cm), vertical at r≈5.8 cm, elbowing INTO the chamber at the top and INTO the fount shoulder at the bottom → SM_Lantern_Tubes
  - globe collar: short cylinder + rim above the glass, below the bell → SM_Lantern_GlobeCollar (resting on the glass top)
  - globe: barrel/egg-shaped dark smoked glass, frosted specks, ≈8.4 cm across → SM_Lantern_Globe (own material)
  - guard wires: two wires crossing in an X over the front of the globe + top ring; bottom cup ring holding the globe → SM_Lantern_Guard (ends welded into the rings)
  - globe-lift levers: small bent wire on the left tube (≈11–12 cm) and on the right (≈9–10 cm) → SM_Lantern_Guard
  - burner: cup under the globe, narrow neck down to the fount → SM_Lantern_Burner
  - wick shaft + knob: thin rod out to the right ending in a small disc knob on edge → SM_Lantern_Burner
  - fount: domed shoulder, vertical wall with 2–3 rolled ridges, slight flare at the foot → SM_Lantern_Fount
  - fill cap: short cylinder with flat top, front-right on the shoulder, oil stain running down below it → SM_Lantern_FillCap (inserted into shoulder)
- Materials seen: ONE metal — aged dark bronze / oil-rubbed brass (dark brown-black with warm
  brassy highlights worn on edges and ridges, dark streaky patina); ONE glass — dark smoked
  blue-grey, frosted with white specks.
- Visual comparison: close match in shape and parts; materials partial — same dark bronze hue and worn
  edges, but the surface reads smoother than the photo (grain about half), and the glass more transparent

## Prompts (copy-paste ready)
- Concept art: none (user image)
- Generation params: none (scripted)

## Source
- Method: scripted (Blender Python, headless build script scripts/build_lantern.py)

## Pipeline
- Source/Import (scripted, v1): scripts/build_lantern.py, headless Blender 5.2.2 → lantern.blend.
  10 parts: SM_Lantern_Fount, _Burner (cup, neck, wick shaft + knob, burner dome), _FillCap, _Globe,
  _Hood (globe collar + bell + air chamber + chimney with 6 vent slots — inventory's Chamber and
  GlobeCollar built as one turned part), _Cap, _TopHandle, _Tubes (+ bail lugs), _Bail, _Guard.
  10,980 tris (2.2× the balanced prop tier's top of 5K — spent on round sections: glass 64 segments,
  turned metal 32, tubes 12 sides, wires 6). Reported, not reduced (rule 4).
  Measures used: template heights/radii (fount r 5.87→5.35 cm, globe max r 4.2 cm at 11 cm, bell r 4.2 cm
  at 18.4 cm, chamber r 3.2 cm, tubes 4.6–7.5 cm from the axis, bail 6.0–6.6 cm at 20 cm); photo pixels for
  the lid (template's lid r 2.5 cm reads thin-rim loss; photo r 3.5 cm used), the bail centre line (traced
  half-widths per row), the tube width (1.6 cm), the top handle pentagon.
  First trial: fillet arcs used Vector.slerp (unit length) → 1 m arcs, 52K tris; fixed before any look.
  Look: review/v1/ (matcap front, q1, q3, top) + MCP viewport capture (framed, material preview).

- Round v1 measure (review/front/, .blend, elev 15°, az 0): silhouette IoU 0.810, face IoU 0.67 (f 0.94,
  offset +2.3/-1.1 mm). Gaps: side tubes 2–3 mm too far out and their bottom elbows too high (photo: diagonal
  into the shoulder near the neck); lid and chamber wide (band 2 core +22 %); vent band too tall (face detail
  at 24 % = 243 % of the photo's area); metal too bright/warm (lum +0.17–0.25, warm +0.10–0.14 — light-
  dependent, an alarm) and the oil stain a hard black block; 10,980 tris > 2× tier.
  Joints (review/front/joints/, 10): shaft into neck and rods into tubes enter with section unchanged; the
  guard wires render alone (their rings are in the same object) — checked by BVH below instead.
- Round v2 changes (shape): tubes moved in (B 0.064→0.0615, T 0.051→0.0495), top arm 3 mm lower, bottom
  elbow goes diagonally into the shoulder at r 3 cm; chamber r 3.25→3.12 cm, bell rim 4.28→4.15 cm, lid −4 % and
  2 mm lower, vent slots 6.6→3.7 mm tall; profile trims → 9,960 tris. Materials: darker browner patina, softer
  narrower oil run (measured at v2 after the bake).
- Cleanup (scripts/cleanup.py): transforms applied, weld 1e-4 m keeping corner normals — 0 vertices merged
  (built welded), 0 loose, 0 degenerate, 0 fused edges. Open edges only where hidden or by design (globe's open
  ends 128; part ends buried in other parts: burner 80, hood 64, cap 32, fill cap 20). Attachment: 31 pieces,
  0 floating (BVH surface distance ≤ 0.5 mm, or surfaces crossing — shaft through neck, bail through lugs into
  tubes, rods into tubes). Size on world vertices: 0.1375 × 0.118 × 0.3598 m, base at z 0, origin centre of
  base. 9,960 tris (≈2× the balanced prop tier's 5K top, inside the soft 2× allowance; not reduced).
  Look: review/v2/sheet.png (front, q1, q3, under).

- Texturing: no Poly Haven set fits (API metal list: rusted/painted steel only, no brass/bronze; the photo
  shows no rust) → procedural, per reference-fidelity § 4 "no set fits a material". ONE metal
  (M_Lantern_Metal: patina stays metal, sRGB 0.27–0.38 base from the photo's hue; bare brass on convex edges by
  per-part curvature percentiles 80–99, broken in patches; non-metal soot crust in creases + AO; dark glossy oil
  run under the fill cap; independent roughness field; fine pits as bump → normal map) and ONE glass
  (M_Lantern_Glass: dark blue-grey smoke, alpha 0.8, frost specks gathered in blotches, coat 1). Palette sampled
  (sRGB 10/50/90 %): fount 0.09/0.15/0.29, chamber 0.07/0.15/0.30, glass 0.07/0.11/0.23 (neutral).
  UVs: lathe = u around × v along profile, sweeps = u around × v along length, packed per material, no
  rotation; uv_check 0 FAIL, 1 WARN (Cap stretch 10.2 % at the lid's pole, under the handle).
  Baked (Cycles GPU, 16 samples): Emission → float → sRGB bytes (BaseColor), roughness G + metallic B
  (MetalRough), tangent NORMAL; glass colour + alpha → RGBA. Final atlases 1024. Procedural materials kept in
  the .blend as M_Lantern_*_Procedural (fake user). Export audit: no procedural node on shipped materials.
- Round v2 measure (review/v2/lantern_v2.glb, 512 bake): silhouette IoU 0.845 (from 0.810), band 2 core +22 %
  → +10 %, face IoU 0.60, f 0.86; metals: base median 0.257 (floor 0.15), mask largest island 88 % (one region).
  Largest remaining: metal too smooth/clean — grain 0.08–0.13 vs photo 0.21–0.36, solid bright rings.
- Round v3 (one material change): mottling at 120/m, fine colour pits/scratches at 450/m, fine roughness
  field, wear broken in patches. Measure: IoU 0.845, face 0.63 (f 0.88), band warmth now within 0.01–0.04 of the
  photo (was +0.07–0.14), lum +0.04–0.09 (light-dependent, alarm only); grain still under the photo (0.08–0.13).
  Stopped there: the two-round cap (reference-fidelity § 5).
- Final bake 1024 → lantern_original.glb (4.07 MB). Look: review/final/sheet.png (colour q1, q3, top, under —
  no UV seams; a small dark mark at the underside pole) + MCP material preview at azimuth −35° and 145°.

- Optimize (gltf-transform, separate steps, rule 20): resize 1024 → WebP q90 → Draco.
  lantern_original.glb 4.07 MB → web/lantern_final.glb 405 KB (−90 %). lantern_preview.glb = copy of the original
  (extensionsUsed: KHR_materials_clearcoat only — no Draco, no WebP; opens in Quick Look). Geometry untouched.
- Export: glTF/GLB, 9,960 tris, 10 meshes, 2 materials (M_Lantern_Metal: baseColor + metallicRoughness + normal;
  M_Lantern_Glass: baseColor RGBA, alphaMode BLEND, clearcoat), export_apply off, no custom attributes.
  lantern.blend saved (baked materials in use, procedural ones kept with fake user, images packed, no .blend1).
- Final measure on web/lantern_final.glb (review/front/, 64 samples): silhouette IoU 0.845, face IoU 0.64 (f 0.89,
  offset +1.1/−2.2 mm); metal base median 0.257 (above the 0.15 floor), metallic mask one region (88 %).
  Open gaps, logged not chased (two-round cap): vent band still reads larger than the photo's slots; grain under
  the photo's; glass lighter/more transparent than the photo's smoke; band 2 core +10 %.
  Joints: 23 rendered (review/front/joints/, joints_sheet.png) — all looked at: ends enter their parts, section
  unchanged; no flat cut, no flared foot.
- Inventory tick (enlarged crops vs final render):
  - bail, pinched peak, ends through lugs into the tubes: present ✓ (lugs added: the photo's eye is too small to read)
  - pentagon top handle through hinge strap on lid: present ✓
  - lid with rolled rim, dome, top step: present ✓
  - chimney with vent slots: present ✓ (6 slots; read larger than the photo's)
  - air chamber + bead + bell skirt: present ✓
  - side tubes into chamber and fount shoulder: present ✓ (bottom elbow now diagonal into the shoulder)
  - globe collar resting on the glass: present ✓
  - smoked frosted globe: present ✓ (lighter than the photo)
  - crossed guard wires + top ring + cup: present ✓
  - left clip and right lift lever, lift rods: present ✓ (simplified bends)
  - burner cup, neck, wick shaft + disc knob front-right: present ✓
  - fount with domed shoulder, rolled ridges, foot: present ✓ (3 ridges, the photo shows 2–3)
  - fill cap front-right with oil run below: present ✓
  - unseen: the back — plain, symmetric with the front (no part invented there).
- Working files kept (auto mode, nobody to answer — listed for the end-of-session cleanup): scripts/ (build,
  cleanup, bake/export, measures), review/ (crops, template profile, TRELLIS renders, v1–v3 renders, review GLBs
  v2/v3, opt/ intermediates resized.glb + webp.glb, HDRI, fidelity outputs).

## Licenses
- Reference image and TRELLIS template: user-provided, used for measurement only, not shipped.
- studio_small_09 HDRI (review lighting only, not shipped): CC0, Poly Haven (polyhaven.com), via the public API.
- Textures: procedural, made in this session — no third-party texture shipped.

## Checkpoint
- Last completed step: [7] EXPORT (web/lantern_final.glb, preview, .blend, log) — done
- Timestamp: 2026-10-22 18:30
