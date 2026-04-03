<p align="center">
  <img src="blender-kiln-logo.png" alt="blender-kiln logo" width="200" />
</p>

# blender-kiln — The 3D Asset Forge

A complete 3D asset production pipeline for Claude Code, powered by Blender MCP.

From a text brief to an optimized, export-ready GLB — in one session.

## What it does

Kiln is a Claude Code skill that turns you into a 3D asset production studio. It orchestrates Blender (via MCP), AI generation (Hunyuan3D, Pollinations/FLUX), and marketplace search (PolyHaven, Sketchfab) into a single coherent pipeline.

```
[1] CONFIG → [2] BRIEF → [3] SOURCE → [4] IMPORT → [5] CLEANUP → [5b] TEXTURING → [6] OPTIMIZE → [7] EXPORT
```

### Pipeline phases

| Phase | What happens |
|---|---|
| **CONFIG** | Collect parameters: asset type, style, export target, detail tier |
| **BRIEF** | Reformulate and confirm understanding — enrich with reference image details if provided (user brief always wins over image) |
| **SOURCE** | Search marketplaces OR create via AI generation / scripted modeling / geometry nodes — reference image guides all methods |
| **IMPORT** | Import into Blender, verify scale (1 unit = 1m), center origin |
| **CLEANUP** | Merge doubles, recalc normals, apply transforms, check poly budget |
| **TEXTURING** | Geometric analysis + PolyHaven PBR, procedural materials, or bake from procedural |
| **OPTIMIZE** | gltf-transform (resize, WebP, Draco) and/or gltfpack (simplify, LOD) |
| **EXPORT** | GLB, FBX, USDZ — with validation checklist |

### Key features

- **Multi-method creation**: AI generation (Hunyuan3D 2.x — local or cloud), scripted modeling (Blender Python), geometry nodes, or marketplace sourcing
- **Local AI generation**: run Hunyuan3D-2 Mini on your machine — NVIDIA GPU for full pipeline, Apple Silicon for shape generation
- **Environment auto-detection**: `/kiln:setup` scans your system and guides installation
- **Reference images**: provide an image per asset (path, URL, or drag-and-drop) — guides all creation methods (AI input, scripted proportions, texture assignment), enriches the brief, and enables post-export visual comparison
- **Concept art input**: text prompt (Pollinations/FLUX), image path, image URL, or nano-banana (optional)
- **Smart recommendations**: auto-suggests the best creation method based on asset type and style
- **Material audit**: detects procedural nodes that will be lost on GLTF export, proposes bake workflow
- **Post-export validation**: 8-point checklist (Babylon.js sandbox, Three.js console, material spot-check)
- **Character support**: T-pose enforcement, rigging patterns, bone validation, Blender 5.x bone collections
- **Multi-asset sessions**: cross-asset coherence (scale, materials, poly budget)
- **Batch mode**: wizard collects scene/theme/palette/reference images upfront, generates a YAML manifest, runner executes autonomously — ideal for overnight production or large asset sets
- **Full logging**: every asset produces a production log with copy-paste prompts

## Commands

| Command | Action |
|---|---|
| `/kiln` | Full pipeline (CONFIG → EXPORT) |
| `/kiln:batch` | Batch wizard → manifest → autonomous multi-asset production |
| `/kiln:batch run` | Execute/resume a batch manifest (`--all`, `--asset <name>`) |
| `/kiln:setup` | Environment detection + guided setup |
| `/kiln:models` | List/switch Hunyuan3D models |
| `/kiln:status` | Show current pipeline state |
| `/kiln:search` | Search PolyHaven/Sketchfab |
| `/kiln:inspect` | Inspect a 3D file (stats, poly count, materials, bbox) |
| `/kiln:cleanup` | Cleanup a mesh in Blender |
| `/kiln:texture` | Texture an untextured mesh |
| `/kiln:optimize` | Optimize a GLB with gltf-transform/gltfpack |
| `/kiln:convert` | Convert between formats (GLB↔USDZ↔FBX) |
| `/kiln:help` | List all commands and usage |

## Requirements

### Required

