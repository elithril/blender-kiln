# Naming Conventions Reference

> PascalCase + prefixes in Blender, kebab-case for web files.

---

## Objects in Blender

**Format:** `{Prefix}_{DescriptiveName}`

| Prefix | Type | Example |
|---|---|---|
| `SM_` | Static Mesh | `SM_WoodenChair`, `SM_Rock_Large` |
| `SK_` | Skeletal Mesh | `SK_CharacterHero` |
| `A_` | Animation | `A_Character_Run` |

**Parts:** `SM_WoodenChair_Leg_01`, `SM_WoodenChair_Seat`
**Variants:** `SM_WoodenChair_01`, `SM_WoodenChair_02`
**LODs:** `SM_WoodenChair_LOD0`, `SM_WoodenChair_LOD1`

**Rules:**
- PascalCase always
- No spaces, no special characters, no accents
- Object name and mesh data-block must match: `SM_WoodenChair` / `SM_WoodenChair_Mesh`

---

## Materials

**Format:** `M_{MaterialType}_{Variant}`

```
M_Wood_Oak
M_Wood_Oak_Weathered
M_Metal_RustedSteel
M_Fabric_Leather_Brown
M_Stone_Cobblestone
```

---

## Textures

**Format:** `T_{AssetName}_{MapSuffix}`

| Suffix | Map type |
|---|---|
| `_D` or `_BaseColor` | Albedo / Diffuse |
| `_N` | Normal Map |
| `_R` | Roughness |
| `_M` | Metallic |
| `_AO` | Ambient Occlusion |
| `_ORM` | Packed: Occlusion / Roughness / Metallic |
| `_E` | Emissive |
| `_H` | Height / Displacement |

```
T_Wood_Oak_D.png
T_Wood_Oak_N.png
T_Wood_Oak_ORM.png
```

**Texture rules:**
- Always power of 2 (256, 512, 1024, 2048, 4096)
- Non-color data (Normal, Roughness, Metallic, AO) → set colorspace to "Non-Color" in Blender

---

## Collections in Blender

```
Props_Medieval
Characters_NPC
Environment_Forest
Lighting_Studio
```

---

## Exported Files

| Target | Convention | Example |
|---|---|---|
| glTF / web | kebab-case | `wooden-chair.glb` |
| FBX / game engine | PascalCase + prefix | `SM_WoodenChair.fbx` |
| USDZ / AR | kebab-case | `wooden-chair.usdz` |
| STL / print | kebab-case, `_{part}` per printed part — the part's name in the brief's language is fine; files go straight into the output folder the user gave | `dutch-windmill_body.stl`, `christmas-tree_etoile.stl` |
| Print reference | the parts before the union, one per printed part | `dutch-windmill_body_parts.blend` |
| Print test piece | in `test/`, `test_{what}.stl` — a coupon, a ring cut to try a mechanism | `test/test_lid-ring.stl` |

---

## Output Folder Structure

```
generated-assets/
└── wooden-chair/                    (kebab-case)
    ├── wooden-chair_original.glb
    ├── wooden-chair_clean.glb
    ├── wooden-chair_textured.glb
    ├── wooden-chair_optimized.glb
    ├── wooden-chair_preview.glb     (a copy of _original.glb: opens in macOS Quick Look)
    ├── wooden-chair.blend
    ├── wooden-chair_log.md
    ├── web/    wooden-chair_final.glb                         (output: a website)
    ├── game/   wooden-chair_game.fbx                          (output: Unity, Unreal)
    ├── ar/     wooden-chair_ar.usdz, wooden-chair_ar.glb      (output: iPhone and Vision Pro, Android)
    └── print/  wooden-chair_print.3mf, wooden-chair_print_seat.stl, …   (output: 3D printing)
```

**Outputs** — one model, a folder per use; the source (the stages, the `.blend`, the log,
the preview) stays at the root. A folder is made when its output is asked for, never empty.
Kiln Studio's Outputs bar finds them by these names and offers to prepare the missing ones
(a `_final.glb` at the root, from before, still counts as the web output):

| Output | Files | How |
|---|---|---|
| Web | `web/{name}_final.glb` | the web target (Draco, WebP) |
| Game | `game/{name}_game.fbx` | `references/export-targets.md` § FBX, from the same scene |
| AR | `ar/{name}_ar.usdz` + `ar/{name}_ar.glb` | `bpy.ops.wm.usd_export(filepath=…usdz)` and the glTF exporter (no Draco: Android's viewer has none), from the same scene |
| 3D print | `print/{name}_print.3mf` + `print/{name}_print_{part}.stl` | print mode (`references/print.md`), then the 3MF below |

The 3MF gathers the checked STLs, as on the bed, in millimetres — PrusaSlicer's command line,
**run from the print folder** (a path in `-o` or no `--dont-arrange`: no file, and still
exit 0):

```bash
cd generated-assets/wooden-chair/print
/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer -m --dont-arrange --export-3mf \
    -o wooden-chair_print.3mf wooden-chair_print_seat.stl wooden-chair_print_legs.stl
```

No PrusaSlicer: the STLs alone, and the report says the 3MF is missing.

---

## GLTF Name Mapping

Blender names are **transformed** on GLTF export. Important for runtime code that references meshes by name.

| Transformation | Blender | GLTF |
|---|---|---|
| Spaces → underscores | `RINGS ball L` | `RINGS_ball_L` |
| Dots → removed | `Sphere.003` | `Sphere003` |
| Combined | `RINGS L.001` | `RINGS_L001` |
| Trailing space | `RINGS S ` | `RINGS_S_` |

**Rule:** Always verify names in the exported GLB (via `gltf-transform inspect`), not in Blender, when runtime code references meshes.

**Verification script:**
```python
import bpy
for obj in bpy.data.objects:
    gltf_name = obj.name.replace(" ", "_").replace(".", "")
    if gltf_name != obj.name:
        print(f"⚠️ '{obj.name}' → '{gltf_name}' in GLTF")
```

---

## Applying Conventions via Python

```python
import bpy

def apply_naming(obj, asset_name, prefix="SM"):
    """Rename object and mesh data to convention."""
    obj.name = f"{prefix}_{asset_name}"
    if obj.data:
        obj.data.name = f"{prefix}_{asset_name}_Mesh"
    
    # Rename materials
    for i, slot in enumerate(obj.material_slots):
        if slot.material and not slot.material.name.startswith("M_"):
            slot.material.name = f"M_{slot.material.name}"

# Example
obj = bpy.context.active_object
apply_naming(obj, "WoodenChair")
```
