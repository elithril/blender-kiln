"""What a session DID, read from its stream-json transcript — the half the shipped file cannot say.

    python3 bench/signals.py bench/runs/<label>/<brief>/transcript.jsonl

measure.py judges the file; this reads the route the session took to it: which rig route
ran, whether it looked at the skin in matcap, whether it proposed the photo projection and
ran it, what it said about a fused hand, which print_check verdicts it saw. Pure Python, no
Blender. Each signal comes from the session's own tool calls (code it ran, commands it
typed) or its own words — evidence that something was attempted, not that it was right;
the file measures say that.
"""
import json, re, sys

# Tool-call evidence, matched on the JSON of each tool_use input of a tool that RUNS or
# writes code (Bash, the Blender MCP's tools, Write/Edit) — reading a file names it without
# running it, so Read/Grep/Glob never count. A kiln tool counts only when executed.
def RUN(name):
    return (r"(?:--python\s+|python3?\s+(?:-I\s+)?|run_path\(|exec\(open\(|subprocess[^\n]{0,300}?)"
            r"['\"]?[^\s'\"]*" + re.escape(name))


CALLS = {
    "autorig": RUN("autorig.py"),
    "rigify": r"rigify_generate|module=.rigify|metarig",
    "quadruped": RUN("quadruped.py"),
    "auto_weights": r"ARMATURE_AUTO|ARMATURE_ENVELOPE",
    "scripted_armature": r"armature_add|armatures\.new|edit_bones\.new",
    "unimate": RUN("unimate.py"),
    "motion_loop": RUN("motion_loop.py"),
    "matcap": r"matcap",
    "photo_project": RUN("photo_project.py"),
    "fidelity_check": RUN("fidelity_check.py"),
    "print_check": RUN("print_check.py"),
    "fit_coupon": RUN("fit_coupon.py"),
    "decimate": r"DECIMATE",
    "voxel_remesh": r"voxel_size|'VOXEL'|\"VOXEL\"",
}
NOT_RUN = {"Read", "Grep", "Glob", "LS", "WebFetch", "WebSearch", "TodoWrite", "Task", "Agent",
           "Skill", "ToolSearch", "NotebookRead"}
# The session's own words: what it offered the user.
PROPOSE_PROJECTION = re.compile(
    r"photo[_ ]project|photo projection|project(?:ing)? the (?:photo|reference)(?:'s)?(?: own)? markings"
    r"|(?:photo|reference)'s (?:own )?markings|projet(?:er|ion) (?:de )?la photo", re.I)
FUSED_HAND = re.compile(
    r"(?:fused|mitten|webbed|stuck together|merged|blob|single mass|no (?:separate )?fingers)"
    r"[^.\n]{0,80}(?:hand|finger)|(?:hand|finger)s?[^.\n]{0,80}"
    r"(?:fused|mitten|webbed|stuck together|merged|blob|single mass)", re.I)
VERDICT = re.compile(r"VERDICT (PASS|FAIL)")


def events(path):
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text", c.get("content", ""))) if isinstance(c, dict) else str(c)
                         for c in content)
    return ""


def flat(x):
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return "\n".join(flat(v) for v in x.values())
    if isinstance(x, list):
        return "\n".join(flat(v) for v in x)
    return ""


def excerpts(rx, texts, n=3, width=220):
    out = []
    for t in texts:
        for m in rx.finditer(t):
            a = max(0, m.start() - 60)
            out.append(re.sub(r"\s+", " ", t[a:a + width]).strip())
            if len(out) >= n:
                return out
    return out


def signals(path, final_text=""):
    calls = {k: 0 for k in CALLS}
    said, results = [], []
    for ev in events(path):
        msg = ev.get("message", {}) if isinstance(ev.get("message"), dict) else {}
        for block in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
            if ev.get("type") == "assistant" and block.get("type") == "tool_use":
                if block.get("name") in NOT_RUN:
                    continue
                text = flat(block.get("input", {}))     # the code and commands as typed
                for k, rx in CALLS.items():
                    if re.search(rx, text, re.I):
                        calls[k] += 1
            elif ev.get("type") == "assistant" and block.get("type") == "text":
                said.append(block.get("text", ""))
            elif ev.get("type") == "user" and block.get("type") == "tool_result":
                results.append(_text(block.get("content")))
    if final_text:
        said.append(final_text)

    if calls["autorig"]:
        route = "autorig (SkinTokens)"
    elif calls["rigify"]:
        route = "rigify"
    elif calls["scripted_armature"] or calls["auto_weights"]:
        route = "scripted armature"
    else:
        route = None
    verdicts = [m.group(1) for r in results for m in VERDICT.finditer(r)]
    proposed = excerpts(PROPOSE_PROJECTION, said)
    tail = (final_text or "").strip()
    return {
        "calls": calls,
        "rig_route": route,
        "quadruped_tool": calls["quadruped"] > 0,
        "matcap_check": calls["matcap"] > 0,
        "projection": {"proposed": bool(proposed), "ran": calls["photo_project"] > 0, "said": proposed},
        "fused_hand": {"mentions": len(excerpts(FUSED_HAND, said, n=99)), "said": excerpts(FUSED_HAND, said)},
        "print_check": {"runs": calls["print_check"], "verdicts": verdicts,
                        "last": verdicts[-1] if verdicts else None},
        # A headless session that asks a question ends there: nobody answers it.
        "ended_on_question": tail.endswith("?") or bool(re.search(r"\?\s*\**\s*$", tail)),
    }


if __name__ == "__main__":
    print(json.dumps(signals(sys.argv[1]), indent=2))
