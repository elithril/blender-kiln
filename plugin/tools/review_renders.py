"""The review renders, headless: what SKILL.md rule 2 asks for when no Blender is connected.

    blender -b --factory-startup --python-exit-code 1 --python tools/review_renders.py -- \\
        MODEL [MODEL ...] --out DIR [--views q1,q3,front,back,top,under] [--mode both] \\
        [--close X,Y,Z,SIZE[,AZ,EL] ...] [--close-from check.json] [--res 1000] [--prefix NAME]

Every print session of 2026-10-13 had no Blender to talk to and wrote its own render script;
one measured a height from bound_box and read 104.8 mm for 90.0. This is that script once:

- MODEL: STL (read as mm), GLB/glTF or .blend (metres), as many as there are parts; they
  are shown where they are — give the assembled GLB for the assembled object;
- framed on the VERTICES in world space, never on bound_box (a turned object's box is larger
  than the object): orthographic, each view fitted to the vertices as that camera sees them —
  the subject spans the frame's width or height, 7 % of margin each side;
- --mode matcap (grey matcap: the geometry, what the printer sees), colour (the materials,
  the paint plan), or both — an STL has no material, so colour needs the GLB or the .blend
  (STLs render grey, which a fox's session took for a fault); a textured model shows its
  textures, a vertex-coloured one its vertex colours (its other parts their materials'
  colours), an untextured one its materials' colours;
- a rigged glTF's bone display shape (a 2 m sphere the importer adds) is left out of the frame;
- --views from front, back, left, right, top, under and the four three-quarters q1-q4
  (front -Y); the default pairs two opposite three-quarters, as rule 2 asks, with top and under;
- --close X,Y,Z,SIZE (mm) renders a close-up there, seen along the surface's normal at that spot
  (a nape seen "from outside the axis" was shot from the front, through the head); the line
  says HIDDEN when the camera still meets another surface first; AZ,EL (degrees, as the
  views: front -Y) choose the side yourself — a grazing look shows a dent's profile;
- a rigged model is shown in its rest pose, the pose its vertices are framed on;
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
    # A rigged glTF brings its bones' display shape along — a 2 m Icosphere in the
    # "glTF_not_exported" collection — and framing on it left a dog 2 % of the frame.
    shapes = {pb.custom_shape for o in bpy.data.objects if o.type == "ARMATURE" and o.pose
              for pb in o.pose.bones if pb.custom_shape}
    new = []
    for o in bpy.data.objects:
        if o in before or o.type != "MESH":
            continue
        if o in shapes or any(c.name.startswith("glTF_not_exported") for c in o.users_collection):
            o.hide_render = True
            continue
        new.append(o)
    if not new:
        die(f"{path}: no mesh in it")
    for o in bpy.data.objects:                  # framed on the rest vertices: show the rest pose, not a clip's frame
        if o.type == "ARMATURE":
            o.data.pose_position = "REST"
    return new


def closes(a, centre_m):
    out = []
    for c in a.close:
        try:
            v = [float(x) for x in c.split(",")]
            assert len(v) in (4, 6)
        except (ValueError, AssertionError):
            die(f"--close {c}: X,Y,Z,SIZE in mm, optionally AZ,EL in degrees")
        out.append((Vector(v[:3]) / 1000, v[3] / 1000, tuple(v[4:]) or None))
    if a.close_from:
        spots = json.load(open(a.close_from)).get("thickness", {}).get("thin_at", [])
        out += [(Vector(q["at_mm"]) / 1000, 0.012, None) for q in spots[:4]]
    return out


def base_colour(m):
    if m is None:
        return (0.8, 0.8, 0.8, 1.0)
    bsdf = next((n for n in (m.node_tree.nodes if m.node_tree else []) if n.type == "BSDF_PRINCIPLED"), None)
    return tuple(bsdf.inputs["Base Color"].default_value) if bsdf else tuple(m.diffuse_color)


def vertex_colours(o):
    """Workbench shows one colour source for every object: the painted ones their vertex colours,
    the others (eyes, a nose) their material's colour, written as vertex colours."""
    me = o.data
    if me.color_attributes:
        if me.color_attributes.active_color is None:
            me.color_attributes.active_color = me.color_attributes[0]
        return
    ca = me.color_attributes.new("review_colour", "BYTE_COLOR", "CORNER")
    cols = [base_colour(s.material) for s in o.material_slots] or [base_colour(None)]
    for poly in me.polygons:
        c = cols[min(poly.material_index, len(cols) - 1)]
        for li in poly.loop_indices:
            ca.data[li].color = c
    me.color_attributes.active_color = ca


