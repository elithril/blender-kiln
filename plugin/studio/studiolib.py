"""Kiln Studio: project scan, model stats, and the review store.

Standard library only. Shared by the server (server.py) and the CLI (studio.py).

A project is any folder. Studio finds every model under it (.glb .gltf .fbx .obj)
and groups them into assets:

- kiln's layout — `wooden-chair/wooden-chair_{original,clean,textured,optimized,final}.glb`
  beside `wooden-chair.blend` and `wooden-chair_log.md` — is one asset whose stages
  are its variants;
- any other model file is an asset of its own; the same stem in several formats
  (`chair.glb`, `chair.fbx`) is one asset with one variant per format.

Everything Studio writes lives in `<project>/.kiln-studio/`:

    catalog.json                    categories and tags, per asset
    assets/<key>/notes.json         notes, with their threads
    assets/<key>/history.json       versions seen (hash, size, tris) + changelog
    assets/<key>/shots/             a screenshot per note, and per "addressed" reply
    assets/<key>/live.json          the build kiln is running: its phases, step by step
    baseline/<key>/                 ONE previous copy of the model (n-1), git-ignored
    cache/thumbs/<key>/<hash>.webp  a small render of each version seen, git-ignored
    cache/server.log
    server.json                     the running server's port and pid, git-ignored

<key> is the asset id with "/" replaced by "~" (a literal "~" or "%" is escaped),
so the folder name stays readable.
Coordinates: three.js/glTF is Y-up with the model front on +Z; notes also carry
Blender coordinates (x, -z, y), front on -Y, Z up, which is what kiln models in.
"""

from __future__ import annotations

import filecmp
import fnmatch
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import struct
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

DATA_DIR = ".kiln-studio"
MODEL_EXTS = (".glb", ".gltf", ".fbx", ".obj", ".usdz", ".3mf", ".stl")
# kiln's pipeline stages, best first: the default variant is the most finished one.
KILN_STAGES = ("final", "optimized", "textured", "clean", "original", "preview", "print", "game", "ar")
# preview: a copy of original, for Quick Look. print, game, ar: the outputs, each in its folder.
# The scratch export kiln writes after each phase while it builds: first while it is the
# newest file of the asset (the build is under way), last once a real stage is newer.
LIVE = "live"
FORMAT_ORDER = (".glb", ".gltf", ".fbx", ".obj", ".usdz", ".3mf", ".stl")
STAGE_RE = re.compile(r"^(?P<name>.+)_(?P<stage>" + "|".join(KILN_STAGES + (LIVE,)) + r")$")
# The printable output's parts beside {name}_print.3mf: {name}_print_{part}.stl, side files of the model.
PRINT_PART_RE = re.compile(r"^(?P<name>.+)_print_[^_/]+$")
# A model's outputs, one folder per use in its own folder: web/{name}_final.glb,
# game/{name}_game.fbx, ar/{name}_ar.usdz + .glb, print/{name}_print.3mf + _print_{part}.stl.
OUTPUT_DIRS = ("web", "game", "ar", "print")
# kiln's phases, in pipeline order; rig and animate only show when a build reports them.
PHASES = ("config", "brief", "source", "import", "cleanup", "texture", "rig", "animate", "optimize", "export")
OPTIONAL_PHASES = ("rig", "animate")
PHASE_ALIASES = {"texturing": "texture", "5b": "texture", "rigging": "rig", "5c": "rig",
                 "animation": "animate", "5d": "animate", "opt": "optimize", "sourcing": "source",
                 "create": "source", "creation": "source", "model": "source", "modeling": "source"}
# Unity's Library/ and Temp/ hold thousands of cached imports, never source models.
SKIP_DIRS = {"node_modules", "__pycache__", "venv", "site-packages", "Library", "Temp"}
STATUSES = ("open", "addressed", "resolved", "wontfix")
ACTIVE = ("open", "addressed")
NOTE_ID_RE = re.compile(r"^n_[a-z0-9]{6,16}$")
REPLY_ID_RE = re.compile(r"^r_[a-z0-9]{6,16}$")
SIDE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".md", ".txt", ".json", ".yaml", ".yml", ".blend", ".py")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    # Time-sortable, short, and unique enough for one person's notes.
    t = format(int(time.time() * 1000), "x")[-8:]
    return f"{prefix}_{t}{secrets.token_hex(2)}"


def asset_key(asset_id: str) -> str:
    # Readable and unambiguous: "a/b" -> "a~b", while a literal "~" or "%" is escaped.
    return asset_id.replace("%", "%25").replace("~", "%7E").replace("/", "~")


# ── project ──────────────────────────────────────────────────────────────────


class Project:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.data = self.root / DATA_DIR

    # paths
    def asset_dir(self, asset_id: str) -> Path:
        return self.data / "assets" / asset_key(asset_id)

    def baseline_dir(self, asset_id: str) -> Path:
        return self.data / "baseline" / asset_key(asset_id)

    def rel(self, p: Path) -> str:
        return Path(p).resolve().relative_to(self.root).as_posix()

    def inside(self, rel: str) -> Path:
        """Resolve a project-relative path, refusing anything outside the project."""
        # Checked before resolving: on Windows, resolving "\\host\share" alone opens
        # an SMB connection, which would hand the user's NTLM hash to that host.
        if "\\" in rel or re.match(r"^[A-Za-z]:", rel) or rel.startswith("/") or "\0" in rel:
            raise ValueError(f"not a project path: {rel!r}")
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"outside the project: {rel!r}")
        return p

    def ensure(self) -> None:
        if (self.data / ".gitignore").exists():
            return
        self.data.mkdir(parents=True, exist_ok=True)
        # Notes, screenshots and version renders are worth committing with the
        # models; the baseline copy, the cache and the pid file are not.
        (self.data / ".gitignore").write_text("baseline/\ncache/\nserver.json\n*.lock\n*.tmp\n")

    def config(self) -> dict:
        p = self.data / "config.json"
        try:
            data = json.loads(p.read_text()) if p.exists() else {}
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def settings(self) -> dict:
        """The project's settings (CONFIG_KEYS) with their defaults filled in. What a model is
        for comes from the project when it says, else from the user's default for every
        project (~/.kiln-studio/defaults.json), else the web."""
        return {**CONFIG_DEFAULTS, "target": user_defaults()["target"], **clean_config(self.config())}

    def target_source(self) -> str:
        return "project" if "target" in clean_config(self.config()) else "default"

    # scanning
    def scan(self) -> list["Asset"]:
        return scan(self)

    def find(self, asset_id: str) -> "Asset":
        for a in self.scan():
            if a.id == asset_id:
                return a
        # Accept a bare name when it is unambiguous: `/kiln studio wooden-chair`.
        hits = [a for a in self.scan() if a.name == asset_id or a.id.endswith("/" + asset_id)]
        if len(hits) == 1:
            return hits[0]
        if hits:
            raise KeyError(f"{asset_id!r} is ambiguous: {', '.join(a.id for a in hits)}")
        raise KeyError(f"no asset {asset_id!r} under {self.root}")


@dataclass
class Variant:
    label: str          # kiln stage ("final") or format ("glb")
    path: Path
    rel: str
    size: int
    mtime: float
    hash: str = ""

    def to_json(self) -> dict:
        return {"label": self.label, "file": self.rel, "size": self.size,
                "mtime": self.mtime, "hash": self.hash, "ext": self.path.suffix.lower()}


