# Texturing Strategy Reference

## When This Applies
- Mesh is white/untextured (AI generation without texture)
- Materials are insufficient or missing
- SKIP if: asset has textures from marketplace or Hunyuan3D texture succeeded, or scripted modeling with materials already assigned

## Strategy 1 — Geometric Analysis + PolyHaven (recommended for props)

### Step 1: Geometric Analysis
Via `execute_blender_code`, analyze each face:

```python
import bmesh
import bpy
from mathutils import Vector

obj = bpy.context.active_object
bm = bmesh.new()
bm.from_mesh(obj.data)

# Classify faces by normal direction + position in bounding box
bbox = obj.bound_box
min_z = min(v[2] for v in bbox)
max_z = max(v[2] for v in bbox)
height = max_z - min_z

for face in bm.faces:
    z_ratio = (face.calc_center_median().z - min_z) / height
    is_horizontal = abs(face.normal.z) > 0.7
    is_vertical = abs(face.normal.z) < 0.3
    
    # Classification heuristics:
    # - horizontal + top half → seat/surface
    # - vertical + bottom quarter → legs
    # - vertical + top half → backrest/back
    # - horizontal + bottom → underside
```

### Step 2: Create Material Slots
```python
# Create colored materials for visualization
colors = [
    ("zone_A", (0.8, 0.2, 0.2, 1)),  # red
    ("zone_B", (0.2, 0.2, 0.8, 1)),  # blue
    ("zone_C", (0.2, 0.8, 0.2, 1)),  # green
    ("zone_D", (0.8, 0.8, 0.2, 1)),  # yellow
]

for name, color in colors:
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    obj.data.materials.append(mat)

# Assign faces to material slots based on classification
for face in bm.faces:
    face.material_index = classified_zone  # 0, 1, 2, 3...

bm.to_mesh(obj.data)
```

### Step 3: Visual Labeling
- `get_viewport_screenshot()` with colored zones visible
- Claude identifies zones: "red = seat (wood), blue = legs (wood), green = cushion (fabric)"
- Propose material mapping to user

### Step 4: User Validation
Present identified zones and proposed materials. User can adjust.

### Step 5: PolyHaven Texture Search
For each zone:
- `search_polyhaven_assets` with material keywords
- Present ~5 options with links
- User picks per zone

### Step 6: Apply Textures
```python
import bpy

# Create PBR material from PolyHaven texture
mat = bpy.data.materials.new(name="M_Wood_Oak")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Get Principled BSDF
bsdf = nodes.get("Principled BSDF")

# Add texture nodes for each map
# Base Color
tex_color = nodes.new("ShaderNodeTexImage")
tex_color.image = bpy.data.images.load(albedo_path)
links.new(tex_color.outputs["Color"], bsdf.inputs["Base Color"])

# Normal Map
tex_normal = nodes.new("ShaderNodeTexImage")
tex_normal.image = bpy.data.images.load(normal_path)
tex_normal.image.colorspace_settings.name = "Non-Color"
normal_map = nodes.new("ShaderNodeNormalMap")
links.new(tex_normal.outputs["Color"], normal_map.inputs["Color"])
links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

# Roughness
tex_rough = nodes.new("ShaderNodeTexImage")
tex_rough.image = bpy.data.images.load(roughness_path)
tex_rough.image.colorspace_settings.name = "Non-Color"
links.new(tex_rough.outputs["Color"], bsdf.inputs["Roughness"])
```

### Step 7: Iterate
User can request changes: "wood too light" → search alternative, swap texture.

## Strategy 2 — Procedural Blender Materials

For stylized/cartoon/low-poly where PBR textures are overkill:

```python
mat = bpy.data.materials.new(name="M_Wood_Stylized")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.45, 0.28, 0.14, 1.0)  # warm brown
bsdf.inputs["Roughness"].default_value = 0.7
bsdf.inputs["Metallic"].default_value = 0.0
```

