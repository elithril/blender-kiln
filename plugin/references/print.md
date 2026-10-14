# 3D Printing Reference

> What a printable mesh must be, and how `tools/print_check.py` says whether one is.

---

## Scope — the method follows the subject

Print mode models **simple objects and figures, each by its own method**:

- **A simple object** — turned or geometric, stylised, a bell, a block or a lathe with details
  cut or engraved: closed primitives and exact unions (§ Printable from the brief). Measured: a
  dog house, a lighthouse, a pumpkin, a ghost's body, a windmill, a teapot.
- **A stylised figure — a cartoon animal, a character, a mascot, from a drawing or a
  description: metaball families, then one voxel remesh** (§ Figures). Measured once: a v2.2
  session, given a single flat drawing of a cartoon dragon, built it that way in 23 minutes —
  standing, wings, tail, clothes — as four colour parts its user found "bluffant". The method
  was the session's own; it is written here so that it is not luck. Supports are normal for
  what the reference shows (§ Like the photo rule 8).
- **A realistic likeness of a real animal or person, from a photo: say at CONFIG that scripted
  modelling does not reach it.** A cat held by a ghost, then a real cat rebuilt from its photo —
  metaball ellipsoids for head and body, cones for the ears, exact unions — passed every print
  check and were unacceptable to look at. Offer what is honest: the subject as a stylised
  cartoon figure, said as such (above); an image-to-3D generation (`ai-generation.md`),
  repaired for print in [5]; or `print_check` on a model the user brings.
- **A model the user brings** (a sculpt, a scan, a model bought or downloaded):
  `tools/print_check.py` works on any mesh, and `tools/flatten.py` makes its nearly flat faces
  flat (§ A model you bring).

**A mechanical part — it carries a load, a lid must close, a size is called to the tenth: say
at CONFIG that a CAD tool is the right one** (build123d, CadQuery, OpenSCAD: exact circles,
fillets, dimensions). A Blender mesh has none of those, and print mode has not been measured on
such a part. Go on only if the user takes it as decorative, and log that answer. Parts that
join by a peg are fine: offer the joint's test print first (§ Printable from the brief rule 5).

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
   **The height asked is the object's, assembled** — parts printed apart included, a windmill
   to the tip of its top sail — unless the brief says otherwise; log which. Two sessions read
   it two ways: a forge took its flame in (70.1 mm), a windmill left its sails out and stood
   ~120 mm tall for a "~90 mm" brief.
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
     **That count is not the verdict — `print_check` on the exported STL is.** Two sessions
     read 0 in Blender while the STL had 84 and 480 edges shared by three faces or more; both
     cleared it by triangulating in Blender before exporting
     (`bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")`).
     A third found the same triangulation, done on the joined mesh, CAUSED 2 to 4 such edges at
     a spout's joint, and cleared them by triangulating each part BEFORE the union. No single
     recipe holds: export and check the STL after each risky step, and try one change at a
     time.
     Set `material_mode = "TRANSFER"` on every boolean: the default `INDEX` paints the second
     part in the first one's material (checked on two cubes, Blender 5.2.2), and the preview
     loses its regions. A difference with many cutters that fails as one pass (66 engraved
     motifs: 1,408 open edges) can pass split into a few passes — check after each.
   - **Interpenetrate, then one voxel remesh**: every part enters its neighbour by at least
     one wall thickness; join, Remesh `VOXEL` (adaptivity 0) at ≤ 0.2 mm and ≤ the thinnest
     feature / 8, then move the lowest vertex back to Z = 0. The study's lantern, remeshed
     at 0.2 mm, passes. The cost is weight: ~900,000 triangles for a 100 mm lantern.
   **A solid of revolution is the cheapest closed volume**: spin one profile (base, body, bands,
   corbels, roof) round Z with `bmesh.ops.spin(..., use_merge=True)` — one closed solid, no
   union at all. Measured on a 90 mm lighthouse: 0 non-manifold edges, PASS first time.
   **Close each end with a flat cap, not a point on the axis**, when anything is cut into it
   afterwards: a 50 mm lighthouse closed by merged axis points was clean, until an EXACT
   engraving re-cut the pole's fan and left a zero-length, non-manifold edge there; ends
   filled flat (`bmesh.ops.holes_fill`, a finial ending in a small disc) left 0 after every
   cut. **Never cut — or join — exactly on the lathe's edges**: windows placed at
   45° + 90°·k on a 64-step spin (one edge every 5.625°) left 3 non-manifold edges; the same
   cuts half a step off (2.8°) left 0. Unions too: a diamond shaft whose lower edge lay on a
   meridian of a 64-step cap, and a 45° cone passing through the corners of an octagon, each
   left non-manifold edges until moved half a step.
   **Remesh last** — for carving and joining the SHAPE; a figure's colour parts are cut from the
   remeshed solid by design (§ Figures rule 5), each then checked closed by the assembly check.
   A boolean applied after a voxel remesh (eyes engraved in a figure, a shell
   carved after a part was joined to it) left 2 to 9 edges shared by three faces: carve and
   join first, remesh at 0.2 mm once at the end, then decimate (2.35 M → 250 k triangles, still
   PASS). A part cut to fit another can leave a crumb behind (a tip hidden behind the other
   part): count islands, drop the ones hidden by the other part, and log it.
   Parts meet by **overlapping, never face to face nor vertex to vertex**: a cone and a sphere
   whose rings shared their vertex positions read as 5 non-manifold edges in the STL while
   Blender counted 0 — sink one part 0.2 mm into the other. Coplanar or touching faces are where an
   exact union leaves slivers and holes. Never `MANIFOLD` as the join: it returned a sealed,
   sliceable mesh that had dropped most of the object.
