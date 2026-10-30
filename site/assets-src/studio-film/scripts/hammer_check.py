import bpy, sys
a = sys.argv[sys.argv.index("--") + 1:]
out = {}
for tag, glb in (("before", a[0]), ("after", a[1])):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    h = bpy.data.objects["SK_KilnSmith_Hammer"]
    out[tag] = [v.co.copy() for v in h.data.vertices]
    print(tag, len(h.data.vertices), "verts", [round(x, 3) for x in h.dimensions])
b, f = out["before"], out["after"]
if len(b) == len(f):
    d = [(x - y).length for x, y in zip(b, f)]
    print("SAME_COUNT max move", round(max(d), 4), "mean", round(sum(d) / len(d), 4))
