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
- Bash commands made only of the skill's own Python scripts and read-only commands
  (`sed -n` printing lines included), the skill's Swift scripts, `sips` reading a size or
  writing a copy in the project, `gltf-transform`'s optimisation steps on the project's files
  (never `optimize`), `cp` / `mv` / `ditto` into the project, and a background
  Blender running one of the skill's scripts.
Anything else is deferred (with KILN_APPROVALS=all: allowed, but for a write outside the
project, sudo or rm outside it; with KILN_APPROVALS=auto: left to Claude Code's auto mode, but
paid generation, which waits for the user unless KILN_PAID=auto). AskUserQuestion is denied with a reason:
nobody can answer it mid-run, the question goes in the message instead.

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
GLTF_TRANSFORM_STEPS = {"inspect", "validate", "draco", "meshopt", "webp", "ktx2", "resize", "dedup", "prune"}
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
    # Split into commands as the shell does: on ; && || | & and new lines, never inside quotes.
    try:
        lex = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return False
    commands, cur = [], []
    for tok in tokens:
        if tok and set(tok) <= set(";&|"):
            commands.append(cur); cur = []
        else:
            cur.append(tok)
    commands.append(cur)
    for argv in commands:
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
        if name == "sed":
            # Printing lines (-n), or editing files of the project in place (-i, like Edit there);
            # never a command that writes elsewhere or runs one (w, W, e).
            args = argv[1:]
            inplace = any(a.startswith(("-i", "--in-place")) for a in args)
            if not inplace and "-n" not in args:
                return False
            if any(re.search(r"(^|[;{}\s/\d$])[wWe](\s|$)", a) for a in args if not a.startswith("-")):
                return False
            if inplace:
                # BSD sed: -i '' then the script then the files; GNU: -i[SUFFIX].
                rest = [a for a in args if not a.startswith("-")]
                if args[args.index(next(a for a in args if a.startswith(("-i", "--in-place")))) + 1:][:1] == [""]:
                    rest = rest[1:] if rest and rest[0] == "" else rest
                files = [a for a in rest[1:] if a != ""]
                if not files or not all(_inside(f, root, cwd) for f in files):
                    return False
            continue
        if (name == "command" and argv[1:2] in (["-v"], ["-V"])) or name == "type" \
                or argv[1:] in (["--version"], ["-v"], ["-V"], ["version"]):
            continue   # which tools are installed, and their versions
        if name.lower() == "blender":
            # A background Blender running the skill's own script (fidelity_check, verify…).
            if not ({"-b", "--background"} & set(argv)) or any(a in ("--python-expr", "--python-console") for a in argv):
                return False
            scripts = [argv[k + 1] for k, a in enumerate(argv[:-1]) if a in ("--python", "-P")]
            if not scripts or not all(_inside(x, plugin, cwd) for x in scripts):
                return False
            continue
        if name == "swift":
            # The skill's own Swift scripts (cutout.swift), like its Python ones.
            if len(argv) < 2 or not argv[1].endswith(".swift") or not _inside(argv[1], plugin, cwd):
                return False
            continue
        if name in ("cp", "mv", "ditto"):
            # Copies and moves within the project (a source may also be the skill's own file).
            paths = [a for a in argv[1:] if not a.startswith("-")]
            if len(paths) < 2 or not _inside(paths[-1], root, cwd):
                return False
            if not all(_inside(a, root, cwd) or _inside(a, plugin, cwd) for a in paths[:-1]):
                return False
            continue
        if name == "gltf-transform":
            # The skill's own optimisation steps (cli-tools.md) on the project's files; never
            # `optimize`, whose simplify destroys geometry (rule 20). On 2026-10-21 a session
            # dropped this step for Blender's exporter only to avoid the approval.
            sub = next((a for a in argv[1:] if not a.startswith("-")), None)
            if sub not in GLTF_TRANSFORM_STEPS:
                return False
            files = [a for a in argv[2:] if re.search(r"\.(glb|gltf)$", a, re.I)]
            if not files or not all(_inside(f, root, cwd) for f in files):
                return False
            continue
        if name == "sips":
            # Reading an image's size, or writing a converted copy inside the project.
            if "--out" in argv or "-o" in argv:
                k = argv.index("--out") if "--out" in argv else argv.index("-o")
                if k + 1 >= len(argv) or not _inside(argv[k + 1], root, cwd):
                    return False
            elif any(a in ("-s", "--setProperty", "-r", "--rotate", "-f", "--flip", "-c", "-z", "-Z", "--resampleWidth",
                           "--resampleHeight", "--resampleHeightWidth", "--resampleHeightWidthMax", "--padToHeightWidth",
                           "--cropToHeightWidth", "-m", "--matchTo", "-e", "--embedProfile", "-d", "--deleteProperty") for a in argv):
                return False   # changes the file in place
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


def outside(tool: str, tool_input: dict, root: Path) -> str:
    """What still waits for the user with allow all: a write outside the project, sudo, or rm of a
    path outside it. Empty when the call stays in the project's work."""
    if tool in EDITS:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        return "" if path and _inside(path, root, root) else "writes outside the project"
    if tool != "Bash":
        return ""
    cmd = str(tool_input.get("command", ""))
    try:
        lex = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return "a shell command it cannot read"
    cwd, first = root, True
    for i, tok in enumerate(tokens):
        if set(tok) <= set(";&|"):
            first = True
            continue
        name = os.path.basename(tok) if first else None
        first = False
        if tok == "sudo":
            return "sudo"
        if name == "cd" and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            cwd = Path(nxt) if Path(nxt).expanduser().is_absolute() else cwd / nxt
        if name in ("rm", "rmdir", "unlink"):
            args = []
            for t in tokens[i + 1:]:
                if set(t) <= set(";&|"):
                    break
                if not t.startswith("-"):
                    args.append(t)
            if not args or not all(_inside(a, root, cwd) for a in args):
                return "deletes outside the project"
    return ""


def decide(event: dict, env: dict) -> tuple[str, str]:
    root = Path(env.get("KILN_STUDIO_ROOT") or event.get("cwd") or ".").resolve()
    plugin = Path(env.get("KILN_PLUGIN_DIR") or Path(__file__).resolve().parent.parent).resolve()
    tool, tool_input = str(event.get("tool_name", "")), event.get("tool_input") or {}
    decision, reason = classify(tool, tool_input if isinstance(tool_input, dict) else {}, root, plugin)
    if decision == "defer" and PAID.match(tool) and env.get("KILN_PAID") == "auto":
        return "allow", "paid generation is set to auto in Kiln Studio"
    if decision == "defer" and env.get("KILN_APPROVALS") == "all" and not PAID.match(tool):
        # Allow all: whatever makes the model goes through; what leaves the project still waits.
        out = outside(tool, tool_input if isinstance(tool_input, dict) else {}, root)
        if not out:
            return "allow", "allow all is on in Kiln Studio"
        reason = out
    if decision == "defer" and env.get("KILN_APPROVALS") == "auto" and not PAID.match(tool):
        # Auto: Claude Code's auto mode decides the rest; only what can spend money waits here.
        return None, "auto mode decides"
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
    if decision is None:
        sys.exit(0)   # no decision: the permission mode's own
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
