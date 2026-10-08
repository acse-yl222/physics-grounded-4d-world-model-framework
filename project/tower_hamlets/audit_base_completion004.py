"""Independent native acceptance for the bounded base-completion candidates.

Config supplies identities and physically meaningful clear vestibule ray domains;
the authoring script's pass/fail assertions are deliberately not reused.
"""
import bpy
import bmesh
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('assembly_helpers', Path(__file__).with_name('assemble_accelerated_repairs002.py'))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main(config_path):
    cfg = json.loads(config_path.read_text())
    source = ROOT / cfg['source']
    candidate = ROOT / cfg['candidate']
    assert sha(source) == cfg['source_sha256']
    assert sha(candidate) == cfg['candidate_sha256']
    bpy.ops.wm.open_mainfile(filepath=str(candidate))
    names = cfg['original_names']
    replacements = set(cfg['replace_names'])
    ids = ('building_id', 'research_object_id', 'aggregate_alias_id', 'source_owner_ids')
    records = {}
    for name in names:
        ob = bpy.data.objects[name]
        records[name] = {
            'fingerprint': helpers.fingerprint(ob),
            'identity': {k: helpers.plain(ob.get(k)) for k in ids},
            'upper_vertices': {tuple(v.co) for v in ob.data.vertices if v.co.z > cfg['preserve_above_z']},
        }
    solids = {}
    for name in cfg['add_names']:
        ob = bpy.data.objects[name]
        assert ob.get('building_id') in cfg['owners'], name
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        assert all(e.is_manifold for e in bm.edges), (name, 'open edge')
        remaining = set(bm.verts)
        volumes = []
        while remaining:
            todo = [remaining.pop()]
            component = set(todo)
            while todo:
                for e in todo.pop().link_edges:
                    for v in e.verts:
                        if v in remaining:
                            remaining.remove(v)
                            component.add(v)
                            todo.append(v)
            faces = {f for v in component for f in v.link_faces}
            volume = 0.0
            reference = next(iter(component)).co.copy()
            for f in faces:
                a = f.verts[0].co - reference
                for i in range(1, len(f.verts)-1):
                    volume += a.dot((f.verts[i].co-reference).cross(f.verts[i+1].co-reference))/6
            assert volume > 0, (name, 'nonpositive component', volume)
            volumes.append(volume)
        bm.free()
        solids[name] = {'components': len(volumes), 'min_signed_volume_m3': min(volumes)}
    ray_records = []
    for domain in cfg['clear_ray_domains']:
        center, tangent, normal = [Vector(domain[k]) for k in ('center', 'tangent', 'normal')]
        for x in domain['x']:
            for z in domain['z']:
                origin = center + tangent*x + normal*domain['start_depth'] + Vector((0, 0, z))
                hits = []
                for name in domain['obstacle_names']:
                    ob = bpy.data.objects[name]
                    inv = ob.matrix_world.inverted()
                    hit, point, _, _ = ob.ray_cast(inv @ origin, inv.to_3x3() @ -normal,
                                                   distance=domain['length'])
                    if hit:
                        hits.append({'name': name, 'point': list(ob.matrix_world @ point)})
                assert not hits, (domain['label'], x, z, hits)
                ray_records.append({'domain': domain['label'], 'x': x, 'z': z})
    visibility = []
    for probe in cfg.get('first_hit_probes', []):
        origin, direction = Vector(probe['origin']), Vector(probe['direction'])
        hits = []
        for name in probe['obstacle_names']:
            ob = bpy.data.objects[name]
            inv = ob.matrix_world.inverted()
            hit, point, _, _ = ob.ray_cast(inv @ origin, inv.to_3x3() @ direction,
                                           distance=probe['length'])
            if hit:
                hits.append(((ob.matrix_world @ point-origin).length, name))
        hits.sort()
        assert hits and hits[0][1] == probe['expected_name'], (probe['label'], hits[:3])
        assert abs(hits[0][0]-probe['expected_distance']) < .0001, (probe['label'], hits[0])
        visibility.append({'label': probe['label'], 'first_hit': hits[0]})
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(source), link=False) as (available, loaded):
        assert all(n in available.objects for n in names)
        loaded.objects = names
    for ob in loaded.objects:
        bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.update()
    unchanged = []
    upper = []
    for ob in loaded.objects:
        rec = records[ob.name]
        assert {k: helpers.plain(ob.get(k)) for k in ids} == rec['identity'], ob.name
        if ob.name not in replacements:
            assert helpers.fingerprint(ob) == rec['fingerprint'], (ob.name, 'changed outside contract')
            unchanged.append(ob.name)
        else:
            vv = {tuple(v.co) for v in ob.data.vertices if v.co.z > cfg['preserve_above_z']}
            assert vv == rec['upper_vertices'], (ob.name, 'upper vertices changed')
            upper.append(ob.name)
    assert sha(source) == cfg['source_sha256'] and sha(candidate) == cfg['candidate_sha256']
    report = {'source_sha256': cfg['source_sha256'], 'candidate_sha256': cfg['candidate_sha256'],
              'unchanged_objects_exact': unchanged, 'replacement_upper_vertex_sets_exact': upper,
              'preserve_above_z': cfg['preserve_above_z'], 'identity_fields_preserved': True,
              'positive_closed_additions': solids, 'clear_ray_checks': ray_records,
              'first_hit_visibility_probes': visibility,
              'scope_limit': 'Upper vertex preservation alone does not certify whole surface equality; author interface evidence and actual visual review remain separate gates.'}
    (config_path.parent / (config_path.stem + '-report.json')).write_text(json.dumps(report, indent=2)+'\n')
    print('Independent native PASS', len(unchanged), 'unchanged;', len(solids), 'new groups;', len(ray_records), 'clear rays')


if __name__ == '__main__':
    main(Path(sys.argv[sys.argv.index('--')+1]).resolve())
