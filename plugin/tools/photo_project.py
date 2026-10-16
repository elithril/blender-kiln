"""Bring the reference photo's own pixels onto the model, where the photo can be trusted.

    blender -b --factory-startup --python-exit-code 1 --python tools/photo_project.py -- \\
        --reference ref.png --model asset_final.glb --hdri studio_small_09_1k.hdr --out project/ \\
        --azimuth 50 --elevation 20 [--view front] [--exclude NAME ...] [--erase-stencil '#RRGGBB' ...] \\
        [--min-iou 0.95] [--facing 0.6] [--samples 64]

An OPTIONAL step after the last fidelity_check round, for markings a script copies badly —
text, a logo, precise wear (reference-fidelity.md § 7, references/photo-projection.md):

- the camera: fidelity_check's own (--view, --azimuth, --elevation: orthographic, scaled to
  the photo's height), then fitted to the photo's silhouette — azimuth, elevation, roll and
  perspective. Below --min-iou (0.95) the photo would land off the model: refused, exit 1;
- each texel of every base-colour texture is projected into the photo and given a confidence:
  seen (depth), facing the camera (full trust at --facing, ≥ 0.6, fading in from 0.35 below),
  away from the model's outline, from inner depth edges and from the matte's edge, inside the
  matte. Where it is trusted the photo wins; elsewhere the model keeps its texture;
- the photo is brought to the model's exposure first: one gain, in linear luminance (the median
  ratio over the texels where both are trusted). The photo's raw pixels are never used — they carry its light;
- --exclude NAME (object or material, glob, case-insensitive): parts that moved or sit
  elsewhere than in the photo (a handle, a lid) get nothing; they still hide what is behind;
- --erase-stencil COLOUR: the scripted marking of that colour is erased (filled from the
  paint around it) wherever the photo is used, so the photo's text does not land beside it.

Writes into --out: {model}_projected.glb (the input's own compression kept; a .blend also
gets {model}_projected.blend), textures/ (the new base colours), confidence/ (white: photo
used), photo_view.png (photo | before | after | confidence, from the fitted camera),
other_angles.png (two other angles, before above after) and photo_project.json — SSIM and
ΔE76 from the photo's view before → after, the coverage, the camera. Prints one
`PHOTO_PROJECT {...}` line. Exit 0 on a projection, 1 on a refusal or an error.

The photo-view numbers are partly circular: the photo is measured against itself where it was
pasted. They say the projection landed; the two other angles say whether it hurt the model.

The confidence tests, their defaults and the gutter growth follow AssetFurnace's Pixel Match
(image-to-3dlab, image_to_3dlab/photo_paint.py, Copyright 2026 Bingeljell and image-to-3dlab
contributors, Apache License 2.0 — plugin/NOTICE). Changed here: a camera fitted from
fidelity_check's instead of a generator's saved one, the exposure gain instead of the raw
pixels, the exclusions and the stencil erase, Blender's own mesh and image I/O.
"""
import argparse, fnmatch, json, math, os, struct, sys

import bpy
import numpy as np
from mathutils import Matrix

VIEWS = {"front": 0.0, "right": 90.0, "back": 180.0, "left": -90.0}
FACING_FADE = 0.35            # the fade starts this far below --facing (0.25 for 0.6, their default)
EDGE, CUT, INNER = 6 / 768, 8 / 768, 8 / 768   # shares of the photo's width (their 6, 8, 8 px at 768)
INNER_JUMP, DEPTH_TOL = 0.02, 0.004            # shares of the model's size
TRUSTED = 0.9                 # a texel this confident counts for the gain and the coverage
GUTTER = 4                    # texels the change grows into the UV gutter (no seam on filtering)
MAX_SIDE = 2048               # a larger photo is reduced to this
FIT_SIDE = 256                # the silhouette fit runs at this size
FIT_TURN, FIT_ROLL = 10.0, 5.0  # degrees the fit may move azimuth / elevation, and roll
STENCIL_TOL = 18.0            # ΔE76 from --erase-stencil's colour


def die(msg, report=None, out=None):
    if report is not None and out:
        report["status"] = "refused"; report["reason"] = msg
        json.dump(report, open(os.path.join(out, "photo_project.json"), "w"), indent=1)
    print(f"photo_project: {msg}", file=sys.stderr)
    sys.exit(1)


def args():
    p = argparse.ArgumentParser(prog="photo_project.py")
    p.error = lambda m: die(m)                     # exit 1, as every other refusal
    p.add_argument("--reference", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--hdri", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--view", default="front", choices=sorted(VIEWS))
    p.add_argument("--azimuth", type=float, default=0.0)
    p.add_argument("--elevation", type=float, default=0.0)
    p.add_argument("--exclude", nargs="+", action="extend", default=[])
    p.add_argument("--erase-stencil", nargs="+", action="extend", default=[])
    p.add_argument("--min-iou", type=float, default=0.95)
    p.add_argument("--facing", type=float, default=0.6)
    p.add_argument("--samples", type=int, default=64)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    for f in (a.reference, a.model, a.hdri):
        if not os.path.isfile(f):
            die(f"no such file: {f}")
    if a.facing < 0.6 or a.facing > 1:
        die(f"--facing {a.facing}: below 0.6 a surface seen at a slant takes the photo "
            "(a stencil at facing 0.59 came out doubled on the ammo box)")
    a.stencil = [parse_colour(c) for c in a.erase_stencil]
    os.makedirs(a.out, exist_ok=True)
    return a


