# Local edits to a saved blend

Use the same support environment and Blender launcher as the creation skill. For a source checkout set `SKILL="$PWD/skills/materials-schematic"` and `PY="$PWD/.figure-env/bin/python"`. For a user installation set SKILL to the installed materials-schematic directory and use the environment's Python. Install the two skills as siblings.

```bash
"$PY" "$SKILL/scripts/host.py" --input v1.blend --script patch.py --output v2.blend --render v2.png
```

Patch examples below are independent. Names match the shipped MoS₂ scenes. Newly composed devices also support stable figure_id values such as `drain` and `channel`. Object keys are exact and must resolve uniquely in the active scene. In Blender's console, `[(o.name, o.get("figure_id")) for o in bpy.context.scene.objects]` lists the choices.

```python
from edits import surface, label, target

surface("Channel · 1H molybdenum disulfide", element="Mo", color="#488291")
surface("Drain · Au", roughness=0.45, opacity=0.35)
label("Doped Si back gate", text="n⁺ Si back gate", offset=(0.5, 0))
```

Opacity is a surface shader mix from 0 (clear) to 1 (opaque) in Cycles. A closed solid has multiple interfaces. This artistic visibility parameter is distinct from optical absorption and from PNG background alpha. Color and opacity work in the studio and cartoon shaders; roughness affects studio shading. Species colors apply to a single atomic object. For continuum geometry, the default is material slot 0; specify `slot=` for another slot. For several parts, explicitly loop over the requested objects. A linked node group or shared material is isolated on first local edit. Repeated edits reuse the local material. The color helper supports the packaged studio/cartoon shader layout; inspect custom or textured graphs before editing them.

A label offset is in camera-plane scene units. The packaged callout keeps the device endpoint fixed while moving the label-side portion of its leader. New callouts store a link to their leader; older scenes use the original matching object names. If an older leader was renamed, set `text_obj["figure_leader"] = leader_obj` before moving the label. For viewport-only or render-only collection visibility use Blender's native collection toggles. For example, `category_collection("label").hide_render = True` after importing `category_collection` from `scene_tools`.

For object movement, edit its native transform. New MoS₂ callouts remember an object-local anchor via `callout(..., follow=part)`. After moving a part, call `refresh_leaders(part)` from `edits` to update its leader tips while retaining text positions. This is an explicit reprojection step suitable for a saved revision. Older callouts without bindings keep their camera-plane geometry. When the lattice itself changes, verify that a site annotation still points at the intended atom.

## Replace a structure

Prepare the new ASE geometry with its own bond model. Select the target by its figure_id or its exact object name on older scenes.

```bash
"$PY" "$SKILL/scripts/host.py" --input v2.blend --geometry replacement.npz \
  --replace 'Channel · 1H molybdenum disulfide' --output v3.blend --render v3.png
```

This replaces the selected object's scientific mesh and cell metadata. Its transform, collection, other modifiers and display branches survive; newly encountered species get new branches. Old species branches may remain dormant for reuse. Mesh-local custom attributes, shapekeys and assignments indexed by site belong to the outgoing geometry. For a site displacement that retains topology, edit the vertex and update the existing mesh instead of replacing it. Review scientific labels and leaders after a real change of species, extent or interface geometry.

Each invocation starts from the specified input. Use v2 as the input for the next edit to retain v2's changes. A failed patch stops before saving. A patch is ordinary trusted Blender Python, so its own explicit global operations can affect the full scene. For a local edit leave off the global style switch. Default transparent PNG export happens after saving the revised blend; supply an explicit background flag to edit the saved film setting too.
