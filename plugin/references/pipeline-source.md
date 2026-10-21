# Pipeline — [3] SOURCE

> Read before [3] SOURCE. Rule numbers are SKILL.md's Iron Rules.

## Contents
- [3] SOURCE — Marketplace or Create?
  - Marketplace Path
  - Creation Path

## [3] SOURCE — Marketplace or Create?

Ask: **"Search marketplaces or create from scratch?"**

### Marketplace Path

Load `references/sourcing-strategy.md`.

**Preflight (rule 23) — do this BEFORE the first search:**

```
get_polyhaven_status()   → {"enabled": false, "message": "...press N..."}
get_sketchfab_status()   → {"enabled": false, "message": "..."}
```

Both are OFF in a default addon install. While OFF, `search_polyhaven_assets`
and `search_sketchfab_models` are **not registered as commands** — they answer
`Unknown command type`, not "disabled". If either is off, show the `message`
field verbatim (it names the BlenderMCP sidebar panel and the N shortcut) and
offer to continue on the other source or switch to the creation path. Never
report the raw `Unknown command type` error to the user.

- Search PolyHaven + Sketchfab with brief keywords
- Present ~10 results (name, poly count, link)
- User can: pick a number, open links ("open 2, 5, 7" or "open all"), refine search, or switch to creation
- Sketchfab: filter downloadable + free only (requires API token)
- PolyHaven: fully free CC0

### Creation Path

**First: recommend a method** based on brief + style + type:

```
IF style = low-poly OR cartoon
    → recommend scripted ("Geometric style = scripting gives clean separated parts.")

IF type = furniture OR simple architecture AND style = stylized
    → recommend scripted ("Geometric + stylized = perfect for scripting.")

IF type = organic (rock, tree, food, creature) OR style = realistic + detailed
    → recommend AI ("Organic forms and realistic detail = AI excels here.")

IF type = complex architecture (cathedral, ornate facade) AND print not set
    → recommend AI ("Complex detail = AI handles it better.")
    # print set: a lighthouse, a windmill, a tower are simple objects — a lathe or a prism,
    # scripted (print.md § Scope). Two print sessions read this line against it.

IF type = character or creature   # decided before the style lines above, which read it otherwise
    → the style decides: cartoon / stylised → scripted, its body ONE skin (overlapping
      volumes or metaballs, one voxel remesh — `characters.md` § An animated creature;
      for print, `print.md` § Figures), never separate parts glued on, never one family
      per region on a skin that bends; realistic / detailed → recommend AI. Sessions read "cartoon → scripted" and
      "character → AI" as a contradiction on every mascot.
    → ASK: "Will this character need rigging/animation?"
      IF yes → force T-pose in concept image prompt
              → record it: the RIG SELECTION gate in PHASE 5c depends on it

ELSE
    → present both options without recommendation
```

Always explain WHY the recommendation, always let the user choose.

**Print set in CONFIG: the method follows the subject** (`references/print.md` § Scope). A
simple object is built from closed primitives. **A stylised figure** — a cartoon animal, a
character, a mascot — from metaball families and one voxel remesh (`print.md` § Figures): a
cartoon dragon from one flat drawing came out that way. **A realistic likeness of a real animal
or person from a photo is said at CONFIG to be out of reach of scripted modelling** — two cats,
metaballs included, passed every check and were unacceptable to look at: offer it as a stylised
figure, an image-to-3D generation repaired for print, or `print_check` on a model the user
brings. A mechanical
part (a load, a lid that must close, a size to the tenth) is said at CONFIG to belong in a CAD
tool, and goes on only as decorative if the user agrees. Parts joined by a peg: offer
`tools/fit_coupon.py`'s test print before modelling the joints — **in auto mode, do not wait
for it**: model at 0.2 mm a face, write the coupon next to the model, and say in the hand-over
that the clearance is not measured (`print.md` rule 5). Scripted, for both. **Load
`references/print.md` § Printable from the brief before the first primitive** — model at print size, closed solids only, one volume
(exact union as you go, or overlap + one voxel remesh), the process's minimum thickness, a flat
base, overhangs that grow out of the part below, relief as geometry. A generated or marketplace
mesh is repaired instead ([5]). Texturing ([5b]) carries nothing to a print. **With a reference
image, `references/print.md` § Like the photo, for print too**: the photo method in full, openings
read on their outer edge, details cut along the photo's camera, the `face` measure every round, and
rounds until the gaps stop closing — **the two-round cap of `reference-fidelity.md` § 5 does not
apply** — and the user decides it is alike.

