# Animation Reference (Phase 5d)

> Getting motion onto a rigged asset: which route fits which subject, the tools kiln
> ships for each, and the rules every scripted animation here was corrected into.

**Phase 5d is optional and runs after [5c] RIG.** Its input is a rig built to
`references/characters.md` § Animation-ready skeleton. A leg made of one bone cannot
fold a knee, whatever drives it: on such a rig, both generators measured here gave
unusable motion (MoCapAnything V2, and UniMate's earlier v2 checkpoint).

## Contents
- Pick the route from the subject
- Rules for scripted animation
- Quadrupeds — `tools/quadruped.py`
- Humanoid presets — `tools/presets.py`
- UniMate
  - Install and keep it current
  - Run it
  - Prompting — measured on a four-legged test rig
  - Speed — measured, M4 Pro, one 2 s clip

## Pick the route from the subject

| Subject | Route | Measured |
|---|---|---|
| Ships its own clips (Quaternius, Poly Pizza "animated") | **Keep them** — export as they are (PHASE 7) | Hand-made clips beat every generator tried here. |
| **Four-legged** — idle, walk | **`tools/quadruped.py`** — scripted cycle, below | Approved cycle: legs ≤ 93% of their length, paws in step, exact loop. |
| **Four-legged** — run, jump, sit, attack… | Its own clips, or keyframe by hand | **Not UniMate**: its walk was unusable on 4 quadrupeds, the model author's own example included. Scripted versions of these were tried too and rejected on review. |
| **Humanoid** with kiln's names (rigged by `tools/autorig.py`), a move in `presets.py list` | **`tools/presets.py`**, below | Preferred to UniMate on review for walk and run; feet slide 1-10 mm/s against UniMate's 120-960, loops at 0.7-1.2× a step. Commercial use allowed. |
| **Biped or winged** creature, a sentence — a move not in the presets, a non-human biped, wings | **UniMate** with `--loop`, below | A reviewer approved a human's walk and a dragon's wing flap, each looped from 4 samples. **Non-commercial weights (CC BY-NC 4.0)**: say so. More expressive than the presets on a dance, by eye. |
| Humanoid, standard moves, a library | **Mixamo** library, retargeted | ~2,500 clips, free with an Adobe account. `references/characters.md` § Animation Retargeting. |
| **Articulated object** — lamp, chest, door, turret | **Keyframe the parts**, below | A desk lamp and a chest were approved first time, built with these rules. |
| A video of the motion | Not supported | MoCapAnything V2 (MIT): excellent on rigs from its own training set, unusable on two from outside it (limbs swung loose, tail stretched ~3×); on CPU ~15 min to prepare a rig, ~10 min per video. |

`tools/unimate.py animate` checks the posture itself: a rig whose forelimbs end in the
lower half, level with its hind limbs, is refused (`--force` overrides) with a pointer
to `tools/quadruped.py`. Right on 6 rigs: 3 quadrupeds, a human, a dragon, a lamp.

## Rules for scripted animation

Each comes from a cycle that looked wrong until it was measured:

1. **Drive a bone in its own rest frame.** Never assume a bone's local Y is "up": a
   cat's `Hips` lies along the body, so a vertical bob written as local Y moved the hips
   1.8 cm forward and back and 1 mm up. Convert world offsets:
   `(arm.matrix_world.to_3x3() @ bone.matrix_local.to_3x3()).inverted() @ world_offset`.
2. **Solve the IK pole angle from the rest pose; never guess it.** With the target at
   rest, search the angle that leaves the chain at its rest rotation. A guessed −90°
   turned a cat's elbows forward; the solved value was +90°.
3. **Keep legs bent.** Size the stride and the hip height so no leg passes ~95% of its
   length. The rejected first walk peaked at 101% — legs locked, read as too long; the
   approved one at 93%, with the hips 15% of a leg lower and a stride of 11% of the body.
   **Lower the hips no further than the legs need**: on a short-legged mascot cat, 15% read
   as a cat stalking its prey. `quadruped.py` now starts at 5% and lowers the hips only
   until the legs hold — the cat settled at 8% (legs 95%), as its own session had found.
4. **Measure a rotation's sign before using it.** Rotate +0.2 rad and watch which way a
   probe moves. A sit and an attack written with the assumed sign tipped the cat nose
   down. The lamp and chest scripts measure every sign first — and were right first time.
5. **Loop exactly.** A cycle of P frames has P distinct poses, 0..P−1, and **a closing key
   at P equal to key 0**: a glTF clip lasts until its last key and three.js wraps there, so
   keyed 0..P−1 only, the step from the last pose back to the first is skipped — measured
   on `quadruped.py`'s walk, 32 keys ending at 31/24 s, the seam jumping 0.045 at once. Key
   P is for the file; Blender's own playback range stops at P−1, or it shows the pose twice.
6. **Judge motion in motion, and with numbers.** A contact sheet showed a jump as a body
   lying flat; the hip height said it rose 0.32 → 0.61 m. Measure leg extension, foot
   height and seams; then watch the loop.
7. **Hold paws level.** A copy-rotation to the rest orientation keeps paws flat through
   the stride.

For **objects**: weight each rigid part 100% to one bone (no blending — a lid is a
solid), measure the hinge's opening sign (rule 4), and use the classic beats —
anticipation (the lid jiggles), overshoot (it pops open past its rest angle), a bounce
when it slams shut. Bone-parented parts (eyes, props in a hand) are folded into the skin
by `tools/bind_rigid_parts.py` before any skin-only pipeline sees them.

## Quadrupeds — `tools/quadruped.py`

```bash
blender --background --factory-startup --python-exit-code 1 --python plugin/tools/quadruped.py -- \
    --asset SK_Cat_rigged.glb --out ./anim --motions idle,walk
```

Lateral-sequence walk (one paw every quarter cycle, 60% on the ground) and a breathing,
glancing idle, both baked to plain FK keys. Before writing a clip it measures it, and
shortens the stride or lowers the hips until the legs stay bent (≤ 95%). It reports the
**root speed** the planted paws share — what a game must move the character at for the
feet not to skate (0.106 m/s on the cat, the four paws in exact step). It needs the
Animation-ready skeleton's names; it says which are missing.

**Secondary motion comes with the bones that carry it** — no session got it unasked, and
the cat's wrote its own module: the head nods twice per stride, `LeftEar` / `RightEar`
trail it (they take where the head was 3 frames before, ×2, so they lag and overshoot), the
`Tail1…n` segments wave each 0.55 rad later than the one before, and the eyelids blink once
in the walk and three times in the idle, a double among them. The blink needs the lid
bone's closing axis and angle, **measured on the model** (rule 4): `--blink X:140` closed the
cat's lids (centred on the eye's axis: −0.39 open → +0.54; −140 reached only +0.08).
Without it the tool says so and writes no blink. The report gives what it measured on the
baked pose: on the cat the ears trail the head by 4 frames in the walk, 3 in the idle (0
before), the tail's tip its root by 10 frames in the idle (0 before), 1 and 3 blinks.

