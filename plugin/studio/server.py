"""Kiln Studio's local HTTP server: the page, the project's files, the review API,
and a server-sent event stream that tells the page when a model or a note changed.

Binds 127.0.0.1 only, and answers only requests addressed to it by that name
(a DNS-rebinding page cannot read the project). Writes need a same-origin JSON body.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import studiolib as sl

VERSION = "1.0.0"
STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 30 * 1024 * 1024
TYPES = {".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".webp": "image/webp",
         ".md": "text/plain; charset=utf-8", ".obj": "text/plain; charset=utf-8",
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
                for name in ("notes.json", "history.json"):
                    p = d / name
                    try:
                        out[f"{d.name}/{name}"] = p.stat().st_mtime
                    except FileNotFoundError:
                        pass
        cat = self.project.data / "catalog.json"
        if cat.exists():
            out["catalog.json"] = cat.stat().st_mtime
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
        store = self._store_files()
        keys = {sl.asset_key(aid): aid for aid in assets}
        for k in set(store) | set(self.store_sig):
            if store.get(k) != self.store_sig.get(k):
                if k == "catalog.json":
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
                if parts[0] == "static" and len(parts) == 2:
                    p = (STATIC / parts[1]).resolve()
                    if p.parent != STATIC:
                        return self._err(403, "forbidden")
                    return self._file(p)
                if parts[0] == "files":
                    p = project.inside("/".join(parts[1:]))
                    # ?h=<hash>: the page asks for one version. If the file changed since,
                    # say so instead of serving content the page would file under the old hash.
                    want = parse_qs(urlparse(self.path).query).get("h", [""])[0]
                    if want and p.is_file() and p.suffix.lower() in sl.MODEL_EXTS and sl.file_hash(p) != want:
                        return self._err(409, "the file changed since; reload")
                    return self._file(p)
                if parts[:2] == ["api", "hello"]:
                    return self._json({"app": "kiln-studio", "version": VERSION,
                                       "root": str(project.root), "pid": os.getpid()})
                if parts[:2] == ["api", "events"]:
                    return self._events()
                if parts[:2] == ["api", "assets"]:
                    cat = sl.load_catalog(project)
                    with studio.lock:
                        assets = list(studio.assets.values())
                    return self._json({"root": str(project.root), "name": project.root.name,
                                       "assets": [sl.asset_summary(project, a, cat) for a in assets]})
                if parts[:2] == ["api", "asset"] and len(parts) == 3:
                    a = studio.asset(parts[2])
                    sl.observe(project, a)
                    return self._json(sl.asset_detail(project, a, sl.load_catalog(project)))
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
                body = self._body() if method != "DELETE" else {}
                if parts[:2] != ["api", "asset"] or len(parts) < 4:
                    return self._err(404, "not found")
                a = studio.asset(parts[2])
                rest = parts[3:]
                shot = _decode_image(body["shot"]) if body.get("shot") else None
                if method == "POST" and rest == ["notes"]:
                    text = str(body.get("text", "")).strip()
                    if not text:
                        raise ValueError("a note needs text")
                    note = sl.add_note(project, a, text, variant=body.get("variant"),
                                       anchor=body.get("anchor"), camera=body.get("camera"), shot=shot)
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
                        return self._json({"shot": sl.set_reply_shot(project, a.id, nid, rest[3], shot)})
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


def make_server(project: sl.Project, port: int, interval: float = 1.0) -> tuple[ThreadingHTTPServer, Studio]:
    studio = Studio(project, interval)
    port_ref = [port]
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(studio, port_ref))
    srv.daemon_threads = True
    port_ref[0] = srv.server_address[1]   # port 0 → the one the OS picked
    threading.Thread(target=studio.watch, daemon=True, name="watch").start()
    return srv, studio
