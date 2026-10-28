<!--
DRAFT README for blender-kiln 3.0 — not committed. Written against:
  release/3.0 @ 47fe14a, origin/feat/print-check @ ebf0027 (PR #26), origin/kiln-studio @ a183996 (PR #27),
  origin/bench-results (summary.json of final-ahujasid, final-lab, ref-kiln-v15, ref-kiln-v15gen).
Placeholders: [GIF: …], [PHOTO: …], [SCREENSHOT: …], [TO MEASURE], [TO RERUN AFTER MERGE], [TO WRITE].
Line counts and test counts in "Skill structure" / "Continuous checks" must be regenerated after
both PRs are merged: verify_docs.py checks them (±15 %).
-->

<p align="center">
  <img src="blender-kiln-logo.png" alt="blender-kiln logo" width="200" />
</p>

<h1 align="center">blender-kiln — The 3D Asset Forge</h1>

<p align="center">
  <a href="https://github.com/elithril/blender-kiln/actions/workflows/verify.yml"><img alt="docs verified" src="https://github.com/elithril/blender-kiln/actions/workflows/verify.yml/badge.svg" /></a>
  <a href="https://github.com/elithril/blender-kiln/actions/workflows/blender.yml"><img alt="Blender checks" src="https://github.com/elithril/blender-kiln/actions/workflows/blender.yml/badge.svg" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg" /></a>
  <img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-d97757" />
  <img alt="Blender 4.4+, verified on 5.0 and 5.2" src="https://img.shields.io/badge/Blender-4.4%2B%20%C2%B7%20verified%205.0%2F5.2-e87d0d?logo=blender&logoColor=white" />
  <a href="https://github.com/elithril/blender-kiln/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/elithril/blender-kiln?style=flat" /></a>
</p>

**Describe an object, or show a photo of it, and get back a clean 3D model you can edit, ship in a game or on the web, animate, or print.**

kiln is a Claude Code skill on top of a Blender MCP server. The MCP server gives Claude
hands in Blender; kiln gives it the production method — sourcing, modelling, cleanup,
texturing from CC0 scans, optimization, validation, export — and measures the file it
ships. It runs on both servers: [ahujasid's `mcp-for-blender`](https://github.com/ahujasid/mcp-for-blender)
and the Blender Foundation's [official Blender Lab MCP](https://projects.blender.org/lab/blender_mcp),
the server behind Claude's Blender connector.

<sub>Cited in <a href="https://arxiv.org/abs/2606.01057"><i>3DCodeBench: Benchmarking Agentic Procedural 3D Modeling Via Code</i></a> (Google DeepMind, USC, 2026), §1.</sub>

<p align="center">
  <img src="docs/images/photo-to-asset.webp" alt="Three reference photos — a hurricane lantern, an ammo box, a gothic chair — and below each, the GLB kiln 2.0 shipped from it, turning" width="100%" />
</p>
<p align="center"><sub>From one photo each, no marketplace, no AI generation: scripted in Blender, textured from CC0 scans,
measured against the real object. Shape scores against the real assets: <b>0.897</b>, <b>0.950</b>, <b>0.750</b> —
<a href="docs/benchmarks.md">how they are measured</a>.</sub></p>

## Quickstart

```
/plugin marketplace add elithril/blender-kiln
/plugin install blender-kiln@blender-kiln
/kiln setup
/kiln A hanging iron lantern for a medieval inn, stylized, for the web
```

`/kiln setup` detects Blender, the MCP server and the optional tools, and says what is
missing — see [Requirements](#requirements). Then, for example:

```
/kiln Rebuild the lamp in ./lamp.png as a game asset
/kiln optimize ./generated.glb               # a GLB from anywhere: lighter, checked
/kiln animate SK_Cat.glb walk, idle
/kiln A 90 mm windmill for my FDM printer
/kiln studio                                 # look at the models, pin notes, let Claude act on them
```

## What's in 3.0

| | |
|---|---|
| **Assets for games, the web and AR** | GLB, FBX, USDZ — clean, named, on the ground, at real size, compressed (Draco, WebP), validated |
| **From a photo, measured** | the silhouette and materials compared with the photo before shipping ([how](#how-it-works-from-a-photo)) |
| **A GLB you already have** | inspected, repaired, lightened, converted ([below](#your-glb-came-out-of-a-generator)) |
| **Animation** | walk and idle cycles, text-to-motion, keyed props ([Animate](#animate)) |
| **3D printing** — new | closed solids at size, a printability verdict, PrusaSlicer as a second opinion ([3D printing](#3d-printing)) |
| **Kiln Studio** — new | a local page to look at every model, pin notes on it and watch Claude address them ([Kiln Studio](#kiln-studio)) |
| **Organic characters** — new | creatures and figures built as one skin, rigged by a learned auto-rig (SkinTokens) for humanoids and generated meshes, ready-made humanoid moves ([Organic characters](#organic-characters)) |

<p align="center">
  [GIF: a model coming out of <code>/kiln animate</code> — e.g. the cat's walk or the dragon's wing flap, looped, ~4 s, under 3 MB]
</p>

## Your GLB came out of a generator?

TRELLIS, Hunyuan3D or another image-to-3D generator gives you a mesh that is often far
too heavy, sometimes in pieces, at an arbitrary size and with one baked material.
kiln works on the file you bring — no need to run the full pipeline:

| Command | What it does to your file |
|---|---|
| `/kiln inspect model.glb` | faces (tris / quads / ngons), vertices, objects, materials, textures and their sizes, bounding box, rig, animations |
| `/kiln cleanup` | merge by distance, recalculate normals, remove loose parts, dissolve degenerate faces, check for fused edges, apply transforms, origin at the centre of the base, scale check (1 unit = 1 m), rename to convention, clean orphans, check materials |
| (poly count) | reported against the detail tier; past twice its top, a **decimation is proposed with before/after previews — never applied without you**. Thin parts (wires, handles, loops) are rebuilt as curves instead of decimated |
| `/kiln texture` | textures a white or untextured mesh — Poly Haven CC0 scans first, procedural second; works on a single fused mesh by grouping faces |
| `/kiln optimize model.glb` | textures resized and converted to WebP, Draco geometry compression, or gltfpack simplification and LODs — each shown before/after, kept only if you say so |
| `/kiln convert` | GLB ↔ FBX, OBJ → GLB, to USDZ, with the material export audit before any glTF export |
| `/kiln animate` | folds bone-parented parts into the skin, checks the rig can bend where asked, then animates ([Animate](#animate)) |

What was measured, and what was not:

- **A generator's GLB, repaired end to end** (bench brief `repair-trellis-glb`, a raw TRELLIS
  output): 191,520 triangles, 11.4 MB, 13,732 non-manifold and 10,220 open edges → **9,000
  triangles, 0.64 MB, 0 and 0**, the thin bail and ring rebuilt as tubes, the rest closed and
  decimated with Blender's Collapse — 16 minutes, $3.89 of API-equivalent usage. On the official
  Lab MCP: the same 0 and 0, 0.93 MB.
- **A generated lantern finished as a game asset** (`ref-lantern-trellis`): shape kept, surface
  rebuilt, **0.946** against the real lantern's 3D model (2.2.0: 0.934 — [how it is scored](#measured-not-claimed)).
- **From a sentence, through the free Hugging Face Spaces** (`ai-mushrooms`): a FLUX.1-schnell
  concept, then TRELLIS.2 (MIT, 89 s of GPU), decimated to 8,991 triangles, textured, shipped at
  279 KB — 12 minutes, $3.80. kiln 2.2.0 went to Hunyuan3D-2 for the same brief, whose licence
  excludes the EU, the UK and South Korea; 3.0 uses it only when asked.

The generator's licence still applies to what you ship — see [What you can ship](#what-you-can-ship).

## How it works, from a photo

<p align="center">
  <img src="docs/images/how-it-works.webp" alt="Five steps from a real session on an ammo box: the photo read in crops, eight scanned textures compared, the silhouette overlay, every joint rendered, the shipped GLB" width="100%" />
</p>
<p align="center"><sub>Every panel is a file the session itself wrote while rebuilding the ammo box above — nothing re-staged.</sub></p>

1. **Read the photo before modeling.** An inventory of every part and how it meets the next,
   from enlarged crops; the real size, the camera's height and angle — asked, or stated as
   assumptions. Given a 3D mesh generated from the same photo, its proportions are measured
   instead ([TRELLIS.2, locally](plugin/references/ai-generation.md)) — never shipped.
2. **Texture from scans, not noise.** A Poly Haven CC0 texture set of the material family,
   chosen by eye against the photo, tinted to its palette, worn by the form.
3. **Measure against the photo.** [`plugin/tools/fidelity_check.py`](plugin/tools/fidelity_check.py) renders
   the model at the photo's camera under a studio light and lists the gaps — silhouette per
   height band, materials, metal that cannot exist.
4. **Look at every joint.** Each end of a long part that touches another is rendered alone: a
   part that joins another enters it.
5. **Ship, and measure the file that ships.** Optimized (Draco, WebP), validated, re-measured
   as a GLB — what the user gets, not the `.blend`.

## Measured, not claimed

A [quality bench](bench/README.md) runs the skill headless, each session in a sandbox,
and measures every file it ships after re-importing it. Photo references are Poly Haven
previews, so the real 3D asset exists: each rebuild is scored against it from five sides —
an asset the session never sees. Blender 5.2.2, Opus 5.5, `mcp-for-blender` 2.2.2, one run each,
October 2026:

| Against the real object (1 = identical) | **2.2.0** | **3.0** | 3.0 shipped | Usage (API-equivalent) |
|---|---:|---:|---:|---:|
| Hurricane lantern, from a photo | 0.900 | 0.885 | 1.18 MB | $6.04 |
| The lantern, with a measured template | 0.880 | **0.917** | 474 KB | $7.16 |
| The lantern, from a TRELLIS.2 mesh | 0.934 | **0.946** | 465 KB | $6.43 |
| Ammo box, from a photo | 0.774 | **0.936** | 373 KB | $4.45 |
| Gothic chair, from a photo | 0.637 | **0.720** | 449 KB | $6.64 |

| The whole bench — 19 briefs both versions ran, plus Kiln Studio | 2.2.0 | **3.0** |
|---|---:|---:|
| Briefs that shipped their files | 19 of 19 | 20 of 20 |
| Prints passing the printability check (PrusaSlicer second opinion) | 1 of 2 | **2 of 2** |
| Rig interpenetration when bent — villager / chibi | 3.15 % / 1.34 % | **0 % / 0 %** |
| A note pinned in Kiln Studio, addressed by Claude | — | **passed, $0.69** |
| Usage for the 19 briefs (API-equivalent) | $54.06 | $75.87 |
| The same 20 briefs on the official Lab MCP | — | 20 of 20, $84.97 |

> **About the usage column.** On a Claude Pro or Max subscription, these sessions are
> included in your plan's usage — there is nothing extra to pay. The dollar figure is what
> the same session would have cost on the Anthropic API (Claude Code's `total_cost_usd`);
> the bench uses it to compare versions, and as a rough measure of how much of your plan's
> usage a run takes. kiln itself never pays for a service (rule 5).
<!-- Do not write "free": a subscription is not free, and plan limits apply. -->

<sub>Shape score: mean silhouette overlap with the real asset from front, back, sides and top
(`bench/gt_compare.py`); openwork views left out for the chair. Size is assumed when a brief gives
none, and a single photo does not give it: every lantern came out 20 to 50 % taller than the real
one. One run per brief, and runs of the same skill differ by about ±0.02. 3.0 costs about 40 %
more than 2.2.0: the new checks (render reviews, UV, printability), the learned auto-rig, closed
loops and the photo projection are extra work in the session. Three photo briefs and the
generator repair were re-run after fixes the bench itself found — what changed and why is in the
[CHANGELOG](CHANGELOG.md).</sub>

**Close, not identical, on purpose.** kiln stops at a few dollars of API-equivalent usage per object.
[img2threejs](https://github.com/img2threejs/img2threejs), which rebuilds an image as Three.js
code through eight vision-reviewed passes, keeps finer surface detail: on the same lantern its
likeness was comparable — 0.866 against kiln's 0.861 — at about three times the usage, estimated on
a run stopped after three of its eight passes
([benchmarks § 4](docs/benchmarks.md#4-kiln-against-an-image-to-code-tool)).

What did not improve is published too: the [benchmarks](docs/benchmarks.md) — fifteen
versions of one lantern, what each fix broke, how the bench was kept honest — and every
number, render and GLB under 1 MB on the [`bench-results`](https://github.com/elithril/blender-kiln/tree/bench-results) branch.

## Requirements

| | Needed | Notes |
|---|---|---|
| **Claude Code** | yes | with a Claude subscription (Pro, Max) or an API key — usage, see [above](#measured-not-claimed) |
| **Blender** | **4.4 or newer** | hard floor: the animation code uses layered actions (4.4+). Measured on **5.0** locally and **5.2 LTS** in CI; the bench ran 5.2.2. 4.4–4.5 satisfy the API but are untested |
| **A Blender MCP server** | yes, one of the two | [ahujasid's `mcp-for-blender`](https://github.com/ahujasid/mcp-for-blender) (addon on port 9876, `uvx blender-mcp install-addon`; the bench pinned 2.0.0) or the [official Blender Lab MCP](https://projects.blender.org/lab/blender_mcp) |
| **GPU** | no | the default path is Claude scripting Blender: no AI model, nothing to install |
| **Python 3** | yes | the tools and Kiln Studio use the standard library only |
| `gltf-transform` (Node) | strongly recommended | `npm install -g @gltf-transform/cli` — WebP, Draco and the Khronos validator every export runs |
| `gltfpack` | optional | `npm install -g gltfpack` — simplification, LODs |
| Sketchfab API token | optional | free account, for marketplace downloads |
| **3D printing:** PrusaSlicer | optional | second arbiter for `print_check` (`--slicer`); measured with 2.9.6 |
| **3D printing:** macOS 14+ | optional | `tools/cutout.swift` cuts a photo's subject out with macOS Vision, locally |
| **Kiln Studio:** a browser | yes, for Studio | with a network connection: three.js 0.186.1 loads from jsDelivr. No extra API key — see [Kiln Studio](#kiln-studio) |
| Local TRELLIS.2 | optional, never required | measured on an M4 Pro with 24 GB: 31 GB of weights, 19.5–22.5 GB of memory at peak |
| UniMate (text-to-motion) | optional | 3.2 GB on disk; upstream is NVIDIA-only, kiln's patch runs it on Apple Silicon (measured on an M4 Pro) and CPU |

The bench ran on an Apple M4 Pro with 24 GB of memory, macOS, Blender 5.2.2.

### How long it takes

Time Claude spent on whole headless sessions in the bench (auto mode, every question answered
in the brief, so no time waiting for you), Blender 5.2.2, skill 3.0, one run each, October 2026.
An interactive session adds your answers.

| Task | ahujasid MCP | Official Lab MCP |
|---|---:|---:|
| Scripted prop from a text brief (lantern) | 3.5 min | 3.6 min |
| A Poly Haven model imported and finished (chair) | 3.5 min | 3.0 min |
| PBR texturing (crate) | 6.3 min | 7.0 min |
| Rigged character (villager) | 7.1 min | 6.5 min |
| Batch brief (three props) | 7.8 min | 8.6 min |
| AI brief (FLUX + TRELLIS.2 Spaces) | 12.3 min | 16.6 min |
| **Rebuild from a photo** (lantern / ammo box / chair) | 18.3 / 15.3 / 23.0 min | 19.1 / 19.1 / 16.7 min |
| A generator's GLB repaired (TRELLIS lantern) | 16.0 min | 15.0 min |
| Humanoid rigged and walking (chibi) | 12.8 min | 9.3 min |
| Quadruped walk and idle (cat) | 12.9 min | 21.6 min |
| 3D print: a 4-colour figurine / a box with a bayonet lid | 16.6 / 6.3 min | 10.9 / 7.2 min |
| Kiln Studio: a pinned note addressed | 1.4 min | 1.5 min |

Single steps, measured where stated:

| Step | Time | Source |
|---|---:|---|
| UniMate, one clip | 18 s on an M4 Pro | CHANGELOG 2.1.0 |
| UniMate install | 77 s with warm package caches; several minutes the first time | `references/animation.md` |
| Local TRELLIS.2, one model | 5–7 min on an M4 Pro, 24 GB | benchmarks § 7 |
| TRELLIS.2 HF Space, one generation | 89 s of GPU quota (a free account gets about 3.5 min a day: one concept image plus one model) | bench, October 2026 |
| Concept art, FLUX.1-schnell Space | 5.6 s an image | CHANGELOG |
| Stylised print figure (cartoon dragon, four colour parts) | 23 min, one v2.2 session | `references/print.md` |
| A print object from a brief (end to end) | 6 to 17 min — a box with a bayonet lid, a 4-colour figurine | bench, October 2026 |
| The fit test print (`fit_coupon.py`) | about 20 min — PrusaSlicer's estimate, not timed on a printer | CHANGELOG 2.3.0 |
| Repair and optimize a generator's GLB (191,520 → 9,000 triangles) | 16 min | bench, October 2026 |
| Kiln Studio, a note addressed (read → change → re-export → reply) | 1.4 min of Claude, 2.4 min with Studio's Blender starting | bench, October 2026 |

## What you can ship

kiln's own code is MIT. What you can do with an asset depends on where its parts came from,
and kiln writes each source and its licence into the asset's production log
(`<name>_log.md`). Kiln Studio's Checks tab reads those entries back ("credit the author",
"not for commercial use").

| Source | Licence | What it means for you | Checked in |
|---|---|---|---|
| **Scripted modelling** (the default) | — | geometry Claude wrote in Blender for you; no third-party model involved | — |
| **Poly Haven** textures, HDRIs, models | **CC0** | "use the work in any way and for any purpose, including commercial purposes", no attribution required. Using their *live API* asks for a credit to Poly Haven, which kiln writes in the log | [polyhaven.com/license](https://polyhaven.com/license); [`Public-API` ToS](https://github.com/Poly-Haven/Public-API) §2.4–2.5 |
| **Sketchfab** downloads | **per model**: CC0, CC BY, CC BY-SA, CC BY-NC, ND variants, or Sketchfab's Standard licence | read on each model's page. kiln shows the licence in search results, logs it, alerts when attribution is required, and never downloads a CC BY-NC model for a commercial project without asking | [Sketchfab Help](https://help.sketchfab.com/en/articles/16152217) |
| **TRELLIS.2** (Space or local) | code and weights **MIT** | — but two parts are not: its background remover **RMBG-2.0 is CC BY-NC 4.0** (the Space uses it on any image without an alpha channel — send a cut-out), and its image encoder **DINOv3** is under Meta's **DINOv3 License** (gated, your account's acceptance) | [TRELLIS.2 LICENSE](https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE); [DINOv3 LICENSE](https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md); Space `app.py` read 2026-10-09 |
| **TRELLIS** Space (`trellis-community`), **TripoSR** Space | MIT; TRELLIS's background removal is `rembg` (MIT) + U²-Net (Apache-2.0) | — | `references/ai-generation.md` |
| **Hunyuan3D 2.0 / 2.1** (Space, local, MCP) — on request only | **Tencent Hunyuan 3D Community License** | **not licensed in the European Union, the United Kingdom or South Korea.** Line 3 of the licence: *"THIS LICENSE AGREEMENT DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA"*; §5(c) forbids using the works **or their Output** outside that Territory; services above 1 million monthly active users need a licence from Tencent (§4) — section numbers from the 2.0 text; 2.1 opens with the same line. kiln never proposes it first, quotes that line and waits for a yes | [Hunyuan3D-2 LICENSE](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE), [Hunyuan3D-2.1 LICENSE](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE) |
| **UniMate** (text-to-motion) | code MIT; **checkpoints CC BY-NC 4.0** | **non-commercial use only**; kiln treats the motions it generates as covered too, and says so before running it | [UniMate README § License](https://github.com/Friedrich-M/UniMate#%EF%B8%8F-license); [model LICENSE](https://huggingface.co/Linzhan/UniMate/blob/main/LICENSE) |
| `tools/quadruped.py`, keyed props | MIT (kiln) | scripted cycles, no model weights | — |
| **FLUX.1-schnell** concept art | Apache-2.0 | concept images only, never shipped in the GLB | `references/ai-generation.md` |
| Mixamo (optional, humanoids) | Adobe account, Adobe's terms | [not checked here] | `references/characters.md` |

<sub>Licences read on 2026-10-16. This is a summary, not legal advice: read the licence before
shipping anything commercial.</sub>

## 3D printing

<p align="center">
  <img src="docs/images/print-windmill.webp" width="100%" alt="A Dutch windmill kiln modelled for an FDM printer: the coloured preview, and the two STL parts as they print — the body upright, the lattice sails flat beside it" />
</p>

Say it will be printed — FDM or resin, a height, your printer's colours — and kiln models
**for the printer from the first primitive**: at size, in closed solids joined into one
volume, walls thick enough (0.8 mm FDM, 0.5 mm resin), a flat base, overhangs designed out
where nobody looks, relief as geometry, and in several parts when one would print in the
air — the windmill above is a body and its sails, laid flat, each checked on its own. STL in
millimetres. Every STL ends with [`tools/print_check.py`](plugin/tools/print_check.py): open and
non-manifold edges, normals, held and floating parts, walls, overhangs, loss against the
original, the smallest scale you can shrink it to in the slicer, and PrusaSlicer as a
second opinion ([`references/print.md`](plugin/references/print.md)).

<p align="center">
  <img src="docs/images/print-teapot.webp" width="100%" alt="A museum photo of an 18th-century drum teapot, and the printable model kiln built from it: body, spout rings, ribbed lid, diamonds and zigzags engraved 0.6 mm deep to paint" />
</p>

Measured on sessions given the skill and nothing else: a dog house and a lighthouse from a
brief, a pumpkin and a ghost from photos, the windmill, and this teapot from three museum
photos — printable, and like what was asked.

**Stylised figures, not likenesses.** Two cats — one held by the ghost, one from a real cat's
photo — passed every check and were unacceptable to look at. A stylised figure is another
matter: a session made a cartoon dragon from one flat drawing, in four colour parts, from
**metaball families and one voxel remesh**, and a fresh session then made a cartoon fox the
same way. So print mode builds a stylised figure that way, and says at CONFIG that a
realistic likeness of a real animal or person is out of reach of scripted modelling.

<p align="center">
  [PHOTO: the windmill, printed — body and sails assembled, on the bed or on a table, with the printer and filament named in the caption]<br>
  [PHOTO: the teapot, printed and painted, beside the museum photo]<br>
  [PHOTO: a colour figure (the dragon or the fox), printed in its four filaments]
</p>
<!-- These photos do not exist yet. Until they do, keep the "None of these models has been printed yet" limit below. -->

### A model you made: flatten it, then check it

<p align="center">
  <img src="docs/images/print-flatten-prusaslicer.svg" width="100%" alt="What PrusaSlicer lays down for the windmill turned 1 degree with 10 percent of its vertices off: the gallery floor's top layer in 4 heights and one edge of the base on the bed; after flatten.py, one height and the whole base" />
</p>

A model finished by hand often has faces that should be flat and are not, and sits a degree
off. [`tools/flatten.py`](plugin/tools/flatten.py) makes nearly flat faces exactly flat and lays the
base on the bed — on the windmill above, **629 mm of first layer become 3,317** — and touches
nothing else: curves, folds, bevels and real slopes stay, no vertex moves past the tolerance,
the input is never overwritten.

```
/kiln inspect model.stl     # print mode: print_check's verdict
/kiln cleanup model.stl     # print mode: flatten.py, then print_check again, before and after shown
```

### Limits

- **None of these models has been printed yet.** Everything here was checked by PrusaSlicer
  2.9.6 and by renders, not on a bed. [UPDATE once the photos above exist]
- **FDM, checked with PrusaSlicer's default profile.** No resin slicing, no orientation search,
  no support generation, no build-volume check.
- **Scaled down in the slicer, a model loses its thin walls.** `print_check` says how far —
  "do not shrink below 40 %" for the windmill's body, 67 % for the lighthouse.
- **Parts are glued or pressed, never moving.** 0.2 mm a side is a usual clearance, not
  measured here; [`tools/fit_coupon.py`](plugin/tools/fit_coupon.py) writes the test print that
  measures it on your printer.
- **Decorative objects, not mechanical parts.** A bracket, or a box whose lid must close, belongs
  in a CAD tool (build123d, CadQuery, OpenSCAD).
- **No multi-material file.** A colour is painted, or printed as its own part.
- **Self-intersections are counted, not repaired**, and `flatten.py` does not fill holes.

The full list is in [`references/print.md`](plugin/references/print.md) § What it does not check.
The teapot photo is the Auckland War Memorial Museum's, CC BY 4.0, via Wikimedia Commons.

## Kiln Studio

<p align="center">
  <img src="docs/images/studio.webp" width="100%" alt="Kiln Studio: a lantern in the browser, a note pinned on its glass with the before and after views, Claude's reply, and the model list on the left" />
</p>
<!-- docs/images/studio.webp exists on the kiln-studio branch. [SCREENSHOT: optional second capture — the live view mid-build, phases shown above the model, or the Checks tab] -->

A local page for looking at what kiln made and telling it what to change.
`/kiln studio` starts it (or reuses the one running) on your project folder; every
`.glb .gltf .fbx .obj` under it shows up, and kiln's `_original` … `_final` stages are one
model you can switch between.

- **Look** — Lit, Unlit, Clay, Normals, UV checker, Faces (back faces red), wireframe, sizes in
  metres, bones, animation clips with a scrubber.
- **Annotate** — pin a note on a spot (it records the point in Blender coordinates, the object
  and material hit, the camera, a screenshot and a close-up) or write one about the whole model.
- **Iterate** — run `/kiln studio` in Claude Code: Claude reads the open notes, changes the
  model, re-exports and replies on each one. The page reloads the model as the file changes and
  renders the note's view again beside its screenshot: each note carries its before and after.
  One previous version is kept, so a pass can be undone; only you can mark a note resolved.
- **Watch it built** — once the brief is confirmed, the page opens the model kiln is building
  and reloads it after each phase.
- **See what kiln is on** — when a command works through several models, each gets a dot in
  the list: waiting, in progress, done.
- **Check** — the Checks tab reads the file in plain words, each with how to fix it: triangles
  against the detail tier, size and ground contact, texture sizes, compression on `_final`, the
  licences the log records, and the fidelity measure against the reference photo.

**No extra API key, no extra service.** Studio is a Python standard-library server bound to
`127.0.0.1`; it never calls a model itself. Claude acts on your notes inside your Claude Code
session when you run `/kiln studio`, on the same plan or API key as the rest of the session.
Notes live in the project's `.kiln-studio/`, ready to commit with the models.
[`references/studio.md`](plugin/references/studio.md) is the reference.

## Animate

<p align="center">
  <img src="docs/images/animate-character-walk.webp" width="32%" alt="A low-poly villager walking in place, looped" />
  <img src="docs/images/animate-character-jump.webp" width="32%" alt="The villager jumping in place, looped" />
  <img src="docs/images/animate-dragon-flap.webp"    width="32%" alt="A low-poly dragon flapping its wings, looped" />
</p>
<p align="center">
  <img src="docs/images/animate-cat-walk.webp" width="24%" alt="A low-poly cat walking, looped" />
  <img src="docs/images/animate-cat-idle.webp" width="24%" alt="The cat idling: breathing, glancing, tail swaying" />
  <img src="docs/images/animate-lamp.webp"     width="24%" alt="An articulated desk lamp looking around" />
  <img src="docs/images/animate-chest.webp"    width="24%" alt="A textured treasure chest: the hasp flips, the lid rattles, pops open on a heap of gold and slams shut" />
</p>

`/kiln animate` picks the route from the subject, because no single method held up across
all of them ([`references/animation.md`](plugin/references/animation.md) has every measurement):

| Subject | Route | Shown above |
|---|---|---|
| Biped or winged, from a sentence | [UniMate](https://github.com/Friedrich-M/UniMate) text-to-motion, looped by `tools/motion_loop.py` — **non-commercial weights** | the villager, the dragon |
| Four-legged, idle and walk | `tools/quadruped.py` — a scripted, measured cycle | the cat |
| Articulated object | rigid parts keyed by script, every rotation's sign measured first | the lamp, the chest |

UniMate was measured **unusable for quadruped walking** — on a cat, a Shiba, a horse and the
model author's own robot dog — so a quadruped never goes to it.

> **What this showcase is, and is not.** Each UniMate tile is the sample, out of 4, that
> `motion_loop.py` kept for looping best, then approved by a reviewer — some prompts tried
> (wave, dance, run) were left out. The scripted tiles are deterministic. These come from
> scripts (`examples/animation/showcase.sh`), not from an interactive session.

### Organic characters

[TO WRITE: the organic-characters work bundled in 3.0 — what it makes, how it was measured, its limits, one image. No source for it was found on origin/feat/print-check or origin/kiln-studio beyond the "eight web and animation sessions" fixes in the 2.3.0 changelog (one skin for a stylised character, a hand-built Mixamo-named quadruped skeleton).]

## Gallery

<p align="center">
  <img src="examples/gallery/renders/gallery.webp" alt="Fifteen reference assets across three themes: forge, sci-fi modular and stylised nature" width="100%" />
</p>

Fifteen props across three themes, modelled from scratch by script, cleaned, audited,
rendered and exported — headless, on one laptop, no cloud service, no paid API. They were
produced by the scripts in `examples/gallery/`, written to the skill's rules, **not** by an
interactive run of the skill: treat them as reference output and a conventions check
([`docs/gallery.md`](docs/gallery.md)).

## Running over Blender MCP

<img src="docs/images/mcp-panel.webp" alt="The BlenderMCP sidebar panel with all four integrations unchecked" width="215" align="right" />

The skill drives a live Blender. On ahujasid's addon, **all four integrations ship off**, and
while one is off the addon does not register its commands at all: a search answers
`Unknown command type: search_polyhaven_assets`, which reads like a version mismatch. kiln
checks `get_polyhaven_status`, `get_sketchfab_status`, `get_hunyuan3d_status` and
`get_hyper3d_status` first (rule 23). Tick the boxes in the BlenderMCP panel of the 3D
Viewport sidebar (<kbd>N</kbd>), then reconnect. On the official Lab MCP, which has no Poly
Haven tools, kiln reaches Poly Haven through its public API.

<br clear="all" />

## Commands

| Command | Action |
|---|---|
| `/kiln` | Full pipeline (CONFIG → EXPORT) |
| `/kiln batch` | Batch wizard → manifest → autonomous multi-asset production |
| `/kiln batch run` | Execute/resume a batch manifest (`--all`, `--asset <name>`) |
| `/kiln setup` | Environment detection + guided setup |
| `/kiln models` | List/switch the optional AI backends |
| `/kiln status` | Show current pipeline state |
| `/kiln search` | Search PolyHaven/Sketchfab |
| `/kiln inspect` | Inspect a 3D file (stats, poly count, materials, bbox); print mode: `print_check`'s verdict |
| `/kiln cleanup` | Clean up a mesh in Blender; print mode: `flatten.py`, then `print_check` |
| `/kiln texture` | Texture an untextured mesh |
| `/kiln animate` | Animate a rigged asset — routed by subject ([Animate](#animate)) |
| `/kiln optimize` | Optimize a GLB with gltf-transform/gltfpack |
| `/kiln convert` | Convert between formats (GLB↔USDZ↔FBX) |
| `/kiln studio` | Open Kiln Studio; act on the notes pinned there (`/kiln studio <asset>`) |
| `/kiln help` | List all commands and usage |

## Installation

### As a Claude Code plugin (recommended)

```
/plugin marketplace add elithril/blender-kiln
/plugin install blender-kiln@blender-kiln
```

Then run `/kiln setup` to detect your environment and install what's missing.

### As a standalone skill

```bash
git clone https://github.com/elithril/blender-kiln.git ~/.claude/skills/blender-kiln
```

Restart Claude Code, then run `/kiln setup`. The skill itself lives in `plugin/`; the
repository root links `SKILL.md`, `references` and `tools` to it. On Windows, enable symlinks
in git (`core.symlinks`) or install as a plugin.

## Skill structure

[TO RERUN AFTER MERGE: union of both branches' tables — print-check adds `references/print.md`,
`print_check.py`, `cutout.swift`, `flatten.py`, `fit_coupon.py`, `review_renders.py` and new line counts
for `reference-fidelity.md` / `fidelity_check.py`; kiln-studio adds `references/studio.md` and `plugin/studio/`.
The two branches disagree on the total (~5,500 vs ~5,300 lines) and on `fidelity_check.py`. Regenerate
from the merged tree; `verify_docs.py` fails past ±15 %.]

## Continuous checks

`plugin/tools/verify_docs.py` runs on every push and checks that this documentation is still
true: rule numbering and citations, line counts, referenced files, README images, the manifest,
the command forms. `plugin/tools/verify_blender.py` re-checks, weekly, what needed Blender to
establish. `plugin/tools/unimate.py drift` checks weekly that kiln's patch still applies to
UniMate's upstream. Seeded test suites: `test_verify_docs.py` **24/24**, `test_fidelity_check.py`
[TO RERUN AFTER MERGE: 34/34 on print-check, 29/29 on kiln-studio], `test_print_check.py` **67/67**,
`test_flatten.py` **22/22**, `test_fit_coupon.py` **18/18**, `test_review_renders.py` **10/10**,
`test_template_profile.py` **4/4**, `plugin/studio/test_studio.py` [TO RERUN: the changelog
says 44 tests] — figures as stated on each branch, not re-run for this draft.

## Iron rules

[KEEP the current section as is, after checking on the merged tree: print-check changes rules 7 and 16
and adds print rules 5–7 in `print.md`; the rule count (31) must be re-read.]

## Output

[KEEP the current section as is; add the print outputs: `{name}_{part}.stl`, `{name}_{part}_parts.blend`,
test pieces in `test/` as `test_{what}.stl`, `PRINT.md` for a colour figure — from print-check's CHANGELOG.]

## Contributing

Fixes are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). One rule shapes it:
**claims must be measured, not reasoned.**

## License

kiln is [MIT](LICENSE) © Nicolas Dolphens. The assets you make carry the licences of their
sources — see [What you can ship](#what-you-can-ship).
