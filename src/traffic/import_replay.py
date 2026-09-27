"""Adapt the preserved SUMO export to ENU sparse trajectory frames without inventing missing time."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from common.storage import Storage
from common.contract import validate


def main():
    storage=Storage.load();root=storage.run('south_ken','legacy_agents');source=root/'data/traffic/replay'
    index=json.loads((source/'frames_index.json').read_text());raw=np.fromfile(source/'traffic_flow.f32',dtype='<f4').reshape(-1,5)
    frames=[]
    for entry in index:
        start=entry['offset_bytes']//20;rows=raw[start:start+entry['count']]
        if len(rows)!=entry['count']:raise ValueError('Truncated recorded traffic frame')
        positions=rows[:,1:3].astype(float)-[2912.594719173,1704.705026026]
        frames.append({'ids':[str(int(v)) for v in rows[:,0]],'positions':[[float(x),float(y),.275] for x,y in positions]})
    (root/'trajectories.json').write_text(json.dumps({'frames':frames},separators=(',',':'),allow_nan=False))
    project=json.loads((storage.metadata('south_ken')/'project.json').read_text())
    with (source/'traffic_flow.f32').open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    manifest={'schema_version':'1.1.0','scene_id':'south_ken','simulation':'traffic','run_id':'legacy_agents','status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'provenance':{'code_revision':'preserved-SUMO-replay-export','dirty':False,'parameters':{'imported':True,'source_format':'uwm-traffic-sparse-flow-v2','source_xy_to_enu_translation_m':[-2912.594719173,-1704.705026026],'source_record_layout':'5 little-endian float32: numeric_id, sumo_x_m, sumo_y_m, angle_deg, speed_m_s','exported_interval_s':[index[0]['t_s'],index[-1]['t_s']],'note':'The available export is 300 seconds. Original simulation metadata describes a longer 3600-second run; missing frames are not fabricated.'},'inputs':[{'id':'traffic_flow.f32','sha256':digest}]},'spatial':project['spatial'],'time':{'unit':'s','samples':[f['t_s'] for f in index]},'layers':[{'id':'traffic','kind':'trajectories','format':'trajectory_frames','asset':'trajectories.json','sampling':'linear','display':{'widget':'trajectories','capabilities':['pick','opacity']}}]}
    path=root/'manifest.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(manifest,indent=2)+'\n');validate(path)
    view={'schema_version':'1.1.0','scene_id':'south_ken','title':'Geometry, wind and recorded traffic','time_alignment':'relative','runs':['legacy_web','legacy_agents'],'layers':[{'run_id':'legacy_web','layer_id':'geometry','visible':True},{'run_id':'legacy_web','layer_id':'wind','visible':True},{'run_id':'legacy_agents','layer_id':'traffic','visible':True}]}
    (storage.metadata('south_ken')/'views/traffic.json').write_text(json.dumps(view,indent=2)+'\n')
    print(f'Registered {len(frames)} recorded frames, {index[0]["t_s"]}–{index[-1]["t_s"]} s')
if __name__=='__main__':main()
