#!/usr/bin/env python3
"""Ready-made humanoid motions (walk, run, jump, dance, …) played on a kiln-named rig.

    python3 plugin/tools/presets.py list
    python3 plugin/tools/presets.py animate --asset SK_Child_rigged.glb --motion walk,run,jump,dance \\
        [--loop] [--speed 1.0] [--take A|B] [--out ./anim] [--stiff-fingers]

Writes {out}/{asset}_animated.glb with ONE clip per motion, named exactly as asked (`walk`,
`run`…), {asset}_animated.measures.json (tools/motion_measure.py on every clip of the file
written) and {asset}_animated.provenance.json (where each motion comes from, its licence).

The clips are image-to-3dlab's (AssetFurnace) presets, generated once with NVIDIA Kimodo
(Kimodo-SOMA-RP-v1.1) for its 77-joint SOMA skeleton and shipped in tools/motions/: 21
motions in two takes (A, B), and a woman's walk — 43 clips, 2.1 MB. The retarget is
upstream's, adapted in tools/retarget.py (Apache-2.0, plugin/NOTICE). The motions:
"Licensed by NVIDIA Corporation under the NVIDIA Open Model License"; NVIDIA claims no
ownership of the outputs, and commercial use is allowed.

The rig must carry kiln's names (references/characters.md § Animation-ready skeleton), as
tools/autorig.py writes them: bones are found by name, not by the tree's shape.

`animate` runs Blender (BLENDER, then `blender` on PATH, then the macOS default) on this file;
inside Blender:

    blender --background --factory-startup --python-exit-code 1 --python presets.py -- \\
        animate --asset X_rigged.glb --motion walk ...

Standard library outside Blender.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOTIONS = HERE / "motions"
SOURCE = dict(
    name="image-to-3dlab (AssetFurnace) Animate presets",
    url="https://github.com/Bingeljell/image-to-3dlab",
    version="v0.4.4", commit="91879333e88a0571945b15b0e21e4bc95ec59e31",
    code_licence="Apache-2.0 (tools/retarget.py adapts scripts/kimodo_retarget.py and scripts/arm_clearance.py)",
    motion_generator="NVIDIA Kimodo, Kimodo-SOMA-RP-v1.1",
    motion_licence="Licensed by NVIDIA Corporation under the NVIDIA Open Model License; "
                   "NVIDIA claims no ownership of outputs; commercial use allowed",
)
# Motions that repeat, which --loop turns into a seamless cycle. The rest are one-shots.
CYCLIC = ("idle", "walk", "walk_woman", "run", "sneak", "fight_stance")


def catalogue() -> dict:
    data = json.loads((MOTIONS / "presets.json").read_text())
    out = {}
    for p in data["presets"]:
        base = p["id"][:-2] if p["id"].endswith("_b") else p["id"]
        take = "B" if p["id"].endswith("_b") else "A"
        out.setdefault(base, {"seconds": p["seconds"], "prompt": p["prompt"], "takes": {}})
        out[base]["takes"][take] = p
    return out


def find_blender() -> str | None:
    for cand in (os.environ.get("BLENDER"), shutil.which("blender"),
                 "/Applications/Blender.app/Contents/MacOS/Blender"):
        if cand and Path(cand).exists():
            return cand
    return None


def cmd_list(_args) -> int:
    cat = catalogue()
    print(f"{len(cat)} motions, {sum(len(m['takes']) for m in cat.values())} clips "
          f"(Kimodo, NVIDIA Open Model License — commercial use allowed)")
    for name, m in cat.items():
        kind = "cycle" if name in CYCLIC else "one-shot"
        print(f"  {name:13s} {m['seconds']:>4} s  takes {'/'.join(sorted(m['takes'])):3s}  {kind:8s}  {m['prompt']}")
    return 0


def parse(argv):
    ap = argparse.ArgumentParser(prog="presets.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    an = sub.add_parser("animate")
    an.add_argument("--asset", required=True, type=Path, help="kiln-named rigged GLB")
    an.add_argument("--motion", required=True, help="comma-separated, e.g. walk,run,jump,dance")
    an.add_argument("--out", type=Path, help="output folder (default: next to the asset)")
    an.add_argument("--loop", action="store_true", help="cut the cyclic motions into seamless in-place cycles")
    an.add_argument("--speed", type=float, default=1.0, help="play faster (>1) or slower (<1)")
    an.add_argument("--take", choices=("A", "B"), default="A")
    an.add_argument("--stiff-fingers", action="store_true", help="fingers follow the hand rigidly")
    an.add_argument("--no-measure", action="store_true", help="skip the measures JSON (faster)")
    an.add_argument("--no-fix", default="", help="leave out kiln's corrections, for comparison: feet")
    return ap.parse_args(argv)


def check_motions(args) -> list[str]:
    cat = catalogue()
    names = [m.strip() for m in args.motion.split(",") if m.strip()]
    unknown = [m for m in names if m not in cat]
    if unknown:
        sys.exit(f"presets: no preset {unknown} — `presets.py list` shows the {len(cat)}; for anything else, "
                 "references/animation.md § Pick the route from the subject")
    if len(set(names)) != len(names):
        sys.exit("presets: a motion is asked twice")
    return names


def cmd_animate(args, argv) -> int:
    check_motions(args)
    blender = find_blender()
    if not blender:
        sys.exit("presets: Blender not found: set BLENDER=/path/to/blender")
    r = subprocess.run([blender, "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", str(Path(__file__).resolve()), "--", *argv])
    return r.returncode


# ── inside Blender ───────────────────────────────────────────────────────────────────────

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blender_animate(args) -> int:  # pragma: no cover - needs bpy
    import bpy
    import numpy as np
    from mathutils import Matrix

    sys.path.insert(0, str(HERE))
    import retarget as R

    names = check_motions(args)
    skip = {x.strip() for x in args.no_fix.split(",") if x.strip()}
    cat = catalogue()
    asset = args.asset.resolve()
    out = (args.out or asset.parent).resolve()
    out.mkdir(parents=True, exist_ok=True)
    stem = asset.stem
    path = out / f"{stem}_animated.glb"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(asset))
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if arm is None:
        sys.exit(f"presets: {asset.name} has no armature — rig it first (tools/autorig.py)")
    bones = arm.data.bones
    parents = {b.name: (b.parent.name if b.parent else None) for b in bones}
    try:
        mapping = R.kiln_to_soma(parents)
    except R.MappingError as e:
        sys.exit(f"presets: {e}")
    if args.stiff_fingers:
        mapping = R.stiffen_fingers(mapping)
    arm_rot = np.array(arm.matrix_world.to_3x3().normalized())
    up = arm_rot.T @ np.array([0.0, 0.0, 1.0])
    inv = np.array(arm.matrix_world.inverted())
    points, owners, weights = [], [], []
    for mesh in (o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm):
        to_arm = inv @ np.array(mesh.matrix_world)
        gname = {g.index: g.name for g in mesh.vertex_groups}
        for v in mesh.data.vertices:
            best = max(v.groups, key=lambda g: g.weight, default=None)
            if best is None or gname.get(best.group) not in parents:
                continue
            points.append((to_arm @ np.append(np.array(v.co), 1.0))[:3])
            owners.append(gname[best.group])
            weights.append({gname[x.group]: x.weight for x in v.groups if x.weight > 0 and gname.get(x.group) in parents})
    rig = R.Rig(rest={b.name: np.array(b.matrix_local) for b in bones},
                tails={b.name: np.array(b.tail_local) for b in bones},
                parents=parents, up=up, points=np.array(points), owners=owners, weights=weights)
    proxy = R.build_proxy(rig, mapping)

    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = 30, 1
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    ad = arm.animation_data_create()
    report, prov = {}, []
    for name in names:
        take = args.take if args.take in cat[name]["takes"] else "A"
        preset = cat[name]["takes"][take]
        npz = MOTIONS / f"{preset['id']}.npz"
        g, joints0, hips, fps = R.load_motion(npz)
        g, hips = R.resample(g, hips, args.speed)
        frames, info = R.retarget(rig, g, joints0, hips, mapping)
        swings = R.clear_arms(rig, frames, proxy) if proxy else {}
        contacts = R.soma_contacts(g, joints0, hips, fps, args.speed)
        feet = R.lock_feet(rig, frames, fps, contacts) if "feet" not in skip else {}
        act = bpy.data.actions.new(name)
        ad.action = act
        for t, basis in enumerate(R.bases(rig, frames)):
            for b, mtx in basis.items():
                pb = arm.pose.bones[b]
                pb.matrix_basis = Matrix(mtx.tolist())
                pb.keyframe_insert("rotation_quaternion", frame=t)
                if parents[b] is None:
                    pb.keyframe_insert("location", frame=t)
        track = ad.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, 0, act)
        if getattr(act, "slots", None) and hasattr(strip, "action_slot"):
            strip.action_slot = act.slots[0]
        ad.action = None
        report[name] = dict(frames=len(frames), seconds=round((len(frames) - 1) / fps, 2),
                            hip_scale=round(info["hip_scale"], 3), arm_swing=swings, feet=feet)
        prov.append(dict(clip=name, preset=preset["id"], take=take, prompt=preset["prompt"],
                         made_with=preset["made_with"], seed=preset["seed"], speed=args.speed,
                         frames=len(frames), fps=fps, file=f"tools/motions/{npz.name}", sha256=sha256(npz)))
        print(f"presets: {name} {json.dumps(report[name])}")
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    sc.frame_start, sc.frame_end = 0, max(r["frames"] for r in report.values()) - 1
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_force_sampling=True)
    print(f"presets: {path} — clips {[t.name for t in ad.nla_tracks]}")
    (out / f"{stem}_animated.provenance.json").write_text(json.dumps(dict(
        output=path.name, asset=asset.name, asset_sha256=sha256(asset), source=SOURCE,
        notice="Motions: Licensed by NVIDIA Corporation under the NVIDIA Open Model License. "
               "Retarget: adapted from image-to-3dlab (Apache-2.0). See blender-kiln plugin/NOTICE.",
        clips=prov), indent=1))
    if not args.no_measure:
        import motion_measure as M
        measures = {}
        for name in names:
            measures[name] = M.measure(str(path), name=name)
            measures[name]["presets"] = report[name]
            fs, fl, sk = measures[name]["foot_slide"], measures[name]["floor"], measures[name]["skin"]
            print(f"presets: measured {name}: slide {fs['mm_s']} mm/s, below floor {fl['below_mm']} mm, "
                  f"arms in body {sk['mean_arm_body_mm2']} mm², seam {measures[name]['seam_x_step']}x a step")
        (out / f"{stem}_animated.measures.json").write_text(json.dumps(measures, indent=1))
    return 0


def main() -> int:
    if "--" in sys.argv:                              # inside Blender
        argv = sys.argv[sys.argv.index("--") + 1:]
        return blender_animate(parse(argv))
    argv = sys.argv[1:]
    args = parse(argv)
    if args.cmd == "list":
        return cmd_list(args)
    return cmd_animate(args, argv)


if __name__ == "__main__":
    sys.exit(main())
