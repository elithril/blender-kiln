# Before / after the baseline fixes — 2026-09-29

Same five briefs (the AI brief is out: the free ZeroGPU quota was spent), Blender
5.2.2, claude-opus-5-5, one run per brief. **Before** = skill 1.1.2 (`main`
9815b94). **After** = `fix/baseline-findings` at `0125ae4`. Labels:
`baseline-52` → `after-ahujasid`, `lab-52` → `after-lab`.

## Shipped size, brief by brief

| Brief | ahujasid before | after | | Lab before | after | |
|---|---:|---:|---:|---:|---:|---:|
| scripted-lantern | 127.5 kB | 19.8 kB | ÷6.4 | 94.9 kB | 19.8 kB | ÷4.8 |
| polyhaven-chair | 16,158 kB | 1,059 kB | ÷15.3 | 493 kB | 1,030 kB | **×2.1** |
| pbr-crate | 16,230 kB | 1,101 kB | ÷14.7 | 3,094 kB | 388 kB | ÷8.0 |
| rigged-character | 238.6 kB | 20.7 kB | ÷11.5 | 74.7 kB | 22.8 kB | ÷3.3 |
| batch-props (3 GLBs) | 97.9 kB | 23.5 kB | ÷4.2 | 112.8 kB | 21.9 kB | ÷5.2 |
| **total** | **32.85 MB** | **2.22 MB** | **÷14.8** | **3.87 MB** | **1.48 MB** | **÷2.6** |

The one regression is real and explained: the Lab chair's "before" session had
picked 1K maps and shipped them uncompressed; the fixed skill then picked 1K–2K for the
balanced tier, and that session took 2K, then WebP. Smaller per pixel, larger in
total. Fixed since in `d13d4e1`: web textures are capped at 1K, as
`uv-materials.md` already said — not yet re-measured.

## Did the fixes cause it? Read in the transcripts, not assumed

| | before (10 sessions) | after (10 sessions) |
|---|---|---|
| Final GLBs compressed (Draco) | 0 of 14 | **14 of 14** |
| Textured GLBs with WebP | 0 of 4 | **4 of 4** |
| Khronos validator run | 3 | **8** |
| Factory Cube | deleted in some, hidden in others | **removed and logged in 10/10** |
| PolyHaven API on the Lab MCP: User-Agent + credit (ToS) | 0 of 2 | **2 of 2** |
| Fused (non-manifold) edges shipped | 84 (Lab lantern) | **0** |
| Measure findings | 4 (2 per MCP) | **0** |

## What it cost

| | Cost ≈ | Turns | Wall |
|---|---:|---:|---:|
| ahujasid before → after | $6.49 → $7.50 (**+16 %**) | 155 → 187 | 21.5 → 23.7 min |
| Lab before → after | $5.82 → $7.37 (**+27 %**) | 119 → 182 | 18.4 → 23.7 min |

The skill now does work it used to skip — optimize, validate, re-check — and that
work is paid in turns. One run per brief: the percentages are leads.

## Still not fixed

- **Rule 2 on the Lab MCP**: 1 screenshot per session on 4 of 5 briefs. The
  mapping names the capture tools; the sessions still skip them.
- Look, not defect: the Lab lantern's glass now uses `KHR_materials_transmission`
  and reads dark in the bench's studio light, where the earlier one was opaque amber.
