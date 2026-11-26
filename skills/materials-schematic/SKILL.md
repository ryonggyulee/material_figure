---
name: materials-schematic
description: Create new editable native Blender figures of materials, atomistic structures, and semiconductor devices from descriptions, sketches, reference figures, or ASE-readable structure files. Supports mixed continuum and atomic scenes, studio renders, and shaded cartoons.
license: MIT
---

# Materials schematics

Deliver a native .blend and a camera render. New figures default to a transparent PNG 4500 pixels wide. Choose the aspect ratio for the composition and honor any requested dimensions. For a visible world background, use `--no-transparent`. Use the figure's scientific claim to choose the viewpoint, channel exposure, and labels. For sketches or references, inspect the image first. Identify layer order, contact placement, scale breaks, and which details are known. Record inferred dimensions and unrelaxed interfaces in the caption or scene notes.

**Geometry.** Read the supplied file with ASE. For a new structure, a database parent, or a defect model, use the companion [atomistic modeling skill](../atomistic-model/SKILL.md) when available, or build from the documented phase with ASE. Prepare the geometry once with `scripts/prepare.py`. Select the frame, finite repeat, and bond model deliberately. The transfer preserves site order, cell, PBC flags and any model history. Edges connect displayed sites only. Use pair cutoffs for materials where a covalent-radius guess would suggest misleading bonds.

**Composition.** Run `scripts/host.py` from the support environment. Pass the prepared geometry and a small figure-specific Blender Python script. Use native meshes for continuum parts, the provided palette and material styles, and editable labels. Group figure objects in the Blender collections `atomistic` (sites and bonds), `continuum` (device bodies and layers), `effect` (electron clouds, density or field depictions), and `label` (text and leaders). Leave an unused category empty. Cameras and lights stay at scene level. The agent chooses the composition. [Commands and composition API](references/workflow.md)

**Cartoon atoms.** Every newly generated element material defaults to 60% band strength and five softly separated tones. Each element keeps its ASE/Jmol color. The shared shader reads `cartoon.atom_bands` from the [project presets](assets/presets.json).

For an existing figure, use [materials-schematic-edit](../materials-schematic-edit/SKILL.md). If only this skill is installed, the [editing API and workflow](references/editing.md) is bundled with it.

**Review.** Render and inspect the actual image at its intended size. Trace each leader and interface, check the exposed lattice and coordination, and compare the result against the supplied geometry or sketch. Correct clipped labels, ambiguous layer contacts, and highlights that erase material boundaries. Report assumptions that affect interpretation.
