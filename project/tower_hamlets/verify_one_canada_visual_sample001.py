"""Independent saved-native/GLB comparison for the timed single-building sample."""
from pathlib import Path
import bpy
import json
import hashlib
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent / 'input/canary_wharf_20261007/exports/one_canada_visual_sample001'
expected = json.loads((OUT / 'native_snapshot.json').read_text())
assembly = json.loads((OUT / 'assembly.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OUT / 'canada.blend') == assembly['native_sha256']
assert sha(OUT / 'canada.glb') == assembly['glb_sha256']

def inspect():
    result = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
        assert vertices, obj.name
        result[obj.name] = {
            'triangles': len(obj.data.loop_triangles),
            'bounds': [[min(v[i] for v in vertices) for i in range(3)],
                       [max(v[i] for v in vertices) for i in range(3)]],
            'building_id': obj.get('building_id'),
            'research_object_id': obj.get('research_object_id'),
            'used_materials': sorted({obj.data.materials[p.material_index].name
                                     for p in obj.data.polygons if obj.data.materials}),
        }
    return result

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'canada.blend'))
native = inspect()
assert native == expected, 'Saved native differs from export snapshot'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT / 'canada.glb'))
imported = inspect()
assert set(imported) == set(expected), 'Mesh names or count differ'
errors = []
max_bound_error = 0.0
for name, wanted in expected.items():
    actual = imported[name]
    for field in ('triangles', 'building_id', 'research_object_id', 'used_materials'):
        if actual[field] != wanted[field]:
            errors.append({'mesh': name, 'field': field,
                           'expected': wanted[field], 'actual': actual[field]})
    error = max(abs(x-y) for row, other in zip(actual['bounds'], wanted['bounds'])
                for x, y in zip(row, other))
    max_bound_error = max(max_bound_error, error)
    if error > .0001:
        errors.append({'mesh': name, 'bounds_error_m': error})
(OUT / 'roundtrip_differences.json').write_text(json.dumps(errors, indent=2) + '\n')
assert not errors, errors[:3]
(OUT / 'verification.json').write_text(json.dumps({
    'native_reopened': True, 'independent_glb_verified': True,
    'native_sha256': assembly['native_sha256'],
    'glb_sha256': assembly['glb_sha256'], 'mesh_count': len(expected),
    'triangles': sum(x['triangles'] for x in expected.values()),
    'max_bounds_error_m': max_bound_error,
    'completed_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Saved native and GLB per-object identity/material/geometry bounds; not geographic verification',
}, indent=2) + '\n')
print('VISUAL_SAMPLE_ROUNDTRIP_PASS', len(expected), max_bound_error)