def parse_colour(c):
    s = c.strip().lstrip("#")
    try:
        v = [int(s[i:i + 2], 16) for i in (0, 2, 4)] if len(s) == 6 and "," not in s else [int(x) for x in s.split(",")]
        assert len(v) == 3 and all(0 <= x <= 255 for x in v)
    except (ValueError, AssertionError):
        die(f"--erase-stencil {c!r}: a colour is #RRGGBB or R,G,B (sRGB, 0-255)")
    return np.array(v, np.float32) / 255


# ── images ─────────────────────────────────────────────────────────────────────────────

def load_rgba(path):
    """(H, W, 4) floats, top row first, as stored (sRGB values for an 8-bit image)."""
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(im)
    return a


def save_rgba(arr, path):
    arr = np.clip(arr, 0, 1).astype(np.float32)
    if arr.ndim == 2:
        arr = np.dstack([arr] * 3)
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones(arr.shape[:2] + (1,), np.float32)], -1)
    h, w = arr.shape[:2]
    img = bpy.data.images.new("_save", w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).ravel())
    img.filepath_raw = path; img.file_format = "PNG"; img.save()
    bpy.data.images.remove(img)


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((np.clip(c, 0, None) + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def lab(rgb):
    xyz = srgb_to_lin(rgb) @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722],
                                       [0.0193, 0.1192, 0.9505]]).T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def gauss(img, s=1.5, r=5):
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    p = np.pad(img, r, mode="edge")
    t = sum(k[i] * p[i:i + img.shape[0], :] for i in range(2 * r + 1))
    return sum(k[i] * t[:, i:i + img.shape[1]] for i in range(2 * r + 1))


def compare(R, M):
    """Inside both alphas: MAE (sRGB, 0-255), mean ΔE76, SSIM of luminance (gaussian 1.5)."""
    mask = (R[..., 3] > 0.99) & (M[..., 3] > 0.99)
    if mask.sum() < 50:
        return dict(pixels=int(mask.sum()))
    x, y = R[..., :3] @ LUM, M[..., :3] @ LUM
    mx, my = gauss(x), gauss(y)
    vx, vy, cxy = gauss(x * x) - mx ** 2, gauss(y * y) - my ** 2, gauss(x * y) - mx * my
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    ssim = ((2 * mx * my + C1) * (2 * cxy + C2)) / ((mx ** 2 + my ** 2 + C1) * (vx + vy + C2))
    dE = np.linalg.norm(lab(R[..., :3]) - lab(M[..., :3]), axis=-1)
    return dict(pixels=int(mask.sum()), ssim=round(float(ssim[mask].mean()), 4),
                dE76=round(float(dE[mask].mean()), 3),
                mae_srgb=round(float(np.abs(R[..., :3] - M[..., :3])[mask].mean() * 255), 3))


def erode_dist(mask, n):
    """Steps (up to n, 4-neighbour) from each True pixel to the nearest False one."""
    d = np.zeros(mask.shape, np.int32); cur = mask.copy()
    for k in range(1, n + 1):
        d[cur] = k
        nxt = cur.copy()
        nxt[1:] &= cur[:-1]; nxt[:-1] &= cur[1:]; nxt[:, 1:] &= cur[:, :-1]; nxt[:, :-1] &= cur[:, 1:]
        nxt[0] = nxt[-1] = False; nxt[:, 0] = nxt[:, -1] = False
        cur = nxt
    d[cur] = n
    return d


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / max(hi - lo, 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def bilinear(img, x, y):
    H, W = img.shape[:2]
    fx = np.clip(x - 0.5, 0, W - 1); fy = np.clip(y - 0.5, 0, H - 1)
    x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int)
    x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
    tx = (fx - x0)[:, None]; ty = (fy - y0)[:, None]
    return (img[y0, x0] * (1 - tx) + img[y0, x1] * tx) * (1 - ty) + (img[y1, x0] * (1 - tx) + img[y1, x1] * tx) * ty


