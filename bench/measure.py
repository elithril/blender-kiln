"""Measure one exported GLB the way a consumer receives it: re-imported, not trusted.

    blender --background --factory-startup --python-exit-code 1 --python bench/measure.py -- <file.glb> [out.json]

Prints one JSON object. Every number is read from the file or from Blender after
import — nothing is taken from the production log, because the log is written by
the same session whose output is being judged.
"""
import bpy, bmesh, json, math, os, struct, sys
from mathutils import Euler

argv = sys.argv[sys.argv.index('--') + 1:]
path = argv[0]
out = argv[1] if len(argv) > 1 else None


def glb_json(p):
    """The glTF JSON chunk, read directly — extensions and image sizes the importer hides."""
    with open(p, 'rb') as f:
        magic, _version, _length = struct.unpack('<4sII', f.read(12))
        if magic != b'glTF':
            raise SystemExit(f"not a GLB: {p}")
        chunk_len, chunk_type = struct.unpack('<I4s', f.read(8))
        if chunk_type != b'JSON':
            raise SystemExit(f"first chunk is not JSON: {p}")
        return json.loads(f.read(chunk_len))


gltf = glb_json(path)
report = {
    "file": os.path.basename(path),
    "bytes": os.path.getsize(path),
    "extensions_used": sorted(gltf.get("extensionsUsed", [])),
    "gltf_meshes": len(gltf.get("meshes", [])),
    "gltf_materials": len(gltf.get("materials", [])),
    "gltf_images": len(gltf.get("images", [])),
    "gltf_skins": len(gltf.get("skins", [])),
    "gltf_joints": sum(len(s.get("joints", [])) for s in gltf.get("skins", [])),
    "gltf_animations": len(gltf.get("animations", [])),
}

# meshopt is a web-runtime format Blender cannot import (README, gallery section).
# Measure the file anyway and say why the geometry half is missing.
if "EXT_meshopt_compression" in report["extensions_used"]:
    report["reimport"] = "skipped: EXT_meshopt_compression is not importable by Blender"
    print(json.dumps(report, indent=2))
    if out:
        json.dump(report, open(out, 'w'), indent=2)
    raise SystemExit(0)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
dg = bpy.context.evaluated_depsgraph_get()

arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
# The glTF importer builds an Icosphere as the display shape of imported bones.
# It is not in the file's geometry, yet it is a MESH object in the scene: counted,
# it put z_min at -1.0 on an arm that stands on the ground (measured).
shapes = {pb.custom_shape for a in arms for pb in a.pose.bones if pb.custom_shape}
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o not in shapes]

