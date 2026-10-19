"""What Studio can tell about the kiln setup on this machine, for its welcome screen.

Standard library only. Each probe says what it found and how: "ok", "missing", or
"unknown" when Studio cannot see it from here, never a guess (SKILL.md § /kiln setup is
the full scan, run by Claude). Results are cached a minute: the probes run programs.
"""

from __future__ import annotations

import glob
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
MCP_PORT = 9876   # the Blender MCP add-on's socket (ahujasid's; references/setup-install.md)
_cache: dict = {}


def _row(key: str, state: str, detail: str, how: str, **data) -> dict:
    """`detail` in English for API readers; `data`, the same facts for the page to word."""
    return {"key": key, "state": state, "detail": detail, "how": how, "data": data}


def blender_paths() -> list[str]:
    found = []
    for env in ("KILN_BLENDER", "BLENDER"):
        if os.environ.get(env):
            found.append(os.environ[env])
    if shutil.which("blender"):
        found.append(shutil.which("blender"))
    system = platform.system()
    if system == "Darwin":
        found += ["/Applications/Blender.app/Contents/MacOS/Blender",
                  str(Path.home() / "Applications/Blender.app/Contents/MacOS/Blender")]
    elif system == "Windows":
        found += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True)
    else:
        found += ["/usr/bin/blender", "/snap/bin/blender", "/usr/local/bin/blender"]
    out = []
    for p in found:
        if p and Path(p).is_file() and p not in out:
            out.append(p)
    return out


def blender() -> dict:
    paths = blender_paths()
    how = "PATH, $BLENDER, and the usual install folders"
    if not paths:
        return _row("blender", "missing", "", how)
    try:
        r = subprocess.run([paths[0], "--version"], capture_output=True, text=True, timeout=20)
        first = next((ln.strip() for ln in r.stdout.splitlines() if ln.startswith("Blender")), "")
    except (OSError, subprocess.TimeoutExpired):
        first = ""
    return _row("blender", "ok", f"{first or 'Blender'} · {paths[0]}", how, version=first, path=paths[0])


def _claude_mcp_names(project_root: Path) -> set[str]:
    """The MCP servers Claude Code is configured with for this project (names only)."""
    names: set[str] = set()
    for p in (project_root / ".mcp.json", Path.home() / ".claude.json"):
        try:
            data = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        names |= set((data.get("mcpServers") or {}).keys())
        proj = (data.get("projects") or {}).get(str(project_root)) or {}
        names |= set((proj.get("mcpServers") or {}).keys()) if isinstance(proj, dict) else set()
    return names


def blender_mcp(project_root: Path) -> dict:
    """Studio cannot see Claude's connections: always "unknown", with what it can see."""
    names = _claude_mcp_names(project_root)
    configured = sorted(n for n in names if "blender" in n.lower())
    try:
        with socket.create_connection(("127.0.0.1", MCP_PORT), timeout=0.3):
            listening = True
    except OSError:
        listening = False
    bits = [f"configured: {', '.join(configured)}" if configured else "no Blender MCP server in Claude Code's settings for this project",
            f"add-on port {MCP_PORT}: {'open' if listening else 'closed'}"]
    return _row("mcp", "unknown", " · ".join(bits),
                "Claude Code's settings and a connection to the add-on's port; whether Claude is connected only Claude can say",
                configured=configured, port=MCP_PORT, listening=listening)


def skintokens() -> dict:
    tool = PLUGIN / "tools" / "autorig.py"
    how = "tools/autorig.py status --quick"
    if not tool.is_file():
        return _row("skintokens", "unknown", "this kiln has no tools/autorig.py", how, reason="no-tool")
    try:
        r = subprocess.run([sys.executable, str(tool), "status", "--quick"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return _row("skintokens", "unknown", str(e), how, reason="error", output=str(e))
    detail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
    state = {0: "ok", 2: "missing", 3: "missing"}.get(r.returncode, "unknown")
    return _row("skintokens", state, detail[0], how, reason=f"exit {r.returncode}", output=detail[0])


def claude_code() -> dict:
    how = "claude --version"
    exe = shutil.which("claude")
    if not exe:
        return _row("claude", "missing", "Claude Code is not on PATH", how)
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
        version = (r.stdout or "").strip().split()[0] if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        version = None
    return _row("claude", "ok", f"Claude Code {version or ''} · {exe}".strip(), how, version=version, path=exe)


def optimizers() -> dict:
    """gltf-transform and gltfpack: kiln's OPTIMIZE phase compresses with them when present."""
    found = {n: shutil.which(n) for n in ("gltf-transform", "gltfpack")}
    have = [n for n, x in found.items() if x]
    state = "ok" if len(have) == 2 else "missing" if not have else "partial"
    return _row("optimizers", state, ", ".join(have) or "neither", "command -v gltf-transform gltfpack", found=have)


def unimate() -> dict:
    """UniMate (text to motion): installed when its venv is there (tools/unimate.py setup)."""
    home = Path(os.environ.get("UNIMATE_HOME") or "~/.cache/blender-kiln/unimate").expanduser()
    venv = home / "venv" / "bin" / "python"
    tool = PLUGIN / "tools" / "unimate.py"
    if not tool.is_file():
        return _row("unimate", "unknown", "this kiln has no tools/unimate.py", "tools/unimate.py status", reason="no-tool")
    return _row("unimate", "ok" if venv.is_file() else "missing", str(home), "tools/unimate.py status", home=str(home))


# What each part is for, how much it matters, what it weighs and under which licence: the
# page shows these beside the state, and Install with Claude runs /kiln setup <key>.
COMPONENTS = {
    "blender": {"need": "required", "size": "≈ 1 GB", "licence": "GPL", "install": True},
    "claude": {"need": "required", "size": "≈ 200 MB", "licence": "Anthropic", "install": False},
    "mcp": {"need": "required", "size": "", "licence": "MIT", "install": False},
    "optimizers": {"need": "recommended", "size": "≈ 60 MB", "licence": "MIT", "install": True},
    "skintokens": {"need": "optional", "size": "≈ 2 GB", "licence": "MIT", "install": True},
    "unimate": {"need": "optional", "size": "≈ 3.2 GB", "licence": "CC BY-NC 4.0 (non-commercial)", "install": True},
}


def install_status(project_root: Path, max_age: float = 60.0) -> dict:
    key = str(project_root)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < max_age:
        return hit[1]
    manifest = {}
    try:
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    except (OSError, ValueError):
        pass
    rows = [blender(), claude_code(), blender_mcp(project_root), optimizers(), skintokens(), unimate()]
    for r in rows:
        r.update(COMPONENTS.get(r["key"], {}))
    out = {"kiln": manifest.get("version"), "rows": rows}
    _cache[key] = (time.monotonic(), out)
    return out
