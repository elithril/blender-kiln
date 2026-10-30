"""The Studio page, driven the way a user drives it: headless Chromium through Playwright.

    uvx --with playwright==1.64.0 python -I bench/studio_page.py URL ASSET OBJECT TEXT SHOTS STOP

Opens the model, starts a pin, clicks the screen point where OBJECT shows (a point the page's
own picking says lands on OBJECT), types TEXT, saves, presses "Work on it with Claude" and
prints `STUDIO_PAGE {...}`. Then stays open, as a user's page does, until the file STOP exists:
a last screenshot, `STUDIO_PAGE_AFTER {...}`. PNGs go into SHOTS (the release's visuals come
from there).

Run by studio_drive.py, never by the session under test.
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEW = {"width": 1440, "height": 900}
TIPS = ("compare", "download", "palette", "pin", "queue")   # every tip('…') of static/app.js

# Screen points where OBJECT shows: vertices of its meshes, projected, kept only when the
# page's picking (the same code a click runs) reports OBJECT there.
FIND = """(name) => {
  const { viewer } = window.__studio;
  const V = viewer.raycaster.ray.origin.constructor;
  let root = null;
  viewer.a.model.traverse((o) => { if (!root && (o.name === name || o.userData.name === name)) root = o; });
  if (!root) return { error: `no object ${name} in the page's model` };
  const rect = viewer.canvas.getBoundingClientRect(), v = viewer.viewRect();
  const pts = [];
  root.traverse((m) => {
    const pos = m.isMesh && m.geometry.attributes.position;
    if (!pos) return;
    const step = Math.max(1, Math.floor(pos.count / 400));
    for (let i = 0; i < pos.count; i += step) {
      const p = new V().fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld).project(viewer.camera);
      pts.push([rect.left + v.x + (p.x + 1) / 2 * v.w, rect.top + v.y + (1 - p.y) / 2 * v.h]);
    }
  });
  // Nudged toward the object's screen centre: an exact silhouette vertex can miss by a pixel.
  const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length, cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
  const hits = [];
  for (const [x, y] of pts) {
    const px = x + Math.sign(cx - x) * 2, py = y + Math.sign(cy - y) * 2;
    const h = viewer.pick(px, py);
    if (h && (h.object === name || h.mesh === name)) hits.push([Math.round(px), Math.round(py)]);
  }
  hits.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  return { candidates: pts.length, hits: hits.length, at: hits[Math.floor(hits.length / 2)] || null };
}"""


def open_page(pw, url, asset):
    browser = pw.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    page = browser.new_page(viewport=VIEW, device_scale_factor=2, locale="en-US")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # A user who has been here before: tutorial offer and tips already dismissed (they would
    # cover the screenshots). Nothing else of the page's state is set.
    page.add_init_script(f"""try {{
      localStorage.setItem('kiln-studio:prefs', JSON.stringify({{ tutorialSeen: true }}));
      localStorage.setItem('kiln-studio:tips', JSON.stringify({json.dumps({k: True for k in TIPS})}));
    }} catch (e) {{}}""")
    page.goto(f"{url}#{asset}")
    page.wait_for_function("(id) => window.__studio && window.__studio.viewer.a.model && window.__studio.detail"
                           " && window.__studio.detail.id === id", arg=asset, timeout=60_000)
    page.wait_for_timeout(1500)   # the first frames, the panels settling
    return browser, page, errors


def session(url, asset, obj, text, shots, stop):
    """The note and the ask, then the page left open while Claude works — as a user leaves it:
    the session turns it to the note's camera and opens Compare through Studio, which needs an
    open page. Ends when the driver creates STOP, with a last screenshot of the live page."""
    with sync_playwright() as pw:
        browser, page, errors = open_page(pw, url, asset)
        page.screenshot(path=str(shots / "01-model.png"))
        found = page.evaluate(FIND, obj)
        if not found.get("at"):
            report({"error": found.get("error") or f"{obj} shows nowhere a click reaches it", "find": found,
                    "page_errors": errors})
            return
        page.evaluate("() => window.__studio.startPin()")
        page.mouse.click(*found["at"])
        page.wait_for_selector("#composer:not([hidden])", timeout=10_000)
        page.fill("#composer-text", text)
        page.screenshot(path=str(shots / "02-note-draft.png"))
        page.click("#composer-save")
        page.wait_for_function("() => (window.__studio.detail.counts || {}).open > 0", timeout=20_000)
        n = page.evaluate("() => window.__studio.detail.notes.at(-1)")
        page.wait_for_timeout(500)
        page.screenshot(path=str(shots / "03-note-saved.png"))
        if not os.environ.get("STUDIO_PAGE_NO_ASK"):   # a free test of the page stops here
            page.click("[data-ask-notes]", timeout=20_000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(shots / "04-asked.png"))
        report({"find": found, "note": {k: n.get(k) for k in ("id", "kind", "text", "anchor", "camera", "version")},
                "page_errors": list(errors)})
        # Waiting with Playwright's own wait, not a blocking read: the page's events keep flowing.
        while not stop.exists():
            page.wait_for_timeout(1000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(shots / "05-after.png"))
        d = page.evaluate("() => window.__studio.detail")
        report({"counts": d.get("counts"), "page_errors": errors}, "STUDIO_PAGE_AFTER")
        browser.close()


def report(out, tag="STUDIO_PAGE"):
    print(f"{tag} " + json.dumps(out), flush=True)


if __name__ == "__main__":
    url, asset, obj, text, shots, stop = sys.argv[1:7]
    shots = Path(shots)
    shots.mkdir(parents=True, exist_ok=True)
    try:
        session(url, asset, obj, text, shots, Path(stop))
    except Exception as e:   # a page that would not do it is a finding: report it, never hang
        report({"error": f"{type(e).__name__}: {e}"})
