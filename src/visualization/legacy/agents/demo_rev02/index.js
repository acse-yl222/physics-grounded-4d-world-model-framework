import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';
import {batchStaticCity} from './static-batches.js';
import {createActorLayer,sumoHeadingToWorldYaw,carColorForId} from './actors/actor-layer.js';
import {addStations,addRoadSurfaces} from './stations.js';
import {createSignalLayer} from './signals.js';
import {createSignalLayerV2} from './signals-v2.js';
import {allocateHubParking} from './parking.js';
import {createFollowCamera} from './follow-camera.js';
import {installDemoCues} from './demo-cues.js';

const $=id=>document.getElementById(id);
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance',logarithmicDepthBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.25));renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;
document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#dce5eb');
scene.add(new THREE.HemisphereLight(0xdceaff,0x6b7663,2.4));
const sun=new THREE.DirectionalLight(0xfff3dd,2.5);sun.position.set(-1200,2500,1000);scene.add(sun);
const camera=new THREE.PerspectiveCamera(43,innerWidth/innerHeight,.5,15000);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=6;controls.maxDistance=6500;controls.maxPolarAngle=Math.PI*.485;
let actors,stationLayer,stations,parking,bayLibrary,routes,roadMesh,signalLayer,hubParking,replay=null,traffic=null;
let simTime=0,duration=3600,playing=false,follow=null,followCar=null,lastReal=performance.now(),lastDraw=-Infinity;
let latestUavs=[],latestCars=[],selectedData=null,selectedCarData=null;const errors=[];
let cameraDiscontinuous=false;
const stationById=new Map(),routeByKey=new Map(),parkingById=new Map(),carIdentities=new Map(),carIdByName=new Map();
const CAR_STOPPED_SPEED_MPS=0.1;
const fpsSamples=[];let lastFrame=performance.now();
const trackedCanvas=document.createElement('canvas');trackedCanvas.width=320;trackedCanvas.height=80;
const trackedTexture=new THREE.CanvasTexture(trackedCanvas);trackedTexture.colorSpace=THREE.SRGBColorSpace;
const trackedLabel=new THREE.Sprite(new THREE.SpriteMaterial({map:trackedTexture,depthTest:false,transparent:true}));trackedLabel.visible=false;trackedLabel.renderOrder=40;scene.add(trackedLabel);let trackedLabelText='';
function labelTrackedActor(text,state){
 trackedLabel.visible=!!state&&(followCar!==null?$('showCars').checked:$('showUavs').checked);if(!state)return;
 if(text!==trackedLabelText){trackedLabelText=text;const g=trackedCanvas.getContext('2d');g.clearRect(0,0,320,80);g.fillStyle='#ffffff';g.beginPath();g.roundRect(2,2,316,76,16);g.fill();g.strokeStyle='#0c7eab';g.lineWidth=4;g.stroke();g.fillStyle='#075e83';g.font='bold 29px system-ui';g.textAlign='center';g.fillText(text,160,52);trackedTexture.needsUpdate=true;}
 trackedLabel.position.set(state.x,state.y+(followCar!==null?2.8:2.2),state.z);
}