def grow(values, known, steps, inside=None):
    """Fill unknown pixels from their known 4-neighbours, `steps` rings (inside `inside` only)."""
    values, known = values.copy(), known.copy()
    for _ in range(steps):
        acc = np.zeros_like(values); n = np.zeros(known.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = np.roll(np.roll(known, dy, 0), dx, 1)
            acc += np.roll(np.roll(values, dy, 0), dx, 1) * k[..., None]; n += k
        new = (~known) & (n > 0)
        if inside is not None:
            new &= inside
        if not new.any():
            break
        values[new] = acc[new] / n[new, None]; known |= new
    return values, known


# ── rasteriser ─────────────────────────────────────────────────────────────────────────

def raster(tri, depth, H, W, want_bary=False, count=False):
    """Triangles (F,3,2) in pixels (x right, y down, centres at +0.5); nearest depth wins.
    Returns face id (-1: empty), barycentrics (H,W,3) or None, depth, and (count=True) how
    many triangles cover each pixel's interior — two means two surfaces share that pixel."""
    zb = np.full(H * W, np.inf); fid = np.full(H * W, -1, np.int64)
    bary = np.zeros((H * W, 3)) if want_bary else None
    cnt = np.zeros(H * W, np.int32) if count else None
    x, y = tri[..., 0], tri[..., 1]
    den = (y[:, 1] - y[:, 2]) * (x[:, 0] - x[:, 2]) + (x[:, 2] - x[:, 1]) * (y[:, 0] - y[:, 2])
    xa = np.clip(np.floor(x.min(1)), 0, W - 1).astype(int); xb = np.clip(np.ceil(x.max(1)), 0, W - 1).astype(int)
    ya = np.clip(np.floor(y.min(1)), 0, H - 1).astype(int); yb = np.clip(np.ceil(y.max(1)), 0, H - 1).astype(int)
    ok = (np.abs(den) > 1e-12) & (x.max(1) >= 0) & (x.min(1) <= W) & (y.max(1) >= 0) & (y.min(1) <= H)
    size = np.maximum(xb - xa, yb - ya) + 1
    cand = []
    lo = 0
    for B in (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
        sel = np.flatnonzero(ok & (size > lo) & (size <= B)); lo = B
        step = max(1, 4_000_000 // (B * B))
        for c in range(0, len(sel), step):
            f = sel[c:c + step]
            gx = xa[f, None, None] + np.arange(B)[None, None, :]
            gy = ya[f, None, None] + np.arange(B)[None, :, None]
            px, py = gx + 0.5, gy + 0.5
            X, Y, d = x[f][:, :, None, None], y[f][:, :, None, None], den[f][:, None, None]
            l0 = ((Y[:, 1] - Y[:, 2]) * (px - X[:, 2]) + (X[:, 2] - X[:, 1]) * (py - Y[:, 2])) / d
            l1 = ((Y[:, 2] - Y[:, 0]) * (px - X[:, 2]) + (X[:, 0] - X[:, 2]) * (py - Y[:, 2])) / d
            l2 = 1 - l0 - l1
            ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6) & (gx <= xb[f, None, None]) & (gy <= yb[f, None, None])
            if not ins.any():
                continue
            D = depth[f]
            z = l0 * D[:, 0, None, None] + l1 * D[:, 1, None, None] + l2 * D[:, 2, None, None]
            idx = (gy * W + gx)[ins]
            np.minimum.at(zb, idx, z[ins])
            if count:
                interior = ins & (l0 > 1e-3) & (l1 > 1e-3) & (l2 > 1e-3)
                np.add.at(cnt, (gy * W + gx)[interior], 1)
            ff = np.broadcast_to(f[:, None, None], ins.shape)[ins]
            cand.append((idx, z[ins], ff, np.stack([l0[ins], l1[ins], l2[ins]], -1) if want_bary else None))
    for idx, z, ff, b in cand:
        win = z <= zb[idx]
        fid[idx[win]] = ff[win]
        if want_bary:
            bary[idx[win]] = b[win]
    return (fid.reshape(H, W), None if bary is None else bary.reshape(H, W, 3), zb.reshape(H, W),
            None if cnt is None else cnt.reshape(H, W))


# ── camera ─────────────────────────────────────────────────────────────────────────────

class Cam:
    """Orbit camera around `ctr`: az toward +X from the front (-Y), el up, roll about the view
    axis; t = 1/distance (0: orthographic). Image = the plane scaled by s, shifted by tx, ty."""

    def __init__(self, ctr, az, el, roll=0.0, t=0.0):
        a, e, r = map(math.radians, (az, el, roll))
        d = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
        f = -d
        right = np.cross(f, [0, 0, 1.0]); right /= np.linalg.norm(right)
        up = np.cross(right, f)
        cr, sr = math.cos(r), math.sin(r)
        self.right, self.up = cr * right + sr * up, -sr * right + cr * up
        self.f, self.ctr, self.t = f, np.asarray(ctr, float), float(t)
        self.az, self.el, self.roll = az, el, roll
        self.s, self.tx, self.ty = 1.0, 0.0, 0.0

    @property
    def position(self):
        return None if self.t == 0 else self.ctr - self.f / self.t

    def plane(self, P):
        q = P - self.ctr
        x, y, z = q @ self.right, q @ self.up, q @ self.f
        k = 1.0 / (1.0 + self.t * z)
        return x * k, -y * k, z

    def to_px(self, P):
        x, y, z = self.plane(P)
        return self.s * x + self.tx, self.s * y + self.ty, z

    def to_cam(self, P):
        if self.t == 0:
            return np.broadcast_to(-self.f, P.shape)
        v = self.position - P
        return v / np.linalg.norm(v, axis=-1, keepdims=True)

    def screen_depth(self, z):     # interpolates linearly on screen (1/w for a perspective)
        return z if self.t == 0 else -1.0 / (1.0 + self.t * z)

    def depth_back(self, d):
        return d if self.t == 0 else (-1.0 / d - 1.0) / self.t

    def fit_box(self, P, box, height_only=False):
        x, y, _ = self.plane(P)
        X0, X1, Y0, Y1 = box
        s = (Y1 - Y0) / (y.max() - y.min())
        if not height_only:
            s = 0.5 * (s + (X1 - X0) / (x.max() - x.min()))
        self.s = s
        self.tx = (X0 + X1) / 2 - s * (x.max() + x.min()) / 2
        self.ty = (Y0 + Y1) / 2 - s * (y.max() + y.min()) / 2
        return self

    def describe(self):
        return dict(azimuth=round(self.az, 2), elevation=round(self.el, 2), roll=round(self.roll, 2),
                    distance_m=None if self.t == 0 else round(1 / self.t, 4))


def silhouette(cam, P, H, W, scale=1.0):
    x, y, z = cam.to_px(P.reshape(-1, 3))
    tri = (np.stack([x, y], -1) * scale).reshape(-1, 3, 2)
    return raster(tri, np.zeros((len(tri), 3)), H, W)[0] >= 0


def iou(a, b):
    return float((a & b).sum() / max((a | b).sum(), 1))


def nelder_mead(f, x0, steps, iters=80):
    pts = [np.array(x0, float)] + [np.array(x0, float) + np.eye(len(x0))[i] * steps[i] for i in range(len(x0))]
    vals = [-f(p) for p in pts]
    for _ in range(iters):
        o = np.argsort(vals); pts = [pts[i] for i in o]; vals = [vals[i] for i in o]
        c = np.mean(pts[:-1], 0)
        xr = c + (c - pts[-1]); fr = -f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - pts[-1]); fe = -f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c); fc = -f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [pts[0] + 0.5 * (p - pts[0]) for p in pts[1:]]
                vals = [vals[0]] + [-f(p) for p in pts[1:]]
    i = int(np.argmin(vals))
    return pts[i], -vals[i]


