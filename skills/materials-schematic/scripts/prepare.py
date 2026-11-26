"""Convert one ASE image into a pickle-free Blender transfer file (angstrom)."""
import argparse
import json
from pathlib import Path

import ase
import numpy as np
from ase.data import chemical_symbols, covalent_radii
from ase.data.colors import jmol_colors
from ase.io import read
from ase.neighborlist import natural_cutoffs, neighbor_list

ASSETS = json.loads((Path(__file__).resolve().parents[1] / "assets/presets.json").read_text())


def pack(atoms, destination, rule="natural", source="ASE Atoms"):
    positions = atoms.get_positions()
    if not len(atoms) or not np.isfinite(positions).all():
        raise ValueError("A nonempty structure with finite coordinates is required")
    if rule == "none":
        edges = np.empty((0, 2), dtype=np.int32)
    else:
        # Draw the displayed fragment only. Re-box a copy so open-boundary
        # neighbor bins also work for translated molecules and triclinic cells.
        fragment = atoms.copy()
        fragment.set_pbc(False)
        fragment.set_cell(np.ptp(positions, axis=0) + 4)
        fragment.positions[:] = positions - positions.min(axis=0) + 2
        if rule == "natural":
            cutoff = natural_cutoffs(fragment, mult=ASSETS["bonds"]["covalent_multiplier"])
        else:
            pairs = ASSETS["bonds"]["presets"][rule] if isinstance(rule, str) else rule
            cutoff = {tuple(pair.split("-")): distance for pair, distance in pairs.items()}
            if any(len(pair) != 2 or not set(pair) <= set(chemical_symbols) or
                   not np.isfinite(d) or d <= 0 for pair, d in cutoff.items()):
                raise ValueError("Pair cutoffs must specify two elements and a positive distance")
        i, j = neighbor_list("ij", fragment, cutoff)
        edges = np.column_stack((i[i < j], j[i < j])).astype(np.int32)
        edges = edges[np.lexsort((edges[:, 1], edges[:, 0]))]
    palette = {}
    for number in np.unique(atoms.numbers):
        style = ASSETS["elements"]
        color = jmol_colors[number].tolist() if number < len(jmol_colors) else style["fallback_srgb"]
        palette[int(number)] = dict(symbol=chemical_symbols[number], srgb=color,
                                    radius=float(covalent_radii[number]) * style["display_fraction"])
    metadata = dict(source=source, units="angstrom", ase=ase.__version__, rule=rule, palette=palette,
                    cutoffs=ASSETS["bonds"], boundary="displayed pairs only")
    if "model_history" in atoms.info:
        metadata["model_history"] = atoms.info["model_history"]
    with Path(destination).open("wb") as stream:
        np.savez_compressed(stream, positions=positions, numbers=atoms.numbers.astype(np.int32),
                            edges=edges, cell=atoms.cell.array, pbc=atoms.pbc, metadata=json.dumps(metadata))
    print(f"{len(atoms)} sites, {len(edges)} displayed bonds -> {destination}")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source")
    cli.add_argument("output")
    cli.add_argument("--index", type=int, default=-1, help="ASE frame index (default last)")
    cli.add_argument("--repeat", nargs=3, type=int, default=(1, 1, 1))
    rules = cli.add_mutually_exclusive_group()
    rules.add_argument("--bonds", choices=["natural", "none", *ASSETS["bonds"]["presets"]], default="natural")
    rules.add_argument("--pairs", help='Pair cutoff map in angstrom, e.g. \'{"Si-O": 1.9}\'')
    args = cli.parse_args()
    atoms = read(args.source, index=args.index)
    if min(args.repeat) < 1:
        cli.error("repeat counts must be positive")
    if tuple(args.repeat) != (1, 1, 1):
        atoms = atoms.repeat(args.repeat)
    pack(atoms, args.output, json.loads(args.pairs) if args.pairs else args.bonds,
         f"{Path(args.source).name}, frame {args.index}, repeat {tuple(args.repeat)}")
