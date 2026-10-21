#!/usr/bin/env python3
"""A model's game and AR outputs, without Claude: kiln's settings, Blender headless, checked.

    python3 tools/export_outputs.py <model folder> game ar [--blender PATH]

From the model's `_original.glb` (the uncompressed export of its source):
- game: game/<name>_game.fbx (tools/glb_to_fbx.py), read back: its size must match the GLB's;
- ar:   ar/<name>_ar.glb — the _original as it is (uncompressed, PNG: Scene Viewer's; its
        finishes and animations kept) — and ar/<name>_ar.usdz (tools/glb_to_usdz.py: vertex
        colours baked, WebP to PNG, Y up, the animation), passed by usdchecker --arkit.

Each file is written beside, then moved into place only once its check passed: a failed
export leaves nothing behind. The model's log gets a line per output. Prints one JSON
object: {"ok": bool, "outputs": {kind: {files, checks}}, "error": str}. Exit 1 on failure.
Studio runs it for "+ Game" and "+ AR"; print stays with Claude (print_check, parts).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_blender(given: str | None) -> str | None:
    for c in (given, os.environ.get("BLENDER"), "/Applications/Blender.app/Contents/MacOS/Blender",
              str(Path.home() / "Applications/Blender.app/Contents/MacOS/Blender"), shutil.which("blender")):
        if c and Path(c).exists():
            return c
    return None


def blender_run(blender: str, script: str, *args: str) -> list[str]:
    r = subprocess.run([blender, "-b", "--factory-startup", "--python", str(HERE / script), "--", *args],
                       capture_output=True, text=True, timeout=900)
    lines = [l for l in r.stdout.splitlines() if l.split(" ", 1)[0] in ("DIMS", "FBX", "USDZ", "FAILED", "ARKIT", "ANIM")]
    if r.returncode != 0 or any(l.startswith("FAILED") for l in lines):
        raise RuntimeError(next((l for l in lines if l.startswith("FAILED")), f"{script}: Blender exited {r.returncode}"))
    return lines


def game(blender: str, d: Path, name: str, src: Path, tmp: Path) -> dict:
    out = tmp / f"{name}_game.fbx"
    lines = blender_run(blender, "glb_to_fbx.py", str(src), str(out))
    dims = {l.split()[1]: [float(x) for x in l.split()[2:5]] for l in lines if l.startswith("DIMS")}
    g, f = dims.get("glb"), dims.get("fbx")
    if not g or not f or any(abs(a - b) > max(0.02 * max(g), 1e-3) for a, b in zip(sorted(g), sorted(f))):
        raise RuntimeError(f"the FBX read back is not the model's size: {f} m against {g} m")
    (d / "game").mkdir(exist_ok=True)
    final = d / "game" / out.name
    shutil.move(out, final)
    return {"files": [str(final)], "checks": f"read back {' × '.join(f'{x:.3f}' for x in f)} m, as the GLB"}


def ar(blender: str, d: Path, name: str, src: Path, tmp: Path) -> dict:
    usdz = tmp / f"{name}_ar.usdz"
    lines = blender_run(blender, "glb_to_usdz.py", str(src), str(usdz))
    baked = next((l for l in lines if l.startswith("USDZ")), "")
    check = blender_run(blender, "check_usdz.py", str(usdz))
    fails = [l[len("ARKIT FAIL "):] for l in check if l.startswith("ARKIT FAIL")]
    if fails:
        raise RuntimeError("the USDZ fails the ARKit check: " + "; ".join(fails[:3]))
    anim = next((l for l in check if l.startswith("ANIM")), None)
    (d / "ar").mkdir(exist_ok=True)
    glb = d / "ar" / f"{name}_ar.glb"
    shutil.copy2(src, glb)
    final = d / "ar" / usdz.name
    shutil.move(usdz, final)
    note = "usdchecker --arkit clean" + (f", animated (frames {anim.split()[1]}–{anim.split()[2]})" if anim else "")
    if "baked on 0" not in baked and "baked on" in baked:
        note += ", vertex colours baked"
    return {"files": [str(glb), str(final)], "checks": note}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder")
    ap.add_argument("kinds", nargs="+", choices=["game", "ar"])
    ap.add_argument("--blender")
    a = ap.parse_args()
    d = Path(a.folder).resolve()
    name = d.name
    src = d / f"{name}_original.glb"
    out = {"ok": False, "outputs": {}, "error": ""}
    blender = find_blender(a.blender)
    try:
        if not src.is_file():
            raise RuntimeError(f"no {src.name}: export the model's source first")
        if not blender:
            raise RuntimeError("Blender not found (install it, or set $BLENDER)")
        with tempfile.TemporaryDirectory(dir=d, prefix=".export-") as t:
            for k in a.kinds:
                out["outputs"][k] = (game if k == "game" else ar)(blender, d, name, src, Path(t))
        log = d / f"{name}_log.md"
        lines = [f"\n## Outputs (Studio, {time.strftime('%Y-%m-%d')})"]
        for k, r in out["outputs"].items():
            files = ", ".join(str(Path(f).relative_to(d)) for f in r["files"])
            lines.append(f"- {files}: kiln's settings, tools/export_outputs.py from {src.name} — {r['checks']}")
        with log.open("a") as f:
            f.write("\n".join(lines) + "\n")
        out["ok"] = True
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        out["error"] = str(e)
    print(json.dumps(out))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
