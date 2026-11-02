// Ground and exact recorded SUMO frames in the scene's flattened ENU frame.
import * as THREE from 'three';
export async function createCorridorContext({scene, config, url, onChange}) {
  const group = new THREE.Group(); group.name='corridor_context'; scene.add(group);
  const panel=document.createElement('details'); panel.open=true;
  panel.style.cssText='padding:10px;border-top:1px solid #567;color:inherit;font:12px sans-serif';
  panel.innerHTML=`<summary style="cursor:pointer;font-weight:bold">Ground & recorded traffic</summary><p>Ground projected to the buildings’ flat ENU plane.</p><label>Ground <select id="corridor-ground"><option value="surface">Roads / green / water</option><option value="elevation">Terrain elevation colour</option></select></label><p id="corridor-ground-key">Grey roads · green vegetation · blue water</p><label><input id="corridor-traffic-visible" type="checkbox" checked> SUMO AM peak · saved subset</label><p><button id="corridor-traffic-play">Play traffic</button> <span id="corridor-traffic-time">Loading…</span></p><input id="corridor-traffic-step" type="range" min="0" value="0" style="width:100%"><p>Independent traffic clock · exact 1 s saved frames · not observed traffic.</p><label>Wind <select id="corridor-wind"><option value="final">4 m final snapshot</option><option value="history">8 m time series</option></select></label>${config.temperature_hidden?'':'<p>Temperature: 32 m grid, sampled 8 m above ground.</p>'}`;
  const container=document.querySelector('#l-ground').closest('aside, .panel, #panel') || document.querySelector('#geometry-quality').parentElement.parentElement;
  container.querySelector('.quality-note').after(panel);
  const select=panel.querySelector('#corridor-wind'); select.value=new URLSearchParams(location.search).get('wind_mode')==='history'?'history':'final';
  select.onchange=()=>{const u=new URL(location.href);u.searchParams.set('wind_mode',select.value);u.searchParams.set('step','1');location.assign(u)};
  const loader=new THREE.TextureLoader();
  const textures=await Promise.all([config.surface,config.elevation].map(p=>loader.loadAsync(url(p))));
  for(const texture of textures){texture.colorSpace=THREE.SRGBColorSpace;texture.magFilter=THREE.NearestFilter;texture.generateMipmaps=false;texture.minFilter=THREE.LinearFilter;}
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(8192,8192),new THREE.MeshBasicMaterial({map:textures[0],side:THREE.DoubleSide}));
  ground.rotation.x=-Math.PI/2;ground.position.y=-0.15;group.add(ground);
  panel.querySelector('#corridor-ground').onchange=e=>{ground.material.map=textures[e.target.value==='surface'?0:1];ground.material.needsUpdate=true;panel.querySelector('#corridor-ground-key').textContent=e.target.value==='surface'?'Grey roads · green vegetation · blue water':config.elevation_label;onChange()};
  const [meta,response]=await Promise.all([fetch(url(config.traffic_meta)).then(r=>{if(!r.ok)throw Error('Traffic metadata unavailable');return r.json()}),fetch(url(config.traffic_binary))]);
  if(!response.ok)throw Error('Traffic frames unavailable');
  const buffer=await response.arrayBuffer(), bytes=new DataView(buffer), frames=[];let offset=0,maxCount=0;
  for(let f=0;f<meta.frames;f++){if(offset+4>buffer.byteLength)throw Error('Truncated traffic frame');const count=bytes.getUint32(offset,true);offset+=4;frames.push({offset,count});offset+=count*16;if(offset>buffer.byteLength)throw Error('Truncated traffic records');maxCount=Math.max(maxCount,count)}
  if(offset!==buffer.byteLength)throw Error('Unexpected traffic bytes');
  const cars=new THREE.InstancedMesh(new THREE.BoxGeometry(1,1,1),new THREE.MeshStandardMaterial({color:0xffffff,roughness:.65}),maxCount);cars.frustumCulled=false;group.add(cars);
  const dummy=new THREE.Object3D(),color=new THREE.Color();let frame=-1,playing=false,elapsed=0;
  const slider=panel.querySelector('#corridor-traffic-step'), clock=panel.querySelector('#corridor-traffic-time'),button=panel.querySelector('#corridor-traffic-play');slider.max=frames.length-1;
  function show(index){index=Math.max(0,Math.min(frames.length-1,index));if(index===frame)return;frame=index;const f=frames[index];cars.count=f.count;
    for(let i=0;i<f.count;i++){const k=f.offset+i*16,id=bytes.getUint32(k,true),kind=meta.vehicles[id]?.type;if(!meta.vehicles[id])throw Error('Unknown traffic vehicle');const bus=kind==='bus';dummy.position.set(bytes.getFloat32(k+4,true),bus?1.65:.85,-bytes.getFloat32(k+8,true));dummy.rotation.set(0,bytes.getFloat32(k+12,true),0);dummy.scale.set(bus?11.5:4.5,bus?3:1.5,bus?2.5:1.85);dummy.updateMatrix();cars.setMatrixAt(i,dummy.matrix);cars.setColorAt(i,color.set(bus?0xf1b943:0xf47155));}
    cars.instanceMatrix.needsUpdate=true;if(cars.instanceColor)cars.instanceColor.needsUpdate=true;slider.value=index;const t=meta.t0+index*meta.dt;clock.textContent=`${String(Math.floor(t/3600)).padStart(2,'0')}:${String(Math.floor(t/60)%60).padStart(2,'0')}:${String(Math.floor(t)%60).padStart(2,'0')} · ${f.count} vehicles`;onChange();}
  button.onclick=()=>{playing=!playing;if(playing&&frame===frames.length-1){elapsed=0;show(0)}button.textContent=playing?'Pause traffic':'Play traffic';};
  slider.oninput=()=>{elapsed=Number(slider.value)*meta.dt;show(Number(slider.value));};
  panel.querySelector('#corridor-traffic-visible').onchange=e=>{cars.visible=e.target.checked;onChange()};show(0);
  return {group,ground,cars,meta,frames,get frame(){return frame},get playing(){return playing},show,
    tick(dt){ground.visible=document.querySelector('#l-ground').checked;if(playing){elapsed=Math.min(elapsed+dt,(frames.length-1)*meta.dt);show(Math.floor(elapsed/meta.dt));if(frame===frames.length-1){playing=false;button.textContent='Play traffic'}}},
  };
}
