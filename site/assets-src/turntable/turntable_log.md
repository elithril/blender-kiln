# Turntable — Production Log

## Config
- Type: prop (studio equipment, sits under the site's 3D objects)
- Target: glTF (three.js), Draco + WebP
- Tier: lightweight · Style: realistic · Mode: auto · Storage: compact

## Reference Image
- none (text brief)

## Source
- Method: scripted modeling, `build_turntable.py`
- Run headless (`blender -b --factory-startup --python-exit-code 1`), Blender 5.2.2 LTS, not over MCP:
  the live Blender connected to the MCP server held another project (`diorama.blend`), left untouched.
  Rule 2 screenshots were replaced by EEVEE renders from two opposite angles (`review_render.py`).

## Pipeline
- Geometry: SM_Turntable_Disc (Ø 0.60 m × 0.03 m, top at 0.05 m), SM_Turntable_Base (Ø 0.50 m × 0.02 m, recessed)
- Cleanup: bevels applied as geometry (rule 18), merge by distance, normals recalculated, sharp edges from 35°
- Texturing: top face from Poly Haven `rubberized_track` (CC0) — roughness and normal from the scan, colour from
  its grain tinted charcoal; degree ring painted on (tick every 5°, long every 30°, orange index at 0° = front, −Y).
  Rim: brushed-aluminium Principled values. Base: dark satin.
- Review: first render read the top near white — measured the texture (byte 70 = charcoal, roughness 0.89): the
  review light was the fault (900 W), not the asset. Re-lit at 110 W, reads as charcoal rubber.
- Material audit (rule 19): Principled + image textures only; all 3 textures present in the GLB.
- Optimize: 4.40 MB → 437 KB (WebP, Draco) → 73 KB with textures resized to 512 px (the disc is small on screen).
  No geometry simplified. Draco needs a decoder on the client.
- Export: `turntable_final.glb`, 72,696 bytes, 1,912 triangles; Khronos validator: no errors.
  The shipped GLB was re-rendered (`work/review/glb-*.png`) and matches the .blend.

## Licenses
- Poly Haven `rubberized_track` texture: CC0 (polyhaven.com/a/rubberized_track)

## Checkpoint
- Last completed step: EXPORT · 2026-10-07