No image textures, just values. Fast, lightweight, style-consistent.

### Shader Recipes (Principled BSDF)

Recettes prêtes à l'emploi pour les matériaux courants. Toutes basées sur Principled BSDF pour compatibilité GLTF export.

#### Metal
```python
mat = bpy.data.materials.new(name="M_Metal_Gold")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (1.0, 0.766, 0.336, 1.0)  # gold tint
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.2  # 0.1=mirror, 0.4=brushed
```
Variations : argent `(0.972, 0.960, 0.915)`, cuivre `(0.955, 0.637, 0.538)`, fer `(0.560, 0.570, 0.580)`.

#### Glass / Transparent
```python
mat = bpy.data.materials.new(name="M_Glass_Clear")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
bsdf.inputs["Transmission Weight"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.0   # 0=clear, >0=frosted
bsdf.inputs["IOR"].default_value = 1.45         # 1.45-1.52 for glass
```
> ⚠️ `Transmission Weight` est le nom Blender 4.x+. Anciennement `Transmission`.

#### Skin / Subsurface Scattering
```python
mat = bpy.data.materials.new(name="M_Skin_Human")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.8, 0.6, 0.5, 1.0)  # skin tone
bsdf.inputs["Subsurface Weight"].default_value = 0.5
bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)  # RGB scatter
bsdf.inputs["Roughness"].default_value = 0.4
bsdf.inputs["Metallic"].default_value = 0.0
```
> ⚠️ SSS ne s'exporte PAS en GLTF. Pour le web, bake le résultat visuel en base color texture.
> En Cycles, utiliser Random Walk pour la meilleure qualité.

#### Emission / Neon
```python
mat = bpy.data.materials.new(name="M_Neon_Blue")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Emission Color"].default_value = (0.0, 0.5, 1.0, 1.0)
bsdf.inputs["Emission Strength"].default_value = 5.0  # 1-50+
```
> L'émission S'EXPORTE en GLTF (`emissiveFactor` + `emissiveTexture`).

#### Toon / Cel Shading (EEVEE uniquement)
```python
# ⚠️ Shader to RGB = EEVEE only, NE S'EXPORTE PAS en GLTF
# Utiliser uniquement pour preview/render Blender, pas pour export web
mat = bpy.data.materials.new(name="M_Toon")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
bsdf = nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.8, 0.2, 0.2, 1.0)
# Shader to RGB → Color Ramp (Constant interpolation) → Material Output
s2rgb = nodes.new("ShaderNodeShaderToRGB")
ramp = nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = 'CONSTANT'
# 3 bandes : ombre, midtone, lumière
ramp.color_ramp.elements[0].position = 0.3
ramp.color_ramp.elements[1].position = 0.7
output = nodes.get("Material Output")
links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])
links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], output.inputs["Surface"])
```

#### Fabric / Textile
```python
mat = bpy.data.materials.new(name="M_Fabric_Cotton")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.3, 0.15, 0.08, 1.0)
bsdf.inputs["Roughness"].default_value = 0.9
bsdf.inputs["Metallic"].default_value = 0.0
# Sheen for fabric micro-fiber effect (Blender 4.x+)
bsdf.inputs["Sheen Weight"].default_value = 0.5
bsdf.inputs["Sheen Roughness"].default_value = 0.5
```

### Compatibilité Export GLTF des Propriétés Principled BSDF

| Propriété | Exporté en GLTF ? | Notes |
|---|---|---|
| Base Color | ✅ | `baseColorFactor` / `baseColorTexture` |
| Metallic | ✅ | `metallicFactor` |
| Roughness | ✅ | `roughnessFactor` |
| Normal Map | ✅ | `normalTexture` |
| Emission | ✅ | `emissiveFactor` / `emissiveTexture` |
| Alpha / Transmission | ✅ partiellement | `KHR_materials_transmission` extension |
| IOR | ✅ | `KHR_materials_ior` extension |
| Subsurface (SSS) | ❌ | Bake en base color |
| Sheen | ✅ | `KHR_materials_sheen` extension |
| Clearcoat | ✅ | `KHR_materials_clearcoat` extension |
| Toon (Shader to RGB) | ❌ | EEVEE only, pas exportable |

