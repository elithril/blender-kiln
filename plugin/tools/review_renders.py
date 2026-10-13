"""The review renders, headless: what SKILL.md rule 2 asks for when no Blender is connected.

    blender -b --factory-startup --python-exit-code 1 --python tools/review_renders.py -- \\
        MODEL [MODEL ...] --out DIR [--views q1,q3,front,back,top,under] [--mode both] \\
        [--close X,Y,Z,SIZE ...] [--close-from check.json] [--res 1000] [--prefix NAME]

Every print session of 2026-10-13 had no Blender to talk to and wrote its own render script;
one measured a height from bound_box and read 104.8 mm for 90.0. This is that script once:

- MODEL: STL (read as mm), GLB/glTF or .blend (metres), as many as there are parts; they
  are shown where they are — give the assembled GLB for the assembled object;
- framed on the VERTICES in world space, never on bound_box (a turned object's box is larger
  than the object): orthographic, each view fitted to the vertices as that camera sees them —
  the subject spans the frame's width or height, 7 % of margin each side;
- --mode matcap (grey matcap: the geometry, what the printer sees), colour (the materials,
  the paint plan), or both;
- --views from front, back, left, right, top, under and the four three-quarters q1-q4
  (front -Y); the default pairs two opposite three-quarters, as rule 2 asks, with top and under;
- --close X,Y,Z,SIZE (mm) renders a close-up there, seen from outside the model's axis;
  --close-from takes the thin spots `print_check` lists (`thickness.thin_at`, the first 4);
- each image is read back: a view where the subject covers under 1 % of the frame (an
  unframed or empty render) is an error, exit 1.

Writes {prefix}_{mode}_{view}.png and {prefix}_{mode}_close{n}.png; prints RENDER <path> for each.
"""
import json, math, os, sys

import bpy
import numpy as np
from mathutils import Vector

DIRS = {  # camera direction toward the subject: azimuth, elevation (degrees); the front is -Y
    "front": (0, 8), "back": (180, 8), "left": (-90, 8), "right": (90, 8), "top": (0, 89.9),
    "under": (0, -89.9), "q1": (-40, 25), "q2": (40, 25), "q3": (140, 25), "q4": (220, 25),
}
MIN_COVER = 0.01


def die(msg):
    print(f"review_renders: {msg}", file=sys.stderr)
    sys.exit(1)


def args():
    import argparse
    p = argparse.ArgumentParser(prog="review_renders.py")
    p.add_argument("models", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--views", default="q1,q3,top,under")
    p.add_argument("--mode", choices=["matcap", "colour", "both"], default="both")
    p.add_argument("--close", action="append", default=[], help="X,Y,Z,SIZE in mm")
    p.add_argument("--close-from", help="a print_check JSON: close-ups at its first 4 thin spots")
    p.add_argument("--res", type=int, default=1000)
    p.add_argument("--prefix")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    # "--close -25,-14,54,14" — a spot left of or in front of the axis — reads as an option to
    # argparse and stopped a session: glue the value on, as --close=-25,-14,54,14
    glued, k = [], 0
    while k < len(argv):
        if argv[k] == "--close" and k + 1 < len(argv) and argv[k + 1].startswith("-"):
            glued.append("--close=" + argv[k + 1]); k += 2
        else:
            glued.append(argv[k]); k += 1
    argv = glued
    a = p.parse_args(argv)
    bad = [v for v in a.views.split(",") if v not in DIRS]
    if bad:
        die(f"unknown view(s) {bad}; known: {', '.join(DIRS)}")
    for m in a.models:
        if not os.path.isfile(m):
            die(f"no such file: {m}")
    return a


def load(path):
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)       # mm -> m
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".blend":
        with bpy.data.libraries.load(path) as (src, dst):
            dst.objects = list(src.objects)
        for o in dst.objects:
            if o is not None and o.type == "MESH":
                bpy.context.scene.collection.objects.link(o)
    else:
        die(f"{path}: STL, GLB/glTF or .blend")
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        die(f"{path}: no mesh in it")
    return new


