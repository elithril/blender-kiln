# Characters Reference (Phase 2)

> Rigging, skinning, animation, retopology, export. Patterns, anti-patterns, and sharp edges.

---

## Current State in Kiln

Character **generation** works via the main pipeline (AI or scripted). T-pose is enforced by Iron Rule #13.

**Implemented:** T-pose generation, basic cleanup (`SK_` prefix), texturing (approximate).
**Phase 2 scope:** retopology, rigging, skinning, animation, blend shapes, character-specific texturing.

---

## T-Pose Requirements

When a character is flagged for rigging:
- Arms extended horizontally, palms facing down
- Legs slightly apart (~shoulder width)
- Neutral face expression
- Fingers slightly spread (not clenched)
- Thumbs pointing forward

**Why T-pose over A-pose:** T-pose is more universally compatible with auto-riggers (Mixamo, Rigify, AccuRIG). A-pose gives better shoulder deformation but requires manual setup.

---

## Rigging Patterns

### 1. Joint Orientation

**Rule:** All joints in a chain must have a consistent local axis pointing down the bone (typically X or Y), with the secondary axis aligned to the bend plane.

```python
import bpy
from mathutils import Vector

# Verify joint orientation consistency
armature = bpy.data.objects['SK_Character'].data
for bone in armature.edit_bones:
    if bone.parent:
        # Bone axis should point from head to tail
        direction = (bone.tail - bone.head).normalized()
        print(f"{bone.name}: axis={direction}, roll={bone.roll:.2f}")
```

**Anti-pattern:** Random joint orientations → unpredictable rotation values, IK solving issues, animation retargeting failures.

### 2. Twist Bones

**Rule:** Add twist bones to forearms and upper legs to distribute twist deformation. Minimum 1 twist bone per segment, 2 for high-quality.

```
Arm chain: Shoulder → UpperArm → UpperArm_Twist → ForeArm → ForeArm_Twist → Hand
Leg chain: Thigh → Thigh_Twist → Shin → Shin_Twist → Foot
```

**Why:** Without twist bones, rotating a hand 180° creates the "candy wrapper" effect — the mesh collapses between shoulder and wrist.

### 3. Control Rig Architecture

**Three-layer system:**

| Layer | Purpose | Naming |
|---|---|---|
| **Deform bones** | Actually drive the mesh (vertex groups) | `DEF_Spine`, `DEF_UpperArm_L` |
| **Control bones** | Animator interacts with these | `CTRL_Spine`, `CTRL_Hand_L` |
| **Mechanism bones** | Helpers (pole targets, twist drivers, constraints) | `MCH_ArmIK_L`, `MCH_Twist_L` |

**Anti-pattern:** Using deform bones as controls → animators break the rig, no separation of concerns.

### 4. FK/IK System

```python
# IK constraint setup pattern
import bpy

def setup_ik_chain(armature_obj, bone_name, chain_length, pole_target_name):
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    pose_bone = armature_obj.pose.bones[bone_name]
    ik = pose_bone.constraints.new('IK')
    ik.chain_count = chain_length
    
    if pole_target_name:
        ik.pole_target = armature_obj
        ik.pole_subtarget = pole_target_name
        ik.pole_angle = 0  # Adjust per limb
    
    bpy.ops.object.mode_set(mode='OBJECT')
```

**FK/IK switch:** Use a custom property on the control bone (0.0 = FK, 1.0 = IK) with driven constraints.

### 5. Facial Rigging (Blend Shapes / Shape Keys)

**Minimum set for basic facial animation (ARKit compatible):**

| Shape Key | Description |
|---|---|
| `Basis` | Neutral face (always index 0) |
| `jawOpen` | Mouth open |
| `mouthSmile_L` / `_R` | Smile left/right |
| `mouthFrown_L` / `_R` | Frown left/right |
| `eyeBlink_L` / `_R` | Eye close left/right |
| `browUp_L` / `_R` | Eyebrow raise |
| `browDown_L` / `_R` | Eyebrow lower |

```python
# Create shape key
obj = bpy.data.objects['SK_Character']
obj.shape_key_add(name='Basis')  # Must be first
sk = obj.shape_key_add(name='jawOpen')
# Modify sk.data[vertex_index].co for each affected vertex
```

**Anti-pattern:** Modifying vertex order after creating shape keys → all blend shapes break silently.

