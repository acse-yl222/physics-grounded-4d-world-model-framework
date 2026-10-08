from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import bpy
from pathlib import Path

root = authoring_path()
out = root / "exports/nhm-polish-001"
bpy.ops.wm.read_factory_settings(use_empty=True)
source = root / "exports/central-preview-007/central_region.blend"
with bpy.data.libraries.load(str(source), link=True) as (a, b):
    b.objects = [
        n
        for n in a.objects
        if not n.startswith("Natural History Museum | Mapped masonry")
        and not n.startswith("Natural History Museum | Partitioned pitched")
    ]
for o in b.objects:
    if o is not None:
        bpy.context.scene.collection.objects.link(o)
with bpy.data.libraries.load(str(out / "natural_history.blend"), link=False) as (a, b):
    b.objects = a.objects
for o in b.objects:
    if o is not None:
        bpy.context.scene.collection.objects.link(o)
bpy.context.scene["delivery_note"] = (
    "Integrated native assembly: unchanged007 objects library-linked; polished NHM local/editable. Keep original007 source at its path."
)
bpy.ops.wm.save_as_mainfile(filepath=str(out / "central_region_linked.blend"), compress=False)
print("LINKED_MASTER_SAVED", flush=True)
