"""Fold bone-parented rigid parts into the skinned mesh, weighted 100% to their bone.

    blender --background --factory-startup --python-exit-code 1 --python bind_rigid_parts.py -- in.glb out.glb

Eyes, helmets, props held in a hand often hang off a bone by parenting instead of
skin weights. They move fine in Blender, but a tool that reads skin weights only drops
them: UniMate's preprocessing kept a Quaternius dragon's body and left its eyes floating
where the head had been. Joined into the skinned mesh with one vertex group named
after their parent bone, they follow the same bone through any such pipeline.
"""
import sys
import bpy

src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
moved = 0
for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    skinned = [o for o in bpy.data.objects if o.type == 'MESH'
               and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)]
    rigid = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm and o.parent_type == 'BONE']
    if not skinned or not rigid:
        continue
    body = max(skinned, key=lambda o: len(o.data.vertices))
    # Skinned vertices are stored in the bind (rest) pose and deformed from there, so read
    # the part where it sits at rest — read posed, the bone's pose is applied twice
    # (measured: a dragon's eyes landed 1.5 m off its face).
    arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
    for part in rigid:
        bone, name = part.parent_bone, part.name
        mw = part.matrix_world.copy()
        part.parent = None; part.matrix_world = mw
        bpy.ops.object.select_all(action='DESELECT'); part.select_set(True)
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        part.vertex_groups.new(name=bone).add(list(range(len(part.data.vertices))), 1.0, 'REPLACE')
        # the body's world transform is what the joined vertices are expressed in
        part.data.transform(body.matrix_world.inverted()); part.matrix_world = body.matrix_world
        bpy.ops.object.select_all(action='DESELECT'); part.select_set(True); body.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()
        moved += 1
        print(f"bind_rigid_parts: {name} -> bone {bone}")
    arm.data.pose_position = 'POSE'
# posture, for routing (references/animation.md): forepaws at ground height = quadruped
for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
    z = {b.name.lower(): (arm.matrix_world @ b.tail_local).z for b in arm.data.bones}
    top, low = max(z.values()), min(z.values())
    h = lambda v: (v - low) / ((top - low) or 1)
    fore = [h(v) for n, v in z.items() if any(k in n for k in ("hand", "forearm", "frontlowerleg", "front_lower", "fingers"))]
    hind = [h(v) for n, v in z.items() if any(k in n for k in ("foot", "feet", "toe", "backlowerleg", "back_lower"))]
    # Measured on six rigs: forelimb ends at 23-34% of the height for three quadrupeds whose
    # leg bones stop short of the ground, 82% for a T-posed human. Quadruped when the
    # forelimbs end in the lower half, level with the hind limbs.
    if fore and hind and min(fore) < 0.5 and abs(min(fore) - min(hind)) < 0.2:
        print("bind_rigid_parts: posture quadruped")
    arm.data.pose_position = 'POSE'
bpy.ops.export_scene.gltf(filepath=dst, export_animations=True)
print(f"bind_rigid_parts: {moved} rigid part(s) folded into the skin")
