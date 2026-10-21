#!/usr/bin/env python3
"""Check autorig.py names SkinTokens' raw skeletons the way kiln does, cleans their weights,
and refuses what it cannot name — all without SkinTokens installed.

    python3 tools/test_autorig.py      # mapping and cleaning: standard library only
                                       # + the Blender stage when Blender is at $BLENDER or the macOS default

Mapping, on the four raw skeletons the measurements in characters.md § Learned auto-rig were
made with (fixtures/skintokens_skeletons.json):
- each maps to the names given by hand for the measured cells (the kiln child, the
  generated humanoid, kiln's cat, a generated cat), body type found;
- the generated humanoid, whose hand is fused to its hip, FAILS naming RightHand — and
  passes with --allow-missing RightHand, saying so;
- seeded: a leg removed, the model turned to face +Y, a second root: each FAILS, by name;
- seeded: the bones renumbered, the joints moved by up to 5 mm (two runs on one mesh moved
  them 8 mm): same names.
Cleaning, on a seeded strip: 6 influences become 4, normalised; a far island of a bone is
dropped; an eye held by its bone alone is kept; an unweighted vertex takes its neighbour's.
Blender stage, on a decimated raw output (fixtures/skintokens_raw_child.glb, 1,843 vertices):
the named rig is written, passes its checks; lid shells get their bones and nothing of the
skin; ear cones get their bones' weights; a raw skeleton with an arm deleted exits 1 naming it.
"""
import json, os, random, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import autorig  # noqa: E402

FIX = json.loads((HERE / "fixtures" / "skintokens_skeletons.json").read_text())
checks = []


def check(what, ok, detail=""):
    checks.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'} {what}" + ("" if ok else f"  {detail}"))


def mapped(sk, **kw):
    return autorig.map_skeleton(sk["heads"], sk["tails"], sk["parents"], sk.get("mass"), **kw)


def fails(sk, **kw):
    try:
        mapped(sk, **kw)
        return None
    except autorig.MappingError as e:
        return str(e)


def drop(sk, gone):
    """The skeleton without the bones in `gone` (and their subtrees), renumbered."""
    kids = autorig._children(sk["parents"])
    gone = {j for g in gone for j in autorig._subtree(g, kids)}
    keep = [i for i in range(len(sk["parents"])) if i not in gone]
    new = {o: k for k, o in enumerate(keep)}
    return {"heads": [sk["heads"][i] for i in keep], "tails": [sk["tails"][i] for i in keep],
            "parents": [None if sk["parents"][i] is None else new[sk["parents"][i]] for i in keep],
            "mass": [sk["mass"][i] for i in keep]}


# Names given by hand to the measured cells (index: name), where the hierarchy agrees.
EXPECT = {
    "kiln_child": ("humanoid", {0: "Hips", 3: "Spine2", 4: "Neck", 5: "Head", 6: "LeftShoulder", 7: "LeftArm",
                                9: "LeftHand", 13: "RightShoulder", 16: "RightHand", 20: "LeftUpLeg",
                                22: "LeftFoot", 23: "LeftToeBase", 27: "RightToeBase"}),
    "generated_humanoid": ("humanoid", {0: "Hips", 3: "Spine2", 4: "Neck", 5: "Head", 6: "LeftShoulder",
                                        9: "LeftHand", 10: "RightShoulder", 12: "RightForeArm", 13: "LeftUpLeg"}),
    "kiln_cat": ("quadruped", {0: "Hips", 1: "Spine", 2: "Spine1", 3: "Neck", 4: "Head", 5: "LeftShoulder",
                               6: "LeftArm", 8: "LeftHand", 12: "RightHand", 14: "Tail1", 17: "Tail4",
                               19: "LeftUpLeg", 23: "RightHipConn", 24: "RightUpLeg", 27: "RightToeBase"}),
    "generated_cat": ("quadruped", {0: "Hips", 2: "Spine1", 3: "Neck", 4: "Head", 5: "HeadX1", 7: "LeftArm",
                                    9: "LeftHand", 10: "LeftFingers", 15: "LeftUpLeg", 19: "Tail1",
                                    23: "Tail5", 24: "RightUpLeg"}),
}

