# UV & Materials Reference

> UV unwrapping, texel density, PBR workflow, texture resolution.

---

## UV Unwrapping

### Seam Placement
- Place seams in **hidden areas**: under arms, inner legs, behind ears, underside of objects
- Follow **natural contours**: clothing seams, metal/fabric junctions, material changes
- For **hard surface**: seams at sharp edges (seams and sharp edges should coincide)
- Never place seams in the middle of visible flat surfaces

### Auto Unwrap (quick)
```python
import bpy

obj = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(
    angle_limit=66.0,      # degrees
    island_margin=0.02,    # margin between islands
    area_weight=0.0,
    correct_aspect=True,
    scale_to_bounds=True,
)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Texel Density
Maintain **uniform texel density** across the entire asset.

| Platform | Texel density | Texture resolution |
|---|---|---|
| Mobile/Web | 5.12-10.24 px/cm | 1K-2K |
| Console/PC | 10.24-20.48 px/cm | 2K-4K |
| Cinematic | 20.48+ px/cm | 4K+ |

### UV Packing
- **Margin between islands**: 4-8 pixels for 2K textures, 8-16 for 4K
- Target utilization: **>85%** of UV space
- Orient islands to maximize space (rotation allowed)
- All textures power of 2 (256, 512, 1024, 2048, 4096)

### UDIM vs Single UV

| | Single UV (0-1) | UDIM |
|---|---|---|
| Usage | Real-time (games, web, mobile) | Film, cinematic, hero assets |
| glTF support | Yes | No |
| Recommendation | **Default for blender-kiln** | Only if single UV insufficient |

---

## PBR Material Setup

### Principled BSDF (the only shader for glTF)

```python
import bpy

def create_pbr_material(name, albedo_path=None, normal_path=None, 
                         roughness_path=None, metallic=0.0, roughness=0.5,
                         base_color=(0.8, 0.8, 0.8, 1.0)):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    bsdf = nodes.get("Principled BSDF")
    
    if albedo_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(albedo_path)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = base_color
    
    if normal_path:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = bpy.data.images.load(normal_path)
        tex_n.image.colorspace_settings.name = "Non-Color"
        normal_map = nodes.new("ShaderNodeNormalMap")
        links.new(tex_n.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    
    if roughness_path:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = bpy.data.images.load(roughness_path)
        tex_r.image.colorspace_settings.name = "Non-Color"
        links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = roughness
    
    bsdf.inputs["Metallic"].default_value = metallic
    
    return mat
```

### Metallic/Roughness Workflow
This is the standard. Not Specular/Glossiness.

| Parameter | Range | Notes |
|---|---|---|
| Base Color | sRGB color | The albedo, no lighting baked in |
| Metallic | 0.0 - 1.0 | Usually binary: 0 (dielectric) or 1 (metal) |
| Roughness | 0.0 - 1.0 | 0 = mirror, 1 = completely rough |
| Normal | Tangent space | Blue-ish image, non-color data |
| AO | 0.0 - 1.0 | Cavity/occlusion, non-color |
| Emissive | sRGB color | Values > 1.0 trigger bloom in glTF |

### ORM Packing (single texture)
Pack AO, Roughness, Metallic into one texture:
- **R** = Ambient Occlusion
- **G** = Roughness  
- **B** = Metallic

Standard for glTF and Unreal Engine. Reduces texture count.

---

## Texture Resolution per Use Case

| Use case | Base Color | Normal | ORM | Emissive |
|---|---|---|---|---|
| Web/WebGL | 512-1024 | 512-1024 | 512 | 512 |
| Mobile | 1024 | 1024 | 512-1024 | 512 |
| Console/PC | 2048-4096 | 2048-4096 | 1024-2048 | 1024 |
| Film | 4096-8192 | 4096-8192 | 4096 | 2048 |

### Web Optimization
- JPEG for Base Color (lossy OK)
- PNG for Normal Map (lossless needed)
- KTX2/Basis for everything (best compression, GPU-friendly)
- WebP as intermediate format

---

## Common Material Values

| Material | Base Color | Metallic | Roughness |
|---|---|---|---|
| Wood (oak) | (0.45, 0.28, 0.14) | 0.0 | 0.6-0.8 |
| Wood (pine) | (0.6, 0.45, 0.25) | 0.0 | 0.5-0.7 |
| Metal (steel) | (0.55, 0.55, 0.55) | 1.0 | 0.3-0.5 |
| Metal (gold) | (1.0, 0.77, 0.34) | 1.0 | 0.2-0.4 |
| Metal (rusted) | (0.45, 0.25, 0.12) | 0.7 | 0.7-0.9 |
| Stone | (0.5, 0.48, 0.45) | 0.0 | 0.8-0.95 |
| Leather | (0.35, 0.2, 0.1) | 0.0 | 0.5-0.7 |
| Fabric | (varies) | 0.0 | 0.8-1.0 |
| Plastic | (varies) | 0.0 | 0.3-0.5 |
| Glass | (0.95, 0.95, 0.95) | 0.0 | 0.0-0.1 |