@dataclass
class Asset:
    id: str
    name: str
    folder: str                          # project-relative folder holding the files
    kiln: bool                           # kiln's stage layout
    variants: list[Variant] = field(default_factory=list)
    files: list[str] = field(default_factory=list)   # side files: .blend, log, images

    @property
    def primary(self) -> Variant:
        return self.variants[0]

    def variant(self, label: str | None) -> Variant:
        if not label:
            return self.primary
        for v in self.variants:
            if v.label == label or v.rel == label:
                return v
        raise KeyError(f"{self.id} has no variant {label!r} "
                       f"(has {', '.join(v.label for v in self.variants)})")

    @property
    def default_category(self) -> str:
        # A kiln asset folder's parent (the output folder, or the batch folder);
        # for a loose file, its own folder.
        folder = str(Path(self.folder).parent) if self.kiln else self.folder
        return "" if folder in (".", "") else folder

    def log_file(self) -> str | None:
        return next((f for f in self.files if f.endswith("_log.md")), None)

    def blend_file(self) -> str | None:
        return next((f for f in self.files if f.endswith(".blend")), None)


# ── project settings: .kiln-studio/config.json ───────────────────────────────
# Shared with Claude: the skill reads live_view, auto_open and target as CONFIG's
# defaults (references/studio.md § 9), the server reads exclude and target.

TARGETS = ("web", "desktop", "print")
BLENDER_MCPS = ("ahujasid", "lab")
RESERVED_PORT = 9876   # the usual Blender MCP port: the user's own Blender, never the worker's
CONFIG_DEFAULTS = {"live_view": True, "auto_open": True, "exclude": [], "target": "web",
                   # The Claude worker (worker.py): off until the user turns it on; its own
                   # Blender's port, and which Blender MCP server drives it.
                   "claude_worker": False, "blender_port": 9877, "blender_mcp": "ahujasid",
                   # How Claude's tool calls are approved (ask: the safe list passes, the rest
                   # waits for the user; auto: Claude Code's auto mode decides, paid generation
                   # still asks), how many runs at once (each its own Blender, ports from
                   # blender_port up), the model ("" = Claude Code's default), and the cap per
                   # request when running on an API key.
                   "claude_approvals": "ask", "claude_parallel": 1, "claude_model": "", "claude_budget_usd": 2.0,
                   # Paid generation (Hyper3D Rodin, Hunyuan3D…): ask each time, or let it through.
                   "claude_paid": "ask",
                   # Studio's Blender opens behind the other windows, without taking focus.
                   "blender_behind": True}
CLAUDE_APPROVALS = ("ask", "auto", "all")   # claude_paid takes ask or auto only


def user_dir() -> Path:
    """The user's own Studio folder, for every project on this computer."""
    return Path(os.environ.get("KILN_STUDIO_HOME") or "~/.kiln-studio").expanduser()


def user_defaults() -> dict:
    d = read_json(user_dir() / "defaults.json", {}) or {}
    return {"target": d.get("target") if d.get("target") in TARGETS else "web"}


def save_user_defaults(**kw) -> dict:
    if "target" in kw and kw["target"] not in TARGETS:
        raise ValueError(f"target must be one of {', '.join(TARGETS)}")
    cur = {**user_defaults(), **kw}
    user_dir().mkdir(parents=True, exist_ok=True)
    write_json(user_dir() / "defaults.json", cur)
    return cur
MAX_PARALLEL = 4
MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9.\-\[\]]{0,63}$")


