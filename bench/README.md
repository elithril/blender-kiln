# Quality bench

The gallery proves the scripted path. Nothing proved the skill: no end-to-end
session driven by `/kiln` had ever been measured. This bench runs the skill on
six fixed briefs — one per pipeline path — and measures the GLB it ships, so a
change to the skill, the MCP server, the generation backend or the model can be
judged against a recorded baseline instead of argued about.

```bash
python3 bench/test_measure.py          # the instrument first: seeded defects, 10/10 expected
python3 bench/run.py baseline          # all six briefs
python3 bench/run.py lot2 ai-mushrooms # one brief under a new label
```

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

**On the session**, from the `stream-json` transcript: turns, wall time,
tokens, tool calls by name (screenshots included), and the CLI's
equivalent-API cost — not billed on a subscription, but the only comparable
measure of how much quota a run consumes.

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
- **Versions are pinned**: `blender-mcp` 2.0.0 with the addon it bundles (1.7),
  installed into a throwaway Blender profile. Blender itself is whatever the
  machine has — recorded in `blender.log`.
- **The machine's Hugging Face token is used.** `gradio_client` sends the locally
  saved token by default, so every Space call in these runs counted against a
  free logged-in account's ZeroGPU quota (3.5 min a day), not the anonymous one.
- **One run per brief.** A model is not deterministic; a single difference
  between two labels is a lead, not a verdict.
