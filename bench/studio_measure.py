"""Every mesh object of two GLBs, before and after a Studio note: its world bounds.

    blender --background --factory-startup --python bench/studio_measure.py -- BEFORE.glb AFTER.glb

Prints one line `STUDIO_JSON {"before": {name: {"min", "max", "size", "tris"}}, "after": {...}}`.
Judging is the driver's (studio_drive.py): this only reads the files.
"""
import json
import sys

import bpy
from mathutils import Vector


def objects(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    out = {}
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        if not pts:
            continue
        mn = [min(p[i] for p in pts) for i in range(3)]
        mx = [max(p[i] for p in pts) for i in range(3)]
        out[o.name] = {"min": [round(x, 5) for x in mn], "max": [round(x, 5) for x in mx],
                       "size": [round(mx[i] - mn[i], 5) for i in range(3)],
                       "tris": sum(len(p.vertices) - 2 for p in o.data.polygons)}
    return out


before, after = sys.argv[sys.argv.index("--") + 1:][:2]
print("STUDIO_JSON " + json.dumps({"before": objects(before), "after": objects(after)}))
