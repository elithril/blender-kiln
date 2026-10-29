"""High-res Studio stills with the real GPU (headed Chromium), for the re-cut.
    uvx --with playwright==1.64.0 python -I capture.py MODE BASE ASSET OUTDIR [NOTE_TEXT]
MODE before: the model, pin mode, the composer with the note typed, the saved open note.
MODE after: the addressed note with Claude's reply, and compare."""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
mode, base, asset, out = sys.argv[1:5]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
text = sys.argv[5] if len(sys.argv) > 5 else ""
TIPS = ("compare", "download", "palette", "pin", "queue")
T = 0.15
RECTS = """() => {
  const r = (e) => { if (!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)]; };
  const card = (txt) => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) if (n.textContent.includes(txt) && n.parentElement.closest('#composer') === null) {
      let e = n.parentElement; while (e && e !== document.body) { const cs = getComputedStyle(e); if (parseFloat(cs.borderTopWidth) > 0 && cs.borderRadius !== '0px') return e; e = e.parentElement; } }
    return null; };
  return { composer: r(document.querySelector('#composer:not([hidden])')), work: r(document.querySelector('#work')),
           ask: r(document.querySelector('[data-ask-notes]')), pins: [...document.querySelectorAll('#pins > *')].map(r),
           note: r(card('too small to read')), side: r(document.querySelector('#side, aside, .side')) };
}"""
FIND = """(name) => {
  const { viewer } = window.__studio;
  const rect = viewer.canvas.getBoundingClientRect(), v = viewer.viewRect();
  const hits = [];
  for (let y = v.y + 4; y < v.y + v.h; y += 8) for (let x = v.x + 4; x < v.x + v.w; x += 8) {
    const px = rect.left + x, py = rect.top + y, h = viewer.pick(px, py);
    if (h && (String(h.object).includes(name) || String(h.mesh).includes(name))) hits.push([Math.round(px), Math.round(py)]);
  }
  hits.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  return { hits: hits.length, at: hits[Math.floor(hits.length / 2)] || null };
}"""
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=False, args=["--window-size=1940,1200"])
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2, locale="en-US")
    ctx.add_init_script(f"""try {{ localStorage.setItem('kiln-studio:prefs', JSON.stringify({{ tutorialSeen: true }}));
      localStorage.setItem('kiln-studio:tips', JSON.stringify({json.dumps({k: True for k in TIPS})})); }} catch (e) {{}}""")
    p = ctx.new_page(); p.goto(f"{base}#{asset}")
    p.wait_for_function("(id) => window.__studio && window.__studio.viewer.a.model && window.__studio.detail && window.__studio.detail.id === id", arg=asset, timeout=90_000)
    p.wait_for_timeout(2500)
    p.click("#a-play"); p.wait_for_timeout(300)
    p.evaluate(f"() => window.__studio.viewer.seek({T})"); p.wait_for_timeout(1200)
    print("GPU", p.evaluate("() => { const g = document.createElement('canvas').getContext('webgl'); const d = g.getExtension('WEBGL_debug_renderer_info'); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : '?'; }"))
    rects = {}
    if mode == "before":
        p.screenshot(path=str(out / "s1-model.png")); rects["s1"] = p.evaluate(RECTS)
        f = p.evaluate(FIND, "SK_KilnSmith_Hammer"); print("FIND", f)
        p.evaluate("() => window.__studio.startPin()"); p.wait_for_timeout(700)
        p.mouse.move(*f["at"]); p.wait_for_timeout(500)
        p.screenshot(path=str(out / "s1-pinmode.png"))
        p.mouse.click(*f["at"]); p.wait_for_selector("#composer:not([hidden])", timeout=10_000); p.wait_for_timeout(500)
        p.screenshot(path=str(out / "s2-composer-empty.png"))
        p.fill("#composer-text", text); p.wait_for_timeout(500)
        p.screenshot(path=str(out / "s2-composer.png")); rects["s2"] = p.evaluate(RECTS)
        p.click("#composer-save")
        p.wait_for_function("() => (window.__studio.detail.counts || {}).open > 0", timeout=20_000); p.wait_for_timeout(1500)
        p.screenshot(path=str(out / "s3-note-open.png")); rects["s3"] = p.evaluate(RECTS)
        r = p.evaluate("() => { const e = document.querySelector('[data-ask-notes]'); if (!e) return null; const b = e.getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; }")
        pin = f["at"]
        (out / "geometry.json").write_text(json.dumps({"hammer_click": pin, "ask_button": r}))
        print("ASK", r)
    else:
        p.screenshot(path=str(out / "s5-after.png")); rects["s5"] = p.evaluate(RECTS)
        p.evaluate("() => window.__studio.setCompare('split')"); p.wait_for_timeout(2500)
        p.screenshot(path=str(out / "s5-compare.png"))
    (out / f"rects-{mode}.json").write_text(json.dumps(rects, indent=1)); print(json.dumps(rects))
    ctx.close(); b.close()
print("CAPTURE_OK")
