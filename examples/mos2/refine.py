"""Local publication variant of the reference device. Run against its saved blend."""
import bpy
from mathutils import Vector

from edits import label, surface, target
from labels import callout

scene = bpy.context.scene
camera = scene.camera
channel = target("Channel · 1H molybdenum disulfide")
# An illustrative transparent contact reveals the channel underneath. Identify
# the rendering convention on the figure itself.
surface("Drain · Au", opacity=0.28)
label("Au drain", text="Au drain (transparent view)", offset=(-1.8, 0))
target("Au drain").data.size = 1.85

# Keep the heading, and label sites at the exposed back edge of the finite sheet.
heading = target("MoS₂ channel")
old_line = heading.get("figure_leader") or target("Leader · MoS₂ channel")
if "figure_leader" in heading:
    del heading["figure_leader"]
bpy.data.objects.remove(old_line, do_unlink=True)
xyz = channel.data.vertices
numbers = channel.data.attributes["atomic_number"].data
assert numbers[69].value == 42 and numbers[124].value == 16
# The Mo centre is partially overlapped in projection; point to its visible flank.
flank = camera.matrix_world.to_quaternion() @ Vector((0.45, 0.14, 0))
callout(camera, "Mo", channel.matrix_world @ xyz[69].co + flank, (-5.2, 13.0), size=1.85, follow=channel)
callout(camera, "S", channel.matrix_world @ xyz[124].co, (3.0, 13.0), size=1.85, follow=channel)

# Shorten the length of dark stroke crossing the back-gate face.
gate_line = target("Leader · Doped Si back gate")
gate = target("Doped Si · back gate")
anchor = Vector((15, -11.5, -9.15))
gate_line["figure_anchor_object"] = gate
gate_line["figure_anchor_local"] = list(gate.matrix_world.inverted() @ anchor)
tip = camera.matrix_world.inverted() @ anchor
point = gate_line.data.splines[0].points[0]
point.co = (tip.x, tip.y, point.co.z, 1)
scene["model_notes"] += " Drain shown semitransparent to expose the channel overlap."

# Mixed transparent surfaces converge more slowly in Cycles.
scene.cycles.samples = 96
