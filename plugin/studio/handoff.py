"""A model's hand-off: every output in one zip, with a sheet that says what each file is for.

    listing(project, asset, lang)                    -> the outputs and their files (the dialog)
    make_package(project, asset, lang, outs, sheet)  -> (zip name, zip bytes)

The outputs keep their folders (web/, game/, ar/, print/; a final at the root, from
before, goes in web/). Only the deliverables: a print's working .blend or a check's
report stay in the project, and so does the source (.blend, _original, the log). The
sheet (LISEZ-MOI.md in French, README.md otherwise) gives the size, each file's use,
its triangles, the outputs made before the model last changed, and the licences the
production log records. Standard library only.
"""
from __future__ import annotations

import io
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


def contents(a: sl.Asset) -> tuple[list[tuple[str, str, Path]], list[str]]:
    """The deliverables, in order — (output, folder, path) — and the outputs to redo."""
    src = next((v for v in a.variants if v.label == "original"), None)
    files: list[tuple[str, str, Path]] = []
    stale: list[str] = []
    for v in a.variants:
        out = output_of(v)
        if not out:
            continue
        if src and v is not src and v.mtime + 1 < src.mtime and out not in stale:
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
    if out == "web":
        draco = ext in (".glb", ".gltf") and "KHR_draco_mesh_compression" in (sl.read_gltf_json(f).get("extensionsUsed") or [])
        return w["web"] if draco else w["web_plain"]
    if out == "ar":
        return w["ar_usdz"] if ext == ".usdz" else w["ar_glb"]
    if out == "print":
        return w["print_3mf"] if ext == ".3mf" else w["print_stl"]
    return w["game"]


def listing(project: sl.Project, a: sl.Asset, lang: str = "en") -> list[dict]:
    """The outputs a package can hold, for the download dialog: each with its files."""
    files, stale = contents(a)
    rows: dict[str, dict] = {}
    for out, folder, f in files:
        r = rows.setdefault(out, {"out": out, "stale": out in stale, "files": []})
        r["files"].append({"path": f"{folder}/{f.name}", "file": f.relative_to(project.root).as_posix(), "size": f.stat().st_size, "use": use_of(out, f, lang)})
    return list(rows.values())


def make_package(project: sl.Project, a: sl.Asset, lang: str = "en", outs: list[str] | None = None,
                 sheet: bool = True) -> tuple[str, bytes]:
    """outs: the outputs to put in (all when None); sheet: the LISEZ-MOI / README with them."""
    w = WORDS.get(lang, WORDS["en"])
    src = next((v for v in a.variants if v.label == "original"), None)
    files, stale = contents(a)
    if outs is not None:
        files = [x for x in files if x[0] in outs]
        stale = [o for o in stale if o in outs]
    # The sheet.
    dims = (sl.variant_stats(src) if src else None) or {}
    dims = dims.get("dimensions_blender") or next(
        ((sl.variant_stats(v) or {}).get("dimensions_blender") for v in a.variants if (sl.variant_stats(v) or {}).get("dimensions_blender")), None)
    lines = [f"# {a.name}", "", w["made"].format(date=time.strftime("%d/%m/%Y" if lang == "fr" else "%Y-%m-%d"))
             + (" · " + w["size"].format(x=_num(dims[0] * 100, lang, 1), y=_num(dims[1] * 100, lang, 1), z=_num(dims[2] * 100, lang, 1)) if dims else ""), "",
             f"## {w['files']}", "", w["head"], "|---|---|---|---|---|"]
    for out, folder, f in files:
        ext = f.suffix.lower()
        st = sl.stl_stats(f) if ext == ".stl" else sl.threemf_stats(f) if ext == ".3mf" else \
            sl.gltf_stats(f) if ext in (".glb", ".gltf") else {}
        use = use_of(out, f, lang)
        tris = st.get("tris")
        lines.append(f"| {folder}/ | `{f.name}` | {use} | {_kb(f.stat().st_size, lang)} | {_num(tris, lang) if tris else '—'} |")
    if stale:
        lines += ["", w["stale"].format(outs=", ".join(w["outs"][o] for o in stale))]
    logp = project.root / a.log_file() if a.log_file() else None
    lic = checks.licence_check(checks.parse_log(logp), bool(logp and logp.is_file()))
    lines += ["", f"## {w['lic']}", ""]
    if not (logp and logp.is_file()):
        lines.append(w["lic_nolog"])
    elif not lic.get("entries"):
        lines.append(w["lic_none"])
    else:
        lines += [f"- {e['text']} — {w['lic_kind'][e['kind']]}" for e in lic["entries"]]
    lines += ["", f"## {w['kept']}", "", w["kept_text"].format(dir=a.folder if a.folder != "." else a.id), ""]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if sheet:
            z.writestr(f"{a.name}/{w['sheet']}", "\n".join(lines))
        for _out, folder, f in files:
            z.write(f, f"{a.name}/{folder}/{f.name}")
    return f"{a.name}.zip", buf.getvalue()

