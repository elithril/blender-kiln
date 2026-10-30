"""Studio stills for the film's intro, real GPU, 3840x2160 (1920x1080 at 2x)."""
import json, re, sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]
TIPS = ("compare", "download", "palette", "pin", "queue")
def btn(p, text):
    return p.locator("button", has_text=text).filter(has_not_text="x").first
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=False, args=["--window-size=1940,1200"])
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2, locale="en-US")
    ctx.add_init_script(f"""try {{ localStorage.setItem('kiln-studio:prefs', JSON.stringify({{ tutorialSeen: true }}));
      localStorage.setItem('kiln-studio:tips', JSON.stringify({json.dumps({k: True for k in TIPS})})); }} catch (e) {{}}""")
    p = ctx.new_page(); p.goto("http://127.0.0.1:8790/#generated-assets/ammo-box")
    p.wait_for_function("() => window.__studio && window.__studio.viewer.a.model && window.__studio.detail", timeout=90_000); p.wait_for_timeout(3000)
    p.screenshot(path=f"{out}/i1-lit.png")
    for mode in ("Clay", "Normals", "Wire"):
        p.get_by_role("button", name=mode, exact=True).click(); p.wait_for_timeout(1500)
        p.screenshot(path=f"{out}/i2-{mode.lower()}.png")
        if mode == "Wire": p.get_by_role("button", name=mode, exact=True).click()
    p.get_by_role("button", name="Lit", exact=True).click(); p.wait_for_timeout(1200)
    p.click("#tb-checks"); p.wait_for_timeout(1500); p.screenshot(path=f"{out}/i3-checks.png")
    p.click("#tb-notes"); p.wait_for_timeout(500)
    p.locator("button").filter(has_text=re.compile(r"^\+\s*AR$")).first.click()
    p.wait_for_function("() => [...document.querySelectorAll('button')].some(e => /✓\\s*AR/.test(e.textContent))", timeout=180_000); p.wait_for_timeout(1500)
    p.screenshot(path=f"{out}/i4-ar-made.png")
    p.get_by_role("button", name="View in AR").click(); p.wait_for_timeout(3000)
    p.screenshot(path=f"{out}/i5-qr.png")
    p.keyboard.press("Escape"); p.wait_for_timeout(600)
    p.locator("button", has_text="kiln-smith").first.click()
    p.wait_for_function("() => window.__studio.detail && window.__studio.detail.id.endsWith('kiln-smith') && window.__studio.viewer.a.model", timeout=90_000); p.wait_for_timeout(2500)
    p.screenshot(path=f"{out}/i6-mascot.png")
    ctx.close(); b.close()
print("INTRO_OK")
