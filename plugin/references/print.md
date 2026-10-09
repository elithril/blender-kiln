# 3D Printing Reference

> What a printable mesh must be, and how `tools/print_check.py` says whether one is.

---

## Requirements

A slicer cuts the mesh into layers and fills what is inside. It needs to know what inside is:

- **Sealed**: every edge shared by exactly two faces — no open edge (a hole), no edge shared
  by three or more (two surfaces glued along a line).
- **Consistent normals**: the two faces of an edge walk it in opposite directions; a part
  whose volume comes out negative is inside out (unless it is a cavity inside another part).
- **Every part held**: on the bed, or crossing, enclosed by, or within one extrusion of a
  held part. A part that starts in mid-air prints as spaghetti.
- **The object still all there**: a repair can produce a perfect manifold that has lost
  most of the object. Measured on the print study: Blender's boolean union in MANIFOLD mode
  returned a sealed, one-part mesh from the chest and from the lantern — and PrusaSlicer
  sliced both happily — after dropping everything but one block.
- **Walls thick enough**: 0.8 mm FDM (two extrusions), 0.5 mm resin.
- **Overhangs**: past 45° from vertical, supports or a better orientation.

## Printable from the brief

When the brief says the object is for printing — FDM or resin, a height in mm — model for
the printer from the first primitive. Repairing afterwards is what the study measured: a game
asset's open shells gave holes under an exact union, a lost object under a MANIFOLD union,
and only a voxel remesh held, at 600,000 triangles.

1. **Model at print size.** 1 Blender unit = 1 m, so an 80 mm object is 0.08 tall. Every
   thickness below is then a real millimetre on the model, not one that a later scale shrinks.
2. **Every primitive is a closed solid** — capped cylinders, boxes, prisms, tori. No plane, no
   circle, no one-sided shell: a shell gets Solidify (applied) at the wall thickness of rule 4,
   a ring is a torus. The study's lantern had 184 open edges, its chest 100: game assets are
   built from open shells. **Text is not closed when converted**: a font object's mesh has
   caps unwelded to its sides — "REX" came out with 472 non-manifold edges. Merge by
   distance (0.001 mm) and count 0 before using it — an exact union absorbed it once, which
   is luck, not a method.
3. **One volume, joined one of two ways** — never by touching faces:
   - **Union as you go**: Boolean, solver `EXACT`, applied part by part; count non-manifold
     edges after each (bmesh, `not e.is_manifold`) and stop at the first that is not 0.
   - **Interpenetrate, then one voxel remesh**: every part enters its neighbour by at least
     one wall thickness; join, Remesh `VOXEL` (adaptivity 0) at ≤ 0.2 mm and ≤ the thinnest
     feature / 8, then move the lowest vertex back to Z = 0. The study's lantern, remeshed
     at 0.2 mm, passes. The cost is weight: ~900,000 triangles for a 100 mm lantern.
   Parts meet by **overlapping, never face to face**: coplanar or touching faces are where an
   exact union leaves slivers and holes. Never `MANIFOLD` as the join: it returned a sealed,
   sliceable mesh that had dropped most of the object.
4. **Minimum thickness, imposed while modelling**, at print size: walls 1.2 mm FDM, 0.8 mm
   resin; free-standing pins, bars and handles 2 mm across FDM, 1 mm resin. The check's
   floors are 0.8 / 0.5 mm; the margin is there because its ray reads a slanted wall thinner.
   A detail the brief's height pushes under the minimum is thickened, and said so.
5. **A flat base on the bed**: lowest Z = 0 on a flat face that carries the object, origin at
   the bottom centre. Every part rests on the bed or enters another — two of the chest's parts
   ended 1.1 mm above the lid and PrusaSlicer reported an empty layer.
6. **Overhangs past 45° from vertical are designed out**: undersides of eaves, caps and rims
   at 45° or steeper (a cone, a chamfer, a roof pitch ≥ 45°), grooves as V-cuts. What remains
   — the top of an arch, the inside of a ring — is reported with the check's overhang %.
   **And every overhang grows out of the part below it**: its lowest edge sits on what is
   under it, never in the air. A 50° eave with no face past 45° still failed — its tip is
   the lowest point of the roof, so each layer starts there as a new island (PrusaSlicer:
   *Floating object part*). Brace it back into the wall at ≥ 45° (a corbel), or end it there.
