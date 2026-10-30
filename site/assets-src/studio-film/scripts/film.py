"""Film a real Kiln Studio session: pin a note on the mascot's hammer, ask Claude, wait, show the result.
    uvx --with playwright==1.64.0 python -I film.py BASE ASSET OBJECT TEXT OUTDIR
Video in OUTDIR/video/*.webm, phase marks in OUTDIR/marks.json (seconds since the page opened)."""
import json, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

base, asset, obj, text, out = sys.argv[1:6]
out = Path(out); out.mkdir(parents=True, exist_ok=True)
VIEW = {"width": 1440, "height": 900}
TIPS = ("compare", "download", "palette", "pin", "queue")
FIND = """(name) => {
  const { viewer } = window.__studio;
  const rect = viewer.canvas.getBoundingClientRect(), v = viewer.viewRect();
  const hits = [], seen = {};
  for (let y = v.y + 4; y < v.y + v.h; y += 14) for (let x = v.x + 4; x < v.x + v.w; x += 14) {
    const px = rect.left + x, py = rect.top + y, h = viewer.pick(px, py);
    if (!h) continue;
    const k = h.object || h.mesh; seen[k] = (seen[k] || 0) + 1;
    if (String(h.object).includes(name) || String(h.mesh).includes(name)) hits.push([Math.round(px), Math.round(py)]);
  }
  hits.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  return { seen, hits: hits.length, at: hits[Math.floor(hits.length / 2)] || null };
}"""
marks, t0 = {}, None

def mark(k): marks[k] = round(time.time() - t0, 1); print("MARK", k, marks[k], flush=True)

def api(path, body=None):
    req = urllib.request.Request(base + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")

with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    ctx = browser.new_context(viewport=VIEW, device_scale_factor=1, locale="en-US",
                              record_video_dir=str(out / "video"), record_video_size=VIEW)
    ctx.add_init_script(f"""try {{
      localStorage.setItem('kiln-studio:prefs', JSON.stringify({{ tutorialSeen: true }}));
      localStorage.setItem('kiln-studio:tips', JSON.stringify({json.dumps({k: True for k in TIPS})}));
    }} catch (e) {{}}""")
    page = ctx.new_page(); t0 = time.time()
    page.goto(f"{base}#{asset}")
    page.wait_for_function("(id) => window.__studio && window.__studio.viewer.a.model && window.__studio.detail"
                           " && window.__studio.detail.id === id", arg=asset, timeout=90_000)
    page.wait_for_timeout(2500); mark("loaded")
    page.click("#a-play"); page.wait_for_timeout(1200)
    found = page.evaluate(FIND, obj)
    print("FIND", json.dumps(found), flush=True)
    if not found.get("at"):
        print("FIND_FAIL", found); sys.exit(1)
    if __import__("os").environ.get("FIND_ONLY"):
        page.screenshot(path=str(out / "find.png")); sys.exit(0)
    page.evaluate("() => window.__studio.startPin()"); page.wait_for_timeout(800)
    page.mouse.move(*found["at"], steps=25); page.wait_for_timeout(400)
    page.mouse.click(*found["at"])
    page.wait_for_selector("#composer:not([hidden])", timeout=10_000); mark("pinned")
    page.type("#composer-text", text, delay=45); page.wait_for_timeout(700)
    page.click("#composer-save")
    page.wait_for_function("() => (window.__studio.detail.counts || {}).open > 0", timeout=20_000)
    page.wait_for_timeout(1200); mark("saved")
    page.click("[data-ask-notes]", timeout=20_000); mark("asked")
    key, seen_done, proposals = f"asset:{asset}", False, []
    while time.time() - t0 < 3600:
        page.wait_for_timeout(3000)
        jobs = [j for j in api("/api/claude")["jobs"] if j.get("key") == key]
        for j in jobs:
            w = j.get("waiting") or {}
            if j["state"] == "waiting" and not w.get("answered"):
                if w.get("type") == "tool":
                    api(f"/api/claude/jobs/{j['id']}/answer", {"decision": "allow"})
                else:
                    proposals.append(w.get("question")); api("/api/claude/jobs", {"kind": "answer", "asset": asset, "text": "Yes, go ahead.", "lang": "en"})
        busy = [j for j in jobs if j["state"] in ("queued", "running", "waiting")]
        if jobs and not busy:
            if seen_done: break
            seen_done = True
        else:
            seen_done = False
    mark("done")
    page.wait_for_timeout(6000); mark("result")
    page.screenshot(path=str(out / "after.png"))
    page.wait_for_timeout(8000); mark("end")
    d = api(f"/api/asset/{quote(asset, safe='')}")
    jobs = [{k: j.get(k) for k in ("state", "cost_usd", "turns", "duration_ms", "error")} for j in api("/api/claude")["jobs"] if j.get("key") == key]
    (out / "marks.json").write_text(json.dumps({"marks": marks, "jobs": jobs, "proposals": proposals,
        "notes": [{k: n.get(k) for k in ("text", "status", "thread")} for n in d.get("notes", [])]}, indent=1, default=str))
    ctx.close(); browser.close()
print("FILM_OK", out)
