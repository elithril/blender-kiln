"""Does the skill fire when it should, and only then? Measure it.

    python3 bench/trigger.py <label>            # BENCH_PLUGIN_DIR picks the skill under test

A skill is chosen from its frontmatter `description` before anything else is
read, so that one sentence decides whether kiln exists for a user. Each prompt
below runs in its own headless session — no user settings, no MCP server, cut
after two turns — and the transcript says whether the Skill tool was called
with kiln. Results: bench/runs/<label>/trigger.json.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parent
PLUGIN = Path(os.environ.get("BENCH_PLUGIN_DIR", BENCH.parent)).resolve()
MODEL = os.environ.get("BENCH_MODEL", "claude-opus-5-5")

# (prompt, should kiln fire?). Written as users write, not as the description does:
# a test phrased in the description's own words only proves it can read itself.
PROMPTS = [
    ("I need a low-poly treasure chest for my three.js game, as a GLB file.", True),
    ("Make me a 3D model of a wooden barrel I can drop into Unity.", True),
    ("génère un asset 3D d'une lanterne médiévale pour mon jeu web", True),
    ("This .glb is 40 MB, can you shrink it for the web without wrecking it?", True),
    ("Rig this humanoid mesh in Blender so I can animate it.", True),
    ("Convert my model.glb to USDZ for AR Quick Look on iPhone.", True),
    ("Find me a free CC0 table model and get it into Blender, cleaned up.", True),
    ("I want 20 props for a sci-fi corridor, all in the same style, exported for the web.", True),
    ("Write a Python function that parses a CSV file and returns a list of dicts.", False),
    ("Design a flat 2D logo for my bakery as an SVG.", False),
    ("Set up a React component with a three.js canvas and orbit controls.", False),
    ("Explain the difference between git merge and git rebase.", False),
]

# Held out: written BEFORE any new description was drafted, and never used to
# tune one. A description is only better if it also improves here — otherwise
# the test just proves it answers the questions it was written against.
HELD_OUT = [
    ("Can you make a stylized sword for my Godot game? I'll need it as a glTF.", True),
    ("My FBX has flipped normals and floats above the ground in Unreal. Can you fix it in Blender?", True),
    ("These procedural Blender materials turn grey when I export to glTF, sort it out.", True),
    ("Generate LODs for this 80k-triangle rock mesh for a web viewer.", True),
    ("Write a GLSL fragment shader for animated water.", False),
    ("Help me write a cover letter for a junior game designer job.", False),
]


def fired(transcript):
    for line in transcript.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "assistant":
            continue
        for b in ev.get("message", {}).get("content", []):
            if b.get("type") == "tool_use" and b.get("name") == "Skill" \
                    and "kiln" in json.dumps(b.get("input", {})):
                return True
    return False


def main():
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] not in ("--held-out", "--all")):
        sys.exit(__doc__ + "\n    add --held-out to run only the held-out set, --all for both")
    mode = sys.argv[2] if len(sys.argv) == 3 else "--main"
    prompts = {"--main": PROMPTS, "--held-out": HELD_OUT, "--all": PROMPTS + HELD_OUT}[mode]
    out = BENCH / "runs" / sys.argv[1]
    out.mkdir(parents=True, exist_ok=True)
    rows, cost = [], 0.0
    for prompt, expect in prompts:
        with tempfile.TemporaryDirectory() as work:     # outside any git checkout
            r = subprocess.run(
                ["claude", "-p", prompt, "--plugin-dir", str(PLUGIN),
                 "--strict-mcp-config", "--setting-sources", "project",
                 "--permission-mode", "bypassPermissions", "--max-turns", "2",
                 "--model", MODEL, "--no-session-persistence",
                 "--output-format", "stream-json", "--verbose"],
                cwd=work, capture_output=True, text=True, timeout=600)
        got = fired(r.stdout)
        res = {}
        for l in r.stdout.splitlines():
            try:
                ev = json.loads(l)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "result":
                res = ev
        cost += res.get("total_cost_usd") or 0
        rows.append({"prompt": prompt, "expect": expect, "fired": got, "ok": got == expect})
        print(f"{'ok  ' if got == expect else 'MISS'} fired={got!s:5} expect={expect!s:5} {prompt[:70]}", flush=True)
    tp = sum(r["fired"] and r["expect"] for r in rows)
    fp = sum(r["fired"] and not r["expect"] for r in rows)
    summary = {"plugin": str(PLUGIN), "model": MODEL, "set": mode, "rows": rows,
               "recall": f"{tp}/{sum(r['expect'] for r in rows)}",
               "false_positives": f"{fp}/{sum(not r['expect'] for r in rows)}",
               "cost_usd_equiv": round(cost, 2)}
    (out / f"trigger{'' if mode == '--main' else mode.replace('--', '-')}.json").write_text(json.dumps(summary, indent=2))
    print(f"\nrecall {summary['recall']} · false positives {summary['false_positives']} · ≈${summary['cost_usd_equiv']}")


if __name__ == "__main__":
    main()
