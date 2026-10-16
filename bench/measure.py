"""Measure one exported GLB the way a consumer receives it: re-imported, not trusted.

    blender --background --factory-startup --python-exit-code 1 --python bench/measure.py -- <file.glb> [out.json]

Prints one JSON object. Every number is read from the file or from Blender after
import — nothing is taken from the production log, because the log is written by
the same session whose output is being judged.
"""
import bpy, bmesh, json, math, os, re, struct, sys
import numpy as np
from mathutils import Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skin_intersect  # noqa: E402  (bench/, next to this file)

argv = sys.argv[sys.argv.index('--') + 1:]
path = argv[0]
out = argv[1] if len(argv) > 1 else None


def glb_chunks(p):
    """The glTF JSON chunk and the BIN chunk, read directly — what the importer hides."""
    with open(p, 'rb') as f:
        magic, _version, _length = struct.unpack('<4sII', f.read(12))
        if magic != b'glTF':
            raise SystemExit(f"not a GLB: {p}")
        chunk_len, chunk_type = struct.unpack('<I4s', f.read(8))
        if chunk_type != b'JSON':
            raise SystemExit(f"first chunk is not JSON: {p}")
        js = json.loads(f.read(chunk_len))
        head = f.read(8)
        binary = b""
        if len(head) == 8:
            n, t = struct.unpack('<I4s', head)
            if t == b'BIN\x00':
                binary = f.read(n)
        return js, binary


COMP = {5120: (np.int8, 127.0), 5121: (np.uint8, 255.0), 5122: (np.int16, 32767.0),
        5123: (np.uint16, 65535.0), 5125: (np.uint32, None), 5126: (np.float32, None)}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def accessor(js, binary, i):
    """One accessor as a float array (count, width); None when it lives outside the GLB."""
    a = js["accessors"][i]
    if "bufferView" not in a or a.get("sparse"):
        return None
    bv = js["bufferViews"][a["bufferView"]]
    if bv.get("buffer", 0) != 0 or js["buffers"][0].get("uri") or bv.get("extensions"):
        return None             # an external buffer, or meshopt-compressed: not read here
    dt, norm = COMP[a["componentType"]]
    w = WIDTH[a["type"]]
    size = np.dtype(dt).itemsize
    stride = bv.get("byteStride") or size * w
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    rows = [np.frombuffer(binary, dt, w, base + k * stride) for k in range(a["count"])]
    out = np.array(rows, dtype=np.float64).reshape(a["count"], w)
    return out / norm if norm and a.get("normalized") else out


LID = re.compile(r"lid|blink|eye_?close|closeeye", re.I)


