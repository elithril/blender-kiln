#!/usr/bin/env python3
"""Kiln Studio: view, annotate and iterate on 3D models in the browser.

    studio.py [open] [PROJECT] [--asset ID] [--port N] [--no-open] [--foreground]
    studio.py stop | status
    studio.py list | notes [--all] | show ASSET [--status S] [--json] | history ASSET
    studio.py reply ASSET NOTE "text" [--status addressed|open|wontfix] [--image PNG/JPG]
    studio.py log ASSET "what changed"
    studio.py snapshot ASSET [--variant LABEL] | revert ASSET
    studio.py meta ASSET [--category C] [--tags a,b]

PROJECT is any folder (default: the current one). Studio finds every .glb .gltf
.fbx .obj under it, groups kiln's _original/_final stages into one asset, and keeps
its notes in PROJECT/.kiln-studio/. `open` prints the URL of the Studio already
running for that folder, or starts one in the background — like `remotion studio`.

The other commands find the project from the current folder upwards (the first
folder holding .kiln-studio/), or take --root. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import studiolib as sl  # noqa: E402

DEFAULT_PORT = 4840
COMMANDS = ("open", "serve", "stop", "status", "list", "notes", "show", "history",
            "reply", "log", "snapshot", "revert", "meta")


# ── the server's lifecycle ───────────────────────────────────────────────────


def _hello(port: int, timeout: float = 0.6) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/hello", timeout=timeout) as r:
            data = json.loads(r.read())
            return data if data.get("app") == "kiln-studio" else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def running(project: sl.Project) -> dict | None:
    """The Studio serving this project, if one answers."""
    info = sl.read_json(project.data / "server.json", None) if project.data.exists() else None
    if info:
        hello = _hello(info["port"])
        if hello and Path(hello["root"]) == project.root:
            return info
    return None


def _free_port(start: int) -> int:
    for port in range(start, start + 50):
        if _hello(port, 0.2):
            continue  # another project's Studio
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"no free port in {start}..{start + 49}; pass --port")


def cmd_open(args) -> None:
    project = sl.Project(args.project or ".")
    if not project.root.is_dir():
        raise SystemExit(f"not a folder: {project.root}")
    if args.asset:
        args.asset = _asset(project, args.asset).id  # `--asset chair` → its full id
    info = running(project)
    if not info:
        project.ensure()
        port = args.port or _free_port(DEFAULT_PORT)
        if args.foreground:
            return serve(project, port, open_url=None if args.no_open else _url(port, args.asset))
        log = project.data / "cache" / "server.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(HERE / "studio.py"), "serve", str(project.root), "--port", str(port)]
        kw: dict = {"stdout": log.open("ab"), "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL,
                    "cwd": str(project.root)}
        if os.name == "nt":
            kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
        subprocess.Popen(cmd, **kw)
        deadline = time.monotonic() + 15
        while not (info := running(project)):
            if time.monotonic() > deadline:
                raise SystemExit(f"Studio did not start; see {log}")
            time.sleep(0.15)
        state = "started"
    else:
        state = "already running"
    url = _url(info["port"], args.asset)
    n = len(project.scan())
    print(f"Kiln Studio {state}: {url}")
    print(f"  project {project.root}  ·  {n} model{'s' * (n != 1)}  ·  notes in {sl.DATA_DIR}/")
    print("  stop it with: studio.py stop")
    if not args.no_open:
        webbrowser.open(url)


def _url(port: int, asset: str | None) -> str:
    from urllib.parse import quote
    return f"http://127.0.0.1:{port}/" + (f"#{quote(asset, safe='/')}" if asset else "")


def serve(project: sl.Project, port: int, open_url: str | None = None) -> None:
    import server
    srv, _ = server.make_server(project, port)
    port = srv.server_address[1]
    project.ensure()
    info = {"port": port, "pid": os.getpid(), "url": f"http://127.0.0.1:{port}/",
            "root": str(project.root), "started": sl.now()}
    sl.write_json(project.data / "server.json", info)

    def bye(*_):
        try:
            cur = sl.read_json(project.data / "server.json", {})
            if cur.get("pid") == os.getpid():
                (project.data / "server.json").unlink(missing_ok=True)
        finally:
            os._exit(0)

    signal.signal(signal.SIGTERM, bye)
    print(f"Kiln Studio {server.VERSION} on {info['url']} for {project.root}", flush=True)
    if open_url:
        webbrowser.open(open_url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    bye()


def cmd_serve(args) -> None:
    serve(sl.Project(args.project or "."), args.port or DEFAULT_PORT)


def cmd_stop(args) -> None:
    project = find_project(args.root)
    info = running(project)
    if not info:
        print("Kiln Studio is not running for", project.root)
        return
    try:
        os.kill(info["pid"], signal.SIGTERM)
    except OSError as e:
        raise SystemExit(f"could not stop pid {info['pid']}: {e}")
    deadline = time.monotonic() + 5  # gone before returning, so a restart gets the same port
    while _hello(info["port"], 0.2) and time.monotonic() < deadline:
        time.sleep(0.1)
    print(f"Kiln Studio stopped ({info['url']})")


def cmd_status(args) -> None:
    project = find_project(args.root)
    info = running(project)
    print(f"Kiln Studio running: {info['url']}" if info else f"Kiln Studio is not running for {project.root}")


# ── reading and answering notes ──────────────────────────────────────────────


def find_project(root: str | None) -> sl.Project:
    if root:
        return sl.Project(root)
    here = Path.cwd().resolve()
    for d in (here, *here.parents):
        if (d / sl.DATA_DIR).is_dir():
            return sl.Project(d)
    return sl.Project(here)


def _asset(project: sl.Project, asset_id: str) -> sl.Asset:
    try:
        return project.find(asset_id)
    except KeyError as e:
        raise SystemExit(str(e).strip("'\""))


def _fmt3(v) -> str:
    return "?" if not v else "(" + ", ".join(f"{x:.3f}" for x in v) + ")"


def cmd_list(args) -> None:
    project = find_project(args.root)
    cat = sl.load_catalog(project)
    rows = [sl.asset_summary(project, a, cat) for a in project.scan()]
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print(f"No models under {project.root}")
        return
    for r in rows:
        c = r["counts"]
        notes = ", ".join(f"{c[s]} {s}" for s in sl.STATUSES if c[s])
        tags = f" #{' #'.join(r['tags'])}" if r["tags"] else ""
        tris = f"{r['tris']:,} tris" if r["tris"] is not None else r["variants"][0]["ext"]
        print(f"{r['id']:40s} {tris:>12s}  [{r['category'] or '-'}]{tags}  {notes}")


def cmd_notes(args) -> None:
    project = find_project(args.root)
    rows = []
    for a in project.scan():
        c = sl.counts(sl.load_notes(project, a.id))
        if c["open"] or (args.all and any(c.values())):
            rows.append((a.id, c))
    if not rows:
        print("No open notes." if not args.all else "No notes yet.")
        return
    for aid, c in rows:
        print(f"{aid:40s} " + ", ".join(f"{c[s]} {s}" for s in sl.STATUSES if c[s]))


def cmd_show(args) -> None:
    project = find_project(args.root)
    a = _asset(project, args.asset)
    sl.observe(project, a)
    detail = sl.asset_detail(project, a, sl.load_catalog(project))
    # Numbered over every note, as the page numbers its pins: "note 3" is the same note.
    number = {n["id"]: i for i, n in enumerate(detail["notes"], 1)}
    notes = [n for n in detail["notes"]
             if (args.status and n["status"] == args.status)
             or (not args.status and (args.all or n["status"] in sl.ACTIVE))]
    if args.json:
        detail["notes"] = notes
        print(json.dumps(detail, indent=2))
        return
    hashes = {v.label: v.hash for v in a.variants}
    print(f"# {a.id}   ({detail['category'] or 'uncategorised'}"
          + (f"; tags {', '.join(detail['tags'])}" if detail["tags"] else "") + ")")
    for v in detail["variants"]:
        st = v.get("stats") or {}
        dims = st.get("dimensions_blender")
        extra = (f"  {st['tris']:,} tris" if st.get("tris") is not None else "") \
            + (f"  {dims[0]:.3f} x {dims[1]:.3f} x {dims[2]:.3f} m (Blender X x Y x Z)" if dims else "")
        print(f"model [{v['label']}]: {project.root / v['file']}  {v['size'] / 1e3:,.1f} kB{extra}")
    for key in ("blend", "log"):
        if detail[key]:
            print(f"{key + ':':6s} {project.root / detail[key]}")
    if detail["baseline"]:
        b = detail["baseline"]
        print(f"previous version (n-1): {project.root / b['file']}  [{b['variant']} {b['hash']}, {b['reason']}]")
    print(f"\n{len(notes)} note(s)" + ("" if args.all or args.status else " active (open + addressed); --all for every note"))
    for n in notes:
        ver = n.get("version", {})
        print(f"\n## {number[n['id']]}. [{n['status']}] {n['id']}  ({n['kind']}, {n.get('created', '?')}, on {ver.get('variant')} {ver.get('hash')})")
        print(n.get("text", ""))
        if hashes.get(ver.get("variant")) not in (None, ver.get("hash")):
            print("   (the model has changed since this note was made)")
        an = n.get("anchor")
        if an:
            print(f"   at Blender {_fmt3(an.get('point_blender'))} m, normal {_fmt3(an.get('normal_blender'))}")
            print(f"   object '{an.get('object', '?')}', mesh '{an.get('mesh', '?')}', "
                  f"material '{an.get('material') or '-'}', region: {an.get('region', '?')}")
        else:
            print("   whole-asset note (no pin)")
        cam = n.get("camera")
        if cam:
            print(f"   camera (Blender) at {_fmt3(cam.get('position_blender'))} looking at {_fmt3(cam.get('target_blender'))}")
        if n.get("shot"):
            print(f"   screenshot: {project.root / n['shot']}")
        for r in n.get("thread", []):
            st = f" -> {r['status']}" if r.get("status") else ""
            print(f"   > {r['by']} ({r['at']}{st}): {r['text']}")
            if r.get("shot"):
                print(f"     screenshot: {project.root / r['shot']}")


def cmd_history(args) -> None:
    project = find_project(args.root)
    a = _asset(project, args.asset)
    sl.observe(project, a)
    events = sl.load_history(project, a.id)
    notes = sl.load_notes(project, a.id)
    for n in notes:
        events.append({"type": "note", "at": n["created"], "text": n["text"], "id": n["id"], "by": n.get("by")})
        for r in n.get("thread", []):
            events.append({"type": "reply", "at": r["at"], "text": r["text"], "id": n["id"],
                           "by": r["by"], "status": r.get("status")})
    for e in sorted(events, key=lambda e: e["at"]):
        t = e["type"]
        if t == "version":
            tris = f", {e['tris']:,} tris" if e.get("tris") is not None else ""
            print(f"{e['at']}  version   {e['variant']} {e['hash']}  {e['size'] / 1e3:,.1f} kB{tris}")
        elif t == "log":
            print(f"{e['at']}  changelog {e['by']}: {e['text']}")
        elif t == "baseline":
            print(f"{e['at']}  kept      {e['variant']} {e['hash']} as the previous version ({e['reason']})")
        elif t == "revert":
            print(f"{e['at']}  reverted  to {e['variant']} {e['hash']}")
        elif t == "note":
            print(f"{e['at']}  note      {e['id']} by {e['by']}: {e['text'][:80]}")
        elif t == "reply":
            st = f" [{e['status']}]" if e.get("status") else ""
            print(f"{e['at']}  reply     {e['id']} by {e['by']}{st}: {e['text'][:80]}")


def _image(path: str | None) -> bytes | None:
    if not path:
        return None
    data = Path(path).read_bytes()
    try:
        sl.image_ext(data)
    except ValueError as e:
        raise SystemExit(f"--image: {e}")
    return data


def cmd_reply(args) -> None:
    project = find_project(args.root)
    a = _asset(project, args.asset)
    try:
        r = sl.reply(project, a, args.note, args.text, by="claude", status=args.status, shot=_image(args.image))
    except (KeyError, ValueError) as e:
        raise SystemExit(str(e).strip("'\""))
    print(f"{a.id} {args.note}: replied" + (f", status -> {args.status}" if args.status else "")
          + (f", on {r['version']['variant']} {r['version']['hash']}" if args.status == "addressed" else ""))


def cmd_log(args) -> None:
    project = find_project(args.root)
    a = _asset(project, args.asset)
    sl.log(project, a, args.text)
    print(f"{a.id}: changelog entry added")


def cmd_snapshot(args) -> None:
    project = find_project(args.root)
    a = _asset(project, args.asset)
    try:
        b = sl.take_baseline(project, a, a.variant(args.variant), reason="snapshot before an edit")
    except KeyError as e:
        raise SystemExit(str(e).strip("'\""))
    print(f"{a.id}: kept {b['variant']} {b['hash']} as the previous version ({project.root / b['file']})")


def cmd_revert(args) -> None:
    project = find_project(args.root)
    a = _asset(project, args.asset)
    try:
        b = sl.revert(project, a)
    except ValueError as e:
        raise SystemExit(str(e))
    print(f"{a.id}: {b['source']} is back to {b['hash']}; the version it replaced is now the previous one")


def cmd_meta(args) -> None:
    project = find_project(args.root)
    a = _asset(project, args.asset)
    tags = [t for t in args.tags.split(",")] if args.tags is not None else None
    entry = sl.set_meta(project, a.id, category=args.category, tags=tags)
    print(f"{a.id}: category {entry.get('category', a.default_category or '-')!r}, tags {entry.get('tags', [])}")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help")):
        argv.insert(0, "open")
    ap = argparse.ArgumentParser(prog="studio.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def p(name: str, fn, help: str, root: bool = True) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help)
        sp.set_defaults(fn=fn)
        if root:
            sp.add_argument("--root", help="the project folder (default: found from here upwards)")
        return sp

    o = p("open", cmd_open, "open Studio (start it if needed)", root=False)
    o.add_argument("project", nargs="?")
    o.add_argument("--asset", help="open on this asset")
    o.add_argument("--port", type=int)
    o.add_argument("--no-open", action="store_true", help="print the URL, do not open a browser")
    o.add_argument("--foreground", action="store_true", help="run in this process until Ctrl+C")
    s = p("serve", cmd_serve, "run the server in the foreground", root=False)
    s.add_argument("project", nargs="?")
    s.add_argument("--port", type=int)
    p("stop", cmd_stop, "stop this project's Studio")
    p("status", cmd_status, "is Studio running here?")
    p("list", cmd_list, "every model, with category, tags and note counts").add_argument("--json", action="store_true")
    p("notes", cmd_notes, "assets with open notes").add_argument("--all", action="store_true")
    sh = p("show", cmd_show, "an asset's files, stats and notes")
    sh.add_argument("asset")
    sh.add_argument("--status", choices=sl.STATUSES)
    sh.add_argument("--all", action="store_true")
    sh.add_argument("--json", action="store_true")
    p("history", cmd_history, "versions seen, changelog, notes and replies").add_argument("asset")
    r = p("reply", cmd_reply, "answer a note")
    r.add_argument("asset")
    r.add_argument("note")
    r.add_argument("text")
    r.add_argument("--status", choices=("addressed", "open", "wontfix"))
    r.add_argument("--image", help="a render to attach (JPEG/PNG), e.g. from Blender at the note's camera")
    lg = p("log", cmd_log, "add a changelog entry to the asset's history")
    lg.add_argument("asset")
    lg.add_argument("text")
    sn = p("snapshot", cmd_snapshot, "keep the current file as the previous version (n-1)")
    sn.add_argument("asset")
    sn.add_argument("--variant")
    p("revert", cmd_revert, "put the previous version back (undoable)").add_argument("asset")
    m = p("meta", cmd_meta, "set an asset's category and tags")
    m.add_argument("asset")
    m.add_argument("--category")
    m.add_argument("--tags", help="comma-separated; empty string clears")
    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except TimeoutError as e:
        raise SystemExit(f"studio.py: {e}")


if __name__ == "__main__":
    main()
