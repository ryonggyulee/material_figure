"""Blender-side entrypoint for host.py."""
import argparse
from pathlib import Path
import runpy
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from appearance import ASSETS, set_style
from atoms import atomic_mesh
from edits import target
from scene_tools import CATEGORIES, category_collection, setup
from upstream_scene import use_device

cli = argparse.ArgumentParser()
for flag in ("input", "output", "geometry", "script", "style", "render", "replace"):
    cli.add_argument("--" + flag)
cli.add_argument("--preview", action="store_true")
cli.add_argument("--transparent", action=argparse.BooleanOptionalAction)
args = cli.parse_args(sys.argv[sys.argv.index("--") + 1:])
start = time.perf_counter()
if not args.input:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in CATEGORIES:
        category_collection(name)
structure = None
if args.geometry:
    structure = atomic_mesh(args.geometry, replace=target(args.replace) if args.replace else None)
if args.script:
    sys.path.insert(0, str(Path(args.script).resolve().parent))
    runpy.run_path(args.script, init_globals={"structure": structure}, run_name="__main__")
scene = bpy.context.scene
if not args.input and not scene.camera:
    if structure is None:
        raise ValueError("Composition needs a camera. Use scene_tools.setup().")
    bpy.context.view_layer.update()
    # Frame the scientific mesh; instanced display bounds differ across Blender versions.
    import numpy as np
    coords = np.empty(len(structure.data.vertices) * 3, dtype=np.float32)
    structure.data.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    center = structure.matrix_world @ Vector((coords.max(0) + coords.min(0)) / 2)
    width = (np.linalg.norm(np.ptp(coords, axis=0)) + 4) * 1.6
    setup(center, width)
if args.style or not args.input:
    set_style(args.style or "studio")
if not args.input or args.transparent is not None:
    transparent = ASSETS["output"]["transparent"] if args.transparent is None else args.transparent
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
if structure is not None and not args.replace:
    bpy.ops.object.select_all(action="DESELECT")
    structure.select_set(True)
    bpy.context.view_layer.objects.active = structure
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=args.output, compress=True)
print("BUILD_AND_SAVE_SECONDS", round(time.perf_counter() - start, 4), flush=True)
if args.render:
    # Export preference applies after saving a locally revised scene.
    if args.input and args.transparent is None:
        scene.render.film_transparent = ASSETS["output"]["transparent"]
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA" if scene.render.film_transparent else "RGB"
    if args.input and scene.render.engine == "CYCLES" and "materials_style" in scene:
        use_device(scene)
    if args.preview:
        scene.render.resolution_percentage = max(1, scene.render.resolution_percentage // 2)
        scene.cycles.samples = max(1, scene.cycles.samples // 4)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = args.render
    bpy.ops.render.render(write_still=True)
