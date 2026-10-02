# Gallery — measurements and method

The fifteen reference props of the README, and what building them measured. Back to the [README](../README.md#gallery).

### What the OPTIMIZE phase actually buys

Measured, not estimated — these are the sizes the commands below produced:

**15 assets · 21,879 tris · 1456.2 kB raw → 132.7 kB after dedup/weld/Draco (91% smaller)**

#### Forge

| Asset | Object | Tris | GLB raw | + Draco | + meshopt | Saved |
|---|---|---:|---:|---:|---:|---:|
| `barrel` | `SM_Barrel` | 2,202 | 111.9 kB | 10.2 kB | 26.0 kB | **91%** |
| `crate` | `SM_Crate` | 1,836 | 128.6 kB | 9.7 kB | 20.9 kB | **92%** |
| `lantern` | `SM_Lantern` | 1,396 | 95.6 kB | 9.3 kB | 17.6 kB | **90%** |
| `anvil` | `SM_Anvil` | 888 | 62.9 kB | 6.5 kB | 11.5 kB | **90%** |
| `crystal` | `SM_CrystalCluster` | 722 | 40.7 kB | 5.3 kB | 11.5 kB | **87%** |
| **subtotal** | | **7,044** | **439.7 kB** | | | **91%** |

#### Sci-fi modular

| Asset | Object | Tris | GLB raw | + Draco | + meshopt | Saved |
|---|---|---:|---:|---:|---:|---:|
| `container` | `SM_CargoContainer` | 5,076 | 350.1 kB | 20.4 kB | 52.3 kB | **94%** |
| `canister` | `SM_Canister` | 2,114 | 139.7 kB | 11.5 kB | 24.0 kB | **92%** |
| `reactor` | `SM_ReactorCell` | 1,872 | 129.0 kB | 11.5 kB | 23.6 kB | **91%** |
| `relay` | `SM_AntennaRelay` | 1,638 | 115.0 kB | 11.2 kB | 21.1 kB | **90%** |
| `hexpad` | `SM_HexPad` | 772 | 41.7 kB | 6.0 kB | 10.9 kB | **86%** |
| **subtotal** | | **11,472** | **775.4 kB** | | | **92%** |

#### Stylised nature

| Asset | Object | Tris | GLB raw | + Draco | + meshopt | Saved |
|---|---|---:|---:|---:|---:|---:|
| `mushrooms` | `SM_Mushrooms` | 984 | 54.4 kB | 7.2 kB | 14.2 kB | **87%** |
| `tree` | `SM_Tree` | 774 | 67.0 kB | 7.4 kB | 14.5 kB | **89%** |
| `cactus` | `SM_Cactus` | 698 | 36.2 kB | 5.0 kB | 9.9 kB | **86%** |
| `stump` | `SM_Stump` | 587 | 49.4 kB | 7.2 kB | 11.6 kB | **85%** |
| `boulder` | `SM_Boulder` | 320 | 34.0 kB | 4.3 kB | 8.3 kB | **87%** |
| **subtotal** | | **3,363** | **241.0 kB** | | | **87%** |

Draco wins on size; gltfpack's meshopt output is roughly twice as large but
decodes faster on the client. Both are lossy, and both run as **individual
steps** — never `gltf-transform optimize`, per iron rule 20.

Two things the intermediate sizes will tell you if you read them closely:

- `weld` makes the file **bigger**. It is a preparation step for Draco, not a
  size win on its own — don't ship its output.
- Only Draco survives a round trip into Blender. Verified by re-importing every
  variant:

| Output | Re-imports into Blender |
|---|---|
| `_original.glb`, `_dedup.glb`, `_weld.glb` | yes, geometry intact |
| `_final.glb` (Draco) | yes — built-in decoder |
| `_packed.glb` (meshopt) | **no** — `EXT_meshopt_compression` unsupported |

`EXT_meshopt_compression` is a **web runtime** format: three.js and Babylon decode
it, Blender's glTF importer does not. That error on import is expected, not a
broken file — reach for `_final.glb` when you need the asset back in Blender, and
for `_packed.glb` when shipping to a viewer that decodes meshopt.

### Which rules the scripts obey

Audited against the iron rules and `references/`, honestly:

| Rule | Status | How |
|---|---|---|
| 3 — one asset at a time | yes | `build.py` handles exactly one per process |
| 4 — never hard-cap polys, alert out of range | yes | `studio.poly_budget()` classifies each asset into a `plugin/references/topology-rules.md` tier — 9 lightweight, 5 balanced, 1 detailed — and alerts only above the top ceiling. Nothing is ever blocked |
| 5 — never spend money | yes | everything local; no marketplace, no generation service |
| 7 / 16 — always keep the .blend, in the asset folder | yes | `<asset>/<asset>.blend` |
| 10 — apply transforms, merge doubles, recalc normals before export | yes | `studio.cleanup()`, in that order, before any export |
| 14 — 1 Blender unit = 1 m, verify | yes | asserted per asset, recorded in the log |
| 15 — naming conventions | yes | `SM_PascalCase` objects with matching `_Mesh` data-blocks, `M_Type_Variant` materials, kebab-case output files |
| 17 — track licences in the log | yes | `<asset>_log.md`, stating that everything is generated in-repo |
| 18 — never `export_apply=True` for GLTF | yes | explicitly `False` |
| 19 — material export audit before GLTF export | yes | `studio.material_audit()` scans for nodes GLTF drops; result recorded per asset |
| 20 — never `gltf-transform optimize` | yes | dedup → weld → draco as separate calls |
| 1 / 2 / 6 — scene info, screenshots, prompt before destroying | **no** | these are MCP-and-interactive by nature; a headless script has no session to prompt |
| 8 / 11 / 12 / 13 — HuggingFace fallback, concept art, AI views, T-pose | n/a | no AI generation and no characters in this gallery |

### Reproduce it

```bash
cd examples/gallery
./run_gallery.sh                      # all three themes
THEMES="forge nature" ./run_gallery.sh
```

Needs Blender 4.4+ (measured on 5.0 and 5.2), plus `gltf-transform`, `gltfpack` and `cwebp`.

`studio.py` holds the shared rig (sRGB→linear palette, three-point lighting with a
per-theme accent, camera fitting, cleanup, budget check, material audit, render,
GLB export). `assets.py` has one builder per prop plus the theme registry.
`build.py` drives a single asset and writes its log.

Two Blender API traps cost real debugging time here, because both fail silently:

- **Principled BSDF inputs are linear, not sRGB.** Feeding hex-picked values
  straight in washes everything out — linear `0.31` is sRGB `0.58`, so a magenta
  lands as pale pink and rich wood as light tan. `studio.srgb()` converts.
- **Writing `obj.location` does not refresh `obj.matrix_world`.** Read it in the
  same breath and you get the *previous* transform, so a "sit it on Z=0"
  correction computes `zmin = 0.0` and does nothing — leaving the asset
  half-buried under the ground plane. Flush with `view_layer.update()` first.

