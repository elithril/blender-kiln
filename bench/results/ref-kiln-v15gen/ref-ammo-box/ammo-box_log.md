# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: realistic
- Mode: auto
- Storage: compact
- Method: scripted modeling (user brief: no marketplace model, no AI generation)

## Reference Image
- Path: /private/tmp/kiln-bench/ref-kiln-v15gen/ref-ammo-box/refs/ammo_box.png (1024x1015, RGBA, alpha cut-out)
- Crops: review/crops/ (top_handle, end_top, end_latch, bottom_corner)

### Assumptions (one photo cannot say)
- Real size: US M19A1 .30 cal / 7.62 mm can, as the stencil says — 0.280 L x 0.095 W x 0.180 H m
  (lid closed, handle folded). No size given in brief → assumed.
- Camera: 3/4 view from the right, looking down. Azimuth ~50 deg (read from projected long-side /
  end widths 680 px / 300 px against the 2.95 L/W ratio), elevation ~20 deg (lid top visible).
- Unseen sides (back long face, left end, bottom) are not in the photo: back = plain painted face,
  left end = plain panel with lid hinge knuckle, bottom = flat. These are inventions, kept plain.
- Stencil text copied as the photo shows it, misspelling included: "200 CARTRIGES / 7.62 MM, M 08 /
  CARTONS • M31" ("M 08" probably a worn "M13").
- The photo is lit low-key (paint mid at sRGB ~(22,24,12)); base colours keep the sampled hues, lifted
  ~1.5x to stay albedo values under a neutral light.

### Inventory (part → how it meets)
- body: rectangular steel can, small corner radii, flat sides               → SM_AmmoBox_Body
- body bottom: rounded bottom edge, rust heaviest there                      → Body
- lid: shallow cap, top panel slightly raised, skirt overlapping body top, rolled bead along the long sides → SM_AmmoBox_Lid, RESTING on body (skirt around body top)
- lid end flange (+X end): turned-down lip carrying a riveted strip           → Lid
- latch hinge strip: flat strip with 5 dome rivets, RIVETED to the end face just below the lid → SM_AmmoBox_LatchHinge, flat against Body
- latch lever: tall plate, round hole near the top showing the end face, two ears at its bottom, hinged at the strip → SM_AmmoBox_LatchLever, hinged into hinge strip, lying on Body end
- latch side wire: thin wire from lid corner down to hinge strip ear (left)   → SM_AmmoBox_LatchWire, ends INSERTED into Lid and hinge ear
- lower bracket: bent sheet bracket with two ears, WELDED to the end face below the lever → SM_AmmoBox_LatchBracket
- bail wire: rectangular wire loop hooked through the bracket ears, hanging down → SM_AmmoBox_BailWire, ends INSERTED into bracket ears
- end recess: vertical channel in the end face behind the lever             → Body (modelled as raised side ribs)
- handle: flat steel strap with turned edges lying along the lid             → SM_AmmoBox_Handle
- handle mounts (x2): small rectangular base plates WELDED to the lid, each with a wire staple whose legs enter the plate and loop through the handle end → SM_AmmoBox_HandleMount_01/02 + SM_AmmoBox_HandleStaple_01/02
- stencil: yellow paint, 3 lines, front long face, worn                      → texture on Body
- finish: olive drab paint, worn through to brown rust on edges, rims and hardware; dark grime patches → one material family (painted steel), rust as a layer

## Prompts (copy-paste ready)
- Concept art: none (user image)

## Source
- Method: scripted (Blender 5.2.2 LTS, blender-mcp addon 1.8)
- Scripts: scripts/01_model.py (geometry), 02_stencil_mask.py (stencil mask render), 03_uv_shader.py (UVs + source
  shader), 04_bake.py (bake + glTF materials), 05_cleanup_export.py (cleanup, audit, export), rev.py, montage.py

## Pipeline
- Scene: factory startup scene (Cube/Camera/Light, no .blend) → factory Cube removed (rule 6 exception). Camera, Light kept.
- Build: 13 parts in collection Props_AmmoBox, parented to empty SM_AmmoBox, origin = base centre, 1 unit = 1 m
  Body, Lid, LatchHinge (5 rivets), LatchLever (round hole), LatchBoss, LatchBracket (2 ears), BailWire, LatchWire,
  HandleMount_01/02, HandleStaple_01/02, Handle
