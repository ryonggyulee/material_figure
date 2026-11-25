# Working in this repository

For new materials figures, follow [the creation skill](skills/materials-schematic/SKILL.md). For an existing blend, follow [the editing skill](skills/materials-schematic-edit/SKILL.md). Use it directly from this checkout even when the skill is not installed in the user's skill directory.

On this cluster, run ASE helpers with `.figure-env/bin/python` and use the existing `blender` on PATH for headless scene generation and rendering. Docker is optional. For a fresh checkout, run `./build.sh` from the repository root. See [README.md](README.md) for usage.

Write new figures and revisions to `figure-output/` by default. For an edit, start from the supplied blend with `host.py --input`. Use [the validation report](validation/RESULTS.md) for the geometry checks and viewport benchmarks when changing the rendering tools.
