# Validation on the Linux cluster

The shipped scenes and PNGs were produced by the cluster's existing Linux Blender 3.1.2. Cycles enumerated an Intel Xeon Silver 4210R CPU. A second headless run explicitly unset DISPLAY, WAYLAND_DISPLAY and BLENDER_EXE, found Blender on PATH and rendered both styles. The GUI benchmark used a separate private Xvnc display with Mesa 22.0.3 llvmpipe. Generation and PNG rendering did not use that display. Windows/WSL interop, newer Blender versions and GPU performance remain untested.

## Scientific and visual checks

- The ASE recipe makes a finite rectangular 1H monolayer from the trigonal-prismatic basis with a = 3.18 Å and outer-plane spacing 3.19 Å. There are 72 Mo and 144 S sites. The upper and lower S planes have corresponding in-plane positions.
- Using a 2.65 Å Mo–S cutoff gives 396 displayed bonds at 2.43204 Å. Fifty-five interior Mo sites have six S neighbors. Edge sites have reduced coordination. The Blender source mesh agrees with the NPZ coordinates to single precision, with identical element IDs, edge indices, cell and boundary flags. Both styles evaluate 216 sphere instances and 396 cylinders. The cylinder endpoints coincide with atomic sites.
- The two Au contacts overlap opposite ends of the channel. Beneath it, the oxide and doped-Si solids meet at a common plane. Their dimensions, doping and interface separations illustrate the device concept. The example represents an ideal, unrelaxed layer. [ASE construction](../examples/mos2/structure.py)
- Both 1800 × 1240 renders were inspected at reduced and full output resolution during development. The initial drain had a clipped white highlight and the source and back-gate labels crossed the solids. Lower softbox energies, increased metal roughness, a shallower camera angle and more space above and below the stack improved legibility. The final cartoon uses 12 samples to smooth its stepped-color edges. Both final images show the two contacts, exposed lattice and oxide/gate boundary. [Studio](../examples/mos2/studio.png) · [Cartoon](../examples/mos2/cartoon.png)

## Same-device reproduction and local revision

Using Blender 3.1.2 on the cluster, we converted the original `channel.extxyz` with the Mo–S cutoff, ran the composition script and rendered the studio and cartoon views at 1800 × 1240 with `--no-transparent`. Every RGB pixel matched the corresponding shipped PNG in both styles. We then applied the refinement to the saved device. Both refined styles export RGBA with alpha values spanning 0–255. [Original studio](../examples/mos2/studio.png) · [Side-by-side comparison on white](../figure-output/mos2-revision/compare.png) · [Refined cartoon](../figure-output/mos2-revision/cartoon.png)

The refined renders identify Mo and S on visible sites and show the lattice under the drain. The drain label explicitly identifies the transparency as an illustration. A shorter leader crosses less of the back-gate face. The studio uses 96 samples for the transparent interfaces. The scientific checks above pass on both reopened blends. The camera transform and orthographic scale, light transforms, colors and energies match the original. The scene grows from 19 to 22 objects through the annotation changes. Both versions still use one atomic mesh. [Figure-specific patch](../examples/mos2/refine.py) · [Editable studio](../figure-output/mos2-revision/studio.blend) · [Editable cartoon](../figure-output/mos2-revision/cartoon.blend)

| CPU, automatic threads, full size | Build or patch and save | Render including PNG | Peak RSS rendering the saved blend¹ |
| --- | ---: | ---: | ---: |
| Reproduced studio, 32 samples | 0.270 s | 9.53 s | 1760 MiB |
| Refined studio, 96 samples | 0.020 s | 24.69 s | 1762 MiB |
| Refined cartoon, 12 samples | 0.011 s | 1.38 s | 477 MiB |

¹ RSS was measured with GNU time in separate headless renders of the saved blends. A paired solid-viewport test using the same private Xvnc/llvmpipe display and orbit script gave median redraws of 113 ms original and 120 ms refined, 95th percentiles of 116 and 136 ms, and GUI peak RSS of 532 MiB for each. These are single runs on a shared CPU host. The orbit hides callouts and measures local redraw.

The editing regression starts from the shipped blend and adds linked copies to expose accidental changes to shared data. It recolors S on one sheet, changes opacity and roughness on one gold contact, moves and renames its label, replaces the selected scientific mesh with a 215-site test structure containing Se, and switches the result to cartoon. Each step opens its predecessor. The unselected sheet and pad retain their bindings. The local material, edited label and contact opacity survive subsequent steps. An unresolved target fails before saving. A second test on both refined blends moves the drain by 2 Å and verifies that the projected leader tip follows while its text stays fixed. [Successive edit test](check_edits.py) · [Scientific and callout checks](check_scene.py)

