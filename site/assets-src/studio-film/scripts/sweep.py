"""Studio's real Compare (split) handle dragged across the hammer: previous version on the left, current on the right.
    uvx --with playwright==1.64.0 python -I sweep.py BASE ASSET OUTDIR N"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
base, asset, out, N = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
TIPS = ("compare", "download", "palette", "pin", "queue")
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=False, args=["--window-size=1940,1200"])
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2, locale="en-US")
    ctx.add_init_script(f"""try {{ localStorage.setItem('kiln-studio:prefs', JSON.stringify({{ tutorialSeen: true }}));
      localStorage.setItem('kiln-studio:tips', JSON.stringify({json.dumps({k: True for k in TIPS})})); }} catch (e) {{}}""")
    p = ctx.new_page(); p.goto(f"{base}#{asset}")
    p.wait_for_function("(id) => window.__studio && window.__studio.viewer.a.model && window.__studio.detail && window.__studio.detail.id === id", arg=asset, timeout=90_000)
    p.wait_for_timeout(2500); p.click("#a-play"); p.wait_for_timeout(300)
    p.evaluate("() => window.__studio.setCompare('split')"); p.wait_for_timeout(3000)
    p.evaluate("() => window.__studio.viewer.seek(0.15)"); p.wait_for_timeout(800)
    stage = p.evaluate("() => { const r = window.__studio.viewer.canvas.getBoundingClientRect(); const v = window.__studio.viewer.viewRect(); return [r.left + v.x, r.top + v.y, v.w, v.h]; }")
    # the hammer's screen extent in the current model (right of the split), found by Studio's own picking
    p.evaluate("() => { window.__studio.viewer.split = 0.05; }"); p.wait_for_timeout(500)
    ext = p.evaluate("""() => { const { viewer } = window.__studio; const r = viewer.canvas.getBoundingClientRect(), v = viewer.viewRect(); let lo = 1e9, hi = -1e9;
      for (let y = v.y; y < v.y + v.h; y += 6) for (let x = v.x; x < v.x + v.w; x += 6) { const h = viewer.pick(r.left + x, r.top + y);
        if (h && String(h.object).includes('Hammer')) { lo = Math.min(lo, r.left + x); hi = Math.max(hi, r.left + x); } } return [lo, hi]; }""")
    print("STAGE", stage, "HAMMER_X", ext)
    k0 = min(0.95, (ext[1] + 60 - stage[0]) / stage[2]); k1 = max(0.05, (ext[0] - 60 - stage[0]) / stage[2])
    h = p.evaluate("() => { const r = document.querySelector('#split').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
    p.evaluate(f"() => {{ window.__studio.viewer.split = {k0}; }}"); p.wait_for_timeout(300)
    # drag the real handle, like a user
    hx = stage[0] + k0 * stage[2]
    hb = p.evaluate("() => { const r = document.querySelector('#split').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, r.width]; }")
    print("HANDLE", hb, "k", k0, k1)
    p.mouse.move(hb[0], hb[1]); p.mouse.down()
    for i in range(N):
        t = i / (N - 1); e = t * t * (3 - 2 * t)
        k = k0 + (k1 - k0) * e
        p.mouse.move(stage[0] + k * stage[2], hb[1]); p.wait_for_timeout(90)
        p.screenshot(path=str(out / f"sw_{i:03d}.png"))
    p.mouse.up()
    ctx.close(); b.close()
print("SWEEP_OK", N)