- **Blender 4.x+** with the [Blender MCP](https://github.com/ahujasid/blender-mcp) addon running (port 9876)

### 3D Generation (choose one or both)

| Backend | Install | GPU needed | Texture gen | Offline |
|---|---|---|---|---|
| **HF Spaces** (default) | `pip3 install gradio_client` | No (cloud) | Yes | No |
| **Local [Hunyuan3D-2](https://github.com/Tencent/Hunyuan3D-2)** | Run `/kiln:setup` (~25 GB download) | Optional | CUDA only | Yes |

On Mac (Apple Silicon): local shape generation works via MPS, texture generation falls back to skill's Blender-based texturing.
On Windows + NVIDIA GPU: full pipeline runs locally — shape + texture, zero cloud dependency.

### Optional

- **nano-banana MCP** — alternative concept art generation via Gemini (requires API key with billing)
- **gltf-transform** — `npm install -g @gltf-transform/cli` (texture compression, Draco)
- **gltfpack** — `npm install -g gltfpack` (mesh simplification, LOD generation)
- **Sketchfab API token** — free account, for marketplace downloads
- **Reality Converter** / **usdzconvert** — USDZ export (macOS)

## Installation

### Claude Code CLI

```bash
# From the skill marketplace
npx skills add blender-kiln

# Or manually: clone into your skills directory
git clone https://github.com/elithril/blender-kiln.git ~/.claude/skills/blender-kiln
```

### Manual

Copy the `blender-kiln/` folder into your Claude Code skills directory:

```
~/.claude/skills/blender-kiln/
├── SKILL.md
└── references/
    ├── ai-generation.md
    ├── batch-mode.md
    ├── characters.md
    ├── cli-tools.md
    ├── export-targets.md
    ├── naming-conventions.md
    ├── sourcing-strategy.md
    ├── texturing-strategy.md
    ├── topology-rules.md
    ├── uv-materials.md
    └── validation-checklist.md
```

## Skill structure

| File | Content | Lines |
|---|---|---|
| `SKILL.md` | Main pipeline, iron rules, commands, setup, model management | ~760 |
| `references/characters.md` | Rigging patterns, anti-patterns, export gotchas, Blender 5.x | ~430 |
| `references/texturing-strategy.md` | 4 strategies + shader recipes + bake workflow | ~340 |
| `references/validation-checklist.md` | Geometry cleanup + material export audit | ~250 |
| `references/export-targets.md` | GLB/FBX/USDZ settings, headless CLI, post-export checklist | ~210 |
| `references/cli-tools.md` | gltf-transform, gltfpack, LOD workflow, metrics | ~210 |
| `references/naming-conventions.md` | Blender + GLTF name mapping + file conventions | ~150 |
| `references/uv-materials.md` | UV unwrapping, PBR channel packing | ~150 |
| `references/ai-generation.md` | Hunyuan3D 2.x (local + cloud), concept art (Pollinations/nano-banana) | ~220 |
| `references/topology-rules.md` | Poly budgets, quad rules, edge flow | ~90 |
| `references/batch-mode.md` | Batch wizard, runner, iron rules 22-26, manifest format | ~365 |
| `references/sourcing-strategy.md` | PolyHaven + Sketchfab search patterns | ~60 |

**Total: ~3,415 lines** of production-tested 3D pipeline knowledge.

## Iron rules

The skill enforces 26 rules (21 core + 5 batch-specific). Key ones:

1. Always `get_scene_info()` before each phase
2. Always `get_viewport_screenshot()` after each modification
3. Never hard-cap poly count — alert if out of range, never block
4. Never silently destroy — decimate/simplify always interactive
5. Always keep intermediate files (original, clean, textured, optimized, final, .blend)
6. Never `export_apply=True` for GLTF — modifiers balloon file size
7. Always run material export audit before GLTF export
8. Never use `gltf-transform optimize` — use individual steps

## Output

Two storage modes, configurable at pipeline start:

**Compact (default)** — minimal footprint, .blend is the recovery point:
```
generated-assets/
└── wooden-chair/
    ├── wooden-chair_original.glb
    ├── wooden-chair_final.glb
    ├── wooden-chair.blend
    └── wooden-chair_log.md
```

**Full** — all intermediate files for debug/comparison:
```
generated-assets/
└── wooden-chair/
    ├── wooden-chair_original.glb
    ├── wooden-chair_clean.glb
    ├── wooden-chair_textured.glb
    ├── wooden-chair_optimized.glb
    ├── wooden-chair_final.glb
    ├── wooden-chair.blend
    └── wooden-chair_log.md
```

**Batch mode** — assets grouped under a batch folder with manifest and report:
```
generated-assets/
└── batch-corporate-office-2026-04-02/
    ├── batch-manifest.yaml
    ├── batch-report.md
    ├── desk/
    ├── chair/
    └── keyboard/
```

At the end of a multi-asset session, Kiln proposes a cleanup of intermediate files with per-asset size breakdown.

## License

MIT
