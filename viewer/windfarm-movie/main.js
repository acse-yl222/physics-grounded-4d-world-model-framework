import {buildRotors} from './rotors.js';
import {createTimeline} from './timeline.mjs';
import {movieLayout} from './layout.mjs';
import {batchStaticCity} from '../../agents/demo_rev02/static-batches.js';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const configResponse=await fetch(new URL('resources.json',import.meta.url));if(!configResponse.ok)throw Error('Resource configuration unavailable');
const resourceConfig=await configResponse.json();
const requestedRun=new URLSearchParams(location.search).get('run');
const runKey=Object.hasOwn(resourceConfig.runs??{},requestedRun)?requestedRun:resourceConfig.default_run;
const base=new URL(resourceConfig.runs?.[runKey]?.data_base??resourceConfig.data_base,import.meta.url).href;
const modelURL=new URL(resourceConfig.model,import.meta.url).href;
const runSelect=document.querySelector('#run');
if(runSelect&&resourceConfig.runs){
 runSelect.replaceChildren(...Object.entries(resourceConfig.runs).map(([key,item])=>new Option(item.label,key)));
 runSelect.value=runKey;runSelect.disabled=false;
 runSelect.onchange=()=>{const url=new URL(location.href);url.searchParams.set('run',runSelect.value);location.href=url.href;};
}else if(runSelect)runSelect.hidden=true;

async function bytes(name){const r=await fetch(base+name);if(!r.ok)throw Error('Unable to load '+name+': '+r.status);return r.arrayBuffer();}
function f16(a){const out=new Float32Array(a.length);for(let i=0;i<a.length;i++){const h=a[i],s=h&32768?-1:1,e=(h>>10)&31,f=h&1023;out[i]=e===31?(f?NaN:s*Infinity):e===0?s*f*2**-24:s*(1+f/1024)*2**(e-15);}return out;}
async function wind(meta){const chunks=await Promise.all((meta.wind_chunks??["u-0.bin", "u-1.bin", "u-2.bin", "u-3.bin"]).map(bytes));const a=new Uint16Array(chunks.reduce((n,b)=>n+b.byteLength/2,0));let at=0;for(const b of chunks){a.set(new Uint16Array(b),at);at+=b.byteLength/2;}return f16(a);}