def _parallel_ok(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= MAX_PARALLEL


def _budget_ok(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0.1 <= v <= 100


def _port_ok(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and 1024 <= v <= 65535 and v != RESERVED_PORT


def clean_config(data: dict) -> dict:
    """The known keys, of the right type; anything else is left out (but kept on disk)."""
    out: dict = {}
    for k in ("live_view", "auto_open", "claude_worker", "blender_behind"):
        if isinstance(data.get(k), bool):
            out[k] = data[k]
    if _port_ok(data.get("blender_port")):
        out["blender_port"] = data["blender_port"]
    if data.get("blender_mcp") in BLENDER_MCPS:
        out["blender_mcp"] = data["blender_mcp"]
    if data.get("claude_approvals") in CLAUDE_APPROVALS:
        out["claude_approvals"] = data["claude_approvals"]
    if data.get("claude_paid") in ("ask", "auto"):
        out["claude_paid"] = data["claude_paid"]
    if _parallel_ok(data.get("claude_parallel")):
        out["claude_parallel"] = data["claude_parallel"]
    if isinstance(data.get("claude_model"), str) and (data["claude_model"] == "" or MODEL_RE.match(data["claude_model"])):
        out["claude_model"] = data["claude_model"]
    if _budget_ok(data.get("claude_budget_usd")):
        out["claude_budget_usd"] = float(data["claude_budget_usd"])
    ex = data.get("exclude")
    if isinstance(ex, list):
        out["exclude"] = [str(x).strip() for x in ex if str(x).strip()][:200]
    if data.get("target") in TARGETS:
        out["target"] = data["target"]
    return out


def save_config(project: "Project", updates: dict) -> dict:
    """Change some settings. Unknown keys and bad values are refused; keys the file has
    that Studio does not know are kept as they are."""
    for k, v in updates.items():
        if k not in CONFIG_DEFAULTS:
            raise ValueError(f"unknown setting {k!r} (known: {', '.join(CONFIG_DEFAULTS)})")
        if k in ("live_view", "auto_open", "claude_worker", "blender_behind") and not isinstance(v, bool):
            raise ValueError(f"{k} must be true or false")
        if k == "blender_port" and not _port_ok(v):
            raise ValueError(f"blender_port must be a port from 1024 to 65535, not {RESERVED_PORT} "
                             "(the usual Blender MCP port, kept for your own Blender)")
        if k == "blender_mcp" and v not in BLENDER_MCPS:
            raise ValueError(f"blender_mcp must be one of {', '.join(BLENDER_MCPS)}")
        if k == "claude_approvals" and v not in CLAUDE_APPROVALS:
            raise ValueError("claude_approvals must be ask, auto or all")
        if k == "claude_paid" and v not in ("ask", "auto"):
            raise ValueError("claude_paid must be ask or auto")
        if k == "claude_parallel" and not _parallel_ok(v):
            raise ValueError(f"claude_parallel must be 1 to {MAX_PARALLEL}")
        if k == "claude_model" and not (isinstance(v, str) and (v == "" or MODEL_RE.match(v))):
            raise ValueError("claude_model is an alias (opus, sonnet…) or a model's full name, or empty for the default")
        if k == "claude_budget_usd" and not _budget_ok(v):
            raise ValueError("claude_budget_usd must be 0.1 to 100 (dollars per request)")
        if k == "exclude" and not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
            raise ValueError("exclude must be a list of glob patterns")
        if k == "target" and v not in (*TARGETS, ""):
            raise ValueError(f"target must be one of {', '.join(TARGETS)}, or empty for your default")
    project.ensure()
    with Lock(project):
        data = project.config()
        data.update(updates)
        if data.get("target") == "":
            data.pop("target")   # back to the user's default
        if "exclude" in updates:
            data["exclude"] = clean_config(data)["exclude"]
        write_json(project.data / "config.json", data)
    return project.settings()


def _within(project: Project, p: Path) -> bool:
    try:
        r = p.resolve()
    except OSError:
        return False
    return r == project.root or project.root in r.parents


def _excluded(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel + "/", p) for p in patterns)


_hash_cache: dict[tuple[str, float, int], str] = {}


def file_hash(p: Path) -> str:
    st = p.stat()
    key = (str(p), st.st_mtime, st.st_size)
    h = _hash_cache.get(key)
    if h is None:
        d = hashlib.sha1()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                d.update(chunk)
        h = _hash_cache[key] = d.hexdigest()[:12]
    return h


def scan(project: Project) -> list[Asset]:
    exclude = project.settings()["exclude"]
    by_dir: dict[Path, list[os.DirEntry]] = {}
    for dirpath, dirnames, filenames in os.walk(project.root):
        d = Path(dirpath)
        rel_dir = "" if d == project.root else d.relative_to(project.root).as_posix()
        dirnames[:] = sorted(
            n for n in dirnames
            if not n.startswith(".") and n not in SKIP_DIRS
            and not _excluded(f"{rel_dir}/{n}".lstrip("/"), exclude))
        models = [f for f in filenames if f.lower().endswith(MODEL_EXTS)
                  and not f.startswith(".")
                  and not _excluded(f"{rel_dir}/{f}".lstrip("/"), exclude)]
        if models and d.name in OUTPUT_DIRS and d != project.root and all(f.startswith(d.parent.name + "_") for f in models):
            # An output folder of the model next to it: its files are that model's.
            by_dir.setdefault(d.parent, []).extend(f"{d.name}/{f}" for f in sorted(models))
            continue
        if models:
            by_dir.setdefault(d, []).extend(sorted(models))
    assets: list[Asset] = []
    for d, models in by_dir.items():
        assets.extend(_group_dir(project, d, models))
    assets.sort(key=lambda a: a.id)
    return assets


def _group_dir(project: Project, d: Path, models: list[str]) -> list[Asset]:
    rel_dir = "" if d == project.root else d.relative_to(project.root).as_posix()
    # A model symlinked from outside the project cannot be served (/files/ stays
    # inside it), so it is left out rather than listed broken.
    models = [f for f in models if _within(project, d / f)]
    siblings = sorted(f for f in os.listdir(d) if f.lower().endswith(SIDE_EXTS) and not f.startswith(".")
                      and _within(project, d / f))
    groups: dict[tuple[str, bool], list[tuple[str, str]]] = {}
    mtimes = {f: (d / f).stat().st_mtime for f in models}
    parts = []
    for f in models:
        stem, ext = os.path.splitext(f.rsplit("/", 1)[-1])   # an output folder's file: its own name
        if ext.lower() in (".stl", ".3mf") and PRINT_PART_RE.match(stem) and not STAGE_RE.match(stem):
            parts.append(f)
            continue
        m = STAGE_RE.match(stem)
        if m:
            groups.setdefault((m.group("name"), True), []).append((m.group("stage"), f))
        else:
            groups.setdefault((stem, False), []).append((ext.lower().lstrip("."), f))
    # A kiln asset and a plain file with the same name (wooden-chair.glb next to
    # wooden-chair_final.glb) are one asset: the plain file joins as a variant.
    for (name, kiln) in list(groups):
        if not kiln and (name, True) in groups:
            groups[(name, True)].extend(groups.pop((name, False)))
    out = []
    for (name, kiln), items in groups.items():
        newest_other = max((mtimes[f] for label, f in items if label != LIVE), default=0.0)

        def order(item: tuple[str, str]) -> tuple[int, int]:
            label, f = item
            ext = os.path.splitext(f)[1].lower()
            if label == LIVE:
                stage = -1 if mtimes[f] >= newest_other else len(KILN_STAGES)
            else:
                stage = KILN_STAGES.index(label) if label in KILN_STAGES else len(KILN_STAGES)
            return (stage, FORMAT_ORDER.index(ext) if ext in FORMAT_ORDER else 9)
        items.sort(key=order)
        variants = []
        seen_labels: set[str] = set()
        for label, f in items:
            p = d / f
            ext = os.path.splitext(f)[1].lower().lstrip(".")
            # final.glb and final.fbx: label the second by its format too.
            lab = label if label not in seen_labels else f"{label}.{ext}"
            seen_labels.add(lab)
            st = p.stat()
            variants.append(Variant(lab, p, p.relative_to(project.root).as_posix(), st.st_size, st.st_mtime))
        # _preview is kiln's copy of _original for Quick Look: the same model twice is no stage to pick.
        orig = next((v for v in variants if v.label == "original"), None)
        if orig:
            variants = [v for v in variants if not (v.label == "preview" and v.size == orig.size
                                                    and filecmp.cmp(v.path, orig.path, shallow=False))]
        # A folder named after the asset is kiln's per-asset output folder: the id is
        # the folder, and every side file in it belongs to the asset.
        own_folder = kiln and d.name == name and rel_dir
        if own_folder:
            asset_id = rel_dir
            files = sorted(siblings + [f for f in parts if f.rsplit("/", 1)[-1].startswith(name)])
        else:
            asset_id = f"{rel_dir}/{name}".lstrip("/")
            files = [f for f in siblings if f.startswith(name) and not f.lower().endswith(MODEL_EXTS)]
        out.append(Asset(asset_id, name, rel_dir or ".", kiln, variants,
                         [f"{rel_dir}/{f}".lstrip("/") for f in files]))
    return out


# ── glTF stats (no decoding: accessor counts and min/max are in the JSON) ────


def read_gltf_json(path: Path) -> dict:
    with path.open("rb") as f:
        if path.suffix.lower() == ".gltf":
            return json.load(f)
        head = f.read(12)
        if len(head) < 12 or head[:4] != b"glTF":
            raise ValueError("not a GLB")
        length, ctype = struct.unpack("<II", f.read(8))
        if ctype != 0x4E4F534A:  # "JSON"
            raise ValueError("GLB has no JSON chunk first")
        return json.loads(f.read(length))


def _mat_mul(a: list[float], b: list[float]) -> list[float]:
    # Column-major 4x4, as glTF stores them.
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]


def _node_matrix(n: dict) -> list[float]:
    if "matrix" in n:
        return list(n["matrix"])
    tx, ty, tz = n.get("translation", (0, 0, 0))
    x, y, z, w = n.get("rotation", (0, 0, 0, 1))
    sx, sy, sz = n.get("scale", (1, 1, 1))
    return [
        (1 - 2 * (y * y + z * z)) * sx, (2 * (x * y + z * w)) * sx, (2 * (x * z - y * w)) * sx, 0,
        (2 * (x * y - z * w)) * sy, (1 - 2 * (x * x + z * z)) * sy, (2 * (y * z + x * w)) * sy, 0,
        (2 * (x * z + y * w)) * sz, (2 * (y * z - x * w)) * sz, (1 - 2 * (x * x + y * y)) * sz, 0,
        tx, ty, tz, 1,
    ]


_NORM = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


def gltf_stats(path: Path) -> dict:
    g = read_gltf_json(path)
    acc = g.get("accessors", [])
    meshes = g.get("meshes", [])
    nodes = g.get("nodes", [])
    tris = verts = instances = 0
    lo = [math.inf] * 3
    hi = [-math.inf] * 3

    def count(a: int | None) -> int:
        return acc[a].get("count", 0) if a is not None and a < len(acc) else 0

    def visit(i: int, parent: list[float], seen: set[int]) -> None:
        nonlocal tris, verts, instances
        if i in seen or i >= len(nodes):
            return
        seen.add(i)
        n = nodes[i]
        m = _mat_mul(parent, _node_matrix(n))
        if "mesh" in n and n["mesh"] < len(meshes):
            instances += 1
            for p in meshes[n["mesh"]].get("primitives", []):
                pos = p.get("attributes", {}).get("POSITION")
                nv = count(pos)
                ni = count(p.get("indices")) if "indices" in p else nv
                mode = p.get("mode", 4)
                tris += ni // 3 if mode == 4 else max(ni - 2, 0) if mode in (5, 6) else 0
                verts += nv
                a = acc[pos] if pos is not None and pos < len(acc) else {}
                if "min" in a and "max" in a:
                    k = _NORM.get(a.get("componentType")) if a.get("normalized") else None
                    mn = [v / k for v in a["min"]] if k else a["min"]
                    mx = [v / k for v in a["max"]] if k else a["max"]
                    for cx in (mn[0], mx[0]):
                        for cy in (mn[1], mx[1]):
                            for cz in (mn[2], mx[2]):
                                for r in range(3):
                                    v = m[r] * cx + m[4 + r] * cy + m[8 + r] * cz + m[12 + r]
                                    lo[r] = min(lo[r], v)
                                    hi[r] = max(hi[r], v)
        for c in n.get("children", []):
            visit(c, m, seen)

    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    scenes = g.get("scenes", [])
    if scenes:
        roots = scenes[g.get("scene", 0) if g.get("scene", 0) < len(scenes) else 0].get("nodes", [])
    else:
        children = {c for n in nodes for c in n.get("children", [])}
        roots = [i for i in range(len(nodes)) if i not in children]
    seen: set[int] = set()
    for r in roots:
        visit(r, ident, seen)
    anims = []
    for a in g.get("animations", []):
        dur = 0.0
        for s in a.get("samplers", []):
            inp = s.get("input")
            if inp is not None and inp < len(acc) and acc[inp].get("max"):
                dur = max(dur, acc[inp]["max"][0])
        anims.append({"name": a.get("name", ""), "duration": round(dur, 3),
                      "channels": len(a.get("channels", []))})
    out = {
        "tris": tris, "verts": verts, "meshes": len(meshes), "instances": instances,
        "nodes": len(nodes), "materials": [m.get("name", f"material_{i}") for i, m in enumerate(g.get("materials", []))],
        "textures": len(g.get("textures", [])), "images": len(g.get("images", [])),
        "animations": anims, "skins": len(g.get("skins", [])),
        "extensions": sorted(set(g.get("extensionsUsed", []))),
        "generator": g.get("asset", {}).get("generator", ""),
    }
    if lo[0] != math.inf:
        dims = [hi[i] - lo[i] for i in range(3)]
        out["bbox"] = {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]}
        # Blender reads glTF (x, y, z) as (x, -z, y): width X, depth Y, height Z.
        out["dimensions_blender"] = [round(dims[0], 4), round(dims[2], 4), round(dims[1], 4)]
    return out


