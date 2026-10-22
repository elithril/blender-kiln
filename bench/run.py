"""Run the skill on the fixed briefs, headless, and measure what it ships.

    python3 bench/run.py <label> [brief-id ...]      # e.g. baseline, or lot2-trellis
    python3 bench/run.py --remeasure <label> [brief-id ...]   # measures again, session kept

For each brief: a fresh Blender on a throwaway profile, the MCP server pinned,
one `claude -p` session with the plugin loaded from this checkout and nothing
from the user's own settings, then bench/measure.py on every *_final.glb the
session left behind. Results land in bench/runs/<label>/<brief-id>/.

--remeasure runs only the measuring half again on a label already run (the transcript and
the work folder are kept): a measure added after a baseline reaches that baseline too.

Nothing here decides pass or fail: report.py compares two labels.
"""
import fnmatch, hashlib, json, os, re, shutil, socket, subprocess, sys, time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
REPO = BENCH.parent
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
# ahujasid's server, by its own name. `blender-mcp` 2.0.0 is only a shim that installs
# `mcp-for-blender>=2.0.0` UNPINNED: "blender-mcp==2.0.0" ran 2.1.9 on 2026-10-16 and 2.2.2 on
# 2026-10-21, with a different bundled addon each time. The real package, pinned, for both halves.
MCP_PACKAGE = "mcp-for-blender"
MCP_VERSION = os.environ.get("BENCH_MCP_VERSION", "2.2.2")
# Which Blender MCP the session drives: "ahujasid" (PyPI blender-mcp) or "lab",
# the official Blender Lab server — whose package is ALSO named blender-mcp, so
# it is always run from its git checkout, never resolved by name.
MCP = os.environ.get("BENCH_MCP", "ahujasid")
LAB_DIR = Path(os.environ.get("BENCH_LAB_DIR", BENCH / "runs" / "_deps" / "blender_mcp_lab"))
MODEL = os.environ.get("BENCH_MODEL", "claude-opus-5-5")
TIMEOUT_S = int(os.environ.get("BENCH_TIMEOUT_S", "3600"))
PORT = 9876
# The skill under test. Defaults to this checkout; point it at another worktree
# to measure a branch without switching this one (the runner and the results
# stay here, so labels from different branches sit side by side).
PLUGIN = Path(os.environ.get("BENCH_PLUGIN_DIR", REPO)).resolve()
# Each session runs in a sandbox OUTSIDE every repository. Before 2026-10-01 it ran in
# bench/runs/<label>/, and v12 of the lantern listed bench/results/ and read a README
# holding the real object's measurements — the answer key. The sandbox holds only what the
# brief names (refs/), a copy of the skill's runtime files (skill/: no README, CHANGELOG
# or docs, which quote the bench's measurements), and the work folder.
SANDBOX = Path(os.environ.get("BENCH_SANDBOX", "/private/tmp/kiln-bench"))
SKILL_RUNTIME = (".claude-plugin", "SKILL.md", "references", "tools", "examples", "LICENSE")
# Any of these in a session's tool calls voids its comparison: the repositories, the
# published results, the truth assets, the archive.
FORBIDDEN = [str(REPO), str(PLUGIN), "_refs/gt", "bench/results", "bench-archive", "blender-kiln-bench"]
# bench/runs may be a symlink into another checkout (a frozen bench worktree writing into the
# main one): that checkout holds the answers too.
_RUNS_HOME = (BENCH / "runs").resolve().parent.parent
if str(_RUNS_HOME) not in FORBIDDEN:
    FORBIDDEN.append(str(_RUNS_HOME))
# The print instrument: the bench's own copy of print_check, the same for every label —
# never the one inside the skill under test (2.2.0 has none).
PRINT_CHECK = REPO / "plugin" / "tools" / "print_check.py"
SLICER = os.environ.get("BENCH_SLICER", "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer")
INSTRUMENTS = [BENCH / "measure.py", BENCH / "skin_intersect.py", BENCH / "signals.py", PRINT_CHECK]
sys.path.insert(0, str(BENCH))
import signals  # noqa: E402


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r.stdout


