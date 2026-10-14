"""Check that a model will print — counted on the raw triangles, then confirmed by a slicer.

    blender -b --factory-startup --python-exit-code 1 --python tools/print_check.py -- \\
        model.stl|model.3mf|model.glb|model.blend [part2.stl …] --process fdm|resin \\
        [--height-mm H] [--parts N] [--reference original.glb|.blend|.stl] \\
        [--slicer /path/to/PrusaSlicer|name] [--slicer-timeout S] [--json out.json]

Exit codes: 0 PASS, 3 FAIL, 1 error (unreadable file, bad arguments, slicer missing or
timed out).

Several files are an ASSEMBLY — one figure printed in several colours, one file per colour.
A colour alone is not printable (pupils float without the head that holds them), and the files
laid end to end share their contact faces, which reads as edges shared by four faces. So each
file is checked closed on its own, the parts' overlap is measured, and their union — one voxel
remesh of them all, 0.25 mm or finer — is checked as one object, slicer included.

Units: STL is read as millimetres, 3MF by its own `unit`, GLB and .blend as metres. With
--height-mm the model is scaled uniformly to that height; every figure is in mm after it.

The counts are RAW: vertices are matched only when their coordinates are bit-identical,
never welded within a distance. Welding before counting glued neighbouring shells together
and made defects that the file did not have (the print study's first measure did exactly
that). Edges are then paired exactly:

- parts: groups of triangles joined through shared edges (what a slicer calls parts);
  closed parts: every edge of the part has exactly two faces;
- open edges (one face), non-manifold edges (more than two), non-manifold vertices (faces
  around the vertex fall into more than one fan), inconsistent normals (an edge walked the
  same way by both its faces);
- self-intersections (triangle pairs crossing, inside a part — a pair that only touches, at a
  shared vertex or a vertex lying on a face, is not one) and intersecting parts, with
  Blender's own BVH — no external dependency;
- floating parts: a part neither on the bed, nor crossing, enclosed by or within one
  extrusion (0.4 mm FDM, 0.05 mm resin) of a held part — a printer fuses closer parts. The
  bed is the lowest point of the parts with volume, and only they hold another part;
  inverted parts: negative volume and not enclosed (a cavity is enclosed). Parts with no
  volume (slivers a decimation leaves) are counted and not judged;
- thin walls: share of faces whose wall, cast inward along the normal, is thinner than the
  process minimum (0.8 mm FDM, 0.5 mm resin) — sampled above 50,000 faces; the JSON's
  `thickness.thin_at` says where, thinnest first: up to 20 spots (centre in mm, wall read),
  one per mm;
- the smallest scale: a slicer shrinks every wall with the model, so the same walls give the
  scale under which 1 % more of the area would fall below that minimum (`min_scale`, and
  `min_dims_mm`), always of the FILE: --height-mm does not move it, and a height under it is
  said. Walls only: an engraving's depth or a bar's width is not counted apart;
- overhangs: share of the downward area steeper than 45° from vertical (bed excluded), past
  0.5° of tolerance so that a face modelled at 45° is not one. A share, not a verdict on
  supports: small ceilings bridge — --slicer says whether it slices clean without them.

--reference compares the model against the file it was repaired from: dimensions, and
volume, both voxelised at the same size so that an original made of overlapping closed
pieces still has one volume. A boolean union that reports a perfect manifold can have
dropped most of the object; only this comparison sees it. The reference is scaled to the
model's height first — a uniform scale is not a loss. The volume is compared only when the
model AND the reference are sealed (no open, no non-manifold edge): an open mesh voxelises
to almost nothing, so an open original is compared on its dimensions alone, and said so.
A reference under one voxel of volume is a FAIL, never a ratio.

--slicer writes the scaled mesh as a binary STL and hands it to PrusaSlicer in a throwaway
--datadir: `--info` (manifold, number_of_parts) and an FDM `--export-gcode`, whose log is
searched for "Empty layer" and "Floating object part". PrusaSlicer is an arbiter IN ADDITION
to the counts, not instead: it slices open meshes with exit 0 and calls a union that lost
the object manifold. It also sees gaps between layers that the counts do not.

PASS needs: 0 open edges, 0 non-manifold edges, consistent normals, no floating or inverted
part (and --parts N parts when given), no loss against --reference, and with --slicer:
manifold = yes, no empty layer, no floating object part. Everything else is a WARN.

Prints a readable verdict and one JSON line (`PRINT_CHECK {...}`); --json writes it to a file.
"""
import argparse, json, math, os, re, shutil, struct, subprocess, sys, tempfile, zipfile
import xml.etree.ElementTree as ET
import numpy as np

PASS, FAIL, ERROR = 0, 3, 1
MIN_WALL = {"fdm": 0.8, "resin": 0.5}       # mm: the usual nozzle-width and resin floors
BED_TOL = {"fdm": 0.2, "resin": 0.05}        # mm: one layer — closer than that is on the bed
FUSE_GAP = {"fdm": 0.4, "resin": 0.05}       # mm: one extrusion width / about one resin pixel —
                                             # two parts closer than that print as one
EMPTY_MM3 = 1e-3                             # a part under a 0.1 mm cube of volume prints nothing
OVERHANG_DEG = 45.0
# A face modelled at 45° reads 45.0x° once written in single-precision STL: every overhang the
# windmill, its sails and the joint's peg reported was one of those (0.1, 0.33, 0.48 % of the
# area, 2026-10-13) — the chamfers print.md asks for, counted against it.
OVERHANG_TOL_DEG = 0.5
THICKNESS_SAMPLE = 50_000
THIN_AT = 20                                 # thin spots listed in the JSON
# Loss against the reference, measured on the print study's chest and lantern: the faithful
# repairs (voxel remesh, decimated or not) are within 0.52 % on every axis and 0.15 % in
# volume; the MANIFOLD unions that dropped the object are 158-208 % off on an axis once
# scaled to the same height. 3 % sits far from both. The volume tolerance has no real
# lossy case with matching dimensions yet — 10 % is a margin over the voxel error, and
# the seeded test (a quarter of the volume, same box) is all that exercises it.
DIM_TOL = 0.03
VOL_TOL = 0.10
VOXELS_ACROSS = 150                          # voxel size = largest dimension / 150


