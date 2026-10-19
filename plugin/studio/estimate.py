"""How long a request to Claude takes and what it costs, said before it is sent.

    estimate(project, task, account) -> {"task", "source", "n", "seen", "needed", "minutes": [lo, hi], "cost_usd": [lo, hi], "billed"}

n: the runs the figure comes from; seen: this project's runs of the task (under needed, the bench).

The tasks: create.text, create.photo (a Create request, with or without a reference photo),
output.web|game|ar|print, notes, chat, setup.

This project's own runs first (.kiln-studio/claude/usage.jsonl): a task is a run and the
resumes after it on the same conversation (each approval is a resume), summed. The time is
Claude's working time (duration_ms), not the time spent waiting for the user's approval.
Under MIN_RUNS such tasks, kiln's bench gives the figure (BENCH: the 2.2.0 baseline, headless
sessions with nobody to wait for); a task the bench has no run of has no estimate. The range
is the middle half of what was seen (25th to 75th percentile), or lowest to highest under 4.
The cost is the API price: a subscription pays nothing more (it counts against its quota),
an API key is billed. Standard library only.
"""
from __future__ import annotations

import json
import re
import statistics

import studiolib as sl

MIN_RUNS = 3
TASK_RE = re.compile(r"^(create\.(text|photo)|output\.(web|game|ar|print)|notes|chat|setup)$")

# bench/runs/v220-ahujasid/<brief>/result.json, kiln 2.2.0, October 2026: (seconds, $ API-equivalent).
BENCH = {
    "create.text": [(160, 0.92), (184, 0.98), (143, 1.05), (220, 1.48), (283, 1.59), (258, 1.38), (341, 1.71)],
    "create.photo": [(967, 4.57), (1136, 4.17), (1230, 5.18)],
}


def task_of(entry: dict, requests: dict[str, dict]) -> str | None:
    """The task a run starts (None for a resume, which continues the one before)."""
    if entry.get("task"):
        return entry["task"]
    kind = entry.get("kind")
    if kind == "create":
        r = requests.get((entry.get("key") or "").removeprefix("request:"))
        return "create.photo" if r and r.get("reference") else "create.text"
    if kind in ("notes", "setup"):
        return kind
    if kind in ("chat", "answer"):
        return "chat"
    return None


def tasks(project: sl.Project) -> dict[str, list[tuple[float, float]]]:
    """Each task's past runs in this project: (seconds of work, $), resumes summed in."""
    p = project.root / ".kiln-studio" / "claude" / "usage.jsonl"
    requests = {r["id"]: r for r in sl.load_requests(project)}
    done: list[tuple[str, list[float]]] = []
    open_: dict[str, list[float]] = {}   # conversation key -> [seconds, $] of its task under way
    for line in (p.read_text().splitlines() if p.is_file() else []):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        secs, cost = (e.get("duration_ms") or 0) / 1000, e.get("cost_usd") or 0
        task = task_of(e, requests) if e.get("kind") != "resume" else None
        if task:
            acc = [secs, cost]
            open_[e.get("key")] = acc
            done.append((task, acc))
        elif e.get("key") in open_:
            open_[e["key"]][0] += secs
            open_[e["key"]][1] += cost
    out: dict[str, list[tuple[float, float]]] = {}
    for task, (secs, cost) in done:
        if secs > 0:
            out.setdefault(task, []).append((secs, cost))
    return out


def _range(xs: list[float]) -> list[float]:
    xs = sorted(xs)
    if len(xs) < 4:
        return [xs[0], xs[-1]]
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return [q[0], q[2]]


def estimate(project: sl.Project, task: str, account: str = "subscription") -> dict:
    if not TASK_RE.match(task or ""):
        raise ValueError(f"not a task: {task!r}")
    mine = tasks(project).get(task, [])
    runs, source = (mine, "project") if len(mine) >= MIN_RUNS else (BENCH.get(task, []), "bench")
    out = {"task": task, "source": source if runs else None, "n": len(runs), "seen": len(mine),
           "needed": MIN_RUNS, "billed": account == "api_key"}
    if runs:
        out["minutes"] = [round(x / 60, 1) for x in _range([s for s, _ in runs])]
        out["cost_usd"] = [round(x, 2) for x in _range([c for _, c in runs])]
    return out
