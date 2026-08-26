"""Procedural asset definitions. Each builder returns the finished mesh object."""
import bpy, bmesh, math, random
from mathutils import Vector
import studio as S


def _lathe(profile, segments, jitter=0.0, seed=0, close_bottom=True, close_top=True, rib=0.0):
    """Revolve a [(radius, z)] profile into a mesh.

    Per-segment radius jitter gives hand-made stock some irregularity without
    touching topology; `rib` alternates segments in and out for fluted forms."""
    rnd = random.Random(seed)
    wob = [1.0 + rnd.uniform(-jitter, jitter) for _ in range(segments)]
    if rib:
        # Alternating in/out per segment, constant over z: reads as vertical ribs
        # (cactus flutes, fluted columns) rather than as surface noise.
        wob = [w + (rib if i % 2 else -rib) for i, w in enumerate(wob)]
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


# ─── Sci-fi modular ────────────────────────────────────────────────────────────
SF_STEEL  = S.srgb('#3A4450')
SF_ALU    = S.srgb('#6E7A88')
SF_DARK   = S.srgb('#222A34')
SF_CYAN   = S.srgb('#22D3EE')
SF_WARN   = S.srgb('#D9A22B')


def container():
    """Cargo container: corrugated flanks, corner castings, barred door end."""
    L, W, H = 0.98, 0.50, 0.54
    steel = S.mat("cnt_steel", SF_STEEL, rough=0.52, metal=0.55)
    alu = S.mat("cnt_alu", SF_ALU, rough=0.40, metal=0.70)
    dark = S.mat("cnt_dark", SF_DARK, rough=0.60, metal=0.40)
    parts = []

    body = _box(L, W, H, (0, 0, H / 2))
    body.data.materials.append(steel)
    S.bevel(body, width=0.010, segments=2)
    parts.append(body)

    # Corrugation: a rib array on both flanks. This is what sells it as a
    # container rather than a box — a flat side reads as neither.
    ribs = 13
    for i in range(ribs):
        x = -L / 2 + L * (i + 0.5) / ribs
        for sy in (-1, 1):
            r = _box(L / ribs * 0.42, 0.022, H * 0.82, (x, sy * (W / 2), H / 2))
            r.data.materials.append(steel)
            S.bevel(r, width=0.005, segments=2)
            parts.append(r)
    # End walls get vertical bars instead, so the two ends read differently.
    for i in range(5):
        y = -W / 2 + W * (i + 0.5) / 5
        for sx in (-1, 1):
            r = _box(0.022, W / 5 * 0.44, H * 0.84, (sx * (L / 2), y, H / 2))
            r.data.materials.append(alu)
            S.bevel(r, width=0.005, segments=2)
            parts.append(r)
    # Corner castings.
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (0, 1):
                c = _box(0.10, 0.10, 0.075,
                         (sx * (L / 2 - 0.05), sy * (W / 2 - 0.05),
                          0.037 if sz == 0 else H - 0.037))
                c.data.materials.append(dark)
                S.bevel(c, width=0.008, segments=2)
                parts.append(c)
    # Roof rails.
    for sy in (-1, 1):
        r = _box(L * 0.94, 0.03, 0.026, (0, sy * (W / 2 - 0.03), H + 0.010))
        r.data.materials.append(alu)
        S.bevel(r, width=0.005, segments=2)
        parts.append(r)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "container")


