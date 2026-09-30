// node export_glb.mjs <host dir> <out.glb> [screenshot.png]
// Serve the host on a FREE port, check that the page answering is this host,
// call window.__exportGLB, save. A fixed port once reached another app's dev
// server on this machine and waited on it for a minute — so: free port, and a
// title check before anything else.
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import net from "node:net";
const [dir, out, shot] = process.argv.slice(2);
const port = await new Promise((res) => { const s = net.createServer(); s.listen(0, () => { const p = s.address().port; s.close(() => res(p)); }); });
const vite = spawn("npx", ["vite", "--port", String(port), "--strictPort"], { cwd: dir, stdio: "ignore" });
let code = 1;
try {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1000, height: 1000 } });
  page.on("pageerror", (e) => console.error("PAGEERROR:", e.message));
  page.on("console", (m) => { if (m.type() === "error") console.error("PAGE:", m.text()); });
  for (let i = 0; i < 60; i++) { try { await page.goto(`http://localhost:${port}/`); break; } catch { await new Promise(r => setTimeout(r, 500)); } }
  if ((await page.title()) !== "bench host") throw new Error(`port ${port} is not the bench host: title "${await page.title()}"`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  await page.waitForTimeout(500);
  if (shot) await page.screenshot({ path: shot });
  const bytes = await page.evaluate(() => window.__exportGLB());
  writeFileSync(out, Buffer.from(bytes));
  console.log(`EXPORTED ${out} ${bytes.length} bytes (port ${port})`);
  await browser.close();
  code = 0;
} catch (e) {
  console.error("EXPORT FAILED:", e.message);
} finally { vite.kill(); process.exit(code); }
