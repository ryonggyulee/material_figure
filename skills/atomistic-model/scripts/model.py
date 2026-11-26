"""Export one ordered atomic model as a checked, single-frame extended XYZ."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from ase import Atoms
from ase.data import chemical_symbols
from ase.io import read, write
import numpy as np


def as_atoms(model):
    """Keep native modeling independent. Adapt a pymatgen model only at export."""
    if isinstance(model, Atoms):
        for species in model.info.get("occupancy", {}).values():
            if len(species) != 1 or next(iter(species.values())) != 1:
                raise ValueError("Resolve partial occupancy into an explicit atomic configuration first")
        return model

    from pymatgen.io.ase import AseAtomsAdaptor

    if not model.is_ordered:
        raise ValueError("Resolve partial occupancy into an explicit atomic configuration first")
    return AseAtomsAdaptor.get_atoms(model, msonable=False)


def check_geometry(expected, actual):
    """Compare ordered sites in Cartesian Å (ASE extxyz prints eight decimals)."""
    for field in ("numbers", "pbc"):
        if not np.array_equal(getattr(expected, field), getattr(actual, field)):
            raise ValueError(f"{field} differs from the expected structure")
    for field in ("cell", "positions"):
        left, right = np.asarray(getattr(expected, field)), np.asarray(getattr(actual, field))
        if left.shape != right.shape or not np.allclose(left, right, atol=1e-8, rtol=0):
            raise ValueError(f"{field} differs from the expected structure")


def write_model(model, destination, *, source=None, operation=None, parent=None, expected=None):
    """Publish after round-trip verification. expected may be an independent ASE site selection."""
    atoms = as_atoms(model).copy()
    if not len(atoms) or np.any((atoms.numbers < 1) | (atoms.numbers >= len(chemical_symbols))):
        raise ValueError("Expected at least one site, with a known element at every site")
    if not np.isfinite(atoms.positions).all() or not np.isfinite(atoms.cell).all():
        raise ValueError("Coordinates and cell vectors must be finite")
    periodic_vectors = atoms.cell[atoms.pbc]
    if len(periodic_vectors) and np.linalg.matrix_rank(periodic_vectors) != len(periodic_vectors):
        raise ValueError("Periodic axes require independent cell vectors")

    # Some constructors (e.g. ase.build.make_supercell) create a fresh object.
    origin = as_atoms(parent) if parent is not None else atoms
    history = list(origin.info.get("model_history", []))
    if not history and not source:
        raise ValueError("Identify the starting structure with source=")
    event = {}
    if source:
        event["source"] = source
    if operation:
        event["operation"] = operation
    if event:
        history.append(event)
    # ASE quotes double quotes in header strings. Escape JSON backslashes too,
    # so Unicode, quoted site labels and Windows paths survive its header parser.
    encoded = json.dumps(history, allow_nan=False).replace("\\", "\\\\")
    atoms.info["model_history"] = "_JSON " + encoded

    destination = Path(destination)
    if destination.suffix.lower() != ".extxyz":
        raise ValueError("Use an .extxyz destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".extxyz", delete=False) as temp:
        staging = Path(temp.name)
    try:
        write(staging, atoms, format="extxyz", write_results=False)
        saved = read(staging, format="extxyz")
        check_geometry(atoms, saved)
        if expected is not None:
            check_geometry(as_atoms(expected), saved)
        if saved.info.get("model_history") != history:
            raise ValueError("The exported structure lost its source or operation history")
        staging.replace(destination)
    finally:
        staging.unlink(missing_ok=True)
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reader", choices=("ase", "pymatgen"), default="ase")
    parser.add_argument("--index", type=int, help="ASE frame number, required for multi-frame inputs")
    args = parser.parse_args()
    with args.input.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    source = {"file": args.input.name, "sha256": digest}
    if args.reader == "pymatgen":
        from pymatgen.core import Structure

        if args.index is not None:
            parser.error("--index applies to the ASE reader")
        model = Structure.from_file(args.input)
    elif args.index is None:
        from ase.io import iread

        frames = iread(args.input, index=":")
        try:
            model = next(frames, None)
            if model is None or next(frames, None) is not None:
                parser.error("Expected one structure. For a trajectory select --index")
        finally:
            frames.close()
    else:
        model = read(args.input, index=args.index)
        source["frame"] = args.index
    saved = write_model(model, args.output, source=source)
    print(f"{saved.get_chemical_formula()} · {len(saved)} sites -> {args.output}")


if __name__ == "__main__":
    main()
