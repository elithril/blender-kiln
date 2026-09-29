"""Run the skill on the fixed briefs, headless, and measure what it ships.

    python3 bench/run.py <label> [brief-id ...]      # e.g. baseline, or lot2-trellis

For each brief: a fresh Blender on a throwaway profile, the MCP server pinned,
one `claude -p` session with the plugin loaded from this checkout and nothing
from the user's own settings, then bench/measure.py on every *_final.glb the
session left behind. Results land in bench/runs/<label>/<brief-id>/.

Nothing here decides pass or fail: report.py compares two labels.
"""
import json, os, shutil, socket, subprocess, sys, time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
REPO = BENCH.parent
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
MCP_VERSION = os.environ.get("BENCH_MCP_VERSION", "2.0.0")
MODEL = os.environ.get("BENCH_MODEL", "claude-opus-5-5")
TIMEOUT_S = int(os.environ.get("BENCH_TIMEOUT_S", "3600"))
PORT = 9876


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r.stdout


def bundled_addon():
    """The addon that ships inside the pinned server package, so both halves match."""
    out = sh(["uvx", "--from", f"blender-mcp=={MCP_VERSION}", "python", "-c",
              "import blender_mcp, os; print(os.path.join(os.path.dirname(blender_mcp.__file__), 'bundled', 'addon.py'))"])
    p = Path(out.strip().splitlines()[-1])
    if not p.is_file():
        sys.exit(f"no bundled addon in blender-mcp {MCP_VERSION}: {p}")
    return p


def port_open():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("localhost", PORT)) == 0


def start_blender(profile, log):
    if port_open():
        sys.exit(f"port {PORT} is already taken — close the other Blender first, "
                 "or the session would drive the wrong one")
    (profile / "scripts" / "addons").mkdir(parents=True, exist_ok=True)
    shutil.copy(bundled_addon(), profile / "scripts" / "addons" / "blender_mcp.py")
    env = dict(os.environ,
               BLENDER_USER_SCRIPTS=str(profile / "scripts"),
               BLENDER_USER_CONFIG=str(profile / "config"),
               BLENDER_USER_EXTENSIONS=str(profile / "extensions"),
               BLENDER_USER_DATAFILES=str(profile / "datafiles"))
    # GUI, not --background: get_viewport_screenshot needs a viewport, and
    # rule 2 calls it after every change.
    proc = subprocess.Popen([BLENDER, "--factory-startup", "--python-exit-code", "1",
                             "--python", str(BENCH / "blender_start.py")],
                            env=env, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(120):
        if port_open():
            return proc
        if proc.poll() is not None:
            sys.exit(f"Blender exited ({proc.returncode}) before serving — see {log.name}")
        time.sleep(0.5)
    proc.kill()
    sys.exit(f"Blender never opened port {PORT} — see {log.name}")


def tool_stats(transcript):
    """Tool calls by name, from the stream-json transcript."""
    calls = {}
    for line in transcript.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "assistant":
            continue
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                calls[block["name"]] = calls.get(block["name"], 0) + 1
    return calls


def skill_fingerprint():
    """Hash of every tracked file. The session's work folder sits inside this
    checkout and permissions are bypassed, so nothing but this stops a session
    from editing the skill it is being measured on."""
    return sh(["git", "-C", str(REPO), "ls-files", "-s"]) + sh(["git", "-C", str(REPO), "diff", "HEAD"])


def run_brief(brief, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / "work"
    work.mkdir(exist_ok=True)
    (outdir / "mcp.json").write_text(json.dumps({"mcpServers": {"blender": {
        "command": "uvx", "args": [f"blender-mcp=={MCP_VERSION}"]}}}))

    before = skill_fingerprint()
    with open(outdir / "blender.log", "w") as blog:
        blender = start_blender(outdir / "profile", blog)
        t0 = time.time()
        try:
            with open(outdir / "transcript.jsonl", "w") as tr, open(outdir / "claude.err", "w") as err:
                prompt = (brief["prompt"] + f"\n\nOutput folder (absolute): {work / 'generated-assets'}")
                r = subprocess.run(
                    ["claude", "-p", prompt,
                     "--plugin-dir", str(REPO),
                     "--mcp-config", str(outdir / "mcp.json"), "--strict-mcp-config",
                     "--setting-sources", "project",
                     "--permission-mode", "bypassPermissions",
                     "--model", MODEL,
                     "--no-session-persistence",
                     "--output-format", "stream-json", "--verbose"],
                    cwd=work, stdout=tr, stderr=err, timeout=TIMEOUT_S)
                code = r.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
        finally:
            wall = round(time.time() - t0, 1)
            blender.terminate()
            try:
                blender.wait(20)
            except subprocess.TimeoutExpired:
                blender.kill()

    if skill_fingerprint() != before:
        sys.exit(f"{brief['id']}: the session modified tracked files of the repository — "
                 "the measurement is void. See `git status` before anything else.")

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
        "brief": brief["id"],
        "claude_exit": code,
        "wall_s": wall,
        "is_error": result.get("is_error"),
        "num_turns": result.get("num_turns"),
        "duration_ms": result.get("duration_ms"),
        # Equivalent API price as the CLI reports it. On a subscription it is not
        # billed; it is the only comparable measure of how much quota a run eats.
        "cost_usd_equiv": result.get("total_cost_usd"),
        "output_tokens": usage.get("output_tokens"),
        "input_tokens_total": sum(usage.get(k) or 0 for k in
                                  ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
        "tool_calls": tool_stats(outdir / "transcript.jsonl"),
        "final_text": (result.get("result") or "")[-2000:],
    }

    finals = sorted((work).rglob("*_final.glb"))
    measures = []
    for glb in finals:
        m = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                            "--python", str(BENCH / "measure.py"), "--", str(glb)],
                           capture_output=True, text=True)
        line = next((l for l in m.stdout.splitlines() if l.startswith("BENCH_JSON ")), None)
        if m.returncode != 0 or line is None:
            # Fail loud: a GLB we could not measure is a finding, not a gap to skip.
            measures.append({"file": str(glb.relative_to(work)), "measure_error": m.stdout[-800:] + m.stderr[-800:]})
        else:
            d = json.loads(line[len("BENCH_JSON "):])
            d["file"] = str(glb.relative_to(work))
            png = outdir / f"render-{glb.stem}.png"
            rr = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                                 "--python", str(BENCH / "render.py"), "--", str(glb), str(png)],
                                capture_output=True, text=True)
            d["render"] = png.name if rr.returncode == 0 else f"render failed: {rr.stdout[-400:]}"
            measures.append(d)
    session["finals"] = len(finals)
    session["measures"] = measures
    (outdir / "result.json").write_text(json.dumps(session, indent=2))
    return session


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    label, only = sys.argv[1], set(sys.argv[2:])
    briefs = json.loads((BENCH / "briefs.json").read_text())["briefs"]
    unknown = only - {b["id"] for b in briefs}
    if unknown:
        sys.exit(f"unknown brief id(s): {sorted(unknown)}")
    for b in briefs:
        if only and b["id"] not in only:
            continue
        outdir = BENCH / "runs" / label / b["id"]
        if (outdir / "result.json").exists():
            print(f"skip {b['id']}: already measured under '{label}' (delete the folder to rerun)")
            continue
        print(f"run  {b['id']} …", flush=True)
        s = run_brief(b, outdir)
        print(f"     exit={s['claude_exit']} turns={s['num_turns']} wall={s['wall_s']}s "
              f"cost≈${s['cost_usd_equiv']} finals={s['finals']}", flush=True)


if __name__ == "__main__":
    main()
