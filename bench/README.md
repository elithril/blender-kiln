# Quality bench

The gallery proves the scripted path. Nothing proved the skill: no end-to-end
session driven by `/kiln` had ever been measured. This bench runs the skill on
fixed briefs — one per pipeline path — and measures the GLB it ships, so a
change to the skill, the MCP server, the generation backend or the model can be
judged against a recorded baseline instead of argued about. Since 3.0 it also runs the
character, animation, repair and print paths (`briefs.json`; each new brief lists what it
records under `record`).

```bash
python3 bench/test_measure.py          # the instrument first: seeded defects, 23/23 expected
python3 bench/run.py baseline          # every enabled brief
python3 bench/run.py lot2 ai-mushrooms # one brief under a new label
python3 bench/run.py --remeasure baseline   # the measures again, on a label already run
BENCH_PLUGIN_DIR=<checkout> nohup python3 bench/drive.py v220-ahujasid:ahujasid v220-lab:lab &
```

`drive.py` runs whole labels unattended, one session at a time, resumable: it skips what
has a `result.json`, waits while port 9876 is taken, and sets aside a session the
subscription's usage limit cut short (`bench/runs/_aborted/`) to run it again. Log:
`bench/runs/_driver.log`; stop after the current brief with `touch bench/runs/_driver.stop`.

Results go to `bench/runs/<label>/<brief>/` (git-ignored, hundreds of MB): the
transcript, the Blender log, the session's output folder, and `result.json`.

`python3 bench/publish.py <label>` copies what proves the claims into
`bench/results/<label>/` — about 0.5–1 MB a label. `bench/results/` is a worktree of the
`bench-results` branch, kept out of `main` so a plugin install does not download it:
`git worktree add bench/results bench-results` once, then commit and push there:
`summary.json`, renders as WebP, the logs the skill wrote, and every shipped GLB
under 1 MB (larger ones listed with size and sha256). No transcript, no `.blend`,
no concept art. Local paths become `<repo>` / `<home>`, and the export fails if a
username or an e-mail address survives.

A published label is a record: never republish it over a different run —
measure under a new label instead.

## What is measured

**On the file**, by `measure.py`, after re-importing the GLB — never from the
production log, which is written by the session being judged:

| Field | Why |
|---|---|
| `tris`, `bytes`, `extensions_used` | budget tier and what OPTIMIZE bought |
| `non_manifold_edges`, `boundary_edges`, `degenerate_faces` | topology, judged after welding seams |
| `dims_m`, `z_min_m`, `centre_xy_m` | rule 14 and the IMPORT phase: metres, on the ground, centred |
| `materials` (images, max px), `empty_material_slots` | textures that survived export — rule 19's silent loss |
| `rigs[]`: dead deform bones, unweighted vertices, max influences | the checks of `references/characters.md` |
| `rigs[].stretch_p99`, `stretch_max` | a deformation probe: every deform bone bent 25°, edge stretch measured. Catches a rig that validates and produces mush |

| `clips[]`: name, duration, `loop_closes`, `seam`, `seam_vs_step`, `blink` | read from the file's own animation channels, not Blender's import: a web player plays the file. A loop closes when its last key repeats the first on every channel (three.js wraps at the last key) |
| `single_skin`, `skinned_mesh_objects` | one mesh carries the body, not a mesh per part (`characters.md`) |
| `rigs[].bent` (`skin_intersect.py`) | the rig study's bent pose — thighs 60° forward, knees and elbows 75° — and the rest area of the skin that then crosses itself, minus what crossed at rest: `inter` (a limb through another part) and `fold` (a crease folding on itself), in mm² and % of the skin. Limbs found by name (kiln's, Rigify's, the usual spellings), parts by hierarchy |
| `rigs[].hand_bones`, `finger_bones` | what the rig did about the hands |
| `input_measures` | the same measures on the file a repair brief started from: before → after |
| `print_check` | the bench's own copy of `plugin/tools/print_check.py` (this checkout, the same for every label — 2.2.0 has none) on the shipped STL/3MF, with PrusaSlicer when installed: one figure in several colours as an assembly, separate parts each alone; a FAIL on a floating part is sliced again with supports (`needs_supports`) |
| `artifacts` | what the skill's tools reported about themselves (`quadruped-report.json`: ear and tail lag, blinks; `photo_project.json`: SSIM from the photo's view) — read, never trusted over the file |

