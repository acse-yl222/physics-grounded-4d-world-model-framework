import {loadScene} from '../scene.js';
import {setDataBase,npy,getFrame,f16,loadMask} from '../npy.js';
const $=id=>document.getElementById(id),canvas=$('map'),ctx=canvas.getContext('2d'),raster=document.createElement('canvas'),rc=raster.getContext('2d');
let scene,manifest,fields=[],field,values,mask,foot,w,h,cell,uvw,ready=false,playing=false,generation=0,turbines=[];
let scale=1,px=0,py=0,drag=null,request=null,playback=0;
function stop(){playing=false;playback++;clearTimeout(request);$('play').textContent='播放';}
const palette=[[38,63,131],[22,139,166],[103,200,164],[243,220,105],[237,116,69]];
function fit(){scale=Math.min(canvas.width/(w||768),canvas.height/(h||704))*.91;px=(canvas.width-(w||768)*scale)/2;py=(canvas.height-(h||704)*scale)/2;draw();}
function resize(){const r=$('plot').getBoundingClientRect();canvas.width=Math.round(r.width);canvas.height=Math.round(r.height);fit();}addEventListener('resize',resize);
function draw(){
 ctx.fillStyle='#101923';ctx.fillRect(0,0,canvas.width,canvas.height);if(!ready)return;
 ctx.imageSmoothingEnabled=false;ctx.drawImage(raster,px,py,w*scale,h*scale);
 if(uvw&&$('arrows').checked){
  const jump=Math.max(4,Math.ceil(28/scale));ctx.strokeStyle='#101d2cd0';ctx.lineWidth=1;
  for(let row=Math.floor(jump/2);row<h;row+=jump)for(let col=Math.floor(jump/2);col<w;col+=jump){
   const i=row*w+col;if(mask?.[i]||!Number.isFinite(values[i]))continue;
   const u=uvw[i],v=uvw[w*h+i],speed=Math.hypot(u,v);if(speed<.02)continue;
   const x=px+(col+.5)*scale,y=py+(h-row-.5)*scale;
   if(x<0||x>canvas.width||y<0||y>canvas.height)continue;
   const a=u/speed*9,b=-v/speed*9;ctx.beginPath();ctx.moveTo(x-a*.5,y-b*.5);ctx.lineTo(x+a*.5,y+b*.5);ctx.lineTo(x+a*.1-b*.3,y+b*.1+a*.3);ctx.moveTo(x+a*.5,y+b*.5);ctx.lineTo(x+a*.1+b*.3,y+b*.1-a*.3);ctx.stroke();
  }
 }
 if(field.solver==='AI4Urban'&&$('buildings').checked){
  const origin=scene.grid.domain_origin_xy_m;
  for(const t of turbines){const x=px+(t.x-origin[0])/cell*scale,y=py+(h-(t.y-origin[1])/cell)*scale;
   ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle='#0e1a29';ctx.lineWidth=1.5;ctx.stroke();}
 }
 ctx.strokeStyle='#7891a8';ctx.strokeRect(px,py,w*scale,h*scale);
 const barMeters=cell*w/6,barPixels=barMeters/cell*scale;
 ctx.fillStyle='#e5edf5';ctx.fillRect(18,canvas.height-24,barPixels,3);ctx.font='12px system-ui';ctx.fillText(`${barMeters.toFixed(0)} m`,18,canvas.height-32);
}
function paint(){
 if(!values)return;const lo=+$('lo').value,hi=+$('hi').value;
 if(!(hi>lo)){ $('status').textContent='颜色上限必须大于下限。';return; }
 raster.width=w;raster.height=h;const image=rc.createImageData(w,h);
 for(let row=0;row<h;row++)for(let col=0;col<w;col++){
  const i=row*w+col,o=((h-1-row)*w+col)*4;let rgb;
  if((foot?.[i]&&$('buildings').checked)||mask?.[i]===1)rgb=[141,151,163];
  else if(mask?.[i]===2||!Number.isFinite(values[i])||(field.key==='flood'&&values[i]<=.02))rgb=[25,40,53];
  else{let t=field.log?Math.log10(Math.max(values[i],1e-12)):values[i];t=Math.max(0,Math.min(1,(t-lo)/(hi-lo)))*4;const j=Math.min(3,Math.floor(t)),f=t-j;rgb=palette[j].map((v,k)=>Math.round(v*(1-f)+palette[j+1][k]*f));}
  image.data.set([...rgb,255],o);
 }
 rc.putImageData(image,0,0);$('min').textContent=field.log?`10^${lo}`:lo;$('max').textContent=field.log?`10^${hi}`:hi;$('unit').textContent=field.unit;draw();
}
async function show(index){
 const token=++generation;ready=false;$('status').textContent='读取数值帧…';
 try{
  const selected=fields[+$('layer').value],path=selected.files?.[index]??selected.file,header=await npy(path).header();
  const count=selected.files?.length??header.shape[0];
  const data=f16(await getFrame(path,selected.files?0:index));if(token!==generation)return;
  field=selected;[h,w]=header.shape.slice(-2);cell=field.cell;uvw=field.key==='wind'?data:null;
  const n=w*h;values=uvw?Float32Array.from({length:n},(_,i)=>Math.hypot(data[i],data[n+i],data[n*2+i])):data;
  if(values.length!==n)throw Error('数组维度不匹配');
  const fp=field.mask?null:scene.masks.footprint[String(cell)];foot=fp?await loadMask(fp):null;
  if(token!==generation)return;
  mask=new Uint8Array(n);
  if(field.mask)mask.set(await loadMask(field.mask));
  else if(field.key==='wind'&&scene.masks.solid_wind){const sm=scene.masks.solid_wind,sh=await npy(sm.file).header();if(sh.shape.at(-1)===w&&sh.shape.at(-2)===h)mask.set(await getFrame(sm.file,sm.layer));}
  if(field.key==='temp'&&scene.masks.study_area){const study=await loadMask(scene.masks.study_area);if(study.length===n)for(let i=0;i<n;i++)if(!study[i])mask[i]=2;}
  if(token!==generation)return;
  const info=manifest.arrays?.[field.file],time=field.times?.[index]??info?.time_local?.[index]??info?.time_s?.[index]??((field.t0??0)+index*(field.dt??0));
  $('time').textContent=typeof time==='string'?`时间：${time}`:`模拟时间：${Number(time).toFixed(0)} s`;
  $('frame-label').textContent=`${index+1} / ${count}${field.steps?' · 第 '+field.steps[index]+' 步':''}`;$('description').textContent=field.label;
  $('frame').max=count-1;$('frame').value=index;$('frame').disabled=count===1;$('play').disabled=count===1;
  $('geometry-label').textContent=field.solver==='AI4Urban'?'23 台风机位置（白点）':'建筑轮廓';ready=true;paint();
  $('status').textContent=`${w} × ${h} 网格 · ${cell} m / 格 · 数值数组`;
 }catch(e){if(token===generation)$('status').textContent='加载失败：'+e.message;}
}
async function change(){stop();const selected=fields[+$('layer').value];$('lo').value=selected.range[0];$('hi').value=selected.range[1];$('arrows').disabled=selected.key!=='wind';const h=await npy(selected.file).header();await show(selected.files?selected.files.length-1:Math.min(59,h.shape[0]-1));fit();}
$('layer').onchange=change;$('frame').oninput=()=>{stop();show(+$('frame').value);};
$('play').onclick=()=>{if(playing){stop();return;}playing=true;$('play').textContent='暂停';tick(++playback);};
async function tick(epoch){if(!playing||epoch!==playback)return;await show((+$('frame').value+1)%(+$('frame').max+1));if(playing&&epoch===playback)request=setTimeout(()=>tick(epoch),150);}
$('reset').onclick=fit;for(const id of ['lo','hi','buildings'])$(id).oninput=paint;$('arrows').onchange=draw;
canvas.addEventListener('wheel',e=>{e.preventDefault();const f=Math.exp(-e.deltaY*.001),next=Math.max(.1,Math.min(30,scale*f)),ratio=next/scale;px=e.offsetX-(e.offsetX-px)*ratio;py=e.offsetY-(e.offsetY-py)*ratio;scale=next;draw();},{passive:false});
canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY,px,py];canvas.setPointerCapture(e.pointerId);};canvas.onpointerup=()=>drag=null;canvas.onpointercancel=()=>drag=null;
canvas.onpointermove=e=>{
 if(drag){px=drag[2]+e.clientX-drag[0];py=drag[3]+e.clientY-drag[1];draw();return;}
 if(!ready)return;const col=Math.floor((e.offsetX-px)/scale),row=h-1-Math.floor((e.offsetY-py)/scale);if(col<0||col>=w||row<0||row>=h)return;
 const i=row*w+col,origin=scene.grid.domain_origin_xy_m??[0,0];
 const value=mask[i]===2?'无数据':mask[i]===1||foot?.[i]?'建筑 / 固体':`${values[i].toFixed(field.key==='poll'?3:4)} ${field.unit}`;
 $('readout').textContent=`${value}\n网格 (${col}, ${row}) · x ${(origin[0]+(col+.5)*cell).toFixed(0)} m / y ${(origin[1]+(row+.5)*cell).toFixed(0)} m`;
};
try{
 scene=await loadScene();setDataBase(scene.physics);$('title').textContent=scene.title+' · 二维物理场';document.title=$('title').textContent;$('three').href='../3d/?scene='+scene.id;
 const r=await fetch(scene.physics+'manifest.json');if(!r.ok)throw Error('缺少数据清单');manifest=await r.json();
 const names={wind:'风速与风向',temp:'温度',poll:'污染物浓度',flood:'积水深度'};
 for(const key of ['wind','temp','poll','flood']){const l=scene.layers[key];if(l)fields.push({key,file:l.file,cell:l.cell_m,range:key==='poll'?[-1,3]:l.range,log:key==='poll',unit:{wind:'m/s',temp:'°C',poll:'示踪浓度',flood:'m'}[key],name:names[key],label:l.label,t0:l.t0_s,dt:l.step_s});}
 if(scene.layers.solar){const s=scene.layers.solar;for(const [date,d] of Object.entries(s.dates))fields.push({key:'solar',file:d.ghi,cell:s.cell_m,range:[0,1000],unit:'W/m²',name:'日照 · '+d.label,label:'地表总水平辐照度 · '+date});}
 if(scene.id==='region'){
  const r=await fetch(scene.physics+'ai4urban/manifest.json',{cache:'no-cache'});
  if(!r.ok)throw Error('缺少 windfarm 的 AI4Urban 二维结果');
  const ai=await r.json();turbines=ai.turbines;
  for(const f of fields)f.name=f.key==='wind'?'SCALED · 风场（固定高程）':`已有${names[f.key]??f.name}（SCALED 风场驱动）`;
  fields=[...ai.fields,...fields];
  $('title').textContent='Windfarm · 二维风场';document.title=$('title').textContent;
  if(!document.getElementById('crop-link')){const link=document.createElement('a');link.id='crop-link';link.href='../windfarm-crop/';link.textContent='23 台风机 · 4 m 裁剪试验 ↗';document.querySelector('header').append(link);}
 }
 $('layer').replaceChildren(...fields.map((f,i)=>Object.assign(document.createElement('option'),{value:i,textContent:f.name})));
 if(scene.id==='region')$('layer').value=fields.findIndex(f=>f.solver==='AI4Urban'&&f.agl_m===80);
 resize();await change();
 if(scene.id==='region')setInterval(async()=>{
  try{const response=await fetch(scene.physics+'ai4urban/manifest.json',{cache:'no-store'});if(!response.ok)return;const latest=await response.json();
   const selected=fields[+$('layer').value],oldCount=selected.files?.length??1,atEnd=+$('frame').value===oldCount-1;
   for(const f of latest.fields){const existing=fields.find(v=>v.solver==='AI4Urban'&&v.agl_m===f.agl_m);if(existing)Object.assign(existing,f);}
   if(selected.solver==='AI4Urban'&&selected.files?.length>oldCount){$('frame').max=selected.files.length-1;$('frame').disabled=false;$('play').disabled=false;if(atEnd&&!playing)await show(selected.files.length-1);}
  }catch(e){console.warn('等待下一批结果',e);}
 },20000);
}catch(e){$('status').textContent='初始化失败：'+e.message;console.error(e);}
