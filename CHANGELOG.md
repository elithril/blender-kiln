# Changelog

All notable changes to blender-kiln are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — ready-made humanoid moves (3.0)

- **`tools/presets.py`**: `list` the 22 motions (43 clips: 21 in two takes, a woman's walk),
  `animate --asset X_rigged.glb --motion walk,run,jump,dance [--loop] [--speed] [--take A|B]`
  on a rig with kiln's names — one GLB with a clip per motion named as asked, a measures JSON,
  a provenance record. The clips are image-to-3dlab's (AssetFurnace, Apache-2.0) presets made
  with NVIDIA Kimodo (NVIDIA Open Model License, commercial use allowed), shipped in
  `tools/motions/` (2.1 MB); `tools/retarget.py` adapts its retarget; both in `plugin/NOTICE`.
- **Corrected before keying**, each measured on the kiln child and the Hunyuan3D humanoid
  (`references/animation.md` § Humanoid presets): bones by name (Hunyuan's handless arm: arm
  through body 4,285 → 1,548 mm² on the walk); feet planted (walk slide 293 → 2.7 mm/s and
  568 → 10.6, under the floor 22.9 → 0 and 38.2 → 0.5 mm); arms out of the hips and belly, the
  swing capped at 25° (child walk 2,638 → 377 mm²); `--loop` adds a closed in-place cycle,
  `{motion}_loop` (walk seam 6.22 → 0.69× a step, 6.42 → 1.20), beside the whole take, which
  keeps the run's start and stop; a near-straight knee bends toward the thigh's front while the
  feet are planted (the child's walk had bent its knee backward 17-35° around heel strike).
  The Hunyuan humanoid stays above 500 mm² of arm through
  body on walk, jump and dance: its fused hand and its shoulder's skin; said, not hidden.
- **PHASE 5d routes** a kiln-named humanoid and a move in the list to `presets.py`; another
  move, a non-human biped or wings to UniMate, non-commercial; quadrupeds unchanged.
- **`tools/motion_measure.py`**: the comparison's measure, for any route. **`tools/test_presets.py`**,
  13 checks on a seeded humanoid (names, licences, feet, arms, loop), on every push without
  Blender and in the Blender workflow.

### Fixed — looped clips keep the hips' height, and carry one clip (3.0)

- **`tools/motion_loop.py`** removed the root's drift and blended its height on the bone's
  own location channels. On a `Hips` bone that leans (12.5° on the Hunyuan3D humanoid) that
  is the wrong axes: the looped hips climbed up to 115.6 mm on a walk and 148.9 mm on a run.
  Worked in world axes now: −2.5 and −6.9 mm against the source (8 clips, both humanoids).
- The `.loop.glb` carried the un-looped source action as well, and on the Hunyuan rig the
  importer made that one active. It now holds one clip, `Loop`, keyed 0..P with key P equal
  to key 0 (animation rule 5) — its seam measured 0.55-1.6× a frame step on the 8 clips.
- `verify_blender.py` loops a travelling root tilted 12.5°: one action, a closing key, the
  height kept (the bone-local version: −131.4 mm, caught).

### Added — the photo's own markings, projected (optional, 3.0)

- **`tools/photo_project.py`**: after the last fidelity round, puts the reference photo's own
  pixels on the base-colour textures where the photo sees the model squarely — for text, a
  logo or precise wear a script copies as a lookalike. The camera is fidelity_check's, fitted
  to the silhouette (bounded to 10°); under 0.95 IoU it refuses. Confidence per texel after
  AssetFurnace's Pixel Match (image-to-3dlab, Apache-2.0 — `plugin/NOTICE`), facing ≥ 0.6;
  the photo brought to the model's exposure by one median gain, never pasted raw; `--exclude`
  for misplaced parts, `--erase-stencil` against a doubled marking. On the bench ammo box:
  IoU 0.918 → 0.963, SSIM from the photo's view 0.551 → 0.597, ΔE76 17.46 → 16.84, GLB
  186.6 → 175.4 kB; with handle and lever excluded and the stencil erased, 0.589 / 17.27 and
  the double "7.62" gone. Those numbers are partly circular (the photo against itself), so
  the tool renders two other angles to look at. One object tested.
- **Offered, never run silently** (rule 6): the scripted-modelling row of PHASE 3 and
  `references/reference-fidelity.md` § 5 propose it only when the photo carries markings and
  the shape is final. `references/photo-projection.md` has the method, the table and the limits.
- **`tools/test_photo_project.py`**, 12 checks in the Blender workflow: a printed letter
  recovered from a seeded photo (correlation 0.17 → 0.95), the unseen back unchanged, an
  excluded part kept, a stencil erased in view and kept unseen, a 40 % too long box refused.

### Added — learned auto-rig (3.0)

- **`tools/autorig.py`**: rigs a character with SkinTokens (VAST-AI, MIT, local) and hands
  back kiln's skeleton — Mixamo names, weights cleaned (≤ 4 influences, normalised, specks
  dropped), lid and ear bones added, the validator's checks run. On one bent pose it crossed
  2,985 mm² of skin through skin against Rigify's 3,926 on a kiln-built child, and 20,917
  against 50,680 on a generated humanoid with a hand fused to its hip. It fails naming the
  bone when a limb comes back short (that humanoid's right hand), and refuses a model facing
  +Y. `references/characters.md` § Learned auto-rig has the table, the method and the limits:
  one pose, two humanoids, no humanoid walk, and runs that differ (2,193 on another run).
- **PHASE 5c routes first**: a humanoid or a mesh kiln did not build → the learned rig when
  installed; a quadruped kiln built → its own rig (SkinTokens walked kiln's cat worse, 527 mm²
  mean against 359). A generated quadruped is rigged both ways.
- **`/kiln setup`** detects it and offers it, asked first: ~5.6 GB, MIT, Apple Silicon through
  kiln's patch (from image-to-3dlab, Apache-2.0 — `plugin/NOTICE`), 35-54 s and ~7 GB of
  memory per mesh. Pinned commit, packages and checkpoint hashes.
- **`tools/test_autorig.py`**, 31 checks without SkinTokens: the four measured raw skeletons
  named as by hand, the fused hand and seeded breaks failing by name, cleaning, lids and ears;
  on every push (no Blender) and in the Blender workflow.

## [2.3.0] — 2026-10-12

kiln now models for a **3D printer** — simple objects only. Measured on sessions given the
skill and a brief or a photo, nothing else: a dog house and a lighthouse from a brief, a
pumpkin and a ghost from photos, a windmill (two parts) from a brief, a teapot from three
museum photos — all printable, all but the ghost's cat looking like what was asked. That cat,
then a real cat from its photo, passed every print check and were unacceptable to look at, so
print mode says at CONFIG that a realistic likeness of a real animal or person is out of reach,
and builds a stylised figure from metaball families and one voxel remesh — the method a v2.2
session found by itself on a cartoon dragon, made from one flat drawing in four colours.

### Added — 3D printing

- **Print in CONFIG** (FDM or resin, height, the printer's colours) switches modelling,
  cleanup and export to `references/print.md`: model at print size, closed solids, one
  volume (exact union as you go, or overlap + one voxel remesh, last), minimum thickness,
  a flat base, overhangs designed out where nobody looks and supported where the photo shows
  them, relief as geometry, a smooth surface the printer will not facet, parts printed apart
  when they would print in the air, STL in mm.
- **`tools/print_check.py`**: a printability verdict, raw — open and non-manifold edges,
  normals, held and floating parts, walls, overhangs, loss against the original (dimensions
  and volume, closed cavities taken out exactly), and PrusaSlicer as a second arbiter
  (`--slicer`, `--supports`). It says when it rescales. 44 seeded cases.
- **Like the photo, for print**: openings read on their outer edge, details cut along the
  photo's camera, a `face` measure in `fidelity_check`, and rounds until the gaps stop
  closing — the two-round cap does not apply to print.
- **`tools/cutout.swift`**: macOS Vision's subject lifting cuts a photo out, local and free,
  where a background fill could not part a white ghost from a white wall.
- **`tools/flatten.py`**, for a model you made: nearly flat faces made exactly flat, the model
  laid level on the bed, nothing else touched — curves, folds, bevels, steps and real slopes
  kept, no vertex past the tolerance, the input never overwritten, holes left to the slicer
  (which closes small ones: an open-topped cube sliced fine in PrusaSlicer 2.9.6). On the
  windmill turned 1° with 10 % of its vertices off, PrusaSlicer finished the gallery floor at
  4 heights and held the print by one edge (629 mm of first layer); flattened, 1 height and
  the whole base (3,317 mm). 22 seeded cases, each after the first added when a real model
  broke the tool. `/kiln inspect` and `/kiln cleanup` gain a print variant.
- **`print_check` gives the smallest scale** (`SCALE`, `min_scale`, `min_dims_mm`): makers
  rescale in the slicer, an STL carries no unit, and the walls shrink with it. The scale
  under which 1 % more of the area falls under the floor — the windmill's body 40 %, the
  lighthouse 67 %, the teapot 67 %. The hand-over gives it with the size it was modelled for.
  Always a scale of the FILE: measured on the mesh `--height-mm` had scaled, the walls already
  thin there were excused and the floor moved with the model — the lighthouse read at 55 %
  said 43 % instead of 67 %, a 2 mm plate read at 200 % said 20 % instead of 40 %. A height
  under it is now a warning.
- **`tools/fit_coupon.py`**: the test print for a joint — a plate with one diamond hole per
  clearance (0.1 / 0.2 / 0.3 mm a face) and one with a 0.5 mm lead-in chamfer on the bed face,
  and the peg on a wall, printed as on the model. About 20 minutes on PrusaSlicer's default
  profile; both parts PASS `print_check`. 11 checks read the sizes back from the STLs.
- print.md: a hole that opens on the bed gets a 45° lead-in chamfer (the first layer's
  "elephant's foot" closes its mouth), and a mesh is for decorative objects, not mechanical
  parts — a CAD tool is named for those.
- **README § 3D printing**, with the windmill (preview and parts), the teapot against its
  museum photo (CC BY 4.0), and the before/after drawn from PrusaSlicer's G-code by
  `examples/print/flatten_demo.py`, which rebuilds it from the committed windmill.

### Added — Kiln Studio: four more themes

- Forge (warm charcoal, ember orange, a few embers drifting behind the model: CSS on the
  compositor, none with reduced motion), Neon (deep violet, cyan, magenta), Studio (soft
  light) and Minimal (greys and the accent picked in Settings), from the design boards.
  "To check" has its own colour token, so it stays apart from the accent where a theme
  wants it to. Every text pair in all seven themes reads at 4.5:1 or more (measured in the
  browser; Dark's muted grey and Light's accent and chips were darkened to get there).

### Fixed — Kiln Studio v1, after a first try

- No blink when a side panel folds or unfolds: the view is drawn in the same callback as
  the resize (screencast of six toggles: 43 of 118 frames blank before, 0 of 117 after).
- The notes panel's fold chevron keeps its own 28 px; tab labels shrink first.
- Sora and JetBrains Mono ship in `studio/static/fonts/` (78 kB, SIL OFL): the page's only
  outside requests are three.js from jsDelivr.
- The Create command is `/kiln …`, like every other command the page shows.
- `SKILL.md`'s `allowed-tools` names the four kiln-studio MCP tools as Claude Code calls
  them (`mcp__plugin_blender-kiln_kiln-studio__get_selection`, …), and says when to ask
  `get_selection`.
- The bottom bar fits the view: the shading buttons become one list, the display toggles
  fold into Options, then the bar wraps; between 761 and 1100 px the side panels are 250 and
  336 px. Measured at six widths, in English and French, in the three themes: 36 of 36 fit.

### Added — kiln-studio, an MCP server: what the user is looking at

- The plugin declares an MCP server, `kiln-studio` (`plugin/.mcp.json`, `studio/mcp_server.py`,
  standard library, stdio). `get_selection`: the model, stage, camera (Blender frame) and
  note the open Studio page shows, which the page now reports to the server. `get_notes`:
  an asset's notes with the pinned point, the camera and the pictures' paths.
  `reply_to_note`: answer a note, never "resolved". `set_camera`: turn the page's view to a
  preset, a note's view or a Blender position and target, opening another model if asked.
  Read-only otherwise. A seeded test drives it over stdio against a running Studio: 59 tests.

### Added — Kiln Studio: Create and Import

- **Import:** drop a GLB, glTF, FBX or OBJ anywhere on the page, or pick it: it is saved into
  `imports/` (a glTF or OBJ with its buffer, materials or textures: `imports/<name>/`),
  never over an existing file, and opens. `POST /api/import`, the file's bytes, 512 MB at most.
- **Create:** a form (brief, type, target, style, optional reference photo, brought down to
  2048 px) writes an open request into `.kiln-studio/requests.json` and gives the command to
  paste: `/kiln <brief>, type …, for …, <style>, reference photo … (Studio
  request q_…)`. `studio.py requests` lists them, `studio.py request ID --status done --asset
  A` closes one. The welcome now offers Create, Import and See an example. 57 tests.

### Added — Kiln Studio: a welcome for an empty project

- An empty project opens on what to do first, and on what Studio can see of the setup:
  Blender (found at PATH, `$BLENDER` or the usual folders, with its version), the Blender
  MCP connection (always "unknown": Studio says whether Claude Code is set up for one and
  whether the add-on answers on port 9876, and that only Claude can say it is connected),
  and SkinTokens (`tools/autorig.py status --quick`, "unknown" in a kiln without it).
  `GET /api/status`.
- **See an example** copies kiln's own gallery barrel (2,202 triangles, 112 kB, MIT, built
  by `examples/gallery/build.py`) into `kiln-example/barrel/` and opens it. 55 tests.

### Added — Kiln Studio in French, numbers in the reader's format

- Every word on the page goes through one dictionary: English, and French
  (`static/i18n/fr.json`); Settings picks the language, the browser's by default. Numbers,
  sizes and lengths follow it: `44 784 tris · 1,95 Mo · 0,40 m` in French. Note text and
  Claude's replies are left as written.
- `checks.py` now builds each finding from a code and its parameters (`MESSAGES`), so the
  page writes the sentence in the user's language while `studio.py checks` keeps its
  English, rendered from the same codes (unchanged on the seven test-project models and on
  31 synthetic findings, but the dimensions line, now `0.21 m × 0.21 m × 0.43 m`).
- `test_studio.py` fails when a string reaches the page without its French, or a check
  code without its translation: 53 tests.

### Added — Kiln Studio: themes, and states that do not rely on colour

- Three themes in Settings: Dark (the approved design), Light and High contrast, and an
  accent colour (cyan, blue, pink, lime) toned for each theme. Every colour on the page is
  a custom property; the words over the 3D view follow its background, not the theme.
- Each state reads by shape or word as well: a work dot is a ring, a disc with a halo or a
  tick; a check is ✓, i or !; a pin is solid, ringed, hollow or dashed by status; counts to
  check carry a ✓.

### Added — Kiln Studio: settings, the user's and the project's

- **Settings** (the gear under the list, or ⌘K), in two parts. *Personal*, kept in this
  browser only: rows Normal or Compact, the shading and the view a model opens in,
  lengths in metres or centimetres, fixed pins hidden or not. *Project*, in
  `.kiln-studio/config.json`, shared with Claude: `live_view`, `auto_open`, `target`
  (`web`, `desktop` for Unity/Unreal, `print`) and `exclude`. The skill reads them as
  CONFIG's defaults (`references/studio.md` § 9); `studio.py open` leaves the browser
  closed when `auto_open` is false; `studio.py config [KEY=VALUE ...]` prints or sets them.
- The project's `target` sets the checks' limits for a model whose production log names
  none: `desktop` raises the texture cap to 2048 and drops the compression warning,
  `print` sets no triangle budget and makes textures and compression notes. A log's own
  target still wins. Unknown keys and bad values are refused; keys Studio does not know
  are kept. `test_studio.py`: 49 tests.

### Added — Kiln Studio: every command by name (⌘K)

- ⌘K (Ctrl+K), from anywhere on the page, even while typing: the commands that apply now,
  each with its key (46 with a model open), filtered on every word typed; Enter runs the
  one picked, ↑ ↓ move. Typing a model's name opens it. `?` still lists the keys.

### Changed — Kiln Studio v1: the approved design

- The page is the prototype approved for v1 (`kiln-3.0/studio-prototype`), on the real
  project: side panels that resize the view and fold into 60 px rails (`[` `]` `\`), the
  view fitted again after they move; on a narrow screen they lie over the view. The list
  header holds in 90 px (measured, 1440 × 900): search, a View menu (Folders or State,
  Normal or Compact), one row of tags, four counters that filter (To check, Open, Claude
  works, Building), and the work line while a run shows. In Folders mode rows stay put and
  flash when they change; in State mode they move (FLIP), deferred while the pointer is
  over the list ("2 changes · re-sort").
- **Compare** is a divider across one view (one camera) or side by side, with the change
  in triangles, file size and height read from both files (cat, final against original:
  +1.63 MB, +508%).
- **Pins stick to the surface.** A pin on a skinned mesh is kept on the bone under it
  (`anchor.node`, `anchor.local`, beside `point`) and follows the animation; on any other
  mesh, on the mesh. Picking and "behind the model" ray-cast the mesh as posed (a posed
  copy of each skinned mesh, refreshed a few times a second while it plays).
- History is one feed, newest first; a note's **View** opens the before and after large
  with a slider and both close-ups. Note pictures are widened to the card's 4:3.
- Keys follow the prototype: `[` `]` fold the panels, so shading moves to `S` / `⇧S`;
  `↑` `↓` change model (`J` / `K` are gone: `K` is the bones).

### Changed — Kiln Studio: note pictures, a third of the size and sharper on the spot

- A pinned note keeps two pictures instead of one: the view, cropped to the model and
  the pin (1024 px at most), and a 640 px close-up rendered nearer the pin along the
  line the user looked at it, so a detail pinned from far away is still readable. WebP,
  JPEG where the browser cannot write WebP (Safari): 26 kB for both against 60 kB for the
  old 1400 px JPEG, measured on the same view, and about half the image tokens when
  Claude reads them. A whole-model note keeps the cropped view only (14 kB).
- The pin is marked by four ticks around it, not a ringed dot on it: the spot stays visible.
- The note stores the crop and the close-up's camera (`view`), so the "after" render
  frames both pictures the same way. The card shows the close-ups; enlarged, each view
  has its close-up in the corner, and a click swaps them. `studio.py show` prints the
  close-up's path. Notes made before keep their single JPEG. `test_studio.py`: 44 tests.

### Changed — Kiln Studio: Checks in plain words, with the fix

- Every check says what it found and why it matters ("Floats 0.200 m above the ground:
  it will hover when placed in a scene"), without kiln's rule numbers or phase names, then
  **How to fix**: the command to run for that model (`/kiln optimize barrel`, copied on
  click) or what to ask Claude. An **Ask Claude** button opens a note on the model with
  the request written out; `/kiln studio` picks it up. `studio.py checks` prints the fix
  under each line. Licence entries read "credit the author", "not for commercial use".
- Compression is a note, not a warning, when the log's target is Unity, Unreal or PC:
  the engine packs the file on import, and Draco and WebP are web formats.
- `/kiln optimize` takes a Studio asset name and works on its `_final` file.
  `test_studio.py`: 43 tests.

### Added — Kiln Studio: what kiln is working on

- **A dot per model while a command works on it.** `studio.py work start <asset>...
  --label "…"` names the models a command will change, in order; `work next` moves on;
  `work begin`, `work done` and `work end` cover out-of-order work and stopping early. The
  run lives in `.kiln-studio/work.json`; the server streams it, and the page puts a dot
  on each model in the list — a ring while it waits, breathing while kiln is on it, green
  when done — with "Kiln · optimize · 1 of 3 · table" above the list and a toast at each
  hand-over. A green dot goes once the user opens that model (or leaves the one they
  watched finish); **Clear** takes them all; the run goes with the last one. A run with
  no word for two hours stops showing work in progress. `/kiln studio` and the standalone
  commands report their models when Studio is running; not in batch runs.
  `test_studio.py`: 42 tests.

### Added — Kiln Studio: watch it built, check it

- **Live view.** While kiln builds, Kiln Studio opens the model and reloads it after each
  phase. `studio/blender_live.py` runs inside Blender, appended to the phase's last
  `execute_blender_code` call: it exports `<name>/<name>_live.glb` (hidden name, then moved
  into place) and records the phase in `.kiln-studio/assets/<key>/live.json`.
  `studio.py live <name> --end` closes the build and removes the export. The page shows
  the phases above the model and a "building" mark in the list, follows the newest stage,
  refits the view as the model grows, and files each live version in History under its
  phase, with a render. Studio now starts once the brief is confirmed.
- **Checks tab and `studio.py checks`**: triangles against the detail tier's soft range
  (WARN only past twice the top, rule 4), size against the usual height of a chair, table,
  door or character, ground contact and centring, texture sizes (read from the image
  headers in the file) against the target's cap, Draco/meshopt and WebP/KTX2 on `_final`
  only, and the licences in the production log (CC-BY: credit; NC: WARN). Without a log,
  the tier and type are assumed and the check says so.
- **Fidelity beside the model**: `tools/fidelity_check.py` also writes `fidelity.json`
  (with the model's hash, the view, elevation and azimuth) and appends a line per run to
  `fidelity_log.jsonl`. With `--out <name>/review/<view>/`, the Checks tab shows the IoU
  and its rounds, whether the measured file is the current one, the overlay or the
  side-by-side, the ranked gaps, the per-band widths, the joints, and a Photo's view
  button. `test_fidelity_check.py`: 29/29.
- **Batch token estimate**: in a batch folder, the wizard's formula read off
  `batch-manifest.yaml`: the asset's, the batch's and what is left to run, ±50%; the
  batch's range on its folder header in the list.
- **Eye button for the pins**: the toolbar's Pins toggle is now an eye floating under the
  model's name (crossed out while hidden, P still works), shown only when the model has at
  least one pin in the notes being listed.
- **Which pins**: hovering the eye unfurls two choices under it: *Hide fixed pins* hides
  the blue pins Claude has addressed (and the grey ones when all notes are listed), *Hide
  pins behind the model* hides those on its far side instead of fading them. A dot on the eye
  while either is on; the note picked in the list keeps its pin.
- `test_studio.py`: 36 tests (live stage order, build record, CLI target, image headers,
  health on shipped and unshipped stages, fidelity by hash, manifest estimate, events).

### Added — Kiln Studio

- **`/kiln studio`: a local page to look at models, pin notes on them, and iterate with
  Claude.** `studio/studio.py` starts it on the project's folder or reuses the one
  already running, like `remotion studio`; Python standard library, three.js 0.186.1
  from jsDelivr. Every `.glb .gltf .fbx .obj` under the folder shows up, and kiln's
  `_original`…`_final` stages are one model with switchable stages; the output or batch
  folder is the default category, and categories and tags can be set.
- **Notes** pinned on a spot record the point and normal in glTF and Blender
  coordinates, the object, mesh and material hit, a region in words, the camera and a
  screenshot; whole-model notes record the view. `open` → `addressed` (Claude, through
  `studio.py reply`) → `resolved` (the user only; the CLI refuses it) or `wontfix`.
- **Before and after per note**: when a note is marked addressed, the page renders the
  note's own view of the new version beside its screenshot. One previous copy of each
  annotated model is kept (the version the review pass started from) for a side-by-side
  Compare and an undoable revert — never a pile of copies. History lists every version
  seen with its size and triangle count, the changelog, notes and replies.
- **The page** follows the files live (server-sent events): a re-export reloads the
  model in place, Claude's replies appear as they are written. Shading Lit, Unlit,
  Clay, Normals, UV checker and Faces (back faces red); wireframe, grid with the front
  marked, bounds in metres, bones, animation clips. Draco, meshopt and KTX2 decode.
- `plugin/studio/test_studio.py` (20 tests: scan, stats, notes, history, baseline,
  HTTP API including host and origin checks) runs in CI; `verify_docs.py` now checks
  `studio/` paths too.

### Changed

- `fidelity_check` refuses a reference with no transparent pixel: measured as it was, a
  photo's table counted as object (0.62 instead of 0.93, exit 0).
- The cleanup's 0.1 mm merge is skipped for a model built closed — it broke a printable one.
- Rule 7: a phase is not done until its log says so — three runs had left it at BRIEF.
- Rule 16: never save over the user's open Blender; build headless when it holds their work.

- **The showcase chest is rebuilt** by its own script, `examples/animation/chest.py`: planks, a
  barrel lid of staves, iron corners, bands, rivets, handles, lock and hasp, a heap of gold inside,
  textured with two Poly Haven CC0 scans it downloads at run time. Three bones (body, lid, hasp),
  every sign measured, an exact 4 s loop. The export now fails loudly if a texture is lost on the
  way, which a relative image path did silently. `props.py` keeps the lamp.
- **AI generation is optional, and Hunyuan3D is no longer proposed first.** The default
  stays Claude scripting Blender — no AI model, nothing to install, and a missing 3D
  backend is no longer reported as a gap. When the user picks AI, kiln proposes the
  free `microsoft/TRELLIS.2` Space (MIT), then `trellis-community/TRELLIS` (MIT), then
  `stabilityai/TripoSR` (MIT; RUNTIME_ERROR on 2026-10-09). Hunyuan3D — Space, local or
  MCP native — stays available on request only: its `LICENSE` does not apply in the EU,
  the UK or South Korea, and kiln quotes that and asks before any call. "MCP native
  (recommended to start)" is gone: it only reaches Hunyuan3D and paid Rodin. Default
  Space, `/kiln models`, the batch manifest (`method: ai`; `hunyuan3d` still read) and
  the manifests' descriptions follow.
- **The TRELLIS.2 Space removes backgrounds with RMBG-2.0 (CC BY-NC 4.0)** unless the
  image already has an alpha channel — read in its `app.py`. The reference says to send
  a cut-out, or to use the TRELLIS Space, whose `rembg`/U²-Net chain is MIT/Apache-2.0.
- **What three isolated print sessions found unclear, contradictory or silent** (a 90 mm
  windmill, a 50 mm lighthouse, a 70 mm forge from the logo, 2026-10-13), each fixed where it
  was read:
  - `print_check` no longer counts a face modelled at 45° as an overhang (it reads 45.0x° in
    an STL: every overhang the windmill, its sails and the joint's peg reported was one), and
    never says a bare "supports": the line says what the slice said — "sliced clean without
    supports: none needed" on the lighthouse and the forge;
  - auto mode does not wait for the measured clearance: 0.2 mm a face, the coupon next to the
    model, said unmeasured in the hand-over;
  - the height asked is the assembled object's — the windmill left its sails out and stood
    ~120 mm for "~90 mm";
  - a lathe is closed by flat caps, not axis points, when it is engraved after: an EXACT
    engraving re-cut the pole and left a non-manifold edge;
  - the peg goes on the steadier part (a flame on its own 4 × 4 mm peg: low bed adhesion);
    an engraving's depth is its shallowest point's on a round wall; an object hidden from the
    render exports an empty STL with no error; touching pairs count as self-intersections;
    the face measure is blind on an illustration;
  - rule 10's merge is skipped in print mode, as the checklist already said; the lighthouse
    is no longer an example of architecture to send to AI; print has no `_original.glb`, its
    `--reference` is one `{name}_{part}_parts.blend` per printed part; STLs are named
    `{name}_{part}.stl`; the preflight points to rule 23.
- **What the two sessions after those fixes still found** (the windmill again at 90 mm, now
  sails included — 90.0 mm assembled; a mushroom house never named in the docs):
  - **`tools/review_renders.py`**: the review renders when no Blender is connected — matcap
    and colour, two opposite three-quarters, top and under, each view fitted to the vertices
    as its camera sees them, close-ups at the check's thin spots; an empty frame is an error.
    Every session had written its own; one framed on bound_box and misread 90 mm as 104.8;
  - `print_check`'s JSON says where the thin walls are (`thickness.thin_at`: centre, wall
    read, thinnest first) — print.md asked to look at them and nothing said where;
  - `fit_coupon.py --shape round`: round holes and a round peg standing up, the joint a cap or
    a flame makes, faceted so that the joint is never tighter than asked;
  - one `--reference` per printed part (the tool reads every mesh of a .blend); `--height-mm`
    scales, and is never the brief's height; a lathe is not JOINED on its own edges either;
    paint regions are decided without a photo too; rules 1 and 24 say what to do headless;
    the `.blend1` files are deleted, or `save_version = 0` (checked) stops them;
  - the Blender workflow now also runs on a change to `flatten.py` and `fit_coupon.py`, which
    it tested but did not watch.
- **What a Christmas tree found after that** (two parts, the star in its own filament on a
  peg, 70.0 mm assembled; the session used `review_renders.py` and one reference per part
  unprompted):
  - `print_check` no longer counts triangles that only TOUCH as self-intersecting — a shared
    vertex, a vertex lying on a face: each is shrunk 0.1 % and tested again. The windmill's
    sails read 32, a forge's flame 2, the joint coupon at a 2.5 mm peg 4; all now 0, and a
    cube with a corner pushed through its bottom still crosses itself;
  - `print_check --brim-mm`: a tall part on a narrow foot read *Low bed adhesion* (the flame,
    the tree) and both sessions checked a brim in PrusaSlicer by hand; the warning now names
    the option, and the tree passes clean with 5 mm;
  - a region the brief does not name gets its paint edge too; a small cut proves little
    against its reference; part names may be in the brief's language; the scripted print's
    checkpoints.
- **Fewer supports and no long bridges, as rules** (two boxes with lids, 2026-10-13): both
  printed with no support, but one bridged a 20 mm flat ceiling and filled 10 mm of its own
  cavity to keep the bridge that short, the other printed a raised pattern face-down. Rule 5:
  each part's orientation is a logged decision — zero supports, then the fewest and shortest
  bridges, then the visible faces off the bed. Rule 6: a flat ceiling past ~10 mm becomes a
  45° cone or vault, never a filled cavity. Rule 7: relief goes on faces that print upright or
  up. `print_check` turns PrusaSlicer's *Long bridging extrusions* into that instruction.
  A session without context then made a bayonet box under those rules: no support, no long
  bridge, every orientation logged. What it still met, now written: a ceiling too wide for the
  part's height starts its 45° vault from a ring inside the wall; test pieces go in `test/` as
  `test_{what}.stl` (a user took two test rings for parts of the box); `review_renders.py
  --close` reads negative coordinates as a value.
- **Stylised figures: metaballs, not a refusal.** Print mode had refused an animal, a person or a
  character since two cats passed every check and were unacceptable to look at. Then a colleague, on v2.2 — no print mode at all — asked for a cartoon dragon from one
  flat drawing, for a multi-colour printer: the session built it from metaball families and one
  voxel remesh, cut it into four colour parts with flush inlays, and wrote how to slice it, in 23
  minutes. The cats had metaball ellipsoids too, but cone ears, exact unions and a photo to
  match; the dragon had one family per region, one remesh, and a drawing. So the line is drawn
  between a stylised figure and a realistic likeness, not between subjects. `print.md` § Figures writes that
  method down — ten times the size (metaball resolution stops at 5 mm, checked), one family per
  region, an element's visible radius 0.574 × its radius (measured), thin parts as meshes, one
  remesh, colours by priority — and the scope sends a stylised figure there.
- **`print_check` checks an assembly**: several files, one per colour, are each checked closed,
  their overlap measured, and their union checked as one object with the slicer. Each colour of
  that dragon alone FAILed three times out of four; the assembly PASSes (union 68.4 cm³, 68.2
  measured by its session with another library; overlap 0).
- **A fresh session, given only the skill, made a cartoon fox** from a text brief: metaballs, four
  colour parts, the assembly PASS (with supports and a 5 mm brim). What it found unclear is now
  written: "remesh last" is about the shape, a figure's colours are cut after it; one voxel
  range; scaling a ×10 model back before export; the figure's reference is the solid before the
  colour cut; parts never meet vertex to vertex; metaballs in a row swell to 0.715 × r, not
  0.574 (measured); colour renders need the GLB. `print_check` no longer says "none needed"
  next to PrusaSlicer's *Floating bridge anchors*: it says to check with `--supports`. And the
  hand-over of a colour figure is a `PRINT.md` next to the STLs — a user looking at the four
  files asked how the scarf would get round the neck.
  An assembly's `SCALE` is now its thinnest part's: the fox's union said 20 %, its orange part —
  thin walls between the inlays — 80 %, and the line names the part.
- **What eight web and animation sessions met everywhere** (owls, dogs, a corgi, 2026-10-14):
  - the creation tree settled "cartoon → scripted" against "character → AI": a character's
    style decides, and a stylised one is scripted as ONE skin, not parts glued on;
  - a quadruped is rigged with a hand-built Mixamo-named skeleton: Rigify's quadruped metarig
    has 34 bones named `spine`, `front_thigh.L`… (checked; the table said 46) and
    `tools/quadruped.py` reads Mixamo names only. The T-pose rule is for bipeds;
  - the detail tier sets the triangle budget, the platform table is only the default; a brief
    that lifts the limit is not proposed a reduction; a reduction the brief asks for is logged;
  - `uv-materials.md` passed `angle_limit=66.0  # degrees`: the operator takes radians (checked:
    default 1.152, max 90°), so it asked for 66 rad;
  - `review_renders.py` left out the 2 m sphere a rigged glTF brings for its bones (a dog was 2 %
    of the frame) and shows textures in colour (a textured body rendered grey).

### Measured — what did not make it

- **Living subjects in print mode**: a cat held by a ghost, then a real cat from its photo,
  both PASS and both rejected on sight. Primitives cannot make an animal; no rule closed it.
- **A single recipe for bad edges after an export**: triangulating before export fixed it
  twice and caused it once. The rule is to check the STL after each risky step.

## [2.2.0] — 2026-10-07

### Added — `/kiln animate`

- **Animate a rigged asset without the full pipeline**: `/kiln animate SK_Cat.glb walk, idle`
  or `/kiln animate dragon.glb "flaps its wings"`. It runs 2.1's PHASE 5d on its own:
  inspects the rig and folds bone-parented parts into the skin, stops on a rig too
  coarse to bend where asked and offers PHASE 5c, offers the asset's own clips first,
  then routes by subject — `tools/quadruped.py` for a quadruped's idle and walk, UniMate
  for bipeds and winged creatures (status checked, non-commercial weights stated, label
  review kept), keyed parts for articulated objects — and shows every kept clip before
  exporting.

## [2.1.0] — 2026-10-07

kiln now **animates** what it rigs — routed by subject, because no single method held up
across all of them. Every route below was measured on real rigs, and every scripted
cycle went through review until it read as a real animal or object.

### Added — PHASE 5d ANIMATE, routed by subject

- **`references/animation.md`**: the routing table, the measurements behind it, and
  seven rules for scripted animation, each a cycle that looked wrong until measured —
  drive a bone in its own rest frame (a cat's `Hips` lies along the body: a "vertical" bob
  moved it 1.8 cm forward and 1 mm up), solve the IK pole angle from the rest pose (a
  guessed −90° turned the elbows forward), keep legs ≤ 95% of their length (the rejected
  walk peaked at 101%), measure a rotation's sign before using it, loop exactly, judge
  motion in motion and in numbers, hold paws level.
- **`tools/quadruped.py`**: scripted idle and lateral-sequence walk for a quadruped,
  IK-planted, baked to FK. It measures the clip before writing it, shortens the stride
  until the legs stay bent, and reports the root speed the planted paws share (0.106 m/s
  on the showcase cat, the four paws in exact step).
- **UniMate**, text-to-motion for any skeleton ([Friedrich-M/UniMate](https://github.com/Friedrich-M/UniMate)),
  for bipeds and winged creatures. **`tools/unimate.py`** installs it at the commit and
  checkpoint kiln measured (`status`, `setup`, `setup --update`, `drift`, `animate`),
  3.2 GB; `tools/unimate.patch` (73 lines) runs it on Apple Silicon and on Blender 5 —
  upstream supports NVIDIA only. 18 s per clip on an M4 Pro. Its checkpoints are
  **CC BY-NC 4.0**, said wherever the route is offered.
- **`tools/motion_loop.py`**: generated clip → seamless loop, keeping the sample that loops
  best. Seams measured against the local frame step: 2.1-9.7x raw, 0.5-1.2x looped
  (12 clips). It refuses still stretches and requires the same direction through the
  seam — a swing matched its mirror image on the way back until it did.
- **`tools/bind_rigid_parts.py`**: bone-parented parts (a dragon's eyes) folded into the
  skin at rest pose, so skin-only pipelines keep them — read posed, the eyes landed
  1.5 m off the face. It also reports a quadruped posture, right on 6 rigs.
- **The animation showcase** in the README: a villager walking and jumping and a dragon
  flapping (UniMate, the looped sample kept out of 4, approved on review), a cat walking
  and idling (`quadruped.py`), a desk lamp and a chest modelled, rigged and keyed by
  script. `examples/animation/showcase.sh` rebuilds all seven, at 720 px (1.6 MB
  together).
- **`.github/workflows/unimate-drift.yml`**: weekly, checks kiln's patch still applies to
  UniMate's upstream HEAD — the project changed its pipeline, checkpoints and licence
  within days of kiln first measuring it.

### Measured — what did not make it

- **UniMate on quadrupeds: unusable for walking** on a cat, a Shiba, a horse and the
  model author's own Go2 example; same result with upstream's adaptive solver, so the
  fixed-step shortcut was ruled out. `unimate.py` recognises a quadruped and refuses it
  unless `--force`.
- **Prompt wording**: "walks in place" 8 of 8, "walks forward" 0 of 8 — it slides with
  the feet still.
- **MoCapAnything V2** (video → motion, MIT): excellent on rigs from its own training set,
  unusable on two from outside it. Not shipped.
- **Scripted trot, jump, sit and attack** for quadrupeds: rejected on review. Quadrupeds
  keep their own clips or hand keys for those.

### Changed

- **Rule 10's weld keeps the shading.** A plain merge re-smoothed a faceted low-poly cat
  (26.7% → 94.5% of face corners bent > 5°), and merging before applying an object scale
  of 100 deleted 108 of 928 faces. The weld now applies transforms first and gives each
  corner its old normal back: unchanged to 0.05°, through `normals_make_consistent` and
  a glTF round trip (`references/validation-checklist.md` § Merge by Distance).
- **Rigs are weighted on the welded mesh** (rule 26, PHASE 5c). Weighted with its split
  edges, the same cat tore 12.5 cm open at the first pose — 2,798 vertex pairs pulled
  apart. `references/characters.md` § Animation-ready skeleton: joints at the bends,
  Mixamo-style names (UniMate's offline labeller read 24 of 26 directly), a measured pose
  test.
- **The gallery's CLEANUP follows the new weld.** Measured on all 15 builders first: their
  shading is unchanged either way (no split edges), and the regenerated gallery matches
  `docs/gallery.md` row for row — 21,879 tris, 1456.2 kB raw → 132.7 kB.
- `verify_blender.py` gains four checks, all on synthetic rigs built in the check: the weld
  (a split tube tears 1.6 cm, 0 welded; shading kept), the quadruped walk, rigid-part
  folding with the posture test, and loop extraction (a 13-frame swing cut at 48 frames loops back to
  exactly 39).

## [2.0.2] — 2026-10-02

### Changed — an install downloads 0.7 MB of skill, not 46 MB of repository

- **The plugin now lives in `plugin/`**, and the marketplace's source points there
  (`"source": "./plugin"`, documented). Measured in a clean Claude Code profile, a 2.0.1
  install held the whole repository twice — a 30 MB marketplace clone and a 16 MB plugin
  copy, 11 MB of it benchmark results — for a skill that needs `SKILL.md`, `references/`
  and `tools/`.
- **The bench's published results moved to the `bench-results` branch**, history kept
  (`git subtree split`); `docs/benchmarks.md` links there. Locally, `bench/results/` is a
  worktree of that branch.
- **Standalone clones keep working**: the repository root links `SKILL.md`, `references`
  and `tools` to `plugin/`. On Windows, git needs `core.symlinks`, or install as a plugin.
- **For contributors**: the checks run as `python3 plugin/tools/verify_docs.py` and so on;
  `verify_docs.py` resolves the README and repository files against the repository and
  the skill's docs against the plugin, and checks the source folder holds a `SKILL.md`
  and a `plugin.json`. The bench copies `plugin/` into each sandbox.

## [2.0.1] — 2026-10-02

### Changed

- **The plugin's description says what 2.0 does.** The manifests still described 1.x —
  "from text brief to optimized GLB", Hunyuan3D only — in the `/plugin` menu. They now
  name the photo method, the CC0 scans, the local TRELLIS.2 templates and both MCP
  servers. No change to the skill.

## [2.0.0] — 2026-10-02

kiln now rebuilds an object **from a photo** — read in crops, textured from CC0 scans,
measured against the photo and checked joint by joint — and runs on both Blender MCP
servers, the Blender Foundation's official one included. Every claim below was measured by
a new quality bench that scores each rebuild against the real 3D asset it was photographed
from: shape **0.830 → 0.897** (lantern), **0.854 → 0.950** (ammo box), **0.445 → 0.750**
(gothic chair); text briefs ship **32.9 MB → 0.96 MB**. The method, what each fix broke and
how the bench was kept honest: [`docs/benchmarks.md`](docs/benchmarks.md).

### Breaking

- **`_final.glb` is compressed by default.** The OPTIMIZE phase now runs in auto mode
  with the glTF preset: Draco geometry and WebP textures (`KHR_draco_mesh_compression`,
  `EXT_texture_webp`). A loader needs a Draco decoder and WebP support — three.js through
  `DRACOLoader`; check your engine's glTF importer. `_final.glb` is written only after
  this phase.
- **The triangle range is a guide, not a cap.** Up to twice a tier's top is kept and
  reported, with where the triangles go; a reduction is proposed only past that (batch
  mode decimates to the tier's top, not its midpoint). The same tier ships heavier assets
  than 1.x did when the detail is visible.
- **Rule 6 now covers thin parts**: wires, bails and loops are rebuilt as curves, never
  decimated — a generated mesh with thin parts is no longer simplified as a whole.

### Upgrading from 1.x

- **Need uncompressed files?** `_original.glb` is still written next to `_final.glb` —
  ship it if your loader cannot decode Draco or WebP — or run in guided mode, where the
  optimization is proposed and can be declined.
- **Want a tighter budget?** Give the triangle count in the brief: a reduction to it is
  proposed, with before/after (rule 6 asks before any decimation).
- **Nothing to migrate** in commands, the brief format, the output layout or the log —
  `/kiln`, `/kiln setup`, `/kiln cleanup` and the rest are unchanged.
- **Optional**: Blender 5.1+ to use the official Lab MCP; a free local TRELLIS.2 setup on
  Apple Silicon (24 GB) for 3D templates — see `references/ai-generation.md`.

### Added — a quality bench, and a baseline to hold every change against

- **Nothing had measured an end-to-end `/kiln` session.** `bench/` runs the skill
  headless on six fixed briefs, one per pipeline path, and measures each shipped
  GLB after re-importing it — topology, grounding, surviving textures, rig
  structure, and a deformation probe that sees a rig which validates yet produces
  mush. Baseline on 1.1.2: `bench/results/baseline-2026-09-29.md`.

### Changed — concept art no longer depends on Pollinations

- **Pollinations answers HTTP 402 `Payment-Required` after one image** (measured
  2026-09-29), and the session then painted over its watermark. The default is now
  the `black-forest-labs/FLUX.1-schnell` HF Space: Apache-2.0, same `gradio_client`
  venv, 5.6 s for a 1024×1024 image, no watermark. `references/ai-generation.md`
  gains the concept-art section `SKILL.md` had been pointing at all along.
- **Rule 5** now says a 402 means switch source, and forbids removing a watermark.

### Added — the official Blender Lab MCP, and PolyHaven without an integration

- **Kiln runs on the Blender Foundation's MCP** — the server behind Claude's Blender
  connector. Measured: 1.1.2 shipped the same 7 GLBs on it for 10% less. `SKILL.md`
  now maps its tools one by one, gives the setup facts that each cost a failed start
  (the add-on's `5.1.0` floor, online access, a package name that collides with
  ahujasid's on PyPI), and says *when* to capture on it — its sessions took one
  screenshot each.
- **PolyHaven's public API**, for a server with no PolyHaven tools: endpoints
  verified live, and what its Terms of Service require that the sessions had not
  done — a unique User-Agent and a visible credit.
- **The Khronos validator after every export**, through the already-required
  `gltf-transform validate`: exit 1 on a seeded broken GLB, exit 0 on all 16 bench
  GLBs. It checks the format, not the mesh.

### Added — measuring a model against its reference image

- **`references/reference-fidelity.md`**, for scripted modeling from an image: a detail
  inventory, the silhouette measured from the pixels, a surface-to-surface attachment
  check, materials sampled from the image, and two review rounds at most.
- **`tools/fidelity_check.py`** renders the model front-on as a silhouette and under a
  Poly Haven studio HDRI, and prints the gaps against the reference, largest first:
  silhouette IoU per height band, widths, and per band luminance, saturation, warmth,
  highlights and texture detail. It reproduced the bench's hand analysis (IoU 0.713
  and 0.772 against 0.717 and 0.773). Judging by eye, sessions over-corrected twice —
  too bright and blotchy, then grey and flat at half the reference's saturation.
- **Texture and wire techniques read from an image-to-code tool's own output**: wires
  traced from the pixels (a bail within 0.7 mm of its hand-measured points), a three-tone
  palette per region, independent colour / roughness / relief fields with grime along a
  turned part's direction, relief baked to a normal map (glTF has no bump — measured to
  export as `normalTexture`), and a frosted-glass recipe. `fidelity_check.py` now counts
  triangles against `--max-tris` and refuses a model with unloaded textures, which had
  rendered black and skewed a measure.
- **What one photo cannot say is settled before modeling**: the real size (asked, or the
  usual size stated as an assumption — five reconstructions of one lantern came out
  23–52 % too tall), more views for an asset whose back will be seen, and the camera's
  elevation read on a rim's ellipse. `fidelity_check.py` takes `--view` and `--elevation`.
  Scored from five sides against the real Poly Haven asset, the version that best fitted
  the ~15° photo from the front was the *worst* against the object: it had copied the
  photo's perspective into the geometry, its base 30 % too tall.
- **What the lantern loop got wrong, corrected before other objects** (commit after 7 trials):
  the review no longer chases the photo score — the real object scores ~0.80 against its own
  photo, and the version that reached 0.898 was the worst against it; shape gaps are local
  (a band's width off by more than 8 %), and wire bands are judged by width, not IoU. Detail
  comes from fine features, never relief amplitude (a session made its lantern read as
  lumpy cast iron). Traced wires become smooth splines, not polylines (a bail came out
  kinked). The inventory is ticked line by line at the final review (a pentagon loop turned
  into a teardrop no number flagged). The procedure scales with the tier — the lantern's
  cost had gone from $1.90 to $3.52. The float bake and its sRGB conversion are one rule.
- **3/4 photos and openwork objects**, found by testing on a crate and a chair: the review
  camera now takes `--azimuth` as well as `--elevation`, framing by projecting the bounding
  box (a real crate against its own 3/4 preview: 0.573 level, 0.925 at 50°/20°); and
  openwork — a chair from the side, 0.12–0.16 at every orientation — is judged on
  proportions and by eye.
- **`tools/test_fidelity_check.py`** seeds the review tool, now 27/27, in the Blender CI. Its
  first run caught the views framed by height only: anything wider than tall was clipped.
- **TRELLIS.2 run locally and measured** (`references/ai-generation.md`): on an M4 Pro with
  24 GB, 5–7 min a model, 19.5–22.5 GB peak, 31 GB of weights; the best shape the bench has
  measured (0.952 from five sides, scripted: 0.861) but always 1 m tall, 160–190k triangles
  and one material. Five install fixes the project does not make, and an MIT-only run: the
  non-commercial RMBG-2.0 swapped for BiRefNet, which needed a float32 cast the lantern's
  cut-out photo never exercised. Finished by kiln it took the real asset's colour — and lost
  its thin parts to a 97 % decimation the score did not see: wires are now rebuilt, not
  decimated (a rule in SKILL.md's CLEANUP, where every session passes — the run had grepped
  the reference, not read it), and open edges are counted after.
- **Scanned CC0 texture sets before procedural noise** (`reference-fidelity.md` § 4). Two
  objects, one verdict: the geometry tools work, the surfaces do not — the crate's rust
  came out a soft orange gradient along its edges, the lantern's patina even and clean.
  Noise makes a smear where a scan has flakes, pits, runs and chips. The skill now starts
  from a Poly Haven texture set of the material family (CC0, no key; tags and thumbnails
  to choose by eye against the photo's crop), tints it to the photo's palette, wears it
  with a second set masked by the form, and bakes it to the UVs. `fetch_texture_set` and
  `scanned_layer` were run on Blender 5.2.2 against the live API.
- **Grain is information, not a gap.** Its lantern-calibrated threshold flagged the real
  crate against its own photo (22–28 %); it stays in the JSON only.
- **Every generation starts from nothing: no figure from a measured object in what a
  session reads.** The references and the review tool's own messages quoted the bench
  lantern's real values as illustrations — its height, its brass's base colour (0.30), its
  metal share, its profile errors, what each version did. Each one a session could find
  became a value it aimed at: the metal share (48 %), the height (0.294 m), and the base
  colour — v11 and v13 logged "median 0.27–0.30 (the doc's real brass is 0.30)" and came
  out light, even and clean, where the real brass's look comes from colour, roughness and
  metal varying TOGETHER. `reference-fidelity.md` is rewritten as a method (403 → 330
  lines, every snippet kept), the tools' docstrings, comments and gap messages keep their
  thresholds without the figures behind them, and the base colour comes from the photo's
  palette, with 0.15 as a floor only. The calibration record stays here and in the bench.
- **v12's lessons, kept as limits rather than more rules.** Told a joining part "sits on a
  shaped foot", v12 flared its tubes into flat tongues: a part now enters with its section
  unchanged, a foot only where the photo clearly shows one, judged against the photo's
  crop. It tackled six material problems in one round and its surface regressed (grain
  28 → 24 % of the photo's — not the WebP step, measured 28 → 26 %): one material problem
  per round now, and ageing added one layer at a time. The too-clean grain line is listed
  as information, not ranked as a gap.
- **A surface too clean for its photo is reported; widths come from the template; glass
  takes the photo's tint.** v11 fixed v10's joints and metals and overshot: one clean
  bronze read new (grain 20 % of the photo's on the tank; the real object 74 %, the
  image-to-code lantern 79 %, v10 57 %). `fidelity_check.py` now measures a band's grain —
  fine variation deep inside solid areas, over its brightness — and reports it under 28 %
  of the photo's (one truth, narrow margin: v10 sits at 31 %). Age is a layer inside the
  material: AO-darkened cavities, worn edges, pits and dents. v11 also took widths from the
  photo, whose perspective narrows (−6 %); the template now gives widths and the parts'
  positions too. And the glass: clear in v8–v11 against a near-black photo — the
  reference's own inventory example said "clear glass".
- **Joints are rendered to be looked at, and patina stays metal** — what v10 got wrong
  where the numbers said it was fine. Its air tubes ended in a flat cut resting on the
  tank's slope, touching at one point and lifting 14.6 mm across their end, while the
  inventory read "inserted"; no distance can judge it (the real tubes lift 8.6 mm under a
  sheet-metal foot), so `fidelity_check.py` renders every end of a long part that touches
  another — the two parts alone, flat grey, two views, `review/joints/` — and the rule is
  that a part joining another enters it or sits on a shaped foot. Its tank read grey
  pewter: most of the brass was painted as non-metal patina (metallic 0.20–0.38 on
  average, the real brass 0.63), and a non-metal reflects white. Tarnish now stays metal,
  darker and rougher; only crusts are non-metal; the tool warns when a metal is mostly
  painted (calibrated on one truth, said so). And one material per PHYSICAL material —
  the reference had said the opposite ("never one material for every metal part"), and
  v10's five metals read as five alloys. Round parts keep 16+ sides (its tubes, 10–11,
  read as bars); grime streaks modulate, they do not stripe (they read as wood grain).
- **A metallic mask in scattered hard islands is reported.** Lantern v9's surface came out
  as copper islands on a dark patina — the skill's dark-metal text had quoted the real brass
  as "48 % metal", and the session thresholded a noise to reach it. The number is gone; the
  rule is one worn region following the form, soft-edged. `fidelity_check.py` flags a mask
  both scattered (largest island < 50 % of the metal) and hard (< 60 % in-between texels):
  v9 on 9 of 9 materials, none of the bench's truths, v8, img2threejs or TRELLIS.2. A mean
  texel jump was tried first and dropped — it counts edges, not their hardness.
- **`tools/template_profile.py` reads proportions off a 3D template** — a generated mesh of
  the photo, a scan — to model from, never to ship. On the bench's lantern the TRELLIS.2
  mesh is within 0.6 mm of the real profile (median; 1.6 mm at worst), the best photo-read
  reconstruction 1.1 mm and 9.7 mm at worst, at the step a 15° camera hides. Seeded by
  `tools/test_template_profile.py` (4/4, in the Blender CI), whose first run caught the
  axis pulled off-centre by a tube reaching the floor. Its first example command carried
  the bench lantern's real height (0.294 m) — the answer key — and a session copied it as
  its "assumption": the example now names the argument, and the reference says where the
  real height comes from.
- **The triangle range is a guide, not a cap.** The review tool ranked any overshoot as
  its first gap, and sessions spent their review cutting round parts (a lantern at 9.5k
  for a 5k top read "90 % over" as its main defect). Up to twice the tier's top is now
  reported last and kept, with where the triangles go; a reduction is proposed past
  twice the top — batch mode decimates to the top there, not to the midpoint.
- **Dark metal is reported, and luminance is no longer something to match.** The bench's
  final lantern read near-black: 100 % metal at a base colour of 0.07–0.15, 23 % darker than
  the real object under the same light — while matching the photo's luminance to 0.003,
  because the photo's own light was darker. `fidelity_check.py` now reads the model's
  materials and reports metal below 0.15 (the real aged brass: 0.30, 46 % metallic, its rust
  painted as non-metal); luminance and highlight gaps are labelled light-dependent.
- **A float colour bake shipped black.** Measured on Blender 5.2.2 with a minimal repro:
  the glTF exporter writes a linear float base-colour image into its PNG without the sRGB
  transfer (linear 0.2 → byte 51, not 124). A lantern reviewed at saturation 0.30 shipped
  at 0.12. `to_srgb_byte()` converts first (byte 124, 0.202 back); the last review measure
  must now be of `_final.glb`, and `fidelity_check.py` warns when given a `.blend`. The
  float bake itself came from this release's own advice.
- **The camera's elevation is read, then fixed — never picked by the score.** A session
  that chose among 10 / 15 / 20° the angle its own model fitted best kept 20°, and shipped a
  base 27 % flatter than the real one. Reviews are now capped at three measures, correct
  half-way toward a target (saturation had jumped 0.17 → 0.38 for 0.33), and keep every
  working file in the asset folder — the same session had written into `/tmp`.
- **Luminance and highlights depend on the light.** The real asset, measured against its
  own preview under the tool's HDRI, reads luminance +0.05 and highlights 2.5 % for
  1.5 %; saturation held (0.33 for 0.32). Those two are now alarms, not targets.
- **The skill replies in the language of the request.** Two sessions had answered in French
  to an English brief.

### Changed — the skill now fires on files people bring, not only on assets they order

- **The frontmatter `description` decides whether kiln exists for a user**, and it
  only described producing an asset. Measured with `bench/trigger.py` on 12 prompts
  written as users write: the old one fired on **6 of 8** that should trigger it —
  it missed "shrink this 40 MB GLB" and "convert to USDZ", both of which kiln does
  — and on none of the 4 that should not. On 6 held-out prompts, written before
  the new description was drafted, it scored 3 of 4 (it missed "generate LODs").
  The new one: **12 of 12, 0 false positives in 6**. One run per prompt.

### Changed — what a Space call spends, and whose

- **The free cloud path is one or two generations a day.** ZeroGPU gives 2 minutes
  without an account and 3.5 with a free one; one TRELLIS.2 run asks 60–120 s. A call
  reserves the Space's declared duration (90 s for a 5.6 s FLUX image), and the quota
  resets 24 h after the first call, not at midnight — measured: still refused the
  next morning. A spent quota means no concept art either; the reference now lists
  the free fallbacks, a PolyHaven CC0 preview among them.
- **A Space call never uses a token silently.** `gradio_client` sends the saved
  Hugging Face token by default (`token=None`; measured). The skill announces whose
  account pays before the first call, offers `token=False`, and never reads, prints
  or writes a token.
- **TRELLIS.2 is documented as a candidate, not the default**: its Space API is
  recorded as read live — `/extract_glb` rejects a target under 100,000 triangles —
  but no generation has completed on it yet. The local Apple Silicon port is listed
  with its licences, including a non-commercial background remover.

### Fixed — what the baseline found

- **Auto mode stopped before OPTIMIZE** on 3 of 6 briefs and named the result
  `_final.glb` — a 16 MB file for a 724-triangle chair. Auto mode now applies the
  default preset for glTF, and `_final.glb` is written only after the phase.
- **Rule 2** measured at 2–4 screenshots for 6–17 edits; it is now anchored to
  phases, with two opposite angles after texturing — a UV defect on one crate
  corner passed every count.
- **Rule 6**: the untouched factory Cube is removed and logged; anything else is
  hidden, never deleted. Runs had done both.
- **`gradio_client` 2.7.1 returns the Hunyuan3D mesh as a dict**; a `gradio_path()`
  helper unwraps both shapes. The Space's textured endpoint fails server-side
  today (`NameError`), and the reference says so.
- **Rigs, measured on Blender 5.2.2**: the glTF exporter re-parents a deform bone
  under a control bone to its nearest deforming ancestor, and binds unweighted
  vertices to a synthetic `neutral_bone` — so validate before export, not after.
- **Batch durations** are measured with timestamps, never estimated.
- **The manifold check never ran**: it was missing from the cleanup's execution
  order, and a lantern shipped 84 edges shared by 3–4 faces. It is step 5 now, and
  separates fused edges (always a defect) from open ones (fine on a leaf).
- **Web textures are capped at 1K**, as `uv-materials.md` already said. An earlier
  fix in this release had set 2K for the balanced tier, and a chair doubled.
- **The README's key-rules list** was a Markdown ordered list, which renumbers
  itself: twelve of thirteen entries named the wrong rule. It now writes
  `**Rule N**`, and `verify_docs.py` checks each entry against its rule and rejects
  an ordered list in that section.
- **The tool surface** now covers all 36 tools of `blender-mcp` 2.0.0, with what
  each costs. It had cited rule 22 for integration status and rule 23 for
  `get_object_info` — both one off after a renumbering. `verify_docs.py` now
  checks tool-table rows against the rule they cite.

### Fixed — a headless Blender crash exited 0, so a failed export read as a success

- **Blender exits 0 when a `--python` script raises**, unless it is given
  `--python-exit-code 1`. An explicit `sys.exit(1)` does propagate; an uncaught
  exception does not. Measured on 5.0.1: the same raising script exits 0 without
  the flag and 1 with it.
- **Rule 21's fallback was the exposed path.** When an MCP export times out the
  skill runs a headless export (`references/export-targets.md`), and a failure
  there came back as success. The command now carries the flag, and the reference
  says to check the exit code, then the file.
- **The Blender CI step had the same hole**: a crash outside `verify_blender.py`'s
  `try` blocks would have passed green. Run with the flag, it still reports 9/9 —
  nothing had been hiding. The flag is also on the gallery script, the usage
  docstrings and CONTRIBUTING.
- **New `exitcode` check in `verify_docs.py`**: every headless Blender command in a
  code fence, script or workflow must fail loud. Prose naming the command is left
  alone. Three cases in `test_verify_docs.py` — **21/21**.

## [1.1.2] — 2026-08-26

### Fixed — the README stated two different Blender versions, and neither was measured

- **The badge said `Blender 4.x+` while the Reproduce section said `Needs Blender
  5.x`.** Both numbers were written rather than measured: nothing in this repository
  has ever run on 4.x. The real floor is **4.4**, for a specific reason — the
  animation code reaches F-curves through `action.layers[].strips[].channelbag()`,
  and layered actions arrived in 4.4. Everything here is measured on 5.0 locally and
  5.2.1 LTS in CI. 4.4–4.5 satisfy the API but are untested, so the README now calls
  them unverified rather than supported, which is the honest word.
- **The check written to catch this took three attempts, and the failures are worth
  recording.** Matching every `Blender N.N` flagged history: "Since Blender 4.0+,
  bone layers were replaced" demands nothing of the reader. Blacklisting history
  words then silenced the check *completely*, because the genuine requirement lines
  say "verified" and "measured on" too — it passed by finding nothing at all, which
  is the worse failure of the two. It now whitelists requirement phrasings and fails
  when it finds no requirement, because a check that cannot fail proves nothing.
- **The test harness could only ever assert that a check fires.** Fourteen cases, all
  seeded regressions, and nothing asserting a check stays *quiet* — yet five false
  positives have shipped in these checkers, and a check people learn to ignore is
  worse than no check. `expect=None` now demands silence on correct input, covering
  the three this repository actually produced: a history note, an API-availability
  qualifier, and `uv pip install` tripping the bare-pip rule.
- **The two plugin manifests could disagree about the version** and nothing noticed.
  `plugin.json` and `marketplace.json` both carry it, a release touches both by hand,
  and a mismatch would install the plugin under the wrong number while every check
  passed. Now verified.

## [1.1.1] — 2026-08-26

### Fixed — the HuggingFace path had gone stale

- **The default HF Space was paused.** `Jbowyer/Hunyuan3D-2.1`, a community
  duplicate, measures `stage: PAUSED` as of 2026-08-26 — and a paused Space answers
  HTTP 200, so it looks alive. The default is now the vendor's own
  `tencent/Hunyuan3D-2` (RUNNING, 3,370 likes), and the reference carries the
  one-line check for the runtime stage. A duplicate depends on one person
  continuing to pay for a GPU, which is exactly how the old default died.
- **The pinned client version was a major release behind**, and the documented API
  flow did not match the Space. Connected live with `gradio_client` 2.6.1 and read
  the signature: `tencent/Hunyuan3D-2` exposes 12 named endpoints, of which
  `/shape_generation` (4 returns) and `/generation_all` (5 returns) matter, both
  taking the same 13 parameters. The documented two-step flow named an
  `/on_export_click` endpoint that is not among them. The reference now carries the
  measured signature and the call that prints it when something changes.
- **`randomize_seed` defaults to True** on both endpoints, which makes runs
  non-reproducible — worth knowing before comparing outputs or re-running a batch.
  Now documented.
- **A bare `pip install` had survived the whole audit in the README**, because
  `verify_docs.py` exempted anything in backticks — and a prescription in markdown
  *is* written in backticks. The exemption is gone, only genuinely correct forms
  (a venv path, `uv pip`) are excused, and the regression suite covers the case:
  **13/13**. This is the mirror of the four false positives found earlier: same
  checker, opposite failure.


## [1.1.0] — 2026-08-26

### Fixed — an API on its way out, caught by the CI's first run

- **`Material.use_nodes` is scheduled for removal in Blender 6.0**, and the docs and
  gallery scripts wrote it in sixteen places. It is already a no-op: a new material
  in 5.x arrives with a `node_tree`, a Principled BSDF and a Material Output
  already in place, and `node_tree` stays non-None even with `use_nodes = False`.
  So every write was doing nothing today and would break in 6.0. Writes removed,
  reads switched to `node_tree`. The gallery reproduces byte-identically —
  21,879 tris, 1456.2 kB → 132.7 kB — so the change is inert.
- **`verify_blender.py` now fails on any `DeprecationWarning`** that the docs or the
  gallery reach. This one appeared as a single buried line in the very first CI run,
  where it would have sat until 6.0 broke the documentation. A warning nobody fails
  on is a warning nobody reads.

### Added — the Blender half of the CI

- **`tools/verify_blender.py`** plus `.github/workflows/blender.yml`, weekly and on
  demand: eight checks that need Blender running. They cover the findings text
  analysis cannot reach — `Action.fcurves` removed in 4.4+ and the channelbag walk
  that replaced it, EEVEE attribute removals and the `BLENDER_EEVEE_NEXT` rename,
  Principled socket names, Rigify's deform-bone counts against the tiers PHASE 5c
  routes on, the IK default that makes FK controls silent, geometry nodes needing
  the modifier applied, and USDZ exporting natively into a conforming archive.
- Each check reports when a finding has gone *stale* as well as when it breaks: if
  `Action.fcurves` returns, or a Rigify rig stops defaulting to IK, the run says so
  rather than passing quietly on advice that is no longer needed.
- Writing it produced four more false positives — a bare `inputs["..."]` regex
  matched Normal Map, Mix and Material Output sockets, so `Color`, `Fac`, `Shader`
  and `Surface` were reported as missing Principled inputs. Narrowed to the
  Principled node. That is the fourth time this session the same mistake surfaced,
  which is why both checkers now carry the reasoning in comments.

### Fixed — geometry nodes, the last untested creation method

- **Iron rule 18 silently destroyed every geometry-nodes asset.** Geometry nodes
  output exists only as a modifier result, and rule 18 mandates
  `export_apply=False`, so the exporter writes the *base* mesh. Measured on a
  2,688-triangle scatter:

  | Export | Result |
  |---|---|
  | `export_apply=False`, modifier live | **2 tris, 1.0 kB** |
  | `export_apply=True` | 2,688 tris, but breaks rule 18 |
  | modifier applied, then `export_apply=False` | **2,688 tris, 208.7 kB** |

  Nothing errors, so a batch would have recorded the asset as done. Rule 18 now
  names the exception and the flow says to apply the modifier — which keeps the
  rule intact, since the `.blend` still holds the procedural version (rule 7).
- The flow told you to Realize Instances "before export", which is necessary but
  not sufficient: realizing without applying still exports the base mesh. Both
  steps are now spelled out, and `references/batch-mode.md` carries the warning for
  the runner, where the failure would be unattended.
- Verified that all four prescribed node types still exist on Blender 5.0.1:
  `DistributePointsOnFaces`, `InstanceOnPoints`, `ObjectInfo`, `RealizeInstances`.

### Fixed

- Three of the twelve per-file line counts in the README structure table had
  drifted by 23-54% after eight pull requests (`characters.md` ~430 → 638,
  `sourcing-strategy.md` ~65 → 100, `ai-generation.md` ~220 → 270). The CI checked
  the *total* and the SKILL.md row but not the individual rows, which is exactly how
  a stale number survives review. It now checks every row, and the seeded-regression
  suite covers the case: **12/12**.

### Added — continuous checks on the documentation itself

- **`tools/verify_docs.py`** plus `.github/workflows/verify.yml`: the repository had
  no CI at all. Nine checks, text only, no Blender, a few seconds on every push.
  Each one exists because the corresponding mistake was actually made here — iron
  rules forming an unbroken sequence, every cited `rule N` existing **and meaning
  what the citation claims**, the README count matching, referenced files existing
  and staying inside the plugin, README images resolving, no bare `pip install`,
  a valid manifest whose `source` is a real directory, and commands documented in
  the form that actually resolves.
- **`tools/test_verify_docs.py`** seeds each of those
  regressions into a copy of the repo and asserts the checker catches it: **11/11**,
  with the clean repo passing. A checker that only ever passes proves nothing —
  the same reasoning that exposed rule 19's material audit and the rig validator.
- Writing it caught two false positives in the checker itself: a 40-character
  window matched "Rule 6 is overridden — Rule 28 (no prompts)" against rule 6, and
  `uv pip install` tripped the bare-pip rule. Both fixed before merging, because a
  check that fires on correct input is the one people learn to ignore.

### Fixed

- README line counts were stale after eight pull requests: `SKILL.md` ~660 → ~880,
  total ~3,250 → ~3,870.

### Changed — pose is now measured, not assumed

- **Iron rule 13 only covered generation.** It said to generate characters in
  T-pose, and stopped there — so a marketplace or downloaded character went
  straight to rigging in whatever pose its author used, unmeasured. Rule 13 now
  requires measuring the pose on import, and PHASE 4 carries the measurement.
- **T-pose is not available from free libraries.** Measured on three: Khronos
  `RiggedFigure` A-pose at -26.8°, Khronos `CesiumMan` A-pose at -28.2°, Blender's
  Human Base Meshes I-pose at -70.8°. A-pose and arms-down are *modelling*
  conventions; T-pose is a *rigging* convention. So converting is the normal path,
  and `references/characters.md` now documents it rather than assuming a T-posed
  source appears.
- **The pose measurement has to be shoulder-to-hand.** A horizontal slice of the
  mesh picks up hip and thigh vertices: it reported -17° on a body whose arms were
  at -71°, an error of 53°. The check is now written down, along with the
  silhouette test that catches a bad conversion — wingspan ≈ height.
- **Documented the conversion that works, and three that do not.** Building a
  throwaway rig for its arm *weights*, then rotating vertices about the shoulder
  scaled by that weight, gives a clean shoulder. Selecting arm vertices
  geometrically puts the pivot on the skull; posing with Euler angles on a bone
  picks the wrong local axis; and the right axis with the wrong sign pushes the
  arms further down. Each of those is recorded with the number it produced, plus
  the two lines of trigonometry that settle the sign before you run anything.
- **Recorded a CC0 source.** Blender's Human Base Meshes bundle, with its two
  traps: the asset entries are preview *cameras* (geometry is under `GEO-`), and an
  object appended as a dependency can land in no collection at all and never appear.

### Changed — the skill now picks the rig instead of leaving it to judgment

- **New PHASE 5c, RIG SELECTION, in `SKILL.md`** — not buried in a reference the
  model may never load. It measures the mesh first and routes from the count, with
  the tiers measured on Blender 5.0.1:

  | Mesh vertices | Rig | Deform bones |
  |---:|---|---:|
  | < 700 | hand-built, 12-20 bones | 12-20 |
  | 700 - 3,000 | `armature_basic_human_metarig_add` | 35 |
  | > 3,000 | `armature_human_metarig_add` | 160 |
  | quadruped > 900 | `armature_basic_quadruped_metarig_add` | 46 |

  **A Rigify human needs ~3,200 vertices to be worth it.** The gate also carries the
  post-skinning check for dead deform bones, and the pointer to the silent IK/FK
  trap. The 370-vertex figure that produced mush now routes to the hand-built rig.
- **New iron rule 26**: never pick a rig without measuring vertices ÷ deform bones.
  Core rules become 1-26, batch 27-31, 31 total. Every cross-reference re-audited
  by meaning — 0 invalid, and rules 15, 22, 23, 24, 26 and 28 each verified to say
  what the citation claims.

### Fixed — rigging reference, exercised on a real armature

- **The Layered Actions section stopped exactly where it gets hard.** Its snippet
  creates and assigns an action, which on Blender 5.0.1 leaves it empty — 0 slots,
  0 layers. The next thing a reader reaches for, `action.fcurves`, raises
  `AttributeError: 'Action' object has no attribute 'fcurves'`, because 4.4+ moved
  F-curves into a channelbag per slot per strip. Every pre-4.4 snippet online uses
  the old attribute, and nothing in the error hints at slots. The section now
  carries the walk down to the F-curves, verified: 1 slot, 1 layer, 3 curves of 2
  keyframes. The previous text hedged with "the API is evolving rapidly" instead of
  giving the path.

- **The validation script raised three false alarms on a production rig.** Run
  against a generated Rigify human it flagged 10 root bones, 706 bones against a
  75-bone mobile limit, and 486 names with "special characters". All three were
  wrong in the way that matters — they fire on a correct rig:
  - the 10 parentless bones are mechanism bones, **none of them deform**;
  - the 75-bone budget applies to the skin palette, and the same rig has **160
    deform bones**, not 706;
  - the offending character is the **hyphen** in Rigify's own `DEF-spine` /
    `MCH-torso` convention, which survives glTF and FBX intact — verified, 486
    hyphenated node names in the exported GLB.

  It now counts deforming bones and deforming roots, and allows hyphens.
  Re-verified both ways: **2 alerts on the Rigify rig, both genuine**, and still
  **6 of 6** on the seeded rig.
- **`export_def_bones` was never mentioned anywhere.** Nor was `use_deform`. Without
  it the glTF exporter ships every control and mechanism bone as a joint: measured
  on the Rigify human, 865 joints and 255 kB become **319 joints and 98 kB**. The
  validator now points at it whenever total bones far exceed deforming ones.
- **Rigify had one table row and no code**, despite being the only free, built-in,
  offline auto-rigging option. It now has the three calls that work — including
  that `addon_utils.enable()` is not enough: it loads the module but leaves
  `RigifyParameters` incomplete, so generation dies on
  `'RigifyParameters' object has no attribute 'make_custom_pivot'`, which names
  nothing relevant. `bpy.ops.preferences.addon_enable(module="rigify")` is the one
  that works.

- **Nothing said to match the rig's density to the mesh's.** Rigging a real CC-BY
  character (Khronos `RiggedFigure`, 370 vertices) with a Rigify human produced
  visible mush: the head detached at the neck and the limbs collapsed into the
  torso. Cause, measured: **2.3 vertices per deform bone**, and **107 of the 160
  deform bones influenced nothing at all** — automatic weights had no geometry to
  localise them, so the vertices that were weighted got smeared across 8 or 9 bones
  each. The same mesh, same pose, on a 13-bone rig sized to it: 28.5 vertices per
  bone, 0 dead bones, volume held. The reference now says to check the ratio before
  choosing a rig, and gives the one-line check.
- **A freshly generated Rigify rig ignores its own FK controls, silently.** Every
  limb ships `IK_FK = 0.0`, so IK drives the chain and rotating `upper_arm_fk.L`
  moves nothing — measured, 0 of 370 vertices displaced, with no error or warning.
  Setting it to 1.0 moved 221 of 370 on the same pose. Documented as the first thing
  to check when a Rigify pose "does not apply".

### Verified — no changes needed

- **Bone Collections (section 10) work verbatim** on Blender 5.0.1: three
  collections created, `DEF` populated by prefix, `MCH` hidden. This is the first
  section of the skill exercised that needed no correction.
- **The character validation script catches everything it claims to.** Run against
  a rig seeded with each defect — non-unit armature scale, a second root bone, a
  bone name with spaces, 5 influences on a vertex, unweighted vertices, shape keys
  with an unapplied modifier — it reported **6 of 6**, no false negatives. Both
  results are now recorded in the reference, since "we tested this" is worth as
  much to a reader as a fix.

### Fixed — USDZ export, measured instead of assumed

- **The skill sent users to install two external tools they do not need.**
  `references/export-targets.md` stated "Blender's native USDZ export is limited"
  and offered only Reality Converter or `usdzconvert`. Measured on Blender 5.0.1
  with a full PolyHaven PBR material, the native `bpy.ops.wm.usd_export` produced a
  1.86 MB archive with four JPEG maps and a complete preview-surface graph — 1
  `UsdPreviewSurface`, 4 `UsdUVTexture`, 1 `UsdPrimvarReader_float2`, with `normal`,
  `roughness`, `metallic` and `displacement` connected. That is *more* than the glTF
  export of the same material carries, which keeps 3 maps and drops displacement.
  The native path is now documented first, with the parameters that work.
- **One real constraint found, and it was not the one claimed.**
  `convert_world_material` defaults to True and writes a `DomeLight` referencing an
  `.exr` into the archive. The USDZ spec admits PNG and JPEG only, so the archive is
  non-conforming and iOS Quick Look may reject it. `convert_world_material=False`
  removes it — verified. This is the sort of specific, checkable limit that
  "native export is limited" was standing in for.
- The third and last known instance of one pattern: the skill reimplementing, worse,
  a capability its own dependency already ships. The other two were Hunyuan3D
  generation (a ~25 GB local install for something the addon exposes natively) and
  texturing (a hand-built node graph for three maps where `set_texture` produces
  sixteen nodes covering seven).

### Fixed — texturing, exercised against the live PolyHaven API

- **The recommended texturing workflow silently loses over half its texture
  maps.** Measured end to end on `american_walnut_veneer`: PolyHaven supplies 7
  maps (AO, ARM, Diffuse, Displacement, nor_dx, nor_gl, Rough) and the exported
  glTF carries **3** — base colour, roughness and normal. AO is dropped even
  though glTF has an `occlusionTexture` slot, because Blender only fills it from
  an ARM-packed arrangement. Displacement has no glTF slot at all. Nothing in
  the skill said so: `AO`, `occlusion`, `Displacement` and
  `KHR_texture_transform` had zero mentions across `texturing-strategy.md` and
  `validation-checklist.md`. The compatibility table there covered Principled
  BSDF *properties* only, never texture *maps*. A map-level table is now
  documented alongside it.
- **Rule 19's audit was checking the wrong level.** `material_audit()` listed
  procedural node types, which cannot see any of the losses above: it flagged a
  harmless Mapping node while missing both the dropped Displacement and the
  dropped AO. It now checks node types *and* image-map roles, and reports the
  exporter's duplicate-image case. Verified: it names all four real losses on the
  PolyHaven material, and reports zero findings across the fifteen gallery assets.
- **Step 6 hand-built the node graph.** It wrote `ShaderNodeTexImage` chains for
  three maps, while the addon's own `download_polyhaven_asset(asset_type='textures')`
  plus `set_texture` produce a 16-node material with all seven maps and the
  colourspaces already correct. `set_texture` had zero mentions in
  `texturing-strategy.md`. The addon path is now the prescribed one — the same
  reimplementation problem already fixed for Hunyuan3D generation.
- `set_texture` names its material `<texture_id>_material_<object>`, which is not
  the `M_Type_Variant` convention. The strategy now says to rename (rule 25).

### Fixed — the marketplace path, exercised against the live PolyHaven API

- **IMPORT never renamed anything.** Rule 15 wants `SM_PascalCase` objects with a
  matching `_Mesh` data-block, but a marketplace download lands under the source
  file's name (`ClassicNightstand_01`) and an AI import under whatever the importer
  chose. The phase said nothing about it, so every non-scripted asset broke rule 15
  by default. New iron rule 25 requires the rename in PHASE 4, whatever the source.
- **Rule 2's screenshots could show an empty scene.** `get_viewport_screenshot`
  captures the viewport as aimed, and on a wide view a 0.7 m prop is a few pixels at
  the origin — so the shot the skill relies on to verify a modification looks like
  the modification deleted everything. New iron rule 22 requires framing the subject
  first, with the `view3d.view_selected` override that does it.
- Iron rules: two core rules added (22, 25), so the core set is 1-25 and the
  batch-specific rules move from 24-28 to 26-30. 30 total, 25 core plus 5 batch.
  Every `rule N` cross-reference in SKILL.md, README.md and references/ was audited
  against the renumbered set — by meaning, not just by existence, which is how the
  previous renumbering left rule 28 pointing at the wrong rule.

### Verified

- The `marketplace` creation method now works end to end against the live PolyHaven
  API: 521 models indexed, search returns polycount and dimensions for tier
  selection, download and import succeed, and scale is exact — PolyHaven reports
  millimetres (`568 x 424 x 700`) and the importer produces
  `0.568 x 0.424 x 0.7` Blender units.
- `references/sourcing-strategy.md` records the millimetre-to-metre detail, so a
  raw 568-unit object is recognisable as a failed conversion.

### Fixed — `/kiln setup`, exercised for the first time

- **Every `pip3 install` in the skill failed.** All six of them, including
  `pip3 install gradio_client` — the first install the "recommended to start"
  path proposes. Homebrew and most Linux distros ship an externally-managed
  Python (PEP 668), where a bare `pip3 install` errors out with
  `externally-managed-environment`. All six now create and use a venv, and
  SKILL.md explains why before any pip is proposed.
- **Five of the eleven fields in the environment report had no command to fill
  them**: Blender MCP status, models list, device, nano-banana, and the PEP 668
  warning. SKILL.md now carries a table pairing every field with its command and
  its gotcha.
- **The report asked for VRAM on Apple Silicon, where there is none.**
  `system_profiler SPDisplaysDataType` reports no VRAM line — memory is unified.
  The template now says "unified" and uses `sysctl -n hw.memsize`.
- **Device detection was circular**: it wanted `cuda / mps / cpu`, which only
  `torch` can confirm, and torch is not installed until a local backend is. It now
  reports "unknown" rather than guessing, with `nvidia-smi` and
  `platform.machine()` as the pre-torch signals.
- **Backend choice did not offer the MCP-native path** documented in the previous
  release, and asked the user to choose without first checking
  `get_hunyuan3d_status()` / `get_hyper3d_status()` to see if it was already on.
- Blender MCP detection now uses `get_addon_status()`, which also reports whether
  the addon is behind the server's protocol — a raw port check only proves
  something is listening.

### Fixed — batch mode, exercised for the first time

- **The batch runner disabled the integrations it depends on, between every
  asset.** Its scene-clear step was `bpy.ops.wm.read_homefile(use_empty=True)`,
  which builds a fresh scene — and the addon keeps every integration flag as a
  *scene* property (`scene.blendermcp_use_polyhaven` and friends). Measured: the
  flag flips to False, the command stops being registered, and the next call
  answers `Unknown command type`. Asset 1 succeeds, every asset after it fails,
  and rule 25 forbids prompting, so an overnight batch failed silently from the
  second asset onward. The clear now removes datablocks instead, which leaves
  scene properties intact — verified.
- **Pre-flight did not validate integrations.** Rule 25 forbids prompting once
  the loop runs, so a missing integration has to be caught before starting.
  Pre-flight now maps each `method` in the manifest to the status calls it needs
  and aborts with the addon's own remediation text.
- Pre-flight now names the tool for "verify Blender MCP is connected"
  (`get_addon_status`) and checks the addon version, since an outdated addon is
  missing commands a batch may need.
- Stale cross-references in `references/batch-mode.md`: "All 21 existing iron
  rules" (now 23), and rule 28 pointing at "Rule 23 (no prompts)" when the
  renumbering in the previous release moved it to 25.
- Removed three dangling entries from SKILL.md's resource table
  (`../creative-excellence/`, `../threejs-r3f/`, `../motion-principles/`). None
  exist, and they point outside the plugin directory, which the plugin spec
  forbids.

### Added

- SKILL.md now records that MCP tool names and the addon's raw socket command
  names differ, that some MCP tools have no socket equivalent, and that ticking
  an integration checkbox takes effect without reconnecting.

### Fixed — found by exercising the skill against a live Blender MCP addon

- **The SOURCE phase failed on a default install with a misleading error.** All
  four addon integrations (PolyHaven, Sketchfab, Tencent Hunyuan3D, Hyper3D
  Rodin) ship OFF, and while an integration is off the addon does not register
  its commands at all — so `search_polyhaven_assets` answers
  `Unknown command type: search_polyhaven_assets`, which reads as a version
  mismatch. The `get_*_status` tools are always registered and carry the exact
  remediation, including the Sketchfab API-key step. New iron rule 22 requires
  checking them first and surfacing their message.
- **The skill reimplemented 3D generation the addon already provides.**
  `references/ai-generation.md` prescribed a ~25 GB local `hy3dgen` install
  (CUDA-only texturing) with an HF Spaces fallback, while never mentioning
  `generate_hunyuan3d_model` and its job tools — nor Hyper3D Rodin, a second
  backend, at all. The MCP-native path is now documented first.
- **Rule 14 could not be satisfied as written.** It asked to verify dimensions,
  but the skill only ever called `get_scene_info()`, which does not carry them.
  New iron rule 23 points at `get_object_info()`, whose `world_bounding_box` is
  what the check actually needs.
- 15 of the 25 MCP tools were never mentioned anywhere in the skill. SKILL.md now
  carries the full tool surface, extracted from the server source and exercised
  live.

### Changed

- Iron rules: two core rules added (22, 23), so the batch-specific rules move
  from 22-26 to 24-28. 28 rules total, 23 core plus 5 batch.

### Added

- `examples/gallery/` — a reproducible render gallery. Fifteen props across three
  themes (forge, sci-fi modular, stylised nature) modelled from scratch by script,
  cleaned, audited, rendered in headless EEVEE and exported to GLB. Measured:
  21,879 tris, 1,456 kB raw, 133 kB after dedup/weld/Draco. Run `run_gallery.sh`
  to regenerate everything, or `THEMES="forge nature" ./run_gallery.sh` for a
  subset.
- The gallery scripts now follow the skill's own rules rather than merely claiming
  to. Added: `SM_PascalCase` object names with matching `_Mesh` data-blocks and
  `M_Type_Variant` materials (rule 15), poly-budget reporting against the
  `topology-rules.md` tiers (rule 4), a material export audit before every GLTF
  export (rule 19), transform application alongside merge and recalc (rule 10),
  a scale check (rule 14), one output folder per asset with its `.blend`
  (rules 7 and 16), and a per-asset production log recording licences (rule 17).
  The README states which rules a headless script cannot honour, and why.
- README gallery section, per-theme metrics tables, and hero contact sheet.
- README section "Running over Blender MCP", with viewport screenshots from a live
  session: the pipeline building an asset inside a running Blender, and the addon
  panel showing all four integrations off — which is what iron rule 22 is about.

## [1.0.0] — 2026-08-26

First tagged release. The pipeline landed in April 2026 but was never released;
everything below ships in 1.0.0.

### Pipeline

- Full 8-phase pipeline: CONFIG → BRIEF → SOURCE → IMPORT → CLEANUP → TEXTURING →
  OPTIMIZE → EXPORT.
- Batch mode: `/kiln batch` wizard, YAML manifest, autonomous runner.
- Reference image support across the full pipeline.
- Hunyuan3D 2.x generation — local (CUDA / Apple Silicon MPS) and HF Spaces.
- Marketplace sourcing via PolyHaven and Sketchfab.
- Four texturing strategies plus a procedural-to-baked workflow.
- Optimization via gltf-transform and gltfpack, with LOD generation.
- GLB / FBX / USDZ export with an 8-point post-export validation checklist.
- Character support: T-pose enforcement, rigging patterns, Blender 5.x bone collections.
- 26 iron rules (21 core + 5 batch-specific).

### Fixed before release

- **The plugin was not installable.** `.claude-plugin/marketplace.json` set `source`
  to `skills/blender-kiln/SKILL.md` — a file, under a directory that does not exist
  in this repo. The spec requires a directory starting with `./`. Since a `SKILL.md`
  at the plugin root is auto-loaded as a single-skill plugin, `source` is now `./`.
  Verified with `claude plugin install` and `claude plugin details`.
- **The documented commands were not invocable.** The README and `SKILL.md` listed
  twelve `/kiln:<sub>` entries, but `kiln` is a single skill with no `commands/`
  directory, and a colon addresses a plugin's skill (`blender-kiln:kiln`) — so
  `/kiln:setup` resolved to nothing. All entry points are now documented as
  `/kiln <sub>`, and `SKILL.md` gained an argument-routing table.
- `owner` is now an object, as the marketplace schema requires.
- Two repository `.png` files were saved HTML error pages, not images. Removed.

### Added before release

- `LICENSE` — MIT was declared in the README and the manifest, but no license file
  existed, so GitHub reported the repository as unlicensed.
- `.claude-plugin/plugin.json` manifest (version, author, license, keywords).
- `.gitignore`, this changelog, and a 1280×640 social preview image.
- 20 repository topics (previously none) and a tightened description.

### Removed before release

- The `npx skills add blender-kiln` install command from the README: the repository
  is not published on that registry, so the command failed.
