"""Executed by Blender through host.py with the prepared channel in 'structure'."""
import bpy

from appearance import swatch
from edits import target
from labels import callout
from scene_tools import setup, slab

structure.name = "Channel · 1H molybdenum disulfide"
structure["figure_id"] = "channel"
camera = setup((0, 0, -1.9), 62, direction=(0.28, -1, 0.72), pixels=(1800, 1240))
# Nominal cartoon device dimensions, in the same coordinate frame as the atoms.
# The adjacent surfaces meet the atom display envelopes at the outer S planes.
oxide_top = -2.25
gate = slab("Doped Si · back gate", (49, 23, 4.2), (0, 0, oxide_top - 3.3 - 2.1), swatch("silicon"))
gate["figure_id"] = "gate"
oxide = slab("SiO₂ · dielectric", (49, 23, 3.3), (0, 0, oxide_top - 1.65), swatch("oxide"))
oxide["figure_id"] = "dielectric"
for name, x in [("Source", -17.9), ("Drain", 17.9)]:
    pad = slab(name + " · Au", (9.8, 18.3, 3.6), (x, 0, 2.25 + 1.8), swatch("gold"), 0.25)
    pad["figure_id"] = name.lower()

callout(camera, "Au source", (-17.9, 0, 5.85), (-20.8, 16.0), follow=target("source"))
callout(camera, "MoS₂ channel", (0, 1, 1.595), (-0.5, 16.0), follow=structure)
callout(camera, "Au drain", (17.9, 0, 5.85), (21.0, 16.0), follow=target("drain"))
callout(camera, "SiO₂ gate dielectric", (-10, -11.5, -3.9), (-15.5, -16.6), above=False, follow=oxide)
callout(camera, "Doped Si back gate", (10, -11.5, -7.6), (12.3, -16.6), above=False, follow=gate)

bpy.context.scene["model_notes"] = ("Ideal 1H monolayer, finite boundaries. Au top contacts. "
    "SiO2 and doped Si shown as continua. Device dimensions and interface spacings are illustrative.")
bpy.ops.object.select_all(action="DESELECT")
structure.select_set(True)
bpy.context.view_layer.objects.active = structure
