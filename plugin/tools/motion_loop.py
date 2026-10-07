"""Turn generated clips into seamless loops, and keep the sample that loops best.

    blender --background --factory-startup --python-exit-code 1 --python motion_loop.py -- \\
        --out best.glb sample_0.glb sample_1.glb ...

For each clip: find the window whose end matches its start in pose and in direction,
cross-fade the last 4 frames into the frames before the window, and remove the root's
horizontal drift so the cycle stays in place. The seam is reported as a multiple of
the frame-to-frame change on either side of it: about 1.0 is invisible.

Two traps this avoids, both hit while measuring: a stretch where nothing moves loops
"perfectly" and shows nothing (windows that move less than 70% of the clip's median
are refused), and a clip that is still for two thirds of its length cannot loop at all
(its best seam stays several times its step — it loses to the other samples).

UniMate's raw clips seamed at 2.1-9.7x the local step (12 clips: walks, wing flaps); looped, 0.5-1.2x.
"""
import json
import sys

import bpy
import numpy as np
from mathutils import Quaternion

K, MIN_LEN = 4, 12


def loop_one(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    f0, f1 = (int(x) for x in arm.animation_data.action.frame_range)
    bones = list(arm.pose.bones); root = next(p for p in bones if p.parent is None)
    for p in bones:
        p.rotation_mode = 'QUATERNION'
    N = f1 - f0 + 1
    Q = np.zeros((N, len(bones), 4)); L = np.zeros((N, 3))
    for i, f in enumerate(range(f0, f1 + 1)):
        bpy.context.scene.frame_set(f)
        for b, p in enumerate(bones):
            Q[i, b] = p.rotation_quaternion[:]
        L[i] = root.location[:]
    dist = lambda a, b: float(np.degrees(2 * np.arccos(np.abs((Q[a] * Q[b]).sum(1)).clip(0, 1))).mean())
    steps = np.array([dist(n, n + 1) for n in range(N - 1)]); step = float(np.median(steps)) or 1e-6
    best = None
    for i in range(K, N - MIN_LEN):
        for j in range(i + MIN_LEN, N):
            moving = steps[i:j].mean()
            if moving < 0.7 * step:
                continue
            # same pose AND same way through it: the frames before the seam must match too,
            # or a swing matches its mirror image on the way back
            cost = (dist(j, i) + dist(j - 1, i - 1)) / moving - 0.01 * (j - i)
            if best is None or cost < best[0]:
                best = (cost, i, j)
    if best is None:
        return None
    _, i, j = best
    idx = list(range(i, j)); QQ, LL = Q[idx].copy(), L[idx].copy()
    for k in range(K):
        w, f, src = (k + 1) / (K + 1), len(idx) - K + k, i - K + k
        for b in range(len(bones)):
            QQ[f, b] = Quaternion(QQ[f, b]).slerp(Quaternion(Q[src, b]), w)[:]
        LL[f, 2] = (1 - w) * LL[f, 2] + w * L[src, 2]
    drift = L[j] - L[i]; drift[2] = 0
    LL -= np.outer(np.arange(len(idx)) / len(idx), drift)
    moving = float(steps[i:j].mean())
    # the seam against the motion's own speed right there (the steps either side of it):
    # an oscillation can seam at its fastest point, where a normal step is 1.5x the mean
    qd = lambda A, B: float(np.degrees(2 * np.arccos(np.abs((A * B).sum(1)).clip(0, 1))).mean())
    local = (qd(QQ[-2], QQ[-1]) + qd(QQ[0], QQ[1])) / 2 or 1e-6
    seam = qd(QQ[-1], QQ[0]) / local
    local_raw = (dist(N - 2, N - 1) + dist(0, 1)) / 2 or 1e-6
    act = bpy.data.actions.new("Loop"); arm.animation_data.action = act
    for n in range(len(idx)):
        for b, p in enumerate(bones):
            p.rotation_quaternion = Quaternion(QQ[n, b]); p.keyframe_insert("rotation_quaternion", frame=n)
        root.location = LL[n]; root.keyframe_insert("location", frame=n)
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, len(idx) - 1
    return dict(clip=path, frames=len(idx), seam=round(seam, 2), motion=round(moving / step, 2),
                seam_raw=round(dist(N - 1, 0) / local_raw, 2))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = argv[argv.index("--out") + 1]
    clips = [a for a in argv if a.endswith(".glb") and a != out]
    results = []
    for c in clips:
        r = loop_one(c)
        if r:
            results.append(r); print(f"motion_loop: {json.dumps(r)}")
    if not results:
        sys.exit("motion_loop: no clip contains a moving stretch long enough to loop")
    # keep the longest of the clips that loop cleanly, else the cleanest seam
    clean = [r for r in results if r["seam"] <= 1.2]
    pick = max(clean, key=lambda r: r["frames"]) if clean else min(results, key=lambda r: r["seam"])
    loop_one(pick["clip"])                                   # rebuild the winner in this scene
    bpy.ops.export_scene.gltf(filepath=out, export_animations=True, export_force_sampling=True)
    print(f"motion_loop: kept {pick['clip']} -> {out} (seam {pick['seam']}x, {pick['frames']} frames)")


if __name__ == "__main__":
    main()
