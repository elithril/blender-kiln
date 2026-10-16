#!/usr/bin/env python3
"""kiln-studio: a small MCP server (stdio) that lets Claude see what the user has open in
Kiln Studio and answer their notes. Shipped with the plugin (`.mcp.json` at its root).

Read-only, but for note replies:

- get_selection   the model, stage, camera and highlighted note the open Studio page shows
                  (the page reports them to the Studio server);
- get_notes       an asset's notes, as `studio.py show` gives them (or the assets with notes);
- reply_to_note   answer a note, as `studio.py reply` (never "resolved": only the user closes);
- set_camera      turn the open page's view: a preset, a note's own view, or a camera
                  position and target in Blender's frame.

The project is the first folder holding `.kiln-studio/` from KILN_STUDIO_ROOT, else
CLAUDE_PROJECT_DIR, else the current folder, upwards; each tool also takes `root`.
Standard library only. MCP over stdio: one JSON-RPC message per line.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import studiolib as sl  # noqa: E402

SERVER = {"name": "kiln-studio", "version": "1.0.0"}
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
ROOT_ARG = {"type": "string", "description": "The project folder (default: found from the session's folder upwards)"}

TOOLS = [
    {
        "name": "get_selection",
        "description": ("What the user has open in Kiln Studio right now: the model (asset id), its stage, "
                        "the camera (Blender frame: metres, Z up, front -Y), the note they picked, and whether "
                        "they compare. Use it when the user says \"this model\", \"here\" or \"this note\"."),
        "inputSchema": {"type": "object", "properties": {"root": ROOT_ARG}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "get_notes",
        "description": ("The user's notes on one model: number, text, status, the pinned point in Blender "
                        "coordinates with the object, material and bone hit, the camera, the pictures (absolute "
                        "paths: read them) and the thread. Without an asset: the models with notes, and their counts."),
        "inputSchema": {"type": "object", "properties": {
            "asset": {"type": "string", "description": "Asset id or unambiguous name; default: the one open in Studio"},
            "all": {"type": "boolean", "description": "Closed notes too (resolved, won't fix)"},
            "root": ROOT_ARG}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "reply_to_note",
        "description": ("Answer a note in Studio, as Claude. status \"addressed\" only once the changed model is "
                        "exported; \"wontfix\" when the user agreed; none to keep it open (a question). Never "
                        "\"resolved\": only the user closes a note."),
        "inputSchema": {"type": "object", "properties": {
            "asset": {"type": "string"}, "note": {"type": "string", "description": "The note's id (n_…) or its number"},
            "text": {"type": "string", "description": "What changed, in a sentence or two"},
            "status": {"type": "string", "enum": ["addressed", "open", "wontfix"]},
            "root": ROOT_ARG}, "required": ["asset", "note", "text"], "additionalProperties": False},
        "annotations": {"readOnlyHint": False, "destructiveHint": False},
    },
    {
        "name": "set_camera",
        "description": ("Turn the view in the open Studio page, to show the user something: a preset view, a "
                        "note's own view, or a camera position and target in Blender coordinates (metres, Z up). "
                        "With an asset, the page opens that model first."),
        "inputSchema": {"type": "object", "properties": {
            "asset": {"type": "string"},
            "view": {"type": "string", "enum": ["front", "back", "left", "right", "top", "iso"]},
            "note": {"type": "string", "description": "A note's id or number: its own camera"},
            "position_blender": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
            "target_blender": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
            "root": ROOT_ARG}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True},
    },
]


class ToolError(Exception):
    pass


def find_project(root: str | None) -> sl.Project:
    if root:
        return sl.Project(root)
    for start in (os.environ.get("KILN_STUDIO_ROOT"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
        if not start:
            continue
        here = Path(start).resolve()
        for d in (here, *here.parents):
            if (d / sl.DATA_DIR).is_dir():
                return sl.Project(d)
    raise ToolError("No Kiln Studio project here: no .kiln-studio/ folder from this folder upwards. "
                    "Start Studio with `/kiln studio`, or pass root.")


def studio_url(project: sl.Project) -> str:
    info = sl.read_json(project.data / "server.json", None)
    if not info:
        raise ToolError(f"Kiln Studio is not running for {project.root}: start it with `studio.py open`.")
    return f"http://127.0.0.1:{info['port']}"


def call_studio(project: sl.Project, path: str, body: dict | None = None) -> dict:
    url = studio_url(project) + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                 headers={"Connection": "close", **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("error", str(e))
        except ValueError:
            msg = str(e)
        raise ToolError(f"Studio said: {msg}")
    except (OSError, ValueError) as e:
        raise ToolError(f"Kiln Studio does not answer at {url} ({e}): it may have stopped; `studio.py open` restarts it.")


def _asset(project: sl.Project, asset: str | None) -> sl.Asset:
    if not asset:
        sel = call_studio(project, "/api/selection").get("selection") or {}
        asset = sel.get("asset")
        if not asset:
            raise ToolError("No asset given, and no model open in Studio.")
    try:
        return project.find(asset)
    except KeyError as e:
        raise ToolError(str(e).strip("'\""))


def _note_id(project: sl.Project, a: sl.Asset, note: str) -> str:
    notes = sl.load_notes(project, a.id)
    n = str(note).strip().lstrip("#")
    if n.isdigit():
        i = int(n)
        if 1 <= i <= len(notes):
            return notes[i - 1]["id"]
        raise ToolError(f"{a.id} has {len(notes)} notes; there is no note {i}")
    if any(x["id"] == n for x in notes):
        return n
    raise ToolError(f"no note {n} on {a.id}")


def get_selection(args: dict) -> dict:
    project = find_project(args.get("root"))
    out = call_studio(project, "/api/selection")
    sel = out.get("selection")
    if not sel:
        return {"open_pages": out.get("pages", 0), "selection": None,
                "note": "No Studio page has reported what it shows yet." if out.get("pages") else
                        "No Studio page is open: the user is not looking at a model in Studio now."}
    note = None
    if sel.get("asset") and sel.get("note"):
        try:
            a = project.find(sel["asset"])
            n = next((x for x in sl.load_notes(project, a.id) if x["id"] == sel["note"]["id"]), None)
            if n:
                note = {"id": n["id"], "number": sel["note"].get("number"), "status": n["status"], "text": n["text"]}
        except KeyError:
            pass
    cam = sel.get("camera") or {}
    return {"open_pages": out.get("pages", 0), "seen_seconds_ago": sel.get("age_s"),
            "asset": sel.get("asset"), "stage": sel.get("variant"), "highlighted_note": note,
            "camera_blender": {"position": cam.get("position_blender"), "target": cam.get("target_blender"),
                               "fov_deg": cam.get("fov")} if cam else None,
            "comparing_with": sel.get("compare"), "shading": sel.get("shading"),
            "project": str(project.root)}


def _pictures(project: sl.Project, n: dict) -> dict:
    ab = lambda rel: str(project.root / rel) if rel else None
    out = {"screenshot": ab(n.get("shot")), "close_up": ab(n.get("detail"))}
    return {k: v for k, v in out.items() if v}


def get_notes(args: dict) -> dict:
    project = find_project(args.get("root"))
    if not args.get("asset"):
        try:
            sel = call_studio(project, "/api/selection").get("selection") or {}
        except ToolError:
            sel = {}
        if not sel.get("asset"):
            rows = []
            for a in project.scan():
                c = sl.counts(sl.load_notes(project, a.id))
                if any(c.values()):
                    rows.append({"asset": a.id, **c})
            return {"project": str(project.root), "assets_with_notes": rows}
        args = {**args, "asset": sel["asset"]}
    a = _asset(project, args["asset"])
    notes = sl.load_notes(project, a.id)
    cur = {v.label: v.hash or sl.file_hash(v.path) for v in a.variants}
    out = []
    for i, n in enumerate(notes, 1):
        if not args.get("all") and n["status"] not in sl.ACTIVE:
            continue
        an = n.get("anchor") or {}
        ver = n.get("version") or {}
        out.append({
            "number": i, "id": n["id"], "status": n["status"], "text": n["text"], "created": n["created"],
            "kind": n.get("kind"),
            "pin": {k: an.get(k) for k in ("point_blender", "normal_blender", "object", "mesh", "material", "bone", "region") if an.get(k) is not None} or None,
            "camera_blender": {"position": (n.get("camera") or {}).get("position_blender"),
                               "target": (n.get("camera") or {}).get("target_blender")} if n.get("camera") else None,
            "made_on": ver, "on_an_earlier_version": bool(ver.get("hash") and cur.get(ver.get("variant")) not in (None, ver.get("hash"))),
            "pictures": _pictures(project, n),
            "thread": [{"by": r["by"], "at": r["at"], "status": r.get("status"), "text": r["text"],
                        **({"after_pictures": _pictures(project, r)} if r.get("shot") else {})} for r in n.get("thread", [])],
        })
    return {"asset": a.id, "files": [v.rel for v in a.variants], "log": a.log_file(), "blend": a.blend_file(),
            "counts": sl.counts(notes), "notes": out}


def reply_to_note(args: dict) -> dict:
    project = find_project(args.get("root"))
    a = _asset(project, args["asset"])
    status = args.get("status") or None
    if status not in (None, "addressed", "open", "wontfix"):
        raise ToolError("status is addressed, open or wontfix; only the user resolves a note")
    text = str(args.get("text", "")).strip()
    if not text:
        raise ToolError("a reply needs text")
    nid = _note_id(project, a, args["note"])
    try:
        entry = sl.reply(project, a, nid, text, by="claude", status=status)
    except (KeyError, ValueError) as e:
        raise ToolError(str(e).strip("'\""))
    return {"asset": a.id, "note": nid, "status": status or "unchanged", "reply": entry["id"],
            "on": entry.get("version"),
            "next": "The page renders the after view itself once the note is addressed." if status == "addressed" else None}


def set_camera(args: dict) -> dict:
    project = find_project(args.get("root"))
    body: dict = {}
    a = None
    if args.get("asset"):
        a = _asset(project, args["asset"])
        body["asset"] = a.id
    if args.get("view"):
        body["view"] = args["view"]
    elif args.get("note"):
        a = a or _asset(project, None)
        body["asset"] = a.id
        body["note"] = _note_id(project, a, args["note"])
    else:
        body["position_blender"], body["target_blender"] = args.get("position_blender"), args.get("target_blender")
    out = call_studio(project, "/api/camera", body)
    return {"sent": True, "pages": out.get("pages"), **{k: v for k, v in out.items() if k != "pages"}}


HANDLERS = {"get_selection": get_selection, "get_notes": get_notes, "reply_to_note": reply_to_note, "set_camera": set_camera}


def handle(msg: dict) -> dict | None:
    """One JSON-RPC message in, its answer out (None for a notification)."""
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:   # a notification: notifications/initialized, cancelled, …
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    if method == "initialize":
        want = params.get("protocolVersion")
        return ok({"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                   "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER,
                   "instructions": "Kiln Studio: what the user looks at (get_selection), their notes "
                                   "(get_notes), your answers (reply_to_note), and turning their view (set_camera)."})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        fn = HANDLERS.get(params.get("name"))
        if not fn:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {params.get('name')!r}"}}
        try:
            result = fn(params.get("arguments") or {})
            return ok({"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}],
                       "structuredContent": result, "isError": False})
        except ToolError as e:
            return ok({"content": [{"type": "text", "text": str(e)}], "isError": True})
        except Exception as e:  # a bug here must not kill the session's server
            return ok({"content": [{"type": "text", "text": f"kiln-studio: {type(e).__name__}: {e}"}], "isError": True})
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"no method {method!r}"}}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            out = handle(msg) if isinstance(msg, dict) else {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "batches are not supported"}}
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
