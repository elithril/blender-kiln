#!/usr/bin/env python3
"""Learned auto-rigging for kiln: SkinTokens' skeleton and skin weights, renamed to kiln's
skeleton and checked before they are handed over.

    python3 plugin/tools/autorig.py status                 # installed? the tested version? exit 2 = not installed
    python3 plugin/tools/autorig.py setup --yes            # installs the tested version (ask the user first)
    python3 plugin/tools/autorig.py rig --asset SK_Child.glb --out ./rig \\
        [--object SK_Child] [--body auto|humanoid|quadruped] [--allow-missing RightHand] \\
        [--lids SK_Child_LidL SK_Child_LidR] [--ears X,Y,Z,X,Y,Z] [--raw skintokens_out.glb]

Writes {out}/{stem}_rigged.glb and .blend, and prints one `autorig: {...}` JSON line.

Why. On a bent pose (characters.md § Learned auto-rig), SkinTokens' rig crossed less skin
through skin than the Rigify rig PHASE 5c prescribed on both humanoids measured: 2,985 mm²
against 3,926 on a kiln-built chibi child, 20,917 against 50,680 on a generated humanoid
whose hand is fused to its hip. On kiln's own cats it was not better where it counted
(the walk: 527 mm² mean against 359), so quadrupeds kiln built keep their own rig.

What SkinTokens returns cannot be used as is: bones are called bone_0..bone_N, the tree
changes from mesh to mesh (and from run to run), connector bones sit between the joints,
there are no ears or eyelids, and a limb fused to the body can come back without its last
bone. So, inside Blender:

1. the raw weights are copied onto the original mesh, vertex by vertex (nearest point);
2. cleaned: at most 4 influences, normalised; a bone's small islands away from its own
   region dropped (specks); an unweighted vertex takes its neighbour's. Weights under 0.01
   are kept: dropping them cost the child's bent pose 99 mm² (2,985 → 3,084);
3. the skeleton is mapped onto kiln's names (characters.md § Animation-ready skeleton) from
   its topology and joint positions — limbs found as the subtrees off the centre line,
   paired left/right, legs being the pair attached nearest the root — and the tool FAILS,
   naming the bone, when a bone tools/quadruped.py or the validator needs is not there;
4. eyelid bones are added for separate lid shells (100% to their bone, the skin left off
   them, as characters.md § 6. Weight Painting says), and ear bones where --ears gives them.

Conventions it relies on, as everywhere in kiln: Z up, the character facing -Y (glTF +Z),
its left on +X. A model facing +Y is refused rather than mirrored.

Standard library only outside Blender. Needs git and uv for `setup`, Blender 4.4+.
SkinTokens' code and checkpoints are MIT (plugin/NOTICE); kiln's Mac patch,
tools/skintokens.patch, comes from image-to-3dlab (Apache-2.0).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

# ── what kiln measured ───────────────────────────────────────────────────────
# Bump only after re-running the measurements in references/characters.md § Learned
# auto-rig against the new version.
REPO_URL = "https://github.com/VAST-AI-Research/SkinTokens.git"
TESTED_COMMIT = "273b691d35989d71cd17ff2895fdc735097b92d1"
HF_REPO, HF_REVISION = "VAST-AI/SkinTokens", "79736cad0fd84de384d5eede659b4ebd24effe33"
QWEN_REPO, QWEN_REVISION = "Qwen/Qwen3-0.6B", "c1899de289a04d12100db370d81485cdf75e47ca"
# The checkpoints are pickles: torch.load runs code from them. Only these bytes are loaded.
CHECKPOINTS = {
    "experiments/articulation_xl_quantization_256_token_4/grpo_1400.ckpt":
        (1131603979, "f4e4706a11cfb520cdde65156a0358545e4fbf8f36237aca01ea5e79d5cb5692"),
    "experiments/skin_vae_2_10_32768/last.ckpt":
        (487311745, "4843f49e58afff88345806b94ca82e6cc9d8def6e7432e2853c677b154de0ed4"),
}
INSTALL_GB = 5.6          # measured: venv 2.0, checkpoints 1.5, uv's download cache 2.0, Python 0.06

HOME = Path(os.environ.get("KILN_SKINTOKENS_HOME", Path.home() / ".cache" / "blender-kiln" / "skintokens"))
CODE = HOME / "SkinTokens"
TOOLS = Path(__file__).resolve().parent
PATCH = TOOLS / "skintokens.patch"
LOCK = TOOLS / "skintokens-requirements.txt"

# Bones tools/quadruped.py and the walk need (characters.md § Animation-ready skeleton).
REQUIRED = ["Hips", "Spine1", "Neck", "Head"] + [f"{s}{p}" for s in ("Left", "Right")
                                                  for p in ("UpLeg", "Leg", "Foot", "Arm", "ForeArm", "Hand")]
ARM_NAMES = ("Arm", "ForeArm", "Hand", "Fingers")
LEG_NAMES = ("UpLeg", "Leg", "Foot", "ToeBase", "Toe_End")
LATERAL = 0.04     # a subtree whose joints all sit this far to one side (share of the skeleton's size) is a limb
SAME_JOINT = 0.03   # joints closer than this share of the size are one (SkinTokens stacks bones on a point;
#                    the shortest real neck measured, a cat's, is 9%)
MAX_INFLUENCES, MIN_WEIGHT = 4, 0.01   # MIN_WEIGHT: what the validator counts as an influence
# Weights under 0.01 are kept: dropping them added 99 mm² of skin through skin to the kiln
# child's bent pose (2,985 → 3,084, one leg), measured.
DROP_BELOW = 0.0
EAR_RAMP = 0.2     # an ear bone holds its skin fully from this share of its length on
SPECK_SHARE = 0.02  # an island of a bone's weights holding under 2% of that bone's vertices is a speck


class MappingError(Exception):
    """The raw skeleton cannot be named safely. The message says which bone and why."""


# ── the mapping: pure, no Blender ────────────────────────────────────────────

def _children(parents):
    kids = defaultdict(list)
    for i, p in enumerate(parents):
        if p is not None:
            kids[p].append(i)
    return kids


def _subtree(i, kids):
    out, stack = [], [i]
    while stack:
        j = stack.pop()
        out.append(j)
        stack.extend(kids[j])
    return out


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _main_path(r, kids, heads, tails):
    """From r down to a leaf, always into the child with the longest reach (the limb, not a
    side branch such as a second finger)."""
    reach = {}

    def far(j):
        if j not in reach:
            reach[j] = max((_dist(heads[j], heads[c]) + far(c) for c in kids[j]),
                           default=_dist(heads[j], tails[j]))
        return reach[j]
    path = [r]
    while kids[path[-1]]:
        path.append(max(kids[path[-1]], key=lambda c: _dist(heads[path[-1]], heads[c]) + far(c)))
    return path


def map_skeleton(heads, tails, parents, mass=None, body="auto", allow_missing=()):
    """Name a raw SkinTokens skeleton after kiln's convention.

    heads, tails: per bone (x, y, z) in metres, world space; parents: per bone its parent's
    index or None; mass: per bone how many skin vertices it dominates (optional, finds the
    head bone among bones stacked on one joint). Returns {"names", "body", "next",
    "warnings", "limbs"}; raises MappingError when a required bone is not there.
    """
    n = len(heads)
    roots = [i for i, p in enumerate(parents) if p is None]
    if len(roots) != 1:
        raise MappingError(f"{len(roots)} root bones ({roots}); a skeleton has one")
    root = roots[0]
    kids = _children(parents)
    pts = list(heads) + list(tails)
    size = max(max(p[k] for p in pts) - min(p[k] for p in pts) for k in range(3)) or 1.0
    cx = heads[root][0]
    sub = {i: _subtree(i, kids) for i in range(n)}
    warnings = []

    def lateral(i):
        # every joint below the bone on one side (its own head may sit on the centre line: a
        # connector, a clavicle); a mean would let the spine plus one arm pass for a limb
        q = [heads[j][0] - cx for j in sub[i] if j != i] or [heads[i][0] - cx]
        if all(x > LATERAL * size for x in q):
            return 1.0
        if all(x < -LATERAL * size for x in q):
            return -1.0
        return 0.0

    limb_roots = [i for i in range(n) if i != root and lateral(i) and not lateral(parents[i])]
    in_limb = {j: r for r in limb_roots for j in sub[r]}
    limbs = []
    for r in limb_roots:
        js = sub[r]
        limbs.append(dict(root=r, side="Left" if lateral(r) > 0 else "Right",
                          path=_main_path(r, kids, heads, tails),
                          centroid=[sum(heads[j][k] for j in js) / len(js) for k in range(3)],
                          minz=min(heads[j][2] for j in js),
                          attach=_dist(heads[r], heads[root])))

    # pair each left limb with its mirror on the right
    lefts = [L for L in limbs if L["side"] == "Left"]
    rights = [R for R in limbs if R["side"] == "Right"]
    cands = sorted(((_dist((2 * cx - L["centroid"][0],) + tuple(L["centroid"][1:]), R["centroid"]), li, ri)
                    for li, L in enumerate(lefts) for ri, R in enumerate(rights)))
    pairs, used_l, used_r = [], set(), set()
    for _, li, ri in cands:
        if li not in used_l and ri not in used_r:
            used_l.add(li); used_r.add(ri)
            pairs.append({"Left": lefts[li], "Right": rights[ri]})
    single = [L for i, L in enumerate(lefts) if i not in used_l] + \
             [R for i, R in enumerate(rights) if i not in used_r]
    groups = pairs + [{s["side"]: s} for s in single]
    if not groups:
        raise MappingError("no limb found: every joint sits on the centre line — is this a character?")

    def attach(g):
        return min(m["attach"] for m in g.values())
    groups.sort(key=attach)
    roles = {}
    legs = groups[0]
    arms = groups[1] if len(groups) > 1 else {}
    for g, role in ((legs, "leg"), (arms, "arm")):
        for m in g.values():
            roles[m["root"]] = role
    for k, g in enumerate(groups[2:], 1):
        for m in g.values():
            roles[m["root"]] = f"limb{k}"
        warnings.append(f"extra limb pair {k} (bones {[m['root'] for m in g.values()]}) named "
                        f"{'/'.join(m['side'] for m in g.values())}Limb{k}_*")

    if body == "auto":
        if legs and arms:
            low = min(m["minz"] for m in legs.values())
            body = "quadruped" if min(m["minz"] for m in arms.values()) - low < 0.2 * size else "humanoid"
        else:
            body = "humanoid"

    names = [None] * n
    nxt = {}

    def chain(path):
        for a, b in zip(path, path[1:]):
            nxt[a] = b

    # the limbs: leading connector bones (at the centre line, or inside the hips for a
    # humanoid's clavicle), then the joints in order
    hip_x = None
    for m in legs.values():
        firsts = [j for j in m["path"] if abs(heads[j][0] - cx) >= 0.25 * max(abs(heads[k][0] - cx) for k in m["path"])]
        if firsts:
            hip_x = min(hip_x or 1e9, abs(heads[firsts[0]][0] - cx))
    limb_report = {}
    for m in limbs:
        role, side, path = roles[m["root"]], m["side"], m["path"]
        reach = max(abs(heads[j][0] - cx) for j in path)
        lead = 0
        if role == "arm" and body == "humanoid" and hip_x:
            while lead < len(path) - 1 and abs(heads[path[lead]][0] - cx) < hip_x:
                lead += 1
        else:
            while lead < len(path) - 1 and abs(heads[path[lead]][0] - cx) < 0.25 * reach:
                lead += 1
        if role == "arm":
            base, conn = ARM_NAMES, ["Shoulder"] if lead == 1 else [f"ShoulderConn{k}" for k in range(1, lead)] + ["Shoulder"]
        elif role == "leg":
            base, conn = LEG_NAMES, [f"HipConn{k}" if lead > 1 else "HipConn" for k in range(1, lead + 1)]
        else:
            base, conn = tuple(f"Limb{role[4:]}_{k}" for k in range(1, 4)), [f"Limb{role[4:]}_Conn{k}" for k in range(1, lead + 1)]
        conn = conn[:lead]
        rest = path[lead:]
        own = list(base[:-1]) + [f"{base[-1]}{k if k > 1 else ''}" for k in range(1, len(rest) - len(base) + 2)] \
            if len(rest) >= len(base) else list(base[:len(rest)])
        for j, nm in zip(path, conn + own):
            names[j] = side + nm
        chain(path)
        limb_report[f"{side}{role}"] = [names[j] for j in path]
        side_bones = [j for j in sub[m["root"]] if names[j] is None]
        for k, j in enumerate(side_bones, 1):          # side branches: a second finger, a dewclaw
            anc = parents[j]
            while names[anc] is None:
                anc = parents[anc]
            names[j] = f"{names[anc]}X{k}"

    # the centre line: root → head is the path through both arms' attachment
    centre = [i for i in range(n) if i not in in_limb]
    leaves = [i for i in centre if not any(c not in in_limb for c in kids[i])]

    def path_to(i):
        p = [i]
        while parents[p[-1]] is not None:
            p.append(parents[p[-1]])
        return p[::-1]
    arm_attach = [parents[m["root"]] for m in arms.values()]
    cand = [l for l in leaves if all(a in path_to(l) for a in arm_attach)]
    if not cand:
        raise MappingError("no centre-line path from the root passes through both shoulders: "
                           "the arms hang off different branches")
    if mass:
        head_leaf = max(cand, key=lambda l: (sum(mass[j] for j in path_to(l)), -l))
    else:
        head_leaf = max(cand, key=lambda l: len(path_to(l)))
    P = path_to(head_leaf)
    at = max((P.index(a) for a in arm_attach), default=0)
    above = P[at + 1:]
    if not above:
        raise MappingError("nothing above the shoulders on the centre line: no Neck or Head bone")
    hstar = max(above, key=lambda j: (mass[j] if mass else 0, P.index(j) if not mass else -P.index(j)))
    hi = P.index(hstar)
    while hi - 1 > at and _dist(heads[P[hi - 1]], heads[P[hi]]) < SAME_JOINT * size:
        hi -= 1                                         # bones stacked on the head's joint: the first is Head
    if hi - 1 <= 0:
        raise MappingError("the head hangs straight off the root: no Neck bone between them")
    spines = P[1:hi - 1]
    if not spines:
        raise MappingError("no bone between the root and the neck: Spine1 cannot be placed")
    sp = {1: ["Spine1"], 2: ["Spine", "Spine1"]}.get(len(spines),
                                                     ["Spine"] + [f"Spine{k}" for k in range(1, len(spines))])
    names[P[0]] = "Hips"
    for j, nm in zip(spines, sp):
        names[j] = nm
    names[P[hi - 1]], names[P[hi]] = "Neck", "Head"
    for k, j in enumerate(P[hi + 1:], 1):
        names[j] = f"HeadX{k}"
    chain(P)

    # other centre branches: a tail behind the hips, connectors carrying limbs, extras
    def carries_limb(j):
        return any(x in in_limb for x in sub[j])
    tails_found = 0
    for leaf in leaves:
        if leaf in P:
            continue
        p = path_to(leaf)
        seg = []
        for j in reversed(p):
            if names[j] is not None or carries_limb(j):
                break
            seg.append(j)
        seg.reverse()
        if not seg:
            continue
        behind = heads[leaf][1] - heads[root][1] > 0.1 * size
        if behind and not tails_found:
            for k, j in enumerate(seg, 1):
                names[j] = f"Tail{k}"
            tails_found = 1
        else:
            for k, j in enumerate(seg, 1):
                names[j] = f"Extra{leaves.index(leaf)}_{k}"
            warnings.append(f"centre branch {seg} named Extra{leaves.index(leaf)}_* (not a tail: "
                            f"{'a second one' if behind else 'not behind the hips'})")
        chain(seg)
    counter = defaultdict(int)
    order, k = [root], 0
    while k < len(order):
        order.extend(kids[order[k]]); k += 1
    for j in order:
        if names[j] is None:
            anc = parents[j]
            while anc is not None and names[anc] is None:
                anc = parents[anc]
            base = names[anc] if anc is not None else "Root"
            base = re.sub(r"Conn\d+$", "", base)
            counter[base] += 1
            names[j] = f"{base}Conn{counter[base]}"

    # facing: kiln's characters face -Y; a mirrored one would swap left and right
    facing = None
    if body == "quadruped":
        facing = heads[P[hi]][1] < heads[root][1]
    elif "LeftToeBase" in names and "LeftFoot" in names:
        facing = heads[names.index("LeftToeBase")][1] < heads[names.index("LeftFoot")][1]
    if facing is False:
        raise MappingError("the character faces +Y; kiln's convention (and glTF's) is -Y, with its "
                           "left on +X — turn the model 180° about Z and rig it again")
    if facing is None:
        warnings.append("facing not checked (no toe bone): left/right assume the character faces -Y")

    missing = [b for b in REQUIRED if b not in names]
    blocking = [b for b in missing if b not in allow_missing]
    if blocking:
        why = []
        for b in blocking:
            side = "Left" if b.startswith("Left") else "Right" if b.startswith("Right") else None
            if side:
                role = "arm" if b[len(side):] in ARM_NAMES else "leg"
                have = limb_report.get(side + role)
                why.append(f"{b}: the {side.lower()} {role} chain is {have}" if have else
                           f"{b}: no {side.lower()} {role} at all")
            else:
                why.append(f"{b}: not on the centre line")
        raise MappingError("required bone(s) not found — " + "; ".join(why) +
                           ". SkinTokens drops or merges a limb's end where the limb touches the body "
                           "(a hand fused to the hip). Separate the limb in the mesh and rig again, or "
                           "accept it with --allow-missing " + " ".join(blocking))
    if missing:
        warnings.append(f"accepted missing: {missing} — tools/quadruped.py will refuse this rig")
    if len(set(names)) != n:
        dup = sorted({x for x in names if names.count(x) > 1})
        raise MappingError(f"two bones would share a name {dup}: the skeleton is not one kiln can name")
    return {"names": names, "body": body, "next": nxt, "warnings": warnings,
            "limbs": limb_report, "missing": missing}


# ── weight cleaning: pure ────────────────────────────────────────────────────

def _find(parent, a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def clean_weights(weights, edges, max_influences=MAX_INFLUENCES, min_weight=DROP_BELOW,
                  speck_share=SPECK_SHARE):
    """weights: per vertex {bone: weight}; edges: (a, b) vertex pairs, coincident vertices
    included. Returns (new weights, stats). Never leaves a vertex without weight if any
    vertex of its connected piece has one."""
    W = []
    trimmed = 0
    for w in weights:
        k = sorted(((b, x) for b, x in w.items() if x > min_weight), key=lambda t: -t[1])
        if len(k) > max_influences or len(k) < len([x for x in w.values() if x > 0]):
            trimmed += 1
        k = k[:max_influences]
        s = sum(x for _, x in k)
        W.append({b: x / s for b, x in k} if s > 0 else {})
    # specks: per bone, islands of its influence that are small and not its main region
    parent = {}
    for a, b in edges:
        for bone in W[a].keys() & W[b].keys():
            pa = parent.setdefault(bone, {})
            pa.setdefault(a, a); pa.setdefault(b, b)
            ra, rb = _find(pa, a), _find(pa, b)
            if ra != rb:
                pa[ra] = rb
    members = defaultdict(lambda: defaultdict(list))
    for v, w in enumerate(W):
        for bone in w:
            pa = parent.setdefault(bone, {})
            pa.setdefault(v, v)
            members[bone][_find(pa, v)].append(v)
    removed = islands = 0
    for bone, comps in members.items():
        total = sum(len(c) for c in comps.values())
        main = max(comps.values(), key=len)
        for c in comps.values():
            if c is main or len(c) > speck_share * total:
                continue
            if any(len(W[v]) == 1 for v in c):      # a part held by this bone alone (an eye on the head)
                continue
            islands += 1
            for v in c:
                x = W[v].pop(bone)
                removed += 1
                s = 1.0 - x
                W[v] = {b: y / s for b, y in W[v].items()}
    # unweighted vertices take their nearest weighted neighbour's weights (by edges)
    nb = defaultdict(list)
    for a, b in edges:
        nb[a].append(b); nb[b].append(a)
    empty = [v for v, w in enumerate(W) if not w]
    filled = 0
    frontier = [v for v in range(len(W)) if W[v]]
    seen = set(frontier)
    while frontier and len(seen) < len(W):
        nxt = []
        for v in frontier:
            for u in nb[v]:
                if u not in seen:
                    seen.add(u)
                    if not W[u]:
                        W[u] = dict(W[v]); filled += 1
                    nxt.append(u)
        frontier = nxt
    return W, {"vertices_trimmed": trimmed, "speck_islands": islands, "speck_weights_removed": removed,
               "unweighted_filled": filled, "unweighted_left": len(empty) - filled}


# ── install / status ─────────────────────────────────────────────────────────

def run(cmd, cwd=None, env=None, check=True, capture=False):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, check=check, text=True,
                          capture_output=capture)


def venv_python():
    return CODE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def find_blender():
    for cand in (os.environ.get("BLENDER"), shutil.which("blender"),
                 "/Applications/Blender.app/Contents/MacOS/Blender"):
        if cand and Path(cand).exists():
            return cand
    return None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def _git(*args, check=False):
    return subprocess.run(["git", *args], cwd=CODE, text=True, capture_output=True, check=check)


def problems(hash_weights=True):
    """What is wrong with the install, [] when it is the tested one."""
    if not CODE.exists():
        return ["not installed"]
    out = []
    head = _git("rev-parse", "HEAD").stdout.strip()
    if head != TESTED_COMMIT:
        out.append(f"code at {head[:12] or '?'}, kiln tested {TESTED_COMMIT[:12]}")
    if _git("apply", "--check", "-R", str(PATCH)).returncode != 0:
        out.append("kiln's Mac patch is not applied (tools/skintokens.patch)")
    if not venv_python().exists():
        out.append(f"no Python environment at {venv_python()}")
    for rel, (size, sha) in CHECKPOINTS.items():
        p = CODE / rel
        if not p.exists():
            out.append(f"checkpoint missing: {rel}")
        elif p.stat().st_size != size:
            out.append(f"checkpoint {rel}: {p.stat().st_size} bytes, expected {size}")
        elif hash_weights and _sha256(p) != sha:
            out.append(f"checkpoint {rel}: SHA-256 differs from the tested one — not loading it")
    if not (CODE / "models" / "Qwen3-0.6B" / "config.json").exists():
        out.append("Qwen3-0.6B config missing")
    return out


def status(args) -> int:
    print(f"SkinTokens home  {HOME}")
    print(f"tested by kiln    {TESTED_COMMIT[:12]}, weights {HF_REPO}@{HF_REVISION[:12]}")
    print("licence           code and checkpoints MIT; kiln's Mac patch Apache-2.0 (plugin/NOTICE)")
    print(f"cost              ~{INSTALL_GB} GB on disk; 35-54 s and ~7 GB of memory per mesh (Apple M-series, MPS)")
    p = problems(hash_weights=not args.quick)
    if p == ["not installed"]:
        print("→ not installed: ask the user, then `autorig.py setup --yes`")
        return 2
    if p:
        for x in p:
            print(f"! {x}")
        print("→ damaged or not the tested version: `autorig.py setup --yes` repairs it")
        return 3
    print("→ installed, the tested version")
    return 0


def setup(args) -> int:
    if not args.yes:
        print(f"setup installs SkinTokens into {HOME}: ~{INSTALL_GB} GB (code, a Python 3.11 environment "
              "with torch, 1.6 GB of checkpoints from Hugging Face), MIT. On a Mac it runs on MPS through "
              "kiln's patch. Ask the user; on a yes run `autorig.py setup --yes`.")
        return 3
    for tool in ("git", "uv"):
        if not shutil.which(tool):
            sys.exit(f"`{tool}` is required (uv: https://docs.astral.sh/uv/).")
    HOME.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(HOME / "uv-python"), UV_CACHE_DIR=str(HOME / "uv-cache"),
               HF_HOME=str(HOME / "hf-cache"))
    if not CODE.exists():
        run(["git", "clone", "--quiet", REPO_URL, CODE])
    run(["git", "fetch", "--quiet", "origin"], cwd=CODE)
    run(["git", "checkout", "--quiet", "--force", TESTED_COMMIT], cwd=CODE)
    run(["git", "apply", PATCH], cwd=CODE)
    if not venv_python().exists():
        run(["uv", "venv", "--quiet", "-p", "3.11", CODE / ".venv"], env=env)
    run(["uv", "pip", "install", "--quiet", "-p", venv_python(), "-r", LOCK], env=env)
    fetch = (
        "import sys\nfrom pathlib import Path\n"
        "from huggingface_hub import hf_hub_download, snapshot_download\n"
        f"root = Path({str(CODE)!r})\n"
        f"for p in {list(CHECKPOINTS)!r}:\n"
        f"    f = Path(hf_hub_download(repo_id={HF_REPO!r}, filename=p, revision={HF_REVISION!r}))\n"
        "    t = root / p; t.parent.mkdir(parents=True, exist_ok=True)\n"
        "    t.unlink(missing_ok=True); t.symlink_to(f)\n"
        f"snapshot_download(repo_id={QWEN_REPO!r}, revision={QWEN_REVISION!r}, "
        "local_dir=str(root / 'models/Qwen3-0.6B'), ignore_patterns=['*.bin', '*.safetensors'])\n")
    run([venv_python(), "-c", fetch], env=env)
    p = problems()
    if p:
        for x in p:
            print(f"! {x}")
        return 1
    print(f"\ninstalled SkinTokens {TESTED_COMMIT[:12]} in {HOME}")
    return 0


# ── rig: the orchestration (plain Python) ────────────────────────────────────

def _blender(blender, *args):
    cmd = [blender, "--background", "--factory-startup", "--python-exit-code", "1",
           "--python", str(Path(__file__).resolve()), "--", *map(str, args)]
    r = subprocess.run(cmd, text=True, capture_output=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith("autorig")]
    for l in lines:
        print(l)
    if r.returncode:
        err = [l for l in (r.stdout + r.stderr).splitlines() if "Error" in l or "FAIL" in l]
        if not lines:
            print("\n".join(err[-8:] or (r.stdout + r.stderr).splitlines()[-15:]), file=sys.stderr)
    return r.returncode, lines


def rig(args) -> int:
    blender = find_blender()
    if not blender:
        sys.exit("Blender not found: set BLENDER=/path/to/blender.")
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    work = out / "_autorig"; work.mkdir(exist_ok=True)
    asset = Path(args.asset).resolve()
    if not args.raw:
        p = problems(hash_weights=True)
        if p:
            print("autorig: SkinTokens is not ready — " + "; ".join(p) +
                  ". Ask the user before `autorig.py setup --yes`, or rig as PHASE 5c's table says.", file=sys.stderr)
            return 2
    if not asset.exists():
        print(f"autorig: FAIL: no such file {asset}", file=sys.stderr)
        return 1
    code, lines = _blender(blender, "prep", asset, args.object or "-", work / "skin.glb", work / "scene.blend")
    if code:
        return code
    prep = json.loads(lines[-1].split("autorig prep: ", 1)[1])
    raw = Path(args.raw).resolve() if args.raw else work / "raw.glb"
    seconds = None
    if not args.raw:
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HOME=str(HOME / "hf-cache"))
        t0 = time.time()
        r = subprocess.run([str(venv_python()), "demo.py", "--input", str(work / "skin.glb"),
                            "--output", str(raw), "--use_transfer"], cwd=CODE, env=env, text=True,
                           capture_output=True)
        seconds = round(time.time() - t0, 1)
        (work / "skintokens.log").write_text(r.stdout + r.stderr)
        if r.returncode or not raw.exists() or "[OK] Exported" not in r.stdout:
            print(f"autorig: SkinTokens failed after {seconds} s — see {work / 'skintokens.log'}", file=sys.stderr)
            return 1
        print(f"autorig: SkinTokens rigged the skin in {seconds} s")
    opts = {"skin": prep["skin"], "body": args.body, "allow_missing": args.allow_missing or [],
            "lids": args.lids, "ears": args.ears, "stem": asset.stem, "seconds": seconds}
    (work / "opts.json").write_text(json.dumps(opts))
    code, lines = _blender(blender, "post", work / "scene.blend", raw, out, work / "opts.json")
    if not args.keep and code == 0:
        shutil.rmtree(work, ignore_errors=True)
    return code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("status"); s.add_argument("--quick", action="store_true", help="skip hashing the checkpoints")
    s.set_defaults(fn=status)
    s = sp.add_parser("setup"); s.add_argument("--yes", action="store_true", help="the user agreed to the download")
    s.set_defaults(fn=setup)
    s = sp.add_parser("rig")
    s.add_argument("--asset", required=True, help="GLB/glTF/FBX/OBJ or .blend holding the character")
    s.add_argument("--object", help="the skin object (default: the mesh with the most vertices)")
    s.add_argument("--out", required=True)
    s.add_argument("--body", choices=("auto", "humanoid", "quadruped"), default="auto")
    s.add_argument("--allow-missing", nargs="*", metavar="BONE", help="accept these required bones missing")
    s.add_argument("--lids", nargs="*", metavar="OBJECT",
                   help="eyelid shells (default: objects whose name says Eyelid or Lid)")
    s.add_argument("--ears", help="left ear base and tip in mm, X,Y,Z,X,Y,Z — the right one is mirrored")
    s.add_argument("--raw", help="a SkinTokens output to post-process instead of running SkinTokens")
    s.add_argument("--keep", action="store_true", help="keep the work files")
    s.set_defaults(fn=rig)
    args = ap.parse_args(argv)
    return args.fn(args)


# ── Blender side ─────────────────────────────────────────────────────────────

def _bl_load(path, obj):
    import bpy
    path = Path(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext = path.suffix.lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(path))
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        raise SystemExit(f"autorig: cannot read {ext} files")


def bl_prep(asset, obj, skin_glb, scene_blend):
    """One scene with the meshes only, transforms applied, no old rig; the skin alone as GLB."""
    import bpy
    from mathutils import Matrix
    _bl_load(asset, obj)
    for o in list(bpy.data.objects):
        if o.type == 'MESH':
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
            for m in [m for m in o.modifiers if m.type == 'ARMATURE']:
                o.modifiers.remove(m)
    for o in list(bpy.data.objects):
        if o.type != 'MESH' or o.name.startswith("Icosphere") and len(o.data.vertices) == 42:
            bpy.data.objects.remove(o, do_unlink=True)      # SkinTokens' own helper sphere, cameras, rigs
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if not meshes:
        raise SystemExit("autorig: FAIL: no mesh in the asset")
    skin = bpy.data.objects.get(obj) if obj != "-" else max(meshes, key=lambda o: len(o.data.vertices))
    if skin is None or skin.type != 'MESH':
        raise SystemExit(f"autorig: FAIL: no mesh named {obj!r}")
    for o in meshes:
        o.data = o.data.copy() if o.data.users > 1 else o.data
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    skin.vertex_groups.clear()
    bpy.ops.object.select_all(action='DESELECT'); skin.select_set(True)
    bpy.context.view_layer.objects.active = skin
    bpy.ops.export_scene.gltf(filepath=str(skin_glb), use_selection=True, export_format='GLB',
                              export_animations=False, export_skins=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_blend))
    print("autorig prep: " + json.dumps({"skin": skin.name, "vertices": len(skin.data.vertices),
                                         "others": [o.name for o in meshes if o != skin]}))


def _fit_sphere(P):
    import numpy as np
    A = np.c_[2 * P, np.ones(len(P))]
    c = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)[0]
    return c[:3], float(math.sqrt(max(c[3] + (c[:3] ** 2).sum(), 0.0)))


def bl_post(scene_blend, raw_glb, out_dir, opts_path):
    import bpy
    import numpy as np
    from mathutils import Vector
    from mathutils.kdtree import KDTree
    opts = json.loads(Path(opts_path).read_text())
    bpy.ops.wm.open_mainfile(filepath=str(scene_blend))
    skin = bpy.data.objects[opts["skin"]]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(raw_glb))
    new = set(bpy.data.objects) - before
    st_arm = next((o for o in new if o.type == 'ARMATURE'), None)
    if st_arm is None:
        raise SystemExit("autorig: FAIL: the SkinTokens output has no armature")
    st_mesh = max((o for o in new if o.type == 'MESH' and o.vertex_groups), key=lambda o: len(o.data.vertices))
    M = st_arm.matrix_world
    # neutral_bone is the glTF exporter's stand-in for unweighted vertices, not a joint
    bones = [b for b in st_arm.data.bones if b.name != "neutral_bone"]
    if all(re.fullmatch(r"bone_\d+", b.name) for b in bones):
        bones.sort(key=lambda b: int(b.name[5:]))
    index = {b.name: i for i, b in enumerate(bones)}
    heads = [tuple(M @ b.head_local) for b in bones]
    tails = [tuple(M @ b.tail_local) for b in bones]
    parents = [index[b.parent.name] if b.parent else None for b in bones]
    gidx = {g.index: index[g.name] for g in st_mesh.vertex_groups if g.name in index}
    SV = [st_mesh.matrix_world @ v.co for v in st_mesh.data.vertices]
    SW = [{gidx[g.group]: g.weight for g in v.groups if g.group in gidx and g.weight > 0}
          for v in st_mesh.data.vertices]
    mass = [0] * len(bones)
    for w in SW:
        if w:
            mass[max(w, key=w.get)] += 1
    try:
        mp = map_skeleton(heads, tails, parents, mass, opts["body"], opts["allow_missing"])
    except MappingError as e:
        print(f"autorig: FAIL: {e}")
        raise SystemExit(1)
    names = mp["names"]

    # 1. weights onto the original skin, nearest SkinTokens vertex
    kd = KDTree(len(SV))
    for i, v in enumerate(SV):
        kd.insert(v, i)
    kd.balance()
    TV = [skin.matrix_world @ v.co for v in skin.data.vertices]
    W, dmax, dsum = [], 0.0, 0.0
    for p in TV:
        _, j, d = kd.find(p)
        W.append(dict(SW[j])); dmax = max(dmax, d); dsum += d
    size = max((max(v[k] for v in TV) - min(v[k] for v in TV)) for k in range(3))
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)

    # 2. cleaning, on the welded adjacency (coincident vertices count as joined)
    edges = [tuple(e.vertices) for e in skin.data.edges]
    same = defaultdict(list)
    for i, p in enumerate(TV):
        same[(round(p.x, 6), round(p.y, 6), round(p.z, 6))].append(i)
    edges += [(g[0], x) for g in same.values() for x in g[1:]]
    W, cstats = clean_weights(W, edges)

    # 3. the named armature: same joints, tails along the chain
    ad = bpy.data.armatures.new(f"{skin.name}_Armature")
    arm = bpy.data.objects.new(f"{skin.name}_Armature", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    nxt = mp["next"]
    kids = _children(parents)
    for i, nm in enumerate(names):
        b = ad.edit_bones.new(nm)
        b.head = heads[i]
        c = nxt.get(i, kids[i][0] if len(kids[i]) == 1 else None)
        t = Vector(heads[c]) if c is not None else Vector(tails[i])
        if (t - Vector(heads[i])).length < 1e-4:
            t = Vector(tails[i])
        if (t - Vector(heads[i])).length < 1e-4:
            t = Vector(heads[i]) + Vector((0, 0, 0.02 * size))
        b.tail = t
    for i, p in enumerate(parents):
        if p is not None:
            ad.edit_bones[names[i]].parent = ad.edit_bones[names[p]]
    # 4a. eyelids: one bone per separate lid shell, at the eye's centre, pointing forward
    lid_objs = [bpy.data.objects[n] for n in opts["lids"]] if opts.get("lids") else \
        [o for o in bpy.data.objects if o.type == 'MESH' and o != skin and re.search(r"eyelid|(^|[^a-z])lid", o.name, re.I)]
    cx = heads[parents.index(None)][0]
    lids = {}
    for o in lid_objs:
        P = np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices])
        c, r = _fit_sphere(P)
        side = "Left" if c[0] > cx else "Right"
        if f"{side}Eyelid" in lids:
            print(f"autorig: FAIL: two lid shells on the {side.lower()} ({lids[side + 'Eyelid'].name}, {o.name})")
            raise SystemExit(1)
        b = ad.edit_bones.new(f"{side}Eyelid")
        b.head = Vector(c); b.tail = Vector(c) + Vector((0, -max(r, 0.01 * size), 0))
        b.parent = ad.edit_bones["Head"]
        lids[f"{side}Eyelid"] = o
    # 4b. ears from --ears (mm), the right one mirrored
    ears = []
    if opts.get("ears"):
        v = [float(x) / 1000 for x in opts["ears"].split(",")]
        if len(v) != 6:
            raise SystemExit("autorig: FAIL: --ears takes X,Y,Z,X,Y,Z (left ear base, then tip, mm)")
        for side, sx in (("Left", 1), ("Right", -1)):
            b = ad.edit_bones.new(f"{side}Ear")
            b.head = Vector((cx + sx * (v[0] - cx), v[1], v[2])); b.tail = Vector((cx + sx * (v[3] - cx), v[4], v[5]))
            b.parent = ad.edit_bones["Head"]
            ears.append(b.name)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 5. weights in, skin bound
    skin.vertex_groups.clear()
    groups = {nm: skin.vertex_groups.new(name=nm) for nm in names}
    for vi, w in enumerate(W):
        for b, x in w.items():
            groups[names[b]].add([vi], x, 'REPLACE')
    skin.parent = arm
    skin.modifiers.new("Armature", 'ARMATURE').object = arm
    if ears:
        ear_stats = _bl_ears(skin, arm, ears, names)
    for bone, o in lids.items():
        o.vertex_groups.clear()
        o.vertex_groups.new(name=bone).add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        o.parent = arm; o.modifiers.new("Armature", 'ARMATURE').object = arm
    # other separate parts (eyes, nose, a prop): 100% to the bone holding the skin next to them
    skd = KDTree(len(TV))
    for i, v in enumerate(TV):
        skd.insert(v, i)
    skd.balance()
    parts = {}
    for o in [o for o in bpy.data.objects if o.type == 'MESH' and o != skin and o not in lids.values()]:
        c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / max(len(o.data.vertices), 1)
        _, j, _ = skd.find(c)
        bone = names[max(W[j], key=W[j].get)] if W[j] else "Head"
        o.vertex_groups.clear()
        o.vertex_groups.new(name=bone).add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        o.parent = arm; o.modifiers.new("Armature", 'ARMATURE').object = arm
        parts[o.name] = bone

    # 6. checks: the validator's, rule 26's ratio, lids off the skin
    deform = [b.name for b in arm.data.bones if b.use_deform]
    gi = {g.index: g.name for g in skin.vertex_groups}
    used = set()
    maxinf, unweighted, on_lid = 0, 0, 0
    for v in skin.data.vertices:
        gs = [g for g in v.groups if g.weight > MIN_WEIGHT]
        maxinf = max(maxinf, len(gs)); unweighted += not gs
        used.update(gi[g.group] for g in gs)
        on_lid += any(gi[g.group].endswith("Eyelid") for g in gs)
    used.update(lids)
    used.update(parts.values())
    dead = [b for b in deform if b not in used]
    report = {"body": mp["body"], "bones": len(arm.data.bones), "deform": len(deform),
              "verts_per_bone": round(len(skin.data.vertices) / max(len(deform), 1), 1),
              "dead_bones": dead, "max_influences": maxinf, "unweighted": unweighted,
              "skin_on_lids": on_lid, "lids": sorted(lids), "ears": ears, "parts": parts,
              "transfer_max_mm": round(dmax * 1000, 3), "transfer_mean_mm": round(dsum / max(len(TV), 1) * 1000, 4),
              "cleaning": cstats, "missing": mp["missing"], "limbs": mp["limbs"], "warnings": mp["warnings"],
              "skintokens_s": opts.get("seconds")}
    if ears:
        report["ear_vertices"] = ear_stats
    if dmax > 0.01 * size:
        report["warnings"].append(f"weights copied from up to {dmax * 1000:.1f} mm away: SkinTokens did not "
                                  "keep the mesh; check the joints on a bent pose")
    out = Path(out_dir)
    stem = opts["stem"]
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f"{stem}_rigged.blend"))
    bpy.ops.export_scene.gltf(filepath=str(out / f"{stem}_rigged.glb"), export_format='GLB',
                              export_animations=False)
    report["out"] = str(out / f"{stem}_rigged.glb")
    print("autorig: " + json.dumps(report))
    if unweighted or maxinf > MAX_INFLUENCES or on_lid:
        print("autorig: FAIL: the rig does not pass its own checks (unweighted vertices, > 4 influences, "
              "or skin on a lid bone)")
        raise SystemExit(1)


def ear_share(p, base, tip):
    """An ear bone's share of a head vertex at p: 0 behind the ear's base plane, rising to
    1 at EAR_RAMP of the ear's length, 0 farther than the ear's length from its axis."""
    axis = [t - b for t, b in zip(tip, base)]
    length2 = sum(a * a for a in axis)
    if not length2:
        return 0.0
    t = sum((x - b) * a for x, b, a in zip(p, base, axis)) / length2
    if t <= 0:
        return 0.0
    foot = [b + min(t, 1.0) * a for b, a in zip(base, axis)]
    if _dist(p, foot) > math.sqrt(length2):
        return 0.0
    return min(t / EAR_RAMP, 1.0)


def _bl_ears(skin, arm, ears, names):
    """Head vertices past an ear's base take that ear bone (ear_share), the rest of their
    weights scaled down to make room. Bone heat was tried first and spread each ear over half
    the head: 1,795 of 2,017 vertices outside the ear, on seeded cones."""
    head_family = {"Head"} | {n for n in names if n.startswith("HeadX")}
    gi = {g.index: g.name for g in skin.vertex_groups}
    groups = {g.name: g for g in skin.vertex_groups}
    segs = {}
    for e in ears:
        b = arm.data.bones[e]
        segs[e] = (tuple(arm.matrix_world @ b.head_local), tuple(arm.matrix_world @ b.tail_local))
        if e not in groups:
            groups[e] = skin.vertex_groups.new(name=e)
    touched = 0
    for v in skin.data.vertices:
        if not v.groups or gi[max(v.groups, key=lambda g: g.weight).group] not in head_family:
            continue
        p = tuple(skin.matrix_world @ v.co)
        share = {e: ear_share(p, *segs[e]) for e in ears}
        e, x = max(share.items(), key=lambda t: t[1])
        if x <= MIN_WEIGHT:
            continue
        old = {gi[g.group]: g.weight for g in v.groups if g.weight > 0}
        new = {b: w * (1 - x) for b, w in old.items()}
        new[e] = new.get(e, 0) + x
        top = sorted(new.items(), key=lambda t: -t[1])[:MAX_INFLUENCES]
        s = sum(w for _, w in top)
        for b in old:
            groups[b].remove([v.index])
        for b, w in top:
            groups[b].add([v.index], w / s, 'REPLACE')
        touched += 1
    return touched


def blender_main(argv):
    stage, rest = argv[0], argv[1:]
    if stage == "prep":
        bl_prep(*rest)
    elif stage == "post":
        bl_post(*rest)
    else:
        raise SystemExit(f"autorig: unknown stage {stage}")


def _in_blender():
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    if _in_blender() and "--" in sys.argv:
        blender_main(sys.argv[sys.argv.index("--") + 1:])
    else:
        sys.exit(main())
