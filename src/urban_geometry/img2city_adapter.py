"""Import an existing Img2City GLB as a static, independently retained scene view."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import struct
import tarfile
from datetime import datetime, timezone

import numpy as np

from common.binary import validate_glb
from common.catalog import project
from common.contract import validate
from common.runs import promote_bundle
from common.storage import identifier, scene_id


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def node_matrix(node):
    if 'matrix' in node:
        return np.asarray(node['matrix'], dtype=float).reshape(4, 4, order='F')
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    matrix = np.eye(4)
    matrix[:3, :3] = np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)],
    ]) @ np.diag(node.get('scale', [1, 1, 1]))
    matrix[:3, 3] = node.get('translation', [0, 0, 0])
    if not np.isfinite(matrix).all():
        raise ValueError('Non-finite node transform')
    return matrix


def glb_bounds(document):
    """World-space bounds of the selected glTF scene, including node transforms."""
    points = []

    def visit(index, parent, ancestors):
        if index in ancestors:
            raise ValueError('Cyclic GLB scene graph')
        node = document['nodes'][index]
        if 'skin' in node:
            raise ValueError('Skinned geometry needs a baked static export')
        matrix = parent @ node_matrix(node)
        if 'mesh' in node:
            for primitive in document['meshes'][node['mesh']]['primitives']:
                if primitive.get('targets'):
                    raise ValueError('Morph targets need a baked static export')
                accessor = document['accessors'][primitive['attributes']['POSITION']]
                if 'min' not in accessor or 'max' not in accessor:
                    raise ValueError('POSITION accessors must declare bounds')
                for corner in itertools.product(*zip(accessor['min'], accessor['max'])):
                    points.append((matrix @ np.array([*corner, 1]))[:3])
        for child in node.get('children', []):
            visit(child, matrix, ancestors | {index})

    for index in document['scenes'][document.get('scene', 0)]['nodes']:
        visit(index, np.eye(4), set())
    if not points or not np.isfinite(points).all():
        raise ValueError('No finite mesh bounds')
    low, high = np.min(points, axis=0), np.max(points, axis=0)
    return {'min': [float(low[0]), float(-high[2]), float(low[1])],
            'max': [float(high[0]), float(-low[2]), float(high[1])]}


def align_glb(source, destination, anchor, origin):
    """Rebase Img2City's recorded equirectangular coordinates without changing BIN data."""
    document = validate_glb(source)
    if anchor.get('proj') != 'equirect':
        raise ValueError('Expected the recorded Img2City equirectangular anchor')
    lat, lon = float(anchor['lat0']), float(anchor['lon0'])
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 < lat < 90 or not -180 <= lon <= 180:
        raise ValueError('Invalid source anchor')
    target_kx = 111320.0 * math.cos(math.radians(origin['latitude']))
    scale_x = target_kx / (111320.0 * math.cos(math.radians(lat)))
    east = (lon - origin['longitude']) * target_kx
    north = (lat - origin['latitude']) * 110540.0
    active_scene = document['scenes'][document.get('scene', 0)]
    wrapper = {'name': 'Img2City_coordinate_adapter',
               'translation': [east, 0.0, -north], 'scale': [scale_x, 1.0, 1.0],
               'children': active_scene['nodes']}
    active_scene['nodes'] = [len(document['nodes'])]
    document['nodes'].append(wrapper)
    # A geometry layer has no protocol time axis. Keep the source's authored static pose.
    animation_count = len(document.pop('animations', []))
    bounds = glb_bounds(document)
    payload = json.dumps(document, separators=(',', ':'), allow_nan=False).encode()
    payload += b' ' * (-len(payload) % 4)
    with Path(source).open('rb') as src:
        src.seek(12)
        old_length, _ = struct.unpack('<II', src.read(8))
        tail_offset = 20 + old_length
        length = 20 + len(payload) + Path(source).stat().st_size - tail_offset
        with Path(destination).open('xb') as dst:
            dst.write(struct.pack('<4sII', b'glTF', 2, length))
            dst.write(struct.pack('<I4s', len(payload), b'JSON'))
            dst.write(payload)
            src.seek(tail_offset)
            shutil.copyfileobj(src, dst)
    validate_glb(destination)
    return bounds, {'source_anchor': anchor, 'target_origin': origin,
                    'gltf_translation': wrapper['translation'], 'gltf_scale': wrapper['scale'],
                    'projection': 'Img2City equirectangular: x=111320*cos(lat0)*delta_lon; north=110540*delta_lat',
                    'vertical_alignment': 'Preserved local zero; terrain elevation is not surveyed',
                    'animations_omitted': animation_count, 'display': 'authored static pose'}


