"""Gallery driver: model -> cleanup -> render -> GLB -> metrics.

    blender --background --factory-startup --python build.py -- <asset> <outdir>
"""
import bpy, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio as S
import assets as A

argv = sys.argv[sys.argv.index('--') + 1:]
name, outdir = argv[0], argv[1]
res = int(argv[2]) if len(argv) > 2 else 1100
samples = int(argv[3]) if len(argv) > 3 else 96
os.makedirs(outdir, exist_ok=True)

S.reset()
scene = bpy.context.scene

t0 = time.time()
obj = A.BUILDERS[name]()
faces_before = S.cleanup(obj)
tris = S.tri_count(obj)
model_s = time.time() - t0

raw = os.path.join(outdir, f"{name}_original.glb")
size_raw = S.export_glb(obj, raw)

theme, spec = A.theme_of(name)
size = max(obj.dimensions)
S.backdrop(scene, world_col=spec["world"], ground_col=spec["ground"])
S.three_point(scene, size, accent=spec["accent"], accent_gain=spec["accent_gain"])
S.frame(scene, obj)
png = os.path.join(outdir, f"{name}.png")
render_s = S.render(scene, png, res=res, samples=samples)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, f"{name}.blend"))

print("METRICS " + json.dumps({
    "asset": name, "theme": theme, "tris": tris, "faces_before_merge": faces_before,
    "glb_raw_bytes": size_raw, "model_s": round(model_s, 2),
    "render_s": round(render_s, 1), "dim_m": [round(d, 3) for d in obj.dimensions],
}))