## Timing and memory

Single runs on a shared host. The four-thread run exercised the launcher with SLURM_CPUS_PER_TASK set to 4. It was launched directly on this node. The studio proof and cartoon checks overlapped in time. Build/save is timed inside Blender after file opening, including the compressed save. Render includes PNG writing. Wall time includes launching Python and Blender. Peak RSS is GNU time's process maximum in MiB.

| Four-thread headless operation | Output | Build/save | Render | Wall | Peak RSS |
| --- | --- | ---: | ---: | ---: | ---: |
| Build device, studio / 32 samples | 1800 × 1240 | 0.272 s | 41.67 s | 43.42 s | 1766 MiB |
| Open saved device, switch to cartoon / 12 samples | 1800 × 1240 | 0.009 s | 4.09 s | 5.78 s | 476 MiB |
| Open studio, render proof / 8 samples | 900 × 620 | 0.009 s | 4.65 s | 6.30 s | 682 MiB |

The proof blend reopened at 1800 × 1240, 100% scale and 32 samples. With Blender's automatic thread count, the shipped studio and cartoon renders took 9.29 s and 1.20 s respectively. The compressed scene files are 296 KiB and 294 KiB.

## Editing and scale

The scene has 19 objects and a single editable site/edge mesh for the channel. A test captured Blender datablock pointers for objects, meshes, materials and node groups, then switched the style and applied the gate-text patch. Every pointer survived. The patched scene was saved, reopened, rendered and compared with the original. The changed pixels were confined to the gate label, within x = 1078–1438 and y = 1129–1174 (top-left origin). Patch/save took 0.012 s; launching Blender, applying the patch, rendering and writing the PNG took 2.68 s. [Revision script](../examples/mos2/revise.py)

A separate silicon CIF exercise produced 32 sites and 37 bonds. Both renders succeeded. Moving one Si site by 0.07 Å in the saved blend preserved the other 31 positions, all 37 edges, the five scene objects and the node group.

Repeating the MoS₂ fragment 12 × 12 × 1 produced 31,104 sites and 61,776 displayed bonds. ASE conversion took 1.47 s wall and 252 MiB peak RSS. The native scene built and saved in 0.140 s inside Blender, 1.60 s including launch, with 329 MiB peak RSS and a 303 KiB blend. This benchmark used the atomistic sheet and default camera/lighting.

| Solid viewport orbit on llvmpipe | Median redraw | 95th percentile | GUI peak RSS |
| --- | ---: | ---: | ---: |
| 216 sites, complete transistor | 112 ms | 116 ms | 569 MiB |
| 31,104 sites, full ball-and-stick display | 1858 ms | 1928 ms | 652 MiB |
| Same large mesh, modifier disabled for viewport, wire display | 99 ms | 100 ms | 605 MiB |

These are GUI measurements in a 991 × 641 3D area. The benchmark rotates the view by 2° per redraw, warms up for three frames, then measures 24 window redraws and swaps. It hides the camera-plane annotations while orbiting. The large full-detail view is slow on software OpenGL. The measured wire mode makes site selection practical while retaining full render geometry. User-input latency over a remote desktop connection was not measured.

## Reproduce the checks

Use the README recipe, then run the geometry and revision checks against the delivered files and the new revision.

```bash
blender -b --python-exit-code 1 -P validation/check_scene.py -- figure-output/revised.blend
blender -b --python-exit-code 1 -P validation/check_scene.py -- --refined-dir figure-output/mos2-revision
.figure-env/bin/python validation/check_edits.py
python "$SKILL/scripts/prepare.py" examples/mos2/channel.extxyz figure-output/large.npz --repeat 12 12 1 --bonds mos2
python "$SKILL/scripts/host.py" --geometry figure-output/large.npz --output figure-output/large.blend
```

On a graphical display, run the timed orbit. Supply a saved scene as the input. The benchmark exits its Blender window when finished.

```bash
blender --factory-startup -p 0 0 1200 740 examples/mos2/studio.blend -P validation/viewport.py
blender --factory-startup -p 0 0 1200 740 figure-output/large.blend -P validation/viewport.py -- --wire
```

The Codex skill frontmatter validator passed. The Miniforge prefix used ASE 3.26.0 and Python 3.12 with a 99-package explicit conda-forge lock. The supporting-tools image was built with rootless Podman and run with networking disabled. Its transfer file matched the native NPZ byte-for-byte (SHA-256 `6211ed55129500b7bc532764272541f7590b6b874852358bb6fa8075c3c9290e`). This host used isolated overlay storage with single-UID extraction for Podman.
