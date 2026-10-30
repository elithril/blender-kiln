# Review rounds — every asset, before OPTIMIZE

> Read before the first review of any asset you build or finish. Rule numbers are SKILL.md's Iron Rules.

## Contents
- Why rounds, and how many
- Before building: the intent
- One round
- The fresh reviewer
- What to look for — every asset
- What to look for — a character
- From a photo: the shape stays, the surface goes on
- The log

## Why rounds, and how many

A session that looks once, judges it "fine" and ships, ships what the user calls ugly. Measured on the
3.0 bench's chibi child: built with the rules alone, two looks, shipped; the user: "pas très quali".
kiln's mascot, built from a richer brief over **six rounds** on the model and three more on its
motion, with a written critique each time: "pas mal en vrai". The rounds were the difference — what
each one found is in `characters.md` § A stylised humanoid.

| The asset | Rounds, at least | Stop |
|---|---:|---|
| A prop, an object, a scene piece | **1**, eight at most | two fresh reviewers in a row find nothing blocking (§ The fresh reviewer) |
| A character, a mascot, a creature — or any brief that says showcase, hero, vitrine, high quality | **6**, twelve at most | the same, every line of the design sheet shows — then rounds on the motion (below) |
| From a photo | the proportions: **2** correction rounds at most (`reference-fidelity.md` § 5); then rounds on the surface, the finish **and the assembly** | the same |
| Print | `print.md`'s own rounds | `print_check` PASS and the gaps stop closing |

