# Changelog

All notable changes to blender-kiln are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
