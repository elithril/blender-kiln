# 3D Printing Reference

> What a printable mesh must be, and how `tools/print_check.py` says whether one is.

---

## Scope — simple objects ONLY

Print mode models **simple objects**: turned or geometric shapes, and stylised figures that are
a bell, a block or a lathe with a few details cut or engraved. Measured on six briefs: a dog
house, a lighthouse, a pumpkin and a ghost's body passed, and looked like what was asked. A
cat held by the ghost, then a real cat rebuilt from its photo, both passed every print check
and were unacceptable to look at — primitives cannot make an animal, and no rule here closes
that gap.

**An animal, a person, a character, a portrait of anything alive: refuse print mode at
CONFIG, before the first primitive.** Say why in one line and offer what is honest:
- the object reduced to a simple stylised shape the user agrees to first (a cat as a bell
  with ears — said as such, not as a likeness);
- or `tools/print_check.py` on a model the user brings (a sculpt, a scan, a model bought or
  downloaded): the check works on any mesh.

Never start one "to see": every round spent on it is spent on a result the user will reject.

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
   **A solid of revolution is the cheapest closed volume**: spin one profile (base, body, bands,
   corbels, roof) round Z with `bmesh.ops.spin(..., use_merge=True)`, then merge the axis
   points — one closed solid, no union at all. Measured on a 90 mm lighthouse: 0 non-manifold
   edges, PASS first time. **Never cut exactly on the lathe's edges**: windows placed at
   45° + 90°·k on a 64-step spin (one edge every 5.625°) left 3 non-manifold edges; the same
   cuts half a step off (2.8°) left 0.
   **Remesh last.** A boolean applied after a voxel remesh (eyes engraved in a figure, a shell
   carved after a part was joined to it) left 2 to 9 edges shared by three faces: carve and
   join first, remesh at 0.2 mm once at the end, then decimate (2.35 M → 250 k triangles, still
   PASS). A part cut to fit another can leave a crumb behind (a tip hidden behind the other
   part): count islands, drop the ones hidden by the other part, and log it.
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
8. **Smooth where the photo is smooth — the printer shows every facet.** Shading hides
   facets on screen; a layer of 0.2 mm does not. Measured on a ghost's head:
   - **one profile, smoothed whole** — a body and a dome built apart and joined at a height
     left a ring all round: the body's smoothing, cut at the joint, flattened its slope
     (−0.27 → −0.15 → −0.31) and the dome's curvature then jumped. Smoothing the joined
     profile over the full height (σ 3 mm, the top's last 2σ kept) gave an even slope and no
     ring;
   - **enough rings for the curve**: a facet strays from its curve by its sagitta, L²/8R. The
     dome's 12 rings strayed by ~0.26 mm — more than a layer, banded on screen and on the
     print; 80 rings, none. Keep it under 0.05 mm;
   - **a voxel remesh serrates every sharp rim at the voxel's size**: engraved eyes came out
     toothed at 0.2 mm. At 0.1 mm the teeth halve (5 M triangles before decimating, 3.4 GB,
     39 s); a detail that must stay crisp is better joined by an exact union than remeshed;
   - **look at the STL itself**, close, with a matcap (Solid → MatCap): the review renders are
     too far and too smooth to show any of this.
9. **Export in mm**: `bpy.ops.wm.stl_export(filepath=…, global_scale=1000,
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

## Like the photo, for print

A print is held in the hand and looked at from every side: it has to look like the reference,
not only pass the slicer. Measured on a carved figure rebuilt from one photo: the first version
passed every print check and the user found it "not alike at all".

1. **The photo method applies in full** (`reference-fidelity.md` § 1–5): cut the photo out,
   inventory on enlarged crops, measure from the pixels, review against the photo. Print mode
   changes how the volume is built, never how closely it follows the reference.
2. **Read openings on their outer edge, not on their shadow.** A carved opening shows its cut
   wall at an angle — a lit band around the dark — and the opening is that band's OUTER line.
   Tracing the dark gave a mouth three times too thin; tracing the shadow and the
   see-through gave eyes half their size. Read the outline on a 6× crop with a 10 px grid.
3. **Wall and groove depths come from the photo too.** The lit band of a cut wall gives the
   wall's thickness in pixels, hence in mm; the outline's bumps and the grooves' darkness give
   a relief's depth. The process minimum is a floor, never the value: a shell at the 1.2 mm
   minimum, where the photo showed three times that, read as paper.
   **An inner wall is an offset of the outer one, solved, not stepped**: a cavity whose radius
   was searched in 0.1 mm steps came out terraced in bands — Solidify, or a bisection to
   0.001 mm per ring.
4. **Project the front details along the photo's camera, not straight back.** A camera
   `--elevation` θ above sees a front point lower than it is: cut along the line
   z cos θ + y sin θ = v (y toward the back), not along y. Cut straight, every opening of one
   figure sat 4.9 mm low; cut along the view, the gap fell to 0.4 % and the face overlap rose
   from 0.24 to 0.63. **The outline too**: at θ > 0 the top of the silhouette is the back of
   the shoulders, not their side — read a turned profile through the same line. θ is read as
   `reference-fidelity.md` § 1 says, on any circle of the object.
   **A cut ends where the detail ends.** A cutter run through the whole figure engraved a
   ghost's eyes on its back as well: print_check passed, the face measure (front only) passed,
   and only the back capture of SKILL.md rule 2 showed it. Give every cutter its depth, and
   look at the side opposite each cut.
5. **Measure the face, not only the silhouette.** The silhouette IoU stayed at 0.90 while the
   mouth went from a line to a grin. Read `fidelity_check`'s `face` block and
   `face_overlay.png` every round: the `offset`, then each detail's area (too small / too
   large / missing). It is an alarm, not a judge (`reference-fidelity.md` § 5): it counts a lit
   cut wall as body, drops thin lines, and reads a deep groove's shadow as a detail.
6. **Iterate until the gaps stop closing, not for a fixed count.** Print mode lifts the photo
   method's two-round cap (`reference-fidelity.md` § 5): one change per round, measured.
   - A change that lowers the face measure by more than 0.01 is undone — unless the crops show
     it follows the photo where the measure is known blind (an outline traced on its outer edge,
     a thin line, a groove's shadow). Then the crop decides, and the log says why.
   - A move under 0.01 either way is noise: judge it on the crops.
   - **Stop when nothing is left to close**: every gap the overlay lists is either closed or
     known blind (a groove's shadow, a cut wall), and the crops show no difference a change
     could fix. Do not invent a change to get an empty round.
   - **A gap two rounds could not close is the method's limit, not a reason to go on**: log it
     as a limit (what was tried, what it measured) and move to the next gap; when every open
     gap is one, stop, and say so to the user. If the limits are the object itself — it was
     not a simple object after all — say that too (§ Scope) rather than hand over a likeness
     it is not.
   - The joint review and the close look at the cut edges (rule 7, `reference-fidelity.md`
     § 3 and § 6) come **before** stopping, not after: run them every round the joints or
     cuts changed — on a pumpkin they found a plateau, steps and a regression the numbers
     did not move on.
   - Then show the user `side_by_side.png`: they decide it is alike.
7. **Colour the preview from the photo** — one material per region sampled from it (body,
   stem), on a lit area, not in shadow. A print has no colour, but the review image is how the
   user judges the shape: a green stem left orange read as a stem half its size.
   Its edges too: a cut with no sharp edge marked reads as a staircase in the preview, and
   the user takes it for the print (`reference-fidelity.md` § 6, sharp edges). The STL
   carries no shading — check the geometry with flat shading before blaming it.
   **After a voxel remesh the regions are gone** — one mesh, one material. Give each face back
   the material of the part it came from (nearest part before the union, by BVH), then look at
   the colour boundary up close before measuring: the face measure reads colour, and a
   ghost's eyes read 12–18 % "too large" for ten rounds because the dark spilled one voxel
   past the engraving, not because the engraving was too large.
8. **Supports are normal for what the photo shows; overhangs are designed out where nobody
   looks.** Hanging teeth, paws or a round belly start in mid-air: check with `--supports` and
   say the print needs them, rather than flattening what the photo shows. What no one sees —
   the ceiling inside a hollow body, the underside of a base — is shaped for the printer (a 45°
   cone, a chamfer), as long as no visible opening looks onto it.
   **When openings look onto the ceiling** (a carved lantern), a 45° ceiling has to start above
   the highest opening — inside a round body it rarely fits: started lower, it turned a
   pumpkin's eyes into blind pockets. Three ways, said to the user (guided) or logged (auto):
   - **one part, bridged ceiling, supports** removed through the openings — the pumpkin's
     choice: a ~42 mm flat ceiling, PASS with supports, PrusaSlicer warning of a collapsing
     overhang. The default in auto mode;
   - **two parts split on a horizontal plane**, each printed open side clear of supports,
     glued along a line the photo already has (a rib's top, the ring round a stem) — how a
     real lantern is cut. Not measured here;
   - **no cavity**: openings as pockets one wall deep, painted dark — no see-through.
9. **The photo's colours are a question for CONFIG, not something the model drops.** On a
   single-colour printer each colour region is either painted afterwards — then the model
   carries the boundary as geometry (a 0.6 mm groove or step, § Printable from the brief, rule
   7) so the brush has an edge — or printed as its own part in its own filament, joined by a peg
   in a hole. The peg's clearance (0.2–0.3 mm per side on FDM) is a common starting value, not
   one measured here: say so, and offer a test print of the joint. Ask which, and log the
   answer.
10. **Nothing the photo does not show.** No opening, part or ornament on a side nobody
    photographed — background seen through an opening is not a view of the back
    (`reference-fidelity.md` § 2). The unseen side stays plain and closed, and the log lists it.
11. **Keep every round's numbers in the log**, whatever the storage mode: compact storage
    drops the intermediate FILES, never the measures. The .blend of a kept version is enough
    to come back to it.

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
  compares dimensions (3 %) and volume (10 %, only when the dimensions agree and BOTH the
  model and the reference are sealed — an open mesh voxelises to almost nothing: an open
  40 × 20 × 20 box gives 4 mm3). A closed cavity is voxelised as solid, so its exact volume is
  taken back out: a hollow figure saved before its openings were cut read as a 77 % loss
  against the carved model, 95 % once corrected (the cut openings). An open reference is
  compared on its dimensions alone, and
  the tool says so; a reference under one voxel of volume is a FAIL, never a ratio. The
  reference is first scaled to the model's height: a uniform scale is not a loss.
- **`--supports`** slices with PrusaSlicer's automatic supports. A figurine whose limbs hang starts
  them in mid-air: *Floating object part* without supports, a clean slice with them (a figure
  held in another's arms). The verdict can then PASS, and says the print needs them.
- **`--slicer`** (a path, or a name on the PATH) gives the scaled mesh to PrusaSlicer in a
  throwaway `--datadir`: `--info` (manifold, parts) and an FDM `--export-gcode`, whose log
  is searched for *Empty layer* and *Floating object part*; past `--slicer-timeout` (1800 s
  per call) it is an error, exit 1. **An arbiter in addition to the counts, never instead**: it
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
