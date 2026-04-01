# Sourcing Strategy Reference

## Overview
Search existing marketplaces before generating. Present ~10 results with links. Iterate until user finds what they need or switches to creation.

## PolyHaven
- Fully free, CC0 (public domain)
- No authentication needed
- Types: HDRIs, textures, 3D models
- MCP tools: `search_polyhaven_assets`, `download_polyhaven_asset`, `set_texture`, `get_polyhaven_categories`
- Categories: wood, metal, rock, fabric, brick, plaster, terrain, floor, roofing, aerial

### Search flow
1. Extract keywords from brief (material, style, era)
2. `search_polyhaven_assets` with keywords
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