### 6. Weight Painting

```python
# Auto-weights from armature
bpy.ops.object.select_all(action='DESELECT')
mesh_obj = bpy.data.objects['SK_Character']
armature_obj = bpy.data.objects['SK_Character_Armature']
mesh_obj.select_set(True)
armature_obj.select_set(True)
bpy.context.view_layer.objects.active = armature_obj
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
```

**Post auto-weights cleanup checklist:**
1. Check for vertices with zero total weight (will stay in place) 
2. Check for vertices weighted to wrong bones (e.g., leg vertices on spine)
3. Normalize all weights (`bpy.ops.object.vertex_group_normalize_all()`)
4. Limit total influences per vertex (4 max for mobile, 8 for desktop)

### 7. Spine Deformation

**Minimum 3 spine bones** for believable bending: `DEF_Spine`, `DEF_Spine1`, `DEF_Spine2`, `DEF_Chest`.

**Preserve volume:** Use Corrective Smooth modifier or driven blend shapes on extreme poses.

### 8. Root Motion

**Root bone placement:**
- Name: `Root` (always)
- Position: origin (0, 0, 0), on the ground plane
- Orientation: aligned to world axes
- Purpose: carries all locomotion translation/rotation

**Anti-pattern:** Root bone at hip height → ground-relative calculations break in game engines.

### 9. Animation Retargeting

For Mixamo → custom rig retargeting:
1. Ensure bone names follow a mappable convention
2. Match rest poses (T-pose to T-pose)
3. Use Blender's bone mapping or a retargeting addon

### 10. Blender 5.x — Bone Collections (replaces Bone Layers)

Since Blender 4.0+, bone layers (32 numeric slots) have been replaced by **Bone Collections** (named, hierarchical, unlimited).

```python
import bpy

armature = bpy.data.armatures['SK_Character']

# Create bone collections
deform_col = armature.collections.new(name="DEF")
ctrl_col = armature.collections.new(name="CTRL") 
mech_col = armature.collections.new(name="MCH")

# Assign bones to collections (in Edit Mode)
bpy.ops.object.mode_set(mode='EDIT')
for bone in armature.edit_bones:
    if bone.name.startswith("DEF_"):
        deform_col.assign(bone)
    elif bone.name.startswith("CTRL_"):
        ctrl_col.assign(bone)
    elif bone.name.startswith("MCH_"):
        mech_col.assign(bone)
bpy.ops.object.mode_set(mode='OBJECT')

# Hide mechanism bones in the viewport
mech_col.is_visible = False
```

**Advantage:** A bone can belong to multiple collections. Allows fine-grained control over visibility and selection for animators.

### 11. Blender 5.x — Layered Actions (Action Slots)

Blender 4.4+ introduces **Layered Actions** with a slots and layers system:

```python
import bpy

# Create an action with slots
action = bpy.data.actions.new(name="A_Character_Walk")

# Slots allow linking an action to multiple objects
# with different channels per slot
armature_obj = bpy.data.objects['SK_Character']
armature_obj.animation_data_create()
armature_obj.animation_data.action = action
```

> ⚠️ The Layered Actions API is evolving rapidly between Blender 4.4 and 5.x. Check the Blender version before using these patterns.

### 12. Mode Switching Gotchas

Common pitfalls when switching modes (critical for rig scripting):

| Pitfall | Detail | Solution |
|---|---|---|
| Edit bones ≠ Pose bones | `armature.edit_bones` (Edit Mode) vs `obj.pose.bones` (Pose Mode). Different properties. | Always check the active mode |
| Bone roll in Edit Mode only | `edit_bone.roll` only exists in Edit Mode | Switch to Edit before modifying rolls |
| Constraints in Pose Mode | Constraints are configured on `pose_bone.constraints`, not on edit_bone | Switch to Pose Mode |
| Shape keys in Object Mode | `keyframe_insert` on shape keys requires Object Mode | Check the mode before keyframing |
| Data lost on switch | Some pending operations are lost if you switch without `update()` | `bpy.context.view_layer.update()` after modifications |

### 13. Corrective Blend Shapes (Corrective Smooth)

Driven shape keys that activate at extreme joint angles to fix deformation artifacts:

