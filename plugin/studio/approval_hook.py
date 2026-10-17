#!/usr/bin/env python3
"""PreToolUse hook for Kiln Studio's Claude worker: lets safe tool calls through and
defers the others, for the user to allow or deny in the Studio page.

Enabled only for the worker's runs (worker.py passes it through --settings); an ordinary
Claude Code session never loads it. It never waits for an answer: a hook that waits is
let through after its timeout, so it defers instead, the run ends with
stop_reason "tool_deferred", and the worker resumes the session once the user answered —
the same call then reaches this hook again and finds the answer in
$KILN_DECISIONS/<tool_use_id>.json.

Safe, allowed at once:
- reading (Read, Glob, Grep), the to-do list, skills, tool search;
- the worker's Blender (mcp__blender__*), except paid generation tools;
- the kiln-studio MCP tools;
- Edit / Write / NotebookEdit inside the project folder;
- Bash commands made only of the skill's own Python scripts and read-only commands.
Anything else is deferred. AskUserQuestion is denied with a reason: nobody can answer it
mid-run, the question goes in the message instead.

Standard library only. Also importable: classify() is what the tests exercise.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

ALWAYS = {"Read", "Glob", "Grep", "TodoWrite", "Skill", "ToolSearch", "LS"}
EDITS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_ONLY = {"ls", "cat", "head", "tail", "wc", "file", "stat", "grep", "rg", "echo", "pwd", "which",
             "du", "date", "sort", "uniq", "cut", "tr", "jq", "basename", "dirname", "realpath", "test",
             "true", "printf", "diff", "shasum", "md5", "sha256sum", "tree"}
# Blender MCP tools that can spend credits (rule 5): never automatic.
PAID = re.compile(r"^mcp__blender__(generate_|poll_|import_generated_asset)")
HARMLESS_REDIRECTS = re.compile(r"\s*(?:2>&1|&>\s*/dev/null|[12]?>\s*/dev/null)")


def _inside(p: str, base: Path, cwd: Path) -> bool:
    try:
        q = Path(p).expanduser()
        q = (q if q.is_absolute() else cwd / q).resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return q == base or base in q.parents


def bash_safe(cmd: str, root: Path, plugin: Path) -> bool:
    """True when every part of the command is the skill's own script or a read-only command."""
    if any(x in cmd for x in ("`", "$", "<(", ">(", "<<")):
        return False
    cmd = HARMLESS_REDIRECTS.sub(" ", cmd)
    if ">" in cmd or "<" in cmd:
        return False
    cwd = root
    for part in re.split(r"&&|\|\||;|\||\n", cmd):
        if not part.strip():
            continue
        try:
            argv = shlex.split(part)
        except ValueError:
            return False
        if not argv:
            continue
        name = os.path.basename(argv[0])
        if name == "cd":
            if len(argv) != 2 or not (_inside(argv[1], root, cwd) or _inside(argv[1], plugin, cwd)):
                return False
            cwd = Path(argv[1]) if Path(argv[1]).is_absolute() else (cwd / argv[1])
            continue
        if re.fullmatch(r"python3?(\.\d+)?", name) or argv[0] == sys.executable:
            if len(argv) < 2 or argv[1].startswith("-") or not argv[1].endswith(".py"):
                return False
            if not _inside(argv[1], plugin, cwd):
                return False
            continue
        if name == "find":
            if any(a in ("-exec", "-execdir", "-delete", "-ok", "-okdir", "-fprint", "-fprintf", "-fls") for a in argv):
                return False
            continue
        if name == "mkdir":
            if not all(_inside(a, root, cwd) for a in argv[1:] if not a.startswith("-")):
                return False
            continue
        if name not in READ_ONLY:
            return False
    return True


def classify(tool: str, tool_input: dict, root: Path, plugin: Path) -> tuple[str, str]:
    """(decision, reason) before the user has said anything: allow, defer or deny."""
    if tool in ALWAYS or tool.startswith("mcp__kiln-studio__"):
        return "allow", "safe"
    if tool.startswith("mcp__blender__"):
        if PAID.match(tool):
            return "defer", "a generation tool that can spend credits"
        return "allow", "the worker's own Blender"
    if tool == "AskUserQuestion":
        return "deny", ("Nobody can answer a question mid-run here: the user reads your messages in Kiln "
                        "Studio. Put the question at the end of your message, on a line starting "
                        "KILN-PROPOSAL:, and end your turn.")
    if tool in EDITS:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if path and _inside(path, root, root):
            return "allow", "inside the project"
        return "defer", "writes outside the project"
    if tool == "Bash":
        if bash_safe(str(tool_input.get("command", "")), root, plugin):
            return "allow", "the skill's scripts or a read-only command"
        return "defer", "a shell command outside the safe list"
    return "defer", f"{tool} is not on the safe list"


def decide(event: dict, env: dict) -> tuple[str, str]:
    root = Path(env.get("KILN_STUDIO_ROOT") or event.get("cwd") or ".").resolve()
    plugin = Path(env.get("KILN_PLUGIN_DIR") or Path(__file__).resolve().parent.parent).resolve()
    tool, tool_input = str(event.get("tool_name", "")), event.get("tool_input") or {}
    decision, reason = classify(tool, tool_input if isinstance(tool_input, dict) else {}, root, plugin)
    if decision == "defer" and env.get("KILN_DECISIONS"):
        tid = str(event.get("tool_use_id", ""))
        if re.fullmatch(r"[A-Za-z0-9_-]{1,100}", tid):
            p = Path(env["KILN_DECISIONS"]) / f"{tid}.json"
            if p.is_file():
                try:
                    ans = json.loads(p.read_text())
                except (OSError, ValueError):
                    ans = {}
                if ans.get("decision") == "allow":
                    return "allow", "the user allowed it in Kiln Studio"
                if ans.get("decision") == "deny":
                    return "deny", "The user denied this call in Kiln Studio" + (f": {ans['reason']}" if ans.get("reason") else ".")
    return decision, reason


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)   # no decision: dontAsk refuses whatever is not on --allowedTools
    decision, reason = decide(event, dict(os.environ))
    log = os.environ.get("KILN_DECISIONS")
    if log:
        try:
            with open(Path(log) / "hook.log", "a") as f:
                f.write(json.dumps({"tool": event.get("tool_name"), "id": event.get("tool_use_id"),
                                    "decision": decision, "reason": reason}) + "\n")
        except OSError:
            pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": decision,
                                             "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    main()