4. **Minimum thickness, imposed while modelling**, at print size: walls 1.2 mm FDM, 0.8 mm
   resin; free-standing pins, bars and handles 2 mm across FDM, 1 mm resin. The check's
   floors are 0.8 / 0.5 mm; the margin is there because its ray reads a slanted wall thinner.
   A detail the brief's height pushes under the minimum is thickened, and said so.
5. **A flat base on the bed**: lowest Z = 0 on a flat face that carries the object, origin at
   the bottom centre. Every part rests on the bed or enters another — two of the chest's parts
   ended 1.1 mm above the lid and PrusaSlicer reported an empty layer.
   **A part that would print in the air is printed apart**, each on its own best face: a
   lattice part, upright, had horizontal bars starting in mid-air; laid flat as a
   second part, both parts PASS with no support. **Each part's print orientation is a decision,
   written in the log**: which face goes on the bed, chosen for zero supports first, then the
   fewest and shortest bridges (rule 6), then the visible faces away from the bed — the bed
   face prints flat and smooth, and a relief on it is lost (rule 7). Each part gets its own STL, its own
   `print_check`, and its own line in the log; they join by a peg in a hole (the clearance of
   § Like the photo rule 9, not measured here — say so, and offer the test print below).
   **The peg goes on the part that stands steadier, the hole in the other**: a 35 mm flame
   standing on its own 4 × 4 mm peg got PrusaSlicer's *Low bed adhesion*; the peg moved to the
   forge and the hole into the flame, the flame stands on its whole base. **A tall part on a
   narrow foot** (a tree in its pot) can read the same warning: widening the pot from 18 to
   23 mm did not clear it, a 5 mm brim did — check with `print_check --brim-mm 5`, and say in
   the hand-over to print with one rather than reshape what the brief asked. A hole that ends
   inside an upright part gets a pointed 45° roof, not a flat ceiling (rule 6).
   **A hole that opens on the bed gets a 45° lead-in chamfer, 0.5 mm deep**, and so does the
   bed edge of a part that must fit into another: the first layer is squashed outward (the
   "elephant's foot") and closes the hole's mouth by a few tenths. The usual FDM advice, not
   measured yet — hole 4 of the test print below measures it. **The joint's test print**:
   `blender -b --factory-startup --python-exit-code 1 --python tools/fit_coupon.py -- --out DIR
   --peg-mm <the peg's side> --depth-mm <the hole's depth>` writes a plate with one diamond hole
   per clearance (0.1, 0.2, 0.3 mm a face) and one at 0.2 with the lead-in, and the peg on a
   wall, printed the way the model's is. **A round peg standing up** (a cap on a stem, a flame
   on its forge): `--shape round --peg-mm <its diameter>` — round holes, the peg standing on a
   base, as on the model; 23 + 5 minutes for an 8 mm peg 6.5 mm deep. About 20 minutes (PrusaSlicer's estimate, default
   profile); the tightest hole the peg enters is the clearance to model. Ask for that number
   before modelling a set of joints — **in auto mode, do not wait**: model at 0.2 mm a face,
   write the coupon to the output folder with the model, and say in the hand-over that the
   clearance is not measured. A peg the coupon does not make (a square one standing up) gets
   only an order of magnitude from the nearest shape: say that too.
   **A test piece is named and stored as one**: the coupon, and any piece a session cuts from
   the model to try a joint or a mechanism (a ring of a lid, a collar with its grooves), goes in
   a `test/` subfolder as `test_{what}.stl`, and the hand-over says to print it first. A user
   loading every STL of an output folder took two test rings for parts of the object and asked
   where the lid was.
