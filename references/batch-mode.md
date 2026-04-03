# Batch Mode — Wizard, Runner & Manifest

## /kiln:batch — Batch Wizard

Launch with `/kiln:batch`. The wizard collects all parameters upfront, generates a YAML manifest, then optionally launches the runner.

**Flow:** Wizard (interactive, ~5-10 min) → Manifest (YAML file) → Runner (autonomous)

### Step 1 — Global Context

Ask these questions one at a time:

1. **Theme/scene:** "Describe the scene or theme for this batch:"
   → Free text (e.g. "Modern corporate office, open space")

2. **Visual style:** "Visual style?"
   → realistic / stylized / low-poly / cartoon

3. **Export target:** "Export target?"
   → glTF-web / Unity FBX / Unreal FBX / USDZ AR / multi

4. **Default tier:** "Default detail tier?"
   → lightweight / balanced / detailed

### Step 2 — Asset List

"List the assets (one per line, with a brief description):"

```
desk: modern rectangular desk, wood top, metal legs
chair: ergonomic chair, black mesh
keyboard: compact mechanical keyboard
lamp: articulated desk lamp, brushed metal
```

Then ask: **"Do you have reference images for any of these assets? (paths, URLs, or 'no')"**

- User can provide one image per asset: local path, URL, or drag-and-drop
- Format: `asset_name: /path/to/image.png` or `asset_name: https://...`
- If "no" → concept art will be auto-generated from briefs (Pollinations)
- Reference images are optional per asset — some assets can have images while others don't

### Step 3 — Materials

"Define a material palette or let me deduce it from the theme?"

**If "deduce":** propose a palette based on the theme AND any reference images provided in Step 2. Analyze reference images to identify visible materials (wood grain, metal finish, fabric texture, etc.) and incorporate them into the palette proposal. Human description + technical ref:
```
── Proposed Palette ────────────────────────
wood:    Light aged wood, warm tone         (polyhaven: wood_cabinet_worn_long)
metal:   Brushed black metal, semi-matte    (procedural: metallic 1.0, roughness 0.3)
fabric:  Dark grey heathered fabric         (polyhaven: fabric_pattern_05)
plastic: Matte black plastic               (procedural: roughness 0.6, color #2d2d2d)
────────────────────────────────────────────
OK or modify?
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
── Generated Manifest ──────────────────────
Scene: {name} │ {style} │ {tier} │ {target}

  #  Asset     Method          Materials        Tier        Ref Image
  1  desk      scripted        wood + metal     balanced    —
  2  chair     hunyuan3d       fabric + plastic balanced    📷 chair-ref.png
  3  keyboard  marketplace     plastic          lightweight —
  ...

⚠️ Estimate: ~{low}K-{high}K tokens (±50% margin)
   Network retries, material complexity, and errors can
   double an individual asset.
────────────────────────────────────────────
Modify? (e.g. "3 → hunyuan3d", "5 tier detailed")
Or: Launch / Later
```

**Token estimation formula:**
- scripted: ~30K tokens/asset
- marketplace: ~20K tokens/asset
- hunyuan3d: ~60-80K tokens/asset
- geometry-nodes: ~40K tokens/asset
- Multiply total by 1.0 (low) and 1.5 (high) for the range

Allow the user to adjust any line before validation. Accept formats like:
- `"3 → hunyuan3d"` — change method
- `"5 tier detailed"` — change tier
- `"2 materials wood + metal"` — change materials
- `"2 ref /path/to/image.png"` — add/change reference image
- `"2 ref none"` — remove reference image
- `"remove 4"` — remove asset from batch

### Step 5 — Generate Manifest & Launch

Write the manifest to `{output_folder}/batch-manifest.yaml` (see Batch Manifest Format section below).

Create the batch output folder structure.

```
Manifest saved: generated-assets/batch-{name}-{date}/batch-manifest.yaml

  1. Launch now
  2. Later (/kiln:batch run <folder>)
```

