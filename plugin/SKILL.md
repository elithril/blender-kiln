---
name: kiln
description: "Makes and fixes 3D assets in Blender, for games, the web and AR. Use when the user wants a 3D model, prop, character or GLB/glTF/FBX/USDZ file made — from a text brief, a reference image, a free marketplace (PolyHaven, Sketchfab) or AI generation — AND when they bring an existing 3D file to fix: too heavy or too many polygons (optimize, compress, LODs), broken normals, scale or origin, materials lost on glTF export, conversion between GLB, FBX and USDZ, texturing, rigging for animation, animating it (walk and idle cycles, text-to-motion, looping clips, articulated props), or inspection. Drives Blender through a Blender MCP server (ahujasid's or the official Blender Lab one). Batch mode produces many consistent assets unattended. Kiln Studio (`/kiln studio`) opens the project's models in the browser, where the user reviews them and pins notes for Claude to act on."
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, WebFetch, WebSearch, mcp__blender__*, mcp__nano-banana__*, mcp__plugin_blender-kiln_kiln-studio__get_selection, mcp__plugin_blender-kiln_kiln-studio__get_notes, mcp__plugin_blender-kiln_kiln-studio__reply_to_note, mcp__plugin_blender-kiln_kiln-studio__set_camera, mcp__plugin_blender-kiln_kiln-studio__get_view_image, mcp__plugin_blender-kiln_kiln-studio__list_models, mcp__plugin_blender-kiln_kiln-studio__add_note, mcp__plugin_blender-kiln_kiln-studio__make_variations, mcp__plugin_blender-kiln_kiln-studio__open_model, mcp__plugin_blender-kiln_kiln-studio__set_view, mcp__plugin_blender-kiln_kiln-studio__compare, mcp__plugin_blender-kiln_kiln-studio__play_clip, mcp__plugin_blender-kiln_kiln-studio__present
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
 2. ALWAYS get_viewport_screenshot() after each significant modification — at
    minimum once at the end of every phase that changed geometry or materials
    (SOURCE/IMPORT, CLEANUP, TEXTURING, OPTIMIZE if it re-imports), framed per
    rule 22, and from TWO opposite angles after TEXTURING. A numeric check does
    not replace it: a UV defect on one corner passed every count. When the MCP
    does not answer (Blender closed), open it without asking: `python3
    <skill>/tools/open_blender.py` — the user's own Blender, behind their windows,
    its MCP add-on serving on 9876, exit 0 once it answers — and say so in one line.
    (Inside Kiln Studio the worker's Blender is always open: never run it there.)
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
    into a print's parts .blend made `--reference` fail by 40 %.
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
    with get_object_info() — see rule 24.
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
22. ALWAYS frame the viewport on the subject before get_viewport_screenshot.
    An unframed view renders a 0.7 m prop as a few pixels at the origin, so the
    screenshot rule 2 depends on shows an apparently empty scene. See PHASE 4.
23. ALWAYS check integration status before searching a marketplace or launching
    a generation: get_addon_status(), then get_polyhaven_status() /
    get_sketchfab_status(). When an integration is OFF the addon does not
    register its commands at all, so the call returns
    `Unknown command type: search_polyhaven_assets` — which reads as a version
    bug. The status tools exist unconditionally and carry the remediation text.
    Surface THAT, never the raw error.
24. ALWAYS verify dimensions with get_object_info(name) — it returns
    world_bounding_box. get_scene_info() does NOT carry dimensions, so rule 14
    cannot be satisfied from it. Headless: measure on the vertices in world
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

## Blender MCP — tool surface

All 36 tools exposed by `blender-mcp` **2.0.0** (bundled addon 1.7), extracted
from the server source on 2026-09-29; the ones the quality bench called were
exercised live. Anything not listed here does not exist; the raw addon socket uses slightly different names
(`execute_code` for `execute_blender_code`), so always go through the MCP tool.

| Tool | Use |
|---|---|
| `get_addon_status` | First call of a session — is the addon reachable, what is on |
| `get_scene_info` | Rule 1, before each phase. Object count and names only — **no dimensions** |
| `get_object_info` | Rule 24. Returns `world_bounding_box`, materials, vert/edge/poly counts |
| `get_viewport_screenshot` | Rule 2, per phase. `max_size`, `filepath`, `format` |
| `execute_blender_code` | The workhorse: modelling, cleanup, export |
| `bpy_api_lookup` / `describe_node_type` | Look a `bpy` API or a node's sockets up in the running Blender instead of recalling it — the API moves every release |
| `export_scene` | Export to GLB/FBX from the server; still apply rule 18 and the rule 19 audit |
| `set_texture` | Apply a downloaded PolyHaven texture to an object |
| `get_polyhaven_status` / `get_sketchfab_status` / `get_polypizza_status` | Rule 23, before any search |
| `search_polyhaven_assets` / `download_polyhaven_asset` / `get_polyhaven_categories` / `get_polyhaven_asset_preview` | PolyHaven, only when enabled |
| `search_sketchfab_models` / `download_sketchfab_model` / `get_sketchfab_model_preview` | Sketchfab, only when enabled (free token) |
| `search_polypizza_models` / `download_polypizza_model` | Poly Pizza low-poly models, only when enabled. Check each model's licence and record it (rule 17) |
| `get_hunyuan3d_status` / `generate_hunyuan3d_model` / `poll_hunyuan_job_status` / `import_generated_asset_hunyuan` | Native Hunyuan3D — **needs Tencent Cloud keys or a local API**, and the licence excludes the EU, UK and South Korea. Never by default; only on explicit request, licence shown, confirmed first |
| `get_hyper3d_status` / `generate_hyper3d_model_via_text` / `generate_hyper3d_model_via_images` / `poll_rodin_job_status` / `import_generated_asset` | Native Hyper3D Rodin — paid API (rule 5) |
| `get_tripo_status` / `generate_tripo_model` / `poll_tripo_job_status` / `import_generated_asset_tripo` | Native Tripo — paid (rule 5) |
| `disable_telemetry` / `record_trajectory_feedback` | Addon telemetry — opt-in since 2.0, leave it off |

**A disabled integration does not fail, it disappears.** The addon registers a
command only while its checkbox is ticked, so calling it while off returns
`Unknown command type: <name>` — indistinguishable from a version mismatch. The
`get_*_status` tools are always registered and carry the fix. Hence rule 23.

**Ticking a box takes effect immediately.** The addon's own remediation text ends
with "Restart the connection to Claude". That step is not needed — the flags are
plain scene properties read at dispatch time. Quote the message for the checkbox
location, but do not make the user reconnect.

**Two layers, different names.** These are MCP tool names. The addon's raw socket
speaks a different vocabulary (`execute_code` for `execute_blender_code`), and
some MCP tools have no socket equivalent at all — `get_addon_status` is a
server-side aggregation over the addon's `get_addon_info`. Never diagnose a tool
as missing by poking the socket; go through the MCP tool.

**Check the addon version once per session.** `get_addon_status()` reports
`up_to_date`. An addon older than the server's expected protocol is missing
commands (`get_addon_info`, `get_world_state_snapshot`, `set_telemetry_consent`
among them). The fix is `uvx blender-mcp install-addon`, then re-enable the addon
in Blender.

### On the official Blender Lab MCP

The Blender Foundation's server (`projects.blender.org/lab/blender_mcp`, the one
behind Claude's Blender connector) drives the same Blender with **different
tools, and none for marketplaces or generation**. Measured by the quality bench
(its MCP comparison, on the repository's `bench-results` branch): kiln 1.1.2 shipped the same 7 GLBs
on it, for 10% less cost. Map the tools, and source around the gaps:

| Skill says | On the Lab MCP |
|---|---|
| `get_scene_info` (rule 1) | `get_objects_summary` |
| `get_object_info` (rule 24) | `get_object_detail_summary` |
| `get_viewport_screenshot` (rule 2) | `get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")`, or `render_viewport_to_path` |
| frame the viewport (rule 22) | `jump_to_view3d_object_by_name` |
| `bpy_api_lookup` | `search_api_docs` / `get_python_api_docs`, plus `search_manual_docs` |
| `execute_blender_code` | same name |
| `get_addon_status`, `get_*_status` (rule 23) | none — `get_objects_summary` answering is the connection check |
| PolyHaven tools, `set_texture` | the public API from Bash — `references/sourcing-strategy.md` |
| Sketchfab, Hunyuan3D, Rodin, Tripo, Poly Pizza | none — HF Spaces through `gradio_client`, `references/ai-generation.md` |
| `export_scene` | `bpy.ops.export_scene.gltf` in `execute_blender_code` (rules 18, 19) |

Setup, each point measured: the add-on's manifest sets
`blender_version_min = "5.1.0"` — kiln's own floor stays 4.4, but this path needs
at least that; it installs as an extension; **online access on** (Preferences → System,
or `--online-mode`), or the add-on refuses to serve. Its PyPI-style package is
**also named `blender-mcp`**, so `uvx blender-mcp` starts ahujasid's server —
run it from git:
`uvx --from "git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp" blender-mcp`.
Register it under the MCP name `blender` so `mcp__blender__*` still matches.

**Rule 2 needs saying twice on this server.** The bench's sessions knew the capture
tool and called it right — then took **one screenshot per session** on 4 of 5
briefs, and framed once in five. At the end of every phase that changed geometry
or materials: `jump_to_view3d_object_by_name(name)`, then
`get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")`. After TEXTURING, a second
angle too. A single-asset run therefore takes **at least four** captures.

---

## Dependencies

**Required:**
- `blender-mcp` — Blender must be open with MCP server started (port 9876);
  `tools/open_blender.py` opens it behind the user's windows with the server started.
  Install the addon with `uvx blender-mcp install-addon`; `addon_utils.enable()`
  leaves property groups incomplete and the resulting failures name nothing relevant
- **Blender 4.4 or newer.** Layered actions arrived in 4.4 and the animation paths
  here go through `action.layers[].strips[].channelbag()`, which does not exist
  before it. Measured on 5.0 and 5.2 LTS; 4.4-4.5 satisfy the API but are untested

**Concept art:**
- `black-forest-labs/FLUX.1-schnell` HF Space — free, Apache-2.0, through the same
  `gradio_client` venv as the 3D Spaces (default). See `references/ai-generation.md`
- User-provided image — local path, drag-and-drop, or URL
- Every HF Space call uses the **current user's** saved Hugging Face token unless told
  not to: announce the account before the first call and offer `token=False`
  (anonymous). Never read or log a token. See `references/ai-generation.md`
- Pollinations — **no longer free**: HTTP 402 after one image (measured 2026-09-29)

**3D Generation — optional, never required.** The default is Claude scripting
Blender: no AI model, nothing to install. AI generation is an option the user picks
(recommended for organic or realistic forms), and a local install is never needed
for it:
- **HF Spaces** (first choice) — free, quota-limited; requires `gradio_client` in a
  venv (see `/kiln setup`; a bare `pip3 install` fails on any PEP 668 Python)
- **Local** — only if the user wants offline work. Run `/kiln setup` to install.

**Optional:**
- `nano-banana` MCP — alternative concept art generation via Gemini (requires API key with billing)
- `gltf-transform` — `npm install -g @gltf-transform/cli`
- `gltfpack` — `npm install -g gltfpack`
- `Sketchfab API token` — free account, needed for downloads
- `Reality Converter` / `usdzconvert` — **not needed.** Blender exports USDZ
  natively via `bpy.ops.wm.usd_export`, with more texture maps than the glTF
  path carries. See `references/export-targets.md` § USDZ

At first launch, run automatic environment detection (see `/kiln setup`). Guide installation for anything missing.

---

## /kiln setup — Environment Detection & Setup

Run this at first launch or when the user runs `/kiln setup`.

### Step 1: Auto-detect environment

Scan and report status for each component:

```
── 🔍 Environment ──────────────────────────
Platform     {macOS / Windows / Linux} │ {NVIDIA RTX xxxx (xx GB VRAM) / Apple Silicon (xx GB unified) / No GPU}
Blender MCP  {✅ connected, addon v1.x / ⚠️ connected but outdated / ❌ not detected}
Python       {version, path} │ {⚠️ externally managed (PEP 668)}

── 3D Generation ───────────────────────────
Backend      {✅ none needed — scripted (default) / ✅ HF Spaces / ✅ Local / ✅ MCP native}
Models       {list installed models with sizes, or "none"}
Device       {cuda / mps / cpu / unknown until a backend is installed}

── Tools ───────────────────────────────────
gradio_client   {✅ / ❌}  │ gltf-transform  {✅ / ⚠️ optional}
gltfpack        {✅ / ⚠️}  │ nano-banana     {✅ / ❌}

── Rigging ─────────────────────────────────
Auto-rig     {✅ SkinTokens, tested version / ⚠️ damaged or untested version / — not installed (optional)}
```

**Detection commands — every field above, with the command that fills it:**

| Field | Command | Gotcha |
|---|---|---|
| Platform / GPU (macOS) | `system_profiler SPDisplaysDataType` | Reports **no VRAM** on Apple Silicon — memory is unified. Use `sysctl -n hw.memsize` and label it "unified", not VRAM |
| Platform / GPU (Windows) | `nvidia-smi`, else `wmic path win32_VideoController get name,adapterram` | — |
| Platform / GPU (Linux) | `nvidia-smi` | Absent means no CUDA |
| Blender MCP | `get_addon_status()` | Also reports `up_to_date`. If false, `uvx blender-mcp install-addon`. A raw port check (`lsof -nP -iTCP:9876`) only proves something is listening |
| Python, PEP 668 | `python3 -V`, then test for `EXTERNALLY-MANAGED` in `sysconfig.get_paths()['stdlib']` | Homebrew and most Linux distros ship one. It makes every bare `pip3 install` fail — see below |
| Models | `du -sh ~/.hunyuan3d/models/*` | Path is the default from `references/setup-install.md`; absent directory means none installed |
| Device | `nvidia-smi` → cuda. Else `platform.machine() == 'arm64'` on Darwin → mps *probable* | `torch.backends.mps.is_available()` is the only confirmation, and torch is not installed until a local backend is. Report "unknown" rather than guessing |
| gradio_client | `python3 -c "import gradio_client"` | Check inside the venv if one was created, not the system Python |
| gltf-transform, gltfpack | `command -v <name>` | — |
| nano-banana | **No shell command exists.** It is an MCP server — check whether its tools are in reach | Never report ❌ from a shell probe |
| Auto-rig | `python3 tools/autorig.py status --quick` | Exit 0 ready, 2 not installed, 3 damaged or not the tested version. `--quick` skips hashing the 1.6 GB of checkpoints; `rig` hashes them before loading (they are pickles) |

### Installing Python packages — read this before proposing pip

Most macOS and Linux Pythons are **externally managed** (PEP 668). `pip3 install
<anything>` fails outright there:

```
error: externally-managed-environment
```

So never propose a bare `pip3 install`. Create a venv and install into it:

```bash
python3 -m venv ~/.hunyuan3d/venv
~/.hunyuan3d/venv/bin/pip install gradio_client
```

Then use `~/.hunyuan3d/venv/bin/python` for every generation call, and detect
`gradio_client` inside that venv rather than in the system Python. `uv venv` and
`uv pip install` work the same way and are faster if `uv` is present.

### Step 2: Guided setup (if needed)

Based on scan results, propose actions:

**No 3D backend is not a gap.** Scripted modeling needs none — never push a setup.
Only when the user picks AI generation, propose in this order (stage `RUNNING`
checked first, `references/ai-generation.md`):
> 1. **TRELLIS.2 Space** (`microsoft/TRELLIS.2`, MIT) — free, textured. Send an
>    image with an alpha cut-out: an opaque one is cut out by RMBG-2.0, non-commercial.
>    Else **TRELLIS** (`trellis-community/TRELLIS`, MIT), else **TripoSR** (MIT).
> 2. **Local** — never required; offline only. TRELLIS.2 on Apple Silicon (31 GB).
> 3. **Hunyuan3D** (Space, local or MCP native) — only on request. Its licence
>    **does not apply in the EU, the UK or South Korea**: say so, confirm before any
>    call. MCP-native Rodin and Tripo are paid (rule 5).

**If user chooses Local:** Load `references/setup-install.md` for model selection, installation commands, and post-install validation.

**Auto-rig (SkinTokens) — offer it when a character is to be rigged, and only then.** Say
what it costs and why before asking: ~5.6 GB on disk (2.0 of it uv's download cache), MIT
code and checkpoints, on a Mac through kiln's patch (MPS; from image-to-3dlab, Apache-2.0),
35-54 s and ~7 GB of memory per mesh. It rigs humanoids and meshes kiln did not build better
than Rigify on the bent pose (PHASE 5c). On a yes: `python3 tools/autorig.py setup --yes` —
the tested commit, the pinned packages (`tools/skintokens-requirements.txt`), the checkpoints'
hashes checked. Without `--yes` it installs nothing. Never install it unasked.

---

## /kiln models — Model Management

List and switch the optional AI backends. Default stays scripted — none needed.

```
── 🧠 Models ───────────────────────────────
  #  │ Backend                     │ Status            │ Licence
  1  │ TRELLIS.2 (HF Space)        │ ✅ RUNNING        │ MIT
  2  │ TRELLIS (HF Space)          │ ✅ RUNNING        │ MIT
  3  │ TripoSR (HF Space)          │ ❌ RUNTIME_ERROR  │ MIT
  4  │ hunyuan3d-dit-v2-mini local │ ❌ not installed  │ ⚠️ not EU/UK/KR

Active: scripted (no AI) │ "use 1" "install 4" "back to scripted"
```

Stages are read live, never copied from here. Choosing Hunyuan3D shows its licence
limit and asks for confirmation first.

User can switch model or backend at any time during a session.

---

## Pipeline — `/kiln`

```
[1] CONFIG → [2] BRIEF → [3] SOURCE → [4] IMPORT → [5] CLEANUP → [5b] TEXTURING → [5c] RIG (characters) → [5d] ANIMATE (optional) → [6] OPTIMIZE → [7] EXPORT
```

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

### [1] CONFIG — Collect Parameters

**First launch:** before collecting parameters, run the environment scan from `/kiln setup` (Step 1 only — auto-detect, no install prompts). Display the summary so the user sees what's available. If critical components are missing (e.g. Blender MCP not connected), warn and offer to run full `/kiln setup`.

**Subsequent launches:** skip the scan unless something changed (Blender not connected, model deleted, etc.).

Collect these parameters. Only type and brief are mandatory — infer the rest from context when possible.

| Parameter | Default | Notes |
|---|---|---|
| **Type** (prop, environment, character, vehicle...) | mandatory | — |
| **Brief** (description, context, mood) | mandatory | Feeds searches and prompts |
| **Export target** (glTF, FBX, USDZ, multi) | glTF | Determines export rules |
| **Print** (FDM / resin + height in mm + colours the printer has) | none | Set when the brief says it will be 3D printed. **Method by subject** — primitives for a simple object, metaballs + voxel remesh for a stylised figure; a realistic likeness from a photo is said out of reach (`print.md` § Scope, § Figures). Switches [3], [5] and [7] to `references/print.md`; target STL (+ 3MF). A single-colour printer: say which regions get painted, or which become separate parts in their own filament (`print.md` § Like the photo, rule 9) |
| **Detail tier** (lightweight / balanced / detailed / custom) | balanced | Soft ranges, never hard caps |
| **Visual style** (realistic, stylized, cartoon, low-poly) | realistic | Impacts sourcing + AI prompts |
| **Mode** (auto / guided) | auto | guided = validation at each step |
| **Storage** (compact / full) | compact | compact = original + final + .blend + log only; intermediates are removed at the end-of-session proposal (EXPORT), never silently mid-run. Auto mode with nobody to answer: keep them and list them in the hand-over. Measures are always logged |
| **3D Backend** (none / hf-spaces / local) | none — scripted | AI only when chosen; then HF Spaces unless a local model is installed |
| **Local model** | none | Only if installed (see `/kiln models`) |
| **HF Space URL** | microsoft/TRELLIS.2 | Then `trellis-community/TRELLIS`. Hunyuan3D only on request (licence). Check `stage: RUNNING` first — a paused Space still answers HTTP 200. See `references/ai-generation.md` |
| **Auto-open links** | false | Configurable mid-session |
| **Live view** | on (interactive), off (batch) | Kiln Studio reloads the model after each phase — see § Live view below |
| **Output folder** (absolute path) | `./generated-assets/` | Confirmed at launch |

**Detail tier ranges:** see `references/topology-rules.md` § Detail Tiers. Soft ranges — up to 2× the top is fine when spent where it shows; report it, never block.

**Scene:** auto-detected via `get_scene_info()` — not asked.

### [2] BRIEF — Confirm Understanding

**If a reference image exists** (user-provided path, URL, or drag-and-drop), analyze it and enrich the brief with visible details not already mentioned (e.g. number of legs, curvature, handle shape, proportions).

**CRITICAL: the user's brief ALWAYS wins over image analysis.** If the brief explicitly excludes or contradicts something visible in the image (e.g. "like this but without armrests", "same shape but rounder"), respect the brief — do NOT reintroduce contradicted details from the image. The image is a starting point; the brief is the final word.

Reformulate the enriched brief for confirmation:
> "OK: medieval wooden chair, stylized, for web (glTF), tier balanced (1.5-5K tris). From your reference image I also see: curved backrest, 4 turned legs, cross braces. Good?"

**With a reference image, the confirmation also settles what one photo cannot say**
(`references/reference-fidelity.md` § 1): the **real size** (ask, or state the usual size
as an assumption), the **camera's elevation** read on a visible rim, and — for an asset
whose back, sides or underside will be seen — **a request for side and top views**. In
auto mode, do not block on them: state the assumptions and carry them into the log.

### [3] SOURCE — Marketplace or Create?

Ask: **"Search marketplaces or create from scratch?"**

#### Marketplace Path

Load `references/sourcing-strategy.md`.

**Preflight (rule 23) — do this BEFORE the first search:**

```
get_polyhaven_status()   → {"enabled": false, "message": "...press N..."}
get_sketchfab_status()   → {"enabled": false, "message": "..."}
```

Both are OFF in a default addon install. While OFF, `search_polyhaven_assets`
and `search_sketchfab_models` are **not registered as commands** — they answer
`Unknown command type`, not "disabled". If either is off, show the `message`
field verbatim (it names the BlenderMCP sidebar panel and the N shortcut) and
offer to continue on the other source or switch to the creation path. Never
report the raw `Unknown command type` error to the user.

- Search PolyHaven + Sketchfab with brief keywords
- Present ~10 results (name, poly count, link)
- User can: pick a number, open links ("open 2, 5, 7" or "open all"), refine search, or switch to creation
- Sketchfab: filter downloadable + free only (requires API token)
- PolyHaven: fully free CC0

#### Creation Path

**First: recommend a method** based on brief + style + type:

```
IF style = low-poly OR cartoon
    → recommend scripted ("Geometric style = scripting gives clean separated parts.")

IF type = furniture OR simple architecture AND style = stylized
    → recommend scripted ("Geometric + stylized = perfect for scripting.")

IF type = organic (rock, tree, food, creature) OR style = realistic + detailed
    → recommend AI ("Organic forms and realistic detail = AI excels here.")

IF type = complex architecture (cathedral, ornate facade) AND print not set
    → recommend AI ("Complex detail = AI handles it better.")
    # print set: a lighthouse, a windmill, a tower are simple objects — a lathe or a prism,
    # scripted (print.md § Scope). Two print sessions read this line against it.

IF type = character or creature   # decided before the style lines above, which read it otherwise
    → the style decides: cartoon / stylised → scripted, its body ONE skin (overlapping
      volumes or metaballs, one voxel remesh — `characters.md` § An animated creature;
      for print, `print.md` § Figures), never separate parts glued on, never one family
      per region on a skin that bends; realistic / detailed → recommend AI. Sessions read "cartoon → scripted" and
      "character → AI" as a contradiction on every mascot.
    → ASK: "Will this character need rigging/animation?"
      IF yes → force T-pose in concept image prompt
              → record it: the RIG SELECTION gate in PHASE 5c depends on it

ELSE
    → present both options without recommendation
```

Always explain WHY the recommendation, always let the user choose.

**Print set in CONFIG: the method follows the subject** (`references/print.md` § Scope). A
simple object is built from closed primitives. **A stylised figure** — a cartoon animal, a
character, a mascot — from metaball families and one voxel remesh (`print.md` § Figures): a
cartoon dragon from one flat drawing came out that way. **A realistic likeness of a real animal
or person from a photo is said at CONFIG to be out of reach of scripted modelling** — two cats,
metaballs included, passed every check and were unacceptable to look at: offer it as a stylised
figure, an image-to-3D generation repaired for print, or `print_check` on a model the user
brings. A mechanical
part (a load, a lid that must close, a size to the tenth) is said at CONFIG to belong in a CAD
tool, and goes on only as decorative if the user agrees. Parts joined by a peg: offer
`tools/fit_coupon.py`'s test print before modelling the joints — **in auto mode, do not wait
for it**: model at 0.2 mm a face, write the coupon next to the model, and say in the hand-over
that the clearance is not measured (`print.md` rule 5). Scripted, for both. **Load
`references/print.md` § Printable from the brief before the first primitive** — model at print size, closed solids only, one volume
(exact union as you go, or overlap + one voxel remesh), the process's minimum thickness, a flat
base, overhangs that grow out of the part below, relief as geometry. A generated or marketplace
mesh is repaired instead ([5]). Texturing ([5b]) carries nothing to a print. **With a reference
image, `references/print.md` § Like the photo, for print too**: the photo method in full, openings
read on their outer edge, details cut along the photo's camera, the `face` measure every round, and
rounds until the gaps stop closing — **the two-round cap of `reference-fidelity.md` § 5 does not
apply** — and the user decides it is alike.

**Options:**

| Method | Best for | Trade-off |
|---|---|---|
| **AI Generation (optional; TRELLIS.2 first)** | organic, realistic, complex | Single mesh, free daily quota |
| **Scripted modeling (Blender Python)** | furniture, archi, stylized, low-poly | Separated parts, clean topology, more geometric |
| **Geometry Nodes (procedural)** | scattering, patterns, parametric | Non-destructive, powerful but complex |
| **User-provided image → AI or scripted** | when user has reference art (path or URL) | Image guides any method (see below) |
| **Concept art first** | when starting from nothing | Generates concept image, then AI or scripted |

**Concept art input — 3 modes:**

Ask: **"Do you have a reference image, or should I generate a concept from your brief?"**

| Mode | How | Notes |
|---|---|---|
| **Text prompt** | Generate via the FLUX.1-schnell HF Space (free, Apache-2.0) | Default method |
| **Image path / drag-and-drop** | User provides local file path | Used as reference for any method |
| **Image URL** | User provides URL, downloaded via curl | Saved locally, used as reference |

**Reference image usage per method:**

A user-provided image (or generated concept art) is useful for ALL creation methods, not just AI generation:

| Method | How the image is used |
|---|---|
| **AI generation** | Passed directly as generation input (image → 3D) |
| **Scripted modeling** | **Load `references/reference-fidelity.md`** — inventory the details, measure the silhouette from the pixels (or, given a generated mesh of the photo, its profile with `tools/template_profile.py` — never ship that mesh), check every part is attached — and LOOK at every joint the review renders (`review/joints/`): a part that joins another enters it, section unchanged (a foot only if the photo shows one) — sample materials from the image (one material per physical material; patina stays metal), review twice against it — then, only when the photo carries text, a logo or precise wear and the shape is final, **propose** projecting the photo's markings (`tools/photo_project.py`, refused under 0.95 fitted IoU; show two other angles; never silently, rule 6 — `references/photo-projection.md`) |
| **Geometry Nodes** | Analyze image to inform node parameters — spacing, density, pattern, scale |
| **Marketplace** | Analyze image to refine search keywords and evaluate result similarity |

If nano-banana MCP is available, offer it as an alternative (supports iterative editing) — it bills a Gemini key, so only on explicit request (rule 5).

**Concept art & AI generation:** Load `references/ai-generation.md` for the concept-art commands, prompt rules, and the 3D backends.

**Scripted modeling flow:**

- `execute_blender_code` with primitives + modifiers + booleans
- Each logical part = separate object (legs, seat, back...) — for props. An animated
  character's body is ONE skin, its eyes, nose and eyelids apart (`characters.md` § An
  animated creature)
- Materials assigned per object from creation
- `get_viewport_screenshot` for iterative validation

**Geometry Nodes flow:**

For assets with repetitive patterns (railings, fences, stone walls, vegetation scattering):
- Create the node tree via `execute_blender_code` (Python API)
- Common patterns: Scatter (Distribute Points → Instance on Points), Extrude + Transform, Curve to Mesh. All four node types verified present on Blender 5.0.1
- **Realize Instances** at the end of the tree (GLTF has no concept of GN instances)
- **Then APPLY the modifier before export.** This is not optional and it is easy to
  miss, because nothing errors: geometry nodes output exists only as a modifier
  result, and rule 18 requires `export_apply=False`, so the exporter writes the
  *base* mesh. Measured on a scatter of 2,688 triangles:

  | Export | Result |
  |---|---|
  | `export_apply=False`, modifier live | **2 tris, 1.0 kB** — the whole scatter gone, silently |
  | `export_apply=True` | 2,688 tris — correct, but violates rule 18 |
  | **modifier applied, then `export_apply=False`** | **2,688 tris, 208.7 kB — correct and rule 18 holds** |

  ```python
  bpy.ops.object.modifier_apply(modifier="GN")   # procedural becomes geometry
  ```

  Keep the .blend with the modifier intact (rule 7) — that is where the
  procedural version survives. Apply on a copy, or apply after saving.
- ⚠️ **Simulation Zone gotchas**: Group Input values do NOT propagate into sim zones (pass via state items), geometry freezes after frame 1 (only state items persist), Set Position required after sim zone output

### [4] IMPORT

```
get_scene_info() → import via execute_blender_code
→ get_object_info(name) → verify world_bounding_box   (rules 14, 23)
→ RENAME to SM_PascalCase, data-block to SM_..._Mesh   (rule 15)
→ center + normalize scale if needed (1 unit = 1 meter)
→ alert if dimensions seem wrong ("Asset is 0.002m tall. Scale issue?")
→ frame the viewport, THEN get_viewport_screenshot     (rule 2)
```

**Measure the pose (rule 13) — characters only.** Do it here, before anything
downstream assumes a rest pose. Measure **shoulder to hand**, never a horizontal
slice of the mesh: a slice picks up hip and thigh vertices and reported -17 deg
on a body whose arms were actually at -71 deg.

```python
cos = [v.co for v in mesh.data.vertices]
H = max(c.z for c in cos)
right = [c for c in cos if c.x > 0]
hand = max(right, key=lambda c: c.x)
torso_w = max(c.x for c in cos if abs(c.z - H * 0.75) < H * 0.02)
shoulder = max((c for c in right if abs(c.x - torso_w) < 0.03), key=lambda c: c.z)
angle = math.degrees(math.atan2(hand.z - shoulder.z, hand.x - shoulder.x))
```

| Angle | Pose | Action |
|---|---|---|
| within ±15 deg | T-pose | proceed |
| -15 to -45 deg | A-pose | convert — see `references/characters.md` § Converting a pose to T-pose |
| below -45 deg | I-pose, arms at the sides | convert; this is the hardest case, the arms touch the torso |

A T-pose also shows in the silhouette: **wingspan ≈ height**. The reference body
measured 1.68 m across for 1.69 m tall once converted.

**Rename on import — every method, not just scripted.** A marketplace download
lands under whatever name the source file carried (`ClassicNightstand_01`), and an
AI-generated mesh under whatever the importer chose. Neither satisfies rule 15, so
rename here, in IMPORT, before anything downstream reads the name:

```python
obj.name = "SM_ClassicNightstand"
obj.data.name = "SM_ClassicNightstand_Mesh"
```

**Frame before you screenshot.** `get_viewport_screenshot` captures the viewport
as it is aimed. On a wide-angle view a 0.7 m prop is a handful of pixels at the
origin, so the screenshot rule 2 relies on shows an apparently empty scene — which
reads as "the operation deleted everything". Frame the subject first:

```python
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for region in area.regions:
            if region.type == 'WINDOW':
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_selected()
```

**Output format:**
```
── ✅ IMPORT ────────────────────────────────
{name} │ {faces} faces │ {x}×{y}×{z}m │ {file_size}
```

For scripted assets: import is implicit (already in Blender).

### [5] CLEANUP

Load `references/validation-checklist.md` and execute:

Execute the full cleanup sequence from `references/validation-checklist.md` § Execution Order. Check poly budget against tier from `references/topology-rules.md`.

**Print set in CONFIG: not the same sequence.** Its 0.1 mm merge broke a printable model
(PASS → FAIL) while its own count read 0; the print variant is under § Execution Order —
no merge on a model built closed, `print_check` on the STL as the count, no tier decimation.

**Poly check:** report the count against the tier. Past **2× the tier's top** → **propose decimate with before/after** (always interactive, even in auto mode); below that, say where the triangles go and keep them.

**Thin parts are never decimated** — wires, bails, loops: anything an order of magnitude
thinner than the body. A simplifier breaks them whatever the budget, and silhouette scores do not see the
holes it leaves. Rebuild each as a curve with a round bevel along the
high-poly's centreline; decimate the body only. **After decimating, compare open and
non-manifold edge counts with before, and look at a close render of every thin part.**

**A creature to animate:** its voxel skin goes through QuadriFlow (merge by distance first),
then the weights are checked on fixed poses before any loop is built by hand
(`references/characters.md` § Retopology: QuadriFlow first). No session did it unasked.

**Auto mode:** non-destructive cleanup runs automatically. Decimate remains interactive.
**Guided mode:** show each step, wait for validation.

**Print set in CONFIG:** after any repair (union, remesh, decimate), run `tools/print_check.py`
with `--reference` on the file it was repaired from (`references/print.md` § The tool): a
sealed, sliceable result can have lost most of the object, and only that comparison sees it.

### [5c] RIG SELECTION — characters only (rule 26)

Runs after CLEANUP, once the mesh is final and **welded** (rule 10). Never weight a
mesh with split edges: each copy of a vertex gets its own weights and the mesh opens
at every joint (rule 26). **Measure before choosing**, never the other way round:

```python
verts  = len(mesh.data.vertices)    # after the rule 10 weld
budget = verts / 20          # deform bones this mesh can actually carry
```

**Route by character first** — measured on one bent pose, `references/characters.md` §
Learned auto-rig (skin through skin, mm², lower is better):

- **A humanoid, or any mesh kiln did not build** (imported, generated) → `tools/autorig.py
  rig` (SkinTokens) when `tools/autorig.py status` exits 0. It crossed 2,985 mm² against
  Rigify's 3,926 on a kiln-built child, 20,917 against 50,680 on a generated humanoid with a
  hand fused to its hip. A generated quadruped: rig it both ways, keep the better — on the
  one measured (a proxy) kiln's rig won, 3,244 against 4,793.
- **A quadruped kiln built** → the hand-built rig in the table below: SkinTokens bent kiln's
  cat better (2,393 against 2,698) but walked it worse (527 mm² mean against 359).
- **Not installed** → say so with those numbers, offer `/kiln setup` (asked first, 5.6 GB),
  and rig from the table below meanwhile — worse on both humanoids measured.

`autorig.py` fails naming the bone when a limb comes back short (a hand fused to the hip):
separate the limb in the mesh, or `--allow-missing` it if the user accepts a rig
`quadruped.py` will refuse. Lid shells get their bones; ears need `--ears`. Its rig still
goes through every check below — its report carries rule 26's ratio and the dead bones — and
through the bent pose, because it is not repeatable: another run on the child gave 2,193.

Then, on the kiln route, pick from what Rigify ships — bone counts measured on Blender 5.0.1:

| Mesh vertices | Choose | Deform bones | Verts/bone |
|---:|---|---:|---:|
| < 700 | **Hand-built rig, 12-20 bones.** See `references/characters.md` § Match the rig's density | 12-20 | 20-35 |
| 700 - 3,000 | `bpy.ops.object.armature_basic_human_metarig_add()` | 35 | 20-85 |
| > 3,000 | `bpy.ops.object.armature_human_metarig_add()` | 160 | 20+ |
| quadruped | **Hand-built, Mixamo-named** — `references/characters.md` § Animation-ready skeleton | 20-30 | 20+ |

**Not Rigify's quadruped metarig**: its 34 bones are named `spine`, `front_thigh.L`… (checked,
Blender 5.2.2) and `tools/quadruped.py` reads Mixamo names only — every quadruped session built
the Mixamo skeleton by hand anyway.

**A Rigify human needs ~3,200 vertices to be worth it.** Below that it is actively
worse than a small rig: on a 370-vertex figure it left 107 of its 160 deform bones
influencing nothing, smeared the rest across 8-9 bones per vertex, and detached the
head. Do not reach for the biggest rig because it is the most capable one.

**After skinning, verify — do not assume:**

```python
dead = sum(1 for vg in mesh.vertex_groups
           if not any(g.group == vg.index and g.weight > 0.01
                      for v in mesh.data.vertices for g in v.groups))
```

Any dead deform bone means the rig is too dense for the mesh. Go down a tier.
**Eyelid bones stay out of the automatic weights** — they took 2,890 of the cat's 16,002 skin
vertices (`references/characters.md` § 6. Weight Painting).
Then run the validator in `references/characters.md` § Validation Script.

**Posing a generated Rigify rig?** Its limbs ship in IK, so the FK controls do
nothing until you flip them — see `references/characters.md` § FK/IK System. This
fails silently: no error, no movement.

### [5d] ANIMATE — optional, rigged characters and articulated objects

Only when the user asks for motion. Route by **subject** — table and measurements in
`references/animation.md`:

- **Ships its own clips** → keep them.
- **Four-legged, idle or walk** → `tools/quadruped.py` (scripted, measured, exact loop, ears,
  tail and blinks included — `--blink` takes the lid's measured closing turn).
  Other quadruped moves → the asset's clips or hand keys. **Never UniMate**: measured
  unusable on four quadrupeds; `unimate.py` refuses one unless `--force`.
- **Humanoid with kiln's names** (rigged by `tools/autorig.py`) **and a move in
  `python3 tools/presets.py list`** (walk, run, jump, dance, idle, wave, punch, kick, sit…) →
  `tools/presets.py animate --asset X_rigged.glb --motion walk,run --loop`: NVIDIA Kimodo clips,
  commercial use allowed, feet planted, arms kept out of the body, cycles closed; one GLB, a
  clip per motion. Report its measures line per clip, and say where a target is missed.
- **Biped or winged, from a sentence** — a move not in the presets, a non-human biped, wings →
  UniMate:
  `python3 tools/unimate.py status` first (exit 2 = not installed, 10 = newer upstream).
  Not installed: ask first — 3.2 GB — then `setup`. The weights are **non-commercial
  (CC BY-NC 4.0)**: say so. Prompts start "An object", one motion, "in place" rather
  than "forward" (forward slid with the feet still, 0 of 8); `--loop` keeps the sample
  that loops best.
- **Articulated object** (lamp, chest, door) → keyframe the rigid parts.

Whatever the route, follow `references/animation.md` § Rules for scripted animation —
every rule there is a cycle that looked wrong until it was measured.

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

### [6] OPTIMIZE (interactive in guided mode)

**Print set in CONFIG: skipped.** The deliverable is the print output (`print/`, below); the
GLB is a preview for the user, exported plain (no Draco, no texture pass) as the web output
`web/{name}_final.glb`. **No
`_original.glb`** — nothing is optimized, so there is nothing to keep it for; the file
`print_check --reference` reads is `{name}_{part}_parts.blend`, one per printed part (`print.md` § The tool).

**Auto mode, glTF target:** apply the default preset without asking — textures to
WebP, resized to the target's cap from `references/uv-materials.md` § Texture
Resolution per Use Case — **1024 for web/glTF, the default, whatever the tier**;
2048 only when the brief asks for close-ups or targets console/PC — then Draco — as individual steps (rule 20). It does not touch
geometry, and `_original.glb` survives, so it is not a destruction under rule 6.
Report before/after sizes, and say that Draco needs a decoder on the client.
Simplify, decimate and LOD stay interactive in every mode.

**Hand over an uncompressed preview too: `{name}_preview.glb`, a copy of `_original.glb`**
(no Draco, no WebP). The Mac's Finder preview (Quick Look) opened neither a Draco nor a
WebP `_final.glb` on the October 2026 sessions — seen by the user, every time — so a user
who double-clicks the deliverable sees nothing. Say in the hand-over which file is for the
site and which one opens on a Mac. Check it: `extensionsUsed` in the preview's JSON names
neither `KHR_draco_mesh_compression` nor `EXT_texture_webp`.

Why: the quality bench measured auto mode stopping here on 3 of 6 briefs, leaving
a 16 MB `_final.glb` for a 724-triangle chair. **`_final.glb` is written only after
this phase** — before it, the export is `_original.glb`, scripted assets included.

**Each output in its own folder** of the model's: the web one is `web/{name}_final.glb`;
game `game/{name}_game.fbx`, AR `ar/{name}_ar.usdz` + `ar/{name}_ar.glb`, print
`print/{name}_print.3mf` + `print/{name}_print_{part}.stl` — made when asked, never
empty folders (`references/naming-conventions.md` § Outputs). The source stays at the root:
`_original.glb`, the `.blend`, the log, the preview.

**Guided mode** — propose options:
- `gltf-transform` → texture compression KTX2, meshopt
- `gltfpack` → mesh simplification, auto LOD
- Both
- Custom parameters
- Skip

After each tool: show before/after. "Keep? (yes / no / adjust)"

Load `references/cli-tools.md` for commands and parameters.

**Standalone:** `/kiln optimize` works outside the pipeline.

**Output format:**
```
── ✅ OPTIMIZE ──────────────────────────────
{before_size} → {after_size} (−{percent}%) │ {tools_used}
Keep? (yes / no / adjust)
```

### [7] EXPORT

Load `references/export-targets.md`.

```
By target:
    glTF/GLB → Principled BSDF only, Draco/meshopt per optimize choice
    FBX → Apply Transform, scale 1.0, version 7.4
    USDZ → Reality Converter or usdzconvert (macOS)
    Print → STL, global_scale=1000 (mm); 3MF too if the extension is installed
```

**An animated creature:** no hand-over before the matcap review, close up, at rest and mid-walk
(`references/characters.md` § Matcap before delivery) — on the cat it found four faults the
measures had missed.

**Print set in CONFIG:** the export ends with `tools/print_check.py --process … --slicer …`
(PrusaSlicer when installed) on the STL. **PASS is required**; otherwise report each FAIL line
as the tool printed it — never call the file printable. The hand-over gives the size it was
modelled for and the check's `SCALE` line: people rescale in the slicer, and the STL does not
say how far down it holds (`print.md` rule 9).

**Axis conversion** handled automatically (Blender -Y/Z → glTF +Z/Y).

Save in output folder per **storage mode** (compact or full). See `references/naming-conventions.md` for folder structure details. The .blend file always contains the full history — compact mode is safe.

Save the .blend file via `execute_blender_code`: `bpy.ops.wm.save_as_mainfile(filepath=...)`. Only when the open file is yours alone — otherwise from the headless Blender that built it (rule 16). Set `bpy.context.preferences.filepaths.save_version = 0` first: no `.blend1` backup is left beside it to ask about (Blender 5.2.2: saved twice, none).

**Output format:**
```
── ✅ EXPORT ────────────────────────────────
{name}_final.{ext} │ {final_size} │ {final_faces} faces │ {format}
.blend saved │ log written
```

**Kiln Studio:** in an interactive session, close the live view once `_final` is written
(`studio.py live <name> --end`), then run `studio.py checks <name>` and report its WARN
lines with the export summary: triangles against the tier, ground contact, texture caps,
Draco/WebP on `_final`, licences. If Studio was not started at BRIEF (Live view off), start
it now on the project root and give the user its URL in one line — they can look at the
model there, pin notes on it, and run `/kiln studio` to hand them to you.
`python3 <skill>/studio/studio.py` (add `--no-open` when Auto-open links is false). Not in
batch runs. Load `references/studio.md`.

**End-of-session cleanup:** At the end of a multi-asset session, propose:
> "Session complete: {n} assets, {total_size} MB. Cleanup intermediate files? (yes / no / pick per asset)"
>
> In **full** mode: list intermediate files per asset with sizes, let user choose.
> In **compact** mode: already minimal, skip.

---

## /kiln status

Show current state at any time:

```
── ⚒️ {name} ──────────────────────────────
{target} │ {tier} │ {style} │ {mode}

CONFIG ✅ → BRIEF ✅ → SOURCE ✅ → IMPORT ✅ → CLEANUP ✅ → TEXTURE ◀️ → OPT ⬜ → EXPORT ⬜

Stats    {faces} faces │ bbox {x}×{y}×{z}m
Files    _original.glb ({size}) │ _clean.glb ({size}) │ .blend
Next     {description}
```

Note: "Reusable prompts" (concept art prompt, generation params) are stored in the log file only — not shown in status output.

---

## Standalone Commands

These commands work independently — no need to run the full pipeline.

**Kiln Studio shows what you are on.** When a command changes models that a running
Kiln Studio shows (`studio.py status` answers for the project), tell it before the first
change and as you go, so the page puts a dot on each model — waiting, breathing while you
work on it, green when done: `studio.py work start <asset>... --label "optimize"` (in the
order you will take them; the first is active), `studio.py work next` after each one,
`studio.py work end` if you stop early. One model is a run of one. Not in batch runs.
`references/studio.md` § 5 has the rest.

### /kiln inspect

Inspect any 3D file without importing it into the pipeline.

```
── 📐 {filename} ({file_size}) ─────────────
Faces    {count} (tri: {tris} │ quad: {quads} │ ngon: {ngons})    Verts    {count}
Objects  {count} [{names}]                                         Materials {count} [{names}]
Bbox     {x} × {y} × {z} m                                        Textures  {count} [{resolutions}]
Anim     {count or "none"}                                         Rig       {yes/no — bone count}
```

Use `execute_blender_code` to import temporarily, read stats via Python API, then undo/delete.
For GLB: can also use `gltf-transform inspect {path}` if installed.

**For a print** (the user says so, or the file is an STL or a 3MF): add `tools/print_check.py`'s
verdict — `--slicer` when PrusaSlicer is installed — and quote each FAIL and warning as the tool
printed it. Never call the file printable on the stats alone.

### /kiln cleanup

Clean up a mesh already open in Blender (or import one first).

1. `get_scene_info()` — identify what's in the scene
2. Ask user which object(s) to clean, or "all"
3. Load `references/validation-checklist.md` — execute full cleanup sequence
4. `get_viewport_screenshot()` after each step
5. If poly count high: propose decimate (always interactive)

**For a print** — a model the user made and wants to print (`/kiln cleanup model.stl`): not the
sequence above. Load `references/print.md` § A model you bring, then: `print_check` on the file,
`tools/flatten.py` to a NEW file (never over theirs), `print_check` again, and show both verdicts
and flatten's report — regions flattened, kept as shapes, past the tolerance, the largest move —
with a matcap close-up of the largest flattened face before and after. Holes are reported, not
filled: the slicer closes small ones, the user decides the rest.

### /kiln texture

Texture an untextured mesh (white mesh from AI generation, or any mesh without materials).

1. `get_scene_info()` — verify mesh exists, check current materials
2. If mesh has no materials or only default: proceed
3. If mesh already has materials: "This mesh already has {n} materials. Re-texture anyway? (yes / no / add to existing)"
4. Load `references/texturing-strategy.md`
5. Follow the texturing strategies in order:
   - Geometric analysis + PolyHaven PBR
   - Procedural Blender materials
   - Assisted manual texturing
6. `get_viewport_screenshot()` after applying materials

**Note on monolithic meshes (AI-generated):** the geometric analysis clusters faces by normal direction, position, and curvature. This works on single-object meshes — it will identify zones (e.g. "top faces = seat", "vertical faces = legs") even without object separation. Results may need manual adjustment for complex shapes.

### /kiln animate

Animate a rigged asset (standalone PHASE 5d): `/kiln animate SK_Cat.glb walk, idle` or
`/kiln animate dragon.glb "flaps its wings"`. Load `references/animation.md` first.

1. **Inspect the rig** — `get_scene_info()`, then the bones. Run
   `tools/bind_rigid_parts.py` on the file: it folds bone-parented parts into the skin and
   prints `posture quadruped` for a four-legged rig.
2. **No rig, or a coarse one** (a limb that must move on its own has no chain, one bone
   per leg): say so, and offer PHASE 5c (`references/characters.md` § Animation-ready
   skeleton) before going further. Do not animate a rig that cannot bend where asked.
3. **Its own clips?** List the actions. If the asked-for moves already exist, offer them
   first — hand-made clips beat every generator measured.
4. **Route by subject** (`references/animation.md` § Pick the route from the subject):
   - quadruped, idle or walk → `tools/quadruped.py --motions idle,walk`, then report the
     root speed it prints: the game moves the character at that speed;
   - quadruped, any other move → its own clips or hand keys; **not UniMate**;
   - humanoid with kiln's names, a move `tools/presets.py list` has → `tools/presets.py animate
     --motion … --loop` (commercial use allowed); report each clip's measured line and the root
     speed of each loop;
   - any other biped (a move not in the presets, a non-human biped) or winged → UniMate:
     `tools/unimate.py status` first (not installed: ask — 3.2
     GB; newer upstream: offer `setup --update`), say the weights are **non-commercial**,
     write each move as "An object … in place.", run `animate --loop --reps 4`, and stop
     at the label review it prints (step 1 of its Run it section);
   - articulated object → key the rigid parts, following § Rules for scripted animation.
5. **Show every kept clip before calling it done** (rule 2): render it or play it in the
   viewport, and say which route made it and, for UniMate, which sample was kept; for the
   presets, which take, and their licence (NVIDIA Open Model License).
6. **Export** (PHASE 7): one GLB with every action (`quadruped.py` and `presets.py` write it), or one per clip
   if asked (`--per-clip`).

### /kiln optimize

Optimize a GLB file with CLI tools.

1. Ask for input file path (or use current pipeline asset). A Kiln Studio asset name
   (`/kiln optimize barrel`, as the Checks tab suggests) means its `_final` file.
2. Show current stats: file size, face count, texture sizes
3. Load `references/cli-tools.md`
4. Propose options:
   - `gltf-transform resize` — resize textures (1024, 512, etc.)
   - `gltf-transform webp` — convert textures to WebP
   - `gltf-transform draco` — Draco mesh compression
   - `gltfpack` — mesh simplification + LOD generation
   - Custom parameters
5. Execute chosen options sequentially
6. Show before/after:
   ```
   ── ✅ OPTIMIZE ──────────────────────────────
   {before_size} → {after_size} (−{reduction}%) │ {tools_used}
   Keep? (yes / no / adjust)
   ```
7. User chooses to keep, discard, or adjust parameters

### /kiln convert

Convert between 3D formats.

1. Ask for input file path and target format
2. Supported conversions:

| From | To | Method |
|---|---|---|
| GLB → FBX | `execute_blender_code` (import GLB, export FBX) |
| GLB → USDZ | Reality Converter (macOS) or usdzconvert |
| FBX → GLB | `execute_blender_code` (import FBX, export GLB) |
| OBJ → GLB | `execute_blender_code` |
| .blend → GLB/FBX/USDZ | `execute_blender_code` (export from open scene) |

3. Load `references/export-targets.md` for format-specific settings
4. Run material export audit before GLTF export (Iron Rule 19)
5. Show output stats:
   ```
   ── ✅ CONVERT ───────────────────────────────
   {input} → {output} │ {size}
   ```

### /kiln search

Search 3D asset marketplaces.

1. Ask for search keywords (or use current brief)
2. Load `references/sourcing-strategy.md`
3. Search in parallel:
   - **PolyHaven** — fully free, CC0. Search via API.
   - **Sketchfab** — filter downloadable + free only (requires API token)
4. Present results:
   ```
   ── 🔎 "{query}" ─────────────────────────
    #  │ Source     │ Name            │ Faces │ License │ Link
    1  │ PolyHaven  │ Wooden Chair    │ 2.3K  │ CC0     │ polyhaven.com/a/...
    2  │ PolyHaven  │ ...             │ ...   │ CC0     │ ...
    6  │ Sketchfab  │ Medieval Chair  │ 4.1K  │ CC-BY   │ sketchfab.com/...
    7  │ Sketchfab  │ ...             │ ...   │ ...     │ ...

   "pick 1" │ "open 2,6" │ "refine: wooden stool" │ "create instead"
   ```
5. User can: pick a number to download, open links, refine search, or cancel

### /kiln studio

Kiln Studio, a local web page (`studio/studio.py`, Python standard library only) where
the user browses every model in the project, pins notes on them, compares versions, and
checks your fixes. Load `references/studio.md` and follow it.

1. Run `studio.py notes` (or take the asset given as argument).
2. Notes waiting → act on them, one asset per pass: `studio.py work start <asset>...
   --label "acting on notes"` with the assets you will take, `studio.py show <asset>`,
   read each note's close-up and screenshot, change the model, re-export to the same file,
   `studio.py reply <asset> <note> "…" --status addressed`, then `studio.py work next`.
   Never mark one resolved.
3. Nothing waiting → start Studio (`studio.py [project]`), give the URL, stop.

When the user points at Studio without naming the model — "what am I looking at",
"fix this", "this note", "here" — call the kiln-studio MCP tool `get_selection` first
(`mcp__plugin_blender-kiln_kiln-studio__get_selection`): it names the model, stage, camera
and picked note the open page shows. `references/studio.md` § 11 has the other three.

Its Checks tab, and `studio.py checks <asset>`, read kiln's rules off the file — tier
range, size, ground, texture cap, compression, licences — with the fidelity measure and,
in a batch folder, the wizard's token estimate.

### /kiln help

Display all available commands from the Commands table above.

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

Each asset produces `{name}_log.md`:

```markdown
# {Asset Name} — Production Log

## Config
- Type: {type}
- Target: {target}
- Tier: {tier}
- Style: {style}
- Mode: {mode}

## Reference Image
- Path: {path or URL or "none"}
- Brief enrichment: [list of details extracted from image, if any]
- Visual comparison: {verdict — "close match" / "partial match" / "loose interpretation" / "N/A"}

## Prompts (copy-paste ready)
- Concept art: "{exact prompt}" (source: {flux-schnell|nano-banana|user image|user URL})
- Concept iterations: ["{edit1}", "{edit2}"]
- Generation params: backend={space}, seed={seed}, and the backend's own settings

## Source
- Method: {AI / scripted / marketplace}
- HF Space: {url} (if AI)
- Marketplace: {url} (if marketplace)

## Pipeline
- Import: {faces} faces, {size}, bbox {dimensions}
- Cleanup: {before} → {after} faces, operations: [merge doubles, recalc normals, ...]
- Texturing: zones [{zone1}: {texture}, {zone2}: {texture}]
- Optimize: {tool}, {before_size} → {after_size}
- Export: {format}, {final_size}, {final_faces}
- Rounds (reference image): v{n}: silhouette {iou}, face {iou} (f {f}, offset {mm}); changed
  {one thing}; kept / undone
- Photo projection (if the user said yes): fitted IoU {iou}, SSIM {before} → {after}, excluded {parts}
- Print check, one line per printed part: {part}: {PASS/FAIL}, {dimensions} mm, {parts} part(s),
  supports {yes/no — from the slice, not from the overhang %}, smallest scale {N} %, warnings {…}

## Licenses
- {resource}: {license} {attribution if needed}

## Checkpoint
<!-- Scripted print: SOURCE and IMPORT are one step (the script builds at size), OPTIMIZE is
     logged as skipped — the checkpoints are BRIEF, SOURCE/IMPORT, CLEANUP, EXPORT + check. -->
- Last completed step: {step}
- Timestamp: {datetime}
```

**Write the log at the end of every phase, not at the end of the run** (Iron Rule 7). A run that stops
mid-way — a crash, a context limit — resumes from it; a log left at BRIEF while the model went
through seven versions records nothing of what was tried or undone.

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
| Photo's markings projected onto the model (optional, after the last review) | `references/photo-projection.md` |
| Kiln Studio: viewer, the user's notes, before/after, history | `references/studio.md` |
