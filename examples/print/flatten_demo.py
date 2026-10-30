#!/usr/bin/env python3
"""The before/after behind docs/images/print-flatten-prusaslicer.svg, rebuilt from the files.

    python3 examples/print/flatten_demo.py [out_dir]     # Blender and PrusaSlicer at their macOS
                                                         # paths, or $BLENDER / $PRUSASLICER

1. takes the windmill kiln modelled for print (models/windmill_body.stl) and makes it what a
   pass by hand often leaves: 10 % of its vertices off by 0.1-0.25 mm, the whole model turned
   1 degree (seeded: the same figure every run);
2. runs tools/flatten.py --bed on it;
3. slices both with PrusaSlicer's default profile;
4. draws, from the two G-code files only, the gallery floor's top finishing layer coloured by
   height and the first layer on the bed.

Measured on PrusaSlicer 2.9.6: the gallery floor in 4 heights before, 1 after; 629 mm of first
layer before (one edge of the base touches), 3,317 mm after.
"""
import json, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
SLICER = os.environ.get("PRUSASLICER", "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
SVG = os.path.join(ROOT, "docs", "images", "print-flatten-prusaslicer.svg")
MODEL = os.path.join(HERE, "models", "windmill_body.stl")
BAND = (44.0, 48.0)                          # the gallery floor's height, mm
os.makedirs(OUT, exist_ok=True)

OFF = r'''
import sys, numpy as np
argv = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, argv[0])
import print_check as pc
V, F = pc.load(argv[1])
rng = np.random.default_rng(5)
k = rng.random(len(V)) < 0.10                       # a pass by hand: 10 % of the vertices off
d = rng.normal(size=V.shape); d /= np.linalg.norm(d, axis=1, keepdims=True)
V[k] += d[k] * rng.uniform(0.1, 0.25, size=(int(k.sum()), 1))
a = np.radians(1.0); c, s = np.cos(a), np.sin(a)    # and the whole model 1 degree off
ctr = V.mean(axis=0); Q = V - ctr
V = np.stack([Q[:, 0] * c + Q[:, 2] * s, Q[:, 1], -Q[:, 0] * s + Q[:, 2] * c], 1) + ctr
pc.write_stl(argv[2], V, F)
'''
tools = os.path.join(ROOT, "plugin", "tools")
with open(f"{OUT}/make_off.py", "w") as f:
    f.write(OFF)


def blender(*a):
    subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", *a], check=True,
                   stdout=subprocess.DEVNULL)


blender("--python", f"{OUT}/make_off.py", "--", tools, MODEL, f"{OUT}/windmill_off.stl")
blender("--python", os.path.join(tools, "flatten.py"), "--", f"{OUT}/windmill_off.stl",
        "--out", f"{OUT}/windmill_flat.stl", "--bed", "--json", f"{OUT}/flatten.json")
for name in ("windmill_off", "windmill_flat"):
    subprocess.run([SLICER, "--export-gcode", "-o", f"{OUT}/{name}.gcode", f"{OUT}/{name}.stl"], check=True,
                   stdout=subprocess.DEVNULL)

SKIP = ("Skirt", "Skirt/Brim", "Brim", "Custom", None)   # the outline round the object and the purge moves


def parse(path):
    z = 0.0; typ = None; x = y = None; segs = []
    for line in open(path):
        if line.startswith(";Z:"):
            z = float(line[3:]); continue
        if line.startswith(";TYPE:"):
            typ = line[6:].strip(); continue
        if not line.startswith(("G1", "G0")):
            continue
        m = dict(re.findall(r"([XYE])(-?[\d.]+)", line.split(";")[0]))
        nx = float(m["X"]) if "X" in m else x
        ny = float(m["Y"]) if "Y" in m else y
        if line.startswith("G1") and "E" in m and float(m["E"]) > 0 and x is not None and nx is not None \
                and typ not in SKIP:
            segs.append((z, typ, x, y, nx, ny))
        x, y = nx, ny
    return segs


