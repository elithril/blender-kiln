#!/usr/bin/env python3
"""What open_blender.py counts as a Blender already open, from `ps` lines.

    python3 tools/test_open_blender.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from open_blender import open_blenders  # noqa: E402

PS = """/Applications/Blender.app/Contents/MacOS/Blender
/Applications/Blender.app/Contents/MacOS/Blender --python /x/skill/tools/blender_mcp_start.py
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python /x/tools/print_check.py -- a.stl
/Applications/Blender.app/Contents/MacOS/Blender --background --python /x/tools/review_renders.py
/Applications/Blender.app/Contents/MacOS/Blender --factory-startup --python /x/plugin/studio/worker_blender.py
/usr/bin/python3 /x/tools/open_blender.py --port 9876
claude -p make a lantern in Blender
"""

failures = []
got = open_blenders(PS)
if len(got) != 2:
    failures.append(f"expected the two windowed Blenders (plain, and the opener's), got {got}")
if any("-b " in g or "--background" in g or "worker_blender" in g for g in got):
    failures.append(f"a headless or Studio worker Blender was counted: {got}")
if open_blenders("") != []:
    failures.append("an empty process list should find nothing")
for f in failures:
    print("FAIL", f)
print(f"{3 - len(failures)}/3")
sys.exit(1 if failures else 0)
