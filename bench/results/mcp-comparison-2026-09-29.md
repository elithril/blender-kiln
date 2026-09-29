# Two MCPs, one skill — 2026-09-29

Skill 1.1.2 unchanged (main 9815b94) · Blender 5.2.2 LTS · claude-opus-5-5 · one run per brief. `baseline-52` drives ahujasid's blender-mcp 2.0.0 (addon 1.7); `lab-52` drives the official Blender Lab server at `dbbf836`. The 5.0.1 baseline is kept in `baseline-2026-09-29.md`.

### baseline-52

| Brief | Exit | Turns | Wall | Cost ≈ | Tool calls | Screenshots | GLB | Tris | Size | Findings |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| ai-mushrooms | 0 | 42 | 5.7 min | $1.25 | 41 | 6 | — | — | — | **no *_final.glb shipped** |
| batch-props | 0 | 35 | 4.5 min | $1.54 | 34 | 7 | `coiled-rope_final.glb` | 1292 | 23.8 kB | — |
| batch-props | 0 | 35 | 4.5 min | $1.54 | 34 | 7 | `water-bucket_final.glb` | 768 | 37.7 kB | — |
| batch-props | 0 | 35 | 4.5 min | $1.54 | 34 | 7 | `wooden-stool_final.glb` | 560 | 34.1 kB | — |
| pbr-crate | 0 | 34 | 4.7 min | $1.28 | 33 | 2 | `sci-fi-supply-crate_final.glb` | 1952 | 15849.3 kB | textures uncompressed (16.2 MB) |
| polyhaven-chair | 0 | 27 | 3.0 min | $0.97 | 26 | 2 | `farmhouse-chair_final.glb` | 724 | 15779.7 kB | textures uncompressed (16.2 MB) |
| rigged-character | 0 | 38 | 6.6 min | $1.81 | 37 | 6 | `villager_final.glb` | 2014 | 233.1 kB | — |
| scripted-lantern | 0 | 21 | 2.7 min | $0.89 | 20 | 2 | `iron-lantern_final.glb` | 1940 | 124.5 kB | — |

6 brief(s), cost ≈ $7.74 equivalent API.

### lab-52

| Brief | Exit | Turns | Wall | Cost ≈ | Tool calls | Screenshots | GLB | Tris | Size | Findings |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| ai-mushrooms | 0 | 17 | 4.1 min | $1.16 | 35 | 3 | — | — | — | **no *_final.glb shipped** |
| batch-props | 0 | 22 | 4.3 min | $1.45 | 20 | 3 | `coiled-rope_final.glb` | 1058 | 34.5 kB | — |
| batch-props | 0 | 22 | 4.3 min | $1.45 | 20 | 3 | `water-bucket_final.glb` | 704 | 47.3 kB | — |
| batch-props | 0 | 22 | 4.3 min | $1.45 | 20 | 3 | `wooden-stool_final.glb` | 356 | 28.3 kB | — |
| pbr-crate | 0 | 28 | 3.0 min | $1.11 | 27 | 3 | `sci-fi-supply-crate_final.glb` | 1972 | 3021.8 kB | textures uncompressed (3.1 MB) |
| polyhaven-chair | 0 | 26 | 3.1 min | $1.0 | 25 | 3 | `painted-wooden-chair_final.glb` | 724 | 481.6 kB | — |
| rigged-character | 0 | 27 | 5.5 min | $1.43 | 26 | 5 | `low-poly-villager_final.glb` | 720 | 73.0 kB | — |
| scripted-lantern | 0 | 16 | 2.5 min | $0.83 | 15 | 2 | `iron-lantern_final.glb` | 2290 | 92.7 kB | 84 non-manifold |

6 brief(s), cost ≈ $6.99 equivalent API.

## Totals

| Series | Cost ≈ | Turns | Wall | Edits (`execute_blender_code`) | Screenshots | GLBs shipped |
|---|---:|---:|---:|---:|---:|---:|
| baseline (ahujasid, 5.0.1) | $7.56 | 192 | 25.7 min | 63 | 19 | 7 |
| baseline-52 (ahujasid, 5.2.2) | $7.74 | 197 | 27.2 min | 67 | 25 | 7 |
| lab-52 (official, 5.2.2) | $6.99 | 136 | 22.5 min | 56 | 19 | 7 |

## What the comparison says

- **The skill works on the official MCP as it stands.** Same 7 GLBs, same brief
  stopping in the same place (AI: the decimate prompt, rule 6). The sessions
  mapped kiln's tool names to the Lab's on their own — "the Lab MCP has different
  tool names from the ones the skill expects, so I used their equivalents".
- **It was cheaper and shorter**: −10 % cost, −31 % turns, −17 % wall time. One run
  per brief: a lead, not a verdict.
- **No PolyHaven tools on the Lab server — and it did not matter.** Both PolyHaven
  briefs went through PolyHaven's public HTTP API from Bash, picked 1K textures,
  and shipped far smaller files: chair **0.48 MB vs 16.2 MB**, crate **3.1 MB vs
  16.2 MB**. The size gap is the texture resolution the session chose, not a
  property of either MCP.
- **One real defect, on the Lab side**: the lantern's frame and roof carry **84
  edges shared by 3–4 faces** — bars joined and welded into internal faces.
  Invisible in the render, caught by the measure.
- **Blender 5.0.1 → 5.2.2 changed nothing measurable** on the same MCP ($7.56 vs
  $7.74, same 7 GLBs).
- **Unchanged by either MCP**, so they belong to the skill: auto mode never ran
  OPTIMIZE; screenshots stay far below edits; the factory Cube is deleted in some
  runs and hidden in others; one session answered in French from an English brief.

## Instrument fix made while reading these

Both villagers showed "1 dead bone". It was `Root` — parentless, the hierarchy's
anchor, named by the skill's own convention. `measure.py` no longer counts a
parentless bone as dead; `test_measure.py` builds its rigs on an unweighted
`Root` and still passes 10/10. The three rig results were re-measured.