def die(msg):
    print(f"print_check: {msg}", file=sys.stderr)
    sys.exit(ERROR)


class Parser(argparse.ArgumentParser):
    def error(self, message):                # argparse exits 2; every error here is 1
        self.print_usage(sys.stderr)
        die(message)


def args():
    p = Parser(prog="print_check.py")
    p.add_argument("model", nargs="+", help="one file, or one per part of an assembly (a colour each)")
    p.add_argument("--process", required=True, choices=("fdm", "resin"))
    p.add_argument("--height-mm", type=float)
    p.add_argument("--parts", type=int, help="expected number of parts (default: any)")
    p.add_argument("--reference")
    p.add_argument("--slicer", help="PrusaSlicer: a path, or a name on the PATH")
    p.add_argument("--slicer-timeout", type=float, default=1800, help="seconds per slicer call (default 1800)")
    p.add_argument("--supports", action="store_true",
                   help="slice with PrusaSlicer's automatic supports: a figurine whose limbs hang starts them "
                        "in mid-air without (Floating object part) and prints with them; the verdict says so")
    p.add_argument("--brim-mm", type=float, default=0.0,
                   help="slice with a brim this wide: a tall part on a narrow foot reads 'Low bed adhesion' "
                        "without one (a forge's flame, a tree in its pot) and not with 5 mm")
    p.add_argument("--json")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return p.parse_args(argv)


# ── loading: every format ends as (vertices in mm, triangles) ────────────────────────────

def read_stl(path):
    """Binary or ASCII STL. A binary file is not refused for the size test alone: exporters
    write a count of 0, pad the end, or start the 80-byte header with "solid"."""
    data = open(path, "rb").read()
    declared = struct.unpack("<I", data[80:84])[0] if len(data) >= 84 else None
    held = (len(data) - 84) // 50 if declared is not None else 0     # whole records in the file
    # ASCII only when it reads as ASCII: "solid" first AND facets written out as text
    if declared is None or 84 + 50 * declared != len(data):
        if data.lstrip()[:5].lower() == b"solid" and re.search(rb"facet\s+normal", data[:4096]):
            co = [l.split()[1:4] for l in data.decode("latin-1").splitlines() if l.strip().startswith("vertex")]
            if not co or len(co) % 3:
                die(f"{path}: ASCII STL with {len(co)} vertices — not whole triangles")
            return np.array(co, dtype=np.float64)
        if not held:
            die(f"{path}: no triangle read (neither binary nor ASCII STL)")
    n = declared
    if declared != held:
        # the count field and the size disagree: trust the records the file actually holds
        # when the count is 0 or larger than the file, or when the size is whole records;
        # a few bytes past the declared count are padding. Said, never silent.
        if declared == 0 or declared > held or (len(data) - 84) % 50 == 0:
            n = held
        print(f"print_check: {path}: binary STL whose count field says {declared} triangles, "
              f"{len(data) - 84} bytes of records follow — reading {n}", file=sys.stderr)
    rec = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]),
                        count=n, offset=84)
    return rec["v"].reshape(-1, 3).astype(np.float64)


UNITS = {"micron": 0.001, "millimeter": 1.0, "centimeter": 10.0, "inch": 25.4, "foot": 304.8, "meter": 1000.0}


def read_3mf(path):
    """Triangle soup in mm from a 3MF: objects, components and build items with transforms."""
    z = zipfile.ZipFile(path)
    rels = z.read("_rels/.rels").decode() if "_rels/.rels" in z.namelist() else ""
    m = re.search(r'Target="/?([^"]+\.model)"', rels)
    root = ET.fromstring(z.read((m.group(1) if m else "3D/3dmodel.model").lstrip("/")))
    ns = root.tag[:root.tag.index("}") + 1] if root.tag.startswith("{") else ""
    unit = UNITS.get(root.get("unit", "millimeter"), 1.0)

    def mat(s):
        if not s:
            return np.eye(4)
        v = [float(x) for x in s.split()]
        M = np.eye(4); M[:3, :3] = np.array(v[:9]).reshape(3, 3).T; M[:3, 3] = v[9:12]
        return M

    # The production extension (Bambu Studio, PrusaSlicer) keeps meshes in other parts of
    # the package and points at them with p:path on each component.
    PATH = "{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path"
    main = m.group(1) if m else "3D/3dmodel.model"
    trees = {main: root}

    def objects(part):
        part = part.lstrip("/")
        if part not in trees:
            trees[part] = ET.fromstring(z.read(part))
        return {o.get("id"): o for o in trees[part].iter(ns + "object")}

    def soup(oid, M, part):
        o, out = objects(part)[oid], []
        mesh = o.find(ns + "mesh")
        if mesh is not None:
            V = np.array([[float(v.get(k)) for k in "xyz"] for v in mesh.iter(ns + "vertex")])
            T = np.array([[int(t.get(k)) for k in ("v1", "v2", "v3")] for t in mesh.iter(ns + "triangle")])
            if len(T):
                W = V @ M[:3, :3].T + M[:3, 3]
                out.append(W[T].reshape(-1, 3))
        comps = o.find(ns + "components")
        if comps is not None:
            for c in comps.iter(ns + "component"):
                out += soup(c.get("objectid"), M @ mat(c.get("transform")), c.get(PATH) or part)
        return out

    parts = []
    for item in root.iter(ns + "item"):
        parts += soup(item.get("objectid"), mat(item.get("transform")), item.get(PATH) or main)
    if not parts:
        die(f"{path}: no mesh in the 3MF build")
    return np.concatenate(parts) * unit


