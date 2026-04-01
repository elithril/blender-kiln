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

### 11. Blender 5.x — Bone Collections (remplace Bone Layers)

Depuis Blender 4.0+, les bone layers (32 slots numériques) sont remplacés par les **Bone Collections** (nommées, hiérarchiques, illimitées).

```python
import bpy

armature = bpy.data.armatures['SK_Character']

# Créer des collections de bones
deform_col = armature.collections.new(name="DEF")
ctrl_col = armature.collections.new(name="CTRL") 
mech_col = armature.collections.new(name="MCH")

# Assigner des bones aux collections (en Edit Mode)
bpy.ops.object.mode_set(mode='EDIT')
for bone in armature.edit_bones:
    if bone.name.startswith("DEF_"):
        deform_col.assign(bone)
    elif bone.name.startswith("CTRL_"):
        ctrl_col.assign(bone)
    elif bone.name.startswith("MCH_"):
        mech_col.assign(bone)
bpy.ops.object.mode_set(mode='OBJECT')

# Masquer les bones mécanisme dans le viewport
mech_col.is_visible = False
```

**Avantage :** Un bone peut appartenir à plusieurs collections. Permet un contrôle fin de la visibilité et de la sélection pour les animateurs.

### 12. Blender 5.x — Layered Actions (Action Slots)

Blender 4.4+ introduit les **Layered Actions** avec un système de slots et layers :

```python
import bpy

# Créer une action avec slots
action = bpy.data.actions.new(name="A_Character_Walk")

# Les slots permettent de lier une action à plusieurs objets
# avec des channels différents par slot
armature_obj = bpy.data.objects['SK_Character']
armature_obj.animation_data_create()
armature_obj.animation_data.action = action
```

> ⚠️ L'API Layered Actions évolue rapidement entre Blender 4.4 et 5.x. Vérifier la version Blender avant d'utiliser ces patterns.

### 13. Mode Switching Gotchas

Pièges courants lors des changements de mode (critique pour le scripting de rigs) :

| Piège | Détail | Solution |
|---|---|---|
| Edit bones ≠ Pose bones | `armature.edit_bones` (Edit Mode) vs `obj.pose.bones` (Pose Mode). Propriétés différentes. | Toujours vérifier le mode actif |
| Bone roll en Edit Mode only | `edit_bone.roll` n'existe qu'en Edit Mode | Switcher en Edit avant de modifier les rolls |
| Constraints en Pose Mode | Les constraints se configurent sur `pose_bone.constraints`, pas sur edit_bone | Switcher en Pose Mode |
| Shape keys en Object Mode | `keyframe_insert` sur les shape keys requiert Object Mode | Vérifier le mode avant keyframing |
| Données perdues au switch | Certaines opérations pending sont perdues si on switch sans `update()` | `bpy.context.view_layer.update()` après modifications |

### 10. Corrective Blend Shapes (Corrective Smooth)

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

| # | Anti-Pattern | Conséquence | Solution |
|---|---|---|---|
| 1 | Orientations joints aléatoires | IK imprévisible, retargeting cassé | Convention d'axes cohérente sur toute la chaîne |
| 2 | Pas de twist bones | Candy wrapper (mesh collapse) | 1-2 twist bones par segment bras/jambe |
| 3 | Deform bones = control bones | Animateurs cassent le rig | Architecture 3 layers (DEF/CTRL/MCH) |
| 4 | Root bone au niveau des hanches | Calculs au sol cassés dans les engines | Root à (0,0,0) sur le ground plane |
| 5 | Modifier vertex order après shape keys | Shape keys silencieusement cassés | Finaliser le mesh AVANT les shape keys |
| 6 | Plus de 4 influences/vertex (mobile) | Artefacts sur GPU mobile | Limiter et normaliser les weights |
| 7 | Scale ≠ 1 sur l'armature | Animations déformées à l'export | Apply scale avant de rigger |
| 8 | Bones sans deform activé qui influencent le mesh | Vertices orphelins | Vérifier le flag deform sur chaque bone |
| 9 | Noms de bones avec espaces/accents | Problèmes d'export FBX/GLTF | Convention `CamelCase` ou `snake_case` |
| 10 | Skip de la normalisation des weights | Vertices qui "flottent" | `normalize_all()` après chaque passe de weight painting |

---

## Sharp Edges — Export Gotchas

### 🔴 Critique

