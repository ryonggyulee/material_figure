---
name: materials-schematic
description: Create new editable native Blender figures of materials, atomistic structures, and semiconductor devices from descriptions, sketches, reference figures, or ASE-readable structure files. Supports mixed continuum and atomic scenes, studio renders, and shaded cartoons.
license: MIT
---

# Materials schematics

Deliver a native .blend and a camera render. Export PNGs with a transparent background by default. For a visible world background, use `--no-transparent`. Use the figure's scientific claim to choose the viewpoint, channel exposure, and labels. For sketches or references, inspect the image first. Identify layer order, contact placement, scale breaks, and which details are known. Record inferred dimensions and unrelaxed interfaces in the caption or scene notes.

**Geometry.** Read the supplied file with ASE, or generate an ASE structure using its documented lattice and phase. Prepare it once with `scripts/prepare.py`. Select the frame, finite repeat, and bond model deliberately. The transfer preserves site order, cell, and PBC flags. Edges connect displayed sites only. Use pair cutoffs for materials where a covalent-radius guess would suggest misleading bonds.

**Composition.** Run `scripts/host.py` from the support environment. Pass the prepared geometry and a small figure-specific Blender Python script. Use native meshes for continuum parts, the provided palette and material styles, and editable labels. Group figure objects in the Blender collections `atomistic` (sites and bonds), `continuum` (device bodies and layers), `effect` (electron clouds, density or field depictions), and `label` (text and leaders). Leave an unused category empty. Cameras and lights stay at scene level. The agent chooses the composition. [Commands and composition API](references/workflow.md)

For an existing figure, use [materials-schematic-edit](../materials-schematic-edit/SKILL.md). If only this skill is installed, the [editing API and workflow](references/editing.md) is bundled with it.

**Review.** Render and inspect the actual image at its intended size. Trace each leader and interface, check the exposed lattice and coordination, and compare the result against the supplied geometry or sketch. Correct clipped labels, ambiguous layer contacts, and highlights that erase material boundaries. Report assumptions that affect interpretation.
