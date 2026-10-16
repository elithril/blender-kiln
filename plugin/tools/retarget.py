"""Kimodo preset clips onto a kiln-named humanoid: the maths, pure numpy (no bpy).

Adapted from image-to-3dlab (AssetFurnace), scripts/kimodo_retarget.py and
scripts/arm_clearance.py at v0.4.4 (commit 91879333), Copyright 2026 Bingeljell and
image-to-3dlab contributors, https://github.com/Bingeljell/image-to-3dlab, licensed under
the Apache License, Version 2.0 (tools/motions/LICENSE-image-to-3dlab.txt). See plugin/NOTICE.

Changed here: bones are found by kiln's names (references/characters.md § Animation-ready
skeleton) instead of by the tree's shape — on the Hunyuan3D humanoid, whose right arm ends
at the forearm, the shape search had put the forearm's turn on the upper arm; time can be
resampled (speed); the posed frames are kept as data so presets.py can correct them before
keying. Kept as upstream: SOMA's tables, the rest-pose alignment, the world-space turn per
bone, the hips' travel scaled by hip height, the arm clearance by capsules.

Kimodo (NVIDIA) writes motion for its 77-joint SOMA skeleton as world-space turns away from
SOMA's T-pose. Each rig bone takes its SOMA joint's turn, applied to its own rest
orientation after the limb is swung to point like SOMA's.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

# SOMA 77-joint order as Kimodo writes it (kimodo.skeleton.definitions.SOMASkeleton77).
SOMA77 = [
    "Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "HeadEnd", "Jaw",
    "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3", "LeftHandThumbEnd",
    "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3", "LeftHandIndex4", "LeftHandIndexEnd",
    "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3", "LeftHandMiddle4", "LeftHandMiddleEnd",
    "LeftHandRing1", "LeftHandRing2", "LeftHandRing3", "LeftHandRing4", "LeftHandRingEnd",
    "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3", "LeftHandPinky4", "LeftHandPinkyEnd",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "RightHandThumb1", "RightHandThumb2", "RightHandThumb3", "RightHandThumbEnd",
    "RightHandIndex1", "RightHandIndex2", "RightHandIndex3", "RightHandIndex4", "RightHandIndexEnd",
    "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3", "RightHandMiddle4", "RightHandMiddleEnd",
    "RightHandRing1", "RightHandRing2", "RightHandRing3", "RightHandRing4", "RightHandRingEnd",
    "RightHandPinky1", "RightHandPinky2", "RightHandPinky3", "RightHandPinky4", "RightHandPinkyEnd",
    "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd",
    "RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd",
]
SOMA_INDEX = {name: i for i, name in enumerate(SOMA77)}
SOMA77_PARENTS = [
    -1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 6, 3, 11, 12, 13, 14, 15, 16, 17, 14, 19, 20, 21, 22, 14, 24, 25, 26,
    27, 14, 29, 30, 31, 32, 14, 34, 35, 36, 37, 3, 39, 40, 41, 42, 43, 44, 45, 42, 47, 48, 49, 50, 42,
    52, 53, 54, 55, 42, 57, 58, 59, 60, 42, 62, 63, 64, 65, 0, 67, 68, 69, 70, 0, 72, 73, 74, 75,
]
SIDES = ("Left", "Right")
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
# kiln leg names -> SOMA's (SOMA calls the thigh "Leg" and the shin "Shin")
LEG_ROLES = {"UpLeg": "Leg", "Leg": "Shin", "Foot": "Foot", "ToeBase": "ToeBase"}
REQUIRED = ["Hips", "Head"] + [f"{s}{b}" for s in SIDES for b in ("UpLeg", "Leg", "Foot", "Arm", "ForeArm")]


class MappingError(ValueError):
    pass


def children(parents: dict[str, str | None]) -> dict[str, list[str]]:
    kids: dict[str, list[str]] = {b: [] for b in parents}
    for b, p in parents.items():
        if p is not None:
            kids[p].append(b)
    return kids


def parent_first(parents: dict[str, str | None]) -> list[str]:
    kids = children(parents)
    order = [b for b, p in parents.items() if p is None]
    i = 0
    while i < len(order):
        order += kids[order[i]]
        i += 1
    return order


def _spread(chain: list[str], names: list[str]) -> dict[str, str]:
    """Map rig bones in `chain` onto SOMA `names` (same order), stretching or squeezing."""
    if not chain:
        return {}
    if len(chain) == 1:
        return {chain[0]: names[-1]}
    idx = np.round(np.linspace(0, len(names) - 1, len(chain))).astype(int)
    return {b: names[i] for b, i in zip(chain, idx)}


def _follow(start: str, kids, pattern: str) -> list[str]:
    """From `start`, follow the child whose name matches `pattern` while there is one."""
    out = []
    b = start
    while True:
        nxt = [c for c in kids.get(b, []) if re.fullmatch(pattern, c)]
        if not nxt:
            return out
        b = nxt[0]
        out.append(b)


def kiln_to_soma(parents: dict[str, str | None]) -> dict[str, str]:
    """{rig bone: SOMA joint} for a rig named as references/characters.md § Animation-ready
    skeleton (what tools/autorig.py writes). Bones the motion has no joint for (ears, lids,
    a tail, connectors, extras) follow the nearest mapped bone above them, rigidly."""
    missing = [b for b in REQUIRED if b not in parents]
    if missing:
        raise MappingError(f"the rig lacks {missing}: name it as references/characters.md "
                           "§ Animation-ready skeleton (tools/autorig.py does)")
    kids = children(parents)
    m: dict[str, str] = {}
    spine = ["Hips"] + _follow("Hips", kids, r"Spine\d*")
    m.update(_spread(spine, ["Hips", "Spine1", "Spine2", "Chest"]))
    if "Neck" in parents:
        m["Neck"] = "Neck2"            # one neck bone: upstream's tree search gives it Neck2 too
    m["Head"] = "Head"
    for s in SIDES:
        for b in ("Shoulder", "Arm", "ForeArm", "Hand"):
            if s + b in parents:
                m[s + b] = s + b
        for b, role in LEG_ROLES.items():
            if s + b in parents:
                m[s + b] = s + role
        hand = s + "Hand"
        if hand not in parents:
            continue
        named = {c for c in parents if re.fullmatch(rf"{s}Hand({'|'.join(FINGERS)})\d", c)}
        for c in named:            # Mixamo fingers: Index1..3 is SOMA's Index2..4 (SOMA has the metacarpal)
            f, k = re.fullmatch(rf"{s}Hand(\w+?)(\d)", c).groups()
            m[c] = f"{s}Hand{f}{int(k) + (0 if f == 'Thumb' else 1)}"
        fingers = _follow(hand, kids, rf"{s}Fingers\d*")
        # kiln's one finger chain (a mitten): it moves as SOMA's middle finger, like upstream
        m.update(_spread(fingers, [f"{s}HandMiddle{i}" for i in (2, 3, 4)]))
    for b in parent_first(parents):
        if b not in m:
            p = parents[b]
            if p is None:
                raise MappingError(f"{b} is a second root: the rig must hang from Hips")
            m[b] = m[p]
    return m


def stiffen_fingers(mapping: dict[str, str]) -> dict[str, str]:
    """Fingers follow their hand rigidly instead of copying SOMA's curls (bad hand weights)."""
    return {b: (s.split("Hand")[0] + "Hand" if "Hand" in s and not s.endswith("Hand") else s)
            for b, s in mapping.items()}


