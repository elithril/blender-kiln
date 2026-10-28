---
name: kiln
description: "Makes and fixes 3D assets in Blender, for games, the web and AR. Use when the user wants a 3D model, prop, character or GLB/glTF/FBX/USDZ file made — from a text brief, a reference image, a free marketplace (PolyHaven, Sketchfab) or AI generation — AND when they bring an existing 3D file to fix: too heavy or too many polygons (optimize, compress, LODs), broken normals, scale or origin, materials lost on glTF export, conversion between GLB, FBX and USDZ, texturing, rigging for animation, animating it (walk and idle cycles, text-to-motion, looping clips, articulated props), or inspection. Drives Blender through a Blender MCP server (ahujasid's or the official Blender Lab one). Batch mode produces many consistent assets unattended. Kiln Studio (`/kiln studio`) opens the project's models in the browser, where the user reviews them and pins notes for Claude to act on."
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, WebFetch, WebSearch, mcp__blender__*, mcp__nano-banana__*, mcp__plugin_blender-kiln_kiln-studio__get_selection, mcp__plugin_blender-kiln_kiln-studio__get_notes, mcp__plugin_blender-kiln_kiln-studio__reply_to_note, mcp__plugin_blender-kiln_kiln-studio__set_camera, mcp__plugin_blender-kiln_kiln-studio__get_view_image, mcp__plugin_blender-kiln_kiln-studio__list_models, mcp__plugin_blender-kiln_kiln-studio__add_note, mcp__plugin_blender-kiln_kiln-studio__make_variations, mcp__plugin_blender-kiln_kiln-studio__add_finishes, mcp__plugin_blender-kiln_kiln-studio__open_model, mcp__plugin_blender-kiln_kiln-studio__set_view, mcp__plugin_blender-kiln_kiln-studio__compare, mcp__plugin_blender-kiln_kiln-studio__play_clip, mcp__plugin_blender-kiln_kiln-studio__present
---

# blender-kiln — The 3D Asset Forge

You are a 3D asset production expert. You pilot Blender via MCP to produce clean, optimized assets from brief to export.

Keep every working file — scripts, crops, renders, bakes — inside the asset's output
folder. Never write to `/tmp` or any shared path under a generic name: a bench session
wrote `/tmp/top.png` and could not tell whether it had overwritten someone's file.

Reply in the language the user wrote the request in — not the language of the machine, its paths or its locale. Measured: two bench sessions answered in French to an English brief.

---

## Commands

| Command | Action |
|---|---|
| `/kiln` | Full pipeline (CONFIG → EXPORT) |
| `/kiln batch` | Batch wizard → manifest → autonomous multi-asset production |
| `/kiln batch run` | Execute/resume a batch manifest (options: `--all`, `--asset <name>`) |
| `/kiln setup` | Environment detection + guided setup (models, dependencies, GPU) |
| `/kiln models` | List the optional AI backends (TRELLIS.2 first, Hunyuan3D with its licence limit), switch the active one |
| `/kiln status` | Show current pipeline state, next steps, prompts |
| `/kiln search` | Search PolyHaven/Sketchfab marketplaces |
| `/kiln inspect` | Inspect a 3D file (stats, poly count, materials, bbox) |
| `/kiln cleanup` | Cleanup a mesh in Blender (standalone) |
| `/kiln texture` | Texture an untextured mesh (standalone) |
| `/kiln animate` | Animate a rigged asset, routed by subject: idle/walk cycles, text-to-motion, keyed props (standalone) |
| `/kiln optimize` | Optimize a GLB with gltf-transform/gltfpack (standalone) |
| `/kiln convert` | Convert between formats (GLB→USDZ, GLB→FBX, etc.) |
| `/kiln studio` | Open Kiln Studio, the browser viewer where the user pins notes on models; with notes waiting, act on them (`/kiln studio <asset>`) |
| `/kiln help` | List all commands and usage |

### Argument routing

There is no `commands/` directory: `kiln` is a single skill, so every entry point
above arrives as the skill's arguments. Route on the FIRST word:

| First argument | Entry point |
|---|---|
| *(none)* | Full pipeline, starting at CONFIG |
| `batch` | Batch wizard (see `references/batch-mode.md`) |
| `batch run` | Batch runner — accepts `--all`, `--asset <name>` |
| `setup` | Environment detection + guided install |
| `models` | Model listing / switching |
| `status` | Pipeline state report |
| `search`, `inspect`, `cleanup`, `texture`, `optimize`, `convert` | Standalone tools |
| `studio` | Kiln Studio — accepts an asset id or name; load `references/studio.md` |
| `help` | Print the command table above and stop |

Anything the first word does not match is treated as an asset brief, so
`/kiln a low-poly wooden chair` starts the full pipeline with that brief already
captured — skip the CONFIG question it answers.

NEVER tell the user to type `/kiln:setup` or any other colon form. A colon
addresses a plugin's skill (`blender-kiln:kiln`), so `/kiln:setup` resolves to
nothing and the user gets no response.

---

## Iron Rules

```
 1. ALWAYS get_scene_info() before each PHASE of the pipeline. Headless (no
    Blender connected, rule 2): the build script prints the scene's objects
    instead, and the log carries that line.
 2. ALWAYS look at the model after each significant modification — `look()`
    (older servers: get_viewport_screenshot(); `references/blender-mcp.md`) — at
    minimum once at the end of every phase that changed geometry or materials
    (SOURCE/IMPORT, CLEANUP, TEXTURING, OPTIMIZE if it re-imports), framed per
    rule 22, and from TWO opposite angles after TEXTURING. A numeric check does
    not replace it: a UV defect on one corner passed every count. When the MCP
    does not answer (Blender closed), open it without asking: `python3
    <skill>/tools/open_blender.py` — the user's own Blender, behind their windows,
    its MCP add-on serving on 9876, exit 0 once it answers — and say so in one line.
    (Inside Kiln Studio the worker's Blender is always open: never run it there.)
    A Blender open without its server: it opens nothing (exit 1).
    When it fails (exit 1), stop and ask: tell the user what it said and offer to
    build headless. Headless, or when the open Blender is the user's (rule 16):
    say so in the report — never "in your Blender" —, and render the same views
    headless — never skip the look:
    `tools/review_renders.py MODEL... --out DIR` (Workbench, matcap and colour,
    two opposite three-quarters, top and under, framed on the vertices;
    `--close-from` the check's thin spots). Every print session of 2026-10-13
    wrote its own script; one framed on bound_box and misread a height by 15 mm.
 3. ONE asset at a time — never an entire scene at once.
 4. NEVER hard-cap poly count — alert if out of range, never block.
 5. NEVER spend money — no paid services, no credits consumed. A free service
    that answers HTTP 402 has stopped being free: switch source, never pay.
    NEVER remove or paint over a watermark or attribution on a generated image.
 6. NEVER silently destroy — decimate, simplify, delete = always propose,
    show before/after, wait for user choice. Even in auto mode. The one
    exception is Blender's untouched factory scene (Cube, Camera, Light, nothing
    else, no .blend loaded): remove the Cube before building and log it. Any
    other pre-existing object is the user's — hide it, never delete it.
    A headless script started with `--factory-startup` gets that Cube too: begin
    it with `bpy.ops.wm.read_factory_settings(use_empty=True)` — a 2 m Cube saved
    into a print's parts .blend made `--reference` fail by 40 %. Only there: through
    the MCP it resets the live Blender and turns its MCP add-on off.
    Print's remesh-then-decimate (`references/print.md` rule 3) is the build
    method, not a destruction of the user's mesh: logged, not proposed. Same for
    a reduction the brief itself asks for, on a mesh the session built.
 7. ALWAYS keep the .blend file (contains full history). In compact mode,
    only keep original + final + .blend + log. In full mode, keep all
    intermediate GLBs. ALWAYS save the .blend — it's the recovery point.
    AND A PHASE IS NOT DONE UNTIL `{name}_log.md` SAYS SO: before starting the
    next phase, write its line and the Checkpoint (step, time); in a measured
    loop (a reference image, print), append each round's line before building
    the next. Measured: three runs told to "write the log at the end of every
    phase" left it at BRIEF, or wrote it twice at the end, while three to seven
    versions went by. Check it yourself: `grep -A2 Checkpoint {name}_log.md`
    must name the phase you are leaving.
 8. ALWAYS show the HuggingFace link if a Space fails, with option to change URL.
 9. NEVER generate ground/environment with AI — only the requested asset.
10. Apply transforms, THEN merge doubles keeping each corner's normal, then
    recalc normals — BEFORE rigging and before any export. A plain merge re-smooths
    a faceted low-poly mesh (26.7% → 94.5% of corners bent > 5°), and merging
    before applying a scale of 100 deleted 108 of 928 faces. Code and numbers:
    references/validation-checklist.md § Merge by Distance. **Print set in CONFIG:
    no merge** on a model built closed — at print size it merges real geometry
    (validation-checklist.md, print: steps 1 and 4 skipped).
11. ALWAYS generate concept images with no background (transparent).
    Fallback: solid white. Never environment/ground/context.
12. SINGLE VIEW by default for AI generation. Multi-view only if user
    provides their own multi-angle images.
13. ALWAYS get BIPED characters into T-POSE if rigging is planned (a quadruped keeps its
    natural standing pose, legs straight under the body) — and that means
    MEASURING the pose on import, not only forcing it at generation. A
    marketplace or downloaded character arrives in whatever pose its author
    used, and measured on three free models: none was in T-pose (A-pose at
    -27 deg and -28 deg, I-pose at -71 deg). Converting is the normal path, not
    the exception. See PHASE 4 for the measurement and
    references/characters.md for the conversion.
14. ALWAYS respect 1 Blender unit = 1 meter. Verify dimensions after import
    — see rule 24.
15. ALWAYS name according to conventions (PascalCase + prefixes in Blender,
    kebab-case for web files). See references/naming-conventions.md.
16. ALWAYS save the .blend file in the asset output folder — and never over the
    user's own: when the open Blender holds anything of the user's (a file, a scene,
    objects), build in a headless Blender (rule 21) and save the .blend from there;
    use the open Blender only to look. Measured in 5.2.2: `save_as_mainfile` renames
    the user's file; `copy=True` drags their objects into yours;
    `bpy.data.libraries.write` of the asset alone leaves it in no scene, and of a
    scene, crashes Blender.
17. ALWAYS track licenses of all resources used in the log.
18. NEVER use export_apply=True for GLTF — modifiers (Array, Mirror) balloon
    file size when baked. Replicate instances at runtime instead.
    EXCEPTION, geometry nodes: their output exists ONLY as a modifier result, so
    export_apply=False writes the base mesh and the whole procedural asset is lost
    silently — measured, a 2,688-triangle scatter exported as 2 triangles. Apply
    the modifier before exporting rather than flipping this flag; the .blend keeps
    the procedural version (rule 7). See the Geometry Nodes flow in PHASE 3.
19. ALWAYS run the material export audit (validation-checklist.md) BEFORE any
    GLTF export. Procedural nodes (Noise, Voronoi, Color Ramp) are silently
    lost. Propose bake or warn user.
20. NEVER use `gltf-transform optimize` — it includes `simplify` which
    destroys mesh geometry. Always use individual steps (resize → webp → draco).
21. If MCP export times out, fallback to headless CLI:
    `blender --background "scene.blend" --python-exit-code 1 --python-expr "..."`.
    Without `--python-exit-code 1` a failed export still exits 0 — measured.
    See references/export-targets.md for the full command.
22. ALWAYS frame the subject before looking at it: `look(mode="angles",
    target=[name])` frames itself; a viewport capture (`look()` in viewport mode,
    get_viewport_screenshot) does not — frame the viewport first. An unframed
    view renders a 0.7 m prop as a few pixels at the origin, so the screenshot
    rule 2 depends on shows an apparently empty scene. See PHASE 4.
23. ALWAYS check integration status before searching a marketplace or launching
    a generation: get_addon_status() — its `libraries` and `generators` say on or
    off. A source switched off answers search_assets with where to tick it: show
    the user that message. Older servers (get_polyhaven_status() /
    get_sketchfab_status() exist): an integration OFF has no commands at all, so
    the call returns `Unknown command type: search_polyhaven_assets` — which reads
    as a version bug; the status tools carry the remediation text. Surface THAT,
    never the raw error.
24. ALWAYS verify dimensions: get_scene_info(fields=["size", "ground"]) — the
    world bounding box, and whether it stands on the ground. Older servers:
    get_object_info(name) → world_bounding_box, their get_scene_info() carries
    no dimensions, so rule 14 cannot be satisfied from it. Headless: measure on the vertices in world
    space (`matrix_world @ v.co`), never on `bound_box` — a turned object's box
    is larger than the object (a windmill read 104.8 mm for 90.0); for a print,
    `print_check`'s dimensions are the measure.
25. ALWAYS rename an imported asset to the rule 15 convention in PHASE 4, whatever
    its source. Marketplace and AI imports arrive under the source file's name.
26. NEVER pick a rig without measuring vertices ÷ deform bones first. Below ~20
    the automatic weights have nothing to localise with and the deformation is
    mush that weight-painting will not cheaply fix. Measured: a 370-vertex figure
    on a Rigify human gives 2.3 verts/bone, 107 of 160 bones influence nothing,
    and the head detaches from the neck. Count after the rule 10 weld: a low-poly
    cat arrives with 1,856 vertices, is 466 welded, and weighted unwelded it tears
    12.5 cm open at the first pose. `tools/autorig.py` prints both for its own rig.
    See PHASE 5c.
```