_stats_cache: dict[tuple[str, str], dict] = {}


def stl_stats(path: Path) -> dict:
    """Triangles and size of an STL (binary or ASCII). kiln's print files are in millimetres."""
    data = path.read_bytes()
    pts: list[tuple[float, float, float]] = []
    n = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0
    if len(data) == 84 + 50 * n and n:
        for i in range(n):
            o = 84 + 50 * i + 12
            pts += [struct.unpack_from("<3f", data, o + 12 * k) for k in range(3)]
    else:
        txt = data.decode("ascii", "replace")
        n = txt.count("facet normal")
        pts = [tuple(map(float, m.groups())) for m in re.finditer(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", txt)]
    out: dict = {"tris": n, "verts": None, "meshes": 1, "units": "mm"}
    if pts:
        lo = [min(p[k] for p in pts) for k in range(3)]
        hi = [max(p[k] for p in pts) for k in range(3)]
        out["dimensions_blender"] = [round((hi[k] - lo[k]) / 1000, 4) for k in range(3)]
    return out


def threemf_stats(path: Path) -> dict:
    """Triangles, parts and size of a 3MF (a zip of XML models)."""
    tris, objects, xs, ys, zs, unit = 0, 0, [], [], [], "millimeter"
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.lower().endswith(".model"):
                continue
            x = z.read(name)
            m = re.search(rb'<model[^>]*\sunit="(\w+)"', x)
            unit = m.group(1).decode() if m else unit
            tris += x.count(b"<triangle ")
            objects += len(re.findall(rb"<mesh>", x))
            for v in re.finditer(rb'<vertex\s+x="([^"]+)"\s+y="([^"]+)"\s+z="([^"]+)"', x):
                xs.append(float(v.group(1))); ys.append(float(v.group(2))); zs.append(float(v.group(3)))
    scale = {"micron": 1e-6, "millimeter": 1e-3, "centimeter": 1e-2, "inch": 0.0254, "foot": 0.3048, "meter": 1.0}.get(unit, 1e-3)
    out: dict = {"tris": tris, "verts": None, "meshes": objects, "units": unit}
    if xs:
        out["dimensions_blender"] = [round((max(a) - min(a)) * scale, 4) for a in (xs, ys, zs)]
    return out


def variant_stats(v: Variant) -> dict | None:
    ext = v.path.suffix.lower()
    if ext not in (".glb", ".gltf", ".stl", ".3mf"):
        return None
    key = (v.rel, v.hash or file_hash(v.path))
    if key not in _stats_cache:
        try:
            _stats_cache[key] = stl_stats(v.path) if ext == ".stl" else threemf_stats(v.path) if ext == ".3mf" else gltf_stats(v.path)
        except (OSError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            _stats_cache[key] = {"error": str(e)}
    return _stats_cache[key]


# ── storage: locked JSON read-modify-write ───────────────────────────────────


class Lock:
    """A cross-process lock file (the server and the CLI both write)."""

    # Holders keep it for milliseconds; one older than STALE died holding it.
    STALE = 5.0

    def __init__(self, project: Project, timeout: float = 15.0):
        self.path = project.data / "store.lock"
        self.timeout = timeout

    def __enter__(self) -> "Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                try:  # a holder that died leaves the file behind
                    if time.time() - self.path.stat().st_mtime > self.STALE:
                        self.path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() > deadline:
                    raise TimeoutError(f"could not lock {self.path}; if no Studio command is running, delete it")
                time.sleep(0.02)

    def __exit__(self, *exc) -> None:
        self.path.unlink(missing_ok=True)


def read_json(p: Path, default):
    try:
        with p.open() as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        raise ValueError(f"{p} is not valid JSON ({e}); fix or delete it") from e


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.chmod(tmp, 0o644)  # mkstemp makes it 0600; these files are shared and committed
    os.replace(tmp, p)


# ── catalog: categories and tags ─────────────────────────────────────────────


def load_catalog(project: Project) -> dict:
    return read_json(project.data / "catalog.json", {"assets": {}})


def set_meta(project: Project, asset_id: str, category: str | None = None,
             tags: list[str] | None = None) -> dict:
    project.ensure()
    with Lock(project):
        cat = load_catalog(project)
        entry = cat.setdefault("assets", {}).setdefault(asset_id, {})
        if category is not None:
            category = category.strip().strip("/")
            if category:
                entry["category"] = category
            else:
                entry.pop("category", None)
        if tags is not None:
            clean = sorted({re.sub(r"\s+", "-", t.strip().lower()) for t in tags if t.strip()})
            if clean:
                entry["tags"] = clean
            else:
                entry.pop("tags", None)
        if not entry:
            cat["assets"].pop(asset_id, None)
        write_json(project.data / "catalog.json", cat)
        return entry


# ── notes ────────────────────────────────────────────────────────────────────


def notes_path(project: Project, asset_id: str) -> Path:
    return project.asset_dir(asset_id) / "notes.json"


def load_notes(project: Project, asset_id: str) -> list[dict]:
    return read_json(notes_path(project, asset_id), {"notes": []}).get("notes", [])


def _save_notes(project: Project, asset_id: str, notes: list[dict]) -> None:
    write_json(notes_path(project, asset_id), {"asset": asset_id, "notes": notes})


def counts(notes: list[dict]) -> dict:
    return {s: sum(1 for n in notes if n.get("status") == s) for s in STATUSES}


def version_ref(v: Variant) -> dict:
    return {"variant": v.label, "file": v.rel, "hash": v.hash or file_hash(v.path)}


def image_ext(data: bytes) -> str:
    if data.startswith(b"\xff\xd8"):
        return ".jpg"
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("a screenshot must be a JPEG, PNG or WebP")


def save_shot(project: Project, asset_id: str, stem: str, data: bytes) -> str:
    d = project.asset_dir(asset_id) / "shots"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (stem + image_ext(data))
    for old in d.glob(stem + ".*"):
        old.unlink()
    p.write_bytes(data)
    return project.rel(p)


def _nums(v, n: int, lo: float = -1e9, hi: float = 1e9) -> list[float] | None:
    if not (isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) for x in v)):
        return None
    return [min(hi, max(lo, float(x))) for x in v]


def clean_view(view) -> dict | None:
    """How a note's pictures were framed, so the "after" ones match: `crop`, the part of
    the view kept (fractions: x0, y0, x1, y1), and for a pin `detail`, the close-up's
    camera (glTF frame). Anything else the page sends is dropped."""
    if not isinstance(view, dict):
        return None
    out: dict = {}
    crop = _nums(view.get("crop"), 4, 0.0, 1.0)
    if crop and crop[2] > crop[0] and crop[3] > crop[1]:
        out["crop"] = crop
    d = view.get("detail")
    if isinstance(d, dict):
        pos, tgt, fov = _nums(d.get("position"), 3), _nums(d.get("target"), 3), d.get("fov")
        if pos and tgt and isinstance(fov, (int, float)) and 1 <= fov <= 120:
            out["detail"] = {"position": pos, "target": tgt, "fov": float(fov)}
    return out or None


def add_note(project: Project, asset: Asset, text: str, *, variant: str | None = None,
             anchor: dict | None = None, camera: dict | None = None, view: dict | None = None,
             shot: bytes | None = None, detail: bytes | None = None, by: str = "user") -> dict:
    """A new note on the variant as it is now. Also takes the n-1 baseline.

    `shot` is the view (cropped to the model); `detail`, for a pin, a close-up of it."""
    project.ensure()
    v = asset.variant(variant)
    nid = new_id("n")
    note = {
        "id": nid, "kind": "pin" if anchor else "general", "text": text.strip(),
        "status": "open", "by": by, "created": now(), "version": version_ref(v),
        "anchor": anchor, "camera": camera, "view": clean_view(view), "shot": None, "detail": None,
        "thread": [],
    }
    if shot:
        note["shot"] = save_shot(project, asset.id, nid, shot)
    if detail:
        note["detail"] = save_shot(project, asset.id, f"{nid}_detail", detail)
    with Lock(project):
        notes = load_notes(project, asset.id)
        notes.append(note)
        _save_notes(project, asset.id, notes)
    observe(project, asset)
    take_baseline(project, asset, v, reason=f"note {nid}", only_if_new=True)
    return note


def update_note(project: Project, asset_id: str, note_id: str, fn) -> dict:
    with Lock(project):
        notes = load_notes(project, asset_id)
        for n in notes:
            if n["id"] == note_id:
                fn(n)
                _save_notes(project, asset_id, notes)
                return n
    raise KeyError(f"no note {note_id} on {asset_id}")


def reply(project: Project, asset: Asset, note_id: str, text: str, *, by: str,
          status: str | None = None, shot: bytes | None = None) -> dict:
    if status is not None and status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if by == "claude" and status == "resolved":
        # Only the owner closes a note: they are the one who has looked at it.
        raise ValueError("only the user resolves a note; reply with --status addressed")
    observe(project, asset)
    entry: dict = {"id": new_id("r"), "by": by, "at": now(), "text": text.strip()}
    if status:
        entry["status"] = status

    def apply(n: dict) -> None:
        # The version the reply was made on: for "addressed", the version to check.
        try:
            v = asset.variant(n.get("version", {}).get("variant"))
        except KeyError:
            v = asset.primary
        entry["version"] = version_ref(v)
        if shot:
            entry["shot"] = save_shot(project, asset.id, f"{n['id']}_{entry['id']}", shot)
        n.setdefault("thread", []).append(entry)
        if status:
            n["status"] = status
        n["updated"] = entry["at"]

    update_note(project, asset.id, note_id, apply)
    return entry


def set_reply_shot(project: Project, asset_id: str, note_id: str, reply_id: str, shot: bytes,
                   detail: bytes | None = None) -> str:
    """The "after" of an addressed reply: the note's view and, for a pin, its close-up."""
    rel = save_shot(project, asset_id, f"{note_id}_{reply_id}", shot)
    rel_d = save_shot(project, asset_id, f"{note_id}_{reply_id}_detail", detail) if detail else None

    def apply(n: dict) -> None:
        for r in n.get("thread", []):
            if r["id"] == reply_id:
                r["shot"] = rel
                if rel_d:
                    r["detail"] = rel_d
                return
        raise KeyError(f"no reply {reply_id}")

    update_note(project, asset_id, note_id, apply)
    return rel


def edit_note_text(project: Project, asset_id: str, note_id: str, text: str) -> dict:
    def apply(n: dict) -> None:
        n["text"] = text.strip()
        n["updated"] = now()
    return update_note(project, asset_id, note_id, apply)


def delete_note(project: Project, asset_id: str, note_id: str) -> None:
    with Lock(project):
        notes = load_notes(project, asset_id)
        keep = [n for n in notes if n["id"] != note_id]
        if len(keep) == len(notes):
            raise KeyError(f"no note {note_id} on {asset_id}")
        _save_notes(project, asset_id, keep)
    shots = project.asset_dir(asset_id) / "shots"
    if shots.is_dir():
        for f in shots.glob(f"{note_id}*"):
            f.unlink()


def pending_shots(notes: list[dict], asset: Asset) -> list[dict]:
    """Replies that marked a note addressed, on the version that is current, with no
    screenshot yet: the page renders them from the note's camera (the "after")."""
    out = []
    current = {v.label: v.hash for v in asset.variants}
    for n in notes:
        for r in n.get("thread", []):
            if r.get("status") == "addressed" and not r.get("shot"):
                ver = r.get("version", {})
                if current.get(ver.get("variant")) == ver.get("hash"):
                    out.append({"note": n["id"], "reply": r["id"], "variant": ver.get("variant")})
    return out


# ── history: versions seen, and the changelog ────────────────────────────────


def history_path(project: Project, asset_id: str) -> Path:
    return project.asset_dir(asset_id) / "history.json"


def load_history(project: Project, asset_id: str) -> list[dict]:
    return read_json(history_path(project, asset_id), {"events": []}).get("events", [])


def _append_events(project: Project, asset_id: str, events: list[dict]) -> None:
    with Lock(project):
        evs = load_history(project, asset_id)
        evs.extend(events)
        write_json(history_path(project, asset_id), {"asset": asset_id, "events": evs})


def observe(project: Project, asset: Asset) -> list[dict]:
    """Record every variant whose content differs from the last version seen.

    No model is copied: a version is its hash, size, triangle count, and the small
    render the page adds. Called by the server's watcher and by every CLI write, so
    history is kept whether or not the page is open.
    """
    def last_seen(events: list[dict]) -> dict[str, str]:
        return {e["variant"]: e["hash"] for e in events if e.get("type") == "version"}

    # Hash and stats outside the lock (slow on big files)...
    for v in asset.variants:
        v.hash = v.hash or file_hash(v.path)
        variant_stats(v)
    if all(last_seen(load_history(project, asset.id)).get(v.label) == v.hash for v in asset.variants):
        return []
    project.ensure()
    live = load_live(project, asset.id) if any(v.label.startswith(LIVE) for v in asset.variants) else None
    # ...and decide under it, so the server and the CLI never both record one version.
    with Lock(project):
        evs = load_history(project, asset.id)
        last = last_seen(evs)
        new = []
        for v in asset.variants:
            if last.get(v.label) != v.hash:
                st = variant_stats(v) or {}
                e = {"type": "version", "at": now(), "variant": v.label, "file": v.rel,
                     "hash": v.hash, "size": v.size,
                     "mtime": datetime.fromtimestamp(v.mtime, timezone.utc).isoformat(timespec="seconds"),
                     "tris": st.get("tris"), "first": v.label not in last}
                if live and v.label.startswith(LIVE):
                    # Which phase this snapshot closed: the build record, version by version.
                    e["phase"], e["step"] = live.get("phase"), (live.get("steps") or [{}])[-1].get("text", "")
                new.append(e)
        if new:
            evs.extend(new)
            write_json(history_path(project, asset.id), {"asset": asset.id, "events": evs})
    return new


def log(project: Project, asset: Asset, text: str, by: str = "claude") -> dict:
    observe(project, asset)
    e = {"type": "log", "at": now(), "by": by, "text": text.strip(), "hash": asset.primary.hash}
    project.ensure()
    _append_events(project, asset.id, [e])
    return e


# Renders of each version, made by the page. A cache: the durable record of what a
# model looked like is the screenshot on each note.
def thumb_path(project: Project, asset_id: str, h: str) -> Path:
    return project.data / "cache" / "thumbs" / asset_key(asset_id) / f"{h}.webp"


def thumb_rel(project: Project, asset_id: str, h: str) -> str:
    return project.rel(thumb_path(project, asset_id, h))


def has_thumb(project: Project, asset_id: str, h: str) -> bool:
    return thumb_path(project, asset_id, h).exists()


def save_thumb(project: Project, asset_id: str, h: str, data: bytes) -> str:
    project.ensure()
    p = thumb_path(project, asset_id, h)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return thumb_rel(project, asset_id, h)


# ── baseline: one previous copy (n-1) ────────────────────────────────────────


def baseline(project: Project, asset_id: str) -> dict | None:
    meta = read_json(project.baseline_dir(asset_id) / "meta.json", None)
    if meta and (project.baseline_dir(asset_id) / meta["name"]).exists():
        meta["file"] = project.rel(project.baseline_dir(asset_id) / meta["name"])
        return meta
    return None


def _gltf_deps(path: Path) -> list[str]:
    """Relative files a .gltf points at (buffers, images), to copy alongside it."""
    if path.suffix.lower() != ".gltf":
        return []
    try:
        g = read_gltf_json(path)
    except (OSError, ValueError):
        return []
    # URIs are URI-encoded: Blender writes "My%20Chair.bin" for "My Chair.bin".
    uris = [unquote(x.get("uri", "")) for x in g.get("buffers", []) + g.get("images", [])]
    return [u for u in uris if u and not u.startswith("data:") and "://" not in u
            and ".." not in u and not u.startswith("/")]


def take_baseline(project: Project, asset: Asset, v: Variant | None = None, *,
                  reason: str, only_if_new: bool = False) -> dict | None:
    """Copy the variant as it is now into the asset's single baseline slot.

    Studio keeps exactly one previous copy per asset — the version a review pass
    started from — so a pass can be compared before/after and reverted, without a
    growing pile of model copies. `only_if_new` keeps an existing baseline of the
    same content (several notes on one version are one pass).
    """
    v = v or asset.primary
    v.hash = v.hash or file_hash(v.path)
    cur = baseline(project, asset.id)
    if only_if_new and cur and cur.get("hash") == v.hash:
        return cur
    project.ensure()
    d = project.baseline_dir(asset.id)
    d.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=d.parent, prefix=d.name + ".", suffix=".tmp"))
    shutil.copy2(v.path, tmp / v.path.name)
    for dep in _gltf_deps(v.path):
        src = v.path.parent / dep
        if src.is_file():
            (tmp / dep).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp / dep)
    meta = {"name": v.path.name, "variant": v.label, "source": v.rel, "hash": v.hash,
            "size": v.size, "at": now(), "reason": reason}
    write_json(tmp / "meta.json", meta)
    with Lock(project):
        shutil.rmtree(d, ignore_errors=True)
        os.replace(tmp, d)
    _append_events(project, asset.id, [{"type": "baseline", "at": meta["at"], "variant": v.label,
                                        "hash": v.hash, "reason": reason}])
    return baseline(project, asset.id)


