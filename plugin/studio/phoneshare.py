"""A model in AR on the phone: a QR code to a page on this computer, over the Wi-Fi.

    share = PhoneShare()
    share.link(name, {"usdz": path, "glb": path}) -> {"url", "expires", "ios", "android"}
    share.stop()

Studio itself listens on 127.0.0.1 only: it writes files and runs Claude, so it never faces
the network. This is a second, separate server, started on the first link: it binds the
local network, serves only the files linked — a page and the AR files of one model, read
only — under a random token, for 15 minutes. Anything else is a 404.

The page: on an iPhone or iPad, the USDZ in AR Quick Look (a link with rel="ar"); on
Android, the GLB in Scene Viewer (an intent link). Standard library only.
"""
from __future__ import annotations

import html
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

MINUTES = 15
TYPES = {"usdz": "model/vnd.usdz+zip", "glb": "model/gltf-binary"}
WORDS = {
    "en": {"title": "{name} in AR", "lead": "Open it in your room, on this phone.", "ios": "View in AR — iPhone, iPad",
           "android": "View in AR — Android", "none": "No AR file for this phone.",
           "foot": "Shared from Kiln Studio on your computer, for {m} minutes, on this Wi-Fi only."},
    "fr": {"title": "{name} en AR", "lead": "Posez-le chez vous, sur ce téléphone.", "ios": "Voir en AR — iPhone, iPad",
           "android": "Voir en AR — Android", "none": "Pas de fichier AR pour ce téléphone.",
           "foot": "Partagé depuis Kiln Studio sur votre ordinateur, pendant {m} minutes, sur ce Wi-Fi seulement."},
}


def lan_ip() -> str | None:
    """This computer's address on the local network (no packet is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None
    finally:
        s.close()


class PhoneShare:
    def __init__(self, port: int = 0):
        self.port = port
        self.srv: ThreadingHTTPServer | None = None
        self.links: dict[str, dict] = {}
        self.lock = threading.Lock()

    def link(self, name: str, files: dict[str, Path], lang: str = "en") -> dict:
        ip = lan_ip()
        if not ip:
            raise ValueError("this computer is on no local network: the phone could not reach it")
        files = {k: Path(v) for k, v in files.items() if k in TYPES and v and Path(v).is_file()}
        if not files:
            raise ValueError("no AR file to show: make the AR output first")
        self._start()
        token = secrets.token_urlsafe(16)
        until = time.time() + MINUTES * 60
        with self.lock:
            now = time.time()
            self.links = {t: l for t, l in self.links.items() if l["until"] > now}
            self.links[token] = {"name": name, "files": files, "until": until, "lang": lang if lang in WORDS else "en"}
        return {"url": f"http://{ip}:{self.srv.server_address[1]}/ar/{token}/", "expires": until,
                "ios": "usdz" in files, "android": "glb" in files, "minutes": MINUTES}

    def stop(self) -> None:
        with self.lock:
            self.links.clear()

    def shutdown(self) -> None:
        if self.srv:
            self.srv.shutdown()
            self.srv.server_close()
            self.srv = None

    def get(self, token: str) -> dict | None:
        with self.lock:
            l = self.links.get(token)
        return l if l and l["until"] > time.time() else None

    def _start(self) -> None:
        if self.srv:
            return
        share = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):   # quiet
                pass

            def do_GET(self):
                parts = self.path.split("?")[0].strip("/").split("/")
                l = share.get(parts[1]) if len(parts) >= 2 and parts[0] == "ar" else None
                if not l:
                    return self._send(404, b"Not found (the link may have expired).", "text/plain; charset=utf-8")
                if len(parts) == 2:
                    return self._send(200, share.page(parts[1], l, self.headers.get("Host", "")).encode(), "text/html; charset=utf-8")
                kind = parts[2].rsplit(".", 1)[-1] if len(parts) == 3 else ""
                f = l["files"].get(kind)
                if not f or parts[2] != f"model.{kind}":
                    return self._send(404, b"Not found.", "text/plain; charset=utf-8")
                self._send(200, f.read_bytes(), TYPES[kind], {"Content-Disposition": f'inline; filename="{quote(l["name"])}.{kind}"'})

            def _send(self, code, body, ctype, extra=None):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

        self.srv = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True, name="phone-share").start()

    def page(self, token: str, l: dict, host: str) -> str:
        w, name = WORDS[l["lang"]], html.escape(l["name"])
        base = f"http://{host}/ar/{token}/"
        # Quick Look wants the link to hold an image; Scene Viewer takes the GLB's full URL.
        icon = ("data:image/svg+xml," + quote('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'))
        ios = (f'<a class="b" rel="ar" href="model.usdz"><img src="{icon}" alt="">{html.escape(w["ios"])}</a>'
               if "usdz" in l["files"] else "")
        glb = quote(base + "model.glb", safe="")
        android = (f'<a class="b" href="intent://arvr.google.com/scene-viewer/1.0?file={glb}&amp;mode=ar_preferred&amp;title={quote(l["name"])}'
                   f'#Intent;scheme=https;package=com.google.android.googlequicksearchbox;action=android.intent.action.VIEW;'
                   f'S.browser_fallback_url={quote(base, safe="")};end;">{html.escape(w["android"])}</a>' if "glb" in l["files"] else "")
        return f"""<!doctype html><html lang="{l['lang']}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(w['title'].format(name=l['name']))}</title>
<style>
body{{margin:0;min-height:100vh;display:flex;flex-direction:column;justify-content:center;gap:14px;padding:28px 22px;box-sizing:border-box;
background:#0B0D11;color:#E6EBF2;font:16px/1.45 -apple-system,system-ui,sans-serif}}
h1{{margin:0;font-size:24px}} p{{margin:0;color:#A3ADBE}}
.b{{display:flex;align-items:center;justify-content:center;min-height:52px;border-radius:12px;background:#5CE1E6;color:#062A2C;
font-weight:600;text-decoration:none;font-size:17px}} .b img{{width:0;height:0}}
.f{{font-size:13px;color:#808A9D;margin-top:8px}}
</style></head><body>
<h1>{name}</h1><p>{html.escape(w['lead'])}</p>
{ios}{android}{'' if ios or android else '<p>' + html.escape(w['none']) + '</p>'}
<p class="f">{html.escape(w['foot'].format(m=MINUTES))}</p>
</body></html>"""