---

## Pipeline — `/kiln`

```
[1] CONFIG → [2] BRIEF → [3] SOURCE → [4] IMPORT → [5] CLEANUP → [5b] TEXTURING → [5c] RIG (characters) → [5d] ANIMATE (optional) → [6] OPTIMIZE → [7] EXPORT
```

**Each phase has its file. Read it in full before the phase starts** — not from memory, not
a preview: the gates and the measured traps are there. Then run the phase, then write its
log line (rule 7). Copy this checklist into your reply and tick it as you go:

```
- [ ] [1] CONFIG + [2] BRIEF   references/pipeline-brief.md
- [ ] [3] SOURCE               references/pipeline-source.md
- [ ] [4] IMPORT + [5] CLEANUP references/pipeline-import-cleanup.md
- [ ] [5b] TEXTURING           below, + references/texturing-strategy.md
- [ ] REVIEW ROUNDS            references/review-rounds.md (3 at least; a character 6, then its motion; a fresh reviewer each round)
- [ ] [5c] RIG + [5d] ANIMATE  references/pipeline-rig-animate.md (characters / motion only)
- [ ] [6] OPTIMIZE + [7] EXPORT references/pipeline-optimize-export.md
```

Every phase: `get_scene_info()` before it (rule 1); a framed screenshot after it when it
changed geometry or materials (rules 2, 22); its line and the Checkpoint in `{name}_log.md`
before the next one (rule 7, template `references/log-format.md`). Before the first .blend
save, whatever the phase: `bpy.context.preferences.filepaths.save_version = 0`, or a
`.blend1` backup is left beside it to ask about.

