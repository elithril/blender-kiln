# Export Targets Reference

> Settings per export format. Axis conversion handled automatically.

---

## Axis Orientation

| Context | Forward | Up |
|---|---|---|
| Blender (working) | -Y | Z |
| glTF | +Z | Y |
| FBX (Unreal) | +X | Z |
| USDZ | variable | Y |

Blender's glTF exporter handles conversion automatically. For FBX, set "Forward" and "Up" in export settings.

---

## glTF / GLB

**The default export target.** Best for web, AR/VR, Three.js/R3F.

### Blender Export Settings
```python
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',          # single binary file
    use_selection=True,            # export selected only
    export_apply=False,            # ⚠️ NEVER True — Array modifiers balloon file size (1MB → 56MB)
    export_yup=True,               # convert to Y-up (glTF convention)
    export_texcoords=True,
    export_normals=True,          # vertex colours: the default (export_vertex_color='MATERIAL');
                                  # export_colors is gone in Blender 5.2 and fails the call
    export_materials='EXPORT',
    export_image_format='AUTO',    # PNG for lossless, JPEG for lossy
    export_draco_mesh_compression_enable=False,  # apply Draco later via gltf-transform
)
```

> **⚠️ `export_apply=False`** — Modifiers (Array, Mirror, etc.) are kept unbaked. Baking at export can cause file size to explode. Replicate instances at runtime if needed.

> **⚠️ `export_draco=False`** — Always export without Draco first. Re-encoding existing Draco via gltf-transform corrupts meshes. Apply Draco as the last optimization step.

### Fallback: Export Headless CLI

The MCP server can **timeout on GLTF exports** (long-running operation). If the export via `execute_blender_code` fails or times out, use the headless CLI export:

`--python-exit-code 1` is not optional: without it Blender exits **0** when the
script raises, so a failed export reads as a successful one (measured on 5.0.1 —
an explicit `sys.exit(1)` propagates, an uncaught exception does not). Check the
exit code, then check the file exists.

```bash
blender \
  --background "/path/to/scene.blend" \
  --python-exit-code 1 \
  --python-expr "
import bpy, os
export_path = '/path/to/output.glb'
os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=export_path,
    export_format='GLB',
    export_apply=False,
    export_animations=True,
    export_nla_strips=True,
    export_cameras=True,
    export_lights=False,
    export_draco_mesh_compression_enable=False,
)
size_mb = os.path.getsize(export_path) / 1024 / 1024
print(f'Export complete: {export_path} ({size_mb:.1f} MB)')
"
```

**When to use the headless CLI:**
- Export timeout via MCP (heavy scenes, many animations)
- Batch exports (multi-format)
- Always quote paths with spaces: `"$HOME/Downloads/blend 3/scene.blend"`

### Material Rules
- **Only Principled BSDF** maps 1:1 to glTF PBR
- Custom shader nodes → NOT exported. Bake before export.
- Textures must be power of 2 (256, 512, 1024, 2048, 4096)
- Non-color data (Normal, Roughness, Metallic) → colorspace "Non-Color"

### Channel Packing (ORM)
glTF packs AO/Roughness/Metallic into one texture:
- R = Occlusion
- G = Roughness
- B = Metallic

### Compression (applied in OPTIMIZE phase)
- **Draco:** geometry compression, quantization 14-bit position, 10-bit normal
- **meshopt:** alternative, no WASM decoder needed client-side
- **KTX2/Basis:** GPU-compressed textures, 60-80% size reduction

### Texture Resolution Guidelines

| Use case | Base Color | Normal | ORM |
|---|---|---|---|
| Web/Mobile | 1024 | 1024 | 512-1024 |
| Desktop | 2048 | 2048 | 1024-2048 |
| Hero asset | 4096 | 4096 | 2048 |

---

### Finishes (KHR_materials_variants)

Finishes are one shape in several materials (oak, walnut, matte black) in **one** glTF
file: a website switches from one to the other without loading again (three.js,
model-viewer). Studio asks for them ("Variations" → "Finishes of this model") and shows
a picker in the view. Only glTF carries them: FBX, USDZ and the print files keep the
default material (make a separate model for those — a variation).

