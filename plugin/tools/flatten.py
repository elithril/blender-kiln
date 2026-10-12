"""Make the nearly flat surfaces of a model exactly flat, for printing — and touch nothing else.

    blender -b --factory-startup --python-exit-code 1 --python tools/flatten.py -- \\
        model.stl --out model_flat.stl [--tol-mm 0.3] [--bed] [--json report.json]

A model finished by hand often has faces that should be flat and are not: a top nudged by a
few tenths, a base a degree off. The slicer prints those as they are. This finds them, and
only them:

- faces are grouped into regions by distance to the region's plane (within --tol-mm), a face
  turning less than --grow-deg from it — so a bevel or a chamfer stays its own face;
- each region gets its best plane; it is flattened only if no vertex is further from that
  plane than --tol-mm, AND it is not a shape: a region a quadric fits much better than a
  plane (a dome, a strip of a cylinder), or whose distance to the plane varies smoothly from
  a vertex to its neighbours (a fold, a wave), or that runs on into its neighbours without an
  edge (a patch of a curved surface; --edge-deg), is kept, and said so;
- a vertex shared by several flattened or already flat regions lands where their planes
  meet (least squares), so edges and corners stay sharp; a vertex that would move past
  --tol-mm is held where it was, and counted;
- a flattened plane within --snap-deg of an axis becomes that axis: meant level, made level;
- --bed turns the model so its largest downward flat face lies on Z = 0 (only when that face
  is within --bed-deg of down), and reports the angle.

It never writes over the input, never fills a hole (print_check says where they are, the
slicer closes small ones), and never changes the triangle list: only vertices move. The same
loader and edge counts as print_check, so before and after are counted alike.
Exit 0 when the result has no open and no non-manifold edge, 3 when it still has some (they
were there before: flattening does not repair), 1 on an error.
"""
import json, math, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import print_check as pc                                          # noqa: E402


def args():
    p = pc.Parser(prog="flatten.py")
    p.add_argument("model")
    p.add_argument("--out", required=True, help="a new STL (mm); never the input")
    p.add_argument("--tol-mm", type=float, default=0.3, help="the furthest a vertex may move")
    p.add_argument("--min-area-mm2", type=float, default=25.0, help="smaller regions are left alone")
    p.add_argument("--curve-mm", type=float, default=0.02,
                   help="a region a quadric fits this much better than a plane is a curve, kept")
    p.add_argument("--grow-deg", type=float, default=8.0,
                   help="a face joins a region only if it turns less than this from its plane")
    p.add_argument("--edge-deg", type=float, default=30.0,
                   help="a region is a face only if its edges turn at least this much")
    p.add_argument("--snap-deg", type=float, default=1.0,
                   help="a flattened plane this close to an axis becomes that axis (0: off)")
    p.add_argument("--bed", action="store_true", help="lay the largest downward flat face on Z = 0")
    p.add_argument("--bed-deg", type=float, default=5.0)
    p.add_argument("--json")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return p.parse_args(argv)


