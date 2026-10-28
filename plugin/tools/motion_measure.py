"""Measure an animated GLB of a kiln-named humanoid: feet, floor, skin through skin, loop seam.

    blender --background --factory-startup --python-exit-code 1 --python motion_measure.py -- \\
        CLIP.glb OUT.json [--rig RIGGED.glb] [--clip NAME] [--every N]

The measures behind references/animation.md § Humanoid presets, the same for every route
(UniMate, AssetFurnace's presets, tools/presets.py), first written for the study that
compared them. `--rig` is the rig the clip was made from: UniMate's GLB re-rests the
character in a T-pose and rescales it (x2.14 on the child), so every length is brought back
to the rig's own scale (factor = sqrt of the rest surface-area ratio) and the rest-pose
crossings subtracted are the rig's own (same topology, checked). Without it, the clip's own
rest. `--clip` picks one clip of a file with several (tools/presets.py writes one per motion);
otherwise `Loop` (tools/motion_loop.py), else the active one.

- foot_slide: per foot, contact where the foot-skate weight clip(2 - 2^(h/H), 0, 1) > 0.5 on
  this frame and the next, h = lowest foot vertex above that foot's 20th-percentile height,
  H = 2.5 cm x height / 1.7 m (i.e. h < 0.58 H). Slide = horizontal speed of the vertices
  touching the floor on frame t (within 3 mm of the lowest), followed to t+1, relative to the
  ground speed (median stance velocity of both feet: ~0 for a clip that travels, the
  treadmill speed for an in-place clip). mm per cycle = summed slide / cycles (cycles =
  contacts of 3+ frames per foot); mm/s = mean slide speed during stance.
- floor: floor = lowest skin vertex at rest. below_mm = deepest vertex under it on any frame;
  frames_below_pct = frames with a vertex more than 5 mm under. foot_float_mm = median over
  frames of the lowest foot's height. air_mm = the highest the LOWER foot gets.
- skin: triangles crossing another triangle once posed minus those crossing at rest (mm²,
  rest areas); arm_body = the part where an arm/hand triangle crosses a torso/head one.
- seam: pose step across the loop point (last frame -> first, horizontal root travel removed)
  over the mean frame step. A clip whose last key equals its first is measured last-1 -> first.
- knee_pops: frames where a knee's bend spikes by KNEE_POP_DEG or more against both neighbours,
  either way — the leg pulled to full reach for one frame, or bent back between two straight ones. Read by eye as knees that
  "tremblent" on a mascot no other measure flagged (2026-10-28: 36 -> 4 -> 20 deg of bend).
"""
import json
import math
import struct
import sys
import time

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

KNEE_POP_DEG = 8.0


def clip_fps(clip, name=None):
    """Frames per second of one clip of a GLB, from its key count and length."""
    raw = open(clip, "rb").read()
    jl, = struct.unpack_from("<I", raw, 12)
    gj = json.loads(raw[20:20 + jl])
    anims = gj.get("animations", [])
    anims = [x for x in anims if x.get("name") == name] or [x for x in anims if x.get("name") == "Loop"] or anims
    times = [(gj["accessors"][s["input"]]["count"], gj["accessors"][s["input"]]["max"][0])
             for an in anims[:1] for s in an["samplers"]]
    cnt, tmax = max(times)
    return round((cnt - 1) / tmax) if tmax > 0 else 30


