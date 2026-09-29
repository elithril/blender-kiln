"""Blender startup for a bench run on the official Blender Lab MCP.

    Blender --online-mode --python-exit-code 1 --python bench/blender_start_lab.py

The add-on is installed by run.py as an extension of the throwaway profile
(`bl_ext.user_default.mcp`). It refuses to serve without online access, hence
--online-mode. It has no marketplace or generation integrations to configure.
"""
import addon_utils, bpy

MOD = "bl_ext.user_default.mcp"
addon_utils.enable(MOD, default_set=True, persistent=True)
if MOD not in bpy.context.preferences.addons:
    raise SystemExit(f"BENCH could not enable {MOD}")
print("BENCH online_access", bpy.app.online_access)
bpy.ops.blmcp.server_start()
print("BENCH lab server start requested")
