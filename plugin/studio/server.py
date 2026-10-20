"""Kiln Studio's local HTTP server: the page, the project's files, the review API,
and a server-sent event stream that tells the page when a model or a note changed.

Binds 127.0.0.1 only, and answers only requests addressed to it by that name
(a DNS-rebinding page cannot read the project). Writes need a same-origin JSON body.
"""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
import queue
import subprocess
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

import checks
import estimate
import handoff
import phoneshare
import setup_status
import studiolib as sl
import worker as wk

HERE = Path(__file__).resolve().parent

VERSION = "1.0.0"
STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 30 * 1024 * 1024
MAX_IMPORT = 512 * 1024 * 1024   # a dropped model file
TYPES = {".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".webp": "image/webp",
         ".md": "text/plain; charset=utf-8", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8", ".json": "application/json; charset=utf-8", ".obj": "text/plain; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".html": "text/html; charset=utf-8", ".yaml": "text/plain; charset=utf-8",
         ".yml": "text/plain; charset=utf-8", ".py": "text/plain; charset=utf-8"}


class Studio:
    """The project, its current asset index, and the live-event subscribers."""

    def __init__(self, project: sl.Project, interval: float = 1.0):
        self.project = project
        self.interval = interval
        self.assets: dict[str, sl.Asset] = {}
        self.sig: dict[str, tuple] = {}
        self.store_sig: dict[str, float] = {}
        self.subs: list[queue.Queue] = []
        self.lock = threading.Lock()
        # What the open page shows (it reports it): read by the kiln-studio MCP server.
        self.selection: dict | None = None
        # The view images asked of the page (get_view_image): id -> (event, image bytes).
        self.captures: dict[str, list] = {}
        # Claude Code runs started from the page (worker.py): off until the project turns it on.
        self.worker = wk.Worker(project, self.emit)
        # A model in AR on the phone: a separate, read-only server, started on the first QR code.
        self.phone = phoneshare.PhoneShare(cache=project.data / "cache" / "ar")
        # Game and AR outputs made here, without Claude (tools/export_outputs.py): asset id -> kinds.
        self.exporting: dict[str, list[str]] = {}
        self.refresh(initial=True)

    # live events
    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=200)
        with self.lock:
            self.subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)

    def emit(self, event: dict) -> None:
        with self.lock:
            subs = list(self.subs)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    # index
    def asset(self, asset_id: str) -> sl.Asset:
        with self.lock:
            a = self.assets.get(asset_id)
        if a is None:
            raise KeyError(f"no asset {asset_id!r}")
        return a

    def _store_files(self) -> dict[str, float]:
        out = {}
        base = self.project.data / "assets"
        if base.is_dir():
            for d in base.iterdir():
                for name in ("notes.json", "history.json", "live.json"):
                    p = d / name
                    try:
                        out[f"{d.name}/{name}"] = p.stat().st_mtime
                    except FileNotFoundError:
                        pass
        for name in ("catalog.json", "work.json", "requests.json"):
            p = self.project.data / name
            try:
                out[name] = p.stat().st_mtime
            except FileNotFoundError:
                pass
        return out

    def refresh(self, initial: bool = False) -> None:
        assets = {a.id: a for a in sl.scan(self.project)}
        sig = {a.id: tuple((v.rel, v.mtime, v.size) for v in a.variants) for a in assets.values()}
        for a in assets.values():
            old = self.assets.get(a.id)
            if old and sig[a.id] == self.sig.get(a.id):
                # Unchanged: keep the hashes already computed.
                for v, ov in zip(a.variants, old.variants):
                    v.hash = ov.hash
        with self.lock:
            prev_sig, self.assets, self.sig = self.sig, assets, sig
        if initial:
            self.store_sig = self._store_files()
            return
        listing = set(prev_sig) != set(sig)
        for aid, s in sig.items():
            if aid in prev_sig and prev_sig[aid] != s:
                a = assets[aid]
                try:
                    sl.observe(self.project, a)
                except (OSError, ValueError, TimeoutError) as e:  # mid-write, or locked
                    print(f"kiln-studio: {aid}: {e}", flush=True)
                    with self.lock:  # forget this signature, so the next tick retries
                        self.sig[aid] = prev_sig[aid]
                    continue
                self.emit({"type": "model", "id": aid,
                           "variants": {v.label: v.hash for v in a.variants}})
                listing = True
        # A model that lands while its build is under way: its build steps were written
        # before it existed, so no live event named it yet.
        for aid in set(sig) - set(prev_sig):
            if assets[aid].kiln:
                live = sl.load_live(self.project, aid)
                if live and live.get("state") == "building":
                    self.emit({"type": "live", "id": aid, "live": sl.live_summary(live)})
        store = self._store_files()
        keys = {sl.asset_key(aid): aid for aid in assets}
        for k in set(store) | set(self.store_sig):
            if store.get(k) != self.store_sig.get(k):
                if k == "catalog.json":
                    listing = True
                elif k == "requests.json":
                    self.emit({"type": "requests"})
                elif k == "work.json":
                    # Which models a kiln command is on: the list's dots.
                    self.emit({"type": "work", "work": sl.work_view(sl.load_work(self.project))})
                elif k.endswith("/live.json"):
                    # A build step: the phase strip, and the list's "building" badge.
                    aid = keys.get(k.split("/")[0])
                    if aid:
                        live = sl.load_live(self.project, aid)
                        self.emit({"type": "live", "id": aid, "live": sl.live_summary(live)})
                        listing = True
                else:
                    aid = keys.get(k.split("/")[0])
                    if aid:
                        self.emit({"type": "notes", "id": aid})
                        listing = True
        self.store_sig = store
        if listing:
            self.emit({"type": "assets"})

    def watch(self) -> None:
        while True:
            time.sleep(self.interval)
            try:
                self.refresh()
            except Exception as e:  # never let the watcher die
                print(f"kiln-studio: watch: {e!r}", flush=True)