def measure(clip, out_json=None, rigf=None, name=None, every=1):
    fps = clip_fps(clip, name)
    def skin_of():
        r = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        return r, max((o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == r),
                      key=lambda o: len(o.data.vertices))
    def world_base(o):
        V = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
        M = np.array(o.matrix_world); return V @ M[:3, :3].T + M[:3, 3]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=rigf or clip)
    _, rm = skin_of(); rm.data.calc_loop_triangles()
    T = np.array([t.vertices[:] for t in rm.data.loop_triangles]); R0 = world_base(rm)
    def areas(V, T=T): P = V[T]; return 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    A = areas(R0) * 1e6
    height = float(R0[:, 2].max() - R0[:, 2].min())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = fps, 1
    bpy.ops.import_scene.gltf(filepath=clip)
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = max((o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == rig),
               key=lambda o: len(o.data.vertices))
    PB = rig.pose.bones
    act = (bpy.data.actions.get(name) if name else None) or bpy.data.actions.get("Loop") or rig.animation_data.action
    if act is None:
        raise ValueError(f"{clip}: no clip named {name!r}")
    rig.animation_data.action = act
    if act.slots: rig.animation_data.action_slot = act.slots[0]
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))


    def family(bn):
        for side in ("Left", "Right"):
            if bn.startswith(side):
                r = bn[len(side):]
                if r in ("Arm", "ForeArm", "Hand") or r.startswith(("Hand", "Fingers")): return side + "Fore"
                if r in ("UpLeg", "Leg", "Foot", "ToeBase", "Toe_End"): return side + "Hind"
                return "Body"
        if bn.startswith(("Neck", "Head")): return "Head"
        return "Body"


    def evaluated():
        dg = bpy.context.evaluated_depsgraph_get(); e = mesh.evaluated_get(dg); m = e.to_mesh()
        V = np.empty(len(m.vertices) * 3); m.vertices.foreach_get("co", V); e.to_mesh_clear()
        V = V.reshape(-1, 3); M = np.array(mesh.matrix_world)
        return V @ M[:3, :3].T + M[:3, 3]


    me = mesh.data; me.calc_loop_triangles()
    T0 = T; Tc = np.array([t.vertices[:] for t in me.loop_triangles])
    assert len(Tc) == len(T0), "clip and rig meshes differ"   # triangles match by index (a few seam vertices may be split)
    names = [g.name for g in mesh.vertex_groups]
    W = np.zeros((len(me.vertices), len(names)))
    for v in me.vertices:
        for g in v.groups: W[v.index, g.group] = g.weight
    dom = W.argmax(1)
    vfam = np.array([family(names[i]) for i in dom])
    tf = vfam[Tc]; tfam = np.where(tf[:, 1] == tf[:, 2], tf[:, 1], tf[:, 0])
    feet = {}
    for sd in ("Left", "Right"):
        idx = [names.index(sd + b) for b in ("Foot", "ToeBase") if sd + b in names]
        feet[sd] = np.where(np.isin(dom, idx))[0]

    # rest pose
    rig.animation_data.action = None
    for p in PB: p.rotation_mode = 'QUATERNION'; p.rotation_quaternion = (1, 0, 0, 0); p.location = (0, 0, 0); p.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    R = evaluated()
    _, canon = np.unique(np.round(R, 6), axis=0, return_inverse=True)
    TC = canon.reshape(-1)[Tc]
    S = math.sqrt(areas(R, Tc).sum() / areas(R0, T0).sum())     # clip scale / rig scale
    floor = float(R[:, 2].min()) / S


    def hits(V, T):
        bvh = BVHTree.FromPolygons(V.tolist(), T.tolist(), all_triangles=True)
        hit, armb = set(), set(); pair = {}
        for i, j in bvh.overlap(bvh):
            if i == j or (set(TC[i]) & set(TC[j])): continue
            hit.add(i); hit.add(j)
            key = "-".join(sorted((tfam[i], tfam[j]))); pair.setdefault(key, set()).update((i, j))
            fi, fj = tfam[i], tfam[j]
            if ("Fore" in fi) != ("Fore" in fj) and ({fi, fj} & {"Body", "Head"}):
                armb.add(i); armb.add(j)
        return hit, armb, pair


    _, canon0 = np.unique(np.round(R0, 6), axis=0, return_inverse=True)
    TC_clip, TC = TC, canon0.reshape(-1)[T]
    rest_hit, _, _ = hits(R0, T0)          # the rig's own rest crossings
    TC = TC_clip
    rig.animation_data.action = act
    if act.slots: rig.animation_data.action_slot = act.slots[0]
    for p in PB: p.rotation_mode = 'QUATERNION'

    t0 = time.time()
    frames = list(range(f0, f1 + 1))
    bypair = {}
    footd = {k: [] for k in feet}; low = []; hips = []; Vs = []; skin = []
    knees = {sd: [] for sd in ("Left", "Right") if sd + "UpLeg" in PB and sd + "Leg" in PB}
    for k, f in enumerate(frames):
        sc.frame_set(f); V = evaluated()
        V = V / S
        hips.append(np.array((rig.matrix_world @ PB["Hips"].head)[:]) / S)
        for sd in knees:
            u = (PB[sd + "UpLeg"].tail - PB[sd + "UpLeg"].head).normalized()
            l = (PB[sd + "Leg"].tail - PB[sd + "Leg"].head).normalized()
            knees[sd].append(math.degrees(math.acos(max(-1.0, min(1.0, u.dot(l))))))
        low.append(float(V[:, 2].min()))
        for sd, idx in feet.items():
            footd[sd].append(V[idx].copy())
        Vs.append(V[::7].copy())
        if k % every == 0:
            h, ab, pr = hits(V, Tc); new = h - rest_hit; nab = ab - rest_hit
            skin.append((float(A[list(new)].sum()) if new else 0.0, float(A[list(nab)].sum()) if nab else 0.0))
            for kk, tri in pr.items():
                tri = tri - rest_hit
                bypair[kk] = bypair.get(kk, 0.0) + (float(A[list(tri)].sum()) if tri else 0.0)
    dt = 1 / fps; n = len(frames)

    # feet
    H = 0.025 * height / 1.7          # foot-skate height scale (2.5 cm on a 1.7 m human)
    stance, onsets, gvs, disp, wts = {}, {}, [], {}, {}
    for sd, seq in footd.items():
        Z = np.array([P[:, 2].min() for P in seq])
        h = np.clip(Z - np.percentile(Z, 20), 0, None)
        w = np.clip(2 - 2 ** (h / H), 0, 1)          # 1 on the floor, 0 from H up
        wts[sd] = np.minimum(w[:-1], w[1:])
        st = wts[sd] > 0.5
        # touch-downs lasting 3+ frames
        runs = np.diff(np.concatenate([[0], st.astype(int), [0]]))
        starts, ends = np.where(runs == 1)[0], np.where(runs == -1)[0]
        onsets[sd] = int(np.sum(ends - starts >= 3))
        stance[sd] = st
        d = []
        for t in range(n - 1):
            P = seq[t]; c = P[:, 2] < P[:, 2].min() + 0.003
            d.append(((seq[t + 1][c, :2] - P[c, :2]).mean(0)) / dt)
        disp[sd] = np.array(d)
        if st.any(): gvs.append(disp[sd][st])
    gv = np.median(np.concatenate(gvs), axis=0) if gvs else np.zeros(2)
    cycles = max(1.0, float(np.mean([onsets[s] for s in onsets])))
    tot_slide = 0.0; st_frames = 0
    for s in disp:
        dv = np.linalg.norm(disp[s] - gv, axis=1)
        tot_slide += float((dv * stance[s] * dt).sum()); st_frames += float(stance[s].sum())
    footz = {sd: np.array([P[:, 2].min() for P in seq]) for sd, seq in footd.items()}
    lowfoot = np.minimum(footz["Left"], footz["Right"]) - floor

    # seam (vertex subsample, horizontal hips travel removed)
    H = np.array(hips)
    def pose(i):
        off = np.array([H[i, 0] - H[0, 0], H[i, 1] - H[0, 1], 0.0]); return Vs[i] - off
    steps = [np.linalg.norm(pose(i + 1) - pose(i), axis=1).mean() for i in range(n - 1)]
    last = n - 1
    if np.linalg.norm(pose(last) - pose(0), axis=1).mean() < 1e-4: last = n - 2   # closing key == key 0
    seam = float(np.linalg.norm(pose(0) - pose(last), axis=1).mean() / (np.mean(steps[:last]) + 1e-12))

    pops = {}
    for sd, a in knees.items():
        a = np.array(a)
        d0, d1 = a[1:-1] - a[:-2], a[2:] - a[1:-1]           # a one-frame spike, either way
        pops[sd] = [int(frames[t + 1]) for t in range(len(d0))
                    if abs(d0[t]) >= KNEE_POP_DEG and abs(d1[t]) >= KNEE_POP_DEG and d0[t] * d1[t] < 0]

    lows = np.array(low) - floor
    res = dict(clip=clip, name=act.name, clip_scale=round(S, 3), fps=fps, frames=n, seconds=round((n - 1) / fps, 2), height_m=round(height, 3),
               ground_speed_m_s=round(float(np.linalg.norm(gv)), 3),
               travel_m=round(float(np.linalg.norm(H[-1, :2] - H[0, :2])), 3),
               foot_slide=dict(cycles=cycles, contact_frames=round(st_frames, 1),
                               mm_per_cycle=round(tot_slide * 1000 / cycles, 1),
                               mm_s=round(tot_slide * 1000 / max(st_frames * dt, 1e-9), 1)),
               floor=dict(below_mm=round(max(0.0, -float(lows.min())) * 1000, 1),
                          frames_below_pct=round(100 * float(np.mean(lows < -0.005)), 1),
                          foot_float_mm=round(float(np.median(lowfoot)) * 1000, 1),
                          air_mm=round(float(lowfoot.max()) * 1000, 1)),
               skin=dict(sampled_every=every, mean_self_mm2=round(float(np.mean([s for s, _ in skin])), 1),
                         worst_self_mm2=round(float(np.max([s for s, _ in skin])), 1),
                         mean_arm_body_mm2=round(float(np.mean([b for _, b in skin])), 1),
                         worst_arm_body_mm2=round(float(np.max([b for _, b in skin])), 1),
                         by_pair_mean_mm2={k: round(v / len(skin), 0) for k, v in sorted(bypair.items(), key=lambda x: -x[1])[:5]},
                         arm_body_frames_pct=round(100 * float(np.mean([b > 1 for _, b in skin])), 1)),
               seam_x_step=round(seam, 2),
               knee_pops=dict(count=sum(len(v) for v in pops.values()), frames=pops),
               measure_s=round(time.time() - t0, 1))
    if out_json:
        json.dump(res, open(out_json, "w"), indent=1)
    return res


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    res = measure(a[0], a[1], rigf=opt("--rig"), name=opt("--clip"), every=int(opt("--every", 1)))
    print("RESULT", json.dumps(res))


if __name__ == "__main__":
    main()