6. **Overhangs past 45° from vertical are designed out**: undersides of eaves, caps and rims
   at 45° or steeper (a cone, a chamfer, a roof pitch ≥ 45°), grooves as V-cuts. What remains
   — the top of an arch, the inside of a ring — is reported with the check's overhang %.
   **And every overhang grows out of the part below it**: its lowest edge sits on what is
   under it, never in the air. A 50° eave with no face past 45° still failed — its tip is
   the lowest point of the roof, so each layer starts there as a new island (PrusaSlicer:
   *Floating object part*). Brace it back into the wall at ≥ 45° (a corbel), or end it there.
   **And a flat ceiling is a bridge — keep it short.** The ceiling of a cavity, the inside of
   a part printed opening-down, the roof of a hole: printed flat, each of its layers spans the
   gap in mid-air. PrusaSlicer bridges a few millimetres cleanly and warns *Long bridging
   extrusions* past that — a 20 mm flat ceiling drew it. **Past about 10 mm across, shape the
   ceiling as a 45° cone, pyramid or pointed vault** rising from its walls: no bridge at all,
   no support. Never shorten a bridge by filling the cavity: a solid added inside to make the
   ceiling smaller took 10 mm of usable depth from the object it was in. `print_check` passes
   the warning on: it is a change to make, not a line to report.
   **When the height is short of the cone** — a 45° cone needs half its width in height: a
   57 mm ceiling under 22 mm of part could not — start the vault from a ring inside the part's
   own wall, where it takes no usable volume: the ceiling steps in on that ring, then rises at
   45°, and what is left at the apex is a bridge of a few millimetres (2.4 mm there, sliced
   clean). Or split the part on a horizontal plane (§ Like the photo rule 8).
