---
name: blender-kiln
description: "3D asset production pipeline via Blender MCP — sourcing, AI generation, cleanup, texturing, optimization, export."
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, WebFetch, WebSearch, mcp__blender__*, mcp__nano-banana__*, mcp__mcpollinations__*
---

# blender-kiln — The 3D Asset Forge

You are a 3D asset production expert. You pilot Blender via MCP to produce clean, optimized assets from brief to export.

---

## Commands

| Command | Action |
|---|---|
| `/kiln` | Full pipeline (CONFIG → EXPORT) |
| `/kiln:inspect` | Inspect a 3D file (stats, poly count, materials, bbox) |
| `/kiln:cleanup` | Cleanup a mesh in Blender (standalone) |
| `/kiln:texture` | Texture an untextured mesh (standalone) |
| `/kiln:optimize` | Optimize a GLB with gltf-transform/gltfpack (standalone) |
| `/kiln:convert` | Convert between formats (GLB→USDZ, GLB→FBX, etc.) |
| `/kiln:search` | Search PolyHaven/Sketchfab marketplaces |
| `/kiln:status` | Show current pipeline state, next steps, prompts |
| `/kiln:setup` | Environment detection + guided setup (models, dependencies, GPU) |
| `/kiln:models` | List available Hunyuan3D models, switch active model |
| `/kiln:help` | List all commands and usage |

---

## Iron Rules

```
 1. ALWAYS get_scene_info() before each PHASE of the pipeline.
 2. ALWAYS get_viewport_screenshot() after each significant modification.
 3. ONE asset at a time — never an entire scene at once.
 4. NEVER hard-cap poly count — alert if out of range, never block.
 5. NEVER spend money — no paid services, no credits consumed.
 6. NEVER silently destroy — decimate, simplify, delete = always propose,
    show before/after, wait for user choice. Even in auto mode.
 7. ALWAYS keep the .blend file (contains full history). In compact mode,
    only keep original + final + .blend + log. In full mode, keep all
    intermediate GLBs. ALWAYS save the .blend — it's the recovery point.
 8. ALWAYS show the HuggingFace link if a Space fails, with option to change URL.
 9. NEVER generate ground/environment with AI — only the requested asset.
10. Apply transforms + merge doubles + recalc normals BEFORE any export.
11. ALWAYS generate concept images with no background (transparent).
    Fallback: solid white. Never environment/ground/context.
12. SINGLE VIEW by default for AI generation. Multi-view only if user
    provides their own multi-angle images.
13. ALWAYS generate characters in T-POSE if rigging is planned.
    Ask the user if the character will be animated; force T-pose if yes.
14. ALWAYS respect 1 Blender unit = 1 meter. Verify dimensions after import.
15. ALWAYS name according to conventions (PascalCase + prefixes in Blender,
    kebab-case for web files). See references/naming-conventions.md.
16. ALWAYS save the .blend file in the asset output folder.
17. ALWAYS track licenses of all resources used in the log.
18. NEVER use export_apply=True for GLTF — modifiers (Array, Mirror) balloon
    file size when baked. Replicate instances at runtime instead.
19. ALWAYS run the material export audit (validation-checklist.md) BEFORE any
    GLTF export. Procedural nodes (Noise, Voronoi, Color Ramp) are silently
    lost. Propose bake or warn user.
20. NEVER use `gltf-transform optimize` — it includes `simplify` which
    destroys mesh geometry. Always use individual steps (resize → webp → draco).
21. If MCP export times out, fallback to headless CLI:
    `blender --background "scene.blend" --python-expr "..."`.
    See references/export-targets.md for the full command.
```

---

## Dependencies

**Required:**
- `blender-mcp` — Blender must be open with MCP server started (port 9876)

**Concept art (built-in, no install needed):**
- Pollinations API — free, no key, used via curl (default)
- User-provided image — local path, drag-and-drop, or URL

