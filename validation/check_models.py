"""Run with .model-env/bin/python validation/check_models.py [--live] [--blender]."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from ase.build import make_supercell
from ase.io import read, write
import numpy as np
from pymatgen.core import Lattice, Structure

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/atomistic-model/scripts"
FIGURE = ROOT / "skills/materials-schematic/scripts"
DEMO = ROOT / "examples/mos2"
OUT = ROOT / "test/atomistic-model"
sys.path.insert(0, str(SCRIPTS))
from fetch import fetch, mp_structure
from model import check_geometry, write_model


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def check_channel():
    # Run the shipped builder in the ignored workspace and compare to the published file.
    recipe = OUT / "structure.py"
    shutil.copyfile(DEMO / recipe.name, recipe)
    run(sys.executable, recipe)
    original = read(OUT / "channel.extxyz")
    check_geometry(read(DEMO / "channel.extxyz"), original)
    assert len(original) == 216 and not any(original.pbc)
    top = np.flatnonzero((original.numbers == 16) & (original.positions[:, 2] > 1.5))
    site = top[np.argmin(np.linalg.norm(original.positions[top, :2], axis=1))]
    expected = original[np.arange(len(original)) != site]
    edited = original.copy()
    del edited[site]
    vacancy = OUT / "vacancy.extxyz"
    saved = write_model(edited, vacancy, source="Published finite 1H MoS2 channel",
                        operation=f"Delete top S site {site}, unrelaxed", expected=expected)
    assert saved.symbols.formula.count() == {"Mo": 72, "S": 143}
    before = vacancy.read_bytes()
    shifted = edited.copy()
    shifted.positions[0, 0] += 0.01
    with np.testing.assert_raises_regex(ValueError, "positions"):
        write_model(shifted, vacancy, source="test", expected=expected)
    assert vacancy.read_bytes() == before
    run(sys.executable, FIGURE / "prepare.py", vacancy, OUT / "vacancy.npz", "--bonds", "mos2")
    with np.load(OUT / "vacancy.npz") as data:
        np.testing.assert_array_equal(data["numbers"], expected.numbers)
        np.testing.assert_allclose(data["positions"], expected.positions, atol=1e-8, rtol=0)
        assert len(data["edges"]) == 393
        assert json.loads(str(data["metadata"]))["model_history"] == saved.info["model_history"]
    print(f"ASE vacancy at site {site}: Mo72S143, all surviving sites preserved", flush=True)


def check_pymatgen():
    model = Structure.from_spacegroup("Fd-3m", Lattice.cubic(5.431), ["Si"], [[0, 0, 0]])
    model.make_supercell([2, 1, 1])
    path = OUT / "diamond.extxyz"
    result = write_model(model, path, source='이상 결정 "Si", a=5.431 Å',
                         operation="2 × 1 × 1 supercell")
    assert result.get_chemical_symbols() == ["Si"] * 16 and all(result.pbc)
    np.testing.assert_allclose(result.cell, np.diag([10.862, 5.431, 5.431]), atol=1e-8)
    np.testing.assert_allclose(result.positions, model.cart_coords, atol=1e-8, rtol=0)
    model.to(filename=OUT / "diamond.cif")
    run(sys.executable, SCRIPTS / "model.py", OUT / "diamond.cif", OUT / "from-cif.extxyz",
        "--reader", "pymatgen")
    cif = read(OUT / "from-cif.extxyz")
    rebuilt = Structure.from_file(OUT / "diamond.cif")
    np.testing.assert_allclose(cif.positions, rebuilt.cart_coords, atol=1e-8, rtol=0)
    assert len(cif.info["model_history"][0]["source"]["sha256"]) == 64
    partial = Structure(Lattice.cubic(4), [{"Si": 0.5, "Ge": 0.5}], [[0, 0, 0]])
    with np.testing.assert_raises_regex(ValueError, "occupancy"):
        write_model(partial, path, source="test")
    partial.to(filename=OUT / "mixed.cif")
    with np.testing.assert_raises_regex(ValueError, "occupancy"):
        write_model(read(OUT / "mixed.cif"), path, source="test")
    frames = OUT / "frames.extxyz"
    frame = result.copy()
    frame.info.clear()
    write(frames, [frame, frame[:1]])
    cmd = [sys.executable, SCRIPTS / "model.py", frames, OUT / "frame.extxyz"]
    assert subprocess.run(cmd, capture_output=True).returncode != 0
    run(*cmd, "--index", "1")
    assert len(read(OUT / "frame.extxyz")) == 1
    print("Pymatgen native supercell, CIF readers, partial occupancy and frame selection passed")


def check_mp_species():
    attributes = dict(species=[dict(name="Si1", chemical_symbols=["Si"], concentration=[1.0])],
                      species_at_sites=["Si1"], nsites=1, structure_features=[],
                      lattice_vectors=np.diag([3, 4, 18]).tolist(), dimension_types=[1, 1, 0],
                      cartesian_site_positions=[[1, 2, 3]])
    structure = mp_structure({"attributes": attributes})
    saved = write_model(structure, OUT / "mixed-pbc.extxyz", source="Synthetic OPTIMADE test")
    assert saved.get_chemical_symbols() == ["Si"] and saved.pbc.tolist() == [True, True, False]
    attributes["species"][0]["concentration"] = [0.5]
    with np.testing.assert_raises_regex(ValueError, "occupancy"):
        mp_structure({"attributes": attributes})


def check_sources():
    sheet = fetch("c2db", "1MoS2-1", OUT / "c2db.extxyz")
    assert sheet.symbols.formula.count() == {"Mo": 1, "S": 2} and sheet.pbc.tolist() == [1, 1, 0]
    sulfurs = sheet.positions[sheet.numbers == 16]
    np.testing.assert_allclose(sulfurs[0, :2], sulfurs[1, :2], atol=1e-6)
    assert np.ptp(sulfurs[:, 2]) > 3
    supercell = make_supercell(sheet, np.diag([2, 2, 1]))
    derived = write_model(supercell, OUT / "c2db-supercell.extxyz", parent=sheet,
                          operation="2 × 2 × 1 periodic supercell")
    assert len(derived) == 12 and len(derived.info["model_history"]) == 2
    silicon = fetch("mp", "mp-149", OUT / "mp.extxyz")
    assert silicon.get_chemical_symbols() == ["Si", "Si"] and all(silicon.pbc)
    for model, uid in [(derived, "1MoS2-1"), (silicon, "mp-149")]:
        source = model.info["model_history"][0]["source"]
        assert source["id"] == uid and len(source["sha256"]) == 64
    print("Live C2DB and MP entries and inherited provenance passed")


def check_blender():
    inspect = OUT / "inspect_blend.py"
    inspect.write_text('''import bpy, json, numpy as np, sys
style, npz, original = sys.argv[-3:]
def layout():
    return (bpy.context.scene.camera.name,
            {o.name: (o.type, tuple(v for row in o.matrix_world for v in row))
             for o in bpy.context.scene.objects})
with np.load(npz) as d:
    atom, = [o for o in bpy.data.objects if "structure_metadata" in o]
    xyz = np.array([v.co[:] for v in atom.data.vertices])
    numbers = [n.value for n in atom.data.attributes["atomic_number"].data]
    np.testing.assert_allclose(xyz, d["positions"], atol=1e-6, rtol=0)
    np.testing.assert_array_equal(numbers, d["numbers"])
    np.testing.assert_array_equal([e.vertices[:] for e in atom.data.edges], d["edges"])
    assert json.loads(atom["structure_metadata"])["model_history"] == json.loads(str(d["metadata"]))["model_history"]
    assert bpy.context.scene["materials_style"] == style
edited_layout = layout()
bpy.ops.wm.open_mainfile(filepath=original)
assert layout() == edited_layout
''')
    for style in ("studio", "cartoon"):
        blend = OUT / f"{style}.blend"
        run(sys.executable, FIGURE / "host.py", "--input", DEMO / f"{style}.blend",
            "--replace", "Channel · 1H molybdenum disulfide", "--geometry", OUT / "vacancy.npz",
            "--output", blend, "--render", blend.with_suffix(".png"), "--preview", "--threads", "2")
        run("blender", "-b", blend, "--threads", "2", "--python-exit-code", "1", "-P", inspect,
            "--", style, OUT / "vacancy.npz", DEMO / f"{style}.blend")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--blender", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    check_channel()
    check_pymatgen()
    check_mp_species()
    if args.live:
        check_sources()
    if args.blender:
        check_blender()
    print("Model checks passed")
