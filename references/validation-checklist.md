# Validation Checklist Reference

> Systematic QA after import. Execute via `execute_blender_code`.

---

## Geometry

### Merge by Distance
```python
import bpy
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
result = bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.object.mode_set(mode='OBJECT')
# Log: "{n} vertices merged"
```

### Recalculate Normals
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
```

Verify visually: Viewport Overlays → Face Orientation. Blue = correct (outward), Red = flipped.

### Remove Loose
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.mesh.select_loose()
bpy.ops.mesh.delete(type='VERT')
bpy.ops.object.mode_set(mode='OBJECT')
```

### Degenerate Dissolve
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Check Manifold
```python
import bmesh
obj = bpy.context.active_object
bm = bmesh.new()
bm.from_mesh(obj.data)
non_manifold = [e for e in bm.edges if not e.is_manifold]
bm.free()
# Log: "{len(non_manifold)} non-manifold edges"
# Alert if > 0 and asset needs to be watertight
```

---

## Transforms

### Apply All Transforms
```python
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```
Result: location=(0,0,0), rotation=(0,0,0), scale=(1,1,1).

### Set Origin
```python
# Origin at center of bottom (base of object)
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
# Then adjust to bottom:
obj = bpy.context.active_object
bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
min_z = min(v.z for v in bbox)
obj.location.z -= min_z
bpy.ops.object.transform_apply(location=True)
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
```

---

## Scale Verification

**1 Blender unit = 1 meter.** Check bounding box after import:

```python
obj = bpy.context.active_object
dims = obj.dimensions
print(f"Dimensions: {dims.x:.2f} x {dims.y:.2f} x {dims.z:.2f} m")
```

| Object | Expected height |
|---|---|
| Character | ~1.75m |
| Chair | ~0.85m |
| Table | ~0.75m |
| Door | ~2.10m |

Alert if dimensions are clearly wrong (< 0.01m or > 100m).

---

## Naming

Apply naming conventions per `naming-conventions.md`:

```python
# Rename object and mesh data
obj.name = "SM_WoodenChair"
obj.data.name = "SM_WoodenChair_Mesh"
```

### Clean Orphans
```python
# Remove unused data blocks
bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
```

---

## Materials Check

```python
obj = bpy.context.active_object
# Check for empty material slots
for i, slot in enumerate(obj.material_slots):
    if slot.material is None:
        print(f"WARNING: Empty material slot at index {i}")

# Check for missing textures
for mat in bpy.data.materials:
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image is None:
                print(f"WARNING: Missing texture in material {mat.name}")
```

---

## Material Export Audit (pre-export GLTF)

**Run BEFORE any GLTF export.** Detects procedural nodes that will be **lost** on export.

```python
import bpy, json

def audit_materials_for_export():
    """Audit materials for GLTF export compatibility. Run before export."""
    PROCEDURAL_NODES = {'TEX_NOISE', 'TEX_VORONOI', 'TEX_WAVE', 'TEX_MUSGRAVE'}
    results = []
    
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        info = {"name": mat.name, "warnings": []}
        has_principled = False
        
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                has_principled = True
            
            if node.type in PROCEDURAL_NODES:
                info["warnings"].append(
                    f"Procedural '{node.name}' ({node.type}) → LOST on GLTF export. Bake to texture first."
                )
            
            if node.type == 'VALTORGB':  # Color Ramp
                info["warnings"].append(
                    f"Color Ramp '{node.name}' → remapping LOST on export. Roughness/metallic will be flat."
                )
            
            if node.type == 'TEX_IMAGE' and node.image:
                w, h = node.image.size[0], node.image.size[1]
                if w > 2048 or h > 2048:
                    info["warnings"].append(
                        f"Large texture: {node.image.filepath} ({w}x{h}). Consider resizing to 1024/2048."
                    )
        
        if not has_principled:
            info["warnings"].append("No Principled BSDF → unpredictable export result.")
        
        if info["warnings"]:
            results.append(info)
    
    return results

audit = audit_materials_for_export()
if audit:
    print("⚠️ MATERIAL PRE-EXPORT AUDIT:")
    for mat in audit:
        print(f"\n  [{mat['name']}]:")
        for w in mat["warnings"]:
            print(f"    - {w}")
else:
    print("✅ All materials are GLTF compatible.")
```

**Nodes lost on GLTF export:**

| Blender Node | What is lost | Solution |
|---|---|---|
| Noise/Voronoi/Wave/Musgrave → input | Entire procedural chain | Bake to image texture |
| Color Ramp on roughness/metallic | Value remapping | Bake or manual values |
| Procedural Bump (Noise → Bump) | Bump detail | Bake normal map |
| Mix Shader with complex factor | Blend logic | Simplify to single BSDF |

**What IS exported:** flat roughness/metallic values, image textures (without Color Ramp), baked normal maps, PBR texture sets (baseColor, metallicRoughness, normal).

---

## Poly Count Check

```python
obj = bpy.context.active_object
face_count = len(obj.data.polygons)
# Compare against tier range
# If > 50% above range → propose decimate (ALWAYS interactive)
```

### Decimate (if needed)
```python
mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.ratio = target / current  # approximate
# SHOW before/after screenshot
# WAIT for user approval before applying
bpy.ops.object.modifier_apply(modifier="Decimate")
```

---

## Execution Order

1. Merge by Distance
2. Recalculate Normals
3. Remove Loose
4. Degenerate Dissolve
5. Apply All Transforms
6. Set Origin (center of base)
7. Scale verification
8. Naming conventions
9. Clean orphans
10. Materials check
11. Poly count check → decimate if needed (interactive)
12. `get_viewport_screenshot()` → final validation

**Auto mode:** steps 1-10 automatic, step 11 always interactive.
**Guided mode:** validate after each step.
