# Blender MCP — tool surface

> Read before the first phase when the Blender MCP is new to the session: kiln runs on three
> tool surfaces, and the rules name the current one. Rule numbers are SKILL.md's Iron Rules.

## Contents
- Which server is this?
- The tools, by need
- mcp-for-blender — what changed, what to know
- On the old surface (mcp-for-blender 2.1.3 and earlier)
- On the official Blender Lab MCP

## Which server is this?

ahujasid's server is **`mcp-for-blender`** (renamed from `blender-mcp` in September 2026;
`blender-mcp` 2.0.0 on PyPI is a shim that installs the latest `mcp-for-blender`, unpinned).
Its tools changed shape in October 2026. Tell the three apart by the tools you have:

| You have | Server | Surface |
|---|---|---|
| `look`, `search_assets` | `mcp-for-blender` **2.1.9 or later** (checked 2.1.9–2.2.2) | current: 9 tools — the names the rules use |
| `get_viewport_screenshot`, `get_object_info` | `mcp-for-blender` 2.1.3 or earlier, `blender-mcp` 1.x | old: 36 tools — the second column below |
| `get_objects_summary`, `get_screenshot_of_area_as_image` | the Blender Lab MCP | § On the official Blender Lab MCP |

## The tools, by need

Read from `mcp-for-blender` 2.2.2's source on 2026-10-21; `look`, `get_scene_info`,
`get_addon_status` and `execute_blender_code` were driven by a bench session the same day.

