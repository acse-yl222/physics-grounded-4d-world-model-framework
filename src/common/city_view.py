"""Retain a city-viewer presentation adapter with protocol and authoring provenance."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tarfile

from common.contract import validate
from common.export import digest, write
from common.provenance import snapshot_sources
from common.runs import promote
from common.storage import Storage, identifier, scene_id


def retain(storage, scene, trial_id, run_id, authoring):
    trial = storage.scratch(scene, 'pipeline', trial_id)
    status = json.loads((trial / 'pipeline_status.json').read_text())
    if not status.get('complete'):
        raise ValueError('Cannot retain an incomplete pipeline')
    folder = storage.scratch(scene, 'city_view', run_id)
    if folder.exists():
        raise FileExistsError(folder)
    shutil.copytree(trial / 'export', folder)
    patch_path = storage.metadata(scene) / 'configs/city_viewer_patch.json'
    metadata = json.loads((folder / 'scene.json').read_text())
    if patch_path.exists():
        patch = json.loads(patch_path.read_text())
        metadata['model'].update(patch.pop('model', {}))
        metadata.update(patch)
        write(folder / 'scene.json', metadata)
        shutil.copy2(patch_path, folder / 'city_viewer_patch.json')
    provenance = folder / 'provenance'
    provenance.mkdir()
    revision = snapshot_sources(storage.root, provenance / 'source_snapshot.tar.gz')
    shutil.copy2(trial / 'source_snapshot.tar.gz', provenance / 'solver_source_snapshot.tar.gz')
    with tarfile.open(provenance / 'authoring_source.tar.gz', 'w:gz') as archive:
        for path in sorted(authoring.rglob('*')):
            if path.is_file() and 'exports' not in path.relative_to(authoring).parts and '__pycache__' not in path.parts:
                archive.add(path, arcname=str(path.relative_to(authoring)), recursive=False)
    for relative in ['pipeline_status.json', 'source_revision.txt', 'configs/scaled_latent.json', 'configs/surface_physics.json',
                     'logs/geometry.log', 'logs/wind.log', 'logs/temperature3d.log', 'logs/solar.log', 'logs/visualize.log',
                     'physics/scaled_latent/run_config.json', 'physics/scaled_latent/status.json',
                     'physics/temperature3d_physical/run_config.json', 'physics/temperature3d_physical/summary.json',
                     'physics/temperature3d_physical/solver_check.json', 'physics/solar_experimental/run_config.json',
                     *[str(path.relative_to(trial)) for path in (trial / 'geometry').glob('voxel_*/metadata.json')]]:
        source = trial / relative
        if source.exists():
            target = provenance / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    simulation = folder / 'simulation'
    simulation.mkdir()
    for source in [*sorted((trial / 'physics/scaled_latent/wind').glob('velocity_final_*_float16.npy')),
                   trial / 'physics/temperature3d_physical/temperature_c_tzyx.npy']:
        shutil.copy2(source, simulation / source.name)
    project = json.loads((storage.metadata(scene) / 'project.json').read_text())
    model = metadata['model']['url']
    artifacts = []
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path.relative_to(folder).as_posix() != model:
            relative = path.relative_to(folder).as_posix()
            artifacts.append({'id': 'source_snapshot' if relative == 'provenance/source_snapshot.tar.gz' else relative,
                              'asset': relative, 'sha256': digest(path), 'media_type': 'application/octet-stream'})
    manifest = {'schema_version': '1.1.0', 'scene_id': scene, 'simulation': 'city_presentation', 'run_id': run_id,
                'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
                'spatial': project['spatial'], 'time': {'unit': 's', 'samples': []},
                'provenance': {'code_revision': revision, 'dirty': True,
                    'parameters': {'pipeline_trial_id': trial_id, 'presentation': metadata,
                                   'solver_source_snapshot': 'provenance/solver_source_snapshot.tar.gz'},
                    'inputs': [{'id': 'geometry_glb', 'sha256': digest(folder / model)},
                               {'id': 'authoring_source', 'sha256': digest(provenance / 'authoring_source.tar.gz')}]},
                'layers': [{'id': 'geometry', 'kind': 'mesh', 'format': 'glb', 'asset': model, 'sampling': 'static',
                            'encoding': {'coordinate_frame': 'glTF-y-up'},
                            'display': {'widget': 'mesh', 'capabilities': ['pick', 'opacity']}}], 'artifacts': artifacts}
    write(folder / 'manifest.json', manifest)
    validate(folder / 'manifest.json')
    return promote(storage, folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=scene_id)
    parser.add_argument('--trial-id', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--authoring', type=Path, required=True)
    args = parser.parse_args()
    print(retain(Storage.load(), args.scene, identifier(args.trial_id, run=True),
                 identifier(args.run_id, run=True), args.authoring))


if __name__ == '__main__':
    main()
