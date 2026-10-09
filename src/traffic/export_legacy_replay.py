"""Verified SUMO replay adapter for the shared legacy city viewer.
Re-simulates immutable retained inputs solely to recover missing pose/lane records,
requiring exact retained positions and signal states at every recorded time.
"""
from pathlib import Path
import argparse,json,math,shutil,hashlib,array
import numpy as np
import sumo,sumolib,traci
from traffic.sumo_pipeline import lonlat_to_scene, clip_segment

def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,separators=(',',':')))
def clip_lane(points,bounds=None):
 bounds=bounds or {"min":[-2000,-2000],"max":[2000,2000]}
 groups=[];current=[]
 for a,b in zip(points,points[1:]):
  pair=clip_segment([a[0],a[2]],[b[0],b[2]],bounds)
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
 source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=False);work=out/'verification_rerun';work.mkdir();read=lambda p:json.loads(p.read_text());cfg=read(source/'config.json');m=read(source/'manifest.json');times=m['time']['samples'];bounds=m['spatial']['bounds_m'];render_bounds={'min':[bounds['min'][0],-bounds['max'][1]],'max':[bounds['max'][0],-bounds['min'][1]]};reference=read(source/'trajectories.json')['frames'];original_signals=read(source/'signals.json');net=sumolib.net.readNet(str(source/'network.net.xml'),withInternal=True);offset=np.asarray(net.getLocationOffset());proj=net.getGeoProj()
 for name in ['network.net.xml','routes.rou.xml','run.sumocfg']:shutil.copy2(source/name,work/name)
 from pyproj import Transformer
 tf=cfg['transform'];projector=Transformer.from_crs('EPSG:4326',tf['crs'],always_xy=True)if tf.get('kind')in('aeqd','projected_affine')else None
 def to_xy(points):
  points=np.asarray(points)-offset;lon,lat=proj(points[:,0],points[:,1],inverse=True);
  if projector is None:return lonlat_to_scene(np.column_stack([lon,lat]),tf)
  xy=np.column_stack(projector.transform(lon,lat));return xy @ np.asarray(tf['matrix']).T + tf['offset'] if tf.get('kind')=='projected_affine'else xy
 def world(points):return [[float(x),.26,float(-y)]for x,y in to_xy(points)]
 def inside(p):return render_bounds['min'][0]<=p[0]<=render_bounds['max'][0] and render_bounds['min'][1]<=p[2]<=render_bounds['max'][1]
 lanes=[]
 for e in net.getEdges(withInternal=False):
  for l in e.getLanes():
   pts=clip_lane(world(l.getShape()),render_bounds)
   if (l.allows('passenger')or e.getID()in cfg.get('conservative_closures',{}).get('edge_ids',[]))and any(inside(p)for p in pts):lanes.append({'id':l.getID(),'way':e.getID().lstrip('-').split('#')[0],'width_m':l.getWidth(),'world_xyz':pts})
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
 label='presentation_pose_recovery';log=(work/'sumo.log').open('w');traci.start([str(Path(sumo.SUMO_HOME)/'bin/sumo'),'-c',str((work/'run.sumocfg').resolve())],label=label,stdout=log);connection=traci.getConnection(label);records=[];f32=array.array('f');counts=[];ids={};subscribed=set();max_error=0.;changes={};previous={};moving_counts=[]
 try:
  for e in net.getEdges(withInternal=False):connection.edge.setMaxSpeed(e.getID(),e.getSpeed()*cfg['intervention']['speed_factor'])
  for eid in cfg['intervention']['closed_edges']:connection.edge.setDisallowed(eid,['passenger'])
  for k,t in enumerate(times):
   connection.simulationStep(t);assert abs(connection.simulation.getTime()-t)<1e-9;vehicle_ids=sorted(connection.vehicle.getIDList())
   for vid in set(vehicle_ids)-subscribed:connection.vehicle.subscribe(vid,[traci.constants.VAR_POSITION,traci.constants.VAR_ANGLE,traci.constants.VAR_SPEED,traci.constants.VAR_LANE_ID]);subscribed.add(vid)
   states_vehicle=connection.vehicle.getAllSubscriptionResults()
   xy=to_xy([states_vehicle[i][traci.constants.VAR_POSITION]for i in vehicle_ids])if vehicle_ids else np.empty((0,2));keep=((xy[:,0]>=bounds['min'][0])&(xy[:,0]<=bounds['max'][0])&(xy[:,1]>=bounds['min'][1])&(xy[:,1]<=bounds['max'][1]))if len(xy)else[];visible=[i for i,yes in zip(vehicle_ids,keep)if yes];pts=xy[np.asarray(keep,dtype=bool)];ref=reference[k];assert visible==ref['ids'];error=float(np.max(abs(pts-np.asarray(ref['positions'])[:,:2])))if len(pts)else 0.;max_error=max(max_error,error);assert error<1e-6
   states={i:connection.trafficlight.getRedYellowGreenState(i)for i in original_signals['states'][k]};assert states==original_signals['states'][k]
   for key,state in states.items():
    if previous.get(key)!=state:changes.setdefault(key,[]).append([t,state]);previous[key]=state
   counts.append(len(visible));moving_counts.append(sum(states_vehicle[i][traci.constants.VAR_SPEED]>.1 for i in visible))
   for vid,(x,y)in zip(visible,pts):
    ids.setdefault(vid,len(ids));angle=states_vehicle[vid][traci.constants.VAR_ANGLE];rad=math.radians(angle);p=np.asarray(states_vehicle[vid][traci.constants.VAR_POSITION]);ahead=p+np.array([math.sin(rad),math.cos(rad)]);a,b=world([p,ahead]);yaw=math.atan2(b[0]-a[0],b[2]-a[2]);speed=states_vehicle[vid][traci.constants.VAR_SPEED];f32.extend([ids[vid],x+2912.594719173,1704.705026026+y,(math.pi-yaw)*180/math.pi,speed])if m['scene_id']=='south_ken'else None;records.append([ids[vid],round(x*10),round(-y*10),round(yaw*10000),round(speed*100),lane_map.get(states_vehicle[vid][traci.constants.VAR_LANE_ID],-1)])
 finally:connection.close();log.close()
 data=np.asarray(records,dtype=np.int64);assert data.min()>=-32768 and data.max()<=32767;(out/'replay').mkdir();data.astype('<i2').tofile(out/'replay/traffic_flow.i16');write(out/'replay/frame_counts.json',counts);write(out/'replay/times_s.json',times);write(out/'replay/tls_changes.json',{'seconds':times[-1],'samples':times,'tls':changes});write(out/'replay/id_map.json',ids)
 if m['scene_id']=='south_ken':
  with (out/'replay/traffic_flow.f32').open('wb')as stream:f32.tofile(stream)
  offset=0;index=[]
  for t,count in zip(times,counts):index.append({'t_s':t,'offset_bytes':offset,'count':count});offset+=count*20
  write(out/'replay/frames_index.json',index);write(out/'replay/actors.json',{'ids':ids,'note':'Numeric actor IDs map to actual SUMO vehicles; f32 X=xENU+2912.594719173,Y=1704.705026026+yENU'})
  with (out/'replay/tls_frames.jsonl').open('w')as stream:
   for t,states in zip(times,original_signals['states']):stream.write(json.dumps({'t':t,'states':states})+'\n')
  shutil.copy2(out/'signal_layer.json',out/'signal_layer_v2.json')
 proof={'passed':True,'source_run':m['run_id'],'source_manifest_sha256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),'frames_verified':len(times),'position_samples_verified':len(records),'maximum_retained_position_error_m':max_error,'all_recorded_signal_states_exact':True,'coordinate_transform':'SUMO projected coordinates -> WGS84 -> retained configured local ENU transform -> render(x,z,-y)','binary_quantization':'positions0.1m, yaw0.0001rad,speed0.01m/s; no overflow','samples_s':[times[0],times[-1]],'no_frames_fabricated':True,'visible_and_moving':{str(t):{'visible':counts[k],'moving_over_0_1_m_s':moving_counts[k]}for k,t in enumerate(times)if t in(300,600,times[-1])},'peak_moving':max(moving_counts)};write(out/'verification.json',proof)
 write(out/'replay.json',{'schema':'RECORDED_SUMO_REPLAY_V2','seconds':times[-1],'start_s':times[0],'end_s':times[-1],'sample_times':'replay/times_s.json','loop':False,'frames':len(times),'vehicles_peak':max(counts),'vehicles':len(ids),'claim':'Recorded seeded SUMO simulation, not observed traffic. Pose/lane fields recovered by exact verified deterministic rerun; all original recorded times retained. Signal hardware positions estimated from lane ends; flat display elevations.'});shutil.copy2(out/'replay.json',out/'current_replay.json');shutil.copy2(Path(__file__),out/'export_source.py');print(json.dumps(proof))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args();export(a.source,a.output)
