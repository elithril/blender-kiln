"""Procedural asset definitions. Each builder returns the finished mesh object."""
import bpy, bmesh, math, random
from mathutils import Vector
import studio as S


def _lathe(profile, segments, jitter=0.0, seed=0, close_bottom=True, close_top=True):
    """Revolve a [(radius, z)] profile into a mesh. Per-segment radius jitter
    gives hand-made stock a bit of irregularity without touching topology."""
    rnd = random.Random(seed)
    wob = [1.0 + rnd.uniform(-jitter, jitter) for _ in range(segments)]
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = []
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            rr = r * wob[i]
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    if close_bottom:
        bm.faces.new(list(reversed(rings[0])))
    if close_top:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("lathe")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("lathe", me)
    bpy.context.scene.collection.objects.link(o)
    return o


def barrel():
    """Staved barrel: bulged body, three iron hoops, recessed lid."""
    h, r0, bulge, segs = 0.95, 0.255, 0.40, 16
    levels = 9
    prof = []
    for i in range(levels):
        t = i / (levels - 1)
        z = t * h
        prof.append((r0 * (1.0 + bulge * math.sin(math.pi * t) ** 0.62), z))

    body = _lathe(prof, segs, jitter=0.014, seed=7, close_top=False)
    body.data.materials.append(S.mat("wood", S.WOOD, rough=0.72))
    S.bevel(body, width=0.006, segments=2, angle=25.0)

    parts = [body]
    # Four hoops, as a real barrel carries them: one at each chime, and a pair
    # flanking the bilge. A single hoop at the widest point is invisible — it
    # sits flush with the belly it is supposed to stand proud of.
    for t, hh in ((0.05, 0.05), (0.30, 0.045), (0.70, 0.045), (0.95, 0.05)):
        r = r0 * (1.0 + bulge * math.sin(math.pi * t) ** 0.62) + 0.022
        hoop = _lathe([(r, t * h - hh / 2), (r, t * h + hh / 2)], segs,
                      close_bottom=False, close_top=False)
        sol = hoop.modifiers.new('Solidify', 'SOLIDIFY')
        sol.thickness = 0.016
        sol.offset = 0.0
        S.apply_modifiers(hoop)
        hoop.data.materials.append(S.mat("iron", S.IRON, rough=0.42, metal=0.9))
        S.bevel(hoop, width=0.004, segments=2, angle=30.0)
        parts.append(hoop)

    # Recessed lid, a touch below the rim so the hoop reads as proud of it.
    lid_r = r0 - 0.004
    lid = _lathe([(lid_r, h - 0.055), (lid_r, h - 0.028)], segs)
    lid.data.materials.append(S.mat("wood_lid", S.WOOD_LT, rough=0.68))
    S.bevel(lid, width=0.005, segments=2, angle=30.0)
    parts.append(lid)

    for p in parts:
        S.apply_modifiers(p)
    o = S.join(parts, "barrel")
    return o


def _prism(sides, r, h, taper=0.12, tip=0.28):
    """A crystal shard: n-gon prism, tapered, closed with a pyramidal tip."""
    bm = bmesh.new()
    base, top = [], []
    for i in range(sides):
        a = 2.0 * math.pi * i / sides
        base.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0.0)))
        rt = r * taper
        top.append(bm.verts.new((rt * math.cos(a), rt * math.sin(a), h)))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((base[i], base[j], top[j], top[i]))
    bm.faces.new(list(reversed(base)))
    apex = bm.verts.new((0.0, 0.0, h + h * tip))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((top[i], top[j], apex))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("prism")
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("prism", me)
    bpy.context.scene.collection.objects.link(o)
    return o


