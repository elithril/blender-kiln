# Generalisation — the lantern's lessons on two other objects

Same briefs as the first kiln try (`ref-kiln`, skill before the lantern loop) against the
skill after it (`ref-kiln-gen`, `bee8c30`). Poly Haven references, CC0; the real assets
score the result (`bench/gt_compare.py`, orientation searched). One run each.

| | truth, 5 views | height | other | cost |
|---|---:|---:|---|---:|
| ammo box, before | 0.854 | +30 % | top view 0.859 | $1.97 |
| **ammo box, now** | **0.888** | **+8 %** | top view 0.976; rust and wear on the edges like the photo | $3.10 * |
| chair, before | 0.464 | −22 % | width/height +13 %, depth/height +7 % | $1.94 |
| **chair, now** | 0.467 | **−8 %** | width/height −11 %, depth/height −16 %; the back's pointed arch, rose and tracery match | $4.41 |

\* Salvaged: the bench guard voided the run because the operator committed a scorer file
during it; the session changed no tracked file, and its output was measured afterwards.

**The chair's silhouette score means nothing.** An openwork object seen from the side is
thin posts only: every orientation scores 0.12–0.16 there, and the scorer even picked the
wrong yaw on that noise. Openwork is judged on proportions and by eye.

Found by this test: the photos are 3/4 views, and `fidelity_check.py` turns its camera in
elevation only — it needs an azimuth; the balanced tier runs the whole procedure and
roughly doubles the cost per object.