- Import/bbox: 0.292 x 0.102 x 0.205 m (body 0.276 x 0.091 x 0.168; lid to 0.180; handle staple raises the top to 0.205)
- Cleanup: merge by distance (48 verts merged on wire seams), loose 0, degenerate dissolve, normals recalculated,
  fused edges 0, open edges 0, transforms identity, attachment check (BVH) — every part ≤ 0.3 mm from another
- Poly: 3,856 tris — inside balanced prop tier (1.5-5K). Spent on: wires/staples 1,688 (round sections), hinge strip
  + rivets 588, lid with bead 492, lever 400
- Texturing: one physical material (painted steel), baked to two texture sets, 1024 each:
  M_Metal_PaintedSteel_Body (body) and M_Metal_PaintedSteel_Hardware (lid + all hardware)
  - base: Poly Haven green_metal_rust scan, tinted toward the photo's olive
  - wear: Poly Haven rust_coarse_01 scan, tinted toward the photo's rust, masked by form (bevel-vs-normal edge mask,
    AO cavities, the bottom 35 mm, broad patches, rust bias per part: hardware 0.8, lid 0.12, body 0); noise only breaks the border
  - grime: broad dark blotches over the paint; stencil: rendered text mask projected on the front face, yellow, worn
  - metallic 0 throughout (paint + rust crust are non-metals); relief baked to tangent normal maps
  - colour baked via Emission to float, converted to sRGB bytes before export; source materials kept (fake user) in .blend
- Material audit (rule 19): shipped materials = Principled + image textures only, no procedural nodes
- Optimize: gltf-transform resize 1024 → webp → draco (separate steps, no simplify): 5.54 MB → 187 KB (-97%).
  Draco needs a decoder on the client.
- Export: GLB, export_apply=False, Y-up

## Review (tools/fidelity_check.py, ortho, azimuth 50, elevation 20 — fixed before modelling)
- Round 0: IoU 0.918. Shape gaps in band 1 (-22%) and band 5 (+11%): photo perspective (close camera, top converges),
  which an ortho render cannot reproduce — geometry left alone. Material: paint too light / green / clean vs the photo's
  near-black blotched olive.
- Round 1 (paint): palette lift 1.5x → 1.2x, dark grime (13,15,10) over ~half the paint. Luminance gap -0.02/band; visibly closer.
- Round 2 (sheen): paint roughness 0.38-0.68 → 0.55-0.80; lid no longer mirrors the studio light (satin as in the photo).
- Final (shipped _final.glb): IoU 0.918, identical to round 2 — export changed nothing.
  Remaining: saturation 0.12-0.18 below the photo and luminance higher — the photo is low-key lit;
  light-dependent, not tuned to.
- Joints: 22 joint renders looked at (review/r0/joints_sheet.png): staple legs enter mount plates, handle ends roll
  round the staple bars, bail hooks through the bracket ears, rivets sit on the strip.

### Inventory tick (final, crop vs render)
- [x] body, rounded edges, rust at the bottom
- [x] lid with rolled bead, skirt over the body, pressed top panel, two rivet dimples
- [x] hinge strip with 5 rivets, side ear + side wire into it
- [~] latch lever with round hole — present, but the hole reads as a rusty disc (the boss behind takes hardware rust);
      the photo shows a dark painted recess
- [x] lower bracket with two angled ears, bail wire hanging down
- [x] handle strap, 2 mount plates, 2 wire staples (one raised, one folded)
- [~] stencil — layout and words match; wear is heavier than the photo's on "CARTONS" and "M 08"
- [x] olive paint worn to brown rust on edges and hardware, dark grime blotches

## Visual comparison: close match (shape, parts, palette); materials slightly cleaner/lighter under a neutral studio light

## Licenses
- green_metal_rust, rust_coarse_01 texture sets: CC0 — Source: Poly Haven (polyhaven.com), via the public API
- studio_small_09 HDRI (review renders only, not shipped): CC0 — Poly Haven
- Reference image: user-provided. Geometry and shaders: scripted in this session.

## Files (compact)
- ammo-box_original.glb (5.54 MB) · ammo-box_final.glb (187 KB) · ammo-box.blend (10.1 MB, textures packed) · ammo-box_log.md
- working: scripts/, textures/ (baked PNGs), src_tex/ (scans, stencil mask, HDRI), review/ (crops, renders, fidelity output)

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-01 20:04