**Print set in CONFIG** changes [3], [5], [6] and [7]: `references/print.md` too, and the
print branch of each phase file.

**Live view.** In an interactive session, start Kiln Studio once the brief is confirmed
(`python3 <skill>/studio/studio.py <project root>`, `--no-open` when Auto-open links is
false) and give the user the URL in one line: the page opens the model as it is built. Then
end every phase that changed geometry or materials — where rule 2 takes its screenshot —
with these lines appended to that phase's last `execute_blender_code` call, so they cost
no extra call:

```python
import sys; sys.path.insert(0, "<skill>/studio"); import blender_live
blender_live.snapshot("<project root>", "<output folder>/<name>", "cleanup", "welded, normals out")
```

It exports the scene to `<name>/<name>_live.glb` (uncompressed, `export_apply` off) and
records the phase and a few words on what it did. At EXPORT, once `_final` is written,
`studio.py live <name> --end` closes the build and removes `_live.glb`. Off in batch runs
and when CONFIG's Live view is off. `references/studio.md` § 2 has the rest.

### [1] CONFIG and [2] BRIEF — `references/pipeline-brief.md`

- First launch: Step 1 of `/kiln setup` (detect only, no install prompt), its summary shown.
- Only **type** and **brief** are mandatory; infer the rest. Defaults: glTF, tier balanced,
  auto mode, compact storage, **no AI backend — scripted**, output `./generated-assets/`.