def neighbours(F):
    """Faces sharing an edge with exactly one other face: (face, face) pairs."""
    e = np.sort(F[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    owner = np.repeat(np.arange(len(F)), 3)
    order = np.lexsort((e[:, 1], e[:, 0]))
    e, owner = e[order], owner[order]
    same = np.all(e[1:] == e[:-1], axis=1)
    pairs = []
    i = 0
    while i < len(e):
        j = i + 1
        while j < len(e) and same[j - 1]:
            j += 1
        if j - i == 2:
            pairs.append((owner[i], owner[i + 1]))
        i = j
    adj = [[] for _ in range(len(F))]
    for a, b in pairs:
        adj[a].append(b); adj[b].append(a)
    return adj


def regions(V, F, n, area, adj, tol, max_deg):
    """Region growing from the largest faces, by distance to the region's plane: a face joins
    while its three vertices lie within tol of that plane and it turns less than max_deg from
    it. The plane is refitted as the region doubles. Measured both ways: by orientation alone
    (10 degrees), a windmill nudged by 0.1-0.2 mm split into 4,453 regions too small to touch;
    by distance with a 30 degree turn allowed, a chest's 0.2 mm plank bevels were flattened
    away. 8 degrees keeps a 20 degree bevel and still joins a hand-placed face's triangles."""
    from collections import deque
    cos_max = math.cos(math.radians(max_deg))
    label = -np.ones(len(F), dtype=np.int64)
    out = []
    for seed in np.argsort(-area):
        if label[seed] >= 0 or area[seed] <= 0:
            continue
        rid = len(out); label[seed] = rid
        pn = n[seed].copy(); pd = float(pn @ V[F[seed]].mean(axis=0))
        members, queue, refit_at = [seed], deque([seed]), 2
        while queue:
            f = queue.popleft()
            for g in adj[f]:
                if label[g] >= 0 or area[g] <= 0 or float(n[g] @ pn) < cos_max:
                    continue
                if np.abs(V[F[g]] @ pn - pd).max() > tol:
                    continue
                label[g] = rid; members.append(g); queue.append(g)
                if len(members) >= refit_at:
                    P = V[np.unique(F[members])]
                    c = P.mean(axis=0)
                    nn = np.linalg.svd(P - c, full_matrices=False)[2][-1]
                    pn = nn if nn @ pn >= 0 else -nn
                    pd = float(pn @ c); refit_at *= 2
        out.append(np.array(members))
    return out, label


def fit(P, mean_normal):
    """Best plane through points P: (normal, offset, residuals along the normal, local u, v)."""
    c = P.mean(axis=0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    nrm = vt[-1]
    if nrm @ mean_normal < 0:
        nrm = -nrm
    e1 = vt[0]; e2 = np.cross(nrm, e1)
    Q = P - c
    return nrm, float(nrm @ c), Q @ nrm, Q @ e1, Q @ e2


def lay_on_bed(V, F, o):
    """Turn V so its largest downward face lying within --bed-deg of down, and within the
    tolerance of a plane, faces straight down. Done BEFORE flattening: flattening first snapped
    a box's sides upright while the box was still tilted, and its top came out 0.04 mm off level."""
    _, n, area = pc.face_data(V, F)
    regs, _ = regions(V, F, n, area, neighbours(F), o.tol_mm, o.grow_deg)
    best = None
    for r in regs:
        a = float(area[r].sum()); vid = np.unique(F[r])
        if a < o.min_area_mm2 or len(vid) < 3:
            continue
        nrm, _, h, _, _ = fit(V[vid], (n[r] * area[r][:, None]).sum(axis=0))
        if nrm[2] < -math.cos(math.radians(o.bed_deg)) and float(np.abs(h).max()) <= o.tol_mm:
            if best is None or a > best[0]:
                best = (a, nrm)
    if best is None:
        return V, 0.0
    nrm = best[1]; target = np.array([0.0, 0.0, -1.0])
    axis = np.cross(nrm, target); s = float(np.linalg.norm(axis)); c = float(nrm @ target)
    deg = math.degrees(math.atan2(s, c))
    if s > 1e-12:
        k = axis / s
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        R = np.eye(3) + s * K + (1 - c) * (K @ K)
        ctr = V.mean(axis=0)
        V = (V - ctr) @ R.T + ctr
    return V, deg


def main():
    o = args()
    if not os.path.exists(o.model):
        pc.die(f"{o.model}: no such file")
    if os.path.realpath(o.out) == os.path.realpath(o.model):
        pc.die(f"--out is the input ({o.out}): flatten.py never writes over the model it reads")
    if not (o.tol_mm > 0 and o.edge_deg > 0):
        pc.die("--tol-mm and --edge-deg must be above 0")
    V, F = pc.load(o.model)
    bed_deg = 0.0
    if o.bed:
        V, bed_deg = lay_on_bed(V, F, o)          # level first, then flatten in that frame
    V0 = V.copy()
    before = pc.topology(V, F)[0]
    _, n, area = pc.face_data(V, F)
    adj = neighbours(F)
    regs, label = regions(V, F, n, area, adj, o.tol_mm, o.grow_deg)
    cos_sharp = math.cos(math.radians(o.edge_deg))

    planes = []                                 # (normal, offset, vertex ids) to satisfy
    counts = dict(flattened=0, snapped=0, already_flat=0, curved=0, past_tolerance=0, small=0)
    flat_area = 0.0
    where = []                                  # every region that moved, for the report
    for r in regs:
        a = float(area[r].sum())
        vid = np.unique(F[r])
        if a < o.min_area_mm2 or len(vid) < 4:
            counts["small"] += 1
            continue
        mean_n = (n[r] * area[r][:, None]).sum(axis=0)
        nrm, d, h, u, v = fit(V[vid], mean_n)
        dev = float(np.abs(h).max())
        if dev < 1e-4:
            counts["already_flat"] += 1
            planes.append((nrm, d, vid, a, mean_n))
            continue
        if dev > o.tol_mm:                      # first: past the tolerance, whatever its shape
            counts["past_tolerance"] += 1
            continue
        # A piece of a larger surface: its neighbours across a soft edge, measured against the
        # same plane. Past the tolerance there, the region is a lucky flat patch of a rough or
        # curved surface (a top with 1 mm of noise left flat islands in it until this).
        rid = int(label[r[0]])
        nside = nrm if nrm @ mean_n >= 0 else -nrm
        ring = [g for f in r for g in adj[f] if label[g] != rid and float(n[g] @ nside) > cos_sharp]
        if ring and float(np.abs(V[np.unique(F[ring])] @ nrm - d).max()) > o.tol_mm:
            counts["past_tolerance"] += 1
            continue
        rms_p = float(np.sqrt((h ** 2).mean())); rms_q = rms_p; smooth = 0.0
        # A face meant flat is bounded by edges: a box's top meets its sides at 90 degrees. A
        # patch of a curved surface runs on into its neighbours. A strip of a two-ring cylinder,
        # or a patch of a ghost's side, has few vertices and no edge: never a face.
        out_n = [n[g] for f in r for g in adj[f] if label[g] != rid]
        soft = sum(1 for m in out_n if float(m @ (nrm if nrm @ mean_n >= 0 else -nrm)) > cos_sharp)
        if out_n and soft > 0.1 * len(out_n) and dev > o.curve_mm:
            counts["curved"] += 1
            continue
        # A quadric fits any 4 to 6 points exactly: the shape tests need 12.
        if len(vid) >= 12 and dev > o.curve_mm:
            # A curve is systematic: a quadric takes it away. Noise is not: a quadric barely helps.
            A = np.stack([u * u, u * v, v * v, u, v, np.ones_like(u)], axis=1)
            coef, *_ = np.linalg.lstsq(A, h, rcond=None)
            rms_q = float(np.sqrt(((h - A @ coef) ** 2).mean()))
            # A shape varies smoothly from a vertex to its neighbours; noise jumps. The ghost's
            # folds were neither a quadric nor noise, and became 0.3 mm facets until this test.
            pos = {int(x): k for k, x in enumerate(vid)}
            ed = np.unique(np.sort(F[r][:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)
            hi, hj = h[[pos[int(a)] for a in ed[:, 0]]], h[[pos[int(b)] for b in ed[:, 1]]]
            smooth = float((hi * hj).sum() / max(((hi ** 2 + hj ** 2) / 2).sum(), 1e-30))
            if rms_q < 0.5 * rms_p or smooth > 0.5:
                counts["curved"] += 1
                continue
        # A face meant flat is almost always meant level or upright: the best plane through a
        # jittered top was 0.14 degrees off, 0.1 mm across 40 mm. Snap it — a real slope is
        # further than --snap-deg from every axis and keeps its own plane.
        ax = np.eye(3)[int(np.argmax(np.abs(nrm)))] * np.sign(nrm[int(np.argmax(np.abs(nrm)))])
        if o.snap_deg > 0 and math.degrees(math.acos(min(1.0, float(nrm @ ax)))) <= o.snap_deg:
            nrm = ax; d = float((V[vid] @ nrm).mean()); counts["snapped"] += 1
        counts["flattened"] += 1
        flat_area += a
        c = V[vid].mean(axis=0)
        where.append(dict(centre_mm=[round(float(x), 2) for x in c], normal=[round(float(x), 3) for x in nrm],
                          area_mm2=round(a, 1), deviation_mm=round(dev, 3),
                          plane_rms_mm=round(rms_p, 4), quadric_rms_mm=round(rms_q, 4),
                          neighbour_correlation=round(smooth, 3)))
        planes.append((nrm, d, vid, a, mean_n))

    # Every constrained vertex lands where its planes meet, as close as possible to where it was.
    lam = 1e-9
    M = np.zeros((len(V), 3, 3)); b = np.zeros((len(V), 3)); hit = np.zeros(len(V), bool)
    for nrm, d, vid, _, _ in planes:
        M[vid] += np.outer(nrm, nrm); b[vid] += nrm * d; hit[vid] = True
    idx = np.flatnonzero(hit)
    if len(idx):
        A = M[idx] + lam * np.eye(3)
        V[idx] = np.linalg.solve(A, (b[idx] + lam * V0[idx])[..., None])[..., 0]
    move = np.linalg.norm(V - V0, axis=1)
    held = move > o.tol_mm + 1e-9
    V[held] = V0[held]

    if o.bed:
        V[:, 2] -= V[:, 2].min()

    after = pc.topology(V, F)[0]
    pc.write_stl(o.out, V, F)
    total_area = float(area.sum())
    rep = dict(model=os.path.abspath(o.model), out=os.path.abspath(o.out), tol_mm=o.tol_mm,
               regions=len(regs), regions_flattened=counts["flattened"],
               regions_snapped_to_axis=counts["snapped"], regions_already_flat=counts["already_flat"], regions_curved=counts["curved"],
               regions_past_tolerance=counts["past_tolerance"], regions_small=counts["small"],
               area_flattened_pct=round(100 * flat_area / max(total_area, 1e-30), 2),
               max_move_mm=round(float(move[~held].max()) if (~held).any() else 0.0, 4),   # by flattening, before --bed
               vertices_moved=int(((move > 1e-6) & ~held).sum()), vertices_held=int(held.sum()),
               bed_rotation_deg=round(bed_deg, 3), flattened=where,
               before={k: before[k] for k in ("open_edges", "nonmanifold_edges", "inconsistent_edges")},
               after={k: after[k] for k in ("open_edges", "nonmanifold_edges", "inconsistent_edges")})
    print("FLATTEN " + json.dumps(rep))
    print(f"{os.path.basename(o.model)} → {os.path.basename(o.out)}: {counts['flattened']} region(s) flattened "
          f"({rep['area_flattened_pct']} % of the area), {counts['already_flat']} already flat, "
          f"{counts['curved']} curved kept, {counts['past_tolerance']} past {o.tol_mm} mm kept; "
          f"largest move {rep['max_move_mm']} mm, {rep['vertices_held']} vertex(es) held"
          + (f"; laid on the bed, turned {rep['bed_rotation_deg']}°" if o.bed else ""))
    if after["open_edges"] or after["nonmanifold_edges"]:
        print(f"  still {after['open_edges']} open and {after['nonmanifold_edges']} non-manifold edges "
              f"(before: {before['open_edges']}, {before['nonmanifold_edges']}) — flattening does not repair; "
              f"run print_check", file=sys.stderr)
    if o.json:
        with open(o.json, "w") as f:
            json.dump(rep, f, indent=1)
    sys.exit(3 if after["open_edges"] or after["nonmanifold_edges"] else 0)


if __name__ == "__main__":
    main()