**Auto mode does not shorten them**: nobody is there to say it looks wrong, so the rounds are the
only eye. A round that finds a blocking defect is followed by another. A prop stops at eight, a
character at twelve: at the cap, ship and list in the hand-over what is still wrong. The mascot's
quality is the bar, and it took six rounds on the model and three on the motion. A defect that
comes back after two fixes is the method's, not the dose's: rebuild that part another way (the
mascot's lids, re-weighted twice, were replaced by a squash blink).

## Before building: the intent

Write it in the log before the first primitive — a session that has not decided what the object
looks like builds the first thing that works (the bench chibi: a plain orange T-shirt and blue
shorts, one material, nothing in its hands):

- **Palette**: 3 to 5 colours, each with a role (main, secondary, accent, metal, light) — from the
  brief, the reference or the brand when there is one; one accent, not five.
- **Materials**: one per physical material, **three at least on an object of several parts** (wood,
  iron, leather, glass…), each with its own roughness; values-only is fine for a stylised asset.
- **Finishes**: three at least — bevels on every visible edge, wear where hands go, a detail at each
  end (rivets, caps, stitching, a cuff, a buckle). They are what reads as quality.
- **A character**: the design sheet of `characters.md` § A stylised humanoid — role, signature
  silhouette, costume layers, a prop.

## One round

1. Render the sheets: `blender -b --factory-startup --python-exit-code 1 --python tools/review_sheet.py
   -- MODEL --out review/round{n}.png` — front, both three-quarters, side, back and a close-up of the
   top (a character's head), under a studio light, a rigged model in its rest pose, framed on its
   vertices. Two sheets: `round{n}.png` in colour, for how it looks, and `round{n}_clay.png`, every
   material replaced by light clay, for how it is built. From a photo, judge colour, glass and wear
   on `side_by_side.png` against the photo (`reference-fidelity.md` § 5), not on the sheet's studio light.
2. **Look at both** (Read the PNGs), every tile, as the person who will use the asset. The clay sheet
   first: paint hides a part out of place — a dark olive ammo box went through eight rounds with its
   latch plate off-centre, seen on the side tile only once the paint was gone (3.0 bench, 2026-10-28).
3. **Have it read by a fresh reviewer** (below), then **write the critique in the log before changing
   anything**: the reviewer's defects and yours, numbered, each with where, in which tile, and the
   fix — or "nothing found", with what was checked. "Looks good" is not a round.
4. Fix them — **all the round lists**, when they touch different parts or regions; two changes to the
   same material region go one per round (`reference-fidelity.md` § 5: together, they regressed the
   surface while each read "applied"). Rebuild, export, and start the next round.

## The fresh reviewer

The session that builds a model reads its sheets as its author: it sees what it meant to make. On
the 3.0 bench, with these rounds, it wrote "nothing found" over a chair whose rosette had black
holes, a mascot whose hair flame read as three horns — the very defect `characters.md` names — and
its locks as strips with the scalp between them, and skin-coloured patches on the shoulders its own
log later called "visible since round 1". Each round is therefore read by **a new subagent that knows
nothing of the build** — the Task (Agent) tool, a general-purpose agent, a fresh one every round:

- **Give it only**: the brief as the user wrote it, the reference photo if there is one, the paths of
  this round's sheets (`round{n}.png`, `round{n}_clay.png`, the close-ups) — and from a photo
  `side_by_side.png` — and the lists of this file (every asset; a character's). **Not** the log, the
  scripts, the intent you wrote, or what the last round fixed: it judges what is on the image.
- **Ask it for**: every defect it sees, each with the tile, where, and **blocking** (a person using
  the asset would notice it in the views it will be seen in) or **detail**; and its verdict in one
  line — would this be shown to the user as is?
- **Use it**: every blocking defect is fixed this round or argued in the log with what was checked
  (the reviewer can be wrong — a shadow read as a hole); details are fixed when cheap.
- **Stop on two clean readings**: when a reviewer finds nothing blocking, and your own reading
  neither, give the same sheets to a second new subagent, briefed the same way. If it finds nothing
  blocking either, the rounds end — a prop as early as round 1, a character once its six are done;
  if it finds something, that round goes on with its fixes. One reviewer can miss what the next one
  sees, and the second reading costs a review, not a rebuild. A prop has no minimum: the rounds were
  a count because the builder judged itself; two outside readings are the judgement now.
- **The motion too**: for a motion round, give it strips of frames (front and side, every 2nd frame
  of the loop, `characters.md` § Matcap before delivery) and the measures, and ask the same.

A prompt that works:

```
You review a 3D asset as its future user would, from images only. The brief: "<brief>".
Images: <paths>. Check, tile by tile: <the lists>. Report every defect: tile, where, blocking or
detail, and one line: would you show this to the user as is? Do not guess at intentions; judge
what you see.
```

## What to look for — every asset

- **Silhouette**: readable in one glance from the front and the three-quarter; one signature shape.
- **Proportions**: against the brief's or the real size; parts a hand uses sized for a hand.
- **Materials**: as many as the intent says; no part left in a default grey; no colour that is
  only a stand-in.
- **Edges**: no razor-sharp CG edge where a real object is worn or bevelled.
- **Finishes**: each one the intent lists, visible in the close-up.
- **Colour**: the palette holds — no stray saturated colour, the accent used once or twice.
- **Nothing floats, nothing pokes through**: parts enter one another; straps follow surfaces.
- **Assembly** (the clay sheet): on a symmetric object, what sits on its axis is centred on it — a
  latch, a handle, a badge; parts the real object lines up are lined up — brackets under the plate
  they hold, rivets along their strip; nothing sticks past the outline that the brief or the
  reference does not show. Check it on the side and back tiles, square-on.
- **The back and the underside**: not left plain or open because the front was the brief.

## What to look for — a character

All of the above, plus `characters.md` § A stylised humanoid § Review rounds: hair (no helmet, horns,
straw, bald nape, stair-stepped edge at the temples), face (eyes, brows, smile, nose), hands (a thumb),
accessories big enough to read, the design sheet's every line. Then the matcap at rest and mid-walk
(`characters.md` § Matcap before delivery).

**Then rounds on the motion**, once rigged and animated, the same way — render the clips (a GIF or a
strip of frames from the front and the side), look, write the defects, fix, again until a round finds
nothing: lids or parts that fly off the head, hips that roll, a head that bobs, feet that slide, knees
that snap straight for a frame, a hand through the body, a prop that leaves the hand. Measure what can
be measured (`tools/motion_measure.py`, `animation.md`: `knee_pops` at 0). The mascot: lids that "flew", hips that rolled, then a head that moved once the hips
were calmed — three rounds, each seen on the clip, none in the numbers alone.

## From a photo: the proportions stay, the assembly is always fixed

`reference-fidelity.md` § 5 stops **reshaping to the photo** at two correction rounds: pushed
further, a lantern's posts were narrowed to fit the photo's perspective and moved away from the real
object (0.900 → 0.849). What it stops is changing a part's size or proportion to raise the score.

It does not freeze the geometry. A part off-centre, out of line with its neighbour, or sticking out
is a build error, not a proportion: fix it at any round, the clay sheet shows it. The ammo box that
read the cap as "no more geometry" spent its six later rounds on paint and rust and shipped its
latch plate off-centre (3.0 bench, 2026-10-28).

So the rounds after the two go on **surface, finish and assembly** — materials against the photo's
crops, wear, bevels, the details of the inventory, every part where it belongs — and measure the
shape again at the end: a drop of more than 0.01 is undone.

## The log

```
- Review round 2 (review/round2.png):
  1. side tile: the strap stops short of the buckle, a 4 mm gap → extend the strap 6 mm into it
  2. close-up: the lid's edge is razor-sharp → bevel 1.5 mm, 2 segments
  3. back tile: plain, no seam → add the hinge pins and a weld line
  fixed, re-exported; round 3 next
```
