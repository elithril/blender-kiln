#!/usr/bin/env python3
"""Check that the skill's own documentation is still true.

Text only: no Blender, no network, runs in seconds. Every check here exists
because the corresponding mistake was actually made in this repository — the
comments say which.

    python3 tools/verify_docs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
BATCH = ROOT / "references" / "batch-mode.md"
DOCS = [SKILL, README] + sorted((ROOT / "references").glob("*.md"))

failures: list[str] = []
notes: list[str] = []


def fail(check: str, msg: str) -> None:
    failures.append(f"{check}: {msg}")


def rule_block(path: Path, header: str) -> dict[int, str]:
    """Parse a fenced, numbered iron-rules block into {number: text}."""
    text = path.read_text()
    if header not in text:
        fail("rules", f"{path.name} has no section {header!r}")
        return {}
    body = text[text.index(header):]
    body = body[body.index("```") + 3:]
    body = body[:body.index("```")]
    out: dict[int, str] = {}
    num, cur = None, []
    for line in body.split("\n"):
        m = re.match(r"^\s*(\d+)\.\s+(.*)", line)
        if m:
            if num is not None:
                out[num] = " ".join(cur)
            num, cur = int(m.group(1)), [m.group(2)]
        elif num is not None and line.strip():
            cur.append(line.strip())
    if num is not None:
        out[num] = " ".join(cur)
    return out


# ── 1. Iron rules form one unbroken sequence.
# Three renumberings happened here; two left the sequence or a reference wrong.
core = rule_block(SKILL, "## Iron Rules")
batch = rule_block(BATCH, "### Iron Rules (batch-specific)")
rules = {**core, **batch}
if rules:
    expected = list(range(1, len(rules) + 1))
    if sorted(rules) != expected:
        missing = set(expected) - set(rules)
        dupes = [n for n in rules if list(rules).count(n) > 1]
        fail("rules", f"not a 1..N sequence — missing {sorted(missing)}, repeated {dupes}")
    else:
        notes.append(f"rules: {len(core)} core + {len(batch)} batch = {len(rules)}, unbroken")

# ── 2. Every cited rule number exists.
cited: dict[int, list[str]] = {}
for doc in DOCS:
    for m in re.finditer(r"\b[Rr]ules?\s+(\d+)\b", doc.read_text()):
        cited.setdefault(int(m.group(1)), []).append(doc.name)
unknown = {n: srcs for n, srcs in cited.items() if n not in rules}
if unknown:
    for n, srcs in sorted(unknown.items()):
        fail("xref", f"rule {n} cited in {sorted(set(srcs))} does not exist")
else:
    notes.append(f"xref: {len(cited)} distinct rule numbers cited, all resolve")

# ── 3. Cited rules mean what the citation claims.
# A renumbering left rule 28 pointing at a "Rule 23 (no prompts)" that had
# become the get_object_info rule. Resolving is not enough; the sense matters.
SEMANTIC = {
    "no prompts": "prompt",
    "frame the viewport": "frame",
    "integration status": "integration",
    "get_object_info": "get_object_info",
    "naming convention": "nam",
}
for doc in DOCS:
    text = doc.read_text()
    for phrase, expect in SEMANTIC.items():
        # Tight window only. A 40-char window matched "Rule 6 is overridden —
        # Rule 28 (no prompts)" against rule 6, which is a false positive, and a
        # check that fires on correct text gets ignored.
        for m in re.finditer(rf"[Rr]ule\s+(\d+)\s*\(?{re.escape(phrase)}", text):
            n = int(m.group(1))
            if n in rules and expect.lower() not in rules[n].lower():
                fail("semantics", f"{doc.name} says rule {n} is about {phrase!r}, "
                                  f"but rule {n} reads {rules[n][:60]!r}")

# ── 4. The rule count advertised in the README matches reality.
m = re.search(r"enforces (\d+) rules \((\d+) core \+ (\d+) batch", README.read_text())
if not m:
    fail("count", "README does not state the rule count in the expected form")
elif (int(m.group(1)), int(m.group(2)), int(m.group(3))) != (len(rules), len(core), len(batch)):
    fail("count", f"README says {m.group(1)} ({m.group(2)}+{m.group(3)}), "
                  f"actual {len(rules)} ({len(core)}+{len(batch)})")
else:
    notes.append(f"count: README matches at {len(rules)}")

# ── 4b. Per-file line counts in the structure table.
# Three of twelve had drifted by 23-54% after eight pull requests. The total was
# checked; the rows were not, which is how a stale number survives a review.
for m in re.finditer(r"\| `references/([\w.-]+)` \|[^|]+\| ~(\d+) \|", README.read_text()):
    name, claimed = m.group(1), int(m.group(2))
    ref = ROOT / "references" / name
    if not ref.exists():
        fail("counts", f"README lists references/{name}, which does not exist")
        continue
    actual = len(ref.read_text().split("\n"))
    if abs(actual - claimed) / max(claimed, 1) > 0.15:
        fail("counts", f"references/{name}: README says ~{claimed}, actual {actual}")

m = re.search(r"\*\*Total: ~([\d,]+) lines\*\*", README.read_text())
if m:
    claimed = int(m.group(1).replace(",", ""))
    actual = sum(len(f.read_text().split("\n"))
                 for f in [SKILL] + sorted((ROOT / "references").glob("*.md")))
    if abs(actual - claimed) / max(claimed, 1) > 0.15:
        fail("counts", f"README total says ~{claimed:,}, actual {actual:,}")
    else:
        notes.append(f"counts: structure table within 15% ({actual:,} lines)")

# ── 5. Referenced files exist.
# SKILL.md once pointed at ../creative-excellence/ and two other skills that
# existed nowhere, and outside the plugin directory besides.
for doc in DOCS:
    for m in re.finditer(r"`((?:\.\./|references/|examples/|tools/|docs/)[\w./-]+\.\w+)`", doc.read_text()):
        rel = m.group(1)
        if rel.startswith("../"):
            fail("paths", f"{doc.name} references {rel} — outside the plugin directory")
        elif not (ROOT / rel).exists():
            fail("paths", f"{doc.name} references {rel}, which does not exist")

# ── 6. README images resolve.
imgs = re.findall(r'src="([^"]+\.(?:webp|png|jpg))"', README.read_text())
missing_imgs = [i for i in imgs if not (ROOT / i).exists()]
if missing_imgs:
    fail("images", f"missing: {missing_imgs}")
else:
    notes.append(f"images: {len(imgs)}/{len(imgs)} resolve")

# ── 7. No bare pip3 install.
# All six in this repo failed on any PEP 668 Python, including the very first
# command the recommended path proposed.
for doc in DOCS:
    for i, line in enumerate(doc.read_text().split("\n"), 1):
        # `uv pip install`, and any pip reached through a venv path, are the
        # recommended forms — not what this check is looking for.
        if re.search(r"(?<!`)\bpip3?\s+install\b", line) \
           and "venv" not in line \
           and not re.search(r"\buv\s+pip\b", line) \
           and not re.search(r"fail|never|not enough|instead|PEP 668", line, re.I):
            fail("pip", f"{doc.name}:{i} bare pip install — use a venv: {line.strip()[:70]}")

# ── 8. The plugin manifest is loadable and self-consistent.
mf = ROOT / ".claude-plugin" / "marketplace.json"
if not mf.exists():
    fail("manifest", "marketplace.json is missing")
else:
    try:
        data = json.loads(mf.read_text())
    except json.JSONDecodeError as e:
        fail("manifest", f"invalid JSON: {e}")
        data = None
    if data:
        if not isinstance(data.get("owner"), dict):
            fail("manifest", "owner must be an object, per the marketplace schema")
        for plugin in data.get("plugins", []):
            src = plugin.get("source")
            if not isinstance(src, str) or not src.startswith("./"):
                fail("manifest", f"source {src!r} must be a path starting with ./")
            elif not (ROOT / src).is_dir():
                fail("manifest", f"source {src!r} is not a directory")
        # A SKILL.md at the plugin root is what makes source './' work at all.
        if not SKILL.exists():
            fail("manifest", "source './' needs a SKILL.md at the repository root")

# ── 9. Documented slash commands use the form that actually resolves.
# Twelve /kiln:<sub> commands were documented; a colon addresses plugin:skill,
# so none of them resolved to anything.
for doc in DOCS:
    for i, line in enumerate(doc.read_text().split("\n"), 1):
        if re.search(r"/kiln:[a-z]", line) and not re.search(
                r"colon|resolve|never tell|Unknown command|instead", line, re.I):
            fail("commands", f"{doc.name}:{i} uses /kiln:<sub>; the invocable form is "
                             f"/kiln <sub>: {line.strip()[:70]}")

print("── verify_docs")
for n in notes:
    print(f"  ok   {n}")
for f in failures:
    print(f"  FAIL {f}")
print(f"── {len(failures)} failure(s)")
sys.exit(1 if failures else 0)
