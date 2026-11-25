"""Specify the back-gate doping in the existing native text object."""
import bpy

from edits import label

label("Doped Si back gate", text="n⁺ Si back gate")
bpy.context.scene["gate_doping"] = "n+ (illustrative)"
