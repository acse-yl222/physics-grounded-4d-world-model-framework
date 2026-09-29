"""Package audited scene samples with rebuild inputs under the versioned run contract."""
import argparse
from datetime import datetime,timezone
import json
import mimetypes
from pathlib import Path
import shutil
import tarfile
import numpy as np
from common.contract import validate
from common.export import digest,write
from common.provenance import snapshot_sources
from common.runtime import trial_root
from common.storage import Storage


def package(case):
    case=Path(case).resolve();movie=case/'movie'
    metadata=json.loads((movie/'metadata.json').read_text())
    config=json.loads((case/'configuration.json').read_text())
    history=json.loads((case/'physical_rotor_history.json').read_text())
    if not history['numerical_smoke_checks_passed']:raise ValueError('Unaudited physics output')
    export_info=json.loads((movie/'export_provenance.json').read_text())
    if export_info['configuration_sha256']!=digest(case/'configuration.json'):
        raise ValueError('Movie/configuration mismatch; export the current completed phase')
    shape=(len(metadata['times']),*metadata['display_shape'])
    raw=np.concatenate([np.fromfile(movie/name,dtype='<f2') for name in metadata['wind_chunks']])
    if raw.size!=int(np.prod(shape)):raise ValueError('Movie payload length mismatch')
    field=raw.reshape(shape);mask=~np.isfinite(field[0])
    if not np.all((~np.isfinite(field))==mask):
        raise ValueError('Changing missing-point support needs an explicit protocol representation')
    out=trial_root('windfarm','openfoam_scene_export');out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(movie,out/'movie')
    np.save(out/'axial_velocity.npy',field)
    np.save(out/'invalid.npy',mask.astype('u1'))
    shutil.copy2(case/'ground.npy',out/'ground.npy')
    for name in ('configuration.json','physical_rotor_history.json','log.pimpleFoam','log.checkMesh',
                 'mesh_mapping.json','rotor_support_audit.json','transient_source_snapshot.tar.gz',
                 'transient_provenance.json','regularized_fluid_cells.npy'):
        shutil.copy2(case/name,out/name)
    for name in ('parent_checkpoint_2s.tar.gz','benchmark_source_snapshot.tar.gz','benchmark_provenance.json',
                 'parallel_comparison.json','completed_benchmark_configuration.json'):
        if (case/name).is_file():shutil.copy2(case/name,out/name)
    # Rebuild from the original block, cell selection, initial fields and exact dictionaries.
    with tarfile.open(out/'case_inputs.tar.gz','w:gz') as archive:
        for directory in ('0','system','constant'):
            for source in sorted((case/directory).rglob('*')):
                if source.is_file() and 'polyMesh' not in source.parts:
                    archive.add(source,arcname=str(source.relative_to(case)))
        for name in ('fluidCells.input','metadata.json','terrain_valid.npy','ground.npy'):
            archive.add(case/name,arcname=name)
        for phase in sorted(case.glob('completed_through_*s')):
            archive.add(phase,arcname=phase.name)
    revision=snapshot_sources(Storage.load().root,out/'source_snapshot.tar.gz')
    spatial=json.loads((Storage.load().metadata('windfarm')/'project.json').read_text())['spatial']
    origin=list(metadata['origin_xyz_m']);origin[2]=metadata['slice_agl_m']
    layer=dict(id='axial_velocity',kind='scalar_field',format='npy',asset='axial_velocity.npy',sampling='linear',
        field={'name':'axial_velocity','unit':'m/s'},encoding=dict(coordinate_frame='ENU',dtype='<f2',shape=list(shape),
        axes='TYX',origin_m=origin,spacing_m=[metadata['display_cell_m']]*2,sample_location='cell_center',
        byte_order='little',compression='none',height_asset='ground.npy',height_dtype='<f4',
        mask_asset='invalid.npy',mask_dtype='|u1',mask_semantics='invalid_nonzero'),
        display={'widget':'scalar_field','capabilities':['pick','legend','opacity'],'range':[0,20]})
    assets=[]
    for index,path in enumerate(sorted(out.rglob('*'))):
        if path.is_file():
            key='source_snapshot' if path.name=='source_snapshot.tar.gz' else f'artifact_{index}'
            assets.append({'id':key,'asset':str(path.relative_to(out)),'sha256':digest(path),'media_type':mimetypes.guess_type(path.name)[0] or 'application/octet-stream'})
    manifest=dict(schema_version='1.1.0',scene_id='windfarm',simulation='openfoam_urans',run_id=out.name,
        status='complete',created_at=datetime.now(timezone.utc).isoformat(),spatial=spatial,
        time={'unit':'s','samples':metadata['times']},layers=[layer],artifacts=assets,
        provenance={'code_revision':revision,'dirty':True,'parameters':config|{'experimental_accuracy_validated':False,
            'publish_ready':False,'completed_run_is_not_full_paper_validation':True},
            'inputs':[{'id':'scene_configuration','sha256':digest(case/'configuration.json')}]})
    write(out/'manifest.json',manifest);validate(out/'manifest.json');print(out);return out

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('case',type=Path)
    package(parser.parse_args().case)
