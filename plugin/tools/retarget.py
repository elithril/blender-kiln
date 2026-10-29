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
    weights: list | None = None   # each vertex's {bone: weight}, for the feet's true skinned heights

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
# SOMA roles the arms must stay out of. Upstream: torso, neck, head, the shoulders, and only
# the elbow, forearm and hand are kept out. kiln adds the hips (the belly and the pelvis), a
# point at 80% of the upper arm, and thicker capsules (95th percentile of the skin's distance
# to its bone, upstream 85th): on the kiln child the upper arm through the flanks was 2,170 of
# the walk's 2,638 mm² of arm through body, on the Hunyuan humanoid the arms through the hips
# 1,176 of 1,538. What the clearance adds is capped at 25 degrees, so a hanging arm stays a
# hanging arm: uncapped, with points at 50% and 80% of the upper arm, the child's arms were
# swung out 61-78 degrees (median) to clear its round belly, back to its rest A-pose. The
# thighs stay out, as upstream found: their outline held hanging arms out like wings.
BODY_ROLES = ("Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "LeftShoulder", "RightShoulder")
UPSTREAM_BODY_ROLES = BODY_ROLES[1:]
UPPER_ARM_POINTS = (0.8,)        # along the upper arm, shoulder to elbow
MAX_SWING_DEG = 25.0             # the largest swing out the clearance may add to an arm
ARM_PERCENTILE = 60
BODY_PERCENTILE = 95
UPSTREAM_BODY_PERCENTILE = 85
HEAD_TO_TORSO = 1.1
ARM_ROLES = ("Arm", "ForeArm", "Hand")
TORSO_ROLES = ("Spine1", "Spine2", "Chest")


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
    max_swing: float = 180.0


def build_proxy(rig: Rig, mapping, body_roles=BODY_ROLES, percentile=BODY_PERCENTILE,
                max_swing=MAX_SWING_DEG) -> Proxy | None:
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
    body = skin_radii(rig.points, rig.owners, segs, [by_role[r] for r in body_roles if r in by_role], percentile)
    torso = max((r for b, r in body.items() if mapping[b] in TORSO_ROLES), default=None)
    if torso is not None:
        body = {b: (min(r, torso * HEAD_TO_TORSO) if mapping[b] == "Head" else r) for b, r in body.items()}
    return Proxy(body=body, arms=arms, side_shoulder={s: by_role.get(f"{s}Shoulder") for s in SIDES},
                 margin=0.01 * height, max_swing=max_swing)


def _sideways(direction, along):
    u = along / np.linalg.norm(along)
    side = direction - (direction @ u) * u
    n = float(np.linalg.norm(side))
    return side / n if n > 1e-6 else np.zeros(3)


def arm_swing(seg, proxy: Proxy, side, iterations=10, upper_points=UPPER_ARM_POINTS):
    """Rotation about the shoulder taking one arm's upper arm, elbow, forearm and hand out of
    every capsule."""
    arm = proxy.arms[side]
    pivot = seg[arm["upper"]][0]
    caps = [(seg[b][0], seg[b][1], r) for b, r in proxy.body.items() if b != proxy.side_shoulder.get(side)]
    fa, fb = seg[arm["fore"]]
    ha, hb = seg[arm["hand"]]
    r = arm["radius"]
    points = [(pivot + u * (fa - pivot), r[arm["upper"]]) for u in upper_points]
    points += [(fa, r[arm["fore"]]), ((fa + fb) / 2, r[arm["fore"]]), (ha, r[arm["hand"]]), (hb, r[arm["hand"]])]
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
    v = log_rot(total)
    ang = float(np.linalg.norm(v))
    if ang > np.radians(proxy.max_swing):
        total = exp_rot(v * np.radians(proxy.max_swing) / ang)
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


def clear_arms(rig: Rig, frames, proxy: Proxy, cyclic=False, upper_points=UPPER_ARM_POINTS) -> dict:
    """Swing each arm out of the body wherever it went in, in place. Returns the swings' sizes."""
    report = {}
    sides = list(proxy.arms)
    sw = {s: [] for s in sides}
    for wr, root in frames:
        seg = segments(rig, posed(rig.rest, rig.parents, rig.order, wr, root)[0])
        for s in sides:
            sw[s].append(arm_swing(seg, proxy, s, upper_points=upper_points))
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


# ── foot locking (kiln) ───────────────────────────────────────────────────────────────────
# Upstream copies the clip's hips and turns, so a foot meant to stand slides wherever the
# character's legs are not the actor's: 293 mm/s on the kiln child's walk, 568 on the Hunyuan
# humanoid's, and that one's soles 38 mm under the floor. Here each foot is pinned while it
# stands: the skin points it rolls on stay where they were on the frame before, the lowest
# one on the floor, and a two-bone solve moves the thigh and shin to put the ankle there.
# Standing is read off the actor, not the rig: on the chibi child the retargeted swing foot
# dips 23 mm under the floor while the standing one sits 5-8 mm above it, so the rig's own
# heights pick the wrong frames. SOMA's ankle or toe joint, near its lowest and slow, is not
# fooled: an actor's standing foot moves < 0.1 m/s and swings at 1-10 m/s in these clips.
CONTACT_HEIGHT = 0.035   # m above that joint's lowest in the clip (SOMA is a 1.7 m actor)
CONTACT_SPEED = 0.40     # m/s of the clip's own time
# A foot in the air clears the floor by this x H (H = 2.5 cm x height / 1.7 m, the foot-skate
# scale): the chibi child's swing foot skimmed 0-6 mm over it at 1.5 m/s, which reads as a
# foot dragged along the floor, not lifted.
LIFT = 0.8
FOOT_SKATE_H = 0.025
ROLL_SET_MM = 3.0        # the points a foot rolls on: within 3 mm of its lowest (the measure's)
FLOOR_MARGIN = 0.001     # the lowest sole point sits this far above the rest floor
EDGE_EASE = 6            # frames over which a correction eases in and out, at a clip's ends
REACH = 0.9995           # a leg straighter than this share of its length cannot be solved
# Past SOFT_REACH of its length, a leg's reach eases toward REACH instead of stopping dead: clamped
# hard, a foot planted a little too far pulled the knee straight on one frame and bent it on the
# next — knees that "tremblent" (kiln's mascot and the bench's, 1.4-2 spikes of 8+ deg a second,
# tools/motion_measure.py knee_pops). The gap left is what lock_feet lowers the hips for. On the
# bench mascot's walk: hard 7 spikes, from 0.97 2, 0.95 1, 0.93 none — the slide 36 -> 42 mm/s.
SOFT_REACH = 0.93
# A knee posed straighter than 5 degrees bends toward the thigh's front; past 25 degrees, in the
# plane it was posed in. Taken from the pose alone, the plane of a near-straight leg is noise:
# the child's walk flipped its knee 130-155 degrees from one frame to the next at heel strike
# and toe-off, and bent it backward up to 44 degrees.
POLE_BEND = (5.0, 25.0)


def soma_joints(g, joints0, hips) -> np.ndarray:
    """[T, 77, 3] SOMA joint positions (Y up) of a clip, by forward kinematics."""
    n = soma_tpose(g[:1], joints0)
    X = np.zeros((len(g), 77, 3))
    X[:, 0] = hips
    for j, p in enumerate(SOMA77_PARENTS):
        if p >= 0:
            X[:, j] = X[:, p] + np.einsum("tij,j->ti", g[:, p], n[j] - n[p])
    return X


def soma_contacts(g, joints0, hips, fps, speed=1.0) -> dict:
    """Per side, the frames the actor stands on that foot: its ankle or toe joint low and slow."""
    X = soma_joints(g, joints0, hips)
    out = {}
    for s in SIDES:
        c = np.zeros(len(g), bool)
        for jn in ("Foot", "ToeBase"):
            x = X[:, SOMA_INDEX[s + jn]]
            h = x[:, 1] - x[:, 1].min()
            v = np.linalg.norm(np.diff(x[:, [0, 2]], axis=0), axis=1) * fps / speed
            v = np.minimum(np.r_[v[:1], v], np.r_[v, v[-1:]])     # slower of the steps in and out
            c |= (h < CONTACT_HEIGHT) & (v < CONTACT_SPEED)
        out[s] = c
    return out


def foot_sets(rig: Rig, cap=600):
    """Per side: (bones, weights [N, bones], rest points [N, 3]) of the skin the foot and toes
    carry, skinned as the mesh is (dominant bone alone when no weights are given)."""
    out = {}
    for s in SIDES:
        own = {b for b in rig.order if re.fullmatch(rf"{s}(Foot|ToeBase|Toe_End\d*)", b)}
        idx = [i for i, o in enumerate(rig.owners) if o in own]
        if len(idx) > cap:
            idx = [idx[k] for k in np.linspace(0, len(idx) - 1, cap).astype(int)]
        if not idx:
            out[s] = None
            continue
        ws = [rig.weights[i] if rig.weights else {rig.owners[i]: 1.0} for i in idx]
        bones = sorted({b for w in ws for b in w})
        W = np.array([[w.get(b, 0.0) for b in bones] for w in ws])
        W /= W.sum(1, keepdims=True)
        out[s] = (bones, W, rig.points[idx], [np.linalg.inv(rig.rest[b]) for b in bones])
    return out


def _foot_world(pose, fs):
    bones, W, V, inv = fs
    P = np.zeros_like(V)
    for k, b in enumerate(bones):
        M = pose[b] @ inv[k]
        P += W[:, k:k + 1] * (V @ M[:3, :3].T + M[:3, 3])
    return P


def _runs(mask, cyclic):
    """[(start, end)] inclusive runs of True; a run through the seam of a cycle is one run."""
    n = len(mask)
    if mask.all():
        return [(0, n - 1)]
    out, t = [], 0
    while t < n:
        if mask[t]:
            s = t
            while t + 1 < n and mask[t + 1]:
                t += 1
            out.append((s, t))
        t += 1
    if cyclic and len(out) > 1 and out[0][0] == 0 and out[-1][1] == n - 1:
        s, _ = out.pop()
        out[0] = (s, out[0][1] + n)          # end past n: indices are taken modulo n
    return out


def _clean(mask, cyclic, gap=2, shortest=2):
    """Fill gaps of up to `gap` frames, drop contacts shorter than `shortest`."""
    m = mask.copy()
    n = len(m)
    for s, e in _runs(~m, cyclic):
        if e - s + 1 <= gap and (cyclic or (s > 0 and e < n - 1)):
            for t in range(s, e + 1):
                m[t % n] = True
    for s, e in _runs(m, cyclic):
        if e - s + 1 < shortest and e - s + 1 < n:
            for t in range(s, e + 1):
                m[t % n] = False
    return m


def two_bone(H, K0, A0, A, L1, L2, ahead=None):
    """Knee and ankle for a leg hip H -> knee -> ankle reaching for A, bending in the plane
    the knee bent in (K0, A0 as posed). A leg posed near straight says nothing of that plane:
    the knee then bends toward `ahead` (where the thigh's front points), fully below
    POLE_BEND[0] degrees of bend, eased to the posed plane by POLE_BEND[1]. Returns (knee,
    ankle reached)."""
    d_vec = A - H
    d = float(np.linalg.norm(d_vec))
    u = d_vec / max(d, 1e-9)
    d = max(d, abs(L1 - L2) + 1e-6)
    soft, hard = SOFT_REACH * (L1 + L2), REACH * (L1 + L2)
    if d > soft:
        d = soft + (hard - soft) * (1 - np.exp(-(d - soft) / (hard - soft)))
    p = (K0 - H) - ((K0 - H) @ u) * u
    if np.linalg.norm(p) < 1e-6:
        p = (A0 - H) - ((A0 - H) @ u) * u
    if ahead is not None:
        q = ahead - (ahead @ u) * u
        bend = np.degrees(np.arccos(np.clip(_unit(K0 - H) @ _unit(A0 - K0), -1, 1)))
        w = float(np.clip((bend - POLE_BEND[0]) / (POLE_BEND[1] - POLE_BEND[0]), 0, 1))
        w = 3 * w * w - 2 * w ** 3
        if np.linalg.norm(q) > 1e-6:
            p = w * _unit(p) + (1 - w) * _unit(q) if np.linalg.norm(p) > 1e-9 else q
    if np.linalg.norm(p) < 1e-6:
        p = np.cross(u, [1.0, 0, 0])
    p /= np.linalg.norm(p)
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    h = np.sqrt(max(L1 * L1 - a * a, 0.0))
    return H + a * u + h * p, H + d * u


def _unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def _solve_leg(wr, pose, s, A_move, L, ahead=None):
    """Two-bone solve putting side `s`'s ankle at its posed place + A_move. Returns the gap
    left. `ahead`: the thigh's front at rest (armature space), turned with the thigh here."""
    H, K0, A0 = (pose[s + x][:3, 3] for x in ("UpLeg", "Leg", "Foot"))
    A = A0 + A_move
    K, Ar = two_bone(H, K0, A0, A, *L, ahead=None if ahead is None else wr[s + "UpLeg"] @ ahead[s])
    wr[s + "UpLeg"] = rotation_between(K0 - H, K - H) @ wr[s + "UpLeg"]
    wr[s + "Leg"] = rotation_between(A0 - K0, Ar - K) @ wr[s + "Leg"]
    return float(np.linalg.norm(A - Ar))


def _smooth_gaps(delta, cyclic):
    """Fill the frames between contacts (NaN rows): from one correction to the next, eased;
    at a clip's open ends, eased to nothing over EDGE_EASE frames."""
    n = len(delta)
    known = ~np.isnan(delta[:, 0])
    if not known.any():
        delta[:] = 0.0
        return delta
    for a, b in _runs(~known, cyclic):
        ids = [t % n for t in range(a, b + 1)]
        before, after = (a - 1) % n, (b + 1) % n
        for k, t in enumerate(ids):
            if not cyclic and a == 0:
                w = max(0.0, 1 - (len(ids) - k) / EDGE_EASE)
                delta[t] = delta[after] * (3 * w * w - 2 * w ** 3)
            elif not cyclic and b == n - 1:
                w = max(0.0, 1 - (k + 1) / EDGE_EASE)
                delta[t] = delta[before] * (3 * w * w - 2 * w ** 3)
            else:
                u = (k + 1) / (len(ids) + 1)
                u = 3 * u * u - 2 * u ** 3
                delta[t] = (1 - u) * delta[before] + u * delta[after]
    return delta


def lock_feet(rig: Rig, frames, fps, contacts, cyclic=False, tread=None, iterations=3) -> dict:
    """Pin each foot to the floor while it stands (`contacts`, from `soma_contacts`), in place.

    A standing foot's lowest skin points (within 3 mm) stay where they were on the frame
    before, so it rolls heel to toe without sliding, the lowest point on the floor; a foot in
    the air clears the floor by LIFT x H. `tread`: on an in-place cycle, the speed (horizontal,
    m/s) a standing foot moves back at; None for a clip that travels. Where a leg cannot reach,
    the hips are lowered just enough, eased over the frames around."""
    up = rig.up
    pts_all = rig.points @ up
    floor = float(pts_all.min())
    lift = LIFT * FOOT_SKATE_H * float(pts_all.max() - floor) / 1.7
    sets = foot_sets(rig)
    dt = 1.0 / fps
    n = len(frames)
    L = {s: (float(np.linalg.norm(rig.heads[s + "Leg"] - rig.heads[s + "UpLeg"])),
             float(np.linalg.norm(rig.heads[s + "Foot"] - rig.heads[s + "Leg"]))) for s in SIDES}
    tv = np.zeros(3) if tread is None else np.asarray(tread, float)
    tv = tv - (tv @ up) * up
    contact = {s: _clean(np.asarray(contacts[s], bool), cyclic) for s in SIDES}
    fwd = character_frame(rig.heads, up)[:, 2]
    ahead = {s: rig.rest[s + "UpLeg"][:3, :3].T @ fwd for s in SIDES}
    pose_of = lambda w: [posed(rig.rest, rig.parents, rig.order, wr, root)[0] for wr, root in w]
    report = {}
    drop = np.zeros(n)
    raw = [({b: r.copy() for b, r in wr.items()}, root.copy()) for wr, root in frames]
    for it in range(iterations):
        work = [({b: r.copy() for b, r in wr.items()}, root - drop[t] * up) for t, (wr, root) in enumerate(raw)]
        poses = pose_of(work)
        short = np.zeros(n)
        for s in SIDES:
            if sets[s] is None:
                continue
            c = contact[s]
            P = [_foot_world(p, sets[s]) for p in poses]
            delta = np.full((n, 3), np.nan)
            runs = _runs(c, cyclic)
            for a, b in runs:
                ids = [t % n for t in range(a, b + 1)]
                whole = cyclic and len(ids) == n        # standing through the whole cycle
                pairs = list(zip(ids[:-1], ids[1:])) + ([(ids[-1], ids[0])] if whole else [])
                d = np.zeros((len(ids) + (1 if whole else 0), 3))
                for k, (t0, t1) in enumerate(pairs, 1):
                    zz = P[t0] @ up
                    roll = zz <= zz.min() + ROLL_SET_MM / 1000
                    move = (P[t1][roll] - P[t0][roll]).mean(0)
                    d[k] = d[k - 1] - (move - (move @ up) * up) + (0 if whole else tv * dt)
                if whole:                               # it must come back to where it started
                    d = d[:-1] - np.outer(np.arange(n) / n, d[-1])
                d -= d.mean(0)
                for k, t in enumerate(ids):
                    delta[t] = d[k] + (floor + FLOOR_MARGIN - float((P[t] @ up).min())) * up
            _smooth_gaps(delta, cyclic)
            for t in range(n):
                low = float((P[t] @ up).min()) + float(delta[t] @ up)
                want = floor + FLOOR_MARGIN + (0.0 if c[t] else lift)
                if low < want:
                    delta[t] += (want - low) * up
                gap = _solve_leg(work[t][0], poses[t], s, delta[t], L[s], ahead)
                if c[t]:
                    short[t] = max(short[t], gap)
            report[s] = dict(contact_frames=int(c.sum()), contacts=len(runs),
                             largest_shift_mm=round(1000 * float(np.abs(delta).max()), 1))
        # the solve changed the shin's turn too, which moves the skin it shares with the foot:
        # read the true lowest points again and settle them on the floor, or above it
        poses = pose_of(work)
        for s in SIDES:
            if sets[s] is None:
                continue
            for t in range(n):
                low = float((_foot_world(poses[t], sets[s]) @ up).min())
                want = floor + FLOOR_MARGIN + (0.0 if contact[s][t] else lift)
                dz = want - low if contact[s][t] else max(0.0, want - low)
                if abs(dz) > 1e-5:
                    _solve_leg(work[t][0], poses[t], s, dz * up, L[s], ahead)
        if short.max() <= 0.001 or it == iterations - 1:
            break
        need = np.zeros(n)
        for t in range(n):
            for k in range(-3, 4):
                j = (t + k) % n if cyclic else min(max(t + k, 0), n - 1)
                need[t] = max(need[t], short[j])
        drop = drop + np.convolve(np.pad(need, 3, mode="wrap" if cyclic else "edge"), np.ones(7) / 7, "valid")
    for t, (wr, root) in enumerate(work):
        frames[t] = (wr, root)
    report["hips_lowered_mm"] = round(1000 * float(drop.max()), 1)
    report["unreached_mm"] = round(1000 * float(short.max()), 1)
    return report


# ── a foot in the air (kiln) ────────────────────────────────────────────────────────────
# Kimodo's actor points its toes down as each foot leaves the floor; retargeted onto kiln's mascot,
# the foot dropped 67 deg below its rest pitch at mid-swing (rest -20, swing -87), tiptoeing in big
# boots — "les pieds sont pas vraiment à plat" (Nicolas, 2026-10-29). Standing, it did no better: the
# actor's planted foot came across 20-25 deg toes-down, heel off the floor, where the rig's own rest has
# the sole flat. So the foot's pitch while standing (its median) is brought back to its rest pitch,
# the sole flat; a foot in the air keeps its turn off that under FOOT_SWING_PITCH[0] degrees and is
# eased toward at most [1] past it; lock_feet, which runs after, plants the feet on the floor.
FOOT_SWING_PITCH = (10.0, 22.0)
# The correction is worked out for the feet in the air, then smoothed over a few frames: the steepest
# turn comes on the frames right after the toe leaves the floor (57-72 deg on the mascot), so a
# correction that only started there either snapped or let most of it through (51 deg).
FOOT_SMOOTH = np.array([1.0, 2.0, 3.0, 2.0, 1.0]) / 9.0


def _soft_pitch(p, knee, top):
    a = abs(p)
    return p if a <= knee else float(np.sign(p)) * (knee + (top - knee) * np.tanh((a - knee) / (top - knee)))


def ease_swing_feet(rig: Rig, frames, contacts, cyclic=False, limits=FOOT_SWING_PITCH) -> tuple[list, dict]:
    """The frames with each foot standing at its rest pitch (the sole flat) and, in the air, turned at most
    `limits[1]` deg off it (about the character's left axis), its toes following; and per side the
    standing pitch off rest, then the largest turn in the air, before -> after (deg)."""
    axes = character_frame(rig.heads, rig.up)
    out = [(dict(wr), pos) for wr, pos in frames]
    n = len(out)
    info = {}
    for s in SIDES:
        foot = s + "Foot"
        if foot not in rig.rest or foot not in out[0][0]:
            continue
        rest = rig.rest[foot][:3, :3]
        below = [b for b in subtree(foot, rig.parents) if b in out[0][0]]
        c = _clean(np.asarray(contacts[s], bool), cyclic)
        ypr = [_ypr(axes.T @ out[t][0][foot] @ rest.T @ axes) for t in range(n)]
        p = np.array([v[1] for v in ypr])
        planted = float(np.median(p[c])) if c.any() else 0.0
        off = p - planted
        want = np.array([o if c[t] else np.radians(_soft_pitch(np.degrees(o), *limits)) for t, o in enumerate(off)])
        k = len(FOOT_SMOOTH) // 2
        fix = np.convolve(np.pad(want - off, k, mode="wrap" if cyclic else "edge"), FOOT_SMOOTH, "valid") - planted
        for t in range(n):
            if abs(fix[t]) < 1e-6:
                continue
            y, _, r = ypr[t]
            turn = axes @ _from_ypr(y, p[t] + fix[t], r) @ axes.T @ rest @ out[t][0][foot].T
            for b in below:
                out[t][0][b] = turn @ out[t][0][b]
        air = ~c
        info[s] = dict(standing_off_rest_deg=round(float(np.degrees(planted)), 1),
                       air_deg=[round(float(np.degrees(np.abs(off[air]).max())), 1) if air.any() else 0.0,
                                round(float(np.degrees(np.abs(off + fix + planted)[air].max())), 1) if air.any() else 0.0])
    return out, info


# ── loops (kiln) ──────────────────────────────────────────────────────────────────────────
# A preset is a take, not a cycle: the walk starts from standing and ends mid-stride, and
# played on repeat it jumped 6.2 frame steps at the seam (child; 6.4 Hunyuan). For a cyclic
# motion the window whose end matches its start, in pose and in the way through it, is cut
# out; what is left of the mismatch is spread over the whole window, so frame P is frame 0
# exactly and is keyed again as the closing key (references/animation.md rule 5); the hips'
# travel is taken out, leaving an in-place cycle and the speed the game moves it at.
LOOP_MIN_SECONDS = 0.6
LOOP_MOVING = 0.7        # a window moving less than 0.7 x the clip's median step is refused
STILL_SPEED = 0.05       # m/s on a 1.7 m human: an in-place cycle slower than this stands still


# ── a calmer gait (kiln) ────────────────────────────────────────────────────────────────
# Kimodo's walk swings the pelvis 18.8 deg of roll and 13.5 deg of yaw peak to peak — about twice
# a human walk; on a chibi with short legs and wide hips it reads as a waddle (measured on kiln's
# mascot and on the 3.0 bench's chibi: identical). Calming the hips alone made it worse: the head
# rolled 12.2 deg instead of 4.3, the spine had been compensating. So the hips' roll and yaw, their
# side sway, the spine's and neck's own turns and the head's roll and yaw in the world are scaled
# down together; the feet are put back by lock_feet afterwards. On the mascot (2026-10-28): hips
# 4.7 deg roll / 5.4 yaw / 11.5 mm sway, head 1.1 deg roll / 1.0 yaw — "beaucoup mieux".
CALM = dict(roll=0.25, yaw=0.4, sway=0.5, spine=0.4, head=0.25, head_pitch=0.7)
CALM_CHAIN = ("Spine", "Spine1", "Spine2", "Neck")
GAITS = ("walk", "walk_woman", "run", "sneak")


def _ypr(r) -> tuple[float, float, float]:
    """(yaw, pitch, roll) of r = Ry(yaw) Rx(pitch) Rz(roll), in the character frame (left, up, forward)."""
    return (float(np.arctan2(r[0, 2], r[2, 2])), float(np.arcsin(np.clip(-r[1, 2], -1, 1))),
            float(np.arctan2(r[1, 0], r[1, 1])))


def _from_ypr(yaw, pitch, roll) -> np.ndarray:
    cy, sy, cp, sp, cr, sr = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch), np.cos(roll), np.sin(roll)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return ry @ rx @ rz


