# Lantern iterations — one reference, thirteen versions

Reference: Poly Haven `Lantern_01` preview (CC0), photographed from ~15° above. The session
only ever sees the photo; the real asset (29.4 cm, 33,902 tris) is the bench's marking
scheme (`bench/gt_compare.py`). Claude Opus 5.5, Blender 5.2.2, one run per version.

| | photo @15° IoU | truth, 5 views | height | base (truth 13.9 %) | saturation (ref 0.32) | detail (ref 0.032) | tris | cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1 | — | 0.830 | +23 % | +19 % | 0.44 | 0.028 | 6,852 | $1.90 |
| v2 | — | 0.865 | +37 % | +13 % | 0.20 | 0.016 | 7,344 | $3.83 |
| v3 | 0.862 | **0.876** | +33 % | +17 % | 0.34 | 0.017 | 10,688 | $2.83 |
| v4 | 0.863 | 0.843 | +29 % | +30 % | 0.33 | 0.021 | 8,044 | $4.06 |
| v5 | 0.846 | 0.848 | +2 % | −27 % | 0.38 | 0.022 | 8,572 | $5.63 |
| v6 shipped | 0.876 | 0.862 | +2 % | +13 % | **0.12** | 0.018 | 8,836 | $4.15 |
| v6 re-exported | 0.876 | 0.862 | +2 % | +13 % | 0.30 | 0.019 | 8,836 | — |
| **v7** | 0.856 | 0.861 | **+2 %** | **−10 %** | **0.31** | 0.018 | 7,552 | **$3.52** |
| img2threejs (pass 3/8) | 0.783 | 0.866 | +52 % | −7 % | 0.38 | 0.026 | 41,736 | ≈ $10 |

What each version changed is in `CHANGELOG.md` and the commits of `fix/baseline-findings`.
What moved the numbers, in order: measuring instead of eyeballing (v3), tracing wires and
layering textures (v4), settling size and camera elevation (v5, over-corrected; v6),
and converting float colour bakes to sRGB before export (v6 shipped near black; v7).

Still open: fine texture detail (~0.018 against 0.032) and triangle count (+51 % over the
balanced tier, reported by the session, not reduced).

## After the colour fix — v8, v9, and TRELLIS.2 (2026-10-01)

v7 read near-black next to the real object: 100 % metal at a base colour of 0.07–0.15,
tuned to the photo's luminance while the photo's own light was darker. `fidelity_check.py`
now reports dark metal (`c390e22`); v8 is the same brief on that skill. v9 adds one
sentence: a local TRELLIS.2 mesh of the same photo, to measure proportions from
(`tools/template_profile.py`, `8d6121a`).

All rows re-measured together — one render setting (Cycles, 32 samples, studio HDRI, 15°):
**not comparable with the table above for detail**, which rises with render noise (v7 reads
0.018 there, 0.035 here). Warmth (R−B) and luminance are under the review HDRI, the real
object rendered under the same light as the witness.

| | truth, 5 views | profile vs truth (median / worst) | height | base (truth 13.9 %) | luminance | warmth | metal base colour | tris | cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| real object (witness) | — | — | 29.4 cm | — | 0.198 | +0.076 | 0.30, 46 % metal | 33,902 | — |
| v7 | 0.861 | — | +2 % | −10 % | 0.152 | +0.040 | **0.07–0.15** | 7,552 | $3.52 |
| v8 — dark metal reported | 0.905 | 1.1 / 9.7 mm | +20 % | −24 % | 0.228 | +0.081 | 0.35 | 9,514 | $4.02 |
| **v9 — + TRELLIS.2 template** | **0.921** | **0.8 / 4.8 mm** | +2 % | **−6 %** | 0.226 | +0.079 | 0.27–0.31 | 9,964 | $5.19 |
| **v10 — + metal mask fixed** | 0.914 | **0.8 / 4.0 mm** | 0 % † | **−4 %** | 0.244 | +0.093 | — | 9,738 | $4.52 |
| v11 — joints rendered, patina metal, one metal ‡ | 0.897 | 1.0 / 4.9 mm | +1 % | +1 % | 0.221 | +0.086 | — | 12,418 | $7.64 |
| ~~v12~~ — **contaminated, not a measurement** § | 0.914 | — | +2 % | −3 % | — | — | — | 10,852 | $8.43 |
| **v13 — v11 + template widths + tinted glass, sandboxed** | **0.924** | 0.7 / 10.8 mm | +2 % | +1 % | 0.235 | +0.074 | — | 9,208 | $5.63 |
| TRELLIS.2 raw (local, free) | 0.952 | 0.6 / 1.6 mm | 1 m | +1 % | 0.207 | +0.137 | 0.32 | 191,520 | $0 |
| TRELLIS.2 finished by kiln, try 1 | 0.926 | — | +2 % | +1 % | 0.214 | +0.078 | — | 5,070 | $4.81 |
| TRELLIS.2 finished by kiln, try 2 | 0.866 | — | 0 % | +6 % | 0.222 | +0.088 | — | 6,092 | $4.84 |

