"""Package a completed three-way comparison with self-contained plot data."""
import argparse,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from common.storage import Storage
from common.runtime import trial_root
from common.export import digest,write
from common.provenance import snapshot_sources
from common.contract import validate
from common.runs import promote

def export(report):
    storage=Storage.load();report=Path(report);result=json.loads((report/'final/comparison.json').read_text())
    if not result['torch_stationarity']['finite_window_passed'] or not result['torch_full_state_stationarity']['finite_window_passed'] or not result['openfoam_convergence']['numerical_convergence_verified']:
        raise ValueError('Comparison gates not satisfied')
    root=trial_root('actuator_lab','three_way_comparison');root.mkdir(parents=True)
    shutil.copytree(report,root/'report')
    revision=snapshot_sources(storage.root,root/'source_snapshot.tar.gz')
    spatial=json.loads((storage.metadata('actuator_lab')/'project.json').read_text())['spatial'];spatial['bounds_m']={'min':[0,0,0],'max':[12,7,2]}
    profiles=json.loads((report/'final/common_profiles.json').read_text());layers=[]
    for row in profiles:
        for model,values in row['curves'].items():
            key=f'curve_{len(layers)}';asset=f'data/{key}.json'
            write(root/asset,{'positions':[[3.66+row['x_over_D']*.4647,3.5+y*.4647/2,.8] for y in row['y_over_R']],'values':values})
            layers.append({'id':key,'kind':'scalar_field','format':'json','asset':asset,'sampling':'static',
                           'field':{'name':'velocity_deficit','unit':'1'},'display':{'widget':'scalar_field','capabilities':['pick','legend']}})
    artifacts=[]
    for f in sorted(root.rglob('*')):
        if f.is_file() and not f.is_relative_to(root/'data'):
            artifacts.append({'id':'source_snapshot' if f==root/'source_snapshot.tar.gz' else f'artifact_{len(artifacts)}',
                'asset':str(f.relative_to(root)),'sha256':digest(f),'media_type':'application/octet-stream'})
    m={'schema_version':'1.1.0','scene_id':'actuator_lab','simulation':'three_way_comparison','run_id':root.name,'status':'complete',
       'created_at':datetime.now(timezone.utc).isoformat(),'spatial':spatial,'time':{'unit':'s','samples':[]},'layers':layers,'artifacts':artifacts,
       'provenance':{'code_revision':revision,'dirty':True,'parameters':{'physical_accuracy_validated':False,'scope':'Matched-input numerical comparison; PyWake engineering-model limitations explicitly retained'},
                     'inputs':[{'id':'comparison','sha256':digest(report/'final/comparison.json')}]}}
    write(root/'manifest.json',m);validate(root/'manifest.json');return promote(storage,root)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args();print(export(a.report))
