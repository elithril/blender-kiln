"""Run whole labels unattended, one session at a time, and survive the night.

    BENCH_PLUGIN_DIR=<checkout> nohup python3 bench/drive.py v220-ahujasid:ahujasid v220-lab:lab \
        >/dev/null 2>&1 &

Each argument is <label>:<mcp>. For each label in turn, every enabled brief of briefs.json
goes through run.py, one at a time (one Blender, one port). Resumable: a brief that already
has a result.json under its label is skipped, so starting the driver again carries on
where it stopped.

- Log: bench/runs/_driver.log (one line per event); run.py's own output in
  bench/runs/<label>/_run-<brief>.log.
- Stop after the current brief: `touch bench/runs/_driver.stop`. Stop now: `kill <pid>`
  (bench/runs/_driver.pid) — the brief in progress is lost, rerun it by starting again
  (delete its folder first if it left a partial one without result.json: run.py starts clean).
- Port 9876 taken (someone opened their own Blender MCP): wait, never drive it.
- The subscription's usage limit ends a session early with an error. That run is not a
  measurement: its folder moves to bench/runs/_aborted/, the driver waits and runs the brief
  again. Any other failure is a result — kept as the baseline recorded it. The limit is read
  off the transcript's result event (api_error_status 429, api_error usage_limit_reached),
  not only the text: on 16 Oct "You've hit your session limit · resets 7:20pm" got past the
  text pattern and 28 sessions were recorded as results. The wait lasts until the reset the
  rate-limit event announces (resetsAt), 5 min past it, or LIMIT_WAIT_S when none is given.
- Memory: a brief starts only with BENCH_MIN_FREE_RIG % free (character briefs, default 40) or
  BENCH_MIN_FREE % (others, default 25); below, the driver waits and logs "memory low".
- BENCH_SKIP=<id>[,<id>]: leave those briefs for a later start (the label stays resumable).
- Every session gets BENCH_TIMEOUT_S (default here 5400 s, recorded in result.json): the
  rig and print briefs run longer than the first six.
"""
import json, os, re, shutil, socket, subprocess, sys, time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
RUNS = BENCH / "runs"
LOG, PID, STOP = RUNS / "_driver.log", RUNS / "_driver.pid", RUNS / "_driver.stop"
PORT = 9876
LIMIT = re.compile(r"usage limit|limit reached|hit your (?:\w+ )?limit|rate[ _-]?limit|"
                   r"too many requests|\b429\b|resets? (?:at |in )?\d|out of (?:extra )?usage", re.I)
FATAL = re.compile(r"not logged in|please run /login|invalid api key|credit balance", re.I)
LIMIT_WAIT_S = int(os.environ.get("BENCH_LIMIT_WAIT_S", "1800"))
MAX_LIMIT_WAITS = 96            # two days of half-hours
MAX_FAILS = 3                   # run.py dying before a result.json (Blender, sandbox, …)


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


# Free memory before a brief starts (macOS memory_pressure). A rig brief runs SkinTokens, ~7 GB per
# mesh, next to Blender: on 2026-10-21 a session killed for memory voided its run. Below the floor
# the driver waits, a minute at a time, and logs it once.
MIN_FREE = {"character": int(os.environ.get("BENCH_MIN_FREE_RIG", "40")),
            "default": int(os.environ.get("BENCH_MIN_FREE", "25"))}


def free_memory_pct():
    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"free percentage:\s*(\d+)%", out)
    return int(m.group(1)) if m else None


def port_open():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("localhost", PORT)) == 0


def transcript_limit(outdir):
    """(limit hit, reset epoch or None) from the transcript's events: the result's API error,
    and the last rate-limit event's reset time."""
    hit, reset = False, None
    try:
        lines = (outdir / "transcript.jsonl").read_text(errors="ignore").splitlines()
    except OSError:
        return False, None
    for line in lines:
        if '"rate_limit' not in line and '"result"' not in line and '"api_error' not in line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        info = ev.get("rate_limit_info")
        if isinstance(info, dict) and info.get("status") == "rejected" and info.get("resetsAt"):
            reset = info["resetsAt"]
        if ev.get("api_error_status") == 429 or ev.get("api_error") == "usage_limit_reached" \
                or (ev.get("terminal_reason") == "api_error" and ev.get("num_turns", 0) <= 1):
            hit = True
    for m in re.finditer(r'"resetsAt":\s*(\d+)', "\n".join(lines[-50:])):
        reset = reset or int(m.group(1))
    return hit, reset


def limit_hit(outdir):
    """(limit hit, fatal, reset epoch or None): the session ended on the subscription's limit,
    or on a login problem, not on the task."""
    try:
        r = json.loads((outdir / "result.json").read_text())
    except (OSError, json.JSONDecodeError):
        return False, False, None
    err = (outdir / "claude.err").read_text(errors="ignore") if (outdir / "claude.err").exists() else ""
    text = (r.get("final_text") or "") + "\n" + err[-4000:]
    if FATAL.search(text):
        return False, True, None
    errored = r.get("is_error") or r.get("claude_exit") not in (0, "timeout")
    hit, reset = transcript_limit(outdir)
    return bool(hit or (errored and LIMIT.search(text))), False, reset


def limit_wait(reset):
    """Seconds to wait: until 5 min past the announced reset, else LIMIT_WAIT_S."""
    if reset:
        return int(min(max(reset - time.time() + 300, 300), 6 * 3600))
    return LIMIT_WAIT_S