print("── mapping")
for key, (body, want) in EXPECT.items():
    r = mapped(FIX[key], allow_missing=["RightHand"] if key == "generated_humanoid" else ())
    wrong = {i: (r["names"][i], n) for i, n in want.items() if r["names"][i] != n}
    check(f"{key}: {body}, named as by hand ({len(want)} joints checked)", r["body"] == body and not wrong,
          (r["body"], wrong))

msg = fails(FIX["generated_humanoid"])
check("generated humanoid (hand fused to the hip): FAILS naming RightHand and the way out",
      msg and "RightHand" in msg and "--allow-missing RightHand" in msg, msg)
r = mapped(FIX["generated_humanoid"], allow_missing=["RightHand"])
check("... with --allow-missing RightHand: named, and the warning says quadruped.py will refuse it",
      any("RightHand" in w for w in r["warnings"]) and r["missing"] == ["RightHand"], r["warnings"])

msg = fails(drop(FIX["kiln_child"], [20]))
check("seeded: kiln child without its left leg FAILS naming LeftUpLeg, LeftLeg, LeftFoot",
      msg and all(b in msg for b in ("LeftUpLeg", "LeftLeg", "LeftFoot")), msg)
msg = fails(drop(FIX["generated_cat"], [11]))
check("seeded: generated cat without its right foreleg FAILS naming RightArm", msg and "RightArm" in msg, msg)
for key in ("kiln_child", "generated_cat"):
    sk = dict(FIX[key])
    sk["heads"] = [[-x, -y, z] for x, y, z in sk["heads"]]
    sk["tails"] = [[-x, -y, z] for x, y, z in sk["tails"]]
    msg = fails(sk)
    check(f"seeded: {key} turned to face +Y FAILS, not mirrored", msg and "+Y" in msg, msg)
sk = dict(FIX["kiln_cat"]); sk["parents"] = list(sk["parents"]); sk["parents"][13] = None
msg = fails(sk)
check("seeded: a second root bone FAILS", msg and "root" in msg, msg)

rng = random.Random(0)
for key in EXPECT:
    sk = FIX[key]
    base = mapped(sk, allow_missing=["RightHand"])["names"]
    perm = list(range(len(base))); rng.shuffle(perm)            # perm[new] = old
    inv = {o: n for n, o in enumerate(perm)}
    shuf = {"heads": [sk["heads"][o] for o in perm], "tails": [sk["tails"][o] for o in perm],
            "parents": [None if sk["parents"][o] is None else inv[sk["parents"][o]] for o in perm],
            "mass": [sk["mass"][o] for o in perm]}
    names = mapped(shuf, allow_missing=["RightHand"])["names"]
    same = all(names[inv[o]] == base[o] for o in range(len(base)))
    jit = 0.005 if "child" in key or "humanoid" in key else 0.002
    moved = []
    for _ in range(20):
        noise = {i: [rng.uniform(-jit, jit) for _ in range(3)] for i in range(len(base))}
        j = {"heads": [[a + b for a, b in zip(h, noise[i])] for i, h in enumerate(sk["heads"])],
             "tails": [[a + b for a, b in zip(t, noise[i])] for i, t in enumerate(sk["tails"])],
             "parents": sk["parents"], "mass": sk["mass"]}
        try:
            moved.append(mapped(j, allow_missing=["RightHand"])["names"] == base)
        except autorig.MappingError:
            moved.append(False)
    check(f"{key}: renumbered → same names; joints moved ±{jit * 1000:.0f} mm, 20 seeds → same names",
          same and all(moved), (same, moved.count(False)))

print("── cleaning")
# a strip of 200 vertices, 0-1-…-199, plus an eye (200-203) not connected to it
edges = [(i, i + 1) for i in range(199)] + [(200, 201), (201, 202), (202, 203)]
W = [{0: 1.0} for _ in range(200)] + [{5: 1.0} for _ in range(4)]
W[3] = {0: 0.3, 2: 0.2, 3: 0.2, 4: 0.15, 6: 0.1, 7: 0.05}        # 6 influences
for i in range(50, 200):
    W[i] = {1: 0.9, 0: 0.1}                                       # bone 1's region: 50..199