def revert(project: Project, asset: Asset) -> dict:
    """Put the baseline back over its source file. The version it replaces becomes
    the new baseline, so a revert is itself one revert away from undone."""
    b = baseline(project, asset.id)
    if not b:
        raise ValueError(f"{asset.id} has no previous version to revert to")
    target = project.inside(b["source"])
    src_dir = project.baseline_dir(asset.id)
    hold = Path(tempfile.mkdtemp(dir=src_dir.parent, prefix=src_dir.name + ".", suffix=".revert"))
    shutil.copytree(src_dir, hold, dirs_exist_ok=True)
    cur = None
    if target.exists():
        v = next((x for x in asset.variants if x.path == target), None)
        if v:
            cur = take_baseline(project, asset, v, reason=f"replaced by revert to {b['hash']}")
    # copyfile, not copy2: the restored file gets a new mtime, so anything watching
    # for newer files (Studio itself, a game engine's importer) sees the change.
    shutil.copyfile(hold / b["name"], target)
    for dep in _gltf_deps(hold / b["name"]):
        if (hold / dep).is_file():
            (target.parent / dep).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(hold / dep, target.parent / dep)
    shutil.rmtree(hold, ignore_errors=True)
    _append_events(project, asset.id, [{"type": "revert", "at": now(), "variant": b["variant"],
                                        "hash": b["hash"], "replaced": cur and cur["hash"]}])
    return b


