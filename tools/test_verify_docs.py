#!/usr/bin/env python3
"""Seed each regression verify_docs.py claims to catch, and check it does.

A checker that only ever passes proves nothing. Every case here is a mistake
that was actually made in this repository.

    python3 tools/test_verify_docs.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Two kinds of case. `expect="name"` seeds a regression and demands that check
# fire. `expect=None` seeds a CORRECT edit and demands total silence — because
# every check in this file has, at some point, fired on correct input, and a
# check people learn to ignore is worse than no check at all.
CASES: list[tuple[str, str | None, callable]] = []


def case(name: str, expect: str | None):
    def deco(fn):
        CASES.append((name, expect, fn))
        return fn
    return deco


@case("renumbering leaves a gap", "rules")
def _(root: Path):
    p = root / "references" / "batch-mode.md"
    p.write_text(p.read_text().replace("\n27. ", "\n99. "))


@case("citation of a rule that does not exist", "xref")
def _(root: Path):
    p = root / "SKILL.md"
    p.write_text(p.read_text() + "\n\nSee rule 77 for details.\n")


@case("citation points at the wrong rule", "semantics")
def _(root: Path):
    p = root / "references" / "batch-mode.md"
    p.write_text(p.read_text().replace("Rule 28 (no prompts)", "Rule 24 (no prompts)"))


@case("README rule count drifts", "count")
def _(root: Path):
    p = root / "README.md"
    p.write_text(re.sub(r"enforces \d+ rules \(\d+ core", "enforces 28 rules (23 core", p.read_text()))


@case("a per-file line count goes stale", "counts")
def _(root: Path):
    p = root / "README.md"
    p.write_text(re.sub(r"(\| `references/characters\.md` \|[^|]+\| )~\d+", r"\g<1>~120", p.read_text()))


@case("reference to a file outside the plugin", "paths")
def _(root: Path):
    p = root / "SKILL.md"
    p.write_text(p.read_text() + "\n\n| Artistic framing | `../creative-excellence/SKILL.md` |\n")


@case("reference to a file that does not exist", "paths")
def _(root: Path):
    p = root / "SKILL.md"
    p.write_text(p.read_text() + "\n\nLoad `references/does-not-exist.md`.\n")


@case("two different minimum Blender versions are stated", "versions")
def _(root: Path):
    p = root / "README.md"
    p.write_text(p.read_text() + "\n\nRequires Blender 3.6+ for this feature.\n")


@case("a history note is not a requirement", None)
def _(root: Path):
    p = root / "references" / "characters.md"
    p.write_text(p.read_text() + "\n\nSince Blender 6.0, bone collections were replaced again.\n")


@case("an API-availability qualifier is not a requirement", None)
def _(root: Path):
    p = root / "references" / "texturing-strategy.md"
    p.write_text(p.read_text() + "\n```python\n# Thin Film weight (Blender 5.2+)\n```\n")


@case("uv pip install is not bare pip", None)
def _(root: Path):
    p = root / "references" / "ai-generation.md"
    p.write_text(p.read_text() + "\n```bash\nuv pip install trimesh\n```\n")


@case("the two manifests drift apart on version", "manifest")
def _(root: Path):
    p = root / ".claude-plugin" / "plugin.json"
    p.write_text(p.read_text().replace('"version": "1.1.2"', '"version": "9.9.9"'))


@case("README image goes missing", "images")
def _(root: Path):
    (root / "examples" / "gallery" / "renders" / "gallery.webp").unlink()


@case("bare pip3 install creeps back", "pip")
def _(root: Path):
    p = root / "references" / "ai-generation.md"
    p.write_text(p.read_text() + "\n```bash\npip3 install gradio_client\n```\n")


@case("bare pip inside backticks slips through", "pip")
def _(root: Path):
    p = root / "README.md"
    p.write_text(p.read_text() + "\n| **Thing** | `pip3 install something` | note |\n")


@case("manifest source stops being a directory", "manifest")
def _(root: Path):
    p = root / ".claude-plugin" / "marketplace.json"
    d = json.loads(p.read_text())
    d["plugins"][0]["source"] = "skills/blender-kiln/SKILL.md"
    p.write_text(json.dumps(d, indent=2))


@case("manifest owner reverts to a string", "manifest")
def _(root: Path):
    p = root / ".claude-plugin" / "marketplace.json"
    d = json.loads(p.read_text())
    d["owner"] = "elithril"
    p.write_text(json.dumps(d, indent=2))


@case("colon command form comes back", "commands")
def _(root: Path):
    p = root / "README.md"
    p.write_text(p.read_text() + "\n| `/kiln:setup` | Environment detection |\n")


def run(root: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(root / "tools" / "verify_docs.py")],
                       capture_output=True, text=True, cwd=root)
    return r.returncode, r.stdout + r.stderr


print("── baseline (unmodified repo must pass)")
code, out = run(ROOT)
if code != 0:
    print(out)
    print("── BASELINE FAILS — fix the repo before trusting this test")
    sys.exit(1)
print("  ok   clean repo passes\n")

print("── seeded regressions")
bad = 0
for name, expect, seed in CASES:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "repo"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "out", "__pycache__"))
        seed(work)
        code, out = run(work)
        fails = [l.strip() for l in out.split("\n") if l.strip().startswith("FAIL")]
        if expect is None:
            good = code == 0
            print(f"  {'ok  ' if good else 'CRIE'} {name}  (must stay silent)")
        else:
            good = code != 0 and any(l.startswith(f"FAIL {expect}") for l in fails)
            print(f"  {'ok  ' if good else 'MISS'} {name}  (expected check: {expect})")
        if not good:
            bad += 1
            print("       " + ("\n       ".join(fails) or "no failure reported"))
pos = sum(1 for _, e, _ in CASES if e is not None)
print(f"\n── {len(CASES) - bad}/{len(CASES)} cases pass "
      f"({pos} seeded regressions, {len(CASES) - pos} must-stay-silent)")
sys.exit(1 if bad else 0)