def _decode_image(data_url: str) -> bytes:
    for prefix, magic in (("data:image/jpeg;base64,", b"\xff\xd8"),
                          ("data:image/webp;base64,", b"RIFF"),
                          ("data:image/png;base64,", b"\x89PNG")):
        if data_url.startswith(prefix):
            raw = base64.b64decode(data_url[len(prefix):])
            if not raw.startswith(magic):
                raise ValueError("image data does not match its type")
            return raw
    raise ValueError("expected a JPEG, WebP or PNG data URL")


VIEWS = ("front", "back", "left", "right", "top", "iso")


def _vec(v, n=3) -> list[float] | None:
    if isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) and abs(x) < 1e7 for x in v):
        return [float(x) for x in v]
    return None


def clean_selection(body: dict) -> dict:
    """What the page reported, kept to known fields of the right shape."""
    cam = body.get("camera") if isinstance(body.get("camera"), dict) else {}
    note = body.get("note") if isinstance(body.get("note"), dict) else None
    out = {
        "asset": str(body["asset"])[:500] if body.get("asset") else None,
        "variant": str(body["variant"])[:100] if body.get("variant") else None,
        "camera": {k: _vec(cam.get(k)) for k in ("position_blender", "target_blender", "position", "target") if _vec(cam.get(k))} or None,
        "note": {"id": str(note.get("id", ""))[:40], "number": note.get("number") if isinstance(note.get("number"), int) else None}
                if note and sl.NOTE_ID_RE.match(str(note.get("id", ""))) else None,
        "compare": str(body["compare"])[:100] if body.get("compare") else None,
        "shading": str(body["shading"])[:20] if body.get("shading") else None,
        "visible": body.get("visible") is not False,
        "at": time.time(),
    }
    if out["camera"] is not None and isinstance(cam.get("fov"), (int, float)):
        out["camera"]["fov"] = float(cam["fov"])
    return out


def clean_camera(body: dict) -> dict:
    """A camera move for the page: a preset view, a note's own view, or a position and a
    target in Blender's frame (metres, Z up); with an asset, the page opens it first."""
    out: dict = {}
    if body.get("asset"):
        out["asset"] = str(body["asset"])[:500]
    if body.get("view"):
        if body["view"] not in VIEWS:
            raise ValueError(f"view must be one of {', '.join(VIEWS)}")
        out["view"] = body["view"]
    elif body.get("note"):
        if not sl.NOTE_ID_RE.match(str(body["note"])):
            raise ValueError("bad note id")
        out["note"] = str(body["note"])
    else:
        pos, tgt = _vec(body.get("position_blender")), _vec(body.get("target_blender"))
        if not (pos and tgt):
            raise ValueError("give view, note, or position_blender and target_blender ([x, y, z] in metres)")
        if pos == tgt:
            raise ValueError("the camera and its target are the same point")
        out["position_blender"], out["target_blender"] = pos, tgt
    return out


SHADINGS = ("lit", "unlit", "clay", "normals", "uv", "faces")
TOGGLES = ("wire", "grid", "bounds", "skeleton")
BACKGROUNDS = ("dark", "mid", "light")
COMPARE_MODES = ("split", "side", "off")


