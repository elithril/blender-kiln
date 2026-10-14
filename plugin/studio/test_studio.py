#!/usr/bin/env python3
"""Kiln Studio's tests: scan, stats, notes, history, baseline, and the HTTP API.

    python3 plugin/studio/test_studio.py

Standard library only, no network, no browser: models are tiny GLBs built here.
"""

from __future__ import annotations

import base64
import http.client
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
import server  # noqa: E402
import studiolib as sl  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 16


def glb(path: Path, *, scale: float = 1.0, tris: int = 1, name: str = "SM_Box") -> Path:
    """A valid GLB with one mesh of `tris` triangles, 1 m tall (times `scale`)."""
    n = tris * 3
    positions = b"".join(struct.pack("<3f", (i % 2) * 0.5, (i % 3) * 0.5, 0.25) for i in range(n))
    gltf = {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"name": name, "mesh": 0, "scale": [scale, scale, scale], "translation": [0, 0.5, 0]}],
        "meshes": [{"name": name + "_Mesh", "primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}],
        "materials": [{"name": "M_Wood"}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": n, "type": "VEC3",
                       "min": [-0.5, -0.5, -0.25], "max": [0.5, 0.5, 0.25]}],
        "bufferViews": [{"buffer": 0, "byteLength": len(positions)}],
        "buffers": [{"byteLength": len(positions)}],
    }
    js = json.dumps(gltf).encode()
    js += b" " * (-len(js) % 4)
    body = positions + b"\0" * (-len(positions) % 4)
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


if __name__ == "__main__":
    unittest.main(verbosity=1)
