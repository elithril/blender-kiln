# Ammo Box — Production Log

## Config
- Type: prop · Target: glTF (GLB) · Tier: balanced (1.5–5K tris) · Style: realistic · Mode: auto · Storage: compact
- Blender 5.2.2 LTS, blender-mcp addon 1.8 (up to date). Factory Cube removed before building (untouched factory scene).

## Reference Image
- Path: /private/tmp/kiln-bench/ref-kiln-v14gen/ref-ammo-box/refs/ammo_box.png (1024×1015, alpha)
- Camera read from the top-face corners: elevation ≈ 15°, azimuth ≈ 54° toward +X (3/4 view, close perspective)
- Real size: ASSUMED, not given — US M19A1-class 7.62 mm can. Measured ratios L:W:H ≈ 1 : 0.40 : 0.65 → 0.286 × 0.119 × 0.183 m (lid included)
- Single view: the back (+Y), the −X end and the underside are not shown in the photo. What they have is assumed (see inventory)

### Inventory (from 2× crops) — ticked at final review
- [x] Body: steel can, rounded vertical corners → SM_AmmoBox_Body
- [x] Lid: overhanging cap, rolled top edge, stamped inset panel, ~18 mm skirt → SM_AmmoBox_Lid (resting over Body)
- [x] Handle: flat strap, raised on its −X link (as in the photo) → SM_AmmoBox_Handle
- [x] Handle brackets: base plate + folded bridge, ×2, on the lid → SM_AmmoBox_HandleBrackets (inserted into lid)
- [x] Handle links: rectangular wire loops, strap end → under the bracket bridge → SM_AmmoBox_HandleLink_L/_R
- [x] +X end lid-hook strip with 5 rivet domes on a bent lip → SM_AmmoBox_LatchStrip
- [x] Latch plate: rounded rectangle, round window, top hook over the strip → SM_AmmoBox_LatchPlate
- [x] Boss seen through the window → SM_AmmoBox_LatchBoss
- [x] Lower hinge: mount plate, plate knuckle, two tabs with rolled ends → SM_AmmoBox_LatchHinge
- [x] Wire bail: U-loop, legs inserted through the tab knuckles → SM_AmmoBox_LatchBail
- [x] Lid hook wire, lid skirt → strip (front one seen; back one MIRRORED, assumed) → SM_AmmoBox_LidHook_F/_B
- [x] Yellow stencil "200 CARTRIGES / 7.62 MM, M108 / CARTONS • M31" on the front face (spelling copied from the photo; the worn "M 08" is read as M108) → baked into BaseColor
- [~] −X end lid-hinge barrel → SM_AmmoBox_LidHinge — INVENTED (not in the photo)
- Attachment: BVH check, every part touches or enters a neighbour (overlap test on the embedded ones). 24 joint renders inspected (review/final/joints): bail legs through the knuckles, hooks enter the lid and strip, links pass under the bridges

## Prompts
- Concept art: none (user image). Hunyuan3D: not used.

## Source
- Method: scripted modelling (bmesh + curves) — scripts/build.py. No marketplace, no AI generation.

## Pipeline
- Geometry: 14 parts under the SM_AmmoBox root empty, 3,448 tris (within balanced 1.5–5K). Most of them go to the round wires (12 sides) and the latch window (48 segments).
- Cleanup: merge by distance 0 verts, fused edges 0, open edges 0 on every part; normals recalculated; transforms identity; origin = base centre; 1 unit = 1 m.
  Bbox measured 0.305 × 0.119 × 0.204 m overall (X includes the +X latch hardware 17 mm proud and the −X hinge barrel); body 0.280 × 0.113 × 0.170, lid 0.286 × 0.119, handle 21 mm above the lid.
- Texturing: ONE physical material (olive-drab painted steel), procedural (scripts/material.py), baked to one atlas (scripts/uv.py: smart project → average island scale → pack):
  paint dark/mid/light + dark worn patches, faint vertical rust run-off, rust crust on edges (box-edge distance + bevel edge + AO cavity + per-part bias), stencil worn by noise, relief (rust scale, pits, dents).
  No bare steel: the photo shows paint over rust only, so both layers are non-metal.
  Palette sampled from the photo (sRGB 10/50/90 percentiles): side paint 0.043/0.047/0.035, end green 0.086/0.094/0.043, rust 0.196/0.137/0.086 → 0.263/0.157/0.098, stencil light 0.25/0.19/0.05. Lifted out of the photo's dim light, same ratios.
  Bake: Emission → float → sRGB bytes (BaseColor), ORM (R=1, G=rough, B=metal), tangent normal; 2048 px, 32 samples. Shipped material M_Metal_PaintedSteel = Principled + 3 images. Procedural kept in the .blend (fake user).
- Material audit before export: OK (no procedural nodes in the shipped material).
- Review (tools/fidelity_check.py, --view front --elevation 15 --azimuth 54, studio_small_09 HDRI):
  - Round 0: IoU 0.879. Low saturation everywhere (−0.18…−0.28), rust far too sparse: the bevel-node edge mask finds nothing on smooth rounded edges.
  - Round 1: wider bevel, more hardware rust. Little change, and shiny bare steel appeared on the hardware plus a "scattered metal" warning.
  - Round 2: analytic box-edge distance for the Body/Lid rust bands, bare steel removed. Rust now follows the photo (edges, lid border, skirt, hardware); metal warnings cleared; saturation gap halved in bands 1–2.
  - Round 3 (last): paint layer — larger dark patches, faint streaks, more matte paint, duller stencil. Then the streaks were softened further after the back view showed wood-grain-like stripes.
  - Final, on ammo-box_final.glb: IoU 0.879. Remaining gaps, not chased:
    - Band 4–5 width +20/+39%: the photo's close high camera narrows its base; an orthographic render can't match that, and the perspective was not built into the geometry.
    - Saturation −0.09…−0.23: the studio HDRI's specular desaturates the paint.
    - Luminance +0.11…+0.14: the photo's light is dim. This number depends on the light, so it was not tuned.
  - Visible differences left: the photo's front face is darker and blotchier, with nearly black worn areas; its stencil is more broken; its lid top is greener and less grey.
- Optimize (auto preset, individual steps, rule 20): gltf-transform resize 1024 → webp → draco. 6.49 MB → 160 KB (−97.5%). Geometry untouched. Clients need a Draco decoder and EXT_texture_webp.
  Note: the lossy WebP normal map is 3 KB, so its subtle relief is mostly flattened. The full normal map is in _original.glb and the .blend.
- Export: ammo-box_final.glb, 160 KB, 3,448 tris, 14 meshes, 1 material, 3 textures 1024².

## Files (compact)
- ammo-box_original.glb (6.5 MB, 2048² PNG textures) · ammo-box_final.glb (160 KB) · ammo-box.blend (packed) · ammo-box_log.md
- scripts/ (build, material, uv, bake, export, pipeline, text_mask, contact_sheet) · textures/ (stencil mask + bakes) · review/ (rounds 0–3, final, crops, joints)

## Licenses
- Geometry, materials, textures: original work (scripted in this session).
- Stencil font: Blender's built-in Bfont (DejaVu-based, free licence) — rasterised into the texture.
- Review HDRI studio_small_09 (Poly Haven, CC0) — review only, not shipped.

## Checkpoint
- Last completed step: EXPORT · 2026-10-01
