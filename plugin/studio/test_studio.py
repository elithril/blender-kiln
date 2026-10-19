#!/usr/bin/env python3
"""Kiln Studio's tests: scan, stats, notes, history, baseline, the live build, work runs, checks, and the HTTP API.

    python3 plugin/studio/test_studio.py

Standard library only, no network, no browser: models are tiny GLBs built here.
"""

from __future__ import annotations

import base64
import contextlib
import http.client
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checks  # noqa: E402
import estimate  # noqa: E402
import server  # noqa: E402
import studio  # noqa: E402
import studiolib as sl  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 16
WEBP = b"RIFF\x10\0\0\0WEBPVP8 " + b"\0" * 16


def png(w: int, h: int) -> bytes:
    """A PNG header: enough for a size reader, not a decodable image."""
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x06\0\0\0"


def glb(path: Path, *, scale: float = 1.0, tris: int = 1, name: str = "SM_Box",
        lift: float = 0.0, image: bytes | None = None, mime: str = "image/png",
        extensions: list[str] | None = None) -> Path:
    """A valid GLB with one mesh of `tris` triangles, 1 m tall (times `scale`), standing on
    the ground (raised by `lift`); with `image`, a base colour texture embedded in it."""
    n = tris * 3
    positions = b"".join(struct.pack("<3f", (i % 2) * 0.5, (i % 3) * 0.5, 0.25) for i in range(n))
    gltf = {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"name": name, "mesh": 0, "scale": [scale, scale, scale], "translation": [0, 0.5 + lift, 0]}],
        "meshes": [{"name": name + "_Mesh", "primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}],
        "materials": [{"name": "M_Wood"}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": n, "type": "VEC3",
                       "min": [-0.5, -0.5, -0.25], "max": [0.5, 0.5, 0.25]}],
        "bufferViews": [{"buffer": 0, "byteLength": len(positions)}],
        "buffers": [{"byteLength": len(positions)}],
    }
    body = positions + b"\0" * (-len(positions) % 4)
    if image is not None:
        gltf["images"] = [{"bufferView": 1, "mimeType": mime, "name": "T_Box_BaseColor"}]
        gltf["textures"] = [{"source": 0}]
        gltf["materials"][0]["pbrMetallicRoughness"] = {"baseColorTexture": {"index": 0}}
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": len(body), "byteLength": len(image)})
        body += image + b"\0" * (-len(image) % 4)
        gltf["buffers"][0]["byteLength"] = len(body)
    if extensions:
        gltf["extensionsUsed"] = list(extensions)
    js = json.dumps(gltf).encode()
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, total)
                     + struct.pack("<II", len(js), 0x4E4F534A) + js
                     + struct.pack("<II", len(body), 0x004E4942) + body)
    return path


