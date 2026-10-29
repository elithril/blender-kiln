# Fox Figurine — Production Log

## Config
- Type: prop (multi-colour 3D-print figurine)
- Target: STL, one file per filament, millimetres (FDM, 0.4 mm nozzle)
- Tier: print-resolution (0.3 mm voxel field; tiers are for real-time assets, not applicable)
- Style: stylized
- Mode: auto
- Storage: compact

## Reference Image
- Path: none
- Visual comparison: N/A

## Source
- Method: scripted modeling (no marketplace, no AI generation)
- Technique: signed-distance-field fox built from smooth-blended ellipsoids and round cones
  (numpy), meshed with OpenVDB `convertToPolygons` inside Blender 5.2.2 LTS. Colour regions
  are separate SDF volumes, meshed, then cut from the master with Blender EXACT booleans:
  black = F∩Kb, white = F∩Kw−Kb, brown = F∩Kr−Kb−Kw, orange = F−Kb−Kw−Kr.
- Scripts: scripts/01_body.py, scripts/02_split_colours.py, scripts/03_export.py
- Factory scene Cube removed before building (rule 6 exception).

## Pipeline
- Master: 156,226 faces, 49.7 × 52.8 × 79.8 mm, 41,671 mm³, flat base at z = 0
- Partition check: 33,817 + 4,605 + 3,063 + 186 = 41,671 mm³ (exact, no overlap, no gap)
- Cleanup: 2 µm weld at triple junctions, degenerate dissolve; 0 non-manifold edges on every part
  (fixed a zero-thickness orange pinch at the nose by enlarging the nose colour volume 0.5 → 0.8 mm)
- Islands: orange 1 · white 4 (face+bib, tail tip, 2 inner ears) · black 5 (nose, 2 eyes, 2 ear tips)
  · dark brown 2 (front stockings+paws, back feet)
- Print checks: bed contact ≈ 500 mm² · overhangs > 45°: chin/cheek tufts/snout (z 40–57) and
  rounded undersides near the bed (tail, haunches, paws)
- Export (binary STL, global_scale 1000 → mm):
  - fox-figurine-orange.stl      15.4 MB  308,722 tris
  - fox-figurine-white.stl        5.3 MB  105,028 tris
  - fox-figurine-black.stl        0.6 MB   11,554 tris
  - fox-figurine-dark-brown.stl   3.5 MB   70,988 tris

## Print notes
- Load all four STLs together as ONE multi-part object (e.g. Bambu/Orca: "load as single object
  with multiple parts"; Prusa: add parts) — do not let the slicer re-centre them individually.
- Supports: tree, "everywhere" (chin/snout land on the chest). Brim recommended (≈ 500 mm² footprint).
- Black eyes/nose/ear tips are small volumes: a prime tower is needed for clean colour changes.

## Licenses
- All geometry original, scripted in this session. No third-party assets.

## Checkpoint
- Last completed step: EXPORT
- Timestamp: 2026-10-21