def canister():
    """Pressurised canister: capsule shell, valve stack, hazard band."""
    steel = S.mat("can_steel", SF_ALU, rough=0.34, metal=0.78)
    dark = S.mat("can_dark", SF_DARK, rough=0.52, metal=0.45)
    warn = S.mat("can_warn", SF_WARN, rough=0.44, metal=0.20)
    parts = []

    prof = [(0.0, 0.0), (0.13, 0.02), (0.175, 0.07), (0.19, 0.16),
            (0.19, 0.52), (0.175, 0.60), (0.13, 0.65), (0.075, 0.68)]
    shell = _lathe(prof, 20)
    shell.data.materials.append(steel)
    S.bevel(shell, width=0.006, segments=2, angle=22.0)
    parts.append(shell)

    for z in (0.24, 0.44):
        b = _lathe([(0.197, 0.0), (0.197, 0.045)], 20,
                   close_bottom=False, close_top=False)
        sol = b.modifiers.new('Solidify', 'SOLIDIFY')
        sol.thickness = 0.012
        S.apply_modifiers(b)
        b.location = (0, 0, z)
        b.data.materials.append(warn if z == 0.44 else dark)
        S.bevel(b, width=0.004, segments=2)
        parts.append(b)

    neck = _lathe([(0.062, 0.0), (0.062, 0.05), (0.048, 0.06)], 14)
    neck.location = (0, 0, 0.68)
    neck.data.materials.append(dark)
    parts.append(neck)

    valve = _box(0.16, 0.055, 0.045, (0, 0, 0.765))
    valve.data.materials.append(dark)
    S.bevel(valve, width=0.008, segments=2)
    parts.append(valve)

    bpy.ops.mesh.primitive_torus_add(major_radius=0.052, minor_radius=0.011,
                                     major_segments=18, minor_segments=8,
                                     location=(0, 0, 0.80))
    wheel = bpy.context.object
    wheel.data.materials.append(warn)
    parts.append(wheel)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "canister")


def relay():
    """Antenna relay: splayed tripod, lattice mast, dish, emitter."""
    steel = S.mat("rly_steel", SF_STEEL, rough=0.50, metal=0.60)
    alu = S.mat("rly_alu", SF_ALU, rough=0.36, metal=0.75)
    glow = S.mat("rly_glow", SF_CYAN, rough=0.30, emit=SF_CYAN, emit_str=5.0)
    parts = []

    pad = _lathe([(0.26, 0.0), (0.27, 0.022), (0.22, 0.045)], 9, jitter=0.02, seed=5)
    pad.data.materials.append(steel)
    S.bevel(pad, width=0.007, segments=2)
    parts.append(pad)

    # Splayed tripod. Euler XYZ applies Y before Z, so (0, -tilt, a) leans the
    # leg's local +Z inward and THEN swings that lean onto bearing `a` — feet out,
    # tops converging on the mast. Building the tilt from cos/sin of `a` instead
    # mixes the two rotations and gives flat blades at wrong angles.
    tilt = 0.32
    for i in range(3):
        a = 2.0 * math.pi * i / 3
        leg = _box(0.050, 0.050, 0.44,
                   (0.15 * math.cos(a), 0.15 * math.sin(a), 0.20))
        leg.rotation_euler = (0.0, -tilt, a)
        leg.data.materials.append(steel)
        S.bevel(leg, width=0.006, segments=2)
        parts.append(leg)

    mast = _box(0.055, 0.055, 0.46, (0, 0, 0.30 + 0.23))
    mast.data.materials.append(alu)
    S.bevel(mast, width=0.006, segments=2)
    parts.append(mast)
    for z in (0.40, 0.56, 0.72):
        c = _box(0.10, 0.10, 0.018, (0, 0, z))
        c.data.materials.append(steel)
        S.bevel(c, width=0.004, segments=2)
        parts.append(c)

    # Dish: a shallow paraboloid lathe, tilted off the mast head.
    dish_prof = [(0.0, 0.0)]
    for i in range(1, 8):
        r = 0.30 * i / 7.0
        dish_prof.append((r, 0.34 * r * r / 0.09))
    dish = _lathe(dish_prof, 20, close_bottom=False, close_top=False)
    sol = dish.modifiers.new('Solidify', 'SOLIDIFY')
    sol.thickness = 0.010
    S.apply_modifiers(dish)
    # Aim the dish AT the camera. studio.frame() views from elev 0.42 / azim -0.62,
    # so the old (0.62, 0, -0.5) pointed the axis at -X and showed only the convex
    # back — hiding everything mounted on the concave face.
    dish.rotation_euler = (0.863, 0.0, 0.955)
    dish.location = (0.02, 0.02, 0.80)
    dish.data.materials.append(alu)
    parts.append(dish)

    # Feed horn at the dish's focal point, on its concave side, 0.18 along the
    # dish axis (0.620, -0.440, 0.650).
    emit = _lathe([(0.048, 0.0), (0.048, 0.075), (0.026, 0.10)], 14)
    emit.rotation_euler = (0.863 + math.pi, 0.0, 0.955)
    emit.location = (0.132, -0.059, 0.917)
    emit.data.materials.append(glow)
    parts.append(emit)
    # Boss on the dish face, so the emitter reads as powered from any angle.
    boss = _lathe([(0.055, 0.0), (0.055, 0.022), (0.032, 0.032)], 14)
    boss.rotation_euler = (0.863, 0.0, 0.955)
    boss.location = (0.02, 0.02, 0.80)
    boss.data.materials.append(glow)
    parts.append(boss)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "relay")


