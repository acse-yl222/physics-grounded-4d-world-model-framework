import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { registry } from '../widgets/index.mjs';
import { createWidget } from '../widgets/binary.mjs';
import { enuToWorld } from '../shared/time.mjs';

const $=id=>document.getElementById(id),viewport=$('viewport');
const scene=new THREE.Scene();scene.background=new THREE.Color(0x111923);
const camera=new THREE.PerspectiveCamera(45,1,.01,1e7);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));viewport.prepend(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
const ambient=new THREE.HemisphereLight(0xdff5ff,0x38514e,2.5);scene.add(ambient);const sun=new THREE.DirectionalLight(0xffffff,3);sun.position.set(300,500,150);scene.add(sun);
const raycaster=new THREE.Raycaster();const widgets=[],rows=new Map();let manifest,playing=false,previous=performance.now(),disposed=false;
const abort=new AbortController();
let solarFrames=null,solarMode='irradiance';
function solarLighting(seconds){
 if(!solarFrames)return;
 let i=0;while(i<solarFrames.length-2&&solarFrames[i+1].seconds<=seconds)i++;
 const a=solarFrames[i],b=solarFrames[i+1],t=Math.max(0,Math.min(1,(seconds-a.seconds)/(b.seconds-a.seconds)));
 const altitude=a.altitude_deg+(b.altitude_deg-a.altitude_deg)*t,azimuth=a.azimuth_deg+(((b.azimuth_deg-a.azimuth_deg+540)%360)-180)*t;
 const alt=altitude*Math.PI/180,az=azimuth*Math.PI/180;
 const center=manifest.spatial.bounds_m.min.map((v,j)=>(v+manifest.spatial.bounds_m.max[j])/2);sun.target.position.set(...enuToWorld(center));scene.add(sun.target);
 sun.position.copy(sun.target.position).add(new THREE.Vector3(Math.cos(alt)*Math.sin(az),Math.sin(alt),-Math.cos(alt)*Math.cos(az)).multiplyScalar(3000));
 const daylight=Math.max(0,Math.sin(alt));sun.intensity=3*daylight;ambient.intensity=.18+1.8*Math.sqrt(daylight);
 scene.background.set(altitude>0?0x233748:0x080d18);
 $('solar-readout').textContent=`太阳高度 ${altitude.toFixed(1)}° · ${altitude>0?'日间':'夜间'} · ${['sky_view','sunlit_hours'].includes(solarMode)?'此图层为全天静态结果':'按已计算数据播放'}`;
}
function setupSolar(frames){
 solarFrames=frames;const panel=document.createElement('section');panel.id='solar-tools';
 panel.innerHTML='<h2>日照展示</h2><label>显示模式 <select id=solar-mode aria-label=日照显示模式><option value=shadow>阴影 · 深蓝遮阴 / 浅黄受光</option><option value=irradiance>辐照度 · 蓝低 / 红高</option><option value=sky_view>天空可见度 · 全天静态</option><option value=sunlit_hours>日照时长 · 全天静态</option><option value=model>仅模型 · 随太阳改变照明</option></select></label><div id=solar-presets></div><p id=solar-readout></p><p>下方滑块只调透明度。切换模式会关闭其他计算图层，避免互相遮盖。</p>';
 $('status').after(panel);
 const full=document.createElement('a');full.href='/src/visualization/legacy/viewer/3d/?scene_config=/project/south_ken/runs/img2city_original_page_20261005/scene.json&lite=0&pose=campus&shot=traffic&play=0';full.textContent='打开原版完整功能（含参考演示数据）';full.style.cssText='display:block;color:#9ce9f2;margin-bottom:10px';panel.prepend(full);
 const choose=mode=>{solarMode=mode;$('solar-mode').value=mode;for(const w of widgets.filter(w=>w.layer.kind==='scalar_field')){const on=w.layer.id===mode;w.setVisible(on);rows.get(`${w.context.manifest.run_id}:${w.layer.id}`).querySelector('input[type=checkbox]').checked=on;}solarLighting(Number($('time').value));invalidate();};
 $('solar-mode').addEventListener('change',()=>choose($('solar-mode').value));
 for(const [label,hour] of [['清晨',6],['正午',12],['傍晚',18],['夜间',0]]){const b=document.createElement('button');b.textContent=label;b.addEventListener('click',()=>{playing=false;$('play').textContent='Play';setTime(hour*3600);});$('solar-presets').append(b);}
 for(const w of widgets.filter(w=>w.layer.kind==='scalar_field')){const cb=rows.get(`${w.context.manifest.run_id}:${w.layer.id}`).querySelector('input[type=checkbox]');cb.addEventListener('change',()=>choose(cb.checked?w.layer.id:'model'));}
 choose('shadow');
}
let animationId=0,dirty=true;
const performanceStats={renders:0};
function invalidate(){dirty=true;if(!disposed&&!document.hidden&&!animationId)animationId=requestAnimationFrame(animate);}
controls.addEventListener('change',invalidate);
const resize=new ResizeObserver(()=>{const {width,height}=viewport.getBoundingClientRect();camera.aspect=width/height;camera.updateProjectionMatrix();renderer.setSize(width,height);invalidate();});resize.observe(viewport);
function fit(){if(!manifest)return;const {min,max}=manifest.spatial.bounds_m;const center=min.map((v,i)=>(v+max[i])/2),span=Math.max(...max.map((v,i)=>v-min[i]),1);controls.target.set(...enuToWorld(center));const radius=Math.hypot(...max.map((v,i)=>v-min[i]))/2||1;const halfFov=Math.min(camera.fov*Math.PI/360,Math.atan(Math.tan(camera.fov*Math.PI/360)*camera.aspect));const distance=radius/Math.sin(halfFov)*1.15;camera.position.copy(controls.target).add(new THREE.Vector3(1,.85,1).normalize().multiplyScalar(distance));camera.near=Math.max(span/10000,.001);camera.far=span*100;camera.updateProjectionMatrix();controls.update();}
function setTime(value){solarLighting(Number(value));$('time').value=value;$('clock').textContent=manifest?.time?.epoch?new Date(Date.parse(manifest.time.epoch)+Number(value)*1000).toISOString().slice(11,16)+' UTC':`${Number(value).toFixed(2)} s`;widgets.forEach(w=>{if(w.layer.sampling!=='static'||w.layer.kind==='time_series')w.setTime(Number(value)-(w.timeOffset||0));});invalidate();}
$('time').addEventListener('input',()=>setTime($('time').value));
$('play').addEventListener('click',()=>{if(!playing&&Number($('time').value)>=Number($('time').max))setTime($('time').min);playing=!playing;$('play').textContent=playing?'Pause':'Play';invalidate();});
$('fit').addEventListener('click',fit);
function showSelection(selection){$('selection').textContent=selection?JSON.stringify(selection,null,2):'No object selected.';}
renderer.domElement.addEventListener('click',event=>{const rect=renderer.domElement.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);showSelection(widgets.map(w=>w.pick({raycaster})).filter(Boolean).sort((a,b)=>a.distance-b.distance)[0]);});
$('charts').addEventListener('click',event=>showSelection(widgets.map(w=>w.pick({chart:event.target,raycaster})).find(Boolean)));
function validateManifest(m){
  if(!['1.0.0','1.1.0'].includes(m.schema_version))throw new Error(`Unsupported protocol ${m.schema_version}`);
  if(m.status!=='complete')throw new Error('This run is not complete.');
  if(m.spatial?.frame!=='ENU'||m.spatial?.units!=='m'||m.time?.unit!=='s')throw new Error('Unsupported spatial/time units');
  const {min,max}=m.spatial.bounds_m||{};if(![min,max].every(v=>Array.isArray(v)&&v.length===3&&v.every(Number.isFinite))||min.some((v,i)=>v>max[i]))throw new Error('Invalid scene bounds');
  const times=m.time.samples;if(!Array.isArray(times)||!times.every((v,i)=>Number.isFinite(v)&&(!i||v>times[i-1])))throw new Error('Invalid time axis');
  if(!Array.isArray(m.layers)||!m.layers.length||new Set(m.layers.map(l=>l.id)).size!==m.layers.length)throw new Error('Missing or duplicate layers');
  if(m.layers.some(l=>l.sampling!=='static')!==Boolean(times.length))throw new Error('Time axis does not match layer sampling');
}
async function json(url){const response=await fetch(url,{signal:abort.signal});if(!response.ok)throw new Error(`Data not found (${response.status}): ${url}`);return response.json();}
async function load(){
  const params=new URLSearchParams(location.search),requested=params.get('manifest');
  const catalogURL=new URL('../../../project/index.json',location.href);
  let catalog={scenes:[]};try{catalog=await json(catalogURL);}catch{}
  for(const item of catalog.scenes){const option=document.createElement('option');option.value=item.scene_id;option.textContent=item.title;$('scene').append(option);}
  const siteRoot=new URL('../../../',location.href);
  try{const published=await json(new URL('src/visualization/public-scenes.json',siteRoot));const group=document.createElement('optgroup');group.label='Published scene viewers';
    for(const item of published.scenes){const option=document.createElement('option');option.value='published:'+item.scene_id;option.textContent=item.title;option.dataset.viewer=new URL(item.viewer_url,siteRoot).href;group.append(option);}$('scene').append(group);
  }catch{}
  let chosen=params.get('scene')||(!requested?catalog.default:'');
  $('scene').value=chosen||'';
  $('scene').addEventListener('change',()=>{const published=$('scene').selectedOptions[0]?.dataset.viewer;if(published){location.href=published;return;}const next=new URL(location.href);next.search='';if($('scene').value)next.searchParams.set('scene',$('scene').value);else next.searchParams.set('manifest','../../../examples/contract-v1/manifest.json');location.href=next;});
  const runs=[];let selections=null,metadata=null,timeMode='relative';
  if(chosen){
    if(!/^[a-z][a-z0-9_]*$/.test(chosen))throw new Error('Invalid scene ID');
    const projectBase=new URL(`${chosen}/`,catalogURL),project=await json(new URL('project.json',projectBase));metadata=project;
    const viewID=params.get('view')||project.default_view;if(!/^[a-z][a-z0-9_]*$/.test(viewID))throw new Error('Invalid view ID');
    const view=await json(new URL(`views/${viewID}.json`,projectBase));
    if(view.scene_id!==chosen||project.scene_id!==chosen)throw new Error('Scene/view identity mismatch');
    timeMode=view.time_alignment;if(!['relative','absolute'].includes(timeMode))throw new Error('Unknown time alignment');
    selections=view.layers;
    const available=catalog.scenes.find(s=>s.scene_id===chosen)?.views||[viewID];
    for(const id of available){const option=document.createElement('option');option.value=id;option.textContent=id;$('view').append(option);}$('view').value=viewID;
    $('view').addEventListener('change',()=>{const next=new URL(location.href);next.searchParams.set('view',$('view').value);location.href=next;});
    for(const id of view.runs){if(!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(id))throw new Error('Invalid run ID');const url=new URL(`runs/${id}/manifest.json`,projectBase);const data=await json(url);validateManifest(data);if(data.scene_id!==chosen||JSON.stringify(data.spatial.origin)!==JSON.stringify(project.spatial.origin))throw new Error('Run coordinates do not match the selected scene');runs.push({manifest:data,url});}
  }else{
    $('view').hidden=true;
    const url=new URL(requested||'../../../examples/contract-v1/manifest.json',location.href);if(url.origin!==location.origin)throw new Error('Choose a same-origin run.');
    const data=await json(url);validateManifest(data);runs.push({manifest:data,url});
  }
  if(!runs.length)throw new Error('No runs in this view');
  const epochs=runs.filter(r=>r.manifest.time.samples.length).map(r=>Date.parse(r.manifest.time.epoch));
  if(timeMode==='absolute'&&epochs.some(e=>!Number.isFinite(e)))throw new Error('Absolute alignment requires epochs for dynamic runs');
  const baseEpoch=timeMode==='absolute'?Math.min(...epochs):0;
  for(const run of runs)run.offset=timeMode==='absolute'&&run.manifest.time.samples.length?(Date.parse(run.manifest.time.epoch)-baseEpoch)/1000:0;
  const times=[...new Set(runs.flatMap(r=>r.manifest.time.samples.map(t=>t+r.offset)))].sort((a,b)=>a-b);
  manifest={...runs[0].manifest,spatial:metadata?.spatial||runs[0].manifest.spatial,time:{unit:'s',samples:times,...(runs.length===1&&runs[0].manifest.time.epoch?{epoch:runs[0].manifest.time.epoch}:{})}};
  $('title').textContent=metadata?.title||manifest.provenance?.parameters?.preview_title||`${manifest.scene_id} · ${manifest.simulation}`;
  if(requested)$('scene').options[0].textContent=$('title').textContent;
  $('source-note').textContent=manifest.provenance?.parameters?.display_note|| (manifest.provenance?.parameters?.synthetic?'Synthetic protocol example':`${runs.length} run(s) · ${timeMode} time`);
  const boundsSize=manifest.spatial.bounds_m.max.map((v,i)=>v-manifest.spatial.bounds_m.min[i]);
  let total=0;
  for(const run of runs){
    for(const layer of run.manifest.layers){
      const selected=selections?.find(s=>s.run_id===run.manifest.run_id&&s.layer_id===layer.id);if(selections&&!selected)continue;
      total++;const key=`${run.manifest.run_id}:${layer.id}`;
      const context={scene,camera,manifest:run.manifest,boundsSize,baseURL:run.url,charts:$('charts'),
        availability(id,available,error){invalidate();const row=rows.get(key);if(row)row.querySelector('small').textContent=error?`Unavailable: ${error}`:available?'':'No data at this time';},
        addLegend(layer,text){const p=document.createElement('p');p.textContent=`${layer.id}: ${text}`;$('legends').append(p);return()=>p.remove();}};
      const row=document.createElement('div');row.className='layer';const label=document.createElement('label');const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=selected?.visible??!run.manifest.provenance?.parameters?.initially_hidden_layers?.includes(layer.id);checkbox.disabled=true;label.append(checkbox,document.createTextNode(run.manifest.provenance?.parameters?.layer_labels?.[layer.id]||(runs.length>1?`${run.manifest.run_id} / ${layer.id}`:layer.id)));const status=document.createElement('small');status.textContent='Loading…';row.append(label,status);$('layers').append(row);rows.set(key,row);
      let widget;
      try{widget=createWidget(layer);await widget.load(context,layer,abort.signal);widget.timeOffset=run.offset;widgets.push(widget);widget.setVisible(checkbox.checked);checkbox.disabled=false;checkbox.addEventListener('change',()=>{widget.setVisible(checkbox.checked);invalidate();});
        if(layer.display.capabilities.includes('opacity')){const opacity=document.createElement('input');opacity.type='range';opacity.min=0;opacity.max=1;opacity.step=.05;opacity.value=widget.initialOpacity??1;opacity.setAttribute('aria-label',`${layer.id} opacity`);opacity.addEventListener('input',()=>{widget.setOpacity(Number(opacity.value));invalidate();});row.append(opacity);}status.textContent='';
      }catch(error){widget?.dispose();status.textContent=`Unavailable: ${error.message}`;checkbox.checked=false;}
    }
  }
  if(selections&&total!==selections.length)throw new Error('View references a missing layer');
  $('status').textContent=`${widgets.length} / ${total} layers ready`;
  if(runs.length===1 && manifest.simulation==='img2city_solar'){const artifact=manifest.artifacts?.find(a=>a.id==='asset_frames');if(artifact)setupSolar(await json(new URL(artifact.asset,runs[0].url)));}
  $('time').min=times[0]||0;$('time').max=times.at(-1)||0;$('time').disabled=times.length<2;$('play').disabled=times.length<2;$('rate').value=String(manifest.provenance?.parameters?.playback_rate||1);setTime(solarFrames?64800:(manifest.provenance?.parameters?.initial_time_s??times[0]??0));fit();
  window.urbanViewer={performanceStats,get manifest(){return manifest;},get widgets(){return widgets;},setTime,fit,dispose};
}
function animate(now){
  animationId=0;if(disposed||document.hidden){previous=0;return;}
  const dt=previous?(now-previous)/1000:0;previous=now;
  if(playing){const next=Math.min(Number($('time').max),Number($('time').value)+dt*Number($('rate').value));setTime(next);if(next>=Number($('time').max)){playing=false;$('play').textContent='Play';}}
  controls.update();
  if(dirty){dirty=false;renderer.render(scene,camera);performanceStats.renders++;}
  if(playing&&!animationId)animationId=requestAnimationFrame(animate);else if(!animationId)previous=0;
}
document.addEventListener('visibilitychange',()=>{if(animationId)cancelAnimationFrame(animationId);animationId=0;previous=0;if(!document.hidden)invalidate();});
function dispose(){if(disposed)return;disposed=true;if(animationId)cancelAnimationFrame(animationId);abort.abort();widgets.forEach(w=>w.dispose());controls.dispose();resize.disconnect();renderer.dispose();}
window.addEventListener('pagehide',dispose,{once:true});
load().catch(error=>{$('error').hidden=false;$('error').textContent=error.message;$('status').textContent='Unable to load this run';});invalidate();
