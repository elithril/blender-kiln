"""Collect per-asset metrics into a markdown table and a contact-sheet manifest."""
import json, os, sys

out, renders = sys.argv[1], sys.argv[2]
rows = []
with open(os.path.join(out, "metrics.jsonl")) as f:
    for line in f:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

def kb(path):
    return os.path.getsize(path) / 1024.0 if os.path.exists(path) else None

for r in rows:
    a = r["asset"]
    r["kb_raw"] = kb(os.path.join(out, f"{a}_original.glb"))
    r["kb_draco"] = kb(os.path.join(out, f"{a}_final.glb"))
    r["kb_packed"] = kb(os.path.join(out, f"{a}_packed.glb"))

hdr = ("| Asset | Tris | GLB raw | + dedup/weld/Draco | + gltfpack (meshopt) | Saved | Render |\n"
       "|---|---:|---:|---:|---:|---:|---:|")
lines = [hdr]
for r in sorted(rows, key=lambda x: -x["tris"]):
    best = min(v for v in (r["kb_draco"], r["kb_packed"]) if v)
    saved = 100.0 * (1 - best / r["kb_raw"])
    lines.append(
        f"| `{r['asset']}` | {r['tris']:,} | {r['kb_raw']:.1f} kB | "
        f"{r['kb_draco']:.1f} kB | "
        f"{(f'{r[chr(107)+chr(98)+chr(95)+chr(112)+chr(97)+chr(99)+chr(107)+chr(101)+chr(100)]:.1f} kB') if r['kb_packed'] else '—'} | "
        f"**{saved:.0f}%** | {r['render_s']:.1f} s |")

tot_tris = sum(r["tris"] for r in rows)
tot_raw = sum(r["kb_raw"] for r in rows)
tot_best = sum(min(v for v in (r["kb_draco"], r["kb_packed"]) if v) for r in rows)
lines.append(f"| **total** | **{tot_tris:,}** | **{tot_raw:.1f} kB** | | | "
             f"**{100.0*(1-tot_best/tot_raw):.0f}%** | |")

table = "\n".join(lines)
with open(os.path.join(out, "table.md"), "w") as f:
    f.write(table + "\n")
print(table)
print()
print(json.dumps({"assets": [r["asset"] for r in sorted(rows, key=lambda x: -x['tris'])],
                  "total_tris": tot_tris, "total_raw_kb": round(tot_raw, 1),
                  "total_best_kb": round(tot_best, 1)}))
