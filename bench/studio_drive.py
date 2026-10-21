"""The Kiln Studio brief: a note written in the page, handled by Studio's own Claude worker.

run.py calls run_studio_brief() for a brief of kind "studio". The session under test is not a
`claude -p` the bench starts: it is the one Studio's worker starts when the user presses
"Work on it with Claude" — its own Blender, its own MCP config, its approval hook. The bench
plays the user:

1. a project in the sandbox holding the brief's fixture (a model kiln made, with its log);
2. Studio served from the sandbox's copy of the skill, the worker on, on the bench's model;
3. the page (studio_page.py, headless Chromium): pin the note on the named object, save it,
   press "Work on it with Claude";
4. while it works: a tool call the hook holds back is allowed if free, denied if it can spend
   money (rule 5) — each one recorded; a proposal gets the brief's standing answer, sent as the
   page's Accept sends it. Approvals go through the page's own endpoint, not a click;
5. Studio stopped (its worker stops its Blender), then measured: the named object before and
   after, every other object unchanged, the note answered, a new version exported.

Every `claude` the worker starts goes through a tee into transcript.jsonl, so the transcript
signals, the sandbox audit and the tool counts are the same as for every other brief.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from urllib.parse import quote
from pathlib import Path

import run as R

# The approval hook's own test for paid generation (plugin/studio/approval_hook.py).
PAID = re.compile(r"^mcp__blender__(generate_|poll_|import_generated_asset)")
PLAYWRIGHT = "playwright==1.64.0"
# Studio's worker Blender: never 9876 (the bench's and the user's), never 9877 (Studio's
# default, which a Studio already open on this Mac may be serving).
WORKER_PORT = int(os.environ.get("BENCH_STUDIO_BLENDER_PORT", "9879"))
POLL_S = 3


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def api(base, path, body=None, timeout=30):
    req = urllib.request.Request(base + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


class Page:
    """studio_page.py in its own uvx environment, open for the whole run like a user's page."""

    def __init__(self, base, asset, obj, text, shots):
        self.stop = shots / ".stop"
        self.stop.unlink(missing_ok=True)
        self.proc = subprocess.Popen(["uvx", "--with", PLAYWRIGHT, "python", "-I", str(R.BENCH / "studio_page.py"),
                                      base, asset, obj, text, str(shots), str(self.stop)],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.tail = []

    def _line(self, tag):
        for line in self.proc.stdout:   # the script has its own timeouts: it always prints or ends
            if line.startswith(tag + " "):
                return json.loads(line[len(tag) + 1:])
            self.tail = (self.tail + [line])[-30:]
        return {"error": "".join(self.tail)[-1500:] or f"studio_page.py ended without {tag}"}

    def noted(self):
        return self._line("STUDIO_PAGE")

    def close(self):
        if self.proc.poll() is not None:
            return {"error": "the page had already closed"}
        self.stop.touch()
        out = self._line("STUDIO_PAGE_AFTER")
        try:
            self.proc.wait(60)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.stop.unlink(missing_ok=True)
        return out


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else None


def judge(spec, before, after):
    """The note's change on the named object, and nothing else moved."""
    name, out = spec["object"], {}
    b, a = before.get(name), after.get(name)
    if a is None:   # renamed on export: the one new name that starts with it
        alt = [k for k in after if k.startswith(name) and k not in before]
        a = after[alt[0]] if len(alt) == 1 else None
        out["object_found_as"] = alt[0] if len(alt) == 1 else None
    if b is None or a is None:
        return {**out, "verdict": "FAIL", "why": f"{name} missing {'before' if b is None else 'after'}"}
    ratios = [round(a["size"][i] / b["size"][i], 3) for i in range(3) if b["size"][i] > 1e-6]
    scale = statistics.median(ratios)
    want, tol = spec["scale"], spec.get("tolerance", 0.15)
    out.update(ratios=ratios, scale=round(scale, 3), scale_ok=abs(scale - want) / want <= tol)
    moved = {}
    for k, v in before.items():
        if k == name:
            continue
        w = after.get(k)
        if w is None:
            moved[k] = "missing after"
            continue
        d = max(abs(v[e][i] - w[e][i]) for e in ("min", "max") for i in range(3))
        if d > spec.get("others_mm", 2.0) / 1000:
            moved[k] = round(d * 1000, 1)
    out["others_moved_mm"] = moved
    if spec.get("attached_to"):
        r = after.get(spec["attached_to"])
        # Touching: the object's bottom no higher than the other's top (+ 2 mm), in Blender Z.
        out["gap_mm"] = None if r is None else round((a["min"][2] - r["max"][2]) * 1000, 1)
        out["attached"] = r is not None and out["gap_mm"] <= 2.0
    ok = out["scale_ok"] and not moved and out.get("attached", True)
    out["verdict"] = "PASS" if ok else "FAIL"
    return out


def run_studio_brief(brief, outdir):
    st = brief["studio"]
    outdir.mkdir(parents=True, exist_ok=True)
    box, refs, skill, work = R.sandbox_for(brief, outdir)
    studio_py = skill / "studio" / "studio.py"
    if not studio_py.is_file():
        sys.exit(f"{brief['id']}: the skill under test has no Studio ({studio_py}) — this brief is 3.0 and later")
    if port_open(WORKER_PORT) or port_open(R.PORT):
        sys.exit(f"{brief['id']}: port {WORKER_PORT} or {R.PORT} is taken — another Blender would be driven")

    # 1. The project: the fixture where kiln would have left it, its log pointing here.
    fixture = R.BENCH / "fixtures" / st["fixture"]
    name = fixture.name
    dst = work / "generated-assets" / name
    shutil.copytree(fixture, dst)
    log = dst / f"{name}_log.md"
    if log.is_file():
        log.write_text(re.sub(r"(?m)^- Output: .*$", f"- Output: {dst}", log.read_text()))
    final = dst / "web" / f"{name}_final.glb"
    shutil.copy2(final, outdir / "before.glb")
    before_hash = sha(final)

    # Every claude the worker starts: through a tee into the transcript.
    transcript = outdir / "transcript.jsonl"
    transcript.write_text("")
    tee = outdir / "claude-tee.sh"
    # Only the sessions (-p): `claude auth status`, which the worker runs first, prints the account's
    # email, and transcripts can be published.
    claude = os.environ.get("BENCH_STUDIO_CLAUDE_BIN") or shutil.which("claude")   # a fake one, for test runs
    tee.write_text(f'#!/bin/sh\ncase " $* " in\n  *" -p "*) "{claude}" "$@" | /usr/bin/tee -a "{transcript}" ;;\n'
                   f'  *) exec "{claude}" "$@" ;;\nesac\n')
    tee.chmod(0o755)

    cfg = [f"claude_worker=true", f"auto_open=false", f"blender_port={WORKER_PORT}",
           f"blender_mcp={'lab' if R.MCP == 'lab' else 'ahujasid'}", f"claude_model={R.MODEL}",
           "claude_approvals=ask", "claude_paid=ask"]
    R.sh([sys.executable, str(studio_py), "config", "--root", str(work), *cfg])
    env = dict(os.environ, KILN_STUDIO_CLAUDE=str(tee), BLENDER=R.BLENDER)
    if R.MCP == "lab":
        env["KILN_STUDIO_LAB_DIR"] = str(R.LAB_DIR)
    if R.MCP_VERSION != "2.2.2":
        print(f"note: Studio's worker pins its own MCP server, not BENCH_MCP_VERSION={R.MCP_VERSION}", flush=True)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    before_fp = R.skill_fingerprint()
    srv_log = open(outdir / "studio.log", "w")
    srv = subprocess.Popen([sys.executable, str(studio_py), "serve", str(work), "--port", str(port)],
                           cwd=work, env=env, stdout=srv_log, stderr=subprocess.STDOUT, start_new_session=True)
    rec = {"approvals": [], "proposals": [], "jobs": [], "page": {}}
    t0 = time.time()
    code, pg = 0, None
    try:
        for _ in range(60):
            try:
                api(base, "/api/hello", timeout=2)
                break
            except OSError:
                time.sleep(0.25)
        assets = api(base, "/api/assets")
        assets = assets["assets"] if isinstance(assets, dict) else assets
        asset = next(a["id"] for a in assets if a["id"].endswith(name))
        rec["asset"] = asset

        # 3. The user's gestures in the page.
        shots = outdir / "shots"
        pg = Page(base, asset, st["object"], st["note"], shots)
        rec["page"]["note"] = pg.noted()
        if rec["page"]["note"].get("error"):
            raise RuntimeError(f"the page: {rec['page']['note']['error'][:300]}")

        # 4. Until the worker has nothing left on this model.
        key, seen_done = f"asset:{asset}", False
        while time.time() - t0 < R.TIMEOUT_S:
            jobs = [j for j in api(base, "/api/claude")["jobs"] if j.get("key") == key]
            waiting = [j for j in jobs if j["state"] == "waiting" and not (j.get("waiting") or {}).get("answered")]
            for j in waiting:
                w = j["waiting"]
                if w.get("type") == "tool":
                    decision = "deny" if PAID.match(w.get("tool") or "") else "allow"
                    rec["approvals"].append({"tool": w.get("tool"), "input": str(w.get("input"))[:400],
                                             "decision": decision, "at_s": round(time.time() - t0)})
                    api(base, f"/api/claude/jobs/{j['id']}/answer", {"decision": decision})
                else:
                    answer = st.get("standing_answer", "Yes, go ahead.")
                    rec["proposals"].append({"question": w.get("question"), "answer": answer,
                                             "at_s": round(time.time() - t0)})
                    api(base, "/api/claude/jobs", {"kind": "answer", "asset": asset, "text": answer, "lang": "en"})
            busy = [j for j in jobs if j["state"] in ("queued", "running", "waiting")]
            if jobs and not busy:
                if seen_done:   # twice in a row: nothing was about to start
                    break
                seen_done = True
            else:
                seen_done = False
            time.sleep(POLL_S)
        else:
            code = "timeout"
        rec["jobs"] = [{k: j.get(k) for k in ("id", "kind", "state", "cost_usd", "turns", "duration_ms",
                                              "stop_reason", "error")}
                       for j in api(base, "/api/claude")["jobs"] if j.get("key") == key]
        rec["thread"] = api(base, f"/api/claude/thread?key={quote(key, safe='')}")["messages"][-60:]
        rec["detail"] = api(base, f"/api/asset/{quote(asset, safe='')}")
        rec["page"]["after"] = pg.close()
    except Exception as e:   # a run that cannot be driven is a finding, recorded, not a crash
        rec["error"] = f"{type(e).__name__}: {e}"
        code = "driver-error"
    finally:
        wall = round(time.time() - t0, 1)
        if pg and pg.proc.poll() is None:   # an error on the way: the page goes too
            pg.proc.kill()
        srv.send_signal(signal.SIGTERM)   # Studio's bye(): the worker stops its run and its Blender
        try:
            srv.wait(30)
        except subprocess.TimeoutExpired:
            srv.kill()
        srv_log.close()
        for _ in range(40):
            if not port_open(WORKER_PORT):
                break
            time.sleep(0.5)
        rec["worker_blender_left_open"] = port_open(WORKER_PORT)

    if R.skill_fingerprint() != before_fp:
        sys.exit(f"{brief['id']}: the session modified tracked files of the repository — the measurement is void.")
    shutil.copytree(work, outdir / "work", dirs_exist_ok=True)
    leaks = R.audit(transcript)
    if leaks:
        print(f"!!! {brief['id']}: CONTAMINATED — {len(leaks)} tool call(s) reached outside the sandbox "
              f"(first: {leaks[0]['matched']}). Its numbers are not a measurement.", flush=True)

    # 5. What changed.
    after_glb = outdir / "work" / "generated-assets" / name / "web" / f"{name}_final.glb"
    code_m, objs, tail = R.blender_json(R.BENCH / "studio_measure.py", [outdir / "before.glb", after_glb], "STUDIO_JSON")
    note_id = ((rec["page"].get("note") or {}).get("note") or {}).get("id")
    note = next((n for n in (rec.get("detail") or {}).get("notes", []) if n.get("id") == note_id), {})
    replies = [r for r in note.get("thread", []) if r.get("by") == "claude"]
    rec["result"] = {
        "change": judge(st, objs["before"], objs["after"]) if objs else {"verdict": "ERROR", "why": tail[-600:]},
        "note_status": note.get("status"),
        "claude_replies": len(replies),
        "new_version": sha(after_glb) not in (None, before_hash),
        "approvals_asked": len(rec["approvals"]),
        "approvals_denied": sum(a["decision"] == "deny" for a in rec["approvals"]),
        "proposals": len(rec["proposals"]),
    }
    r = rec["result"]
    r["verdict"] = ("PASS" if r["change"]["verdict"] == "PASS" and r["note_status"] == "addressed"
                    and r["claude_replies"] and r["new_version"] else "FAIL")

    results = []
    for line in transcript.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            results.append(ev)
    usage = [json.loads(l) for l in (outdir / "work" / ".kiln-studio" / "claude" / "usage.jsonl").read_text().splitlines()
             if l.strip()] if (outdir / "work" / ".kiln-studio" / "claude" / "usage.jsonl").is_file() else []
    session = {
        "brief": brief["id"],
        "mcp": f"{R.MCP_PACKAGE}==2.2.2 (Studio's worker)" if R.MCP != "lab"
               else f"lab@{R.sh(['git', '-C', str(R.LAB_DIR), 'rev-parse', '--short', 'HEAD']).strip()} (Studio's worker)",
        "blender": R.sh([R.BLENDER, "--version"]).splitlines()[0],
        "skill": R.sh(["git", "-C", str(R.PLUGIN), "rev-parse", "--short", "HEAD"]).strip()
                 + " " + R.sh(["git", "-C", str(R.PLUGIN), "branch", "--show-current"]).strip(),
        "claude_exit": code,
        "wall_s": wall,
        "is_error": any(e.get("is_error") for e in results) or bool(rec.get("error")),
        # One worker run per start and per resume (each approval resumes): summed.
        "runs": len(usage),
        "num_turns": sum(u.get("turns") or 0 for u in usage),
        "duration_ms": sum(u.get("duration_ms") or 0 for u in usage),
        "cost_usd_equiv": round(sum(u.get("cost_usd") or 0 for u in usage), 4),
        "tool_calls": R.tool_stats(transcript),
        "final_text": ((results[-1].get("result") if results else "") or "")[-2000:],
        "sandbox": str(box),
        "contamination": leaks,
        "timeout_s": R.TIMEOUT_S,
        "studio": rec,
    }
    R.measure_into(brief, outdir, session)
    return session
