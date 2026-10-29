# Kiln Studio's film

The source of `site/public/assets/video/kiln-studio-session.mp4`, the film in the site's Kiln Studio
section: a [HyperFrames](https://hyperframes.studio) project (HTML rendered to video), 1920 × 1080,
30 fps, silent, 60.3 s.

- `index.html` mounts the scenes; `compositions/` holds one per scene: `opener`, `intro` (Studio on
  the ammo box), `studio` (the note pinned on the mascot), `work` (Claude in its own Blender), `back`
  (the note addressed, before and after), `walk`, `mcp`, `endcard`.
- `BRIEF.md`, `SPEC.md`, `STORYBOARD.md`: what the film says, every figure it may show, shot by shot.
- `scripts/`: how the pictures were made.
  - `film.py` films a real session in Studio (the note pinned, Claude asked, the result);
    `capture.py` takes the 3840 × 2160 stills of it on the GPU.
  - `capture_intro.py` takes the opening's stills on a demo project with four kiln 3.0 models;
    `capture_fix.py` took two of them again (the wireframe on clay, the mascot opened).
  - `hammer_morph.py`, `hammer_check.py`, `sweep.py`: the hammer growing (the real before and after
    meshes) and Studio's compare sweep; `walk_render.py`: the mascot's walk on the sweep.

The pictures, 31 MB, are on the `bench-results` branch, in
[`studio-film/assets/`](https://github.com/elithril/blender-kiln/tree/bench-results/studio-film/assets).
To render the film again:

```bash
cp -R <bench-results checkout>/studio-film/assets site/assets-src/studio-film/
cd site/assets-src/studio-film
npm run check && npm run render
```

The QR code in the opening was pixelated and the address under it blurred: they pointed to the
computer it was filmed on.
