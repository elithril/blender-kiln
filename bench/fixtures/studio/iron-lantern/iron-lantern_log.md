# Iron Lantern — Production Log

## Config
- Type: prop
- Target: glTF (web/)
- Tier: balanced (prop 1.5-5K tris, soft)
- Style: stylized
- Mode: auto
- Storage: compact
- Backend: none — scripted (user asked: no marketplace, no AI)
- Environment: Blender 5.2.2 LTS, mcp-for-blender addon 1.8 (protocol 14, up to date), gltf-transform + gltfpack present
- Output: /private/tmp/kiln-bench/mcp2/scripted-lantern/work/generated-assets/iron-lantern

## Reference Image
- Path: none
- Visual comparison: N/A

## Brief
Hanging iron lantern for a medieval inn, stylized. Assumptions (auto mode): ~0.45 m tall incl. ring,
~0.2 m square body; square base tray, 4 corner posts, mid/top frame bands, amber glass panes,
pyramid roof with chimney cap, ring on top, candle inside. Origin at centre of base, front -Y.

## Prompts (copy-paste ready)
- Concept art: none (scripted from the text brief)

## Source
- Method: scripted (Blender Python)

## Pipeline
- CONFIG/BRIEF: confirmed (auto). Blender held the untouched factory scene (Cube, Camera, Light, unsaved): Cube to be removed before building (rule 6 exception).
- SOURCE: scripted, build_iron_lantern.py (bmesh primitives, bevels baked into the mesh, no modifiers). Factory Cube removed (logged by script).
- Import: scripted, 7 mesh parts under empty SM_IronLantern (Base, Frame, Glass, Roof, Ring, Candle, Flame), 2,696 tris; world size 0.265 x 0.266 x 0.522 m (measured on vertices), on ground (zmin 0.000). All parts closed: 0 non-manifold, 0 boundary edges. Looked: front, 3/4, top, under-3/4 + close-up of candle with glass hidden — OK.
- Cleanup: 2,696 → 2,696 tris. Per part: transforms identity (built in world space), merge 1e-5 m keeping corner normals, degenerate dissolve, loose removed (0), normals recalculated outward; 0 fused / 0 non-manifold / 0 boundary edges on all 7 parts. Origin = centre of base (0,0,0), on ground. Orphans purged. Materials: M_Metal_WroughtIron, M_Glass_Amber, M_Wax_Candle, M_Emissive_Flame.
  - Round 1 merge fused the chimney rim to the cap cone (coincident rims, 12 edges with 3 faces): undone by rebuilding, cap cone now overlaps the rim by 4 mm; re-run gives 0 merged, 0 fused.
  - Poly check: 2,696 tris, inside balanced prop range (1.5-5K). Most in Frame (bevelled bars) and Ring (torus 24x8).
- Texturing: skipped — scripted with Principled value materials per part (stylized); no image textures, so no UV bake (uv_check n/a).
- Optimize: no image textures → WebP step n/a; gltf-transform draco (separate step, rule 20): 99.4 KB → 15.7 KB (−84%). Geometry untouched. Preview = copy of _original (no Draco/WebP; extensionsUsed: KHR_materials_transmission, KHR_materials_emissive_strength).
- Export: material audit — all 4 materials Principled-only, nothing procedural lost. glTF GLB, export_apply=False, Y-up, selection only (no camera/light). web/iron-lantern_final.glb 15.7 KB, 2,696 tris, 7 meshes, 4 materials (Draco). .blend saved (save_version 0). Studio checks: triangles, size, ground, compression all ok.

## Licenses
None — every mesh and material was authored in this session by script.

## Checkpoint
- Last completed step: [7] EXPORT (done)
- Timestamp: 2026-10-21
