# Building and editing a figure

In a source checkout, run `./build.sh` at the repository root and use `.figure-env/bin/python` for the Python commands below. Set `SKILL` to the materials-schematic skill directory. For a standalone skill installation on x86-64 Linux or WSL2, create and activate the locked environment with Miniforge:

```bash
conda create -y -n materials-schematic --file "$SKILL/environment/linux-64.lock"
conda activate materials-schematic
```

The explicit lock contains conda-forge package URLs and hashes. The portable solver input is `environment/environment.yml`. Blender uses its own Python and NumPy. The launcher uses `BLENDER_EXE` when set, then `blender` on PATH. On a cluster, load the local Blender module if needed. Generation and Cycles rendering run headless. The launcher passes the Slurm task's CPU count to Blender when available. Use `--threads N` for an explicit budget. Cycles checks for a supported GPU and falls back to CPU. Set `SCHEMATIC_3D_DEVICE=cpu` to force CPU rendering.

On WSL without a native Blender on PATH, the launcher searches the standard Blender Foundation directories on C:. To select a particular Windows installation, set `BLENDER_EXE` to its mounted executable path. The launcher translates paths with `wslpath -w`. Use a Windows-mounted work directory if the host restricts WSL UNC access.

```bash
python "$SKILL/scripts/prepare.py" input.cif atoms.npz --repeat 3 3 1 --pairs '{"Mo-S":2.65}'
python "$SKILL/scripts/host.py" --geometry atoms.npz --output crystal.blend --render crystal.png
python "$SKILL/scripts/host.py" --input crystal.blend --style cartoon --output cartoon.blend --render cartoon.png
```

New figures use the width in `output.width_px` (4500 px). The default 5:3 canvas is 4500 × 2700. To frame a different aspect ratio at the same print resolution, import `output_pixels` from `scene_tools` and pass e.g. `pixels=output_pixels((16, 9))` to `setup`. Pass `pixels=(width, height)` for an exact size. An existing blend keeps its saved resolution on edits and style switches. Add `--preview` to render at half size and a quarter of the samples. The saved blend retains the full settings. Use `--open` in a graphical session to open the result interactively.

New scenes and PNG exports use a transparent world background by default. Set `--no-transparent` for the scene's visible world background (white in the supplied studio setup). For existing blends the automatic PNG export preference applies only to the PNG. An explicit background flag also saves that setting in the output blend. A scene-only revision preserves the input blend's settings unless a background option is supplied. The project default is `output.transparent` in [presets.json](../assets/presets.json).

Run `prepare.py --help` for frame, bond, and repeat options. Use `--bonds none` to omit sticks, or `--bonds mos2` for the supplied Mo–S pair rule. The input file or ASE recipe remains the scientific source. The NPZ carries positions in ångströms, atomic numbers, edge indices, cell rows, PBC flags and the resolved palette. Electronic results, constraints, occupancies and custom arrays require separate treatment. Expand a periodic structure to the visible fragment before packing it. Mixed-occupancy CIFs need an explicit representation decision.

## Composition script

Pass `--script figure.py` alongside `--geometry`. The script executes in Blender with `structure` set to the imported object. Its local mesh has one vertex per source site and one edge per displayed bond. The integer point attribute `atomic_number` identifies species. Each Blender unit represents one ångström in these local coordinates. Each distinct species has an instanced sphere, and the bond display derives its length and orientation from the live edges.

```python
from appearance import swatch
from scene_tools import setup, slab
from labels import callout

# Example dimensions assume a centered channel with its bottom near z = -2.
camera = setup((0, 0, -2), width=56)
slab("Gate oxide", (42, 18, 3), (0, 0, -3.5), swatch("oxide"))
callout(camera, "Gate oxide", (-6, -9, -3.5), (-12, -12), above=False)
```

The Outliner has four figure collections. The atomic importer fills `atomistic`, `slab` fills `continuum`, and `callout` fills `label`. For custom geometry, use `from scene_tools import categorize`, then e.g. `categorize(cloud, "effect")` on an electron-cloud object. This only changes collection membership. In an older blend, categorize existing objects directly when organizing it; older callouts may appear under `Callouts`.

Use `material(name, srgb, metallic=..., roughness=...)` from `appearance` for additional materials. All new atomic species share the editable `Atom cartoon shading` node group. In [presets.json](../assets/presets.json), `cartoon.atom_bands.strength` sets the mix with smooth light. Each pair in `transitions` specifies a light threshold and the tone above it. Four transitions produce five tones. `edge_half_width` softens either side of each boundary. Each species maps the result through its own color ramp. Existing materials retain their saved shaders during revisions. Bonds and device bodies use their own stepped shading; studio uses its own shader.

`callout` takes a world-space anchor and a camera-plane text position in scene units. Its leader is projected for the chosen view. Reposition leaders after moving anchors or changing camera direction. The font is packed in the blend.

## Revising a saved scene

```bash
python "$SKILL/scripts/host.py" --input crystal.blend --script edit.py --output revised.blend --render revised.png
```

See [local edits](editing.md) for object and species edits and channel replacement. A revision script receives `structure=None` unless new geometry was explicitly supplied. Find an existing channel by its object name or its `structure_metadata` property. For an atom displacement, change the corresponding `obj.data.vertices[i].co`, then call `obj.data.update()`. Connected sticks follow their endpoints. For changes that alter neighbors, recompute the affected structure's connectivity with ASE. Keep unrelated objects and node groups. Enable overlays in the viewport to select vertices in Edit Mode. Hide the label collection while orbiting. For a lightweight site/edge view, disable the Atoms and bonds modifier's monitor icon and choose Wire under Object Properties → Viewport Display → Display As. The modifier's camera icon controls full render detail independently.

Keep trusted composition and patch scripts outside the blend for reproducibility. A saved scene renders and opens interactively without the skill, ASE, or an add-on.
