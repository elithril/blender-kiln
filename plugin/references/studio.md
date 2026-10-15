# Kiln Studio — view, annotate, iterate

Kiln Studio is a local web page that shows every model in a project and lets the user
pin notes on them for you. You read the notes, change the model in Blender, re-export,
and reply. The page reloads the model the moment the file changes, and renders the
same view of the new version beside the note's own screenshot, so every note ends up
with a before and an after.

`<skill>/studio/studio.py` — Python standard library only, nothing to install. The
page loads three.js 0.186.1 from jsDelivr, so the browser needs a network connection.

---

## 1. Start it

```bash
python3 <skill>/studio/studio.py [PROJECT] [--asset ID] [--no-open]
```

- `PROJECT` is the folder to show, default the current one. Use the **project root**
  (the folder kiln's output folder sits in, or the game/web project the assets are for),
  not the output folder itself: notes are stored under `PROJECT/.kiln-studio/`.
- It prints the URL and returns. A Studio already serving that folder is reused (its
  URL is printed, nothing restarts); otherwise one starts in the background, logging to
  `.kiln-studio/cache/server.log`. `studio.py stop` stops it, `studio.py status` reports it.
- It opens the browser unless `--no-open`. Honour CONFIG's **Auto-open links**: when it
  is false, pass `--no-open` and give the user the printed URL.
- `--asset generated-assets/wooden-chair` opens on that model.

**When to start it:** in an interactive session, once the brief is confirmed, so the user
watches the model being built (§ 2); with Live view off, at the end of EXPORT, once the
first model of the session is written. Say one line — "Kiln Studio shows it at <url>: pin
notes on it and run `/kiln studio` when you want me to act on them" — and start it.
In batch or unattended runs, do not start it; print the command in the final summary.
On `/kiln studio` with no notes to act on, start it and stop there.

What it finds: every `.glb .gltf .fbx .obj` under the folder, skipping hidden folders,
`node_modules`, Unity's `Library/` and `Temp/`. Kiln's
`<name>/<name>_{original,clean,textured,optimized,final,live}.glb` is **one** asset whose
stages are switchable variants, with its `.blend`, `_log.md` and images listed beside
it; the folder above (the output or batch folder) is its default category. Excluding
more: `.kiln-studio/config.json` → `{"exclude": ["site/public/*"]}`.

---

## 2. Live view — the model as it is built

While kiln builds, the page shows the scene after each phase. At the end of every phase
that changed geometry or materials (where rule 2 takes its screenshot), append to that
phase's last `execute_blender_code` call:

```python
import sys; sys.path.insert(0, "<skill>/studio"); import blender_live
blender_live.snapshot("<project root>", "generated-assets/wooden-chair", "cleanup", "welded, normals out")
```

- The folder is the asset's output folder, relative to the project root; the asset takes
  its name. It exports the scene to `wooden-chair/wooden-chair_live.glb` — written under a
  hidden name and moved into place, uncompressed, `export_apply` off (rule 18) — and
  records the phase (`config brief source import cleanup texture rig animate optimize
  export`; `[5b] TEXTURING` and `5b` work too) with what it did, in a few words.
- `export=False` records a step without exporting (a phase that changed nothing visible).
  From a shell: `studio.py live generated-assets/wooden-chair --phase brief --text "…"`.
- The page opens a model being built if none is open, shows the phases above it, reloads
  it as each export lands and refits the view, and files each version in History under
  its phase, with a render. `_live` is the default stage while it is the newest file.
- **At EXPORT,** once `_final` is written: `studio.py live wooden-chair --end` closes the
  build and removes `_live.glb` — compact storage keeps original, final, `.blend` and log
  (`--keep-file` keeps it). History keeps every live version's size, triangles and render.

Off in batch runs: nobody watches them, and the wizard's token estimate does not count it.

---

## 3. Checks — kiln's rules, read off the file

The page's **Checks** tab, and `studio.py checks <asset>` (`show` prints its warnings),
read the production log and the model file:

| Check | From | Level |
|---|---|---|
| Triangles against the detail tier's soft range | log's Type and Tier, `topology-rules.md` | note above the top, WARN past twice it (rule 4: never blocks) |
| Size, and the usual height of a chair, table, door or character | `validation-checklist.md` § Scale | WARN under 1 cm or over 100 m |
| On the ground at Z = 0, centred on the origin | the bounds | WARN on a kiln asset |
| Texture sizes against the target's cap: 1024 for web, 2048 for console/PC | images read in the file | WARN on `_final` |
| Draco or meshopt geometry, WebP or KTX2 textures | `extensionsUsed`, image formats | WARN on `_final`; other stages are not shipped |
| Licences | the log's Licenses section | note for CC-BY (credit), WARN for non-commercial |

With no log, the tier is assumed balanced and the type a prop, and the check says so.
Report the WARN lines with the export summary; none of them is a target to tune to.

**Against the reference photo.** `tools/fidelity_check.py` writes `fidelity.json` and a
`fidelity_log.jsonl` line per run into its `--out`. With `--out <name>/review/<view>/` (one
folder per reference view), the tab shows the silhouette IoU and its rounds, whether the
measured file is the current one (by hash), the overlay and side-by-side, the ranked gaps,
the per-band widths, the joint renders, and a **Photo's view** button that turns the model
to where the photo's camera stood.

**In a batch folder,** it shows the wizard's token estimate from `batch-manifest.yaml`
(`batch-mode.md` § Step 4): this asset's, the whole batch's and what is left to run, ±50%;
the list shows the batch's range on its folder header.

---

## 4. `/kiln studio [asset]` — act on the user's notes

1. **Pick the work.** With an asset argument, that asset (`chair` works when the name
   is unambiguous). Without one, run `studio.py notes`: one asset listed → take it;
   several → list them with their counts and ask which, or offer to go in order. **One
   asset per pass** keeps the context small.

2. **Read the notes.**

   ```bash
   python3 <skill>/studio/studio.py show <asset>
   ```

   It prints each model file (size, triangles, Blender dimensions), the `.blend`, the
   log, and every open or addressed note: its text, the pinned point in **Blender
   coordinates** (metres, Z up, front −Y) with face normal, the object, mesh and
   material hit, a rough region ("top, front (−Y), +X side"), the camera, the screenshot
   path, and the thread. **Read each screenshot** — "this bit" means nothing without
   it; the ringed spot is the pin. Read earlier replies before redoing something that
   was already tried. A note "made on an earlier version" was pinned before the last
   export: trust the object and material names over the exact point.

3. **Keep a way back.** Studio keeps one previous copy of each annotated model, taken
   when the user's first note on that version was saved — the user compares against
   it and can put it back. If the user asked for a change in chat rather than in a
   note, take it yourself before editing: `studio.py snapshot <asset>`.

4. **Change the model** with the usual pipeline rules: open the asset's `.blend`,
   change it, look from the note's camera (`camera (Blender) at … looking at …`) and
   from one other angle, then re-export **to the same file** — Studio tracks files by
   path. Rule 6 still applies: destruction stays a proposal.

5. **Answer each note.**

   ```bash
   python3 <skill>/studio/studio.py reply <asset> <note id> "What changed, in a sentence or two." --status addressed
   ```

   - `--status addressed` only after the new file is exported. The page then renders
     the after view itself; to attach your own render instead (Blender, from the note's
     camera), add `--image render.png`.
   - A question, or a note you will not do: reply without `--status` (the note stays
     open), or `--status wontfix` with the reason when the user agreed.
   - **Never mark a note resolved**: only the user closes a note, after looking. The
     CLI refuses `resolved`.
   - A change that was not asked for in a note: `studio.py log <asset> "what changed"`
     puts it in the asset's history.

6. **Wrap up** with the notes addressed, the ones waiting on the user, and the link
   (`studio.py open --asset <asset> --no-open` prints it). Don't commit unless asked;
   when you do, commit `.kiln-studio/` (notes, screenshots, history, catalog) with the
   model files — its own `.gitignore` already leaves out the model copy and the cache.

---

## 5. Commands

| Command | Does |
|---|---|
| `studio.py [open] [PROJECT]` | Start or reuse Studio, print the URL (`--asset`, `--port`, `--no-open`, `--foreground`) |
| `studio.py stop` / `status` | Stop / report this project's Studio |
| `studio.py list` | Every model: triangles, category, tags, note counts (`--json`) |
| `studio.py notes` | Assets with open notes (`--all`: any notes) |
| `studio.py show <asset>` | Files, stats, previous version, active notes (`--all`, `--status S`, `--json`) |
| `studio.py history <asset>` | Versions seen (hash, size, triangles), changelog, notes and replies, in order |
| `studio.py reply <asset> <note> "text"` | Answer a note (`--status addressed\|open\|wontfix`, `--image`) |
| `studio.py log <asset> "text"` | Add a changelog entry |
| `studio.py snapshot <asset>` | Keep the file as it is now as the previous version |
| `studio.py revert <asset>` | Put the previous version back; the replaced one becomes the previous (undoable) |
| `studio.py meta <asset> --category C --tags a,b` | Organise: category and tags (empty clears) |
| `studio.py checks <asset>` | Tier, size, ground, textures, compression, licences, fidelity, batch estimate (`--json`) |
| `studio.py live <folder> --phase P --text "…"` | Record a build step; alone, show the build; `--end` closes it and removes `_live` |

The commands other than `open` find the project from the current folder upwards (the
first folder holding `.kiln-studio/`); pass `--root PROJECT` from elsewhere.

---

## 6. What the user sees

- **Left:** every model with a thumbnail, grouped by category (the folder by default;
  editable), filterable by text, tags and note state; a "new" badge when a model
  changed since they last looked.
- **Centre:** orbit, pan, zoom; shading Lit / Unlit / Clay / Normals / UV checker /
  Faces (back faces red: flipped normals and holes); wireframe, grid with the front
  marked, bounds with sizes in metres, bones; preset views; animation clips with a
  scrubber; **Compare**: the previous version or another stage side by side, one camera
  for both, size and triangle change shown.
- **Right:** Notes (pin or whole-model, statuses, threads, before/after shots,
  "Looks right" / "Not yet"), Checks (§ 3), Details (stages, stats, textures, organise,
  previous version, side files and the log), History (every version seen with its render,
  size and triangle change, the build's phases, and every note and reply).
- **While kiln builds:** a "building" mark in the list, and the phases above the model.

Only one previous copy of a model is ever kept. The record of what a model looked like
at each step is the screenshot on each note and the version renders — a few tens of
kilobytes each, not a copy of the model.

## 7. Storage

```
PROJECT/.kiln-studio/
├── .gitignore                    baseline/, cache/, server.json
├── catalog.json                  category and tags per asset
├── assets/<id with / as ~>/
│   ├── notes.json                notes and their threads
│   ├── history.json              versions seen + changelog
│   ├── live.json                 the last build: its phases, step by step
│   └── shots/                    one per note, one per "addressed" reply
├── baseline/<id>/                the one previous copy (git-ignored)
└── cache/                        version renders, server log (git-ignored)
```

Notes store points in both frames: `point` (glTF, Y up, front +Z) and `point_blender`.
Statuses: `open` → `addressed` (you) → `resolved` (the user) or `wontfix`.
