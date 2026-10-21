# Blender MCP — tool surface

> Read before the first phase when the Blender MCP is new to the session, and always on the
> official Blender Lab MCP (no `get_addon_status`): its tools have other names. Rule numbers are SKILL.md's Iron Rules.

All 36 tools exposed by `blender-mcp` **2.0.0** (bundled addon 1.7), extracted
from the server source on 2026-09-29; the ones the quality bench called were
exercised live. Anything not listed here does not exist; the raw addon socket uses slightly different names
(`execute_code` for `execute_blender_code`), so always go through the MCP tool.

| Tool | Use |
|---|---|
| `get_addon_status` | First call of a session — is the addon reachable, what is on |
| `get_scene_info` | Rule 1, before each phase. Object count and names only — **no dimensions** |
| `get_object_info` | Rule 24. Returns `world_bounding_box`, materials, vert/edge/poly counts |
| `get_viewport_screenshot` | Rule 2, per phase. `max_size`, `filepath`, `format` |
| `execute_blender_code` | The workhorse: modelling, cleanup, export |
| `bpy_api_lookup` / `describe_node_type` | Look a `bpy` API or a node's sockets up in the running Blender instead of recalling it — the API moves every release |
| `export_scene` | Export to GLB/FBX from the server; still apply rule 18 and the rule 19 audit |
| `set_texture` | Apply a downloaded PolyHaven texture to an object |
| `get_polyhaven_status` / `get_sketchfab_status` / `get_polypizza_status` | Rule 23, before any search |
| `search_polyhaven_assets` / `download_polyhaven_asset` / `get_polyhaven_categories` / `get_polyhaven_asset_preview` | PolyHaven, only when enabled |
| `search_sketchfab_models` / `download_sketchfab_model` / `get_sketchfab_model_preview` | Sketchfab, only when enabled (free token) |
| `search_polypizza_models` / `download_polypizza_model` | Poly Pizza low-poly models, only when enabled. Check each model's licence and record it (rule 17) |
| `get_hunyuan3d_status` / `generate_hunyuan3d_model` / `poll_hunyuan_job_status` / `import_generated_asset_hunyuan` | Native Hunyuan3D — **needs Tencent Cloud keys or a local API**, and the licence excludes the EU, UK and South Korea. Never by default; only on explicit request, licence shown, confirmed first |
| `get_hyper3d_status` / `generate_hyper3d_model_via_text` / `generate_hyper3d_model_via_images` / `poll_rodin_job_status` / `import_generated_asset` | Native Hyper3D Rodin — paid API (rule 5) |
| `get_tripo_status` / `generate_tripo_model` / `poll_tripo_job_status` / `import_generated_asset_tripo` | Native Tripo — paid (rule 5) |
| `disable_telemetry` / `record_trajectory_feedback` | Addon telemetry — opt-in since 2.0, leave it off |

**A disabled integration does not fail, it disappears.** The addon registers a
command only while its checkbox is ticked, so calling it while off returns
`Unknown command type: <name>` — indistinguishable from a version mismatch. The
`get_*_status` tools are always registered and carry the fix. Hence rule 23.

**Ticking a box takes effect immediately.** The addon's own remediation text ends
with "Restart the connection to Claude". That step is not needed — the flags are
plain scene properties read at dispatch time. Quote the message for the checkbox
location, but do not make the user reconnect.

**Two layers, different names.** These are MCP tool names. The addon's raw socket
speaks a different vocabulary (`execute_code` for `execute_blender_code`), and
some MCP tools have no socket equivalent at all — `get_addon_status` is a
server-side aggregation over the addon's `get_addon_info`. Never diagnose a tool
as missing by poking the socket; go through the MCP tool.

**Check the addon version once per session.** `get_addon_status()` reports
`up_to_date`. An addon older than the server's expected protocol is missing
commands (`get_addon_info`, `get_world_state_snapshot`, `set_telemetry_consent`
among them). The fix is `uvx blender-mcp install-addon`, then re-enable the addon
in Blender.

## On the official Blender Lab MCP

The Blender Foundation's server (`projects.blender.org/lab/blender_mcp`, the one
behind Claude's Blender connector) drives the same Blender with **different
tools, and none for marketplaces or generation**. Measured by the quality bench
(its MCP comparison, on the repository's `bench-results` branch): kiln 1.1.2 shipped the same 7 GLBs
on it, for 10% less cost. Map the tools, and source around the gaps:

| Skill says | On the Lab MCP |
|---|---|
| `get_scene_info` (rule 1) | `get_objects_summary` |
| `get_object_info` (rule 24) | `get_object_detail_summary` |
| `get_viewport_screenshot` (rule 2) | `get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")`, or `render_viewport_to_path` |
| frame the viewport (rule 22) | `jump_to_view3d_object_by_name` |
| `bpy_api_lookup` | `search_api_docs` / `get_python_api_docs`, plus `search_manual_docs` |
| `execute_blender_code` | same name |
| `get_addon_status`, `get_*_status` (rule 23) | none — `get_objects_summary` answering is the connection check |
| PolyHaven tools, `set_texture` | the public API from Bash — `references/sourcing-strategy.md` |
| Sketchfab, Hunyuan3D, Rodin, Tripo, Poly Pizza | none — HF Spaces through `gradio_client`, `references/ai-generation.md` |
| `export_scene` | `bpy.ops.export_scene.gltf` in `execute_blender_code` (rules 18, 19) |

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
