"""Skin self-intersection on a bent pose — how much of a rigged skin passes through itself.

    blender --background --factory-startup --python-exit-code 1 --python bench/skin_intersect.py -- <file.glb>

Ported from the rig study's measure_cells.py (2026-10-16, ~/Downloads/kiln-tests-rig), bent
pose only. measure.py calls `measure()` on every armature it finds; run standalone, it prints
one `SKIN_INTERSECT {...}` line.

The pose is the study's: biped — thighs 60° forward, knees 75°, arms 45° forward, elbows 75°,
spine 20°, neck 30°; quadruped — the study's crease flex. On the evaluated skin, triangulated:

- self_mm2: rest area of the triangles that cross another one (pairs sharing a vertex
  ignored), LESS those already crossing at rest — a generated mesh may cross itself at rest;
- inter_mm2: the part where the two triangles belong to different body parts and one of them
  is a limb (a thigh through the belly, an arm through the chest) — what a viewer sees;
- fold_mm2: the part inside one body part (skin folding on itself at a crease);
- *_pct: the same as a share of the skin's rest area, so sizes compare.

A body part is the family of the bone that weighs most on the vertex. Families come from the
HIERARCHY, not the names: every bone under the left thigh is LeftHind, whatever it is called.
The limb roots are found by name — Mixamo-style (kiln's), Rigify DEF-, and the usual
thigh/upperarm spellings with a side mark; a rig whose limbs cannot be named is reported as
such, never measured on a guessed pose.
"""
import math, re, sys

SIDES = (("Left", re.compile(r"(^|[^a-z])(left|l)([^a-z]|$)|\.l(\.|$)|_l(_|$)|^l_|left", re.I)),
         ("Right", re.compile(r"(^|[^a-z])(right|r)([^a-z]|$)|\.r(\.|$)|_r(_|$)|^r_|right", re.I)))
# role → name patterns, matched on the name with its side mark and any "DEF-"/"mixamorig:" removed
ROLES = {
    "UpLeg": r"^(upleg|upperleg|thigh|hip(?!s)|femur|legupper|upper_?leg)$",
    "Leg": r"^(leg|lowerleg|shin|calf|knee|lower_?leg|leglower)$",
    "Foot": r"^(foot|ankle|paw_?hind|hindfoot|hindpaw)$",
    "Arm": r"^(arm|upperarm|upper_?arm|humerus|armupper|frontleg|foreleg_?upper)$",
    "ForeArm": r"^(forearm|lowerarm|lower_?arm|elbow|armlower|forelegl?ower)$",
    "Hand": r"^(hand|wrist|paw|frontpaw|forepaw)$",
}
CENTRE = {
    # Rigify's hips bone is "spine" (DEF-spine); a Mixamo rig's Hips sits above its Spine and wins
    "Hips": r"^(hips|pelvis|hip|root_?hips|spine)$",
    "Spine1": r"^(spine1|spine\.?001|spine_?01|chest)$",
    "Neck": r"^(neck|neck1|neck_?01|spine\.?004)$",
    "Head": r"^(head|spine\.?006|skull)$",
}


def _strip(name):
    n = re.sub(r"^(DEF[-_]|mixamorig\d*:|ORG[-_])", "", name)
    side = None
    for s, rx in SIDES:
        # Mixamo glues the side to the role (LeftUpLeg); others mark it (.L, _l, L_)
        if n.startswith(s):
            return s, n[len(s):]
        if rx.search(n):
            side = s
    if side:
        n = re.sub(r"(\.|_)(l|r)(\.\d+)?$|^(l|r)_|(left|right)", "", n, flags=re.I)
        n = re.sub(r"\.\d+$", "", n)
    return side, n.strip("._-")


def resolve(bones):
    """bones: {name: parent_name or None}. Returns {canonical: actual} for what is found.

    Pure Python, so the seeded test can check it outside Blender. When a role matches several
    bones (Rigify keeps a chain thigh / thigh.001), the one closest to the root wins."""
    depth = {}

    def d(n):
        if n not in depth:
            p = bones.get(n)
            depth[n] = 0 if p is None or p not in bones else d(p) + 1
        return depth[n]

    found = {}
    for name in sorted(bones, key=d):
        side, base = _strip(name)
        low = base.lower().replace(" ", "")
        if side:
            for role, rx in ROLES.items():
                if re.match(rx, low) and side + role not in found:
                    found[side + role] = name
        else:
            for role, rx in CENTRE.items():
                if re.match(rx, low) and role not in found:
                    found[role] = name
    return found


