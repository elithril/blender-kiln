# Changelog

All notable changes to blender-kiln are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `.claude-plugin/marketplace.json` was unusable: `source` pointed at a `SKILL.md`
  file under a non-existent `skills/` directory. It now points at the plugin root
  (`./`), so `/plugin marketplace add elithril/blender-kiln` works.
- `owner` is now an object, per the marketplace schema.
- Skill naming harmonized on `kiln` (matching the `SKILL.md` frontmatter) instead of
  the mixed `blender-kiln` / `kiln` references.
- Documented commands were not invocable. The README and `SKILL.md` listed twelve
  `/kiln:<sub>` entries, but `kiln` is a single skill with no `commands/` directory,
  and a colon addresses a plugin's skill (`blender-kiln:kiln`) — so `/kiln:setup`
  resolved to nothing. All entry points are now documented in their working form,
  `/kiln <sub>`, and `SKILL.md` gained an argument-routing table.

### Added
- `.claude-plugin/plugin.json` manifest (version, author, license, keywords).
- `LICENSE` file — MIT was declared in the README but no license file existed.
- `.gitignore`.
- Plugin install instructions in the README.

### Removed
- Unverified `npx skills add blender-kiln` install command from the README.

## [1.0.0] — 2026-04-03

### Added
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
