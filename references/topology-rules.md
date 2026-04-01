# Topology Rules Reference

## Fundamental Rules

### Quads vs Triangles
- **Quads** for anything that deforms (characters, animated objects) — clean edge flow, predictable subdivision
- **Triangles** acceptable for static optimized props — game engines triangulate anyway
- **N-gons** avoid everywhere — convert to quads, then triangulate if needed
- AI-generated meshes are always dense triangulated → retopo or decimate needed

### Edge Flow
- Edge loops must follow muscle/joint lines on characters
- Critical loops: eyes, mouth, shoulders, elbows, knees
- Poles (vertices with 3 or 5+ edges): keep away from deformation zones
- 5-edge poles preferred over 3-edge poles

### Mesh Cleanliness
- Manifold meshes (no holes) except by deliberate design
- No overlapping faces, no interior faces
- No zero-area faces (degenerate)
- No doubled vertices (merge by distance)
- Normals all facing outward (recalculate)

## Poly Budgets by Platform

| Platform | Hero/Character | Prop | Background |
|---|---|---|---|
| Web/WebGL | 5-15K tris | 500-3K tris | 100-500 tris |
| Mobile | 10-25K tris | 1-5K tris | 200-1K tris |
| Console/PC | 50-150K+ tris | 5-30K tris | 1-10K tris |
| VR/AR | 10-30K tris | 1-5K tris | 200-2K tris |
| UE5 Nanite | Millions OK | Millions OK | Millions OK |

## Detail Tiers (blender-kiln)

| Tier | Hero/Character | Prop/Furniture | Background |
|---|---|---|---|
| lightweight | 3-8K tris | 300-1.5K | 50-300 |
| balanced | 8-20K tris | 1.5-5K | 300-1.5K |
| detailed | 20-80K tris | 5-15K | 1.5-5K |

These are SOFT ranges. Alert if >50% above range. Never block.

## Decimation Strategy

### When to decimate
- AI-generated mesh (typically 100-300K faces) → always needs reduction
- Marketplace asset exceeds tier range → propose reduction
- User requests specific poly count

### Blender Python decimation
```python
import bpy

obj = bpy.context.active_object
mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.ratio = target_faces / current_faces  # approximate
bpy.ops.object.modifier_apply(modifier="Decimate")
```

### Decimate modes
- **Collapse** — best general-purpose, preserves shape
- **Un-Subdivide** — reverses subdivision, good for regular grids
- **Planar** — dissolves flat faces, good for flat surfaces

### Rules
- ALWAYS show before/after (poly count + screenshot)
- ALWAYS ask user before applying
- Keep the original file as backup
- Multiple passes at low ratios > one aggressive pass

## LOD Pipeline

| LOD | % of LOD0 | Typical distance | Usage |
|---|---|---|---|
| LOD0 | 100% | 0-10m | Full detail |
| LOD1 | 50% | 10-25m | Medium |
| LOD2 | 25% | 25-50m | Far |
| LOD3 | 10-12% | 50-100m | Very far |

Generate LODs via gltfpack: `gltfpack -i model.glb -o optimized.glb -si 0.5`

## Post-AI-Generation Cleanup Priority

1. Merge by Distance (remove doubles)
2. Recalculate Normals
3. Remove Loose geometry
4. Apply All Transforms
5. Check poly count vs tier
6. Decimate if needed (interactive)
7. Center origin at base
