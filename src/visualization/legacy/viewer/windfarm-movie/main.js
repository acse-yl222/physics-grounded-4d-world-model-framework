import {buildRotors} from './rotors.js';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const base='../../scenes/windfarm_movie/';
async function bytes(name){const r=await fetch(base+name);if(!r.ok)throw Error('Unable to load '+name+': '+r.status);return r.arrayBuffer();}
function f16(a){const out=new Float32Array(a.length);for(let i=0;i<a.length;i++){const h=a[i],s=h&32768?-1:1,e=(h>>10)&31,f=h&1023;out[i]=e===31?(f?NaN:s*Infinity):e===0?s*f*2**-24:s*(1+f/1024)*2**(e-15);}return out;}
async function wind(){const chunks=await Promise.all(["u-0.bin", "u-1.bin", "u-2.bin", "u-3.bin"].map(bytes));const a=new Uint16Array(chunks.reduce((n,b)=>n+b.byteLength/2,0));let at=0;for(const b of chunks){a.set(new Uint16Array(b),at);at+=b.byteLength/2;}return f16(a);}

const canvas=document.querySelector('canvas'),renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.SRGBColorSpace;
const ctx=canvas.getContext('2d');canvas.width=innerWidth;canvas.height=innerHeight;
const scene=new THREE.Scene();scene.background=new THREE.Color('#101923');
scene.add(new THREE.HemisphereLight(0xd7edff,0x817c64,2.4));const sun=new THREE.DirectionalLight(0xffefd4,3);sun.position.set(-1800,4000,1800);scene.add(sun);
const camera=new THREE.PerspectiveCamera(43,innerWidth/innerHeight,5,24000);camera.position.set(2600,3000,3400);const controls=new OrbitControls(camera,canvas);controls.target.set(200,210,0);controls.update();
try{
const [meta,ground,frames,model]=await Promise.all([fetch('../../scenes/windfarm_movie/metadata.json').then(r=>r.json()),bytes('ground.bin').then(b=>new Float32Array(b)),wind(),new GLTFLoader().loadAsync('../../scenes/region/models/region.glb')]);
scene.add(model.scene);model.scene.traverse(o=>{if(o.isMesh&&o.name.startsWith('Surface_study'))o.visible=false;});
const [ny,nx]=meta.display_shape,N=nx*ny,geo=new THREE.PlaneGeometry((nx-1)*8,(ny-1)*8,nx-1,ny-1),pos=geo.attributes.position;
for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const k=j*nx+i;pos.setXYZ(k,meta.origin_xyz_m[0]+5+i*8,ground[k]+80,-(meta.origin_xyz_m[1]+5+j*8));geo.attributes.uv.setXY(k,i/(nx-1),j/(ny-1));}
geo.computeVertexNormals();const pixels=new Uint8Array(N*4),texture=new THREE.DataTexture(pixels,nx,ny,THREE.RGBAFormat);texture.colorSpace=THREE.SRGBColorSpace;texture.magFilter=THREE.LinearFilter;texture.minFilter=THREE.LinearFilter;
const mat=new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide,transparent:true,opacity:.72,depthWrite:false});const field=new THREE.Mesh(geo,mat);scene.add(field);
const history=await fetch('../../scenes/windfarm_movie/rotor-speeds.json').then(r=>r.json());const rotorSystem=buildRotors(model.scene,scene,meta,history);
const comparison={};for(const key of ['mac_mean','jensen04','jensen10','gaussian'])comparison[key]=f16(new Uint16Array(await bytes('comparison/'+key+'.bin')));
const labels={mac_live:'OUR MAC / TIME EVOLUTION',mac_mean:'OUR MAC / MEAN 200–300 s',jensen04:'PYWAKE / JENSEN k=0.04',jensen10:'PYWAKE / JENSEN k=0.10',gaussian:'PYWAKE / GAUSSIAN k=0.04'};
const select=document.querySelector('#model');function selectModel(key){select.value=key;const live=key==='mac_live';document.querySelector('#time').disabled=!live;document.querySelector('#play').disabled=!live;document.querySelector('#spin').disabled=!live;}select.onchange=()=>selectModel(select.value);selectModel('mac_mean');
const palette=[[38,63,131],[22,139,166],[103,200,164],[243,220,105],[237,116,69]];
let playing=true,time=0,last=0;document.querySelector('#loading').remove();document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'暂停':'播放';};document.querySelector('#time').oninput=e=>{time=+e.target.value;playing=false;document.querySelector('#play').textContent='播放';};
function render(t,opacity=.72,chapter='SIMULATED WIND + GEOMETRY'){
const selected=select.value,live=selected==='mac_live',chosen=comparison[selected];chapter=labels[selected];
const a=Math.min(meta.times.length-1,Math.floor(t/2)),b=Math.min(a+1,meta.times.length-1),mix=(t-meta.times[a])/2;
for(let k=0;k<N;k++){const u=chosen?chosen[k]:frames[a*N+k]*(1-mix)+frames[b*N+k]*mix,q=Number.isFinite(u)?Math.max(0,Math.min(4,u/5)):0,c=Math.min(3,Math.floor(q)),f=q-c;for(let z=0;z<3;z++)pixels[k*4+z]=palette[c][z]*(1-f)+palette[c+1][z]*f;pixels[k*4+3]=Number.isFinite(u)?255:0;}
const rpm=rotorSystem.update(t,live&&document.querySelector('#spin').checked);texture.needsUpdate=true;mat.opacity=opacity;field.visible=opacity>0;renderer.render(scene,camera);ctx.drawImage(renderer.domElement,0,0);
const W=canvas.width,H=canvas.height,s=W/1920;ctx.save();ctx.scale(s,s);const hh=H/s;const grad=ctx.createLinearGradient(0,0,0,220);grad.addColorStop(0,'#0b1728e8');grad.addColorStop(1,'#0b172800');ctx.fillStyle=grad;ctx.fillRect(0,0,1920,220);
ctx.fillStyle='#8fe3d2';ctx.font='600 17px system-ui';ctx.fillText('WIND FARM / 23 TURBINES',64,58);ctx.fillStyle='#f1f7fc';ctx.font='600 38px system-ui';ctx.fillText(chapter,64,110);ctx.fillStyle='#b5c9d6';ctx.font='20px system-ui';ctx.fillText('Same geometry + camera + scale   ·   Terrain-following slice: 80 m AGL',64,151);
ctx.textAlign='right';ctx.fillStyle='#f1f7fc';ctx.font='600 37px system-ui';ctx.fillText(live?`${t.toFixed(1)} / 300 s`:selected==='mac_mean'?'200–300 s mean':'Steady engineering model',1856,77);ctx.font='18px system-ui';ctx.fillStyle='#b5c9d6';ctx.fillText(selected.startsWith('mac')?'MAC: 2 m grid · Terrain included':'PyWake: no terrain-flow correction',1856,109);if(live)ctx.fillText(`Visual rotor speeds: ${rpm[0].toFixed(1)}–${rpm[1].toFixed(1)} rpm (assumed)`,1856,141);ctx.textAlign='left';
ctx.fillStyle='#101923d9';ctx.fillRect(48,hh-120,1824,100);ctx.font='16px system-ui';ctx.fillStyle='#b5c9d6';ctx.fillText('Exploratory comparison: different terrain treatment / no accuracy ranking · Display sampled at 8 m',64,hh-45);
const legend=ctx.createLinearGradient(64,0,504,0);palette.forEach((c,i)=>legend.addColorStop(i/4,`rgb(${c})`));ctx.fillStyle=legend;ctx.fillRect(64,hh-96,440,10);ctx.fillStyle='#eef7ff';ctx.font='17px system-ui';ctx.fillText('0',64,hh-63);ctx.fillText('Axial wind speed (m/s)',180,hh-63);ctx.fillText('20',486,hh-63);ctx.restore();
document.querySelector('#clock').textContent=live?t.toFixed(1)+' s':'静态对比';document.querySelector('#time').value=t;
}
window.movie={ready:true,meta,rotorSystem,comparison,selectModel,frame(f,n){const k=f/(n-1),p=Math.max(0,Math.min(1,(k-.12)/.76)),t=300*p;const angle=.18+Math.sin(k*Math.PI)*.20,dist=4500-k*600;camera.position.set(200+Math.sin(angle)*dist,2600-k*550,Math.cos(angle)*dist);controls.target.set(200,230,0);controls.update();render(t,Math.min(.72,Math.max(0,(k-.08)*12)),k<.12?'TERRAIN + TURBINE GEOMETRY':'SIMULATED WIND + GEOMETRY');return canvas.toDataURL('image/jpeg',.94).split(',')[1];},render};
function animate(now){const dt=last?(now-last)/1000:0;last=now;if(playing&&select.value==='mac_live')time=(time+dt*12.5)%300;controls.update();render(time);requestAnimationFrame(animate);}if(!new URLSearchParams(location.search).has('capture'))requestAnimationFrame(animate);else render(0);
}catch(e){console.error(e);const el=document.querySelector('#loading');if(el)el.textContent=e.message;}
