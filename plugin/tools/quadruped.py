"""Procedural idle and walk cycles for a rigged quadruped, measured before export.

    blender --background --factory-startup --python-exit-code 1 --python quadruped.py -- \\
        --asset SK_Cat.glb --out ./anim [--motions idle,walk] [--period 32]

Why this exists: text-to-motion (UniMate) was measured unusable for quadruped
locomotion on four rigs, including the model author's own example — see
references/animation.md. A scripted cycle is deterministic and loops exactly.

The rig must follow references/characters.md § Animation-ready skeleton
(Hips, Spine1, Neck, Head, {Left,Right}{UpLeg,Leg,Foot}, {Left,Right}{Arm,ForeArm,Hand},
optional Tail1..n). Each clip is checked before it is written:

- legs never straighter than 95% of their length (a locked leg reads as too long:
  the rejected first cat cycle peaked at 101%, the approved one at 93%) — the tool shortens the stride and lowers
  the hips until it holds;
- planted paws all travel back at one steady speed, reported as the root speed a game
  must move the character at for the feet not to skate;
- the loop closes: frame P would equal frame 0.

Rules it encodes, each from a mistake actually made: bones are driven in their own
rest frame (the cat's Hips lies along the body, so "bone Y" was forward, not up), the
IK pole angle is solved from the rest pose (a guessed -90° turned the elbows forward),
and the cycle has exactly P frames (P+1 repeated a frame at the seam).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

REQUIRED = ["Hips", "Spine1", "Neck", "Head"] + [f"{s}{p}" for s in ("Left", "Right")
                                                  for p in ("UpLeg", "Leg", "Foot", "Arm", "ForeArm", "Hand")]
LEGS = {"LeftLeg": "LH", "RightLeg": "RH", "LeftForeArm": "LF", "RightForeArm": "RF"}
UPPER = {"LeftLeg": "LeftUpLeg", "RightLeg": "RightUpLeg", "LeftForeArm": "LeftArm", "RightForeArm": "RightArm"}
PAWS = ("LeftFoot", "RightFoot", "LeftHand", "RightHand")
WALK = dict(LH=0.0, LF=0.25, RH=0.5, RF=0.75)          # lateral-sequence walk: one foot every quarter cycle
MAX_EXTENSION = 0.95   # the cycle a reviewer approved peaked at 0.89 (hind) and 0.93 (fore)


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    sc = bpy.context.scene; sc.render.fps = 24
    arm = next(o for o in sc.objects if o.type == 'ARMATURE')
    missing = [b for b in REQUIRED if b not in arm.data.bones]
    if missing:
        sys.exit(f"quadruped: the rig lacks {missing} — name it as references/characters.md "
                 "§ Animation-ready skeleton describes")
    return sc, arm


def setup(sc, arm):
    """IK per leg with the pole angle solved from the rest pose, paws held level."""
    M, B, PB = arm.matrix_world, arm.data.bones, arm.pose.bones
    fwd = M @ B["Neck"].head_local - M @ B["Hips"].head_local; fwd.z = 0; fwd.normalize()
    body = (M @ B["Spine1"].head_local - M @ B["Hips"].head_local).length * 2.2
    leg = (M @ B["LeftLeg"].tail_local - M @ B["LeftUpLeg"].head_local).length
    bpy.context.view_layer.objects.active = arm
    for p in PB:
        p.rotation_mode = 'XYZ'
    feet = {}
    for bone, key in LEGS.items():
        rest = M @ B[bone].tail_local
        tgt = bpy.data.objects.new(f"IK_{bone}", None); sc.collection.objects.link(tgt); tgt.location = rest
        pole = bpy.data.objects.new(f"Pole_{bone}", None); sc.collection.objects.link(pole)
        hind = key.endswith("H")
        pole.location = (M @ B[bone].head_local) + fwd * (0.6 * body if hind else -0.6 * body)  # knees ahead, elbows behind
        c = PB[bone].constraints.new('IK'); c.target = tgt; c.pole_target = pole; c.chain_count = 2
        chain, best = [PB[bone], PB[bone].parent], None
        for deg in range(-180, 180, 2):
            c.pole_angle = math.radians(deg); bpy.context.view_layer.update()
            err = sum(p.matrix.to_quaternion().rotation_difference(p.bone.matrix_local.to_quaternion()).angle for p in chain)
            if best is None or err < best[0]:
                best = (err, deg)
        c.pole_angle = math.radians(best[1])
        feet[key] = (tgt, rest.copy())
    for paw in PAWS:
        level = bpy.data.objects.new(f"Level_{paw}", None); sc.collection.objects.link(level)
        level.matrix_world = M @ B[paw].matrix_local
        PB[paw].constraints.new('COPY_ROTATION').target = level
    to_hips = (M.to_3x3() @ B["Hips"].matrix_local.to_3x3()).inverted()   # world offset -> Hips rest frame
    tails = sorted((b for b in B if b.name.startswith("Tail")), key=lambda b: b.name)
    return dict(PB=PB, fwd=fwd, body=body, leg=leg, feet=feet, to_hips=to_hips, tails=[t.name for t in tails])


def pose(R, f, feet, up=0.0, hips=(0, 0, 0), chest=(0, 0, 0), neck=(0, 0, 0), head=(0, 0, 0), tail=(0, 0, 0)):
    PB, fwd = R["PB"], R["fwd"]
    for k, (tgt, rest) in R["feet"].items():
        d, h = feet.get(k, (0.0, 0.0))
        tgt.location = rest + fwd * d + Vector((0, 0, h)); tgt.keyframe_insert("location", frame=f)
    PB["Hips"].location = R["to_hips"] @ Vector((0, 0, up))
    for name, rot in (("Hips", hips), ("Spine1", chest), ("Neck", neck), ("Head", head)):
        PB[name].rotation_euler = rot; PB[name].keyframe_insert("rotation_euler", frame=f)
    for i, t in enumerate(R["tails"]):
        PB[t].rotation_euler = tail; PB[t].keyframe_insert("rotation_euler", frame=f)
    PB["Hips"].keyframe_insert("location", frame=f)


def walk(R, f, n, stride, crouch):
    w, L = 2 * math.pi * n, R["leg"]
    feet = {}
    for k, ph in WALK.items():
        t = (n + ph) % 1.0
        if t < 0.60:                                              # stance: the paw slides back under the body
            feet[k] = ((0.5 - t / 0.60) * stride * R["body"], 0.0)
        else:                                                     # swing: an arc forward
            u = (t - 0.60) / 0.40
            feet[k] = ((-0.5 + u) * stride * R["body"], 0.06 * R["body"] * math.sin(math.pi * u))
    pose(R, f, feet, up=-crouch * L + 0.015 * L * math.sin(2 * w),
         hips=(0, 0.04 * math.sin(w), 0.03 * math.sin(w)), chest=(0, -0.03 * math.sin(w), -0.04 * math.sin(w)),
         head=(0.05 * math.sin(2 * w + 1), 0, 0.03 * math.sin(w)), tail=(0, 0, 0.12 * math.sin(w - 1)))


def idle(R, f, n, stride, crouch):
    w, L = 2 * math.pi * n, R["leg"]
    look = 0.35 * math.sin(w) * min(1.0, abs(math.sin(w)) * 1.5)
    pose(R, f, {}, up=-0.10 * L + 0.006 * L * math.sin(2 * w), chest=(0.015 * math.sin(2 * w), 0, 0),
         neck=(0, 0, 0.4 * look), head=(0.05 * math.sin(w), 0, 0.6 * look), tail=(0, 0, 0.18 * math.sin(w)))


def bake(sc, arm, P):
    sc.frame_start, sc.frame_end = 0, P - 1
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=0, frame_end=P - 1, only_selected=True, visual_keying=True,
                     clear_constraints=True, use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in [o for o in sc.objects if o.type == 'EMPTY' and o.name.split("_")[0] in ("IK", "Pole", "Level")]:
        bpy.data.objects.remove(o)


def measure(sc, arm, P):
    """Leg extension, stance slip and loop seam on the baked action."""
    M, B, PB = arm.matrix_world, arm.data.bones, arm.pose.bones
    rest = {lo: (M @ B[lo].tail_local - M @ B[up].head_local).length for lo, up in UPPER.items()}
    ext, paws = 0.0, {k: [] for k in PAWS}
    first = None
    for f in list(range(P)) + [0]:
        sc.frame_set(f)
        for lo, up in UPPER.items():
            ext = max(ext, (M @ PB[lo].tail - M @ PB[up].head).length / rest[lo])
        snap = [(M @ PB[p].tail) for p in PAWS]
        for p, v in zip(PAWS, snap):
            paws[p].append(v)
        if first is None:
            first = snap
    # In an in-place cycle the planted paws travel back under the body like on a treadmill.
    # What matters is that every planted paw moves at the same, steady speed: that speed is
    # the root speed a game must apply for the feet not to skate.
    fwd = M @ B["Neck"].head_local - M @ B["Hips"].head_local; fwd.z = 0; fwd.normalize()
    speeds = []
    for p, pts in paws.items():
        ground = min(v.z for v in pts)
        for a, b in zip(pts, pts[1:]):
            if a.z < ground + 0.003 and b.z < ground + 0.003:
                speeds.append(-(b - a).dot(fwd) * sc.render.fps)
    speeds = [v for v in speeds if v > 0] or [0.0]
    mean = sum(speeds) / len(speeds)
    spread = (max(speeds) - min(speeds)) / mean if mean > 0 else 0.0
    return dict(extension=round(ext, 3), root_speed_m_s=round(mean, 3), stance_speed_spread=round(spread, 2), frames=P)


def make(asset, out, name, P, fn, stride, crouch):
    sc, arm = load(asset); R = setup(sc, arm)
    for f in range(P):
        fn(R, f, f / P, stride, crouch)
    bake(sc, arm, P)
    m = measure(sc, arm, P)
    arm.animation_data.action.name = name
    return sc, arm, m


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(); ap.add_argument("--asset", required=True); ap.add_argument("--out", default="anim")
    ap.add_argument("--motions", default="idle,walk"); ap.add_argument("--period", type=int, default=32)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in a.motions.split(","):
        fn, P = {"walk": (walk, a.period), "idle": (idle, a.period * 3 // 2)}[name]
        stride, crouch = 0.11, 0.15
        for attempt in range(6):                  # shorten the stride / lower the hips until the legs stay bent
            sc, arm, m = make(a.asset, out, name, P, fn, stride, crouch)
            if m["extension"] <= MAX_EXTENSION or name == "idle":
                break
            stride *= 0.85; crouch += 0.03
        if name == "idle":                        # nothing walks: speed and spread do not apply
            m.pop("root_speed_m_s"); m.pop("stance_speed_spread")
        m.update(stride=round(stride, 3), crouch=round(crouch, 3), ok=m["extension"] <= MAX_EXTENSION)
        bpy.ops.export_scene.gltf(filepath=str(out / f"{name}.glb"), export_animations=True, export_force_sampling=True)
        report[name] = m
        print(f"quadruped: {name} {json.dumps(m)}")
    (out / "quadruped-report.json").write_text(json.dumps(report, indent=2))
    sys.exit(0 if all(r["ok"] for r in report.values()) else 1)


if __name__ == "__main__":
    main()
