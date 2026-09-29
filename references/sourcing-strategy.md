# Sourcing Strategy Reference

## Preflight — rule 23, before the first search

```
get_polyhaven_status()  →  {"enabled": bool, "message": "..."}
get_sketchfab_status()  →  {"enabled": bool, "message": "..."}
```

Both integrations are **OFF in a default addon install**. While off, the addon
does not register `search_polyhaven_assets` / `search_sketchfab_models` at all,
so calling them returns `Unknown command type: <name>` — which looks like a
version mismatch and sends the user hunting for the wrong problem.

If `enabled` is false, print the `message` field verbatim. It names the exact
fix: the BlenderMCP panel in the 3D Viewport sidebar (press N if hidden), and the
checkbox to tick. Then offer the other marketplace, or the creation path.

Never surface `Unknown command type` to the user.


## Overview
Search existing marketplaces before generating. Present ~10 results with links. Iterate until user finds what they need or switches to creation.

## PolyHaven
- Fully free, CC0 (public domain)
- No authentication needed
- Types: HDRIs, textures, 3D models
- MCP tools: `search_polyhaven_assets`, `download_polyhaven_asset`, `set_texture`, `get_polyhaven_categories`
- Categories: wood, metal, rock, fabric, brick, plaster, terrain, floor, roofing, aerial

### Without the MCP integration — the public API

On the official Blender Lab MCP, or with the integration off, go to PolyHaven's
public API from Bash. No key, CC0 assets. Verified 2026-09-29:

```bash
UA="blender-kiln"                                          # ToS 2.4: a unique User-Agent, always
curl -s -A "$UA" "https://api.polyhaven.com/assets?type=models&categories=furniture"   # {id: {name, categories, ...}}
curl -s -A "$UA" "https://api.polyhaven.com/files/WoodenChair_01"   # per format, per resolution
```

`files/<id>` → `gltf` → `1k` / `2k` / `4k` → `gltf` gives the `.gltf` URL and an
`include` map of its textures and `.bin`; download every entry into the same
relative layout, then import the `.gltf`. **Pick the resolution from the tier**
(lightweight 1k, balanced 1k–2k, detailed 2k–4k): the bench's chair shipped at
16.2 MB from 2K maps and at 0.48 MB from 1K, same 724 triangles.

**Terms of Service** (`Poly-Haven/Public-API`, `ToS.md`): the assets are CC0 and
need no attribution, but using the *live API* requires a unique User-Agent (2.4)
and a visible credit to Poly Haven for the content (2.5). Write
`Source: Poly Haven (polyhaven.com), via the public API` in the asset log (rule 17).

### Search flow
1. Extract keywords from brief (material, style, era)
2. `search_polyhaven_assets` with keywords — or the API above when the MCP has no PolyHaven tools
3. Present results with name, type, link
4. Links format: `https://polyhaven.com/a/{asset_name}`

## Sketchfab
- Mix of free and paid models
- REQUIRES API token for downloads (free account)
- Token setup: https://sketchfab.com/settings/password → "API Token"
- MCP tools: `search_sketchfab_models`, `get_sketchfab_model_preview`, `download_sketchfab_model`

### Search flow
1. `search_sketchfab_models` with query, downloadable=true, count=10
2. Filter results for free/downloadable only
3. Present results with: name, poly count, link, license
4. Links format: `https://sketchfab.com/3d-models/{slug}-{uid}`
5. `download_sketchfab_model` with target_size to normalize dimensions

### License awareness
- PolyHaven: always CC0, no attribution needed
- Sketchfab licenses vary: CC0, CC-BY, CC-BY-SA, CC-BY-NC, etc.
- ALWAYS log the license in the asset log
- ALERT if license requires attribution (CC-BY, CC-BY-SA)
- NEVER download CC-BY-NC assets for commercial projects without user confirmation

## Search Result Presentation

```
Results for "medieval wooden chair":

 1. Old Wooden Chair — 2.3K tris — polyhaven.com/a/old_wooden_chair (CC0)
 2. Medieval Chair — 4.1K tris — sketchfab.com/3d-models/xxx (CC-BY 4.0)
 3. ...
10. Rustic Stool — 1.8K tris — polyhaven.com/a/rustic_stool (CC0)

Open links? (number, "all", or refine search)
```

## Link Opening
- `auto_open_links=false` by default
- User can: "open 2, 5, 7" → opens specific links
- User can: "open all" → opens all 10 links
- macOS: `open "https://..."` via Bash
- Can toggle auto_open_links mid-session

## Refinement Loop
When results don't match:
- User says "more rustic" / "try oak furniture" / "nothing works"
- Adjust keywords, re-search
- If nothing found after 2-3 iterations → propose switching to creation

## After download — rules 24 and 25

A PolyHaven or Sketchfab import arrives under the source file's own name
(`ClassicNightstand_01`), not the project convention. Two things before anything
downstream reads it:

```
get_object_info(name)  → world_bounding_box, to verify 1 unit = 1 m (rule 24)
rename                 → SM_PascalCase + SM_..._Mesh data-block (rule 25)
```

**Scale is usually right, but check it anyway.** PolyHaven reports dimensions in
millimetres in its search results (`568 x 424 x 700` for a nightstand) while the
importer converts to metres, so a correct import measures `0.568 x 0.424 x 0.7`.
Verified against the live API. A raw 568-unit object means the conversion did not
happen.
