"""Editable camera-plane callouts on an orthographic view."""
from pathlib import Path

import bpy
from mathutils import Vector

from upstream_scene import hex_rgb
from scene_tools import category_collection


def callout(camera, text, anchor, xy, above=True, size=2.2, follow=None):
    group = category_collection("label")
    ink = bpy.data.materials.get("Annotation ink")
    if ink is None:
        ink = bpy.data.materials.new("Annotation ink")
        ink.diffuse_color = hex_rgb("#223644")
        ink.use_nodes = True
        emit = ink.node_tree.nodes.new("ShaderNodeEmission")
        emit.inputs[0].default_value = ink.diffuse_color
        ink.node_tree.links.new(emit.outputs[0], ink.node_tree.nodes["Material Output"].inputs[0])
    width = camera.data.ortho_scale

    def attach(name, data):
        obj = bpy.data.objects.new(name, data)
        group.objects.link(obj)
        obj.parent = camera
        obj.visible_shadow = obj.visible_diffuse = obj.visible_glossy = False
        data.materials.append(ink)
        return obj

    bpy.context.view_layer.update()
    tip = camera.matrix_world.inverted() @ Vector(anchor)
    x, y = xy
    sign = 1 if above else -1
    label = bpy.data.curves.new(text, "FONT")
    font = bpy.data.fonts.load(str(Path(__file__).resolve().parents[1] / "assets/SourceSans3-Regular.otf"),
                               check_existing=True)
    if not font.packed_file:
        font.pack()
    label.font, label.body, label.size = font, text, size
    label.align_x = "CENTER"
    label.align_y = "BOTTOM_BASELINE" if above else "TOP_BASELINE"
    label_obj = attach(text, label)
    label_obj.location = (x, y + sign * 0.55 - (0 if above else size * 0.72), -width)

    line = bpy.data.curves.new("Leader · " + text, "CURVE")
    line.dimensions = "3D"
    line.resolution_u = 1
    line.bevel_depth = width * 0.00064
    line.bevel_resolution = 2
    spline = line.splines.new("POLY")
    spline.points.add(2)
    knee = (x, y - sign * min(1.3, abs(y - tip.y) / 2))
    for p, (u, v) in zip(spline.points, [(tip.x, tip.y), knee, (x, y)]):
        p.co = (u, v, -width, 1)
    leader = attach(line.name, line)
    label_obj["figure_leader"] = leader
    if follow is not None:
        leader["figure_anchor_object"] = follow
        leader["figure_anchor_local"] = list(follow.matrix_world.inverted() @ Vector(anchor))
    return label_obj
