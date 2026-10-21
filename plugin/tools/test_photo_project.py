#!/usr/bin/env python3
"""Seed what photo_project.py claims, and check it does.

    python3 tools/test_photo_project.py      # needs Blender at $BLENDER or the macOS default

No bench assets, no network: the test builds a 30 x 10 x 20 cm box with a plate on its
front, an "E" printed on the front — the truth —, photographs it from a known perspective
camera one stop and a third darker than the tool renders, cuts it out (alpha), and hands the
tool the same box WITHOUT the letter, as a session's scripted model would be. Cases:

- the projection recovers the letter: the front's texture correlates with the truth's
  (it did not before), and the SSIM from the photo's view rises while ΔE76 falls;
- the camera, started 5° off in azimuth and 3° in elevation, fits above 0.95 IoU;
- the photo is brought to the scan's exposure: the front's mean luminance stays the scan's,
  not the darker photo's (the raw pixels carry the photo's light);
- where the photo cannot see (the back) the shipped GLB's texture is the scan's, unchanged;
- --exclude Plate: the plate keeps its grey (the truth's is red; projected without the
  exclusion, it turns red);
- --erase-stencil: a scripted yellow mark on the front is gone where the photo is used, the
  same mark on the back (unseen) is kept;
- a box 40 % too long: the fitted IoU is under 0.95 — refused, exit 1, no GLB written;
- --exclude matching nothing, and --facing 0.5: exit 1, no traceback.
"""
import json, os, subprocess, sys, tempfile

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photo_project.py")

BUILD = r'''
import bpy, bmesh, math, sys
import numpy as np
from mathutils import Vector
d = sys.argv[sys.argv.index("--") + 1]
CELLS = {"front": (0, 0), "back": (1, 0), "right": (2, 0), "left": (0, 1), "top": (1, 1), "bottom": (2, 1)}

def box_faces(x0, x1, y0, y1, z0, z1):
    return {
        "front": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        "back": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        "right": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        "left": [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
        "top": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        "bottom": [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)]}

def cell_uv(face, lu, lv, m=0.02):
    c, r = CELLS[face]
    return (c / 3 + m + lu * (1 / 3 - 2 * m), r / 2 + m + lv * (1 / 2 - 2 * m))

def make_box(name, bounds, mat):
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    for face, cs in box_faces(*bounds).items():
        f = bm.faces.new([bm.verts.new(c) for c in cs])
        for loop, (lu, lv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv].uv = cell_uv(face, lu, lv)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    return ob

def material(name, px, size):
    img = bpy.data.images.new("T_" + name, size, size)
    img.pixels.foreach_set(np.ascontiguousarray(px, np.float32).ravel()); img.pack()
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = img
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8
    return m

def region(px, face, u0, u1, v0, v1, colour):
    S = px.shape[0]
    (a, b), (c, e) = cell_uv(face, u0, v0), cell_uv(face, u1, v1)
    px[int(b * S):int(e * S), int(a * S):int(c * S), :3] = colour

def box_texture(letter, stencil):
    S = 256
    yy, xx = np.mgrid[0:S, 0:S] / S
    px = np.ones((S, S, 4), np.float32)
    px[..., 0] = 0.25 + 0.04 * np.sin(xx * 40) * np.sin(yy * 31)
    px[..., 1] = 0.32 + 0.04 * np.sin(xx * 40) * np.sin(yy * 31)
    px[..., 2] = 0.20
    if letter:   # an "E", printed on the front
        for u0, u1, v0, v1 in ((0.15, 0.24, 0.2, 0.8), (0.15, 0.45, 0.2, 0.3), (0.15, 0.40, 0.45, 0.55), (0.15, 0.45, 0.7, 0.8)):
            region(px, "front", u0, u1, v0, v1, (0.92, 0.9, 0.85))
    if stencil:  # a scripted mark, on the front where the photo has none, and on the back
        for face in ("front", "back"):
            region(px, face, 0.5, 0.65, 0.55, 0.85, (0.85, 0.7, 0.1))
    return px

def build(path, letter=False, stencil=False, plate_red=False, sx=1.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_box("Box", (-0.15 * sx, 0.15 * sx, -0.05, 0.05, 0.0, 0.2), material("Box", box_texture(letter, stencil), 256))
    p = np.ones((64, 64, 4), np.float32); p[..., :3] = (0.7, 0.1, 0.1) if plate_red else (0.5, 0.5, 0.5)
    make_box("Plate", (0.06 * sx, 0.12 * sx, -0.058, -0.05, 0.05, 0.09), material("Plate", p, 64))
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB")

# the HDRI: a small flat-grey Radiance file
img = bpy.data.images.new("env", 16, 8, float_buffer=True)
img.pixels = [0.8, 0.8, 0.8, 1.0] * (16 * 8)
img.filepath_raw = f"{d}/env.hdr"; img.file_format = "HDR"; img.save()

build(f"{d}/scan.glb")
build(f"{d}/scan_stencil.glb", stencil=True)
build(f"{d}/scan_long.glb", sx=1.4)
build(f"{d}/truth.glb", letter=True, plate_red=True)
# the photo: the truth, from a known perspective camera, darker than the tool's light, cut out
sc = bpy.context.scene
w = bpy.data.worlds.new("w"); sc.world = w
env = w.node_tree.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(f"{d}/env.hdr")
w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
az, el, dist, ctr = math.radians(25), math.radians(15), 0.9, Vector((0, -0.004, 0.1))
cam.location = ctr + dist * Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 60
sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"
sc.view_settings.view_transform = "Standard"
sc.render.film_transparent = True; sc.render.image_settings.color_mode = "RGBA"
sc.render.resolution_x, sc.render.resolution_y = 384, 288
sc.render.filepath = f"{d}/photo.png"
bpy.ops.render.render(write_still=True)
'''

