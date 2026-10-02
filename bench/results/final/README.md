# Final bench — the six original briefs, before and after everything

Blender 5.2.2, claude-opus-5-5, one run per brief. **Before**: skill 1.1.2 (`baseline-52`,
`lab-52`). **After**: `fix/baseline-findings` at `2b313d2` (`final-ahujasid`, `final-lab`),
which carries every fix of the baseline, the lantern loop and the generalisation test.

| Five briefs without AI | ahujasid before → after | Lab MCP before → after |
|---|---|---|
| Shipped size | 32.85 MB → **0.96 MB** (÷34) | 3.87 MB → **0.75 MB** (÷5) |
| GLBs compressed | 0 / 7 → **7 / 7** | 0 / 7 → **7 / 7** |
| Measure findings | 2 → 1 (a stool 6 mm below the ground) | 2 → **0** |
| Cost | $6.49 → $7.34 (+13 %) | $5.82 → $7.81 (+34 %) |

No visual regression on either MCP (`before-after-*.webp`, left before, right after).

**The AI brief ships no GLB, by design**, before and after: generation works (Hunyuan3D
Space, 275K triangles), then the session proposes decimation options with previews and
waits for the user (rule 6). A headless run cannot answer. Both sessions also flagged, on
their own, that Hunyuan3D's licence excludes the EU.
