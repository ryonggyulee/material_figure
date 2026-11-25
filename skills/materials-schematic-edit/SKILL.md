---
name: materials-schematic-edit
description: Revise an existing editable materials-science Blender figure. Use for requests to change selected atoms, materials, device parts, labels, visibility or channel structure while retaining the approved composition.
license: MIT
---

# Edit a materials schematic

Start from the latest approved .blend. Use the companion materials-schematic skill's `scripts/host.py --input` and a separate output filename. Open the actual scene to identify the requested object, species or collection. Resolve ambiguous targets from context or ask when it changes the result.

Write a short patch using the [local editing API](../materials-schematic/references/editing.md). For new geometry replacing an existing channel, use `--replace`. Use native Blender Python for edits outside the helpers. A whole-scene style switch is appropriate when the requested scope is the whole figure.

Inspect the rendered change and the relevant neighbors. For a shared metal, check the other contact. For an atom color, check the other species and mesh. For a replacement, check counts, bonds and interface positions. Retain the editable version as the starting point for the next request. Mention any label or interface whose scientific meaning needs review.
