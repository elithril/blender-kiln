"""Blender startup for a bench run: enable the MCP addon, set its integrations, serve.

    Blender --python-exit-code 1 --python bench/blender_start.py

Run with BLENDER_USER_SCRIPTS / BLENDER_USER_CONFIG pointing at a throwaway
profile (bench/run.py does), so the user's own Blender setup is never touched.
The integrations match what the briefs need: PolyHaven on, everything that
needs a key or a paid account off, telemetry off.
"""
import addon_utils, bpy

addon_utils.enable("blender_mcp", default_set=True, persistent=True)

scene = bpy.context.scene
settings = {
    "blendermcp_use_polyhaven": True,
    "blendermcp_use_sketchfab": False,
    "blendermcp_use_hyper3d": False,
    "blendermcp_use_hunyuan3d": False,   # the brief uses the HF Space via gradio_client, the skill's path
    "blendermcp_use_tripo": False,
    "blendermcp_use_polypizza": False,
}
for k, v in settings.items():
    if hasattr(scene, k):
        setattr(scene, k, v)
        print(f"BENCH setting {k}={v}")
    else:
        print(f"BENCH absent {k}")

prefs = bpy.context.preferences.addons.get("blender_mcp")
if prefs and hasattr(prefs.preferences, "telemetry_consent"):
    prefs.preferences.telemetry_consent = False
    print("BENCH telemetry_consent=False")

bpy.ops.blendermcp.start_server()
print("BENCH server started on", scene.blendermcp_port)
