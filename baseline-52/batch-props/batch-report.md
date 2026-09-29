# Batch Report: blacksmith-workshop — 2026-09-29

## Summary
3/3 ✅ │ 0 ❌ │ duration: ~5 min (runner, 16:13 → 16:18)

## Assets
| # | Asset | Status | Method | Faces (tris) | Size | Duration |
|---|-------|--------|--------|-------|------|----------|
| 1 | wooden-stool | ✅ | scripted | 560 | 34.9KB | ~2.5m |
| 2 | water-bucket | ✅ | scripted | 768 | 38.6KB | ~2m |
| 3 | coiled-rope | ✅ | scripted | 1,292 | 24.4KB | ~2m |

## Notes
- Palette: all procedural Principled BSDF (wood #8a5a34, wood_dark #5e3b22, iron #4a4c50 metallic, rope #b08a5a, water #2c4a5a). Material audit clean on all three.
- optimize_preset: none. No textures, and the files are already 24-39 KB. Draco can be added later with `gltf-transform draco`.
- No UV maps on most parts (not needed for flat materials). Unwrap if textures are added later.
- water-bucket: 14 open edges on the water plane (intended).
