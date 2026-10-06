#!/usr/bin/env python3
"""Install, check and run UniMate (text-to-motion for any rigged skeleton) for kiln.

UniMate is an external research project that changes fast, so this tool pins the
version kiln was measured against and tells you when upstream has moved:

    python3 plugin/tools/unimate.py status            # installed vs tested vs upstream
    python3 plugin/tools/unimate.py drift             # does kiln's patch still apply upstream? (CI, weekly)
    python3 plugin/tools/unimate.py setup             # install the tested version
    python3 plugin/tools/unimate.py setup --update    # move to upstream HEAD, if the patch still applies
    python3 plugin/tools/unimate.py animate --asset rigged.glb \\
        --prompt "An object walks in place." "An object jumps forward." --out ./anim

Standard library only. Needs git, uv (for Python 3.10) and Blender 4.4+.
The released checkpoints are CC BY-NC 4.0: non-commercial use only.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_URL = "https://github.com/Friedrich-M/UniMate"
HF_REPO = "Linzhan/UniMate"
# What kiln measured. Bump these only after re-running the measurements in
# references/animation.md against the new version.
TESTED_COMMIT = "004d787452e0bf8253d669d6e7b26c2064055cad"
TESTED_CHECKPOINT = "unimate_uniml3d_f60_v3"
TESTED_STEP = 150000

HOME = Path(os.environ.get("KILN_UNIMATE_HOME", Path.home() / ".cache" / "blender-kiln" / "unimate"))
CODE = HOME / "UniMate"
VENV = HOME / "venv"
BLENDER_LIB = HOME / "blender-site"      # third-party modules for Blender's own Python
WRAPPER_DIR = HOME / "bin"              # holds a `blender` that sees BLENDER_LIB
PATCH = Path(__file__).resolve().parent / "unimate.patch"
STATE = HOME / "kiln-install.json"


def run(cmd, cwd=None, env=None, check=True, capture=False):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, check=check,
                          text=True, capture_output=capture)


def py():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def find_blender() -> str | None:
    for cand in (os.environ.get("BLENDER"), shutil.which("blender"),
                 "/Applications/Blender.app/Contents/MacOS/Blender"):
        if cand and Path(cand).exists():
            return cand
    return None


def device() -> str:
    """cuda, mps or cpu, as the installed torch sees it."""
    if not py().exists():
        return "unknown (not installed)"
    r = run([py(), "-c", "import torch;print('cuda' if torch.cuda.is_available() else "
             "'mps' if torch.backends.mps.is_available() else 'cpu')"], check=False, capture=True)
    return r.stdout.strip() or "unknown"


# ── version checks ───────────────────────────────────────────────────────────

def upstream_commit() -> str | None:
    r = run(["git", "ls-remote", REPO_URL, "HEAD"], check=False, capture=True)
    return r.stdout.split()[0] if r.returncode == 0 and r.stdout else None


def upstream_checkpoint() -> tuple[str, int] | None:
    """Newest released (non-preview) uniml3d checkpoint on the Hub: (dir, step)."""
    try:
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{HF_REPO}", timeout=20) as f:
            files = [s["rfilename"] for s in json.load(f)["siblings"]]
    except Exception:
        return None
    best = None
    for name in files:
        m = re.match(r"(unimate_uniml3d_f60_v(\d+))/checkpoints/checkpoint_step_(\d+)\.pt$", name)
        if m:
            key = (int(m.group(2)), int(m.group(3)))
            if best is None or key > best[0]:
                best = (key, m.group(1), int(m.group(3)))
    return (best[1], best[2]) if best else None


def local_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def status(_args=None) -> int:
    st = local_state()
    up, ck = upstream_commit(), upstream_checkpoint()
    print(f"UniMate home      {HOME}")
    print(f"installed code    {st['commit'][:12] if st else 'not installed'}")
    print(f"installed weights {st.get('checkpoint', '-')} step {st.get('step', '-')}")
    print(f"tested by kiln    {TESTED_COMMIT[:12]}  {TESTED_CHECKPOINT} step {TESTED_STEP}")
    print(f"upstream code     {up[:12] if up else 'unreachable'}")
    print(f"upstream weights  {f'{ck[0]} step {ck[1]}' if ck else 'unreachable'}")
    print(f"device            {device()}")
    print("licence           code MIT; checkpoints CC BY-NC 4.0 — non-commercial use only")
    if not st:
        print("→ not installed: run `unimate.py setup`")
        return 2
    newer = []
    if up and up != st.get("commit"):
        newer.append("code")
    if ck and (ck[0], ck[1]) != (st.get("checkpoint"), st.get("step")):
        newer.append("weights")
    if newer:
        print(f"→ upstream has newer {' and '.join(newer)} than installed. "
              "`setup --update` moves to it if kiln's patch still applies; the result is "
              "then UNTESTED by kiln — re-check a few prompts before relying on it.")
        return 10
    print("→ up to date" + ("" if st.get("commit") == TESTED_COMMIT else " (but newer than kiln tested)"))
    return 0


def drift(_args=None) -> int:
    """Does kiln's patch still apply to upstream HEAD? Network only, no install —
    run weekly in CI so a breaking upstream change shows up before a user hits it."""
    import tempfile
    up = upstream_commit()
    with tempfile.TemporaryDirectory() as tmp:
        run(["git", "clone", "--quiet", "--depth", "1", REPO_URL, tmp])
        applies = run(["git", "apply", "--check", PATCH], cwd=tmp, check=False).returncode == 0
    ck = upstream_checkpoint()
    print(f"upstream {up[:12] if up else '?'} (kiln tested {TESTED_COMMIT[:12]}); "
          f"weights {f'{ck[0]} step {ck[1]}' if ck else '?'} (tested {TESTED_CHECKPOINT} step {TESTED_STEP})")
    if not applies:
        print("FAIL: kiln's patch no longer applies to upstream HEAD — `setup --update` will "
              "stay on the tested version until tools/unimate.patch is refreshed.")
        return 1
    print("ok: the patch applies to upstream HEAD" +
          ("" if up == TESTED_COMMIT else " — but that version is not measured by kiln yet"))
    return 0


# ── setup ────────────────────────────────────────────────────────────────────

def setup(args) -> int:
    for tool in ("git", "uv"):
        if not shutil.which(tool):
            sys.exit(f"`{tool}` is required (uv: https://docs.astral.sh/uv/).")
    blender = find_blender()
    if not blender:
        sys.exit("Blender not found: set BLENDER=/path/to/blender.")
    HOME.mkdir(parents=True, exist_ok=True)

    # 1. code at the tested commit, or upstream HEAD with --update
    if not CODE.exists():
        run(["git", "clone", "--quiet", REPO_URL, CODE])
    run(["git", "fetch", "--quiet", "origin"], cwd=CODE)
    target = TESTED_COMMIT
    if args.update:
        target = run(["git", "rev-parse", "origin/HEAD"], cwd=CODE, capture=True).stdout.strip()
    run(["git", "checkout", "--quiet", "--force", target], cwd=CODE)
    run(["git", "clean", "-fdq", "--exclude=outputs/"], cwd=CODE)
    # 2. kiln's patch: Apple MPS (no float64), a fixed-step ODE switch, Blender 5 actions
    if run(["git", "apply", "--check", PATCH], cwd=CODE, check=False).returncode != 0:
        if target != TESTED_COMMIT:
            run(["git", "checkout", "--quiet", "--force", TESTED_COMMIT], cwd=CODE)
            print(f"! kiln's patch no longer applies to upstream {target[:12]}; "
                  f"staying on the tested {TESTED_COMMIT[:12]}.")
            target = TESTED_COMMIT
        else:
            sys.exit("kiln's patch does not apply to the tested commit — the checkout is damaged.")
    run(["git", "apply", PATCH], cwd=CODE)

    # 3. Python 3.10 environment
    if not py().exists():
        run(["uv", "venv", "--quiet", "-p", "3.10", VENV])
    reqs = (CODE / "requirements.txt").read_text().splitlines()
    on_mac = platform.system() == "Darwin"
    keep = []
    for line in reqs:
        line = line.split("#")[0].strip()
        if not line or line.startswith("--extra-index-url") or line.startswith("bpy"):
            continue
        if line.startswith(("openai", "google-genai")):   # LLM labelling backends: kiln uses the offline rules
            continue
        if on_mac:
            line = line.replace("+cu124", "")
        keep.append(line)
    plain = [r for r in keep if " @ git+" not in r]
    git_deps = [r for r in keep if " @ git+" in r]
    req_file = HOME / "requirements-kiln.txt"
    req_file.write_text("\n".join(plain) + "\n")
    extra = [] if on_mac else ["--extra-index-url", "https://download.pytorch.org/whl/cu124"]
    run(["uv", "pip", "install", "--quiet", "-p", py(), *extra, "-r", req_file, "setuptools<81"])
    run(["uv", "pip", "install", "--quiet", "-p", py(), "--no-build-isolation", *git_deps])
    run(["uv", "pip", "install", "--quiet", "-p", py(),
         "--extra-index-url", "https://download.blender.org/pypi/", "bpy==4.0.0"])

    # 4. mesh driving runs inside Blender: give its Python the modules it imports
    bl_py = run([blender, "-b", "--factory-startup", "--python-expr",
                 "import sys;print('PY='+sys.executable)"], capture=True).stdout
    bl_py = re.search(r"PY=(\S+)", bl_py).group(1)
    run(["uv", "pip", "install", "--quiet", "--python", bl_py, "--target", BLENDER_LIB,
         "loguru", "tqdm", "scipy", "matplotlib", "imageio", "torch"])
    for leftover in BLENDER_LIB.glob("numpy*"):           # Blender ships its own numpy
        shutil.rmtree(leftover) if leftover.is_dir() else leftover.unlink()
    site = run([py(), "-c", "import Animation,os;print(os.path.dirname(Animation.__file__))"],
               capture=True).stdout.strip()
    for mod in ("Animation", "AnimationStructure", "BVH", "InverseKinematics", "Quaternions", "Pivots"):
        src = Path(site) / f"{mod}.py"
        if src.exists():
            shutil.copy(src, BLENDER_LIB / src.name)
    WRAPPER_DIR.mkdir(exist_ok=True)
    wrapper = WRAPPER_DIR / "blender"
    wrapper.write_text("#!/bin/bash\n"
                       f'export PYTHONPATH="{BLENDER_LIB}:${{PYTHONPATH:-}}"\n'
                       f'exec "{blender}" --python-use-system-env "$@"\n')
    wrapper.chmod(0o755)

    # 5. weights: the tested checkpoint, or the newest released one with --update
    ckpt, step = TESTED_CHECKPOINT, TESTED_STEP
    if args.update:
        ckpt, step = upstream_checkpoint() or (ckpt, step)
    run([VENV / "bin" / "hf", "download", HF_REPO, "--repo-type", "model",
         "--local-dir", CODE / "outputs", "--include", f"{ckpt}/*.json", "--include", f"{ckpt}/*.npy",
         "--include", f"{ckpt}/checkpoints/checkpoint_step_{step}.pt"])
    cfg_path = CODE / "outputs" / ckpt / "config.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["sampling"]["device"] = device()
    cfg_path.write_text(json.dumps(cfg, indent=2))

    STATE.write_text(json.dumps({"commit": target, "checkpoint": ckpt, "step": step,
                                 "device": cfg["sampling"]["device"], "blender": blender}, indent=2))
    print(f"\ninstalled UniMate {target[:12]} + {ckpt} step {step} on {cfg['sampling']['device']}")
    if target != TESTED_COMMIT or (ckpt, step) != (TESTED_CHECKPOINT, TESTED_STEP):
        print("! this is newer than what kiln measured — re-check a few prompts before relying on it.")
    print("licence: checkpoints are CC BY-NC 4.0 — non-commercial use only.")
    return 0


# ── animate ──────────────────────────────────────────────────────────────────

def animate(args) -> int:
    st = local_state()
    if not st:
        sys.exit("UniMate is not installed: run `unimate.py setup` first.")
    asset = Path(args.asset).resolve()
    name = re.sub(r"[^A-Za-z0-9_]", "_", asset.stem)
    work = CODE / "outputs" / "kiln" / name
    env = dict(os.environ, PATH=f"{WRAPPER_DIR}:{VENV / 'bin'}:{os.environ['PATH']}",
               PYTORCH_ENABLE_MPS_FALLBACK="1")
    if st["device"] != "cuda":
        env["UNIMATE_ODE"] = "euler:50"      # dopri5 takes 344 steps on CPU/MPS; 50 Euler steps look the same

    # 1. skeleton → conditioning, labelled offline (no LLM key, no cost)
    rig = work / "asset"
    cond = rig / "cond.npy"
    base = [py(), "-m", "data_process.rig_preprocess", "run", "--input", asset, "--output_dir", rig]
    if args.annotation:
        ann = Path(args.annotation).resolve()
        if cond.exists() and cond.stat().st_mtime >= max(ann.stat().st_mtime, asset.stat().st_mtime):
            print(f"reusing {rig} (asset and labels unchanged since it was built)")
        else:
            # rebuilding moves the asset dir's own annotation.json aside: read from a copy
            reviewed = work / "annotation.reviewed.json"
            shutil.copy(ann, reviewed)
            run(base + ["--profile", "general", "--annotation", reviewed, "--overwrite"], cwd=CODE, env=env)
    else:
        run(base + ["--annotate", "rule", "--overwrite"] + (["--no_review"] if args.no_review else []),
            cwd=CODE, env=env)
    if not cond.exists():
        print(f"\nReview the joint labels first: {rig / 'REVIEW.md'}\n"
              f"Edit {rig / 'annotation.json'} if needed, then rerun with "
              f"--annotation {rig / 'annotation.json'}")
        return 3

    # 2. text → motion, 3. motion → animated GLB
    samples = work / time.strftime("samples-%Y%m%d-%H%M%S")   # upstream appends to an existing dir
    run([py(), "-m", "unimate.inference.sample", "--exp_dir", CODE / "outputs" / st["checkpoint"],
         "--asset", rig, "--prompt", *args.prompt, "--num_repetitions", str(args.reps),
         "--output_dir", samples] + (["--seed", str(args.seed)] if args.seed is not None else [])
        + (["--cfg_scale", str(args.cfg)] if args.cfg is not None else []),
        cwd=CODE, env=env)
    run(["bash", "scripts/run_animate_motion.sh", samples], cwd=CODE, env=env)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    glbs = sorted((samples / "animated").rglob("*.glb"))
    for g in glbs:
        shutil.copy(g, out / g.name)
    print(f"\n{len(glbs)} animated GLB(s) in {out}")
    return 0 if glbs else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="installed vs tested vs upstream versions")
    sub.add_parser("drift", help="does kiln's patch still apply to upstream HEAD? (no install)")
    s = sub.add_parser("setup", help="install (or --update) UniMate")
    s.add_argument("--update", action="store_true", help="move to upstream HEAD and the newest weights")
    a = sub.add_parser("animate", help="rigged GLB + prompts -> animated GLBs")
    a.add_argument("--asset", required=True, help="rigged GLB / glTF / FBX")
    a.add_argument("--prompt", nargs="+", required=True, help='e.g. "An object walks in place."')
    a.add_argument("--reps", type=int, default=4, help="samples per prompt (default 4: they vary a lot)")
    a.add_argument("--seed", type=int)
    a.add_argument("--cfg", type=float, help="prompt adherence, upstream default 3")
    a.add_argument("--out", default="animated")
    a.add_argument("--annotation", help="reviewed annotation.json from a previous run")
    a.add_argument("--no-review", action="store_true", help="skip the label review stop")
    args = ap.parse_args()
    return {"status": status, "drift": drift, "setup": setup, "animate": animate}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
