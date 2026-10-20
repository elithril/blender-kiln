"""A model's hand-off: every output in one zip, with a sheet that says what each file is for.

    listing(project, asset, lang)                              -> the outputs, the variations (the dialog)
    make_package(project, asset, lang, outs, sheet, variants)  -> (zip name, zip bytes)

The outputs keep their folders (web/, game/, ar/, print/; a final at the root, from
before, goes in web/). Only the deliverables: a print's working .blend or a check's
report stay in the project, and so does the source (.blend, _original, the log). The
sheet (LISEZ-MOI.md in French, README.md otherwise) gives the size, each file's use,
its triangles, the outputs made before the model last changed, and the licences the
production log records. Standard library only.
"""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import checks
import studiolib as sl

WORDS = {
    "en": {
        "sheet": "README.md", "made": "Prepared with kiln on {date}", "size": "{x} × {y} × {z} cm (width × depth × height)",
        "files": "The files", "head": "| Folder | File | For | Size | Triangles |",
        "web": "a website — glTF, Draco-compressed: the site needs a Draco decoder (three.js: DRACOLoader)",
        "web_plain": "a website — glTF",
        "game": "Unity, Unreal", "ar_usdz": "iPhone, iPad, Vision Pro (AR Quick Look)", "ar_glb": "Android (Scene Viewer)",
        "print_3mf": "the slicer: every part, in millimetres", "print_stl": "one part, in millimetres",
        "stale": "**To redo:** {outs} — made before the model last changed.",
        "lic": "Licences", "lic_none": "Nothing from outside: kiln made all of it.",
        "lic_nolog": "No production log: check the licences of anything downloaded before publishing.",
        "lic_kind": {"non-commercial": "not for commercial use", "attribution required": "credit the author",
                     "free": "free to use", "check the terms": "read the terms"},
        "kept": "Not in this package", "kept_text": "The source (the .blend, `_original.glb`, the production log) stays in the project: `{dir}/`.",
        "outs": {"web": "Web", "game": "Game", "ar": "AR", "print": "3D print"},
        "variant": "Variation · {name}", "variants_dir": "variations",
        "finishes": " — {n} finishes (glTF material variants): {list}",
    },
    "fr": {
        "sheet": "LISEZ-MOI.md", "made": "Préparé avec kiln le {date}", "size": "{x} × {y} × {z} cm (largeur × profondeur × hauteur)",
        "files": "Les fichiers", "head": "| Dossier | Fichier | Pour | Taille | Triangles |",
        "web": "un site web — glTF compressé en Draco : le site doit avoir un décodeur Draco (three.js : DRACOLoader)",
        "web_plain": "un site web — glTF",
        "game": "Unity, Unreal", "ar_usdz": "iPhone, iPad, Vision Pro (AR Quick Look)", "ar_glb": "Android (Scene Viewer)",
        "print_3mf": "le trancheur : toutes les pièces, en millimètres", "print_stl": "une pièce, en millimètres",
        "stale": "**À refaire :** {outs} — faites avant la dernière modification du modèle.",
        "lic": "Licences", "lic_none": "Rien de l'extérieur : kiln a tout fait.",
        "lic_nolog": "Pas de journal de fabrication : vérifier les licences de ce qui a été téléchargé avant de publier.",
        "lic_kind": {"non-commercial": "pas d'usage commercial", "attribution required": "créditer l'auteur",
                     "free": "libre d'usage", "check the terms": "lire les conditions"},
        "kept": "Pas dans ce paquet", "kept_text": "La source (le .blend, `_original.glb`, le journal de fabrication) reste dans le projet : `{dir}/`.",
        "outs": {"web": "Web", "game": "Jeu", "ar": "AR", "print": "Impression 3D"},
        "variant": "Variante · {name}", "variants_dir": "variantes",
        "finishes": " — {n} finitions (variantes de matériaux glTF) : {list}",
    },
}


def output_of(v: sl.Variant) -> str | None:
    kind = v.label.split(".")[0]
    if kind in ("print", "game", "ar"):
        return kind
    if kind == "final" and v.path.suffix.lower() in (".glb", ".gltf"):
        return "web"
    return None


def _kb(n: int, lang: str) -> str:
    unit = ("Ko", "o") if lang == "fr" else ("KB", "B")
    return f"{_num(round(n / 1024), lang)} {unit[0]}" if n >= 1024 else f"{n} {unit[1]}"


