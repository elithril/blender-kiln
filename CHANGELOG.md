# Changelog

All notable changes to blender-kiln are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
