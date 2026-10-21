# Standalone commands

> Read for `/kiln status`, `inspect`, `cleanup`, `texture`, `animate`, `optimize`, `convert`,
> `search`, `studio`, `help`: the section of the command, then do it. They work without the
> pipeline. Rule numbers are SKILL.md's Iron Rules.

These commands work independently — no need to run the full pipeline.

**Kiln Studio shows what you are on.** When a command changes models that a running
Kiln Studio shows (`studio.py status` answers for the project), tell it before the first
change and as you go, so the page puts a dot on each model — waiting, breathing while you
work on it, green when done: `studio.py work start <asset>... --label "optimize"` (in the
order you will take them; the first is active), `studio.py work next` after each one,
`studio.py work end` if you stop early. One model is a run of one. Not in batch runs.
`references/studio.md` § 5 has the rest.

## Contents
- /kiln status
- /kiln inspect
- /kiln cleanup
- /kiln texture
- /kiln animate
- /kiln optimize
- /kiln convert
- /kiln search
- /kiln studio
- /kiln help

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

## /kiln inspect

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

## /kiln cleanup

Clean up a mesh already open in Blender (or import one first).

1. `get_scene_info()` — identify what's in the scene
2. Ask user which object(s) to clean, or "all"
3. Load `references/validation-checklist.md` — execute full cleanup sequence
4. `look()` after each step (rule 2)
5. If poly count high: propose decimate (always interactive)

**For a print** — a model the user made and wants to print (`/kiln cleanup model.stl`): not the
sequence above. Load `references/print.md` § A model you bring, then: `print_check` on the file,
`tools/flatten.py` to a NEW file (never over theirs), `print_check` again, and show both verdicts
and flatten's report — regions flattened, kept as shapes, past the tolerance, the largest move —
with a matcap close-up of the largest flattened face before and after. Holes are reported, not
filled: the slicer closes small ones, the user decides the rest.

## /kiln texture

Texture an untextured mesh (white mesh from AI generation, or any mesh without materials).

1. `get_scene_info()` — verify mesh exists, check current materials
2. If mesh has no materials or only default: proceed
3. If mesh already has materials: "This mesh already has {n} materials. Re-texture anyway? (yes / no / add to existing)"
4. Load `references/texturing-strategy.md`
5. Follow the texturing strategies in order:
   - Geometric analysis + PolyHaven PBR
   - Procedural Blender materials
   - Assisted manual texturing
6. `look(shading="material")` after applying materials (rule 2)

**Note on monolithic meshes (AI-generated):** the geometric analysis clusters faces by normal direction, position, and curvature. This works on single-object meshes — it will identify zones (e.g. "top faces = seat", "vertical faces = legs") even without object separation. Results may need manual adjustment for complex shapes.

## /kiln animate

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

## /kiln optimize

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

## /kiln convert

Convert between 3D formats.

1. Ask for input file path and target format
2. Supported conversions:

| From | To | Method |
|---|---|---|
| GLB → FBX | `execute_blender_code` (import GLB, export FBX) |
| GLB → USDZ | `blender -b --factory-startup --python tools/glb_to_usdz.py -- in.glb out.usdz` (export-targets.md § USDZ) |
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

## /kiln search

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

## /kiln studio

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

## /kiln help

Display all available commands from the table in SKILL.md § Commands.
