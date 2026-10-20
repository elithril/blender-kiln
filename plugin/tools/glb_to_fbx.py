"""A GLB to an FBX for Unity and Unreal, in Blender, headless and deterministic.

    blender -b --factory-startup --python tools/glb_to_fbx.py -- in.glb out.fbx

kiln's FBX settings (references/export-targets.md § FBX): FBX_SCALE_ALL with the unit
scale applied and the space transform baked (metres in, metres out in both engines),
face smoothing, deform bones only and no leaf bones, textures copied and embedded. Then
the FBX is read back in a clean scene and both sizes are printed:

    DIMS glb x y z
    DIMS fbx x y z
    FBX <path>

Exits 1 with `FAILED <reason>` otherwise.
"""
import sys

import bpy
from mathutils import Vector


def dims() -> tuple[float, float, float]:
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or not o.visible_get():   # the importer's hidden bone shapes are not the model
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return tuple(round(h - l, 4) for l, h in zip(lo, hi)) if hi.x > lo.x else (0.0, 0.0, 0.0)


def clear() -> None:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def main() -> None:
    a = sys.argv[sys.argv.index("--") + 1:]
    src, out = a[0], a[1]
    clear()
    bpy.ops.import_scene.gltf(filepath=src)
    bpy.context.view_layer.update()
    print("DIMS glb", *dims(), flush=True)
    for o in bpy.data.objects:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True,
                             apply_scale_options="FBX_SCALE_ALL", apply_unit_scale=True, bake_space_transform=True,
                             use_mesh_modifiers=True, mesh_smooth_type="FACE", use_armature_deform_only=True,
                             add_leaf_bones=False, path_mode="COPY", embed_textures=True, batch_mode="OFF")
    clear()
    bpy.ops.import_scene.fbx(filepath=out)
    bpy.context.view_layer.update()
    print("DIMS fbx", *dims(), flush=True)
    print(f"FBX {out}", flush=True)


try:
    main()
except Exception as e:
    print(f"FAILED {e!r}", flush=True)
    sys.exit(1)