## Strategy 2b — Bake Procedural to Image Textures

Pour récupérer les matériaux procéduraux avant export GLTF. Utile quand l'asset a des matériaux Blender riches (Noise, Voronoi, Color Ramp) qui seraient perdus à l'export.

### Quand utiliser
- L'audit matériaux pré-export (validation-checklist.md) détecte des nœuds procéduraux
- L'asset vient de la modélisation scriptée avec des matériaux procéduraux
- On veut conserver la variation visuelle des procéduraux dans le GLB final

### Workflow de Bake

```python
import bpy, os

def bake_channel(obj, channel_type, output_path, resolution=1024):
    """
    Bake a material channel to an image texture.
    channel_type: 'DIFFUSE', 'ROUGHNESS', 'NORMAL', 'EMIT'
    """
    # Ensure Cycles is active (required for baking)
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 64  # enough for bake
    
    # Select and activate the object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Create bake target image
    img_name = f"{obj.name}_{channel_type.lower()}_baked"
    bake_img = bpy.data.images.new(img_name, width=resolution, height=resolution)
    if channel_type in ('ROUGHNESS', 'NORMAL'):
        bake_img.colorspace_settings.name = 'Non-Color'
    
    # Add image texture node to each material (set as active for bake target)
    for slot in obj.material_slots:
        if not slot.material or not slot.material.use_nodes:
            continue
        nodes = slot.material.node_tree.nodes
        img_node = nodes.new('ShaderNodeTexImage')
        img_node.image = bake_img
        img_node.name = "__bake_target__"
        nodes.active = img_node
    
    # Ensure UVs exist
    if not obj.data.uv_layers:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Bake
    bpy.ops.object.bake(type=channel_type, save_mode='INTERNAL')
    
    # Save
    bake_img.filepath_raw = output_path
    bake_img.file_format = 'PNG'
    bake_img.save()
    
    # Cleanup temp nodes
    for slot in obj.material_slots:
        if slot.material and slot.material.use_nodes:
            nodes = slot.material.node_tree.nodes
            temp = nodes.get("__bake_target__")
            if temp:
                nodes.remove(temp)
    
    print(f"✅ Baked {channel_type} → {output_path}")
    return bake_img

# Usage:
# obj = bpy.context.active_object
# bake_channel(obj, 'ROUGHNESS', '/tmp/roughness_baked.png', 1024)
# bake_channel(obj, 'NORMAL', '/tmp/normal_baked.png', 1024)
# bake_channel(obj, 'DIFFUSE', '/tmp/diffuse_baked.png', 1024)
```

### Après le bake
1. Reconnecter les images bakées aux inputs du Principled BSDF
2. Supprimer les nœuds procéduraux
3. Re-lancer l'audit matériaux pour confirmer la compatibilité
4. `get_viewport_screenshot()` pour comparer avant/après visuellement

---

## Strategy 3 — Assisted Manual Texturing

Skill prepares the terrain:
1. Auto-unwrap UVs (`bpy.ops.uv.smart_project()`)
2. Material slots created and named by zone
3. User textures manually in Blender or their own tools

## Strategy 4 — Try Another Space

If current HuggingFace Space doesn't support texture generation:
- Inform user
- Offer to try a different Space URL
- If no working Space → fall back to Strategy 1 or 2

## Choosing a Strategy

| Situation | Recommended Strategy |
|---|---|
| White mesh + realistic style | Strategy 1 (PolyHaven) |
| White mesh + stylized/cartoon | Strategy 2 (procedural) |
| User wants full control | Strategy 3 (manual assisted) |
| Another Space might work | Strategy 4 (retry) |

Always present options and let user choose.