```python
# Add driver: shape key value driven by bone rotation
sk = obj.data.shape_keys.key_blocks['shoulder_corrective_L']
driver = sk.driver_add('value').driver
driver.type = 'SCRIPTED'
var = driver.variables.new()
var.name = 'rot'
var.type = 'TRANSFORMS'
var.targets[0].id = armature_obj
var.targets[0].bone_target = 'DEF_UpperArm_L'
var.targets[0].transform_type = 'ROT_X'
driver.expression = 'max(0, rot - 0.5) * 2'  # Activates past 30°
```

---

## Anti-Patterns

| # | Anti-Pattern | Consequence | Solution |
|---|---|---|---|
| 1 | Random joint orientations | Unpredictable IK, broken retargeting | Consistent axis convention across the entire chain |
| 2 | No twist bones | Candy wrapper (mesh collapse) | 1-2 twist bones per arm/leg segment |
| 3 | Deform bones = control bones | Animators break the rig | 3-layer architecture (DEF/CTRL/MCH) |
| 4 | Root bone at hip level | Ground calculations broken in engines | Root at (0,0,0) on the ground plane |
| 5 | Modifying vertex order after shape keys | Shape keys silently broken | Finalize the mesh BEFORE shape keys |
| 6 | More than 4 influences/vertex (mobile) | Artifacts on mobile GPU | Limit and normalize weights |
| 7 | Scale ≠ 1 on the armature | Deformed animations on export | Apply scale before rigging |
| 8 | Bones without deform enabled that influence the mesh | Orphan vertices | Check the deform flag on each bone |
| 9 | Bone names with spaces/accents | FBX/GLTF export issues | `CamelCase` or `snake_case` convention |
| 10 | Skipping weight normalization | Vertices that "float" | `normalize_all()` after each weight painting pass |

---

## Sharp Edges — Export Gotchas

### 🔴 Critique

**FBX Bind Pose:** Blender does NOT export an explicit bind pose in FBX. Unity/Unreal recalculate from the rest pose. If the Blender rest pose ≠ T-pose, deformation will be incorrect in the engine.
- **Fix:** Always apply the pose as rest pose BEFORE export: `bpy.ops.pose.armature_apply(selected=False)`

**Weight Normalization Culling:** Some engines (Unity) silently discard influences < 0.01. Vertices with many micro-influences lose total weight.
- **Fix:** Limit to 4 max influences, normalize, then re-check.

**Joint Limit Export:** Blender joint limits (`ik_min_x`, `ik_max_x`) are NOT exported in GLTF. Only partially in FBX.
- **Fix:** Recreate the limits in the target engine.

### 🟠 Important

**Mobile Bone Limits:** Mobile GPUs typically support **75 bones max** per draw call (uniform buffer limit). Beyond that, the mesh is automatically split = extra draw calls = performance drop.
- **Recommended budget:** 50-65 bones for mobile, 150+ for desktop.

**Shoulder Deformation:** The clavicle alone is not enough. Add a `Shoulder` bone between clavicle and upper arm, with a partial driver (30-50% of the upper arm rotation).

