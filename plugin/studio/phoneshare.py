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
import json
import re
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

MINUTES = 15
TOOL = Path(__file__).resolve().parent.parent / "tools" / "glb_to_usdz.py"


def blender() -> str | None:
    """The user's Blender, to make a finish's USDZ (as tools/open_blender.py finds it)."""
    import os
    import shutil
    for c in (os.environ.get("BLENDER"), "/Applications/Blender.app/Contents/MacOS/Blender",
              str(Path.home() / "Applications/Blender.app/Contents/MacOS/Blender"), shutil.which("blender")):
        if c and Path(c).exists():
            return c
    return None
TYPES = {"usdz": "model/vnd.usdz+zip", "glb": "model/gltf-binary"}
WORDS = {
    "en": {"title": "{name} in AR", "lead": "Open it in your room, on this phone.", "ios": "View in AR — iPhone, iPad",
           "android": "View in AR — Android", "none": "No AR file for this phone.",
           "foot": "Shared from Kiln Studio on your computer, for {m} minutes, on this Wi-Fi only.",
           "finish": "Finish", "nousdz": "On iPhone this finish has no AR file of its own yet: AR shows the model's own material."},
    "fr": {"title": "{name} en AR", "lead": "Posez-le chez vous, sur ce téléphone.", "ios": "Voir en AR — iPhone, iPad",
           "android": "Voir en AR — Android", "none": "Pas de fichier AR pour ce téléphone.",
           "foot": "Partagé depuis Kiln Studio sur votre ordinateur, pendant {m} minutes, sur ce Wi-Fi seulement.",
           "finish": "Finition", "nousdz": "Sur iPhone, cette finition n'a pas encore son fichier AR : l'AR montre la matière du modèle."},
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
    def __init__(self, port: int = 0, cache: Path | None = None):
        self.port = port
        # A finish's USDZ, made here by Blender from its GLB (tools/glb_to_usdz.py), kept by content.
        self.cache = Path(cache) if cache else None
        self.making: dict[str, threading.Event] = {}
        self.srv: ThreadingHTTPServer | None = None
        self.links: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.log: list[str] = []

    def link(self, name: str, files: dict[str, Path], lang: str = "en", finishes: list[str] | None = None,
             shown: str | None = None, usdz_finishes: dict[str, Path] | None = None,
             swatches: dict[str, str] | None = None) -> dict:
        """finishes: the GLB's (KHR_materials_variants), the page offers them — Android gets a
        GLB of the one picked, made here; iPhone a USDZ of it when one was exported
        (usdz_finishes, by finish name), the default USDZ otherwise."""
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
            self.links[token] = {"name": name, "files": files, "until": until, "lang": lang if lang in WORDS else "en",
                                 "finishes": list(finishes or []) if len(finishes or []) > 1 else [],
                                 "shown": shown, "usdz_finishes": {k: Path(v) for k, v in (usdz_finishes or {}).items() if Path(v).is_file()},
                                 "made": {}, "swatches": {k: v for k, v in (swatches or {}).items()
                                                          if re.match(r"^(#[0-9a-fA-F]{3,8}|rgb\(\d{1,3},\d{1,3},\d{1,3}\))$", v)}}
            l = self.links[token]
        # An iPhone's finishes: each one's USDZ, made in the background when Blender is there.
        if l["finishes"] and "glb" in files and blender() and self.cache:
            for i, f in enumerate(l["finishes"]):
                if f not in l["usdz_finishes"] and f != shown:
                    self._make_usdz(l, i)
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

    def file(self, l: dict, fname: str) -> bytes | None:
        """model.usdz / model.glb, or a finish's: model-<n>.usdz (exported), model-<n>.glb
        (made here once from the GLB, that finish alone)."""
        stem, kind = fname.rsplit(".", 1)
        if stem == "model":
            f = l["files"].get(kind)
            return f.read_bytes() if f else None
        if not stem.startswith("model-") or not stem[6:].isdigit() or int(stem[6:]) >= len(l["finishes"]):
            return None
        fin = l["finishes"][int(stem[6:])]
        if kind == "usdz":
            return self.usdz_for(l, int(stem[6:]))
        if fname not in l["made"]:
            import handoff
            l["made"][fname] = handoff.with_finishes(l["files"]["glb"], [fin], fin)
        return l["made"][fname]

    def _usdz_key(self, l: dict, i: int) -> str:
        import hashlib
        g = l["files"]["glb"]
        return hashlib.sha1(f"{g}|{g.stat().st_mtime}|{l['finishes'][i]}|{TOOL.stat().st_mtime}".encode()).hexdigest()[:16]

    def _make_usdz(self, l: dict, i: int) -> None:
        """The finish's GLB (that finish alone), then Blender: a USDZ, in the cache."""
        key = self._usdz_key(l, i)
        out = self.cache / f"{key}.usdz"
        if out.is_file() or key in self.making:
            return
        ev = self.making[key] = threading.Event()

        def run():
            import subprocess
            import tempfile
            try:
                self.cache.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory() as d:
                    src = Path(d) / "finish.glb"
                    src.write_bytes(self.file(l, f"model-{i}.glb"))
                    tmp = Path(d) / "finish.usdz"
                    subprocess.run([blender(), "-b", "--factory-startup", "--python", str(TOOL), "--", str(src), str(tmp)],
                                   capture_output=True, timeout=600)
                    if tmp.is_file():
                        tmp.replace(out)
            finally:
                ev.set()
                self.making.pop(key, None)
        threading.Thread(target=run, daemon=True, name="usdz-finish").start()

    def usdz_for(self, l: dict, i: int, wait: float = 240) -> bytes | None:
        """A finish's USDZ: exported with the model, else made here (waiting for it if needed)."""
        fin = l["finishes"][i]
        if fin in l["usdz_finishes"]:
            return l["usdz_finishes"][fin].read_bytes()
        if not self.cache:
            return None
        key = self._usdz_key(l, i)
        ev = self.making.get(key)
        if ev:
            ev.wait(wait)
        out = self.cache / f"{key}.usdz"
        return out.read_bytes() if out.is_file() else None

    def _start(self) -> None:
        if self.srv:
            return
        share = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *a):
                # What the phone asked, kept short (the last 50), to see why an opening failed.
                share.log.append(f"{time.strftime('%H:%M:%S')} {self.command} {self.path.split('?')[0][-40:]} "
                                 f"range={self.headers.get('Range', '-')} -> {a[1] if len(a) > 1 else ''} "
                                 f"{(self.headers.get('User-Agent') or '')[:60]}")
                del share.log[:-50]

            def do_HEAD(self):
                self._head_only = True
                self.do_GET()

            def do_GET(self):
                parts = self.path.split("?")[0].strip("/").split("/")
                l = share.get(parts[1]) if len(parts) >= 2 and parts[0] == "ar" else None
                if not l:
                    return self._send(404, b"Not found (the link may have expired).", "text/plain; charset=utf-8")
                if len(parts) == 2:
                    return self._send(200, share.page(parts[1], l, self.headers.get("Host", "")).encode(), "text/html; charset=utf-8")
                kind = parts[2].rsplit(".", 1)[-1] if len(parts) == 3 else ""
                data = share.file(l, parts[2]) if kind in TYPES else None
                if data is None:
                    return self._send(404, b"Not found.", "text/plain; charset=utf-8")
                extra = {"Content-Disposition": f'inline; filename="{quote(l["name"])}.{kind}"', "Accept-Ranges": "bytes"}
                # A byte range (Quick Look and media loaders ask for one): 206 with that part.
                rng = self.headers.get("Range", "")
                if rng.startswith("bytes="):
                    try:
                        a0, _, a1 = rng[6:].split(",")[0].partition("-")
                        start = int(a0) if a0 else max(0, len(data) - int(a1))
                        end = min(int(a1), len(data) - 1) if a0 and a1 else len(data) - 1
                        if start > end or start >= len(data):
                            raise ValueError
                    except ValueError:
                        return self._send(416, b"", TYPES[kind], {"Content-Range": f"bytes */{len(data)}"})
                    return self._send(206, data[start:end + 1], TYPES[kind], {**extra, "Content-Range": f"bytes {start}-{end}/{len(data)}"})
                self._send(200, data, TYPES[kind], extra)

            def _send(self, code, body, ctype, extra=None):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                if not getattr(self, "_head_only", False):
                    self.wfile.write(body)

        self.srv = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True, name="phone-share").start()

    def page(self, token: str, l: dict, host: str) -> str:
        w, name = WORDS[l["lang"]], html.escape(l["name"])
        base = f"http://{host}/ar/{token}/"
        fins = l["finishes"]
        # Per finish: its USDZ when exported (else the default), its GLB made on demand.
        made = bool(self.cache and blender() and "glb" in l["files"])
        has = [f in l["usdz_finishes"] or made or f == l["shown"] for f in fins]
        usdz = [f"model-{i}.usdz" if (f in l["usdz_finishes"] or made) and f != l["shown"] else "model.usdz" for i, f in enumerate(fins)]
        glbs = [f"model-{i}.glb" for i in range(len(fins))]
        intent = lambda f: (f"intent://arvr.google.com/scene-viewer/1.0?file={quote(base + f, safe='')}&mode=ar_preferred&title={quote(l['name'])}"
                            f"#Intent;scheme=https;package=com.google.android.googlequicksearchbox;action=android.intent.action.VIEW;"
                            f"S.browser_fallback_url={quote(base, safe='')};end;")
        # Quick Look wants the link to hold an image; Scene Viewer takes the GLB's full URL.
        icon = ("data:image/svg+xml," + quote('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'))
        ios = (f'<a class="b ios" rel="ar" href="model.usdz"><img src="{icon}" alt="">{html.escape(w["ios"])}</a>'
               if "usdz" in l["files"] else "")
        android = (f'<a class="b android" href="{html.escape(intent("model.glb"))}">{html.escape(w["android"])}</a>' if "glb" in l["files"] else "")
        cur = fins.index(l["shown"]) if l["shown"] in fins else 0
        picker = (f'<div class="fins" role="radiogroup" aria-label="{html.escape(w["finish"])}">'
                  + "".join(f'<button role="radio" aria-checked="{"true" if i == cur else "false"}" data-i="{i}">'
                            f'<span class="sw" style="background:{l["swatches"].get(f, "#2A3244")}"></span><span class="nm">{html.escape(f)}</span></button>'
                            for i, f in enumerate(fins))
                  + "</div>" if fins else "")
        nousdz = html.escape(w["nousdz"])
        data = json.dumps({"usdz": usdz, "glb": [intent(g) for g in glbs], "has": has, "cur": cur})
        return f"""<!doctype html><html lang="{l['lang']}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(w['title'].format(name=l['name']))}</title>
<style>
body{{margin:0;min-height:100vh;display:flex;flex-direction:column;justify-content:center;gap:14px;padding:28px 22px;box-sizing:border-box;
background:#0B0D11;color:#E6EBF2;font:16px/1.45 -apple-system,system-ui,sans-serif}}
h1{{margin:0;font-size:24px}} p{{margin:0;color:#A3ADBE}}
.b{{display:flex;align-items:center;justify-content:center;min-height:52px;border-radius:12px;background:#5CE1E6;color:#062A2C;
font-weight:600;text-decoration:none;font-size:17px}} .b img{{width:0;height:0}}
.fins{{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:10px}}
.fins button{{display:grid;justify-items:center;gap:8px;padding:12px 6px 10px;border-radius:14px;border:1px solid #1F2533;background:#10141C;color:#A3ADBE;font:inherit;font-size:14px}}
.fins .sw{{width:44px;height:44px;border-radius:50%;box-shadow:inset 0 0 0 1px rgba(255,255,255,.15)}}
.fins .nm{{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.fins button[aria-checked=true]{{color:#E6EBF2;border-color:#5CE1E6}} .fins button[aria-checked=true] .sw{{box-shadow:0 0 0 3px #10141C,0 0 0 5px #5CE1E6}}
.n{{font-size:13px;color:#FFB547}} .f{{font-size:13px;color:#808A9D;margin-top:8px}}
</style></head><body>
<h1>{name}</h1><p>{html.escape(w['lead'])}</p>
{picker}{ios}{android}<p class="n" id="n" hidden>{nousdz}</p>{'' if ios or android else '<p>' + html.escape(w['none']) + '</p>'}
<p class="f">{html.escape(w['foot'].format(m=MINUTES))}</p>
<script>
var D = {data};
// The button for this phone only: AR Quick Look on Apple's, Scene Viewer on Android.
var ua = navigator.userAgent, apple = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1), android = /Android/.test(ua);
if (apple) document.querySelectorAll('.android').forEach(function (e) {{ e.remove(); }});
if (android) document.querySelectorAll('.ios').forEach(function (e) {{ e.remove(); }});
function pick(i) {{
  D.cur = i;
  document.querySelectorAll('.fins button').forEach(function (b) {{ b.setAttribute('aria-checked', String(+b.dataset.i === i)); }});
  var a = document.querySelector('.ios'), g = document.querySelector('.android');
  if (a) a.href = D.usdz[i];
  if (g) g.href = D.glb[i];
  document.getElementById('n').hidden = !(apple && !D.has[i] && i !== {cur});
}}
// On an iPhone, only the finishes that have their own USDZ (and the model's own).
if (apple) document.querySelectorAll('.fins button').forEach(function (b) {{ var i = +b.dataset.i; if (!D.has[i] && i !== D.cur) b.remove(); }});
var fins = document.querySelectorAll('.fins button');
if (fins.length < 2 && document.querySelector('.fins')) {{ document.querySelector('.fins').remove(); D.usdz = []; }}
fins.forEach(function (b) {{ b.onclick = function () {{ pick(+b.dataset.i); }}; }});
if (D.usdz.length) pick(D.cur);
// One model, no finish to pick, on an iPhone: straight to Quick Look (AR is one tap there).
else if (apple && document.querySelector('.ios')) location.replace('model.usdz');
</script>
</body></html>"""