def calm(rig: Rig, frames, k=CALM) -> tuple[list, dict]:
    """The frames with a calmer pelvis, spine and head (see CALM above), and what it changed:
    peak-to-peak hips roll and yaw, head roll and yaw (deg), hips side sway (mm), before -> after."""
    axes = character_frame(rig.heads, rig.up)
    left = axes[:, 0]
    rest = {b: rig.rest[b][:3, :3] for b in rig.order}
    root = rig.root

    def off_rest(world, b):
        return _ypr(axes.T @ world @ rest[b].T @ axes)

    def scaled(world, b, ky, kp, kr):
        y, p, r = off_rest(world, b)
        return axes @ _from_ypr(y * ky, p * kp, r * kr) @ axes.T @ rest[b]

    side0 = float(np.mean([f[1] @ left for f in frames]))
    chain = [b for b in rig.order if b in CALM_CHAIN]
    out = []
    for wr, pos in frames:
        new = dict(wr)
        new[root] = scaled(wr[root], root, k["yaw"], 1.0, k["roll"])
        pos = pos - ((pos @ left) - side0) * (1 - k["sway"]) * left
        for b in chain:
            p = rig.parents[b]
            q0 = rest[p].T @ rest[b]
            delta = (wr[p].T @ wr[b]) @ q0.T
            new[b] = new[p] @ exp_rot(log_rot(delta) * k["spine"]) @ q0
        if "Head" in new:
            new["Head"] = scaled(wr["Head"], "Head", k["head"], k["head_pitch"], k["head"])
        out.append((new, pos))

    def ptp(fr, b, i):
        v = [np.degrees(off_rest(f[0][b], b)[i]) for f in fr]
        return round(float(max(v) - min(v)), 1)

    def sway(fr):
        v = [f[1] @ left * 1000 for f in fr]
        return round(float(max(v) - min(v)), 1)

    info = {"hips_roll_deg": [ptp(frames, root, 2), ptp(out, root, 2)],
            "hips_yaw_deg": [ptp(frames, root, 0), ptp(out, root, 0)],
            "hips_sway_mm": [sway(frames), sway(out)]}
    if "Head" in rest:
        info["head_roll_deg"] = [ptp(frames, "Head", 2), ptp(out, "Head", 2)]
        info["head_yaw_deg"] = [ptp(frames, "Head", 0), ptp(out, "Head", 0)]
    return out, info


