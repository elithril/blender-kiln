#!/usr/bin/env python3
"""Check review_renders.py renders what it says.

    python3 tools/test_review_renders.py      # needs Blender at $BLENDER or the macOS default

- a 20 x 10 x 40 mm block (STL, mm): exit 0, one PNG per view and mode, each the --res asked,
  the subject spanning the frame (its tallest side over 80 % of the frame's height);
- a close-up taken from a print_check JSON's thin spots: written, and framed on something;
- a close-up aimed at empty space: the frame is empty, exit 1 — never an image that shows nothing;
- a rigged GLB, its bones shown by a 2 m sphere as the glTF importer does: the frame is the
  model's, not the sphere's;
- a textured GLB in colour: the texture shows (two colours), not the material's flat grey;
- a vertex-coloured GLB in colour: its vertex colours show, and a part beside it with a plain
  material keeps that material's colour (the cat's fur rendered grey before);
- a close-up on a low part just behind a taller one: seen along the surface's normal, not
  through the taller part — the side it used to choose is reported HIDDEN;
- an unknown view, or a missing file: exit 1, no traceback;
- --close with negative coordinates (a spot left of or in front of the axis) is read as a value,
  not as an option: a session's `--close -25,-14,54,14` stopped argparse before this.
"""
import json, os, struct, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_renders.py")
QUADS = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def block(path, x, y, z, more=()):
    """A box from the origin; more: further boxes (x0, y0, z0, x1, y1, z1) in the same file."""
    tris = []
    for x0, y0, z0, x1, y1, z1 in ((0, 0, 0, x, y, z),) + tuple(more):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        tris += [[v[i] for i in t] for a, b, c, d in QUADS for t in ((a, b, c), (a, c, d))]
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


MAKE_GLB = """
import bpy, sys
out, kind = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, 0, 0.1)); body = bpy.context.object
if kind == "rigged":
    bpy.ops.object.armature_add(location=(0, 0, 0)); arm = bpy.context.object
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, location=(3, 0, 0)); shape = bpy.context.object
    arm.pose.bones[0].custom_shape = shape
    body.parent = arm; body.modifiers.new("a", "ARMATURE").object = arm
    body.vertex_groups.new(name=arm.pose.bones[0].name).add(list(range(8)), 1.0, "REPLACE")
    bpy.data.objects.remove(shape)
    bpy.ops.object.select_all(action="SELECT")
elif kind == "painted":
    # vertex colours, red on one half and blue on the other, read by the material (COLOR_0 in glTF);
    # beside it an eye-like part with a plain green material and no vertex colour
    me = body.data; ca = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for poly in me.polygons:
        for li in poly.loop_indices:
            x = me.vertices[me.loops[li].vertex_index].co.x
            ca.data[li].color = (1, 0, 0, 1) if x < 0 else (0, 0, 1, 1)
    m = bpy.data.materials.new("Fur"); m.use_nodes = True
    attr = m.node_tree.nodes.new("ShaderNodeVertexColor"); attr.layer_name = "Col"
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    m.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    body.data.materials.append(m)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, -0.12, 0.15)); eye = bpy.context.object
    g = bpy.data.materials.new("Eye"); g.use_nodes = True
    next(n for n in g.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0, 1, 0, 1)
    eye.data.materials.append(g)
    bpy.ops.object.select_all(action="SELECT")
else:
    img = bpy.data.images.new("T", 8, 8); px = []
    for y in range(8):
        for x in range(8):
            px += [1, 0, 0, 1] if x < 4 else [0, 0, 1, 1]
    img.pixels = px
    m = bpy.data.materials.new("M"); m.use_nodes = True
    tex = m.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
    m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    body.data.materials.append(m)
    bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True,
                          **({"export_vertex_color": "MATERIAL"} if kind == "painted" else {}))
"""


def make_glb(d, kind):
    open(f"{d}/make_glb.py", "w").write(MAKE_GLB)
    out = f"{d}/{kind}.glb"
    subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", f"{d}/make_glb.py",
                    "--", out, kind], capture_output=True, text=True)
    return out


def colours(path):
    """How many clearly different hues the subject shows — read with Blender."""
    code = (f"import bpy, numpy as np; im = bpy.data.images.load({path!r}); w, h = im.size; "
            "px = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]; bg = px[0]; "
            "fg = px[np.abs(px - bg).max(axis=1) > 0.05]; "
            "r = ((fg[:, 0] > fg[:, 2] + 0.15).mean() if len(fg) else 0); b = ((fg[:, 2] > fg[:, 0] + 0.15).mean() if len(fg) else 0); "
            "g = ((fg[:, 1] > np.maximum(fg[:, 0], fg[:, 2]) + 0.15).mean() if len(fg) else 0); "
            "print('HUES', round(float(r), 3), round(float(b), 3), round(float(g), 3))")
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-expr", code], capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines() if l.startswith("HUES ")), "HUES 0 0 0")
    return tuple(float(x) for x in line.split()[1:])


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

    # a "head" in front (-Y) of a low "body": a spot on the body's top, just behind the head, was
    # shot from the front through the head (the cat's nape); seen along its normal it is not
    block(f"{d}/nape.stl", 20, 10, 40, more=((0, 10, 0, 20, 60, 15),))
    rc, log = run(f"{d}/nape.stl", "--out", f"{d}/k", "--views", "q1", "--mode", "matcap",
                  "--close", "10,20,15,12", "--close", "10,20,15,12,0,20")
    lines = [l for l in log.splitlines() if "close" in l and l.startswith("RENDER")]
    check("close-up behind a taller part: seen along its normal, not hidden; the old side is reported HIDDEN",
          rc == 0 and len(lines) == 2 and "HIDDEN" not in lines[0] and "HIDDEN" in lines[1], (rc, lines, log[-300:]))

    rigged = make_glb(d, "rigged")
    rc, log = run(rigged, "--out", f"{d}/g", "--views", "front", "--mode", "matcap", "--res", "400")
    sp = span(f"{d}/g/rigged_matcap_front.png") if rc == 0 else 0
    check("rigged GLB: framed on the model, not on the 2 m bone sphere (over 70 % of the height)",
          rc == 0 and sp > 0.7, (rc, round(sp, 3), log[-200:]))
    textured = make_glb(d, "textured")
    rc, log = run(textured, "--out", f"{d}/h", "--views", "front", "--mode", "colour", "--res", "400")
    hues = colours(f"{d}/h/textured_colour_front.png") if rc == 0 else (0, 0)
    check("textured GLB in colour: its red and blue texture show, not a flat grey",
          rc == 0 and hues[0] > 0.2 and hues[1] > 0.2, (rc, hues, log[-200:]))

    painted = make_glb(d, "painted")
    rc, log = run(painted, "--out", f"{d}/p", "--views", "front", "--mode", "colour", "--res", "400")
    hues = colours(f"{d}/p/painted_colour_front.png") if rc == 0 else (0, 0, 0)
    check("vertex-coloured GLB in colour: its red and blue vertex colours show, and the green part beside it",
          rc == 0 and hues[0] > 0.1 and hues[1] > 0.1 and hues[2] > 0.01, (rc, hues, log[-200:]))

    rc, log = run(f"{d}/block.stl", "--out", f"{d}/e", "--views", "sideways")
    check("unknown view: exit 1, no traceback", rc == 1 and "unknown view" in log and "Traceback" not in log, (rc, log[-200:]))
    rc, log = run(f"{d}/none.stl", "--out", f"{d}/f")
    check("missing file: exit 1, no traceback", rc == 1 and "no such file" in log and "Traceback" not in log, (rc, log[-200:]))

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
