"""Kiln Studio's checks: what kiln's own rules say about a model, read from the file.

Standard library only. Three readers, each used by the server (the page's Checks tab)
and by the CLI (`studio.py checks`):

- health(): the shipped file against kiln's rules — triangles against the detail tier
  (topology-rules.md, soft ranges: rule 4), size and ground contact (validation-checklist.md),
  texture sizes against the target's cap (uv-materials.md), Draco and WebP on `_final`
  (OPTIMIZE), and the licences the production log records;
- fidelity_runs(): what tools/fidelity_check.py measured against the reference photo,
  found in the asset folder's `review*/` folders;
- batch_estimate(): the batch wizard's token estimate (batch-mode.md § Step 4), from the
  batch folder's batch-manifest.yaml.

Every check is information: none blocks, and none is worded as a target.
"""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from urllib.parse import unquote

import studiolib as sl

# references/topology-rules.md § Detail Tiers: soft ranges, up to twice the top is fine.
TIERS = {
    "lightweight": {"hero": (3000, 8000), "prop": (300, 1500), "background": (50, 300)},
    "balanced": {"hero": (8000, 20000), "prop": (1500, 5000), "background": (300, 1500)},
    "detailed": {"hero": (20000, 80000), "prop": (5000, 15000), "background": (1500, 5000)},
}
CATEGORY_LABEL = {"hero": "hero/character", "prop": "prop", "background": "background"}
HERO_WORDS = {"character", "creature", "hero", "vehicle", "human", "humanoid", "animal"}
BACKGROUND_WORDS = {"background", "environment", "scenery", "backdrop"}
# references/validation-checklist.md § Scale Verification.
EXPECTED_HEIGHT = {"character": 1.75, "chair": 0.85, "table": 0.75, "door": 2.10}
# references/uv-materials.md § Texture Resolution: 1024 for web/glTF whatever the tier;
# 2048 for console/PC targets (or a brief that asks for close-ups).
CAP_WEB, CAP_DESKTOP = 1024, 2048
# references/batch-mode.md § Step 4: tokens per asset by method; the range is
# low x 1.0 to high x 1.5.
TOKENS = {"scripted": (30_000, 30_000), "marketplace": (20_000, 20_000),
          "ai": (60_000, 80_000), "geometry-nodes": (40_000, 40_000)}
HIGH_FACTOR = 1.5
MANIFESTS = ("batch-manifest.yaml", "batch-manifest.yml")

RANK = {"ok": 0, "info": 1, "warn": 2}


def kfmt(n: float) -> str:
    """1500 -> 1.5K, 20000 -> 20K, 300 -> 300, 1_250_000 -> 1.25M."""
    if n >= 1e6:
        return f"{n / 1e6:.2f}".rstrip("0").rstrip(".") + "M"
    if n >= 1000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "K"
    return f"{int(n)}"


def _check(key: str, label: str, level: str, text: str, **extra) -> dict:
    return {"key": key, "label": label, "level": level, "text": text, **extra}


# ── the production log ───────────────────────────────────────────────────────


def parse_log(path: Path | None) -> dict:
    """`{name}_log.md` (SKILL.md § Log Format): sections of `- Key: value` bullets.

    Returns {"sections": {section: [bullet, ...]}, "config": {key: value}}, keys lowercased.
    """
    out: dict = {"sections": {}, "config": {}}
    if not path or not path.is_file():
        return out
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return out
    section = ""
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            section = m.group(1).strip().lower()
            out["sections"].setdefault(section, [])
            continue
        m = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if m and section:
            out["sections"][section].append(m.group(1))
    for b in out["sections"].get("config", []):
        m = re.match(r"^([^:]+):\s*(.*)$", b)
        if m:
            out["config"][m.group(1).strip().lower()] = m.group(2).strip()
    return out


def _words(*texts: str) -> set[str]:
    return {w for t in texts if t for w in re.split(r"[^a-z0-9]+", t.lower()) if w}


def category_of(type_: str) -> str:
    w = _words(type_)
    if w & HERO_WORDS:
        return "hero"
    if w & BACKGROUND_WORDS:
        return "background"
    return "prop"


def texture_cap(target: str) -> int:
    t = (target or "").lower()
    return CAP_DESKTOP if any(k in t for k in ("fbx", "unity", "unreal", "console", "pc", "desktop")) else CAP_WEB


# ── image sizes, read from the headers ───────────────────────────────────────


