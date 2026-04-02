# /kiln:batch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `/kiln:batch` and `/kiln:batch run` commands to the blender-kiln skill for autonomous multi-asset batch production.

**Architecture:** The batch system is pure skill instructions (markdown in SKILL.md). No Python/TypeScript code. The wizard collects info interactively, writes a YAML manifest, and the runner executes assets sequentially using the existing pipeline phases. The manifest is the source of truth — editable, reproductible, versionnable.

**Tech Stack:** Markdown (SKILL.md), YAML (manifest format)

**Design doc:** `docs/plans/2026-04-02-kiln-batch-design.md`

---

### Task 1: Add batch commands to the Commands table

**Files:**
- Modify: `SKILL.md:14-27` (Commands table)

**Step 1: Add the two new commands to the table**

In `SKILL.md`, the Commands table at lines 14-27 currently has 11 commands. Add 2 new rows:

```markdown
| Command | Action |
|---|---|
| `/kiln` | Full pipeline (CONFIG → EXPORT) |
| `/kiln:batch` | Batch wizard → manifest → autonomous multi-asset production |
| `/kiln:batch run` | Execute/resume a batch manifest (pending, failed, redo assets) |
| `/kiln:setup` | Environment detection + guided setup (models, dependencies, GPU) |
| `/kiln:models` | List available Hunyuan3D models, switch active model |
| `/kiln:status` | Show current pipeline state, next steps, prompts |
| `/kiln:search` | Search PolyHaven/Sketchfab marketplaces |
| `/kiln:inspect` | Inspect a 3D file (stats, poly count, materials, bbox) |
| `/kiln:cleanup` | Cleanup a mesh in Blender (standalone) |
| `/kiln:texture` | Texture an untextured mesh (standalone) |
| `/kiln:optimize` | Optimize a GLB with gltf-transform/gltfpack (standalone) |
| `/kiln:convert` | Convert between formats (GLB→USDZ, GLB→FBX, etc.) |
| `/kiln:help` | List all commands and usage |
```

Place `/kiln:batch` and `/kiln:batch run` right after `/kiln` (before `/kiln:setup`) since they are primary pipeline commands.

**Step 2: Verify the table renders correctly**

Read SKILL.md lines 14-30 to confirm the table is well-formed.

**Step 3: Commit**

```bash
git add SKILL.md
git commit -m "feat(batch): add /kiln:batch commands to command table"
```

---

### Task 2: Add /kiln:batch help entry

**Files:**
- Modify: `SKILL.md` — the `/kiln:help` section (around line 611-626)

**Step 1: Add batch commands to the help output**

Find the `/kiln:help` section and add the two new commands to the help display block:

```markdown
### /kiln:help

Display all available commands with descriptions.

```
── ⚒️ blender-kiln ─────────────────────────
/kiln              Full pipeline (CONFIG → EXPORT)
/kiln:batch        Batch wizard → manifest → multi-asset production
/kiln:batch run    Execute/resume a batch manifest
/kiln:setup        Environment detection + setup
/kiln:models       List/switch Hunyuan3D models
/kiln:status       Show current pipeline state
/kiln:search       Search PolyHaven/Sketchfab
/kiln:inspect      Inspect a 3D file (stats, bbox)
/kiln:cleanup      Cleanup a mesh in Blender
/kiln:texture      Texture an untextured mesh
/kiln:optimize     Optimize a GLB (gltf-transform/gltfpack)
/kiln:convert      Convert formats (GLB↔FBX↔USDZ)
/kiln:help         This help message
─────────────────────────────────────────────
Quick: /kiln:setup → /kiln
Batch: /kiln:batch → /kiln:batch run
```
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat(batch): add batch commands to /kiln:help output"
```

---

### Task 3: Write the /kiln:batch wizard section

**Files:**
- Modify: `SKILL.md` — insert new section after the "Multi-Asset Sessions" section (after line ~645)