**On the session**, from the `stream-json` transcript: turns, wall time,
tokens, tool calls by name (screenshots included), and the CLI's
equivalent-API cost — not billed on a subscription, but the only comparable
measure of how much quota a run consumes. `signals.py` reads what the session ran (only
tools that run or write code count — a Read of `autorig.py` is not a rig): the rig route
(SkinTokens' autorig, Rigify, a scripted armature), `quadruped.py`, a matcap look, the photo
projection proposed (its own words) and run, what it said about a fused hand, the
print_check verdicts it saw, and whether it ended on a question nobody could answer.

## Inputs

Everything a brief names lives in `bench/runs/_refs/` (git-ignored), each with its source:

| File | Source | Licence |
|---|---|---|
| `Lantern_01.png`, `ammo_box.png`, `WoodenChair_01.png`, `gt/` | Poly Haven (`gt/*/files.txt`) | CC0 |
| `trellis/lantern_trellis.glb` | a local TRELLIS.2 generation from `Lantern_01.png` | MIT model, CC0 photo |
| `hunyuan/hunyuan_demo_1.glb` | a Hunyuan3D-2 demo output (rig study, 2026-10-16) | Tencent Hunyuan 3D 2.0 Community License — **its territory excludes the EU, the UK and South Korea**: bench-internal, never published; a rig of it is a derivative, check before publishing `generated-humanoid-rig` |

`SOURCE.txt` beside each holds its sha256.

## Traps the instrument had to get past

Each one was measured while building it, and each would have produced a
plausible, wrong number:

- **Blender exits 0 when a Python script raises**, unless given
  `--python-exit-code 1`. An explicit `sys.exit(1)` does propagate. Every
  Blender call here passes the flag.
- **The glTF importer keeps vertices split at every UV and normal seam.** A
  closed barrel came back with 4,112 boundary edges. Topology is judged after
  welding coincident points.
- **The importer adds an `Icosphere` mesh object** as the display shape of
  imported bones. Counted as geometry, it put an arm standing on the ground at
  z = −1.0.
- **The glTF exporter hides unweighted vertices** by binding them to a
  synthetic `neutral_bone`, and the file validates. A vertex only that bone
  drives is counted as unweighted.
- **The exporter drops loose edges by default**, so a shipped GLB cannot carry
  one; the field is kept, the seeded check is not.

## Deviations from canonical use

Stated here so no result is read as more than it is:

- **The skill is interactive; the bench is not.** Every CONFIG parameter is
  given in the brief and the session runs in `auto` mode. Rule 6 (prompt before
  destroying) is therefore never exercised by a human answer.
- **Permissions are bypassed** (`--permission-mode bypassPermissions`) and the
  session loads **no user settings** (`--setting-sources project`), so no
  personal CLAUDE.md, hook or memory colours the result.
- **Versions are pinned**: `mcp-for-blender` 2.2.2 (ahujasid's server, renamed from
  `blender-mcp`) with the addon it bundles, installed into a throwaway Blender profile; each
  result records `mcp-for-blender==<version>`. Until 2026-10-21 the pin read `blender-mcp==2.0.0`,
  a shim that installs the latest `mcp-for-blender`: runs before that date drove whichever
  version was current (2.1.9 on 2026-10-16), not 2.0.0. Blender itself is whatever the
  machine has — recorded in `blender.log`.
- **The machine's Hugging Face token is used.** `gradio_client` sends the locally
  saved token by default, so every Space call in these runs counted against a
  free logged-in account's ZeroGPU quota (3.5 min a day), not the anonymous one.
- **Standing answers.** A headless session cannot answer: a question ends the run. A brief
  that must get past a proposal gives its answer in the prompt, word for word the same for
  every version (`ref-ammo-box-project`: yes to every optional step; `print-bayonet-box`:
  carry on if it would send the lid to a CAD tool). The original `ref-ammo-box` stays
  unanswered, to record whether the skill proposes at all; `ref-lantern` is the negative
  control (a photo with no markings: nothing should be proposed).
- **Timeout 5400 s** a session under `drive.py` (3600 s under `run.py` alone, as the first
  labels ran): the rig and print briefs run longer. Recorded as `timeout_s`.
- **The Studio brief** (`studio-note-roundtrip`, 3.0 and later; a skill without Studio skips it)
  runs through Kiln Studio, not a `claude -p` of the bench's own (`studio_drive.py`): a fixed
  model (`fixtures/studio/iron-lantern`, the 3.0 lantern of 2026-10-21), the note pinned on its
  ring in the real page by headless Chromium (`studio_page.py`, Playwright 1.64.0), "Work on it
  with Claude" pressed, and Studio's own worker doing the work on its own Blender (port 9879).
  The bench plays the user: a held-back tool call is allowed when free, denied when it can spend
  money, each one recorded; approvals go through the page's endpoint, not a click. Measured:
  the ring 2x (±15 %), the other parts within 2 mm, the ring still on the roof, the note
  addressed, a new version; the page's screenshots land in `shots/`. Its numbers stand alone:
  2.2.0 has no Studio to compare with.
- **One run per brief.** A model is not deterministic; a single difference
  between two labels is a lead, not a verdict.