Height is an assumption in every brief: none gives the size, and the template is 1 m tall.
† **Contaminated.** The skill at v9 and v10 (`8d6121a`–`a4808a7`) carried the real height
in an example command (`--height 0.294`); v10 copied it as its assumption, v9 saw it and
assumed 30 cm. Removed in `18f8eec`. Shape scores and profiles are scaled to the real
height before comparing and are not affected; v10's height column is.

**What these say, and what they do not.**

- **The colour fix holds**: metal base colour from 0.07–0.15 to ~0.30, warmth from half the
  real object's to within 0.005 of it.
- **The template moves the proportions where the photo lied**: the tank-to-burner step a
  15° camera hides, read 9.7 mm off by v8, 4.8 mm by v9. Base share from −24 % to −6 %.
- **v9's surface regressed**: bright copper islands on a dark patina — v1's "camouflage".
  The skill's new dark-metal text cited the real brass as "48 % metal", and the session
  made it a target, thresholding a noise into bare-metal islands. Being corrected for v10.
- **Finishing a TRELLIS.2 mesh is not the way**: try 1 scored 0.926 with every wire
  broken by a 97 % decimation (silhouettes do not see holes); try 2, wires rebuilt as
  curves, is intact but faceted, its texture smeared. TRELLIS.2 is worth its
  proportions, not its surface — hence the template.

- **v10 fixes the surface and keeps the shape** (`a4808a7`: the metal share quoted as a
  figure is gone, a scattered hard-edged metallic mask is reported): one worn region with
  soft edges, highlights 0.033 for the real object's 0.030 (v8: 0.015), the profile still
  within 0.8 mm median. Still open, by the session's own review and by eye: the band above
  the globe too prominent, a plain grey filler cap, the globe's frosting too faint, and one
  material (the tank) at the edge of the islands threshold (0.59 in-between, largest 48 %).

- **v11 fixes what v10 hid** (`1dc852d`): the air tubes now bend into the tank on a
  fillet instead of a flat cut on its slope; one bronze for the whole body (3 materials,
  metallic 0.97–1.00); 16+ sides. But it overshot: the bronze reads new and clean —
  albedo variation 0.017 for the real 0.029, almost no relief — the patina lost with the
  non-metal. ‡ The account's usage limit cut the session after EXPORT and its own
  verification, during the final message: the file and log are complete.

- § **v12 read the answer key.** Sessions ran inside the bench's own repository; v12
  listed `bench/results/` and read this README — the real object's height, base share,
  profile errors and metal values — and v11's log. Its numbers are kept, struck out, as
  a record. The runner now puts every session in a sandbox outside every repository
  (`bench/run.py`: only the files the brief names, the skill's runtime files without its
  README, CHANGELOG or docs) and audits each transcript for calls that reach outside it.
  Of the earlier runs, the targeted audit found no read of the truth or of results;
  TRELLIS.2 try 2 listed the truth folder's name without opening it.
- **And a caveat no sandbox fixes**: the skill's own references now carry lessons
  measured on THIS lantern. Its improvement on the lantern overstates how it generalises;
  the crate and the chair are the test of that.

- **v13, the first sandboxed run** (`0ec4783`, audit: 0 calls outside the sandbox): the
  best shape of all (0.924, front 0.896), joints entering clean with their section kept,
  the glass tinted. **The texture is not there**: the tank reads clean, bright and glossy
  — grain 16 % of the photo's, highlights 0.053 for the real object's 0.030. By the
  criterion set before the run (texture at least v10's, geometry at least v11's), it
  passes on geometry and fails on texture.

Images: `v13-compare.webp`, `v13-closeups.webp`, `v12-contaminated-compare.webp`, `v12-contaminated-closeups.webp`, `v10-v11-compare.webp`, `v11-closeups-texture-joint.webp`, `v8-v9-v10-compare.webp`, `progression-v1-v8.webp` (all versions, same render), `v7-v8-v9-compare.webp`,
`trellis-finish-compare.webp`, `trellis-finish-front-diff.webp` (red: truth only, blue:
model only — try 2's wires are intact and a few pixels out, which empties a thin band's
overlap).