**Step 1: Write the complete wizard section**

Insert the following section after "Multi-Asset Sessions" and before "Log Format":

````markdown
---

## /kiln:batch — Batch Wizard

Launch with `/kiln:batch`. The wizard collects all parameters upfront, generates a YAML manifest, then optionally launches the runner.

**Flow:** Wizard (interactive, ~5-10 min) → Manifest (YAML file) → Runner (autonomous)

### Step 1 — Global Context

Ask these questions one at a time:

1. **Theme/scene:** "Describe the scene or theme for this batch:"
   → Free text (e.g. "Bureau d'entreprise moderne, open space")

2. **Visual style:** "Visual style?"
   → realistic / stylized / low-poly / cartoon

3. **Export target:** "Export target?"
   → glTF-web / Unity FBX / Unreal FBX / USDZ AR / multi

4. **Default tier:** "Default detail tier?"
   → lightweight / balanced / detailed

### Step 2 — Asset List

"List the assets (one per line, with a brief description):"

```
desk: bureau rectangulaire moderne, plateau bois, pieds métal
chair: chaise ergonomique, mesh noir
keyboard: clavier mécanique compact
lamp: lampe de bureau articulée, métal brossé
```

### Step 3 — Materials

"Define a material palette or let me deduce it from the theme?"

**If "deduce":** propose a palette with human description + technical ref:
```
── Palette proposée ────────────────────────
wood:    Bois clair vieilli, chaleureux     (polyhaven: wood_cabinet_worn_long)
metal:   Métal noir brossé, semi-mat        (procédural: metallic 1.0, roughness 0.3)
fabric:  Tissu gris anthracite chiné        (polyhaven: fabric_pattern_05)
plastic: Plastique noir mat                 (procédural: roughness 0.6, color #2d2d2d)
────────────────────────────────────────────
OK ou modifier ?
```

**If "I define":** ask material by material — name, description, source (polyhaven ID or procedural params).

The palette is shared across all batch assets for visual coherence.

### Step 4 — Recap & Adjustments

Infer creation method per asset using these heuristics:

```
IF brief suggests simple geometric shapes (table, shelf, door, box, frame)
    → method: scripted

IF brief suggests organic/complex forms (ergonomic chair, articulated lamp, plant, rock)
    → method: hunyuan3d

IF type = character
    → method: hunyuan3d (always)

IF brief suggests repetitive patterns (cables, grids, fences, railings)
    → method: geometry-nodes

IF brief suggests very standard/common object (keyboard, mouse, monitor, phone)
    → method: marketplace
```

Infer tier per asset (default from config, override if obvious: cable → lightweight, detailed statue → detailed).

Assign materials from palette per asset based on brief keywords.

Display the full recap:

```
── Manifest généré ─────────────────────────
Scène: {name} │ {style} │ {tier} │ {target}

  #  Asset     Méthode         Matériaux        Tier
  1  desk      scripted        wood + metal     balanced
  2  chair     hunyuan3d       fabric + plastic balanced
  3  keyboard  marketplace     plastic          lightweight
  ...

⚠️ Estimation : ~{low}K-{high}K tokens (marge ±50%)
   Retries réseau, complexité matériaux et erreurs peuvent
   doubler un asset individuel.
────────────────────────────────────────────
Modifier ? (ex: "3 → hunyuan3d", "5 tier detailed")
Ou : Lancer / Plus tard
```

**Token estimation formula:**
- scripted: ~30K tokens/asset
- marketplace: ~20K tokens/asset
- hunyuan3d: ~60K tokens/asset
- geometry-nodes: ~40K tokens/asset
- Multiply total by 1.0 (low) and 1.5 (high) for the range

Allow the user to adjust any line before validation. Accept formats like:
- `"3 → hunyuan3d"` — change method
- `"5 tier detailed"` — change tier
- `"2 materials wood + metal"` — change materials
- `"remove 4"` — remove asset from batch

