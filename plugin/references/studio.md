# Kiln Studio — view, annotate, iterate

Kiln Studio is a local web page that shows every model in a project and lets the user
pin notes on them for you. You read the notes, change the model in Blender, re-export,
and reply. The page reloads the model the moment the file changes, and renders the
same view of the new version beside the note's own screenshot, so every note ends up
with a before and an after.

`<skill>/studio/studio.py` — Python standard library only, nothing to install. Its two
fonts ship with it (`static/fonts/`, SIL OFL), but three.js 0.186.1 is still fetched from
jsDelivr: the page's one outside request, so the browser needs a network connection.

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
- It opens the browser unless `--no-open`, or the project's `auto_open` is false (§ 9).
  Honour CONFIG's **Auto-open links**: when it is false, pass `--no-open` and give the user
  the printed URL.
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
more: the project's `exclude` (§ 9), e.g. `["site/public/*"]`.

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
Off too when the project's `live_view` is false (§ 9): then start Studio at EXPORT only.

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
| Draco or meshopt geometry, WebP or KTX2 textures | `extensionsUsed`, image formats | WARN on `_final` for a web target; a note for Unity/Unreal/PC, whose engine packs the file itself; other stages are not shipped |
| Licences | the log's Licenses section | note for CC-BY (credit), WARN for non-commercial |

With no log, the tier is assumed balanced and the type a prop, and the check says so. The
target is the log's, else the project's `target` (§ 9), else the web, assumed and said.
For `print` the checks set no triangle budget, and textures and compression are notes.
Report the WARN lines with the export summary; none of them is a target to tune to.

Each check is written for the user: what was found and why it matters, then **How to
fix** — the command to run, such as `/kiln optimize <name>` (copied on click), or "ask
Claude" — and an **Ask Claude** button that opens a note on the model with the request
written out, for the user to read and save; `/kiln studio` then picks it up like any note.
`studio.py checks` prints the same fix under each line. In `--json` each finding also
carries `msg`, `fix_msg` and `ask_msg`: lists of `[code, params]` from `checks.py`'s
`MESSAGES`, which the page renders in the user's language; `text`, `fix` and `ask` are the
same in English. The wording leaves out kiln's
rules, but they still hold when you act on one: a reduction is a proposal the user sees
before it is kept (rules 4 and 6), and OPTIMIZE runs resize, WebP and Draco as separate
steps (rule 20).

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
   is unambiguous). With the kiln-studio MCP tools in reach (§ 11), `get_selection` says
   which model the user has open and which note they picked: "this one" means that. Without one, run `studio.py notes`: one asset listed → take it;
   several → list them with their counts and ask which, or offer to go in order. **One
   asset per pass** keeps the context small.

2. **Read the notes.**

   ```bash
   python3 <skill>/studio/studio.py show <asset>
   ```

   It prints each model file (size, triangles, Blender dimensions), the `.blend`, the
   log, and every open or addressed note: its text, the pinned point in **Blender
   coordinates** (metres, Z up, front −Y) with face normal, the object, mesh and
   material hit, a rough region ("top, front (−Y), +X side"), the camera, the pictures,
   and the thread. **Read the pictures** — "this bit" means nothing without them. A pin
   has two: the **close-up** (`close-up of the pin:`), rendered nearer along the user's
   line of sight, to see what is at the spot — read it first; and the **screenshot**,
   the view cropped to the model, to see where it is. Four orange ticks point at the
   pin and leave the spot itself uncovered. A whole-model note has the screenshot only,
   and older notes a full-view JPEG with the spot ringed. Read earlier replies before redoing something that
   was already tried. A note "made on an earlier version" was pinned before the last
   export: trust the object and material names over the exact point.

   **Show the user what you are on** before you change anything:
   `studio.py work start <asset> [<asset>...] --label "acting on notes"` (§ 5).

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

6. **Next model.** `studio.py work next` — this one's dot goes green, the next one's
   starts breathing. Stopping before the list is done: `studio.py work end`.