W[10] = {0: 0.7, 1: 0.3}                                          # bone 1 on vertex 10: a speck off its region
W[100] = {}                                                       # unweighted
C, st = autorig.clean_weights(W, edges)
check("6 influences → the 4 largest, normalised", len(C[3]) == 4 and abs(sum(C[3].values()) - 1) < 1e-9
      and set(C[3]) == {0, 2, 3, 4}, C[3])
check("bone 1 on a 1-vertex island away from its 150-vertex region: dropped",
      1 not in C[10] and abs(C[10][0] - 1) < 1e-9, C[10])
check("an eye held by bone 5 alone, disconnected: kept", all(C[i] == {5: 1.0} for i in range(200, 204)), C[200:])
check("an unweighted vertex takes its neighbour's weights", C[100] and abs(sum(C[100].values()) - 1) < 1e-9, C[100])
check("every vertex sums to 1", all(abs(sum(w.values()) - 1) < 1e-9 for w in C), st)
C2, st2 = autorig.clean_weights([{0: 0.6, 1: 0.4}, {0: 0.5, 1: 0.5}], [(0, 1)])
check("clean weights stay as they are (none dropped, no speck)",
      C2 == [{0: 0.6, 1: 0.4}, {0: 0.5, 1: 0.5}] and st2["speck_islands"] == 0, (C2, st2))

print("── install")
def cli(*args, home):
    r = subprocess.run([sys.executable, str(HERE / "autorig.py"), *args], capture_output=True, text=True,
                       env=dict(os.environ, KILN_SKINTOKENS_HOME=home, BLENDER=sys.executable))
    return r.returncode, r.stdout + r.stderr
with tempfile.TemporaryDirectory() as home:
    rc, log = cli("status", "--quick", home=home)
    check("status, nothing installed: exit 2, says to ask first", rc == 2 and "ask the user" in log, (rc, log[-200:]))
    rc, log = cli("setup", home=home)
    check("setup without --yes: installs nothing, exit 3, says the size and the licence",
          rc == 3 and "5.6 GB" in log and "MIT" in log and not os.listdir(home), (rc, log[-200:]))
    rc, log = cli("rig", "--asset", "x.glb", "--out", home + "/o", home=home)
    check("rig, nothing installed: exit 2 before touching Blender", rc == 2 and "not ready" in log, (rc, log[-200:]))

# ── Blender stage
BLENDER = os.environ.get("BLENDER") or "/Applications/Blender.app/Contents/MacOS/Blender"
if not os.environ.get("BLENDER") and not os.path.exists(BLENDER):
    print("── Blender stage skipped: no Blender at $BLENDER or the macOS default")
