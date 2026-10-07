# Animation Reference (Phase 5d)

> Getting motion onto a rigged asset: which route fits which subject, the tools kiln
> ships for each, and the rules every scripted animation here was corrected into.

**Phase 5d is optional and runs after [5c] RIG.** Its input is a rig built to
`references/characters.md` § Animation-ready skeleton. A leg made of one bone cannot
fold a knee, whatever drives it: on such a rig, both generators measured here gave
unusable motion (MoCapAnything V2, and UniMate's earlier v2 checkpoint).

## Pick the route from the subject

| Subject | Route | Measured |
|---|---|---|
| Ships its own clips (Quaternius, Poly Pizza "animated") | **Keep them** — export as they are (PHASE 7) | Hand-made clips beat every generator tried here. |
| **Four-legged** — idle, walk | **`tools/quadruped.py`** — scripted cycle, below | Approved cycle: legs ≤ 93% of their length, paws in step, exact loop. |
| **Four-legged** — run, jump, sit, attack… | Its own clips, or keyframe by hand | **Not UniMate**: its walk was unusable on 4 quadrupeds, the model author's own example included. Scripted versions of these were tried too and rejected on review. |
| **Biped or winged** creature, a sentence | **UniMate** with `--loop`, below | A reviewer approved a human's walk and a dragon's wing flap, each looped from 4 samples. Non-commercial weights. |
| Humanoid, standard moves | **Mixamo** library, retargeted | ~2,500 clips, free with an Adobe account. `references/characters.md` § Animation Retargeting. |
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
4. **Measure a rotation's sign before using it.** Rotate +0.2 rad and watch which way a
   probe moves. A sit and an attack written with the assumed sign tipped the cat nose
   down. The lamp and chest scripts measure every sign first — and were right first time.
5. **Loop exactly.** A cycle of P frames keys frames 0..P−1; keying P as well repeats a
   pose and stutters at the seam.
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
   `samples/`.
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