Blender 5.2's exporter writes them from its own data, **through its operators only**
(assigning `variant_idx` or `gltf2_variant_mesh_data` directly crashed Blender 5.2.2):

```python
prefs = bpy.context.preferences.addons["io_scene_gltf2"].preferences
prefs.KHR_materials_variants_ui = True          # registers the variant data; the export needs it on
sc = bpy.data.scenes[0]
finishes = [("Oak", {obj: [mat_oak, ...]}), ("Walnut", {obj: [mat_walnut, ...]})]   # per object, per slot
for i, (name, per_obj) in enumerate(finishes):
    bpy.ops.scene.gltf2_variant_add()
    sc.gltf2_KHR_materials_variants_variants[i].name = name
    sc.gltf2_active_variant = i
    for obj, mats in per_obj.items():
        for slot, m in zip(obj.material_slots, mats):
            slot.material = m
        bpy.context.view_layer.objects.active = obj
        bpy.ops.scene.gltf2_assign_to_variant()   # records this object's slots for variant i
# Put back the finish shown first (the file's own material), then export as usual.
```

- The first finish is the model's current material, under its name ("Current" when it
  has none); the one shown first is the materials left on the slots at export.
- Same slots, same UVs for every finish: only the material changes. A finish that needs
  other geometry is a variation, not a finish.
- Check after export: `extensionsUsed` holds `KHR_materials_variants`, the root
  `extensions.KHR_materials_variants.variants` lists the names, each primitive has a
  `mappings` entry per finish. Draco and the variants live together.
- Log the finishes (names, materials) in `<name>_log.md`.

## FBX

**For Unity and Unreal Engine.**

### Blender Export Settings
```python
bpy.ops.export_scene.fbx(
    filepath=output_path,
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',
    apply_unit_scale=True,
    bake_space_transform=True,
    use_mesh_modifiers=True,
    mesh_smooth_type='FACE',       # let engine handle smoothing
    use_armature_deform_only=True,  # skip helper bones
    add_leaf_bones=False,
    path_mode='COPY',              # embed textures
    embed_textures=True,
    batch_mode='OFF',
)
```