def reactor():
    """Reactor cell: hex housing slotted to show an emissive core."""
    steel = S.mat("rct_steel", SF_STEEL, rough=0.46, metal=0.62)
    dark = S.mat("rct_dark", SF_DARK, rough=0.55, metal=0.40)
    # 7.0 clips the core to white and loses the cyan the theme is built on.
    core_m = S.mat("rct_core", SF_CYAN, rough=0.25, emit=SF_CYAN, emit_str=3.4)
    parts = []

    base = _lathe([(0.30, 0.0), (0.31, 0.035), (0.27, 0.07)], 6)
    base.data.materials.append(dark)
    S.bevel(base, width=0.010, segments=2)
    parts.append(base)

    core = _lathe([(0.15, 0.0), (0.175, 0.04), (0.175, 0.40), (0.15, 0.44)], 12)
    core.location = (0, 0, 0.07)
    core.data.materials.append(core_m)
    parts.append(core)

    # Six columns on the hex corners: the gaps between them ARE the slots.
    for i in range(6):
        a = 2.0 * math.pi * i / 6 + math.pi / 6
        col = _box(0.085, 0.085, 0.48,
                   (0.225 * math.cos(a), 0.225 * math.sin(a), 0.07 + 0.24),
                   (0, 0, a))
        col.data.materials.append(steel)
        S.bevel(col, width=0.008, segments=2)
        parts.append(col)

    for z in (0.16, 0.42):
        ring = _lathe([(0.245, 0.0), (0.245, 0.04)], 6,
                      close_bottom=False, close_top=False)
        sol = ring.modifiers.new('Solidify', 'SOLIDIFY')
        sol.thickness = 0.016
        S.apply_modifiers(ring)
        ring.location = (0, 0, z)
        ring.data.materials.append(dark)
        S.bevel(ring, width=0.005, segments=2)
        parts.append(ring)

    cap = _lathe([(0.30, 0.0), (0.31, 0.035), (0.26, 0.075), (0.16, 0.10)], 6)
    cap.location = (0, 0, 0.55)
    cap.data.materials.append(dark)
    S.bevel(cap, width=0.009, segments=2)
    parts.append(cap)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "reactor")


def hexpad():
    """Hex floor tile: inset panel, bolt heads, glowing seam."""
    steel = S.mat("hex_steel", SF_STEEL, rough=0.50, metal=0.58)
    alu = S.mat("hex_alu", SF_ALU, rough=0.38, metal=0.72)
    glow = S.mat("hex_glow", SF_CYAN, rough=0.28, emit=SF_CYAN, emit_str=3.6)
    parts = []

    plate = _lathe([(0.48, 0.0), (0.50, 0.020), (0.50, 0.055), (0.47, 0.075)], 6)
    plate.data.materials.append(steel)
    S.bevel(plate, width=0.008, segments=2)
    parts.append(plate)

    seam = _lathe([(0.435, 0.0), (0.435, 0.012)], 6,
                  close_bottom=False, close_top=False)
    sol = seam.modifiers.new('Solidify', 'SOLIDIFY')
    sol.thickness = 0.010
    S.apply_modifiers(seam)
    seam.location = (0, 0, 0.068)
    seam.data.materials.append(glow)
    parts.append(seam)

    panel = _lathe([(0.40, 0.0), (0.40, 0.016), (0.37, 0.026)], 6)
    panel.location = (0, 0, 0.070)
    panel.data.materials.append(alu)
    S.bevel(panel, width=0.006, segments=2)
    parts.append(panel)

    for i in range(6):
        a = 2.0 * math.pi * i / 6 + math.pi / 6
        bolt = _lathe([(0.030, 0.0), (0.030, 0.016), (0.022, 0.022)], 8)
        bolt.location = (0.455 * math.cos(a), 0.455 * math.sin(a), 0.070)
        bolt.data.materials.append(alu)
        parts.append(bolt)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "hexpad")