7. **Relief is geometry.** An STL has no colour, no material and no texture: letters, planks
   and frames are embossed or engraved — ≥ 0.6 mm deep FDM, 0.3 mm resin, strokes at the
   wall minimum. **The depth is the shallowest point's**: a flat cutter on a round wall cuts
   less deep at its sides than at its middle — a 50 mm lighthouse engraved 0.9-1.0 mm at the
   middle to keep its sides above 0.6. A texture or a normal map never carries information
   on a print.
   **Relief goes on faces that print upright or facing up.** A pattern on a face printed
   against the bed is flattened by the bed, and its grooves print as small bridges: a raised
   pattern on a part printed face-down drew *Long bridging extrusions* and 9 % of overhang
   for 1.2 mm grooves. Put the decoration on the walls and the upward faces of the print
   orientation (rule 5); a face that must go on the bed is left plain, or carries shallow
   engraved lines only. On a wall, a relief's underside obeys rule 6: chamfered at 45°, or
   pointed downward.
   **Paint regions are decided with or without a photo**: one filament and a painted result
   means each colour region ends on an edge the brush can follow (a 0.6 mm groove or step —
   § Like the photo rule 9 has the rule and the alternative, a part in its own filament), and
   the preview gives each region its own flat material so the user sees the paint plan.
   A region the brief does not name (a trunk, the soil in a pot) gets its edge too, and the
   hand-over lists it as the user's choice to paint or not.
   **Cut a pattern as exact polygons, never on a grid**: engraved diamonds built on a
   displaced grid kept the grid's step on every slanted edge — a ~0.2 mm staircase, plain in
   a matcap close-up although every check passed. A grid is fine for a straight groove that
   follows its rows; anything slanted is a boolean of a real outline.
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
   **Delete the `.blend1`** Blender writes beside each re-saved file — every session of
   2026-10-13 left two to four of them in a compact output folder — or set
   `bpy.context.preferences.filepaths.save_version = 0` before saving (checked, Blender 5.2.2:
   saved twice, no `.blend1`; without it, one).
   **An object hidden from the render exports nothing**: `hide_render` left on the sails after
   the review renders wrote an 84-byte STL, 0 triangles, with no error. Restore visibility
   before exporting; `print_check` counts the triangles.
   Then `print_check.py` on the STL; PASS is required, or say what fails. **Hand over the
   size with the file**: the height it was modelled for, and the check's `SCALE` line — "do
   not shrink below N %; enlarging is safe". For parts that assemble, the largest of their
   scales holds for all of them: a peg and its hole shrink together, the clearance does not
   (it is printer-side), so say that a scaled joint wants a new clearance.

Measured on two objects modelled headless from these rules alone (Blender 5.2.2, PrusaSlicer
2.9.6): a dog house, 72 × 64 × 79.4 mm FDM, union as you go — 854 triangles, one closed part,
PASS (overhangs 0.69 %), and its 3MF too; a lantern, 44 × 44 × 100.5 mm resin, voxel at
0.2 mm — 889,152 triangles, PASS (overhangs 1.18 %, 75 self-intersecting pairs left by the
remesh, a warning; sliced as FDM, the only slicer pass). The dog house's first build failed on
its eaves: rule 6's second half comes from it.

## Figures: metaballs, then one voxel remesh

What a session found by itself on a cartoon character, checked here before it was written. A
stylised figure is organic: its volumes melt into each other, which primitives cannot do and
metaballs do by construction. It is not a way to a realistic likeness: a cat from its photo,
made of metaball ellipsoids, was still unacceptable (§ Scope). What differed on the figure that
worked: one family per region, every part joined by ONE remesh rather than exact unions, and a
drawing — a stylised subject — rather than a photo.

1. **Model at ten times the size.** Blender's metaball resolution stops at 0.005 (5 mm at
   1 unit = 1 m, checked on Blender 5.2.2): far too coarse for a 100 mm figure. Build it about
   1 m tall — the one exception to rule 1, said in the log; every thickness of rule 4 is then
   read ×10. **Scale the meshes back by the print height over the model's height before
   exporting** (×0.1 for a 1 m model printed at 100 mm), then export as rule 9 says
   (`global_scale=1000`): the STL comes out at the print height, in mm, and `print_check` reads
   it as any other.
