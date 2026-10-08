# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated (the owner left technical choices to Claude, 2026-10-07). Chosen: **Astro**, static
output, deployed to GitHub Pages from `site/` in the blender-kiln repository. Reason: zero JS by
default, content collections fit the "content lives in data files" requirement, 3D loaded as
isolated islands only where it appears. three.js for the GLB viewers (Draco + WebP decoders).
Nothing is deployed, pushed or put on a domain without the owner's explicit go-ahead.

## Users

Mixed, no priority (owner's answer):

- **Claude Code users** who want 3D assets without knowing Blender — job: install, describe or
  show a photo, get a usable GLB.
- **3D artists and game developers** who know Blender — job: judge whether the output is
  production-grade (topology, UVs, weight, rig) before trusting it.
- **three.js / web developers** — job: get light, compressed GLBs that load fast.

The site is in **English** (international audience; owner to confirm — inferred from the brief).

## Product Purpose

blender-kiln is a Claude Code plugin (MIT, https://github.com/elithril/blender-kiln) that turns
a text brief or a photo into a production-ready 3D asset (GLB optimized with Draco/WebP, FBX,
USDZ) by driving Blender through an MCP server (ahujasid's or the official Blender Lab MCP).
Since 2.1 it also animates what it rigs, routed by subject; 2.2 adds `/kiln animate`.

The site succeeds when a visitor installs the plugin, or trusts it enough to try, because the
evidence convinced them — and when it gets shared.

## Positioning

**Measured, not claimed.** A quality bench scores each photo rebuild against the *real* 3D object
the photo was taken of — an asset the session never sees. No neighbouring tool publishes that,
nor its failures: fifteen versions of one lantern, what each fix broke, a contaminated run struck
out, animation methods measured and rejected.

## Operating Context

- Install: `/plugin marketplace add elithril/blender-kiln` then `/plugin install
  blender-kiln@blender-kiln`, then `/kiln setup`.
- Requires Blender 4.4+ (verified 5.0 / 5.2) with a Blender MCP server running.
- Releases move fast (2.0 → 2.2 in five days). GitHub release notes are the source of truth for
  "what's new".

## Capabilities and Constraints

- **Every number shown comes from the bench or the README.** Nothing invented; no testimonials,
  no "trusted by", no logos of users.
- **Content is data**: version, bench figures, features, 3D assets and clips live in a content
  file, never hard-coded in sections, so a release updates the site without a redesign.
- **Truthful framing to keep**: the 15-prop gallery and the animation showcase were produced by
  scripts written to the skill's rules, *not* by an interactive session of the skill. UniMate's
  weights are CC BY-NC 4.0 (non-commercial). One run per brief; a few hundredths are not
  significant. Size is an assumption when a brief gives none.
- **Performance**: compressed GLBs, progressive 3D loading, a fallback without WebGL,
  `prefers-reduced-motion` honoured.
- **No paid service** (image generation, APIs, Hunyuan3D/Hyper3D/Tripo cloud) without explicit
  consent and a cost estimate. Any 3D asset made *for* the site is produced by kiln itself.

## Brand Commitments

- Name: **blender-kiln**, tagline in the README: "The 3D Asset Forge". Command prefix `/kiln`.
- Logo: `blender-kiln-logo.png` (768 px, a low-poly slate-blue kiln with an orange crystal flame).
- Voice (from the README and benchmarks): plain, exact, first-hand; claims carry their measure;
  limits stated next to results.

## Evidence on Hand

- Bench figures — `docs/benchmarks.md`, README "Measured, not claimed": lantern 0.830 → 0.897,
  ammo box 0.854 → 0.950, gothic chair 0.445 → 0.750; text briefs 32.9 MB → 0.96 MB
  (ahujasid MCP), 3.9 → 0.75 MB (Lab MCP); 7 of 7 GLBs compressed; costs per run.
- Shipped GLBs, usable as-is: `bench-results` branch, `ref-kiln-v15/` (lantern, 229 KB),
  `ref-kiln-v15gen/` (ammo box 187 KB, chair 239 KB); earlier lantern versions v11–v14, TRELLIS.
- Images: `docs/images/photo-to-asset.webp`, `how-it-works.webp`, seven `animate-*.webp` clips,
  `examples/gallery/renders/`, comparison sheets under `bench-results/` (lantern-iterations,
  generalisation, final).
- Citation: *3DCodeBench* (Google DeepMind, USC, 2026), arXiv 2606.01057, §1.
- Absences that must stay absent: user counts, star counts as social proof, testimonials,
  customer logos.

## Product Principles

1. Show the proof, then the claim — a number is always next to how it was measured.
2. Failures are content, not footnotes.
3. The real artefact beats an illustration: shipped GLBs and real session files over mock-ups.
4. The site follows the releases without a redesign.
5. The site is its own demonstration — anything 3D on it was made by kiln.

## Accessibility & Inclusion

WCAG 2.2 AA. Every 3D view has a static, described fallback; motion respects
`prefers-reduced-motion`; numbers are readable as text, not only as graphics.
