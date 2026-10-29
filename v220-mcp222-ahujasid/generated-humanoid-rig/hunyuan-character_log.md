# Hunyuan Character — Production Log

## Config
- Type: character (rig for animation) · Target: glTF · Tier: balanced · Style: stylized · Mode: auto · Storage: compact

## Reference Image
- none — the source mesh is the input ("keep its shape").
- Visual comparison: N/A (geometry unchanged, vertex for vertex).

## Source
- Method: user-supplied mesh, Hunyuan3D-2 output (trimesh-written GLB)
- File: refs/hunyuan/hunyuan_demo_1.glb (720.8 kB) → copied as hunyuan-character_original.glb
- No marketplace, no new AI generation.

## Pipeline
- Scene: removed the factory default Cube (untouched startup scene, no .blend loaded). Also removed the importer's `world` empty wrapper.
- Import: 19,996 verts / 40,000 tris, one closed manifold island, bbox 0.734 × 0.593 × 1.084 m. No normals, UVs, materials or textures in the source.
- Scale: kept at 1.084 m tall (Hunyuan normalises to ~1 unit). Assumed a chibi child figure about 1.1 m tall. Rescale the rig and mesh together if another size is needed.
- Cleanup: transforms applied · weld at 1e-4 m merged 0 verts (already welded) · normals recalculated (volume +0.091 m³, outward) · 0 loose, 0 degenerate, 0 fused (>2 faces) edges, 0 open edges · base centred on the origin (min z = 0).
- Shading: smooth shading enabled. The source GLB had no NORMAL attribute, so viewers rendered it faceted, and a faceted export would triple the vertex count. Geometry was not touched.
- Poly count: 40,000 tris against 8–20K for balanced. That is exactly 2× the top of the range, not past it, so nothing was decimated (and the brief says to keep the shape).
- Pose (rule 13): left arm hangs at ≈ -62° (shoulder → hand), close to an I-pose. The right arm is akimbo and **the hand is fused into the hip** (single connected island). Not converted to T-pose: the conversion would require cutting the hand off the hip, which changes the shape. Rigged in the as-generated pose.
- Rig selection (rule 26): 19,996 verts → table says Rigify human (160 deform). Chose the **Rigify basic human** (+2 pigtail bones, breast bones removed) because the mesh has no separate fingers and no face topology (no mouth or eyelids) for finger or face bones to drive. 35 deform bones → 571 verts/bone. 0 dead deform bones.
- Rig: RIG_HunyuanCharacter (Rigify control rig, 222 bones, IK/FK arms and legs; IK is the default). Metarig kept hidden in the .blend for regeneration.
- Skinning: bone-heat automatic weights. Then: the pigtail bones were limited to the pigtails (|x| > 0.215–0.255 m falloff, the rest given back to the head); right hand/forearm weights were faded off the torso surface (hip/pelvis.R, spine.001 take them); clean < 0.01; max 4 influences; normalised. 0 unweighted verts.
- Pose test: thighs ±30–45°, knee 50°, both arms, head, neck, chest, pigtails. Deformation holds except at the fused right hand. Moving that arm more than ~20–30° away from the hip stretches the hip/hand bridge (the bulk of the 448 edges stretched > 2× or < 0.5× were there).
- Texturing: skipped (out of scope for this brief). Single neutral material M_Clay_Base (Principled, flat values) assigned. The mesh has no UVs.
- Material audit: M_Clay_Base OK (Principled, no procedural nodes).
- Export: GLB, export_def_bones=True (35 joints, no neutral_bone), export_apply=False, no animation → 1.13 MB.
- Optimize: gltf-transform draco → 192.1 kB (−83%). No geometry change. Needs a Draco decoder on the client. No textures to resize.
- Verification: re-imported the final GLB: 35 bones, 19,996 verts, same bbox; posing 4 DEF bones moved 13,776 verts.

## Licenses
- Source mesh: Hunyuan3D-2 output supplied by the user. Tencent Hunyuan3D-2 community licence applies (excludes EU/UK/South Korea territories).
- Rigify: part of Blender (GPL). The generated rig data carries no licence restriction.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
