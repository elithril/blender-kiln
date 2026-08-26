# Changelog

All notable changes to blender-kiln are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
