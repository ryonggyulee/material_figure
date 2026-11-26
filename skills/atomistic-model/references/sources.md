# External starting structures

Use the source named in the request. For a formula-only request, inspect candidate records for the requested phase, polytype, thickness and symmetry. C2DB's entry pages report layer groups. Materials Project offers bulk polymorphs and different unit-cell representations. If the choice changes the scientific claim and the request leaves it open, identify the candidate you propose and the assumption it entails.

From the repository root, retrieve one selected public entry:

```bash
.model-env/bin/python skills/atomistic-model/scripts/fetch.py c2db 1MoS2-1 figure-output/mos2.extxyz
.model-env/bin/python skills/atomistic-model/scripts/fetch.py mp mp-149 figure-output/si.extxyz
```

C2DB supplies an extended XYZ from its entry page. This preserves the two in-plane periodic axes and the nonperiodic slab normal. The Materials Project public OPTIMADE endpoint provides lattice vectors, Cartesian coordinates, site occupancies and periodic axes by MP ID without an API key. For a specific calculation or relaxation functional, consult the MP task linked to the structure. Cite the database and the originating work and consult the source's reuse terms for redistribution. [C2DB](https://c2db.fysik.dtu.dk/) · [MP OPTIMADE provider](https://www.optimade.org/providers-dashboard/providers/mp.html) · [MP structure origins](https://docs.materialsproject.org/downloading-data/using-the-api/querying-data)

The resulting file records the entry ID, entry and download URLs, retrieval date and SHA-256 of the response under `model_history`. Continue from this file offline. Record operations such as layer extraction, a supercell matrix, strain or atom deletion when deriving the next structure. For a supplied database export, `model.py` records its local filename and hash. Include the original database ID in the recipe when known. C2DB lists CC BY-NC 4.0 on its database site. [C2DB license notice](https://c2db.fysik.dtu.dk/)