def _num(x: float, lang: str, digits: int = 0) -> str:
    """1,234.5 in English, 1 234,5 in French (a narrow space between thousands)."""
    s = f"{x:,.{digits}f}"
    return s.replace(",", "\u202f").replace(".", ",") if lang == "fr" else s


def contents(a: sl.Asset, project: sl.Project | None = None) -> tuple[list[tuple[str, str, Path]], list[str]]:
    """The deliverables, in order — (output, folder, path) — and the outputs to redo (made
    before the shape last changed: new finishes are not a change of shape)."""
    src = next((v for v in a.variants if v.label == "original"), None)
    since = (sl.shape_since(project, a) if project and a.kiln else None) or (src.mtime if src else None)
    files: list[tuple[str, str, Path]] = []
    stale: list[str] = []
    for v in a.variants:
        out = output_of(v)
        if not out:
            continue
        if since and v is not src and v.mtime + 1 < since and out not in stale:
            stale.append(out)
        folder = out
        if out in ("print", "ar") and v.path.parent.name == out:
            # The whole folder's deliverables: a print's parts, AR's two files.
            for f in sorted(v.path.parent.iterdir()):
                if f.is_file() and f.suffix.lower() in sl.MODEL_EXTS and (out, folder, f) not in files:
                    files.append((out, folder, f))
        else:
            files.append((out, folder, v.path))
    uniq: dict[tuple[str, str], tuple[str, str, Path]] = {}
    for out, folder, f in files:   # a final at the root and one in web/: the first, once
        uniq.setdefault((folder, f.name), (out, folder, f))
    order = ["web", "game", "ar", "print"]
    return sorted(uniq.values(), key=lambda x: (order.index(x[0]), x[2].suffix.lower() != ".3mf", x[2].name)), stale


def use_of(out: str, f: Path, lang: str = "en") -> str:
    """What a file is for, in a line."""
    w = WORDS.get(lang, WORDS["en"])
    ext = f.suffix.lower()
    fin = ""
    if ext in (".glb", ".gltf"):
        names = [v.get("name", "") for v in (sl.read_gltf_json(f).get("extensions") or {}).get("KHR_materials_variants", {}).get("variants", [])]
        fin = w["finishes"].format(n=len(names), list=", ".join(names)) if len(names) > 1 else ""
    if out == "web":
        draco = ext in (".glb", ".gltf") and "KHR_draco_mesh_compression" in (sl.read_gltf_json(f).get("extensionsUsed") or [])
        return (w["web"] if draco else w["web_plain"]) + fin
    if out == "ar":
        return w["ar_usdz"] if ext == ".usdz" else w["ar_glb"] + fin
    if out == "print":
        return w["print_3mf"] if ext == ".3mf" else w["print_stl"]
    return w["game"]


def variants_of(project: sl.Project, a: sl.Asset) -> list[sl.Asset]:
    """The models declined from this one (Studio's variations), in the order made."""
    ids = sl.derivations(sl.load_catalog(project), a.id)
    return [x for x in sl.scan(project) if x.id in ids]


def _rows(project: sl.Project, a: sl.Asset, lang: str) -> list[dict]:
    files, stale = contents(a, project)
    rows: dict[str, dict] = {}
    for out, folder, f in files:
        r = rows.setdefault(out, {"out": out, "stale": out in stale, "files": []})
        r["files"].append({"path": f"{folder}/{f.name}", "file": f.relative_to(project.root).as_posix(), "size": f.stat().st_size, "use": use_of(out, f, lang)})
    return list(rows.values())


def listing(project: sl.Project, a: sl.Asset, lang: str = "en") -> dict:
    """What a package can hold, for the download dialog: the outputs and their files, and
    the variations with theirs."""
    cat = sl.load_catalog(project)["assets"]
    glbs = [f for _o, _fo, f in contents(a, project)[0] if f.suffix.lower() == ".glb"]
    names, own = next((st for st in (finish_state(f) for f in glbs) if len(st[0]) > 1), ([], None))
    return {"outputs": _rows(project, a, lang), "finishes": {"names": names, "shown": own},
            "variants": [{"id": v.id, "name": v.name, "text": (cat.get(v.id, {}).get("derived") or {}).get("text", ""),
                          "outputs": _rows(project, v, lang)} for v in variants_of(project, a)]}