def stl(path: Path, tris: int = 2, size_mm: float = 30.0) -> Path:
    """A binary STL of `tris` triangles inside a size_mm cube."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = b"".join(struct.pack("<12fH", 0, 0, 1, 0, 0, 0, size_mm, 0, 0, 0, size_mm, size_mm, 0) for _ in range(tris))
    path.write_bytes(b"\0" * 80 + struct.pack("<I", tris) + body)
    return path


def threemf(path: Path, tris: int = 3) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    verts = '<vertex x="0" y="0" z="0"/><vertex x="40" y="0" z="0"/><vertex x="0" y="20" z="10"/>'
    xml = ('<?xml version="1.0"?><model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
           f'<resources><object id="1" type="model"><mesh><vertices>{verts}</vertices><triangles>'
           + '<triangle v1="0" v2="1" v3="2"/>' * tris + '</triangles></mesh></object></resources><build><item objectid="1"/></build></model>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("3D/3dmodel.model", xml)
    return path


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="kiln-studio-test-"))
        self.p = sl.Project(self.tmp)
        # Never the user's own ~/.kiln-studio.
        self._home = os.environ.get("KILN_STUDIO_HOME")
        os.environ["KILN_STUDIO_HOME"] = str(self.tmp / ".home")

    def tearDown(self) -> None:
        if self._home is None:
            os.environ.pop("KILN_STUDIO_HOME", None)
        else:
            os.environ["KILN_STUDIO_HOME"] = self._home
        shutil.rmtree(self.tmp, ignore_errors=True)


class Scan(Base):
    def test_kiln_layout_is_one_asset_with_stages(self) -> None:
        d = self.tmp / "generated-assets" / "wooden-chair"
        glb(d / "wooden-chair_original.glb")
        glb(d / "wooden-chair_final.glb")
        (d / "wooden-chair_log.md").write_text("# log")
        (d / "wooden-chair.blend").write_bytes(b"BLENDER")
        (d / "reference.png").write_bytes(b"\x89PNG")
        [a] = self.p.scan()
        self.assertEqual(a.id, "generated-assets/wooden-chair")
        self.assertTrue(a.kiln)
        self.assertEqual([v.label for v in a.variants], ["final", "original"])  # most finished first
        self.assertEqual(a.default_category, "generated-assets")
        self.assertEqual(a.log_file(), "generated-assets/wooden-chair/wooden-chair_log.md")
        self.assertEqual(a.blend_file(), "generated-assets/wooden-chair/wooden-chair.blend")
        self.assertIn("generated-assets/wooden-chair/reference.png", a.files)

    def test_outputs_in_their_folders_are_the_model_s(self) -> None:
        d = self.tmp / "generated-assets" / "stool"
        glb(d / "stool_original.glb")
        (d / "stool.blend").write_bytes(b"BLENDER")
        glb(d / "web" / "stool_final.glb")
        (d / "game").mkdir()
        (d / "game" / "stool_game.fbx").write_bytes(b"Kaydara FBX Binary")
        glb(d / "ar" / "stool_ar.glb")
        (d / "ar" / "stool_ar.usdz").write_bytes(b"PK\x03\x04")
        threemf(d / "print" / "stool_print.3mf", tris=3)
        stl(d / "print" / "stool_print_seat.stl", tris=2)
        stl(d / "print" / "stool_print_legs.stl", tris=4)
        glb(self.tmp / "props" / "web" / "lamp.glb")   # a folder named web elsewhere is just a folder
        a, lamp = sorted(self.p.scan(), key=lambda x: x.id)
        self.assertEqual(a.id, "generated-assets/stool")
        self.assertEqual([v.label for v in a.variants], ["final", "original", "print", "game", "ar", "ar.usdz"])
        self.assertEqual(a.variant("final").rel, "generated-assets/stool/web/stool_final.glb")
        self.assertIn("generated-assets/stool/print/stool_print_seat.stl", a.files)   # a part: not a model of its own
        st = sl.variant_stats(a.variant("print"))
        self.assertEqual((st["tris"], st["meshes"], st["units"]), (3, 1, "millimeter"))
        self.assertEqual(st["dimensions_blender"], [0.04, 0.02, 0.01])
        one = sl.stl_stats(d / "print" / "stool_print_legs.stl")
        self.assertEqual((one["tris"], one["dimensions_blender"]), (4, [0.03, 0.03, 0.03]))
        self.assertEqual(lamp.id, "props/web/lamp")

    def test_a_final_at_the_root_is_still_the_web_output(self) -> None:
        glb(self.tmp / "generated-assets" / "chair" / "chair_final.glb")
        [a] = self.p.scan()
        self.assertEqual([v.label for v in a.variants], ["final"])

    def test_batch_folder_is_the_category(self) -> None:
        glb(self.tmp / "generated-assets" / "batch-office" / "desk" / "desk_final.glb")
        [a] = self.p.scan()
        self.assertEqual(a.default_category, "generated-assets/batch-office")

    def test_loose_files_and_formats(self) -> None:
        glb(self.tmp / "assets" / "props" / "crate.glb")
        (self.tmp / "assets" / "props" / "crate.obj").write_text("v 0 0 0\n")
        glb(self.tmp / "assets" / "props" / "barrel.glb")
        ids = {a.id: a for a in self.p.scan()}
        self.assertEqual(sorted(ids), ["assets/props/barrel", "assets/props/crate"])
        self.assertEqual([v.label for v in ids["assets/props/crate"].variants], ["glb", "obj"])
        self.assertFalse(ids["assets/props/crate"].kiln)
        self.assertEqual(ids["assets/props/crate"].default_category, "assets/props")

    def test_skips_hidden_vendor_and_excluded(self) -> None:
        glb(self.tmp / ".godot" / "imported" / "x.glb")
        glb(self.tmp / "node_modules" / "pkg" / "y.glb")
        glb(self.tmp / "site" / "public" / "z.glb")
        glb(self.tmp / "keep.glb")
        self.p.data.mkdir()
        (self.p.data / "config.json").write_text(json.dumps({"exclude": ["site/public/*"]}))
        self.assertEqual([a.id for a in self.p.scan()], ["keep"])

    def test_symlink_out_of_the_project_is_skipped(self) -> None:
        outside = Path(tempfile.mkdtemp(prefix="kiln-studio-outside-"))
        try:
            glb(outside / "x.glb")
            glb(self.tmp / "props" / "real.glb")
            (self.tmp / "props" / "linked.glb").symlink_to(outside / "x.glb")
            self.assertEqual([a.id for a in self.p.scan()], ["props/real"])
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_inside_refuses_unc_drive_and_absolute(self) -> None:
        for bad in ("\\\\evil\\share\\x", "C:/Windows/win.ini", "/etc/passwd", "../x", "a/../../x"):
            with self.assertRaises(ValueError, msg=bad):
                self.p.inside(bad)
        self.assertEqual(self.p.inside("a/b.glb"), self.tmp.resolve() / "a" / "b.glb")

    def test_keys_do_not_collide(self) -> None:
        ids = ["a/b", "a~b", "a%7Eb", "a/~b", "a~/b"]
        self.assertEqual(len({sl.asset_key(i) for i in ids}), len(ids))
        self.assertEqual(sl.asset_key("generated-assets/chair"), "generated-assets~chair")

    def test_find_accepts_a_bare_name(self) -> None:
        glb(self.tmp / "generated-assets" / "lamp" / "lamp_final.glb")
        self.assertEqual(self.p.find("lamp").id, "generated-assets/lamp")
        with self.assertRaises(KeyError):
            self.p.find("nope")


class Stats(Base):
    def test_counts_and_blender_dimensions(self) -> None:
        f = glb(self.tmp / "m.glb", scale=2.0, tris=4)
        st = sl.gltf_stats(f)
        self.assertEqual(st["tris"], 4)
        self.assertEqual(st["verts"], 12)
        self.assertEqual(st["materials"], ["M_Wood"])
        # glTF box 1 x 1 x 0.5 scaled by 2 → Blender X 2, Y (glTF z) 1, Z (glTF y) 2.
        self.assertEqual(st["dimensions_blender"], [2.0, 1.0, 2.0])
        self.assertAlmostEqual(st["bbox"]["min"][1], -0.5)  # translated up 0.5, scaled 2

    def test_not_a_glb(self) -> None:
        f = self.tmp / "bad.glb"
        f.write_bytes(b"nope")
        with self.assertRaises(ValueError):
            sl.gltf_stats(f)


class Notes(Base):
    def setUp(self) -> None:
        super().setUp()
        self.f = glb(self.tmp / "generated-assets" / "chair" / "chair_final.glb")
        self.a = self.p.find("chair")

    def test_lifecycle_and_after_shot(self) -> None:
        n = sl.add_note(self.p, self.a, "  legs too thin ", anchor={"point": [0, 1, 0]}, shot=JPEG)
        self.assertEqual(n["status"], "open")
        self.assertEqual(n["kind"], "pin")
        self.assertEqual(n["text"], "legs too thin")
        self.assertTrue((self.tmp / n["shot"]).exists())
        self.assertEqual(n["version"]["hash"], sl.file_hash(self.f))
        # Claude re-exports, then replies "addressed": the page owes an after shot.
        glb(self.f, tris=2)
        a = self.p.find("chair")
        r = sl.reply(self.p, a, n["id"], "thicker legs", by="claude", status="addressed")
        self.assertEqual(r["version"]["hash"], sl.file_hash(self.f))
        notes = sl.load_notes(self.p, a.id)
        self.assertEqual(notes[0]["status"], "addressed")
        self.assertEqual(sl.pending_shots(notes, a), [{"note": n["id"], "reply": r["id"], "variant": "final"}])
        rel = sl.set_reply_shot(self.p, a.id, n["id"], r["id"], JPEG)
        self.assertTrue(rel.endswith(".jpg"))
        self.assertEqual(sl.pending_shots(sl.load_notes(self.p, a.id), a), [])
        # A later re-export makes the owed shot moot: it would show the wrong version.
        n2 = sl.add_note(self.p, a, "seat")
        r2 = sl.reply(self.p, a, n2["id"], "done", by="claude", status="addressed")
        glb(self.f, tris=3)
        a = self.p.find("chair")
        self.assertNotIn(r2["id"], [p["reply"] for p in sl.pending_shots(sl.load_notes(self.p, a.id), a)])

    def test_only_the_user_resolves(self) -> None:
        n = sl.add_note(self.p, self.a, "x")
        with self.assertRaises(ValueError):
            sl.reply(self.p, self.a, n["id"], "done", by="claude", status="resolved")
        sl.reply(self.p, self.a, n["id"], "", by="user", status="resolved")
        self.assertEqual(sl.load_notes(self.p, self.a.id)[0]["status"], "resolved")

    def test_view_and_close_up(self) -> None:
        view = {"crop": [0.2, -0.5, 0.8, 0.9], "detail": {"position": [0, 1, 2], "target": [0, 1, 0], "fov": 35},
                "junk": "<script>"}
        n = sl.add_note(self.p, self.a, "dent here", anchor={"point": [0, 1, 0]}, view=view, shot=WEBP, detail=WEBP)
        self.assertTrue(n["shot"].endswith(f"{n['id']}.webp"))
        self.assertTrue(n["detail"].endswith(f"{n['id']}_detail.webp"))
        self.assertEqual(n["view"], {"crop": [0.2, 0.0, 0.8, 0.9],
                                     "detail": {"position": [0, 1, 2], "target": [0, 1, 0], "fov": 35.0}})
        self.assertIsNone(sl.clean_view({"crop": [0.5, 0, 0.4, 1], "detail": {"fov": 500}}))
        r = sl.reply(self.p, self.a, n["id"], "filled", by="claude", status="addressed")
        sl.set_reply_shot(self.p, self.a.id, n["id"], r["id"], WEBP, WEBP)
        [got] = sl.load_notes(self.p, self.a.id)
        self.assertTrue(got["thread"][0]["detail"].endswith("_detail.webp"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            studio.main(["show", "chair", "--root", str(self.tmp)])
        self.assertIn("close-up of the pin:", out.getvalue())
        self.assertIn("close-up:", out.getvalue())
        sl.delete_note(self.p, self.a.id, n["id"])
        self.assertEqual(list((self.p.asset_dir(self.a.id) / "shots").iterdir()), [])

    def test_delete_removes_shots(self) -> None:
        n = sl.add_note(self.p, self.a, "x", shot=JPEG)
        sl.delete_note(self.p, self.a.id, n["id"])
        self.assertEqual(sl.load_notes(self.p, self.a.id), [])
        self.assertEqual(list((self.p.asset_dir(self.a.id) / "shots").iterdir()), [])

    def test_meta(self) -> None:
        sl.set_meta(self.p, self.a.id, category="Props/Furniture/", tags=["Wood", " low poly ", "wood"])
        e = sl.load_catalog(self.p)["assets"][self.a.id]
        self.assertEqual(e, {"category": "Props/Furniture", "tags": ["low-poly", "wood"]})
        sl.set_meta(self.p, self.a.id, category="", tags=[])
        self.assertNotIn(self.a.id, sl.load_catalog(self.p)["assets"])

    def test_gitignore_keeps_notes_and_drops_copies(self) -> None:
        sl.add_note(self.p, self.a, "x")
        ignore = (self.p.data / ".gitignore").read_text().split()
        self.assertIn("baseline/", ignore)
        self.assertIn("cache/", ignore)
        self.assertNotIn("assets/", ignore)


class History(Base):
    def test_versions_and_baseline_revert(self) -> None:
        f = glb(self.tmp / "lamp" / "lamp_final.glb", tris=1)
        a = self.p.find("lamp")
        h1 = sl.file_hash(f)
        sl.add_note(self.p, a, "brighter")              # takes the baseline (n-1)
        self.assertEqual(sl.baseline(self.p, a.id)["hash"], h1)
        sl.add_note(self.p, a, "taller")                # same version: same baseline
        self.assertEqual(sum(e["type"] == "baseline" for e in sl.load_history(self.p, a.id)), 1)
        glb(f, tris=5)
        a = self.p.find("lamp")
        h2 = sl.file_hash(f)
        self.assertEqual(len(sl.observe(self.p, a)), 1)
        self.assertEqual(sl.observe(self.p, a), [])     # nothing new the second time
        versions = [e for e in sl.load_history(self.p, a.id) if e["type"] == "version"]
        self.assertEqual([v["hash"] for v in versions], [h1, h2])
        self.assertEqual([v["tris"] for v in versions], [1, 5])
        # Revert puts h1 back and keeps h2 as the previous version: undoable.
        sl.revert(self.p, a)
        self.assertEqual(sl.file_hash(f), h1)
        self.assertEqual(sl.baseline(self.p, a.id)["hash"], h2)
        sl.revert(self.p, self.p.find("lamp"))
        self.assertEqual(sl.file_hash(f), h2)

    def test_gltf_with_encoded_uris_reverts_whole(self) -> None:
        d = self.tmp / "m"
        d.mkdir()

        def write(tag: str) -> None:
            (d / "My Chair.bin").write_bytes(b"\0" * 36 + tag.encode())
            (d / "My Chair.gltf").write_text(json.dumps({
                "asset": {"version": "2.0", "generator": tag}, "buffers": [{"uri": "My%20Chair.bin", "byteLength": 37}]}))

        write("A")
        a = self.p.find("My Chair")
        sl.take_baseline(self.p, a, reason="t")
        self.assertTrue((self.p.baseline_dir(a.id) / "My Chair.bin").exists())
        write("B")
        sl.revert(self.p, self.p.find("My Chair"))
        self.assertEqual((d / "My Chair.bin").read_bytes()[-1:], b"A")
        self.assertEqual((self.p.baseline_dir(a.id) / "My Chair.bin").read_bytes()[-1:], b"B")

    def test_one_copy_only(self) -> None:
        f = glb(self.tmp / "m.glb")
        for i in range(4):
            glb(f, tris=i + 1)
            sl.take_baseline(self.p, self.p.find("m"), reason=str(i))
        self.assertEqual(len(list((self.p.data / "baseline").iterdir())), 1)
        self.assertEqual(len(list(self.p.baseline_dir("m").glob("*.glb"))), 1)

    def test_log(self) -> None:
        glb(self.tmp / "m.glb")
        sl.log(self.p, self.p.find("m"), "rounded the edges")
        self.assertEqual(sl.load_history(self.p, "m")[-1]["text"], "rounded the edges")


class Live(Base):
    def test_live_stage_leads_while_newest(self) -> None:
        d = self.tmp / "generated-assets" / "chair"
        glb(d / "chair_original.glb")
        live = glb(d / "chair_live.glb")
        t = time.time()
        os.utime(d / "chair_original.glb", (t - 60, t - 60))
        os.utime(live, (t, t))
        [a] = sl.scan(self.p)
        self.assertEqual([v.label for v in a.variants], ["live", "original"])
        glb(d / "chair_final.glb")
        os.utime(d / "chair_final.glb", (t + 60, t + 60))
        [a] = sl.scan(self.p)
        self.assertEqual([v.label for v in a.variants], ["final", "original", "live"])

    def test_build_record_before_the_first_export(self) -> None:
        aid = "generated-assets/chair"
        sl.set_live(self.p, aid, "[3] SOURCE", "blockout")
        st = sl.set_live(self.p, aid, "5b", "oak scan")
        self.assertEqual((st["state"], st["phase"]), ("building", "texture"))
        self.assertEqual([x["phase"] for x in st["steps"]], ["source", "texture"])
        with self.assertRaises(ValueError):
            sl.set_live(self.p, aid, "polish")
        # The asset appears with its first export, under the same id, its version filed under the phase.
        glb(self.tmp / aid / "chair_live.glb")
        [a] = sl.scan(self.p)
        self.assertEqual(a.id, aid)
        [e] = sl.observe(self.p, a)
        self.assertEqual((e["variant"], e["phase"], e["step"]), ("live", "texture", "oak scan"))
        self.assertEqual(sl.asset_summary(self.p, a, {})["live"]["phase"], "texture")
        state, removed = sl.end_live(self.p, aid)
        self.assertEqual(state["state"], "done")
        self.assertEqual(removed, [f"{aid}/chair_live.glb"])
        self.assertFalse((self.tmp / aid / "chair_live.glb").exists())
        # A step after the end starts a new build.
        self.assertEqual(len(sl.set_live(self.p, aid, "cleanup")["steps"]), 1)

    def test_cli_resolves_a_folder_not_exported_yet(self) -> None:
        cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                studio.main(["live", "generated-assets/lamp", "--phase", "brief", "--root", str(self.tmp)])
            self.assertEqual(sl.load_live(self.p, "generated-assets/lamp")["phase"], "brief")
            with self.assertRaises(SystemExit):
                studio.main(["live", "../elsewhere", "--phase", "brief", "--root", str(self.tmp)])
        finally:
            os.chdir(cwd)


class Work(Base):
    A, B, C = "out/chair", "out/table", "out/lamp"

    def dots(self) -> dict:
        v = sl.work_view(sl.load_work(self.p))
        return {k: d["state"] for k, d in v["dots"].items()} if v else {}

    def test_a_run_moves_through_its_models(self) -> None:
        sl.start_work(self.p, [self.A, self.B, self.C, self.A], "acting on notes")
        self.assertEqual(self.dots(), {self.A: "active", self.B: "queued", self.C: "queued"})
        sl.work_next(self.p, "seat lowered")
        self.assertEqual(self.dots(), {self.A: "done", self.B: "active", self.C: "queued"})
        # Out of order: the lamp now, the table counts as done.
        sl.work_begin(self.p, self.C)
        self.assertEqual(self.dots(), {self.A: "done", self.B: "done", self.C: "active"})
        run = sl.work_next(self.p)
        self.assertEqual(run["state"], "done")
        v = sl.work_view(run)
        self.assertEqual((v["running"], v["done"], v["total"], v["active"]), (False, 3, 3, None))
        self.assertEqual(run["items"][0]["text"], "seat lowered")

    def test_checked_dots_go_then_the_run(self) -> None:
        sl.start_work(self.p, [self.A, self.B])
        sl.work_next(self.p)
        sl.check_work(self.p, [self.A])   # looked at it while kiln works on the table
        self.assertEqual(self.dots(), {self.B: "active"})
        sl.work_next(self.p)
        self.assertEqual(self.dots(), {self.B: "done"})
        self.assertIsNone(sl.check_work(self.p, [self.B]))
        self.assertIsNone(sl.load_work(self.p))
        # "Clear" checks every done model at once.
        sl.start_work(self.p, [self.A, self.B])
        sl.work_next(self.p)
        sl.work_next(self.p)
        self.assertIsNone(sl.check_work(self.p))
        self.assertIsNone(sl.load_work(self.p))

    def test_end_drops_the_rest_and_a_stale_run_stops_working(self) -> None:
        sl.start_work(self.p, [self.A, self.B, self.C])
        sl.end_work(self.p, "stopped: the user asked")
        self.assertEqual(self.dots(), {self.A: "done"})
        self.assertEqual(sl.work_view(sl.load_work(self.p))["total"], 1)
        with self.assertRaises(ValueError):
            sl.work_next(self.p)
        sl.start_work(self.p, [self.A, self.B])
        sl.work_next(self.p)
        run = sl.load_work(self.p)
        run["updated"] = "2020-01-01T00:00:00+00:00"
        sl.write_json(sl.work_path(self.p), run)
        v = sl.work_view(sl.load_work(self.p))
        self.assertEqual((v["running"], v["stale"], v["active"]), (False, True, None))
        self.assertEqual(self.dots(), {self.A: "done"})

    def test_begin_without_a_run_starts_one(self) -> None:
        sl.work_begin(self.p, self.B)
        self.assertEqual(self.dots(), {self.B: "active"})
        sl.work_begin(self.p, self.A)
        self.assertEqual(self.dots(), {self.B: "done", self.A: "active"})

    def test_cli(self) -> None:
        glb(self.tmp / "out" / "chair" / "chair_final.glb")
        glb(self.tmp / "out" / "table" / "table_final.glb")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            studio.main(["work", "start", "chair", "table", "--label", "acting on notes", "--root", str(self.tmp)])
            studio.main(["work", "next", "--text", "seat lowered", "--root", str(self.tmp)])
            studio.main(["work", "--root", str(self.tmp)])
        self.assertEqual(self.dots(), {"out/chair": "done", "out/table": "active"})
        self.assertIn("acting on notes: running, 1/2 done", out.getvalue())
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            studio.main(["work", "start", "sofa", "--root", str(self.tmp)])
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            studio.main(["work", "done", "--root", str(self.tmp)])


LOG = """# Crate — Production Log

