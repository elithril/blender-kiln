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
    export_normals=True,
    export_colors=True,
    export_materials='EXPORT',
    export_image_format='AUTO',    # PNG for lossless, JPEG for lossy
    export_draco_mesh_compression_enable=False,  # apply Draco later via gltf-transform
)
```

> **⚠️ `export_apply=False`** — Les modifiers (Array, Mirror, etc.) sont conservés non-bakés. Les bake à l'export peut faire exploser la taille du fichier. Répliquer les instances au runtime si nécessaire.

> **⚠️ `export_draco=False`** — Toujours exporter sans Draco d'abord. Re-encoder du Draco existant via gltf-transform corrompt les meshes. Appliquer Draco en dernière étape d'optimisation.

### Fallback: Export Headless CLI

Le serveur MCP peut **timeout sur les exports GLTF** (opération longue). Si l'export via `execute_blender_code` échoue ou timeout, utiliser l'export headless CLI :

```bash
blender \
  --background "/path/to/scene.blend" \
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

**Quand utiliser le headless CLI :**
- Export timeout via MCP (scènes lourdes, beaucoup d'animations)
- Exports batch (multi-format)
- Toujours quote les chemins avec espaces : `"$HOME/Downloads/blend 3/scene.blend"`

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

USDZ is a zip archive containing a USD file + textures. Blender's native USDZ export is limited.

### Option 1: Reality Converter (macOS, GUI)
Download from Apple Developer: `https://developer.apple.com/augmented-reality/tools/`

### Option 2: usdzconvert (CLI)
```bash
pip3 install usd-core
# Then:
usdzconvert input.glb output.usdz
```

### Option 3: gltf-transform (if supported)
```bash
# gltf-transform does NOT convert to USDZ
# Use usdzconvert or Reality Converter
```

### USDZ Constraints
- Maximum texture size: 4096x4096 (Apple recommendation: 2048)
- Materials: PBR Metallic/Roughness workflow
- Animations: skeletal and transform supported
- No custom shaders

---

## Multi-Target Export

When export target is "multi":
1. Export glTF/GLB first (primary format)
2. Export FBX from the same Blender scene
3. Convert GLB → USDZ via CLI

Each format saved in the output folder:
```
generated-assets/wooden-chair/
├── wooden-chair_final.glb
├── SM_WoodenChair_final.fbx
└── wooden-chair_final.usdz
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
10. ✅ Material audit passed — no nœuds procéduraux non-bakés (voir validation-checklist.md)

---

## Post-Export Validation Checklist

After EVERY export, verify before de livrer le GLB :

1. ✅ **Taille fichier raisonnable** — GLB brut < 30 MB, optimisé < 5 MB pour le web. Alerter si dépassé.
2. ✅ **Inspect gltf-transform** — `gltf-transform inspect final.glb` → vérifier mesh count, texture count, tailles textures, animation count. Pas de duplication inattendue.
3. ✅ **Test visuel Babylon.js Sandbox** — drag-and-drop sur sandbox.babylonjs.com. Vérifier : mesh visible, textures présentes, animations jouées, pas de matériaux noirs/roses.
4. ✅ **Pas d'erreurs console Three.js** — charger dans un test GLTFLoader minimal. Erreurs courantes : `Unknown extension`, textures manquantes, version Draco incompatible.
5. ✅ **Spot-check matériaux** — 3-5 matériaux : roughness, metalness, base color visuellement corrects. Comparer avec le viewport Blender.
6. ✅ **Spot-check animations** — si animé, vérifier qu'au moins une animation joue. Frame count attendu.
7. ✅ **Mapping noms vérifié** — si le code runtime référence des noms de mesh, confirmer la correspondance (voir naming-conventions.md § GLTF Name Mapping).
8. ✅ **Pas de textures manquantes** — vérifier l'onglet Network dans Babylon.js. Aucun 404. Toutes les textures packées dans le GLB.