def _table(files: list[tuple[str, str, Path]], stale: list[str], w: dict, lang: str, prefix: str = "") -> list[str]:
    lines = [w["head"], "|---|---|---|---|---|"]
    for out, folder, f in files:
        ext = f.suffix.lower()
        st = sl.stl_stats(f) if ext == ".stl" else sl.threemf_stats(f) if ext == ".3mf" else \
            sl.gltf_stats(f) if ext in (".glb", ".gltf") else {}
        tris = st.get("tris")
        lines.append(f"| {prefix}{folder}/ | `{f.name}` | {use_of(out, f, lang)} | {_kb(f.stat().st_size, lang)} | {_num(tris, lang) if tris else '—'} |")
    if stale:
        lines += ["", w["stale"].format(outs=", ".join(w["outs"][o] for o in stale))]
    return lines


def finish_state(path: Path) -> tuple[list[str], str | None]:
    """A glTF file's finishes, and the one it shows by itself (its meshes' own material)."""
    g = sl.read_gltf_json(path)
    names = [v.get("name", "") for v in (g.get("extensions") or {}).get("KHR_materials_variants", {}).get("variants", [])]
    for m in g.get("meshes") or []:
        for p in m.get("primitives") or []:
            for x in (p.get("extensions") or {}).get("KHR_materials_variants", {}).get("mappings", []):
                if x.get("material") == p.get("material") and x.get("variants"):
                    return names, names[x["variants"][0]]
    return names, names[0] if names else None