def fit_camera(P, ctr, size, az0, el0, matte):
    """fidelity_check's camera, then azimuth / elevation / roll / perspective fitted on the matte."""
    H, W = matte.shape
    ys, xs = np.nonzero(matte)
    box = (xs.min(), xs.max() + 1, ys.min(), ys.max() + 1)
    start = Cam(ctr, az0, el0).fit_box(P, box, height_only=True)
    start_iou = iou(silhouette(start, P, H, W), matte)
    k = FIT_SIDE / max(H, W)
    h, w = max(1, round(H * k)), max(1, round(W * k))
    small = matte[(np.arange(h) / k).astype(int).clip(0, H - 1)][:, (np.arange(w) / k).astype(int).clip(0, W - 1)]

    def score(p):
        az, el, roll, t = p
        # Bounded near the camera the session read: unbounded, a box 40 % too long fitted
        # 0.955 by turning the camera 30° and stepping it back — fitting the shape error away.
        if t < 0 or t > 3.0 / size or abs(el) > 85 or abs(az - az0) > FIT_TURN or abs(el - el0) > FIT_TURN \
                or abs(roll) > FIT_ROLL:
            return 0.0
        return iou(silhouette(Cam(ctr, az, el, roll, t).fit_box(P, box), P, h, w, k), small)

    best = None
    for da in (-10, -5, 0, 5, 10):
        for de in (-10, -5, 0, 5, 10):
            for t in (0.0, 0.5 / size, 1.0 / size):
                s = score((az0 + da, el0 + de, 0.0, t))
                if best is None or s > best[0]:
                    best = (s, [az0 + da, el0 + de, 0.0, t])
    x, _ = nelder_mead(score, best[1], [3, 3, 2, 0.3 / size])
    cam = Cam(ctr, *map(float, x)).fit_box(P, box)
    return start, start_iou, cam, iou(silhouette(cam, P, H, W), matte), box


# ── scene ──────────────────────────────────────────────────────────────────────────────

def open_model(path):
    if path.lower().endswith((".glb", ".gltf")):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    for o in sc.objects:
        if o.type in ("CAMERA", "LIGHT"):
            o.hide_render = True
    shapes = {pb.custom_shape for a in sc.objects if a.type == "ARMATURE" for pb in a.pose.bones if pb.custom_shape}
    meshes = [o for o in sc.objects if o.type == "MESH" and o not in shapes and not o.hide_render]
    if not meshes:
        die("no renderable mesh in the model")
    return sc, meshes


