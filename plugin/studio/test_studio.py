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
import shutil
import struct
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checks  # noqa: E402
import server  # noqa: E402
import studio  # noqa: E402
import studiolib as sl  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 16


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


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="kiln-studio-test-"))
        self.p = sl.Project(self.tmp)

    def tearDown(self) -> None:
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
        self.assertEqual(by["ground"]["level"], "warn")
        self.assertIn("floats 0.200 m", by["ground"]["text"])
        self.assertEqual(by["textures"]["level"], "warn")
        self.assertEqual(by["textures"]["images"][0]["slots"], ["baseColor"])
        self.assertEqual(by["compression"]["level"], "warn")
        self.assertEqual(by["licence"]["level"], "info")
        self.assertEqual([e["kind"] for e in by["licence"]["entries"]], ["free", "attribution required"])
        # The original stage is not shipped: its 4K texture and no Draco are not faults.
        orig = {r["key"]: r for r in c["health"]["original"]}
        self.assertEqual((orig["textures"]["level"], orig["compression"]["level"]), ("info", "info"))

    def test_an_optimized_final_passes(self) -> None:
        a = self._asset(tris=1000, image=png(1024, 1024)[:0] + b"RIFF\0\0\0\0WEBPVP8X" + b"\0" * 8
                        + (1023).to_bytes(3, "little") + (1023).to_bytes(3, "little"), mime="image/webp",
                        extensions=["KHR_draco_mesh_compression", "EXT_texture_webp"])
        by = {r["key"]: r for r in checks.asset_checks(self.p, a)["health"]["final"]}
        for k in ("tris", "scale", "ground", "textures", "compression"):
            self.assertEqual(by[k]["level"], "ok", (k, by[k]["text"]))

    def test_size_against_the_expected_height_and_units(self) -> None:
        glb(self.tmp / "props" / "chair.glb", scale=2.0)
        glb(self.tmp / "props" / "pebble.glb", scale=0.005)
        by_name = {a.name: a for a in sl.scan(self.p)}
        chair = {r["key"]: r for r in checks.health(self.p, by_name["chair"], by_name["chair"].primary)}
        self.assertEqual(chair["scale"]["level"], "info")
        self.assertIn("a chair is usually ~0.85 m", chair["scale"]["text"])
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

    def test_assets_and_detail(self) -> None:
        code, data = self.req("GET", "/api/assets")
        self.assertEqual(code, 200)
        self.assertEqual([a["id"] for a in data["assets"]], ["generated-assets/crate"])
        code, d = self.req("GET", "/api/asset/generated-assets%2Fcrate")
        self.assertEqual(code, 200)
        self.assertEqual(d["variants"][0]["stats"]["tris"], 1)

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


if __name__ == "__main__":
    unittest.main(verbosity=1)