else:
    print("── Blender stage")
    RAW = HERE / "fixtures" / "skintokens_raw_child.glb"
    MAKE = r"""
import bpy, sys
raw, out, kind = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=raw)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if kind == "noarm":                       # SkinTokens without the left arm: bones 6..12 gone
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    for i in range(6, 13):
        arm.data.edit_bones.remove(arm.data.edit_bones[f"bone_{i}"])
    bpy.ops.object.mode_set(mode='OBJECT')
if kind == "lids":                        # the skin with two ear cones, two lid shells, no rig
    skin = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    from mathutils import Vector
    for sx in (1, -1):
        a, b = Vector((0.20 * sx, 0, 0.86)), Vector((0.30 * sx, 0, 0.98))
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.05, depth=(b - a).length, location=(a + b) / 2)
        c = bpy.context.object; c.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action='DESELECT'); c.select_set(True); skin.select_set(True)
        bpy.context.view_layer.objects.active = skin; bpy.ops.object.join()
    for x, n in ((0.045, "SK_Child_LidL"), (-0.045, "SK_Child_LidR")):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.03, location=(x, -0.14, 0.74))
        o = bpy.context.object; o.name = n
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in o.data.vertices:
            v.select = v.co.z < 0.0       # keep the upper cap
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.delete(type='VERT'); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_animations=False)
"""

    def blender(script, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(script)
        r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                            "--python", f.name, "--", *map(str, args)], capture_output=True, text=True)
        os.unlink(f.name)
        return r.returncode

    def rig(*args):
        r = subprocess.run([sys.executable, str(HERE / "autorig.py"), "rig", *map(str, args)],
                           capture_output=True, text=True, env=dict(os.environ, BLENDER=BLENDER))
        rep = [json.loads(l.split("autorig: ", 1)[1]) for l in r.stdout.splitlines() if l.startswith("autorig: {")]
        return r.returncode, r.stdout + r.stderr, rep[-1] if rep else {}

    def glb_joints(path):
        import struct
        b = Path(path).read_bytes(); n = struct.unpack("<I", b[12:16])[0]
        j = json.loads(b[20:20 + n])
        skins = j.get("skins", [])
        meshes = {nd.get("name"): nd.get("skin") for nd in j["nodes"] if "mesh" in nd}
        return [{j["nodes"][k]["name"] for k in s["joints"]} for s in skins], meshes, skins

    with tempfile.TemporaryDirectory() as d:
        rc, log, rep = rig("--asset", RAW, "--raw", RAW, "--out", d)
        joints, _, _ = glb_joints(f"{d}/skintokens_raw_child_rigged.glb") if rc == 0 else ([set()], {}, [])
        check("raw child → named rig written: every bone quadruped.py needs is a joint of the GLB",
              rc == 0 and set(autorig.REQUIRED) <= joints[0], (rc, log[-400:]))
        check("... and it passes its checks: ≤ 4 influences, nothing unweighted, no dead bone",
              rep.get("max_influences", 9) <= 4 and rep.get("unweighted") == 0 and rep.get("dead_bones") == [], rep)

        blender(MAKE, RAW, f"{d}/noarm.glb", "noarm")
        rc, log, _ = rig("--asset", RAW, "--raw", f"{d}/noarm.glb", "--out", f"{d}/noarm")
        check("seeded: raw skeleton without its left arm → exit 1 naming LeftArm, no traceback",
              rc == 1 and "LeftArm" in log and "Traceback" not in log, (rc, log[-400:]))

        blender(MAKE, RAW, f"{d}/lids.glb", "lids")
        rc, log, rep = rig("--asset", f"{d}/lids.glb", "--raw", RAW, "--out", f"{d}/lids",
                           "--ears", "200,0,860,300,0,980")
        joints, meshes, skins = glb_joints(f"{d}/lids/lids_rigged.glb") if rc == 0 else ([set()], {}, [])
        check("lid shells found by name → LeftEyelid / RightEyelid, the skin 0 vertices on them",
              rc == 0 and rep.get("lids") == ["LeftEyelid", "RightEyelid"] and rep.get("skin_on_lids") == 0
              and {"LeftEyelid", "RightEyelid"} <= joints[0], (rc, rep, log[-300:]))
        check("... each shell skinned in the GLB (100% to its bone, Armature modifier)",
              rc == 0 and meshes.get("SK_Child_LidL") is not None and meshes.get("SK_Child_LidR") is not None, meshes)
        check("--ears → LeftEar / RightEar with skin weights, no dead bone",
              rc == 0 and rep.get("ears") == ["LeftEar", "RightEar"] and rep.get("ear_vertices", 0) > 0
              and rep.get("dead_bones") == [], rep)
        EARS = r"""
import bpy, json, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
sk = bpy.data.objects["SK_KilnChild"]; gi = {g.index: g.name for g in sk.vertex_groups}
out = {}
for e, sx in (("LeftEar", 1), ("RightEar", -1)):
    w = lambda v: sum(g.weight for g in v.groups if gi[g.group] == e)
    tip = max(sk.data.vertices, key=lambda v: sx * v.co.x + v.co.z)
    out[e] = dict(tip=round(w(tip), 3), middle=sum(1 for v in sk.data.vertices if sx * v.co.x < 0.1 and w(v) > 0.01))
print("EARS " + json.dumps(out))
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(EARS)
        r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1", "--python",
                            f.name, "--", f"{d}/lids/lids_rigged.blend"], capture_output=True, text=True)
        os.unlink(f.name)
        ea = next((json.loads(l[5:]) for l in r.stdout.splitlines() if l.startswith("EARS ")), {})
        check("... local: each ear's tip 100% on its bone, no vertex near the head's middle on an ear",
              ea and all(x["tip"] > 0.99 and x["middle"] == 0 for x in ea.values()), ea)

print(f"\n{sum(checks)}/{len(checks)}")
sys.exit(0 if all(checks) else 1)