def clean_control(body: dict) -> dict:
    """A command for the open page (the kiln-studio MCP server drives Studio with them):
    open a model and a stage, set the view, compare, play a clip, present."""
    action = body.get("action")
    out: dict = {"action": action}
    s = lambda k, n=200: str(body[k])[:n] if body.get(k) not in (None, "") else None
    if action == "open":
        if not s("asset", 500):
            raise ValueError("open needs an asset")
        out["asset"], out["stage"] = s("asset", 500), s("stage", 100)
    elif action == "view":
        if body.get("shading") is not None and body["shading"] not in SHADINGS:
            raise ValueError(f"shading is one of {', '.join(SHADINGS)}")
        if body.get("background") is not None and body["background"] not in BACKGROUNDS:
            raise ValueError(f"background is one of {', '.join(BACKGROUNDS)}")
        if body.get("view") is not None and body["view"] not in VIEWS:
            raise ValueError(f"view is one of {', '.join(VIEWS)}")
        out.update({k: body[k] for k in ("shading", "background", "view") if body.get(k) is not None})
        out.update({k: bool(body[k]) for k in (*TOGGLES, "frame") if body.get(k) is not None})
        if len(out) == 1:
            raise ValueError("view needs at least one of shading, background, view, frame, " + ", ".join(TOGGLES))
    elif action == "compare":
        if body.get("mode") not in COMPARE_MODES:
            raise ValueError(f"compare mode is one of {', '.join(COMPARE_MODES)}")
        out["mode"], out["target"] = body["mode"], s("target", 100)
    elif action == "play":
        out["clip"] = s("clip", 200)
        if body.get("playing") is not None:
            out["playing"] = bool(body["playing"])
        if body.get("speed") is not None:
            if body["speed"] not in (0.25, 0.5, 1, 2):
                raise ValueError("speed is 0.25, 0.5, 1 or 2")
            out["speed"] = body["speed"]
        if body.get("time") is not None:
            if not isinstance(body["time"], (int, float)) or body["time"] < 0:
                raise ValueError("time is seconds from the clip's start")
            out["time"] = float(body["time"])
    elif action == "present":
        out["on"] = body.get("on") is not False
    else:
        raise ValueError("action is open, view, compare, play or present")
    return {k: v for k, v in out.items() if v is not None}