# ── live: the build kiln is running ──────────────────────────────────────────


def live_path(project: Project, asset_id: str) -> Path:
    return project.asset_dir(asset_id) / "live.json"


def load_live(project: Project, asset_id: str) -> dict | None:
    try:
        return read_json(live_path(project, asset_id), None)
    except ValueError:
        return None


def norm_phase(phase: str) -> str:
    # "cleanup", "CLEANUP", "[5] CLEANUP", "5b", "texturing" are all accepted.
    p = (phase or "").strip().lower()
    p = PHASE_ALIASES.get(p, p)
    if p not in PHASES:
        p = re.sub(r"^\[?\d+[a-z]?\]?\s*", "", p)
        p = PHASE_ALIASES.get(p, p)
    if p not in PHASES:
        raise ValueError(f"unknown phase {phase!r}: one of {', '.join(PHASES)}")
    return p


def live_files(project: Project, asset_id: str) -> list[Path]:
    """The scratch `<name>_live.*` exports of a kiln asset folder."""
    d = project.inside(asset_id)
    name = d.name
    return [p for ext in (".glb", ".gltf") if (p := d / f"{name}_{LIVE}{ext}").is_file()]


def set_live(project: Project, asset_id: str, phase: str | None = None, text: str = "",
             end: bool = False) -> dict:
    """Record a step of a build. The asset need not exist yet: `asset_id` is its kiln folder
    (`generated-assets/wooden-chair`), which is the id it gets once a model lands there.

    A step on a build that ended starts a new one. `end` closes the build; the scratch
    `_live` export is the caller's to remove (end_live does both).
    """
    project.ensure()
    with Lock(project):
        cur = load_live(project, asset_id)
        t = now()
        if not cur or (cur.get("state") != "building" and not end):
            cur = {"asset": asset_id, "state": "building", "started": t, "phase": None, "steps": []}
        if phase:
            cur["phase"] = norm_phase(phase)
        elif end:
            cur["phase"] = "export"   # the build ends with its export
        if phase or text:
            cur["steps"] = (cur.get("steps") or [])[-199:] + [{"at": t, "phase": cur.get("phase"), "text": text.strip()}]
        if end:
            cur["state"] = "done"
            cur["ended"] = t
        cur["updated"] = t
        write_json(live_path(project, asset_id), cur)
        return cur


