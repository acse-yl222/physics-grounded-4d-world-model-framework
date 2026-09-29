import * as THREE from 'three';
import {createTimeline} from './timeline.mjs';
// Display-only rotor kinematics. TSR=7 is assumed, not turbine controller data.
// Phase advances at 1/12.5 of the accelerated simulation timeline for readable motion.
export function buildRotors(model,scene,meta,history){
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
