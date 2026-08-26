#!/usr/bin/env bash
# Reproduce the README gallery: model, render, export, optimize, collect metrics.
#   ./run_gallery.sh                 # all themes
#   THEMES="forge scifi" ./run_gallery.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
OUT="$HERE/out"
RENDERS="$HERE/renders"
RES="${RES:-1100}"
SAMPLES="${SAMPLES:-96}"
mkdir -p "$OUT" "$RENDERS"

FORGE="barrel crate lantern anvil crystal"
SCIFI="container canister relay reactor hexpad"
NATURE="tree boulder mushrooms stump cactus"
THEMES="${THEMES:-forge scifi nature}"

ASSETS=""
for t in $THEMES; do
  case "$t" in
    forge)  ASSETS="$ASSETS $FORGE" ;;
    scifi)  ASSETS="$ASSETS $SCIFI" ;;
    nature) ASSETS="$ASSETS $NATURE" ;;
    *) echo "unknown theme: $t" >&2; exit 1 ;;
  esac
done

: > "$OUT/metrics.jsonl"

for a in $ASSETS; do
  echo "── $a"
  "$BLENDER" --background --factory-startup --python "$HERE/build.py" -- \
      "$a" "$OUT" "$RES" "$SAMPLES" 2>/dev/null \
    | grep '^METRICS ' | sed 's/^METRICS //' >> "$OUT/metrics.jsonl"

  D="$OUT/$a"
  # Commit renders as WebP: the whole set is ~230 kB this way against 16 MB as
  # PNG, and GitHub renders WebP in READMEs.
  cwebp -q 88 -resize 900 900 -quiet "$D/$a.png" -o "$RENDERS/$a.webp"

  # OPTIMIZE phase. Individual steps only — never `gltf-transform optimize`
  # (iron rule 20), whose `simplify` destroys geometry.
  gltf-transform dedup "$D/${a}_original.glb" "$D/${a}_dedup.glb" >/dev/null 2>&1
  gltf-transform weld  "$D/${a}_dedup.glb"    "$D/${a}_weld.glb"  >/dev/null 2>&1
  gltf-transform draco "$D/${a}_weld.glb"     "$D/${a}_final.glb" >/dev/null 2>&1
  gltfpack -i "$D/${a}_weld.glb" -o "$D/${a}_packed.glb" -cc >/dev/null 2>&1 || true
done

python3 "$HERE/report.py" "$OUT" "$RENDERS"