7. **Wrap up** with the notes addressed, the ones waiting on the user, and the link
   (`studio.py open --asset <asset> --no-open` prints it). Don't commit unless asked;
   when you do, commit `.kiln-studio/` (notes, screenshots, history, catalog) with the
   model files — its own `.gitignore` already leaves out the model copy and the cache.

---

## 5. Work — which models you are on

Whenever a command changes models the page shows — `/kiln studio` on notes, `/kiln
optimize`, `/kiln texture`, `/kiln cleanup`, `/kiln convert` on files in the project —
and Studio is running (`studio.py status`), say which ones before the first change. Each
gets a dot in the page's list: a ring while it waits, breathing while you are on it,
green when you are done; a line above the list reads "Kiln · optimize · 1 of 3 · table".

```bash
python3 <skill>/studio/studio.py work start chair table lamp --label "optimize"   # chair active
python3 <skill>/studio/studio.py work next --text "8.2K → 2.4K tris"            # chair done, table active
python3 <skill>/studio/studio.py work next                                       # … lamp done: the run ends
```

- `start` takes the models in the order you will take them; the first is active at
  once. It replaces any earlier run. One model is a run of one.
- `next` closes the active model (`--text`: what was done, in a few words — the dot's
  tooltip) and moves to the next; after the last one the run is done.
- Out of order: `work begin <asset>` (the active one counts as done; a model not in the
  run joins it), `work done <asset>`. Stopping early: `work end` — the active model is
  done, the ones not started lose their dot. `work` alone prints the run.
- Call `next` once the model is re-exported, so the green dot and the reloaded model
  arrive together.
- The user clears a green dot by opening the model, or by leaving the one they watched
  finish; **Clear** above the list clears them all. When none is left, the run is gone.
- A run with no word from you for two hours is treated as stopped: its breathing and
  waiting dots go, the green ones stay.
- Not in batch runs: nobody watches them, and their models do not exist yet.

---

## 6. Commands

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
| `studio.py work start <asset>... --label L` | Show the user which models a command works on (§ 5); `next`, `begin <asset>`, `done <asset>`, `end`; alone, show the run |
| `studio.py config [KEY=VALUE ...]` | The project's settings (§ 9): print them, or set `live_view`, `auto_open`, `target`, `exclude` (`--json`) |
| `studio.py requests` / `request ID --status done --asset A` | The models asked for in the Create form (§ 10): list them, close one once built |

The commands other than `open` find the project from the current folder upwards (the
first folder holding `.kiln-studio/`); pass `--root PROJECT` from elsewhere.

---

## 7. What the user sees