const markerGeometry=new THREE.BufferGeometry();markerGeometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(300*3),3));
markerGeometry.setAttribute('color',new THREE.BufferAttribute(new Float32Array(300*4),4));
const uavMarkers=new THREE.Points(markerGeometry,new THREE.PointsMaterial({size:3.5,sizeAttenuation:false,vertexColors:true,depthTest:false,depthWrite:false,transparent:true}));uavMarkers.frustumCulled=false;uavMarkers.renderOrder=20;scene.add(uavMarkers);
window.demoState={stage:'loading',errors,hasValidatedUavReplay:false,hasValidatedTrafficReplay:false};
const followCamera=createFollowCamera({camera,controls,onModeChange:mode=>{for(const m of ['orbit','behind'])$(m+'Follow').classList.toggle('active',m===mode);}});
function goView(kind){
 follow=null;followCar=null;selectedData=null;selectedCarData=null;followCamera.clear();trackedLabel.visible=false;$('follow').value='';$('carId').value='';$('detail').style.display='none';$('followModes').style.display='none';
 const centre=new THREE.Vector3(210,0,0);
 if(kind==='campus'){controls.target.set(740,18,400);camera.position.set(1050,460,940);}
 else {controls.target.copy(centre);camera.position.copy(centre).add(kind==='top'?new THREE.Vector3(0,4000,.01):new THREE.Vector3(1800,2200,2450));}
 for(const id of ['overview','campus','top','trafficView'])$(id).classList.toggle('active',id===kind);controls.update();
}
goView('overview');
function timeString(seconds){const t=Math.max(0,Math.floor(seconds));return `${String(Math.floor(t/60)).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`;}
function activityLabel(kind){return {HOLD:'Parked',RETURN_TO_HUB:'Returning to Hub',INFLIGHT_TO_C:'Flying to collection',INFLIGHT_C_TO_D:'Delivering',WAIT_PRE_C:'Waiting for collection',WINDOW_WAIT:'Waiting for delivery time',WAIT_AT_HUB:'Waiting at Hub',BATTERY_SWAP:'Swapping battery',C_SERVICE:'Collecting',D_SERVICE:'Delivering'}[kind]??kind.replaceAll('_',' ').toLowerCase();}
async function readJSON(url,optional=false){const r=await fetch(url);if(!r.ok){if(optional&&r.status===404)return null;throw new Error(`${url}: ${r.status}`);}return r.json();}
function routePoints(from,to,owner,segment){
 const key=Math.min(from,to)+'-'+Math.max(from,to);const route=routeByKey.get(key);if(!route)throw new Error(`Missing flight path ${from}→${to}`);
 let points=route.points_m.map(p=>p.slice());if(from>to)points.reverse();
 const h=points[1][1];
 // Keep the validated centreline; add only certified short bay-to-centre links.
 if(stationById.get(from).role==='hub'){
  const centre=stationById.get(from),base=parkingById.get(owner),offset=segment?._departureOffset??base.offset_from_station_m;
  const bay=[centre.x_m+offset[0],centre.y_m,centre.z_m+offset[2]];
  points=[bay,[bay[0],h,bay[2]],...points.slice(1)];
 }
 if(stationById.get(to).role==='hub'){
  const centre=stationById.get(to),base=parkingById.get(owner),offset=segment?._arrivalOffset??base.offset_from_station_m;
  const bay=[centre.x_m+offset[0],centre.y_m,centre.z_m+offset[2]];
  points=[...points.slice(0,-1),[bay[0],h,bay[2]],bay];
 }
 const lengths=[];let total=0;for(let i=1;i<points.length;i++){total+=Math.hypot(...points[i].map((x,k)=>x-points[i-1][k]));lengths.push(total);}
 if(total>route.route_length_bound_m+1e-5)throw new Error('Owner path exceeds scheduling distance bound');
 return {points,lengths,total};
}
function pointAlong(path,fraction){
 const distance=Math.min(1,Math.max(0,fraction))*path.total;let i=path.lengths.findIndex(d=>d>=distance);if(i<0)i=path.points.length-2;
 const previous=i?path.lengths[i-1]:0,length=path.lengths[i]-previous,ratio=length>1e-8?(distance-previous)/length:0;
 const a=path.points[i],b=path.points[i+1];return {x:a[0]+(b[0]-a[0])*ratio,y:a[1]+(b[1]-a[1])*ratio,z:a[2]+(b[2]-a[2])*ratio,headingRadians:Math.atan2(b[0]-a[0],b[2]-a[2])};
}
function stationaryPose(stationId,owner,t=0){
 const s=stationById.get(stationId),p={x:s.x_m,y:s.y_m,z:s.z_m,headingRadians:0};
 if(s.role==='hub'){const off=hubParking?.offset(owner,stationId,t)??parkingById.get(owner).offset_from_station_m;p.x+=off[0];p.z+=off[2];}
 return p;
}
function initialiseReplay(data){
 if(data.audit?.status!=='PASS'||data.audit.unique_deliveries!==600||data.audit.continuous_timelines!==300)throw new Error('UAV replay has not passed its release gate');
 hubParking=allocateHubParking(data,stations,parking,bayLibrary);window.demoState.parking=hubParking.audit;
 if(hubParking.audit.overflow_stays)throw new Error('Hub parking exceeds the individually validated display allocation');
 for(const u of data.uavs)for(const seg of u.segments)if(seg.from_station!==seg.to_station){seg._path=routePoints(seg.from_station,seg.to_station,u.id,seg);if(seg._path.total/(seg.t1_s-seg.t0_s)>15.00001)throw new Error('UAV display path exceeds flight speed bound');}
 replay=data;duration=data.metadata.duration_s;window.demoState.hasValidatedUavReplay=true;
 $('scrub').max=duration;$('duration').textContent=timeString(duration);
}
function getUavStates(t){
 if(!replay)return parking.map(p=>({idIndex:p.uav_id,x:p.position_m[0],y:p.position_m[1],z:p.position_m[2],headingRadians:0,activity:'Parked',soc:75,airborne:false,station:p.hub_station_id}));
 return replay.uavs.map(u=>{
  const seg=u.segments.find(s=>t>=s.t0_s&&t<s.t1_s)??u.segments[u.segments.length-1];
  if(!seg)return {idIndex:u.id,...stationaryPose(u.birth_station,u.id),activity:'Parked',soc:75,airborne:false,station:u.birth_station};
  const fraction=Math.min(1,Math.max(0,(t-seg.t0_s)/Math.max(1e-8,seg.t1_s-seg.t0_s))),airborne=!!seg._path;
  const pose=airborne?pointAlong(seg._path,fraction):stationaryPose(seg.from_station,u.id,t);
  const swap=seg.kind.includes('SWAP');const soc=swap?(fraction<1?seg.soc0:seg.soc1):seg.soc0+(seg.soc1-seg.soc0)*fraction;
  // Display-only fading at the original landing/departure times. No ledger field changes.
  const dockedHidden=!airborne&&hubParking.isReturnedStay(u.id,seg.from_station,t);
  const fadeSeconds=Math.min(1.2,(seg.t1_s-seg.t0_s)/2);
  let opacity=dockedHidden?0:1;
  if(airborne&&fadeSeconds>0){
   if(seg._fadeIntoHub)opacity=Math.min(opacity,Math.max(0,(seg.t1_s-t)/fadeSeconds));
   if(seg._fadeOutOfHub)opacity=Math.min(opacity,Math.max(0,(t-seg.t0_s)/fadeSeconds));
  }
  return {idIndex:u.id,...pose,activity:seg.display_kind??seg.kind,order_id:seg.order_id,soc,airborne,station:airborne?null:seg.from_station,color:swap?'#2563eb':(seg.payload0?'#f2924b':'#ffffff'),opacity,visible:!dockedHidden,hubDockedHidden:dockedHidden};
 });
}
function sampleSparseTraffic(t){
 if(!traffic||t<traffic.firstTime||t>traffic.lastTime)return [];
 const index=Math.floor(t)-traffic.firstTime,a=traffic.frames[index],b=traffic.frames[index+1],fraction=t-Math.floor(t);
 if(!a)return [];
 function frameMap(frame){const m=new Map();if(!frame)return m;const offset=frame.offset_bytes/4;for(let i=0;i<frame.count;i++){const k=offset+i*5;m.set(traffic.binary[k],traffic.binary.subarray(k+1,k+5));}return m;}
 const current=frameMap(a),next=fraction>0?frameMap(b):new Map(),records=[];
 for(const [id,v] of current){
  const w=next.get(id);let x=v[0],y=v[1],angle=v[2],speed=v[3];
  if(w){x+=(w[0]-x)*fraction;y+=(w[1]-y)*fraction;let delta=((w[2]-angle+540)%360)-180;angle+=delta*fraction;speed+=(w[3]-speed)*fraction;}
  records.push({nativeId:id,x:x-2912.594719173,y:.275,z:1704.705026026-y,headingRadians:sumoHeadingToWorldYaw(angle*Math.PI/180),speed,color:carColorForId(id)});
 }
 // A render slot is not a vehicle identity. Map the current frame in stable ID order.
 records.sort((a,b)=>a.nativeId-b.nativeId);records.forEach((r,i)=>r.idIndex=i);return records;
}
async function loadTraffic(){
 const manifest=await readJSON('/data/traffic/current_replay.json',true);if(!manifest)return;
 if(manifest.status!=='PASS'||manifest.format!=='uwm-traffic-sparse-flow-v2')throw new Error('Traffic replay has not passed its release gate');
 const base=new URL(manifest.base_url,location.href);
 const [frames,buffer]=await Promise.all([readJSON(new URL('frames_index.json',base)),fetch(new URL('traffic_flow.f32',base)).then(r=>{if(!r.ok)throw new Error('Traffic binary unavailable');return r.arrayBuffer();})]);
 traffic={frames:Array.isArray(frames)?frames:frames.frames,binary:new Float32Array(buffer),manifest};
 const identities=await readJSON(new URL('actors.json',base));
 for(const [key,item] of Object.entries(identities)){const id=Number(key);carIdentities.set(id,item);carIdByName.set(item.native_id,id);}
 traffic.firstTime=traffic.frames[0].t_s;traffic.lastTime=traffic.frames[traffic.frames.length-1].t_s;
 const maximum=Math.max(...traffic.frames.map(f=>f.count));if(maximum>actors.cars.capacity)throw new Error(`Traffic capacity ${maximum} exceeds rendered actor allocation`);
 const [movementGeometry,tlsResponse]=await Promise.all([readJSON(new URL(manifest.signal_layer_v2_url??manifest.signal_geometry_url??'/data/traffic/city_signal_movements_v1.json',location.href)),fetch(new URL('tls_frames.jsonl',base))]);
 if(!tlsResponse.ok)throw new Error('Recorded traffic signal states unavailable');
 const tlsFrames=(await tlsResponse.text()).trim().split('\n').filter(Boolean).map(line=>JSON.parse(line));
 signalLayer=manifest.signal_layer_v2_url?createSignalLayerV2(scene,movementGeometry,tlsFrames):createSignalLayer(scene,movementGeometry,tlsFrames);
 window.demoState.signals=signalLayer.stats??{movements:signalLayer.movements.length};
 window.demoState.hasValidatedTrafficReplay=true;
}
function refreshLabels(){
 $('replayNote').textContent=replay?(traffic?'Revision 02: NVMF deliveries (staggered take-off display), SUMO traffic on the repaired lane network and simulated signal heads. Aircraft fade out while docked at Hubs.':'NVMF delivery replay ready. Road traffic is being validated.'):'Initial fleet layout. NVMF scheduling is running; no delivery result is shown yet.';
}
function renderReplay(t){
 latestUavs=getUavStates(t);latestCars=sampleSparseTraffic(t);
 // Keep all individual ledger states; aggregate stationary rooftop aircraft only
 // in the rendered layer so multiple final tails do not draw overlapping models.
 const roofSeen=new Set(),roofCounts=new Map(),groundCounts=new Map();
 for(const u of latestUavs)if(!u.airborne)groundCounts.set(u.station,(groundCounts.get(u.station)??0)+1);
 stationLayer?.setGroundCounts(groundCounts);
 for(const u of latestUavs)if(!u.airborne&&stationById.get(u.station)?.role!=='hub')roofCounts.set(u.station,(roofCounts.get(u.station)??0)+1);
 const displayed=latestUavs.map(u=>{
  if(u.airborne||stationById.get(u.station)?.role==='hub')return u;
  const show=u.idIndex===follow||(!roofSeen.has(u.station)&&!latestUavs.some(v=>v.idIndex===follow&&!v.airborne&&v.station===u.station));
  if(show)roofSeen.add(u.station);return {...u,visible:show};
 });
 actors.updateUavs(displayed);actors.updateCars(latestCars);signalLayer?.update(t);
 window.demoState.stationary_rooftop_counts=Object.fromEntries(roofCounts);
 const pos=markerGeometry.attributes.position,color=markerGeometry.attributes.color,c=new THREE.Color();
 displayed.forEach((u,i)=>{pos.setXYZ(i,u.x,u.y+1,u.z);c.set(u.airborne?(u.color==='#f2924b'?'#dd7626':'#1a6977'):'#586877');color.setXYZW(i,c.r,c.g,c.b,u.visible===false?0:u.opacity??1);});pos.needsUpdate=true;color.needsUpdate=true;
 const done=replay?replay.deliveries.filter(d=>d.dropoff_s<=t).length:0;
 const movingCars=latestCars.filter(c=>c.speed>CAR_STOPPED_SPEED_MPS).length,stoppedCars=latestCars.length-movingCars;
 $('carBreakdown').textContent=traffic?`${movingCars.toLocaleString()} moving · ${stoppedCars.toLocaleString()} stopped`:'';
 $('served').textContent=done;$('servedBar').style.width=(done/600*100)+'%';$('airborne').textContent=latestUavs.filter(u=>u.airborne).length;$('cars').textContent=traffic?latestCars.length:'—';
 if(follow!==null){
  selectedData=latestUavs.find(u=>u.idIndex===follow);if(selectedData){
   $('activity').textContent=activityLabel(selectedData.activity);$('soc').textContent=Math.max(0,selectedData.soc).toFixed(0)+' / 75';
   $('uavServed').textContent=(replay?replay.deliveries.filter(d=>d.uav_id===follow&&d.dropoff_s<=t).length:0)+' requests';
  }
 }
 if(followCar!==null){
  selectedCarData=latestCars.find(c=>c.nativeId===followCar)??null;
  const identity=carIdentities.get(followCar);
  $('activity').textContent=selectedCarData?(selectedCarData.speed<=CAR_STOPPED_SPEED_MPS?'Stopped':'Driving'):(identity?.arrival_s!=null&&t>=identity.arrival_s?'Left the road network':'Not on the road at this time');
  $('carSpeed').textContent=selectedCarData?(selectedCarData.speed*2.236936292).toFixed(1)+' mph':'—';
 }

 labelTrackedActor(follow!==null?`UAV ${String(follow+1).padStart(3,'0')}`:carIdentities.get(followCar)?.native_id??'',follow!==null?selectedData:followCar!==null?selectedCarData:null);
 $('time').textContent=timeString(t);$('scrub').value=t;
 window.demoState={...window.demoState,time_s:t,served:done,activeCars:latestCars.length,movingCars,stoppedCars,airborne:latestUavs.filter(u=>u.airborne).length,hiddenAtHub:latestUavs.filter(u=>u.hubDockedHidden).length,followedUav:follow,followedCar:followCar,selectedAircraft:selectedData?{...selectedData}:null};
}
try{
 [stations,parking,routes,bayLibrary]=await Promise.all([readJSON('/data/stations.json'),readJSON('/data/parking.json'),readJSON('/data/routes.json'),readJSON('/data/hub-bays.json')]);
 parking=parking.parking;stations.forEach(s=>stationById.set(s.station_id,s));parking.forEach(p=>parkingById.set(p.uav_id,p));routes.routes.forEach(r=>routeByKey.set(r.from_station+'-'+r.to_station,r));
 const loader=new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
 const city=await loader.loadAsync('/assets/city.glb',p=>{if(p.total)$('status').textContent=`Loading the city… ${Math.round(p.loaded/p.total*100)}%`;});
 // revision_02: original GLB is untouched; this is a display filter. Earlier-animation cars (layer traffic_vehicle),
 // prediction and bird layers stay hidden. Aerial-photo parked vehicles are shown unless they sit on a drivable lane.
 const staticFilter=await readJSON('/data/static-vehicle-filter.json',true);
 // GLTFLoader sanitises node names (whitespace -> '_', [].:/ removed, duplicates get _2, _3 ...; multi-primitive
 // meshes get children named <node>_<i>), so the filter names are compared after the same sanitisation.
 const sanitiseName=n=>n.replace(/\s/g,'_').replace(/[\[\]\.:\/]/g,'');
 const parkedShow=new Set((staticFilter?.aerial_vehicles??[]).filter(a=>a.show).map(a=>sanitiseName(a.name)));
 const parkedAllowed=n=>parkedShow.has(n)||parkedShow.has(n.replace(/_\d+$/,''));
 const parkedNodes=[];
 city.scene.traverse(o=>{
  if(['traffic_vehicle','traffic_prediction','bird'].includes(o.userData.layer))o.visible=false;
  if(o.name.startsWith('AERIAL-VEHICLE')){parkedNodes.push(o);const allowed=staticFilter?parkedAllowed(o.name):false;o.visible=allowed;o.userData.parkedAllowed=allowed;}
 });
 window.demoState.staticVehicles={aerial:parkedNodes.length,shown:parkedNodes.filter(o=>o.visible).length,filter:staticFilter?.rule??null};
 $('showParked').onchange=()=>{for(const o of parkedNodes)o.visible=$('showParked').checked&&o.userData.parkedAllowed;};
 scene.add(city.scene);$('status').textContent='Preparing buildings and city details…';
 const batches=await batchStaticCity(city.scene);scene.add(batches.object);
 $('status').textContent='Placing stations and vehicles…';
 actors=await createActorLayer({scene,carCapacity:1800,uavCapacity:300});
 stationLayer=addStations(scene,stations,parking);
 const roadGeometry=await readJSON('/data/roads.json');roadMesh=addRoadSurfaces(scene,roadGeometry);
 for(let u=0;u<300;u++){const option=document.createElement('option');option.value=u;option.textContent=`UAV ${String(u+1).padStart(3,'0')}`;$('follow').append(option);}
 const schedule=await readJSON('/data/schedule.json',true);if(schedule){
  initialiseReplay(schedule);
  window.demoState.uavTimeline=schedule.metadata?.demo_timeline??'original';
  const alternate=await readJSON('/data/schedule_original.json',true);
  if(alternate){
   $('uavTimeline').style.display='block';
   $('uavTimeline').onchange=()=>{const useOriginal=$('uavTimeline').value==='original';initialiseReplay(useOriginal?alternate:schedule);window.demoState.uavTimeline=useOriginal?'original':(schedule.metadata?.demo_timeline??'staggered');renderReplay(simTime);};
  }
  const cues=await readJSON('/data/uav-cues.json');
  installDemoCues({element:$('demoCue'),cues,replay,onChoose:entry=>{
   playing=false;$('play').textContent='▶';$('speed').value='1';goView('overview');window.seekDemo(entry.time_s);
   if(entry.uav_id!==undefined){$('follow').value=String(entry.uav_id);$('follow').dispatchEvent(new Event('change'));}
  }});
 }
 await loadTraffic();if(traffic)simTime=traffic.firstTime;refreshLabels();renderReplay(simTime);window.demoState.stage='ready';$('loading').style.display='none';
}catch(error){errors.push(String(error));window.demoState.stage='error';$('status').textContent=String(error);console.error(error);}

