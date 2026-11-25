"""Run in a Blender window. Orbit a solid viewport and time completed swaps."""
import json
import math
import sys
from statistics import median
import time
import traceback

import bpy
from mathutils import Quaternion


def benchmark():
    try:
        window = bpy.context.window_manager.windows[0]
        area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
        space = area.spaces.active
        view = space.region_3d
        space.shading.type = "SOLID"
        view.view_perspective = "ORTHO"
        for group in bpy.data.collections:
            if group.get("figure_category", group.name) in ("label", "Callouts"):
                group.hide_viewport = True
        if "--" in sys.argv and "--wire" in sys.argv[sys.argv.index("--") + 1:]:
            for obj in bpy.context.scene.objects:
                if "structure_metadata" in obj:
                    obj.modifiers["Atoms and bonds"].show_viewport = False
                    obj.display_type = "WIRE"
        times = []
        for i in range(27):
            view.view_rotation = Quaternion((0, 0, 1), math.radians(2)) @ view.view_rotation
            area.tag_redraw()
            start = time.perf_counter()
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
            if i >= 3:
                times.append(time.perf_counter() - start)
        print("VIEWPORT", json.dumps(dict(width=area.width, height=area.height, frames=len(times),
              median_ms=median(times)*1000, p95_ms=sorted(times)[math.ceil(.95*len(times))-1]*1000)),
              flush=True)
    except Exception:
        traceback.print_exc()
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(benchmark, first_interval=2)
