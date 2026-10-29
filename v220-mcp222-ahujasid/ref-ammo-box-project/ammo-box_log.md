# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact (original + final + .blend + log; plus the pre-markings version, kept because the brief asked to keep the version before every optional step)
- Method: scripted modeling (Blender Python), no marketplace model, no AI generation
- Output: /private/tmp/kiln-bench/v220-mcp222-ahujasid/ref-ammo-box-project/work/generated-assets/ammo-box/

## Environment
- macOS arm64, 24 GB unified memory; Blender 5.2.2 LTS, MCP addon 1.8 (protocol 14, up to date)
- Poly Haven library on; Sketchfab / Poly Pizza off; all generators off (not used — brief says scripted)
- gltf-transform and gltfpack present
- Scene at start: factory scene (Cube, Camera, Light, no .blend loaded) → Cube removed (rule 6 exception), Camera and Light kept

## Reference Image
- Path: /private/tmp/kiln-bench/v220-mcp222-ahujasid/ref-ammo-box-project/refs/ammo_box.png (1024×1015, RGBA, background already transparent)
- Identified as a US M19A1-type ammunition can (.30 cal / 7.62 mm, 200 rounds), stencil "200 CARTRIGES / 7.62 MM, M?08 / CARTONS • M31" (spelling as in the photo)

### Camera (read on the box's edges, before modeling)
- Orthographic fit of the two visible top edges: front-top edge slope 220/690, end-top edge slope −70/330
  → sin(elev)² = 0.319 × 0.212 → **elevation ≈ 15°**, **azimuth ≈ 51°** toward the box's right (+X)
- Recovered ratios from the same fit: L : W : H = 1 : 0.39 : 0.69

### Size (assumption — one photo has no scale)
- M19A1 nominal: 10.75 × 3.75 × 7 in (273 × 95 × 178 mm). Photo fit says W/L 0.39, H/L 0.69.
- **Chosen: 0.280 (X, length) × 0.107 (Y, depth, lid) × 0.187 (Z, height) m** — the photo's ratios, blended
  halfway toward the nominal can (the photo's perspective inflates the near end). Front (stencil) = −Y, latch end = +X.

### Inventory (from 2× crops in review/crops/)
- Body: deep sheet-steel box, small-radius vertical corners, rounded bottom edge      → SM_AmmoBox_Body
- Lid: shallow cap whose skirt overlaps the body top (~15 mm), rolled lip, slightly raised top panel → SM_AmmoBox_Lid, RESTING on the body
- Carry handle: flat steel strap lying along the lid's length, one end lifted ~20 mm → SM_AmmoBox_Handle, parent Lid
- Handle brackets ×2: small flat plates on the lid centreline, ~0.23 and ~0.67 of the length (modeled symmetric, ±62 mm) → SM_AmmoBox_HandleBracket_01/02, WELDED flat on the lid
- Handle bails ×2: U-shaped wire loops, legs INSERTED into the bracket knuckles, bight wrapped by the strap's rolled end → SM_AmmoBox_HandleBail_01/02
- Hinge strip: horizontal plate across the latch end just under the lid, row of 5 dome rivets → SM_AmmoBox_LatchStrip, RIVETED to the body end
- Latch lever: vertical plate hanging from the strip's knuckle, large round recessed dish (Ø ≈ 42 mm, centre above the plate's middle), bottom edge bent outward into a tab → SM_AmmoBox_LatchLever, HINGED on the strip
- Bail ears ×2: small bent tabs on the body end at the lever's foot, left and right → part of SM_AmmoBox_LatchBail mount, WELDED to the body
- Latch bail: rectangular wire loop, legs INSERTED in the ears, hanging down to ~45 mm above the base → SM_AmmoBox_LatchBail
- Corner hook wire: short bent wire at the front-upper corner of the latch end, from lid lip down to the strip → SM_AmmoBox_HookWire, INSERTED in lid lip and strip
- Stencil markings: yellow stencil, 4 lines, on the front long side → texture layer of Body (optional step: projected from the photo)

### Materials (one physical material)
- Painted sheet steel, olive drab, heavily worn: near-black dirty green on the long side, greener on lid top / end, rust bloom on every edge and all hardware
- Hardware (strip, lever, wires, handle) is the same steel, rust dominant
- Stencil paint: yellow-ochre, layer of the body

### Palette (sRGB, 10th / 50th / 90th luminance percentile)
- front long side: (0.035,0.043,0.027) / (0.047,0.051,0.043) / (0.125,0.102,0.098)
- lid top: (0.141,0.125,0.086) / (0.216,0.216,0.192) / (0.255,0.263,0.239) (sheen-lifted)
- end, lower: (0.078,0.086,0.039) / (0.086,0.094,0.047) / (0.188,0.125,0.082)
- rust (latch strip): (0.216,0.122,0.078) / (0.267,0.145,0.102) / (0.318,0.184,0.114)
- handle strap: (0.169,0.125,0.082) / (0.224,0.153,0.114) / (0.302,0.169,0.125)
- stencil yellow (contaminated sample, upper end): (0.247,0.188,0.047)

## Source
- Method: scripted (scripts/build_geometry.py), bmesh primitives + bevels + one exact boolean (lever dish), wires as
  smooth Bezier curves (AUTO handles, round bevel) converted to mesh
- Marketplace: none. AI generation: none.

## Pipeline
- Build: 11 objects, all parented under SM_AmmoBox_Body (handle parts under SM_AmmoBox_Lid), origin at the base centre,
  transforms identity, 1 unit = 1 m. Overall bbox 0.291 × 0.107 × 0.211 m (box 0.280 × 0.107 × 0.187; the lifted handle adds the rest)
