# Working with the model

From this checkout, `./build.sh --modeling` creates `.model-env` on Linux x86-64 or WSL2. Use its Python for either library. A standalone installation can use the same lock with `conda create --prefix ./model-env --file <skill>/environment/linux-64.lock`. For local recipes add the skill's `scripts/` directory to the Python search path.

```bash
export PYTHONPATH="$PWD/skills/atomistic-model/scripts${PYTHONPATH:+:$PYTHONPATH}"
.model-env/bin/python my_structure_recipe.py
```

**ASE example.** This recipe selects the top-layer sulfur atom closest to the in-plane center of the published finite channel. The reference slice verifies the count, identity, order and coordinates of all surviving atoms before replacing the output.

```python
import numpy as np
from ase.io import read
from model import write_model

original = read("examples/mos2/channel.extxyz")
top = np.flatnonzero((original.numbers == 16) &
                     np.isclose(original.positions[:, 2], original.positions[:, 2].max()))
xy = original.positions[:, :2]
center = (xy.min(0) + xy.max(0)) / 2
site = top[np.argmin(np.linalg.norm(xy[top] - center, axis=1))]
edited = original.copy()
del edited[site]
write_model(edited, "figure-output/channel.extxyz",
            source="examples/mos2/channel.extxyz (ideal finite 1H channel)",
            operation=f"Remove top S at zero-based site {site}, unrelaxed",
            expected=original[np.arange(len(original)) != site])
```

**Pymatgen example.** Construct a conventional diamond cell by space group and replicate it in pymatgen. Pass the native object to the writer. ASE handles the extxyz serialization.

```python
from pymatgen.core import Lattice, Structure
from model import write_model

silicon = Structure.from_spacegroup("Fd-3m", Lattice.cubic(5.431), ["Si"], [[0, 0, 0]])
silicon.make_supercell([2, 1, 1])
write_model(silicon, "figure-output/si.extxyz",
            source="Ideal diamond Si, conventional cubic a=5.431 Å",
            operation="2 × 1 × 1 conventional supercell, unrelaxed")
```

For a surface, set the requested Miller index, termination, slab thickness, vacuum and periodicity explicitly. For a monolayer, verify coordination and registry of the two faces. A finite channel cutout and an in-plane periodic sheet can have identical coordinates and different boundary conditions. ASE and pymatgen both support supercells with integer transformation matrices. Check the resulting lattice orientation and site count. When a builder returns a fresh object, pass `parent=original` to inherit its history. [ASE builders](https://docs.ase-lib.org/ase/build/build.html) · [pymatgen core](https://pymatgen.org/pymatgen.core.html)

Convert a local file with `python scripts/model.py input.cif output.extxyz --reader pymatgen` from the skill directory, or use the default ASE reader. Specify `--index N` for a trajectory. For a disordered structure choose and record an explicit site configuration before export. Retain the source file for crystallographic metadata, calculation results and constraints. The export verifies geometry and model history.
