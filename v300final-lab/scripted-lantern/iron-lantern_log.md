# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (web)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: stylized
- Mode: auto
- Storage: compact
- 3D backend: none — scripted modelling (brief: no marketplace, no AI)
- Output: /private/tmp/kiln-bench/v300final-lab/scripted-lantern/work/generated-assets/iron-lantern
- Environment: macOS, Apple M4 Pro; Blender 5.2.2 LTS via the official Blender Lab MCP; gltf-transform + gltfpack present; no AI backend needed

## Brief
Hanging wrought-iron lantern for a medieval inn, stylized: square iron base tray, four corner
posts with a riveted-look cage (vertical bars + a mid band) over glass panes, a pyramid roof
with a small chimney cap, a hanging ring on top, a candle with a flame inside.
- Assumed size (no reference given): ~0.43 m tall including the ring, body 0.18 m square.
- Origin: centre of the base (kiln convention), -Y front, +Z up.

## Reference Image
- Path: none
- Brief enrichment: none
- Visual comparison: N/A

## Prompts (copy-paste ready)
- Concept art: none (scripted from the text brief)

## Source
- Method: scripted (Blender Python)

## Pipeline
- Source: scripted modelling chosen by the brief (geometric stylized prop → separate iron parts, clean topology); build script iron-lantern_build.py
- Scene start: Blender factory scene (Cube, Camera, Light, no file) — default Cube removed before building (rule 6 exception)
- Import (scripted, implicit): SM_IronLantern empty + 7 parts (Base, Frame, Glass, Roof, Ring, Candle, Flame), 3,532 tris, 0.223 × 0.223 × 0.470 m (world vertices), z min 0.000 — stands on the ground, origin at base centre. Viewport look (material preview, three-quarter): all parts attached, ring seated in the roof knob. Flame emission 6 clips to white → lower at cleanup.
- Cleanup: 3,532 → 3,532 tris. Per part: transforms applied, merge by distance 1e-4 keeping corner normals (0 merged — parts built as separate closed shells), loose 0, degenerate dissolve, normals recalculated outward; non-manifold: 0 open / 0 fused edges on all 7 parts. Origin at base centre (0,0,0), z min 0.000. Orphans purged (factory 'Material'). Flame emission 6 → 2.5, colour more orange. Poly check: 3,532 tris, inside balanced prop 1.5–5K (Frame 2,252 — bars, bands, 24 rivets; Ring 448). Look: back three-quarter from slightly below, all parts attached.
- Texturing: skipped — scripted, materials assigned per part (values only, stylized): M_Metal_WroughtIron (Base, Frame, Roof, Ring), M_Glass_Amber (transmission 1.0, IOR 1.5, alpha 0.35), M_Wax_Candle, M_Flame_Emissive (emissive 2.5). Material export audit (rule 19): Principled BSDF + Output only, nothing procedural to lose. Two opposite looks taken (front three-quarter, back three-quarter from below). No UV textures → uv_check not applicable.
- Rig / Animate: not applicable (static prop).
- Optimize: no textures (WebP step not applicable); gltf-transform draco: 156.7 KB → 17.6 KB (−89%). iron-lantern_preview.glb = copy of _original (no Draco, no WebP — opens in Quick Look).
- Export: glTF/GLB, web/iron-lantern_final.glb, 17.6 KB, 3,532 tris, 7 meshes under SM_IronLantern, export_apply=False; extensions: Draco, KHR_materials_transmission, KHR_materials_emissive_strength; glass alphaMode BLEND. .blend saved (save_version 0). Studio checks: triangles, size, ground, compression all ok, no WARN.
- Kept (compact): _original.glb, _preview.glb, web/_final.glb, .blend, log, build script.

## Licenses
- SM_IronLantern (geometry, materials): original work, scripted in this session

## Checkpoint
- Last completed step: [7] EXPORT — done
- Timestamp: 2026-10-22
