"""Managed material styles. Both shaders remain editable in each .blend."""
import json
from pathlib import Path

import bpy

from upstream_scene import hex_rgb

ASSETS = json.loads((Path(__file__).resolve().parents[1] / "assets/presets.json").read_text())


def socket(group, name, direction, kind):
    if bpy.app.version >= (4, 0, 0):
        return group.interface.new_socket(name=name, in_out=direction, socket_type=kind)
    sockets = group.inputs if direction == "INPUT" else group.outputs
    return sockets.new(kind, name)


def atom_band_group():
    """Share one editable tone control across element materials in the blend."""
    bands = ASSETS["cartoon"]["atom_bands"]
    if len(bands["transitions"]) + 1 != bands["tone_count"] or not 0 <= bands["strength"] <= 1:
        raise ValueError("cartoon.atom_bands requires one transition per boundary and strength in [0, 1]")
    name = "Atom cartoon shading"
    for group in bpy.data.node_groups:
        if group.get("materials_schematic_atom_bands"):
            return group
    # The originally approved scene predates the marker. Reuse its working control.
    group = bpy.data.node_groups.get(name)
    if group and group.bl_idname == "ShaderNodeTree" and group.nodes.get("Band strength"):
        inputs = next((n.outputs for n in group.nodes if n.type == "GROUP_INPUT"), ())
        outputs = next((n.inputs for n in group.nodes if n.type == "GROUP_OUTPUT"), ())
        if "Smooth light" in inputs and "Direct light" in inputs and "Tone" in outputs:
            return group

    group = bpy.data.node_groups.new(name, "ShaderNodeTree")
    group["materials_schematic_atom_bands"] = True
    socket(group, "Smooth light", "INPUT", "NodeSocketFloat")
    socket(group, "Direct light", "INPUT", "NodeSocketFloat")
    socket(group, "Tone", "OUTPUT", "NodeSocketFloat")
    source = group.nodes.new("NodeGroupInput")
    source.location = (-520, 80)
    steps = group.nodes.new("ShaderNodeValToRGB")
    steps.label = f"{bands['tone_count']} tones with soft edges"
    steps.location = (-280, -100)
    steps.color_ramp.interpolation = "EASE"
    levels = steps.color_ramp.elements
    low = 0.0
    half_width = bands["edge_half_width"]
    for threshold, high in bands["transitions"]:
        levels.new(threshold - half_width).color = (low, low, low, 1)
        levels.new(threshold + half_width).color = (high, high, high, 1)
        low = high
    mix = group.nodes.new("ShaderNodeMixRGB")
    mix.name = mix.label = "Band strength"
    mix.location = (40, 90)
    mix.inputs[0].default_value = bands["strength"]
    out = group.nodes.new("NodeGroupOutput")
    out.location = (260, 90)
    wire = group.links.new
    wire(source.outputs["Direct light"], steps.inputs["Fac"])
    wire(source.outputs["Smooth light"], mix.inputs[1])
    wire(steps.outputs["Color"], mix.inputs[2])
    wire(mix.outputs[0], out.inputs["Tone"])
    return group


def material(name, srgb, metallic=0.0, roughness=0.4, *, atom=False):
    if atom:
        # A legacy material can have the same name and a different shader.
        # Keep it on the old mesh and reuse the new preset on subsequent imports.
        for mat in bpy.data.materials:
            if mat.get("atom_preset_name") == name and not mat.get("figure_local"):
                return mat
    else:
        existing = bpy.data.materials.get(name)
        if existing and existing.get("materials_schematic"):
            return existing
    if isinstance(srgb, str):
        rgba = hex_rgb(srgb)
    else:
        rgba = tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in srgb) + (1,)
    mat = bpy.data.materials.new(name)
    mat["materials_schematic"] = True
    mat.diffuse_color = rgba
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    wire = mat.node_tree.links.new
    surface = nodes.get("Principled BSDF")
    surface.name = "Studio"
    surface.inputs["Base Color"].default_value = rgba
    surface.inputs["Roughness"].default_value = roughness
    surface.inputs["Metallic"].default_value = metallic
    settings = ASSETS["cartoon"]
    normal = nodes.new("ShaderNodeNewGeometry")
    normal.location = (-750, -300)
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.location = (-520, -300)
    wire(normal.outputs["Normal"], dot.inputs[0])
    dot.inputs[1].default_value = settings["light_direction"]
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-320, -300)
    ramp.color_ramp.interpolation = "CONSTANT"
    colors = ramp.color_ramp.elements
    colors.remove(colors[1])
    for i, (stop, tone) in enumerate(zip(settings["thresholds"], settings["tones"])):
        element = colors.new(stop) if i else colors[0]
        element.color = tuple(min(1, c * tone) for c in rgba[:3]) + (1,)
    wire(dot.outputs["Value"], ramp.inputs[0])
    flat = nodes.new("ShaderNodeEmission")
    flat.name = "Cartoon"
    flat.location = (0, -300)
    wire(ramp.outputs[0], flat.inputs[0])
    if atom:
        mat["atom_preset_name"] = name
        smooth_cartoon_atom(mat)
        factor = ramp.inputs["Fac"]
        smooth = factor.links[0].from_socket
        bands = nodes.new("ShaderNodeGroup")
        bands.node_tree = atom_band_group()
        bands.label = "Atom cartoon shading"
        bands.location = (ramp.location.x, ramp.location.y - 360)
        wire(smooth, bands.inputs["Smooth light"])
        wire(dot.outputs["Value"], bands.inputs["Direct light"])
        wire(bands.outputs["Tone"], factor)
    style_surface(mat, bpy.context.scene.get("materials_style", "studio"))
    return mat


def smooth_cartoon_atom(mat):
    """Replace the hard cartoon bands on an atom with a softly shaded ramp."""
    tree = mat.node_tree
    ramp = tree.nodes["Cartoon"].inputs["Color"].links[0].from_node
    factor = ramp.inputs["Fac"]
    light = factor.links[0].from_socket
    if light.node.bl_idname == "ShaderNodeVectorMath" and light.node.operation == "DOT_PRODUCT":
        # Extend the transition past grazing light while keeping a readable shadow.
        wrap = tree.nodes.new("ShaderNodeMath")
        wrap.operation = "MULTIPLY_ADD"
        wrap.label = "Wrap light around atom"
        wrap.location = (ramp.location.x - 180, ramp.location.y - 310)
        scale = 1 / (1 + ASSETS["cartoon"]["atom_light_wrap"])
        wrap.inputs[1].default_value = scale
        wrap.inputs[2].default_value = 1 - scale
        tree.links.new(light, wrap.inputs[0])
        tree.links.new(wrap.outputs[0], factor)
    ramp.color_ramp.interpolation = "B_SPLINE"


def style_surface(mat, style):
    tree = mat.node_tree
    mix = tree.nodes.get("Figure opacity")
    destination = mix.inputs[2] if mix else tree.get_output_node("ALL").inputs["Surface"]
    tree.links.new(tree.nodes[style.title()].outputs[0], destination)


def swatch(name):
    p = ASSETS["materials"][name]
    return material("Device · " + name, p["color"], p["metallic"], p["roughness"])


def set_style(style):
    scene = bpy.context.scene
    for mat in bpy.data.materials:
        if mat.get("materials_schematic") and mat.use_nodes:
            style_surface(mat, style)
    scene["materials_style"] = style
    scene.cycles.samples = ASSETS[style]["samples"]
    scene.cycles.use_denoising = style == "studio"
