# Pipeline — [5c] RIG SELECTION and [5d] ANIMATE

> Read before [5c], for a character to rig, and before [5d] or `/kiln animate`. Rule numbers are SKILL.md's Iron Rules.

## [5c] RIG SELECTION — characters only (rule 26)

Runs after CLEANUP, once the mesh is final and **welded** (rule 10). Never weight a
mesh with split edges: each copy of a vertex gets its own weights and the mesh opens
at every joint (rule 26). **Measure before choosing**, never the other way round:

```python
verts  = len(mesh.data.vertices)    # after the rule 10 weld
budget = verts / 20          # deform bones this mesh can actually carry
```

**Route by character first** — measured on one bent pose, `references/characters.md` §
Learned auto-rig (skin through skin, mm², lower is better):

- **A humanoid, or any mesh kiln did not build** (imported, generated) → `tools/autorig.py
  rig` (SkinTokens) when `tools/autorig.py status` exits 0. It crossed 2,985 mm² against
  Rigify's 3,926 on a kiln-built child, 20,917 against 50,680 on a generated humanoid with a
  hand fused to its hip. A generated quadruped: rig it both ways, keep the better — on the
  one measured (a proxy) kiln's rig won, 3,244 against 4,793.
- **A quadruped kiln built** → the hand-built rig in the table below: SkinTokens bent kiln's
  cat better (2,393 against 2,698) but walked it worse (527 mm² mean against 359).
- **Not installed** → say so with those numbers, offer `/kiln setup` (asked first, 5.6 GB),
  and rig from the table below meanwhile — worse on both humanoids measured.

`autorig.py` fails naming the bone when a limb comes back short (a hand fused to the hip):
separate the limb in the mesh, or `--allow-missing` it if the user accepts a rig
`quadruped.py` will refuse. Lid shells get their bones; ears need `--ears`. Its rig still
goes through every check below — its report carries rule 26's ratio and the dead bones — and
through the bent pose, because it is not repeatable: another run on the child gave 2,193.

Then, on the kiln route, pick from what Rigify ships — bone counts measured on Blender 5.0.1:

| Mesh vertices | Choose | Deform bones | Verts/bone |
|---:|---|---:|---:|
| < 700 | **Hand-built rig, 12-20 bones.** See `references/characters.md` § Match the rig's density | 12-20 | 20-35 |
| 700 - 3,000 | `bpy.ops.object.armature_basic_human_metarig_add()` | 35 | 20-85 |
| > 3,000 | `bpy.ops.object.armature_human_metarig_add()` | 160 | 20+ |
| quadruped | **Hand-built, Mixamo-named** — `references/characters.md` § Animation-ready skeleton | 20-30 | 20+ |

**Not Rigify's quadruped metarig**: its 34 bones are named `spine`, `front_thigh.L`… (checked,
Blender 5.2.2) and `tools/quadruped.py` reads Mixamo names only — every quadruped session built
the Mixamo skeleton by hand anyway.

**A Rigify human needs ~3,200 vertices to be worth it.** Below that it is actively
worse than a small rig: on a 370-vertex figure it left 107 of its 160 deform bones
influencing nothing, smeared the rest across 8-9 bones per vertex, and detached the
head. Do not reach for the biggest rig because it is the most capable one.

**After skinning, verify — do not assume:**

```python
dead = sum(1 for vg in mesh.vertex_groups
           if not any(g.group == vg.index and g.weight > 0.01
                      for v in mesh.data.vertices for g in v.groups))
```

Any dead deform bone means the rig is too dense for the mesh. Go down a tier.
**Eyelid bones stay out of the automatic weights** — they took 2,890 of the cat's 16,002 skin
vertices (`references/characters.md` § 6. Weight Painting).
Then run the validator in `references/characters.md` § Validation Script.

**Posing a generated Rigify rig?** Its limbs ship in IK, so the FK controls do
nothing until you flip them — see `references/characters.md` § FK/IK System. This
fails silently: no error, no movement.

## [5d] ANIMATE — optional, rigged characters and articulated objects

Only when the user asks for motion. Route by **subject** — table and measurements in
`references/animation.md`:

- **Ships its own clips** → keep them.
- **Four-legged, idle or walk** → `tools/quadruped.py` (scripted, measured, exact loop, ears,
  tail and blinks included — `--blink` takes the lid's measured closing turn).
  Other quadruped moves → the asset's clips or hand keys. **Never UniMate**: measured
  unusable on four quadrupeds; `unimate.py` refuses one unless `--force`.
- **Humanoid with kiln's names** (rigged by `tools/autorig.py`) **and a move in
  `python3 tools/presets.py list`** (walk, run, jump, dance, idle, wave, punch, kick, sit…) →
  `tools/presets.py animate --asset X_rigged.glb --motion walk,run --loop`: NVIDIA Kimodo clips,
  commercial use allowed, feet planted, arms kept out of the body, cycles closed; one GLB, a
  clip per motion. Report its measures line per clip, and say where a target is missed.
- **Biped or winged, from a sentence** — a move not in the presets, a non-human biped, wings →
  UniMate:
  `python3 tools/unimate.py status` first (exit 2 = not installed, 10 = newer upstream).
  Not installed: ask first — 3.2 GB — then `setup`. The weights are **non-commercial
  (CC BY-NC 4.0)**: say so. Prompts start "An object", one motion, "in place" rather
  than "forward" (forward slid with the feet still, 0 of 8); `--loop` keeps the sample
  that loops best.
- **Articulated object** (lamp, chest, door) → keyframe the rigid parts.

Whatever the route, follow `references/animation.md` § Rules for scripted animation —
every rule there is a cycle that looked wrong until it was measured.