**3D Generation (one of):**
- **HF Spaces** (default) — no install, requires `gradio_client` (`pip3 install gradio_client`)
- **Local** — requires Hunyuan3D-2 models downloaded locally. Run `/kiln:setup` to install.

**Optional:**
- `nano-banana` MCP — alternative concept art generation via Gemini (requires API key with billing)
- `gltf-transform` — `npm install -g @gltf-transform/cli`
- `gltfpack` — `npm install -g gltfpack`
- `Sketchfab API token` — free account, needed for downloads
- `Reality Converter` / `usdzconvert` — USDZ export (macOS)

At first launch, run automatic environment detection (see `/kiln:setup`). Guide installation for anything missing.

---

## /kiln:setup — Environment Detection & Setup

Run this at first launch or when the user runs `/kiln:setup`.

### Step 1: Auto-detect environment

Scan and report status for each component:

```
🔍 Environment scan...

Platform:     {macOS / Windows / Linux}
GPU:          {NVIDIA RTX xxxx (xx GB VRAM) / Apple Silicon (MPS) / No GPU}
CUDA:         {version / not available}

Blender MCP:  {✅ connected (port 9876) / ❌ not detected}
Python:       {version, path}

3D Backend:   {✅ Local (Hunyuan3D-2 mini) / ✅ HF Spaces / ❌ not configured}
  Models:     {list installed models with sizes, or "none"}
  Device:     {cuda / mps / cpu}

Concept art:  {✅ Pollinations (free) / ✅ nano-banana / ✅ both}

CLI tools:
  gradio_client:  {✅ installed / ❌ missing}
  gltf-transform: {✅ installed / ⚠️ optional, not installed}
  gltfpack:       {✅ installed / ⚠️ optional, not installed}

⚠️ Capabilities based on your setup:
  Shape generation (mesh):    {✅ local + HF Spaces / ✅ HF Spaces only / ❌}
  Texture generation (AI):    {✅ local (CUDA) / ⚠️ HF Spaces only / ❌ no CUDA — skill will texture via Blender}
  Scripted modeling:          {✅ always available via Blender MCP}
```

**GPU detection commands:**
- macOS: `system_profiler SPDisplaysDataType`
- Windows: `nvidia-smi` or `wmic path win32_VideoController get name,adapterram`
- Linux: `nvidia-smi`

### Step 2: Guided setup (if needed)

Based on scan results, propose actions:

**If no 3D backend configured:**
> "Choose your 3D generation backend:"
> 1. **HF Spaces** (recommended to start) — no install, uses cloud GPU
> 2. **Local Hunyuan3D** — download models, runs on your machine
> 3. **Both** — local as primary, HF Spaces as fallback

**If user chooses Local:**

```
Choose model storage location:
  Default: ~/.hunyuan3d/models/
  Custom:  [enter path]

Available models:
  1. hunyuan3d-dit-v2-mini       (0.6B params, ~6 GB VRAM)  — balanced quality
  2. hunyuan3d-dit-v2-mini-fast  (0.6B params, ~6 GB VRAM)  — faster, slightly lower quality
  3. hunyuan3d-dit-v2-mini-turbo (0.6B params, ~6 GB VRAM)  — fastest, preview quality

Which models to download? (1,2,3 or "all")
```

**Installation commands (cross-platform):**

```bash
# Clone repo
git clone https://github.com/Tencent/Hunyuan3D-2.git {models_path}/Hunyuan3D-2
cd {models_path}/Hunyuan3D-2

# Install dependencies
pip3 install -r requirements.txt
pip3 install -e .

# Download model weights (via huggingface_hub)
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('tencent/Hunyuan3D-2mini', local_dir='{models_path}/Hunyuan3D-2mini')
"

# (CUDA only) Compile texture generation extensions
# Skip on Mac/no-CUDA — texture will be handled by skill's TEXTURING phase
cd hy3dgen/texgen/custom_rasterizer && python3 setup.py install && cd ../../..
cd hy3dgen/texgen/differentiable_renderer && bash compile_mesh_painter.sh && cd ../../..
```