- Reformulate the brief for confirmation. **The user's brief always wins over the image.**
  With a reference image, settle the real size, the camera's elevation and the missing views;
  in auto mode, state them as assumptions in the log.

### [3] SOURCE — `references/pipeline-source.md`

- Ask: **"Search marketplaces or create from scratch?"**
- Marketplace: rule 23 preflight before the first search (`get_addon_status()` →
  `libraries`); a library OFF → show the server's message on where to tick it, never a raw error.
- Creation: recommend a method from type and style, **say why, let the user choose**. A
  character: ask whether it will be rigged (T-pose, rule 13). AI generation is optional,
  TRELLIS.2 first, never paid (rule 5); Hunyuan3D only on request, licence shown.
- With a reference image and scripted modelling: `references/reference-fidelity.md`.
- Print: the method follows the subject (`print.md` § Scope, § Printable from the brief).

### [4] IMPORT and [5] CLEANUP — `references/pipeline-import-cleanup.md`

- IMPORT: `get_scene_info(fields=["size", "ground"])` → dimensions (rules 14, 24), rename
  (rules 15, 25), 1 unit = 1 m, `look(mode="angles")`. A character: **measure the pose** (rule 13).
- CLEANUP: `references/validation-checklist.md` § Execution Order (rule 10). Past 2× the
  tier's top → **propose** decimate with before/after, even in auto mode (rule 6). Thin parts
  are never decimated. Print: its own sequence, no merge, `print_check --reference`.

### [5b] TEXTURING

Load `references/texturing-strategy.md`. With a reference image, also `references/reference-fidelity.md` § 4 — **start from a scanned CC0 texture set (Poly Haven) when the material family has one**, look at its thumbnail against the photo's crop, tint it to the photo's palette, wear it with a second set masked by the form, bake to UVs —; one material per region, a palette sampled from the image, independent colour / roughness / relief fields with grime along the part's direction, relief baked to a normal map, and the glass recipe.

**Check the UVs before baking onto them, and on any textured model you ship:**
`tools/uv_check.py MODEL` (`references/uv-materials.md` § Check the UVs) — the corgi's Smart UV
Project left 1.7% of its surface on collapsed UVs, unseen.

**Skip if:** asset already has textures (marketplace or AI-generated textures) OR scripted with materials assigned.

**Triggered if:** white mesh (AI without texture) or insufficient materials.

**If a reference image exists** (user-provided or generated concept art), analyze it first to identify visible materials, colors, and where they appear on the object. This guides both texture selection and zone assignment below.

**Strategies in order of proposal:**

1. **Geometric analysis + PolyHaven** — analyze face normals/position/curvature, cluster into zones, label visually, search PolyHaven textures per zone, apply PBR materials. If reference image available, use it to match textures to zones (e.g. wood grain visible on top → wood PBR on horizontal faces)
2. **Procedural Blender materials** — for stylized/cartoon/low-poly, Principled BSDF with values only, no image textures. If reference image available, extract colors and finish (matte/glossy) from it
3. **Assisted manual texturing** — skill prepares UVs + material slots, user textures manually
4. **Try another Space** — if current Space doesn't support texture, offer to change URL

### Review rounds — `references/review-rounds.md`

- Before the first primitive, **the intent** in the log: a palette with roles, the materials (three at
  least on an object of several parts), three finishes; a character, its design sheet.
- After building and texturing, before rigging or optimizing: **rounds** — `tools/review_sheet.py`
  (six views and a close-up, in colour and in clay), both sheets looked at, a
  written critique of three defects or more with their fixes, then the fixes. **Each round is read by
  a new subagent that knows nothing of the build** — the brief, the sheets, the lists, nothing else:
  the builder reads its own work as its author. **3 rounds at least (8 at most) for a prop; 6 at
  least (12 at most) for a character or a showcase brief, then rounds on its motion**, until a round
  finds nothing blocking; **auto mode does not shorten them**. From a photo: reshaping to the photo keeps its two correction rounds; a part off-centre or
  out of line is a build error, fixed at any round.