**FBX Bind Pose :** Blender n'exporte PAS de bind pose explicite en FBX. Unity/Unreal recalculent depuis la rest pose. Si la rest pose Blender ≠ T-pose → déformation incorrecte dans l'engine.
- **Fix :** Toujours appliquer la pose comme rest pose AVANT export : `bpy.ops.pose.armature_apply(selected=False)`

**Weight Normalization Culling :** Certains engines (Unity) éliminent silencieusement les influences < 0.01. Des vertices avec beaucoup de micro-influences perdent du poids total.
- **Fix :** Limiter à 4 influences max, normaliser, puis re-vérifier.

**Joint Limit Export :** Les joint limits Blender (`ik_min_x`, `ik_max_x`) ne s'exportent PAS en GLTF. Seulement partiellement en FBX.
- **Fix :** Re-créer les limites dans l'engine cible.

### 🟠 Important

**Mobile Bone Limits :** Les GPUs mobiles supportent typiquement **75 bones max** par draw call (uniform buffer limit). Au-delà → split automatique du mesh = draw calls supplémentaires = baisse de perf.
- **Budget recommandé :** 50-65 bones pour mobile, 150+ pour desktop.

**Shoulder Deformation :** Le clavicle seul ne suffit pas. Ajouter un bone `Shoulder` entre clavicle et upper arm, avec un driver partiel (30-50% de la rotation du upper arm).

**Candy Wrapper :** Se produit quand un segment (forearm) tourne > 90° sans twist bones. Visible surtout sur les forearms et les thighs.
- **Fix :** Twist bones (voir pattern #2 ci-dessus).

**Humanoid vs Generic (Unity) :** 
- **Humanoid** : retargeting automatique Mixamo/mocap, mais force la structure de bones Unity. Requiert des noms de bones mappables.
- **Generic** : conserve le rig exact, pas de retargeting auto. Mieux pour les créatures non-humanoïdes.

### 🟡 Attention

**FBX Axis Conversion :** Blender = Z-up, Unity = Y-up. L'exporteur FBX compense, mais peut créer un nœud racine supplémentaire avec rotation -90°. Vérifier dans l'engine.

**Blend Shape Vertex Order :** Si le mesh est modifié APRÈS création des shape keys (merge, delete vertices), les indices de vertex changent → shape keys déformés aléatoirement. **Toujours finaliser la géométrie avant les shape keys.**

**Animation Compression :** Les engines compressent les animations à l'import. Vérifier que les courbes critiques (root motion, IK targets) ne sont pas sur-compressées. Réduire la tolérance pour ces tracks.

**Scale dans le Skeleton :** Ne JAMAIS animer le scale des bones sauf pour des effets spéciaux (squash & stretch). Le scale propagé dans la hiérarchie cause des artefacts de shearing.

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
            warnings.append(f"🔴 Mesh '{child.name}': {unweighted} vertices sans weight. Resteront en place.")
        
        # Check for shape keys + non-applied modifiers
        if child.data.shape_keys and len(child.modifiers) > 0:
            mod_names = [m.name for m in child.modifiers if m.type not in ('ARMATURE', 'CORRECTIVE_SMOOTH')]
            if mod_names:
                warnings.append(f"🟡 Mesh '{child.name}': shape keys + modifiers non-appliqués ({mod_names}). Appliquer les modifiers d'abord.")
    
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
| **Mixamo** | Web service (free) | Humanoïdes standard | Upload mesh, auto-rig + 2500 animations. Requiert compte Adobe. |
| **Rigify** | Blender addon (built-in) | Tous types | Meta-rig configurable, production-ready. Plus de contrôle que Mixamo. |
| **AccuRIG** (Reallusion) | Desktop app (free) | Humanoïdes détaillés | Meilleur résultat que Mixamo sur les mains/doigts. |
| **Auto-Rig Pro** | Blender addon (payé ~$40) | Production | Smart retopo + rig + export game-ready. |

## Retopology Tools

| Tool | Type | Best for |
|---|---|---|
| **Quad Remesher** | Blender addon (payé) | Meilleure qualité auto-retopo |
| **InstantMeshes** | Standalone (gratuit) | Rapide, open-source |
| **Blender Remesh** | Built-in | Prototypage rapide (voxel remesh) |
| **OpenSubdiv** | Built-in | Subdivision pour low-poly → high-poly |

---

## Kiln Integration

### Dans le pipeline principal

Phase [5] CLEANUP pour les characters :
1. Standard cleanup (merge doubles, normals, transforms)
2. Vérifier T-pose si rigging prévu
3. Retopology si mesh AI (typiquement trop dense pour rigging)
4. `validate_character_rig()` si armature présente

### Export spécifique characters

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
