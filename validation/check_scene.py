"""Run with blender -b --python-exit-code 1 -P validation/check_scene.py [-- revised.blend --refined-dir DIR]."""
import argparse
from collections import Counter
from pathlib import Path
import runpy
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples/mos2"
sys.path.insert(0, str(ROOT / "skills/materials-schematic/scripts"))
from appearance import set_style
from edits import refresh_leaders, target


def read_mesh(obj):
    mesh = obj.data
    xyz = np.empty(3 * len(mesh.vertices), np.float32)
    edges = np.empty(2 * len(mesh.edges), np.int32)
    numbers = np.empty(len(mesh.vertices), np.int32)
    mesh.vertices.foreach_get("co", xyz)
    mesh.edges.foreach_get("vertices", edges)
    mesh.attributes["atomic_number"].data.foreach_get("value", numbers)
    return xyz.reshape(-1, 3), edges.reshape(-1, 2), numbers


def endpoint_heights(obj):
    coords = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
    return np.array([min(coords), max(coords)])


def snapshot():
    return {kind: {item.name: item.as_pointer() for item in getattr(bpy.data, kind)}
            for kind in ("objects", "meshes", "materials", "node_groups", "cameras", "curves")}


def check_file(path, style, label):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    assert scene["materials_style"] == style
    obj, = [o for o in scene.objects if "structure_metadata" in o]
    xyz, edges, numbers = read_mesh(obj)
    with np.load(DEMO / "channel.npz", allow_pickle=False) as d:
        np.testing.assert_allclose(xyz, d["positions"], atol=1e-6)
        for key, actual in (("edges", edges), ("numbers", numbers), ("pbc", obj["pbc"]),
                            ("cell", np.reshape(obj["cell_angstrom_rows"], (3, 3)))):
            np.testing.assert_array_equal(actual, d[key])
    assert Counter(numbers) == {42: 72, 16: 144}
    np.testing.assert_allclose(np.unique(xyz[:, 2]), [-1.595, 0, 1.595], atol=1e-6)
    assert {tuple(p) for p in xyz[xyz[:, 2] > 1, :2]} == {tuple(p) for p in xyz[xyz[:, 2] < -1, :2]}
    left, right = edges.T
    assert len(edges) == 396 and np.all(numbers[left] != numbers[right])
    np.testing.assert_allclose(np.linalg.norm(xyz[right] - xyz[left], axis=1), 2.43204132, atol=2e-6)
    degree = np.bincount(edges.ravel(), minlength=len(xyz))
    assert np.sum(degree[numbers == 42] == 6) == 55
    assert np.max(degree[numbers == 16]) == 3
    endpoints = {tuple(v.round(4)) for v in xyz}
    count = rods = 0
    for inst in bpy.context.evaluated_depsgraph_get().object_instances:
        if not inst.is_instance or inst.object.original != obj:
            continue
        count += 1
        ma = np.asarray(inst.matrix_world)
        # Cylinder prototypes have depth one. Both displayed endpoints must be sites.
        if np.linalg.norm(ma[:3, 2]) > 2:
            rods += 1
            for sign in (-0.5, 0.5):
                tip = (ma[:3, 3] + sign * ma[:3, 2]).astype(np.float32)
                assert tuple(tip.round(4)) in endpoints
        else:
            assert tuple(ma[:3, 3].astype(np.float32).round(4)) in endpoints
    assert (count, rods) == (612, 396)
    gate = bpy.data.objects["Doped Si · back gate"]
    oxide = bpy.data.objects["SiO₂ · dielectric"]
    assert np.isclose(endpoint_heights(gate)[1], endpoint_heights(oxide)[0])
    assert endpoint_heights(oxide)[1] < min(xyz[:, 2])
    for sign, name in ((-1, "Source · Au"), (1, "Drain · Au")):
        contact = bpy.data.objects[name]
        x0 = sign * contact.location.x - contact.dimensions.x / 2
        assert 0 < x0 < np.max(sign * xyz[:, 0])
        assert endpoint_heights(contact)[0] > max(xyz[:, 2])
    text = bpy.data.objects["Doped Si back gate"].data
    assert text.body == label and text.font.packed_file
    print(path.name, count, "atom and bond instances;", len(scene.objects), "editable scene objects")
    return obj


def camera_and_lights(scene):
    state = {o.name: (np.asarray(o.matrix_world).tolist(), o.data.energy, tuple(o.data.color))
             for o in scene.objects if o.type == "LIGHT"}
    camera = scene.camera
    state[camera.name] = (np.asarray(camera.matrix_world).tolist(), camera.data.ortho_scale)
    return state


def check_refined(directory, original_view):
    for style in ("studio", "cartoon"):
        check_file(directory / (style + ".blend"), style, "Doped Si back gate")
        scene = bpy.context.scene
        assert camera_and_lights(scene) == original_view
        assert scene.render.film_transparent
        drain = target("drain")
        assert abs(drain.active_material.node_tree.nodes["Figure opacity"].inputs[0].default_value - 0.28) < 1e-5
        assert target("source").active_material.node_tree.nodes.get("Figure opacity") is None
        for symbol in ("Mo", "S"):
            assert target(symbol)["figure_leader"]["figure_anchor_object"] == target("channel")
        point = target("Au drain")["figure_leader"].data.splines[0].points[0]
        tip = point.co.copy()
        label_pos = target("Au drain").location.copy()
        drain.location.x += 2
        refresh_leaders(drain)
        shift = scene.camera.matrix_world.inverted().to_3x3() @ Vector((2, 0, 0))
        assert abs(point.co.x - tip.x - shift.x) < 1e-4 and abs(point.co.y - tip.y - shift.y) < 1e-4
        assert target("Au drain").location == label_pos
    print("PASS refined studio and cartoon, reference view and local callout edits")


options = argparse.ArgumentParser()
options.add_argument("revised", nargs="?", type=Path)
options.add_argument("--refined-dir", type=Path, help="Directory containing the refined studio and cartoon blends")
args = options.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
check_file(DEMO / "studio.blend", "studio", "Doped Si back gate")
original_view = camera_and_lights(bpy.context.scene)
before = snapshot()
set_style("cartoon")
runpy.run_path(str(DEMO / "revise.py"))
assert snapshot() == before
assert bpy.data.objects["Doped Si back gate"].data.body == "n⁺ Si back gate"
check_file(DEMO / "cartoon.blend", "cartoon", "Doped Si back gate")
if args.revised:
    check_file(args.revised.resolve(), "cartoon", "n⁺ Si back gate")
if args.refined_dir:
    check_refined(args.refined_dir.resolve(), original_view)
print("PASS geometry, bond endpoints, stack order, packed type and in-place revisions")
