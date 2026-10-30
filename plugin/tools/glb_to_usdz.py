"""A GLB to a USDZ for AR Quick Look, in Blender, headless and deterministic.

    blender -b --factory-startup --python tools/glb_to_usdz.py -- in.glb out.usdz [--size 1024]

kiln's USDZ recipe (references/export-targets.md § USDZ): materials and their textures
in the archive, Y up / -Z forward (ARKit's), the animation kept (the active clip; Quick
Look plays one, in a loop), no world light. And one thing glTF does and USD cannot
carry to Quick Look: colours held in the vertices (COLOR_0). Quick Look shows only the
material, so a mesh coloured that way comes out white — its colours are baked into a
texture on its UVs first, multiplied into the material's base colour.

Studio runs it for the phone page (a finish's USDZ, made from the GLB of that finish).
Prints `USDZ <path>` on success; exits 1 with the reason otherwise.
"""
import sys

import bpy


def args() -> tuple[str, str, int]:
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) < 2:
        print("usage: -- in.glb out.usdz [--size N]")
        sys.exit(1)
    size = int(a[a.index("--size") + 1]) if "--size" in a else 1024
    return a[0], a[1], size


def bake_vertex_colours(size: int) -> int:
    """Each mesh with a colour attribute and UVs: its colours to an image, into its materials."""
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.data.color_attributes and o.data.uv_layers]
    if not meshes:
        return 0
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 1
    sc.cycles.device = "CPU"
    done = 0
    for o in meshes:
        attr = o.data.color_attributes.active_color or o.data.color_attributes[0]
        img = bpy.data.images.new(f"T_{o.name}_VertexColour", size, size)
        img.colorspace_settings.name = "sRGB"
        # Bake: each material, for a moment, emits the colour attribute; the image node active.
        saved = []
        for slot in o.material_slots:
            m = slot.material
            if not m:
                continue
            nt = m.node_tree
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            col = nt.nodes.new("ShaderNodeVertexColor")
            col.layer_name = attr.name
            emit = nt.nodes.new("ShaderNodeEmission")
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            nt.nodes.active = tex
            old = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None
            nt.links.new(col.outputs["Color"], emit.inputs["Color"])
            nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
            saved.append((m, out, old, col, emit, tex))
        for x in bpy.data.objects:
            x.select_set(x == o)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        img.pack()
        # Put each material back, its base colour now times the baked image.
        for m, out, old, col, emit, tex in saved:
            nt = m.node_tree
            nt.nodes.remove(col)
            nt.nodes.remove(emit)
            if old:
                nt.links.new(old, out.inputs["Surface"])
            # Where the material reads the vertex colours (glTF's importer wires them in), it
            # reads the baked image instead.
            readers = [n for n in nt.nodes if n.type in ("VERTEX_COLOR", "ATTRIBUTE") and n is not col]
            if readers:
                for n in readers:
                    for link in list(n.outputs[0].links):
                        nt.links.new(tex.outputs["Color"], link.to_socket)
                    nt.nodes.remove(n)
                continue
            bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf is None:
                continue
            base = bsdf.inputs["Base Color"]
            if base.links:   # already textured, and not by the vertex colours: left as it is
                nt.nodes.remove(tex)
                continue
            r, g, b, _ = base.default_value
            if (r, g, b) != (1.0, 1.0, 1.0):
                mul = nt.nodes.new("ShaderNodeMix")
                mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
                mul.inputs[0].default_value = 1.0
                mul.inputs[6].default_value = base.default_value
                nt.links.new(tex.outputs["Color"], mul.inputs[7])
                nt.links.new(mul.outputs[2], base)
            else:
                nt.links.new(tex.outputs["Color"], base)
        done += 1
    return done


def main() -> None:
    src, out, size = args()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.import_scene.gltf(filepath=src)
    baked = bake_vertex_colours(size)
    # USDZ holds PNG and JPEG only: a WebP (a web GLB's) goes in as PNG.
    import tempfile
    tmp = tempfile.mkdtemp()
    for img in list(bpy.data.images):
        if img.source == "FILE" and img.file_format not in ("PNG", "JPEG") and img.size[0]:   # size: loads it
            path = f"{tmp}/{bpy.path.clean_name(img.name)}.png"
            img.filepath_raw, img.file_format = path, "PNG"
            img.save()
            png = bpy.data.images.load(path)
            png.colorspace_settings.name = img.colorspace_settings.name
            img.user_remap(png)   # the materials now read the PNG
            png.name = img.name
    sc = bpy.context.scene
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE" and o.animation_data and o.animation_data.action), None)
    if arm:
        a = arm.animation_data.action
        sc.frame_start, sc.frame_end = int(a.frame_range[0]), int(a.frame_range[1])
    for o in bpy.data.objects:
        o.select_set(True)
    bpy.ops.wm.usd_export(filepath=out, selected_objects_only=True, export_materials=True, export_textures_mode="NEW",
                          relative_paths=True, convert_world_material=False, export_animation=True,
                          convert_orientation=True, export_global_forward_selection="NEGATIVE_Z",
                          export_global_up_selection="Y")
    print(f"USDZ {out} (vertex colours baked on {baked} mesh{'es' if baked != 1 else ''})", flush=True)


try:
    main()
except Exception as e:   # one line for the caller
    print(f"FAILED {e!r}", flush=True)
    sys.exit(1)
