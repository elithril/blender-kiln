#!/usr/bin/env bash
# Frames (transparent, shadow kept) -> composited on the page's #404040 sweep -> looping lossy WebP + still.
# encode.sh <name>   reads out/f_<name>/*.png, writes ../../public/assets/img/animate/<name>.webp and <name>-still.webp
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; n="$1"; F="$HERE/out/f_$n"; C="$HERE/out/c_$n"; O="$HERE/../../public/assets/img/animate"
rm -rf "$C"; mkdir -p "$C"
for f in "$F"/*.png; do
  ffmpeg -loglevel error -y -f lavfi -i "color=c=0x404040:s=600x600" -i "$f" -filter_complex "[0][1]overlay,format=rgb24" -frames:v 1 "$C/$(basename "$f")"
done
args=(); for f in "$C"/*.png; do args+=(-d 42 -lossy -q "${Q:-70}" -m 6 "$f"); done
img2webp -loop 0 "${args[@]}" -o "$O/$n.webp" >/dev/null
cwebp -quiet -q 82 "$C/0000.png" -o "$O/$n-still.webp"
echo "$n $(du -k "$O/$n.webp" | cut -f1) KB"
