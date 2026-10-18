"""Blender startup for Kiln Studio's Claude worker: enable the MCP add-on, serve on the
worker's own port, never on 9876 (the user's own Blender, or a bench, uses that one).

    Blender --factory-startup --python-exit-code 1 --python worker_blender.py

worker.py runs it with KILN_BLENDER_PORT and KILN_BLENDER_MCP (ahujasid or lab) set, and
BLENDER_USER_* pointing at a profile under .kiln-studio/cache/worker/, so the user's own
Blender setup is never touched. Same approach as bench/blender_start.py.
"""
import os

import addon_utils
import bpy

PORT = int(os.environ["KILN_BLENDER_PORT"])
if os.environ.get("KILN_BLENDER_PIDFILE"):
    # Opened through macOS's `open -g` (behind the other windows), Studio has no process
    # of its own to stop: it reads this one.
    with open(os.environ["KILN_BLENDER_PIDFILE"], "w") as f:
        f.write(str(os.getpid()))
KIND = os.environ.get("KILN_BLENDER_MCP", "ahujasid")
if PORT == 9876:
    raise SystemExit("KILN worker: refusing port 9876, the usual Blender MCP port")

if KIND == "lab":
    MOD = "bl_ext.user_default.mcp"
    addon_utils.enable(MOD, default_set=True, persistent=False)
    if MOD not in bpy.context.preferences.addons:
        raise SystemExit(f"KILN worker: could not enable {MOD}")
    prefs = bpy.context.preferences.addons[MOD].preferences
    if hasattr(prefs, "use_autostart"):
        prefs.use_autostart = False
    prefs.port = PORT
    bpy.ops.blmcp.server_start()
    print("KILN worker: Blender Lab MCP on", PORT, flush=True)
else:
    addon_utils.enable("blender_mcp", default_set=True, persistent=False)

    def pin(scene) -> None:
        # The add-on's own auto-start reads the scene's port (default 9876): every scene,
        # the startup one and any .blend Claude opens, says ours and does not auto-start.
        if hasattr(scene, "blendermcp_auto_start_server"):
            scene.blendermcp_auto_start_server = False
        scene.blendermcp_port = PORT
        for k, v in {"blendermcp_use_polyhaven": True, "blendermcp_use_sketchfab": False,
                     "blendermcp_use_hyper3d": False, "blendermcp_use_hunyuan3d": False,
                     "blendermcp_use_tripo": False, "blendermcp_use_polypizza": False}.items():
            if hasattr(scene, k):
                setattr(scene, k, v)

    pin(bpy.context.scene)

    @bpy.app.handlers.persistent
    def _kiln_pin_port(_unused) -> None:
        for s in bpy.data.scenes:
            pin(s)

    bpy.app.handlers.load_post.append(_kiln_pin_port)
    p = bpy.context.preferences.addons.get("blender_mcp")
    if p and hasattr(p.preferences, "telemetry_consent"):
        p.preferences.telemetry_consent = False
    bpy.ops.blendermcp.start_server()
    print("KILN worker: blender-mcp on", bpy.context.scene.blendermcp_port, flush=True)