def read_blender(path):
    import bpy
    if path.lower().endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=path)
    sc = bpy.context.scene
    shapes = {pb.custom_shape for a in sc.objects if a.type == "ARMATURE" for pb in a.pose.bones if pb.custom_shape}
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for ob in sc.objects:
        if ob.type != "MESH" or ob in shapes or ob.hide_render:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        tri = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
        me.loop_triangles.foreach_get("vertices", tri)
        M = np.array(ob.matrix_world)
        out.append((co @ M[:3, :3].T + M[:3, 3])[tri])
        ev.to_mesh_clear()
    if not out:
        die(f"{path}: no renderable mesh")
    return np.concatenate(out) * 1000.0


def load(path):
    if not os.path.exists(path):
        die(f"{path}: no such file")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".stl":
        soup = read_stl(path)
    elif ext == ".3mf":
        soup = read_3mf(path)
    elif ext in (".glb", ".gltf", ".blend"):
        soup = read_blender(path)
    else:
        die(f"{path}: STL, 3MF, GLB or .blend only")
    # Exact matching only: bit-identical coordinates share a vertex, nothing else does.
    V, F = np.unique(soup, axis=0, return_inverse=True)
    return V, F.reshape(-1, 3).astype(np.int64)


# ── topology ─────────────────────────────────────────────────────────────────────────────

def components(n, a, b):
    """Connected components of n nodes joined by the pairs (a, b): hook roots, shortcut."""
    p = np.arange(n)
    while True:
        while True:
            pp = p[p]
            if np.array_equal(pp, p):
                break
            p = pp
        ra, rb = p[a], p[b]
        k = ra != rb
        if not k.any():
            return p
        lo, hi = np.minimum(ra[k], rb[k]), np.maximum(ra[k], rb[k])
        np.minimum.at(p, hi, lo)


def topology(V, F):
    nf = len(F)
    # directed half-edges, then undirected keys
    a = F.reshape(-1); b = F[:, [1, 2, 0]].reshape(-1)
    face = np.repeat(np.arange(nf), 3)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    key = lo * len(V) + hi
    order = np.argsort(key, kind="stable")
    ks, fs = key[order], face[order]
    fwd = (a < b)[order]
    starts = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    counts = np.diff(np.r_[starts, len(ks)])
    open_e = int((counts == 1).sum())
    nm_e = int((counts > 2).sum())
    # pairs of faces sharing an edge: consecutive faces in each edge group
    i = np.flatnonzero(ks[1:] == ks[:-1])
    fa, fb = fs[i], fs[i + 1]
    label = components(nf, fa, fb) if nf else np.array([], dtype=np.int64)
    roots, part = np.unique(label, return_inverse=True)
    nparts = len(roots)
    # a part is closed when every edge it holds has exactly two faces
    edge_ok = np.repeat(counts == 2, counts)
    bad_face = np.zeros(nf, bool); bad_face[fs[~edge_ok]] = True
    closed = np.ones(nparts, bool); closed[np.unique(part[bad_face])] = False
    # inconsistent normals: on a two-face edge, both faces walk it the same way
    two = starts[counts == 2]
    incoh = int((fwd[two] == fwd[two + 1]).sum())
    # non-manifold vertices: corners (face, vertex) joined across two-face edges; a vertex
    # whose corners fall into more than one fan — or that sits on a >2-face edge — is one
    e_local = np.tile(np.arange(3), nf)[order]          # which edge of its face (0: v0v1 ...)
    k2 = np.flatnonzero(np.repeat(counts == 2, counts) & np.r_[ks[1:] == ks[:-1], False])
    ca, cb = [], []
    for side in (0, 1):
        va = F[fs[k2], (e_local[k2] + side) % 3]
        # the same vertex in the other face
        other = F[fs[k2 + 1]]
        j = np.argmax(other == va[:, None], axis=1)
        ca.append(fs[k2] * 3 + (e_local[k2] + side) % 3)
        cb.append(fs[k2 + 1] * 3 + j)
    ca = np.concatenate(ca) if ca else np.array([], np.int64)
    cb = np.concatenate(cb) if cb else np.array([], np.int64)
    fan = components(3 * nf, ca, cb) if nf else np.array([], np.int64)
    cv = F.reshape(-1)
    pairs = np.unique(np.stack([cv, fan], 1), axis=0)
    fans_per_v = np.bincount(pairs[:, 0], minlength=len(V))
    nm_v = fans_per_v > 1
    nm_v[np.r_[lo[order][starts[counts > 2]], hi[order][starts[counts > 2]]]] = True
    return dict(open_edges=open_e, nonmanifold_edges=nm_e, inconsistent_edges=incoh,
                nonmanifold_vertices=int(nm_v.sum())), part, nparts, closed


# ── geometry ─────────────────────────────────────────────────────────────────────────────

def face_data(V, F):
    t = V[F]
    c = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area2 = np.linalg.norm(c, axis=1)
    n = c / np.maximum(area2, 1e-30)[:, None]
    return t, n, area2 / 2


def touching_only(V, F, pairs):
    """How many of these triangle pairs only touch. The BVH overlap counts a pair that touches
    as one that crosses: the windmill's sails gave 32 (a shared vertex, or a vertex lying on
    a face beside it), a forge's flame 2, the joint coupon 4 at a 2.5 mm peg — none crossing.
    Shrunk 0.1 % toward its centroid, a triangle leaves what it only touched and still
    crosses what it crossed: a crossing shallower than that is not told from a touch."""
    if not len(pairs):
        return 0
    ids = np.unique(pairs)
    t = V[F[ids]]
    c = t.mean(axis=1, keepdims=True)
    small = (c + (t - c) * 0.999).reshape(-1, 3)
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromPolygons(small.tolist(), np.arange(len(small)).reshape(-1, 3).tolist(), all_triangles=True)
    still = {(int(ids[a]), int(ids[b])) for a, b in tree.overlap(tree)}
    return int(sum(1 for a, b in pairs if (int(a), int(b)) not in still))


