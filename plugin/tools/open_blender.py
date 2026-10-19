#!/usr/bin/env python3
"""Open the user's Blender with its MCP add-on serving, when nothing answers on the port.

    python3 tools/open_blender.py            # port 9876, the Blender MCP's own
    python3 tools/open_blender.py --port N   # another port (tests)
    python3 tools/open_blender.py --front    # in front (default: behind the user's windows)

kiln runs it on its own when the Blender MCP does not answer (SKILL.md rule 2): it opens the
user's Blender, behind their windows, with their own preferences and add-ons, then starts
the add-on's server (tools/blender_mcp_start.py) and waits until the port answers. Already
answering: says so and opens nothing. On a failure, kiln stops and asks the user.

Exit 0 when the port answers; 1 with the reason otherwise (no Blender found, the add-on
not installed — `uvx blender-mcp install-addon` —, or no answer in time). Standard library.
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
START = HERE / "blender_mcp_start.py"


def answers(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def find_blender() -> tuple[str, list[str]] | None:
    """(how, command prefix): the app on macOS, else a blender executable."""
    env = os.environ.get("BLENDER")
    if env and Path(env).exists():
        return "exe", [env]
    if sys.platform == "darwin":
        for app in ("/Applications/Blender.app", str(Path.home() / "Applications/Blender.app")):
            if Path(app).exists():
                return "app", ["open", "-g", "-n", "-a", app, "--args"]
    exe = shutil.which("blender")
    return ("exe", [exe]) if exe else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=9876)
    ap.add_argument("--timeout", type=float, default=90)
    ap.add_argument("--front", action="store_true", help="bring Blender to the front (macOS)")
    a = ap.parse_args()
    if answers(a.port):
        print(f"BLENDER already answers on port {a.port}: nothing opened.")
        return 0
    found = find_blender()
    if not found:
        print("BLENDER not found: install it (blender.org), or set $BLENDER to its executable.")
        return 1
    how, cmd = found
    if a.front and "-g" in cmd:
        cmd.remove("-g")   # `open -g` leaves it behind the user's windows
    env = dict(os.environ, KILN_MCP_PORT=str(a.port))
    args = ["--python", str(START)]
    if how == "app":
        # macOS: through `open`, so Blender is a normal app window; the port goes in by --env.
        cmd = cmd[:-1] + ["--env", f"KILN_MCP_PORT={a.port}", "--args"] + args
        subprocess.run(cmd, check=True, env=env, timeout=30)
    else:
        subprocess.Popen(cmd + args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < a.timeout:
        if answers(a.port):
            print(f"BLENDER opened, its MCP add-on answers on port {a.port} ({time.time() - t0:.0f} s).")
            return 0
        time.sleep(1)
    print(f"BLENDER opened, but nothing answers on port {a.port} after {a.timeout:.0f} s: is the "
          "Blender MCP add-on installed (`uvx blender-mcp install-addon`)? Blender's console says why.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
