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
# Needs Blender 4.4+ and libwebp's img2webp. Writes to a temporary dir, then docs/images/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$HERE/../.."
BLENDER="${BLENDER:-blender}"
TOOLS="$REPO/plugin/tools"
work="$(mktemp -d)"
run_bl() { "$BLENDER" --background --factory-startup --python-exit-code 1 --python "$@" >/dev/null; }

tile() {   # tile <name> <clip.glb> [repeats]
  local name="$1" clip="$2" reps="${3:-2}"
  run_bl "$HERE/render.py" -- "$clip" "$work/f_$name" --res 360 --step 1 --samples 24
  local args=()
  for _ in $(seq "$reps"); do for f in "$work/f_$name"/*.png; do args+=(-d 42 -lossy -q 72 "$f"); done; done
  img2webp -loop 0 "${args[@]}" -o "$REPO/docs/images/animate-$name.webp" >/dev/null
  echo "animate-$name.webp  $(du -h "$REPO/docs/images/animate-$name.webp" | cut -f1)"
}

# scripted: props and the quadruped cycles
run_bl "$HERE/props.py" -- "$work/props"
tile lamp  "$work/props/lamp_look.glb"
tile chest "$work/props/chest_open.glb"
run_bl "$HERE/rig_cat.py" -- "$HERE/assets/cat_madtrollstudio.glb" "$work/cat.glb"
run_bl "$TOOLS/quadruped.py" -- --asset "$work/cat.glb" --out "$work/cat"
tile cat-walk "$work/cat/walk.glb" 3
tile cat-idle "$work/cat/idle.glb"

# UniMate: skipped, not faked, when it is not installed
if python3 "$TOOLS/unimate.py" status >/dev/null 2>&1 || [ $? -eq 10 ]; then
  python3 "$TOOLS/unimate.py" animate --asset "$HERE/assets/villager.glb" --no-review --loop \
    --reps 4 --seed 0 --out "$work/villager" --prompt "An object walks in place." "An object jumps in place." >/dev/null 2>&1
  tile character-walk "$(ls "$work"/villager/*walks_in_place.loop.glb)" 3
  tile character-jump "$(ls "$work"/villager/*jumps_in_place.loop.glb)" 3
  python3 "$TOOLS/unimate.py" animate --asset "$HERE/assets/dragon_quaternius.glb" --loop --reps 4 --seed 0 \
    --annotation "$HERE/annotations/dragon_quaternius.json" --out "$work/dragon" \
    --prompt "An object flaps its wings." >/dev/null 2>&1
  tile dragon-flap "$(ls "$work"/dragon/*.loop.glb)" 3
else
  echo "UniMate not installed: character-walk and dragon-flap kept as they are (python3 plugin/tools/unimate.py setup)"
fi
rm -rf "$work"
