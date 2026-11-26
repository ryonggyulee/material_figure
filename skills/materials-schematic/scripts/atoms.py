"""Native editable site/edge mesh and a non-realizing Geometry Nodes display."""
import json

import bpy
import numpy as np

from appearance import ASSETS, material, socket, swatch
from scene_tools import category_collection


def atomic_modifier(obj):
    matches = [m for m in obj.modifiers if m.type == "NODES" and m.node_group
               and any(n.type == "GROUP_INPUT" and "Atomic number" in n.outputs
                       for n in m.node_group.nodes)]
    if "structure_metadata" not in obj or len(matches) != 1:
        raise ValueError(f"{obj.name}: expected one skill-generated atomic display")
    return matches[0]


def element_material(asset):
    """Every ASE species uses the project's atom shader and its own element color."""
    return material("Element · " + asset["symbol"], asset["srgb"],
                    roughness=ASSETS["studio"]["atom_roughness"], atom=True)


def atomic_mesh(path, name="Atomic structure", *, replace=None):
    mod = atomic_modifier(replace) if replace is not None else None
    with np.load(path, allow_pickle=False) as data:
        xyz, edges = data["positions"], data["edges"]
        meta = json.loads(str(data["metadata"]))
        mesh = bpy.data.meshes.new(name)
        mesh.vertices.add(len(xyz))
        mesh.vertices.foreach_set("co", xyz.astype(np.float32).ravel())
        mesh.edges.add(len(edges))
        mesh.edges.foreach_set("vertices", edges.ravel())
        mesh.update()
        numbers = mesh.attributes.new("atomic_number", "INT", "POINT")
        numbers.data.foreach_set("value", data["numbers"])
        if replace is None:
            obj = bpy.data.objects.new(name, mesh)
            category_collection("atomistic").objects.link(obj)
        else:
            obj = replace
            previous = obj.data
            obj.data = mesh
            if not previous.users:
                bpy.data.meshes.remove(previous)
        obj["cell_angstrom_rows"] = data["cell"].ravel().tolist()
        obj["pbc"] = data["pbc"].astype(int).tolist()
        obj["structure_metadata"] = json.dumps(meta)
    palette = list(meta["palette"].items())
    add_bonds = bool(len(edges))
    y = 100
    if mod:
        group = mod.node_group
        branches = {n.label for n in group.nodes if n.type == "INSTANCE_ON_POINTS"}
        palette = [(z, asset) for z, asset in palette if asset["symbol"] not in branches]
        add_bonds = add_bonds and "One cylinder per displayed pair" not in branches
        if not palette and not add_bonds:
            return obj
        if group.users > 1:
            group = group.copy()
            mod.node_group = group
        y = min(n.location.y for n in group.nodes) - 400
    else:
        group = bpy.data.node_groups.new(name + " · ball and stick", "GeometryNodeTree")
        socket(group, "Geometry", "INPUT", "NodeSocketGeometry")
        element = socket(group, "Atomic number", "INPUT", "NodeSocketInt")
        socket(group, "Geometry", "OUTPUT", "NodeSocketGeometry")

    def node(kind, x, y, label=""):
        n = group.nodes.new(kind)
        n.location = x, y
        n.label = label
        return n

    wire = group.links.new
    if mod:
        source, = [n for n in group.nodes if n.type == "GROUP_INPUT"]
        join, = [n for n in group.nodes if n.type == "JOIN_GEOMETRY"]
        detail, = [n for n in group.nodes if n.label == "Viewport 2 / render 3"]
    else:
        source = node("NodeGroupInput", -1100, 100)
        join = node("GeometryNodeJoinGeometry", 680, 100)
        output = node("NodeGroupOutput", 900, 100)
        wire(join.outputs[0], output.inputs[0])

        viewport = node("GeometryNodeIsViewport", -1100, 400)
        detail = node("ShaderNodeMath", -870, 400, "Viewport 2 / render 3")
        detail.operation = "SUBTRACT"
        detail.inputs[0].default_value = 3
        wire(viewport.outputs[0], detail.inputs[1])

    def prototype(shape, mat, x, y):
        smooth = node("GeometryNodeSetShadeSmooth", x, y)
        wire(shape.outputs[0], smooth.inputs["Geometry"])
        assign = node("GeometryNodeSetMaterial", x + 180, y)
        assign.inputs["Material"].default_value = mat
        wire(smooth.outputs[0], assign.inputs["Geometry"])
        return assign.outputs[0]

    for number, asset in palette:
        sphere = node("GeometryNodeMeshIcoSphere", -680, y)
        sphere.inputs["Radius"].default_value = asset["radius"]
        wire(detail.outputs[0], sphere.inputs["Subdivisions"])
        sphere_geo = prototype(sphere, element_material(asset), -480, y)
        select = node("ShaderNodeMath", -100, y, asset["symbol"])
        select.operation = "COMPARE"
        select.inputs[1].default_value = int(number)
        select.inputs[2].default_value = 0.01
        wire(source.outputs["Atomic number"], select.inputs[0])
        instances = node("GeometryNodeInstanceOnPoints", 240, y, asset["symbol"])
        wire(source.outputs["Geometry"], instances.inputs["Points"])
        wire(select.outputs[0], instances.inputs["Selection"])
        wire(sphere_geo, instances.inputs["Instance"])
        wire(instances.outputs[0], join.inputs[0])

        y -= 370

    if add_bonds:
        y -= 180
        verts = node("GeometryNodeInputMeshEdgeVertices", -1100, y)
        delta = node("ShaderNodeVectorMath", -900, y)
        delta.operation = "SUBTRACT"
        wire(verts.outputs["Position 2"], delta.inputs[0])
        wire(verts.outputs["Position 1"], delta.inputs[1])
        capture = node("GeometryNodeCaptureAttribute", -680, y, "Bond vector on edges")
        capture.domain = "EDGE"
        if hasattr(capture, "capture_items"):
            capture.capture_items.new("VECTOR", "Direction")
        else:
            capture.data_type = "FLOAT_VECTOR"
        wire(source.outputs["Geometry"], capture.inputs["Geometry"])
        wire(delta.outputs[0], capture.inputs[1])
        vector = capture.outputs[1]
        midpoints = node("GeometryNodeMeshToPoints", -420, y)
        midpoints.mode = "EDGES"
        wire(capture.outputs[0], midpoints.inputs["Mesh"])
        length = node("ShaderNodeVectorMath", -400, y - 240)
        length.operation = "LENGTH"
        wire(vector, length.inputs[0])
        scale = node("ShaderNodeCombineXYZ", -180, y - 240)
        scale.inputs["X"].default_value = scale.inputs["Y"].default_value = 1
        wire(length.outputs["Value"], scale.inputs["Z"])
        align_type = ("FunctionNodeAlignRotationToVector" if bpy.app.version >= (4, 2, 0)
                      else "FunctionNodeAlignEulerToVector")
        align = node(align_type, -180, y - 460)
        align.axis = "Z"
        wire(vector, align.inputs["Vector"])
        rod = node("GeometryNodeMeshCylinder", -680, y - 650)
        rod.inputs["Depth"].default_value = 1
        rod.inputs["Radius"].default_value = ASSETS["bonds"]["radius_angstrom"]
        rod.inputs["Vertices"].default_value = 10
        bonds = node("GeometryNodeInstanceOnPoints", 240, y, "One cylinder per displayed pair")
        wire(prototype(rod, swatch("bond"), -430, y - 680), bonds.inputs["Instance"])
        wire(midpoints.outputs[0], bonds.inputs["Points"])
        wire(align.outputs[0], bonds.inputs["Rotation"])
        wire(scale.outputs[0], bonds.inputs["Scale"])
        wire(bonds.outputs[0], join.inputs[0])

    if mod is None:
        mod = obj.modifiers.new("Atoms and bonds", "NODES")
        mod.node_group = group
        mod[element.identifier + "_use_attribute"] = True
        mod[element.identifier + "_attribute_name"] = "atomic_number"
    obj.update_tag()
    return obj
