# Working in this repository

For atomic geometry and `.extxyz` deliverables, use the [atomistic modeling skill](skills/atomistic-model/SKILL.md). Run `./build.sh --modeling` for its ASE and pymatgen environment. Use `.model-env/bin/python` for model recipes and database imports.

For new materials figures, follow [the creation skill](skills/materials-schematic/SKILL.md). For an existing blend, follow [the editing skill](skills/materials-schematic-edit/SKILL.md). Use it directly from this checkout even when the skill is not installed in the user's skill directory.

On this cluster, run ASE helpers with `.figure-env/bin/python` and use the existing `blender` on PATH for headless scene generation and rendering. Docker is optional. For a fresh checkout, run `./build.sh` from the repository root. See [README.md](README.md) for usage.

Write user figures and revisions to `figure-output/` by default. Use the Git-ignored `test/` workspace for visual experiments, reproduction runs, comparisons and benchmarks. Keep published examples in `examples/` and reusable checks in `validation/`. For an edit, start from the supplied blend with `host.py --input`. [Validation report](validation/RESULTS.md)

When a visual choice is approved as a project default, record its parameters in the [shared presets](skills/materials-schematic/assets/presets.json), make the normal creation path consume them, and state the scope in the creation skill. Figure-specific composition and overrides stay in the working scene.