$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'❚❚':'▶';};
$('scrub').oninput=()=>{simTime=Number($('scrub').value);cameraDiscontinuous=true;if(actors)renderReplay(simTime);};
for(const id of ['overview','campus','top'])$(id).onclick=()=>goView(id);
$('showCars').onchange=()=>{actors?.setVisible({cars:$('showCars').checked});if(actors)renderReplay(simTime);};$('showUavs').onchange=()=>{actors?.setVisible({uavs:$('showUavs').checked});if(actors)renderReplay(simTime);};
$('showSignals').onchange=()=>signalLayer?.setVisible($('showSignals').checked&&!!traffic);
$('showStations').onchange=()=>stationLayer?.setVisible($('showStations').checked);$('showCoverage').onchange=()=>stationLayer?.setCoverage($('showCoverage').checked);
function showTrackedDetails(kind,title){
 $('detail').style.display='block';$('followModes').style.display='flex';$('detailTitle').textContent=title;
 $('detailEyebrow').textContent=kind==='car'?'Vehicle activity':'Aircraft activity';
 $('completedRow').style.display=kind==='car'?'none':'flex';$('batteryRow').style.display=kind==='car'?'none':'flex';$('carSpeedRow').style.display=kind==='car'?'flex':'none';
 $('detailNote').textContent=kind==='car'?'The camera follows this recorded vehicle ID. Traffic and signal timings are simulated.':'Aircraft fade out while docked at a Hub; their activity and battery remain visible here. Roof parking is grouped.';
 for(const id of ['overview','campus','top','trafficView'])$(id).classList.remove('active');
}
$('follow').onchange=()=>{
 follow=$('follow').value===''?null:Number($('follow').value);followCar=null;selectedCarData=null;$('carId').value='';
 if(follow===null){followCamera.clear();$('detail').style.display='none';$('followModes').style.display='none';return;}
 showTrackedDetails('uav',`UAV ${String(follow+1).padStart(3,'0')}`);if(actors)renderReplay(simTime);
 followCamera.select({kind:'uav',id:follow},selectedData);followCamera.setMode('behind');
};
function populateCarIds(){
 const fragment=document.createDocumentFragment();for(const c of latestCars){const option=document.createElement('option');option.value=carIdentities.get(c.nativeId)?.native_id??String(c.nativeId);fragment.append(option);}$('carIds').replaceChildren(fragment);
}
$('carId').onfocus=populateCarIds;
function followChosenCar(){
 const text=$('carId').value.trim(),id=text?(carIdByName.get(text)??(carIdentities.has(Number(text))?Number(text):undefined)):undefined;
 if(id===undefined){$('toast').textContent=traffic?'Choose a recorded car ID from the list.':'Vehicle IDs will be available when the traffic replay is ready.';$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',3500);return;}
 follow=null;selectedData=null;$('follow').value='';followCar=id;$('carId').value=carIdentities.get(id).native_id;
 showTrackedDetails('car',carIdentities.get(id).native_id);renderReplay(simTime);followCamera.select({kind:'car',id},selectedCarData);followCamera.setMode('behind');
}
$('carFollow').onclick=followChosenCar;$('carId').onkeydown=e=>{if(e.key==='Enter')followChosenCar();};
$('orbitFollow').onclick=()=>followCamera.setMode('orbit');$('behindFollow').onclick=()=>followCamera.setMode('behind');
$('trafficView').onclick=()=>{
 follow=null;followCar=null;selectedData=null;selectedCarData=null;followCamera.clear();trackedLabel.visible=false;$('follow').value='';$('carId').value='';$('detail').style.display='none';$('followModes').style.display='none';
 $('speed').value='1';
 const candidates=signalLayer?.movements??[];
 let selected=null,best=-1;
 for(const m of candidates){const p=m.world_stop_point_xyz;const near=latestCars.filter(c=>Math.hypot(c.x-p[0],c.z-p[2])<55).length;if(near>best){best=near;selected=p;}}
 const p=selected??[740,0,400];controls.target.set(p[0],1,p[2]);camera.position.set(p[0]+45,50,p[2]+50);controls.update();
 for(const id of ['overview','campus','top','trafficView'])$(id).classList.toggle('active',id==='trafficView');
};
window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
window.seekDemo=t=>{simTime=Math.max(0,Math.min(duration,t));cameraDiscontinuous=true;renderReplay(simTime);};
window.setDemoView=goView;
function animate(){
 requestAnimationFrame(animate);const now=performance.now(),delta=Math.min(.2,(now-lastReal)/1000);lastReal=now;
 if(playing&&actors){simTime=Math.min(duration,simTime+delta*Number($('speed').value));if(simTime>=duration){playing=false;$('play').textContent='▶';}}
 if(actors&&((playing&&now-lastDraw>=35)||lastDraw===-Infinity)){renderReplay(simTime);lastDraw=now;}
 if(follow!==null||followCar!==null)followCamera.update(follow!==null?selectedData:selectedCarData,delta,{discontinuous:cameraDiscontinuous});cameraDiscontinuous=false;
 controls.update();renderer.render(scene,camera);fpsSamples.push(now-lastFrame);lastFrame=now;if(fpsSamples.length>120)fpsSamples.shift();
 if(stationLayer)for(const sprite of stationLayer.labels.children){const metresPerPixel=2*camera.position.distanceTo(sprite.position)*Math.tan(camera.fov*Math.PI/360)/innerHeight;sprite.scale.set(48*metresPerPixel,48/(sprite.userData.aspect??(48/22))*metresPerPixel,1);}
 if(trackedLabel.visible){const mpp=2*camera.position.distanceTo(trackedLabel.position)*Math.tan(camera.fov*Math.PI/360)/innerHeight;trackedLabel.scale.set(136*mpp,34*mpp,1);}
 uavMarkers.visible=$('showUavs').checked&&camera.position.distanceTo(controls.target)>200;
 window.demoState.render={calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,meanFrameMs:fpsSamples.reduce((a,b)=>a+b,0)/fpsSamples.length};
}
animate();