def signed_volumes(V, F, part, nparts):
    t = V[F]
    v6 = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2]))
    return np.bincount(part, weights=v6, minlength=nparts) / 6.0


def bvh(V, F):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons(V.tolist(), F.tolist(), all_triangles=True)


def ray_hits(tree, origin, direction, limit=1e9):
    """All hit distances along a ray (for inside/outside parity)."""
    from mathutils import Vector
    o, d, out, travelled = Vector(origin), Vector(direction).normalized(), [], 0.0
    for _ in range(10_000):
        loc, nrm, idx, dist = tree.ray_cast(o, d, limit)
        if loc is None:
            return out
        travelled += dist; out.append(travelled)
        o = loc + d * 1e-5
    return out


def support(V, F, part, nparts, closed, vol, overlaps, bed_tol, gap, real, zmin):
    """Which parts are held: on the bed, or crossing, enclosed by, or within `gap` of a held
    part — a printer fuses what is closer than one extrusion. Only `real` parts are judged,
    and only a real part holds another: a sliver prints nothing, so it carries nothing.
    `zmin` is the bed: the lowest point of the real parts."""
    lo = np.full((nparts, 3), np.inf); hi = np.full((nparts, 3), -np.inf)
    t = V[F]
    np.minimum.at(lo, part, t.min(axis=1)); np.maximum.at(hi, part, t.max(axis=1))
    held = (lo[:, 2] <= zmin + bed_tol) & real
    touch = {}
    for i, j in overlaps:
        touch.setdefault(i, set()).add(j); touch.setdefault(j, set()).add(i)
    enclosed = np.zeros(nparts, bool)
    # faces of each part, sorted once: part k is order[bounds[k]:bounds[k + 1]]
    order = np.argsort(part, kind="stable")
    bounds = np.searchsorted(part[order], np.arange(nparts + 1))
    trees, verts = {}, {}

    def faces(k):
        return order[bounds[k]:bounds[k + 1]]

    def vertices(k):
        if k not in verts:
            verts[k] = np.unique(F[faces(k)])
        return verts[k]

    def tree(k):
        if k not in trees:
            used, inv = np.unique(F[faces(k)], return_inverse=True)
            trees[k] = bvh(V[used], inv.reshape(-1, 3))
        return trees[k]

    def inside(p, q):                   # p's lowest vertex inside closed part q (ray parity)
        if not closed[q] or (lo[p] < lo[q]).any() or (hi[p] > hi[q]).any():
            return False
        v = V[vertices(p)]
        o = v[np.argmin(v[:, 2])]
        return len(ray_hits(tree(q), o, (0.267, 0.534, 0.802))) % 2 == 1

    def near(p, q):
        """Some vertex of p within `gap` of q's surface, or back. Every vertex that can be
        that close — the ones inside the other part's box grown by `gap` — is tried, none
        sampled: on a dense part the one contact is a single vertex."""
        from mathutils import Vector
        for x, y in ((p, q), (q, p)):
            v = V[vertices(x)]
            v = v[((v >= lo[y] - gap) & (v <= hi[y] + gap)).all(axis=1)]
            if len(v):
                t = tree(y)
                if any(t.find_nearest(Vector(c), gap)[0] is not None for c in v.tolist()):
                    return True
        return False

    for p in np.flatnonzero(real):      # the box test for every candidate at once
        within = closed & real & (lo <= lo[p]).all(axis=1) & (hi >= hi[p]).all(axis=1)
        within[p] = False
        if any(inside(p, q) for q in np.flatnonzero(within)):
            enclosed[p] = True
    changed = True
    while changed:
        changed = False
        for p in np.flatnonzero(~held & real):
            if any(held[q] and real[q] for q in touch.get(p, ())):
                held[p] = True; changed = True
                continue
            cand = held & real & (lo - gap <= hi[p]).all(axis=1) & (lo[p] - gap <= hi).all(axis=1)
            cand[p] = False
            if any(enclosed[p] and inside(p, q) or near(p, q) for q in np.flatnonzero(cand)):
                held[p] = True; changed = True
    held |= ~real                       # not judged: never reported floating
    inverted = (vol < 0) & closed & ~enclosed & real
    return held, inverted, enclosed, lo, hi


