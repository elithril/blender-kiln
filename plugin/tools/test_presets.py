#!/usr/bin/env python3
"""Check presets.py on a seeded humanoid: clip names, the licence trail, and the measures.

    python3 tools/test_presets.py      # catalogue and licence files: standard library only
                                       # + the Blender stage when Blender is at $BLENDER or the macOS default

Standard library: the 43 shipped clips are all there and hash as recorded in the provenance,
the NOTICE carries the image-to-3dlab and NVIDIA lines, the adapted code says where it comes
from, an unknown motion is refused before Blender starts.
Blender stage, on a 28-bone synthetic humanoid named like tools/autorig.py's output (the
kiln child's joints, a skin of tubes and box feet, 100% to one bone each):
- the GLB holds exactly the clips asked, named as asked;
- the provenance names the motions' licence for every clip;
- feet: the walk's standing feet slide < 50 mm/s and no skin goes 5 mm under the floor, where
  the same clip with --no-fix feet slides and sinks (the regression direction);
- arms: the jump's hands and forearms, which hang into the wide hips, cross the body < 500 mm²,
  where upstream's clearance (--no-fix arms: torso, neck and head only) leaves > 500;
- a rig missing a leg bone is refused, naming it.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
checks = []


def check(what, ok, detail=""):
    checks.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'} {what}" + ("" if ok else f"  {detail}"))


# Bone heads of the kiln child as tools/autorig.py named it (metres, Z up, facing -Y).
HEADS = {
    "Hips": (0.002, 0.003, 0.279), "LeftUpLeg": (0.069, -0.001, 0.253), "LeftLeg": (0.072, -0.005, 0.142),
    "LeftFoot": (0.072, -0.001, 0.076), "LeftToeBase": (0.076, -0.064, 0.017),
    "Spine": (0.002, 0.003, 0.323), "Spine1": (0.002, 0.003, 0.375), "Spine2": (0.002, 0.003, 0.434),
    "LeftShoulder": (0.039, 0.003, 0.493), "LeftArm": (0.113, 0.003, 0.482), "LeftForeArm": (0.205, 0.003, 0.419),
    "LeftHand": (0.286, 0.003, 0.353), "LeftFingers": (0.32, 0.003, 0.323), "LeftFingers2": (0.331, 0.003, 0.316),
    "LeftFingers3": (0.345, 0.003, 0.305), "Neck": (0.002, 0.003, 0.5), "Head": (0.002, 0.01, 0.615),
}
PARENT = {"Hips": None, "LeftUpLeg": "Hips", "LeftLeg": "LeftUpLeg", "LeftFoot": "LeftLeg", "LeftToeBase": "LeftFoot",
          "Spine": "Hips", "Spine1": "Spine", "Spine2": "Spine1", "LeftShoulder": "Spine2", "LeftArm": "LeftShoulder",
          "LeftForeArm": "LeftArm", "LeftHand": "LeftForeArm", "LeftFingers": "LeftHand", "LeftFingers2": "LeftFingers",
          "LeftFingers3": "LeftFingers2", "Neck": "Spine2", "Head": "Neck"}
for _b in [b for b in HEADS if b.startswith("Left")]:
    x, y, z = HEADS[_b]
    HEADS["Right" + _b[4:]] = (-x, y, z)
    p = PARENT[_b]
    PARENT["Right" + _b[4:]] = "Right" + p[4:] if p.startswith("Left") else p
# Wide hips, like the chibi child's (0.11 from the spine) and the Hunyuan humanoid's: hanging
# hands go into them, which upstream's clearance (torso, neck, head only) leaves.
RADIUS = {"Hips": 0.11, "Spine": 0.09, "Spine1": 0.085, "Spine2": 0.08, "Neck": 0.03, "Head": 0.11,
          "Shoulder": 0.012, "Arm": 0.022, "ForeArm": 0.02, "Hand": 0.02, "Fingers": 0.012, "Fingers2": 0.01,
          "Fingers3": 0.008, "UpLeg": 0.035, "Leg": 0.03}


def build(out, drop=()):  # pragma: no cover - needs bpy
    """The synthetic humanoid as a GLB: one armature, one skin."""
    import bmesh
    import bpy
    from mathutils import Matrix, Vector

    bpy.ops.wm.read_factory_settings(use_empty=True)
    ad = bpy.data.armatures.new("SK_Test_Armature")
    arm = bpy.data.objects.new("SK_Test_Armature", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    kids = {b: [c for c, p in PARENT.items() if p == b] for b in PARENT}
    for b, h in HEADS.items():
        if b in drop:
            continue
        e = ad.edit_bones.new(b)
        e.head = h
        own = [c for c in kids[b] if c not in drop and not c.endswith("Shoulder") and c not in ("LeftUpLeg", "RightUpLeg")]
        if b == "Hips":
            own = ["Spine"]
        if own:
            e.tail = HEADS[own[0]]
        elif b == "Head":
            e.tail = (h[0], h[1], h[2] + 0.2)
        else:
            d = Vector(h) - Vector(HEADS[PARENT[b]])
            e.tail = Vector(h) + d.normalized() * 0.03
    for b in HEADS:
        if b in drop or PARENT[b] is None or PARENT[b] in drop:
            continue
        ad.edit_bones[b].parent = ad.edit_bones[PARENT[b]]
    bpy.ops.object.mode_set(mode="OBJECT")
    bm = bmesh.new()
    owner = []

    def tube(a, b, r, bone):
        a, b = Vector(a), Vector(b)
        axis = b - a
        rot = axis.to_track_quat("Z", "Y").to_matrix().to_4x4()
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=r, depth=axis.length,
                                    matrix=Matrix.Translation((a + b) / 2) @ rot)
        owner.extend((v, bone) for v in res["verts"])

    def box(lo, hi, bone):
        lo, hi = Vector(lo), Vector(hi)
        res = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((lo + hi) / 2) @
                                    Matrix.Diagonal((*(hi - lo), 1.0)))
        owner.extend((v, bone) for v in res["verts"])

    for b in HEADS:
        if b in drop or b.endswith(("Foot", "ToeBase")):
            continue
        key = b[4:] if b.startswith("Left") else b[5:] if b.startswith("Right") else b
        a, tail = Vector(HEADS[b]), ad.bones[b].tail_local
        if b.startswith(("Left", "Right")):     # limbs stop short of their joints: no crossing at a bend
            a, tail = a.lerp(tail, 0.15), a.lerp(tail, 0.85)
        tube(a, tail, RADIUS[key], b)
    for s, sx in (("Left", 1), ("Right", -1)):
        if s + "Foot" not in drop:
            box((sx * 0.072 - 0.03, -0.05, 0.0), (sx * 0.072 + 0.03, 0.035, 0.08), s + "Foot")
            box((sx * 0.076 - 0.028, -0.095, 0.0), (sx * 0.076 + 0.028, -0.05, 0.03), s + "ToeBase")
    me = bpy.data.meshes.new("SK_Test")
    bm.verts.index_update()
    idx = [(v.index, bone) for v, bone in owner]
    bm.to_mesh(me)
    bm.free()
    body = bpy.data.objects.new("SK_Test", me)
    bpy.context.scene.collection.objects.link(body)
    for i, bone in idx:
        g = body.vertex_groups.get(bone) or body.vertex_groups.new(name=bone)
        g.add([i], 1.0, "REPLACE")
    body.parent = arm
    body.modifiers.new("Armature", "ARMATURE").object = arm
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_format="GLB")


def find_blender():
    for c in (os.environ.get("BLENDER"), shutil.which("blender"), "/Applications/Blender.app/Contents/MacOS/Blender"):
        if c and Path(c).exists():
            return c
    return None


def glb_animations(path):
    b = Path(path).read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    return [a.get("name") for a in json.loads(b[20:20 + n]).get("animations", [])]


def main():
    sys.path.insert(0, str(HERE))
    import presets
    print("── test_presets: catalogue and licences")
    cat = presets.catalogue()
    clips = [p for m in cat.values() for p in m["takes"].values()]
    check("22 motions, 43 clips, every .npz shipped",
          len(cat) == 22 and len(clips) == 43 and all((presets.MOTIONS / f"{p['id']}.npz").exists() for p in clips),
          f"{len(cat)} motions, {len(clips)} clips")
    check("every cyclic motion is in the catalogue", all(c in cat for c in presets.CYCLIC), presets.CYCLIC)
    notice = " ".join((PLUGIN / "NOTICE").read_text().split())
    check("NOTICE credits image-to-3dlab with its link and the NVIDIA licence line",
          "https://github.com/Bingeljell/image-to-3dlab" in notice and "tools/retarget.py" in notice
          and "Licensed by NVIDIA Corporation under the NVIDIA Open Model License" in notice)
    lic = (presets.MOTIONS / "LICENSE-image-to-3dlab.txt").read_text()
    check("the Apache-2.0 text ships with the clips", "Apache License" in lic and "Version 2.0" in lic)
    head = (HERE / "retarget.py").read_text()[:1200]
    check("retarget.py says what it adapts, from where, under which licence",
          "image-to-3dlab" in head and "Apache License, Version 2.0" in head and "Changed here" in head)
    r = subprocess.run([sys.executable, str(HERE / "presets.py"), "animate", "--asset", "x.glb", "--motion", "moonwalk"],
                       capture_output=True, text=True, env={**os.environ, "BLENDER": "/nonexistent"})
    check("an unknown motion is refused, before Blender, pointing at the routes",
          r.returncode != 0 and "moonwalk" in r.stderr and "animation.md" in r.stderr, r.stderr[-200:])

    blender = find_blender()
    if not blender:
        print("  skip Blender stage: no Blender")
        return finish()
    print("── test_presets: Blender stage (synthetic humanoid)")
    tmp = Path(tempfile.mkdtemp(prefix="kiln_presets_"))
    rig = tmp / "SK_Test_rigged.glb"
    bad = tmp / "SK_NoFoot_rigged.glb"
    for path, drop in ((rig, ""), (bad, "LeftFoot,LeftToeBase")):
        subprocess.run([blender, "--background", "--factory-startup", "--python-exit-code", "1", "--python",
                        str(Path(__file__).resolve()), "--", "build", str(path), drop],
                       check=True, capture_output=True)
    env = {**os.environ, "BLENDER": blender}
    run = subprocess.run([sys.executable, str(HERE / "presets.py"), "animate", "--asset", str(rig),
                          "--motion", "walk,jump", "--out", str(tmp)], capture_output=True, text=True, env=env)
    out = tmp / "SK_Test_rigged_animated.glb"
    check("presets.py animate runs on a kiln-named rig", run.returncode == 0 and out.exists(), run.stdout[-600:] + run.stderr[-600:])
    if out.exists():
        check("one clip per motion, named exactly as asked", glb_animations(out) == ["walk", "jump"], glb_animations(out))
        prov = json.loads((tmp / "SK_Test_rigged_animated.provenance.json").read_text())
        check("the provenance names the motions' licence and source for every clip",
              "NVIDIA Open Model License" in prov["source"]["motion_licence"] and len(prov["clips"]) == 2
              and all(c["sha256"] == presets.sha256(presets.MOTIONS / f"{c['preset']}.npz") for c in prov["clips"]))
        meas = json.loads((tmp / "SK_Test_rigged_animated.measures.json").read_text())
        nofix = subprocess.run([sys.executable, str(HERE / "presets.py"), "animate", "--asset", str(rig), "--motion", "walk,jump",
                                "--no-fix", "feet,arms", "--out", str(tmp / "nofix")], capture_output=True, text=True, env=env)
        raws = json.loads((tmp / "nofix" / "SK_Test_rigged_animated.measures.json").read_text()) \
            if nofix.returncode == 0 else {}
        raw = raws.get("walk")
        w = meas["walk"]
        check(f"feet planted: walk slides {w['foot_slide']['mm_s']} mm/s, {w['floor']['below_mm']} mm under the floor "
              f"(without the fix: {raw and raw['foot_slide']['mm_s']} mm/s, {raw and raw['floor']['below_mm']} mm)",
              raw and w["foot_slide"]["mm_s"] < 50 and w["floor"]["below_mm"] < 5
              and (raw["foot_slide"]["mm_s"] > 50 or raw["floor"]["below_mm"] > 5))
        j, rj = meas["jump"]["skin"]["mean_arm_body_mm2"], raws.get("jump", {}).get("skin", {}).get("mean_arm_body_mm2")
        check(f"arms out of the hips: jump {j} mm² of arm through body (upstream's clearance: {rj} mm²)",
              rj is not None and j < 500 < rj)
    bad_run = subprocess.run([sys.executable, str(HERE / "presets.py"), "animate", "--asset", str(bad),
                              "--motion", "walk", "--out", str(tmp)], capture_output=True, text=True, env=env)
    check("a rig without LeftFoot is refused, naming it", bad_run.returncode != 0 and "LeftFoot" in bad_run.stdout + bad_run.stderr,
          bad_run.stdout[-300:])
    shutil.rmtree(tmp, ignore_errors=True)
    return finish()


def finish():
    print(f"── {sum(checks)}/{len(checks)} checks pass")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    if "--" in sys.argv:
        a = sys.argv[sys.argv.index("--") + 1:]
        if a[0] == "build":
            build(a[1], tuple(x for x in (a[2] if len(a) > 2 else "").split(",") if x))
        sys.exit(0)
    sys.exit(main())
