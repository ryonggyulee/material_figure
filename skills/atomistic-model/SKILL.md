---
name: atomistic-model
description: Build, source, or revise atomic structures for materials science with ASE or pymatgen and deliver a validated extxyz. Use for crystal phases, slabs, supercells, defects, and structures selected from C2DB or Materials Project.
---

# Atomic structure modeling

Deliver one ordered atomic configuration per `.extxyz`. Use the supplied structure when revising. For a new model, identify the phase, dimensionality and boundary conditions that matter to the request. Distinguish a relaxed database parent from an ideal construction or an unrelaxed derivative.

Choose the native modeling library for the work. Use ASE builders and `Atoms` operations for coordinate-based construction and edits, or work directly with pymatgen `Structure`, symmetry tools and slab transformations. Use the installed library's signatures and docstrings when choosing settings such as surface termination or supercell basis. [Modeling and export examples](references/modeling.md)

For C2DB or Materials Project, select a record matching the requested phase and dimensionality. Fetch the exact ID with `scripts/fetch.py`. Keep the originating entry and the transformations in the model history. [Database selection and commands](references/sources.md)

Export through `scripts/model.py` using `write_model`. It checks site order and species, Cartesian coordinates, cell, periodic axes, and history after reading the file back. Check the scientific claim separately, for example layer registry for a 1H monolayer or unchanged sites for a vacancy. Report the defining parameters, source and any relaxation assumptions. A requested figure can consume this same file through `materials-schematic`.