def end_live(project: Project, asset_id: str, text: str = "", keep_file: bool = False) -> tuple[dict, list[str]]:
    """Close the build, and remove the scratch `_live` export unless asked to keep it:
    kiln wrote it for the view, and compact storage keeps only original, final, .blend, log."""
    state = set_live(project, asset_id, text=text, end=True)
    removed = []
    if not keep_file:
        for p in live_files(project, asset_id):
            removed.append(project.rel(p))
            p.unlink()
    return state, removed


def live_summary(live: dict | None) -> dict | None:
    if not live:
        return None
    return {k: live.get(k) for k in ("state", "phase", "started", "updated", "ended")}


# ── work: which models a kiln command is on ──────────────────────────────────
#
# One run per project, `.kiln-studio/work.json`: the models a command works through, in
# order, each queued → active → done. The page shows a dot per model (waiting, breathing,
# green); a done model's dot goes once the user has looked at it, and the run with it.

WORK_STATES = ("queued", "active", "done", "dropped")
# A run with no word from kiln for this long died with its session: stop showing it working.
WORK_STALE = 2 * 3600


def work_path(project: Project) -> Path:
    return project.data / "work.json"


def load_work(project: Project) -> dict | None:
    try:
        return read_json(work_path(project), None)
    except ValueError:
        return None


def _work_item(run: dict, asset_id: str) -> dict:
    for it in run["items"]:
        if it["asset"] == asset_id:
            return it
    raise KeyError(f"{asset_id!r} is not in the run ({', '.join(it['asset'] for it in run['items'])})")


def _activate(it: dict, t: str) -> None:
    it["state"] = "active"
    it["started"] = it.get("started") or t


def _finish(it: dict, t: str, text: str = "") -> None:
    it["state"] = "done"
    it["ended"] = t
    if text.strip():
        it["text"] = text.strip()


def _update_work(project: Project, fn) -> dict:
    project.ensure()
    with Lock(project):
        run = load_work(project)
        t = now()
        run = fn(run, t)
        run["updated"] = t
        if run["state"] == "running" and not any(it["state"] in ("queued", "active") for it in run["items"]):
            run["state"] = "done"
            run["ended"] = t
        write_json(work_path(project), run)
        return run


def start_work(project: Project, asset_ids: list[str], label: str = "") -> dict:
    """A new run over these models, in this order, the first one active. It replaces the
    last run, its unchecked dots included."""
    ids = list(dict.fromkeys(asset_ids))
    if not ids:
        raise ValueError("name at least one model")

    def fn(_old, t):
        items = [{"asset": a, "state": "queued"} for a in ids]
        _activate(items[0], t)
        return {"id": new_id("w"), "label": label.strip(), "state": "running", "started": t, "items": items}
    return _update_work(project, fn)


def _running(run: dict | None) -> dict:
    if not run or run.get("state") != "running":
        raise ValueError("no run under way: start one with `studio.py work start <asset>...`")
    return run


def work_next(project: Project, text: str = "") -> dict:
    """The active model is done; the next queued one becomes active."""
    def fn(run, t):
        run = _running(run)
        for it in run["items"]:
            if it["state"] == "active":
                _finish(it, t, text)
        nxt = next((it for it in run["items"] if it["state"] == "queued"), None)
        if nxt:
            _activate(nxt, t)
        return run
    return _update_work(project, fn)


def work_begin(project: Project, asset_id: str) -> dict:
    """Work on this model now, out of order; the one active before it is done. A model not
    in the run joins it; with no run under way, this starts one."""
    def fn(run, t):
        if not run or run.get("state") != "running":
            return {"id": new_id("w"), "label": "", "state": "running", "started": t,
                    "items": [{"asset": asset_id, "state": "active", "started": t}]}
        for it in run["items"]:
            if it["state"] == "active" and it["asset"] != asset_id:
                _finish(it, t)
        try:
            _activate(_work_item(run, asset_id), t)
        except KeyError:
            run["items"].append({"asset": asset_id, "state": "active", "started": t})
        return run
    return _update_work(project, fn)


def work_done(project: Project, asset_id: str, text: str = "") -> dict:
    def fn(run, t):
        _finish(_work_item(_running(run), asset_id), t, text)
        return run
    return _update_work(project, fn)


def end_work(project: Project, text: str = "") -> dict:
    """Close the run: the active model is done, the ones never started are dropped."""
    def fn(run, t):
        run = _running(run)
        for it in run["items"]:
            if it["state"] == "active":
                _finish(it, t)
            elif it["state"] == "queued":
                it["state"] = "dropped"
        if text.strip():
            run["text"] = text.strip()
        run["state"] = "done"
        run["ended"] = t
        return run
    return _update_work(project, fn)


def check_work(project: Project, asset_ids: list[str] | None = None) -> dict | None:
    """The user looked: these models' green dots go (all the done ones when None).
    A finished run whose done models are all checked is cleared."""
    with Lock(project):
        run = load_work(project)
        if not run:
            return None
        changed = False
        for it in run["items"]:
            if it["state"] == "done" and not it.get("checked") and (asset_ids is None or it["asset"] in asset_ids):
                it["checked"] = now()
                changed = True
        if run["state"] != "running" and all(it.get("checked") or it["state"] != "done" for it in run["items"]):
            work_path(project).unlink(missing_ok=True)
            return None
        if changed:
            write_json(work_path(project), run)
        return run


def _age(iso: str | None) -> float:
    try:
        return time.time() - datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return float("inf")


def work_view(run: dict | None) -> dict | None:
    """What the page shows: each model's dot (queued, active, done), and the run's progress.
    Checked and dropped models have none; a stale run shows only what it finished."""
    if not run:
        return None
    stale = run.get("state") == "running" and _age(run.get("updated")) > WORK_STALE
    dots = {}
    for it in run["items"]:
        st = it["state"]
        if stale and st in ("queued", "active"):
            continue
        if st == "dropped" or (st == "done" and it.get("checked")):
            continue
        dots[it["asset"]] = {k: it.get(k) for k in ("state", "started", "ended", "text")}
    if not dots:
        return None
    done = sum(it["state"] == "done" for it in run["items"])
    total = sum(it["state"] != "dropped" for it in run["items"])
    active = next((it["asset"] for it in run["items"] if it["state"] == "active" and not stale), None)
    return {"id": run["id"], "label": run.get("label", ""), "running": run["state"] == "running" and not stale,
            "stale": stale, "done": done, "total": total, "active": active,
            "started": run.get("started"), "updated": run.get("updated"), "dots": dots}


# ── requests: a model asked for in Studio's Create form ──────────────────────
# Like a note, but for a model that does not exist yet: open until Claude has built it.

