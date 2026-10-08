"""Verify explicitly selected city runs and deterministic SUMO comparisons."""
from datetime import datetime,timezone
import json
import xml.etree.ElementTree as ET
import numpy as np
from .city import audit,SCENES
from .storage import Storage
from .contract import validate
from .export import digest,write


def routes(path):
    root=ET.parse(path).getroot()
    return [(v.get('id'),v.get('depart'),v.find('route').get('edges')) for v in root.findall('vehicle')]


def verify(storage):
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'capabilities':audit(storage),'scenes':{}}
    if not result['capabilities']['module_parity']:raise ValueError('City module parity is incomplete')
    for scene in SCENES:
        config=storage.metadata(scene)/'configs'
        def read(name):return json.loads((config/name).read_text())
        fields=read('city_fields.json');traffic=read('traffic_experiment.json')
        entries=[x['run_id'] for x in fields.values()]+list(traffic.values())
        entries += [read(f)['run_id'] for f in ('traffic_result.json','diurnal_result.json','transport_snapshot.json','rsi_city_result.json')]
        checks=[]
        for rid in sorted(set(entries)):
            checks.append({'run_id':rid,'layers':validate(storage.run(scene,rid)/'manifest.json')})
        base,slow,repeat=(storage.run(scene,traffic[k]) for k in ('baseline','speed_0_7','repeat'))
        same_routes=routes(base/'routes.rou.xml')==routes(slow/'routes.rou.xml')==routes(repeat/'routes.rou.xml')
        same_frames=digest(base/'trajectories_full.json')==digest(repeat/'trajectories_full.json')
        intervention_changes=digest(base/'trajectories_full.json')!=digest(slow/'trajectories_full.json')
        if not same_routes or not same_frames or not intervention_changes:raise ValueError('SUMO intervention/reproducibility check failed')
        summaries={k:json.loads((storage.run(scene,rid)/'summary.json').read_text()) for k,rid in traffic.items()}
        if any(v['collisions'] or v['teleports'] for v in summaries.values()):raise ValueError('Traffic smoke check reported collisions/teleports')
        for root in (base,slow,repeat):
            if ET.parse(root/'network.net.xml').getroot().get('lefthand')!='true':raise ValueError('Traffic network is not left-hand')
        thermal=storage.run(scene,read('diurnal_result.json')['run_id'])
        air=np.load(thermal/'air.npy',mmap_mode='r');mask=np.load(thermal/'air_invalid.npy').astype(bool)
        thermal_metrics={'shape':list(air.shape),'all_finite':bool(np.isfinite(air).all()),
                         'final_fluid_mean_c':float(air[-1][~mask].mean()),'final_fluid_min_c':float(air[-1][~mask].min()),
                         'final_fluid_max_c':float(air[-1][~mask].max())}
        transport=read('transport_snapshot.json')
        if transport['failed_requests']:raise ValueError('TfL snapshot still has missing requests')
        context=json.loads((storage.run(scene,transport['run_id'])/'context.json').read_text())
        result['scenes'][scene]={'validated_manifests':checks,'traffic':{'runs':traffic,'same_od_routes':same_routes,
                  'exact_repeat_trajectories':same_frames,'intervention_changed_trajectories':intervention_changes,
                  'summaries':summaries,'interpretation':'300-second cold-start engineering tests with 100 scheduled synthetic trips. Right-censored trip durations; not calibrated real-world performance.'},
                  'thermal':thermal_metrics,'transport':{'stops':len(context['stops']),'route_lines':len({r['line_id'] for r in context['routes']}),'missing_requests':0},
                  'observations':read('traffic_observations.json'),'rsi':read('rsi_city_result.json')}
    browser=storage.root/'cache/framework/city-parity-browser/report.json'
    if browser.exists():result['browser']=json.loads(browser.read_text())
    for scene in SCENES:
        folder=storage.metadata(scene)/'reports';folder.mkdir(exist_ok=True)
        write(folder/'city-parity-20260930.json',result)
    return result


if __name__=='__main__':
    result=verify(Storage.load())
    print(json.dumps({s:{'manifests':len(x['validated_manifests']),'traffic_reproduced':x['traffic']['exact_repeat_trajectories'],
                        'traffic':x['traffic']['summaries'],'thermal':x['thermal'],'transport':x['transport']} for s,x in result['scenes'].items()},indent=2))
