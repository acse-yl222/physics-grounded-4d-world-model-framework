"""Compare a completed parallel branch against already-recorded reference times.

Uses interpolation only within recorded reference samples, never extrapolation.
The runs have different write-adjusted steps and share a contended host; this is
an operational comparison, not a pure strong-scaling or time-convergence study.
"""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from common.export import write,digest
from .scene_diagnostics import analyze,loads
from .export_scene_movie import sample_grid


def wall_records(text):
    segment=re.split(r'^Exec\s+:',text,flags=re.M)[-1]
    records=[];current=None
    for line in segment.splitlines():
        if line.startswith('Time = '):current=float(line.split('=')[1])
        match=re.search(r'ExecutionTime = \S+ s\s+ClockTime = (\S+) s',line)
        if match and current is not None:records.append((current,float(match[1])))
    return np.asarray(records)


def compare(reference,candidate):
    reference=Path(reference);candidate=Path(candidate)
    result=analyze(candidate)
    if not result['numerical_smoke_checks_passed']:raise ValueError('Candidate failed numerical checks')
    a=json.loads((reference/'configuration.json').read_text());b=json.loads((candidate/'configuration.json').read_text())
    for key in ('inlet_m_s','rho_kg_m3','ct','sigma_m','cutoff_sigma','cell_m','turbulence_model',
                'kinematic_viscosity_m2_s','turbulence_intensity','turbulence_length_m','world_origin_xyz_m'):
        if a[key]!=b[key]:raise ValueError(f'Physical settings differ: {key}')
    for name in ('constant/fvOptions','system/fvSchemes','system/fvSolution'):
        if digest(reference/name)!=digest(candidate/name):raise ValueError(f'Solver/source settings differ: {name}')
    end=b['target_seconds']
    ref_log=(reference/'log.pimpleFoam').read_text()
    # Reference remains live; require its completed steps to extend beyond the compared interval.
    clocks=wall_records(ref_log)
    if clocks[-1,0]<=end+.5:raise ValueError('Reference has not advanced sufficiently')
    lines=[line for line in ref_log.splitlines() if line.startswith('FARM_ROTOR ') and float(line.split()[2])<=end+.5]
    ref_loads=loads('\n'.join(lines)+'\n',a['rho_kg_m3'])
    target_times=np.asarray(result['times']);chosen=(target_times>2)&(target_times<=end)
    force=np.asarray(result['thrust_N'])[chosen];times=target_times[chosen]
    if times[0]<ref_loads['times'][0] or times[-1]>ref_loads['times'][-1]:raise ValueError('Load extrapolation forbidden')
    expected=np.stack([np.interp(times,ref_loads['times'],np.asarray(ref_loads['thrust_N'])[:,i]) for i in range(23)],axis=1)
    force_error=float(np.max(np.abs(force-expected)/np.maximum(np.abs(expected),1.)))
    ref_samples=sorted((float(p.name),p) for p in (reference/'postProcessing/terrainSlice').iterdir() if p.is_dir())
    ground=np.load(reference/'ground.npy');valid=np.load(reference/'terrain_valid.npy')
    if not np.array_equal(ground,np.load(candidate/'ground.npy')):raise ValueError('Terrain changed')
    geometry=json.loads((reference/'metadata.json').read_text());cache={}
    def field(folder):
        key=str(folder)
        if key not in cache:
            cache[key]=sample_grid(np.loadtxt(folder/'slice_U.xy'),ground,a['cell_m'],a['slice_agl_m'],geometry['origin_xyz_m'][2])
        return cache[key]
    profile=[]
    for folder in sorted((candidate/'postProcessing/terrainSlice').iterdir(),key=lambda p:float(p.name)):
        time=float(folder.name)
        if time<=2:continue
        upper=int(np.searchsorted([t for t,_ in ref_samples],time))
        if upper==0 or upper==len(ref_samples):raise ValueError('Field extrapolation forbidden')
        t0,p0=ref_samples[upper-1];t1,p1=ref_samples[upper]
        fraction=(time-t0)/(t1-t0);expected_field=(1-fraction)*field(p0)+fraction*field(p1);actual=field(folder)
        if not np.array_equal(np.isfinite(actual),np.isfinite(expected_field)):raise ValueError('Missing support differs')
        mask=valid&np.isfinite(actual);delta=actual[mask]-expected_field[mask]
        profile.append(dict(time_s=time,rms_difference_m_s=float(np.sqrt(np.mean(delta**2))),
                            relative_l2_difference=float(np.linalg.norm(delta)/np.linalg.norm(expected_field[mask])),
                            max_difference_m_s=float(np.max(np.abs(delta)))))
    if not profile or not np.isclose(profile[-1]['time_s'],end,rtol=0,atol=1e-7):
        raise ValueError('Final candidate field sample is missing')
    candidate_clock=wall_records((candidate/'log.pimpleFoam').read_text())
    start=2.5;stop=end-.5
    elapsed=[]
    for clock in (clocks,candidate_clock):
        if clock[0,0]>start or clock[-1,0]<stop:raise ValueError('Insufficient timing window')
        elapsed.append(float(np.interp(stop,clock[:,0],clock[:,1])-np.interp(start,clock[:,0],clock[:,1])))
    return dict(reference_case=reference.name,candidate_case=candidate.name,
        max_relative_thrust_difference=force_error,field_comparisons=profile,
        timing_window_s=[start,stop],reference_wall_seconds=elapsed[0],candidate_wall_seconds=elapsed[1],
        observed_speed_ratio=elapsed[0]/elapsed[1],
        numerical_difference_screen_passed=bool(force_error<.01 and all(x['relative_l2_difference']<.01 for x in profile)),
        interpretation=__doc__,experimental_accuracy_validated=False,
        candidate_log_sha256=digest(candidate/'log.pimpleFoam'))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',type=Path);parser.add_argument('candidate',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=compare(args.reference,args.candidate);write(args.output,result);print(json.dumps(result,indent=2))
