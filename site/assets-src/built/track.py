"""The README's Built with kiln picture: the site's track, recorded frame by frame.

    npm run dev  (in site/)
    uvx --with playwright==1.64.0 --with pillow python -I site/assets-src/built/track.py docs/images/built-with-kiln.webp

Every animation of the track is paused and stepped, so one pass of the track (a seamless loop) is
cut into 144 frames, played at 12 a second: three times the site's speed, a 12 s loop. The frames
are cropped under the makers' handles (the descriptions are listed under the picture in the README)."""
import os, sys, tempfile
from PIL import Image
from playwright.sync_api import sync_playwright

out = sys.argv[1]
url = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:4321/blender-kiln/"
N, WIDTH, CROP, QUALITY = 144, 880, 345, 50
frames = []
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome")
    p = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
    p.goto(url); p.wait_for_timeout(1500)
    p.evaluate("() => document.querySelector('#built .band').scrollIntoView({ block: 'center' })"); p.wait_for_timeout(2500)
    p.evaluate("""() => { document.querySelectorAll('#built video').forEach(v => { v.pause(); v.currentTime = 2; });
      document.querySelector('header, .bar, nav')?.style.setProperty('visibility', 'hidden'); }""")
    p.mouse.move(5, 5)
    pass_ms = p.evaluate("() => parseFloat(getComputedStyle(document.querySelector('#built [data-band]')).getPropertyValue('--pass')) * 1000")
    box = p.locator("#built .band").bounding_box()
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(N):
            p.evaluate("(t) => document.querySelectorAll('#built .band *').forEach(e => e.getAnimations().forEach(a => { a.pause(); a.currentTime = t; }))", pass_ms * i / N)
            p.wait_for_timeout(40)
            f = os.path.join(tmp, f"f_{i:03d}.png")
            p.screenshot(path=f, clip={"x": 0, "y": box["y"] + 6, "width": 1280, "height": box["height"] - 6})
            im = Image.open(f).convert("RGB").crop((0, 0, 1280, CROP))
            frames.append(im.resize((WIDTH, round(CROP * WIDTH / 1280)), Image.LANCZOS))
    b.close()
frames[0].save(out, save_all=True, append_images=frames[1:], duration=83, loop=0, quality=QUALITY, method=6)
print(out, len(frames), frames[0].size, os.path.getsize(out) // 1000, "KB")
