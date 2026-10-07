"""Independently audit, plot and export the scene-specific ground routing."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def check_polyline(points, mask, spacing):
    """Independent NumPy grid-plane traversal including both sides of closed faces."""
    for a,b in zip(points[:-1],points[1:]):
        delta=b-a
        times=[0.,1.]
        for axis in range(3):
            if abs(delta[axis])<1e-12:
                continue
            low=int(np.floor(min(a[axis],b[axis])/spacing))+1
            high=int(np.ceil(max(a[axis],b[axis])/spacing))
            t=(np.arange(low,high)*spacing-a[axis])/delta[axis]
            times.extend(t[(t>0)&(t<1)].tolist())
        t=np.unique(times)
        t=np.r_[t,(t[:-1]+t[1:])/2]
        q=(a+t[:,None]*delta)/spacing
        on=np.abs(q-np.round(q))<1e-8
        idx=np.where(on,np.round(q),np.floor(q)).astype(int)
        for bits in itertools.product((0,1),repeat=3):
            ix=idx-on*np.array(bits)
            if np.any(ix<0) or np.any(ix>=np.array(mask.shape)) or mask[tuple(ix.T)].any():
                return False
    return True


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scene',choices=['south_ken','white_city'],default='south_ken')
    ap.add_argument('--wave-repo',type=Path,required=True)
    ap.add_argument('--geometry',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--run-id',default='wavepde_routes_20261007_8m')
    ap.add_argument('--framework',type=Path,default=Path(__file__).resolve().parents[2])
    args=ap.parse_args(); out=args.output
    summary=json.loads((out/'summary.json').read_text())
    stations=json.loads((out/'stations_enu.json').read_text())
    ground=summary.get('ground_mode',False)
    endpoint_key='pad_enu_m' if ground else 'gate_enu_m'
    d=np.load(out/'domain_8m.npz'); mask=d['mask']; origin=d['origin_enu_m']; cell=float(d['spacing_m'])
    valid=[r for r in summary['routes'] if r['success']]
    checks=[]
    for r in valid:
        p=np.load(out/r['path'])
        ok=check_polyline(p-origin,mask,cell)
        ends=np.allclose(p[0],stations[r['source_index']][endpoint_key],atol=1e-5,rtol=0) and np.allclose(p[-1],stations[r['target_index']][endpoint_key],atol=1e-5,rtol=0)
        delta=np.diff(p,axis=0)/np.array([15,15,5]); drift=np.array([0,0,.2]); a=1-drift@drift
        db=delta@drift; cost=np.sum((-db+np.sqrt(db**2+a*np.sum(delta**2,axis=1)))/a)
        cost_ok=abs(cost-r['path_travel_time_s'])<1e-3
        if ground:
            assert np.allclose(p[0,:2],p[1,:2]) and abs(p[1,2]-p[0,2]-30)<1e-6
            assert np.allclose(p[-1,:2],p[-2,:2]) and abs(p[-2,2]-p[-1,2]-30)<1e-6
        checks.append(dict(source=r['source'],target=r['target'],collision_free=bool(ok),endpoints=bool(ends),cost_agrees=bool(cost_ok)))
    dump(out/'independent_validation.json',dict(method='NumPy exact grid-plane subdivision with closed-cell neighbours',routes=checks,passed=sum(all(r[k] for k in ['collision_free','endpoints','cost_agrees']) for r in checks)))
    assert all(r['collision_free'] and r['endpoints'] and r['cost_agrees'] for r in checks)
    print('Independent collision, endpoint and cost checks:',len(checks),flush=True)
    fig,axes=plt.subplots(1,2,figsize=(16,7),layout='constrained')
    extent=[origin[0],origin[0]+mask.shape[0]*cell,origin[1],origin[1]+mask.shape[1]*cell]
    colors={'hub':'#dc542e','collection':'#138a78','dropoff':'#4c67b8'}
    for ax,source,title in [(axes[0],None,'All successful directed airborne routes'),(axes[1],'H1','H1 to the other stations')]:
        ax.imshow(d['height_yx_m'],origin='lower',extent=extent,cmap='Greys',vmin=0,vmax=80,alpha=.65)
        paths=[np.load(out/r['path'])[:,:2] for r in valid if source is None or r['source']==source]
        ax.add_collection(LineCollection(paths,colors='#267bb3',linewidths=.5 if source is None else 1.1,alpha=.08 if source is None else .65))
        for s in stations:
            x,y,z=s['gate_enu_m'];ax.scatter(x,y,c=colors[s['role']],s=26,zorder=4);ax.annotate(s['label'],(x,y),xytext=(4,3),textcoords='offset points',fontsize=7,zorder=5)
        ax.set(xlim=extent[:2],ylim=extent[2:],xlabel='East [m]',ylabel='North [m]',title=title,aspect='equal')
    fig.suptitle(f'{args.scene} | Wave PDE | {len(valid)}/{len(summary["routes"])} routes\n8 m grid, no wind; {"ground + 30m vertical legs" if ground else "elevated gates only"}; no fleet scheduling',fontsize=13)
    fig.savefig(out/'routes_overview.png',dpi=180);plt.close(fig)
    matrix=np.load(out/'travel_time_matrix_s.npy');fig,ax=plt.subplots(figsize=(9,8),layout='constrained')
    im=ax.imshow(matrix,cmap='viridis');fig.colorbar(im,ax=ax,label='Path-integrated model time [s]')
    labels=[s['label'] for s in stations];ax.set_xticks(range(30),labels,rotation=90,fontsize=7);ax.set_yticks(range(30),labels,fontsize=7)
    ax.set(xlabel='Destination',ylabel='Source',title='Directed travel times — '+('ground to ground' if ground else 'airborne gates only'))
    fig.savefig(out/'travel_times.png',dpi=160);plt.close(fig)
    # Retained protocol run: grouped thin ribbons display the computed static routes.
    run_id=args.run_id
    from common.storage import Storage
    storage=Storage.load(args.framework)
    run=storage.run(args.scene,run_id)
    run.mkdir(exist_ok=False)
    (run/'data').mkdir()
    layers=[]
    for s in stations:
        positions=[];triangles=[]
        for r in valid:
            if r['source']!=s['label']:continue
            p=np.load(out/r['path'])
            for a,b in zip(p[:-1],p[1:]):
                tangent=b[:2]-a[:2]; norm=np.linalg.norm(tangent)
                side=np.array([-tangent[1],tangent[0],0.])/norm*.7 if norm>1e-10 else np.array([.7,0,0])
                n=len(positions);positions.extend([(a-side).tolist(),(a+side).tolist(),(b-side).tolist(),(b+side).tolist()]);triangles.extend([[n,n+1,n+2],[n+1,n+3,n+2]])
        if not positions:continue
        layer_id='routes_'+s['label'].lower();asset='data/'+layer_id+'.json'
        dump(run/asset,dict(positions=positions,triangles=triangles))
        layers.append(dict(id=layer_id,kind='mesh',format='json',asset=asset,sampling='static',display=dict(widget='mesh',capabilities=['opacity','pick'])))
    dump(run/'data/gates.json',dict(positions=[s['gate_enu_m'] for s in stations],values=[s['gate_enu_m'][2] for s in stations]))
    layers.append(dict(id='flight_gates',kind='scalar_field',format='json',asset='data/gates.json',sampling='static',field=dict(name='flight_gate_height',unit='m'),display=dict(widget='scalar_field',capabilities=['pick','opacity'])))
    if ground:
        dump(run/'data/ground_stations.json',dict(positions=[s['pad_enu_m'] for s in stations],values=[float(s['id']) for s in stations]))
        layers.append(dict(id='ground_stations',kind='scalar_field',format='json',asset='data/ground_stations.json',sampling='static',field=dict(name='station_id',unit='1'),display=dict(widget='scalar_field',capabilities=['pick','opacity'])))
    artifacts=[]
    for name in (['stations_ground.json','ground_site_audit.npz'] if ground else [])+['summary.json','stations_enu.json','domain_8m.npz','travel_time_matrix_s.npy','travel_time_matrix_s.csv','independent_validation.json','routes_overview.png','travel_times.png']:
        shutil.copy2(out/name,run/name)
        artifacts.append(dict(id=name.replace('.', '_'),asset=name,sha256=hashlib.sha256((run/name).read_bytes()).hexdigest(),media_type='application/octet-stream'))
    with tarfile.open(run/'source_snapshot.tar.gz','w:gz') as tar:
        for path in sorted((args.wave_repo/'src/wavepde').rglob('*.py')):
            tar.add(path,arcname='wavepde/'+str(path.relative_to(args.wave_repo)))
        for directory in ['src/uav_routing','src/urban_geometry/voxelization']:
            for path in sorted((args.framework/directory).rglob('*.py')):
                tar.add(path,arcname='framework/'+str(path.relative_to(args.framework)))
    # Retain the numerical and station-selection inputs, not just their hashes.
    with tarfile.open(run/'routing_inputs.tar.gz','w:gz') as tar:
        for name in ['height_m.npy','metadata.json','ground_mesh_m_yx.npy','ground_mesh_valid_yx.npy','asphalt_8m_yx.npy','canopy_8m_yx.npy']:
            tar.add(args.geometry/name,arcname='geometry/'+name)
        for name in ['stations.json','selection.json']:
            tar.add(storage.assets(args.scene,'input')/'stations_ground_20261007'/name,arcname='stations/'+name)
    artifacts.append(dict(id='routing_inputs',asset='routing_inputs.tar.gz',sha256=hashlib.sha256((run/'routing_inputs.tar.gz').read_bytes()).hexdigest(),media_type='application/gzip'))
    artifacts.append(dict(id='source_snapshot',asset='source_snapshot.tar.gz',sha256=hashlib.sha256((run/'source_snapshot.tar.gz').read_bytes()).hexdigest(),media_type='application/gzip'))
    with tarfile.open(run/'paths_enu.tar.gz','w:gz') as tar:
        for f in sorted(out.glob('route_*.npy')):tar.add(f,arcname=f.name)
    artifacts.append(dict(id='paths_enu',asset='paths_enu.tar.gz',sha256=hashlib.sha256((run/'paths_enu.tar.gz').read_bytes()).hexdigest(),media_type='application/gzip'))
    project=json.loads((args.framework/'project'/args.scene/'project.json').read_text())
    manifest=dict(schema_version='1.1.0',scene_id=args.scene,simulation='wavepde',run_id=run_id,status='complete',created_at=datetime.now(timezone.utc).isoformat(),
       provenance=dict(code_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),dirty=True,
                       parameters={k:v for k,v in summary.items() if k not in ['routes','geometry']},inputs=[dict(id='baked_geometry',sha256=summary['geometry']['source_sha256']),dict(id='stations',sha256=summary['station_sha256'])]),
       spatial=project['spatial'],time=dict(unit='s',samples=[]),layers=layers,artifacts=artifacts)
    dump(run/'manifest.json',manifest)
    view=dict(schema_version='1.1.0',scene_id=args.scene,title='Wave PDE ground routes · 30m ascent' if ground else 'Wave PDE airborne routes · 8 m · no wind',time_alignment='relative',runs=['legacy_web',run_id],layers=[dict(run_id='legacy_web',layer_id='geometry',visible=True)]+[dict(run_id=run_id,layer_id=l['id'],visible=l['id'] in (['routes_h1','ground_stations'] if ground else ['routes_h1','flight_gates'])) for l in layers])
    dump(args.framework/'project'/args.scene/'views'/f'{run_id}.json',view)
    print('Retained:',run,flush=True)

if __name__=='__main__':main()
