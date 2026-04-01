# CLI Tools Reference

> gltf-transform, gltfpack, Reality Converter — standalone optimization and conversion.

---

## gltf-transform

**Install:** `npm install -g @gltf-transform/cli`
**Doc:** https://gltf-transform.dev/cli

### Inspect a GLB
```bash
gltf-transform inspect input.glb
```
Shows: meshes, materials, textures, animations, file size breakdown.

### Texture Compression (KTX2/Basis)
```bash
gltf-transform ktx2 input.glb output.glb --slots "baseColor,normal,occlusion,metallicRoughness,emissive"
```
Reduces texture size 60-80%. GPU-decompressed on client.

### meshopt Compression
```bash
gltf-transform meshopt input.glb output.glb
```
Compresses geometry. No WASM decoder needed client-side (unlike Draco).

### Draco Compression
```bash
gltf-transform draco input.glb output.glb \
  --quantize-position 14 \
  --quantize-normal 10 \
  --quantize-texcoord 12
```
Requires Draco WASM decoder on client (~200KB). More aggressive compression than meshopt.

### Full Optimization Pipeline

> **⚠️ NE JAMAIS utiliser `gltf-transform optimize`** — cette commande inclut `simplify` qui **détruit la géométrie du mesh** de manière irréversible. Toujours utiliser les étapes individuelles dans l'ordre :

```bash
# 1. Resize textures (max 1K pour web/mobile)
gltf-transform resize input.glb resized.glb --width 1024 --height 1024

# 2. Compression textures WebP (qualité 90 préserve le détail)
gltf-transform webp resized.glb webp.glb --quality 90

# 3. Compression mesh Draco (TOUJOURS en dernier — irréversible)
gltf-transform draco webp.glb final.glb

# 4. Inspecter le résultat
gltf-transform inspect final.glb
```

### Métriques de Référence

| Étape | Taille typique | GPU Memory (par texture) |
|---|---|---|
| Export brut (4K textures) | ~22 MB | ~89 MB |
| Après resize 1K | ~3.7 MB | ~5.6 MB |
| Après WebP q90 | ~3.7 MB | ~5.6 MB |
| Après Draco | ~1 MB | ~5.6 MB |

> **16x de réduction mémoire GPU** en passant de 4K à 1K. Les GPUs mobiles (Adreno, Mali) bénéficient le plus du downscaling textures.

### Resize Textures
```bash
gltf-transform resize input.glb output.glb --width 1024 --height 1024
```

### Dedup (remove duplicate resources)
```bash
gltf-transform dedup input.glb output.glb
```

---

## gltfpack

**Install:** `npm install -g gltfpack` or binary from https://github.com/zeux/meshoptimizer/releases
**Doc:** https://meshoptimizer.org/gltf/

### Simplify Mesh
```bash
gltfpack -i input.glb -o output.glb -si 0.5
```
`-si 0.5` = simplify to 50% of original faces. Preserves visual quality.

### Simplify to Target
```bash
gltfpack -i input.glb -o output.glb -si 0.5 -sa
```
`-sa` = aggressive simplification (allows topology changes).

### Generate LODs

LODs (Level of Detail) permettent au runtime de switcher entre des versions plus ou moins détaillées selon la distance caméra. Utilise l'extension `MSFT_lod`.

```bash
# Générer 3 niveaux de LOD (100%, 50%, 25% des faces)
gltfpack -i input.glb -o output_lod.glb -si 0.5 -sl 3
```
`-sl 3` = 3 LOD levels. `-si 0.5` = ratio de simplification entre niveaux.

**Workflow LOD complet (contrôle fin) :**

```bash
# 1. LOD0 = original (ou légèrement optimisé)
cp input.glb asset_lod0.glb

# 2. LOD1 = 50% faces
gltfpack -i input.glb -o asset_lod1.glb -si 0.5

# 3. LOD2 = 25% faces
gltfpack -i input.glb -o asset_lod2.glb -si 0.25

# 4. LOD3 = 10% faces (silhouette seulement)
gltfpack -i input.glb -o asset_lod3.glb -si 0.1 -sa

# 5. Inspecter chaque LOD
gltf-transform inspect asset_lod0.glb
gltf-transform inspect asset_lod1.glb
gltf-transform inspect asset_lod2.glb
gltf-transform inspect asset_lod3.glb
```

**Budget LOD recommandé :**

| LOD | Distance (Three.js) | % faces | Usage |
|---|---|---|---|
| LOD0 | < 5m | 100% | Close-up, hero |
| LOD1 | 5-15m | 50% | Mid-range |
| LOD2 | 15-50m | 25% | Background |
| LOD3 | > 50m | 10% | Far, silhouette only |

> **⚠️** Toujours vérifier visuellement chaque LOD après génération. `-sa` (aggressive) peut créer des artefacts sur les edges marqués.

### Full Optimization
```bash
gltfpack -i input.glb -o output.glb \
  -tc    # texture compression (KTX2) \
  -tq 8  # texture quality (1-10) \
  -si 0.5 # simplify 50%
```

### Compression Only (no simplification)
```bash
gltfpack -i input.glb -o output.glb -cc
```
`-cc` = meshopt compression, no geometry changes.

---

## Reality Converter (USDZ — macOS only)

**Download:** https://developer.apple.com/augmented-reality/tools/
**Type:** GUI application (no CLI)

### Usage
1. Open Reality Converter
2. Drag & drop GLB file
3. Adjust materials if needed
4. File → Export → USDZ

### Alternative: usdzconvert (CLI)
```bash
pip3 install usd-core
usdzconvert input.glb output.usdz
```

### USDZ Constraints
- Max texture: 4096x4096 (Apple recommends 2048)
- PBR Metallic/Roughness only
- No custom shaders

---

## Comparison: When to Use What

| Need | Tool | Command |
|---|---|---|
| Inspect GLB stats | gltf-transform | `gltf-transform inspect file.glb` |
| Compress textures (KTX2) | gltf-transform | `gltf-transform ktx2 in.glb out.glb` |
| Compress geometry (meshopt) | gltf-transform or gltfpack | `gltf-transform meshopt` or `gltfpack -cc` |
| Compress geometry (Draco) | gltf-transform | `gltf-transform draco in.glb out.glb` |
| Simplify mesh (reduce polys) | gltfpack | `gltfpack -si 0.5` |
| Generate LODs | gltfpack | `gltfpack -si 0.5 -sl 3` |
| Full optimization | gltfpack only | `gltfpack -tc -si 0.5` (⚠️ NE PAS utiliser `gltf-transform optimize`) |
| Resize textures | gltf-transform | `gltf-transform resize --width 1024` |
| Convert to USDZ | usdzconvert | `usdzconvert in.glb out.usdz` |

---

## Before/After Reporting

After any optimization, show:
```
Avant : 5.2 MB, 12K faces, 3 textures (2048x2048)
Après : 890 KB, 12K faces, 3 textures (1024x1024, KTX2)
Réduction : 83%

On garde ? (oui / non / ajuster les paramètres)
```

Always keep the pre-optimization file as backup.
