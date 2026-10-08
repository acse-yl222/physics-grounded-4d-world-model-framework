"""Read frozen benchmark assets for exact manifest bounds and provenance."""
from pathlib import Path
from datetime import datetime, timezone
import bpy, json, hashlib

R = Path(__file__).resolve().parent / 'input/canary_wharf_20261007'
results = {}
for key in ('hsbc', 'citi', 'quay1'):
    folder = R / 'exports' / ('benchmark_batch001_' + key)
    native, glb = folder / (key + '.blend'), folder / (key + '.glb')
    audit = json.loads((R / 'exports' / ('benchmark_batch001_' + key + '_independent') / 'checks.json').read_text())
    native_hash = hashlib.sha256(native.read_bytes()).hexdigest()
    assert native_hash == audit['native_sha256']
    bpy.ops.wm.open_mainfile(filepath=str(native))
    vertices, ids, names = [], set(), []
    triangles = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        names.append(obj.name)
        ids.add(obj.get('building_id'))
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    assert len(ids) == 1 and None not in ids
    results[key] = {
        'native_sha256': native_hash, 'glb_sha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
        'owner_ids': sorted(ids), 'mesh_count': len(names), 'triangles': triangles,
        'bounds_m': {'min': [min(v[i] for v in vertices) for i in range(3)],
                     'max': [max(v[i] for v in vertices) for i in range(3)]},
    }
(R / 'references/building_timing_batch001/frozen_assets.json').write_text(json.dumps({
    'inspected_utc': datetime.now(timezone.utc).isoformat(), 'assets': results,
}, indent=2) + '\n')
print('BATCH_FROZEN_ASSETS', results)