const navigation=document.querySelector('nav');
if(navigation)new ResizeObserver(()=>{
 const hud=document.querySelector('.movie-hud');if(hud)hud.style.top=`${navigation.getBoundingClientRect().bottom+12}px`;
}).observe(navigation);
const canvas=document.querySelector('canvas');
const captureMode=new URLSearchParams(location.search).has('capture');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:captureMode});
const overlay=document.createElement('canvas');overlay.id='annotations';overlay.setAttribute('aria-hidden','true');
overlay.style.cssText='position:absolute;inset:0;pointer-events:none';overlay.style.display=captureMode?'block':'none';
document.documentElement.dataset.capture=String(captureMode);canvas.after(overlay);
let invalidate=()=>{};
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();window.dispatchEvent(new Event('viewer-context-lost'));});
renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.SRGBColorSpace;
const ctx=overlay.getContext('2d');overlay.width=innerWidth;overlay.height=innerHeight;
const scene=new THREE.Scene();scene.background=new THREE.Color('#101923');
scene.add(new THREE.HemisphereLight(0xd7edff,0x817c64,2.4));const sun=new THREE.DirectionalLight(0xffefd4,3);sun.position.set(-1800,4000,1800);scene.add(sun);
const camera=new THREE.PerspectiveCamera(43,innerWidth/innerHeight,5,24000);camera.position.set(2600,3000,3400);const controls=new OrbitControls(camera,canvas);controls.target.set(200,210,0);controls.update();controls.addEventListener('change',()=>invalidate());
addEventListener('resize',()=>{
  camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight);overlay.width=innerWidth;overlay.height=innerHeight;invalidate();
});
try{
const metaResponse=await fetch(base+'metadata.json');if(!metaResponse.ok)throw Error('Wind metadata unavailable');const meta=await metaResponse.json();
const [ground,frames,model]=await Promise.all([bytes('ground.bin').then(b=>new Float32Array(b)),wind(meta),new GLTFLoader().loadAsync(modelURL)]);
const timeline=createTimeline(meta.times);
document.querySelector('#time').min=timeline.start;document.querySelector('#time').max=timeline.end;
if(frames.length!==meta.times.length*meta.display_shape[0]*meta.display_shape[1])throw Error('Wind data length does not match recorded frame times');
scene.add(model.scene);model.scene.traverse(o=>{if(o.isMesh&&o.name.startsWith('Surface_study'))o.visible=false;});
const layout=movieLayout(meta,ground.length),{ny,nx,spacing}=layout,N=nx*ny,geo=new THREE.PlaneGeometry((nx-1)*spacing,(ny-1)*spacing,nx-1,ny-1),pos=geo.attributes.position;
for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const k=j*nx+i;pos.setXYZ(k,...layout.position(i,j,ground[k]));geo.attributes.uv.setXY(k,i/(nx-1),j/(ny-1));}
geo.computeVertexNormals();const pixels=new Uint8Array(N*4),texture=new THREE.DataTexture(pixels,nx,ny,THREE.RGBAFormat);texture.colorSpace=THREE.SRGBColorSpace;texture.magFilter=THREE.LinearFilter;texture.minFilter=THREE.LinearFilter;
const mat=new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide,transparent:true,opacity:.72,depthWrite:false});const field=new THREE.Mesh(geo,mat);scene.add(field);
const history=await fetch(base+'rotor-speeds.json').then(r=>r.json());const rotorSystem=buildRotors(model.scene,scene,meta,history);
const staticBatches=await batchStaticCity(model.scene);scene.add(staticBatches.object);
for(const root of [model.scene,staticBatches.object])root.traverse(object=>{object.updateMatrix();object.matrixAutoUpdate=false;});
const comparison={};for(const key of (meta.comparison_keys??['mac_mean','jensen04','jensen10','gaussian'])){comparison[key]=f16(new Uint16Array(await bytes('comparison/'+key+'.bin')));if(comparison[key].length!==N)throw Error('Comparison shape mismatch');}
const labels={mac_live:'OUR MAC / TIME EVOLUTION',mac_mean:'OUR MAC / MEAN 200–300 s',jensen04:'PYWAKE / JENSEN k=0.04',jensen10:'PYWAKE / JENSEN k=0.10',gaussian:'PYWAKE / GAUSSIAN k=0.04',...(meta.model_labels??{})};
const select=document.querySelector('#model');select.replaceChildren(...['mac_live',...Object.keys(comparison)].map(key=>new Option(labels[key]??key,key)));
document.querySelector('#slice-detail').textContent=`${meta.turbines.length} turbines · Terrain-following slice: ${layout.height} m AGL`;
document.querySelector('#sampling-detail').textContent=meta.display_note??`Exploratory comparison · Different terrain treatment; no accuracy ranking · Display sampled at ${spacing} m`;
function selectModel(key){select.value=key;const live=key==='mac_live';document.querySelector('#time').disabled=!live;document.querySelector('#play').disabled=!live;document.querySelector('#spin').disabled=!live;invalidate();}select.onchange=()=>selectModel(select.value);selectModel(meta.default_model??(comparison.mac_mean?'mac_mean':'mac_live'));
let lastFieldKey=null;const metrics={renders:0,fieldUpdates:0};
const palette=[[38,63,131],[22,139,166],[103,200,164],[243,220,105],[237,116,69]];
let playing=true,time=timeline.start,last=0;document.querySelector('#loading').remove();document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'Pause':'Play';invalidate();};document.querySelector('#time').oninput=e=>{time=+e.target.value;playing=false;document.querySelector('#play').textContent='Play';invalidate();};
function render(t,opacity=.72,chapter='SIMULATED WIND + GEOMETRY',forExport=false){
const selected=select.value,live=selected==='mac_live',chosen=comparison[selected];chapter=labels[selected];
const {a,b,mix}=timeline.sample(t);
const fieldKey=live?`${selected}:${t}`:selected;
if(fieldKey!==lastFieldKey){
for(let k=0;k<N;k++){const u=chosen?chosen[k]:frames[a*N+k]*(1-mix)+frames[b*N+k]*mix,q=Number.isFinite(u)?Math.max(0,Math.min(4,u/5)):0,c=Math.min(3,Math.floor(q)),f=q-c;for(let z=0;z<3;z++)pixels[k*4+z]=palette[c][z]*(1-f)+palette[c+1][z]*f;pixels[k*4+3]=Number.isFinite(u)?255:0;}
texture.needsUpdate=true;lastFieldKey=fieldKey;metrics.fieldUpdates++;
}
const rpm=rotorSystem.update(t,live&&document.querySelector('#spin').checked);mat.opacity=opacity;field.visible=opacity>0;renderer.render(scene,camera);metrics.renders++;if(document.querySelector('#wind-title').textContent!==chapter)document.querySelector('#wind-title').textContent=chapter;
const detail=meta.model_details?.[selected]??(selected.startsWith('mac')?'MAC: 2 m grid · Terrain included':'PyWake: no terrain-flow correction');
if(document.querySelector('#wind-detail').textContent!==detail)document.querySelector('#wind-detail').textContent=detail;
if(captureMode||forExport){ctx.clearRect(0,0,overlay.width,overlay.height);
const W=canvas.width,H=canvas.height,s=W/1920;ctx.save();ctx.scale(s,s);const hh=H/s;const grad=ctx.createLinearGradient(0,0,0,220);grad.addColorStop(0,'#0b1728e8');grad.addColorStop(1,'#0b172800');ctx.fillStyle=grad;ctx.fillRect(0,0,1920,220);
ctx.fillStyle='#8fe3d2';ctx.font='600 17px system-ui';ctx.fillText(`WIND FARM / ${meta.turbines.length} TURBINES`,64,58);ctx.fillStyle='#f1f7fc';ctx.font='600 38px system-ui';ctx.fillText(chapter,64,110);ctx.fillStyle='#b5c9d6';ctx.font='20px system-ui';ctx.fillText(`Same geometry + camera + scale   ·   Terrain-following slice: ${layout.height} m AGL`,64,151);
ctx.textAlign='right';ctx.fillStyle='#f1f7fc';ctx.font='600 37px system-ui';ctx.fillText(live?`${t.toFixed(1)} / ${timeline.end} s`:selected==='mac_mean'?'200–300 s mean':'Steady engineering model',1856,77);ctx.font='18px system-ui';ctx.fillStyle='#b5c9d6';ctx.fillText(detail,1856,109);if(live)ctx.fillText(`Visual rotor speeds: ${rpm[0].toFixed(1)}–${rpm[1].toFixed(1)} rpm (assumed)`,1856,141);ctx.textAlign='left';
ctx.fillStyle='#101923d9';ctx.fillRect(48,hh-120,1824,100);ctx.font='16px system-ui';ctx.fillStyle='#b5c9d6';ctx.fillText(meta.display_note??`Exploratory comparison: different terrain treatment / no accuracy ranking · Display sampled at ${spacing} m`,64,hh-45);
const legend=ctx.createLinearGradient(64,0,504,0);palette.forEach((c,i)=>legend.addColorStop(i/4,`rgb(${c})`));ctx.fillStyle=legend;ctx.fillRect(64,hh-96,440,10);ctx.fillStyle='#eef7ff';ctx.font='17px system-ui';ctx.fillText('0',64,hh-63);ctx.fillText('Axial wind speed (m/s)',180,hh-63);ctx.fillText('20',486,hh-63);ctx.restore();}
document.querySelector('#clock').textContent=live?t.toFixed(1)+' s':'Static comparison';document.querySelector('#time').value=t;
}
window.movie={ready:true,metrics,renderer,staticBatchStats:staticBatches.stats,meta,rotorSystem,comparison,selectModel,frame(f,n){const k=f/(n-1),p=Math.max(0,Math.min(1,(k-.12)/.76)),t=timeline.start+timeline.duration*p;const angle=.18+Math.sin(k*Math.PI)*.20,dist=4500-k*600;camera.position.set(200+Math.sin(angle)*dist,2600-k*550,Math.cos(angle)*dist);controls.target.set(200,230,0);controls.update();render(t,Math.min(.72,Math.max(0,(k-.08)*12)),k<.12?'TERRAIN + TURBINE GEOMETRY':'SIMULATED WIND + GEOMETRY',true);const output=document.createElement('canvas');output.width=canvas.width;output.height=canvas.height;const context=output.getContext('2d');context.drawImage(canvas,0,0);context.drawImage(overlay,0,0);return output.toDataURL('image/jpeg',.94).split(',')[1];},render};
let animationId=0,dirty=true;
function animate(now){
  animationId=0;
  if(document.hidden){last=0;return;}
  const dt=last?(now-last)/1000:0;last=now;
  const moving=playing&&select.value==='mac_live';
  if(moving)time=timeline.advance(time,dt,12.5);
  controls.update();
  if(dirty||moving){dirty=false;render(time);}
  if(moving&&!captureMode&&!animationId)animationId=requestAnimationFrame(animate);else last=0;
}
invalidate=()=>{dirty=true;if(!captureMode&&!document.hidden&&!animationId)animationId=requestAnimationFrame(animate);};
document.querySelector('#spin').addEventListener('change',invalidate);
document.addEventListener('visibilitychange',()=>{
  if(animationId)cancelAnimationFrame(animationId);animationId=0;last=0;
  if(!document.hidden)invalidate();
});
if(captureMode)render(timeline.start);else invalidate();
}catch(e){throw e;}
