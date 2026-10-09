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