def stopping():
    if STOP.exists():
        log("stop file found — stopping before the next brief")
        STOP.unlink()
        return True
    return False


def main():
    pairs = [a.split(":", 1) for a in sys.argv[1:]]
    if not pairs or any(len(p) != 2 or p[1] not in ("ahujasid", "lab") for p in pairs):
        sys.exit(__doc__)
    RUNS.mkdir(exist_ok=True)
    PID.write_text(str(os.getpid()))
    os.environ.setdefault("BENCH_TIMEOUT_S", "5400")
    # BENCH_SKIP=id,id: briefs left for a later start of the same label (ai-mushrooms when the day's
    # free ZeroGPU quota is spent: a run on an empty quota measures the quota, not the skill).
    skip = {x.strip() for x in os.environ.get("BENCH_SKIP", "").split(",") if x.strip()}
    briefs = [b for b in json.loads((BENCH / "briefs.json").read_text())["briefs"]
              if not b.get("disabled") and b["id"] not in skip]
    log(f"driver {os.getpid()} start: {sys.argv[1:]} plugin={os.environ.get('BENCH_PLUGIN_DIR', '(this checkout)')} "
        f"timeout={os.environ['BENCH_TIMEOUT_S']}s briefs={len(briefs)}" + (f" skip={sorted(skip)}" if skip else ""))
    for label, mcp in pairs:
        for b in briefs:
            outdir = RUNS / label / b["id"]
            if (outdir / "result.json").exists():
                continue
            # run.py skips it too, without a result.json: counted here, it would be 3 failures.
            plugin = Path(os.environ.get("BENCH_PLUGIN_DIR", BENCH.parent))
            if b.get("kind") == "studio" and not (plugin / "plugin" / "studio" / "studio.py").is_file():
                log(f"skip  {label} / {b['id']}: the skill under test has no Kiln Studio")
                continue
            fails = waits = 0
            while True:
                if stopping():
                    return
                if port_open():
                    log(f"port {PORT} taken — waiting (another Blender MCP is open)")
                    while port_open():
                        time.sleep(300)
                    log(f"port {PORT} free again")
                floor = MIN_FREE.get(b.get("kind"), MIN_FREE["default"])
                free = free_memory_pct()
                if free is not None and free < floor:
                    log(f"memory low — waiting: {free}% free, {b['id']} needs {floor}%")
                    while (free := free_memory_pct()) is not None and free < floor:
                        if stopping():
                            return
                        time.sleep(60)
                    log(f"memory ok again: {free}% free")
                if outdir.exists() and not (outdir / "result.json").exists():
                    shutil.rmtree(outdir)          # a partial folder from a killed run
                log(f"run   {label} / {b['id']} (mcp={mcp})")
                (RUNS / label).mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                with open(RUNS / label / f"_run-{b['id']}.log", "a") as out:
                    rc = subprocess.run([sys.executable, str(BENCH / "run.py"), label, b["id"]],
                                        env=dict(os.environ, BENCH_MCP=mcp), stdout=out,
                                        stderr=subprocess.STDOUT).returncode
                mins = round((time.time() - t0) / 60, 1)
                if not (outdir / "result.json").exists():
                    fails += 1
                    log(f"FAIL  {label} / {b['id']}: run.py exit {rc} after {mins} min, no result.json "
                        f"({fails}/{MAX_FAILS}) — see {label}/_run-{b['id']}.log")
                    if fails >= MAX_FAILS:
                        log(f"give up {label} / {b['id']}")
                        break
                    time.sleep(60)
                    continue
                hit, fatal, reset = limit_hit(outdir)
                if fatal:
                    log(f"FATAL {label} / {b['id']}: authentication problem — driver stops; nothing else will run")
                    dest = RUNS / "_aborted" / label / f"{b['id']}-{time.strftime('%Y%m%d-%H%M%S')}"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(outdir), dest)
                    return
                if hit:
                    waits += 1
                    dest = RUNS / "_aborted" / label / f"{b['id']}-{time.strftime('%Y%m%d-%H%M%S')}"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(outdir), dest)
                    wait = limit_wait(reset)
                    until = time.strftime("%H:%M", time.localtime(time.time() + wait))
                    log(f"LIMIT {label} / {b['id']} after {mins} min — moved to {dest.relative_to(RUNS)}, "
                        f"waiting {wait // 60} min, until {until} ({waits}/{MAX_LIMIT_WAITS})")
                    if waits >= MAX_LIMIT_WAITS:
                        log("too many limit waits — driver stops")
                        return
                    for _ in range(wait // 30):        # the stop file is still honoured while waiting
                        if STOP.exists():
                            break
                        time.sleep(30)
                    continue
                r = json.loads((outdir / "result.json").read_text())
                log(f"done  {label} / {b['id']}: exit={r.get('claude_exit')} turns={r.get('num_turns')} "
                    f"wall={round((r.get('wall_s') or 0) / 60, 1)} min finals={r.get('finals')} "
                    f"cost≈${r.get('cost_usd_equiv')}")
                break
    log("driver finished: every brief of every label has a result.json (or was given up — see above)")


if __name__ == "__main__":
    try:
        main()
    finally:
        if PID.exists() and PID.read_text().strip() == str(os.getpid()):
            PID.unlink()