### Step 5 — Generate Manifest & Launch

Write the manifest to `{output_folder}/batch-manifest.yaml` (see Manifest Format section).

Create the batch output folder structure.

```
Manifest saved: generated-assets/batch-{name}-{date}/batch-manifest.yaml

  1. Lancer maintenant
  2. Plus tard (/kiln:batch run <dossier>)
```

If "lancer" → immediately start the runner (see /kiln:batch run section).
If "plus tard" → done. User launches when ready.
````

**Step 2: Verify insertion point**

Read SKILL.md around the insertion point to confirm the section flows correctly between "Multi-Asset Sessions" and "Log Format".

**Step 3: Commit**

```bash
git add SKILL.md
git commit -m "feat(batch): add /kiln:batch wizard section"
```

---

### Task 4: Write the /kiln:batch run (runner) section

**Files:**
- Modify: `SKILL.md` — insert after the wizard section

**Step 1: Write the complete runner section**

Insert after the wizard section:

````markdown
---

## /kiln:batch run — Batch Runner

Execute a batch manifest autonomously. Zero interaction during execution.

**Usage:**
- `/kiln:batch run <batch-folder>` — run pending/failed/redo assets
- `/kiln:batch run <batch-folder> --all` — force rerun all assets
- `/kiln:batch run <batch-folder> --asset <name>` — rerun one specific asset

### Pre-flight

1. Read `{batch-folder}/batch-manifest.yaml`
2. Validate: all palette materials have valid sources, all assets have required fields
3. Run environment scan (Step 1 of `/kiln:setup` — auto-detect only, no prompts)
4. Verify Blender MCP is connected
5. Display batch summary:

```
── Batch: {name} ───────────────────────────
{n} assets │ {pending} pending │ {failed} failed │ {done} done
Backend: {backend} │ Style: {style} │ Target: {target}
Starting...
```

### Execution Loop

For each asset where `status` is `pending`, `failed`, or `redo` (in manifest order):

```
1. Update manifest: status → "running"

2. Clear Blender scene:
   execute_blender_code → bpy.ops.wm.read_homefile(use_empty=True)

3. Execute pipeline phases:

   [BRIEF] — Use asset.brief from manifest. No user confirmation needed.

   [CHOIX] — Use asset.method from manifest:
     - scripted → go to scripted modeling flow
     - hunyuan3d → generate concept art (Pollinations, auto prompt from brief),
       then AI generation. Use config.backend.
     - marketplace → search PolyHaven/Sketchfab with brief keywords,
       auto-pick first result matching tier. If no result → status: failed.
     - geometry-nodes → go to geometry nodes flow

   [IMPORT] — Standard import. Verify scale (1 unit = 1m).
     Alert in log if dimensions seem wrong (don't block).

   [CLEANUP] — Full auto cleanup:
     Merge by Distance, Recalculate Normals, Remove Loose,
     Degenerate Dissolve, Apply Transforms, Origin to center of base.
     If poly count >50% above tier range → auto-decimate to tier midpoint.
     Log before/after stats.

   [TEXTURING] — Apply materials from palette:
     For each material in asset.materials:
       - If source=polyhaven → download and apply PBR textures
       - If source=procedural → create Principled BSDF with params
     Use geometric analysis to assign materials to mesh zones
     (face normals/position clustering).
     Skip if asset already has textures (marketplace with textures).

   [OPTIMIZE] — Apply config.optimize_preset:
     - "resize-1k-webp-draco" → gltf-transform resize 1024 → webp → draco
     - "resize-512-webp" → gltf-transform resize 512 → webp
     - "none" → skip
     - Custom string → parse and apply
     Log before/after file size.

   [EXPORT] — Export per config.target format.
     Run material export audit (Iron Rule 19).
     Save in batch-folder/asset-name/ per storage mode.
     Save .blend file.

4. Take final viewport screenshot:
   get_viewport_screenshot() → save to {asset-name}/{name}_screenshot.png

5. Write asset log: {asset-name}/{name}_log.md (standard log format,
   include the batch brief as "Source Brief" section)

6. Update manifest:
   status → "done"
   result: { faces, file_size, duration, screenshot }

7. Append to batch-report.md
```