before, after = parse(f"{OUT}/windmill_off.gcode"), parse(f"{OUT}/windmill_flat.gcode")
floor = lambda s: s[1] == "Top solid infill" and BAND[0] <= s[0] <= BAND[1]
zb, za = min(s[0] for s in before), min(s[0] for s in after)
first_b, first_a = (lambda s: s[0] == zb), (lambda s: s[0] == za)
length = lambda segs, pick: sum(math.dist(s[2:4], s[4:6]) for s in segs if pick(s))
def layers(segs):
    """Heights of the gallery floor's top layer that carry filament. PrusaSlicer writes the odd
    zero-length extrusion move (0.0 mm at 46.25 after flattening): a point, not a layer."""
    by = {}
    for s in segs:
        if floor(s):
            by[round(s[0], 2)] = by.get(round(s[0], 2), 0.0) + math.dist(s[2:4], s[4:6])
    return sorted(h for h, mm in by.items() if mm >= 1.0)


heights = sorted(set(layers(before)) | set(layers(after)))
ramp = ["#fde0c5", "#f8b58b", "#f2855d", "#e24a3b", "#b8322b"]      # one hue, light to dark: height
col = {h: ramp[min(len(ramp) - 1, i)] for i, h in enumerate(heights)}
hb, ha = layers(before), layers(after)

W, H, P, PW, PH = 960, 900, 30, 420, 340       # canvas, padding, panel


def frame(*picked):
    """One frame for a row: before and after at the same scale and place, so a sliver of a base
    reads as a sliver, not as a shape of its own."""
    keep = [s for segs, pick in picked for s in segs if pick(s)]
    return [v for s in keep for v in (s[2], s[4])], [v for s in keep for v in (s[3], s[5])]


def panel(segs, pick, ox, oy, colour, title, sub, box):
    keep = [s for s in segs if pick(s)]
    xs, ys = box
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    k = 0.9 * min(PW / (max(xs) - min(xs)), PH / (max(ys) - min(ys)))   # one scale for x and y
    f = lambda X, Y: (ox + PW / 2 + (X - cx) * k, oy + PH / 2 - (Y - cy) * k)
    out = [f'<text x="{ox}" y="{oy - 34}" class="t">{title}</text>',
           f'<text x="{ox}" y="{oy - 14}" class="s">{sub}</text>',
           f'<rect x="{ox}" y="{oy}" width="{PW}" height="{PH}" class="bed"/>']
    for s in keep:
        a, b = f(s[2], s[3]), f(s[4], s[5])
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{colour(s)}" '
                   f'stroke-width="1.4" stroke-linecap="round"/>')
    return out


el = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
      'font-family="ui-sans-serif, -apple-system, Segoe UI, sans-serif">',
      '<style>.t{font-size:17px;font-weight:600;fill:#e9e6e1}.s{font-size:13px;fill:#a9a49c}'
      '.bed{fill:#23201d;stroke:#3a3631}.k{font-size:12px;fill:#a9a49c}</style>',
      f'<rect width="{W}" height="{H}" fill="#151311"/>']
row1, row2 = frame((before, floor), (after, floor)), frame((before, first_b), (after, first_a))
el += panel(before, floor, P, 70, lambda s: col.get(round(s[0], 2), ramp[0]), "Before: the gallery floor's top layer",
            f"split over {len(hb)} heights, {hb[0]:.2f} to {hb[-1]:.2f} mm", row1)
el += panel(after, floor, W / 2 + 10, 70, lambda s: col.get(round(s[0], 2), ramp[0]), "After flatten.py --bed",
            f"one height, {ha[0]:.2f} mm" if len(ha) == 1 else f"{len(ha)} heights", row1)
el += panel(before, first_b, P, 480, lambda s: "#d9d4cc", "Before: first layer on the bed",
            f"{length(before, first_b):.0f} mm of filament, one edge of the base touches", row2)
el += panel(after, first_a, W / 2 + 10, 480, lambda s: "#d9d4cc", "After",
            f"{length(after, first_a):.0f} mm, the whole base", row2)
lx = P
for h in heights:
    el.append(f'<rect x="{lx}" y="{H - 64}" width="14" height="14" rx="3" fill="{col[h]}"/>'
              f'<text x="{lx + 20}" y="{H - 52}" class="k">{h:.2f} mm</text>')
    lx += 100
el.append(f'<text x="{P}" y="{H - 20}" class="k">PrusaSlicer 2.9.6 G-code, default profile. The windmill kiln modelled, '
          f'turned 1°, 10 % of its vertices off by 0.1-0.25 mm.</text>')
el.append("</svg>")
with open(SVG, "w") as f:
    f.write("\n".join(el))
print(json.dumps(dict(floor_before=hb, floor_after=ha, first_before=round(length(before, first_b)),
                      first_after=round(length(after, first_a)))))