def clips(js, binary):
    """Every clip as the file carries it: names, length, whether the loop closes, and what moves.

    Read from the file, not from Blender's import: a clip is what a web player will play.
    The loop closes when the last key repeats the first on every channel — three.js wraps
    at the last key, so a clip keyed 0..P-1 skips the step back to frame 0 (quadruped.py's
    own rule). seam_vs_step says by how much: ~1 for a clip one key short, 0 for a closed one."""
    nodes = js.get("nodes", [])
    targets = {}
    for ni, n in enumerate(nodes):
        if "mesh" in n:
            m = js["meshes"][n["mesh"]]
            targets[ni] = (m.get("extras") or {}).get("targetNames") or []
    out = []
    for an in js.get("animations", []):
        samplers = an.get("samplers", [])
        seam = {"rotation_deg": 0.0, "translation_m": 0.0, "scale": 0.0, "weights": 0.0}
        steps, moving, blink, duration, keys, unread = [], set(), [], 0.0, 0, 0
        for ch in an.get("channels", []):
            tgt = ch.get("target", {})
            node, path_ = tgt.get("node"), tgt.get("path")
            smp = samplers[ch["sampler"]]
            t = accessor(js, binary, smp["input"])
            v = accessor(js, binary, smp["output"])
            if t is None or v is None or not len(t):
                unread += 1
                continue
            if smp.get("interpolation") == "CUBICSPLINE":
                v = v[1::3]
            if path_ == "weights":
                v = v.reshape(len(t), -1)
            duration = max(duration, float(t[-1, 0]))
            keys = max(keys, len(t))
            name = nodes[node].get("name", str(node)) if node is not None and node < len(nodes) else "?"
            if path_ == "rotation":
                q = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
                ang = lambda a_, b_: math.degrees(2 * math.acos(min(1.0, abs(float(np.dot(a_, b_))))))
                d = ang(q[0], q[-1])
                st = [ang(q[k], q[k + 1]) for k in range(len(q) - 1)]
                rng = max((ang(q[0], x) for x in q), default=0.0)
                seam["rotation_deg"] = max(seam["rotation_deg"], d)
                if rng > 0.5:
                    moving.add(name)
                    steps.append((np.median(st) if st else 0.0, d))
                if LID.search(name) and rng > 5:
                    blink.append(f"{name}.rotation")
            else:
                d = float(np.abs(v[0] - v[-1]).max())
                key = {"translation": "translation_m", "scale": "scale", "weights": "weights"}.get(path_)
                if key:
                    seam[key] = max(seam[key], d)
                rng = float(np.abs(v - v[0]).max())
                if rng > (0.01 if path_ == "weights" else 1e-3):
                    moving.add(name)
                if path_ == "weights" and rng > 0.3:
                    names = targets.get(node, [])
                    for k in range(v.shape[1]):
                        tn = names[k] if k < len(names) else f"target{k}"
                        if LID.search(tn) and float(np.ptp(v[:, k])) > 0.3:
                            blink.append(f"{name}.{tn}")
        closes = (seam["rotation_deg"] <= 0.5 and seam["translation_m"] <= 1e-3
                  and seam["scale"] <= 1e-3 and seam["weights"] <= 0.01)
        ratio = [d / s_ for s_, d in steps if s_ > 1e-6]
        out.append({
            "name": an.get("name", ""),
            "duration_s": round(duration, 4),
            "keys": keys,
            "channels": len(an.get("channels", [])),
            "unread_channels": unread,
            "moving_nodes": len(moving),
            # None: a channel could not be read (meshopt-compressed) — unknown, not open
            "loop_closes": None if unread else bool(closes),
            "seam": {k: round(x, 4) for k, x in seam.items()},
            "seam_vs_step": round(max(ratio), 2) if ratio else None,
            "blink": sorted(set(blink)),
        })
    return out


gltf, gltf_bin = glb_chunks(path)
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
    # Meshes bound to a skin: "one skin" is one of them, the rest rigid or static.
    "gltf_skinned_nodes": sum(1 for n in gltf.get("nodes", []) if "skin" in n and "mesh" in n),
    "clips": clips(gltf, gltf_bin),
}
report["clip_names"] = [c["name"] for c in report["clips"]]
report["blink"] = any(c["blink"] for c in report["clips"])

# meshopt is a web-runtime format Blender cannot import (README, gallery section).
# Measure the file anyway and say why the geometry half is missing.
if "EXT_meshopt_compression" in report["extensions_used"]:
    report["reimport"] = "skipped: EXT_meshopt_compression is not importable by Blender"
    print("BENCH_JSON " + json.dumps(report))       # run.py reads this line, as below
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
FINGER = re.compile(r"finger|thumb|(index|middle|ring|pinky)[\d._]|^f_|palm", re.I)
for a in arms:
    skinned = [o for o in meshes if any(m.type == 'ARMATURE' and m.object == a for m in o.modifiers)]
    # The importer makes the first clip the active action: every probe below would measure
    # a frame of it instead of the bend. Detach it (the clips were read from the file above).
    if a.animation_data:
        a.animation_data.action = None
        for tr in a.animation_data.nla_tracks:
            tr.mute = True
    bpy.context.view_layer.update()
    # Bent-pose skin intersection (bench/skin_intersect.py), before the 25° probe poses the rig.
    try:
        bent = skin_intersect.measure(a, skinned)
    except Exception as ex:          # a finding, not a crash: the other measures still stand
        bent = {"status": f"error: {type(ex).__name__}: {ex}"}
    hands = [b.name for b in a.data.bones if re.search(r"hand|wrist", b.name, re.I)]
    fingers = [b.name for b in a.data.bones if FINGER.search(re.sub(r"^(DEF|ORG|MCH)-", "", b.name))]
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
        "hand_bones": len(hands),
        "finger_bones": len(fingers),
        "bent": bent,
    })
report["rigs"] = rigs
report["skinned_mesh_objects"] = sum(r["skinned_meshes"] for r in rigs)
# One skin: one mesh carries the whole body — not a mesh per part glued on (characters.md).
report["single_skin"] = bool(rigs) and report["skinned_mesh_objects"] == 1

print("BENCH_JSON " + json.dumps(report))
if out:
    with open(out, 'w') as f:
        json.dump(report, f, indent=2)