2. **One metaball family per region** — body and head, each arm, the legs or feet, the tail —
   so that regions meant to stay apart do not melt together. A tube is a row of elements along a
   path, spaced about a quarter of their radius, so its outline stays even. An element shows a
   radius of **0.574 × its radius** at stiffness 2 and threshold 0.6 (measured: 0.574 at
   resolution 0.05, 0.575 at 0.02) — **alone**. In a row spaced a quarter of their radius their
   fields add: 0.673 for two elements, **0.715 × r** from five on (measured, resolution 0.02).
   Size a tube's elements with 0.715, a lone blob with 0.574, and check on the render.
3. **Thin parts as closed meshes** — ears, horns, a wing's membrane, a tail's tip — overlapping
   the metaballs by at least one wall, at the minimum thickness of rule 4 once printed (a wing
   membrane at 2.4 mm printed passed the checks; not printed yet).
4. **Convert, join and remesh once**: every metaball family and mesh part into one object, one
   voxel remesh — rule 3's 0.2 mm once printed is the safe value; 0.45 mm passed on a 100 mm
   figure with no detail under 1.5 mm, 0.35 on an 80 mm one — then a flat cut at Z = 0 so that
   the feet stand.
   One watertight solid, whatever overlapped (rule 3, interpenetrate then remesh).
5. **Colours as parts** (§ Like the photo rule 9): each colour a closed part cut from the
   solid by booleans in a priority order (black, then eye white, then clothes, then skin): each
   part loses the UNCUT tool shape of the parts above it, never a piece already cut to its skin
   — that left zero-area slivers. Eyes, nostrils and a mouth line are flush inlays, at least
   1.5 mm wide. Parts must not overlap: their union is the figure.
6. **Check the parts together**: `print_check part1.stl part2.stl … --slicer …` checks each
   part closed, then their union as one figure (§ The tool). One colour's file alone is not a
   printable object — the pupils float without the head that holds them. The figure's
   `--reference` is the solid BEFORE the colour cut (its metaballs and meshes saved before the
   remesh): check that solid alone against it first, then the colour parts as an assembly.