def image_size(head: bytes) -> tuple[int, int, str] | None:
    """(width, height, format) from the first bytes of a PNG, JPEG, WebP or KTX2 image."""
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        w, h = struct.unpack(">II", head[16:24])
        return w, h, "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP" and len(head) >= 30:
        kind = head[12:16]
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", head[26:30])
            return w & 0x3FFF, h & 0x3FFF, "webp"
        if kind == b"VP8L":
            b = head[21:25]
            w = 1 + (((b[1] & 0x3F) << 8) | b[0])
            h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
            return w, h, "webp"
        if kind == b"VP8X":
            w = 1 + int.from_bytes(head[24:27], "little")
            h = 1 + int.from_bytes(head[27:30], "little")
            return w, h, "webp"
    if head[:12] == b"\xabKTX 20\xbb\r\n\x1a\n" and len(head) >= 28:
        w, h = struct.unpack("<II", head[20:28])
        return w, h, "ktx2"
    if head[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(head):
            if head[i] != 0xFF:
                i += 1
                continue
            marker = head[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", head[i + 2:i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", head[i + 5:i + 9])
                return w, h, "jpeg"
            i += 2 + seg
    return None


HEAD = 256 * 1024  # enough to reach a JPEG's frame header past its EXIF


def _glb_bin_offset(path: Path) -> int | None:
    with path.open("rb") as f:
        head = f.read(20)
        if len(head) < 20 or head[:4] != b"glTF":
            return None
        jlen = struct.unpack("<I", head[12:16])[0]
        f.seek(20 + jlen)
        chunk = f.read(8)
        if len(chunk) < 8 or chunk[4:8] != b"BIN\0":
            return None
        return 20 + jlen + 8


def images(project: sl.Project, path: Path, g: dict) -> list[dict]:
    """Every image of a glTF with its size, format and the material slots that use it."""
    views = g.get("bufferViews", [])
    buffers = g.get("buffers", [])
    is_glb = path.suffix.lower() == ".glb"
    bin_at = _glb_bin_offset(path) if is_glb else None
    slots: dict[int, set[str]] = {}

    def source(ti: int | None) -> int | None:
        tex = g.get("textures", [])
        if ti is None or ti >= len(tex):
            return None
        t = tex[ti]
        for ext in ("EXT_texture_webp", "KHR_texture_basisu", "EXT_texture_avif"):
            if ext in t.get("extensions", {}):
                return t["extensions"][ext].get("source")
        return t.get("source")

    for m in g.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        for slot, ref in (("baseColor", pbr.get("baseColorTexture")), ("metallicRoughness", pbr.get("metallicRoughnessTexture")),
                          ("normal", m.get("normalTexture")), ("occlusion", m.get("occlusionTexture")),
                          ("emissive", m.get("emissiveTexture"))):
            if ref:
                s = source(ref.get("index"))
                if s is not None:
                    slots.setdefault(s, set()).add(slot)

    out = []
    for i, im in enumerate(g.get("images", [])):
        head = b""
        try:
            if "bufferView" in im and im["bufferView"] < len(views):
                bv = views[im["bufferView"]]
                buf = buffers[bv.get("buffer", 0)] if bv.get("buffer", 0) < len(buffers) else {}
                if is_glb and "uri" not in buf and bin_at is not None:
                    with path.open("rb") as f:
                        f.seek(bin_at + bv.get("byteOffset", 0))
                        head = f.read(min(bv.get("byteLength", 0), HEAD))
                elif buf.get("uri") and not buf["uri"].startswith("data:"):
                    bp = (path.parent / unquote(buf["uri"])).resolve()
                    if bp.is_file() and (project.root in bp.parents):
                        with bp.open("rb") as f:
                            f.seek(bv.get("byteOffset", 0))
                            head = f.read(min(bv.get("byteLength", 0), HEAD))
            elif im.get("uri") and not im["uri"].startswith("data:") and "://" not in im["uri"]:
                ip = (path.parent / unquote(im["uri"])).resolve()
                if ip.is_file() and (project.root in ip.parents):
                    with ip.open("rb") as f:
                        head = f.read(HEAD)
        except (OSError, KeyError, TypeError, ValueError):
            head = b""
        size = image_size(head) if head else None
        mime = im.get("mimeType", "")
        out.append({"index": i, "name": im.get("name") or (im.get("uri") or "").split("/")[-1] or f"image_{i}",
                    "w": size[0] if size else None, "h": size[1] if size else None,
                    "format": size[2] if size else (mime.split("/")[-1] if mime else None),
                    "slots": sorted(slots.get(i, ()))})
    return out


# ── health ───────────────────────────────────────────────────────────────────


def shipped(asset: sl.Asset, v: sl.Variant) -> bool:
    """The file the user gets: kiln's _final, or any model outside kiln's layout."""
    return not asset.kiln or v.label.split(".")[0] == "final"


def _tris_check(tris: int, cfg: dict, name: str) -> dict:
    tier = (cfg.get("tier") or "").lower().split()[0] if cfg.get("tier") else ""
    assumed = []
    if tier not in TIERS:
        if tier == "custom":
            return _check("tris", "Triangles", "info", f"{tris:,} tris, custom tier: no range to compare with",
                          value=tris)
        tier = "balanced"
        assumed.append("tier")
    if not cfg.get("type"):
        assumed.append("type")
    cat = category_of(cfg.get("type", ""))
    lo, hi = TIERS[tier][cat]
    rng = f"{tier} {CATEGORY_LABEL[cat]} range {kfmt(lo)}–{kfmt(hi)}"
    note = f" (assumed {' and '.join(assumed)}: no production log says)" if assumed else ""
    base = {"value": tris, "range": [lo, hi], "tier": tier, "category": cat}
    if tris > 2 * hi:
        return _check("tris", "Triangles", "warn",
                      f"{tris:,} tris, over twice the {rng} (+{tris / hi - 1:.0%}): propose a reduction, "
                      f"never cut silently (rule 6){note}", **base)
    if tris > hi:
        return _check("tris", "Triangles", "info",
                      f"{tris:,} tris, above the {rng} (+{tris / hi - 1:.0%}): fine where they show "
                      f"(round parts, wires); report it, do not cut (rule 4){note}", **base)
    if tris < lo:
        return _check("tris", "Triangles", "info", f"{tris:,} tris, under the {rng}: fine if it reads{note}", **base)
    return _check("tris", "Triangles", "ok", f"{tris:,} tris, within the {rng}{note}", **base)


def _scale_checks(st: dict, cfg: dict, name: str, kiln: bool) -> list[dict]:
    dims = st.get("dimensions_blender")
    bb = st.get("bbox")
    if not dims or not bb:
        return []
    out = []
    x, y, z = dims
    biggest = max(dims)
    if biggest < 0.01:
        out.append(_check("scale", "Size", "warn",
                          f"{biggest * 1000:.1f} mm at its largest: probably exported in the wrong unit (1 unit = 1 m)"))
    elif biggest > 100:
        out.append(_check("scale", "Size", "warn",
                          f"{biggest:,.0f} m at its largest: probably exported in the wrong unit (1 unit = 1 m)"))
    else:
        words = _words(name, cfg.get("type", ""))
        hit = next((k for k in EXPECTED_HEIGHT if k in words), None)
        if hit:
            want = EXPECTED_HEIGHT[hit]
            off = z / want - 1
            level = "info" if abs(off) > 0.35 else "ok"
            out.append(_check("scale", "Size", level,
                              f"{z:.2f} m tall; a {hit} is usually ~{want:.2f} m"
                              + (f" ({off:+.0%}): check the scale, or say why" if level == "info" else ""),
                              value=z, expected=want))
        else:
            out.append(_check("scale", "Size", "ok", f"{x:.2f} × {y:.2f} × {z:.2f} m (X × Y × Z), 1 unit = 1 m"))
    # kiln's convention: origin at the centre of the base, sitting on Z = 0 (glTF Y).
    zmin = bb["min"][1]
    tol = max(0.001, 0.01 * z)
    cx = (bb["min"][0] + bb["max"][0]) / 2
    cy = -(bb["min"][2] + bb["max"][2]) / 2   # Blender Y is glTF -Z
    off_c = max(abs(cx) / max(x, 1e-6), abs(cy) / max(y, 1e-6))
    lvl = "warn" if kiln else "info"
    if abs(zmin) > tol:
        out.append(_check("ground", "On the ground", lvl,
                          f"{'floats' if zmin > 0 else 'sinks'} {abs(zmin):.3f} m {'above' if zmin > 0 else 'below'} "
                          f"Z = 0: kiln sets the origin at the centre of the base", value=zmin))
    elif off_c > 0.05:
        out.append(_check("ground", "On the ground", "info",
                          f"on Z = 0, off-centre by X {cx:+.3f} m, Y {cy:+.3f} m: the origin is not under the middle"))
    else:
        out.append(_check("ground", "On the ground", "ok", "on Z = 0, centred on the origin"))
    return out


def _texture_checks(ims: list[dict], cfg: dict, is_shipped: bool, label: str) -> list[dict]:
    if not ims:
        return []
    cap = texture_cap(cfg.get("target", ""))
    target = cfg.get("target") or "glTF (assumed)"
    known = [i for i in ims if i["w"]]
    over = [i for i in known if max(i["w"], i["h"]) > cap]
    biggest = max((max(i["w"], i["h"]) for i in known), default=0)
    sizes = ", ".join(f"{i['w']}×{i['h']}" + (f" {'/'.join(i['slots'])}" if i["slots"] else "") for i in known[:6])
    sizes += f", +{len(known) - 6}" if len(known) > 6 else ""
    out = []
    if not is_shipped:
        out.append(_check("textures", "Textures", "info",
                          f"{len(ims)} image(s), largest {biggest}px — the cap ({cap}px for {target}) is checked "
                          f"on _final; {label} is not the shipped file", images=ims))
    elif over:
        out.append(_check("textures", "Textures", "warn",
                          f"{len(over)} of {len(ims)} image(s) above the {cap}px cap for {target}: {sizes}. "
                          f"OPTIMIZE resizes them (2048 only for console/PC or close-ups)", images=ims))
    else:
        out.append(_check("textures", "Textures", "ok", f"{len(ims)} image(s), all within the {cap}px cap for {target}",
                          images=ims))
    return out


def _compression_checks(st: dict, ims: list[dict], is_shipped: bool, label: str) -> list[dict]:
    ext = set(st.get("extensions", []))
    draco = "KHR_draco_mesh_compression" in ext
    meshopt = "EXT_meshopt_compression" in ext
    geo = "Draco" if draco else "meshopt" if meshopt else None
    fmts = {i["format"] for i in ims if i["format"]}
    light = fmts and fmts <= {"webp", "ktx2", "avif"}
    if not is_shipped:
        return [_check("compression", "Compression", "info",
                       f"{label} keeps the uncompressed file on purpose; compression is checked on _final")]
    parts, level = [], "ok"
    if geo:
        parts.append(f"geometry {geo}" + (" (the client needs a Draco decoder)" if draco else ""))
    else:
        level = "warn"
        parts.append("geometry not compressed: OPTIMIZE adds Draco, as its own step (rule 20)")
    if ims:
        if light:
            parts.append(f"textures {', '.join(sorted(f.upper() for f in fmts))}")
        else:
            level = "warn"
            parts.append(f"textures {', '.join(sorted(f.upper() for f in fmts)) or 'of unknown format'}: OPTIMIZE converts them to WebP")
    return [_check("compression", "Compression", level, "; ".join(parts), draco=draco, meshopt=meshopt,
                   formats=sorted(fmts))]


def licence_check(log: dict, has_log: bool) -> dict:
    if not has_log:
        return _check("licence", "Licences", "info", "no production log beside the model: licences unknown")
    lines = [b for b in log["sections"].get("licenses", log["sections"].get("licences", []))
             if not re.match(r"^\s*(none|n/?a|-)\s*$", b, re.I)]
    if not lines:
        return _check("licence", "Licences", "info", "the log records no licence")
    entries, level = [], "ok"
    for b in lines:
        if re.search(r"\bNC\b|non-?commercial", b, re.I):
            kind, lv = "non-commercial", "warn"
        elif re.search(r"CC[- ]?BY", b, re.I):
            kind, lv = "attribution required", "info"
        elif re.search(r"CC0|public domain|\bMIT\b|apache", b, re.I):
            kind, lv = "free", "ok"
        else:
            kind, lv = "check the terms", "info"
        entries.append({"text": b, "kind": kind, "level": lv})
        level = max(level, lv, key=RANK.get)
    head = {"ok": "free to use", "info": "credit or terms needed", "warn": "non-commercial use only"}[level]
    return _check("licence", "Licences", level, f"{len(entries)} source(s), {head}", entries=entries)


_health_cache: dict[tuple, list[dict]] = {}


def health(project: sl.Project, asset: sl.Asset, v: sl.Variant, log: dict | None = None) -> list[dict]:
    """kiln's rules against one variant. Cached by the file's content and the log's mtime."""
    logp = project.root / asset.log_file() if asset.log_file() else None
    try:
        log_m = logp.stat().st_mtime if logp else 0
    except OSError:
        log_m = 0
    v.hash = v.hash or sl.file_hash(v.path)
    key = (asset.id, v.rel, v.hash, log_m)
    if key in _health_cache:
        return _health_cache[key]
    log = log if log is not None else parse_log(logp)
    cfg = log["config"]
    is_shipped = shipped(asset, v)
    out: list[dict] = []
    st = sl.variant_stats(v)
    if st is None:
        out.append(_check("format", "Format", "info", f"{v.path.suffix.upper().lstrip('.')}: Studio reads stats from glTF files only"))
    elif "error" in st:
        out.append(_check("format", "Format", "warn", f"could not read the file: {st['error']}"))
    else:
        out.append(_tris_check(st["tris"], cfg, asset.name))
        out += _scale_checks(st, cfg, asset.name, asset.kiln)
        try:
            ims = images(project, v.path, sl.read_gltf_json(v.path))
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            ims = []
        out += _texture_checks(ims, cfg, is_shipped, v.label)
        out += _compression_checks(st, ims, is_shipped, v.label)
    if asset.kiln or logp:
        out.append(licence_check(log, bool(logp)))
    if len(_health_cache) > 512:
        _health_cache.clear()
    _health_cache[key] = out
    return out


def worst(checks: list[dict]) -> str:
    return max((c["level"] for c in checks), key=RANK.get, default="ok")


# ── fidelity: tools/fidelity_check.py's measures against the reference photo ─


def _rel_if_inside(project: sl.Project, p: str | None) -> str | None:
    if not p:
        return None
    try:
        q = Path(p).resolve()
        return project.rel(q) if q.is_file() and (project.root in q.parents) else None
    except (OSError, ValueError):
        return None


def fidelity_runs(project: sl.Project, asset: sl.Asset) -> list[dict]:
    """The fidelity measures of this asset, latest first: one per `review*/` folder (one per
    reference view), read from the `fidelity.json` the tool writes there."""
    base = project.root / asset.folder
    if not base.is_dir():
        return []
    found: list[Path] = []
    for d in sorted(base.iterdir()):
        if d.is_dir() and d.name.lower().startswith("review") and not d.name.startswith("."):
            found += [f for f in [d / "fidelity.json", *sorted(d.glob("*/fidelity.json"))] if f.is_file()]
    current = {v.hash or sl.file_hash(v.path): v.label for v in asset.variants}
    runs = []
    for f in found:
        try:
            data = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        model = str(data.get("model") or "")
        # A review folder shared by several loose models: keep the runs of this one.
        if not asset.kiln and model and not Path(model).name.startswith(asset.name):
            continue
        d = f.parent
        trend = []
        logf = d / "fidelity_log.jsonl"
        if logf.is_file():
            for line in logf.read_text(errors="replace").splitlines()[-20:]:
                try:
                    e = json.loads(line)
                    trend.append({"at": e.get("at"), "iou": e.get("iou"), "gaps": e.get("gaps"),
                                  "model_hash": e.get("model_hash")})
                except ValueError:
                    pass
        h = data.get("model_hash")
        joints = sorted(d.glob("joints/*.png"))[:24]
        runs.append({
            "dir": project.rel(d), "at": data.get("at"), "mtime": f.stat().st_mtime,
            "iou": data.get("iou"), "gaps": data.get("gaps", []), "shape": data.get("shape", []),
            "tris": data.get("tris"), "max_tris": data.get("max_tris"),
            "view": data.get("view", "front"), "elevation": data.get("elevation", 0), "azimuth": data.get("azimuth", 0),
            "model": Path(model).name if model else None, "model_hash": h,
            "measured": current.get(h), "current": h in current if h else None,
            "reference": _rel_if_inside(project, data.get("reference")),
            "reference_name": Path(str(data.get("reference") or "")).name or None,
            "overlay": project.rel(d / "overlay.png") if (d / "overlay.png").is_file() else None,
            "side_by_side": project.rel(d / "side_by_side.png") if (d / "side_by_side.png").is_file() else None,
            "joints": [project.rel(j) for j in joints],
            "trend": trend,
        })
    runs.sort(key=lambda r: r["mtime"], reverse=True)
    return runs


# ── batch: the wizard's token estimate, from the manifest ───────────────────


def _scalar(v: str) -> str:
    v = v.strip()
    if v and v[0] in "\"'":
        q = v[0]
        end = v.find(q, 1)
        return v[1:end] if end > 0 else v[1:]
    return re.sub(r"\s+#.*$", "", v).strip()


def parse_manifest(text: str) -> dict:
    """The parts of batch-manifest.yaml the estimate needs: the batch name, the default
    tier, and per asset its name, method, status and tier. Line-based: the manifest is
    generated by the wizard in one known shape (batch-mode.md § Batch Manifest Format)."""
    out: dict = {"name": None, "tier": None, "assets": []}
    top = None
    item: dict | None = None
    key_indent = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0:
            top = line.split(":", 1)[0].strip()
            item = None
            continue
        if top in ("batch", "config"):
            m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
            if m and indent <= 2:
                k, v = m.group(1), _scalar(m.group(2))
                if top == "batch" and k == "name":
                    out["name"] = v
                if top == "config" and k == "tier":
                    out["tier"] = v
        elif top == "assets":
            m = re.match(r"^-\s+(\w[\w-]*):\s*(.*)$", line)
            if m:
                item = {m.group(1): _scalar(m.group(2))}
                out["assets"].append(item)
                key_indent = indent + 2
                continue
            m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
            if m and item is not None and indent == key_indent:
                item[m.group(1)] = _scalar(m.group(2))
    return out


def tokens_for(method: str) -> tuple[int, int] | None:
    base = TOKENS.get((method or "").strip().lower())
    return (base[0], round(base[1] * HIGH_FACTOR)) if base else None


def manifest_for(project: sl.Project, folder: str) -> Path | None:
    d = project.root / folder
    for name in MANIFESTS:
        if (d / name).is_file():
            return d / name
    return None


def batch_estimate(project: sl.Project, folder: str, asset_name: str | None = None) -> dict | None:
    """The batch folder's token estimate (batch-mode.md § Step 4): per method, low x 1.0
    to high x 1.5, for the whole batch, for what is left to run, and for one asset."""
    mp = manifest_for(project, folder)
    if not mp:
        return None
    try:
        m = parse_manifest(mp.read_text(errors="replace"))
    except (OSError, ValueError, IndexError, KeyError, TypeError):
        return None  # hand-edited into a shape the reader does not know: no estimate
    total, left = [0, 0], [0, 0]
    n_left, unknown, by_method = 0, [], {}
    mine = None
    for a in m["assets"]:
        rng = tokens_for(a.get("method", ""))
        status = (a.get("status") or "pending").lower()
        if a.get("name") == asset_name:
            mine = {"name": a.get("name"), "method": a.get("method"), "status": status, "range": rng}
        if not rng:
            unknown.append(a.get("name") or "?")
            continue
        by_method[a["method"]] = by_method.get(a["method"], 0) + 1
        total[0] += rng[0]
        total[1] += rng[1]
        if status != "done":
            n_left += 1
            left[0] += rng[0]
            left[1] += rng[1]
    return {"manifest": project.rel(mp), "name": m["name"] or Path(folder).name, "tier": m["tier"],
            "assets": len(m["assets"]), "by_method": by_method, "range": total,
            "remaining": {"assets": n_left, "range": left}, "unknown": unknown, "asset": mine,
            "note": "estimate ±50%: network retries, material complexity and errors can double one asset"}


def fmt_range(r: list[int] | tuple[int, int] | None) -> str:
    if not r:
        return "–"
    return f"~{kfmt(r[0])}–{kfmt(r[1])} tokens" if r[0] != r[1] else f"~{kfmt(r[0])} tokens"


# ── all of it, for one asset ─────────────────────────────────────────────────


def asset_checks(project: sl.Project, asset: sl.Asset) -> dict:
    logp = project.root / asset.log_file() if asset.log_file() else None
    log = parse_log(logp)
    per_variant = {v.label: health(project, asset, v, log) for v in asset.variants}
    ship = next((v for v in asset.variants if shipped(asset, v)), None)
    batch = None
    if asset.kiln and asset.folder not in (".", ""):
        batch = batch_estimate(project, str(Path(asset.folder).parent), asset.name)
    return {"health": per_variant, "shipped": ship.label if ship else None,
            "config": log["config"], "fidelity": fidelity_runs(project, asset), "batch": batch}