- Cleanup: welded (16 verts per wire seam, shading normals kept), degenerates dissolved, loose removed; fused edges 0 everywhere;
  open edges 40, only the dish cup's front rim, hidden inside the lever's hole (intentional); cup normals flipped inward (80 faces)
- Attachment (BVH, surface to surface): every part touches or enters another; the 23 joint renders (review/round0/joints/) were looked at —
  wires enter the knuckles and ears, the hook enters both the lid skirt and the strip, the lever's top sits inside the knuckle
- Poly count: **3,246 tris** — inside the balanced prop range (1.5–5K). Wires take 1,380 of them (12-sided tubes)
- UVs: Smart UV Project + pack, two sets: Body (1 object), Lid (lid + all hardware, 10 objects)
- Texturing: one shader M_Metal_PaintedSteel (kept in the .blend): Poly Haven `green_metal_rust` box-projected and tinted to the photo's
  paint, `rust_coarse_01` tinted to the photo's rust, masked by form (bevel-normal edges, inside-AO for convex rims, AO cavities,
  band under the lid lip, per-part bias on hardware), grime blotches and rust-brown haze from noise, fine pits as bump.
  Metallic 0 (paint and rust are both non-metal crusts; the photo shows no bare steel). Baked at 1024 (Cycles, 32 spp): BaseColor
  via emission into float → sRGB bytes, Roughness, tangent Normal. Baked materials: M_Metal_PaintedSteel_Body / _Body_Marked / _Lid
- Material export audit: both exported materials are Principled + 3 image textures; GLB carries baseColorTexture, metallicRoughnessTexture
  and normalTexture for each (checked in the file). No procedural node reaches the export.

## Review against the reference (tools/fidelity_check.py, front view, elevation 15°, azimuth 51°, studio_small_09)
| Round | Change | IoU | sat band 3 / 5 | Notes |
|---|---|---|---|---|
| 0 | — | 0.905 | 0.192 / 0.151 (ref 0.392 / 0.423) | lid highlight 0.143 vs 0 |
| 1 | paint roughness +0.2 (matte field paint) | 0.905 | 0.179 / 0.135 | highlight gap gone |
| 2 | palette moved halfway up within the photo's range: paint (0.14,0.15,0.08)→(0.19,0.21,0.085), rust →(0.30,0.155,0.085), grime, haze | 0.905 | 0.242 / 0.216 | dark albedo was dominated by grey specular |
| final, shipped `_final.glb` (marked) | stencil projected | 0.905 | 0.266 / 0.216 | |
| final, shipped `_unmarked_final.glb` | — | 0.905 | 0.243 / 0.217 | |
- Width gaps in bands 4–5 (+15 %, +36 %) and band 1 (−9 %) are the photo's close perspective: its bottom edge climbs steeply to the
  left while an orthographic render keeps it parallel to the top. Not corrected — that would copy the perspective into the geometry.
- Luminance (+0.10–0.13 per band) is light-dependent: the reference is a dim render. Alarm only, not tuned.
- Remaining material gap, not closed (two-round limit): the photo's front long side has larger near-black grime patches and stronger
  rust on the vertical corners than the model; saturation still ~0.15 below the photo.

## Optional step (pre-authorised): stencil markings projected from the photo
- scripts/project_markings.py: homography from the body's front plane (x, z) to the photo, on 4 corners read on the silhouette
  (left edge line × bottom line, the lowest point = front-right base corner, lid-skirt line at both ends). Rectified face:
  textures/markings/T_AmmoBox_Front_PhotoRectified.png; yellow keyed by (R+G)/2−B and G/R (stencil 0.78 vs rust 0.55) →
  T_AmmoBox_Stencil_Mask.png (4.6 % of the face), worn letters as in the photo
- Stencil colour: photo median of the brightest quarter (0.25, 0.188, 0.043) sRGB, scaled by the round-2 factor → (0.34, 0.26, 0.06);
  mixed under the rust layer so edge rust runs over it; front face only (normal −Y), Body only
- **Version before it is kept**: ammo-box_unmarked_original.glb / ammo-box_unmarked_final.glb (material M_Metal_PaintedSteel_Body, kept in the .blend)

## Optimize (auto, glTF default preset — no geometry change)
- gltf-transform resize 1024 → webp q90 → draco (individual steps, never `optimize`)
- marked: 5.29 MB → 402 KB (−92 %); unmarked: 5.27 MB → 395 KB (−93 %). Draco needs a decoder on the client.

## Export
- ammo-box_final.glb — 402 KB, 3,246 tris, 11 meshes, 2 materials (EXT_texture_webp, KHR_draco_mesh_compression)
- ammo-box_original.glb — 5.29 MB, same geometry, PNG textures, no compression
- ammo-box_unmarked_final.glb / ammo-box_unmarked_original.glb — pre-markings version
- ammo-box.blend — full history: procedural material, both baked body materials, all textures packed
- Parts not in the photo, NOT invented: the hinge end (−X), back long side and underside are plain painted steel

## Licenses
- green_metal_rust (Rob Tuytel), rust_coarse_01 (Dimitrios Savva, Rico Cilliers), studio_small_09 HDRI (review only, not shipped):
  CC0. Source: Poly Haven (polyhaven.com), via the public API
- Stencil markings: projected from the user-provided reference image (user's own material)

## Checkpoint
- Last completed step: EXPORT (+ final fidelity measure of the shipped files)
- Timestamp: 2026-10-21 15:35