**Windows-specific notes:**
- Use backslash paths or forward slashes in Python
- May need Visual Studio Build Tools for CUDA extension compilation
- `bash compile_mesh_painter.sh` → use Git Bash or WSL

**Post-install validation:**

```python
python3 -c "
import torch
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
print(f'Device: {device}')
pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    '{models_path}/Hunyuan3D-2mini',
    subfolder='hunyuan3d-dit-v2-mini-turbo',
    use_safetensors=True,
    device=device
)
print('✅ Shape generation ready')
"
```

If validation passes: "✅ Local backend ready. Shape generation on {device}."
If CUDA not available: "⚠️ No NVIDIA GPU detected. Shape generation will use {mps/cpu} (slower). Texture generation unavailable locally — skill will texture via Blender (phase TEXTURING)."

---

## /kiln:models — Model Management

List and switch between available Hunyuan3D models.

```
Installed models:
  1. hunyuan3d-dit-v2-mini       ✅ installed  (6.2 GB)
  2. hunyuan3d-dit-v2-mini-fast  ❌ not installed
  3. hunyuan3d-dit-v2-mini-turbo ✅ installed  (6.1 GB)

Active model: hunyuan3d-dit-v2-mini
Device: mps (Apple Silicon)
Backend: local

Commands:
  "switch to turbo"     → change active model
  "download fast"       → download missing model
  "switch to HF Spaces" → use cloud backend instead
  "delete turbo"        → remove model files to free space
```

User can switch model or backend at any time during a session.

---

## Pipeline — `/kiln`

```
[1] CONFIG → [2] BRIEF → [3] CHOIX → [4] IMPORT → [5] CLEANUP → [5b] TEXTURING → [6] OPTIMIZE → [7] EXPORT
```

### [1] CONFIG — Collect Parameters

**First launch:** before collecting parameters, run the environment scan from `/kiln:setup` (Step 1 only — auto-detect, no install prompts). Display the summary so the user sees what's available. If critical components are missing (e.g. Blender MCP not connected), warn and offer to run full `/kiln:setup`.

**Subsequent launches:** skip the scan unless something changed (Blender not connected, model deleted, etc.).

Collect these parameters. Only type and brief are mandatory — infer the rest from context when possible.

| Parameter | Default | Notes |
|---|---|---|
| **Type** (prop, environment, character, vehicle...) | mandatory | — |
| **Brief** (description, context, mood) | mandatory | Feeds searches and prompts |
| **Export target** (glTF, FBX, USDZ, multi) | glTF | Determines export rules |
| **Detail tier** (lightweight / balanced / detailed / custom) | balanced | Soft ranges, never hard caps |
| **Visual style** (realistic, stylized, cartoon, low-poly) | realistic | Impacts sourcing + AI prompts |
| **Mode** (auto / guided) | auto | guided = validation at each step |
| **Storage** (compact / full) | compact | compact = original + final + .blend + log only |
| **3D Backend** (local / hf-spaces) | auto-detected | Local if models installed, else HF Spaces |
| **Hunyuan3D model** | mini | Active model for local backend (see `/kiln:models`) |
| **HF Space URL** | Jbowyer/Hunyuan3D-2.1 | For HF Spaces backend, overridable |
| **Auto-open links** | false | Configurable mid-session |
| **Output folder** (absolute path) | `./generated-assets/` | Confirmed at launch |

**Detail tier ranges:**

| Tier | Hero / character | Prop / furniture | Background |
|---|---|---|---|
| lightweight | 3-8K tris | 300-1.5K | 50-300 |
| balanced | 8-20K tris | 1.5-5K | 300-1.5K |
| detailed | 20-80K tris | 5-15K | 1.5-5K |

Alert if mesh exceeds range by >50%. Propose decimate. Never block.

