#!/usr/bin/env python3
"""Check review_sheet.py shows the model, framed, whatever its place.

    python3 tools/test_review_sheet.py      # needs Blender at $BLENDER or the macOS default

- a 0.3 m crate 5 m off the origin, as a GLB: exit 0, six tiles at the --res asked and the
  3 x 2 sheet, every tile's subject over 10 % of it — framed on the vertices, not on the origin;
- painted near-black: the colour sheet's exposure moved one stop at most (pushed further, a dark
  lantern's colours shifted and the session "fixed" them), the clay sheet's subject at 0.3-0.6;
- a missing model: exit 1, no traceback.
"""
import os, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_sheet.py")
FAILS, RUN = [], []


def check(what, ok, detail=""):
    RUN.append(what)
    print(f"  {'ok  ' if ok else 'FAIL'} {what}" + (f" — {detail}" if not ok and detail else ""))
    if not ok:
        FAILS.append(what)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def main():
    if not os.path.exists(BLENDER):
        print("  skip: no Blender")
        return 0
    print("── test_review_sheet")
    tmp = tempfile.mkdtemp(prefix="kiln_sheet_")
    glb = os.path.join(tmp, "crate.glb")
    subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python-expr",
                    "import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); "
                    "bpy.ops.mesh.primitive_cube_add(size=0.3, location=(5, 3, 0.15)); "
                    "m = bpy.data.materials.new('dark'); m.use_nodes = True; "
                    "next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.02, 0.025, 0.015, 1); "
                    "bpy.context.object.data.materials.append(m); "
                    f"bpy.ops.export_scene.gltf(filepath={glb!r}, export_format='GLB')"],
                   check=True, capture_output=True)
    out = os.path.join(tmp, "sheet.png")
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", TOOL, "--",
                        glb, "--out", out, "--res", "200"], capture_output=True, text=True)
    views = [l.split() for l in r.stdout.splitlines() if l.startswith("VIEW ")]
    clay = out[:-4] + "_clay.png"
    check("a crate 5 m off the origin: exit 0, six views on each sheet, both sheets",
          r.returncode == 0 and len(views) == 12 and os.path.exists(out) and os.path.exists(clay),
          r.stdout[-400:] + r.stderr[-400:])
    if r.returncode == 0:
        check("each tile at the --res asked, each sheet 3 x 2 of them",
              all(png_size(v[2]) == (200, 200) for v in views) and png_size(out) == png_size(clay) == (600, 400),
              [png_size(v[2]) for v in views] + [png_size(out), png_size(clay)])
        ex = {l.split()[1]: (float(l.split()[2]), float(l.split()[-1])) for l in r.stdout.splitlines()
              if l.startswith("EXPOSURE ")}
        check(f"near-black: colour exposure one stop at most, clay subject 0.3-0.6 ({ex})",
              set(ex) == {"colour", "clay"} and abs(ex["colour"][0]) <= 1.0 and 0.3 <= ex["clay"][1] <= 0.6,
              r.stdout[-400:])
        cov = [float(v[4]) for v in views]
        check(f"the crate fills every tile (subject {min(cov):.0f}-{max(cov):.0f} %)", min(cov) > 10, cov)
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", TOOL, "--",
                        os.path.join(tmp, "none.glb"), "--out", out], capture_output=True, text=True)
    check("a missing model: exit 1, no traceback", r.returncode != 0 and "Traceback" not in r.stdout + r.stderr,
          (r.stdout + r.stderr)[-300:])
    print(f"── {len(RUN) - len(FAILS)}/{len(RUN)} checks pass")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