| Tool (≥ 2.1.9) | Use | Old surface (≤ 2.1.3) |
|---|---|---|
| `get_addon_status` | Rule 23. First call: addon reachable, `up_to_date`, `libraries` and `generators` each `on`/`off` | `get_addon_status()`, then `get_polyhaven_status()` / `get_sketchfab_status()` / `get_polypizza_status()` |
| `get_scene_info` | Rule 1, before each phase. Dimensions (rule 24): `fields=["size", "ground"]` — world bounding box, on / above / below the ground; `query=` or `root=` for one object. Mesh health after cleanup: `fields=["topology", "materials"]` (quads, tris, ngons, non-manifold and boundary edges, loose verts), `weights` for a rig | `get_scene_info()` — names and counts only; dimensions from `get_object_info(name)` → `world_bounding_box` |
| `look` | Rule 2, per phase. `look(mode="angles", target=[name], shading="material")` — framed on the target (rule 22), 1-6 views (front, back, left, right, top, three_quarter, or `[x, y, z]`) in one image; `shading="solid"` for the shape; `mode="frames"` for an animation strip | frame the viewport (PHASE 4's code), then `get_viewport_screenshot()` |
| `execute_blender_code` | Build, clean, export: the workhorse | same |
| `search_assets` | Rule 23 first. `search_assets(source="polyhaven" \| "sketchfab" \| "polypizza", query=…, previews=N)` — results carry each asset's id | `search_polyhaven_assets` / `search_sketchfab_models` / `search_polypizza_models` |
| `import_asset` | Brings a found asset in: `import_asset(source, id, asset_type=…, target_size=…)` sizes it and reports the box; PolyHaven textures with `apply_to=[names]`. Record its licence (rule 17) | `download_polyhaven_asset` / `download_sketchfab_model` / `download_polypizza_model`, `set_texture` |
| `generate_3d` | A model from a generation API — Tripo, Hunyuan3D, Hyper3D, Meshy, or the server's paid Premium: **never by default** (rule 5); kiln's free route is the HF Spaces of `references/ai-generation.md` | `generate_hunyuan3d_model`, `generate_hyper3d_model_via_*`, `generate_tripo_model` and their poll / import tools — same rule |
| `disable_telemetry` | Leave telemetry off; never call `record_trajectory_feedback` | same |

Gone from the current surface, no replacement: `bpy_api_lookup` and `describe_node_type`
(look an API up with `execute_blender_code` — `dir()`, `bl_rna.properties` — rather than from
memory), and `export_scene` (export with `bpy.ops.export_scene.gltf` in `execute_blender_code`,
rules 18 and 19, as kiln always did).

## mcp-for-blender — what changed, what to know

**A library switched off answers in plain words.** `search_assets` on a source whose sidebar
box is unticked returns "Poly Haven is switched off. Ask the user to tick it in the MCP for
Blender sidebar (press N in the 3D Viewport)." Show the user that message — rule 23 — and offer
the other sources or the creation path. `get_addon_status()` says the same up front, in
`libraries`.

**Ticking a box takes effect immediately.** The flags are scene properties read at dispatch
time: no reconnection needed.

**`look` restores what it touches.** Every viewport setting it changes to take the picture is
put back. It frames the target itself in `angles` mode — rule 22 holds without the framing
code; in the default `viewport` mode it shows the viewport as it is aimed, so frame first.
`max_size` defaults to 768: images stay in the conversation, so keep checks small and go larger
only to read fine detail.

**`get_scene_info` measures.** Its `size` is the world bounding box: an axis-aligned box, so a
turned object reads larger than it is — for a print, `print_check`'s dimensions are the
measure, and headless the vertices in world space (rule 24).

**`generate_3d` can cost money.** Each call may use the user's API credits or a monthly
generation; "Premium" is a paid plan. kiln never calls it unasked (rule 5), and never points the
user to Premium.

**`user_prompt`.** Every tool takes the user's own words, for the server's telemetry. Pass the
brief as given, or nothing; telemetry stays off.

**Safe mode breaks kiln.** `BLENDER_MCP_SAFE_MODE=1` (off by default) lets scripts import only
`bpy`, `bmesh`, `mathutils` and pure-Python modules, and refuses `open`, `exec`, `sys`: kiln's
build scripts run through `exec(open(...))` and the live view through `sys.path`. If a script
is refused with "SAFE_MODE is enabled", say so: kiln needs it off, or builds headless (rule 21).

**Check the addon once per session.** `get_addon_status()` reports `up_to_date`; an outdated
addon misses commands. The fix: `uvx mcp-for-blender install-addon`, then disable and enable
"Interface: Blender MCP" in Blender's preferences (or restart Blender) and start the server.

**Two layers, different names.** These are MCP tool names. The addon's raw socket speaks
another vocabulary (`execute_code`), and `get_addon_status` is a server-side aggregation. Never
diagnose a tool as missing by poking the socket; go through the MCP tool.

## On the old surface (mcp-for-blender 2.1.3 and earlier)

Thirty-six tools, one per library and generator — the second column of the table above. Two
things differ in kind:

**A disabled integration does not fail, it disappears.** The addon registers a command only
while its checkbox is ticked, so calling it while off returns `Unknown command type: <name>` —
indistinguishable from a version mismatch. The `get_*_status` tools are always registered and
carry the fix: call them before a search (rule 23), and surface their `message`, never the raw
error. Their remediation text ends with "Restart the connection to Claude": not needed.

**`get_scene_info` carries no dimensions.** Measure with `get_object_info(name)` (rule 24), and
frame the viewport before `get_viewport_screenshot` (rule 22, PHASE 4's code).

`bpy_api_lookup` / `describe_node_type` exist there: look an API or a node's sockets up in the
running Blender rather than recalling it.

## On the official Blender Lab MCP

The Blender Foundation's server (`projects.blender.org/lab/blender_mcp`, the one
behind Claude's Blender connector) drives the same Blender with **different
tools, and none for marketplaces or generation**. Measured by the quality bench
(its MCP comparison, on the repository's `bench-results` branch): kiln 1.1.2 shipped the same 7 GLBs
on it, for 10% less cost. Map the tools, and source around the gaps:

| Rule needs | On the Lab MCP |
|---|---|
| the scene (rule 1) | `get_objects_summary` |
| dimensions (rule 24) | `get_object_detail_summary` |
| a look at the model (rule 2) | `get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")`, or `render_viewport_to_path` |
| framing (rule 22) | `jump_to_view3d_object_by_name` |
| an API looked up | `search_api_docs` / `get_python_api_docs`, plus `search_manual_docs` |
| `execute_blender_code` | same name |
| addon and integration status (rule 23) | none — `get_objects_summary` answering is the connection check |
| PolyHaven | the public API from Bash — `references/sourcing-strategy.md` |
| Sketchfab, Poly Pizza, generation | none — HF Spaces through `gradio_client`, `references/ai-generation.md` |
| export | `bpy.ops.export_scene.gltf` in `execute_blender_code` (rules 18, 19) |

Setup, each point measured: the add-on's manifest sets
`blender_version_min = "5.1.0"` — kiln's own floor stays 4.4, but this path needs
at least that; it installs as an extension; **online access on** (Preferences → System,
or `--online-mode`), or the add-on refuses to serve. Its PyPI-style package is
**also named `blender-mcp`**, so `uvx blender-mcp` starts ahujasid's server —
run it from git:
`uvx --from "git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp" blender-mcp`.
Register it under the MCP name `blender` so `mcp__blender__*` still matches.

**Rule 2 needs saying twice on this server.** The bench's sessions knew the capture
tool and called it right — then took **one screenshot per session** on 4 of 5
briefs, and framed once in five. At the end of every phase that changed geometry
or materials: `jump_to_view3d_object_by_name(name)`, then
`get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")`. After TEXTURING, a second
angle too. A single-asset run therefore takes **at least four** captures.
