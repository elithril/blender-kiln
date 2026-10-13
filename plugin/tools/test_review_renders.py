#!/usr/bin/env python3
"""Check review_renders.py renders what it says.

    python3 tools/test_review_renders.py      # needs Blender at $BLENDER or the macOS default

- a 20 x 10 x 40 mm block (STL, mm): exit 0, one PNG per view and mode, each the --res asked,
  the subject spanning the frame (its tallest side over 80 % of the frame's height);
- a close-up taken from a print_check JSON's thin spots: written, and framed on something;
- a close-up aimed at empty space: the frame is empty, exit 1 — never an image that shows nothing;
- an unknown view, or a missing file: exit 1, no traceback;
- --close with negative coordinates (a spot left of or in front of the axis) is read as a value,
  not as an option: a session's `--close -25,-14,54,14` stopped argparse before this.
"""
import json, os, struct, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_renders.py")
QUADS = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def block(path, x, y, z):
    v = [(0, 0, 0), (x, 0, 0), (x, y, 0), (0, y, 0), (0, 0, z), (x, 0, z), (x, y, z), (0, y, z)]
    tris = [[v[i] for i in t] for a, b, c, d in QUADS for t in ((a, b, c), (a, c, d))]
    with open(path, "wb") as f:
        f.write(b"test_review_renders".ljust(80, b" ")); f.write(struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<3f", 0, 0, 0))
            for p in t:
                f.write(struct.pack("<3f", *p))
            f.write(b"\0\0")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def span(path):
    """The subject's tallest extent in the frame, as a share of its height — read with Blender."""
    code = (f"import bpy, numpy as np; im = bpy.data.images.load({path!r}); w, h = im.size; "
            "px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3]; "
            "m = np.abs(px - px[0, 0]).max(axis=2) > 0.03; rows = np.flatnonzero(m.any(axis=1)); "
            "print('SPAN', (rows.max() - rows.min() + 1) / h if len(rows) else 0)")
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-expr", code], capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines() if l.startswith("SPAN ")), "SPAN 0")
    return float(line.split()[1])


def run(*extra):
    p = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", TOOL, "--", *extra],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


checks = []
def check(name, ok, got=""):
    checks.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"   got: {got}"))


with tempfile.TemporaryDirectory() as d:
    block(f"{d}/block.stl", 20, 10, 40)

    rc, log = run(f"{d}/block.stl", "--out", f"{d}/a", "--views", "front,q1,top", "--res", "400")
    files = sorted(os.listdir(f"{d}/a")) if os.path.isdir(f"{d}/a") else []
    want = sorted(f"block_{m}_{v}.png" for m in ("matcap", "colour") for v in ("front", "q1", "top"))
    check("block: exit 0, one PNG per view and mode", rc == 0 and files == want, (rc, files, log[-300:]))
    check("block: every image 400 x 400", files and all(png_size(f"{d}/a/{f}") == (400, 400) for f in files),
          [png_size(f"{d}/a/{f}") for f in files])
    if rc == 0:
        sp = span(f"{d}/a/block_matcap_front.png")
        check("block, front: the 40 mm side spans over 80 % of the frame", 0.8 < sp < 0.95, round(sp, 3))

    json.dump({"thickness": {"thin_at": [{"at_mm": [20, 5, 20], "wall_mm": 0.5}]}}, open(f"{d}/check.json", "w"))
    rc, log = run(f"{d}/block.stl", "--out", f"{d}/b", "--views", "q1", "--mode", "matcap", "--close-from", f"{d}/check.json")
    check("close-up from print_check's thin spots: written", rc == 0 and os.path.isfile(f"{d}/b/block_matcap_close1.png"),
          (rc, log[-300:]))

    rc, log = run(f"{d}/block.stl", "--out", f"{d}/c", "--views", "q1", "--mode", "matcap", "--close", "500,500,500,5")
    check("close-up on empty space: exit 1, said empty", rc == 1 and "nothing framed" in log and "Traceback" not in log,
          (rc, log[-300:]))

    rc, log = run(f"{d}/block.stl", "--out", f"{d}/n", "--views", "q1", "--mode", "matcap", "--close", "-1,-1,20,12")
    check("close-up at negative coordinates: read as a value, written",
          rc == 0 and os.path.isfile(f"{d}/n/block_matcap_close1.png"), (rc, log[-300:]))

    rc, log = run(f"{d}/block.stl", "--out", f"{d}/e", "--views", "sideways")
    check("unknown view: exit 1, no traceback", rc == 1 and "unknown view" in log and "Traceback" not in log, (rc, log[-200:]))
    rc, log = run(f"{d}/none.stl", "--out", f"{d}/f")
    check("missing file: exit 1, no traceback", rc == 1 and "no such file" in log and "Traceback" not in log, (rc, log[-200:]))

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