def families(bones, found):
    """Each bone's body part, from the hierarchy below the resolved limb roots."""
    roots = {}
    for side in ("Left", "Right"):
        for role, fam in (("Arm", "Fore"), ("UpLeg", "Hind")):
            if side + role in found:
                roots[found[side + role]] = side + fam
    if "Neck" in found:
        roots[found["Neck"]] = "Head"
    elif "Head" in found:
        roots[found["Head"]] = "Head"
    out = {}
    for n in bones:
        p, fam = n, "Body"
        seen = set()
        while p is not None and p in bones and p not in seen:
            seen.add(p)
            if p in roots:
                fam = roots[p]
                break
            if re.search(r"tail", p, re.I):
                fam = "Tail"
                break
            p = bones.get(p)
        out[n] = fam
    return out


def measure(rig, meshes):
    """Bent-pose intersection of the skins `meshes` driven by armature object `rig`.

    Leaves the rig at rest, its animation detached. Returns a dict (never raises on a rig it
    cannot read: says why instead)."""
    import bpy
    import numpy as np
    from mathutils import Quaternion, Vector
    from mathutils.bvhtree import BVHTree

    B, PB = rig.data.bones, rig.pose.bones
    tree = {b.name: (b.parent.name if b.parent else None) for b in B}
    found = resolve(tree)
    need = [k for k in ("Hips", "LeftUpLeg", "RightUpLeg") if k not in found]
    if not meshes:
        return {"status": "no skinned mesh"}
    if need:
        return {"status": "limbs not recognised", "missing": need, "resolved": found,
                "bones_sample": sorted(tree)[:40]}
    fam = families(tree, found)

    if rig.animation_data:
        rig.animation_data.action = None
        for tr in rig.animation_data.nla_tracks:
            tr.mute = True
    for o in meshes:
        sk = o.data.shape_keys
        if sk and sk.animation_data:
            sk.animation_data.action = None
            for tr in sk.animation_data.nla_tracks:
                tr.mute = True

    def reset():
        for p in PB:
            p.rotation_mode = 'QUATERNION'
            p.rotation_quaternion = (1, 0, 0, 0)
            p.location = (0, 0, 0)
            p.scale = (1, 1, 1)
        bpy.context.view_layer.update()

    W = rig.matrix_world

    def head(k):
        return W @ B[found[k]].head_local

    # Biped when the neck (or the head, or the top of the spine) stands above the hips.
    top = next((k for k in ("Neck", "Head", "Spine1") if k in found), None)
    biped = False
    if top:
        v = head(top) - head("Hips")
        biped = abs(v.z) > 0.7 * v.length
        fwd = v
    if biped or not top:
        biped = True
        foot = found.get("LeftFoot") or found.get("RightFoot")
        if foot:
            b = B[foot]
            fwd = W.to_3x3() @ (b.tail_local - b.head_local)
        else:
            fwd = Vector((0, -1, 0))        # Blender's front
    fwd.z = 0
    if fwd.length < 1e-6:
        fwd = Vector((0, -1, 0))
    f = fwd.normalized()
    up = Vector((0, 0, 1))
    side_axis = f.cross(up).normalized()
    spec = {}
    for sd in ("Left", "Right"):
        if biped:
            spec[sd + "UpLeg"] = (side_axis, 60, f)
            spec[sd + "Leg"] = (side_axis, 75, -f)
            spec[sd + "Arm"] = (side_axis, 45, f)
            spec[sd + "ForeArm"] = (side_axis, 75, f + up)
        else:
            spec[sd + "Arm"] = (side_axis, 30, -f)
            spec[sd + "ForeArm"] = (side_axis, 75, f + 0.6 * up)
            spec[sd + "UpLeg"] = (side_axis, 30, f)
            spec[sd + "Leg"] = (side_axis, 75, -f + 0.6 * up)
    if biped:
        spec["Spine1"] = (side_axis, 20, f)
        spec["Neck"] = (side_axis, 30, f - up)
    else:
        spec["Neck"] = (side_axis, 30, 0.3 * f - up)

    def evaluated():
        dg = bpy.context.evaluated_depsgraph_get()
        Vs = []
        for o in meshes:
            e = o.evaluated_get(dg)
            m = e.to_mesh()
            M = o.matrix_world
            Vs.append(np.array([(M @ v.co)[:] for v in m.vertices]))
            e.to_mesh_clear()
        return np.concatenate(Vs) if Vs else np.zeros((0, 3))

    def set_pose():
        reset()
        posed = []
        for k, (axis, deg, want) in spec.items():
            if k not in found:
                continue
            pb = PB[found[k]]
            Mb = (W @ pb.matrix).to_3x3().normalized()
            loc = (Mb.inverted() @ axis).normalized()
            best = None
            for sgn in (1, -1):
                t0 = (W @ pb.tail).copy()
                pb.rotation_quaternion = Quaternion(loc, sgn * math.radians(deg))
                bpy.context.view_layer.update()
                gain = ((W @ pb.tail) - t0).dot(want.normalized())
                pb.rotation_quaternion = (1, 0, 0, 0)
                bpy.context.view_layer.update()
                if best is None or gain > best[0]:
                    best = (gain, sgn)
            pb.rotation_quaternion = Quaternion(loc, best[1] * math.radians(deg))
            bpy.context.view_layer.update()
            posed.append(k)
        return posed

    # Triangles and their body part, all skins in one soup (an eye crossing its head at rest
    # is subtracted with every other rest crossing).
    T, tfam, off = [], [], 0
    for o in meshes:
        me = o.data
        me.calc_loop_triangles()
        t = np.array([lt.vertices[:] for lt in me.loop_triangles], dtype=np.int64).reshape(-1, 3)
        names = [g.name for g in o.vertex_groups]
        vf = np.array(["Body"] * len(me.vertices), dtype=object)
        for v in me.vertices:
            best = max(((g.weight, g.group) for g in v.groups if g.group < len(names)), default=None)
            if best and best[0] > 0:
                vf[v.index] = fam.get(names[best[1]], "Body")
        tf = vf[t] if len(t) else np.zeros((0, 3), dtype=object)
        tfam.append(np.where(tf[:, 1] == tf[:, 2], tf[:, 1], tf[:, 0]) if len(t) else np.zeros(0, dtype=object))
        T.append(t + off)
        off += len(me.vertices)
    T = np.concatenate(T)
    tfam = np.concatenate(tfam)
    limb = np.array([("Fore" in x) or ("Hind" in x) for x in tfam])

    reset()
    R = evaluated()
    # Weld by position for the "shares a vertex" test: a glTF round trip splits every seam.
    _, canon = np.unique(np.round(R, 6), axis=0, return_inverse=True)
    TC = canon.reshape(-1)[T]

    def hits(V):
        bvh = BVHTree.FromPolygons([tuple(v) for v in V], [tuple(t) for t in T], all_triangles=True)
        P = np.array(bvh.overlap(bvh), dtype=np.int64).reshape(-1, 2)
        if not len(P):
            return set(), set()
        P = P[P[:, 0] != P[:, 1]]
        a, b = TC[P[:, 0]], TC[P[:, 1]]
        share = np.zeros(len(P), bool)
        for i in range(3):
            for j in range(3):
                share |= a[:, i] == b[:, j]
        P = P[~share]
        cross = (tfam[P[:, 0]] != tfam[P[:, 1]]) & (limb[P[:, 0]] | limb[P[:, 1]])
        return set(P.ravel().tolist()), set(P[cross].ravel().tolist())

    Pt = R[T]
    A = 0.5 * np.linalg.norm(np.cross(Pt[:, 1] - Pt[:, 0], Pt[:, 2] - Pt[:, 0]), axis=1) * 1e6   # mm²
    total = float(A.sum())
    rest_hit, _ = hits(R)
    posed = set_pose()
    hit, inter = hits(evaluated())
    new, newi = hit - rest_hit, inter - rest_hit
    s = float(A[list(new)].sum()) if new else 0.0
    i = float(A[list(newi)].sum()) if newi else 0.0
    by = {}
    for t in new:
        by[tfam[t]] = by.get(tfam[t], 0.0) + float(A[t])
    reset()
    pct = lambda x: round(100 * x / total, 3) if total else None
    return {
        "status": "ok",
        "posture": "biped" if biped else "quadruped",
        "posed_bones": sorted(posed),
        "resolved": found,
        "skins": len(meshes),
        "tris": int(len(T)),
        "area_mm2": round(total, 1),
        "rest_self_mm2": round(float(A[list(rest_hit)].sum()), 1) if rest_hit else 0.0,
        "self_mm2": round(s, 1), "inter_mm2": round(i, 1), "fold_mm2": round(s - i, 1),
        "self_pct": pct(s), "inter_pct": pct(i), "fold_pct": pct(s - i),
        "by_part_mm2": {k: round(v, 1) for k, v in sorted(by.items())},
    }


def skinned_meshes(rig, scene_objects):
    return [o for o in scene_objects if o.type == 'MESH'
            and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]


if __name__ == "__main__" and "bpy" in sys.modules:
    import bpy, json
    path = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    for a in [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']:
        print("SKIN_INTERSECT " + json.dumps({"armature": a.name,
                                              **measure(a, skinned_meshes(a, bpy.context.scene.objects))}))
