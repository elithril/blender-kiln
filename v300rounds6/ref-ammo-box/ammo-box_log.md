# Ammo Box — Production Log

## Config
- Type: prop
- Target: glTF (GLB)
- Tier: balanced (prop 1.5–5K tris, soft; up to 10K reported, never blocked)
- Style: realistic
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling (user's brief: no marketplace, no AI generation)
- Live view / Kiln Studio: off (unattended bench run; nothing to open)
- Output folder: /private/tmp/kiln-bench/v300rounds6/ref-ammo-box/work/generated-assets
- Environment: Blender 5.2.2 LTS, MCP for Blender addon 1.8 (protocol 14, up to date); Poly Haven library on.
  The open Blender holds only the untouched factory scene; the build runs headless
  (`/Applications/Blender.app/Contents/MacOS/Blender -b`) from `scripts/build.py`, reviews are headless renders
  (rule 2 headless path). Nothing of the user's is touched.

## Reference Image
- Path: /private/tmp/kiln-bench/v300rounds6/ref-ammo-box/refs/ammo_box.png (1024×1015, RGBA, already cut out)
- Brief: "Rebuild the ammo box in this reference image as a game asset … Match the reference's proportions,
  parts, materials and colours as closely as you can."
- Assumptions (auto mode, stated not asked):
  - Real size: a US M19A1 .30 cal / 7.62 mm can — 276 × 97 × 183 mm (L × W × H, lid closed). The image's
    ratios agree: end face W/H ≈ 0.46 apparent at ~56° → 0.53 real (M19A1: 0.53).
  - Camera: azimuth ≈ 56° toward +X (the long stencilled side is the front, −Y; the latch end is +X),
    elevation ≈ 15° (read on the lid's top edges: X edge drop 220 px over 876 px depth-proj., Y edge 55/213 px).
    Close perspective camera (verticals converge).
  - Unseen: back long side (+Y), the hinge end (−X) and the underside. Kept plain and closed, no invented parts;
    the hinge end gets a plain lid skirt only.
- Stencil text as read: "200 CARTRIGES / 7.62 MM,  M108 / CARTONS • M31" (spelling of the photo kept;
  "M108" is a reading of a partly worn mark).
- Palette sampled (sRGB, 10/50/90th pct, photo light is dark):
  side paint (9,11,7)/(11,13,10)/(33,26,25); stencil (66,50,9) light; lid top (32,30,21)/(46,34,21)/(57,58,53);
  end paint (20,21,10)/(20,23,10)/(22,24,12); rust rim (30,16,10)/(68,48,41)/(94,59,36);
  latch plate (21,20,10)/(35,28,18)/(58,34,27); handle (42,32,21)/(67,37,28)/(77,42,32).

### Inventory (from 2–3× crops in crops/)
- body: steel box, vertical corners rounded (~8 mm), bottom edge bevelled           → SM_AmmoBox_Body
- lid: overlapping cap, ~22 mm skirt over the body, rolled/rounded top edge, two
  round embossed dimples near the latch end on top                                    → SM_AmmoBox_Lid, RESTS on body (skirt overlaps it)
- top handle: flat steel strip ~170 × 30 mm, left end raised (folded up ~25 mm)       → SM_AmmoBox_Handle, held by the wire loops
- handle brackets: two flat stamped plates on the lid with a bent wire loop each,
  loop legs INSERTED into the bracket, strip ends hooked over the loops               → SM_AmmoBox_HandleBracket_L/R (+ wire in each)
- rivet strip: horizontal strap across the latch end under the lid, 5 dome rivets   → SM_AmmoBox_RivetStrip, WELDED to body end
- latch lever: tall plate on the latch end, chamfered lower corners, large round
  dished recess in its upper half, two hinge tabs at its top                          → SM_AmmoBox_LatchLever, hinged under the rivet strip
- lid hook wire: thin wire from the lid's skirt at the end's left edge down to the
  lever's left tab                                                                   → SM_AmmoBox_LidWire, INSERTED into skirt and tab
- lower bracket: two bent tabs on the body end below the lever                      → SM_AmmoBox_LowerBracket, WELDED to body end
- bail wire: rectangular wire loop hooked in the two lower tabs, hanging down        → SM_AmmoBox_Bail, INSERTED into the tabs
- stencil: three lines of yellow-ochre stencil on the front long side, worn          → paint layer of the body material (baked), not geometry
- wear: heavy rust on edges, lid, end face, all small parts; dark olive paint
  remaining in big patches mid-side                                                  → wear layer of the steel material

## Intent (before the first primitive)
- Palette (roles): main = dark olive drab paint (≈ sRGB 42,46,28, dark 25,28,18); secondary = brown rust
  (light 95,55,32 / dark 60,32,20); accent = stencil yellow-ochre (≈ 140,105,20, used once: the text);
  metal = bare steel at the hardest-worn edges (≈ 120,115,105, metallic).
- Materials (one per physical material): M_AmmoBox_PaintedSteel (body, lid, plates — paint over steel, rust as a
  layer within it, scanned Poly Haven green_metal_rust tinted + rust_coarse_01 masked by form);
  M_AmmoBox_RustedSteel (handle strip, wires, rivets, tabs: bare corroded steel, rougher);
  stencil paint as a layer of the painted steel (baked into it). Roughness: paint 0.55–0.7, rust 0.85–0.95,
  bare steel 0.4.
- Finishes: bevels on every visible edge (body corners, lid roll, plates 1 mm); wear where hands go (lid edges,
  latch lever, handle → rust and bare steel); detail at each end: 5 rivets on the strip, wire loops through
  their brackets, two embossed dimples on the lid, the bail hooked in its tabs.

- Visual comparison: close match — all inventory parts present and placed (ticked below); paint reads greener/cleaner
  than the photo's near-black olive under its dark light (logged, kept).
- Inventory ticked at the final review (photo crops vs final sheets): body ✓, lid + rolled rim + 2 dimples ✓, handle strip
  raised on its −X loop ✓, 2 handle brackets + loops ✓, rivet strip 5 rivets ✓, latch lever + round recess + hinge tabs ✓,
  lid hook wire ✓, lower bracket + tabs ✓, bail ✓, stencil 3 lines ✓, wear (rust edges, end, lid rim) ✓.

## Prompts
- Concept art: none (user image)

## Source
- Method: scripted (Blender Python, headless), from the reference image
- Textures: Poly Haven green_metal_rust, rust_coarse_01 (CC0) — thumbnails compared to the photo's crops
  (crops/thumbs_montage.png): green_metal_rust reads like the olive paint, rust_coarse_01 like its smooth brown rust.

## Pipeline
- [1] CONFIG + [2] BRIEF: done — brief reformulated above, assumptions stated (auto mode).
- [3] SOURCE: scripted (user's choice in the brief), `scripts/build.py`, headless Blender 5.2.2, factory scene emptied
  by `read_factory_settings(use_empty=True)` (no user object touched). 12 separate parts, SM_AmmoBox_* (rule 15).
  - v0 → v1 (proportions read on the photo, near vertical edge = 4044 px/m): lid skirt 22 → 13 mm (photo: thin cap,
    rolled 4–5 mm rim); end-face parts raised to the photo's heights — rivet strip z 146–164 mm, lever 69–146 mm,
    recess r 16.5 → 19 mm centred z 118 mm, lower tabs z 66–80 mm, bail down to z 47 mm; handle brackets set
    symmetric at x = ±66 mm (photo's −83/+46 mm is mostly perspective; a centred handle is the real object).
- [4] IMPORT (scripted, implicit): 12 objects, 6,248 tris; world bbox on vertices X −139.2…139.2, Y −49.7…49.7,
  Z 0…212.9 mm (lid top 183.8 mm, the raised handle end 212.9 mm); stands on the ground (z min 0). 1 unit = 1 m.
  Look: review/geo/ammo-box_geo_matcap_q1.png, _q3.png (headless matcap renders, rule 2 headless path).
- [5] CLEANUP: per object merge-by-distance 0.01 mm, normals recalculated outward, sharp edges marked > 40°
  (flat shading on the lever, rivet strip and lower bracket — the boolean recess smeared smooth shading), no
  transforms to apply (built in world space). Attachment (BVH, surface to surface): every part ≤ 0.37 mm from its
  neighbour; the bail floated 1.45 mm off its tabs in v1 → its ends now enter both tabs (0.1 mm). Tris 6,248 vs tier
  1.5–5K: within 2× the top — the extra is in the 5 wires (12-sided, 306 faces each) and the rounded lid; kept, no
  reduction proposed (rule 4).
- [5b] TEXTURING: `scripts/texture.py` + `scripts/params.json`. One procedural steel shader (M_AmmoBox_Steel_Procedural,
  kept in the .blend with a fake user): Poly Haven green_metal_rust (paint) and rust_coarse_01 (rust), box-projected,
  tinted to the photo palette; rust masked by the form (AO-inside convex edges, AO cavities), a per-object `wear`
  attribute, broad noise patches, a rust band down from the lid on the body, more on the latch end (+X normal);
  bare steel only on the hardest edges; stencil = Blender's built-in font (Bfont) rendered to
  textures/stencil_mask.png, projected on the −Y face, chipped and under the rust. Baked to 3 texture sets
  (Body, Lid, Parts atlas) — colour (Emission bake, float → sRGB bytes), roughness, metallic, tangent normal —
  final materials M_AmmoBox_Body / _Lid / _Parts are Principled + images only (glTF-safe). UVs: Smart UV Project 60°,
  packed per set.
- Rounds (reference image, fidelity_check, az 56°, el 15°, ortho; review/front/):
  - v1: silhouette 0.853; band 5 +25 %, band 1 −30 % (the photo's close perspective: the near latch end and the
    lid top read larger — expected, not reshaped). Surface: paint too light/green, pale bare-steel patches on lid,
    lever and handle (AO-inside reached through thin plates and into the body under the lid), a scan mark on the
    front reading as a hanging wire. → paint darker (30,33,21), scan detail halved, edge AO 8 → 2.5 mm, bare
    threshold 0.45 → 0.7, lid wear 0.55 → 0.35.
  - v2: 0.853; now too clean against the photo's heavy rust. → rust reach raised (edge 4 mm, weights up), +X end term.
  - v3: 0.853; face details 11.2 mm too low (stencil); rust too orange and blotchy low on the body. → stencil up
    5.5 mm (halfway), rust darker (82,45,28), patches weaker, rust band from the lid line; paint rougher 0.6–0.8.
  - v4: 0.853; the band also rusted the whole lid → band restricted to the body, cavities keep their paint
    (photo: the lever recess is dark olive), lid wear 0.45 for its rust rim, bare steel scaled down on rusted parts
    (the wires read as bright steel). Shape untouched since v1 — the two reshaping rounds were not needed.
- Final bake v4 at 1024 / 64 samples; uv_check: 12 meshes ok, 0 FAIL, 0 WARN (no overlap, no collapsed UVs).
- Review round 1 (review/round1.png, round1_clay.png, round1_end*.png; fresh reviewer + own reading):
  1. all tiles: handle strap tilted, one loop standing → ARGUED, kept: the photo's top crop (crops/top_handle.png)
     shows exactly that (−X loop up, strap resting on the +X loop's hem); the reviewer read the photo as flat.
  2. side/clay: bail hangs out ~30° past the outline → hangs straight down now (bottom 1.5 mm out, not 6).
  3. side tiles: rust a bright orange band, body green too light, lid clean & glossy → this round: palette darkened
     (paint 26,29,19 / dark 12,14,9; rust 68,38,25 / dark 36,20,14); distribution + lid gloss next round (one
     change per material region per round).
  4. end close-up: recess reads as a rusty raised disc → face attribute `paint_keep` on the recess, the shader
     keeps the paint there (dark olive, as the photo).
  5. stencil too bright, round, unworn → ochre 128,98,34, cap 20 → 22 mm (narrower look at the same width),
     more chipping. Font kept: Blender's Bfont (licence-clean; no condensed stencil font bundled).
  6. lid: overhang at the latch end → lid extended 3 mm over the latch end.
  7. lid gloss → next round (same region as 3).
  8. vertical crease on the front/back → the paint scan's own seam mark; box projection offset, scan detail 0.5 → 0.4.
  9. upper hinge tabs sharp blocks sticking 12 mm out → 8.5 mm, chamfered, 0.8 mm bevel.
  10. body surface too smooth → open (relief already from both scans' normals; revisit after colour).
  11. back repeats the front's wear → open, next round with the distribution.
  12. underside unseen → rendered: review/round2_under/.
  Own reading: lever, rivet strip, bail centred on the end (clay end tile), nothing floats (BVH ≤ 0.37 mm).
  Fixed, re-baked at 512/24 for review; silhouette 0.853 → 0.859 (lid lip). Round 2 next.
- Review round 2 (review/round2*.png, round2_under/; fresh reviewer):
  1. lid glossy blue-grey, no rust rim (blocking) → paint roughness 0.6–0.8 → 0.7–0.88, lid wear 0.45 → 0.55.
  2. rust in saturated orange bands under the lid and along the bottom (blocking) → rust moved onto the edges
     (edge weight 1.6 → 2.2, AO-inside 4 → 5 mm), body top band 0.3 → 0.12, patches 1.3 → 1.0, rust 62,35,23.
     (1 and 2 touch the same region in one round — both blocking; roughness and distribution are separate channels.)
  3. stencil "7.62 NM" — the first M chipped away → chipping threshold 0.4 → 0.33.
  4. recess reads as a glossy lens → same cause as 1 (roughness).
  5. two large domed buttons on the lid → the photo shows two dimples there (crops/end_top.png); shrunk r 6.5 → 5 mm,
     1.6 → 1.0 mm high.
  6. lid seam a thin line, photo has a heavier rolled rim → bead 1.2 → 1.8 mm out, 3.5 → 5 mm tall.
  7. underside near-black, no texture → argued: it is the dark paint facing the floor, closed and bevelled; kept.
  Re-render (round3 sheets): rust now follows edges and the lid rim. Lid still reads glossy: measured roughness map
  0.78 mean, metallic 0.01 — correct; the cause is the paint's albedo (linear 0.010), so dark that the 4 % specular
  dominates. → paint 26,29,19 → 38,42,27 (dark 20,22,14), roughness 0.75–0.9: faded olive drab, the photo's darkness
  being its light (fidelity_check: luminance is light-dependent, an alarm, not a target).
- Review round 3 (review/round3*.png; reviewer A: nothing blocking, "would show"; reviewer B, same sheets: 2 blocking):
  1. B: handle should lie flat (blocking) → re-measured on the photo, not taken on trust: a flat strap at Y=0 would run
     parallel to the lid's front edge (image slope 0.32); the photo's strap slopes 0.41 and its −X end sits ~70 px ≈ 19 mm
     above its own bracket, on a standing wire (crops/top_handle.png). Raised it stays; lift corrected halfway
     24 → 21 mm (A also found it steep).
  2. B: wear lighter and cleaner than the photo, no rubbed dark patches (blocking) → dark worn-paint patches back
     (dark 14,16,10, wider noise range), body band from the lid 0.12 → 0.2.
  3. A+B: recess still reads as glass → recess paint darker (paint_keep → dark multiply) and matte (0.92).
  4. B: stencil crisp → kept at round-2 chipping (A found it fine; the round-2 reviewer had "NM" from more chipping).
  5. B: "tick marks" under the lid rim on the back → looked at round4_clay_back.png: the strap's soft shadow
     (EEVEE sampling), no geometry there.
  6. B: latch plate flat, photo's lower edge leans out → lever tilted 3° about its hinge; its tabs then lifted 0.5 mm
     off the end (BVH check) → tabs sunk 1.5 mm into the end face, 0.04 mm now.
  7. A+B: lid dimples oversized → already shrunk in round 2; the photo shows them (crops/end_top.png); kept.
  8. A: faint line under the bail → the bail's shadow (round3_end_clay_close.png), no geometry.
  9. A: plain hinge end (−X) → unseen in the photo, kept plain and closed (no invented parts).
  Silhouette 0.860 → 0.874 (strap lift). Round 4 next.
- Review round 4 (review/round4*.png): reviewer A — nothing blocking, "yes, would show"; own reading — nothing
  blocking; reviewer B (second fresh reading, same sheets) — nothing blocking, "yes". Two clean readings in a row:
  the rounds end (4 rounds, cap 8). Details applied after the readings, cheap and separate regions:
  1. A: dashed line under the lid lip (clay back) → real: the rim bead and the lid shared a coplanar bottom face
     (z-fighting) → bead bottom 0.5 mm lower.
  2. B: lid should be one step lighter than the body (photo) → object attribute `paint_lift`, lid paint ×1.35.
  3. A+B: stencil a little bright/orange → ochre 118,92,36.
  Left as they are (details, logged): paint still greener/cleaner than the photo's near-black olive (both readers);
  the photo's light is unknown and darker paint made the lid read as glossy plastic in round 2, so the albedo stays a
  faded olive drab; no pitting/dent geometry on the panels (the scans' normal maps carry the relief); hinge end and
  underside plain (unseen in the photo).
  Final look at the joints (review/joints_grid.png, 24 joints from fidelity_check): every wire and tab enters its part;
  the rivet domes were faceted (flat shading set on the whole rivet strip for the lever's boolean) → strip back to
  smooth + sharp edges, rebaked.
- Material audit (rule 19): shipped materials M_AmmoBox_Body / _Lid / _Parts = Principled BSDF + image textures only
  (colour sRGB bytes, roughness+metallic, tangent normal); the procedural source shader stays in the .blend (fake user,
  assigned to nothing, not exported). Verified on the re-imported GLB: roughness ≈ 0.78, metallic ≈ 0.01, normal 0.5/0.5/1.
- [6] OPTIMIZE (auto mode, glTF, rule 20 — separate steps, no `optimize`): gltf-transform resize 1024 → webp q90 →
  draco. ammo-box_original.glb 7.96 MB (4 sets of 1024 PNG) → web/ammo-box_final.glb ≈ 0.50 MB (−94 %). Geometry
  untouched (6,552 tris). ammo-box_preview.glb = copy of _original (no Draco, no WebP: `extensionsUsed` none — the
  file a Mac's Quick Look opens). Exported with tangents; gltf-transform validate: 0 errors; 7 warnings
  MESH_PRIMITIVE_GENERATED_TANGENT_SPACE (7 of 12 primitives get MikkTSpace tangents from the viewer, as the spec
  prescribes); infos: UNUSED_OBJECT ×12 (Draco's leftover buffer views), UNSUPPORTED_EXTENSION (the validator does
  not check EXT_texture_webp). Draco needs a decoder on the client.
- Rebake after the rivet fix (1024 / 64): uv_check 12 meshes 0 FAIL 0 WARN; re-optimized: _original 7.94 MB →
  web/ammo-box_final.glb 0.50 MB (−94 %); preview = copy of _original.
- [7] EXPORT: glTF (GLB), Y-up, export_apply off (rule 18; no modifiers left — all applied at build), tangents on.
  Last measure on the shipped file web/ammo-box_final.glb (rule: the file that ships): silhouette IoU 0.874
  (v1 0.853 → 0.874; no drop at the end), 6,552 tris, 12 meshes, 3 materials, 9 images ≤ 1024 px; vertices
  X −139.8…153.0 (latch hardware to +153), Y −50.3…50.3, Z 0…209.9 mm — on the ground, 1 unit = 1 m.
  Final looks: review/final.png + final_clay.png (six views), review/final_views/ (two opposite three-quarters,
  top, under, rivet close-up — rivets smooth). Studio `checks`: no WARN; notes: tris +31 % over the tier's top
  (wires, rolled lid, rivets — kept, rule 4), licences to credit.
  .blend saved: ammo-box.blend (packed textures, procedural shader kept with fake user; save_version 0, no .blend1).
- Files: root — ammo-box.blend, ammo-box_original.glb, ammo-box_preview.glb (opens in Quick Look), ammo-box_log.md;
  web/ammo-box_final.glb (Draco + WebP, for the site/engine). Intermediates kept (auto mode, nobody to ask —
  compact storage proposes their removal): ammo-box_geo.blend, scripts/ (build.py, texture.py, params.json …),
  textures/ (baked PNGs, stencil mask), textures_src/ (Poly Haven sets, HDRI), crops/, review/ (~190 MB of renders).

## Licenses
- Poly Haven textures green_metal_rust, rust_coarse_01: CC0. Source: Poly Haven (polyhaven.com), via the public API.
- Reference image: user-provided.
- Stencil font: Blender's built-in Bfont (GPL with font exception), rasterised into the texture only.
- HDRI studio_small_09 (review renders only, not shipped): CC0, Poly Haven.

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-29 10:11
