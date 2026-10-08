"""Verified SUMO replay adapter for the shared legacy city viewer.
Re-simulates immutable retained inputs solely to recover missing pose/lane records,
requiring exact retained positions and signal states at every recorded time.
"""
from pathlib import Path
import argparse,json,math,shutil,hashlib
import numpy as np
import sumo,sumolib,traci
from traffic.sumo_pipeline import lonlat_to_scene, clip_segment

def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,separators=(',',':')))
def clip_lane(points):
 groups=[];current=[]
 for a,b in zip(points,points[1:]):
  pair=clip_segment([a[0],a[2]],[b[0],b[2]],{'min':[-2000,-2000],'max':[2000,2000]})
  if pair is None:
   if current:groups.append(current);current=[]
   continue
  x,y=pair;aa=[float(x[0]),.26,float(x[1])];bb=[float(y[0]),.26,float(y[1])]
  if current and np.linalg.norm(np.asarray(current[-1])-aa)>1e-6:groups.append(current);current=[]
  if not current:current=[aa]
  current.append(bb)
 if current:groups.append(current)
 return max(groups,key=len)if groups else []

def export(source,out):
 source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=False);work=out/'verification_rerun';work.mkdir();read=lambda p:json.loads(p.read_text());cfg=read(source/'config.json');m=read(source/'manifest.json');times=m['time']['samples'];reference=read(source/'trajectories.json')['frames'];original_signals=read(source/'signals.json');net=sumolib.net.readNet(str(source/'network.net.xml'),withInternal=True);offset=np.asarray(net.getLocationOffset());proj=net.getGeoProj()
 for name in ['network.net.xml','routes.rou.xml','run.sumocfg']:shutil.copy2(source/name,work/name)
 def to_xy(points):
  points=np.asarray(points)-offset;lon,lat=proj(points[:,0],points[:,1],inverse=True);return lonlat_to_scene(np.column_stack([lon,lat]),cfg['transform'])
 def world(points):return [[float(x),.26,float(-y)]for x,y in to_xy(points)]
 def inside(p):return -2000<=p[0]<=2000 and -2000<=p[2]<=2000
 lanes=[]
 for e in net.getEdges(withInternal=False):
  for l in e.getLanes():
   pts=clip_lane(world(l.getShape()))
   if l.allows('passenger')and any(inside(p)for p in pts):lanes.append({'id':l.getID(),'way':e.getID().lstrip('-').split('#')[0],'width_m':l.getWidth(),'world_xyz':pts})
 lane_map={l['id']:i for i,l in enumerate(lanes)};write(out/'roads.json',{'schema':'RECORDED_SUMO_ROADS_V1','coordinate_frame':'glTF XYZ = ENU(x,z,-y); flatY=.26m, no surveyed road elevations','counts':{'lanes':len(lanes)},'lanes':lanes})
 poles=[];heads=[];polemap={};tlsset=set()
 for tls in net.getTrafficLights():
  for lane,_,index in tls.getConnections():
   shape=lane.getShape()
   if len(shape)<2:continue
   a,b=np.asarray(shape[-2]),np.asarray(shape[-1]);d=b-a;d/=max(np.linalg.norm(d),1e-9);p=b+np.array([-d[1],d[0]])*(lane.getWidth()/2+2.3);pw=world([p])[0]
   if not inside(pw):continue
   if lane.getID()not in polemap:polemap[lane.getID()]=len(poles);poles.append({'lane':lane.getID(),'world_xyz':pw,'height_m':3.9,'heads':0})
   pi=polemap[lane.getID()];base=poles[pi];aw,bw=world([a,b]);yaw=math.atan2(aw[0]-bw[0],aw[2]-bw[2]);hp=world([p-d*.3])[0];hp[1]+=3.3-base['heads']*.45;heads.append({'pole':pi,'tls_id':tls.getID(),'link_index':index,'world_xyz':hp,'yaw_rad':yaw});base['heads']+=1;tlsset.add(tls.getID())
 write(out/'signal_layer.json',{'claim':'Recorded simulated states; estimated stop-line pole/head placements, not surveyed traffic hardware','counts':{'tls':len(tlsset),'heads':len(heads),'poles':len(poles),'movements':0},'poles':poles,'heads':heads,'movements':[]})
 label='presentation_pose_recovery';log=(work/'sumo.log').open('w');traci.start([str(Path(sumo.SUMO_HOME)/'bin/sumo'),'-c',str((work/'run.sumocfg').resolve())],label=label,stdout=log);connection=traci.getConnection(label);records=[];counts=[];ids={};max_error=0.;changes={};previous={}
 try:
  for e in net.getEdges(withInternal=False):connection.edge.setMaxSpeed(e.getID(),e.getSpeed()*cfg['intervention']['speed_factor'])
  for eid in cfg['intervention']['closed_edges']:connection.edge.setDisallowed(eid,['passenger'])
  for k,t in enumerate(times):
   connection.simulationStep();assert abs(connection.simulation.getTime()-t)<1e-9;vehicle_ids=sorted(connection.vehicle.getIDList());xy=to_xy([connection.vehicle.getPosition(i)for i in vehicle_ids])if vehicle_ids else np.empty((0,2));keep=(abs(xy).max(1)<=2000)if len(xy)else[];visible=[i for i,yes in zip(vehicle_ids,keep)if yes];pts=xy[np.asarray(keep,dtype=bool)];ref=reference[k];assert visible==ref['ids'];error=float(np.max(abs(pts-np.asarray(ref['positions'])[:,:2])))if len(pts)else 0.;max_error=max(max_error,error);assert error<1e-6
   states={i:connection.trafficlight.getRedYellowGreenState(i)for i in original_signals['states'][k]};assert states==original_signals['states'][k]
   for key,state in states.items():
    if previous.get(key)!=state:changes.setdefault(key,[]).append([t,state]);previous[key]=state
   counts.append(len(visible))
   for vid,(x,y)in zip(visible,pts):
    ids.setdefault(vid,len(ids));angle=connection.vehicle.getAngle(vid);rad=math.radians(angle);p=np.asarray(connection.vehicle.getPosition(vid));ahead=p+np.array([math.sin(rad),math.cos(rad)]);a,b=world([p,ahead]);yaw=math.atan2(b[0]-a[0],b[2]-a[2]);speed=connection.vehicle.getSpeed(vid);records.append([ids[vid],round(x*10),round(-y*10),round(yaw*10000),round(speed*100),lane_map.get(connection.vehicle.getLaneID(vid),-1)])
 finally:connection.close();log.close()
 data=np.asarray(records,dtype=np.int64);assert data.min()>=-32768 and data.max()<=32767;(out/'replay').mkdir();data.astype('<i2').tofile(out/'replay/traffic_flow.i16');write(out/'replay/frame_counts.json',counts);write(out/'replay/times_s.json',times);write(out/'replay/tls_changes.json',{'seconds':times[-1],'samples':times,'tls':changes});write(out/'replay/id_map.json',ids)
 proof={'passed':True,'source_run':m['run_id'],'source_manifest_sha256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),'frames_verified':len(times),'position_samples_verified':len(records),'maximum_retained_position_error_m':max_error,'all_recorded_signal_states_exact':True,'coordinate_transform':'SUMO projected coordinates -> WGS84 -> same AEQD ENU -> render(x,z,-y)','binary_quantization':'positions0.1m, yaw0.0001rad,speed0.01m/s; no overflow','samples_s':[times[0],times[-1]],'no_frames_fabricated':True};write(out/'verification.json',proof)
 write(out/'replay.json',{'schema':'RECORDED_SUMO_REPLAY_V2','seconds':times[-1],'start_s':times[0],'end_s':times[-1],'sample_times':'replay/times_s.json','loop':False,'frames':len(times),'vehicles_peak':max(counts),'vehicles':len(ids),'claim':'Recorded seeded SUMO simulation, not observed traffic. Pose/lane fields recovered by exact verified deterministic rerun; original times1–600s retained. Signal hardware positions estimated from lane ends; flat display elevations.'});shutil.copy2(Path(__file__),out/'export_source.py');print(json.dumps(proof))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args();export(a.source,a.output)
