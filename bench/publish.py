"""Copy what a bench label proves into bench/results/<label>/, small and clean.

    python3 bench/publish.py baseline-52

bench/runs/ is git-ignored and weighs hundreds of MB: transcripts full of
base64 screenshots, .blend files, throwaway Blender profiles. What a reader of
the repository needs to check a claim is much smaller:

- summary.json   every result.json of the label, one object per brief
- <brief>/       renders as WebP, the production logs the skill wrote, and the
                 shipped GLBs under MAX_GLB — larger ones are listed with their
                 size and sha256 instead, so the claim stays checkable
- nothing else   no transcript, no .blend, no concept art: a session painted
                 over a service's watermark, and that image is not ours to ship

Local paths are rewritten to <repo> / <home>, and the export FAILS if anything
personal survives — a silent leak is worse than a loud refusal.
"""
import hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
REPO = BENCH.parent
HOME = str(Path.home())
MAX_GLB = 1_000_000
TEXT = {".md", ".yaml", ".json"}


def scrub(text):
    return text.replace(str(REPO), "<repo>").replace(HOME, "<home>")


def assert_clean(root):
    user = Path.home().name
    bad = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in TEXT:
            t = p.read_text(errors="ignore")
            leaks = [user] if user in t else []
            leaks += re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", t)       # any e-mail address
            if leaks:
                bad.append(f"{p.relative_to(root)}: {sorted(set(leaks))[:3]}")
    if bad:
        sys.exit(f"personal data survived the scrub, nothing published: {bad}")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    label = sys.argv[1]
    src = BENCH / "runs" / label
    dst = BENCH / "results" / label
    if not src.is_dir():
        sys.exit(f"no runs under {src}")
    if shutil.which("cwebp") is None:
        sys.exit("cwebp is required (brew install webp)")
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)

    summary = {}
    for rj in sorted(src.glob("*/result.json")):
        brief = rj.parent.name
        res = json.loads(scrub(rj.read_text()))
        out = dst / brief
        out.mkdir()
        for png in sorted(rj.parent.glob("render-*.png")):
            webp = out / (png.stem + ".webp")
            r = subprocess.run(["cwebp", "-quiet", "-q", "85", "-resize", "1000", "0", str(png), "-o", str(webp)])
            if r.returncode != 0:
                sys.exit(f"cwebp failed on {png}")
        shipped = []
        work = rj.parent / "work"
        for glb in sorted(work.rglob("*_final.glb")):
            size = glb.stat().st_size
            entry = {"file": glb.name, "bytes": size,
                     "sha256": hashlib.sha256(glb.read_bytes()).hexdigest()}
            if size <= MAX_GLB:
                shutil.copy(glb, out / glb.name)
                entry["published"] = True
            else:
                entry["published"] = False
            shipped.append(entry)
        for doc in sorted(list(work.rglob("*_log.md")) + list(work.rglob("batch-report.md"))
                          + list(work.rglob("batch-manifest.yaml"))):
            (out / doc.name).write_text(scrub(doc.read_text()))
        res["glbs"] = shipped
        summary[brief] = res

    (dst / "summary.json").write_text(json.dumps(summary, indent=2))
    assert_clean(dst)
    total = sum(p.stat().st_size for p in dst.rglob("*") if p.is_file())
    print(f"published {label}: {len(summary)} briefs, {round(total / 1e6, 2)} MB → {dst.relative_to(REPO)}")


if __name__ == "__main__":
    main()