## Config
- Type: prop
- Target: glTF
- Tier: lightweight
- Style: stylized

## Licenses
- Wood texture: CC0 (Poly Haven)
- Lantern model: CC-BY 4.0, credit "someone" on Sketchfab
"""

MANIFEST = """# batch-manifest.yaml — generated by /kiln batch wizard
batch:
  name: corporate-office              # kebab-case identifier
  description: "Modern corporate office, open space # not a comment"

config:
  tier: balanced

assets:
  - name: desk
    brief: "Modern desk: light wood top"
    method: scripted
    materials: [wood, metal]
    status: done
    result:
      faces: 2100
      status: ignored-nested
  - name: chair
    method: ai
    status: pending
  - name: keyboard
    method: marketplace
    status: failed
  - name: cables
    method: geometry-nodes
  - name: mystery
    method: telepathy
"""


class Estimate(Base):
    def usage(self, *entries: dict) -> None:
        d = self.tmp / ".kiln-studio" / "claude"
        d.mkdir(parents=True, exist_ok=True)
        (d / "usage.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))

    def test_a_task_sums_its_resumes_and_this_project_wins_from_three(self) -> None:
        sl.write_json(self.tmp / ".kiln-studio" / "requests.json", {"requests": [
            {"id": "q1", "reference": ".kiln-studio/requests/q1.jpg"}, {"id": "q2", "reference": None}]})
        run = lambda kind, key, s, c, **kw: {"kind": kind, "key": key, "duration_ms": s * 1000, "cost_usd": c, **kw}
        self.usage(run("create", "request:q1", 60, 1.0), run("resume", "request:q1", 120, 2.0),   # a photo: 3 min, $3
                   run("create", "request:q2", 60, 0.5),
                   *[run("chat", "asset:a", 60 * m, 0.1 * m) for m in (1, 2, 3, 4)],
                   run("chat", "asset:a", 240, 0.8, task="output.print"), run("resume", "asset:a", 60, 0.2))
        t = estimate.tasks(self.p)
        self.assertEqual(t["create.photo"], [(180.0, 3.0)])
        self.assertEqual(t["output.print"], [(300.0, 1.0)])
        self.assertEqual(len(t["chat"]), 4)
        chat = estimate.estimate(self.p, "chat")
        self.assertEqual((chat["source"], chat["n"]), ("project", 4))
        self.assertEqual(chat["minutes"], [1.8, 3.2])   # the middle half of 1, 2, 3, 4 min
        # Under three in the project: the bench; none in either: no figure, never a made-up one.
        photo = estimate.estimate(self.p, "create.photo", "api_key")
        self.assertEqual((photo["source"], photo["billed"]), ("bench", True))
        self.assertEqual(photo["minutes"], [16.1, 20.5])
        self.assertEqual(estimate.estimate(self.p, "notes"), {"task": "notes", "source": None, "n": 0, "seen": 0, "needed": 3, "billed": False})
        with self.assertRaises(ValueError):
            estimate.estimate(self.p, "anything")


class Checks(Base):
    def test_image_sizes_from_headers(self) -> None:
        self.assertEqual(checks.image_size(png(2048, 1024)), (2048, 1024, "png"))
        jpeg = b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 16) + b"\0" * 14 \
            + b"\xff\xc0" + struct.pack(">HBHH", 17, 8, 512, 768) + b"\0" * 12
        self.assertEqual(checks.image_size(jpeg), (768, 512, "jpeg"))
        vp8x = b"RIFF" + b"\0" * 4 + b"WEBPVP8X" + b"\0" * 8 + (1023).to_bytes(3, "little") + (511).to_bytes(3, "little")
        self.assertEqual(checks.image_size(vp8x), (1024, 512, "webp"))
        ktx2 = b"\xabKTX 20\xbb\r\n\x1a\n" + b"\0" * 8 + struct.pack("<II", 256, 128)
        self.assertEqual(checks.image_size(ktx2), (256, 128, "ktx2"))
        self.assertIsNone(checks.image_size(b"nothing"))

    def _asset(self, **kw) -> sl.Asset:
        d = self.tmp / "generated-assets" / "crate"
        glb(d / "crate_original.glb", image=png(4096, 4096))
        glb(d / "crate_final.glb", **kw)
        (d / "crate_log.md").write_text(LOG)
        [a] = sl.scan(self.p)
        return a

    def test_shipped_file_against_kiln_rules(self) -> None:
        a = self._asset(tris=4000, image=png(2048, 2048), lift=0.2)
        c = checks.asset_checks(self.p, a)
        self.assertEqual(c["shipped"], "final")
        by = {r["key"]: r for r in c["health"]["final"]}
        # lightweight prop: 300–1.5K, 4,000 is past twice the top
        self.assertEqual(by["tris"]["level"], "warn")
        self.assertIn("lightweight prop", by["tris"]["text"])
        self.assertIn("/kiln optimize crate", by["compression"]["fix"])
        self.assertIn("/kiln optimize crate", by["textures"]["fix"])
        for k in ("tris", "ground", "textures", "compression"):
            self.assertTrue(by[k]["fix"] and by[k]["ask"], k)
            self.assertNotRegex(by[k]["text"] + by[k]["fix"], r"rule \d|OPTIMIZE", k)
        self.assertEqual(by["ground"]["level"], "warn")
        self.assertIn("Floats 0.200 m above the ground", by["ground"]["text"])
        self.assertEqual(by["textures"]["level"], "warn")
        self.assertEqual(by["textures"]["images"][0]["slots"], ["baseColor"])
        self.assertEqual(by["compression"]["level"], "warn")
        self.assertEqual(by["licence"]["level"], "info")
        self.assertEqual([e["kind"] for e in by["licence"]["entries"]], ["free", "attribution required"])
        # The original stage is not shipped: its 4K texture and no Draco are not faults.
        orig = {r["key"]: r for r in c["health"]["original"]}
        self.assertEqual((orig["textures"]["level"], orig["compression"]["level"]), ("info", "info"))

    def test_findings_carry_their_codes(self) -> None:
        a = self._asset(tris=4000, image=png(2048, 2048), lift=0.2)
        for rows in checks.asset_checks(self.p, a)["health"].values():
            for r in rows:
                self.assertTrue(r["msg"] and all(c in checks.MESSAGES for c, _ in r["msg"]), r["key"])
                self.assertEqual(checks.render(r["msg"]), r["text"])
                self.assertEqual(checks.render(r["fix_msg"]), r["fix"])
                self.assertEqual(checks.render(r["ask_msg"]), r["ask"])
        json.dumps(checks.asset_checks(self.p, a))   # the codes and params travel as JSON

    def test_an_optimized_final_passes(self) -> None:
        a = self._asset(tris=1000, image=png(1024, 1024)[:0] + b"RIFF\0\0\0\0WEBPVP8X" + b"\0" * 8
                        + (1023).to_bytes(3, "little") + (1023).to_bytes(3, "little"), mime="image/webp",
                        extensions=["KHR_draco_mesh_compression", "EXT_texture_webp"])
        by = {r["key"]: r for r in checks.asset_checks(self.p, a)["health"]["final"]}
        for k in ("tris", "scale", "ground", "textures", "compression"):
            self.assertEqual(by[k]["level"], "ok", (k, by[k]["text"]))
            self.assertIsNone(by[k]["fix"], k)

    def test_desktop_targets_are_not_told_to_compress(self) -> None:
        a = self._asset(tris=1000, image=png(2048, 2048))
        (self.tmp / "generated-assets" / "crate" / "crate_log.md").write_text(LOG.replace("Target: glTF", "Target: Unity (FBX)"))
        by = {r["key"]: r for r in checks.asset_checks(self.p, a)["health"]["final"]}
        self.assertEqual((by["compression"]["level"], by["compression"]["fix"]), ("info", None))
        self.assertEqual(by["textures"]["level"], "ok")   # 2048 is the cap for PC

    def test_size_against_the_expected_height_and_units(self) -> None:
        glb(self.tmp / "props" / "chair.glb", scale=2.0)
        glb(self.tmp / "props" / "pebble.glb", scale=0.005)
        by_name = {a.name: a for a in sl.scan(self.p)}
        chair = {r["key"]: r for r in checks.health(self.p, by_name["chair"], by_name["chair"].primary)}
        self.assertEqual(chair["scale"]["level"], "info")
        self.assertIn("a chair is usually about 0.85 m", chair["scale"]["text"])
        pebble = {r["key"]: r for r in checks.health(self.p, by_name["pebble"], by_name["pebble"].primary)}
        self.assertEqual(pebble["scale"]["level"], "warn")

    def test_fidelity_runs_follow_the_model(self) -> None:
        a = self._asset()
        rev = self.tmp / "generated-assets" / "crate" / "review" / "front"
        rev.mkdir(parents=True)
        (rev / "overlay.png").write_bytes(png(8, 8))
        final = a.variant("final")
        (rev / "fidelity.json").write_text(json.dumps({
            "iou": 0.861, "gaps": ["band 2/5: width +12%"], "shape": [], "view": "front", "elevation": 12,
            "model": str(final.path), "model_hash": sl.file_hash(final.path), "reference": "/nowhere/ref.png"}))
        (rev / "fidelity_log.jsonl").write_text('{"iou": 0.79}\n{"iou": 0.861}\n')
        [run] = checks.fidelity_runs(self.p, a)
        self.assertEqual((run["measured"], run["current"]), ("final", True))
        self.assertEqual([t["iou"] for t in run["trend"]], [0.79, 0.861])
        self.assertEqual(run["overlay"], "generated-assets/crate/review/front/overlay.png")
        self.assertIsNone(run["reference"])   # outside the project: not served
        glb(final.path, tris=9)
        [a] = sl.scan(self.p)
        [run] = checks.fidelity_runs(self.p, a)
        self.assertEqual((run["measured"], run["current"]), (None, False))

    def test_batch_estimate_from_the_manifest(self) -> None:
        m = checks.parse_manifest(MANIFEST)
        self.assertEqual(m["name"], "corporate-office")
        self.assertEqual([(x["name"], x.get("method"), x.get("status")) for x in m["assets"]],
                         [("desk", "scripted", "done"), ("chair", "ai", "pending"), ("keyboard", "marketplace", "failed"),
                          ("cables", "geometry-nodes", None), ("mystery", "telepathy", None)])
        b = self.tmp / "generated-assets" / "batch-office"
        b.mkdir(parents=True)
        (b / "batch-manifest.yaml").write_text(MANIFEST)
        glb(b / "chair" / "chair_final.glb")
        [a] = sl.scan(self.p)
        est = checks.asset_checks(self.p, a)["batch"]
        # scripted 30K + ai 60K + marketplace 20K + geometry nodes 40K = 150K;
        # high: (30 + 80 + 20 + 40) x 1.5 = 255K
        self.assertEqual(est["range"], [150_000, 255_000])
        self.assertEqual(est["remaining"], {"assets": 3, "range": [120_000, 210_000]})
        self.assertEqual(est["asset"]["range"], (60_000, 120_000))
        self.assertEqual(est["unknown"], ["mystery"])
        self.assertEqual(checks.fmt_range(est["range"]), "~150K–255K tokens")


class Tutorial(unittest.TestCase):
    """The tutorial's models and their stats ship together: fixtures.json was made from these
    files (static/tutorial/make_tutorial.py, then Studio's own stats and checks)."""

    def test_fixtures_match_the_files(self) -> None:
        d = STATIC / "tutorial"
        fx = json.loads((d / "fixtures.json").read_text())
        self.assertEqual(set(fx), {"barrel_before", "barrel_after", "lantern_1_blockout", "lantern_2_details",
                                   "lantern_3_materials", "lantern_4_final"})
        for key, f in fx.items():
            glb_file = d / f"{key}.glb"
            self.assertEqual(glb_file.stat().st_size, f["size"], key)
            self.assertEqual(sl.file_hash(glb_file), f["hash"], key)
            self.assertIn("final", f["checks"]["health"])
        src = (STATIC / "tutorial.js").read_text()
        for key in fx:
            self.assertIn(f"'{key}'", src)   # every model is used


class Settings(Base):
    def test_target_default_for_every_project_and_override(self) -> None:
        self.assertEqual((self.p.settings()["target"], self.p.target_source()), ("web", "default"))
        sl.save_user_defaults(target="print")   # every project on this computer
        self.assertEqual((self.p.settings()["target"], self.p.target_source()), ("print", "default"))
        self.assertTrue((self.tmp / ".home" / "defaults.json").is_file())
        sl.save_config(self.p, {"target": "desktop"})   # this one says otherwise
        self.assertEqual((self.p.settings()["target"], self.p.target_source()), ("desktop", "project"))
        sl.save_config(self.p, {"target": ""})          # back to the default
        self.assertEqual((self.p.settings()["target"], self.p.target_source()), ("print", "default"))
        with self.assertRaises(ValueError):
            sl.save_user_defaults(target="moon")
        sl.save_config(self.p, {"claude_paid": "auto"})
        self.assertEqual(self.p.settings()["claude_paid"], "auto")
        with self.assertRaises(ValueError):
            sl.save_config(self.p, {"claude_paid": "always"})

    def test_defaults_validation_and_unknown_keys_kept(self) -> None:
        self.assertEqual(self.p.settings(), sl.CONFIG_DEFAULTS)
        self.p.ensure()
        (self.p.data / "config.json").write_text(json.dumps({"exclude": ["site/*"], "theirs": 1, "target": "moon"}))
        self.assertEqual(self.p.settings()["exclude"], ["site/*"])
        self.assertEqual(self.p.settings()["target"], "web")   # a bad value reads as the default
        out = sl.save_config(self.p, {"target": "print", "live_view": False})
        self.assertEqual((out["target"], out["live_view"], out["auto_open"]), ("print", False, True))
        on_disk = json.loads((self.p.data / "config.json").read_text())
        self.assertEqual(on_disk["theirs"], 1)   # a key Studio does not know is left alone
        for bad in ({"target": "unity"}, {"live_view": "no"}, {"exclude": "a/*"}, {"colour": "red"}):
            with self.assertRaises(ValueError, msg=bad):
                sl.save_config(self.p, bad)

    def test_cli(self) -> None:
        def run(*a: str) -> str:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                studio.main([*a, "--root", str(self.tmp)])
            return out.getvalue()
        self.assertIn("(default)", run("config"))
        run("config", "target=print", "live_view=off", "exclude=site/*, docs/*")
        st = json.loads(run("config", "--json"))
        self.assertEqual((st["target"], st["live_view"], st["exclude"]), ("print", False, ["site/*", "docs/*"]))
        with self.assertRaises(SystemExit):
            run("config", "target=moon")
        with self.assertRaises(SystemExit):
            run("config", "auto_open=maybe")

    def test_exclude_applies_to_the_scan(self) -> None:
        glb(self.tmp / "site" / "public" / "hero.glb")
        glb(self.tmp / "props" / "chair.glb")
        self.assertEqual(len(sl.scan(self.p)), 2)
        sl.save_config(self.p, {"exclude": ["site/*", "  "]})
        self.assertEqual([a.id for a in sl.scan(self.p)], ["props/chair"])
        self.assertEqual(self.p.settings()["exclude"], ["site/*"])

    def test_the_project_target_sets_the_thresholds(self) -> None:
        d = self.tmp / "generated-assets" / "crate"
        glb(d / "crate_final.glb", tris=40000, image=png(2048, 2048))
        [a] = sl.scan(self.p)
        web = {r["key"]: r for r in checks.health(self.p, a, a.primary)}
        self.assertEqual((web["tris"]["level"], web["textures"]["level"], web["compression"]["level"]), ("warn", "warn", "warn"))
        self.assertIn("assumed", web["textures"]["text"])
        sl.save_config(self.p, {"target": "desktop"})
        desk = {r["key"]: r for r in checks.health(self.p, a, a.primary)}
        self.assertEqual((desk["textures"]["level"], desk["compression"]["level"]), ("ok", "info"))
        self.assertIn("the project's target", desk["textures"]["text"])
        sl.save_config(self.p, {"target": "print"})
        pr = {r["key"]: r for r in checks.health(self.p, a, a.primary)}
        self.assertEqual((pr["tris"]["level"], pr["textures"]["level"], pr["compression"]["level"]), ("ok", "info", "info"))
        self.assertEqual(checks.asset_checks(self.p, a)["config"]["target"], "3D print")
        # The production log's own target wins over the project's.
        (d / "crate_log.md").write_text(LOG)
        [a] = sl.scan(self.p)
        logged = {r["key"]: r for r in checks.health(self.p, a, a.primary)}
        self.assertEqual(logged["compression"]["level"], "warn")


STATIC = Path(__file__).resolve().parent / "static"


def ui_strings() -> set[str]:
    """Every string the page passes through t(), tp() or N_(), every palette label, and
    every [data-i18n] text and [data-i18n-attr] attribute of index.html: the English
    keys static/i18n/<lang>.json must translate."""
    from html.parser import HTMLParser
    q = r"""(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")"""

    def un(a, b):
        return (a if a is not None else b).replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
    keys: set[str] = set()
    for f in ("app.js", "i18n.js", "tutorial.js"):
        src = (STATIC / f).read_text()
        keys |= {un(m.group(1), m.group(2)) for m in re.finditer(r"\b(?:t|N_)\(\s*" + q, src)}
        for m in re.finditer(r"\btp\([^'\"]*?,\s*" + q + r"\s*,\s*" + q, src):
            keys |= {un(m.group(1), m.group(2)), un(m.group(3), m.group(4))}
        for m in re.finditer(r"\badd\(\s*'([^']+)'\s*,\s*" + q, src):
            keys |= {m.group(1), un(m.group(2), m.group(3))}

    class H(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.stack: list = []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            for at in (a.get("data-i18n-attr") or "").split(","):
                if at and a.get(at):
                    keys.add(a[at])
            self.stack.append(("data-i18n" in a, []))

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            self.stack.pop()

        def handle_endtag(self, tag):
            if self.stack:
                on, buf = self.stack.pop()
                if on and "".join(buf).strip():
                    keys.add("".join(buf))
                if self.stack:
                    self.stack[-1][1].extend(buf)

        def handle_data(self, d):
            if self.stack:
                self.stack[-1][1].append(d)
    H().feed((STATIC / "index.html").read_text())
    return keys


def holes(s) -> list[str]:
    return sorted(re.findall(r"\{(\w+)", " ".join(s) if isinstance(s, list) else s))


class Language(unittest.TestCase):
    """French is complete: a string added in English without its French fails here."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fr = json.loads((STATIC / "i18n" / "fr.json").read_text())

    def test_every_page_string_has_its_french(self) -> None:
        keys = ui_strings()
        self.assertGreater(len(keys), 400)   # the extractor still finds the page's strings
        self.assertEqual(sorted(keys - set(self.fr["ui"])), [])
        for en, fr in self.fr["ui"].items():
            self.assertEqual(holes(en), holes(fr), en)

    def test_every_check_code_has_its_french(self) -> None:
        self.assertEqual(sorted(set(checks.MESSAGES) ^ set(self.fr["checks"])), [])
        for code, en in checks.MESSAGES.items():
            fr = self.fr["checks"][code]
            self.assertEqual(isinstance(en, list), isinstance(fr, list), code)
            self.assertEqual(holes(en), holes(fr), code)

    def test_the_words_a_finding_carries_are_translated(self) -> None:
        words = {*checks.WORDS, *checks.LABELS, *checks.LICENCE_KIND.values(), *checks.CATEGORY_LABEL.values(),
                 *checks.TIERS, *checks.EXPECTED_HEIGHT}
        self.assertEqual(sorted(words - set(self.fr["ui"])), [])
        src = Path(checks.__file__).read_text()
        self.assertEqual(sorted(set(re.findall(r'_check\("\w+", "([^"]+)"', src)) - set(checks.LABELS)), [])


class Api(Base):
    def setUp(self) -> None:
        super().setUp()
        self.f = glb(self.tmp / "generated-assets" / "crate" / "crate_final.glb")
        self.srv, self.studio = server.make_server(self.p, 0, interval=0.1)
        self.port = self.srv.server_address[1]
        self.srv.RequestHandlerClass.log_message = lambda *a: None
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def req(self, method: str, path: str, body=None, headers=None) -> tuple[int, dict | bytes]:
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": f"127.0.0.1:{self.port}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, raw

    def test_a_file_downloads_under_its_name_and_only_the_model_s_files_reveal(self) -> None:
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/files/generated-assets/crate/crate_final.glb?download=1", headers={"Host": f"127.0.0.1:{self.port}"})
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertIn("attachment", r.getheader("Content-Disposition"))
        self.assertIn("crate_final.glb", r.getheader("Content-Disposition"))
        self.assertEqual(r.read(), self.f.read_bytes())
        c.close()
        code, _ = self.req("POST", "/api/asset/generated-assets%2Fcrate/reveal", {"file": "../../etc/passwd"})
        self.assertEqual(code, 400)
        stl(self.tmp / "generated-assets" / "crate" / "print" / "crate_print_lid.stl")
        stl(self.tmp / "generated-assets" / "crate" / "print" / "crate_print_box.stl")
        (self.tmp / "generated-assets" / "crate" / "print" / "crate_lid_parts.blend").write_bytes(b"BLENDER")   # kiln's working file
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/files/generated-assets/crate/print?zip=1", headers={"Host": f"127.0.0.1:{self.port}"})
        r = c.getresponse()
        self.assertEqual((r.status, r.getheader("Content-Type")), (200, "application/zip"))
        self.assertIn("crate_print.zip", r.getheader("Content-Disposition"))
        self.assertEqual(sorted(zipfile.ZipFile(io.BytesIO(r.read())).namelist()), ["crate_print_box.stl", "crate_print_lid.stl"])
        c.close()
        code, _ = self.req("GET", "/files/generated-assets?zip=1")   # only an output folder zips
        self.assertNotEqual(code, 200)

    def test_the_package_holds_every_output_and_a_sheet(self) -> None:
        d = self.tmp / "generated-assets" / "crate"
        glb(d / "crate_original.glb")
        glb(d / "web" / "crate_final.glb")
        (d / "game").mkdir()
        (d / "game" / "crate_game.fbx").write_bytes(b"Kaydara FBX Binary")
        stl(d / "print" / "crate_print_lid.stl")
        threemf(d / "print" / "crate_print.3mf")
        (d / "print" / "crate_lid_parts.blend").write_bytes(b"BLENDER")
        (d / "crate_log.md").write_text("# crate\n\n## Licenses\n- Wood texture: Poly Haven, CC0\n")
        old = time.time() - 3600
        os.utime(d / "game" / "crate_game.fbx", (old, old))   # made before the model last changed
        self.studio.refresh()
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/api/asset/generated-assets%2Fcrate/package?lang=fr", headers={"Host": f"127.0.0.1:{self.port}"})
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertIn("crate.zip", r.getheader("Content-Disposition"))
        z = zipfile.ZipFile(io.BytesIO(r.read()))
        c.close()
        names = sorted(z.namelist())
        self.assertIn("crate/web/crate_final.glb", names)
        self.assertIn("crate/game/crate_game.fbx", names)
        self.assertIn("crate/print/crate_print.3mf", names)
        self.assertIn("crate/print/crate_print_lid.stl", names)
        self.assertNotIn("crate/print/crate_lid_parts.blend", names)   # a working file stays
        self.assertFalse(any("original" in n for n in names))          # the source stays
        sheet = z.read("crate/LISEZ-MOI.md").decode()
        self.assertIn("Unity, Unreal", sheet)
        self.assertIn("**À refaire :** Jeu", sheet)
        self.assertIn("Poly Haven, CC0 — libre d'usage", sheet)
        # The dialog lists each output and its files; a pick without the sheet holds only those.
        code, d = self.req("GET", "/api/asset/generated-assets%2Fcrate/outputs?lang=fr")
        self.assertEqual(code, 200)
        self.assertEqual([o["out"] for o in d["outputs"]], ["web", "game", "print"])
        self.assertTrue(d["outputs"][1]["stale"])
        self.assertEqual([f["path"] for f in d["outputs"][2]["files"]], ["print/crate_print.3mf", "print/crate_print_lid.stl"])
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/api/asset/generated-assets%2Fcrate/package?lang=fr&outs=print&sheet=0", headers={"Host": f"127.0.0.1:{self.port}"})
        z = zipfile.ZipFile(io.BytesIO(c.getresponse().read()))
        c.close()
        self.assertEqual(sorted(z.namelist()), ["crate/print/crate_print.3mf", "crate/print/crate_print_lid.stl"])

    def test_the_estimate_route(self) -> None:
        code, e = self.req("GET", "/api/claude/estimate?task=create.text")
        self.assertEqual((code, e["source"], e["n"]), (200, "bench", 7))
        code, _ = self.req("GET", "/api/claude/estimate?task=rm%20-rf")
        self.assertEqual(code, 400)

    def test_assets_and_detail(self) -> None:
        code, data = self.req("GET", "/api/assets")
        self.assertEqual(code, 200)
        self.assertEqual([a["id"] for a in data["assets"]], ["generated-assets/crate"])
        code, d = self.req("GET", "/api/asset/generated-assets%2Fcrate")
        self.assertEqual(code, 200)
        self.assertEqual(d["variants"][0]["stats"]["tris"], 1)

    def test_settings_api(self) -> None:
        code, data = self.req("GET", "/api/config")
        self.assertEqual((code, data["settings"]["target"], data["file"]), (200, "web", ".kiln-studio/config.json"))
        code, data = self.req("PUT", "/api/config", {"target": "desktop", "auto_open": False})
        self.assertEqual((code, data["settings"]["target"], data["settings"]["auto_open"]), (200, "desktop", False))
        code, data = self.req("PUT", "/api/config", {"target": "mars"})
        self.assertEqual(code, 400)
        code, _ = self.req("PUT", "/api/config", {"target": "web"}, headers={"Origin": "http://evil.example"})
        self.assertEqual(code, 403)
        self.assertEqual(self.p.settings()["target"], "desktop")

    def test_setup_status_says_unknown_rather_than_guess(self) -> None:
        code, st = self.req("GET", "/api/status")
        self.assertEqual(code, 200)
        rows = {r["key"]: r for r in st["rows"]}
        self.assertEqual(set(rows), {"blender", "claude", "mcp", "optimizers", "skintokens", "unimate"})
        for r in rows.values():   # what it is for, what it weighs, under which licence
            self.assertIn(r["need"], ("required", "recommended", "optional"))
            self.assertIn("licence", r)
        self.assertEqual(rows["unimate"]["licence"], "CC BY-NC 4.0 (non-commercial)")
        self.assertIn(rows["optimizers"]["state"], ("ok", "partial", "missing"))
        self.assertIn(rows["blender"]["state"], ("ok", "missing"))
        self.assertEqual(rows["mcp"]["state"], "unknown")   # Studio cannot see Claude's connections
        self.assertIn("listening", rows["mcp"]["data"])
        if not (Path(studio.__file__).resolve().parent.parent / "tools" / "autorig.py").exists():
            self.assertEqual((rows["skintokens"]["state"], rows["skintokens"]["data"]["reason"]), ("unknown", "no-tool"))

    def test_the_example_lands_in_the_project(self) -> None:
        code, r = self.req("POST", "/api/example", {})
        self.assertEqual((code, r["id"]), (200, "kiln-example/barrel"))
        self.assertTrue((self.tmp / "kiln-example" / "barrel" / "barrel_final.glb").is_file())
        code, data = self.req("GET", "/api/assets")
        self.assertIn("kiln-example/barrel", [a["id"] for a in data["assets"]])
        self.assertEqual(self.req("POST", "/api/example", {})[1]["id"], "kiln-example/barrel")   # once only
        [a] = [x for x in sl.scan(self.p) if x.id == "kiln-example/barrel"]
        by = {c["key"]: c for c in checks.health(self.p, a, a.primary)}
        self.assertEqual((by["tris"]["value"], by["tris"]["level"], by["licence"]["level"]), (2202, "ok", "ok"))

    def raw(self, path: str, data: bytes, headers=None) -> tuple[int, dict]:
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/octet-stream"}
        h.update(headers or {})
        c.request("POST", path, body=data, headers=h)
        r = c.getresponse()
        out = (r.status, json.loads(r.read() or b"{}"))
        c.close()
        return out

    def test_import_saves_into_imports_never_over_a_file(self) -> None:
        model = self.f.read_bytes()
        code, r = self.raw("/api/import?name=chair.glb", model)
        self.assertEqual((code, r["path"]), (200, "imports/chair.glb"))
        code, r = self.raw("/api/import?name=chair.glb", model)
        self.assertEqual(r["path"], "imports/chair-2.glb")
        ids = [a["id"] for a in self.req("GET", "/api/assets")[1]["assets"]]
        self.assertIn("imports/chair", ids)
        self.assertIn("imports/chair-2", ids)
        # a glTF and its buffer, together in a folder of their own
        self.assertEqual(self.raw("/api/import?name=scene.gltf&folder=scene", b"{}")[1]["path"], "imports/scene/scene.gltf")
        self.assertEqual(self.raw("/api/import?name=scene.bin&folder=scene", b"\0")[1]["path"], "imports/scene/scene.bin")
        self.assertEqual(self.raw("/api/import?name=tool.exe", b"MZ")[0], 400)
        self.assertEqual(self.raw("/api/import?name=scene.bin", b"\0")[0], 400)   # a buffer alone is not a model
        self.assertEqual(self.raw("/api/import?name=x.glb&folder=..", model)[0], 400)
        self.assertEqual(self.raw("/api/import?name=x.glb", model, {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.raw("/api/import?name=x.glb", model, {"Origin": "http://evil.example"})[0], 403)
        self.assertFalse((self.tmp / "x.glb").exists() or (self.tmp / "imports" / "x.glb").exists())

    def test_a_request_for_a_new_model(self) -> None:
        photo = "data:image/jpeg;base64," + base64.b64encode(JPEG).decode()
        code, r = self.req("POST", "/api/requests", {"brief": "a low-poly wooden chair", "type": "prop",
                                                      "target": "web", "style": "low-poly", "photo": photo})
        self.assertEqual((code, r["status"]), (200, "open"))
        self.assertTrue(r["command"].startswith("/kiln a low-poly wooden chair, type prop, for the web (glTF), low-poly, reference photo .kiln-studio/requests/"))
        self.assertTrue(r["command"].endswith(f"(Studio request {r['id']})"))
        self.assertTrue((self.tmp / r["reference"]).is_file())
        self.assertEqual([x["id"] for x in self.req("GET", "/api/requests")[1]["requests"]], [r["id"]])
        self.assertEqual(self.req("POST", "/api/requests", {"brief": "  "})[0], 400)
        self.assertEqual(self.req("POST", "/api/requests", {"brief": "x", "type": "spaceship"})[0], 400)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            studio.main(["requests", "--root", str(self.tmp)])
            studio.main(["request", r["id"], "--status", "done", "--asset", "crate", "--root", str(self.tmp)])
            studio.main(["requests", "--root", str(self.tmp)])
        lines = out.getvalue().splitlines()
        self.assertIn("a low-poly wooden chair", lines[0])
        self.assertEqual(lines[-2:], [f"{r['id']}: done, generated-assets/crate", "No open request."])

    def test_fonts_are_local_and_jsdelivr_is_the_only_outside_host(self) -> None:
        hosts = set()
        for f in ("index.html", "style.css", "app.js", "viewer.js", "i18n.js"):
            hosts |= set(re.findall(r"https?://([\w.-]+)", (STATIC / f).read_text()))
        self.assertEqual(hosts - {"cdn.jsdelivr.net", "127.0.0.1", "www.w3.org", "blender.org"}, set())
        for font in ("sora-latin", "sora-latin-ext", "jetbrains-mono-latin", "jetbrains-mono-latin-ext"):
            self.assertIn(f"url(fonts/{font}.woff2)", (STATIC / "style.css").read_text())
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            c.request("GET", f"/static/fonts/{font}.woff2", headers={"Host": f"127.0.0.1:{self.port}"})
            r = c.getresponse()
            self.assertEqual((r.status, r.getheader("Content-Type"), r.read(4)), (200, "font/woff2", b"wOF2"))
            c.close()
        for lic in ("OFL-Sora.txt", "OFL-JetBrainsMono.txt"):
            self.assertIn("SIL Open Font License", (STATIC / "fonts" / lic).read_text())

    def test_files_stay_inside_the_project(self) -> None:
        code, body = self.req("GET", "/files/generated-assets/crate/crate_final.glb")
        self.assertEqual(code, 200)
        self.assertTrue(body.startswith(b"glTF"))
        code, _ = self.req("GET", "/files/../../etc/passwd")
        self.assertIn(code, (400, 404))
        code, _ = self.req("GET", "/files/%2E%2E/%2E%2E/etc/passwd")
        self.assertIn(code, (400, 404))

    def test_a_stale_version_request_is_refused(self) -> None:
        h = sl.file_hash(self.f)
        code, _ = self.req("GET", f"/files/generated-assets/crate/crate_final.glb?h={h}")
        self.assertEqual(code, 200)
        code, _ = self.req("GET", "/files/generated-assets/crate/crate_final.glb?h=0123456789ab")
        self.assertEqual(code, 409)

    def test_rebinding_and_cross_origin_are_refused(self) -> None:
        code, _ = self.req("GET", "/api/assets", headers={"Host": f"evil.example:{self.port}"})
        self.assertEqual(code, 403)
        code, _ = self.req("POST", "/api/asset/generated-assets%2Fcrate/notes", {"text": "x"},
                           headers={"Origin": "http://evil.example"})
        self.assertEqual(code, 403)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("POST", "/api/asset/generated-assets%2Fcrate/notes", body="text=x",
                  headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "text/plain"})
        self.assertEqual(c.getresponse().status, 400)   # no form posts: JSON only
        c.close()

    def test_note_flow(self) -> None:
        shot = "data:image/jpeg;base64," + base64.b64encode(JPEG).decode()
        code, n = self.req("POST", "/api/asset/generated-assets%2Fcrate/notes",
                           {"text": "too clean", "anchor": {"point": [0, 0, 0]}, "camera": {"position": [1, 1, 1], "target": [0, 0, 0]}, "shot": shot})
        self.assertEqual(code, 200, n)
        code, r = self.req("POST", f"/api/asset/generated-assets%2Fcrate/notes/{n['id']}/thread",
                           {"text": "", "status": "wontfix"})
        self.assertEqual(code, 200, r)
        code, d = self.req("GET", "/api/asset/generated-assets%2Fcrate")
        self.assertEqual(d["notes"][0]["status"], "wontfix")
        self.assertIsNotNone(d["baseline"])
        code, _ = self.req("PUT", "/api/asset/generated-assets%2Fcrate/meta", {"category": "props", "tags": ["wood"]})
        self.assertEqual(code, 200)
        code, data = self.req("GET", "/api/assets")
        self.assertEqual((data["assets"][0]["category"], data["assets"][0]["tags"]), ("props", ["wood"]))
        webp = "data:image/webp;base64," + base64.b64encode(WEBP).decode()
        code, n2 = self.req("POST", "/api/asset/generated-assets%2Fcrate/notes",
                            {"text": "dent", "anchor": {"point": [0, 0.5, 0]}, "shot": webp, "detail": webp,
                             "view": {"crop": [0.1, 0.1, 0.9, 0.9]}})
        self.assertEqual(code, 200, n2)
        self.assertTrue(n2["detail"].endswith("_detail.webp"))
        self.assertEqual(n2["view"], {"crop": [0.1, 0.1, 0.9, 0.9]})
        code, _ = self.req("POST", "/api/asset/generated-assets%2Fcrate/notes", {"text": "x", "detail": "data:image/webp;base64,AAAA"})
        self.assertEqual(code, 400)
        code, _ = self.req("POST", "/api/asset/generated-assets%2Fcrate/notes", {"text": "  "})
        self.assertEqual(code, 400)
        code, _ = self.req("POST", "/api/asset/generated-assets%2Fcrate/notes", {"text": "x", "shot": "data:image/jpeg;base64,AAAA"})
        self.assertEqual(code, 400)

    def test_live_event_on_reexport(self) -> None:
        q = self.studio.subscribe()
        time.sleep(0.05)
        glb(self.f, tris=7)
        os.utime(self.f, (time.time() + 5, time.time() + 5))
        deadline = time.time() + 5
        seen = []
        while time.time() < deadline:
            try:
                seen.append(q.get(timeout=0.5))
            except Exception:
                pass
            if any(e["type"] == "model" for e in seen):
                break
        ev = next(e for e in seen if e["type"] == "model")
        self.assertEqual(ev["id"], "generated-assets/crate")
        self.assertEqual(ev["variants"]["final"], sl.file_hash(self.f))
        hist = sl.load_history(self.p, "generated-assets/crate")
        self.assertEqual(hist[-1]["tris"], 7)

    def test_live_event_on_a_build_step(self) -> None:
        q = self.studio.subscribe()
        sl.set_live(self.p, "generated-assets/crate", "cleanup", "welded")
        deadline = time.time() + 5
        ev = None
        while time.time() < deadline and not ev:
            try:
                e = q.get(timeout=0.5)
                ev = e if e["type"] == "live" else None
            except Exception:
                pass
        self.assertIsNotNone(ev)
        self.assertEqual((ev["id"], ev["live"]["phase"]), ("generated-assets/crate", "cleanup"))
        code, d = self.req("GET", "/api/asset/generated-assets%2Fcrate")
        self.assertEqual(d["live"]["steps"][-1]["text"], "welded")
        self.assertEqual(d["checks"]["shipped"], "final")
        self.assertIn("final", d["checks"]["health"])

    def test_work_events_and_check(self) -> None:
        q = self.studio.subscribe()
        sl.start_work(self.p, ["generated-assets/crate"], "optimize")
        deadline = time.time() + 5
        ev = None
        while time.time() < deadline and not ev:
            try:
                e = q.get(timeout=0.5)
                ev = e if e["type"] == "work" else None
            except Exception:
                pass
        self.assertIsNotNone(ev)
        self.assertEqual(ev["work"]["active"], "generated-assets/crate")
        sl.work_next(self.p)
        code, data = self.req("GET", "/api/assets")
        self.assertEqual(data["work"]["dots"]["generated-assets/crate"]["state"], "done")
        code, r = self.req("POST", "/api/work/check", {"assets": ["generated-assets/crate"]})
        self.assertEqual((code, r["work"]), (200, None))
        code, data = self.req("GET", "/api/assets")
        self.assertIsNone(data["work"])
        code, _ = self.req("POST", "/api/work/check", {}, headers={"Origin": "http://evil.example"})
        self.assertEqual(code, 403)

    def test_batch_estimates_in_the_listing(self) -> None:
        b = self.tmp / "generated-assets" / "batch-office"
        b.mkdir(parents=True)
        (b / "batch-manifest.yaml").write_text(MANIFEST)
        glb(b / "desk" / "desk_final.glb")
        self.studio.refresh()
        code, data = self.req("GET", "/api/assets")
        self.assertEqual(data["batches"]["generated-assets/batch-office"]["range"], [150_000, 255_000])


class Mcp(Base):
    """The kiln-studio MCP server over stdio, against a running Studio and a seeded note."""

    def setUp(self) -> None:
        super().setUp()
        glb(self.tmp / "generated-assets" / "crate" / "crate_final.glb")
        [self.a] = sl.scan(self.p)
        self.note = sl.add_note(self.p, self.a, "the lid is too thin",
                                anchor={"point": [0, 1, 0], "point_blender": [0, 0, 1], "object": "SM_Box", "region": "top"},
                                camera={"position": [1, 1, 1], "target": [0, 0, 0], "position_blender": [1, -1, 1], "target_blender": [0, 0, 0]},
                                shot=WEBP)
        self.srv, self.studio = server.make_server(self.p, 0, interval=0.1)
        self.srv.RequestHandlerClass.log_message = lambda *a: None
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        port = self.srv.server_address[1]
        sl.write_json(self.p.data / "server.json", {"port": port, "pid": os.getpid()})
        self.port = port
        # What the page reports when the user has the crate open, note 1 picked.
        self.report(shading="clay")
        env = {**os.environ, "KILN_STUDIO_ROOT": str(self.tmp)}
        self.proc = subprocess.Popen([sys.executable, str(Path(server.__file__).with_name("mcp_server.py"))],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env, cwd="/")
        self.n = 0

    def report(self, **change) -> None:
        body = {"asset": self.a.id, "variant": "final", "shading": "clay",
                "camera": {"position_blender": [2, -2, 1.5], "target_blender": [0, 0, 0.5], "fov": 35},
                "note": {"id": self.note["id"], "number": 1}, **change}
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("POST", "/api/selection", body=json.dumps(body),
                  headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(c.getresponse().status, 200)
        c.close()

    def tearDown(self) -> None:
        self.proc.stdin.close()
        self.proc.wait(timeout=5)
        self.proc.stdout.close()
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def rpc(self, method: str, params: dict | None = None, notify: bool = False):
        msg = {"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})}
        if not notify:
            self.n += 1
            msg["id"] = self.n
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        if notify:
            return None
        out = json.loads(self.proc.stdout.readline())
        self.assertEqual(out["id"], self.n)
        return out

    def tool(self, name: str, **args) -> tuple[bool, dict | str]:
        r = self.rpc("tools/call", {"name": name, "arguments": args})["result"]
        text = r["content"][0]["text"]
        return r["isError"], (text if r["isError"] else json.loads(text))

    def test_the_tools(self) -> None:
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test"}})
        self.assertEqual((init["result"]["serverInfo"]["name"], init["result"]["protocolVersion"]), ("kiln-studio", "2025-06-18"))
        self.rpc("notifications/initialized", notify=True)
        names = [t["name"] for t in self.rpc("tools/list")["result"]["tools"]]
        self.assertEqual(names, ["get_selection", "get_notes", "reply_to_note", "set_camera", "get_view_image", "list_models",
                                 "add_note", "open_model", "set_view", "compare", "play_clip", "present"])

        err, sel = self.tool("get_selection")   # no page holds the event stream: closed
        self.assertFalse(err, sel)
        self.assertEqual((sel["page_open"], sel["selection"]), (False, None))
        self.assertIn("closed", sel["note"])
        page = self.studio.subscribe()          # the page is open
        err, sel = self.tool("get_selection")
        self.assertFalse(err, sel)
        self.assertTrue(sel["page_open"] and sel["current"])
        self.assertLess(sel["confirmed_seconds_ago"], 5)
        self.assertEqual((sel["asset"], sel["stage"], sel["shading"]), ("generated-assets/crate", "final", "clay"))
        self.assertEqual(sel["camera_blender"]["position"], [2, -2, 1.5])
        self.assertEqual((sel["highlighted_note"]["number"], sel["highlighted_note"]["text"]), (1, "the lid is too thin"))

        err, notes = self.tool("get_notes")   # no asset: the one open in Studio
        self.assertFalse(err, notes)
        [n] = notes["notes"]
        self.assertEqual((n["number"], n["status"], n["pin"]["point_blender"], n["pin"]["region"]), (1, "open", [0, 0, 1], "top"))
        self.assertTrue(Path(n["pictures"]["screenshot"]).is_file())

        err, r = self.tool("reply_to_note", asset="crate", note="1", text="Lid thickened to 2 cm.", status="addressed")
        self.assertFalse(err, r)
        stored = sl.load_notes(self.p, self.a.id)[0]
        self.assertEqual((stored["status"], stored["thread"][-1]["by"], stored["thread"][-1]["text"]),
                         ("addressed", "claude", "Lid thickened to 2 cm."))
        err, msg = self.tool("reply_to_note", asset="crate", note="1", text="done", status="resolved")
        self.assertTrue(err)   # only the user closes a note
        self.assertEqual(sl.load_notes(self.p, self.a.id)[0]["status"], "addressed")
        self.assertTrue(self.tool("reply_to_note", asset="crate", note="7", text="x")[0])

        # The heartbeat: the same view again confirms it, without resetting how long it has been kept.
        time.sleep(0.3)
        self.report(shading="clay")
        err, again = self.tool("get_selection")
        self.assertLess(again["confirmed_seconds_ago"], again["unchanged_for_seconds"])
        self.report(shading="lit")   # a change
        err, changed = self.tool("get_selection")
        self.assertEqual(changed["shading"], "lit")
        self.assertLess(changed["unchanged_for_seconds"], 0.3)
        self.studio.unsubscribe(page)
        self.assertTrue(self.tool("set_camera", view="front")[0])   # no page open: it says so
        q = self.studio.subscribe()   # a page now listens
        err, cam = self.tool("set_camera", position_blender=[0, -3, 1], target_blender=[0, 0, 0.5])
        self.assertFalse(err, cam)
        ev = q.get(timeout=2)
        self.assertEqual((ev["type"], ev["position_blender"], ev["target_blender"]), ("camera", [0, -3, 1], [0, 0, 0.5]))
        self.assertFalse(self.tool("set_camera", note="1")[0])
        self.assertEqual(q.get(timeout=2)["note"], self.note["id"])
        self.assertTrue(self.tool("set_camera", view="sideways")[0])

        # Driving the page: each tool sends one control event, checked before it goes.
        err, r = self.tool("open_model", asset="crate", stage="final")
        self.assertFalse(err, r)
        self.assertEqual({k: v for k, v in q.get(timeout=2).items()}, {"type": "control", "action": "open", "asset": self.a.id, "stage": "final"})
        self.assertTrue(self.tool("open_model", asset="crate", stage="nope")[0])   # no such stage: refused here
        self.assertFalse(self.tool("set_view", shading="clay", wire=True, view="front")[0])
        ev = q.get(timeout=2)
        self.assertEqual((ev["action"], ev["shading"], ev["wire"], ev["view"]), ("view", "clay", True, "front"))
        self.assertTrue(self.tool("set_view")[0])                      # nothing to change
        self.assertTrue(self.tool("set_view", shading="chrome")[0])
        self.assertFalse(self.tool("compare", mode="side", target="baseline")[0])
        self.assertEqual((q.get(timeout=2)["mode"]), "side")
        self.assertFalse(self.tool("play_clip", clip="walk_loop", speed=0.5)[0])
        ev = q.get(timeout=2)
        self.assertEqual((ev["action"], ev["clip"], ev["speed"]), ("play", "walk_loop", 0.5))
        self.assertTrue(self.tool("play_clip", speed=3)[0])
        self.assertFalse(self.tool("present")[0])
        self.assertEqual(q.get(timeout=2), {"type": "control", "action": "present", "on": True})
        self.assertFalse(self.tool("present", on=False)[0])
        self.assertEqual(q.get(timeout=2)["on"], False)

        # The view image: the page answers the capture event with its picture.
        def answer() -> None:
            ev = q.get(timeout=5)
            self.assertEqual((ev["type"], ev["full"]), ("capture", True))
            png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            c.request("POST", f"/api/view-image/{ev['id']}", body=json.dumps({"image": "data:image/png;base64," + png}),
                      headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.port}"})
            c.getresponse().read()
            c.close()
        t = threading.Thread(target=answer)
        t.start()
        err, img = self.tool("get_view_image")
        t.join()
        self.assertFalse(err, img)
        self.assertTrue(Path(img["path"]).is_file() and img["path"].endswith(".png"))
        self.assertEqual(img["asset"], "generated-assets/crate")

        err, models = self.tool("list_models")
        self.assertFalse(err, models)
        [m] = models["models"]
        self.assertEqual((m["asset"], m["notes"]["open"] + m["notes"].get("addressed", 0) >= 1), ("generated-assets/crate", True))

        err, nn = self.tool("add_note", asset="crate", text="The handles look thin from the side.")
        self.assertFalse(err, nn)
        stored = sl.load_notes(self.p, self.a.id)[-1]
        self.assertEqual((stored["by"], stored["kind"], stored["status"], nn["number"]), ("claude", "general", "open", 2))
        self.studio.unsubscribe(q)
        self.assertTrue(self.tool("present")[0])   # no page open: it says so

    def test_plugin_declares_it(self) -> None:
        cfg = json.loads((Path(server.__file__).resolve().parent.parent / ".mcp.json").read_text())
        spec = cfg["mcpServers"]["kiln-studio"]
        self.assertEqual(spec["args"], ["${CLAUDE_PLUGIN_ROOT}/studio/mcp_server.py"])
        self.assertEqual(spec["env"], {"CLAUDE_PROJECT_DIR": "${CLAUDE_PROJECT_DIR}"})
        # The skill may call every tool by the names Claude Code gives a plugin's MCP
        # tools: mcp__plugin_<plugin>_<server>__<tool>.
        plugin = json.loads((Path(server.__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json").read_text())["name"]
        skill = (Path(server.__file__).resolve().parent.parent / "SKILL.md").read_text().split("\n---", 1)[0]
        allowed = re.search(r"^allowed-tools: (.+)$", skill, re.M).group(1).split(", ")
        for t in [x["name"] for x in self.rpc("tools/list")["result"]["tools"]]:
            self.assertIn(f"mcp__plugin_{plugin}_kiln-studio__{t}", allowed)
        self.rpc("initialize", {"protocolVersion": "2024-11-05"})
        self.assertEqual(self.rpc("ping")["result"], {})
        self.assertEqual(self.rpc("nope")["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main(verbosity=1)
