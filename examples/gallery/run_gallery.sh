#!/usr/bin/env bash
# Reproduce the README gallery: model, render, export, optimize, collect metrics.
#   ./run_gallery.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
OUT="$HERE/out"
RENDERS="$HERE/renders"
RES="${RES:-1100}"
SAMPLES="${SAMPLES:-96}"
mkdir -p "$OUT" "$RENDERS"

ASSETS=(barrel crate lantern anvil crystal)
: > "$OUT/metrics.jsonl"

for a in "${ASSETS[@]}"; do
  echo "── $a"
  "$BLENDER" --background --factory-startup --python "$HERE/build.py" -- \
      "$a" "$OUT" "$RES" "$SAMPLES" 2>/dev/null \
    | grep '^METRICS ' | sed 's/^METRICS //' >> "$OUT/metrics.jsonl"
  cp "$OUT/$a.png" "$RENDERS/$a.png"

  # OPTIMIZE phase. Individual steps only — never `gltf-transform optimize`
  # (iron rule 8), which bundles choices this pipeline needs to make itself.
  gltf-transform dedup "$OUT/$a"_original.glb "$OUT/$a"_dedup.glb >/dev/null 2>&1
  gltf-transform weld  "$OUT/$a"_dedup.glb    "$OUT/$a"_weld.glb  >/dev/null 2>&1
  gltf-transform draco "$OUT/$a"_weld.glb     "$OUT/$a"_final.glb >/dev/null 2>&1
  gltfpack -i "$OUT/$a"_weld.glb -o "$OUT/$a"_packed.glb -cc >/dev/null 2>&1 || true
done

python3 "$HERE/report.py" "$OUT" "$RENDERS"
