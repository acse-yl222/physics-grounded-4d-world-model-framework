"""Reproducible scene-specific Wave PDE all-pairs ground routing.

Uses scene geometry rasterized by the framework prepare_glb adapter.
Ground mode adds 30m vertical legs; sites are model-derived, not surveyed.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.ndimage import maximum_filter
import torch
from wavepde.torch_backend import WaveConfig, plan_paths, waveform_samples
from wavepde.torch_backend.geometry import segment_free, segment_time


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scene', choices=['south_ken', 'white_city'], default='south_ken')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--framework', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--sources', type=int, default=30)
    ap.add_argument('--geometry', type=Path, required=True, help='Prepared 2m geometry directory')
    ap.add_argument('--station-file', type=Path)
    ap.add_argument('--ground-mode', action='store_true')
    args = ap.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    geo = args.geometry
    meta = json.loads((geo / 'metadata.json').read_text())
    from common.storage import Storage
    storage = Storage.load(args.framework)
    station_file = args.station_file or storage.assets(args.scene, 'input') / 'stations_ground_20261007/stations.json'
    stations = json.loads(station_file.read_text())
    fine = np.load(geo / 'height_m.npy')
    # Include sampled canopy heights if available in future adapter exports.
    cell = 8.0
    factor = 4
    ny, nx = fine.shape
    height = fine.reshape(ny//factor, factor, nx//factor, factor).max(axis=(1,3))
    # One coarse cell horizontal dilation; full vertical columns close overhangs.
    height = maximum_filter(height, size=3, mode='nearest')
    nz = 20
    mask = np.ascontiguousarray(((np.arange(nz)*cell)[None,None,:] < height.T[:,:,None]))
    origin = np.array(meta['source_region_origin_xyz_m'], dtype=float)
    np.savez_compressed(out/'domain_8m.npz', mask=mask, origin_enu_m=origin, spacing_m=cell, height_yx_m=height)
    gates = []
    for s in stations:
        x,y,z = s['xyz']
        pad = np.array([x,-z,y])
        ij = np.floor((pad[:2]-origin[:2])/cell).astype(int)
        roof = float(height[ij[1],ij[0]])
        gate = pad.copy()
        gate[2] = pad[2] + 30. if args.ground_mode else max(24., np.ceil(max(roof,pad[2])/cell)*cell+12.)
        if args.ground_mode and roof > 0:
            raise ValueError(f'Ground station has blocked vertical column: {s["label"]}')
        if gate[2] >= (nz-2)*cell:
            raise ValueError(f'Flight gate too high: {s["label"]}')
        gates.append(gate-origin)
        s['pad_enu_m'] = pad.tolist()
        s['gate_enu_m'] = gate.tolist()
        s['gate_height_above_pad_m'] = float(gate[2]-pad[2])
        s['takeoff_landing_verified'] = bool(args.ground_mode)
        s['verification_scope'] = 'closed 8m routing voxels and sampled ground support' if args.ground_mode else 'not verified'
    gates = np.array(gates)
    write_json(out/'stations_enu.json', stations)
    cfg = WaveConfig(c0=15,cz_up=6,cz_down=4,dt=.2,n_steps=1800,
                     pulse_t0_steps=60,pulse_tau_steps=8,source_sigma_cells=1.5,
                     sponge_layers=4,min_peak_amp=1e-8,reg_low_factor=1,
                     reg_z_low=-2,reg_z_full=-1)
    device = 'cuda'
    torch.set_num_threads(4)
    m = torch.as_tensor(mask,device=device)
    waveform = waveform_samples('gaussian_long',cfg.dt,cfg.n_steps,device=device)
    routes = []
    matrix = np.full((len(stations),len(stations)),np.nan)
    np.fill_diagonal(matrix,0)
    identity = dict(station_sha256=hashlib.sha256(station_file.read_bytes()).hexdigest(),
                    geometry_sha256=hashlib.sha256((geo/'height_m.npy').read_bytes()).hexdigest(),
                    ground_mode=args.ground_mode, cfg=asdict(cfg), spacing_m=cell)
    identity_path = out/'input_identity.json'
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise ValueError('Output directory belongs to different inputs or configuration')
    if not identity_path.exists() and list(out.glob('source_*.json')):
        raise ValueError('Existing checkpoints have no input identity; use a fresh output directory')
    write_json(identity_path, identity)
    started = time.time()
    for i in range(args.sources):
        checkpoint = out/f'source_{i:02d}.json'
        if checkpoint.exists():
            rows = json.loads(checkpoint.read_text())
            routes.extend(rows)
            for r in rows:
                if r['success']: matrix[i,r['target_index']] = r['path_travel_time_s']
            continue
        targets = [j for j in range(len(stations)) if j!=i]
        t0 = time.time()
        result = plan_paths(m,cell,gates[i],gates[targets],cfg,device=device,
                            waveform=waveform,smoothing_m=4,step_m=4,
                            terminal_m=24,max_steps=3000)
        names = result.traces.status_names()
        rows = []
        for k,j in enumerate(targets):
            p = result.traces.path(k)
            success = names[k]=='reached'
            if args.ground_mode and success:
                pads = [np.array(stations[v]['pad_enu_m'])-origin for v in (i,j)]
                p = torch.cat([torch.as_tensor(pads[0],device=device)[None],p,torch.as_tensor(pads[1],device=device)[None]])
            collision_free = bool(segment_free(m,p[:-1],p[1:],cell,max_length=32).all()) if len(p)>1 else False
            endpoints = bool(torch.linalg.vector_norm(p[0]-torch.as_tensor(np.array(stations[i]['pad_enu_m'])-origin if args.ground_mode else gates[i],device=device))<1e-3 and
                             torch.linalg.vector_norm(p[-1]-torch.as_tensor(np.array(stations[j]['pad_enu_m'])-origin if args.ground_mode else gates[j],device=device))<1e-3)
            success = success and collision_free and endpoints
            arr = float(result.traces.arrivals[k])
            cost = float(segment_time(p[1:]-p[:-1]).sum()) if success else None
            name=f'route_{stations[i]["label"]}_{stations[j]["label"]}.npy'
            # Failed traces are kept explicitly as partial paths, never used in matrix.
            np.save(out/name,p.cpu().numpy()+origin)
            row = dict(source_index=i,target_index=j,source=stations[i]['label'],target=stations[j]['label'],
                       status=names[k],success=success,collision_free=collision_free,endpoints_verified=endpoints,
                       path=name,points=len(p),path_travel_time_s=cost,
                       length_m=float(torch.linalg.vector_norm(p[1:]-p[:-1],dim=-1).sum()) if success else None,
                       raw_detector_arrival_s=arr if np.isfinite(arr) else None,
                       projected_steps=int(result.traces.projected_steps[k]),takeoff_landing_included=bool(args.ground_mode and success))
            rows.append(row)
            if success: matrix[i,j]=cost
        write_json(checkpoint,rows)
        routes.extend(rows)
        print(f'{i+1}/{args.sources} {stations[i]["label"]}: {sum(r["success"] for r in rows)}/{len(rows)} {Counter(names)} {time.time()-t0:.1f}s',flush=True)
        del result
    np.save(out/'travel_time_matrix_s.npy',matrix)
    np.savetxt(out/'travel_time_matrix_s.csv',matrix,delimiter=',',header=','.join(s['label'] for s in stations),comments='')
    summary = dict(scene=args.scene,cfg=asdict(cfg),spacing_m=cell,shape_xyz=list(mask.shape),origin_enu_m=origin.tolist(),
                   ground_mode=args.ground_mode,waveform='gaussian_long',routes=routes,successes=sum(r['success'] for r in routes),total=len(routes),
                   elapsed_this_invocation_s=time.time()-started,geometry=meta,
                   station_sha256=hashlib.sha256(station_file.read_bytes()).hexdigest(),
                   solver='wavepde.torch_backend.plan_paths',torch_version=torch.__version__,device=torch.cuda.get_device_name(),
                   assumptions=['No wind; no inter-UAV scheduling or dynamic obstacles.',
                     'Ground stations; vertical ascent/descent 30m included.' if args.ground_mode else 'Airborne gates only, same XY as stations; rooftop takeoff/landing excluded.',
                     '2m sampled building height raster max pooled to 8m, dilated one 8m cell horizontally.',
                     '2.5D solid columns; thin geometry may be missed; trees excluded by source raster adapter.',
                     'Path travel times integrate model speed along routes; uncalibrated raw PDE detector times are separate.',
                     'Independent continuous GLB collision validation not performed.'])
    write_json(out/'summary.json',summary)
    print(f'DONE {summary["successes"]}/{len(routes)}',flush=True)

if __name__=='__main__':
    main()