7. **Hand over the assembly**: one STL per colour, and a 3MF with the parts when the 3MF
   extension is installed (rule 9). Say how to load it — all the STLs together, answered *yes*
   to "load as a single object with multiple parts", one filament per part; on a single-colour
   printer, all the parts with the same filament (no single STL holds the whole figure). Say
   where supports go (under a snout, wings, elbows, a tail's curl) and the brim for small feet.
   **Write it in a `PRINT.md` next to the STLs, in the user's language** — not only in the log:
   a user looking at four STLs asked how the scarf would get round the neck. Say in its first
   line that the files are ONE print in several colours, not parts to assemble.

## A model you bring

`print_check` works on any mesh, and `tools/flatten.py` is the one change kiln makes to a model
it did not build. A model finished by hand often has faces that should be flat and are not,
and sits a degree off; the slicer prints it as it is.

```
blender -b --factory-startup --python-exit-code 1 --python tools/flatten.py -- \
    model.stl --out model_flat.stl --bed --json flatten.json      # then print_check on both
```

- **What it changes**: a face whose vertices all lie within `--tol-mm` (0.3) of one plane, and
  that is not a shape, becomes exactly flat; a flattened plane within 1° of an axis becomes
  that axis; `--bed` first turns the model so its largest downward face is level, then sets it
  on Z = 0. Vertices shared by flat faces land where their planes meet, so edges stay sharp.
- **What it keeps** — each one a case that broke a version of the tool on a real file: a curve
  (a quadric fits it), a fold or a wave (its distance to the plane varies smoothly between
  neighbours: a ghost's sides came out faceted until this), a patch that runs on into its
  neighbours without an edge, a 0.2 mm step behind a vertical wall, a bevel turning more than
  8° (a chest's plank bevels were flattened away until this), a real slope.
- **What it does not do**: fill a hole (the slicer closes small ones; `print_check` says where
  the rest are), change the triangle list, move a vertex past the tolerance, write over its
  input.
- **Measured** on the windmill, turned 1° with 10 % of its vertices off by 0.1-0.25 mm:
  PrusaSlicer finished its gallery floor at 4 heights and held it by one edge of the base
  (629 mm of first layer); flattened, one height and the whole base (3,317 mm). 52 of its 74
  flat faces back flat to 0.01 mm; with every vertex off (scan-like noise), 31. On the
  windmill, the teapot, the pumpkin and the ghost as kiln made them, nothing moves but the
  ghost's base (0.01 mm). A script in the repository's examples rebuilds the README's figure
  from the G-code alone.

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
   - **On an illustration** (a logo, a painting) the face measure reads painted light and
     shadow as details: on the forge logo it stayed at 0.00 every round. Judge on the
     silhouette (±0.01) and the crops, and say so in the log.
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
   one measured here: say so, and offer a test print of the joint (`tools/fit_coupon.py`,
   § Printable from the brief rule 5). Ask which, and log the answer.
10. **Nothing the photo does not show.** No opening, part or ornament on a side nobody
    photographed — background seen through an opening is not a view of the back
    (`reference-fidelity.md` § 2). The unseen side stays plain and closed, and the log lists it.
11. **Keep every round's numbers in the log**, whatever the storage mode: compact storage
    drops the intermediate FILES, never the measures. The .blend of a kept version is enough
    to come back to it.

## The tool

```
blender -b --factory-startup --python-exit-code 1 --python tools/print_check.py -- \
    model_body.stl --process fdm \
    --reference model_body_parts.blend --slicer /Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer \
    --json check.json
```

**`--height-mm` SCALES the file** to that height before checking — for reading a model at
another size (`SCALE`, below), never to state the brief's height. A file modelled at size
needs none: given the assembly's 90 mm, a 71 mm body would be checked enlarged.

STL (mm), 3MF (its own unit), GLB and .blend (metres). Exit 0 PASS, 3 FAIL, 1 error.

- **Counted raw.** Vertices are shared only when their coordinates are bit-identical. The
  study's first measure welded at 1e-5 before counting; that glued neighbouring shells and
  made defects the file did not have. The tool's counts match an independent exact edge
  pairing on every study file.
- **`--reference`** is the file the model came from: the original before a repair, or — for a
  model built from scratch by unions — the parts saved just before the union (both sessions
  that built one chose that, and it caught nothing false), saved as `{name}_{part}_parts.blend`,
  **one per printed part**: the tool reads every visible mesh of a .blend, so one file for two
  parts compares each part with both; for
  a solid turned and then engraved, that solid before the engravings. A part built closed in
  one piece, with no union and no repair, has none: say so. A part whose one operation is a
  small cut (a peg hole in a star) proves little against its reference — a hole of a few
  mm³ is under the 10 % volume tolerance: measure the cut itself on a section instead. It voxelises both meshes at the same size (largest dimension / 150) and
  compares dimensions (3 %) and volume (10 %, only when the dimensions agree and BOTH the
  model and the reference are sealed — an open mesh voxelises to almost nothing: an open
  40 × 20 × 20 box gives 4 mm3). A closed cavity is voxelised as solid, so its exact volume is
  taken back out: a hollow figure saved before its openings were cut read as a 77 % loss
  against the carved model, 95 % once corrected (the cut openings). An open reference is
  compared on its dimensions alone, and
  the tool says so; a reference under one voxel of volume is a FAIL, never a ratio. The
  reference is first scaled to the model's height: a uniform scale is not a loss.
- **Several files are an assembly** — a figure in several colours, one file per colour:
  `print_check green.stl blue.stl ivory.stl black.stl --process fdm --slicer …`. Each file is
  checked closed on its own; the parts' overlap is measured (summed volumes less the union's) and
  warned past 1 %; their union — one voxel remesh at 0.25 mm or finer — is checked as one object,
  slicer included. One colour alone is not a printable object (the pupils float without the head
  that holds them), and the files laid end to end in one STL share their contact faces: both
  FAIL a print that is fine. Measured on a four-colour dragon: each colour alone FAILed three
  times out of four; the assembly PASSes, its union 68.4 cm³ against the 68.2 its session had
  measured with another library, overlap 0. Its `SCALE` is the thinnest PART's, not the union's
  (rule 9: parts that print together shrink together): a fox's union held to 20 %, its orange part
  — thin walls between the inlays — to 80 %, and the line says which part sets it.
  `--reference` checks one model: not an assembly.
- **`--brim-mm`** slices with a brim that wide: *Low bed adhesion* on a tall, narrow part
  (a flame on its own base, a tree in its pot) went with 5 mm, and the warning without a brim
  names the option. The verdict then says to print with one.
- **`--supports`** slices with PrusaSlicer's automatic supports. A figurine whose limbs hang starts
  them in mid-air: *Floating object part* without supports, a clean slice with them (a figure
  held in another's arms). The verdict can then PASS, and says the print needs them.
- **`--slicer`** (a path, or a name on the PATH) gives the scaled mesh to PrusaSlicer in a
  throwaway `--datadir`: `--info` (manifold, parts) and an FDM `--export-gcode`, whose log
  is searched for *Empty layer* and *Floating object part*; past `--slicer-timeout` (1800 s
  per call) it is an error, exit 1. **An arbiter in addition to the counts, never instead**: it
  slices open meshes with exit 0 and calls the MANIFOLD union that lost the object manifold.
  It also sees what the counts do not — a gap between layers.
- **`SCALE`, the smallest scale.** A slicer shrinks every wall with the model, and makers
  rescale in the slicer as a habit: an STL carries no unit, and nothing in it says what size
  it was designed for. From the same walls, the tool gives the scale under which 1 % more of
  the area would fall under the process floor, and the dimensions there. Measured: the
  windmill's body 40 % (its 2 mm railing posts), the lighthouse 67 % (its 1.2 mm parapet),
  the teapot 67 %. Not the first wall to cross: that was 2 faces at the foot of the
  lighthouse's door (0.09 % of the area) at 80 %. Walls only: an engraving's depth and a
  bar's width are not counted apart. **The rim of an engraving on a round wall reads thin**
  (the ray leaves through the curve beside it) and weighs on the line: look at the faces
  flagged before thickening anything — the JSON's `thickness.thin_at` lists where they are
  (centre in mm, wall read), and `tools/review_renders.py --close-from check.json` renders
  them. On the 50 mm lighthouse every face left under 0.8 mm was such a rim. A real thin wall is fixed even when that lowers the line's margin. **Always a scale of the file**: `--height-mm` does not
  move it, and a height under it is a warning — the lighthouse read at 49.5 mm, 55 %, is
  under its 67 %, with 5.4 % of its area under 0.8 mm.

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
- `fit_coupon.py` makes diamond pegs on their side and round pegs standing up, and measures
  nothing itself: the printer and the hand that tries the peg do.
- Decorative objects, not mechanical parts: a mesh modelled in Blender has no exact circle,
  no fillet, no dimension a drawing could call. A bracket, a box whose lid must close, a
  hook that takes a load belong in a CAD tool (build123d, CadQuery, OpenSCAD) — say so.
- Self-intersections are counted (Blender's BVH), not repaired, and not a FAIL: a slicer
  merges overlapping solids. Pairs that only TOUCH — a shared vertex, a vertex lying on a
  face — are not counted: each triangle is shrunk 0.1 % toward its centroid and tested again
  (the windmill's sails read 32 such pairs, a coupon 4, all at distance 0; now 0). A crossing
  shallower than that 0.1 % is not told from a touch.
- Overhangs are counted past 45.5° (a face modelled at 45° reads 45.0x° in an STL), as a
  share: small ceilings bridge. Whether the print needs supports is the slicer's answer —
  "sliced clean without supports: none needed" — not the share's.
