"""Retain lineage evidence with the existing static time-series widget contract."""
from datetime import datetime,timezone
from pathlib import Path
import shutil
from common.storage import Storage
from common.contract import validate
from ..problem import digest,write_json
from .runner import read,verify


def export(directory):
    root=Path(directory).resolve();verify(root)
    if read(root/'state.json')['status']!='complete':raise ValueError('Complete final evaluation before exporting')
    target=root/'export';target.mkdir(exist_ok=False)
    for path in root.iterdir():
        if path.name=='export' or path.suffix in ('.lock','.tmp'):continue
        if path.is_dir():shutil.copytree(path,target/path.name)
        else:shutil.copy2(path,target/path.name)
    final=read(root/'final.json');cfg=read(root/'config.json');layers=[]
    def layer(name,labels,values,unit):
        asset=f'data/{name}.json';write_json(target/asset,{'labels':labels,'values':values})
        layers.append({'id':name,'kind':'time_series','format':'json','asset':asset,'sampling':'static',
                       'field':{'name':name,'unit':unit},'display':{'widget':'time_series','capabilities':['legend']}})
    layer('final_submission_valid',[x['task_id'] for x in final['scores']],
          [int(x['submitted']) for x in final['scores']],'1')
    successful=[x for x in final['scores'] if x['submitted']]
    if successful:
        layer('final_summer_reduction',[x['task_id'] for x in successful],
              [x['holdout']['summer_reduction_fraction'] for x in successful],'1')
        layer('final_holdout_feasible',[x['task_id'] for x in successful],[int(x['holdout']['feasible']) for x in successful],'1')
    artifacts=[]
    for i,path in enumerate(sorted(target.rglob('*'))):
        if path.is_file():artifacts.append({'id':'source_snapshot' if path.name=='source_snapshot.tar.gz' else f'artifact_{i}',
                                            'asset':str(path.relative_to(target)),'sha256':digest(path),'media_type':'application/octet-stream'})
    storage=Storage.load();spatial=read(storage.metadata(cfg['scene_id'])/'project.json')['spatial']
    manifest={'schema_version':'1.1.0','scene_id':cfg['scene_id'],'simulation':'urban_planning','run_id':root.name,
              'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),
              'provenance':{'code_revision':read(root/'environment.json')['code_revision'],'dirty':True,
                            'parameters':{'scope':cfg['scope'],'provider':final['provider'],'model':final['model'],
                                          'claim':final['claim'],'representation':'Static per-task evaluation summaries, not a physical time history.'},
                            'inputs':[{'id':'frozen_inputs','sha256':digest(root/'input_identity.json')}]},
              'spatial':spatial,'time':{'unit':'s','samples':[]},'layers':layers,'artifacts':artifacts}
    write_json(target/'manifest.json',manifest);validate(target/'manifest.json')
    return target
