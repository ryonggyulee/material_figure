"""Composition helpers, with dimensions in angstrom and an orthographic camera."""
import bpy
from mathutils import Vector

from appearance import ASSETS
from upstream_scene import camera_look, use_device


CATEGORIES = ("atomistic", "continuum", "effect", "label")


def category_collection(name):
    if name not in CATEGORIES:
        raise ValueError(f"Unknown figure category: {name}")
    children = bpy.context.scene.collection.children
    for group in children:
        if group.get("figure_category", group.name) == name:
            return group
    group = bpy.data.collections.new(name)
    group["figure_category"] = name
    children.link(group)
    return group


def categorize(obj, name):
    """Place a figure object in one category, retaining unrelated collection links."""
    group = category_collection(name)
    if obj.name not in group.objects:
        group.objects.link(obj)
    root = bpy.context.scene.collection
    for old in obj.users_collection:
        if old == group:
            continue
        if old == root or (old.name in root.children and old.get("figure_category", old.name) in CATEGORIES):
            old.objects.unlink(obj)
    return obj


def setup(target, width, direction=(0.48, -1, 0.70), pixels=(1800, 1080)):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    use_device(scene)
    scene.render.resolution_x, scene.render.resolution_y = pixels
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.world = bpy.data.worlds.new("Paper and studio fill")
    scene.world.use_nodes = True
    tree = scene.world.node_tree
    path = tree.nodes.new("ShaderNodeLightPath")
    mix = tree.nodes.new("ShaderNodeMixShader")
    paper = tree.nodes.new("ShaderNodeBackground")
    paper.inputs[0].default_value = (1, 1, 1, 1)
    ambient = tree.nodes.get("Background")
    ambient.inputs[0].default_value = (1, 1, 1, 1)
    ambient.inputs[1].default_value = ASSETS["studio"]["world_strength"]
    tree.links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
    tree.links.new(ambient.outputs[0], mix.inputs[1])
    tree.links.new(paper.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], tree.nodes["World Output"].inputs["Surface"])
    target = Vector(target)
    cam = camera_look(target + Vector(direction).normalized() * width * 2, target, ortho=width)
    cam.data.clip_start, cam.data.clip_end = width * 0.001, width * 10
    # Scale the upstream three-softbox rig to the subject's field of view.
    for name, pos, power, size in [
        ("Key", (-0.65, -0.85, 1.3), 11, 0.85),
        ("Fill", (0.85, -0.45, 0.6), 5, 0.72),
        ("Rim", (0.1, 0.9, 0.95), 7, 0.65),
    ]:
        bpy.ops.object.light_add(type="AREA", location=target + Vector(pos) * width)
        lamp = bpy.context.object
        lamp.name = name
        lamp.rotation_euler = (target - lamp.location).to_track_quat("-Z", "Y").to_euler()
        lamp.data.energy = power * width ** 2
        lamp.data.size = size * width
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_rotation = cam.rotation_euler.to_quaternion()
            space.region_3d.view_distance = width * 1.15
            space.region_3d.view_location = target
            space.region_3d.view_perspective = "CAMERA"
            space.shading.color_type = "MATERIAL"
            space.overlay.show_overlays = False
            space.clip_end = cam.data.clip_end
    return cam


def slab(name, size, center, mat, bevel=0.18):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    for v in obj.data.vertices:
        v.co = tuple(c * d for c, d in zip(v.co, size))
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Edge finish", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        if hasattr(obj.data, "use_auto_smooth"):
            obj.data.use_auto_smooth = True
        obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    return categorize(obj, "continuum")