def import_model(storage, source, metadata, scene='south_ken', run_id=None, view_id=None):
    source, metadata = Path(source).resolve(), Path(metadata).resolve()
    scene = scene_id(scene)
    run_id = identifier(run_id or 'img2city_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'), run=True)
    view_id = identifier(view_id or run_id.lower())
    registered = project(storage, scene)
    if (storage.metadata(scene) / 'views' / f'{view_id}.json').exists() or storage.run(scene, run_id).exists():
        raise FileExistsError('Choose a new run/view ID; existing results are preserved')
    anchor = json.loads(metadata.read_text())['anchor']
    source_hash, metadata_hash = digest(source), digest(metadata)
    trial = storage.scratch(scene, 'img2city_import', run_id)
    trial.mkdir(parents=True, exist_ok=False)
    run = trial / run_id
    (run / 'data').mkdir(parents=True)
    bounds, transform = align_glb(source, run / 'data/model.glb', anchor, registered['spatial']['origin'])
    shutil.copy2(metadata, run / 'data/input_metadata.json')
    snapshot = run / 'source_snapshot.tar.gz'
    with tarfile.open(snapshot, 'w:gz') as archive:
        archive.add(Path(__file__), arcname='img2city_adapter.py')
    if digest(source) != source_hash or digest(metadata) != metadata_hash:
        raise ValueError('Input changed during import; rerun with a new run ID')
    spatial = {**registered['spatial'], 'bounds_m': bounds}
    manifest = {
        'schema_version': '1.1.0', 'scene_id': scene, 'simulation': 'img2city_geometry',
        'run_id': run_id, 'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
        'provenance': {'code_revision': 'legacy-unrecorded', 'dirty': True,
                       'parameters': {'source_file': source.name, 'transform': transform,
                                      'preview_title': 'Img2City · ' + registered['title'],
                                      'generation_revision': 'Unknown for this existing GLB; snapshot covers import adapter only',
                                      'scope': 'Static geometry preview; no physics or traffic results are reused'},
                       'inputs': [{'id': 'img2city_glb', 'sha256': source_hash},
                                  {'id': 'buildings_metadata', 'sha256': metadata_hash}]},
        'spatial': spatial, 'time': {'unit': 's', 'samples': []},
        'layers': [{'id': 'img2city', 'kind': 'mesh', 'format': 'glb', 'asset': 'data/model.glb',
                    'sampling': 'static', 'encoding': {'coordinate_frame': 'glTF-y-up'},
                    'display': {'widget': 'mesh', 'capabilities': ['pick', 'opacity']}}],
        'artifacts': [{'id': 'source_snapshot', 'asset': snapshot.name, 'sha256': digest(snapshot), 'media_type': 'application/gzip'},
                      {'id': 'source_metadata', 'asset': 'data/input_metadata.json', 'sha256': metadata_hash, 'media_type': 'application/json'},
                      {'id': 'aligned_model', 'asset': 'data/model.glb', 'sha256': digest(run/'data/model.glb'), 'media_type': 'model/gltf-binary'}],
    }
    write_json(run / 'manifest.json', manifest)
    validate(run / 'manifest.json')
    view = {'schema_version': '1.1.0', 'scene_id': scene, 'title': 'Img2City · static geometry preview',
            'time_alignment': 'relative', 'runs': [run_id],
            'layers': [{'run_id': run_id, 'layer_id': 'img2city', 'visible': True}]}
    write_json(trial / 'bundle.json', {'scene_id': scene, 'view_id': view_id, 'runs': [run_id],
                                      'view': view, 'project': registered})
    return promote_bundle(storage, trial)
