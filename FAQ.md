# FAQ

The questions that come back most, from Reddit, X, Hacker News and people trying it.
Every answer links to where the README shows it. Something missing?
[Open a discussion](https://github.com/elithril/blender-kiln/discussions).

- [Is it free? What does a model cost?](#is-it-free-what-does-a-model-cost)
- [Where does the real size come from? Can I set a dimension?](#where-does-the-real-size-come-from-can-i-set-a-dimension)
- [From one photo, what about the side it doesn't show?](#from-one-photo-what-about-the-side-it-doesnt-show)
- [Does it do low poly?](#does-it-do-low-poly)
- [How is it different from Tripo, Meshy or other image-to-3D tools?](#how-is-it-different-from-tripo-meshy-or-other-image-to-3d-tools)
- [Why not just ask Claude with a Blender MCP server?](#why-not-just-ask-claude-with-a-blender-mcp-server)
- [Can I change one part afterwards and keep the rest?](#can-i-change-one-part-afterwards-and-keep-the-rest)
- [Is the topology clean enough for a game engine?](#is-the-topology-clean-enough-for-a-game-engine)
- [Can I 3D print what it makes?](#can-i-3d-print-what-it-makes)
- [What is Kiln Studio?](#what-is-kiln-studio)
- [What do I need? A GPU?](#what-do-i-need-a-gpu)
- [How long does a model take?](#how-long-does-a-model-take)
- [Can I use the models commercially?](#can-i-use-the-models-commercially)
- [Is this the same project as the other "Kiln"s?](#is-this-the-same-project-as-the-other-kilns)

---

### Is it free? What does a model cost?

The plugin is free and MIT licensed. What you pay for is Claude: kiln runs inside Claude Code,
with a Claude subscription (Pro, Max) or an API key.

On the bench, in API-equivalent usage: a rebuild from a photo costs **$4 to $7**, **$9 to $14**
with review rounds; a note addressed in Kiln Studio, **$0.69**. On a subscription, that comes out
of your plan's usage, not a bill. The default path uses no paid service: paid AI generation is
only ever proposed, never run without your yes.
→ [Measured, not claimed](README.md#measured-not-claimed)

### Where does the real size come from? Can I set a dimension?

From you, first. Say *"40 cm tall"* in the brief and everything follows that dimension. If you
don't, kiln asks — or takes the object's usual size and **writes it in the log as an
assumption**, never silently: a photo has no scale, and an unstated size drifts by tens of
percent. A ruler in the photo works too.

The result is an ordinary Blender model at real size, so rescaling it later is a scale, nothing more.
For printing, `print_check` tells you how far you can shrink it before thin walls are lost.

### From one photo, what about the side it doesn't show?

kiln rebuilds the object part by part, by script — it does not guess pixels. What the photo
doesn't show is **kept plain and closed, and listed in the log as unseen**: no invented opening,
part or ornament on a side nobody photographed. For anything whose back or underside will be
seen — a hero asset, a character — it asks for a side and a top view, and measures each one you
give.
→ [From a photo](README.md#from-a-photo--rebuilt-in-blender-measured-against-the-real-object)

### Does it do low poly?

Yes — ask for it (`/kiln a low-poly wooden chair`). The animated cat, dragon and villager in the
README are low poly. Poly counts are checked against a budget; a decimation is proposed with
before/after previews, never applied without you. `/kiln optimize` does compression,
simplification and LODs.
→ [Animate](README.md#animate-and-characters-that-bend) ·
[A GLB from a generator](README.md#a-glb-from-a-generator--repaired-lightened-converted)

### How is it different from Tripo, Meshy or other image-to-3D tools?

Different job. A generator gives you a mesh in seconds. kiln writes the model in Blender by
script: clean, named parts, real size, textures from CC0 scans, an editable `.blend` — and it
measures the result against your photo before shipping it.

They work together, too: kiln can start from a free TRELLIS.2 or TripoSR mesh, or from a GLB you
generated elsewhere, and repair, lighten and convert it (191,520 → 9,000 triangles on the bench).

Rule of thumb: a mesh as-is, fast → a generator. An asset you will edit, animate, print or ship
→ kiln.

### Why not just ask Claude with a Blender MCP server?

You can, and kiln runs on exactly that. The MCP server gives Claude hands in Blender; kiln gives
it the method, and the checks you would otherwise do by hand, prompt after prompt: real size,
cleanup, textures from CC0 scans, poly budget, compression, a validated export — and a score
against your photo before it calls the model done. And kiln itself is measured: every release
runs a bench against the previous one, on both MCP servers.
→ [Measured, not claimed](README.md#measured-not-claimed)

### Can I change one part afterwards and keep the rest?

Yes, that is what Kiln Studio is for. Pin a note on the part — *"make the armrests wider"* — and
Claude changes that, re-exports and replies with a before/after. On the bench, a note asking for a
ring twice as big came back ×1.9, **nothing else moved**, in 1.4 minutes. The model is also a
normal `.blend` with named parts, so you can make the change yourself.
→ [Kiln Studio](README.md#kiln-studio--look-at-your-models-pin-a-note-let-claude-fix-it)

### Is the topology clean enough for a game engine?

A scripted model is built from clean, named parts, not a dense scan-like mesh. The rule kiln
follows: quads for anything that deforms, triangles accepted on a static prop (engines
triangulate anyway), no n-gons, no doubled or degenerate faces. Characters are retopologised
(QuadriFlow) and their weights checked on fixed poses, so skin no longer passes through skin
when they bend. A mesh from an AI generator is the dense case: kiln repairs and decimates it,
with before/after. With `gltf-transform` installed, every GLB export goes through the Khronos
glTF validator.
→ [Animate](README.md#animate-and-characters-that-bend) ·
[A GLB from a generator](README.md#a-glb-from-a-generator--repaired-lightened-converted)

### Can I 3D print what it makes?

Yes, that is a mode of its own: STL or 3MF in millimetres, split into parts that print flat, and
every file checked by `print_check` (walls, overhangs, open edges, PrusaSlicer as a second
opinion). Four models were printed exactly as exported on a Bambu Lab P1S. It is for decorative
objects and figurines: mechanical parts belong in a CAD tool.
→ [3D printing](README.md#3d-printing--models-that-actually-print) · [Limits](README.md#limits)

### What is Kiln Studio?

New in 3.0: a local page with every model in your project (`/kiln studio`). Turn it, look at it
in clay, normals or wireframe, compare with the previous version — then **pin a note on a spot**
(*"the ring is too small"*) and Claude makes the change, re-exports and replies on the note, with
a before/after. It also exports for games and AR in seconds, and shows the model in AR on an
iPhone through a QR code.
→ [Kiln Studio](README.md#kiln-studio--look-at-your-models-pin-a-note-let-claude-fix-it)

### What do I need? A GPU?

No GPU. Claude Code, Blender 4.4 or newer, one of the two Blender MCP servers (ahujasid's or the
official Blender Lab one), and Python 3. `gltf-transform` is strongly recommended for web
compression. Everything else (local AI models, auto-rig, text-to-motion) is optional.
→ [Requirements](README.md#requirements) · [Installation](README.md#installation)

### How long does a model take?

On the bench: about **3.5 minutes** for a prop from a sentence, **15 to 23 minutes** for a rebuild
from a photo, **1.4 minutes** for a Studio note. An interactive session adds the time you take to
answer its questions.
→ [How long it takes](README.md#how-long-it-takes)

### Can I use the models commercially?

It depends on where the asset's parts came from, and kiln tells you: each source and its licence
go into the model's log, and Kiln Studio's Checks tab reads them back ("credit the author", "not
for commercial use"). Poly Haven textures are CC0. Sketchfab models carry their own licence, and
kiln never downloads a non-commercial one for a commercial project without asking. kiln's own
code is MIT.
→ [What you can ship](README.md#what-you-can-ship)

### Does it work in the Claude desktop app?

Yes — in the **Code** tab, with the same install (`/plugin marketplace add elithril/blender-kiln`,
then `/plugin install blender-kiln@blender-kiln`) and the same `/kiln` commands.

- **Blender connector.** The desktop app's built-in Blender connector is the official Blender Lab
  MCP, registered as `Blender`, so its tools are `mcp__Blender__*`. `SKILL.md` allows both that and
  ahujasid's `mcp__blender__*`; there is nothing to register. kiln maps the Lab tools itself
  (`plugin/references/blender-mcp.md`, "On the official Blender Lab MCP"): no marketplace search
  or generation there, so it sources through PolyHaven's public API and scripted modelling. The
  add-on needs Blender 5.1+ with its server started and online access on.
- **`/kiln setup`.** Its shell-side check cannot see a connector, so it can report "no Blender MCP
  server configured". A connected connector answers `get_objects_summary`; that is the check.
- **Kiln Studio.** "Ask Claude from Studio" runs `claude -p`. An app-launched process often has a
  minimal `PATH`, so Studio also looks in `~/.local/bin`, `~/.claude/local`, `/opt/homebrew/bin` and
  `/usr/local/bin`; set `KILN_STUDIO_CLAUDE` to point at another install.

### Is this the same project as the other "Kiln"s?

No. Kiln is a common name: there is a 3D-printer MCP server, a Godot material baker, and other
sites using the name. **blender-kiln** lives here, at
[github.com/elithril/blender-kiln](https://github.com/elithril/blender-kiln), with its site at
[elithril.github.io/blender-kiln](https://elithril.github.io/blender-kiln/). Nothing else is
affiliated with it.