**Options:**

| Method | Best for | Trade-off |
|---|---|---|
| **AI Generation (optional; TRELLIS.2 first)** | organic, realistic, complex | Single mesh, free daily quota |
| **Scripted modeling (Blender Python)** | furniture, archi, stylized, low-poly | Separated parts, clean topology, more geometric |
| **Geometry Nodes (procedural)** | scattering, patterns, parametric | Non-destructive, powerful but complex |
| **User-provided image → AI or scripted** | when user has reference art (path or URL) | Image guides any method (see below) |
| **Concept art first** | when starting from nothing | Generates concept image, then AI or scripted |

**Concept art input — 3 modes:**

Ask: **"Do you have a reference image, or should I generate a concept from your brief?"**

| Mode | How | Notes |
|---|---|---|
| **Text prompt** | Generate via the FLUX.1-schnell HF Space (free, Apache-2.0) | Default method |
| **Image path / drag-and-drop** | User provides local file path | Used as reference for any method |
| **Image URL** | User provides URL, downloaded via curl | Saved locally, used as reference |

**Reference image usage per method:**

A user-provided image (or generated concept art) is useful for ALL creation methods, not just AI generation:

| Method | How the image is used |
|---|---|
| **AI generation** | Passed directly as generation input (image → 3D) |
| **Scripted modeling** | **Load `references/reference-fidelity.md`** — inventory the details, measure the silhouette from the pixels (or, given a generated mesh of the photo, its profile with `tools/template_profile.py` — never ship that mesh), check every part is attached — and LOOK at every joint the review renders (`review/joints/`): a part that joins another enters it, section unchanged (a foot only if the photo shows one) — sample materials from the image (one material per physical material; patina stays metal), review twice against it — then, only when the photo carries text, a logo or precise wear and the shape is final, **propose** projecting the photo's markings (`tools/photo_project.py`, refused under 0.95 fitted IoU; show two other angles; never silently, rule 6 — `references/photo-projection.md`) |
| **Geometry Nodes** | Analyze image to inform node parameters — spacing, density, pattern, scale |
| **Marketplace** | Analyze image to refine search keywords and evaluate result similarity |

If nano-banana MCP is available, offer it as an alternative (supports iterative editing) — it bills a Gemini key, so only on explicit request (rule 5).

**Concept art & AI generation:** Load `references/ai-generation.md` for the concept-art commands, prompt rules, and the 3D backends.

**Scripted modeling flow:**

- `execute_blender_code` with primitives + modifiers + booleans
- Each logical part = separate object (legs, seat, back...) — for props. An animated
  character's body is ONE skin, its eyes, nose and eyelids apart (`characters.md` § An
  animated creature)
- Materials assigned per object from creation
- `get_viewport_screenshot` for iterative validation

**Geometry Nodes flow:**

For assets with repetitive patterns (railings, fences, stone walls, vegetation scattering):
- Create the node tree via `execute_blender_code` (Python API)
- Common patterns: Scatter (Distribute Points → Instance on Points), Extrude + Transform, Curve to Mesh. All four node types verified present on Blender 5.0.1
- **Realize Instances** at the end of the tree (GLTF has no concept of GN instances)
- **Then APPLY the modifier before export.** This is not optional and it is easy to
  miss, because nothing errors: geometry nodes output exists only as a modifier
  result, and rule 18 requires `export_apply=False`, so the exporter writes the
  *base* mesh. Measured on a scatter of 2,688 triangles:

  | Export | Result |
  |---|---|
  | `export_apply=False`, modifier live | **2 tris, 1.0 kB** — the whole scatter gone, silently |
  | `export_apply=True` | 2,688 tris — correct, but violates rule 18 |
  | **modifier applied, then `export_apply=False`** | **2,688 tris, 208.7 kB — correct and rule 18 holds** |

  ```python
  bpy.ops.object.modifier_apply(modifier="GN")   # procedural becomes geometry
  ```

  Keep the .blend with the modifier intact (rule 7) — that is where the
  procedural version survives. Apply on a copy, or apply after saving.
- ⚠️ **Simulation Zone gotchas**: Group Input values do NOT propagate into sim zones (pass via state items), geometry freezes after frame 1 (only state items persist), Set Position required after sim zone output
