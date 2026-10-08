"""Embed each shipped raster's origin (impeccable's provenance rule). Run from site/: python3 assets-src/provenance.py"""
import glob, os, subprocess
IMP = os.path.expanduser('~/.claude/skills/impeccable/scripts/impeccable')
SHEETS = {**{f'v{i}': 'lantern-iterations/progression-v1-v8.webp' for i in range(1, 9)},
          'photo': 'lantern-iterations/progression-v1-v8.webp', 'truth': 'lantern-iterations/progression-v1-v8.webp',
          'v9': 'lantern-iterations/v8-v9-v10-compare.webp', 'v10': 'lantern-iterations/v13-compare.webp',
          'v11': 'lantern-iterations/v13-compare.webp', 'v12': 'lantern-iterations/v12-contaminated-compare.webp',
          'v13': 'lantern-iterations/v13-compare.webp', 'v14': 'lantern-iterations/v15-compare.webp',
          'v15': 'lantern-iterations/v15-compare.webp'}
REFS = {'Lantern_01': 'Lantern_01', 'ammo_box': 'ammo_box', 'WoodenChair_01': 'WoodenChair_01'}
RENDERS = {'lantern': 'ref-kiln-v15/ref-lantern-template/render-hurricane-lantern_final.webp',
           'ammo-box': 'ref-kiln-v15gen/ref-ammo-box/render-ammo-box_final.webp',
           'chair': 'ref-kiln-v15gen/ref-chair/render-gothic-wooden-chair_final.webp'}
REBUILT = {'character-walk': 'out/villager-walk/*walks_in_place.loop.glb (tools/unimate.py --loop, seed 0, 4 samples)',
           'character-jump': 'out/villager-set/*jumps_in_place.loop.glb (tools/unimate.py --loop, seed 0, 4 samples)',
           'dragon-flap': 'out/dragon/*flaps_its_wings.loop.glb (tools/unimate.py --loop, seed 0, 4 samples, reviewed annotation)',
           'cat-walk': 'out/cat/walk.glb (tools/quadruped.py on rig_cat.py)', 'cat-idle': 'out/cat/idle.glb (tools/quadruped.py on rig_cat.py)',
           'lamp': 'out/props/lamp_look.glb (examples/animation/props.py)', 'chest': 'examples/animation/chest.py, textures Poly Haven rough_wood + rusty_metal_04 (CC0)'}

def origin(path):
    name = os.path.splitext(os.path.basename(path))[0]
    d = os.path.basename(os.path.dirname(path))
    if d == 'lantern':
        if name in ('v12', 'v15', 'truth'):
            src = 'the real Poly Haven Lantern_01 glTF (CC0)' if name == 'truth' else f'bench-results:ref-kiln-{name}/.../hurricane-lantern_final.glb'
            return f'Rendered for the site: plugin/tools/fidelity_check.py on {src}, studio_small_09 HDRI, 15 deg, transparent film; framed to its bench sheet tile by site/assets-src/lantern/match_frame.py.'
        if name == 'photo':
            return 'Sourced: Poly Haven Lantern_01 preview (CC0), the bench reference photo, original alpha; framed to its sheet tile by match_frame.py.'
        return f'Sourced: {name} cut from blender-kiln bench-results:{SHEETS[name]} (no GLB was kept for this version), ground keyed out by site/assets-src/lantern/key_grey.py.'
    if d == 'method3d':
        if name.startswith('crop-'):
            return f'Sourced: {name} of the ammo box session crop montage (how-it-works panel 1, review/crops), split by site/assets-src/method/split_crops.py.'
        if name in ('green_metal_rust', 'rust_coarse_01'):
            return f'Sourced: Poly Haven {name} diffuse 1k (CC0), the scan the ammo box session used, resized to 512.'
        if name == 'photo':
            return 'Sourced: Poly Haven ammo_box preview (CC0), the bench reference photo, cropped to its alpha.'
        if name == 'photo-mask':
            return 'Derived: the alpha of the Poly Haven ammo_box preview (CC0) as a white silhouette, for the measure step.'
    if d == 'method':
        return f'Sourced: panel {name[-1]} of 5 cropped from blender-kiln docs/images/how-it-works.webp (files written by a kiln session rebuilding the ammo box), caption removed.'
    if d == 'animate':
        base = name.replace('-still', '')
        if base in REBUILT:
            kind = 'first frame' if name.endswith('-still') else 'looping clip'
            return f'Rendered for the site ({kind}): site/assets-src/animate/render_bench.py on {REBUILT[base]}, bench HDRI studio_small_09, composited on #404040.'
        kind = 'first frame of' if name.endswith('-still') else 'copy of'
        return f'Sourced: {kind} blender-kiln docs/images/animate-{base}.webp (examples/animation/showcase.sh, UniMate route).'
    if d == 'bench':
        cleaned = name in ('before-after-ahujasid', 'v7-control', 'crate-chair')
        how = 'its empty grid cells (pure black fill) painted #2e2e2e by site/assets-src/bench/fill_empty_cells.py' if cleaned else 'unchanged copy'
        return f'Sourced: blender-kiln bench-results sheet {name}.webp, {how}.'
    if name.startswith('ref-'):
        a = name[4:]
        return f'Sourced: Poly Haven {REFS[a]} preview image (CC0), as used by the blender-kiln bench (bench/runs/_refs), converted to WebP.'
    if name.startswith('render-'):
        return f'Sourced: blender-kiln bench-results:{RENDERS[name[7:]]} (bench render of the shipped GLB), no-WebGL fallback.'
    if name == 'forge-still':
        return 'Rendered for the site: site/assets-src/forge/review.py on forge.blend (the kiln-made forge, build_forge.py), EEVEE, no-WebGL fallback.'
    if name in ('logo-72', 'favicon-64'):
        return f'Sourced: blender-kiln-logo.png from the blender-kiln repository root, resized to {name.split("-")[1]} px.'
    raise SystemExit(f'no origin for {path}')

for p in sorted(glob.glob('public/assets/img/**/*.*', recursive=True)):
    if os.path.splitext(p)[1].lower() not in ('.webp', '.png', '.jpg', '.jpeg'):
        continue
    subprocess.run([IMP, 'embed-prompt', p, '--prompt', origin(p)], check=True, capture_output=True)
print(subprocess.run([IMP, 'embed-prompt', '--scan', 'public/assets/img'], capture_output=True, text=True).stdout.strip().splitlines()[-1])
