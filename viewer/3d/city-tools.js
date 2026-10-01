// Presentation adapter: protocol widgets share the existing city camera and geometry.
export async function installCityTools({root, catalogURL, scene, camera, enter, leave, invalidate}) {
  const response = await fetch(catalogURL);
  if (!response.ok) throw Error(`City tools catalogue: HTTP ${response.status}`);
  const catalog = await response.json();
  const {createWidget} = await import(new URL('src/visualization/widgets/binary.mjs', root));
  const panel = document.createElement('section'); panel.id = 'city-tools';
  panel.innerHTML = `<div class="row head">City tools · 2026-09-30</div>
    <select id="city-module" aria-label="City module"><option value="">Existing scene views</option></select>
    <p id="city-note" class="hint"></p><p id="city-status" role="status"></p>
    <div id="city-layer-controls"></div><div id="city-legends"></div>
    <div class="row"><button id="city-play" class="btn">Play</button><input id="city-time" aria-label="City module time" type="range" step="any"><output id="city-clock"></output></div>
    <div id="city-charts"></div><pre id="city-selection"></pre>
    <p class="hint">Roads: © OpenStreetMap contributors (ODbL). Public transport: Powered by TfL Open Data. Recorded snapshot, not live arrivals.</p>`;
  document.getElementById('layers').prepend(panel);
  const $ = id => panel.querySelector('#city-' + id), select = $('module');
  for (const [id,item] of Object.entries(catalog.modules)) select.add(new Option(item.title,id));
  let widgets=[], controller=null, serial=0, playing=false, timer=null, current=null, seconds=0;
  function stop(){playing=false;clearInterval(timer);timer=null;$('play').textContent='Play';}
  function clear(){stop();controller?.abort();widgets.forEach(w=>w.dispose());widgets=[];for(const id of ['layer-controls','legends','charts','selection']) $(id).replaceChildren();invalidate();}
  async function setTime(t){seconds=t;$('time').value=t;$('clock').textContent=`${t.toFixed(0)} s`;await Promise.all(widgets.map(w=>w.setTime(t)));invalidate();}
  async function selectModule(id){
    const version=++serial;clear();current=id;select.value=id;$('status').textContent='';
    const item=catalog.modules[id];document.body.classList.toggle('city-tool-active',Boolean(item));
    if(!item){$('note').textContent='';leave();return;}
    enter();$('note').textContent=item.note;$('status').textContent='Loading…';controller=new AbortController();const signal=controller.signal;
    try{
      const url=new URL(item.manifest,catalogURL),r=await fetch(url,{signal});if(!r.ok)throw Error(`Manifest: HTTP ${r.status}`);
      const manifest=await r.json(),times=manifest.time.samples;
      $('time').min=times[0]||0;$('time').max=times.at(-1)||0;$('time').disabled=$('play').disabled=times.length<2;
      for(const layer of manifest.layers){
        const row=document.createElement('label');row.className='layer';const toggle=document.createElement('input');toggle.type='checkbox';toggle.checked=true;row.append(toggle,document.createTextNode(layer.id));$('layer-controls').append(row);
        const widget=createWidget(layer);
        try{await widget.load({scene,camera,manifest,baseURL:url,boundsSize:manifest.spatial.bounds_m.max.map((v,i)=>v-manifest.spatial.bounds_m.min[i]),charts:$('charts'),availability(id,available,error){if(error)$('status').textContent=error;invalidate();},addLegend(layer,text){const p=document.createElement('p');p.className='hint';p.textContent=`${layer.id}: ${text}`;$('legends').append(p);return()=>p.remove();}},layer,signal);}catch(error){widget.dispose();throw error;}
        if(version!==serial){widget.dispose();return;}
        if(layer.format==='json'&&layer.kind==='scalar_field'&&widget.instances){const ratio=4/widget.scale;widget.instances.geometry.scale(ratio,ratio,ratio);}
        widgets.push(widget);
        toggle.addEventListener('change',()=>{widget.setVisible(toggle.checked);invalidate();});
        const opacity=document.createElement('input');opacity.type='range';opacity.min=0;opacity.max=1;opacity.step=.05;opacity.value=1;opacity.setAttribute('aria-label',`${layer.id} opacity`);opacity.addEventListener('input',()=>{widget.setOpacity(+opacity.value);invalidate();});row.append(opacity);
      }
      await setTime(times[0]||0);if(version===serial)$('status').textContent=`${widgets.length} / ${manifest.layers.length} layers ready`;
    }catch(error){if(version===serial&&!signal.aborted){clear();$('status').textContent=`Unable to load: ${error.message}`;}}
  }
  select.addEventListener('change',()=>selectModule(select.value));$('time').addEventListener('input',()=>{stop();setTime(+$('time').value);});
  $('play').addEventListener('click',()=>{
    if(playing){stop();return;}playing=true;$('play').textContent='Pause';if(seconds>=+$('time').max)seconds=+$('time').min;
    let busy=false;timer=setInterval(async()=>{if(busy||document.hidden)return;busy=true;try{await setTime(Math.min(+$('time').max,seconds+(current==='diurnal'?600:1)));if(seconds>=+$('time').max)stop();}finally{busy=false;}},100);
  });
  const {Raycaster,Vector2}=await import('three'),raycaster=new Raycaster(),canvas=document.getElementById('gl');
  canvas.addEventListener('click',event=>{if(!current)return;const r=canvas.getBoundingClientRect();raycaster.setFromCamera(new Vector2((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1),camera);const hit=widgets.map(w=>w.pick({raycaster})).filter(Boolean).sort((a,b)=>a.distance-b.distance)[0];$('selection').textContent=hit?JSON.stringify(hit,null,2):'';});
  // Existing scene buttons resume their own clocks and rendering.
  document.getElementById('tabs').addEventListener('click',event=>{if(event.target.closest('button')&&current){++serial;clear();current=null;document.body.classList.remove('city-tool-active');select.value='';$('status').textContent='';$('note').textContent='';}},true);
  window.cityTools={selectModule,setTime,get widgets(){return widgets;},get current(){return current;},dispose(){++serial;clear();panel.remove();}};
  const requested=new URLSearchParams(location.search).get('module');if(catalog.modules[requested])await selectModule(requested);
}
