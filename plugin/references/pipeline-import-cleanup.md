# Pipeline — [4] IMPORT and [5] CLEANUP

> Read before [4] IMPORT. Rule numbers are SKILL.md's Iron Rules.

## Contents
- [4] IMPORT
- [5] CLEANUP

## [4] IMPORT

```
get_scene_info() → import via execute_blender_code
→ get_object_info(name) → verify world_bounding_box   (rules 14, 23)
→ RENAME to SM_PascalCase, data-block to SM_..._Mesh   (rule 15)
→ center + normalize scale if needed (1 unit = 1 meter)
→ alert if dimensions seem wrong ("Asset is 0.002m tall. Scale issue?")
→ frame the viewport, THEN get_viewport_screenshot     (rule 2)
```

**Measure the pose (rule 13) — characters only.** Do it here, before anything
downstream assumes a rest pose. Measure **shoulder to hand**, never a horizontal
slice of the mesh: a slice picks up hip and thigh vertices and reported -17 deg
on a body whose arms were actually at -71 deg.

```python
cos = [v.co for v in mesh.data.vertices]
H = max(c.z for c in cos)
right = [c for c in cos if c.x > 0]
hand = max(right, key=lambda c: c.x)
torso_w = max(c.x for c in cos if abs(c.z - H * 0.75) < H * 0.02)
shoulder = max((c for c in right if abs(c.x - torso_w) < 0.03), key=lambda c: c.z)
angle = math.degrees(math.atan2(hand.z - shoulder.z, hand.x - shoulder.x))
```

| Angle | Pose | Action |
|---|---|---|
| within ±15 deg | T-pose | proceed |
| -15 to -45 deg | A-pose | convert — see `references/characters.md` § Converting a pose to T-pose |
| below -45 deg | I-pose, arms at the sides | convert; this is the hardest case, the arms touch the torso |

A T-pose also shows in the silhouette: **wingspan ≈ height**. The reference body
measured 1.68 m across for 1.69 m tall once converted.

**Rename on import — every method, not just scripted.** A marketplace download
lands under whatever name the source file carried (`ClassicNightstand_01`), and an
AI-generated mesh under whatever the importer chose. Neither satisfies rule 15, so
rename here, in IMPORT, before anything downstream reads the name:

```python
obj.name = "SM_ClassicNightstand"
obj.data.name = "SM_ClassicNightstand_Mesh"
```

**Frame before you screenshot.** `get_viewport_screenshot` captures the viewport
as it is aimed. On a wide-angle view a 0.7 m prop is a handful of pixels at the
origin, so the screenshot rule 2 relies on shows an apparently empty scene — which
reads as "the operation deleted everything". Frame the subject first:

```python
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for region in area.regions:
            if region.type == 'WINDOW':
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_selected()
```

**Output format:**
```
── ✅ IMPORT ────────────────────────────────
{name} │ {faces} faces │ {x}×{y}×{z}m │ {file_size}
```

For scripted assets: import is implicit (already in Blender).

## [5] CLEANUP

Load `references/validation-checklist.md` and execute:

Execute the full cleanup sequence from `references/validation-checklist.md` § Execution Order. Check poly budget against tier from `references/topology-rules.md`.

**Print set in CONFIG: not the same sequence.** Its 0.1 mm merge broke a printable model
(PASS → FAIL) while its own count read 0; the print variant is under § Execution Order —
no merge on a model built closed, `print_check` on the STL as the count, no tier decimation.

**Poly check:** report the count against the tier. Past **2× the tier's top** → **propose decimate with before/after** (always interactive, even in auto mode); below that, say where the triangles go and keep them.

**Thin parts are never decimated** — wires, bails, loops: anything an order of magnitude
thinner than the body. A simplifier breaks them whatever the budget, and silhouette scores do not see the
holes it leaves. Rebuild each as a curve with a round bevel along the
high-poly's centreline; decimate the body only. **After decimating, compare open and
non-manifold edge counts with before, and look at a close render of every thin part.**

**A creature to animate:** its voxel skin goes through QuadriFlow (merge by distance first),
then the weights are checked on fixed poses before any loop is built by hand
(`references/characters.md` § Retopology: QuadriFlow first). No session did it unasked.

**Auto mode:** non-destructive cleanup runs automatically. Decimate remains interactive.
**Guided mode:** show each step, wait for validation.

**Print set in CONFIG:** after any repair (union, remesh, decimate), run `tools/print_check.py`
with `--reference` on the file it was repaired from (`references/print.md` § The tool): a
sealed, sliceable result can have lost most of the object, and only that comparison sees it.
