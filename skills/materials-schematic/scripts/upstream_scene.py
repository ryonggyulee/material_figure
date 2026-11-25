"""Selected scene.py helpers from lgwrightlab/schematic-figure. See ../LICENSE."""
import os

import bpy
from mathutils import Vector


def hex_rgb(h, a=1.0):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (a,)


_GPU_BACKENDS = ('OPTIX', 'CUDA', 'METAL', 'HIP', 'ONEAPI')


def use_device(sc, mode=None):
    """Choose the Cycles device and print the choice. mode: 'auto' | 'gpu' | 'cpu'; None reads the environment
    variable SCHEMATIC_3D_DEVICE and falls back to 'auto'. auto and gpu try OptiX, CUDA, Metal, HIP and oneAPI in
    that order and use the first backend that lists a GPU. They fall back to the CPU when there is none, and gpu
    says so. Returns 'CPU' or the backend name."""
    mode = (mode or os.environ.get('SCHEMATIC_3D_DEVICE') or 'auto').strip().lower()
    if mode not in ('auto', 'gpu', 'cpu'):
        raise ValueError("SCHEMATIC_3D_DEVICE must be 'auto', 'gpu' or 'cpu', not %r" % mode)
    found, why = None, 'forced by SCHEMATIC_3D_DEVICE=cpu' if mode == 'cpu' else 'no GPU found'
    if mode != 'cpu':
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for kind in _GPU_BACKENDS:
                try: prefs.compute_device_type = kind
                except TypeError: continue   # this Blender build has no such backend
                (prefs.refresh_devices if hasattr(prefs, 'refresh_devices') else prefs.get_devices)()
                gpus = [d for d in prefs.devices if d.type == kind] or [d for d in prefs.devices if d.type != 'CPU']
                if gpus:
                    for d in prefs.devices: d.use = d in gpus   # the GPU only: a CPU in the mix slows it down
                    found = (kind, ', '.join(d.name for d in gpus)); break
        except Exception as e:   # no Cycles preferences in this build: render on the CPU
            why = 'GPU setup failed (%s)' % e
    if found:
        sc.cycles.device = 'GPU'
        print('schematic-3d: Cycles device = %s (%s)' % found)
        return found[0]
    sc.cycles.device = 'CPU'
    print('schematic-3d: Cycles device = CPU (%s)' % why)
    return 'CPU'


def camera_look(loc=(0, -9, 5), target=(0, 0, 0), lens_mm=50, ortho=None):
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.object; bpy.context.scene.camera = cam
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho: cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    else: cam.data.lens = lens_mm
    return cam