def _flat(v, up):
    return v - (v @ up) * up


def character_frame(heads: dict[str, np.ndarray], up) -> np.ndarray:
    """3x3, columns (left, up, forward) in armature space. Forward is where the feet point
    (foot -> toe), or the knees' bend when the rig has no toes."""
    votes = []
    for s in SIDES:
        if s + "ToeBase" in heads:
            votes.append(heads[s + "ToeBase"] - heads[s + "Foot"])
        else:
            hip, knee, ankle = heads[s + "UpLeg"], heads[s + "Leg"], heads[s + "Foot"]
            votes.append(knee - (hip + ankle) / 2)
    f = _flat(np.mean(votes, axis=0), up)
    f /= np.linalg.norm(f)
    return np.stack([np.cross(up, f), up, f], axis=1)


def rotation_between(a, b) -> np.ndarray:
    """Smallest rotation (3x3) turning direction `a` onto direction `b`."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v, c = np.cross(a, b), float(a @ b)
    if c > 1 - 1e-12:
        return np.eye(3)
    if c < -1 + 1e-9:
        perp = np.cross(a, [1.0, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1.0, 0])
        perp /= np.linalg.norm(perp)
        return 2 * np.outer(perp, perp) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


def log_rot(r) -> np.ndarray:
    """Rotation matrix -> rotation vector (axis * angle)."""
    q = matrices_to_quaternions(r)
    w, v = q[0], q[1:]
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        return np.zeros(3)
    return v / n * 2 * np.arctan2(n, w)


def exp_rot(v) -> np.ndarray:
    angle = float(np.linalg.norm(v))
    if angle < 1e-12:
        return np.eye(3)
    k = v / angle
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(angle) * kx + (1 - np.cos(angle)) * kx @ kx


def soma_tpose(global_rots: np.ndarray, posed_joints0: np.ndarray) -> np.ndarray:
    """SOMA's T-pose joint positions (hips at origin), from frame 0:
    x_j = x_parent + G_parent @ (N_j - N_parent)."""
    n = np.zeros((77, 3))
    for j, p in enumerate(SOMA77_PARENTS):
        if p >= 0:
            n[j] = n[p] + global_rots[0, p].T @ (posed_joints0[j] - posed_joints0[p])
    return n


def rest_alignment(parents, heads, mapping, axes, tpose) -> dict[str, np.ndarray]:
    """Per-bone swing making the rig's rest point like SOMA's T-pose (limbs only; a hand
    turns with its forearm, a leaf with its parent). As upstream."""
    kids = children(parents)
    out = {}
    for b in parents:
        out[b] = np.eye(3)
        if len(kids[b]) != 1 or not mapping[b].startswith(SIDES):
            continue
        c = kids[b][0]
        j, k = SOMA_INDEX[mapping[b]], SOMA_INDEX[mapping[c]]
        want = axes @ (tpose[k] - tpose[j])
        have = heads[c] - heads[b]
        if np.linalg.norm(want) > 1e-6 and np.linalg.norm(have) > 1e-6:
            out[b] = rotation_between(have, want)
    for b, p in parents.items():
        if len(kids[b]) > 1 and p is not None and mapping[b].endswith("Hand"):
            out[b] = out[p]
    for b in parent_first(parents):
        p = parents[b]
        if not kids[b] and p is not None:
            out[b] = out[p]
    return out


def matrices_to_quaternions(m) -> np.ndarray:
    """[..., 3, 3] -> [..., 4] unit quaternions (w, x, y, z), w >= 0."""
    m = np.asarray(m, dtype=np.float64)
    w = np.sqrt(np.clip(1 + m[..., 0, 0] + m[..., 1, 1] + m[..., 2, 2], 0, None)) / 2
    x = np.sqrt(np.clip(1 + m[..., 0, 0] - m[..., 1, 1] - m[..., 2, 2], 0, None)) / 2
    y = np.sqrt(np.clip(1 - m[..., 0, 0] + m[..., 1, 1] - m[..., 2, 2], 0, None)) / 2
    z = np.sqrt(np.clip(1 - m[..., 0, 0] - m[..., 1, 1] + m[..., 2, 2], 0, None)) / 2
    x = np.copysign(x, m[..., 2, 1] - m[..., 1, 2])
    y = np.copysign(y, m[..., 0, 2] - m[..., 2, 0])
    z = np.copysign(z, m[..., 1, 0] - m[..., 0, 1])
    q = np.stack([w, x, y, z], axis=-1)
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def quaternions_to_matrices(q) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = (q[..., i] for i in range(4))
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
        np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
        np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1),
    ], -2)


def load_motion(path) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """(world rotations [T,77,3,3], frame-0 joints [77,3], hips track [T,3], fps) of a packed clip."""
    d = np.load(path)
    fps = float(d["fps"]) if "fps" in d.files else 30.0
    return (quaternions_to_matrices(d["quats"].astype(np.float64)), d["joints0"].astype(np.float64),
            d["hips"].astype(np.float64), fps)


def resample(g, hips, speed: float):
    """The clip played `speed` times faster (2 = half the frames), slerped on whole frames."""
    if speed <= 0:
        raise ValueError("speed must be positive")
    if abs(speed - 1) < 1e-9:
        return g, hips
    T = len(g)
    n = int(round((T - 1) / speed)) + 1
    src = np.linspace(0, T - 1, n)
    q = matrices_to_quaternions(g)
    out_q = np.empty((n,) + q.shape[1:])
    out_h = np.empty((n, 3))
    for k, s in enumerate(src):
        i = min(int(np.floor(s)), T - 2)
        u = s - i
        a, b = q[i], q[i + 1].copy()
        b[(a * b).sum(-1) < 0] *= -1
        out_q[k] = (1 - u) * a + u * b              # nlerp: frames 1/30 s apart, angles small
        out_h[k] = (1 - u) * hips[i] + u * hips[i + 1]
    return quaternions_to_matrices(out_q), out_h


def soma_hip_height(joints0) -> float:
    """Hips above the lowest foot joint on frame 0 (SOMA is Y-up)."""
    feet = [SOMA_INDEX[n] for n in ("LeftToeBase", "RightToeBase", "LeftFoot", "RightFoot")]
    return float(joints0[SOMA_INDEX["Hips"], 1] - joints0[feet, 1].min())


def posed(rest, parents, order, world_rot, root_pos) -> tuple[dict, dict]:
    """(pose, basis) 4x4 per bone for one frame. `rest` is Blender's bone.matrix_local,
    `world_rot` the wanted armature-space rotation per bone; Blender's rule
    pose_b = pose_parent @ inv(rest_parent) @ rest_b @ basis_b."""
    pose, basis = {}, {}
    for b in order:
        p = parents[b]
        rel = rest[b] if p is None else np.linalg.inv(rest[p]) @ rest[b]
        unposed = (np.eye(4) if p is None else pose[p]) @ rel
        target = np.eye(4)
        target[:3, :3] = world_rot[b]
        target[:3, 3] = root_pos if p is None else unposed[:3, 3]
        pose[b] = target
        basis[b] = np.linalg.inv(unposed) @ target
    return pose, basis


@dataclass
class Rig:
    """What the maths needs of a rig, in armature space (`up` is world up there)."""
    rest: dict          # bone -> 4x4 matrix_local
    tails: dict         # bone -> rest tail
    parents: dict
    up: np.ndarray
    points: np.ndarray  # skin vertices at rest
    owners: list        # each vertex's dominant bone

    def __post_init__(self):
        self.order = parent_first(self.parents)
        self.heads = {b: m[:3, 3].copy() for b, m in self.rest.items()}
        self.root = self.order[0]


def retarget(rig: Rig, g, joints0, hips, mapping, align=True):
    """Frames [(world_rot {bone: 3x3}, root_pos)] of a clip on the rig, as upstream."""
    frame = character_frame(rig.heads, rig.up)
    axes = frame                         # SOMA's frame is (left, up, forward) = identity
    lowest = min(h @ rig.up for h in rig.heads.values())
    hip_scale = float(rig.heads[rig.root] @ rig.up - lowest) / soma_hip_height(joints0)
    tpose = soma_tpose(g[:1], joints0)
    al = rest_alignment(rig.parents, rig.heads, mapping, axes, tpose) if align else \
        {b: np.eye(3) for b in rig.order}
    rest_rot = {b: rig.rest[b][:3, :3] for b in rig.order}
    idx = {b: SOMA_INDEX[mapping[b]] for b in rig.order}
    frames = []
    for t in range(len(g)):
        wr = {b: axes @ g[t, idx[b]] @ axes.T @ al[b] @ rest_rot[b] for b in rig.order}
        root = rig.rest[rig.root][:3, 3] + axes @ (hips[t] - hips[0]) * hip_scale
        frames.append((wr, root))
    return frames, dict(frame=frame, hip_scale=hip_scale)


# ── arm clearance (adapted from upstream's arm_clearance.py) ────────────────────────────
# SOMA roles the arms must stay out of. Upstream: torso, neck, head, the shoulders.
BODY_ROLES = ("Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "LeftShoulder", "RightShoulder")
ARM_ROLES = ("Arm", "ForeArm", "Hand")
BODY_PERCENTILE = 85
HEAD_TO_TORSO = 1.1
TORSO_ROLES = ("Spine1", "Spine2", "Chest")
ARM_PERCENTILE = 60


def point_segment(p, a, b):
    axis = b - a
    l2 = float(axis @ axis)
    t = 0.0 if l2 == 0 else min(1.0, max(0.0, float((p - a) @ axis) / l2))
    c = a + t * axis
    return float(np.linalg.norm(p - c)), c


def skin_radii(points, owners, segments, bones, percentile):
    owners = np.asarray(owners)
    radii = {}
    for bone in bones:
        mine = points[owners == bone]
        if len(mine) and bone in segments:
            a, b = segments[bone]
            radii[bone] = float(np.percentile([point_segment(p, a, b)[0] for p in mine], percentile))
    return radii


@dataclass
class Proxy:
    body: dict
    arms: dict
    side_shoulder: dict
    margin: float


def build_proxy(rig: Rig, mapping, body_roles=BODY_ROLES) -> Proxy | None:
    """Capsules round the body's bones, each as thick as the skin it carries, from the rest."""
    by_role = {}
    for bone in rig.order:
        by_role.setdefault(mapping[bone], bone)
    segs = {b: (rig.heads[b], rig.tails[b]) for b in rig.order}
    height = max(h @ rig.up for h in rig.heads.values()) - min(h @ rig.up for h in rig.heads.values())
    arms = {}
    for s in SIDES:
        bones = [by_role.get(f"{s}{r}") for r in ARM_ROLES]
        if None in bones:          # an arm without its hand (fused to the body) is left as it is
            continue
        r = skin_radii(rig.points, rig.owners, segs, bones, ARM_PERCENTILE)
        arms[s] = {"upper": bones[0], "fore": bones[1], "hand": bones[2], "radius": {b: r.get(b, 0.0) for b in bones}}
    if not arms:
        return None
    body = skin_radii(rig.points, rig.owners, segs, [by_role[r] for r in body_roles if r in by_role], BODY_PERCENTILE)
    torso = max((r for b, r in body.items() if mapping[b] in TORSO_ROLES), default=None)
    if torso is not None:
        body = {b: (min(r, torso * HEAD_TO_TORSO) if mapping[b] == "Head" else r) for b, r in body.items()}
    return Proxy(body=body, arms=arms, side_shoulder={s: by_role.get(f"{s}Shoulder") for s in SIDES},
                 margin=0.01 * height)


