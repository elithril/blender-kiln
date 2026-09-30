"""Put each reference, the exact prompt every tool received, and what it shipped side by side.

    python3 bench/compare.py <out-name> <label> [<label> ...]     # e.g. ref-compare ref-kiln ref-img2threejs

Writes bench/results/<out-name>/index.html plus the images it shows, as WebP, with
relative paths — a static page that opens from disk and survives a copy into a
site. Only briefs that carry a "reference" in briefs.json are shown. The prompt
shown is the one the runner sent, rebuilt from the same source the runner uses,
so a reader judges the result against the actual instruction.
"""
import html, json, shutil, subprocess, sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
RUNS = BENCH / "runs"
sys.path.insert(0, str(BENCH))
import run_img2threejs as I2   # its PROMPT is the one sent

BRIEFS = {b["id"]: b for b in json.loads((BENCH / "briefs.json").read_text())["briefs"] if b.get("reference")}


def webp(src, dst, width=900):
    r = subprocess.run(["cwebp", "-quiet", "-q", "85", "-resize", str(width), "0", str(src), "-o", str(dst)])
    if r.returncode != 0:
        sys.exit(f"cwebp failed on {src}")


def prompt_for(label, result, brief):
    if result.get("tool") == "img2threejs":
        return I2.PROMPT
    return brief["prompt"].replace("<REFS>/", "") + "\n\nOutput folder (absolute): <run folder>/generated-assets"


def cell(label, res, out, bid):
    if res is None:
        return f"<td class='missing'>not run under <code>{html.escape(label)}</code></td>"
    tool = res.get("tool", "kiln")
    m = res["measures"][0] if res.get("measures") else None
    img = ""
    if m and m.get("render") and not str(m["render"]).startswith("render failed"):
        name = f"{bid}-{label}.webp"
        webp(RUNS / label / bid / m["render"], out / name)
        img = f"<img src='{name}' alt='{html.escape(tool)} result for {bid}'>"
    if m and "tris" in m:
        stats = (f"{m['tris']:,} tris · {m['bytes'] / 1e6:.2f} MB · {m['objects_mesh']} meshes · "
                 f"{m['non_manifold_edges']} fused edges")
    else:
        stats = "no GLB shipped"
    cost = res.get("cost_usd_equiv")
    if cost is None and res.get("cost_usd_equiv_estimate"):
        cost_s = f"≈ ${res['cost_usd_equiv_estimate']:.2f} (estimated, run stopped)"
    else:
        cost_s = f"${cost:.2f}" if cost is not None else "—"
    note = f"<p class='note'>{html.escape(res['note'])}</p>" if res.get("note") else ""
    return (f"<td>{img}<p class='stats'><b>{html.escape(tool)}</b> — {stats}<br>"
            f"cost {cost_s} · {round((res.get('wall_s') or 0) / 60, 1)} min · "
            f"{res.get('num_turns') or '—'} turns</p>{note}</td>")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    name, labels = sys.argv[1], sys.argv[2:]
    out = BENCH / "results" / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    rows = []
    for bid, brief in BRIEFS.items():
        results = {}
        for label in labels:
            p = RUNS / label / bid / "result.json"
            results[label] = json.loads(p.read_text()) if p.exists() else None
        if not any(results.values()):
            continue
        ref = f"{bid}-reference.webp"
        webp(RUNS / "_refs" / brief["reference"], out / ref, 600)
        prompts = "".join(
            f"<details><summary>prompt sent to <b>{html.escape(r.get('tool', 'kiln'))}</b></summary>"
            f"<pre>{html.escape(prompt_for(l, r, brief))}</pre></details>"
            for l, r in results.items() if r)
        rows.append(
            f"<tr><td class='ref'><img src='{ref}' alt='reference {bid}'>"
            f"<p class='stats'><b>reference</b> — Poly Haven <code>{html.escape(brief['reference'][:-4])}</code>, CC0</p>"
            f"{prompts}</td>" + "".join(cell(l, results[l], out, bid) for l in labels) + "</tr>")
    head = "".join(f"<th>{html.escape(l)}</th>" for l in labels)
    (out / "index.html").write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Reference comparison</title>
<style>
:root{{--bg:#16171a;--fg:#e8e6e1;--mute:#9a978f;--line:#2c2e33}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
h1{{font-size:20px;margin:0 0 4px}} .lede{{color:var(--mute);margin:0 0 20px;max-width:70ch}}
table{{border-collapse:collapse;width:100%}} th,td{{vertical-align:top;padding:12px;border-top:1px solid var(--line);text-align:left}}
th{{font-weight:600;color:var(--mute)}} img{{width:100%;max-width:520px;display:block;border-radius:6px}}
td.ref img{{max-width:260px;background:#26282d}} .stats{{font-size:13px;color:var(--mute);margin:6px 0}}
.note{{font-size:13px;color:#e0b25b;margin:4px 0}} pre{{white-space:pre-wrap;font-size:12px;background:#0f1012;padding:10px;border-radius:6px;max-width:60ch}}
details{{margin:6px 0}} summary{{cursor:pointer;font-size:13px}} .missing{{color:var(--mute)}}
</style></head><body>
<h1>Same reference image, same instruction</h1>
<p class="lede">Each row: the Poly Haven preview both tools were given, the exact prompt each received,
and the GLB each shipped, re-imported and rendered under the same studio light by the bench.
Reference images: Poly Haven (polyhaven.com), CC0, fetched through its public API.</p>
<table><tr><th>input</th>{head}</tr>{''.join(rows)}</table></body></html>""")
    print(f"wrote {out.relative_to(BENCH.parent)}/index.html ({len(rows)} rows)")


if __name__ == "__main__":
    main()
