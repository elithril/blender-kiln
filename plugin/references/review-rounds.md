# Review rounds — every asset, before OPTIMIZE

> Read before the first review of any asset you build or finish. Rule numbers are SKILL.md's Iron Rules.

## Contents
- Why rounds, and how many
- Before building: the intent
- One round
- What to look for — every asset
- What to look for — a character
- From a photo: the shape stays, the surface goes on
- The log

## Why rounds, and how many

A session that looks once, judges it "fine" and ships, ships what the user calls ugly. Measured on the
3.0 bench's chibi child: built with the rules alone, two looks, shipped; the user: "pas très quali".
kiln's mascot, built from a richer brief over **five rounds** before the user's validation and one
after, with a written critique each time: "pas mal en vrai". The rounds were the difference — what
each one found is in `characters.md` § A stylised humanoid.

| The asset | Rounds, at least | Stop |
|---|---:|---|
| A prop, an object, a scene piece | **3** | a round finds nothing from the lists below |
| A character, a mascot, a creature — or any brief that says showcase, hero, vitrine, high quality | **5** | the same, and every line of the design sheet shows |
| From a photo | the shape: **2** correction rounds at most (`reference-fidelity.md` § 5); then **3** rounds on the surface and the finish | the same |
| Print | `print.md`'s own rounds | `print_check` PASS and the gaps stop closing |

**Auto mode does not shorten them**: nobody is there to say it looks wrong, so the rounds are the
only eye. A round that finds a defect is followed by another. Eight at most: at the cap, ship and
list in the hand-over what is still wrong.

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

1. Render the sheet: `blender -b --factory-startup --python-exit-code 1 --python tools/review_sheet.py
   -- MODEL --out review/round{n}.png` — front, both three-quarters, side, back and a close-up of the
   top (a character's head), under a studio light, a rigged model in its rest pose, framed on its
   vertices. `tools/review_renders.py` (matcap) is for the geometry; this one is for how it looks.
2. **Look at it** (Read the PNG), every tile, as the person who will use the asset.
3. **Write the critique in the log before changing anything**: at least three numbered defects, each
   with where, in which tile, and the fix — or "nothing found", with what was checked. "Looks good" is
   not a round.
4. Fix them, rebuild, export, and start the next round.

## What to look for — every asset

- **Silhouette**: readable in one glance from the front and the three-quarter; one signature shape.
- **Proportions**: against the brief's or the real size; parts a hand uses sized for a hand.
- **Materials**: as many as the intent says; no part left in a default grey; no colour that is
  only a stand-in.
- **Edges**: no razor-sharp CG edge where a real object is worn or bevelled.
- **Finishes**: each one the intent lists, visible in the close-up.
- **Colour**: the palette holds — no stray saturated colour, the accent used once or twice.
- **Nothing floats, nothing pokes through**: parts enter one another; straps follow surfaces.
- **The back and the underside**: not left plain or open because the front was the brief.

## What to look for — a character

All of the above, plus `characters.md` § A stylised humanoid § Review rounds: hair (no helmet, horns,
straw, bald nape, stair-stepped edge at the temples), face (eyes, brows, smile, nose), hands (a thumb),
accessories big enough to read, the design sheet's every line. Then the matcap at rest and mid-walk
(`characters.md` § Matcap before delivery).

## From a photo: the shape stays, the surface goes on

`reference-fidelity.md` § 5 stops the shape at two correction rounds: pushed further, a lantern's
posts were narrowed to fit the photo's perspective and moved away from the real object (0.900 →
0.849). The rounds after them change **surface and finish only** — materials against the photo's
crops, wear, bevels, the details of the inventory — and measure the shape again at the end: a drop
of more than 0.01 is undone.

## The log

```
- Review round 2 (review/round2.png):
  1. side tile: the strap stops short of the buckle, a 4 mm gap → extend the strap 6 mm into it
  2. close-up: the lid's edge is razor-sharp → bevel 1.5 mm, 2 segments
  3. back tile: plain, no seam → add the hinge pins and a weld line
  fixed, re-exported; round 3 next
```
