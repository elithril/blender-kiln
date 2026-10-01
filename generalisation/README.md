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

## The crate with the lantern's final skill (v14, `83ffb68`, 2026-10-01)

Sandboxed (audit 0), one run, $4.34. A first attempt was lost to the machine sleeping
mid-review (`API Error: Connection lost while your computer was asleep`), not measured.

| | truth, 5 views | height | base share | albedo variation (fine / mid / large) | roughness | metal |
|---|---:|---:|---:|---|---|---|
| real crate | — | 17.7 cm | 89.0 % | 0.016 / 0.027 / 0.030 | 0.55 ± 0.14 | 0.02 |
| before the lantern loop | 0.854 | +30 % | +9 % | — | — | — |
| mid-way (`bee8c30`) | 0.888 | +8 % | +7 % | 0.008–0.016 / … | 0.51–0.69 ± 0.27–0.38 | 1.00 |
| **v14 skill** | 0.878 | +15 % | **+1 %** | 0.035 / 0.039 / 0.039 | 0.61 ± 0.33 | **0.01** |

- **Shape holds** across objects: within the earlier runs' range, the best base share.
- **The material is the right KIND** — painted steel as a non-metal paint (0.01, the real
  0.02) where mid-way made it bare metal — and one material for the whole crate.
- **It does not read as rust.** Rust is a soft orange gradient airbrushed along the edges,
  the paint a flat dark green, the stencil crisp and new — where the photo's is worn and
  broken. Its variation is twice the real crate's but in the wrong places: a smear, not
  flakes, pits and chips. The geometry tools have nothing to match on the material side.
- The grain line flags the REAL crate against its own photo (bands 2–4, 22–28 %): the
  lantern-calibrated threshold does not transfer. To be removed from the session's view.
- The session reported that WebP had erased the normal map's fine relief; measured, the
  grain moved 0.48 → 0.40 at most and the normals' mean tilt did not change (0.4°).

## The crate with scanned texture sets (skill `66e0b08`, 2026-10-01)

Sandboxed (audit 0), one run, $3.80, 15 min. The session chose two Poly Haven sets
(`green_metal_rust` as the paint, `rust_coarse_01` as the wear), tinted both toward the
photo's palette, masked the rust by the form, baked to UVs and credited Poly Haven.

| | truth, 5 views | height | base share | metal |
|---|---:|---:|---:|---|
| v14 skill (procedural noise) | 0.878 | +15 % | +1 % | 0.01 |
| **v15 skill (scanned sets)** | **0.950** | +16 % | −1 % | 0 (factor 0) |

- **The best shape on the bench, any object** — 0.958 from the front.
- **The surface reads as worn paint**: the stencil is broken like the photo's, the paint
  has a scanned grain, the rust sits along the lower edge and the seams. From a distance
  it is still soft, and the large front face fairly even — the photo's darker blotches
  are missing.
- A stats script of mine read the paint as 100 % metal: it ignored `metallicFactor: 0`.
  The review tool applies the factor, which is why it raised nothing.

## The chair with scanned texture sets (skill `66e0b08`, 2026-10-01)

Sandboxed (audit 0), one run, $6.13 (one correction round over the limit, declared).

| | truth (front, back, top) | width / height | depth / height | height | materials |
|---|---:|---:|---:|---:|---:|
| real chair | — | 0.30 | 0.29 | 227 cm | 1 |
| before the lantern loop | 0.445 | 0.34 | 0.31 | −22 % | — |
| mid-way (`bee8c30`) | 0.673 | 0.27 | 0.24 | −8 % | 4 |
| **scanned sets** | **0.750** | 0.33 | **0.29** | **−29 %** | **1** |

- **The wood reads as wood**: one mahogany from Poly Haven's `dark_wood`, its grain visible,
  rendered warmth +0.077 for the real chair's +0.077.
- **The tracery is there** — pointed arch, rose, lancets, finials, turned legs.
- **The size is wrong**: a tall-backed chair assumed at an ordinary chair's height. The
  case where the session should have asked rather than assumed.
- The apron's round arches came out saw-toothed; the rose is simplified.

**Three objects, one skill (`66e0b08`)**: crate 0.950, lantern 0.897, chair 0.750 against
their real assets, every surface one material per physical material. Scanned sets made
rust and wood credible; brass, which has no scan, gained less.