def base_image(mat):
    """The image texture feeding a material's Principled Base Color, walking upstream."""
    if not mat or not mat.node_tree:
        return None
    b = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is None or not b.inputs["Base Color"].is_linked:
        return None
    todo, seen = [b.inputs["Base Color"].links[0].from_node], set()
    while todo:
        n = todo.pop(0)
        if n.name in seen:
            continue
        seen.add(n.name)
        if n.type == "TEX_IMAGE" and n.image:
            return n.image
        todo += [l.from_node for i in n.inputs if i.is_linked for l in i.links]
    return None


def gather(meshes):
    """World triangles: positions, corner normals, UVs, and per triangle its object, material, image."""
    dg = bpy.context.evaluated_depsgraph_get()
    P, N, UV, OB, MA, IM = [], [], [], [], [], []
    for ob in meshes:
        ev = ob.evaluated_get(dg); me = ev.to_mesh()
        me.calc_loop_triangles()
        lt = len(me.loop_triangles)
        if not lt:
            ev.to_mesh_clear(); continue
        mw = np.array(ob.matrix_world); nm = np.array(ob.matrix_world.to_3x3().inverted().transposed())
        co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        nl = len(me.loops)
        cn = np.zeros(nl * 3); me.corner_normals.foreach_get("vector", cn)
        cn = cn.reshape(-1, 3) @ nm.T; cn /= np.maximum(np.linalg.norm(cn, axis=1, keepdims=True), 1e-12)
        uvl = me.uv_layers.active
        uv = np.zeros(nl * 2)
        if uvl:
            uvl.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        lv = np.zeros(lt * 3, np.int64); me.loop_triangles.foreach_get("vertices", lv)
        ll = np.zeros(lt * 3, np.int64); me.loop_triangles.foreach_get("loops", ll)
        mi = np.zeros(lt, np.int64); me.loop_triangles.foreach_get("material_index", mi)
        slots = [s.material for s in ob.material_slots] or [None]
        mats = [slots[min(i, len(slots) - 1)] for i in mi]
        P.append(co[lv.reshape(-1, 3)]); N.append(cn[ll.reshape(-1, 3)]); UV.append(uv[ll.reshape(-1, 3)])
        OB += [ob.name] * lt
        MA += [m.name if m else "" for m in mats]
        IM += [(base_image(m) if (m and uvl) else None) for m in mats]
        ev.to_mesh_clear()
    return np.concatenate(P), np.concatenate(N), np.concatenate(UV), np.array(OB), np.array(MA), IM


def glb_info(path):
    """Draco and WebP in the input GLB: the output keeps them."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(20)
            n = struct.unpack("<I", head[12:16])[0]
            doc = json.loads(fh.read(n))
    except (OSError, ValueError, struct.error):
        return False, False
    draco = "KHR_draco_mesh_compression" in doc.get("extensionsUsed", [])
    webp = any(i.get("mimeType") == "image/webp" for i in doc.get("images", [])) \
        or "EXT_texture_webp" in doc.get("extensionsUsed", [])
    return draco, webp


def setup_render(sc, hdri, samples):
    w = bpy.data.worlds.new("_project_hdri"); sc.world = w
    env = w.node_tree.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdri)
    w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
    sc.render.engine = "CYCLES"; sc.cycles.samples = samples; sc.cycles.device = "CPU"
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = True; sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_percentage = 100
    sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1


def shoot(sc, cam, W, H, path):
    """A Blender camera reproducing Cam's pixel mapping, rendered to `path`."""
    data = bpy.data.cameras.new("_project_cam"); ob = bpy.data.objects.new("_project_cam", data)
    sc.collection.objects.link(ob); sc.camera = ob
    big = max(W, H)
    D = 1.0 / cam.t if cam.t else 10.0
    m = np.eye(4); m[:3, :3] = np.stack([cam.right, cam.up, -cam.f], 1); m[:3, 3] = cam.ctr - cam.f * D
    ob.matrix_world = Matrix(m.tolist())
    data.sensor_fit = "HORIZONTAL" if W >= H else "VERTICAL"; data.sensor_width = data.sensor_height = 36.0
    if cam.t:
        data.type = "PERSP"; data.lens = cam.s * D * 36.0 / big
    else:
        data.type = "ORTHO"; data.ortho_scale = big / cam.s
    data.shift_x = (W / 2 - cam.tx) / big
    data.shift_y = (cam.ty - H / 2) / big
    data.clip_start, data.clip_end = 0.001, D * 10 + 100
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(ob); bpy.data.cameras.remove(data)
    return load_rgba(path)


def renders(sc, cams, out, tag):
    os.makedirs(os.path.join(out, "renders"), exist_ok=True)
    return {k: shoot(sc, c, w, h, os.path.join(out, "renders", f"{tag}_{k}.png")) for k, (c, w, h) in cams.items()}


def on_grey(a):
    return a[..., :3] * a[..., 3:4] + 0.22 * (1 - a[..., 3:4])


