# Bayonet Box — Production Log

## Config
- Type: prop (two-part print: box + bayonet lid)
- Target: STL, FDM, 0.4 mm nozzle, one colour
- Tier: n/a (print); 6.2k tris body, 6.4k tris lid
- Style: stylized (grip ribs, two V bands, lock marker)
- Mode: auto │ Storage: compact
- Standing answer applied: mechanical part → carried on in Blender at decorative precision, fit-test coupons written to print first.

## Reference Image
- none — Visual comparison: N/A

## Source
- Method: scripted modeling (`build_bayonet_box.py`, parametric, mm values at the top)
- Scene: Blender 5.2.2 LTS factory scene; the default Cube was removed (rule 6 exception), nothing else touched.

## Design (mm)
- Box: Ø60 × 36. Wall 2, floor 2. Neck Ø54 (r 27), from the shoulder z 28 to z 36. Inside, a 45° step from r 28 to r 25 (prints with no support).
- 3 lugs at 90/210/330°, each 12° wide, sticking out 1.4 mm (to r 28.4), with a 45° underside so they print with no support. Flat top at z 34.
- Lid: Ø60 (61.4 over the ribs) × 11. Plate 2.6. Skirt inner r 27.3, so **0.3 mm radial clearance**. A 0.5 mm lead-in chamfer at the skirt mouth.
- Inside the skirt: an L-slot per lug. A 16° entry slot runs from the rim, then a groove carries the lug 40° round (**twist clockwise seen from above to lock**). Groove depth r 28.8, which leaves 1.2 mm of wall (3 perimeters).
- Lock: the groove's lower face ramps from 0.55 mm clearance to −0.15 mm (cam/interference), then drops into a pocket at +0.15 mm. You feel it snap over, then it seats.
- Marks: the wide rib on the lid lines up with the short V-notch on the box body when the lid is locked.

## Validation
- Both parts are watertight: 0 non-manifold / boundary edges (exact boolean; ring vertices are phase-shifted so they don't land on the lug edges).
- Fit sweep (`check_fit.py`, volume where the lid overlaps the box):
  - entry position, any height 0–6 mm: 0 mm³ (drops on freely)
  - twisted back 20–40°, lid down: 0
  - twisted back 6–14° (cam bump): about 0.6 mm³
  - locked: 0
  - locked and lifted 0.2 / 0.4 mm: 0.96 / 4.8 mm³ (the lugs hold the lid)
  - half-way, lifted 2 mm: 34.7 mm³ (retained)
- STL read back: body 59.99×59.99×36.0 mm, lid 61.4×62.4×11.0 mm. Units are mm (global_scale 1000) and z min = 0.

## Print notes
- Body: print upright, no supports. Lid: exported upside down (top on the bed), no supports; the groove ceilings are 45°.
- Print the fit-test pair first (`bayonet-box-fit-test-neck.stl` 4.0 cm³ + `-ring.stl` 6.1 cm³).
  - Too tight: raise `CLEAR` and/or `D_PEAK` in the script.
  - Too loose / no click: lower `D_PEAK`.
  - Then re-run the build and export scripts.

## Pipeline
- Import: implicit (scripted). Cleanup: none needed (built manifold, flat-shaded, transforms identity).
- Texturing: M_PLA_Teal (Principled, preview only — STL carries no material).
- Optimize: skipped (STL, no textures).
- Export: STL binary.
  - bayonet-box-body_final.stl: 300 kB, 6,156 tris
  - bayonet-box-lid_final.stl: 313 kB, 6,412 tris
  - bayonet-box-fit-test-neck.stl: 175 kB
  - bayonet-box-fit-test-ring.stl: 291 kB

## Licenses
- All geometry original, scripted in this session. No external assets.

## Checkpoint
- Last completed step: EXPORT (.blend saved: bayonet-box.blend)
- Timestamp: 2026-10-21