**On error at any phase:**
```
1. Log error message + phase where it failed
2. Update manifest: status → "failed", error: "{phase}: {message}"
3. Append failure to batch-report.md
4. Continue to next asset (no retry, no fallback)
```

### Iron Rules (batch-specific)

All 21 existing iron rules apply. Additional batch rules:

```
22. NEVER switch creation method on failure — skip the asset. DA coherence
    is more important than completion rate.
23. NEVER prompt the user during runner execution. All decisions come from
    the manifest. If a decision can't be made from manifest data, log it
    as an error and skip.
24. ALWAYS update the manifest file after each asset (status + result).
    If the process crashes, the manifest reflects progress.
25. ALWAYS clear the Blender scene between assets. Never carry state from
    one asset to the next.
```

### Batch Report

The runner maintains `batch-report.md` in the batch folder, updated after each asset:

```markdown
# Batch Report: {name} — {date}

## Summary
{done}/{total} ✅ │ {failed} ❌ │ duration: ~{time}

## Assets
| # | Asset | Status | Method | Faces | Size | Duration |
|---|-------|--------|--------|-------|------|----------|
| 1 | desk | ✅ | scripted | 2.1K | 340KB | 3m |
| 2 | chair | ✅ | hunyuan3d | 3.8K | 1.2MB | 5m |
| 3 | keyboard | ❌ | marketplace | — | — | — |
|   | | | Error: No matching asset found on PolyHaven/Sketchfab |
```

### End of Batch

When all assets are processed, display:

```
── Batch terminé ───────────────────────────
{done}/{total} ✅ │ {failed} ❌ ({failed_names}) │ ~{duration}

  1. Relancer les {failed} échecs
  2. Relancer tout le batch
  3. Relancer un asset spécifique
  4. Éditer le manifest et relancer
  5. Terminé
```

**Option 1:** re-run the same manifest (failed/redo assets only)
**Option 2:** set all assets to `pending`, re-run
**Option 3:** ask which asset, set it to `redo`, re-run
**Option 4:** open manifest path for user to edit, then re-run
**Option 5:** done, show batch-report.md path
````

**Step 2: Verify section placement and flow**

Read SKILL.md around the insertion to confirm it fits between the wizard section and Log Format.

**Step 3: Commit**

```bash
git add SKILL.md
git commit -m "feat(batch): add /kiln:batch run (runner) section"
```

---

### Task 5: Write the Manifest Format section

**Files:**
- Modify: `SKILL.md` — insert after the runner section

**Step 1: Write the manifest format reference**

Insert after the runner section:

````markdown
---

## Batch Manifest Format

The manifest is the source of truth for a batch. Generated by the wizard, updated by the runner, editable by the user.

**File:** `{batch-folder}/batch-manifest.yaml`

