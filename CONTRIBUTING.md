# Contributing

Fixes and additions are welcome. This document is short, and one rule shapes all
of it: **claims must be measured, not reasoned.**

## Contents

- [The one rule](#the-one-rule)
- [Finding ways to help](#finding-ways-to-help)
- [Setup](#setup)
- [Testing](#testing)
- [Pull requests](#pull-requests)
- [Adding or changing an iron rule](#adding-or-changing-an-iron-rule)
- [Reporting a bug](#reporting-a-bug)
- [Use of AI](#use-of-ai)
- [Questions](#questions)
- [Licence](#licence)

## The one rule

This skill's documentation was audited by *running* it, and **fifteen bugs turned
up that reading could not have found**: a manifest pointing at a path that did not
exist, twelve documented commands that resolved to nothing, six `pip install`
lines that fail on any PEP 668 Python, a texturing workflow that lost four of the
seven maps it downloaded, a batch runner whose scene-clear disabled the
integrations it depended on, an export that turned a 2,688-triangle scatter into
2 triangles.

None of those were visible in the text. Each needed the thing itself — the
official schema, a live addon, a dry-run of pip, a real PolyHaven material, a
generated Rigify rig.

So if you add a claim, run it first and put the number in. *"Draco is smaller"* is
an opinion. *"435.1 kB becomes 43.9 kB"* is a fact a reader can check and a
maintainer can re-verify later.

The corollary: when Blender changes, a measured claim fails loudly in CI. An
unmeasured one just quietly becomes wrong.

## Finding ways to help

Concrete gaps, roughly in order of value:

- **Paths never exercised.** `hunyuan3d` and Hyper3D Rodin generation, and
  Sketchfab sourcing. The first two consume credits and the third needs an API
  key, which is why they are untested — if you have access, running them once and
  reporting what actually happens is the most useful thing you can do here.
- **Token cost.** `SKILL.md` is around 15.7k tokens on invoke, up 50% over the
  audit. The measured tables it now carries could move into `references/`, where
  loading is lazy, without losing the decisions.
- **The FK/IK, twist-bone and facial-rigging sections** of
  `references/characters.md` need an actual animated character and a human eye on
  the deformation. A synthetic rig cannot judge them.
- **Anything the CI does not cover.** It was written after the audit, so it guards
  the mistakes already made. New classes are welcome — with a regression case, see
  [Testing](#testing).

## Setup

Required to work on the skill itself:

- **Blender 4.x+** (developed against 5.0, CI runs 5.2 LTS) with the
  [Blender MCP](https://github.com/ahujasid/blender-mcp) addon. Install the addon
  with `uvx blender-mcp install-addon` — `addon_utils.enable()` is not enough, it
  leaves property groups incomplete and failures name nothing relevant.
- **Python 3.10+** for `tools/`. No dependencies.

Additionally, to regenerate the gallery:

```bash
npm install -g @gltf-transform/cli gltfpack
brew install webp          # or your platform's equivalent, for cwebp
cd examples/gallery && ./run_gallery.sh
```

That reproduces all fifteen assets and the metrics table. If your numbers differ
from the README's, say so in the pull request — it means something changed.

## Testing

Before opening a pull request:

```bash
python3 tools/verify_docs.py        # documentation self-consistency
python3 tools/test_verify_docs.py   # and the checker's own regressions
```

Both run in CI on every push. If you touch `SKILL.md`, `references/` or the
gallery, the Blender workflow runs too:

```bash
blender --background --factory-startup --python tools/verify_blender.py
```

**If you add a check, add its regression case in the same change.** A checker that
only ever passes proves nothing — that is what exposed, in this repository, a
material audit firing on a harmless node while missing both real losses, and a rig
validator raising three false alarms on a perfectly correct production rig.

And **a check that fires on correct input is worse than no check**, because people
learn to ignore it, and then it protects nothing. That mistake was made four times
during the audit, twice inside the checkers themselves. Test both directions.

## Pull requests

- One concern per pull request. The audit's changes are separate commits for a
  reason: each is revertible on its own.
- Say what you measured and how. If a claim changed, show the before and after.
- Be explicit about what you did *not* test. Half the value of the audit's pull
  requests is their "not covered" sections.
- CI must be green. If a check fails and you believe the check is wrong, fix the
  check and add the case that proves it — do not weaken it.

## Adding or changing an iron rule

`SKILL.md` and `references/batch-mode.md` hold one numbered sequence: core rules
first, batch-specific after. Adding a core rule means renumbering the batch ones.

Three renumberings happened here and **two left a citation pointing at a rule that
had changed subject** — one of them said "Rule 23 (no prompts)" after 23 had become
the dimension-checking rule. `verify_docs.py` now validates cross-references by
meaning as well as existence, and the README's rule count. Run it, and update the
count.

## Reporting a bug

Use the [issue templates](.github/ISSUE_TEMPLATE). Say what you ran, what you
expected, what happened, and your Blender version.

Two things worth including that are easy to overlook:

- **Warnings, not only errors.** Several bugs here failed in complete silence and
  surfaced only as a Blender warning nobody was told to read. One example: a
  geometry-nodes export wrote a 1 kB file and reported success.
- **`get_addon_status()`**, which reports whether the MCP addon is behind the
  server. An outdated addon is missing commands, and the resulting errors name
  nothing relevant to the real cause.

## Use of AI

AI-assisted contributions are fine — this skill's own audit was AI-driven, and the
transcript is in the pull request history.

The bar is the same as everywhere else in this document, and AI makes it easier to
miss: **do not submit a claim a model produced without running it.** During the
audit an AI-written checker had four false positives, an AI-derived tool list was
silently truncated by a regex that excluded digits, and a rotation sign was wrong
twice before anyone checked the arithmetic. Every one of those looked plausible.

You are responsible for what you submit. Review it, run it, and mark what you did
not verify.

## Questions

For usage questions, open a
[discussion](https://github.com/elithril/blender-kiln/discussions) rather than an
issue. Issues are for something that is wrong.

## Licence

Contributions are accepted under the [MIT licence](LICENSE).