def closes(a, centre_m):
    out = []
    for c in a.close:
        try:
            x, y, z, s = (float(v) for v in c.split(","))
        except ValueError:
            die(f"--close {c}: X,Y,Z,SIZE in mm")
        out.append((Vector((x, y, z)) / 1000, s / 1000))
    if a.close_from:
        spots = json.load(open(a.close_from)).get("thickness", {}).get("thin_at", [])
        out += [(Vector(q["at_mm"]) / 1000, 0.012) for q in spots[:4]]
    return out


def cover(path):
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
    bpy.data.images.remove(img)
    bg = px[0]                                                    # a corner: the background
    return float((np.abs(px - bg).max(axis=1) > 0.03).mean())


def main():
    a = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    meshes = [o for m in a.models for o in load(m)]
    bpy.context.view_layer.update()
    V = np.array([tuple(o.matrix_world @ v.co) for o in meshes for v in o.data.vertices])
    lo, hi = V.min(axis=0), V.max(axis=0)
    centre = Vector(((lo + hi) / 2).tolist())
    size = float(np.linalg.norm(hi - lo)) * 1.05                 # the diagonal: any view fits
    os.makedirs(a.out, exist_ok=True)
    prefix = a.prefix or os.path.splitext(os.path.basename(a.models[0]))[0]

    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.render.image_settings.file_format = "PNG"
    sc.display.shading.show_cavity = False
    sc.display.shading.show_object_outline = False
    sc.world = sc.world or bpy.data.worlds.new("World")
    cd = bpy.data.cameras.new("ReviewCam")
    cd.type = "ORTHO"
    cd.clip_start, cd.clip_end = 1e-4, 100.0
    cam = bpy.data.objects.new("ReviewCam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam

    shots = [(v, None, None, DIRS[v]) for v in a.views.split(",")]
    for n, (at, s) in enumerate(closes(a, centre), 1):
        out = Vector((at.x - centre.x, at.y - centre.y, 0))      # from outside the axis, toward the spot
        az = math.degrees(math.atan2(out.x, -out.y)) if out.length > 1e-9 else 0.0
        shots.append((f"close{n}", at, s, (az, 20)))

    modes = ["matcap", "colour"] if a.mode == "both" else [a.mode]
    written = []
    for mode in modes:
        sh = sc.display.shading
        sh.light = "MATCAP" if mode == "matcap" else "STUDIO"
        sh.color_type = "SINGLE" if mode == "matcap" else "MATERIAL"
        sh.single_color = (0.8, 0.8, 0.8)
        for name, at, s, (az, el) in shots:
            az, el = math.radians(az), math.radians(el)
            d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
            rot = (-d).to_track_quat("-Z", "Y")
            if at is None:                    # a whole view: fit the vertices as this camera sees them
                R = np.array(rot.to_matrix())
                P = V @ R                     # columns: the camera's right, up, back
                plo, phi = P.min(axis=0), P.max(axis=0)
                mid = (plo + phi) / 2
                at = Vector((R @ mid).tolist())   # the middle of what it sees, back in world space
                s = float(max(phi[0] - plo[0], phi[1] - plo[1])) / 0.86
            cd.ortho_scale = s
            cam.location = at + d * max(size, s) * 4
            cam.rotation_euler = rot.to_euler()
            path = os.path.join(os.path.abspath(a.out), f"{prefix}_{mode}_{name}.png")
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            if not os.path.isfile(path):
                die(f"{path}: not written")
            c = cover(path)
            if c < MIN_COVER:
                die(f"{path}: the subject covers {100 * c:.2f} % of the frame — nothing framed")
            print(f"RENDER {path} (subject {100 * c:.0f} % of the frame)")
            written.append(path)
    print(f"review_renders: {len(written)} image(s) in {os.path.abspath(a.out)}")


try:
    main()
except SystemExit:
    raise
except Exception as e:                                     # fail loud: --python-exit-code turns this into 1
    die(f"{type(e).__name__}: {e}")
