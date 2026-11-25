"""Managed material styles. Both shaders remain editable in each .blend."""
import json
from pathlib import Path

import bpy

from upstream_scene import hex_rgb

ASSETS = json.loads((Path(__file__).resolve().parents[1] / "assets/presets.json").read_text())


def material(name, srgb, metallic=0.0, roughness=0.4):
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
    style_surface(mat, bpy.context.scene.get("materials_style", "studio"))
    return mat


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
