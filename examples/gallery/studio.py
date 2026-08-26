"""Shared studio rig for the gallery: lighting, framing, render, export, metrics.

Run through Blender, never as plain Python:
    blender --background --factory-startup --python build.py -- <asset> <outdir>
"""
import bpy, bmesh, json, math, os, time
from mathutils import Vector

def srgb(hex_str):
    """sRGB hex -> linear RGBA.

    Principled BSDF inputs are LINEAR, not sRGB. Feeding sRGB values straight in
    washes everything out: linear 0.31 is sRGB 0.58, so a hex-picked magenta
    lands as pale pink and rich wood lands as light tan.
    """
    h = hex_str.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


# Palette lifted from the project logo: slate-blue stone, warm forge orange.
STONE    = srgb('#2E3A52')
STONE_LT = srgb('#4A5B7E')
WOOD     = srgb('#6B4423')
WOOD_LT  = srgb('#8A5A2E')
IRON     = srgb('#2A2E36')
IRON_LT  = srgb('#525A64')   # for objects that are ALL metal: see anvil()
STEEL    = srgb('#8A929C')
BRASS    = srgb('#96672A')
EMBER    = srgb('#FF6A1A')
CRYSTAL  = srgb('#E0455C')
BACKDROP = srgb('#0B1020')
GROUND   = srgb('#10141F')


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, base, rough=0.5, metal=0.0, emit=None, emit_str=0.0, alpha=1.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = base
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['IOR'].default_value = ior
    if emit:
        b.inputs['Emission Color'].default_value = emit
        b.inputs['Emission Strength'].default_value = emit_str
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'
    return m


def shade(obj, smooth=True, angle=32.0):
    """Smooth-shade with an angle split, so bevels read soft and facets stay crisp."""
    obj.data.use_auto_smooth = True if hasattr(obj.data, 'use_auto_smooth') else None
    for p in obj.data.polygons:
        p.use_smooth = smooth
    if smooth:
        m = obj.modifiers.new('Smooth by Angle', 'NODES')
        try:
            ng = bpy.data.node_groups.get('Smooth by Angle')
            if ng is None:
                bpy.ops.object.modifier_remove(modifier=m.name)
                return
            m.node_group = ng
            m['Socket_1'] = math.radians(angle)
        except Exception:
            obj.modifiers.remove(m)


def bevel(obj, width=0.01, segments=2, angle=40.0):
    m = obj.modifiers.new('Bevel', 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.harden_normals = False
    return m


def join(objs, name):
    objs = [o for o in objs if o and o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    return o


def apply_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception:
            obj.modifiers.remove(m)


def cleanup(obj, merge=0.0004):
    """The CLEANUP phase, headless: merge doubles, recalc normals, origin to base."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    before = len(bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.location = (0, 0, 0)
    # Flush the new location before reading matrix_world: writing to location does
    # not refresh the matrix, so reading it here returns the PREVIOUS transform and
    # zmin comes back 0. The correction below then does nothing and the asset ends
    # up half-buried under the ground plane.
    bpy.context.view_layer.update()
    # Sit the asset on Z=0, the convention every export target expects.
    zmin = min((obj.matrix_world @ Vector(c)).z for c in obj.bound_box)
    obj.location.z -= zmin
    bpy.context.view_layer.update()
    return before


def tri_count(obj):
    me = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    return n


def backdrop(scene, radius=14.0):
    """Dark studio ground + world, matched to the repo's social card."""
    world = bpy.data.worlds.new("studio")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = BACKDROP
    bg.inputs['Strength'].default_value = 0.42

    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=radius, fill_type='NGON')
    g = bpy.context.object
    g.name = "ground"
    g.data.materials.append(mat("ground", GROUND, rough=0.62))
    return g


def three_point(scene, size):
    """Key / fill / rim / amber accent, scaled to the subject.

    Energies are absolute watts calibrated for a ~0.9 m subject and rescaled by
    (size/0.9)^2, since illuminance falls off with the square of the distance and
    every light is placed as a multiple of `size`.
    """
    s = max(size, 0.35)
    k = (s / 0.9) ** 2
    specs = [
        ("key",   115.0 * k, 3.2 * s, ( 2.6 * s, -2.2 * s,  3.1 * s), (0.85, 0.18, 0.86),  (1.0, 0.97, 0.93)),
        ("fill",   26.0 * k, 4.5 * s, (-3.0 * s, -1.7 * s,  1.5 * s), (1.16, -0.1, -1.05), (0.82, 0.88, 1.0)),
        ("rim",    72.0 * k, 2.0 * s, (-1.4 * s,  3.0 * s,  2.4 * s), (1.05, 0.05, -2.65), (0.90, 0.94, 1.0)),
        ("amber",  30.0 * k, 1.6 * s, ( 1.1 * s,  2.2 * s,  0.5 * s), (1.45, 0.0, -2.2),   (1.0, 0.52, 0.24)),
    ]
    for name, energy, sz, loc, rot, col in specs:
        l = bpy.data.lights.new(name, 'AREA')
        l.energy = energy
        l.size = sz
        l.color = col
        o = bpy.data.objects.new(name, l)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot


def frame(scene, obj, margin=1.10, elev=0.42, azim=-0.62, lens=72.0):
    """Place a camera on a fixed 3/4 orbit, then fit the subject's silhouette.

    Fitting the bounding sphere wastes frame on squat objects, so this projects
    the eight box corners onto the camera plane and fits that extent instead.
    """
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    center = sum(corners, Vector()) / 8.0

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = lens
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam

    d = Vector((math.cos(elev) * math.cos(azim), math.cos(elev) * math.sin(azim), math.sin(elev)))
    fov = 2.0 * math.atan(cam_d.sensor_width / (2.0 * cam_d.lens))

    right = d.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(d).normalized()
    half = max(max(abs((c - center).dot(right)) for c in corners),
               max(abs((c - center).dot(up)) for c in corners))
    depth = max((c - center).dot(d) for c in corners)
    dist = (half * margin) / math.tan(fov / 2.0) + depth

    cam.location = center + d * dist
    fwd = (center - cam.location).normalized()
    cam.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler()
    return half


def render(scene, path, res=1100, samples=96, exposure=0.0):
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = path
    # Blender 5's EEVEE dropped use_gtao / use_bloom; raytracing covers both.
    ee = scene.eevee
    ee.taa_render_samples = samples
    ee.use_shadows = True
    ee.use_raytracing = True
    ee.shadow_ray_count = 4
    ee.shadow_step_count = 12
    # AgX desaturates saturated albedo hard — a magenta crystal lands pale salmon.
    # Khronos PBR Neutral preserves hue while still rolling off highlights; plain
    # Standard is the fallback on builds that lack it.
    opts = [i.identifier for i in
            scene.view_settings.bl_rna.properties['view_transform'].enum_items]
    for want in ('Khronos PBR Neutral', 'Standard'):
        if want in opts:
            scene.view_settings.view_transform = want
            break
    scene.view_settings.exposure = exposure
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t


def export_glb(obj, path, draco=False):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Iron rule 6: never export_apply for GLTF.
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True,
        export_apply=False, export_yup=True,
        export_draco_mesh_compression_enable=draco,
    )
    return os.path.getsize(path)