**Candy Wrapper:** Occurs when a segment (forearm) rotates > 90° without twist bones. Most visible on forearms and thighs.
- **Fix:** Twist bones (see pattern #2 above).

**Humanoid vs Generic (Unity):** 
- **Humanoid**: automatic Mixamo/mocap retargeting, but forces Unity's bone structure. Requires mappable bone names.
- **Generic**: preserves the exact rig, no auto retargeting. Better for non-humanoid creatures.

### 🟡 Attention

**FBX Axis Conversion:** Blender = Z-up, Unity = Y-up. The FBX exporter compensates, but may create an extra root node with -90° rotation. Verify in the engine.

**Blend Shape Vertex Order:** If the mesh is modified AFTER shape key creation (merge, delete vertices), vertex indices change, resulting in randomly deformed shape keys. **Always finalize geometry before shape keys.**

**Animation Compression:** Engines compress animations on import. Verify that critical curves (root motion, IK targets) are not over-compressed. Reduce tolerance for these tracks.

**Scale in the Skeleton:** NEVER animate bone scale except for special effects (squash & stretch). Scale propagated through the hierarchy causes shearing artifacts.

---

## Validation Script

```python
import bpy

def validate_character_rig(armature_obj):
    """Run before export. Returns list of warnings."""
    warnings = []
    armature = armature_obj.data
    
    # Check scale
    if any(abs(s - 1.0) > 0.001 for s in armature_obj.scale):
        warnings.append("🔴 Armature scale ≠ 1.0. Apply scale first.")
    
    # Check root bone
    root_bones = [b for b in armature.bones if not b.parent]
    if len(root_bones) != 1:
        warnings.append(f"🔴 Expected 1 root bone, found {len(root_bones)}: {[b.name for b in root_bones]}")
    elif root_bones[0].name != 'Root':
        warnings.append(f"🟡 Root bone named '{root_bones[0].name}', expected 'Root'.")
    
    # Count bones
    bone_count = len(armature.bones)
    if bone_count > 75:
        warnings.append(f"🟠 {bone_count} bones. Mobile limit ~75 per draw call.")
    
    # Check for bones with spaces/special chars in names
    import re
    for bone in armature.bones:
        if re.search(r'[^a-zA-Z0-9_.]', bone.name):
            warnings.append(f"🟡 Bone '{bone.name}' has special characters. May cause export issues.")
    
    # Check vertex groups on child meshes
    for child in armature_obj.children:
        if child.type != 'MESH':
            continue
        
        # Check max influences per vertex
        max_influences = 0
        for v in child.data.vertices:
            influences = len([g for g in v.groups if g.weight > 0.01])
            max_influences = max(max_influences, influences)
        if max_influences > 4:
            warnings.append(f"🟠 Mesh '{child.name}': max {max_influences} influences/vertex. Mobile max = 4.")
        
        # Check for unweighted vertices
        unweighted = sum(1 for v in child.data.vertices if len(v.groups) == 0)
        if unweighted > 0:
            warnings.append(f"🔴 Mesh '{child.name}': {unweighted} vertices without weight. Will remain in place.")
        
        # Check for shape keys + non-applied modifiers
        if child.data.shape_keys and len(child.modifiers) > 0:
            mod_names = [m.name for m in child.modifiers if m.type not in ('ARMATURE', 'CORRECTIVE_SMOOTH')]
            if mod_names:
                warnings.append(f"🟡 Mesh '{child.name}': shape keys + unapplied modifiers ({mod_names}). Apply modifiers first.")
    
    return warnings

# Usage:
# armature = bpy.data.objects['SK_Character_Armature']
# for w in validate_character_rig(armature):
#     print(w)
```

---

## Auto-Rigging Tools

| Tool | Type | Best for | Notes |
|---|---|---|---|
| **Mixamo** | Web service (free) | Standard humanoids | Upload mesh, auto-rig + 2500 animations. Requires Adobe account. |
| **Rigify** | Blender addon (built-in) | All types | Configurable meta-rig, production-ready. More control than Mixamo. |
| **AccuRIG** (Reallusion) | Desktop app (free) | Detailed humanoids | Better results than Mixamo on hands/fingers. |
| **Auto-Rig Pro** | Blender addon (paid ~$40) | Production | Smart retopo + rig + game-ready export. |

## Retopology Tools

| Tool | Type | Best for |
|---|---|---|
| **Quad Remesher** | Blender addon (paid) | Best quality auto-retopo |
| **InstantMeshes** | Standalone (free) | Fast, open-source |
| **Blender Remesh** | Built-in | Quick prototyping (voxel remesh) |
| **OpenSubdiv** | Built-in | Subdivision for low-poly to high-poly |

---

## Kiln Integration

### In the main pipeline

Phase [5] CLEANUP for characters:
1. Standard cleanup (merge doubles, normals, transforms)
2. Verify T-pose if rigging is planned
3. Retopology if AI mesh (typically too dense for rigging)
4. `validate_character_rig()` if armature is present

### Character-specific export

```python
# Character export settings (GLTF)
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_apply=False,
    export_animations=True,
    export_nla_strips=True,
    export_skins=True,         # vertex groups / skinning
    export_morph=True,         # blend shapes / shape keys
    export_draco_mesh_compression_enable=False,
)
```

```python
# Character export settings (FBX — Unity/Unreal)
bpy.ops.export_scene.fbx(
    filepath=output_path,
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',
    apply_unit_scale=True,
    bake_space_transform=True,
    use_armature_deform_only=True,  # skip helper bones (MCH_*)
    add_leaf_bones=False,           # Unity doesn't need leaf bones
    bake_anim=True,
    bake_anim_use_all_actions=True,
    path_mode='COPY',
    embed_textures=True,
)
```