If "launch" → immediately start the runner (see /kiln:batch run section below).
If "later" → done. User launches when ready.

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

   [REF IMAGE] — IF asset.reference_image exists:
     Download if URL, verify file exists if path.
     Read/analyze the image to extract visual context (proportions,
     shape, parts, colors, style). This analysis informs ALL methods below.

   [BRIEF ENRICHMENT] — IF reference image was analyzed:
     Extract visible details from the image that are NOT already in
     the brief (e.g. number of legs, drawer, handle shape, curvature).
     CRITICAL: the user's brief ALWAYS wins over image analysis.
     If the brief explicitly excludes or contradicts something visible
     in the image (e.g. "like this but without armrests"), respect the
     brief — do NOT reintroduce contradicted details from the image.
     Log the enriched brief in the asset log for traceability.

   [SOURCE] — Use asset.method from manifest:
     - scripted →
       IF reference image was analyzed:
         Use visual analysis to guide Python modeling — match proportions,
         number of parts, shapes, and structural details from the image.
       Go to scripted modeling flow.
     - hunyuan3d →
       IF reference image was analyzed:
         Use reference image directly as Hunyuan3D input (skip concept art generation).
       ELSE:
         Generate concept art (Pollinations, auto prompt from brief).
       Then AI generation. Use config.backend.
     - marketplace → search PolyHaven/Sketchfab with brief keywords,
       auto-pick first result matching tier. If no result → status: failed.
     - geometry-nodes → go to geometry nodes flow

   [IMPORT] — Standard import. Verify scale (1 unit = 1m).
     Alert in log if dimensions seem wrong (don't block).

   [CLEANUP] — Full auto cleanup per references/validation-checklist.md.
     Check poly budget against tier from references/topology-rules.md.
     If poly count >50% above tier range → auto-decimate to tier midpoint.
     Log before/after stats.

   [TEXTURING] — Load references/texturing-strategy.md. Apply materials from palette:
     For each material in asset.materials:
       - If source=polyhaven → download and apply PBR textures
       - If source=procedural → create Principled BSDF with params
     Use geometric analysis to assign materials to mesh zones
     (face normals/position clustering).
     IF reference image was analyzed:
       Use it to guide material zone assignment — match which material
       goes where based on visible colors/textures in the image
       (e.g. wood on top surfaces, metal on legs).
     Skip if asset already has textures (marketplace with textures).

   [OPTIMIZE] — Apply config.optimize_preset:
     - "resize-1k-webp-draco" → gltf-transform resize 1024 → webp → draco
     - "resize-512-webp" → gltf-transform resize 512 → webp
     - "none" → skip
     - Custom string → dash-separated steps, e.g. "resize-512-draco" or "resize-2k-webp".
       Format: "resize-{size}-{compression}". See references/cli-tools.md for available steps.
     Log before/after file size.

   [EXPORT] — Export per config.target format.
     Run material export audit (Iron Rule 19).
     Save in batch-folder/asset-name/ per storage mode.
     Save .blend file.

4. Take final viewport screenshot:
   get_viewport_screenshot() → save to {asset-name}/{name}_screenshot.png

4b. IF reference image exists — Visual comparison:
    Compare the final screenshot against the reference image.
    Log a short verdict in the asset log (informational, never blocking):
      - Proportions: OK / differs (e.g. "legs shorter than ref")
      - Structure: OK / differs (e.g. "missing cross braces visible in ref")
      - Overall: "close match" / "partial match" / "loose interpretation"
    This helps the user decide which assets to redo post-batch.

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
26. BATCH EXCEPTION to Rule 6: In batch runner mode, auto-decimate replaces
    the interactive proposal when poly count >50% above tier range. Log
    before/after stats in the asset log for post-batch review. This is the
    only case where Rule 6 is overridden — Rule 23 (no prompts) takes
    precedence in batch mode.
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
── Batch complete ──────────────────────────
{done}/{total} ✅ │ {failed} ❌ ({failed_names}) │ ~{duration}

  1. Retry the {failed} failures
  2. Rerun entire batch
  3. Rerun a specific asset
  4. Edit manifest and rerun
  5. Done
```

**Option 1:** re-run the same manifest (failed/redo assets only)
**Option 2:** set all assets to `pending`, re-run
**Option 3:** ask which asset, set it to `redo`, re-run
**Option 4:** open manifest path for user to edit, then re-run
**Option 5:** done, show batch-report.md path

---

## Batch Manifest Format

The manifest is the source of truth for a batch. Generated by the wizard, updated by the runner, editable by the user.

**File:** `{batch-folder}/batch-manifest.yaml`

```yaml
# batch-manifest.yaml — generated by /kiln:batch wizard
# Editable. Runner executes assets where status ≠ done.

batch:
  name: corporate-office              # kebab-case identifier
  created: 2026-04-02T22:30:00        # ISO 8601 (auto-generated)
  description: "Modern corporate office, open space"

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
    description: "Light aged wood, warm tone"
    source: polyhaven                 # polyhaven | procedural
    id: wood_cabinet_worn_long        # PolyHaven asset ID
  metal:
    description: "Brushed black metal, semi-matte"
    source: procedural
    params:
      metallic: 1.0
      roughness: 0.3
      color: "#1a1a1a"
  # ... more materials

assets:
  - name: desk                        # kebab-case, used for folder + file names
    brief: "Modern rectangular desk, light wood top, tubular metal legs"
    method: scripted                  # scripted | hunyuan3d | marketplace | geometry-nodes
    reference_image: null             # optional: local path or URL to reference image
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
- Add/change `reference_image` to provide visual reference
- Add/remove assets from the list
- Change `materials` assignments
- Change `optimize_preset` globally
