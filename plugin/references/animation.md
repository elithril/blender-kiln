# Animation Reference (Phase 5d)

> Getting motion onto a rigged asset: which route fits which input, and the one
> automated route kiln has measured — UniMate, text-to-motion for any skeleton.

**Phase 5d is optional and runs after [5c] RIG.** Its input is a rig built to
`references/characters.md` § Animation-ready skeleton. A leg made of one bone cannot
fold a knee, whatever drives it: on such a rig, both generators measured here gave
unusable motion (MoCapAnything V2, and UniMate's earlier v2 checkpoint).

## Pick the route from what you have

| You have | Route | Notes |
|---|---|---|
| An asset that already ships animations (Quaternius, Poly Pizza "animated") | **Keep them** | Hand-made clips beat every generator measured here. Export them as they are (PHASE 7). |
| A humanoid and standard moves (walk, run, idle, attack) | **Mixamo** library, retargeted | Free with an Adobe account; ~2,500 clips. See `references/characters.md` § Animation Retargeting. |
| A text description, any skeleton (biped, quadruped, tail, wings) | **UniMate** — below | Experimental. Non-commercial weights. Samples vary: generate 4, keep the best. |
| A video of the motion | Not supported yet | MoCapAnything V2 (MIT) was measured: excellent on rigs from its own training set, unusable on two rigs from outside it (limbs swung loose, tail stretched ~3×). On CPU: ~15 min to prepare a rig's reference view, then ~10 min per video. |
| Nothing — a specific, authored move | Keyframe it by hand | `references/characters.md` § Blender 5.x — Layered Actions. |

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
python3 plugin/tools/unimate.py animate --asset SK_Cat_rigged.glb \
    --prompt "An object walks in place." "An object jumps forward." --reps 4 --out ./anim
```

1. **The run stops once for review** and prints the path of `REVIEW.md`. Read the
   joint labels in `annotation.json`, fix what is wrong, then rerun with
   `--annotation <that file>`. For a four-legged animal, set the hind leg to
   *Thigh / Shin / Fetlock / Foot* (`…Foot` → *Fetlock*, `…ToeBase` → *Foot*): that is
   how the training data labels it.
2. **Output:** one animated GLB per prompt × repetition, 2 s long (generated as 60
   frames at 30 fps; the GLB carries them as 48 at 24 fps). Longer moves chain prompts (UniMate's "motion expansion"; not measured by
   kiln).
3. **Look at every clip before keeping one** (rule 2): samples of the same prompt
   differ more than prompts do.
4. **Time:** 2 prompts × 2 samples took 6.5 min end to end on an M4 Pro — labelling,
   loading the model, generating, and driving the mesh in Blender.

### Prompting — measured

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
