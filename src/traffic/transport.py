"""Fetch and retain the same TfL context layers for either city; no demand inference."""
import argparse
from datetime import datetime, timezone
import json
import time
import uuid
from urllib.parse import quote
import numpy as np
import requests
from common.storage import Storage
from common.export import write, digest
from common.contract import validate
from common.provenance import snapshot_sources
from common.runs import promote
from common.city import register_view
from .sumo_pipeline import configuration, lonlat_to_scene


def fetch(storage, scene, resume=False):
    cfg = configuration(storage, scene)
    project = json.loads((storage.metadata(scene)/'project.json').read_text())
    origin = project['spatial']['origin']; bounds = project['spatial']['bounds_m']
    rid = 'transport_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
    out = storage.scratch(scene, 'transport', rid); (out/'raw').mkdir(parents=True)
    revision = snapshot_sources(storage.root, out/'source_snapshot.tar.gz')
    records, errors = [], []
    previous=None; previous_records={}
    if resume:
        selection=json.loads((storage.metadata(scene)/'configs/transport_snapshot.json').read_text())
        previous=storage.run(scene,selection['run_id'])
        previous_records={r['id']:r for r in json.loads((previous/'context.json').read_text())['requests']}
    def get(name, endpoint, **params):
        url = 'https://api.tfl.gov.uk'+endpoint
        if previous is not None and (previous/'raw'/f'{name}.json').exists():
            import shutil
            shutil.copy2(previous/'raw'/f'{name}.json',out/'raw'/f'{name}.json')
            records.append(dict(previous_records[name],reused_from=previous.name))
            return json.loads((out/'raw'/f'{name}.json').read_text())
        for attempt in range(3):
            try:
                time.sleep(1.2)
                r = requests.get(url, params=params, timeout=30, headers={'User-Agent':'PhysicsGroundedUrbanResearch/0.1'})
                r.raise_for_status(); data = r.json(); write(out/'raw'/f'{name}.json', data)
                records.append({'id':name,'url':r.url,'retrieved_utc':datetime.now(timezone.utc).isoformat()})
                return data
            except (requests.RequestException, ValueError) as exc:
                if attempt == 2: errors.append({'id':name,'error':str(exc)}); return None
                time.sleep(15 if isinstance(exc, requests.HTTPError) and exc.response.status_code==429 else 2)
    response = get('stops', '/StopPoint', lat=origin['latitude'], lon=origin['longitude'], radius=3000,
                   stopTypes='NaptanPublicBusCoachTram,NaptanMetroStation,NaptanRailStation', returnLines='true')
    if response is None: raise RuntimeError(f'TfL stop request failed: {errors}')
    def point(lon, lat): return lonlat_to_scene([[lon,lat]],cfg['transform'])[0].tolist()
    def inside(p): return all(bounds['min'][i] <= p[i] <= bounds['max'][i] for i in (0,1))
    stops = []
    for s in response['stopPoints']:
        xy = point(s['lon'],s['lat'])
        if inside(xy): stops.append({'id':s['naptanId'],'name':s['commonName'],'xy':xy,'lines':s.get('lines',[]),'modes':s.get('modes',[]),'type':s['stopType']})
    lines = sorted({l['id'] for s in stops for l in s['lines']})
    routes = []
    for i,lid in enumerate(lines):
        response = get('route_'+lid, '/Line/'+quote(lid,safe='')+'/Route/Sequence/all', serviceTypes='Regular', excludeCrowding='true')
        if response:
            for line in response.get('lineStrings',[]):
                coordinates = json.loads(line)
                parts = coordinates if coordinates and isinstance(coordinates[0][0],list) else [coordinates]
                for part in parts:
                    if len(part)>1: routes.append({'line_id':lid,'xy':lonlat_to_scene(part,cfg['transform']).tolist()})
        if i%10 == 0: print(f'{scene}: TfL routes {i+1}/{len(lines)}',flush=True)
        time.sleep(.2)
    get('line_status','/Line/Mode/tube,overground,elizabeth-line,national-rail,dlr,tram/Status')
    get('disruptions','/Road/all/Disruption',stripContent='false')
    get('cameras','/Place/Type/JamCam')
    for s in stops:
        if s['type'] in ('NaptanMetroStation','NaptanRailStation'):
            get('arrivals_'+s['id'],'/StopPoint/'+quote(s['id'],safe='')+'/Arrivals');time.sleep(.2)
    write(out/'context.json', {'stops':stops,'routes':routes,'requests':records,'errors':errors,
          'attribution':'Powered by TfL Open Data; contains OS data © Crown copyright and database rights',
          'scope':'Snapshot within a 3 km query radius, clipped to scene bounds; service data is not measured OD demand.'})
    write(out/'stops.json',{'positions':[[*s['xy'],1.] for s in stops],'values':[float(len(s['lines'])) for s in stops]})
    positions,triangles=[],[]
    for route in routes:
        for a,b in zip(route['xy'][:-1],route['xy'][1:]):
            if not inside(a) or not inside(b): continue
            a,b=np.asarray(a),np.asarray(b);delta=b-a;n=np.linalg.norm(delta)
            if n<1e-6:continue
            offset=np.array([-delta[1],delta[0]])/n*1.2;start=len(positions)
            positions.extend([[float(p[0]),float(p[1]),.4] for p in (a-offset,a+offset,b+offset,b-offset)])
            triangles.extend([[start,start+1,start+2],[start,start+2,start+3]])
    write(out/'routes.json',{'positions':positions,'triangles':triangles})
    layers=[{'id':'stops','kind':'scalar_field','format':'json','asset':'stops.json','sampling':'static','field':{'name':'serving_lines','unit':'1'},'display':{'widget':'scalar_field','capabilities':['pick','legend','opacity']}},
            {'id':'routes','kind':'mesh','format':'json','asset':'routes.json','sampling':'static','display':{'widget':'mesh','capabilities':['pick','opacity']}}]
    artifacts=[{'id':'source_snapshot' if p.name=='source_snapshot.tar.gz' else str(p.relative_to(out)),
                'asset':str(p.relative_to(out)),'sha256':digest(p),'media_type':'application/octet-stream'} for p in sorted(out.rglob('*')) if p.is_file() and (p.name not in ('stops.json','routes.json') or p.parent.name=='raw')]
    write(out/'manifest.json',{'schema_version':'1.1.0','scene_id':scene,'simulation':'transport','run_id':rid,'status':'complete',
         'created_at':datetime.now(timezone.utc).isoformat(),'provenance':{'code_revision':revision,'dirty':True,'parameters':{'transform':cfg['transform'],'failed_requests':errors,'observed_at_different_times':True},
         'inputs':[{'id':r['id'],'sha256':digest(out/'raw'/f"{r['id']}.json")} for r in records]},'spatial':project['spatial'],
         'time':{'unit':'s','samples':[]},'layers':layers,'artifacts':artifacts})
    validate(out/'manifest.json');dest=promote(storage,out)
    register_view(storage,scene,rid.lower(),['legacy_web',rid],[{'run_id':'legacy_web','layer_id':'geometry','visible':True},*[{'run_id':rid,'layer_id':x['id'],'visible':True} for x in layers]],'TfL public transport · dated snapshot')
    write(storage.metadata(scene)/'configs/transport_snapshot.json',{'run_id':rid,'view_id':rid.lower(),'failed_requests':errors})
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',choices=['south_ken','white_city']);p.add_argument('--resume',action='store_true');a=p.parse_args();print(fetch(Storage.load(),a.scene,a.resume))