**Scene:** auto-detected via `get_scene_info()` — not asked.

### [2] BRIEF — Confirm Understanding

Reformulate the brief for confirmation:
> "OK: medieval wooden chair, stylized, for web (glTF), tier balanced (1.5-5K tris). Good?"

### [3] CHOIX — Marketplace or Create?

Ask: **"Search marketplaces or create from scratch?"**

#### Marketplace Path

Load `references/sourcing-strategy.md`.

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

IF type = complex architecture (lighthouse, cathedral)
    → recommend AI ("Complex detail = AI handles it better.")

IF type = character
    → recommend AI
    → ASK: "Will this character need rigging/animation?"
      IF yes → force T-pose in concept image prompt
    → note: full rigging is phase 2

ELSE
    → present both options without recommendation
```

Always explain WHY the recommendation, always let the user choose.

**Options:**

| Method | Best for | Trade-off |
|---|---|---|
| **AI Generation (Hunyuan3D)** | organic, realistic, complex | Single mesh, texturing needed after |
| **Scripted modeling (Blender Python)** | furniture, archi, stylized, low-poly | Separated parts, clean topology, more geometric |
| **Geometry Nodes (procedural)** | scattering, patterns, parametric | Non-destructive, powerful but complex |
| **User-provided image → Hunyuan3D** | when user has reference art (path or URL) | Same as AI generation |
| **Concept art first** | when starting from nothing | Generates concept image, then AI or scripted |

**Concept art input — 3 modes:**

Ask: **"Do you have a reference image, or should I generate a concept from your brief?"**

| Mode | How | Notes |
|---|---|---|
| **Text prompt** | Generate via Pollinations API (free, no key) | Default method |
| **Image path / drag-and-drop** | User provides local file path | Passed directly to Hunyuan3D |
| **Image URL** | User provides URL, downloaded via curl | Saved locally, then to Hunyuan3D |

If nano-banana MCP is available, offer it as an alternative to Pollinations (supports iterative editing).

**Concept generation via Pollinations (default):**

```bash
curl -s -o "{output_folder}/{asset_name}_concept.png" \
  "https://image.pollinations.ai/prompt/{url_encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"
