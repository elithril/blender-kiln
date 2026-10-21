"""Blender startup for tools/open_blender.py: enable the user's Blender MCP add-on and start
its server on $KILN_MCP_PORT (default 9876), in the user's own Blender and preferences.

    Blender --python tools/blender_mcp_start.py

Nothing is saved to the preferences (the add-on is enabled for this session only when it
was off). The add-on is ahujasid's mcp-for-blender (formerly blender-mcp; module `blender_mcp`),
installed with `uvx mcp-for-blender install-addon`.
"""
import os
import sys

import addon_utils
import bpy

PORT = int(os.environ.get("KILN_MCP_PORT", "9876"))

if "blender_mcp" not in bpy.context.preferences.addons:
    addon_utils.enable("blender_mcp", default_set=True, persistent=False)
if "blender_mcp" not in bpy.context.preferences.addons:
    print("KILN: the Blender MCP add-on is not installed (uvx mcp-for-blender install-addon)", file=sys.stderr, flush=True)
else:
    scene = bpy.context.scene
    if hasattr(scene, "blendermcp_port"):
        scene.blendermcp_port = PORT

    def start() -> None:
        # After the window is up: the operator needs a context, and an auto-started server
        # (the add-on's own option) is left alone.
        try:
            bpy.ops.blendermcp.start_server()
            print(f"KILN: Blender MCP add-on serving on port {PORT}", flush=True)
        except Exception as e:   # already running, or an add-on without that operator
            print(f"KILN: could not start the add-on's server: {e}", file=sys.stderr, flush=True)
        return None

    bpy.app.timers.register(start, first_interval=1.0)