```yaml
# batch-manifest.yaml — generated by /kiln:batch wizard
# Editable. Runner executes assets where status ≠ done.

batch:
  name: corporate-office              # kebab-case identifier
  created: 2026-04-02T22:30:00        # ISO 8601
  description: "Bureau d'entreprise moderne, open space"

config:
  style: realistic                    # realistic | stylized | low-poly | cartoon
  target: gltf-web                    # gltf-web | unity-fbx | unreal-fbx | usdz-ar | multi
  tier: balanced                      # lightweight | balanced | detailed
  storage: compact                    # compact | full
  backend: hf-spaces                  # hf-spaces | local
  hf_space_url: Jbowyer/Hunyuan3D-2.1  # override if needed
  hunyuan_model: mini                 # mini | mini-fast | mini-turbo (local only)
  optimize_preset: resize-1k-webp-draco  # resize-1k-webp-draco | resize-512-webp | none | custom
  output_folder: ./generated-assets/batch-corporate-office-2026-04-02

palette:
  wood:
    description: "Bois clair vieilli, chaleureux"
    source: polyhaven                 # polyhaven | procedural
    id: wood_cabinet_worn_long        # PolyHaven asset ID
  metal:
    description: "Métal noir brossé, semi-mat"
    source: procedural
    params:
      metallic: 1.0
      roughness: 0.3
      color: "#1a1a1a"
  # ... more materials

assets:
  - name: desk                        # kebab-case, used for folder + file names
    brief: "Bureau rectangulaire moderne, plateau bois clair, pieds métal tubulaire"
    method: scripted                  # scripted | hunyuan3d | marketplace | geometry-nodes
    materials: [wood, metal]          # refs to palette keys
    tier: balanced                    # override config.tier if needed
    status: pending                   # pending | running | done | failed | redo

    # Added by runner after execution:
    result:
      faces: 2100
      file_size: "340KB"
      duration: "180s"
      screenshot: "desk/desk_screenshot.png"
    error: null                       # error message if failed
```

### Status Values

| Status | Meaning | Runner action |
|--------|---------|---------------|
| `pending` | Not yet processed | Execute |
| `running` | Currently processing | (set by runner) |
| `done` | Completed successfully | Skip |
| `failed` | Failed (see `error` field) | Re-execute |
| `redo` | Marked for redo by user | Re-execute |

### Editing the Manifest

Common edits between runs:
- Change an asset's `status` from `done` to `redo` to re-process it
- Change `method` to try a different creation approach
- Adjust `brief` for better results on retry
- Add/remove assets from the list
- Change `materials` assignments
- Change `optimize_preset` globally
````

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat(batch): add batch manifest format reference"
```

---

### Task 6: Add batch output structure to the Export section

**Files:**
- Modify: `SKILL.md` — the Export section [7] (around lines 416-467)

**Step 1: Add batch folder structure**

After the existing "Full" storage mode structure, add:

```markdown
**Batch mode** (when run from `/kiln:batch run`):
```
generated-assets/
└── batch-{name}-{date}/
    ├── batch-manifest.yaml
    ├── batch-report.md
    └── {asset-name}/
        ├── {name}_final.{ext}
        ├── {name}.blend
        ├── {name}_screenshot.png
        └── {name}_log.md
```

In batch mode, each asset follows the same compact/full rules but nested inside the batch folder. The manifest and report are at the batch root level.
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat(batch): add batch output structure to export section"
```

---

### Task 7: Update the description in the frontmatter

**Files:**
- Modify: `SKILL.md:3` (description field)

**Step 1: Update description to mention batch**

Change line 3 from:
```
description: "3D asset production pipeline via Blender MCP — sourcing, AI generation, cleanup, texturing, optimization, export."
```
To:
```
description: "3D asset production pipeline via Blender MCP — sourcing, AI generation, cleanup, texturing, optimization, export. Batch mode for autonomous multi-asset production."
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat(batch): update skill description to mention batch mode"
```

---

### Task 8: Final review and squash commit

**Step 1: Read the full SKILL.md to verify all sections are coherent**

Read the entire file, checking:
- Commands table has batch entries
- Help output has batch entries
- Wizard section is complete and flows logically
- Runner section is complete with all pipeline phases
- Manifest format is documented
- Export section mentions batch structure
- No duplicate content, no orphaned references

**Step 2: Verify cross-references**

- Wizard references "Manifest Format section" → verify it exists
- Runner references "Iron Rule 19" → verify number is correct
- Help output mentions `/kiln:batch run` → verify command matches

**Step 3: Final commit if any fixes needed**

```bash
git add SKILL.md
git commit -m "fix(batch): review fixes and consistency pass"
```
