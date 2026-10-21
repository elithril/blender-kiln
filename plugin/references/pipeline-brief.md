# Pipeline — [1] CONFIG and [2] BRIEF

> Read before [1] CONFIG. Rule numbers are SKILL.md's Iron Rules.

## [1] CONFIG — Collect Parameters

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
| **Live view** | on (interactive), off (batch) | Kiln Studio reloads the model after each phase — see SKILL.md § Pipeline, Live view |
| **Output folder** (absolute path) | `./generated-assets/` | Confirmed at launch |

**Detail tier ranges:** see `references/topology-rules.md` § Detail Tiers. Soft ranges — up to 2× the top is fine when spent where it shows; report it, never block.

**Scene:** auto-detected via `get_scene_info()` — not asked.

## [2] BRIEF — Confirm Understanding

**If a reference image exists** (user-provided path, URL, or drag-and-drop), analyze it and enrich the brief with visible details not already mentioned (e.g. number of legs, curvature, handle shape, proportions).

**CRITICAL: the user's brief ALWAYS wins over image analysis.** If the brief explicitly excludes or contradicts something visible in the image (e.g. "like this but without armrests", "same shape but rounder"), respect the brief — do NOT reintroduce contradicted details from the image. The image is a starting point; the brief is the final word.

Reformulate the enriched brief for confirmation:
> "OK: medieval wooden chair, stylized, for web (glTF), tier balanced (1.5-5K tris). From your reference image I also see: curved backrest, 4 turned legs, cross braces. Good?"

**With a reference image, the confirmation also settles what one photo cannot say**
(`references/reference-fidelity.md` § 1): the **real size** (ask, or state the usual size
as an assumption), the **camera's elevation** read on a visible rim, and — for an asset
whose back, sides or underside will be seen — **a request for side and top views**. In
auto mode, do not block on them: state the assumptions and carry them into the log.
