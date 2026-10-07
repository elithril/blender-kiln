#!/usr/bin/env bash
# Rebuild the README's animation showcase: one looping WebP per tile, in docs/images/.
#
#   BLENDER=/path/to/blender ./showcase.sh
#
# Tiles and their route (references/animation.md):
#   character-walk/-jump  UniMate, looped (tools/unimate.py animate --loop) — needs `unimate.py setup`
#   dragon-flap     UniMate, looped, eyes folded into the skin first
#   cat-idle/-walk  tools/quadruped.py on the cat rigged by rig_cat.py
#   lamp, chest     props.py: modelled, rigged and keyed from scratch
# UniMate samples vary: each UniMate tile is the sample tools/motion_loop.py kept out of 4.
# Needs Blender 4.4+ and libwebp's img2webp. Clips are kept in examples/animation/out/ (gitignored).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$HERE/../.."
BLENDER="${BLENDER:-blender}"
TOOLS="$REPO/plugin/tools"
work="$HERE/out"                      # kept (gitignored): re-render a tile without regenerating it
mkdir -p "$work"
run_bl() { "$BLENDER" --background --factory-startup --python-exit-code 1 --python "$@" >/dev/null; }

tile() {   # tile <name> <clip.glb> — one pass of the loop; a WebP loops by itself
  local name="$1" clip="$2"
  # 720 px: a README tile shown a third wide covers ~600 device pixels on a 2x screen
  rm -rf "$work/f_$name"
  run_bl "$HERE/render.py" -- "$clip" "$work/f_$name" --res 720 --step 1 --samples 48
  local args=()
  for f in "$work/f_$name"/*.png; do args+=(-d 42 -lossy -q 85 -m 6 "$f"); done
  img2webp -loop 0 "${args[@]}" -o "$REPO/docs/images/animate-$name.webp" >/dev/null
  echo "animate-$name.webp  $(du -h "$REPO/docs/images/animate-$name.webp" | cut -f1)"
}

# scripted: props and the quadruped cycles
run_bl "$HERE/props.py" -- "$work/props"
tile lamp  "$work/props/lamp_look.glb"
tile chest "$work/props/chest_open.glb"
run_bl "$HERE/rig_cat.py" -- "$HERE/assets/cat_madtrollstudio.glb" "$work/cat.glb"
run_bl "$TOOLS/quadruped.py" -- --asset "$work/cat.glb" --out "$work/cat"
tile cat-walk "$work/cat/walk.glb"
tile cat-idle "$work/cat/idle.glb"

# UniMate: skipped, not faked, when it is not installed
if python3 "$TOOLS/unimate.py" status >/dev/null 2>&1 || [ $? -eq 10 ]; then
  # the same calls, seed and batches that produced the tiles a reviewer approved
  python3 "$TOOLS/unimate.py" animate --asset "$HERE/assets/villager.glb" --no-review --loop \
    --reps 4 --seed 0 --out "$work/villager-walk" --prompt "An object walks in place." >/dev/null 2>&1
  tile character-walk "$(ls "$work"/villager-walk/*walks_in_place.loop.glb)"
  python3 "$TOOLS/unimate.py" animate --asset "$HERE/assets/villager.glb" --no-review --loop \
    --reps 4 --seed 0 --out "$work/villager-set" --prompt "An object runs in place." "An object jumps in place." \
    "An object waves its right hand." "An object dances in place." >/dev/null 2>&1
  tile character-jump "$(ls "$work"/villager-set/*jumps_in_place.loop.glb)"
  python3 "$TOOLS/unimate.py" animate --asset "$HERE/assets/dragon_quaternius.glb" --loop --reps 4 --seed 0 \
    --annotation "$HERE/annotations/dragon_quaternius.json" --out "$work/dragon" \
    --prompt "An object flaps its wings." >/dev/null 2>&1
  tile dragon-flap "$(ls "$work"/dragon/*.loop.glb)"
else
  echo "UniMate not installed: character-walk and dragon-flap kept as they are (python3 plugin/tools/unimate.py setup)"
fi