BUILDERS.update({"container": container, "canister": canister, "relay": relay,
                 "reactor": reactor, "hexpad": hexpad})

# Each theme carries its own studio: world colour, ground colour, accent light.
THEMES = {
    "forge": {
        "assets": ["barrel", "crate", "lantern", "anvil", "crystal"],
        "world": S.BACKDROP, "ground": S.GROUND,
        "accent": (1.0, 0.52, 0.24), "accent_gain": 1.0,
    },
    "scifi": {
        "assets": ["container", "canister", "relay", "reactor", "hexpad"],
        "world": S.srgb('#0A1420'), "ground": S.srgb('#0E1826'),
        "accent": (0.16, 0.72, 0.88), "accent_gain": 1.6,
    },
}


def theme_of(asset):
    for name, spec in THEMES.items():
        if asset in spec["assets"]:
            return name, spec
    raise KeyError(f"no theme registers asset {asset!r}")


# ─── Stylised nature ───────────────────────────────────────────────────────────
NT_BARK   = S.srgb('#5A4632')
NT_BARK_L = S.srgb('#7A6144')
NT_LEAF   = S.srgb('#3D6B3A')
NT_LEAF_L = S.srgb('#4F8544')
NT_MOSS   = S.srgb('#6E8257')
NT_STONE  = S.srgb('#6B7280')
NT_STONE_D= S.srgb('#4A5058')
NT_CAP    = S.srgb('#A6432E')
NT_STEM   = S.srgb('#D9CFB8')
NT_CACTUS = S.srgb('#4E7A52')


def _blob(r, squash, loc, seed, rough_amt=0.16, subdiv=2):
    """A faceted lump: icosphere with per-vertex radial noise, flat shaded.

    This is the workhorse for organic mass — foliage, moss, boulders. Randomising
    radius per vertex is what stops it reading as a sphere.
    """
    rnd = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r, location=loc)
    o = bpy.context.object
    for v in o.data.vertices:
        v.co *= 1.0 + rnd.uniform(-rough_amt, rough_amt)
    o.scale = (1.0, 1.0, squash)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def tree():
    """Stylised tree: tapered trunk, recursive limbs, faceted foliage clumps."""
    rnd = random.Random(23)
    bark = S.mat("tr_bark", NT_BARK, rough=0.80)
    leaf = S.mat("tr_leaf", NT_LEAF, rough=0.72)
    leaf_l = S.mat("tr_leaf_l", NT_LEAF_L, rough=0.70)
    parts = []

    trunk = _lathe([(0.115, 0.0), (0.088, 0.14), (0.074, 0.36),
                    (0.062, 0.60), (0.050, 0.82)], 9, jitter=0.09, seed=4)
    trunk.data.materials.append(bark)
    parts.append(trunk)

    # Buttress roots: short tapered lathes leaning out of the trunk base.
    for i in range(5):
        a = 2.0 * math.pi * i / 5 + 0.3
        rt = _lathe([(0.052, 0.0), (0.030, 0.10), (0.014, 0.17)], 6)
        rt.rotation_euler = (0.0, 1.15, a)
        rt.location = (0.085 * math.cos(a), 0.085 * math.sin(a), 0.055)
        rt.data.materials.append(bark)
        parts.append(rt)

    # Primary limbs off the upper trunk, each ending in a foliage clump.
    limbs = [(0.58, 0.95, 0.30, 0.30), (0.66, 2.30, 0.34, 0.26),
             (0.72, 3.85, 0.28, 0.24), (0.62, 5.20, 0.32, 0.28)]
    tips = [(0.0, 0.0, 1.02, 0.30)]
    for z0, az, length, tilt in limbs:
        lb = _lathe([(0.034, 0.0), (0.022, length * 0.6), (0.012, length)], 6)
        lb.rotation_euler = (0.0, math.pi / 2 - tilt, az)
        lb.location = (0.045 * math.cos(az), 0.045 * math.sin(az), z0)
        lb.data.materials.append(bark)
        parts.append(lb)
        # Clump sits at the limb tip: base + horizontal reach + vertical rise.
        reach = length * math.sin(math.pi / 2 - tilt)
        rise = length * math.cos(math.pi / 2 - tilt)
        tips.append((math.cos(az) * (0.045 + reach), math.sin(az) * (0.045 + reach),
                     z0 + rise, 0.235))
    for i, (x, y, z, r) in enumerate(tips):
        cl = _blob(r, rnd.uniform(0.70, 0.86), (x, y, z), seed=40 + i)
        cl.data.materials.append(leaf if i % 2 else leaf_l)
        parts.append(cl)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "tree")


