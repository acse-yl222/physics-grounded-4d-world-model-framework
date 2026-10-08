import * as THREE from 'three';
import {createTimeline} from './timeline.mjs';
// Display-only rotor kinematics. TSR=7 is assumed, not turbine controller data.
// Phase advances at 1/12.5 of the accelerated simulation timeline for readable motion.
export function buildRotors(model,scene,meta,history,kinematics=null){
 if(meta.rotor_model==='actuator_line')return buildActuatorLines(model,scene,meta,kinematics);
 const timeline=createTimeline(meta.times);
 if(history.length!==meta.times.length||history.some(row=>!Array.isArray(row)||row.length!==meta.turbines.length||row.some(v=>!Number.isFinite(v))))throw Error('Rotor history does not match saved wind-frame times and turbines');
 model.updateMatrixWorld(true);const rotors=[];
 for(let k=0;k<meta.turbines.length;k++){
  const t=meta.turbines[k],parts=[],blades=[];
  model.traverse(o=>{if(!o.isMesh||o.userData.building_id!==t.id)return;const name=o.userData.semantic_id||o.name;if(/blade/.test(name)){parts.push(o);blades.push(o);}else if(/rotor.hub.and.spinner/.test(name))parts.push(o);});
  if(blades.length!==3)throw Error(`Expected three blades for ${t.id}; found ${blades.length}`);
  const centers=blades.map(b=>new THREE.Box3().setFromObject(b).getCenter(new THREE.Vector3()));
  const axis=centers[1].clone().sub(centers[0]).cross(centers[2].clone().sub(centers[0])).normalize();if(axis.x<0)axis.negate();
  const group=new THREE.Group();group.position.set(t.hub_xyz_m[0],t.hub_xyz_m[2],-t.hub_xyz_m[1]);scene.add(group);group.updateMatrixWorld(true);parts.forEach(p=>group.attach(p));
  const omega=history.map(r=>7*Math.max(0,r[k])/t.radius_m),phase=[0];for(let i=1;i<omega.length;i++)phase.push(phase[i-1]+.5*(omega[i-1]+omega[i])*(meta.times[i]-meta.times[i-1])/12.5);
  rotors.push({id:t.id,group,axis,phase,omega,partCount:parts.length});
 }
 return {rotors,update(t,enabled=true){const {a,b,mix:f}=timeline.sample(t);for(const r of rotors)r.group.quaternion.setFromAxisAngle(r.axis,enabled?r.phase[a]*(1-f)+r.phase[b]*f:0);const rpm=rotors.map(r=>(r.omega[a]*(1-f)+r.omega[b]*f)*60/(2*Math.PI));return [Math.min(...rpm),Math.max(...rpm)];}};
}


function buildActuatorLines(model,scene,meta,data){
 const timeline=createTimeline(meta.times),count=meta.turbines.length;
 if(!data||data.times.length!==meta.times.length||data.times.some((t,i)=>t!==meta.times[i])||data.phase_rad.length!==meta.times.length||data.omega_rad_s.length!==meta.times.length)throw Error('Missing recorded actuator-line kinematics');
 for(const rows of [data.phase_rad,data.omega_rad_s])if(rows.some(row=>row.length!==count||row.some(v=>!Number.isFinite(v))))throw Error('Invalid recorded rotor state');
 const removed=[];model.traverse(o=>{if(o.isMesh&&/blade/.test(o.userData.semantic_id||o.name))removed.push(o);});removed.forEach(o=>o.removeFromParent());
 const enu=a=>new THREE.Vector3(a[0],a[2],-a[1]);
 const rotors=meta.turbines.map((t,k)=>{
  const axis=enu(t.normal_xyz).normalize(),e1=enu(data.basis_e1_xyz[k]).normalize(),e2=new THREE.Vector3().crossVectors(axis,e1),group=new THREE.Group();group.position.copy(enu(t.hub_xyz_m));scene.add(group);
  const root=t.radius_m*data.root_radius_fraction;
  for(let b=0;b<3;b++){
   const direction=e1.clone().multiplyScalar(Math.cos(b*2*Math.PI/3)).addScaledVector(e2,Math.sin(b*2*Math.PI/3));
   const geometry=new THREE.BufferGeometry().setFromPoints([direction.clone().multiplyScalar(root),direction.clone().multiplyScalar(t.radius_m)]);
   group.add(new THREE.Line(geometry,new THREE.LineBasicMaterial({color:0xffd166})));
  }
  return {id:t.id,group,axis,phase:data.phase_rad.map(row=>row[k]),omega:data.omega_rad_s.map(row=>row[k]),partCount:3};
 });
 return {rotors,phaseSource:'recorded_solver_kinematics',update(t,enabled=true){const {a,b,mix:f}=timeline.sample(t);for(const r of rotors){r.group.visible=enabled;r.group.quaternion.setFromAxisAngle(r.axis,r.phase[a]*(1-f)+r.phase[b]*f);}const rpm=rotors.map(r=>(r.omega[a]*(1-f)+r.omega[b]*f)*60/(2*Math.PI));return [Math.min(...rpm),Math.max(...rpm)];}};
}
