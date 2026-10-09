"""Add recorded-network approach geometry for legacy junction cameras.
This is lane-derived placement, not observed signal hardware or turn paths.
"""
from pathlib import Path
import json,argparse,math,shutil
import numpy as np
import sumolib
from traffic.sumo_pipeline import lonlat_to_scene

def export(source,output):
 source=Path(source);output=Path(output);cfg=json.loads((source/'config.json').read_text());net=sumolib.net.readNet(str(source/'network.net.xml'),withInternal=True);proj=net.getGeoProj();offset=np.array(net.getLocationOffset());layer=json.loads((output/'signal_layer.json').read_text());visible={(h['tls_id'],h['link_index'])for h in layer['heads']};movements=[]
 for tls in net.getTrafficLights():
  for incoming,outgoing,index in tls.getConnections():
   if (tls.getID(),index)not in visible:continue
   shape=incoming.getShape()
   if len(shape)<2:continue
   ll=[proj(*(np.array(p)-offset),inverse=True)for p in shape[-2:]];xy=lonlat_to_scene(ll,cfg['transform']);xyz=[[float(x),.26,float(-y)]for x,y in xy];d=np.array(xyz[1])[::2]-np.array(xyz[0])[::2];d/=max(np.linalg.norm(d),1e-9)
   movements.append({'id':f'movement:{tls.getID()}:{index}:{incoming.getID()}:{outgoing.getID()}','tls_id':tls.getID(),'link_index':index,'from_lane':incoming.getID(),'to_lane':outgoing.getID(),'world_stop_point_xyz':xyz[-1],'world_forward_xz':d.tolist(),'world_shape_xyz':xyz,'geometry_claim':'Actual incoming lane final segment for camera/approach display; not a surveyed turn path.'})
 layer['movements']=movements;layer['counts']['movements']=len(movements)
 for name in ['signal_layer.json','signal_layer_v2.json']:(output/name).write_text(json.dumps(layer,separators=(',',':')))
 if (output/'replay/traffic_flow.f32').exists():
  identities=json.loads((output/'replay/id_map.json').read_text());(output/'replay/actors.json').write_text(json.dumps({str(n):{'numeric_id':n,'native_id':native,'entry_kind':'recorded_SUMO_departure'}for native,n in identities.items()}))
 shutil.copy2(__file__,output/'signal_movement_export_source.py');print(len(movements))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args();export(a.source,a.output)
