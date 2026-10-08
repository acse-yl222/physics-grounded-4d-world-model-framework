"""Retain engineering wake experiments with explicit world-coordinate mapping."""
import argparse,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from common.storage import Storage
from common.export import write,digest
from common.contract import validate
from common.runs import promote

def export(root):
    root=Path(root);storage=Storage.load();cfg=json.loads((root/'configuration.json').read_text())
    profiles=json.loads((root/'profiles.json').read_text());prov=json.loads((root/'provenance.json').read_text())
    if json.loads((root/'status.json').read_text())['state']!='profiles_computed':raise ValueError('Run incomplete')
    layers=[];hx,hy,hz=cfg['hub_xyz_m'];D=cfg['rotor_diameter_m']
    for i,row in enumerate(profiles):
        name=f'profile_{i:03d}';asset=f'data/{name}.json'
        positions=[[hx+row['x_over_D']*D,hy+y*D/2,hz] for y in row['y_over_R']]
        write(root/asset,{'positions':positions,'values':row['deficit']})
        layers.append(dict(id=name,kind='scalar_field',format='json',asset=asset,sampling='static',
                           field={'name':'velocity_deficit','unit':'1'},display={'widget':'scalar_field','capabilities':['pick','legend']}))
    write(root/'layer_index.json',[{'id':f'profile_{i:03d}',**{k:r[k] for k in ['model','ct','expansion_k','x_over_D']}} for i,r in enumerate(profiles)])
    shutil.copyfile(__file__,root/'exporter_source.py')
    spatial=json.loads((storage.metadata('actuator_lab')/'project.json').read_text())['spatial']
    spatial['bounds_m']={'min':[0,0,0],'max':cfg['domain_xyz_m']}
    files=[p for p in root.iterdir() if p.is_file() and p.name!='manifest.json']
    artifacts=[{'id':'source_snapshot' if p.name=='source_snapshot.tar.gz' else f'artifact_{i}',
                'asset':p.name,'sha256':digest(p),'media_type':'application/octet-stream'} for i,p in enumerate(sorted(files))]
    parameters={'pywake_version':cfg['pywake_version'],'power_computed':False,
                'coordinate_transform':'PyWake origin at hub, +x downstream, wd=270; translated by CFD hub_xyz_m',
                'scope':'Engineering free-flow wakes; no tunnel walls, annular hole, or RANS equations',
                'experimental_accuracy_validated':False}
    manifest={'schema_version':'1.1.0','scene_id':'actuator_lab','simulation':'pywake_alignment','run_id':root.name,
      'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'spatial':spatial,'time':{'unit':'s','samples':[]},
      'layers':layers,'artifacts':artifacts,'provenance':{'code_revision':prov['revision'],'dirty':True,
          'parameters':parameters,'inputs':[{'id':'configuration','sha256':digest(root/'configuration.json')}]}}
    write(root/'manifest.json',manifest);validate(root/'manifest.json');return promote(storage,root)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();print(export(a.run))