def bundled_addon():
    """The addon that ships inside the pinned server package, so both halves match."""
    out = sh(["uvx", "--from", f"{MCP_PACKAGE}=={MCP_VERSION}", "python", "-c",
              "import blender_mcp, os; print(os.path.join(os.path.dirname(blender_mcp.__file__), 'bundled', 'addon.py'))"])
    p = Path(out.strip().splitlines()[-1])
    if not p.is_file():
        sys.exit(f"no bundled addon in {MCP_PACKAGE} {MCP_VERSION}: {p}")
    return p


def port_open():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("localhost", PORT)) == 0


def start_blender(profile, log):
    if port_open():
        sys.exit(f"port {PORT} is already taken — close the other Blender first, "
                 "or the session would drive the wrong one")
    if MCP == "lab":
        ext = profile / "extensions" / "user_default" / "mcp"
        shutil.rmtree(ext, ignore_errors=True)
        shutil.copytree(LAB_DIR / "addon" / "blender_mcp_addon", ext)
        start, extra = "blender_start_lab.py", ["--online-mode"]
    else:
        (profile / "scripts" / "addons").mkdir(parents=True, exist_ok=True)
        shutil.copy(bundled_addon(), profile / "scripts" / "addons" / "blender_mcp.py")
        start, extra = "blender_start.py", []
    env = dict(os.environ,
               BLENDER_USER_SCRIPTS=str(profile / "scripts"),
               BLENDER_USER_CONFIG=str(profile / "config"),
               BLENDER_USER_EXTENSIONS=str(profile / "extensions"),
               BLENDER_USER_DATAFILES=str(profile / "datafiles"))
    # GUI, not --background: get_viewport_screenshot needs a viewport, and
    # rule 2 calls it after every change.
    proc = subprocess.Popen([BLENDER, "--factory-startup", *extra, "--python-exit-code", "1",
                             "--python", str(BENCH / start)],
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
    """Hash of every tracked file. Permissions are bypassed, and the sandbox is a
    convention, not a wall: nothing but this stops a session from editing the
    skill it is being measured on."""
    return "".join(sh(["git", "-C", str(d), "ls-files", "-s"]) + sh(["git", "-C", str(d), "diff", "HEAD"])
                   for d in {REPO, PLUGIN})


def sandbox_for(brief, outdir):
    box = SANDBOX / outdir.parent.name / outdir.name
    shutil.rmtree(box, ignore_errors=True)
    refs, skill, work = box / "refs", box / "skill", box / "work"
    for d in (refs, skill, work):
        d.mkdir(parents=True)
    for rel in sorted(set(re.findall(r"<REFS>/([\w./-]+?)(?=[\s:,;]|\.(?:\s|$)|$)", brief["prompt"]))):
        src = BENCH / "runs" / "_refs" / rel
        if not src.is_file():
            sys.exit(f"{brief['id']}: the prompt names <REFS>/{rel}, which does not exist")
        (refs / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, refs / rel)
    tracked = sh(["git", "-C", str(PLUGIN), "ls-files"]).splitlines()
    # Since 2.0.2 the skill lives in plugin/ — exactly what an install ships, so the
    # sandbox gets that folder as is. Older checkouts kept it at the repository root.
    if (PLUGIN / "plugin" / ".claude-plugin" / "plugin.json").is_file():
        files = [(rel, rel[len("plugin/"):]) for rel in tracked if rel.startswith("plugin/")]
    else:
        files = [(rel, rel) for rel in tracked if rel.split("/")[0] in SKILL_RUNTIME]
    for rel, dst in files:
        if (PLUGIN / rel).is_file() and not (PLUGIN / rel).is_symlink():
            (skill / dst).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(PLUGIN / rel, skill / dst)
    if not (skill / ".claude-plugin" / "plugin.json").is_file() or not (skill / "SKILL.md").is_file():
        sys.exit("sandbox: the skill copy has no plugin.json or SKILL.md — the layout changed")
    return box, refs, skill, work


def close_orphans(box):
    """Blenders a session started from its sandbox and left open, closed; what still holds the port, named.

    run.py stops only the Blender it started. On 2026-10-21 a 3.0 session lost its MCP and reopened
    one with tools/open_blender.py (its command line names the sandbox's blender_mcp_start.py): left
    on 9876, it held the next label 50 min. A listener not started from the sandbox is the user's,
    never touched."""
    closed = []
    for pid in subprocess.run(["pgrep", "-f", str(box)], capture_output=True, text=True).stdout.split():
        exe = subprocess.run(["ps", "-o", "comm=", "-p", pid], capture_output=True, text=True).stdout.strip()
        if os.path.basename(exe).lower() != "blender":
            continue
        cmd = subprocess.run(["ps", "-o", "command=", "-p", pid], capture_output=True, text=True).stdout.strip()
        try:
            os.kill(int(pid), 15)
            closed.append(cmd[:300])
        except OSError:
            pass
    for _ in range(20):
        if not port_open():
            break
        time.sleep(0.5)
    held = None
    if port_open():
        pids = subprocess.run(["lsof", "-tnP", f"-iTCP:{PORT}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
        held = subprocess.run(["ps", "-o", "command=", "-p", pids[0]], capture_output=True, text=True).stdout.strip()[:300] if pids else "?"
    return {"closed": closed, "port_still_held_by": held}


def audit(transcript):
    """Tool calls that reached outside the sandbox, toward anything that holds an answer."""
    hits = []
    for i, line in enumerate(transcript.read_text().splitlines()):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "assistant":
            continue
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                text = json.dumps(block.get("input", {}))
                for f in FORBIDDEN:
                    if f in text:
                        hits.append({"line": i, "tool": block["name"], "matched": f, "input": text[:300]})
                        break
    return hits


def run_brief(brief, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    box, refs, skill_copy, work = sandbox_for(brief, outdir)
    if MCP == "lab":
        server = {"command": "uvx", "args": ["--from", str(LAB_DIR / "mcp"), "blender-mcp"],
                  "env": {"BLENDER_PATH": BLENDER}}
    else:
        server = {"command": "uvx", "args": ["--from", f"{MCP_PACKAGE}=={MCP_VERSION}", MCP_PACKAGE]}
    # Named "blender" either way: the skill's allowed-tools is mcp__blender__*.
    (outdir / "mcp.json").write_text(json.dumps({"mcpServers": {"blender": server}}))

    before = skill_fingerprint()
    with open(outdir / "blender.log", "w") as blog:
        blender = start_blender(outdir / "profile", blog)
        t0 = time.time()
        try:
            with open(outdir / "transcript.jsonl", "w") as tr, open(outdir / "claude.err", "w") as err:
                prompt = (brief["prompt"].replace("<REFS>", str(refs))
                          + f"\n\nOutput folder (absolute): {work / 'generated-assets'}")
                r = subprocess.run(
                    ["claude", "-p", prompt,
                     "--plugin-dir", str(skill_copy),
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

    orphans = close_orphans(box)
    if orphans["closed"] or orphans["port_still_held_by"]:
        print(f"     orphan Blender(s) closed: {len(orphans['closed'])}; port {PORT} still held by: "
              f"{orphans['port_still_held_by']}", flush=True)
    if skill_fingerprint() != before:
        sys.exit(f"{brief['id']}: the session modified tracked files of the repository — "
                 "the measurement is void. See `git status` before anything else.")
    # Bring the work back next to the transcript; the sandbox is left for inspection.
    shutil.copytree(work, outdir / "work", dirs_exist_ok=True)
    work = outdir / "work"
    leaks = audit(outdir / "transcript.jsonl")
    if leaks:
        print(f"!!! {brief['id']}: CONTAMINATED — {len(leaks)} tool call(s) reached outside the sandbox "
              f"(first: {leaks[0]['matched']}). Its numbers are not a measurement.", flush=True)

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
        "mcp": f"{MCP_PACKAGE}=={MCP_VERSION}" if MCP != "lab" else f"lab@{sh(['git', '-C', str(LAB_DIR), 'rev-parse', '--short', 'HEAD']).strip()}",
        "blender": sh([BLENDER, "--version"]).splitlines()[0],
        "skill": sh(["git", "-C", str(PLUGIN), "rev-parse", "--short", "HEAD"]).strip()
                 + " " + sh(["git", "-C", str(PLUGIN), "branch", "--show-current"]).strip(),
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
        "sandbox": str(box),
        "contamination": leaks,
        "orphan_blenders": orphans,
    }

    session["timeout_s"] = TIMEOUT_S
    measure_into(brief, outdir, session)
    (outdir / "result.json").write_text(json.dumps(session, indent=2))
    return session


def blender_json(script, args, prefix):
    """Run a bench instrument in a fresh background Blender; its one JSON line, or the error."""
    m = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", str(script), "--", *map(str, args)], capture_output=True, text=True)
    line = next((l for l in m.stdout.splitlines() if l.startswith(prefix + " ")), None)
    return m.returncode, (json.loads(line[len(prefix) + 1:]) if line else None), m.stdout[-800:] + m.stderr[-800:]


def measure_glb(glb, work, outdir):
    code, d, tail = blender_json(BENCH / "measure.py", [glb], "BENCH_JSON")
    if code != 0 or d is None:
        # Fail loud: a GLB we could not measure is a finding, not a gap to skip.
        return {"file": str(glb.relative_to(work)) if work in glb.parents else str(glb), "measure_error": tail}
    d["file"] = str(glb.relative_to(work)) if work in glb.parents else glb.name
    if outdir is not None:
        png = outdir / f"render-{glb.stem}.png"
        rr = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                             "--python", str(BENCH / "render.py"), "--", str(glb), str(png)],
                            capture_output=True, text=True)
        d["render"] = png.name if rr.returncode == 0 else f"render failed: {rr.stdout[-400:]}"
    return d


def shipped(work, patterns):
    """Files matching the brief's patterns, outside review/test/intermediate folders."""
    skip = {"review", "test", "tmp", "_tmp", "intermediate", "intermediates", "concept"}
    out = []
    for p in sorted(work.rglob("*")):
        dirs = p.relative_to(work).parts[:-1]
        # Hidden folders are tools' state, not shipped: Studio keeps a copy of the model it was
        # noted on in .kiln-studio/baseline/.
        if p.is_file() and not (skip & {x.lower() for x in dirs}) and not any(x.startswith(".") for x in dirs) \
                and any(fnmatch.fnmatch(p.name, pat) for pat in patterns):
            out.append(p)
    return out


def print_check(files, process, assembly):
    """print_check on the shipped STL/3MF: each file, and all together as an assembly. With
    PrusaSlicer when present; a FAIL on a floating part is sliced again with supports, so the
    record says whether the print needs them."""
    if not PRINT_CHECK.is_file():
        return {"error": f"no instrument at {PRINT_CHECK}"}
    slicer = ["--slicer", SLICER] if Path(SLICER).exists() else []

    def one(paths, supports=False):
        code, d, tail = blender_json(PRINT_CHECK, [*paths, "--process", process, *slicer,
                                                   *(["--supports"] if supports else [])], "PRINT_CHECK")
        if d is None:
            return {"exit": code, "error": tail}
        keep = {k: d.get(k) for k in ("verdict", "fails", "warnings", "triangles", "dims_mm", "parts",
                                      "closed_parts", "open_edges", "nonmanifold_edges", "inconsistent_edges",
                                      "self_intersecting_pairs", "intersecting_part_pairs", "floating_parts",
                                      "inverted_parts", "volume_mm3", "overhang_area_pct", "assembly")
                if k in d}
        if "thickness" in d:
            keep["min_scale"] = d["thickness"].get("min_scale")
        if "slicer" in d:
            keep["slicer"] = {k: d["slicer"].get(k) for k in ("manifold", "number_of_parts",
                              "empty_layer_count", "floating_count", "stability_issues", "slice_exit", "supports")}
        floating = any("Floating object part" in f for f in keep.get("fails") or [])
        if floating and slicer and not supports:
            keep["with_supports"] = one(paths, supports=True)
        return keep

    rec = {"slicer": bool(slicer), "assembly_expected": assembly, "files": {}}
    for f in files:
        rec["files"][f.name] = one([f])
    # An assembly (one figure, a file per colour) is judged together: one colour alone is not
    # printable. Separate prints (a box and its lid) are judged each on its own.
    if assembly and len(files) > 1:
        rec["assembly"] = one(files)
        judged = [rec["assembly"]]
    else:
        judged = list(rec["files"].values())
    if judged:
        verdicts = [j.get("verdict") for j in judged]
        rec["verdict"] = "PASS" if all(v == "PASS" for v in verdicts) else (
            "FAIL" if all(v in ("PASS", "FAIL") for v in verdicts) else "ERROR")
        sup = [j for j in judged if j.get("with_supports")]
        rec["needs_supports"] = bool(sup) and all(j["with_supports"].get("verdict") == "PASS" for j in sup)
        rec["verdict_with_supports"] = ("PASS" if all(
            (j.get("with_supports") or j).get("verdict") == "PASS" for j in judged) else "FAIL")
    return rec


def artifacts(work):
    """Reports the skill's own tools wrote — read, never trusted over the file measures."""
    out = {}
    for name in ("quadruped-report.json", "photo_project.json"):
        found = sorted(work.rglob(name))
        if found:
            try:
                out[name] = {str(p.relative_to(work)): json.loads(p.read_text()) for p in found}
            except (json.JSONDecodeError, OSError) as ex:
                out[name] = {"error": str(ex)}
    pp = out.get("photo_project.json", {})
    for k, v in pp.items():
        if isinstance(v, dict) and v.get("photo_view"):
            out["projection_ssim"] = {"before": v["photo_view"].get("before", {}).get("ssim"),
                                      "after": v["photo_view"].get("after", {}).get("ssim"),
                                      "iou": (v.get("camera") or {}).get("iou"), "file": k}
    return out


def instruments():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in INSTRUMENTS if p.is_file()}


def measure_into(brief, outdir, session):
    """The measuring half: every shipped file, the inputs it started from, the transcript's
    signals, the tools' own reports. Writes result.json."""
    work = outdir / "work"
    session["instruments"] = instruments()
    session["signals"] = signals.signals(outdir / "transcript.jsonl", session.get("final_text") or "")
    session["artifacts"] = artifacts(work)
    refs = BENCH / "runs" / "_refs"
    session["input_measures"] = [measure_glb(refs / rel, refs, None) for rel in brief.get("inputs", [])]
    finals = shipped(work, brief.get("finals", ["*_final.glb"]))
    finals = [p for p in finals if p.suffix.lower() == ".glb"]
    session["finals"] = len(finals)
    session["measures"] = [measure_glb(glb, work, outdir) for glb in finals]
    if brief.get("print"):
        # test pieces (a coupon, a ring cut to try the lock) are the session's, not the model
        files = [p for p in shipped(work, ["*.stl", "*.3mf"])
                 if not re.search(r"(^test_|coupon|essai|_test\b|fit[-_]?test)", p.stem, re.I)]
        session["print_files"] = [str(p.relative_to(work)) for p in files]
        pr = brief["print"]
        session["print_check"] = (print_check(files, pr.get("process", "fdm"), pr.get("assembly", False))
                                  if files else None)
    (outdir / "result.json").write_text(json.dumps(session, indent=2))
    return session


def remeasure(label, only, briefs):
    for b in briefs:
        if only and b["id"] not in only:
            continue
        outdir = BENCH / "runs" / label / b["id"]
        rj = outdir / "result.json"
        if not rj.exists():
            continue
        s = json.loads(rj.read_text())
        s["remeasured"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        print(f"remeasure {label}/{b['id']} …", flush=True)
        measure_into(b, outdir, s)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    briefs = json.loads((BENCH / "briefs.json").read_text())["briefs"]
    if sys.argv[1] == "--remeasure":
        if len(sys.argv) < 3:
            sys.exit(__doc__)
        return remeasure(sys.argv[2], set(sys.argv[3:]), briefs)
    label, only = sys.argv[1], set(sys.argv[2:])
    unknown = only - {b["id"] for b in briefs}
    if unknown:
        sys.exit(f"unknown brief id(s): {sorted(unknown)}")
    for b in briefs:
        if only and b["id"] not in only:
            continue
        if b.get("disabled"):
            print(f"skip {b['id']}: disabled — {b['disabled']}")
            continue
        outdir = BENCH / "runs" / label / b["id"]
        if (outdir / "result.json").exists():
            print(f"skip {b['id']}: already measured under '{label}' (delete the folder to rerun)")
            continue
        print(f"run  {b['id']} …", flush=True)
        if b.get("kind") == "studio" and not (PLUGIN / "plugin" / "studio" / "studio.py").is_file():
            print(f"skip {b['id']}: the skill under test has no Kiln Studio (3.0 and later)")
            continue
        if b.get("kind") == "studio":
            import studio_drive   # the session is Studio's worker's, not one started here
            s = studio_drive.run_studio_brief(b, outdir)
        else:
            s = run_brief(b, outdir)
        print(f"     exit={s['claude_exit']} turns={s['num_turns']} wall={s['wall_s']}s "
              f"cost≈${s['cost_usd_equiv']} finals={s['finals']}", flush=True)


if __name__ == "__main__":
    main()