# Regions of a texture, read from a GLB: the front's correlation with the truth, the back's
# change against the scan, the plate's colour, the yellow mark's texels.
INSPECT = r'''
import bpy, json, sys
import numpy as np
glb, scan, truth, out = sys.argv[sys.argv.index("--") + 1:]
def tex(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    r = {}
    for im in bpy.data.images:
        if im.name.startswith("T_") and im.size[0]:
            w, h = im.size
            r[im.name] = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[..., :3]
    return r
A, S, T = tex(glb), tex(scan), tex(truth)
def cell(px, c, r, m=0.06):
    n = px.shape[0]
    return px[int((r / 2 + m) * n):int(((r + 1) / 2 - m) * n), int((c / 3 + m) * n):int(((c + 1) / 3 - m) * n)]
lum = lambda x: x @ np.array([0.2126, 0.7152, 0.0722])
fa, fs, ft = (lum(cell(X["T_Box"], 0, 0)).ravel() for X in (A, S, T))
yellow = lambda x: int(((x[..., 0] > 0.55) & (x[..., 1] > 0.45) & (x[..., 2] < 0.3)).sum())
json.dump(dict(
    front_corr=float(np.corrcoef(fa, ft)[0, 1]), scan_corr=float(np.corrcoef(fs, ft)[0, 1]),
    front_lum=float(fa[ft < 0.5].mean()), scan_front_lum=float(fs[ft < 0.5].mean()),   # the paint, off the letter
    back_change=float(np.abs(cell(A["T_Box"], 1, 0, 0.03) - cell(S["T_Box"], 1, 0, 0.03)).max()),
    plate_red=float((cell(A["T_Plate"], 0, 0, 0.12)[..., 0] - cell(A["T_Plate"], 0, 0, 0.12)[..., 1]).mean()),  # its front
    yellow_front=yellow(cell(A["T_Box"], 0, 0)), yellow_back=yellow(cell(A["T_Box"], 1, 0)),
), open(out, "w"))
'''


def blender(script, *args):
    return subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", script, "--", *args],
                          capture_output=True, text=True)


checks = []
def check(name, ok, got=""):
    checks.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"   got: {got}"))


def project(d, model, tag, *extra):
    out = f"{d}/{tag}"
    p = blender(TOOL, "--reference", f"{d}/photo.png", "--model", f"{d}/{model}", "--hdri", f"{d}/env.hdr",
                "--out", out, "--azimuth", "30", "--elevation", "12", "--samples", "8", *extra)
    try:
        r = json.load(open(f"{out}/photo_project.json"))
    except (OSError, ValueError):
        r = {}
    return p.returncode, p.stdout + p.stderr, r, out


def inspect(d, glb, scan="scan.glb"):
    blender(f"{d}/inspect.py", glb, f"{d}/{scan}", f"{d}/truth.glb", f"{d}/inspect.json")
    try:
        return json.load(open(f"{d}/inspect.json"))
    except (OSError, ValueError):
        return {}


