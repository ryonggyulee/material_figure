"""Build a rectangular, finite, stoichiometric 1H MoS2 channel."""
from pathlib import Path

import numpy as np
from ase.build import make_supercell, mx2
from ase.io import write

primitive = mx2("MoS2", kind="2H", a=3.18, thickness=3.19, vacuum=6)
rect = make_supercell(primitive, [[1, 0, 0], [1, 2, 0], [0, 0, 1]])
channel = rect.repeat((12, 3, 1))
channel.positions -= (channel.positions.max(0) + channel.positions.min(0)) / 2
channel.pbc = False
channel.info["description"] = "Finite ideal 1H MoS2 sheet. Coordinates in angstrom."
write(Path(__file__).with_name("channel.extxyz"), channel)