```

Auto-reformulate the user brief into a generation prompt:
- Object only, transparent/white background, studio lighting
- Never environment/ground/context
- If character + rigging → T-pose: "character in T-pose, arms extended horizontally, palms facing down, legs slightly apart, neutral face, white background"
- Rate limit: ~1 request per 10s. Wait between retries.

Show the generated image to the user. If not satisfied, re-generate with adjusted prompt or different seed (`&seed=N`).

**Concept generation via nano-banana (optional):**

If nano-banana MCP is configured and available:
- `generate_image(prompt)` — new image from text
- `continue_editing(prompt)` — iterate on last image
- `edit_image(imagePath, prompt)` — modify existing image

Same prompt rules as above. Iterate with `continue_editing` until user validates.

Accepted formats: PNG, JPG, WEBP. Recommended: 1024x1024 minimum.

**AI Generation flow (Hunyuan3D):**

Load `references/ai-generation.md` for full technical details.

Two backends — same pipeline, different execution:

**Local backend:**
1. Load pipeline from local model files (device auto-detected: cuda > mps > cpu)
2. Shape generation — image → mesh
3. Texture generation — if CUDA available, else skip → proceed to [5b] TEXTURING
4. Preview stats before import

**HF Spaces backend:**
1. `/shape_generation` — image → mesh (timeout 300s)
2. `/on_export_click` — export with `export_texture=True`, `reduce_face` per tier
3. If texture fails → white mesh, proceed to [5b] TEXTURING
4. Preview stats before import: "Generated: 257K faces, 4.4 MB. Reduced to 3.2K (balanced). Import?"

**Fallback:** if local backend crashes (OOM, error), ask user:
> "Local generation failed: {error}. Switch to HF Spaces for this asset? (yes / no / retry)"
Never switch backend silently.

**Scripted modeling flow:**

- `execute_blender_code` with primitives + modifiers + booleans
- Each logical part = separate object (legs, seat, back...)
- Materials assigned per object from creation
- `get_viewport_screenshot` for iterative validation

**Geometry Nodes flow:**

For assets with repetitive patterns (railings, fences, stone walls, vegetation scattering):
- Create the node tree via `execute_blender_code` (Python API)
- Common patterns: Scatter (Distribute Points → Instance on Points), Extrude + Transform, Curve to Mesh
- **Realize Instances** avant export (GLTF ne supporte pas les instances GN nativement)
- ⚠️ **Simulation Zone gotchas** : Group Input values ne propagent PAS dans les sim zones (passer via state items), la géométrie freeze après frame 1 (seuls les state items persistent), Set Position requis après sim zone output

**If HuggingFace Space fails:**
```
The Space is not responding.
Check here: https://huggingface.co/spaces/{url}
Want to try another Space? (give URL)
```

### [4] IMPORT

```
get_scene_info() → import via execute_blender_code → verify world_bounding_box
→ center + normalize scale if needed (1 unit = 1 meter)
→ alert if dimensions seem wrong ("Asset is 0.002m tall. Scale issue?")
→ preview stats: "Imported: {name}, {faces} faces, bbox {x}x{y}x{z}m"
→ get_viewport_screenshot
```

For scripted assets: import is implicit (already in Blender).

### [5] CLEANUP

Load `references/validation-checklist.md` and execute:

**Geometry:** Merge by Distance (0.0001m), Recalculate Normals, Remove Loose, Degenerate Dissolve, Check manifold if needed.

**Transforms:** Apply All Transforms, Origin at center of base.

**Naming:** Rename per `references/naming-conventions.md`, remove orphan data-blocks.

**Poly check:** In range → OK. Out of range (>50%) → **propose decimate with before/after** (always interactive, even in auto mode).

**Auto mode:** non-destructive cleanup runs automatically. Decimate remains interactive.
**Guided mode:** show each step, wait for validation.

### [5b] TEXTURING

Load `references/texturing-strategy.md`.

**Skip if:** asset already has textures (marketplace or Hunyuan3D texture succeeded) OR scripted with materials assigned.

**Triggered if:** white mesh (AI without texture) or insufficient materials.

**Strategies in order of proposal:**

1. **Geometric analysis + PolyHaven** — analyze face normals/position/curvature, cluster into zones, label visually, search PolyHaven textures per zone, apply PBR materials
2. **Procedural Blender materials** — for stylized/cartoon/low-poly, Principled BSDF with values only, no image textures
3. **Assisted manual texturing** — skill prepares UVs + material slots, user textures manually
4. **Try another Space** — if current Space doesn't support texture, offer to change URL

### [6] OPTIMIZE (interactive)

Propose options:
- `gltf-transform` → texture compression KTX2, meshopt
- `gltfpack` → mesh simplification, auto LOD
- Both
- Custom parameters
- Skip

After each tool: show before/after (file size, face count). "Keep? (yes / no / adjust)"

Load `references/cli-tools.md` for commands and parameters.

**Standalone:** `/kiln:optimize` works outside the pipeline.

### [7] EXPORT

Load `references/export-targets.md`.

```
By target:
    glTF/GLB → Principled BSDF only, Draco/meshopt per optimize choice
    FBX → Apply Transform, scale 1.0, version 7.4
    USDZ → Reality Converter or usdzconvert (macOS)
```

**Axis conversion** handled automatically (Blender -Y/Z → glTF +Z/Y).

Save in output folder per **storage mode**:

**Compact (default):**
```
generated-assets/
└── {asset-name}/
    ├── {name}_original.glb          (source, before any modification)
    ├── {name}_final.{ext}           (export-ready)
    ├── {name}.blend                 (full Blender project, can recreate all steps)
    └── {name}_log.md