REQUEST_ID_RE = re.compile(r"^q_[a-z0-9]{6,16}$")
REQUEST_TYPES = ("prop", "character", "creature", "vehicle", "environment")
REQUEST_TARGETS = ("web", "desktop", "ar", "print")
REQUEST_STYLES = ("realistic", "stylized", "cartoon", "low-poly")
TARGET_WORDS = {"web": "for the web (glTF)", "desktop": "for Unity/Unreal (FBX)", "ar": "for AR (USDZ)",
                "print": "for 3D printing"}


def requests_path(project: Project) -> Path:
    return project.data / "requests.json"


def load_requests(project: Project) -> list[dict]:
    return read_json(requests_path(project), {"requests": []}).get("requests", [])


def request_command(r: dict) -> str:
    """What the user pastes in Claude Code: the brief first (the skill reads anything that
    is not a command as a brief), then what the form said, then the request's id."""
    parts = [r["brief"].strip().rstrip(".")]
    if r.get("type"):
        parts.append(f"type {r['type']}")
    if r.get("target"):
        parts.append(TARGET_WORDS[r["target"]])
    if r.get("style"):
        parts.append(r["style"])
    if r.get("reference"):
        parts.append(f"reference photo {r['reference']}")
    one_line = " ".join(", ".join(parts).split())
    return f"/kiln {one_line} (Studio request {r['id']})"


def add_request(project: Project, brief: str, *, type_: str | None = None, target: str | None = None,
                style: str | None = None, photo: bytes | None = None) -> dict:
    brief = " ".join(str(brief or "").split())
    if not brief:
        raise ValueError("a request needs a brief")
    if len(brief) > 4000:
        raise ValueError("the brief is too long (4,000 characters at most)")
    for name, v, allowed in (("type", type_, REQUEST_TYPES), ("target", target, REQUEST_TARGETS), ("style", style, REQUEST_STYLES)):
        if v and v not in allowed:
            raise ValueError(f"{name} must be one of {', '.join(allowed)}")
    project.ensure()
    rid = new_id("q")
    r = {"id": rid, "kind": "create", "brief": brief, "type": type_ or None, "target": target or None,
         "style": style or None, "reference": None, "status": "open", "by": "user", "created": now(),
         "thread": []}
    if photo:
        d = project.data / "requests"
        d.mkdir(parents=True, exist_ok=True)
        p = d / (rid + image_ext(photo))
        p.write_bytes(photo)
        r["reference"] = project.rel(p)
    r["command"] = request_command(r)
    with Lock(project):
        items = load_requests(project)
        items.append(r)
        write_json(requests_path(project), {"requests": items})
    return r


def close_request(project: Project, rid: str, *, status: str = "done", asset: str | None = None,
                  text: str = "") -> dict:
    if status not in ("open", "done", "wontfix"):
        raise ValueError("status must be open, done or wontfix")
    with Lock(project):
        items = load_requests(project)
        for r in items:
            if r["id"] == rid:
                r["status"] = status
                if asset:
                    r["asset"] = asset
                r.setdefault("thread", []).append({"by": "claude", "at": now(), "status": status, "text": text.strip()})
                write_json(requests_path(project), {"requests": items})
                return r
    raise KeyError(f"no request {rid}")


# ── import: model files dropped on the page ──────────────────────────────────

IMPORT_DIR = "imports"
COMPANION_EXTS = (".bin", ".mtl", ".png", ".jpg", ".jpeg", ".webp", ".ktx2")
SAFE_NAME_RE = re.compile(r"^[^/\\\x00-\x1f:*?\"<>|]{1,200}$")


def import_file(project: Project, name: str, data: bytes, folder: str | None = None) -> str:
    """Save a dropped file under imports/ (or imports/<folder>/ for a glTF or OBJ and the
    files it needs), never over an existing one. Returns its project path."""
    name = Path(str(name)).name
    if not SAFE_NAME_RE.match(name) or name.startswith("."):
        raise ValueError(f"not a file name Studio saves: {name!r}")
    ext = Path(name).suffix.lower()
    if ext not in MODEL_EXTS and not (folder and ext in COMPANION_EXTS):
        raise ValueError(f"{name}: Studio imports {', '.join(MODEL_EXTS)} (and, beside a glTF or OBJ, its {', '.join(COMPANION_EXTS)})")
    base = project.root / IMPORT_DIR
    if folder:
        folder = Path(str(folder)).name
        if not re.match(r"^[\w.-]{1,80}$", folder) or folder.startswith("."):
            raise ValueError(f"not a folder name Studio makes: {folder!r}")
        base = base / folder
    base.mkdir(parents=True, exist_ok=True)
    dst = base / name
    # Never replace a file: chair.glb, chair-2.glb, … (companions keep their name: the
    # glTF or OBJ refers to them by it, and their folder is new).
    if dst.exists() and not (folder and ext in COMPANION_EXTS):
        stem, n = dst.stem, 2
        while (base / f"{stem}-{n}{dst.suffix}").exists():
            n += 1
        dst = base / f"{stem}-{n}{dst.suffix}"
    tmp = dst.with_name(f".{dst.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dst)
    return project.rel(dst)


# ── the example model: "See an example" on Studio's welcome screen ───────────

EXAMPLE_SRC = Path(__file__).resolve().parent / "example"
EXAMPLE_DIR = "kiln-example"


def add_example(project: Project) -> str:
    """Copy Studio's example model (kiln's gallery barrel, MIT) into the project, in
    kiln's layout, unless it is there already. Returns its asset id."""
    src = EXAMPLE_SRC / "barrel"
    dst = project.root / EXAMPLE_DIR / "barrel"
    if not (dst / "barrel_final.glb").is_file():
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)
    return f"{EXAMPLE_DIR}/barrel"


# ── summaries for the page and the CLI ───────────────────────────────────────


def asset_summary(project: Project, a: Asset, catalog: dict) -> dict:
    notes = load_notes(project, a.id)
    meta = catalog.get("assets", {}).get(a.id, {})
    for v in a.variants:
        v.hash = v.hash or file_hash(v.path)
    st = variant_stats(a.primary) or {}
    b = baseline(project, a.id)
    return {
        "id": a.id, "name": a.name, "folder": a.folder, "kiln": a.kiln,
        "category": meta.get("category", a.default_category),
        "category_custom": "category" in meta,
        "tags": meta.get("tags", []),
        "variants": [v.to_json() for v in a.variants],
        "thumb": thumb_rel(project, a.id, a.primary.hash) if has_thumb(project, a.id, a.primary.hash) else None,
        "counts": counts(notes),
        "tris": st.get("tris"),
        "updated": max(v.mtime for v in a.variants),
        "baseline": b and {"hash": b["hash"], "variant": b["variant"], "at": b["at"]},
        "pending_shots": len(pending_shots(notes, a)),
        "live": live_summary(load_live(project, a.id)) if a.kiln else None,
    }


def asset_detail(project: Project, a: Asset, catalog: dict) -> dict:
    out = asset_summary(project, a, catalog)
    out["variants"] = [dict(v.to_json(), stats=variant_stats(v)) for v in a.variants]
    out["files"] = a.files
    out["log"] = a.log_file()
    out["blend"] = a.blend_file()
    out["notes"] = load_notes(project, a.id)
    out["history"] = load_history(project, a.id)
    out["baseline"] = baseline(project, a.id)
    out["pending"] = pending_shots(out["notes"], a)
    versions = {e["hash"] for e in out["history"] if e.get("type") == "version"}
    out["thumbs"] = sorted(h for h in versions if has_thumb(project, a.id, h))
    out["live"] = load_live(project, a.id) if a.kiln else None
    return out