def boulder():
    """Erratic boulder: heavily noised icosphere, sheared and sat flat."""
    rock = S.mat("bd_rock", NT_STONE, rough=0.84)
    moss_m = S.mat("bd_moss", NT_MOSS, rough=0.88)
    parts = []

    b = _blob(0.42, 0.72, (0, 0, 0.30), seed=9, rough_amt=0.26, subdiv=2)
    # Shear so it leans: a symmetric lump reads as a ball, not as rock.
    for v in b.data.vertices:
        v.co.x += 0.20 * (v.co.z / 0.30)
        v.co.z = max(v.co.z, -0.24)   # flatten the bed it sits on
    b.data.materials.append(rock)
    parts.append(b)

    for i, (x, y, z, r) in enumerate([(0.10, -0.08, 0.56, 0.13),
                                      (-0.14, 0.11, 0.50, 0.10),
                                      (0.22, 0.14, 0.44, 0.085)]):
        m = _blob(r, 0.32, (x, y, z), seed=60 + i, rough_amt=0.30)
        m.data.materials.append(moss_m)
        parts.append(m)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "boulder")


def mushrooms():
    """Cluster of five toadstools of graded size on a mossy pad."""
    cap_m = S.mat("mu_cap", NT_CAP, rough=0.58)
    stem_m = S.mat("mu_stem", NT_STEM, rough=0.72)
    moss_m = S.mat("mu_moss", NT_MOSS, rough=0.86)
    parts = []

    pad = _lathe([(0.36, 0.0), (0.38, 0.035), (0.30, 0.065)], 11, jitter=0.16, seed=6)
    pad.data.materials.append(moss_m)
    S.bevel(pad, width=0.010, segments=2)
    parts.append(pad)

    #        x      y     scale  lean
    caps = [(0.00,  0.00, 1.00, 0.00),
            (-0.15, 0.07, 0.66, 0.16),
            (0.14, -0.10, 0.58, -0.13),
            (0.06,  0.17, 0.44, 0.20),
            (-0.09,-0.16, 0.36, -0.18)]
    for i, (x, y, sc, lean) in enumerate(caps):
        stem = _lathe([(0.040 * sc, 0.0), (0.032 * sc, 0.10 * sc),
                       (0.036 * sc, 0.20 * sc)], 10)
        cap = _lathe([(0.0, 0.115 * sc), (0.060 * sc, 0.100 * sc),
                      (0.105 * sc, 0.062 * sc), (0.122 * sc, 0.022 * sc),
                      (0.116 * sc, 0.0)], 14, close_bottom=True, close_top=False)
        cap.location = (0, 0, 0.19 * sc)
        for o, m in ((stem, stem_m), (cap, cap_m)):
            o.data.materials.append(m)
        S.apply_modifiers(stem)
        S.apply_modifiers(cap)
        grp = S.join([stem, cap], f"shroom{i}")
        grp.rotation_euler = (lean, 0.0, i * 1.3)
        grp.location = (x, y, 0.055)
        parts.append(grp)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "mushrooms")


