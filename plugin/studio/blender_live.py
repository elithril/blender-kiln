"""Kiln Studio's live view, from inside Blender: one call at the end of a phase exports
the scene as `<folder>/<name>_live.glb` and records the phase, so the page open on
Studio reloads the model as it is built.

Run in Blender (over MCP, appended to the phase's last execute_blender_code call):

    import sys; sys.path.insert(0, "<skill>/studio")
    import blender_live
    blender_live.snapshot("<project>", "generated-assets/wooden-chair", "cleanup", "welded, normals out")

`folder` is the asset's kiln output folder, relative to the project (or absolute, inside
it); the asset is named after it. The export is written beside the folder's other files
under a hidden name, then moved into place, so Studio never reads half a file. Nothing in
the scene changes. `studio.py live <asset> --end` closes the build and removes the export.
"""

from __future__ import annotations

import os
from pathlib import Path

import studiolib as sl


def _target(project: sl.Project, folder: str) -> tuple[str, Path]:
    p = Path(folder)
    rel = project.rel(p) if p.is_absolute() else Path(folder).as_posix().strip("/")
    d = project.inside(rel)
    if d == project.root:
        raise ValueError("folder is the asset's own output folder, not the project root")
    return rel, d


def snapshot(root: str, folder: str, phase: str, text: str = "", export: bool = True) -> dict:
    """Export the scene for the live view, then record `phase` (and what it did, in a few
    words). `export=False` records the step alone (a phase that changed nothing visible)."""
    project = sl.Project(root)
    rel, d = _target(project, folder)
    phase = sl.norm_phase(phase)
    if export:
        import bpy  # only here: the rest of Studio runs without Blender
        d.mkdir(parents=True, exist_ok=True)
        final = d / f"{d.name}_{sl.LIVE}.glb"
        tmp = d / f".{d.name}_{sl.LIVE}.tmp.glb"
        # export_apply stays False (rule 18); no compression: this file is for looking at.
        bpy.ops.export_scene.gltf(filepath=str(tmp), export_format="GLB", export_apply=False,
                                  use_selection=False, export_cameras=False, export_lights=False)
        # The phase first, so the version Studio sees is filed under it.
        state = sl.set_live(project, rel, phase, text)
        os.replace(tmp, final)
        return state
    return sl.set_live(project, rel, phase, text)
