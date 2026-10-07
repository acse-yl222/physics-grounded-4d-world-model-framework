"""Export retained ground routes as compact world XYZ + elapsed-time records."""
import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path
import numpy as np
from common.storage import Storage


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-id',default='wavepde_ground_20261007_8m')
    args=ap.parse_args();storage=Storage.load();run=storage.run('south_ken',args.run_id)
    summary=json.loads((run/'summary.json').read_text());stations=json.loads((run/'stations_enu.json').read_text())
    if not summary.get('ground_mode'):raise ValueError('Ground-to-ground routes required')
    target=run/'uav_visualization';target.mkdir(exist_ok=False)
    rows=[];offset=0
    with tarfile.open(run/'paths_enu.tar.gz','r:gz') as tar, (target/'routes.f32').open('wb') as out:
        for r in summary['routes']:
            if not r['success']:continue
            p=np.load(io.BytesIO(tar.extractfile(r['path']).read()),allow_pickle=False)
            a=stations[r['source_index']];b=stations[r['target_index']]
            if not np.allclose(p[0],a['pad_enu_m']) or not np.allclose(p[-1],b['pad_enu_m']):raise ValueError('Endpoint mismatch')
            delta=np.diff(p,axis=0)/[15,15,5];db=delta[:,2]*.2
            dt=(-db+np.sqrt(db*db+.96*np.sum(delta*delta,axis=1)))/.96
            times=np.r_[0,np.cumsum(dt)]
            if np.any(np.diff(times)<=0):raise ValueError('Nonpositive route segment duration')
            if abs(times[-1]-r['path_travel_time_s'])>1e-3:raise ValueError('Travel-time mismatch')
            data=np.c_[p[:,0],p[:,2],-p[:,1],times].astype('<f4');out.write(data.tobytes())
            rows.append(dict(from_station=a['station_id'],to_station=b['station_id'],offset_records=offset,count=len(p),duration_s=float(data[-1,3])))
            offset+=len(p)
    converted=[dict(station_id=s['station_id'],id=s['id'],label=s['label'],role=s['role'],name=s['name'],x_m=s['pad_enu_m'][0],y_m=s['pad_enu_m'][2],z_m=-s['pad_enu_m'][1]) for s in stations]
    doc=dict(schema_version='wavepde-uav-preview-1',source_run=args.run_id,coordinate_frame='world-y-up',record=['east_m','up_m','south_m','elapsed_s'],dtype='<f4',binary='routes.f32',sha256=hashlib.sha256((target/'routes.f32').read_bytes()).hexdigest(),stations=converted,routes=rows,mode='independent_random_routes',seed=20261007,uav_count=300,duration_s=3600,limitations=['Illustrative independent flights; no multi-UAV collision avoidance or scheduling.','Routing uses an 8m sampled building grid; not continuous mesh validation.'])
    (target/'routes.json').write_text(json.dumps(doc,separators=(',',':')))
    # Declare appended assets without changing the computed routes.
    m=json.loads((run/'manifest.json').read_text())
    for name in ['routes.json','routes.f32']:
        p=target/name;m['artifacts'].append(dict(id='uav_preview_'+name.replace('.','_'),asset=str(p.relative_to(run)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),media_type='application/json' if name.endswith('.json') else 'application/octet-stream'))
    source=target/'export_source.py';source.write_bytes(Path(__file__).read_bytes())
    m['artifacts'].append(dict(id='uav_preview_export_source',asset=str(source.relative_to(run)),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),media_type='text/x-python'))
    (run/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    print(f'{len(rows)} routes, {offset} records, {target}')

if __name__=='__main__':main()
