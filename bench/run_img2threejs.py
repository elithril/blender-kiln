"""Run img2threejs on the bench's reference images, export, and measure like kiln.

    python3 bench/run_img2threejs.py <label> [ref-id ...]      # ids from briefs.json with a "reference"

Same conditions as run.py where they can be the same: one headless session per
reference, no user settings, permissions bypassed, the same reference image and
the same fidelity instruction. What cannot be the same is the output — code, not
a file — so the bench exports it itself: the session writes src/model.ts in a
shared host project, and bench/img2threejs_host/export_glb.mjs turns it into a
GLB through Three.js's GLTFExporter. Then measure.py and render.py, unchanged.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
HOST = BENCH / "img2threejs_host"
SKILL = Path(os.environ.get("BENCH_IMG2_DIR", BENCH / "runs" / "_deps" / "img2threejs"))
REFS = BENCH / "runs" / "_refs"
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
MODEL = os.environ.get("BENCH_MODEL", "claude-opus-5-5")
TIMEOUT_S = int(os.environ.get("BENCH_TIMEOUT_S", "3600"))

PROMPT = """/img2threejs Rebuild the object in reference.png as a procedural Three.js model.

Match the reference's proportions, parts, materials and colours as closely as you can.
Write the factory to src/model.ts, exporting `createModel(): THREE.Group`. Use 1 unit =
1 metre, with the object standing on y = 0.

The host project in this folder is ready (three 0.180, vite, TypeScript, node_modules
installed). `npx vite --port <free port>` serves it; `src/main.ts` frames and lights
whatever createModel() returns. For your side-by-side reviews, capture the render with
`npx playwright screenshot --wait-for-timeout 3000 http://localhost:<port>/ shot.png`.

Work autonomously and do not ask questions: this is a non-interactive run."""


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def tool_stats(path):
    calls = {}
    for line in path.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    calls[b["name"]] = calls.get(b["name"], 0) + 1
    return calls


def run_one(brief, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / "work"
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(HOST, work, ignore=shutil.ignore_patterns("node_modules", "dist"))
    (work / "node_modules").symlink_to(HOST / "node_modules")
    shutil.copy(REFS / brief["reference"], work / "reference.png")
    skills = work / ".claude" / "skills"
    skills.mkdir(parents=True)
    shutil.copytree(SKILL, skills / "img2threejs", ignore=shutil.ignore_patterns(".git"))
    placeholder = (work / "src" / "model.ts").read_text()

    t0 = time.time()
    with open(outdir / "transcript.jsonl", "w") as tr, open(outdir / "claude.err", "w") as err:
        try:
            r = subprocess.run(
                ["claude", "-p", PROMPT, "--strict-mcp-config", "--setting-sources", "project",
                 "--permission-mode", "bypassPermissions", "--model", MODEL,
                 "--no-session-persistence", "--output-format", "stream-json", "--verbose"],
                cwd=work, stdout=tr, stderr=err, timeout=TIMEOUT_S)
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    wall = round(time.time() - t0, 1)
    subprocess.run(["pkill", "-f", f"vite.*{work}"], capture_output=True)

    result = {}
    for line in (outdir / "transcript.jsonl").read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            result = ev
    usage = result.get("usage", {})
    session = {
        "brief": brief["id"], "tool": "img2threejs",
        "img2threejs": sh(["git", "-C", str(SKILL), "rev-parse", "--short", "HEAD"]).stdout.strip(),
        "blender": sh([BLENDER, "--version"]).stdout.splitlines()[0],
        "claude_exit": code, "wall_s": wall, "is_error": result.get("is_error"),
        "num_turns": result.get("num_turns"), "cost_usd_equiv": result.get("total_cost_usd"),
        "output_tokens": usage.get("output_tokens"),
        "tool_calls": tool_stats(outdir / "transcript.jsonl"),
        "final_text": (result.get("result") or "")[-2000:],
        "model_ts_written": (work / "src" / "model.ts").read_text() != placeholder,
        "model_ts_lines": len((work / "src" / "model.ts").read_text().splitlines()),
        "measures": [],
    }

    glb = work / f"{brief['id']}_final.glb"
    if session["model_ts_written"]:
        ex = sh(["node", str(HOST / "export_glb.mjs"), str(work), str(glb), str(outdir / "browser.png")],
                timeout=300)
        session["export"] = (ex.stdout + ex.stderr).strip()[-600:]
    else:
        session["export"] = "skipped: src/model.ts is still the placeholder"
    if glb.exists():
        m = sh([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                "--python", str(BENCH / "measure.py"), "--", str(glb)])
        line = next((l for l in m.stdout.splitlines() if l.startswith("BENCH_JSON ")), None)
        if m.returncode != 0 or line is None:
            session["measures"].append({"file": glb.name, "measure_error": (m.stdout + m.stderr)[-800:]})
        else:
            d = json.loads(line[len("BENCH_JSON "):])
            d["file"] = glb.name
            png = outdir / f"render-{glb.stem}.png"
            rr = sh([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                     "--python", str(BENCH / "render.py"), "--", str(glb), str(png)])
            d["render"] = png.name if rr.returncode == 0 else f"render failed: {rr.stdout[-400:]}"
            session["measures"].append(d)
    session["finals"] = len(session["measures"])
    (outdir / "result.json").write_text(json.dumps(session, indent=2))
    return session


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    label, only = sys.argv[1], set(sys.argv[2:])
    briefs = [b for b in json.loads((BENCH / "briefs.json").read_text())["briefs"] if b.get("reference")]
    unknown = only - {b["id"] for b in briefs}
    if unknown:
        sys.exit(f"unknown reference brief id(s): {sorted(unknown)}")
    for b in briefs:
        if only and b["id"] not in only:
            continue
        outdir = BENCH / "runs" / label / b["id"]
        if (outdir / "result.json").exists():
            print(f"skip {b['id']}: already measured under '{label}'")
            continue
        print(f"run  {b['id']} …", flush=True)
        s = run_one(b, outdir)
        print(f"     exit={s['claude_exit']} turns={s['num_turns']} wall={s['wall_s']}s "
              f"cost≈${s['cost_usd_equiv']} model.ts={s['model_ts_lines']} lines glb={s['finals']}", flush=True)


if __name__ == "__main__":
    main()