def make_handler(studio: Studio, port_ref: list[int]):
    project = studio.project

    class Handler(BaseHTTPRequestHandler):
        server_version = f"KilnStudio/{VERSION}"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            if len(args) > 1 and str(args[1])[:1] in "45":
                super().log_message(fmt, *args)

        # helpers
        def _send(self, code: int, body: bytes, ctype: str, headers: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (headers or {"Cache-Control": "no-store"}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj).encode(), "application/json")

        def _err(self, code: int, msg: str) -> None:
            # A refused request may still have an unread body; on a kept-alive
            # connection it would be parsed as the next request.
            self.close_connection = True
            self._json({"error": msg}, code)

        def _file(self, p: Path) -> None:
            if not p.is_file():
                return self._err(404, "not found")
            st = p.stat()
            etag = f'"{int(st.st_mtime * 1000):x}-{st.st_size:x}"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            ctype = TYPES.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            self._send(200, p.read_bytes(), ctype, {"Cache-Control": "no-cache", "ETag": etag})

        def _body(self) -> dict:
            if "json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("expected a JSON body")
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("body too large")
            data = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data

        def _host_ok(self) -> bool:
            host = self.headers.get("Host", "")
            return host in (f"127.0.0.1:{port_ref[0]}", f"localhost:{port_ref[0]}")

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            return origin is None or origin == f"http://{self.headers.get('Host')}"

        def _route(self) -> list[str]:
            # Asset ids are sent encodeURIComponent'd: split first, then unquote.
            return [unquote(p) for p in urlparse(self.path).path.split("/")[1:]]

        # verbs
        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            if not self._host_ok():
                return self._err(403, "bad host")
            parts = self._route()
            try:
                if parts in ([""], ["index.html"]):
                    return self._file(STATIC / "index.html")
                if parts[0] == "static" and 2 <= len(parts) <= 3:
                    # static/app.js, static/i18n/fr.json: nothing outside static/.
                    p = (STATIC / "/".join(parts[1:])).resolve()
                    if STATIC not in p.parents:
                        return self._err(403, "forbidden")
                    return self._file(p)
                if parts[:2] == ["api", "messages"]:
                    # The checks' words, in English: the page renders a finding's codes with
                    # them, or with static/i18n/<lang>.json.
                    return self._json({"messages": checks.MESSAGES})
                if parts[0] == "files":
                    p = project.inside("/".join(parts[1:]))
                    # ?h=<hash>: the page asks for one version. If the file changed since,
                    # say so instead of serving content the page would file under the old hash.
                    want = parse_qs(urlparse(self.path).query).get("h", [""])[0]
                    if want and p.is_file() and p.suffix.lower() in sl.MODEL_EXTS and sl.file_hash(p) != want:
                        return self._err(409, "the file changed since; reload")
                    if parse_qs(urlparse(self.path).query).get("zip") and p.is_dir() and p.name in sl.OUTPUT_DIRS:
                        # An output with several files (a print's 3MF and STLs, AR's USDZ and GLB): one zip.
                        buf = io.BytesIO()
                        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                            for f in sorted(p.iterdir()):
                                # The deliverables only: kiln's working files (a part's .blend, a
                                # check's report) stay in the folder.
                                if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in sl.MODEL_EXTS:
                                    z.write(f, f.name)
                        name = f"{p.parent.name}_{p.name}.zip"
                        return self._send(200, buf.getvalue(), "application/zip",
                                          {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
                                           "Cache-Control": "no-store"})
                    if parse_qs(urlparse(self.path).query).get("download") and p.is_file():
                        # The Outputs bar's download: the file itself, saved under its own name.
                        return self._send(200, p.read_bytes(), "application/octet-stream",
                                          {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(p.name)}",
                                           "Cache-Control": "no-store"})
                    return self._file(p)
                if parts[:2] == ["api", "hello"]:
                    return self._json({"app": "kiln-studio", "version": VERSION,
                                       "root": str(project.root), "pid": os.getpid()})
                if parts[:2] == ["api", "config"]:
                    # The project's settings, shared with Claude (references/studio.md § 9).
                    md = project.root / "CLAUDE.md"
                    return self._json({"settings": project.settings(), "defaults": sl.CONFIG_DEFAULTS,
                                       "targets": list(sl.TARGETS), "file": f"{sl.DATA_DIR}/config.json",
                                       "claude_md": {"path": str(md), "exists": md.is_file(),
                                                     "lines": len(md.read_text(errors="ignore").splitlines()) if md.is_file() else 0},
                                       "target_source": project.target_source(), "user_defaults": sl.user_defaults()})
                if parts[:2] == ["api", "status"]:
                    # The welcome screen's setup line: Blender, the MCP add-on, SkinTokens.
                    fresh = parse_qs(urlparse(self.path).query).get("fresh", [""])[0] == "1"
                    return self._json(setup_status.install_status(project.root, max_age=0 if fresh else 60))
                if parts[:2] == ["api", "requests"]:
                    return self._json({"requests": sl.load_requests(project)})
                if parts[:2] == ["api", "selection"]:
                    with studio.lock:
                        sel, pages = studio.selection, len(studio.subs)
                    if sel:
                        now = time.time()
                        sel = {**sel, "age_s": round(now - sel["seen_at"], 1),
                               "changed_s": round(now - sel["changed_at"], 1)}
                    return self._json({"selection": sel, "pages": pages})
                if parts[:2] == ["api", "events"]:
                    return self._events()
                if parts == ["api", "claude"]:
                    q = parse_qs(urlparse(self.path).query)
                    return self._json(studio.worker.status(force_auth=q.get("auth", [""])[0] == "1"))
                if parts == ["api", "claude", "estimate"]:
                    # Before a request: how long and how much, from this project's runs or the bench.
                    task = parse_qs(urlparse(self.path).query).get("task", [""])[0]
                    return self._json(estimate.estimate(project, task, wk.user_settings()["account"]))
                if parts == ["api", "claude", "thread"]:
                    key = parse_qs(urlparse(self.path).query).get("key", [""])[0]
                    if not (key.startswith(("asset:", "request:")) or key in (wk.PROJECT_KEY, wk.SETUP_KEY)):
                        raise ValueError("key is asset:<id>, request:<id>, project or setup")
                    return self._json(studio.worker.thread(key))
                if parts[:2] == ["api", "assets"]:
                    cat = sl.load_catalog(project)
                    with studio.lock:
                        assets = list(studio.assets.values())
                    rows = [sl.asset_summary(project, a, cat) for a in assets]
                    # The batch folders' token estimates, for the list's category headers.
                    batches = {}
                    for folder in {a.default_category for a in assets if a.kiln and a.default_category}:
                        est = checks.batch_estimate(project, folder)
                        if est:
                            batches[folder] = {k: est[k] for k in ("name", "assets", "range", "remaining", "manifest")}
                    return self._json({"root": str(project.root), "name": project.root.name,
                                       "assets": rows, "batches": batches,
                                       "work": sl.work_view(sl.load_work(project))})
                if parts[:2] == ["api", "asset"] and parts[3:] == ["outputs"]:
                    # The download dialog: each output, its files, their size and use.
                    lang = parse_qs(urlparse(self.path).query).get("lang", ["en"])[0]
                    return self._json(handoff.listing(project, studio.asset(parts[2]), lang))
                if parts[:2] == ["api", "asset"] and parts[3:] == ["package"]:
                    # What to hand over: the outputs picked (all by default) and a sheet, in one zip.
                    q = parse_qs(urlparse(self.path).query)
                    outs = q["outs"][0].split(",") if q.get("outs") else None
                    name, data = handoff.make_package(project, studio.asset(parts[2]), q.get("lang", ["en"])[0],
                                                      outs, q.get("sheet", ["1"])[0] != "0",
                                                      q["variants"][0].split(",") if q.get("variants") else [],
                                                      # The finishes to send, by name (absent: all of them), and the one shown.
                                                      [x for x in q["finishes"][0].split("\n") if x] if "finishes" in q else None,
                                                      q.get("shown", [None])[0])
                    return self._send(200, data, "application/zip",
                                      {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
                                       "Cache-Control": "no-store"})
                if parts[:2] == ["api", "asset"] and len(parts) == 3:
                    a = studio.asset(parts[2])
                    sl.observe(project, a)
                    detail = sl.asset_detail(project, a, sl.load_catalog(project))
                    detail["exporting"] = studio.exporting.get(a.id, [])
                    try:
                        detail["checks"] = checks.asset_checks(project, a)
                    except Exception as e:  # a check must never hide the model
                        print(f"kiln-studio: checks {a.id}: {e!r}", flush=True)
                        detail["checks"] = None
                    return self._json(detail)
                return self._err(404, "not found")
            except KeyError as e:
                return self._err(404, str(e).strip("'\""))
            except ValueError as e:
                return self._err(400, str(e))
            except TimeoutError as e:
                return self._err(503, str(e))

        def _write(self, method: str) -> None:
            if not (self._host_ok() and self._origin_ok()):
                return self._err(403, "cross-origin")
            parts = self._route()
            try:
                if method == "POST" and parts == ["api", "import"]:
                    # A model file dropped on the page: the bytes as they are, not JSON.
                    q = parse_qs(urlparse(self.path).query)
                    n = int(self.headers.get("Content-Length") or 0)
                    if n > MAX_IMPORT:
                        raise ValueError(f"file too large (over {MAX_IMPORT // 2**20} MB)")
                    if "octet-stream" not in (self.headers.get("Content-Type") or ""):
                        raise ValueError("expected the file's bytes (application/octet-stream)")
                    rel = sl.import_file(project, q.get("name", [""])[0], self.rfile.read(n), q.get("folder", [None])[0])
                    studio.refresh()
                    return self._json({"path": rel})
                body = self._body() if method != "DELETE" else {}
                if method == "POST" and parts == ["api", "work", "check"]:
                    # The user looked at these models (all the finished ones when none named).
                    ids = body.get("assets")
                    run = sl.check_work(project, [str(i) for i in ids] if isinstance(ids, list) else None)
                    return self._json({"work": sl.work_view(run)})
                if method == "POST" and parts == ["api", "requests"]:
                    photo = _decode_image(body["photo"]) if body.get("photo") else None
                    r = sl.add_request(project, body.get("brief", ""), type_=body.get("type") or None,
                                       target=body.get("target") or None, style=body.get("style") or None, photo=photo)
                    return self._json(r)
                if method == "POST" and parts == ["api", "selection"]:
                    # The page says what it shows: the model, its stage, the camera, the note picked.
                    # Sent on every change and every 15 s while the page is open: `seen_at` is
                    # the last word from the page, `changed_at` the last time what it shows changed.
                    sel = clean_selection(body)
                    with studio.lock:
                        prev = studio.selection
                        same = prev and {k: v for k, v in prev.items() if k not in ("at", "seen_at", "changed_at", "visible")} == \
                            {k: v for k, v in sel.items() if k not in ("at", "seen_at", "changed_at", "visible")}
                        sel["seen_at"] = sel["at"]
                        sel["changed_at"] = prev["changed_at"] if same else sel["at"]
                        studio.selection = sel
                    return self._json({"ok": True})
                if method == "POST" and parts == ["api", "camera"]:
                    # Turn the open page's view (the kiln-studio MCP server's set_camera).
                    ev = clean_camera(body)
                    with studio.lock:
                        pages = len(studio.subs)
                    if not pages:
                        return self._err(409, "no Studio page is open to turn")
                    studio.emit({"type": "camera", **ev})
                    return self._json({"pages": pages, **ev})
                if method == "POST" and parts == ["api", "control"]:
                    # Drive the open page (the kiln-studio MCP server's open_model, set_view, …).
                    ev = clean_control(body)
                    with studio.lock:
                        pages = len(studio.subs)
                    if not pages:
                        return self._err(409, "no Studio page is open to drive")
                    studio.emit({"type": "control", **ev})
                    return self._json({"pages": pages, **ev})
                if method == "POST" and parts == ["api", "view-image"]:
                    # Ask the open page for the image it shows; it posts it back below.
                    with studio.lock:
                        pages = len(studio.subs)
                    if not pages:
                        return self._err(409, "no Studio page is open to look at")
                    cid = sl.new_id("v")
                    done = threading.Event()
                    with studio.lock:
                        studio.captures[cid] = [done, None]
                    studio.emit({"type": "capture", "id": cid, "full": body.get("full") is not False})
                    done.wait(10)
                    with studio.lock:
                        _, img = studio.captures.pop(cid)
                    if img is None:
                        return self._err(504, "the page did not send its view in 10 s (hidden tab, or still loading)")
                    ext = "jpg" if img[:2] == b"\xff\xd8" else "webp" if img[:4] == b"RIFF" else "png"
                    d = project.data / "cache" / "views"
                    d.mkdir(parents=True, exist_ok=True)
                    for old in sorted(d.glob("v_*"))[:-20]:   # keep the last 20
                        old.unlink(missing_ok=True)
                    path = d / f"{cid}.{ext}"
                    path.write_bytes(img)
                    return self._json({"path": str(path), "bytes": len(img)})
                if method == "POST" and parts[:2] == ["api", "view-image"] and len(parts) == 3:
                    img = _decode_image(str(body.get("image", "")))
                    with studio.lock:
                        slot = studio.captures.get(parts[2])
                        if slot and slot[1] is None:
                            slot[1] = img
                            slot[0].set()
                    return self._json({"ok": bool(slot)})
                if method == "POST" and parts == ["api", "claude", "jobs"]:
                    # Ask Claude: a chat message, the open notes, a Create request, an answer.
                    return self._json(studio.worker.submit(
                        str(body.get("kind", "")), asset=str(body["asset"])[:500] if body.get("asset") else None,
                        text=str(body.get("text", "")), request=str(body["request"])[:40] if body.get("request") else None,
                        context=body.get("context") if isinstance(body.get("context"), dict) else None,
                        lang=str(body.get("lang", "en")), task=str(body["task"])[:40] if body.get("task") else None,
                        key=str(body["key"])[:600] if str(body.get("key", "")).startswith("request:") or body.get("key") == wk.PROJECT_KEY else None))
                if method == "POST" and parts[:3] == ["api", "claude", "jobs"] and len(parts) == 5:
                    if parts[4] == "stop":
                        return self._json(studio.worker.stop(parts[3]))
                    if parts[4] == "edit":
                        return self._json(studio.worker.edit(parts[3], str(body.get("text", ""))[:8000]))
                    if parts[4] == "now":
                        return self._json(studio.worker.now(parts[3]))
                    if parts[4] == "answer":
                        return self._json(studio.worker.answer(parts[3], str(body.get("decision", "")), str(body.get("reason", ""))))
                if parts == ["api", "phone", "log"]:
                    return self._json({"log": studio.phone.log})
                if method == "POST" and parts == ["api", "phone", "stop"]:
                    studio.phone.stop()
                    return self._json({"ok": True})
                if method == "PUT" and parts == ["api", "claude", "account"]:
                    # Per user (~/.kiln-studio/claude.json), not per project: which account runs.
                    wk.save_user_settings(account=str(body.get("account", "")))
                    return self._json(studio.worker.status(force_auth=True))
                if method == "POST" and parts == ["api", "claude", "key"]:
                    # The API key goes to the keychain; it never comes back out through here.
                    wk.set_api_key(str(body["key"]) if body.get("key") else None)
                    return self._json(studio.worker.status(force_auth=True))
                if method == "POST" and parts == ["api", "claude", "login"]:
                    wk.login_account(studio.worker.claude)
                    return self._json({"started": True, "folder": str(wk.account_dir())})
                if method == "POST" and parts == ["api", "claude", "blender", "stop"]:
                    for i in sorted({0, *studio.worker.blenders}):
                        studio.worker.blender_for(i).stop()
                    return self._json(studio.worker.blender.status())
                if method == "POST" and parts == ["api", "example"]:
                    aid = sl.add_example(project)
                    studio.refresh()
                    return self._json({"id": aid})
                if method == "PUT" and parts == ["api", "config"]:
                    settings = sl.save_config(project, body)
                    studio.refresh()   # exclude: the list changes now, not at the next tick
                    return self._json({"settings": settings, "target_source": project.target_source(),
                                       "user_defaults": sl.user_defaults()})
                if method == "POST" and parts == ["api", "claude-md"]:
                    # The project's CLAUDE.md, which Claude Code reads in every session here (the
                    # terminal's and Studio's): created on request with a short head, then opened
                    # in the user's own editor.
                    md = project.root / "CLAUDE.md"
                    created = False
                    if not md.exists():
                        fr = body.get("lang") == "fr"
                        md.write_text(("# Instructions pour Claude\n\n"
                                       "Claude Code lit ce fichier à chaque session dans ce dossier, depuis le terminal comme depuis Kiln Studio.\n"
                                       "Décrivez ce qui vaut pour tout le projet : l'univers, le style, l'échelle, les budgets.\n\n")
                                      if fr else
                                      ("# Instructions for Claude\n\n"
                                       "Claude Code reads this file in every session in this folder, from the terminal and from Kiln Studio.\n"
                                       "Say what holds for the whole project: the world, the style, the scale, the budgets.\n\n"))
                        created = True
                    opener = "open" if sys.platform == "darwin" else "xdg-open" if sys.platform.startswith("linux") else None
                    if opener:
                        subprocess.Popen([opener, str(md)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif os.name == "nt":
                        os.startfile(str(md))  # noqa: S606 - the user's own file, on their request
                    return self._json({"path": str(md), "created": created})
                if method == "PUT" and parts == ["api", "defaults"]:
                    # The user's defaults for every project on this computer (~/.kiln-studio).
                    sl.save_user_defaults(**{k: v for k, v in body.items() if k == "target"})
                    return self._json({"settings": project.settings(), "target_source": project.target_source(),
                                       "user_defaults": sl.user_defaults()})
                if parts[:2] != ["api", "asset"] or len(parts) < 4:
                    return self._err(404, "not found")
                a = studio.asset(parts[2])
                rest = parts[3:]
                shot = _decode_image(body["shot"]) if body.get("shot") else None
                detail = _decode_image(body["detail"]) if body.get("detail") else None
                if method == "POST" and rest == ["notes"]:
                    text = str(body.get("text", "")).strip()
                    if not text:
                        raise ValueError("a note needs text")
                    note = sl.add_note(project, a, text, variant=body.get("variant"),
                                       anchor=body.get("anchor"), camera=body.get("camera"),
                                       view=body.get("view"), shot=shot, detail=detail)
                    return self._json(note)
                if len(rest) >= 2 and rest[0] == "notes":
                    nid = rest[1]
                    if not sl.NOTE_ID_RE.match(nid):
                        raise ValueError("bad note id")
                    if method == "DELETE" and len(rest) == 2:
                        sl.delete_note(project, a.id, nid)
                        return self._json({"ok": True})
                    if method == "PATCH" and len(rest) == 2:
                        return self._json(sl.edit_note_text(project, a.id, nid, str(body.get("text", ""))))
                    if method == "POST" and rest[2:] == ["thread"]:
                        status = body.get("status") or None
                        return self._json(sl.reply(project, a, nid, str(body.get("text", "")),
                                                   by="user", status=status, shot=shot))
                    if method == "POST" and len(rest) == 5 and rest[2] == "thread" and rest[4] == "shot":
                        if not sl.REPLY_ID_RE.match(rest[3]) or not shot:
                            raise ValueError("bad reply id or no shot")
                        return self._json({"shot": sl.set_reply_shot(project, a.id, nid, rest[3], shot, detail)})
                if method == "PUT" and rest == ["meta"]:
                    tags = body.get("tags")
                    return self._json(sl.set_meta(project, a.id, category=body.get("category"),
                                                  tags=list(tags) if isinstance(tags, list) else None))
                if method == "POST" and rest == ["thumb"]:
                    h = str(body.get("hash", ""))
                    if not h.isalnum() or not shot:
                        raise ValueError("bad thumb")
                    return self._json({"thumb": sl.save_thumb(project, a.id, h, shot)})
                if method == "POST" and rest == ["snapshot"]:
                    return self._json(sl.take_baseline(project, a, a.variant(body.get("variant")),
                                                       reason="snapshot from Studio"))
                if method == "POST" and rest == ["export"]:
                    # "+ Game", "+ AR": kiln's settings in Blender headless, checked; seconds, no Claude.
                    kinds = [k for k in body.get("kinds", []) if k in ("game", "ar")]
                    if not kinds or not a.kiln:
                        raise ValueError("game or ar, on a kiln model")
                    if not any(v.label == "original" for v in a.variants):
                        raise ValueError(f"{a.name} has no _original.glb to export from")
                    with studio.lock:
                        if a.id in studio.exporting:
                            raise ValueError("an export of this model is already running")
                        studio.exporting[a.id] = kinds
                    folder = project.root / a.folder
                    aid = a.id

                    def run() -> None:
                        t0 = time.time()
                        try:
                            r = subprocess.run([sys.executable, str(HERE.parent / "tools" / "export_outputs.py"), str(folder), *kinds],
                                               capture_output=True, text=True, timeout=1200)
                            out = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"ok": False, "error": r.stderr[-300:]}
                        except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
                            out = {"ok": False, "error": str(e)}
                        with studio.lock:
                            studio.exporting.pop(aid, None)
                        studio.refresh()
                        studio.emit({"type": "export", "id": aid, "kinds": kinds, "ok": out.get("ok", False),
                                     "error": out.get("error", ""), "seconds": round(time.time() - t0)})
                    threading.Thread(target=run, daemon=True, name="export").start()
                    studio.emit({"type": "export", "id": aid, "kinds": kinds, "state": "running"})
                    return self._json({"started": True, "kinds": kinds})
                if method == "POST" and rest == ["phone"]:
                    # The QR code: AR's USDZ (iPhone) and GLB (Android; the web one if AR has none).
                    files = {}
                    for v in a.variants:
                        kind, ext = v.label.split(".")[0], v.path.suffix.lower()
                        if kind == "ar" and ext == ".usdz" and (v.path.name == f"{a.name}_ar.usdz" or "usdz" not in files):
                            files["usdz"] = v.path   # the model's own, not a finish's
                        elif kind == "ar" and ext == ".glb":
                            files["glb"] = v.path
                    if "glb" not in files:
                        web = next((v for v in a.variants if v.label == "final" and v.path.suffix.lower() == ".glb"), None)
                        if web:
                            files["glb"] = web.path
                    # Its finishes (from the GLB), and a USDZ per finish when one was exported.
                    fins, shown = handoff.finish_state(files["glb"]) if files.get("glb") else ([], None)
                    per = {}
                    if files.get("usdz"):
                        for f in fins:
                            p = files["usdz"].with_name(f"{a.name}_ar_{sl.finish_slug(f)}.usdz")
                            if p.is_file():
                                per[f] = p
                    sw = body.get("swatches") if isinstance(body.get("swatches"), dict) else {}
                    out = studio.phone.link(a.name, files, str(body.get("lang", "en")), fins, shown, per,
                                            {k: str(v)[:40] for k, v in sw.items() if k in fins})
                    # The finishes an iPhone cannot pick yet (no USDZ of their own).
                    # (none when Studio makes them itself, with the user's Blender)
                    out["ios_missing"] = [] if phoneshare.blender() else [f for f in fins if f != shown and f not in per] if files.get("usdz") else []
                    return self._json(out)
                if method == "POST" and rest == ["derive"]:
                    # Décliner: a new model from a copy of this one, then Claude makes the change.
                    new = sl.derive(project, a, str(body.get("name", "")), str(body.get("text", ""))[:4000],
                                    target=str(body.get("target", "same")), start=str(body.get("start", "current")),
                                    copy_notes=bool(body.get("notes")))
                    studio.refresh()
                    job = None
                    if body.get("prompt") and project.settings()["claude_worker"]:
                        job = studio.worker.submit("chat", asset=new.id, text=str(body["prompt"]), lang=str(body.get("lang", "en")),
                                                   task="derive")
                    return self._json({"asset": new.id, "job": job})
                if method == "POST" and rest == ["reveal"]:
                    # Show one of the model's files in the Finder (or the file manager).
                    rel = str(body.get("file") or "")
                    if rel not in {v.rel for v in a.variants} | set(a.files):
                        return self._err(400, "not one of this model's files")
                    p = project.inside(rel)
                    if sys.platform == "darwin":
                        subprocess.Popen(["open", "-R", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif sys.platform.startswith("linux"):
                        subprocess.Popen(["xdg-open", str(p.parent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif os.name == "nt":
                        subprocess.Popen(["explorer", "/select,", str(p)])
                    return self._json({"ok": True})
                if method == "POST" and rest == ["revert"]:
                    b = sl.revert(project, a)
                    studio.refresh()
                    return self._json(b)
                return self._err(404, "not found")
            except KeyError as e:
                return self._err(404, str(e).strip("'\""))
            except (ValueError, TypeError) as e:
                return self._err(400, str(e))
            except TimeoutError as e:
                return self._err(503, str(e))

        def do_POST(self) -> None:
            self._write("POST")

        def do_PUT(self) -> None:
            self._write("PUT")

        def do_PATCH(self) -> None:
            self._write("PATCH")

        def do_DELETE(self) -> None:
            self._write("DELETE")

        def _events(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = studio.subscribe()
            try:
                self.wfile.write(b"retry: 1500\n\n")
                self.wfile.flush()
                while True:
                    try:
                        ev = q.get(timeout=15)
                        self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                studio.unsubscribe(q)
                self.close_connection = True

    return Handler


class Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address) -> None:
        # A client that hangs up on a kept-alive connection is not an error worth a traceback.
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def make_server(project: sl.Project, port: int, interval: float = 1.0) -> tuple[ThreadingHTTPServer, Studio]:
    studio = Studio(project, interval)
    port_ref = [port]
    srv = Server(("127.0.0.1", port), make_handler(studio, port_ref))
    srv.daemon_threads = True
    port_ref[0] = srv.server_address[1]   # port 0 → the one the OS picked
    threading.Thread(target=studio.watch, daemon=True, name="watch").start()
    return srv, studio
