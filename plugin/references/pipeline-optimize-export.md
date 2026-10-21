# Pipeline — [6] OPTIMIZE and [7] EXPORT

> Read before [6] OPTIMIZE. Rule numbers are SKILL.md's Iron Rules.

## Contents
- [6] OPTIMIZE (interactive in guided mode)
- [7] EXPORT

## [6] OPTIMIZE (interactive in guided mode)

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

## [7] EXPORT

Load `references/export-targets.md`.

```
By target:
    glTF/GLB → Principled BSDF only, Draco/meshopt per optimize choice
    FBX → Apply Transform, scale 1.0, version 7.4
    USDZ → Blender: `tools/glb_to_usdz.py` on the AR GLB (export-targets.md § USDZ)
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