def _sideways(direction, along):
    u = along / np.linalg.norm(along)
    side = direction - (direction @ u) * u
    n = float(np.linalg.norm(side))
    return side / n if n > 1e-6 else np.zeros(3)


def arm_swing(seg, proxy: Proxy, side, iterations=10):
    """Rotation about the shoulder taking one arm's elbow, forearm and hand out of every capsule."""
    arm = proxy.arms[side]
    pivot = seg[arm["upper"]][0]
    caps = [(seg[b][0], seg[b][1], r) for b, r in proxy.body.items() if b != proxy.side_shoulder.get(side)]
    fa, fb = seg[arm["fore"]]
    ha, hb = seg[arm["hand"]]
    r = arm["radius"]
    points = [(fa, r[arm["fore"]]), ((fa + fb) / 2, r[arm["fore"]]), (ha, r[arm["hand"]]), (hb, r[arm["hand"]])]
    total = np.eye(3)
    for _ in range(iterations):
        worst, push = 0.0, None
        for p, ra in points:
            for a, b, rb in caps:
                d, closest = point_segment(p, a, b)
                depth = rb + ra + proxy.margin - d
                if depth > worst and d > 1e-9:
                    away = _sideways(p - closest, p - pivot)
                    if not away.any():
                        away = _sideways(pivot - point_segment(pivot, a, b)[1], p - pivot)
                    if not away.any():
                        away = _sideways(np.cross(b - a, p - pivot), p - pivot)
                    if away.any():
                        worst, push = depth, (p, away)
        if push is None:
            break
        p, normal = push
        step = rotation_between(p - pivot, p + normal * worst - pivot)
        total = step @ total
        points = [(pivot + step @ (q - pivot), rr) for q, rr in points]
    return total