The two side panels resize the view, and fold into 60 px rails (`[` the list, `]` the
notes, `\` both); the view fits the model again once they have moved. On a narrow
screen they lie over the view, one at a time, and the rails stay.

- **Left:** a search, a **View** menu (group by Folders or State, Normal or Compact rows,
  which models to show, sort), one row of tags, and four counters that filter the list:
  **To check** (notes you addressed), **Open**, **Claude works**, **Building**. While a
  command works on models (§ 5), a line under them: "Kiln · optimize · 1 of 3 · table".
  Every model has a thumbnail, its note counts, a "new" badge when it changed since the
  user last looked, and its work dot. Grouped by Folders, rows never move: a change
  updates the row in place, with a flash. Grouped by State (Claude works, Building, To
  check, Open notes, Nothing to do), rows move to their group, but not while the pointer
  is over the list: "2 changes · re-sort" waits for a click or for the pointer to leave.
  Folded, the rail shows the thumbnails with their counts and dots.
- **Centre:** orbit, pan, zoom; shading Lit / Unlit / Clay / Normals / UV checker /
  Faces (back faces red: flipped normals and holes; a list when the bar is short of room,
  with the display toggles under **Options**); wireframe, grid with the front
  marked, bounds with sizes in metres, bones; under the model's name, its stages, and an
  eye that hides the note pins (there once the model has one), and on hover hides the
  fixed ones or those behind the model. Pins stick to the surface: on a skinned mesh to
  the bone under them, so they follow the animation; "behind the model" is a ray from the
  camera against the mesh as posed. Preset views; animation clips with a scrubber;
  **Compare** with the previous version or another stage: a divider dragged across one
  view (one camera, the other version left of it) or side by side, with the triangle,
  file size and height change read from both files.
- **Right:** Notes (the composer at the top; pin or whole-model notes, statuses, threads,
  each with its picture and the pin's close-up in the corner, then the after beside it;
  **View** opens both large with a before/after slider and the close-ups; "Looks right" /
  "Not yet"), Checks (§ 3: each finding, how to fix it, Ask Claude), Details (stages,
  stats, textures, organise, previous version, side files and the log), History (one
  feed, newest first: every version seen with its render, size and triangle change, the
  build's phases, the checks, every note and reply). Folded, the rail shows each tab with
  its count, and N / M.
- **An empty project** opens on a welcome: **See an example** copies kiln's gallery barrel
  (MIT) into `kiln-example/barrel/` to try the page on, and *Your setup* says what Studio
  can see: Blender found (PATH, `$BLENDER`, the usual folders) or not; the Blender MCP
  connection as **unknown**, with whether Claude Code is set up for one and whether the
  add-on answers on port 9876 (only Claude can say it is connected); SkinTokens through
  `tools/autorig.py status --quick` when this kiln has it, unknown otherwise. `/kiln setup`
  is the full scan.
- **While kiln builds:** a "building" mark in the list, and the phases above the model.
- **While a command works on models** (§ 5): a dot on each — waiting, breathing, green —
  and its progress above the list; a toast as it moves from one model to the next.
- **States read without colour too:** a work dot is a ring (waiting), a disc with a halo
  (working) or a tick (done); a check is ✓, i or !; a pin is solid (open), ringed
  (addressed), hollow (resolved) or dashed (won't fix); counts to check carry a ✓.
- **Keys:** `/` find, `↑ ↓` previous and next model, `1`–`6` views, `F` frame, `S` / `⇧S`
  shading, `W G B K` wire, grid, size, bones, `P` pins, `C` / `⇧C` compare and its layout,
  `N` pin a note, `M` whole-model note, `Space` play, `?` the list. **⌘K** (Ctrl+K) opens
  every command by name, with its key: type to filter, Enter runs it; a model's name opens it.

Only one previous copy of a model is ever kept. The record of what a model looked like
at each step is the pictures on each note and the version renders — WebP, 10 to 20
kilobytes each (JPEG where the browser cannot write WebP), not a copy of the model.

## 8. Storage

```
PROJECT/.kiln-studio/
├── .gitignore                    baseline/, cache/, server.json
├── config.json                   the project's settings (§ 9)
├── catalog.json                  category and tags per asset
├── work.json                     the models a command is working through (§ 5)
├── assets/<id with / as ~>/
│   ├── notes.json                notes and their threads
│   ├── history.json              versions seen + changelog
│   ├── live.json                 the last build: its phases, step by step
│   └── shots/                    per note and per "addressed" reply: the view, and a pin's close-up (_detail)
├── baseline/<id>/                the one previous copy (git-ignored)
└── cache/                        version renders, server log (git-ignored)
```

Notes store points in both frames: `point` (glTF, Y up, front +Z) and `point_blender`.
Statuses: `open` → `addressed` (you) → `resolved` (the user) or `wontfix`.

---

## 9. Settings — the project's, and the user's

The page's **Settings** (the gear under the list, or ⌘K → Settings) has two parts.

**Personal** — this browser only, never in the project: the language (English or French;
the browser's by default), the theme (Dark, Light, High contrast, Forge, Neon, Studio, Minimal) and an accent colour
(Forge, Neon and Studio have their own), rows Normal or Compact, the shading and the view a model
opens in, lengths in metres or centimetres, whether fixed pins start hidden. Nothing for
you to read.

**Project** — `.kiln-studio/config.json`, committed with the notes. Read it at CONFIG
(`studio.py config`, or the file): a key **set in the file** is the session's default
(`studio.py config` marks the others `(default)`: they change nothing), and the user's
answer in the session wins.

| Key | Values (default) | What it sets |
|---|---|---|
| `live_view` | `true` / `false` (`true`) | CONFIG's **Live view**: false, do not export after each phase; start Studio at EXPORT |
| `auto_open` | `true` / `false` (`true`) | CONFIG's **Auto-open links**; `studio.py open` does not open the browser when false |
| `target` | `"web"`, `"desktop"` (Unity/Unreal), `"print"` (`"web"`) | CONFIG's **Target** when the brief names none; the checks' limits for a model whose log gives no target |
| `exclude` | glob patterns from the project folder (`[]`) | folders and files Studio leaves out of the list |

Studio refuses an unknown key or a bad value from the page, and keeps any other key the
file has as it is.

---

## 10. Create and Import — models the user brings or asks for

**Import.** A `.glb .gltf .fbx .obj` dropped anywhere on the page, or picked with the
import button, is saved into `imports/` (a glTF or OBJ dropped with its `.bin`, `.mtl` or
textures: `imports/<its name>/`), never over a file already there (`chair-2.glb`), and opens.
It is an ordinary model from then on: notes, checks, `/kiln studio`.

**Create.** The form (brief, type, target, style, an optional reference photo) writes a
request into `.kiln-studio/requests.json` — open, like a note, the photo beside it in
`.kiln-studio/requests/` — and gives the user the command to paste:

```
/kiln a sturdy oak barrel, type prop, for the web (glTF), stylized, reference photo .kiln-studio/requests/q_….jpg (Studio request q_…)
```

It is a brief like any other: run the pipeline on it, the photo as the reference image.
When the model is exported, close the request:

```bash
python3 <skill>/studio/studio.py request q_… --status done --asset <the asset>
```

`studio.py requests` lists the open ones (`--all`, `--json`).

---

## 11. The kiln-studio MCP server — what the user is looking at

The plugin declares a small MCP server, `kiln-studio` (`.mcp.json` at the plugin root →
`studio/mcp_server.py`, standard library, stdio). It reads what the open Studio page shows
and the notes; it writes nothing but note replies.

| Tool | Gives / does |
|---|---|
| `get_selection` | The model the page shows (asset id), its stage, the camera in Blender's frame, the note picked, compare and shading, and how many seconds ago the page said so |
| `get_notes` | The notes of an asset (default: the one open), as `studio.py show` gives them, with the pictures' absolute paths to read; no asset and none open: the assets with notes |
| `reply_to_note` | `studio.py reply`: `status` addressed, open or wontfix — never resolved |
| `set_camera` | Turns the open page's view: `view` (front, back, left, right, top, iso), a `note`'s own view, or `position_blender` and `target_blender`; with `asset`, opens it first |

Their full names, as Claude Code calls a plugin's MCP tools (`mcp__plugin_<plugin>_<server>__<tool>`):
`mcp__plugin_blender-kiln_kiln-studio__get_selection`, `…__get_notes`, `…__reply_to_note`,
`…__set_camera` — the skill's `allowed-tools` lists all four.

**When to call `get_selection`:** before anything the user says about what is on their
screen without naming it — "what am I looking at", "fix this", "this note", "here", "the
one open" — and at the start of `/kiln studio` without an argument when Studio is open.
Then `get_notes` for that model; `set_camera` to show the user a change from the note's view.

It finds the project from `KILN_STUDIO_ROOT`, `CLAUDE_PROJECT_DIR` (the plugin passes it) or the session's folder,
upwards (each tool takes `root`). Without a running Studio, `get_selection` and `set_camera`
say so; `get_notes` and `reply_to_note` work from the files alone. Use `set_camera` to show
the user what you changed, from the note's camera, before asking them to look.