tris = verts = non_manifold = boundary = loose = degenerate = 0
zmin, lo, hi = math.inf, [math.inf] * 3, [-math.inf] * 3
for o in meshes:
    bm = bmesh.new()
    bm.from_object(o, dg)
    bm.transform(o.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris += len(bm.faces)
    verts += len(bm.verts)
    # glTF stores one vertex per UV/normal seam corner, and the importer keeps
    # them split: a closed barrel comes back with every edge open (measured —
    # 4,112 boundary edges on SM_Barrel). Weld coincident points before judging
    # topology, or every check below measures the file format, not the mesh.
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    for e in bm.edges:
        n = len(e.link_faces)
        if n == 0:
            loose += 1
        elif n == 1:
            boundary += 1
        elif n > 2:
            non_manifold += 1
    degenerate += sum(1 for f in bm.faces if f.calc_area() < 1e-10)
    for v in bm.verts:
        for i in range(3):
            lo[i] = min(lo[i], v.co[i])
            hi[i] = max(hi[i], v.co[i])
    bm.free()

dims = [round(hi[i] - lo[i], 4) for i in range(3)] if meshes else [0, 0, 0]
report.update({
    "objects_mesh": len(meshes),
    "object_names": sorted(o.name for o in meshes),
    "tris": tris,
    "verts": verts,
    # Edges shared by more than two faces. Boundary edges are reported apart:
    # an open mesh is legitimate for a leaf card, a fused one never is.
    "non_manifold_edges": non_manifold,
    "boundary_edges": boundary,
    "loose_edges": loose,
    "degenerate_faces": degenerate,
    "dims_m": dims,
    # Rule 14 and the IMPORT phase: 1 unit = 1 m, the asset sits on Z=0.
    "z_min_m": round(lo[2], 4) if meshes else None,
    "centre_xy_m": [round((lo[i] + hi[i]) / 2, 4) for i in range(2)] if meshes else None,
})

# Materials as they came back: a material with no image and a flat colour after
# a textured brief is the silent loss rule 19 exists for.
mats = {}
for o in meshes:
    for slot in o.material_slots:
        m = slot.material
        if not m or m.name in mats:
            continue
        imgs = []
        if m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image:
                    imgs.append(list(n.image.size))
        mats[m.name] = {"images": len(imgs), "max_px": max((max(s) for s in imgs), default=0)}
report["materials"] = mats
report["empty_material_slots"] = sum(
    1 for o in meshes for s in o.material_slots if s.material is None)

# Rig: the checks of references/characters.md, plus a deformation probe the
# reference does not have. Structural checks cannot see a rig that is valid and
# produces mush — which is exactly the 370-vertex failure of 26 August.
rigs = []
for a in arms:
    skinned = [o for o in meshes if any(m.type == 'ARMATURE' and m.object == a for m in o.modifiers)]
    # The glTF exporter does not drop an unweighted vertex: it binds it to a
    # synthetic joint named neutral_bone, and the file validates. That bone is
    # the exporter's, not the rig's — a vertex that only it drives is unweighted.
    NEUTRAL = "neutral_bone"
    deform = [b for b in a.data.bones if b.use_deform and b.name != NEUTRAL]
    used = set()
    unweighted = 0
    max_infl = 0
    for o in skinned:
        names = {g.index: g.name for g in o.vertex_groups}
        for v in o.data.vertices:
            gs = [g for g in v.groups if g.weight > 0.01 and names.get(g.group) != NEUTRAL]
            if not gs:
                unweighted += 1
            max_infl = max(max_infl, len(gs))
            used.update(names[g.group] for g in gs if g.group in names)
    # A parentless root that drives nothing is the hierarchy's anchor, not a
    # defect — the skill's own convention names it Root. Both bench villagers
    # have one; counted as dead it flagged two healthy rigs.
    dead = [b.name for b in deform if b.name not in used and b.parent is not None]

    # Deformation probe: bend every deforming bone by 25° and compare edge
    # lengths posed against rest. A healthy skin stretches a little; a tearing
    # or collapsing one shows up in the tail of the distribution.
    def edge_lengths():
        d = bpy.context.evaluated_depsgraph_get()
        out_l = []
        for o in skinned:
            ev = o.evaluated_get(d)
            me = ev.to_mesh()
            out_l += [(me.vertices[e.vertices[0]].co - me.vertices[e.vertices[1]].co).length
                      for e in me.edges]
            ev.to_mesh_clear()
        return out_l

    rest = edge_lengths()
    for pb in a.pose.bones:
        if a.data.bones[pb.name].use_deform:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = Euler((math.radians(25), 0, 0))
    bpy.context.view_layer.update()
    posed = edge_lengths()
    ratios = sorted(p / r for p, r in zip(posed, rest) if r > 1e-6)
    pick = lambda q: round(ratios[min(len(ratios) - 1, int(q * len(ratios)))], 3) if ratios else None
    rigs.append({
        "armature": a.name,
        "neutral_bone": NEUTRAL in a.data.bones,
        "bones": len(a.data.bones),
        "deform_bones": len(deform),
        "deform_bones_without_influence": len(dead),
        "skinned_meshes": len(skinned),
        "unweighted_verts": unweighted,
        "max_influences": max_infl,
        "stretch_p50": pick(0.50),
        "stretch_p99": pick(0.99),
        "stretch_max": pick(1.0),
    })
report["rigs"] = rigs

print("BENCH_JSON " + json.dumps(report))
if out:
    with open(out, 'w') as f:
        json.dump(report, f, indent=2)
