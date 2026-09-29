"""Tabulate one bench label, or compare two.

    python3 bench/report.py baseline
    python3 bench/report.py baseline lot2      # second label compared against the first

Prints Markdown. A brief with no shipped GLB, or a GLB that could not be
measured, is printed as such — never dropped from the table.
"""
import json, sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs"
BRIEFS = {b["id"]: b for b in json.loads((RUNS.parent / "briefs.json").read_text())["briefs"]}


def load(label):
    out = {}
    for p in sorted((RUNS / label).glob("*/result.json")):
        out[p.parent.name] = json.loads(p.read_text())
    if not out:
        sys.exit(f"no results under {RUNS / label}")
    return out


def flags(brief, m):
    """Findings on one GLB, against what its brief expected."""
    f = []
    if "measure_error" in m:
        return ["NOT MEASURABLE"]
    if m.get("reimport"):
        f.append("meshopt: geometry not re-importable")
    if m.get("non_manifold_edges"):
        f.append(f"{m['non_manifold_edges']} non-manifold")
    if m.get("degenerate_faces"):
        f.append(f"{m['degenerate_faces']} degenerate")
    if m.get("z_min_m") is not None and abs(m["z_min_m"]) > 0.005:
        f.append(f"z_min {m['z_min_m']} m")
    if m.get("empty_material_slots"):
        f.append(f"{m['empty_material_slots']} empty slots")
    imgs = sum(v["images"] for v in m.get("materials", {}).values())
    compressed = {"EXT_texture_webp", "KHR_texture_basisu"} & set(m.get("extensions_used", []))
    if imgs and not compressed and m.get("bytes", 0) > 1_000_000:
        f.append(f"textures uncompressed ({round(m['bytes'] / 1e6, 1)} MB)")
    if brief["expect"].get("textures") and imgs == 0:
        f.append("no texture survived")
    if brief["expect"].get("rig") and not m.get("rigs"):
        f.append("no rig")
    for r in m.get("rigs", []):
        if r["deform_bones_without_influence"]:
            f.append(f"{r['deform_bones_without_influence']} dead bones")
        if r["unweighted_verts"]:
            f.append(f"{r['unweighted_verts']} unweighted verts")
        if r["max_influences"] > 4:
            f.append(f"{r['max_influences']} influences/vertex")
    return f or ["—"]


def row(bid, s):
    b = BRIEFS.get(bid, {"expect": {}, "path": "?"})
    tc = s.get("tool_calls", {})
    # Each MCP names its capture tools differently: ahujasid's get_viewport_screenshot,
    # the Lab server's get_screenshot_of_* and render_viewport_to_path.
    shots = sum(n for k, n in tc.items()
                if k.endswith("get_viewport_screenshot") or "screenshot_of" in k or k.endswith("render_viewport_to_path"))
    sess = (f"{s['claude_exit']} | {s['num_turns']} | {round(s['wall_s'] / 60, 1)} min | "
            f"${round(s['cost_usd_equiv'] or 0, 2)} | {sum(tc.values())} | {shots}")
    if not s["measures"]:
        return [f"| {bid} | {sess} | — | — | — | **no *_final.glb shipped** |"]
    rows = []
    for m in s["measures"]:
        kb = round(m.get("bytes", 0) / 1024, 1)
        rows.append(f"| {bid} | {sess} | `{m['file'].split('/')[-1]}` | {m.get('tris', '?')} | {kb} kB | "
                    f"{', '.join(flags(b, m))} |")
    return rows


def table(label, res):
    print(f"### {label}\n")
    print("| Brief | Exit | Turns | Wall | Cost ≈ | Tool calls | Screenshots | GLB | Tris | Size | Findings |")
    print("|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|")
    for bid, s in res.items():
        for r in row(bid, s):
            print(r)
    total = sum(s["cost_usd_equiv"] or 0 for s in res.values())
    print(f"\n{len(res)} brief(s), cost ≈ ${round(total, 2)} equivalent API.\n")


a = load(sys.argv[1])
table(sys.argv[1], a)
if len(sys.argv) > 2:
    b = load(sys.argv[2])
    table(sys.argv[2], b)
    missing = sorted(set(a) - set(b))
    if missing:
        print(f"Not run under {sys.argv[2]}: {', '.join(missing)}\n")
