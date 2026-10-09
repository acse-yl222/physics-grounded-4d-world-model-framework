"""Publish only selected three-scene activity browser exports; never push.

Run build_public_site.py first. Per-scene city_density026.json records the
accepted traffic export path; retained solvers, source snapshots and geometry
are not copied. Existing geometry resource manifests remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n')

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def copy_traffic(source,target,demo=False):
    if target.exists():raise ValueError('Do not overwrite a published traffic version: '+str(target))
    target.mkdir(parents=True)
    names=('current_replay.json','roads.json','signal_layer_v2.json') if demo else ('replay.json','roads.json','signal_layer.json','verification.json')
    for name in names:shutil.copy2(source/name,target/name)
    shutil.copytree(source/'replay',target/'replay')

def package(site):
    for scene,legacy in [('south_ken','south_kensington'),('white_city','white_city'),('tower_hamlets','tower_hamlets')]:
        config=json.loads((ROOT/f'project/{scene}/configs/city_density026.json').read_text())
        source=(ROOT/config['traffic_export']).resolve()
        if not source.is_relative_to(ROOT/'project'/scene/'runs'):raise ValueError('Expected retained scene export')
        if scene=='south_ken':
            target=site/'project/south_ken/input/traffic_density026'
            copy_traffic(source,target,demo=True)
            scene_path=site/f'scenes/{legacy}/scene.json'
            metadata=json.loads(scene_path.read_text());metadata['limits']=list(dict.fromkeys(metadata.get('limits',[])+config.get('limits',[])));write(scene_path,metadata)
            route=site/'project/south_ken/configs/uav_visualization.json'
            data=json.loads(route.read_text());data['traffic_replay']='../input/traffic_density026/';write(route,data)
        else:
            target=site/f'scenes/{legacy}/traffic_density026'
            copy_traffic(source,target)
            scene_path=site/f'scenes/{legacy}/scene.json'
            data=json.loads(scene_path.read_text())
            if scene=='tower_hamlets':
                run=ROOT/'project/tower_hamlets/runs/canary_wharf_city_activity_026'
                old_model=data['model'];data=json.loads((run/'scene.json').read_text())
                data['model']['parts_manifest']=old_model['parts_manifest']
                shutil.copytree(run/'uav',site/f'scenes/{legacy}/uav',dirs_exist_ok=True)
            data['traffic']={'dir':'traffic_density026/','start_s':600,'label':config['label']}
            data['limits']=list(dict.fromkeys(data.get('limits',[])+config.get('limits',[])))
            write(scene_path,data)
        files=[{'path':str(p.relative_to(target)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(target.rglob('*'))if p.is_file()]
        write(target/'publication.json',{'scene_id':scene,'source_run':config['traffic_run'],'source_manifest_sha256':sha(ROOT/f'project/{scene}/runs'/config['traffic_run']/'manifest.json'),'assets':files,'limits':config.get('limits',[])})
    with (site/'.gitignore').open('a') as f:f.write('\n# Selected South Kensington dense recorded traffic\n!project/south_ken/input/traffic_density026/replay/*.f32\n!project/south_ken/input/traffic_density026/replay/*.jsonl\n')
    # Refresh the Canary page-level browser asset inventory after the versioned update.
    folder=site/'scenes/tower_hamlets'
    write(folder/'publication.json',{'source_run':'canary_wharf_city_activity_026','source_manifest_sha256':sha(ROOT/'project/tower_hamlets/runs/canary_wharf_city_activity_026/manifest.json'),'assets':[{'path':str(p.relative_to(folder)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(folder.rglob('*'))if p.is_file() and p!=folder/'publication.json']})
    print('Prepared three selected dense activity exports; original scene geometry and fields preserved.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('site',type=Path);args=parser.parse_args();package(args.site.resolve())