def thickness(V, F, n, area, wall, scale=1.0, seed=0):
    tree = bvh(V, F)
    from mathutils import Vector
    nf = len(F)
    idx = np.arange(nf) if nf <= THICKNESS_SAMPLE else np.sort(
        np.random.default_rng(seed).choice(nf, THICKNESS_SAMPLE, replace=False))
    c = V[F[idx]].mean(axis=1)
    eps = 1e-6 * float(np.ptp(V, axis=0).max())
    reach = float(np.linalg.norm(np.ptp(V, axis=0))) + 1.0
    wall_at = np.full(len(idx), np.inf)
    for k, (ci, ni) in enumerate(zip(c, n[idx])):
        if not ni.any():
            continue
        d = Vector((-ni).tolist())
        loc, hn, _, dist = tree.ray_cast(Vector((ci - ni * eps).tolist()), d, reach)
        # only a back wall counts: the face we leave the solid through points along the ray
        if loc is not None and hn.dot(d) > 0:
            wall_at[k] = dist + eps
    thin = wall_at < wall
    a = area[idx]
    total = max(a.sum(), 1e-30)
    # The smallest scale this file takes: shrunk in a slicer, every wall shrinks with it. Walls
    # are taken thinnest first; the scale stops where they add up to 1 % of the area more than
    # is already thin at 100 % — the next wall would cross the floor below it. 100 % is the
    # FILE, whatever --height-mm asked: measured on the scaled mesh, a lighthouse read at 55 %
    # had its parapet already thin, so it was excused, and the line said 43 % for a model
    # whose floor is 67 % — under the floor, told it could shrink further.
    native = wall_at / scale
    order = np.argsort(native)
    cum = np.cumsum(a[order])
    allowed = a[native < wall].sum() + 0.01 * total
    k = int(np.searchsorted(cum, allowed, side="right"))
    nxt = native[order[k]] if k < len(order) else np.inf
    min_scale = round(float(wall / nxt), 3) if np.isfinite(nxt) and nxt > 0 else None
    # Not the first wall to cross: on the lighthouse that was 2 faces at the foot of the door's
    # engraving (0.09 % of the area) at 80 %, while the parapet — 4.9 % of it, 1.0-1.2 mm —
    # sets 67 %. One percent of the area is a wall someone sees.
    # Where they are: print.md asks to cast rays at the faces flagged before thickening anything,
    # and two sessions wrote their own probe to find them. Thinnest first, one per 1 mm.
    at = []
    for k in np.flatnonzero(thin)[np.argsort(wall_at[thin])]:
        p = c[k]
        if all(np.linalg.norm(p - np.array(q["at_mm"])) > 1.0 for q in at):
            at.append(dict(at_mm=[round(float(x), 2) for x in p], wall_mm=round(float(wall_at[k]), 3)))
            if len(at) == THIN_AT:
                break
    return dict(min_wall_mm=wall, faces_thin_pct=round(100 * thin.mean(), 2) if len(idx) else 0.0,
                area_thin_pct=round(100 * a[thin].sum() / total, 2),
                min_scale=min_scale, sampled=int(len(idx)), of=int(nf), thin_at=at)


def voxel_volume(V, F, size):
    """Volume of the voxelised surface — defined even for an open or overlapping mesh."""
    import bpy, bmesh
    me = bpy.data.meshes.new("pc_vox")
    me.from_pydata(V.tolist(), [], F.tolist())
    ob = bpy.data.objects.new("pc_vox", me); bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new("r", "REMESH"); md.mode = "VOXEL"; md.voxel_size = size
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    bm = bmesh.new(); bm.from_mesh(ev.to_mesh())
    vol = abs(bm.calc_volume(signed=True))
    bm.free(); ev.to_mesh_clear()
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    # The voxel remesh fills a CLOSED cavity: a hollow figure saved before its openings were cut
    # read as solid, and the carved model as a 77 % loss against it (a pumpkin, 2026-10-09).
    # A closed shell with a negative volume is that cavity: take it back out, exactly.
    _, part, nparts, closed = topology(V, F)
    sv = signed_volumes(V, F, part, nparts)
    cav = closed & (sv < -EMPTY_MM3)
    return max(vol - float(-sv[cav].sum()), 0.0)


# ── slicer ───────────────────────────────────────────────────────────────────────────────