7. **Relief is geometry.** An STL has no colour, no material and no texture: letters, planks
   and frames are embossed or engraved — ≥ 0.6 mm deep FDM, 0.3 mm resin, strokes at the
   wall minimum. A texture or a normal map never carries information on a print.
8. **Export in mm**: `bpy.ops.wm.stl_export(filepath=…, global_scale=1000,
   apply_modifiers=True, export_selected_objects=True)`. 3MF only when the 3MF Import/Export
   extension is installed — `bpy.ops.export_mesh.threemf.get_rna_type()` in a `try`;
   `hasattr(bpy.ops.export_mesh, "threemf")` is True even when it is not (Blender 5.2.2).
   Then `print_check.py` on the STL; PASS is required, or say what fails.

Measured on two objects modelled headless from these rules alone (Blender 5.2.2, PrusaSlicer
2.9.6): a dog house, 72 × 64 × 79.4 mm FDM, union as you go — 854 triangles, one closed part,
PASS (overhangs 0.69 %), and its 3MF too; a lantern, 44 × 44 × 100.5 mm resin, voxel at
0.2 mm — 889,152 triangles, PASS (overhangs 1.18 %, 75 self-intersecting pairs left by the
remesh, a warning; sliced as FDM, the only slicer pass). The dog house's first build failed on
its eaves: rule 6's second half comes from it.

## The tool

```
blender -b --factory-startup --python-exit-code 1 --python tools/print_check.py -- \
    model.stl --process fdm --height-mm 100 \
    --reference original.glb --slicer /Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer \
    --json check.json
```

STL (mm), 3MF (its own unit), GLB and .blend (metres). Exit 0 PASS, 3 FAIL, 1 error.

- **Counted raw.** Vertices are shared only when their coordinates are bit-identical. The
  study's first measure welded at 1e-5 before counting; that glued neighbouring shells and
  made defects the file did not have. The tool's counts match an independent exact edge
  pairing on every study file.
- **`--reference`** voxelises both meshes at the same size (largest dimension / 150) and
  compares dimensions (3 %) and volume (10 %, only when the dimensions agree and the model
  is sealed — a mesh with holes voxelises hollow). The reference is first scaled to the
  model's height: a uniform scale is not a loss.
- **`--slicer`** gives the scaled mesh to PrusaSlicer in a throwaway `--datadir`: `--info`
  (manifold, parts) and an FDM `--export-gcode`, whose log is searched for *Empty layer* and
  *Floating object part*. **An arbiter in addition to the counts, never instead**: it
  slices open meshes with exit 0 and calls the MANIFOLD union that lost the object manifold.
  It also sees what the counts do not — a gap between layers.

PASS needs 0 open and 0 non-manifold edges, consistent normals, no floating or inverted
part, no loss against the reference and, with the slicer, manifold = yes, no empty layer,
no floating object part. Thin walls, overhangs, self-intersections, crossing parts,
non-manifold vertices and zero-volume slivers are warnings with their figures.

On the study's files (PrusaSlicer 2.9.6): both exact unions FAIL (holes), both MANIFOLD
unions FAIL (dimensions 158-208 % off the original), the lantern's voxel remesh PASSes, the
chest's voxel remesh FAILs — two parts 1.1 mm above the lid (PrusaSlicer's empty layer) and
three hardware parts 0.5-2.1 mm off the body, which PrusaSlicer does not call floating.

## What it does not check

- Wall thickness is a ray cast inward from each face (sampled above 50,000 faces): a wall
  measured along a slant, or a part crossing another, reads thinner than it is.
- The fuse distance (0.4 mm FDM, 0.05 mm resin) and the bed tolerance (one layer) are
  defaults, not a printer profile.
- No resin slicing: the slicer pass is FDM with PrusaSlicer's defaults, whatever `--process`.
- No orientation search, no support generation, no hollowing or drain holes for resin, no
  check that the model fits a given build volume, no tolerances between moving parts.
- Self-intersections are counted (Blender's BVH), not repaired, and not a FAIL: a slicer
  merges overlapping solids.
