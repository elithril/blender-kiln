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
    # Each MCP names its capture tools differently: mcp-for-blender's look (get_viewport_screenshot
    # up to 2.1.3), the Lab server's get_screenshot_of_* and render_viewport_to_path.
    shots = sum(n for k, n in tc.items()
                if k.endswith(("__look", "get_viewport_screenshot", "render_viewport_to_path")) or "screenshot_of" in k)
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
    # What ran: a label mixing servers or skill commits is not one measurement.
    for k in ("mcp", "skill", "blender"):
        seen = sorted({str(s.get(k) or "?").strip() for s in res.values()})
        print(f"- {k}: {', '.join(seen)}")
    print()
    print("| Brief | Exit | Turns | Wall | Cost ≈ | Tool calls | Screenshots | GLB | Tris | Size | Findings |")
    print("|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|")
    for bid, s in res.items():
        for r in row(bid, s):
            print(r)
    total = sum(s["cost_usd_equiv"] or 0 for s in res.values())
    print(f"\n{len(res)} brief(s), cost ≈ ${round(total, 2)} equivalent API.\n")


def _main_glb(s):
    """The GLB the brief is judged on: the rigged one when there is one, else the largest."""
    ms = [m for m in s.get("measures", []) if "measure_error" not in m]
    if not ms:
        return None
    return max(ms, key=lambda m: (bool(m.get("rigs")), len(m.get("clips", [])), m.get("tris", 0)))


def extras(bid, s):
    """The fields the newer briefs record, one short string each — '' when not applicable."""
    b = BRIEFS.get(bid, {"expect": {}})
    e, sig, m = {}, s.get("signals") or {}, _main_glb(s)
    exp = b.get("expect", {})
    if exp.get("rig") or (m and m.get("rigs")):
        e["route"] = sig.get("rig_route") or "—"
        if sig.get("quadruped_tool"):
            e["route"] += " + quadruped.py"
        if m and m.get("rigs"):
            r = m["rigs"][0]
            bent = r.get("bent") or {}
            e["skin"] = (f"{m.get('skinned_mesh_objects')} skinned"
                         + (" (one skin)" if m.get("single_skin") else ""))
            e["bent"] = (f"inter {bent.get('inter_mm2')} / fold {bent.get('fold_mm2')} mm² "
                         f"({bent.get('inter_pct')} / {bent.get('fold_pct')} %)" if bent.get("status") == "ok"
                         else bent.get("status", "—"))
            e["rig"] = (f"{r['deform_bones']} deform, {r['deform_bones_without_influence']} dead, "
                        f"{r['unweighted_verts']} unweighted, p99 {r['stretch_p99']}, "
                        f"{r.get('finger_bones', 0)} finger bones")
        elif exp.get("rig"):
            e["rig"] = "no rig"
    if exp.get("clips") or (m and m.get("clips")):
        cl = (m or {}).get("clips", [])
        e["clips"] = ", ".join(f"{c['name']} {c['duration_s']}s"
                               + ("" if c["loop_closes"] else " OPEN" if c["loop_closes"] is False else " ?")
                               for c in cl) or "none"
        if exp.get("one_glb"):
            want = set(exp.get("clips", []))
            have = {c["name"].lower() for c in cl}
            e["one_glb"] = "yes" if all(any(w in h for h in have) for w in want) else "no"
        e["blink"] = "yes" if (m or {}).get("blink") else "no"
        q = (s.get("artifacts") or {}).get("quadruped-report.json") or {}
        for rep in q.values():
            if isinstance(rep, dict):
                lags = [f"{k}: ear {v.get('ear_lag_frames')} / tail {v.get('tail_tip_lag_frames')} fr"
                        for k, v in rep.items() if isinstance(v, dict)]
                e["lag"] = "; ".join(lags)
    if bid.startswith("owl") or exp.get("single_skin"):
        e["matcap"] = "yes" if sig.get("matcap_check") else "no"
    if b.get("inputs"):
        before = (s.get("input_measures") or [{}])[0]
        if m:
            e["before_after"] = (f"{before.get('tris')} → {m.get('tris')} tris, "
                                 f"{round((before.get('bytes') or 0) / 1e6, 2)} → {round(m.get('bytes', 0) / 1e6, 2)} MB, "
                                 f"non-manifold {before.get('non_manifold_edges')} → {m.get('non_manifold_edges')}, "
                                 f"boundary {before.get('boundary_edges')} → {m.get('boundary_edges')}")
    if "projection" in exp or bid.startswith("ref-"):
        pj = sig.get("projection") or {}
        ss = (s.get("artifacts") or {}).get("projection_ssim")
        e["projection"] = (("proposed" if pj.get("proposed") else "not proposed")
                           + (", ran" if pj.get("ran") else "")
                           + (f", SSIM {ss['before']} → {ss['after']}" if ss else "")
                           + (", ended on a question" if sig.get("ended_on_question") else ""))
    if b.get("print"):
        pc = s.get("print_check") or {}
        if not pc:
            e["print"] = "no STL/3MF shipped"
        else:
            parts = len(pc.get("files", {}))
            asm = (pc.get("assembly") or {}).get("assembly") or {}
            e["print"] = (f"{pc.get('verdict')}"
                          + (f" (with supports: {pc.get('verdict_with_supports')})" if pc.get("needs_supports") else "")
                          + f", {parts} file(s)"
                          + (f", overlap {asm.get('overlap_mm3')} mm³" if asm else "")
                          + f"; session's own: {(sig.get('print_check') or {}).get('verdicts') or 'none'}")
    return e


def signals_table(label, res):
    rows = [(bid, extras(bid, s)) for bid, s in res.items()]
    rows = [(bid, e) for bid, e in rows if e]
    if not rows:
        return
    print(f"#### {label} — recorded fields\n")
    print("| Brief | Field | Value |\n|---|---|---|")
    for bid, e in rows:
        for k, v in e.items():
            print(f"| {bid} | {k} | {v} |")
    print()


def compare(la, a, lb, b):
    print(f"### {la} → {lb}\n")
    print(f"| Brief | Field | {la} | {lb} |\n|---|---|---|---|")
    for bid in sorted(set(a) | set(b)):
        ea = extras(bid, a[bid]) if bid in a else {}
        eb = extras(bid, b[bid]) if bid in b else {}
        ma, mb = (_main_glb(a[bid]) if bid in a else None), (_main_glb(b[bid]) if bid in b else None)
        ea["tris"] = ma.get("tris") if ma else "—"
        eb["tris"] = mb.get("tris") if mb else "—"
        for k in dict.fromkeys(list(ea) + list(eb)):
            print(f"| {bid} | {k} | {ea.get(k, '—')} | {eb.get(k, '—')} |")
    print()


a = load(sys.argv[1])
table(sys.argv[1], a)
signals_table(sys.argv[1], a)
if len(sys.argv) > 2:
    b = load(sys.argv[2])
    table(sys.argv[2], b)
    signals_table(sys.argv[2], b)
    compare(sys.argv[1], a, sys.argv[2], b)
    missing = sorted(set(a) - set(b))
    if missing:
        print(f"Not run under {sys.argv[2]}: {', '.join(missing)}\n")
