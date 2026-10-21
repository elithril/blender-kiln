# Setup — dependencies, `/kiln setup`, `/kiln models`

> Read at first launch (CONFIG runs Step 1 of `/kiln setup`), on `/kiln setup`, `/kiln models`,
> or when a component is missing. Local AI models: `references/setup-install.md`. Rule numbers are SKILL.md's Iron Rules.

## Contents
- Dependencies
- /kiln setup — Environment Detection & Setup
  - Step 1: Auto-detect environment
  - Installing Python packages — read this before proposing pip
  - Step 2: Guided setup (if needed)
- /kiln models — Model Management

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