def with_finishes(path: Path, keep: list[str], shown: str | None) -> bytes:
    """A GLB with only the finishes kept, showing `shown` by itself: its JSON rewritten, its
    binary as it is (then pruned by gltf-transform when it is there, so the textures of the
    finishes left out go too). One finish kept: the extension goes, the file is plain."""
    import shutil
    import struct
    import subprocess
    import tempfile
    b = path.read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    g = json.loads(b[20:20 + n])
    names = [v.get("name", "") for v in g["extensions"]["KHR_materials_variants"]["variants"]]
    old_new = {i: k for k, i in enumerate(i for i, nm in enumerate(names) if nm in keep)}
    kept = [names[i] for i in sorted(old_new)]
    show = old_new.get(names.index(shown)) if shown in names else None
    for m in g.get("meshes") or []:
        for p in m.get("primitives") or []:
            ext = (p.get("extensions") or {}).get("KHR_materials_variants")
            if not ext:
                continue
            maps = []
            for x in ext.get("mappings", []):
                vs = [old_new[v] for v in x.get("variants", []) if v in old_new]
                if vs:
                    maps.append({**x, "variants": vs})
                if show is not None and show in vs:
                    p["material"] = x["material"]
            if len(kept) > 1:
                ext["mappings"] = maps
            else:
                p["extensions"].pop("KHR_materials_variants")
                if not p["extensions"]:
                    p.pop("extensions")
    if len(kept) > 1:
        g["extensions"]["KHR_materials_variants"]["variants"] = [{"name": nm} for nm in kept]
    else:
        g["extensions"].pop("KHR_materials_variants")
        if not g["extensions"]:
            g.pop("extensions")
        g["extensionsUsed"] = [e for e in g.get("extensionsUsed", []) if e != "KHR_materials_variants"]
        if not g["extensionsUsed"]:
            g.pop("extensionsUsed")
    j = json.dumps(g, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    rest = b[20 + n:]
    out = b[:8] + struct.pack("<I", 12 + 8 + len(j) + len(rest)) + struct.pack("<I", len(j)) + b"JSON" + j + rest
    tool = shutil.which("gltf-transform")
    if tool:
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "in.glb", Path(d) / "out.glb"
            src.write_bytes(out)
            try:
                r = subprocess.run([tool, "prune", str(src), str(dst)], capture_output=True, timeout=60)
                # prune writes the meshes uncompressed: Draco again when the file had it.
                if r.returncode == 0 and "KHR_draco_mesh_compression" in g.get("extensionsUsed", []):
                    r = subprocess.run([tool, "draco", str(dst), str(dst)], capture_output=True, timeout=120)
                if r.returncode == 0 and dst.is_file() and finish_state(dst)[0] == (kept if len(kept) > 1 else []):
                    out = dst.read_bytes()
            except (OSError, subprocess.TimeoutExpired):
                pass   # the JSON alone: the left-out textures stay in the file, unused
    return out


def make_package(project: sl.Project, a: sl.Asset, lang: str = "en", outs: list[str] | None = None,
                 sheet: bool = True, variants: list[str] | None = None, finishes: list[str] | None = None,
                 shown: str | None = None) -> tuple[str, bytes]:
    """outs: the outputs to put in (all when None); sheet: the LISEZ-MOI / README with them;
    variants: the variations to add (ids of models declined from this one), each in
    variants/<its name>/ with its outputs; finishes / shown: in the model's glTF files, only
    these finishes, this one shown by itself (the project's files keep them all)."""
    w = WORDS.get(lang, WORDS["en"])
    cat = sl.load_catalog(project)["assets"]
    parts: list[tuple[sl.Asset, str]] = [(a, "")]
    parts += [(v, f"{w['variants_dir']}/{v.name}/") for v in variants_of(project, a) if v.id in (variants or [])]
    packed: list[tuple[sl.Asset, str, list, list]] = []
    for x, prefix in parts:
        files, stale = contents(x, project)
        if outs is not None:
            files = [f for f in files if f[0] in outs]
            stale = [o for o in stale if o in outs]
        packed.append((x, prefix, files, stale))
    # The model's glTF files, with the finishes picked (the variations go as they are).
    rewritten: dict[Path, bytes] = {}
    if finishes is not None or shown:
        for _out, _folder, f in packed[0][2]:
            if f.suffix.lower() != ".glb":
                continue
            have, own = finish_state(f)
            if len(have) < 2:
                continue
            keep = [x for x in have if finishes is None or x in finishes] or [shown or own]
            if keep != have or (shown and shown != own):
                rewritten[f] = with_finishes(f, keep, shown if shown in keep else (own if own in keep else keep[0]))
    # Written beside, under the same names: the sheet reads them (size, finishes), the zip takes them.
    tmp = Path(tempfile.mkdtemp(prefix="kiln-package-")) if rewritten else None
    if rewritten:
        subs = {}
        for f, data in rewritten.items():
            t = tmp / f"{len(subs)}" / f.name
            t.parent.mkdir()
            t.write_bytes(data)
            subs[f] = t
        x, prefix, files, stale = packed[0]
        packed[0] = (x, prefix, [(o, fo, subs.get(f, f)) for o, fo, f in files], stale)
        # The sheet: the model, then each variation, then the licences of all.
    src = next((v for v in a.variants if v.label == "original"), None)
    dims = (sl.variant_stats(src) if src else None) or {}
    dims = dims.get("dimensions_blender") or next(
        ((sl.variant_stats(v) or {}).get("dimensions_blender") for v in a.variants if (sl.variant_stats(v) or {}).get("dimensions_blender")), None)
    lines = [f"# {a.name}", "", w["made"].format(date=time.strftime("%d/%m/%Y" if lang == "fr" else "%Y-%m-%d"))
             + (" · " + w["size"].format(x=_num(dims[0] * 100, lang, 1), y=_num(dims[1] * 100, lang, 1), z=_num(dims[2] * 100, lang, 1)) if dims else ""), "",
             f"## {w['files']}", ""]
    lines += _table(packed[0][2], packed[0][3], w, lang)
    for x, prefix, files, stale in packed[1:]:
        text = (cat.get(x.id, {}).get("derived") or {}).get("text", "")
        lines += ["", f"## {w['variant'].format(name=x.name)}", "", *([f"> {text}", ""] if text else []), *_table(files, stale, w, lang, prefix)]
    entries, logged, missing = [], False, False
    for x, *_ in packed:
        logp = project.root / x.log_file() if x.log_file() else None
        if logp and logp.is_file():
            logged = True
            for e in checks.licence_check(checks.parse_log(logp), True).get("entries") or []:
                if e["text"] not in [y["text"] for y in entries]:
                    entries.append(e)
        else:
            missing = True
    lines += ["", f"## {w['lic']}", ""]
    if not logged or missing and not entries:
        lines.append(w["lic_nolog"])
    elif not entries:
        lines.append(w["lic_none"])
    else:
        lines += [f"- {e['text']} — {w['lic_kind'][e['kind']]}" for e in entries]
    lines += ["", f"## {w['kept']}", "", w["kept_text"].format(dir=a.folder if a.folder != "." else a.id), ""]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if sheet:
            z.writestr(f"{a.name}/{w['sheet']}", "\n".join(lines))
        for _x, prefix, files, _stale in packed:
            for _out, folder, f in files:
                z.write(f, f"{a.name}/{prefix}{folder}/{f.name}")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return f"{a.name}.zip", buf.getvalue()

