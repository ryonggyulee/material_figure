"""Local edits to objects in the active Blender scene."""
import re

import bpy
from mathutils import Vector

from appearance import ASSETS
from atoms import atomic_modifier
from upstream_scene import hex_rgb


def target(key):
    """Resolve an exact object name or an optional stable figure_id in this scene."""
    if isinstance(key, bpy.types.Object):
        return key
    matches = [obj for obj in bpy.context.scene.objects if obj.name == key or obj.get("figure_id") == key]
    if len(matches) != 1:
        raise ValueError(f"Expected one scene object for {key!r}, found {len(matches)}")
    return matches[0]


def _material_binding(obj, element, slot):
    if element is None:
        if not (0 <= slot < len(obj.material_slots)) or obj.material_slots[slot].material is None:
            raise ValueError(f"{obj.name}: no material in slot {slot}")
        binding = obj.material_slots[slot]
        mat = binding.material
        if binding.link == "DATA" and obj.data.users > 1:
            binding.link = "OBJECT"
            binding.material = mat
        return binding, "material"
    mod = atomic_modifier(obj)
    if mod.node_group.users > 1:
        mod.node_group = mod.node_group.copy()
    branches = [n for n in mod.node_group.nodes if n.type == "INSTANCE_ON_POINTS" and n.label == element]
    if len(branches) != 1:
        raise ValueError(f"{obj.name}: expected one atomic display branch for {element!r}")
    link, = branches[0].inputs["Instance"].links
    assign = link.from_node
    if assign.type != "SET_MATERIAL" or assign.inputs["Material"].is_linked:
        raise ValueError(f"{obj.name}: inspect the customized {element} material graph")
    return assign.inputs["Material"], "default_value"


def _set_opacity(mat, opacity):
    tree = mat.node_tree
    mix = tree.nodes.get("Figure opacity")
    if mix is None:
        surface = tree.get_output_node("ALL").inputs["Surface"]
        link, = surface.links
        shader = link.from_socket
        mix = tree.nodes.new("ShaderNodeMixShader")
        mix.name = "Figure opacity"
        clear = tree.nodes.new("ShaderNodeBsdfTransparent")
        tree.links.new(clear.outputs[0], mix.inputs[1])
        tree.links.new(shader, mix.inputs[2])
        tree.links.new(mix.outputs[0], surface)
    mix.inputs[0].default_value = opacity
    mat.diffuse_color[3] = opacity


def surface(key, *, element=None, slot=0, color=None, roughness=None, opacity=None):
    """Edit one object's material slot or one species in one atomic display."""
    if all(v is None for v in (color, roughness, opacity)):
        raise ValueError("Specify color, roughness, or opacity")
    if color is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError("Use a six-digit sRGB color, e.g. #407CA0")
    for v in (roughness, opacity):
        if v is not None and not 0 <= v <= 1:
            raise ValueError("Roughness and opacity must be between 0 and 1")
    obj = target(key)
    binding, attr = _material_binding(obj, element, slot)
    mat = getattr(binding, attr)
    if mat is None or not mat.use_nodes:
        raise ValueError("Select a node-based material")
    if (color is not None or roughness is not None) and not mat.get("materials_schematic"):
        raise ValueError("Color/roughness helpers require a managed material; inspect the artist shader")
    # Even a single-user preset may be reused by name when a new part is added.
    if mat.users > 1 or not mat.get("figure_local"):
        mat = mat.copy()
        mat["figure_local"] = True
        setattr(binding, attr, mat)
    nodes = mat.node_tree.nodes
    if color is not None:
        rgb = hex_rgb(color)
        studio = nodes["Studio"].inputs["Base Color"]
        if studio.is_linked:
            raise ValueError("Base Color is driven by a custom node")
        ramp = nodes["Cartoon"].inputs["Color"].links[0].from_node.color_ramp
        tones = ASSETS["cartoon"]["tones"]
        if len(tones) != len(ramp.elements):
            raise ValueError("Inspect the custom cartoon color ramp before recoloring")
        studio.default_value = rgb
        mat.diffuse_color = (*rgb[:3], mat.diffuse_color[3])
        for stop, tone in zip(ramp.elements, tones):
            stop.color = (*[min(1, c * tone) for c in rgb[:3]], 1)
    if roughness is not None:
        socket = nodes["Studio"].inputs["Roughness"]
        if socket.is_linked:
            raise ValueError("Roughness is driven by a custom node")
        socket.default_value = roughness
    if opacity is not None:
        _set_opacity(mat, opacity)
    return mat


def label(key, *, text=None, offset=None):
    """Set native text or move a camera-plane callout by (dx, dy) scene units."""
    obj = target(key)
    if obj.type != "FONT":
        raise ValueError(f"{obj.name} is not editable text")
    if text is not None:
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        obj.data.body = text
    if offset is None:
        return
    dx, dy = offset
    delta = Vector((dx, dy, 0))
    leader = obj.get("figure_leader") or bpy.context.scene.objects.get("Leader · " + obj.name)
    if leader is not None:
        if any(other != obj and other.get("figure_leader") == leader for other in bpy.context.scene.objects):
            raise ValueError("Assign a dedicated leader before moving labels that share one")
        if leader.parent != obj.parent or not obj.parent or obj.parent.type != "CAMERA":
            raise ValueError("Inspect the custom callout parenting before moving its leader")
        if leader.data.users > 1:
            leader.data = leader.data.copy()
        spline, = leader.data.splines
        if spline.type != "POLY" or len(spline.points) != 3:
            raise ValueError("Inspect the custom leader path")
        line_delta = leader.matrix_local.to_3x3().inverted() @ delta
        for p in list(spline.points)[1:]:
            p.co = (*(p.co.xyz + line_delta), p.co.w)
    obj.location += delta


def refresh_leaders(key):
    """Reproject stored local anchors for this part after moving it in the scene."""
    part = target(key)
    bpy.context.view_layer.update()
    for leader in bpy.context.scene.objects:
        if leader.get("figure_anchor_object") != part:
            continue
        camera = leader.parent
        world = part.matrix_world @ Vector(leader["figure_anchor_local"])
        projected = camera.matrix_world.inverted() @ world
        if leader.data.users > 1:
            leader.data = leader.data.copy()
        point = leader.data.splines[0].points[0]
        projected.z = (leader.matrix_local @ point.co.xyz).z
        point.co = (*(leader.matrix_local.inverted() @ projected), point.co.w)