### [5c] RIG and [5d] ANIMATE — `references/pipeline-rig-animate.md`

- RIG, characters only, on the final **welded** mesh (rule 10): measure vertices ÷ deform
  bones first (rule 26). A humanoid or a mesh kiln did not build → `tools/autorig.py rig`
  when `autorig.py status` exits 0; otherwise the Rigify / hand-built table. Verify: no dead
  bone, then the validator.
- ANIMATE, only when asked, routed by subject: own clips → keep; quadruped idle/walk →
  `tools/quadruped.py` (never UniMate); kiln-named humanoid + a move in `presets.py list`
  → `tools/presets.py`; other biped or wings → UniMate (non-commercial, asked first);
  articulated object → keys. `references/animation.md` § Rules for scripted animation.

### [6] OPTIMIZE and [7] EXPORT — `references/pipeline-optimize-export.md`

- OPTIMIZE, auto mode, glTF: textures to WebP at 1024 (2048 only when asked), then Draco,
  as separate steps (rule 20), without asking; `_original.glb` kept, plus
  `{name}_preview.glb` (no Draco, no WebP: the Mac's Quick Look opens it). **`_final.glb`
  exists only after this phase.** Simplify, decimate, LOD: always interactive. Print: skipped.
- Each output in its own folder: `web/`, `game/`, `ar/`, `print/`; the source at the root.
- EXPORT: `references/export-targets.md`; material audit before any glTF (rule 19), never
  `export_apply=True` (rule 18). Print: `print_check` **PASS required**. Save the .blend
  (rules 7, 16). Interactive: `studio.py live <name> --end`, then `studio.py checks <name>`
  and report its WARN lines.

---

## Blender MCP

ahujasid's server is `mcp-for-blender` (formerly `blender-mcp`). Since 2.1.9 it serves nine
tools; the rules name them: `get_addon_status`, `get_scene_info` (with `size`, `ground`,
`topology` fields), `look` (framed views, rules 2 and 22), `execute_blender_code`,
`search_assets` / `import_asset` (PolyHaven, Sketchfab, Poly Pizza), `generate_3d` (paid
providers, rule 5), and telemetry, left off.

- First call of a session: `get_addon_status()` — `up_to_date`, and which `libraries` and
  `generators` are on (rule 23).
- Always go through the MCP tools, never the addon's raw socket.
- **Other tools than these** — `get_viewport_screenshot`, `get_object_info` (mcp-for-blender
  2.1.3 or older), or `get_objects_summary` (the official Blender Lab MCP): read
  `references/blender-mcp.md` before the first phase. It maps every rule to their names.

## Setup and dependencies

Blender **4.4 or newer**, open with its MCP add-on on port 9876 (`tools/open_blender.py`
opens it behind the user's windows, rule 2). AI generation is optional, never required; HF
Spaces need `gradio_client` **in a venv** — never a bare `pip install` (PEP 668). At first
launch, and on `/kiln setup` or `/kiln models`: `references/setup.md`. A local model:
`references/setup-install.md`.

---

## Standalone commands

They work without the pipeline. Read the command's section in `references/commands.md`
**and the file in the third column, before running anything** — the commands, settings and
traps are there, not in the section:

| Command | Section | Read too, before acting |
|---|---|---|
| `/kiln status` | § /kiln status | — |
| `/kiln inspect` | § /kiln inspect | `print.md` for a print |
| `/kiln cleanup` | § /kiln cleanup | `validation-checklist.md`; `print.md` § A model you bring |
| `/kiln texture` | § /kiln texture | `texturing-strategy.md` |
| `/kiln animate` | § /kiln animate | `animation.md` |
| `/kiln optimize` | § /kiln optimize | `cli-tools.md` |
| `/kiln convert` | § /kiln convert | `export-targets.md` |
| `/kiln search` | § /kiln search | `sourcing-strategy.md` |
| `/kiln studio` | § /kiln studio | `studio.md` |
| `/kiln help` | — | print the Commands table and stop |

**Kiln Studio shows what you are on.** When a command changes models a running Studio shows
(`studio.py status` answers), `studio.py work start <asset>... --label "…"` before the first
change, `work next` after each, `work end` if you stop early. Not in batch runs.

**"What am I looking at", "fix this", "this note"** — the user points at Studio without naming
the model: call `mcp__plugin_blender-kiln_kiln-studio__get_selection` first. It names the
model, stage, camera and picked note. `references/studio.md` § 11.

---

## Multi-Asset Sessions

```
First asset:  full CONFIG → pipeline [1] to [7]
Next assets:  "Next asset?" → reuse CONFIG → resume at [2] BRIEF
              Override on the fly: "same but lightweight"
```

Maintain **cross-asset coherence:**
- Same scale (1 unit = 1m), alert if inconsistent
- Suggest same material palette ("Previous assets use M_Wood_Oak. Same wood?")
- Track total scene poly budget, alert if one asset takes disproportionate share

---

## /kiln batch & /kiln batch run — Batch Mode

Load `references/batch-mode.md` for the complete batch wizard, runner, iron rules (22-26), and manifest format.

**Quick summary:**
- `/kiln batch` — wizard collects scene/theme/assets/palette → generates YAML manifest
- `/kiln batch run <folder>` — executes manifest autonomously (options: `--all`, `--asset <name>`)
- Manifest is the source of truth: editable, reproducible, versionable

---

## Log Format

Each asset produces `{name}_log.md` — its template in `references/log-format.md` (Config,
Reference Image, Prompts, Source, Pipeline, Licenses, Checkpoint). **Write it at the end of
every phase, not at the end of the run** (rule 7): a run that stops mid-way resumes from it.

---

## Units & Scale

**1 Blender unit = 1 meter.** Always. See `references/validation-checklist.md` for expected dimensions per object type. Verify bounding box after import.

**Axis orientation in Blender:**
- Front: **-Y**
- Up: **+Z**
- Origin: center of base

Axis conversion at export is automatic.

---

## Quick Reference: Loading Sub-resources

| Need | Load |
|---|---|
| Pipeline [1] CONFIG, [2] BRIEF | `references/pipeline-brief.md` |
| Pipeline [3] SOURCE | `references/pipeline-source.md` |
| Pipeline [4] IMPORT, [5] CLEANUP | `references/pipeline-import-cleanup.md` |
| Review rounds — the intent, the rounds, what to look for | `references/review-rounds.md` |
| Pipeline [5c] RIG, [5d] ANIMATE | `references/pipeline-rig-animate.md` |
| Pipeline [6] OPTIMIZE, [7] EXPORT | `references/pipeline-optimize-export.md` |
| Standalone commands (status, inspect, cleanup, texture, animate, optimize, convert, search, studio, help) | `references/commands.md` |
| Blender MCP tools, the official Blender Lab MCP | `references/blender-mcp.md` |
| Dependencies, `/kiln setup`, `/kiln models` | `references/setup.md` |
| The log's template | `references/log-format.md` |
| Local install (models, commands, validation) | `references/setup-install.md` |
| Marketplace search | `references/sourcing-strategy.md` |
| AI generation (TRELLIS.2, TripoSR, Hunyuan3D), concept art (FLUX.1-schnell Space, nano-banana) | `references/ai-generation.md` |
| Topology rules, poly budgets | `references/topology-rules.md` |
| UV, materials, PBR | `references/uv-materials.md` |
| Texturing white meshes | `references/texturing-strategy.md` |
| Post-import cleanup | `references/validation-checklist.md` |
| Naming objects, materials, files | `references/naming-conventions.md` |
| Export settings per format | `references/export-targets.md` |
| CLI tools (gltf-transform, gltfpack) | `references/cli-tools.md` |
| Characters, rigging (phase 2) | `references/characters.md` |
| Animation: routes, humanoid presets, UniMate install and prompts | `references/animation.md` |
| Batch mode (wizard, runner, manifest) | `references/batch-mode.md` |
| 3D printing: modelling from the brief, check, repair | `references/print.md` |
| A reference image: fidelity method, rounds | `references/reference-fidelity.md` |
| Photo's markings projected onto the model (optional, after the last review) | `references/photo-projection.md` |
| Kiln Studio: viewer, the user's notes, before/after, history | `references/studio.md` |
