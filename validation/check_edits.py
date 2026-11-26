"""Run with .figure-env/bin/python validation/check_edits.py on the Blender host."""
import hashlib
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from ase.io import read
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/materials-schematic/scripts"
DEMO = ROOT / "examples/mos2"
sys.path.insert(0, str(SCRIPTS))
from prepare import pack


def run(directory):
    original = DEMO / "studio.blend"
    digest = hashlib.sha256(original.read_bytes()).digest()
    current = original

    def step(name, code, *options):
        nonlocal current
        patch = directory / (name + ".py")
        patch.write_text(HEADER + code)
        out = directory / (name + ".blend")
        subprocess.run([sys.executable, str(SCRIPTS / "host.py"), "--input", str(current),
                        "--script", str(patch), "--output", str(out), "--threads", "2", *options],
                       check=True)
        current = out

    # Linked copies make accidental edits to shared meshes and node groups visible.
    step("color", '''
for obj, name in [(target(channel), "Untouched sheet"), (target(drain), "Untouched pad")]:
    duplicate = obj.copy()
    duplicate.name = name
    bpy.context.scene.collection.objects.link(duplicate)
    duplicate.hide_render = True
surface(channel, element="S", color="#9653ce")
assert atomic_modifier(target(channel)).node_group != atomic_modifier(target("Untouched sheet")).node_group
''')
    step("contact", '''
assert element(channel, "S") != element("Untouched sheet", "S")
assert tuple(element(channel, "S").diffuse_color)[:3] != tuple(element(channel, "Mo").diffuse_color)[:3]
surface(drain, opacity=0.35, roughness=0.41)
mat = target(drain).active_material
surface(drain, roughness=0.43)
assert target(drain).active_material == mat
assert target("Source · Au").active_material == target("Untouched pad").active_material != mat
''')
    preview = directory / "patch.png"
    step("callout", '''
obj = target("Au drain")
line = target("Leader · Au drain")
points = line.data.splines[0].points
before = [p.co.copy() for p in points]
label(obj, text="Au drain (section)", offset=(1, 0.5))
assert (before[0] - points[0].co).length == 0
assert all((points[i].co - before[i] - Vector((1,.5,0,0))).length < 1e-5 for i in (1,2))
''', "--render", str(preview), "--preview")
    with Image.open(preview) as im:
        assert im.mode == "RGBA" and im.getchannel("A").getextrema() == (0, 255)

    atoms = read(DEMO / "channel.extxyz")
    del atoms[-1]
    atoms[1].symbol = "Se"
    replacement = directory / "replacement.npz"
    pack(atoms, replacement, {"Mo-S": 2.65, "Mo-Se": 2.65}, "synthetic regression fixture")
    step("replace", '''
assert not bpy.context.scene.render.film_transparent  # PNG default was export-only
obj = target(channel)
assert len(obj.data.vertices) == 215 and len(target("Untouched sheet").data.vertices) == 216
assert obj.data.attributes["atomic_number"].data[1].value == 34
assert element(channel, "Se") and element(channel, "S").get("figure_local")
assert obj.matrix_world == target("Untouched sheet").matrix_world
assert "Se" not in [n.label for n in atomic_modifier(target("Untouched sheet")).node_group.nodes]
assert target("Au drain").data.body == "Au drain (section)"
assert sum("structure_metadata" in o for o in bpy.context.scene.objects) == 2
''', "--geometry", str(replacement), "--replace", "Channel · 1H molybdenum disulfide", "--style", "cartoon")
    step("verify", '''
mat = target(drain).active_material
mix = mat.node_tree.nodes["Figure opacity"]
assert abs(mix.inputs[0].default_value - 0.35) < 1e-5
assert mix.inputs[2].links[0].from_node.name == "Cartoon"
assert mat.node_tree.get_output_node("ALL").inputs["Surface"].links[0].from_node == mix
assert abs(mat.node_tree.nodes["Studio"].inputs["Roughness"].default_value - 0.43) < 1e-5
assert target("Source · Au").active_material.node_tree.nodes.get("Figure opacity") is None
assert (Vector(element(channel, "S").diffuse_color) - Vector(hex_rgb("#9653ce"))).length < 1e-5
assert len(bpy.context.scene.objects) == 21
''')
    # Importing a new mesh into an older blend must use the current atom preset,
    # even for species that already have a legacy material with the same name.
    step("defaults", '''
shared = None
for symbol in ("Mo", "S", "Se"):
    mat = element(structure, symbol)
    ramp = mat.node_tree.nodes["Cartoon"].inputs["Color"].links[0].from_node
    group = ramp.inputs["Fac"].links[0].from_node.node_tree
    assert shared is None or group == shared
    shared = group
    assert abs(group.nodes["Band strength"].inputs[0].default_value - 0.60) < 1e-6
    steps, = [n.color_ramp for n in group.nodes if n.type == "VALTORGB"]
    assert len({stop.color[0] for stop in steps.elements}) == 5
assert element(structure, "Se") == element(channel, "Se")
assert element(structure, "Mo") != element("Untouched sheet", "Mo")
assert element("Untouched sheet", "Mo").node_tree.nodes["Cartoon"].inputs[0].links[0].from_node.color_ramp.interpolation == "CONSTANT"
''', "--geometry", str(replacement))
    bad = directory / "failed.blend"
    patch = directory / "missing.py"
    patch.write_text('from edits import surface\nsurface("Absent pad", opacity=0.2)\n')
    result = subprocess.run([sys.executable, str(SCRIPTS / "host.py"), "--input", str(current),
                             "--output", str(bad), "--script", str(patch)], capture_output=True)
    assert result.returncode and not bad.exists()
    assert hashlib.sha256(original.read_bytes()).digest() == digest


HEADER = '''import bpy
from mathutils import Vector
from edits import surface, label, target
from atoms import atomic_modifier
from upstream_scene import hex_rgb
channel = "Channel · 1H molybdenum disulfide"
drain = "Drain · Au"
def element(key, symbol):
    group = atomic_modifier(target(key)).node_group
    branch, = [n for n in group.nodes if n.type == "INSTANCE_ON_POINTS" and n.label == symbol]
    return branch.inputs["Instance"].links[0].from_node.inputs["Material"].default_value
'''

if __name__ == "__main__":
    work = ROOT / "test"
    work.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="edit-", dir=work) as tmp:
        run(Path(tmp))
    print("PASS successive edits, linked copies, species replacement, export alpha, missing target and atom defaults")
