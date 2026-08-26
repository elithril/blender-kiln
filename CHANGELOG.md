# Changelog

All notable changes to blender-kiln are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