def facing(meshes, V, N, at, s, centre):
    """A close-up looks at the surface along its normal there: seen "from outside the axis", a
    spot on the back's midline (a cat's nape) was shot from the front, through the head."""
    near = np.linalg.norm(V - np.array(at[:]), axis=1) < s / 4
    if near.sum() >= 20:                      # a dense skin: the mean normal around the spot
        n = Vector(N[near].mean(axis=0).tolist())
    else:                                     # a coarse mesh: the normal of the face nearest the spot
        best = None
        for o in meshes:
            inv = o.matrix_world.inverted()
            hit, loc, nor, _ = o.closest_point_on_mesh(inv @ at)
            if hit:
                d = (o.matrix_world @ loc - at).length
                if best is None or d < best[0]:
                    best = (d, o.matrix_world.to_3x3() @ nor)
        n = best[1] if best and best[0] < s else Vector()   # no surface within the frame: nothing to face
    if n.length < 1e-6:                       # no surface there: from outside the axis, as before
        out = Vector((at.x - centre.x, at.y - centre.y, 0))
        n = out if out.length > 1e-9 else Vector((0, -1, 0))
    n = n.normalized()
    if abs(n.z) > 0.9999:                     # straight up or down: the camera's up axis needs a tilt
        n = Vector((0, -0.002, math.copysign(1, n.z))).normalized()
    return n


BACKGROUND = 0.2235      # Workbench's own grey, kept so the images look as they always did


def cover(path):
    """The share of the frame the subject covers, read from the render's alpha — a corner taken
    as the background called a close-up filled by one flat face empty — then the image is put
    back on an opaque grey."""
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    a = px[:, 3:4].copy()
    px[:, :3] = px[:, :3] * a + BACKGROUND * (1 - a); px[:, 3] = 1.0
    img.pixels = px.ravel().tolist(); img.filepath_raw = path; img.file_format = "PNG"; img.save()
    bpy.data.images.remove(img)
    return float((a > 0.5).mean())


def main():
    a = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    meshes = [o for m in a.models for o in load(m)]
    bpy.context.view_layer.update()
    V = np.array([tuple(o.matrix_world @ v.co) for o in meshes for v in o.data.vertices])
    N = np.array([tuple((o.matrix_world.to_3x3() @ v.normal).normalized()) for o in meshes for v in o.data.vertices])
    lo, hi = V.min(axis=0), V.max(axis=0)
    centre = Vector(((lo + hi) / 2).tolist())
    size = float(np.linalg.norm(hi - lo)) * 1.05                 # the diagonal: any view fits
    os.makedirs(a.out, exist_ok=True)
    prefix = a.prefix or os.path.splitext(os.path.basename(a.models[0]))[0]

    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True             # the alpha says where the subject is (cover)
    sc.display.shading.show_cavity = False
    sc.display.shading.show_object_outline = False
    sc.world = sc.world or bpy.data.worlds.new("World")
    cd = bpy.data.cameras.new("ReviewCam")
    cd.type = "ORTHO"
    cd.clip_start, cd.clip_end = 1e-4, 100.0
    cam = bpy.data.objects.new("ReviewCam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam

    def towards(az, el):
        az, el = math.radians(az), math.radians(el)
        return Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))

    shots = [(v, None, None, towards(*DIRS[v])) for v in a.views.split(",")]
    for n, (at, s, view) in enumerate(closes(a, centre), 1):
        shots.append((f"close{n}", at, s, towards(*view) if view else facing(meshes, V, N, at, s, centre)))

    modes = ["matcap", "colour"] if a.mode == "both" else [a.mode]
    written = []
    for mode in modes:
        sh = sc.display.shading
        sh.light = "MATCAP" if mode == "matcap" else "STUDIO"
        # MATERIAL shows a material's flat colour only: a textured body rendered grey, read as a fault,
        # and so did a body painted with vertex colours (COLOR_0, the cat's fur)
        textured = any(n.type == "TEX_IMAGE" for o in meshes for m in o.data.materials if m and m.node_tree
                       for n in m.node_tree.nodes)
        painted = not textured and any(o.data.color_attributes for o in meshes)
        if mode != "matcap" and painted:
            for o in meshes:
                vertex_colours(o)
        sh.color_type = "SINGLE" if mode == "matcap" else ("TEXTURE" if textured else "VERTEX" if painted else "MATERIAL")
        sh.single_color = (0.8, 0.8, 0.8)
        for name, at, s, d in shots:
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
            hidden = ""
            if name.startswith("close"):              # what the camera meets first, on its way to the spot
                hit, loc = sc.ray_cast(bpy.context.evaluated_depsgraph_get(), cam.location, -d)[:2]
                if hit and (loc - at).length > s / 4 and (cam.location - loc).length < (cam.location - at).length:
                    hidden = f", HIDDEN: the camera meets the surface {1000 * (loc - at).length:.0f} mm before the spot"
            print(f"RENDER {path} (subject {100 * c:.0f} % of the frame{hidden})")
            written.append(path)
    print(f"review_renders: {len(written)} image(s) in {os.path.abspath(a.out)}")


try:
    main()
except SystemExit:
    raise
except Exception as e:                                     # fail loud: --python-exit-code turns this into 1
    die(f"{type(e).__name__}: {e}")
