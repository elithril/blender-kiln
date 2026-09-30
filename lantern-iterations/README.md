# Lantern iterations — one reference, seven versions

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
