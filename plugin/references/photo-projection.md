# Photo projection — the photo's own markings on the model (optional)

A script copies text, a logo or precise wear as a lookalike: the ammo box's stencil came
out in the right font, a few millimetres off and worn in the wrong places. The photo holds
the right answer for every surface it sees squarely. `tools/photo_project.py` puts those
pixels back on the model's base-colour textures, and nowhere else. The method is
AssetFurnace's Pixel Match (image-to-3dlab, Apache-2.0 — `plugin/NOTICE`), on kiln's cameras.

**Optional, never the default, never silent.** It runs after the last fidelity_check round
(`reference-fidelity.md` § 5), and only when all three hold:

- the photo carries **text, a logo or precise wear** the script did not get right;
- the **fitted camera's silhouette IoU is ≥ 0.95** (the tool refuses below);
- **the user said yes** — propose it with what it changes and the two other angles (rule 6:
  it repaints the textures the user already saw; the input is never overwritten).

## Run it

```bash
# --view / --azimuth / --elevation: the same as the fidelity_check calls (read before modelling).
# --exclude: parts placed differently from the photo (a handle folded the other way, a lever).
# --erase-stencil: the scripted marking's colour (sRGB), erased where the photo is used.
blender -b --factory-startup --python-exit-code 1 --python <skill>/tools/photo_project.py -- \
  --reference ref.png --model asset_final.glb --hdri studio_small_09_1k.hdr --out review/project/ \
  --view front --azimuth 50 --elevation 20 \
  --exclude SM_AmmoBox_Handle SM_AmmoBox_LatchLever --erase-stencil '#443A14'
```

It writes `{model}_projected.glb` (Draco and WebP kept when the input had them),
`textures/`, `confidence/` (white: the photo is used), `photo_view.png` (photo | before |
after | confidence), `other_angles.png` (before above after) and `photo_project.json`.

1. **The camera.** fidelity_check's (orthographic, scaled to the photo's height), then
   azimuth, elevation, roll and distance fitted to the photo's silhouette — bounded to 10°
   from it, 5° of roll. Unbounded, a box 40 % too long fitted 0.955 by turning 30° away.
2. **Each texel's confidence**, multiplied: seen (depth), facing the camera (full at
   `--facing`, 0.6 by default and never less, fading in from 0.35 below), away from the
   model's outline, from inner depth edges and from the matte's edge, inside the matte. A
   texel two surfaces share in the UVs gets nothing.
3. **The photo at the model's exposure**: one gain in linear luminance, the median ratio
   over the trusted texels (≥ 0.9). Never the photo's raw pixels: they carry its light — on
   the ammo box, the photo's near-black lighting pasted into the base colour. A mean ratio
   is pulled by what the model lacks: a white letter on 11 % of a face set it at 1.25 and left
   the face 18 % dark, letter included; the median (2.07) keeps it within 15 % of the model's.
4. **Blend**: photo × confidence + texture × (1 − confidence), the change grown 4 texels
   into the UV gutter. Excluded parts receive nothing but still hide what is behind them.

## Read it

- **Look at `other_angles.png` first.** It is the only view not measured against the photo.
  The SSIM and ΔE76 from the photo's view are **partly circular** — the photo compared with
  itself where it was pasted: they say the projection landed, not that the model is better.
- **fidelity_check's numbers are not the judge either**: on the ammo box its saturation gap
  grew (0.131 → 0.183, prototype) while the stencil became the photo's.
- **Look for the defects seen on the ammo box**: a **double marking** (the photo's text beside
  the script's, half-blended) — pass `--erase-stencil`; **a highlight or part pasted where
  the model has another part** (a lid highlight on a handle placed differently) — `--exclude`
  that part; **an opening painted on a flat plate** (the lever's hole) — exclude it, or model
  the hole; **text faded at the trust's edge** (the "7" of "7.62", near the face's outline) —
  a limit, said to the user.
- Refusals exit 1: fitted IoU under `--min-iou`, `--facing` under 0.6, an `--exclude` that
  matches no object or material, no textured part, fewer than 50 trusted texels.

## Measured

The ammo box (bench `ref-kiln-v15gen`, scripted, 3,856 tris, two 1024 textures), azimuth
50 / elevation 20 as its session read them. Camera: IoU **0.918 → 0.963** after the fit
(az 51.9, el 15.7, 0.92 m). From the photo's view, Cycles under `studio_small_09`:

| Run | Gain | SSIM | ΔE76 | GLB |
|---|---|---|---|---|
| Before (the session's `_final.glb`) | — | 0.551 | 17.46 | 186.6 kB |
| Prototype, raw pixels | — | 0.655 | 12.90 | — |
| Prototype, mean-ratio gain | 2.05 | 0.619 | 15.42 | 171.8 kB |
| `photo_project.py`, median-ratio gain | 2.71 | 0.597 | 16.84 | 175.4 kB |
| + `--exclude` handle and lever, `--erase-stencil '#443A14'` | 2.97 | 0.589 | 17.27 | 174.3 kB |

The tool scores below the prototype's mean gain on this one photo, and is right on the
seeded box where the mean left the face 18 % dark: the brighter median lifts the dark photo further from
itself, which is the circularity above. Raw scores highest and is refused — it is the
photo's lighting. The erase removed 19,273 stencil texels where the photo is used, kept
67,206 where it is not; the double "7.62" is gone by eye. 14 % of the texels trusted, 25 %
touched. 83 s headless (Apple Silicon CPU, 64 samples, six renders).

`tools/test_photo_project.py` (Blender workflow): a box with an "E" printed on its front,
photographed 1⅓ stops darker from az 25 / el 15 at 0.9 m, the tool started at 30 / 12 —
IoU 0.917 → 0.992, SSIM 0.771 → 0.847, ΔE76 16.9 → 14.5, gain 2.07, the front's correlation
with the truth 0.17 → 0.95, the back's texture unchanged, an excluded plate kept, a yellow
mark erased in view and kept on the back, a 40 % longer box refused at 0.859.

## Limits

- **One object tested** (the ammo box, one photo), plus the seeded box. No organic shape, no
  glossy material, no second photo.
- One photo, one camera: the sides it does not face keep the scripted texture, and the seam
  between them is only as good as the gain. No local colour match (AssetFurnace's).
- The photo's exposure is matched, not its light: shading and highlights in the photo stay
  in the base colour where it is trusted.
- The model's shape must match: a misplaced part gets the photo of what is in front of it.