def smooth_swings(swings, radius=4, cyclic=False):
    """Each frame's swing spread over its neighbours, never below the raw swing."""
    v = np.array([log_rot(s) for s in swings])
    n = len(v)
    w = np.exp(-0.5 * (np.arange(-radius, radius + 1) / max(radius / 2, 1)) ** 2)
    out = []
    for t in range(n):
        if cyclic:
            ids = [(t + k) % n for k in range(-radius, radius + 1)]
            ww = w
        else:
            lo, hi = max(0, t - radius), min(n, t + radius + 1)
            ids = list(range(lo, hi))
            ww = w[lo - t + radius:hi - t + radius]
        blended = (v[ids] * ww[:, None]).sum(0) / ww.sum()
        out.append(exp_rot(blended if np.linalg.norm(blended) >= np.linalg.norm(v[t]) else v[t]))
    return out


def subtree(root, parents):
    kids = children(parents)
    out, stack = [], [root]
    while stack:
        b = stack.pop()
        out.append(b)
        stack.extend(kids[b])
    return out


def segments(rig: Rig, pose):
    out = {}
    for b in rig.order:
        moved = pose[b] @ np.linalg.inv(rig.rest[b])
        out[b] = (pose[b][:3, 3], (moved @ np.append(rig.tails[b], 1.0))[:3])
    return out


def clear_arms(rig: Rig, frames, proxy: Proxy, cyclic=False) -> dict:
    """Swing each arm out of the body wherever it went in, in place. Returns the swings' sizes."""
    report = {}
    sides = list(proxy.arms)
    sw = {s: [] for s in sides}
    for wr, root in frames:
        seg = segments(rig, posed(rig.rest, rig.parents, rig.order, wr, root)[0])
        for s in sides:
            sw[s].append(arm_swing(seg, proxy, s))
    for s in sides:
        deg = [float(np.degrees(np.linalg.norm(log_rot(r)))) for r in sw[s]]
        report[s] = dict(largest_deg=round(max(deg), 1), median_deg=round(float(np.median(deg)), 1))
        arm = subtree(proxy.arms[s]["upper"], rig.parents)
        for (wr, _), swing in zip(frames, smooth_swings(sw[s], cyclic=cyclic)):
            for b in arm:
                wr[b] = swing @ wr[b]
    return report


def bases(rig: Rig, frames):
    """Blender matrix_basis (4x4) per bone per frame."""
    return [posed(rig.rest, rig.parents, rig.order, wr, root)[1] for wr, root in frames]
