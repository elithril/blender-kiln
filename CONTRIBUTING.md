# Contributing

Fixes and additions are welcome. One rule shapes everything below.

## Claims must be measured, not reasoned

This skill's documentation was audited by running it, and **fifteen bugs turned
up that reading could not have found**. A manifest pointing at a path that did
not exist. Twelve documented commands that resolved to nothing. Six
`pip install` lines that failed on any PEP 668 Python. A texturing workflow that
lost four of the seven maps it downloaded. A batch runner whose scene-clear
disabled the integrations it depended on. An export that turned a 2,688-triangle
scatter into 2 triangles.

None of those were visible in the text. Each needed the thing itself: the
official schema, a live addon, a dry-run of pip, a real PolyHaven material, a
generated Rigify rig.

So: **if you add a claim, run it first, and put the number in.** "Draco is
smaller" is an opinion; "435.1 kB becomes 43.9 kB" is a fact a reader can check
and a future maintainer can re-verify.

## Before opening a pull request

```bash
python3 tools/verify_docs.py        # documentation self-consistency, seconds
python3 tools/test_verify_docs.py   # and the checker's own regression suite
```

Both run in CI on every push (`.github/workflows/verify.yml`). If you touch
`SKILL.md`, `references/` or the gallery, the Blender workflow also runs
(`.github/workflows/blender.yml`); to run it locally:

```bash
blender --background --factory-startup --python tools/verify_blender.py
```

## If you add a check

Add its regression to `tools/test_verify_docs.py` in the same change. A checker
that only ever passes proves nothing — that principle came out of finding, in
this repository, a material audit that fired on a harmless node while missing
both real losses, and a rig validator that raised three false alarms on a
perfectly correct production rig.

And **a check that fires on correct input is worse than no check**, because
people learn to ignore it. That mistake was made four times during the audit,
including twice inside the checkers themselves. Test both directions.

## Iron rules

`SKILL.md` and `references/batch-mode.md` hold a single numbered sequence — core
rules first, batch-specific after. Adding one means renumbering the batch rules.
Three renumberings happened here and **two left a citation pointing at a rule
that had changed subject**, so `verify_docs.py` now checks cross-references by
meaning and not only by existence. Run it.

## Reporting a bug

Say what you ran, what you expected, what happened, and your Blender version.
`get_addon_status()` reports whether the MCP addon is behind the server, which is
worth including — an outdated addon is missing commands, and the resulting errors
name nothing relevant.

## Licence

Contributions are accepted under the [MIT licence](LICENSE).
