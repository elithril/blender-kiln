import json, sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]
TIPS = ("compare", "download", "palette", "pin", "queue")
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=False, args=["--window-size=1940,1200"])
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2, locale="en-US")
    ctx.add_init_script(f"""try {{ localStorage.setItem('kiln-studio:prefs', JSON.stringify({{ tutorialSeen: true }}));
      localStorage.setItem('kiln-studio:tips', JSON.stringify({json.dumps({k: True for k in TIPS})})); }} catch (e) {{}}""")
    p = ctx.new_page(); p.goto("http://127.0.0.1:8790/#generated-assets/ammo-box")
    p.wait_for_function("() => window.__studio && window.__studio.viewer.a.model && window.__studio.detail", timeout=90_000); p.wait_for_timeout(3000)
    # a share left running by the last capture: stop it
    for t in ("Stop sharing", "Close"):
        loc = p.get_by_role("button", name=t)
        if loc.count() and loc.first.is_visible(): loc.first.click(); p.wait_for_timeout(500)
    p.get_by_role("button", name="Clay", exact=True).click(); p.wait_for_timeout(800)
    p.get_by_role("button", name="Wire", exact=True).click(); p.wait_for_timeout(1500)
    p.screenshot(path=f"{out}/i2-wire.png")
    p.get_by_role("button", name="Wire", exact=True).click(); p.get_by_role("button", name="Lit", exact=True).click(); p.wait_for_timeout(800)
    p.evaluate("() => window.__studio.openAsset('generated-assets/kiln-smith')")
    p.wait_for_function("() => window.__studio.detail && window.__studio.detail.id.endsWith('kiln-smith') && window.__studio.viewer.a.model", timeout=90_000); p.wait_for_timeout(2500)
    p.screenshot(path=f"{out}/i6-mascot.png")
    print("QR_RECT", p.evaluate("() => null"))
    ctx.close(); b.close()
print("FIX_OK")