def rig_height(rig: Rig) -> float:
    z = rig.points @ rig.up
    return float(z.max() - z.min())


def _rot_dist(wa, wb, bones):
    """Mean angle (degrees) between two frames' rotations over `bones`."""
    qa = matrices_to_quaternions(np.array([wa[b] for b in bones]))
    qb = matrices_to_quaternions(np.array([wb[b] for b in bones]))
    return float(np.degrees(2 * np.arccos(np.clip(np.abs((qa * qb).sum(1)), 0, 1))).mean())


def cut_loop(rig: Rig, frames, contacts, fps, mapping):
    """(frames of the cycle, its contacts, the in-place tread velocity, info). The cycle has
    P frames, 0..P-1; the caller keys frame 0 again at P."""
    bones = [b for b in rig.order if mapping[b] != mapping.get(rig.parents[b] or "", None) or rig.parents[b] is None]
    n = len(frames)
    D = np.zeros((n, n))
    for a in range(n):
        for b in range(a + 1, n):
            D[a, b] = D[b, a] = _rot_dist(frames[a][0], frames[b][0], bones)
    steps = np.array([D[t, t + 1] for t in range(n - 1)])
    step = float(np.median(steps)) or 1e-6
    shortest = max(4, int(round(LOOP_MIN_SECONDS * fps)))
    best = None
    for i in range(1, n - shortest):
        for j in range(i + shortest, n):
            moving = float(steps[i:j].mean())
            if moving < LOOP_MOVING * step:
                continue
            cost = (D[j, i] + D[j - 1, i - 1]) / moving - 0.01 * (j - i)
            if best is None or cost < best[0]:
                best = (cost, i, j)
    if best is None:
        raise ValueError("no stretch of the clip moves enough to loop")
    _, i, j = best
    P = j - i
    up = rig.up
    res_rot = {b: log_rot(frames[j][0][b] @ frames[i][0][b].T) for b in rig.order}
    res_root = frames[j][1] - frames[i][1]
    travel = res_root - (res_root @ up) * up
    out = []
    for k in range(P):
        wr, root = frames[i + k]
        u = k / P
        out.append(({b: exp_rot(-u * res_rot[b]) @ r for b, r in wr.items()}, root - u * res_root))
    seam_raw = (D[n - 1, 0]) / step
    speed = float(np.linalg.norm(travel)) / (P / fps)
    # an idle drifts a few mm a second: that is not a treadmill to walk the feet back on
    tread = -travel / (P / fps) if speed >= STILL_SPEED * rig_height(rig) / 1.7 else np.zeros(3)
    info = dict(start=i, frames=P, seconds=round(P / fps, 3), seam_cost=round(best[0], 3),
                seam_raw_x_step=round(seam_raw, 2), root_speed_m_s=round(float(np.linalg.norm(tread)), 3),
                residual_deg=round(float(np.degrees(np.mean([np.linalg.norm(v) for v in res_rot.values()]))), 2))
    return out, {s: np.asarray(c)[i:j] for s, c in contacts.items()}, tread, info