def sheet(tiles, path):
    h = max(t.shape[0] for t in tiles); w = max(t.shape[1] for t in tiles)
    tiles = [np.pad(t, ((0, h - t.shape[0]), (0, w - t.shape[1]), (0, 0)), constant_values=1) for t in tiles]
    save_rgba(np.concatenate([np.pad(t, ((4, 4), (4, 4), (0, 0)), constant_values=1) for t in tiles], 1), path)


# ── main ───────────────────────────────────────────────────────────────────────────────

def main():
    a = args()
    out = a.out
    report = dict(tool="photo_project", reference=a.reference, model=a.model, status="running", warnings=[])

    ref = load_rgba(a.reference)
    alpha = ref[..., 3] > 0.5
    if not alpha.any():
        die(f"{a.reference} has no opaque pixel — a reference needs alpha")
    if alpha.all():
        die(f"{a.reference} has no transparent pixel — cut the object out first "
            "(reference-fidelity.md § 2, Cut the photo out)")
    if max(ref.shape[:2]) > MAX_SIDE:
        k = math.ceil(max(ref.shape[:2]) / MAX_SIDE)
        h, w = ref.shape[0] // k, ref.shape[1] // k
        ref = ref[:h * k, :w * k].reshape(h, k, w, k, 4).mean((1, 3))
        report["warnings"].append(f"photo reduced {k}x to {w}x{h}")
    H, W = ref.shape[:2]
    matte = ref[..., 3] > 0.5

    sc, meshes = open_model(a.model)
    P, N, UV, OB, MA, IM = gather(meshes)
    allp = P.reshape(-1, 3)
    lo, hi = allp.min(0), allp.max(0); ctr = (lo + hi) / 2; size = float(np.linalg.norm(hi - lo))

    # Exclusions: an object or a material, by glob. A pattern matching nothing is a typo.
    excl = np.zeros(len(P), bool); matched = {}
    for pat in a.exclude:
        hit = np.array([fnmatch.fnmatch(o.lower(), pat.lower()) or fnmatch.fnmatch(m.lower(), pat.lower())
                        for o, m in zip(OB, MA)])
        if not hit.any():
            die(f"--exclude {pat!r} matches no object or material — objects: {sorted(set(OB))}, "
                f"materials: {sorted(set(MA) - {''})}")
        excl |= hit; matched[pat] = sorted(set(OB[hit]))
    report["excluded"] = matched

    images = {}
    for i, im in enumerate(IM):
        if im is not None and not excl[i]:
            images.setdefault(im.name, (im, []))[1].append(i)
    if not images:
        die("no base-colour image texture on the parts left to project — the photo has nowhere to go "
            "(a plain material has no texels; bake it to a texture first)")
    untextured = sorted({m for m, im, e in zip(MA, IM, excl) if im is None and not e and m})
    if untextured:
        report["warnings"].append(f"materials without a base-colour texture, left as they are: {untextured}")

    # Camera: fidelity_check's, then fitted to the silhouette.
    az0 = VIEWS[a.view] + a.azimuth
    start, start_iou, cam, fit_iou, box = fit_camera(P, ctr, size, az0, a.elevation, matte)
    report["camera"] = dict(fidelity_check=dict(start.describe(), iou=round(start_iou, 4)),
                            fitted=dict(cam.describe(), iou=round(fit_iou, 4)), min_iou=a.min_iou)
    print(f"camera: fidelity_check's IoU {start_iou:.3f} -> fitted IoU {fit_iou:.3f} "
          f"(az {cam.az:.1f}, el {cam.el:.1f}, roll {cam.roll:.1f}, "
          f"{'orthographic' if cam.t == 0 else f'{1 / cam.t:.2f} m away'})")
    if fit_iou < a.min_iou:
        die(f"the fitted camera's silhouette IoU is {fit_iou:.3f}, under {a.min_iou} — the photo would land "
            "off the model (wrong proportions, a part placed elsewhere, or the wrong --view / --azimuth / "
            "--elevation). Fix the shape first, or exclude nothing and do not project", report, out)

    # The views for the control renders: the photo's, and two others (a quarter turn, the back).
    other = lambda az, el: Cam(ctr, az, el, 0, cam.t).fit_box(P, (48, 720, 48, 720))
    views = {"photo": (cam, W, H), "turn": (other(cam.az - 90, 20), 768, 768),
             "back": (other(cam.az + 180, 30), 768, 768)}
    setup_render(sc, a.hdri, a.samples)
    before = renders(sc, views, out, "before")

    # The photo camera's own depth, and the masks the confidence fades from.
    x, y, z = cam.to_px(allp)
    fid, _, zb, _ = raster(np.stack([x, y], -1).reshape(-1, 3, 2), cam.screen_depth(z).reshape(-1, 3), H, W)
    seen = fid >= 0
    zc = np.where(seen, cam.depth_back(np.where(seen, zb, -1.0 if cam.t else 0.0)), np.inf)
    edge = smoothstep(erode_dist(seen, max(1, round(EDGE * W))) / max(1, round(EDGE * W)), 0, 1)
    jump = np.zeros_like(seen)
    for sa, sb in (((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
                   ((slice(None), slice(1, None)), (slice(None), slice(None, -1)))):
        both = seen[sa] & seen[sb]
        diff = np.subtract(zc[sa], zc[sb], out=np.zeros(both.shape), where=both)
        j = both & (np.abs(diff) > INNER_JUMP * size)
        jump[sa] |= j; jump[sb] |= j
    n_in, n_cut = max(1, round(INNER * W)), max(1, round(CUT * W))
    inner = smoothstep(erode_dist(~jump, n_in) / n_in, 0, 1)
    cut = smoothstep(erode_dist(matte, n_cut) / n_cut, 0, 1)
    view_w = edge * inner * cut * ref[..., 3]
    lo_f = a.facing - FACING_FADE

    per, trusted_own, trusted_photo = {}, [], []
    for name, (img, tris) in images.items():
        tris = np.array(tris)
        tw, th = img.size
        if not img.has_data and not img.packed_file and not os.path.exists(bpy.path.abspath(img.filepath)):
            die(f"texture {name} is not loaded — pack it first (bpy.ops.file.pack_all())")
        tex = np.array(img.pixels[:], np.float32).reshape(th, tw, -1)[::-1].copy()
        if tex.shape[2] == 3:
            tex = np.concatenate([tex, np.ones(tex.shape[:2] + (1,), np.float32)], -1)
        uvpx = np.stack([UV[tris, :, 0] * tw, (1 - UV[tris, :, 1]) * th], -1)
        tf, bary, _, cnt = raster(uvpx, np.zeros((len(tris), 3)), th, tw, want_bary=True, count=True)
        cov = tf >= 0
        f = tris[tf[cov]]; bc = bary[cov]
        pts = (bc[:, :, None] * P[f]).sum(1)
        nrm = (bc[:, :, None] * N[f]).sum(1); nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        px, py, pz = cam.to_px(pts)
        ix, iy = np.floor(px).astype(int), np.floor(py).astype(int)
        inside = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        ix, iy = np.clip(ix, 0, W - 1), np.clip(iy, 0, H - 1)
        vis = inside & (pz <= zc[iy, ix] + DEPTH_TOL * size)
        facing = np.maximum((nrm * cam.to_cam(pts)).sum(1), 0)
        shared = cnt[cov] > 1                      # one texel, two surfaces: painting it paints both
        w = vis * smoothstep(facing, lo_f, a.facing) * view_w[iy, ix] * ~shared
        photo = bilinear(ref[..., :3], px, py)
        own = tex[..., :3][cov]
        per[name] = dict(img=img, tex=tex, cov=cov, w=w, photo=photo, own=own, shared=int(shared.sum()))
        t = w > TRUSTED
        trusted_own.append(own[t]); trusted_photo.append(photo[t])

    to, tp = np.concatenate(trusted_own), np.concatenate(trusted_photo)
    if len(to) < 50:
        die(f"only {len(to)} texels are trusted — the photo does not face any textured part squarely "
            "enough to project", report, out)
    # The median of the per-texel ratios: a mean is pulled by what the photo has and the model
    # lacks — a white letter on 13 % of a face set it at 1.25 for a true 2.6.
    lo_, lp_ = srgb_to_lin(to) @ LUM, srgb_to_lin(tp) @ LUM
    keep = lp_ > 1e-4
    gain = float(np.median(lo_[keep] / lp_[keep])) if keep.sum() >= 50 else 1.0
    report["exposure_gain_linear"] = round(gain, 4)
    if not 0.25 <= gain <= 4:
        report["warnings"].append(f"exposure gain {gain:.2f}: the photo and the model differ by more than two stops "
                                  "where both are trusted — check the palette before trusting the projection")

    os.makedirs(os.path.join(out, "textures"), exist_ok=True)
    os.makedirs(os.path.join(out, "confidence"), exist_ok=True)
    report["images"], total, total_t, total_any = {}, 0, 0, 0
    for name, d in per.items():
        tex, cov, w, photo, own = d["tex"], d["cov"], d["w"], d["photo"], d["own"]
        base = own
        erased = kept = 0
        if a.stencil:
            # The scripted marking goes where the photo is used: otherwise the photo's text and
            # the script's, a few millimetres apart, show both (the ammo box's double "7.62").
            L = lab(own)
            paint = np.linalg.norm(L - lab(np.median(own, 0)[None])[0], axis=-1)   # the image's usual paint
            sten = np.zeros(len(own), bool)
            for c in a.stencil:
                dc = np.linalg.norm(L - lab(c[None])[0], axis=-1)
                sten |= (dc < STENCIL_TOL) & (dc < paint)        # nearer the marking than the paint
            gone = sten & (w > 0.01)
            erased, kept = int(gone.sum()), int((sten & ~gone).sum())
            if erased:
                full = np.zeros(tex.shape[:2] + (3,), np.float32); full[cov] = own
                known = cov.copy(); known[cov] = ~gone
                fill, ok = grow(full, known, 512, inside=cov)
                rest = cov & ~ok
                if rest.any():
                    fill[rest] = own[~sten].mean(0) if (~sten).any() else own.mean(0)
                base = fill[cov]
        src = np.clip(lin_to_srgb(srgb_to_lin(photo) * gain), 0, 1)
        new = base * (1 - w[:, None]) + src * w[:, None]
        delta = np.zeros(tex.shape[:2] + (3,), np.float32); delta[cov] = new - own
        delta, filled = grow(delta, cov, GUTTER)
        tex[..., :3] = np.clip(tex[..., :3] + delta * filled[..., None], 0, 1)
        img = d["img"]
        img.pixels.foreach_set(np.ascontiguousarray(tex[::-1]).ravel())
        img.update(); img.pack()
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)
        save_rgba(tex[..., :3], os.path.join(out, "textures", f"{safe}.png"))
        wm = np.zeros(tex.shape[:2], np.float32); wm[cov] = w
        save_rgba(wm, os.path.join(out, "confidence", f"{safe}.png"))
        nt, na = int((w > TRUSTED).sum()), int((w > 0.01).sum())
        total += int(cov.sum()); total_t += nt; total_any += na
        report["images"][name] = dict(size=list(img.size), texels=int(cov.sum()),
                                      trusted_share=round(nt / max(cov.sum(), 1), 4),
                                      touched_share=round(na / max(cov.sum(), 1), 4),
                                      shared_texels=d["shared"], stencil_erased=erased, stencil_kept_unseen=kept)
    report["coverage"] = dict(trusted_share=round(total_t / max(total, 1), 4),
                              touched_share=round(total_any / max(total, 1), 4))

    # The confidence as the photo's camera sees it (flat normals: for looking at, not for numbers).
    fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    fn *= np.sign((fn * N.mean(1)).sum(1, keepdims=True) + 1e-12)
    fpx = np.where(seen, fid, 0)
    cen = P.mean(1)[fpx.ravel()].reshape(H, W, 3)
    fac = np.maximum((fn[fpx.ravel()].reshape(H, W, 3) * cam.to_cam(cen.reshape(-1, 3)).reshape(H, W, 3)).sum(-1), 0)
    vw = seen * view_w * smoothstep(fac, lo_f, a.facing) * ~excl[fpx]

    # Export: the input's compression kept. Then the shipped file is what gets measured.
    stem = os.path.splitext(os.path.basename(a.model))[0]
    glb_out = os.path.join(out, f"{stem}_projected.glb")
    draco, webp = glb_info(a.model) if a.model.lower().endswith(".glb") else (False, False)
    for o in list(sc.objects):
        if o.name.startswith("_project_"):
            bpy.data.objects.remove(o)
    bpy.ops.export_scene.gltf(filepath=glb_out, export_format="GLB", export_apply=False,
                              export_image_format="WEBP" if webp else "AUTO",
                              export_draco_mesh_compression_enable=draco)
    if not a.model.lower().endswith((".glb", ".gltf")):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"{stem}_projected.blend"), copy=True)
    report["glb_bytes"] = dict(input=os.path.getsize(a.model), output=os.path.getsize(glb_out), draco=draco, webp=webp)

    sc, _ = open_model(glb_out)
    setup_render(sc, a.hdri, a.samples)
    after = renders(sc, views, out, "after")
    b, f_ = compare(ref, before["photo"]), compare(ref, after["photo"])
    report["photo_view"] = dict(before=b, after=f_)
    if f_.get("ssim", 0) <= b.get("ssim", 0):
        report["warnings"].append("SSIM from the photo's view did not rise — the projection did not land; "
                                  "look at photo_view.png and the confidence maps")
    sheet([on_grey(ref), on_grey(before["photo"]), on_grey(after["photo"]), np.dstack([vw] * 3)],
          os.path.join(out, "photo_view.png"))
    rows = [np.concatenate([on_grey(before[k]), on_grey(after[k])], 0) for k in ("turn", "back")]
    sheet(rows, os.path.join(out, "other_angles.png"))
    report["status"] = "ok"
    json.dump(report, open(os.path.join(out, "photo_project.json"), "w"), indent=1)
    print("PHOTO_PROJECT " + json.dumps(report))
    print(f"\nphoto view: SSIM {b.get('ssim')} -> {f_.get('ssim')}, ΔE76 {b.get('dE76')} -> {f_.get('dE76')}; "
          f"photo trusted on {report['coverage']['trusted_share']:.0%} of the texels "
          f"(touched {report['coverage']['touched_share']:.0%}); gain {gain:.2f}; "
          f"{glb_out} ({report['glb_bytes']['input']:,} -> {report['glb_bytes']['output']:,} bytes)")
    for wmsg in report["warnings"]:
        print("  WARNING", wmsg)
    print(f"LOOK at {out}/other_angles.png (before above after): the photo-view numbers measure the photo "
          "against itself where it was pasted; the other angles show what it did to the model")


main()
