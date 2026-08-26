"""Collect per-asset metrics into per-theme markdown tables."""
import json, os, sys

out, renders = sys.argv[1], sys.argv[2]
rows = []
with open(os.path.join(out, "metrics.jsonl")) as f:
    for line in f:
        if line.strip():
            rows.append(json.loads(line))

def kb(asset, suffix):
    p = os.path.join(out, asset, f"{asset}{suffix}")
    return os.path.getsize(p) / 1024.0 if os.path.exists(p) else None

for r in rows:
    a = r["asset"]
    r["kb_raw"] = kb(a, "_original.glb")
    r["kb_draco"] = kb(a, "_final.glb")
    r["kb_packed"] = kb(a, "_packed.glb")
    r["best"] = min(v for v in (r["kb_draco"], r["kb_packed"]) if v)

THEME_TITLES = {"forge": "Forge", "scifi": "Sci-fi modular", "nature": "Stylised nature"}
blocks, alerts = [], []

for theme in ("forge", "scifi", "nature"):
    group = [r for r in rows if r["theme"] == theme]
    if not group:
        continue
    lines = [f"#### {THEME_TITLES[theme]}", "",
             "| Asset | Object | Tris | GLB raw | + Draco | + meshopt | Saved |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for r in sorted(group, key=lambda x: -x["tris"]):
        saved = 100.0 * (1 - r["best"] / r["kb_raw"])
        packed = f"{r['kb_packed']:.1f} kB" if r["kb_packed"] else "—"
        lines.append(f"| `{r['asset']}` | `{r['object']}` | {r['tris']:,} | "
                     f"{r['kb_raw']:.1f} kB | {r['kb_draco']:.1f} kB | {packed} | "
                     f"**{saved:.0f}%** |")
    t_tris = sum(r["tris"] for r in group)
    t_raw = sum(r["kb_raw"] for r in group)
    t_best = sum(r["best"] for r in group)
    lines.append(f"| **subtotal** | | **{t_tris:,}** | **{t_raw:.1f} kB** | | | "
                 f"**{100.0 * (1 - t_best / t_raw):.0f}%** |")
    blocks.append("\n".join(lines))
    for r in group:
        if r["budget"] in ("over", "ALERT"):  # tiers are fine; only excess alerts
            alerts.append(f"- `{r['asset']}` — {r['budget_note']}")
        if r["material_audit"]:
            alerts.append(f"- `{r['asset']}` — procedural nodes would be lost: "
                          f"{r['material_audit']}")
        if not r["scale_ok"]:
            alerts.append(f"- `{r['asset']}` — scale check failed: {r['dim_m']}")

tris = sum(r["tris"] for r in rows)
raw = sum(r["kb_raw"] for r in rows)
best = sum(r["best"] for r in rows)
summary = (f"**{len(rows)} assets · {tris:,} tris · {raw:.1f} kB raw → "
           f"{best:.1f} kB after dedup/weld/Draco ({100.0 * (1 - best / raw):.0f}% smaller)**")

doc = summary + "\n\n" + "\n\n".join(blocks)
if alerts:
    doc += ("\n\n#### Budget and audit notes\n\nIron rule 4 reports, it never blocks:\n\n"
            + "\n".join(sorted(set(alerts))))
with open(os.path.join(out, "table.md"), "w") as f:
    f.write(doc + "\n")
print(doc)