### Unity Specifics
- Scale Factor: 1.0 (if Blender export is correct)
- Materials need recreation in Unity (Blender materials don't transfer)
- Animations: export as "All Actions" or "NLA Strips"

### Unreal Engine 5 Specifics
- FBX version 7.4 (Blender default, compatible)
- Collision meshes: prefix `UCX_MeshName`
- LODs: name `MeshName_LOD0`, `MeshName_LOD1`, etc.
- Nanite: import high-poly directly, enable Nanite in mesh properties
- Skeletal: root bone must be X-forward for UE5

---

## USDZ

**For Apple AR (Quick Look, Reality Composer).**

USDZ is a zip archive containing a USD file + textures.

### Blender exports it natively — start here

Measured on Blender 5.0.1 with a full PolyHaven PBR material:

```python
bpy.ops.wm.usd_export(
    filepath=path,                    # .usdz extension selects the archive
    selected_objects_only=True,
    export_materials=True,
    export_textures_mode='NEW',       # copies textures into the archive
    relative_paths=True,
    convert_world_material=False,     # see the gotcha below — this matters
    export_animation=True,            # an animated model: OFF by default, the USDZ is then still
    convert_orientation=True,         # ARKit wants Y up: usdchecker --arkit fails on Z up
    export_global_forward_selection='NEGATIVE_Z',
    export_global_up_selection='Y',
)
```

**Animation:** `export_animation` is off by default — checked on Blender 5.2.2: with
kiln's settings an animated cube and a rigged bone came out still (no time samples);
with it on, the cube's `xformOp:translate` and the bone's `SkelAnimation` (24 keys) are
there. AR Quick Look plays the file's animation in a loop, with no choice of clip: the
one the scene has active is the one seen. Several clips to show in AR: a USDZ per clip.

What that produced: a 1.86 MB archive holding the `.usdc` plus **four JPEG maps**,
and a complete preview-surface graph — 1 `UsdPreviewSurface`, 4 `UsdUVTexture`,
1 `UsdPrimvarReader_float2`, with `normal`, `roughness`, `metallic` **and
`displacement`** connected.

That is *more* than the glTF export of the same material carries: glTF kept 3 maps
and dropped displacement entirely (see
`references/texturing-strategy.md` § texture maps).

**The one real gotcha:** `convert_world_material` defaults to True, which writes a
`DomeLight` referencing an **`.exr`** into the archive. The USDZ specification
admits PNG and JPEG only, so that file makes the archive non-conforming and can
break iOS Quick Look. Setting it to False removes it — verified, the archive then
holds nothing but the `.usdc` and its JPEGs.

Cosmetic: exported texture files get temporary names (`tmprw2fto0v.jpg`). Harmless,
but rename them if the archive is a deliverable.

### If the native export is not enough

Reality Converter (macOS GUI, from Apple Developer tools) and `usdzconvert` remain
options, but neither is needed for a standard PBR prop and both are an extra
install. Reach for them only when you have measured a specific shortfall — and
record what it was, so the next person does not reinstall them on faith.

### USDZ Constraints
- Images: **PNG and JPEG only.** Anything else (EXR, TIFF) makes the archive
  non-conforming — hence `convert_world_material=False` above
- Maximum texture size: 4096x4096 (Apple recommendation: 2048)
- Materials: PBR Metallic/Roughness workflow
- Animations: skeletal and transform supported
- No custom shaders

---

## STL / 3MF (3D print)

Everything for print — export in mm (`global_scale=1000`), 3MF only when its extension is
installed, and `tools/print_check.py` on the file — is in `references/print.md`, rule 9 of
§ Printable from the brief and § The tool. The glTF material rules above do not apply: an
STL carries geometry only.

## Multi-Target Export

When export target is "multi":
1. Export glTF/GLB first (primary format)
2. Export FBX from the same Blender scene
3. Export USDZ from the same scene with `bpy.ops.wm.usd_export` — no CLI
   conversion needed, and it carries more maps than the GLB

Each format in its output folder (`naming-conventions.md` § Outputs):
```
generated-assets/wooden-chair/
├── web/   wooden-chair_final.glb
├── game/  wooden-chair_game.fbx
└── ar/    wooden-chair_ar.usdz, wooden-chair_ar.glb
```

---

## Pre-Export Checklist

Before ANY export:
1. ✅ All transforms applied (loc=0, rot=0, scale=1)
2. ✅ Doubles merged
3. ✅ Normals recalculated
4. ✅ Origin at center of base
5. ✅ Naming conventions applied
6. ✅ Materials are Principled BSDF (for glTF)
7. ✅ Textures are power of 2
8. ✅ No missing textures
9. ✅ No empty material slots
10. ✅ Material audit passed — no unbaked procedural nodes (see validation-checklist.md)

---

## Post-Export Validation Checklist

After EVERY export, verify before delivering the GLB:

0. ✅ **Khronos validator** — `gltf-transform validate final.glb` must exit **0**.
   It exits 1 on a broken file and names the error (`ACCESSOR_TOO_LONG`,
   `UNRESOLVED_REFERENCE` — both seeded and caught, 2026-09-29). Run it after each
   optimization step too: re-encoding Draco is where files break. It checks the
   *format*, not the mesh — a model with dozens of fused edges passes it clean.
1. ✅ **Reasonable file size** — Raw GLB < 30 MB, optimized < 5 MB for web. Alert if exceeded.
2. ✅ **Inspect gltf-transform** — `gltf-transform inspect final.glb` → check mesh count, texture count, texture sizes, animation count. No unexpected duplication.
3. ✅ **Visual test Babylon.js Sandbox** — drag-and-drop onto sandbox.babylonjs.com. Verify: mesh visible, textures present, animations playing, no black/pink materials.
4. ✅ **No Three.js console errors** — load in a minimal GLTFLoader test. Common errors: `Unknown extension`, missing textures, incompatible Draco version.
5. ✅ **Spot-check materials** — 3-5 materials: roughness, metalness, base color visually correct. Compare with the Blender viewport.
6. ✅ **Spot-check animations** — if animated, verify at least one animation plays. Expected frame count.
7. ✅ **Name mapping verified** — if runtime code references mesh names, confirm the mapping (see naming-conventions.md § GLTF Name Mapping).
8. ✅ **No missing textures** — check the Network tab in Babylon.js. No 404s. All textures packed in the GLB.
