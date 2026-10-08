"""Renders the chest at four poses of its loop from two angles, for review (rule 2).

    blender -b examples/animation/out/chest/chest.blend --python-exit-code 1 --python render_review.py
"""
import math, os, bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "work"); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in sc.render.bl_rna.properties["engine"].enum_items] else sc.render.engine
sc.render.resolution_x = sc.render.resolution_y = 640; sc.render.film_transparent = True
w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs["Color"].default_value = (0.08, 0.06, 0.05, 1); bg.inputs["Strength"].default_value = 0.6
for name, loc, e, col in (("Key", (1.5, -2, 2.4), 600, (1, .8, .6)), ("Rim", (-1.8, 1.6, 1.5), 300, (1, .5, .2)), ("Fill", (-2, -1.5, 1), 120, (.7, .8, 1))):
    L = bpy.data.lights.new(name, "AREA"); L.energy = e; L.color = col; L.size = 1.5
    o = bpy.data.objects.new(name, L); o.location = loc; sc.collection.objects.link(o)
    o.rotation_euler = (Vector((0, 0, .25)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
for tag, ang in (("front", -35), ("back", 145)):
    a = math.radians(ang); cam.location = (math.sin(a) * -1.9, -math.cos(a) * 1.9, 1.05)
    cam.rotation_euler = (Vector((0, 0, .28)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    for f in ((0, 12, 40, 56) if tag == "front" else (0, 40)):
        sc.frame_set(f); sc.render.filepath = os.path.join(OUT, f"chest_{tag}_{f:02d}.png"); bpy.ops.render.render(write_still=True)
print("RENDERED")