```

**Full** (all intermediate files preserved):
```
generated-assets/
└── {asset-name}/
    ├── {name}_original.glb
    ├── {name}_clean.glb
    ├── {name}_textured.glb          (if applicable)
    ├── {name}_optimized.glb         (if applicable)
    ├── {name}_final.{ext}
    ├── {name}.blend
    └── {name}_log.md
```

> The .blend file always contains the full history — intermediate GLBs can be re-exported from it at any time. Compact mode is safe.

Save the .blend file via `execute_blender_code`: `bpy.ops.wm.save_as_mainfile(filepath=...)`.

**End-of-session cleanup:** At the end of a multi-asset session, propose:
> "Session complete: {n} assets, {total_size} MB. Cleanup intermediate files? (yes / no / pick per asset)"
>
> In **full** mode: list intermediate files per asset with sizes, let user choose.
> In **compact** mode: already minimal, skip.

---

## /kiln:status

Show current state at any time:

```
Asset: {name}
Config: {target} | {tier} | {style} | {mode}

Pipeline:
  [1] CONFIG     ✅
  [2] BRIEF      ✅  "{brief summary}"
  [3] CHOIX      ✅  {method chosen} ({recommendation})
  [4] IMPORT     ✅  {name} — {faces} faces
  [5] CLEANUP    ✅  {before} → {after} faces
  [5b] TEXTURING ◀️  IN PROGRESS — {detail}
  [6] OPTIMIZE   ⬜
  [7] EXPORT     ⬜

Next recommended step: {description}

Files:
  ├── {name}_original.glb    ({size})
  ├── {name}_clean.glb       ({size})
  └── {name}.blend

Session: {n} assets completed ({list})

Reusable prompts:
  Concept art: "{exact prompt}" (via {pollinations|nano-banana|user image})
  Hunyuan3D: steps={s}, seed={seed}, octree={res}, mode={mode}
```

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

## Prompts (copy-paste ready)
- Concept art: "{exact prompt}" (source: {pollinations|nano-banana|user image|user URL})
- Concept iterations: ["{edit1}", "{edit2}"]
- Hunyuan3D params: steps={s}, guidance_scale={g}, seed={seed},
  octree_resolution={res}, mode={mode}

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

## Licenses
- {resource}: {license} {attribution if needed}

## Checkpoint
- Last completed step: {step}
- Timestamp: {datetime}
```

---

## Units & Scale

**1 Blender unit = 1 meter.** Always.

| Object | Approximate height |
|---|---|
| Adult character | ~1.75m |
| Chair | ~0.85m |
| Table | ~0.75m |
| Door | ~2.10m |
| Tree | ~5-15m |

After import, verify bounding box. Alert if dimensions seem wrong.

**Axis orientation in Blender:**
- Front: **-Y**
- Up: **+Z**
- Origin: center of base

Axis conversion at export is automatic.

---

## Quick Reference: Loading Sub-resources

| Need | Load |
|---|---|
| Marketplace search | `references/sourcing-strategy.md` |
| AI generation (Hunyuan3D), concept art (Pollinations, nano-banana) | `references/ai-generation.md` |
| Topology rules, poly budgets | `references/topology-rules.md` |
| UV, materials, PBR | `references/uv-materials.md` |
| Texturing white meshes | `references/texturing-strategy.md` |
| Post-import cleanup | `references/validation-checklist.md` |
| Naming objects, materials, files | `references/naming-conventions.md` |
| Export settings per format | `references/export-targets.md` |
| CLI tools (gltf-transform, gltfpack) | `references/cli-tools.md` |
| Characters, rigging (phase 2) | `references/characters.md` |
| Artistic framing | `../creative-excellence/SKILL.md` |
| Three.js/R3F compatibility | `../threejs-r3f/SKILL.md` |
| Animation principles | `../motion-principles/SKILL.md` |
