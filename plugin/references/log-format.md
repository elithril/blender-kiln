# Log format — `{name}_log.md`

> Read when creating an asset's log (end of [1] CONFIG). Rule 7: a phase is not done until
> its line and the Checkpoint are written.

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