def write_stl(path, V, F):
    t = V[F].astype(np.float32)
    rec = np.zeros(len(F), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    rec["v"] = t
    # Real facet normals: PrusaSlicer 2.9.6 refuses to load some binary STLs whose normals are all zero
    # ("Loading of a model file failed": a 10 mm cube did, a 10 x 10 x 20 box did not). Measured 2026-10-09.
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    rec["n"] = np.divide(n, ln, out=np.zeros_like(n), where=ln > 0)
    with open(path, "wb") as f:
        f.write(b"print_check".ljust(80, b" ")); f.write(struct.pack("<I", len(F))); f.write(rec.tobytes())


def slicer(name, V, F, timeout, supports=False, brim=0.0):
    exe = shutil.which(name)                 # a path, or a command on the PATH
    if exe is None:
        die(f"slicer not found, or not executable: {name}")
    d = tempfile.mkdtemp(prefix="print_check_")

    def call(argv):
        try:
            return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            die(f"slicer timed out after {timeout:g} s (--slicer-timeout): {' '.join(argv[-2:])}")
        except OSError as e:
            die(f"slicer could not run: {e}")

    try:
        stl = os.path.join(d, "model.stl"); write_stl(stl, V, F)
        data = os.path.join(d, "datadir"); os.makedirs(data)
        base = [exe, "--datadir", data, "--loglevel", "2"]
        info = call(base + ["--info", stl])
        txt = info.stdout + info.stderr
        man = re.search(r"manifold\s*=\s*(\w+)", txt)
        parts = re.search(r"number_of_parts\s*=\s*(\d+)", txt)
        opn = re.search(r"open_edges\s*=\s*(\d+)", txt)
        sup = ["--support-material", "--support-material-auto"] if supports else []
        rim = ["--brim-width", f"{brim:g}"] if brim > 0 else []
        sl = call(base + sup + rim + ["--export-gcode", "-o", os.path.join(d, "out.gcode"), stl])
        log = sl.stdout + sl.stderr
        empty = re.findall(r"Empty layer[^\n]*", log)
        floating = re.findall(r"Floating object part[^\n]*", log)
        # "Detected print stability issues:" / blank / object name / the issues, comma-separated
        m = re.search(r"Detected print stability issues:\s*\n\s*\n[^\n]*\n([^\n]+)", log)
        issues = [x.strip() for x in m.group(1).split(",")] if m else []
        return dict(info_exit=info.returncode, manifold=man.group(1) if man else None,
                    number_of_parts=int(parts.group(1)) if parts else None,
                    open_edges=int(opn.group(1)) if opn else 0,
                    slice_exit=sl.returncode, gcode=os.path.exists(os.path.join(d, "out.gcode")),
                    empty_layers=empty[:5], empty_layer_count=len(empty),
                    floating_parts=floating[:5], floating_count=len(floating), stability_issues=issues)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ── main ─────────────────────────────────────────────────────────────────────────────────

def voxel_union(V, F, size):
    """One closed surface around everything: the parts of an assembly, touching or overlapping,
    remeshed together. The lowest point is put back where it was — the voxel grid moves it."""
    import bpy
    me = bpy.data.meshes.new("pc_union")
    me.from_pydata(V.tolist(), [], F.tolist())
    ob = bpy.data.objects.new("pc_union", me); bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new("r", "REMESH"); md.mode = "VOXEL"; md.voxel_size = size; md.adaptivity = 0.0
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    um = ev.to_mesh(); um.calc_loop_triangles()
    UV = np.array([v.co for v in um.vertices], dtype=float).reshape(-1, 3)
    UF = np.array([t.vertices for t in um.loop_triangles], dtype=np.int64).reshape(-1, 3)
    ev.to_mesh_clear(); bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    if len(UV):
        UV[:, 2] += float(V[:, 2].min()) - float(UV[:, 2].min())
    return UV, UF


def assembly(paths):
    """Each part checked closed on its own; the overlap between parts measured; the union returned."""
    parts, Vs, Fs, own, off = [], [], [], [], 0
    for path in paths:
        Vi, Fi = load(path)
        if not len(Fi):
            die(f"{path}: no triangle")
        ti, _, ni, ci = topology(Vi, Fi)
        parts.append(dict(file=os.path.abspath(path), triangles=int(len(Fi)), parts=int(ni),
                          closed=bool(ci.all() and ti["open_edges"] == 0 and ti["nonmanifold_edges"] == 0
                                      and ti["inconsistent_edges"] == 0),
                          open_edges=ti["open_edges"], nonmanifold_edges=ti["nonmanifold_edges"],
                          inconsistent_edges=ti["inconsistent_edges"]))
        own.append((Vi, Fi)); Vs.append(Vi); Fs.append(Fi + off); off += len(Vi)
    V, F = np.vstack(Vs), np.vstack(Fs)
    size = min(0.25, float(np.ptp(V, axis=0).max()) / 400)
    UV, UF = voxel_union(V, F, size)
    if not len(UF):
        die("the assembly's union is empty")
    # overlap = what the parts count twice: their volumes summed, less the union's
    vsum = sum(voxel_volume(Vi, Fi, size) for Vi, Fi in own)
    vunion = voxel_volume(UV, UF, size)
    return UV, UF, dict(parts=parts, voxel_mm=round(size, 4), volume_parts_mm3=round(vsum, 1),
                        volume_union_mm3=round(vunion, 1), overlap_mm3=round(max(vsum - vunion, 0.0), 1))


def main():
    o = args()
    asm = None
    if len(o.model) > 1:
        if o.reference:
            die("--reference compares one model with its original: check the parts of an assembly one by one for that")
        V, F, asm = assembly(o.model)
    else:
        V, F = load(o.model[0])
    o.model = o.model[0] if asm is None else " + ".join(os.path.basename(m) for m in o.model)
    if not len(F):
        die(f"{o.model}: no triangle")
    native_h = float(V[:, 2].max() - V[:, 2].min())
    if o.height_mm is not None:
        # 0 would be ignored, a negative height mirrors the model and turns its normals inside out
        if not (math.isfinite(o.height_mm) and o.height_mm > 0):
            die(f"--height-mm must be a height above 0, not {o.height_mm:g}")
        if native_h <= 0:
            die("the model is flat: no height to scale")
    scale = o.height_mm / native_h if o.height_mm is not None else 1.0
    if o.slicer and not o.slicer_timeout > 0:
        die(f"--slicer-timeout must be above 0, not {o.slicer_timeout:g}")
    V = V * scale
    dims = np.ptp(V, axis=0)
    topo, part, nparts, closed = topology(V, F)
    t, n, area = face_data(V, F)
    vol = signed_volumes(V, F, part, nparts)

    tree = bvh(V, F)
    pairs = np.array(tree.overlap(tree), dtype=np.int64).reshape(-1, 2)
    pa, pb = part[pairs[:, 0]], part[pairs[:, 1]]
    same = pairs[pa == pb]
    selfx = int(len(same) - touching_only(V, F, same))
    inter = sorted({(int(min(x, y)), int(max(x, y))) for x, y in zip(pa, pb) if x != y})

    # Zero-volume parts — flat slivers a decimation or a voxel pass leaves behind — print
    # nothing and a slicer drops them; they are counted, not judged.
    real = np.abs(vol) >= EMPTY_MM3
    # The bed is the lowest point of what prints: a sliver under the model does not lower it.
    zmin = float(t[real[part]][:, :, 2].min()) if real.any() else float(V[:, 2].min())
    held, inverted, enclosed, plo, phi = support(V, F, part, nparts, closed, vol, inter, BED_TOL[o.process],
                                                 FUSE_GAP[o.process], real, zmin)
    floating = [int(p) for p in np.flatnonzero(~held)]
    from mathutils import Vector
    float_info = []
    for p in floating[:20]:                   # where each one is, and how far from the rest
        vv = np.unique(F[part == p])
        vv = vv if len(vv) <= 500 else np.random.default_rng(0).choice(vv, 500, replace=False)
        gaps = [d for c in V[vv].tolist() for _, _, i, d in tree.find_nearest_range(Vector(c), 5.0)
                if part[i] != p and real[part[i]]]
        float_info.append(dict(bbox_mm=[np.round(plo[p], 2).tolist(), np.round(phi[p], 2).tolist()],
                               volume_mm3=round(float(vol[p]), 2),
                               gap_to_other_part_mm=round(min(gaps), 3) if gaps else "> 5"))

    on_bed = (t[:, :, 2] <= zmin + BED_TOL[o.process]).all(axis=1)
    # a face θ from vertical has n_z = -sin θ: steeper than the limit is below -sin(limit)
    down = (n[:, 2] < -math.sin(math.radians(OVERHANG_DEG + OVERHANG_TOL_DEG))) & ~on_bed
    overhang_pct = round(100 * area[down].sum() / max(area.sum(), 1e-30), 2)
    thin = thickness(V, F, n, area, MIN_WALL[o.process], scale)

    r = dict(file=os.path.abspath(o.model) if asm is None else o.model, process=o.process, triangles=int(len(F)), vertices=int(len(V)),
             scale=scale, dims_mm=[round(float(x), 3) for x in dims],
             parts=int(nparts), closed_parts=int(closed.sum()), empty_parts=int((~real).sum()), **topo,
             self_intersecting_pairs=selfx, intersecting_part_pairs=len(inter),
             floating_parts=len(floating), floating=float_info, inverted_parts=int(inverted.sum()),
             cavities=int((enclosed & (vol < 0)).sum()),
             volume_mm3=round(float(vol[closed].sum()), 3), overhang_area_pct=overhang_pct, thickness=thin)
    if thin["min_scale"] is not None:
        thin["min_dims_mm"] = [round(float(x) / scale * thin["min_scale"], 1) for x in dims]
    fails, warns = [], []
    if asm is not None:
        r["assembly"] = asm
        for q in asm["parts"]:
            if not q["closed"]:
                fails.append(f"assembly: {os.path.basename(q['file'])} is not closed on its own "
                             f"({q['open_edges']} open, {q['nonmanifold_edges']} non-manifold edges)")
        if asm["overlap_mm3"] > 0.01 * max(asm["volume_union_mm3"], 1e-9) and asm["overlap_mm3"] > 1.0:
            warns.append(f"assembly: the parts overlap by {asm['overlap_mm3']} mm3 — a slicer prints that volume "
                         f"in one colour or the other; cut each part by the ones above it")
        warns.append(f"assembly of {len(asm['parts'])} files: their union checked as one object "
                     f"(voxel {asm['voxel_mm']} mm) — load them in the slicer as ONE object with several parts")
    # A rescale hides a model built at the wrong size: one at 93.7 mm passed as 100 mm in silence.
    if abs(scale - 1.0) > 0.01:
        warns.append(f"scaled x{scale:.3f} to {o.height_mm:g} mm: the file itself is {native_h:.1f} mm tall "
                     f"— print it at that scale, or export it at size")
        if thin["min_scale"] is not None and scale < thin["min_scale"] - 1e-9:
            warns.append(f"{o.height_mm:g} mm is under the smallest scale: the file holds down to "
                         f"{100 * thin['min_scale']:.0f} % ({thin['min_dims_mm'][2]:g} mm tall), this is "
                         f"{100 * scale:.0f} % — {thin['area_thin_pct']} % of the area under {thin['min_wall_mm']} mm")
    if topo["open_edges"]:
        fails.append(f"{topo['open_edges']} open edges — the surface has holes")
    if topo["nonmanifold_edges"]:
        fails.append(f"{topo['nonmanifold_edges']} edges shared by more than two faces")
    if topo["inconsistent_edges"]:
        fails.append(f"{topo['inconsistent_edges']} edges with inconsistent normals")
    if floating:
        fails.append(f"{len(floating)} floating part(s): not on the bed, nor crossing or within one extrusion of a held part")
    if r["inverted_parts"]:
        fails.append(f"{r['inverted_parts']} inverted part(s): negative volume and not a cavity")
    if o.parts is not None and int(real.sum()) != o.parts:
        fails.append(f"{int(real.sum())} parts with volume, expected {o.parts}")
    if (~real).any():
        warns.append(f"{int((~real).sum())} part(s) with no volume (under {EMPTY_MM3} mm3) — slivers, ignored "
                     f"by a slicer; not judged")
    if topo["nonmanifold_vertices"]:
        warns.append(f"{topo['nonmanifold_vertices']} non-manifold vertices (faces meeting at a single point)")
    if selfx:
        warns.append(f"{selfx} self-intersecting triangle pairs inside a part")
    if inter:
        warns.append(f"{len(inter)} pair(s) of parts crossing each other — a slicer merges them, a union is cleaner")
    if thin["faces_thin_pct"] > 0:
        warns.append(f"{thin['faces_thin_pct']} % of faces on a wall under {thin['min_wall_mm']} mm "
                     f"({thin['area_thin_pct']} % of the area)")
    # Said as a share, never as "supports": three sessions read the bare word against a clean
    # slice without them and could not tell which to hand over. The slicer pass answers it.
    over_at = None
    if overhang_pct > 0:
        over_at = len(warns)
        warns.append(f"{overhang_pct} % of the area overhangs more than {OVERHANG_DEG:.0f}° — small areas "
                     f"bridge; --slicer says whether it needs supports")

    if o.reference:
        RV, RF = load(o.reference)
        rh = float(RV[:, 2].max() - RV[:, 2].min())
        RV = RV * (dims[2] / rh) if rh > 0 else RV
        rdims = np.ptp(RV, axis=0)
        size = float(max(dims.max(), rdims.max())) / VOXELS_ACROSS
        rtopo = topology(RV, RF)[0]
        ref_sealed = not rtopo["open_edges"] and not rtopo["nonmanifold_edges"]
        sealed = not topo["open_edges"] and not topo["nonmanifold_edges"]
        # An open reference voxelises to almost nothing — 4 mm3 for an open 40 x 20 x 20 box —
        # and any model reads as a gain over it: its volume is not measured at all.
        rv = voxel_volume(RV, RF, size) if ref_sealed else None
        mv = voxel_volume(V, F, size) if ref_sealed else None
        # under one voxel the reference has no volume to compare against: no ratio, never a NaN
        ref_empty = rv is not None and rv < size ** 3
        ratio = mv / rv if rv is not None and not ref_empty else None
        dd = (dims - rdims) / np.maximum(rdims, 1e-9)
        r["reference"] = dict(file=os.path.abspath(o.reference), dims_mm=[round(float(x), 3) for x in rdims],
                              dims_diff_pct=[round(100 * float(x), 2) for x in dd], voxel_mm=round(size, 4),
                              open_edges=rtopo["open_edges"], nonmanifold_edges=rtopo["nonmanifold_edges"],
                              volume_voxel_mm3=None if rv is None else round(rv, 1),
                              model_volume_voxel_mm3=None if mv is None else round(mv, 1),
                              volume_ratio=None if ratio is None else round(ratio, 4), volume_compared=True)
        dims_off = bool((np.abs(dd) > DIM_TOL).any())
        if dims_off:
            fails.append(f"dimensions differ from the reference by {[round(100 * float(x), 1) for x in dd]} % "
                         f"(tolerance {100 * DIM_TOL:.0f} %) — part of the object is gone or added")
        # The volume speaks only when the dimensions agree (otherwise the height scaling has
        # already distorted it), when the model is sealed — a surface with holes voxelises to
        # a shell with no inside, and reads as a loss it is not; it already FAILs as open — and
        # when the reference is sealed too, for the same reason the other way round.
        if ref_empty:
            fails.append(f"the reference has no volume ({rv:.3g} mm3 voxelised, under one {size:.3g} mm voxel) "
                         f"— nothing to compare against")
        if not ref_sealed:
            warns.append(f"the reference is open ({rtopo['open_edges']} open, {rtopo['nonmanifold_edges']} "
                         f"non-manifold edges) — volume not compared, only dimensions")
        if dims_off or not sealed or ratio is None:
            r["reference"]["volume_compared"] = False
        elif ratio < 1 - VOL_TOL:
            fails.append(f"volume is {100 * ratio:.1f} % of the reference (tolerance {100 * VOL_TOL:.0f} %) "
                         f"— the object lost material")
        elif ratio > 1 + VOL_TOL:
            warns.append(f"volume is {100 * ratio:.1f} % of the reference — cavities filled or parts thickened")

    if o.slicer:
        if o.brim_mm < 0:
            die(f"--brim-mm must be 0 or more, not {o.brim_mm:g}")
        s = slicer(o.slicer, V, F, o.slicer_timeout, o.supports, o.brim_mm)
        s["supports"] = bool(o.supports)
        s["brim_mm"] = o.brim_mm
        if o.brim_mm > 0:
            warns.append(f"sliced with a {o.brim_mm:g} mm brim (--brim-mm): print it with one")
        r["slicer"] = s
        if o.supports:
            warns.append("sliced with automatic supports (--supports): print it with them, then remove them")
        if s["manifold"] != "yes":
            fails.append(f"PrusaSlicer: manifold = {s['manifold']} ({s['open_edges']} open edges)")
        if s["empty_layer_count"]:
            fails.append(f"PrusaSlicer: {s['empty_layer_count']} empty layer(s) — {s['empty_layers'][0]}")
        if s["floating_count"]:
            fails.append("PrusaSlicer: floating object part")
        other = [x for x in s["stability_issues"] if x != "Floating object part"]
        if other:
            hint = (" — try --brim-mm 5" if "Low bed adhesion" in other and not o.brim_mm > 0 else "")
            # a flat ceiling over ~10 mm: a change to make (print.md rule 6), not a line to report
            if "Long bridging extrusions" in other:
                hint += " — a flat ceiling over ~10 mm: shape it as a 45° cone or vault (print.md rule 6)"
            warns.append(f"PrusaSlicer stability issues: {', '.join(other)}{hint}")
        if s["slice_exit"] != 0 or not s["gcode"]:
            fails.append(f"PrusaSlicer: slicing failed (exit {s['slice_exit']})")
        clean = (s["manifold"] == "yes" and not s["empty_layer_count"] and not s["floating_count"]
                 and s["slice_exit"] == 0 and s["gcode"])
        # "none needed" next to "Floating bridge anchors" read as a contradiction: a fox's session
        # had to find --supports by itself. Those two warnings are about what hangs.
        hanging = [x for x in other if x in ("Floating bridge anchors", "Collapsing overhang")]
        if over_at is not None:
            warns[over_at] = (f"{overhang_pct} % of the area overhangs more than {OVERHANG_DEG:.0f}° — "
                              + ("sliced with supports" if o.supports else
                                 f"sliced without supports, but PrusaSlicer warns {', '.join(hanging)}: "
                                 f"check with --supports" if clean and hanging else
                                 "sliced clean without supports: none needed" if clean else
                                 "and the slice is not clean: see the FAIL lines, then try --supports"))

    r["verdict"] = "FAIL" if fails else "PASS"
    r["fails"], r["warnings"] = fails, warns
    # strict JSON: a NaN here is a bug to hear about, not a token to hand a parser
    print("PRINT_CHECK " + json.dumps(r, allow_nan=False))
    if o.json:
        with open(o.json, "w") as f:
            json.dump(r, f, indent=1, allow_nan=False)
    print(f"\n{os.path.basename(o.model)} · {o.process} · {r['dims_mm'][0]:.1f} × {r['dims_mm'][1]:.1f} × "
          f"{r['dims_mm'][2]:.1f} mm (scale {scale:.4g}) · {len(F):,} triangles · {nparts} part(s), "
          f"{r['closed_parts']} closed")
    for x in fails:
        print("  FAIL ", x)
    for x in warns:
        print("  WARN ", x)
    if thin["min_scale"] is not None:
        print(f"  SCALE do not shrink below {100 * thin['min_scale']:.0f} %"
              f"{' of the file' if abs(scale - 1.0) > 0.01 else ''} "
              f"({' × '.join(f'{x:g}' for x in thin['min_dims_mm'])} mm): "
              f"1 % more of the area would fall under {thin['min_wall_mm']} mm. Enlarging is safe.")
    print(f"\nVERDICT {r['verdict']}")
    sys.exit(FAIL if fails else PASS)


if __name__ == "__main__":
    main()