def crystal():
    """Crystal cluster on a rock base: shards of graded height, emissive core."""
    rnd = random.Random(11)
    parts = []

    # More levels and stronger jitter: a 4-level lathe reads as a flat coaster,
    # not as rock the shards have broken through.
    base = _lathe([(0.34, 0.0), (0.42, 0.06), (0.45, 0.13), (0.41, 0.21),
                   (0.33, 0.28), (0.21, 0.33)],
                  11, jitter=0.22, seed=3)
    # STONE sits within a hair of the backdrop value and disappears against it.
    base.data.materials.append(S.mat("rock", S.STONE_LT, rough=0.80))
    S.bevel(base, width=0.012, segments=2, angle=28.0)
    parts.append(base)

    # Opaque on purpose: EEVEE Next does not sort blended surfaces, so alpha < 1
    # makes overlapping shards drop out of the render entirely.
    glow = S.mat("crystal", S.CRYSTAL, rough=0.18, emit=S.EMBER, emit_str=0.8, ior=1.62)
    shards = [
        # (radius, height, x, y, tilt, spin)
        (0.105, 0.62,  0.00,  0.00, 0.05, 0.0),
        (0.072, 0.42, -0.15,  0.06, 0.34, 1.1),
        (0.061, 0.34,  0.14, -0.09, 0.40, 2.3),
        (0.050, 0.25,  0.05,  0.17, 0.52, 3.6),
        (0.044, 0.19, -0.09, -0.15, 0.61, 4.9),
        (0.038, 0.14,  0.19,  0.08, 0.70, 0.6),
    ]
    for r, h, x, y, tilt, spin in shards:
        sh = _prism(rnd.choice((5, 6)), r, h)
        sh.data.materials.append(glow)
        sh.location = (x, y, 0.24)
        sh.rotation_euler = (tilt, 0.0, spin)
        S.bevel(sh, width=0.006, segments=1, angle=35.0)
        parts.append(sh)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "crystal")


BUILDERS = {}  # populated at the bottom of this module


def _box(sx, sy, sz, loc=(0, 0, 0), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = (sx, sy, sz)
    S.apply_modifiers(o)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def crate():
    """Shipping crate: panelled body inside a timber frame, iron corner plates."""
    w, bar = 0.72, 0.055
    wood = S.mat("crate_wood", S.WOOD, rough=0.74)
    trim = S.mat("crate_trim", S.WOOD_LT, rough=0.70)
    iron = S.mat("crate_iron", S.IRON, rough=0.44, metal=0.9)
    parts = []

    # Body sits slightly inside the frame so the timbers read as proud of it.
    body = _box(w - bar, w - bar, w - bar, (0, 0, w / 2))
    body.data.materials.append(wood)
    S.bevel(body, width=0.008, segments=2)
    parts.append(body)

    h = w / 2
    # Four uprights.
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = _box(bar, bar, w, (sx * (h - bar / 2), sy * (h - bar / 2), h))
            p.data.materials.append(trim)
            S.bevel(p, width=0.006, segments=2)
            parts.append(p)
    # Top and bottom rails on all four faces.
    for z in (bar / 2 + 0.012, w - bar / 2 - 0.012):
        for axis in (0, 1):
            for sgn in (-1, 1):
                loc = [0, 0, z]
                loc[1 - axis] = sgn * (h - bar / 2)
                sx = w - 2 * bar if axis == 0 else bar
                sy = bar if axis == 0 else w - 2 * bar
                p = _box(sx, sy, bar, tuple(loc))
                p.data.materials.append(trim)
                S.bevel(p, width=0.006, segments=2)
                parts.append(p)
    # Corner plates, top face only — enough to read as ironwork without clutter.
    for sx in (-1, 1):
        for sy in (-1, 1):
            # Sized to finish flush with the outer edge; any wider and they read
            # as tabs stuck on the lid rather than corner reinforcement.
            p = _box(0.12, 0.12, 0.016, (sx * (h - 0.06), sy * (h - 0.06), w - 0.006))
            p.data.materials.append(iron)
            S.bevel(p, width=0.004, segments=2)
            parts.append(p)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "crate")