It writes **one GLB with every motion as a named clip**, `{asset}_animated.glb` — a site
plays Walk and Idle from one file (`--per-clip` also writes `{motion}.glb` each, as it once
did only). The clips are the motions' names (`idle`, `walk`): rename the actions if the
brief names them otherwise.

## Humanoid presets — `tools/presets.py`

```bash
python3 plugin/tools/presets.py list                     # 22 motions, 43 clips, cycle or one-shot
python3 plugin/tools/presets.py animate --asset SK_Child_rigged.glb --motion walk,run,jump,dance --loop
```

Ready-made clips for a humanoid: image-to-3dlab's (AssetFurnace) Animate presets, generated
once with NVIDIA Kimodo (Kimodo-SOMA-RP-v1.1) — 21 motions in two takes (`--take A|B`) and a
woman's walk, 2.1 MB in `tools/motions/`. The rig needs kiln's names (`references/characters.md`
§ Animation-ready skeleton), as `tools/autorig.py` writes them; bones are found by name. Writes
`{asset}_animated.glb`, **one clip per motion, named as asked**, a `.measures.json`
(`tools/motion_measure.py` on every clip of the file written) and a `.provenance.json` (preset,
take, prompt, file hash, licences). `--speed 1.25` plays faster; `--no-fix feet,arms` gives the
upstream behaviour back, for comparison.