with tempfile.TemporaryDirectory() as d:
    open(f"{d}/build.py", "w").write(BUILD); open(f"{d}/inspect.py", "w").write(INSPECT)
    b = blender(f"{d}/build.py", d)
    if b.returncode or not os.path.exists(f"{d}/photo.png"):
        print(b.stdout[-1500:], b.stderr[-1500:]); sys.exit(1)

    rc, log, r, out = project(d, "scan.glb", "plain")
    cam = r.get("camera", {}).get("fitted", {})
    pv = r.get("photo_view", {})
    check("projects, exit 0", rc == 0 and r.get("status") == "ok", (rc, log[-600:]))
    check("camera started 5° / 3° off fits above 0.95 IoU", cam.get("iou", 0) >= 0.95, cam)
    check("SSIM from the photo's view rises, ΔE76 falls",
          pv.get("after", {}).get("ssim", 0) > pv.get("before", {}).get("ssim", 1) + 0.02
          and pv.get("after", {}).get("dE76", 99) < pv.get("before", {}).get("dE76", 0), pv)
    s = inspect(d, f"{out}/scan_projected.glb")
    print(f"  measured: IoU {r.get('camera', {}).get('fidelity_check', {}).get('iou')} -> {cam.get('iou')}, "
          f"SSIM {pv.get('before', {}).get('ssim')} -> {pv.get('after', {}).get('ssim')}, "
          f"dE76 {pv.get('before', {}).get('dE76')} -> {pv.get('after', {}).get('dE76')}, "
          f"gain {r.get('exposure_gain_linear')}, front corr {s.get('scan_corr', 0):.2f} -> {s.get('front_corr', 0):.2f}")
    check("the letter is recovered: front texture correlates with the truth's",
          s.get("front_corr", 0) > 0.8 and s.get("scan_corr", 1) < 0.3, s)
    check("the photo is brought to the scan's exposure (front luminance within 15 % of the scan's)",
          abs(s.get("front_lum", 0) / max(s.get("scan_front_lum", 1e-6), 1e-6) - 1) < 0.15 and r.get("exposure_gain_linear", 0) > 1.5,
          (s, r.get("exposure_gain_linear")))
    check("where the photo cannot see (the back) the GLB keeps the scan's texture", s.get("back_change", 1) < 2 / 255, s)
    check("the plate, not excluded, takes the photo's red", s.get("plate_red", 0) > 0.25, s)

    rc, log, r, out = project(d, "scan.glb", "exclude", "--exclude", "plate")
    s = inspect(d, f"{out}/scan_projected.glb")
    check("--exclude plate: the plate keeps its grey, the box still projects",
          rc == 0 and abs(s.get("plate_red", 1)) < 0.01 and s.get("front_corr", 0) > 0.8, (rc, s, log[-400:]))

    rc, log, r, out = project(d, "scan_stencil.glb", "stencil", "--erase-stencil", "#D9B31A")
    s = inspect(d, f"{out}/scan_stencil_projected.glb", "scan_stencil.glb")
    st = r.get("images", {}).get("T_Box", {})
    check("--erase-stencil: the mark is gone where the photo is used, kept on the unseen back",
          rc == 0 and s.get("yellow_front", 99) < 20 and s.get("yellow_back", 0) > 300 and st.get("stencil_erased", 0) > 0
          and st.get("stencil_kept_unseen", 0) > 300, (rc, s, st, log[-400:]))

    rc, log, r, out = project(d, "scan_long.glb", "long")
    print(f"  measured: the long box fits {r.get('camera', {}).get('fitted', {}).get('iou')}")
    check("a box 40 % too long: refused under 0.95 IoU, exit 1, no GLB",
          rc == 1 and "IoU" in log and r.get("status") == "refused" and not os.path.exists(f"{out}/scan_long_projected.glb"),
          (rc, r.get("camera"), log[-300:]))

    rc, log, r, out = project(d, "scan.glb", "typo", "--exclude", "handle")
    check("--exclude matching nothing: exit 1, no traceback", rc == 1 and "matches no object" in log and "Traceback" not in log,
          (rc, log[-300:]))
    rc, log, r, out = project(d, "scan.glb", "facing", "--facing", "0.5")
    check("--facing under 0.6: exit 1, no traceback", rc == 1 and "facing" in log and "Traceback" not in log, (rc, log[-300:]))

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
