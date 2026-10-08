"""Retain static sampled fields and an illustrative movie under protocol 1.1."""
import argparse,json,shutil
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from common.storage import Storage
from common.runtime import trial_root
from common.export import digest,write
from common.provenance import snapshot_sources
from common.contract import validate
from common.runs import promote
from .animate_alignment import D,HUB,NAMES

def export(report):
    storage=Storage.load(); root=trial_root('actuator_lab','alignment_animation');root.mkdir(parents=True)
    shutil.copytree(report,root/'media')
    a=np.load(report/'fields.npz');x,y=a['x'],a['y'];xx,yy=np.meshgrid(x,y)
    pos=np.stack([HUB[0]+xx*D,HUB[1]+yy*D,np.full_like(xx,HUB[2])],-1).reshape(-1,3)
    layers=[]
    for i,field in enumerate(a['fields']):
        asset=f'data/field_{i}.json';write(root/asset,{'positions':pos.tolist(),'values':field.ravel().tolist()})
        layers.append({'id':f'field_{i}','kind':'scalar_field','format':'json','asset':asset,'sampling':'static',
                       'field':{'name':'streamwise_velocity','unit':'m/s'},'display':{'widget':'scalar_field','capabilities':['pick','legend']}})
    rev=snapshot_sources(storage.root,root/'source_snapshot.tar.gz')
    spatial=json.loads((storage.metadata('actuator_lab')/'project.json').read_text())['spatial'];spatial['bounds_m']={'min':[0,0,0],'max':[12,7,2]}
    artifacts=[{'id':'source_snapshot' if f.name=='source_snapshot.tar.gz' else f'artifact_{i}',
        'asset':str(f.relative_to(root)),'sha256':digest(f),'media_type':'video/mp4' if f.suffix=='.mp4' else 'application/octet-stream'}
        for i,f in enumerate(sorted(root.rglob('*'))) if f.is_file() and not f.is_relative_to(root/'data')]
    write(root/'manifest.json',{'schema_version':'1.1.0','scene_id':'actuator_lab','simulation':'alignment_animation','run_id':root.name,
        'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'spatial':spatial,'time':{'unit':'s','samples':[]},
        'layers':layers,'artifacts':artifacts,'provenance':{'code_revision':rev,'dirty':True,
        'parameters':{'models':NAMES,'physical_transient_animation':False,'description':'Static sampled Ux fields; illustrative Ux-only tracers. See media/provenance.json.','replay':'python -m urban_flow.paper_rotor.animate_alignment render media'},
        'inputs':[{'id':'sampled_fields','sha256':digest(report/'fields.npz')}]}})
    validate(root/'manifest.json');return promote(storage,root)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);print(export(p.parse_args().report))