**Licences.** The clips: *Licensed by NVIDIA Corporation under the NVIDIA Open Model License*;
NVIDIA claims no ownership of the outputs; commercial use allowed. The data and the retarget
(`tools/retarget.py`, adapted): image-to-3dlab, Apache-2.0. Both are in `plugin/NOTICE`.

**What kiln adds to upstream's retarget**, each measured before → after on the two humanoids of
§ Learned auto-rig (`references/characters.md`): the kiln child (SkinTokens) and the Hunyuan3D-2
humanoid whose right hand is fused to its hip:

1. **Bones by name**, not by the tree's shape: the Hunyuan rig's right arm stops at the forearm,
   and the shape search had given the upper arm the forearm's turn — arm through body 4,285 →
   1,548 mm² on the walk, 13,638 → 1,679 on the dance. The child: identical to upstream.
2. **Feet planted**: while the actor stands on a foot (its SOMA ankle or toe low and slow — the
   rig's own heights pick the wrong frames on the chibi child), the foot's lowest skin points
   stay where they were the frame before, the lowest on the floor; a two-bone solve moves thigh
   and shin; the hips drop where a leg cannot reach (21 mm at most). In the air the foot clears
   the floor by 0.8 × the foot-skate scale. A knee the actor holds near straight (under 5°)
   bends toward the thigh's front, eased to the actor's own plane by 25°: read off the pose
   alone, that plane is noise, and the child's walk bent its knee backward 17-35° around heel
   strike, flipping 130-155° from one frame to the next.
3. **Arms out of the hips and belly**: the hips join upstream's capsules (torso, neck, head), a
   point at 80% of the upper arm is kept out too, capsules at the 95th percentile of their
   skin, and the swing it adds is **capped at 25°** — uncapped, the child's arms went out
   61-78° (median), back to its A-pose. Thighs stay out (upstream: arms held out like wings).
4. **`--loop`** (idle, walk, walk_woman, run, sneak, fight_stance) adds a second clip,
   **`{motion}_loop`**, beside the whole take (`run`: its start and its stop, travelling, as
   Kimodo made it): the window whose end matches its start, the mismatch spread over it, frame P
   keyed equal to frame 0 (rule 5 of § Rules for scripted animation), the hips' travel taken
   out; the root speed to move the character at is recorded. One-shots are kept whole, not
   looped.

**Measured** with `tools/motion_measure.py`, the same measure on every route (method in its
docstring): standing-foot slide (mm/s), deepest skin under the floor (mm), arm through body
(mm² per frame, rest crossings subtracted), loop seam (× the mean frame step; walk and run:
the `_loop` clips, jump and dance are one-shots, their seam is the take's own end). Targets: < 50 mm/s,
< 5 mm, < 500 mm², ≤ 1.2×. UniMate: the comparison study's samples (`--loop` for walk and run).

| Character | Move | UniMate | Upstream presets | **`presets.py`** |
|---|---|---|---|---|
| Child | walk | 149 · 0.0 · 0 · 1.62 | 293 · 22.9 · 2,638 · 6.22 | **2.7 · 0.0 · 377 · 0.69** |
| Child | run | 120 · 6.5 · 1,482 · 0.51 | 372 · 5.8 · 1,305 · 6.47 | **0.8 · 0.0 · 159 · 1.05** |
| Child | jump | 48 · 0.0 · 545 · — | 47 · 4.0 · 4,539 · — | **0.7 · 0.0 · 74 · —** |
| Child | dance | 102 · 6.7 · 564 · — | 103 · 0.5 · 1,162 · — | **1.0 · 0.0 · 84 · —** |
| Hunyuan | walk | 962 · 54.6 · 1 · 0.97 | 568 · 38.2 · 4,285 · 6.42 | **10.6 · 0.5 · 858 · 1.20** |
| Hunyuan | run | 277 · 46.2 · 236 · 1.73 | 353 · 34.7 · 9,690 · 5.92 | **5.4 · 0.0 · 481 · 1.20** |
| Hunyuan | jump | 63 · 36.9 · 327 · — | 15 · 13.5 · 6,715 · — | **3.5 · 0.2 · 2,029 · —** |
| Hunyuan | dance | 35 · 11.7 · 617 · — | 34 · 14.0 · 13,638 · — | **8.4 · 0.2 · 973 · —** |

Each cell: slide · under the floor · arm through body · seam. A reviewer, shown UniMate and the
upstream presets side by side, preferred the presets for walk and run, and found UniMate more
expressive on the dance; `presets.py`'s fixes were not yet in that review.

**Limits — what this does not show:**

- **The Hunyuan humanoid misses the arm target** on walk (837), jump (2,033) and dance (970):
  its right arm has no hand bone, so it is not cleared and crosses the hips 170-430 mm², and its
  upper arm folds into its own shoulder's skin at the joint (160-730 mm²), which no swing of the
  arm removes. UniMate keeps the arms out by re-resting the character in a T-pose and holding
  them away from the body — at the cost of the feet (54.6 mm under the floor).
- Two humanoids, four moves measured against the targets. Outside them: the idle loops at
  1.12× (child) and 1.79× (Hunyuan), fight_stance at 1.47× (child), and fight_stance's guard
  holds the fists in the chest (524 / 13,279 mm²) — small or close motions, looked at less.
- The measure reads the skin; whether a 25°-capped swing still "reads" as the move is judged
  by eye, on the comparison videos, not measured.
- Kimodo's clips are what they are: a walk is a walk forward, no style or speed beyond `--speed`.

## UniMate

[UniMate](https://github.com/Friedrich-M/UniMate) (SIGGRAPH Asia 2026) generates a
motion for any rigged skeleton from a sentence, without retraining per skeleton. It
reads the skeleton's topology and the *names* of its joints, so the
Animation-ready skeleton's naming is not cosmetic.

**Licence.** Code MIT; the released checkpoints are **CC BY-NC 4.0 — non-commercial
use only**. Treat motions generated with them as covered by it too. Say so to the user
before running it for anything that may ship commercially.

**Platform.** Upstream supports NVIDIA GPUs only. kiln's `tools/unimate.patch` (73
lines) makes it run on Apple Silicon (MPS) and on CPU, and on Blender 5's layered
actions. Measured on an M4 Pro.

### Install and keep it current

UniMate is a research project that changes weekly, so `tools/unimate.py` pins the
version kiln measured and reports when upstream has moved:

```bash
python3 plugin/tools/unimate.py status          # installed vs tested vs upstream; exit 10 = newer upstream
python3 plugin/tools/unimate.py setup           # installs the tested commit + checkpoint
python3 plugin/tools/unimate.py setup --update  # upstream HEAD + newest weights, if kiln's patch still applies
```

- **Ask before `setup`**: it takes **3.2 GB** on disk (code, a Python 3.10
  environment with torch, the 1.1 GB checkpoint). Measured at 77 s with package
  caches already warm — expect several minutes the first time. Everything goes to `~/.cache/blender-kiln/unimate`
  (`KILN_UNIMATE_HOME` to move it).
- **Run `status` before each animation session.** Exit 10 means a newer upstream
  exists. `--update` refuses an upstream the patch no longer applies to and stays on
  the tested version; when it does move, the result is untested by kiln — re-check
  a few prompts before relying on it.
- `drift` checks, without installing anything, whether kiln's patch still applies to
  upstream HEAD; kiln's CI runs it weekly.
- No API key, no LLM: joint labels come from UniMate's offline rules.

### Run it

```bash
python3 plugin/tools/unimate.py animate --asset SK_Dragon_rigged.glb --loop \
    --prompt "An object flaps its wings." "An object walks in place." --reps 4 --out ./anim
```

1. **The run stops once for review** and prints the path of `REVIEW.md`. Read the
   joint labels in `annotation.json`, fix what is wrong, then rerun with
   `--annotation <that file>`. For a four-legged animal, set the hind leg to
   *Thigh / Shin / Fetlock / Foot* (`…Foot` → *Fetlock*, `…ToeBase` → *Foot*): that is
   how the training data labels it.
2. **Output:** one animated GLB per prompt × repetition, 2 s long (generated as 60
   frames at 30 fps; the GLB carries them as 48 at 24 fps). Longer moves chain prompts (UniMate's "motion expansion"; not measured by
   kiln).
3. **`--loop` keeps one looped clip per prompt** (`<prompt>.loop.glb`), cut by
   `tools/motion_loop.py` from the sample that loops best: the window whose end matches
   its start in pose and direction, cross-faded, root drift removed. Raw clips seam at
   2.1-9.7x the local frame step; looped, 0.5-1.2x (12 clips). All samples stay in
   `samples/`. The file carries **one clip, `Loop`**, with a closing key equal to its first
   (rule 5 of § Rules for scripted animation), and the root's drift and height are worked in
   world axes (that section's rule 1): on the Hunyuan3D humanoid, whose `Hips` bone leans
   12.5°, the bone-local version raised the looped hips up to 115.6 mm (walk) and 148.9 mm
   (run), and carried the source action too, which the importer made the active one; now
   −2.5 and −6.9 mm, one action (8 clips, both humanoids, UniMate and preset sources).
4. **Look at the kept clip before using it** (rule 2): samples of the same prompt
   differ more than prompts do.
5. **Time:** 2 prompts × 2 samples took 6.5 min end to end on an M4 Pro — labelling,
   loading the model, generating, and driving the mesh in Blender.

### Prompting — measured on a four-legged test rig

These counts are on the 26-bone cat — they show how prompts behave; the clips themselves
were then rejected on review, which is why quadrupeds route to `tools/quadruped.py`.

Write like the training captions: start with **"An object"**, one motion, no
description of the character. Measured on the 26-bone cat, 8 samples per prompt (4 at
`--cfg` 3, 4 at 5, seed 0), each clip scored from its bones rather than by eye —
foot lift, all four feet off the ground, hip drop and distance travelled, as
fractions of the cat's height:

| Prompt | Does what it says | Criterion | Notes |
|---|---:|---|---|
| "An object walks in place." | **8 of 8** | feet lift 9-15%, no travel | the reliable walk |
| "An object walks forward." | **0 of 8** | — | **slides** 0.7-3.4 heights with the feet still: use "in place" and move the root yourself |
| "An object jumps forward." | 6 of 8 | all feet off the ground > 15% | 4 of the 6 leap more than a full height — too high for a cat |
| "An object crouches down." | 4 of 8 | hips drop > 20% | the others barely move |
| "An object runs forward." | 5 of 8 | travels > 2 heights, all feet off the ground | 3 of 4 at `--cfg` 5, 2 of 4 at 3 |

So **generate at least 4 samples per prompt** and keep the best; `--cfg` 5 helped
only the run.

### Speed — measured, M4 Pro, one 2 s clip

| Device | ODE solver | Time per clip |
|---|---|---:|
| CPU | adaptive (upstream default, 344 network calls) | 247 s |
| CPU | fixed, 50 Euler steps | 30 s |
| **MPS** | **fixed, 50 Euler steps** | **18 s** |

Measured on the earlier v2 checkpoint; on v3, 16 clips took 290 s on MPS, the same
~18 s each. `unimate.py` uses 50 Euler steps off CUDA; on the clip compared side by
side, the result was indistinguishable from the adaptive solver's by eye.