def stump():
    """Cut stump: flared base, ring-marked top, moss on the north face."""
    bark = S.mat("st_bark", NT_BARK, rough=0.82)
    heart = S.mat("st_heart", NT_BARK_L, rough=0.66)
    moss_m = S.mat("st_moss", NT_MOSS, rough=0.88)
    parts = []

    body = _lathe([(0.30, 0.0), (0.255, 0.09), (0.235, 0.22), (0.242, 0.34)],
                  11, jitter=0.075, seed=8, close_top=False)
    body.data.materials.append(bark)
    parts.append(body)

    # Cut face, inset a hair so the bark reads as a rim around it.
    top = _lathe([(0.232, 0.0), (0.232, 0.012)], 11, jitter=0.075, seed=8)
    top.location = (0, 0, 0.335)
    top.data.materials.append(heart)
    parts.append(top)
    ring = _lathe([(0.110, 0.0), (0.110, 0.006)], 11)
    ring.location = (0, 0, 0.348)
    ring.data.materials.append(bark)
    parts.append(ring)

    for i in range(6):
        a = 2.0 * math.pi * i / 6 + 0.25
        rt = _lathe([(0.058, 0.0), (0.034, 0.09), (0.016, 0.15)], 6)
        rt.rotation_euler = (0.0, 1.25, a)
        rt.location = (0.24 * math.cos(a), 0.24 * math.sin(a), 0.042)
        rt.data.materials.append(bark)
        parts.append(rt)

    for i, (x, y, z, r) in enumerate([(-0.18, 0.14, 0.20, 0.115),
                                      (-0.10, 0.22, 0.09, 0.090),
                                      (0.19, 0.15, 0.30, 0.075)]):
        m = _blob(r, 0.30, (x, y, z), seed=80 + i, rough_amt=0.32)
        m.data.materials.append(moss_m)
        parts.append(m)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "stump")


def cactus():
    """Barrel cactus with two arms: fluted via the lathe's alternating-rib mode."""
    green = S.mat("ca_green", NT_CACTUS, rough=0.66)
    soil = S.mat("ca_soil", NT_STONE_D, rough=0.86)
    parts = []

    pot = _lathe([(0.26, 0.0), (0.27, 0.03), (0.23, 0.06)], 11, jitter=0.10, seed=2)
    pot.data.materials.append(soil)
    S.bevel(pot, width=0.008, segments=2)
    parts.append(pot)

    body = _lathe([(0.115, 0.0), (0.145, 0.09), (0.150, 0.52),
                   (0.140, 0.66), (0.100, 0.74), (0.045, 0.78)],
                  16, rib=0.075)
    body.location = (0, 0, 0.045)
    body.data.materials.append(green)
    parts.append(body)

    # Two arms: a vertical limb sat on the end of a short elbow.
    for sgn, z0, ln in ((1, 0.30, 0.26), (-1, 0.42, 0.20)):
        elbow = _lathe([(0.058, 0.0), (0.055, 0.08), (0.052, 0.15)], 12, rib=0.06)
        elbow.rotation_euler = (0.0, sgn * 1.32, 0.0)
        elbow.location = (sgn * 0.12, 0.0, z0)
        elbow.data.materials.append(green)
        parts.append(elbow)
        up = _lathe([(0.055, 0.0), (0.052, ln * 0.7), (0.040, ln * 0.92),
                     (0.018, ln)], 12, rib=0.06)
        up.location = (sgn * 0.255, 0.0, z0 + 0.03)
        up.data.materials.append(green)
        parts.append(up)

    for p in parts:
        S.apply_modifiers(p)
    return S.join(parts, "cactus")


BUILDERS.update({"tree": tree, "boulder": boulder, "mushrooms": mushrooms,
                 "stump": stump, "cactus": cactus})

THEMES["nature"] = {
    "assets": ["tree", "boulder", "mushrooms", "stump", "cactus"],
    "world": S.srgb('#0E1712'), "ground": S.srgb('#141C16'),
    "accent": (0.62, 0.86, 0.48), "accent_gain": 0.85,
}