def lantern():
    """Forge lantern: iron cage around an emissive core, tapered cap, ring bail."""
    iron = S.mat("lant_iron", S.IRON, rough=0.40, metal=0.92)
    brass = S.mat("lant_brass", S.BRASS, rough=0.32, metal=0.95)
    core = S.mat("lant_core", S.EMBER, rough=0.30, emit=S.EMBER, emit_str=6.0)
    parts = []

    base = _lathe([(0.20, 0.0), (0.215, 0.028), (0.185, 0.055), (0.15, 0.075)], 12)
    base.data.materials.append(iron)
    S.bevel(base, width=0.007, segments=2)
    parts.append(base)

    # Emissive core, inset so the cage reads in front of it.
    glow = _lathe([(0.085, 0.0), (0.125, 0.045), (0.125, 0.30), (0.085, 0.35)], 12)
    glow.location = (0, 0, 0.085)
    glow.data.materials.append(core)
    parts.append(glow)

    # Cage uprights on a square, plus a mid band.
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = _box(0.026, 0.026, 0.40, (sx * 0.115, sy * 0.115, 0.075 + 0.20))
            p.data.materials.append(iron)
            S.bevel(p, width=0.005, segments=2)
            parts.append(p)
    band = _lathe([(0.175, 0.0), (0.175, 0.03)], 12, close_bottom=False, close_top=False)
    sol = band.modifiers.new('Solidify', 'SOLIDIFY')
    sol.thickness = 0.014
    S.apply_modifiers(band)
    band.location = (0, 0, 0.25)
    band.data.materials.append(brass)
    S.bevel(band, width=0.004, segments=2)
    parts.append(band)

    cap = _lathe([(0.215, 0.0), (0.20, 0.035), (0.12, 0.085), (0.045, 0.115)], 12)
    cap.location = (0, 0, 0.475)
    cap.data.materials.append(iron)
    S.bevel(cap, width=0.006, segments=2)
    parts.append(cap)

    bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.011,
                                     major_segments=16, minor_segments=8,
                                     location=(0, 0, 0.635),
                                     rotation=(math.pi / 2, 0, 0))
    bail = bpy.context.object
    bail.data.materials.append(brass)
    parts.append(bail)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "lantern")


def anvil():
    """Blacksmith's anvil: splayed foot, waisted stem, face with horn and heel."""
    # A wholly-metal object has nothing to reflect in a dark studio, so it
    # collapses to black. Lighter albedo and lower metalness restore the form.
    iron = S.mat("anvil_iron", S.IRON_LT, rough=0.42, metal=0.50)
    steel = S.mat("anvil_face", S.STEEL, rough=0.22, metal=0.70)
    parts = []

    foot = _box(0.42, 0.30, 0.10, (0, 0, 0.05))
    foot.data.materials.append(iron)
    S.bevel(foot, width=0.014, segments=2)
    parts.append(foot)

    stem = _box(0.20, 0.16, 0.16, (0, 0, 0.18))
    stem.data.materials.append(iron)
    S.bevel(stem, width=0.020, segments=3)
    parts.append(stem)

    body = _box(0.56, 0.24, 0.15, (0, 0, 0.335))
    body.data.materials.append(iron)
    S.bevel(body, width=0.016, segments=3)
    parts.append(body)

    face = _box(0.50, 0.215, 0.022, (0, 0, 0.421))
    face.data.materials.append(steel)
    S.bevel(face, width=0.006, segments=2)
    parts.append(face)

    # Horn: a tapered lathe laid on its side, pointing out from the body.
    horn = _lathe([(0.105, 0.0), (0.085, 0.10), (0.055, 0.20), (0.018, 0.27)], 12)
    horn.rotation_euler = (0, math.pi / 2, 0)
    horn.location = (0.28, 0, 0.345)
    horn.data.materials.append(iron)
    S.bevel(horn, width=0.006, segments=2)
    parts.append(horn)

    heel = _box(0.10, 0.20, 0.12, (-0.31, 0, 0.345))
    heel.data.materials.append(iron)
    S.bevel(heel, width=0.012, segments=2)
    parts.append(heel)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "anvil")


BUILDERS.update({"barrel": barrel, "crystal": crystal, "crate": crate,
                 "lantern": lantern, "anvil": anvil})
