import * as THREE from 'three';
export function createNeuralWind(scene,clip){
 const $=id=>document.getElementById(id),query=new URLSearchParams(location.search);
 const sourceName={ai4urban:'AI4Urban fixed operators',scaled:'SCALED surrogate'};
 $('wind-source').value=query.get('solver')==='ai4urban'?'ai4urban':'scaled';
 const group=new THREE.Group();scene.add(group);group.visible=false;
 let manifest,level,positions,vectors,shafts,tips,playing=false,last=0,request=0;
 const matrix=new THREE.Matrix4(),rotation=new THREE.Quaternion(),dir=new THREE.Vector3(),up=new THREE.Vector3(0,1,0),end=new THREE.Vector3(),scale=new THREE.Vector3(1,1,1);
 const colors=['#417ee8','#44d8d0','#fae95a','#f07748'].map(x=>new THREE.Color(x));
 const color=new THREE.Color();
 function draw(){
  if(!vectors)return;
  const step=+$('wind-step').value-1,cut=clip(),n=level.count;
  const xyz=shafts.geometry.attributes.position.array,rgb=shafts.geometry.attributes.color.array;
  let visible=0;
  for(let i=0;i<n;i++){
   const p=i*3,v=(step*n+i)*3,x=positions[p],y=positions[p+1],z=positions[p+2];
   if(x>=-3072+cut.xcut*8||y>=cut.zcut*8)continue;
   dir.set(vectors[v],vectors[v+1],vectors[v+2]);const speed=dir.length();if(speed<1e-5)continue;dir.divideScalar(speed);
   const t=Math.min(speed/2.5,1)*3,k=Math.min(2,Math.floor(t));color.copy(colors[k]).lerp(colors[k+1],t-k);
   const length=12+Math.min(speed,2.5)*16;
   end.set(x,y,z).addScaledVector(dir,length);
   xyz.set([x,y,z,end.x,end.y,end.z],visible*6);
   rgb.set([color.r,color.g,color.b,color.r,color.g,color.b],visible*6);
   rotation.setFromUnitVectors(up,dir);matrix.compose(end,rotation,scale);tips.setMatrixAt(visible,matrix);tips.setColorAt(visible,color);visible++;
  }
  tips.count=visible;tips.instanceMatrix.needsUpdate=true;if(tips.instanceColor)tips.instanceColor.needsUpdate=true;
  shafts.geometry.setDrawRange(0,visible*2);shafts.geometry.attributes.position.needsUpdate=true;shafts.geometry.attributes.color.needsUpdate=true;
  const solverStep=manifest.step_indices?.[step]??step+1,time=manifest.time_seconds?.[step];
  $('wind-step-value').textContent=`${solverStep}${time!==undefined?` · ${time.toFixed(1)} s`:` / ${manifest.frames}`}`;
  $('wind-status').textContent=`${sourceName[manifest.viewerSource]} · Step ${solverStep} steps · ${visible.toLocaleString()} arrows · Sampled-layer mean ${level.mean_speed_by_step[step].toFixed(3)} / maximum ${level.max_speed_by_step[step].toFixed(3)} m/s`;
 }
 async function fetchOK(base,file){const r=await fetch(base+file,{cache:file.endsWith('.json')?'no-cache':'default'});if(!r.ok)throw Error(`${file}: HTTP ${r.status}`);return r;}
 async function load(){
  const id=++request,source=$('wind-source').value;
  const base=`../../scenes/region/${source==='ai4urban'?'ai4urban_wind':'neural_wind'}/`;
  playing=false;group.visible=false;$('wind-play').disabled=true;$('wind-play').textContent='Play simulation';$('wind-status').textContent=`Loading ${sourceName[source]} results…`;
  try{
   const nextManifest=await (await fetchOK(base,'manifest.json')).json();
   const selected=nextManifest.levels.find(l=>l.agl_m===+$('wind-height').value);
   const [p,v]=await Promise.all([fetchOK(base,selected.positions).then(r=>r.arrayBuffer()),fetchOK(base,selected.vectors).then(r=>r.arrayBuffer())]);
   if(id!==request)return;
   if(p.byteLength!==selected.count*12||v.byteLength!==nextManifest.frames*selected.count*12)throw Error('Wind-field dimensions do not match');
   manifest={...nextManifest,viewerSource:source};
   $('wind-step').max=manifest.frames;$('wind-step').value=manifest.frames;
   $('wind-detail').textContent=`${manifest.cell_m} m wind field, displayed every 64 m; AGL sampling error up to ±${manifest.cell_m/2} m。${source==='ai4urban'?`Started from zero, dt=0.5 s; latest output step: ${manifest.step_indices.at(-1)} steps。`:'Existing neural-surrogate results for 100 steps.'} Simulated wind, not measurements; no rotating wake and no verified steady state.`;
   level=selected;positions=new Float32Array(p);vectors=new Float32Array(v);
   if(shafts){group.remove(shafts,tips);shafts.geometry.dispose();shafts.material.dispose();tips.geometry.dispose();tips.material.dispose();tips.dispose();}
   const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(level.count*6),3));geometry.setAttribute('color',new THREE.BufferAttribute(new Float32Array(level.count*6),3));
   shafts=new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({vertexColors:true}));shafts.frustumCulled=false;
   tips=new THREE.InstancedMesh(new THREE.ConeGeometry(3,9,5),new THREE.MeshBasicMaterial(),level.count);tips.frustumCulled=false;
   group.add(shafts,tips);group.visible=$('wind-on').checked;$('wind-play').disabled=false;draw();
  }catch(e){if(id===request)$('wind-status').textContent='Loading failed: '+e.message;}
 }
 $('wind-on').checked=query.get('wind')==='1';
 $('wind-on').onchange=()=>{group.visible=$('wind-on').checked;if(group.visible&&!vectors)load();};
 $('wind-height').onchange=load;
 $('wind-source').onchange=load;
 $('wind-refresh').onclick=load;
 $('wind-step').oninput=()=>{playing=false;$('wind-play').textContent='Play simulation';draw();};
 $('wind-play').onclick=()=>{playing=!playing;if(playing&&+$('wind-step').value===manifest.frames)$('wind-step').value=1;$('wind-play').textContent=playing?'Pause':'Play simulation';draw();};
 if($('wind-on').checked)load();
 return {refresh:draw,update(now){if(playing&&group.visible&&now-last>180){last=now;const next=+$('wind-step').value+1;$('wind-step').value=next>manifest.frames?1:next;draw();}}};
}
