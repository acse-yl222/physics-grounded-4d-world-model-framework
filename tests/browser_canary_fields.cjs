(async()=>{
const fs=require('node:fs'),assert=require('node:assert/strict');const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
const out=process.env.FIELDS_REPORT_DIR||'project/tower_hamlets/reports/fields027';fs.mkdirSync(out,{recursive:true});
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
try{const p=await b.newPage();await p.setViewport({width:1440,height:1000});const errors=[],failed=[];p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))failed.push([r.status(),r.url()]);});
if(process.env.FIELDS_PAGES_MODE==='1'){await p.setRequestInterception(true);p.on('request',r=>new URL(r.url()).pathname.endsWith('/viewer/config.js')?r.respond({status:200,contentType:'application/javascript',body:'export const ON_PAGES = true;'}):r.continue());}
await p.goto(process.env.FIELDS_URL||'http://127.0.0.1:8895/viewer/3d/?scene=tower_hamlets&lite=1&pose=overhead&hold=1&play=0',{waitUntil:'domcontentloaded',timeout:180000});
await p.waitForFunction(()=>window.viewer&&document.querySelector('#loading').classList.contains('hide'),{timeout:240000});
const config=await p.evaluate(()=>({wind:viewer.LAYERS.wind,keys:Object.keys(viewer.LAYERS),physics:viewer.SCENE.physics,grid:viewer.SCENE.grid}));assert.equal(config.wind.cell_m,4);assert.equal(config.wind.y,2);assert.equal(config.wind.particle_time_scale,Number(process.env.FIELDS_PARTICLE_SCALE||1));if(process.env.FIELDS_WIND_FRAMES)assert.equal(config.wind.frames,Number(process.env.FIELDS_WIND_FRAMES));assert.equal(config.grid.cols,1000);for(const k of ['wind','temp','poll','solar','flood'])assert.ok(config.keys.includes(k));
const reports=[];
for(const key of ['wind','temp','poll','solar','flood']){
 await p.evaluate(key=>document.querySelector(`[data-field="${key}"]`).click(),key);
 await p.waitForFunction(key=>viewer.state.phase===key&&!viewer.state.loading&&viewer.state.fields[key],{timeout:180000},key);
 await p.evaluate(()=>{if(viewer.state.playing)document.querySelector('#play').click();const s=document.querySelector('#step');s.value=s.max;s.dispatchEvent(new Event('input',{bubbles:true}));});
 await p.waitForFunction(()=>!viewer.state.loading,{timeout:180000});
 const report=await p.evaluate(async key=>{const {getFrame,loadMask,npy}=await import('../npy.js');const layer=viewer.LAYERS[key];const file=key==='solar'?Object.values(layer.dates)[0].ghi:layer.file;const {hasLayer,getFrameF32}=await import('../frames.js');const frameKey=key==='solar'?'solar_'+Object.keys(layer.dates)[0]:key;const expected=hasLayer(frameKey)?await getFrameF32(frameKey,layer.frames-1):await getFrame(file,layer.frames-1);const actual=viewer.state.fields[key];let err=0,min=Infinity,max=-Infinity;for(let i=0;i<actual.length;i++){err=Math.max(err,Math.abs(actual[i]-expected[i]));min=Math.min(min,actual[i]);max=Math.max(max,actual[i]);}const maskFile=viewer.SCENE.masks.layer_invalid?.[key];let invalid=0,badAlpha=0;if(maskFile||key==='wind'){const mask=key==='wind'?await npy(viewer.SCENE.masks.solid_wind.file).read(0):await loadMask(maskFile),pixels=viewer.planes[key].data;for(let i=0;i<mask.length;i++)if(mask[i]){invalid++;if(pixels[i*4+3]!==0)badAlpha++;}}return{key,length:actual.length,maxError:err,min,max,invalid,badAlpha,label:document.querySelector('#time-label').textContent,camera:viewer.camera.position.toArray()};},key);
 assert.equal(report.maxError,0);assert.equal(report.badAlpha,0);assert.ok(Number.isFinite(report.max)&&report.max>0);if(key==='wind')assert.ok(report.label.includes('Model step 100'));if(key==='flood')assert.ok(report.invalid>900000);reports.push(report);
 await new Promise(r=>setTimeout(r,2500));await p.screenshot({path:`${out}/${key}.png`});console.log(JSON.stringify(report));
}
// Verify genuine frame selection and playback across the longer wind sequence.
await p.evaluate(()=>document.querySelector('[data-field="wind"]').click());
await p.waitForFunction(()=>viewer.state.phase==='wind'&&!viewer.state.loading);
const windSamples=[];
for(const step of [1,Math.ceil(config.wind.frames/2),config.wind.frames]){
 await p.evaluate(step=>{if(viewer.state.playing)document.querySelector('#play').click();const slider=document.querySelector('#step');slider.value=step;slider.dispatchEvent(new Event('input',{bubbles:true}));},step);
 await p.waitForFunction(step=>!viewer.state.loading&&viewer.state.step===step,{timeout:180000},step);
 windSamples.push(await p.evaluate(()=>({step:viewer.state.step,label:document.querySelector('#time-label').textContent,sum:viewer.state.fields.wind.reduce((a,v)=>a+v,0)})));
}
assert.equal(new Set(windSamples.map(x=>x.sum)).size,3);
await p.evaluate(()=>{const slider=document.querySelector('#step');slider.value=1;slider.dispatchEvent(new Event('input',{bubbles:true}));});
await p.waitForFunction(()=>!viewer.state.loading&&viewer.state.step===1);
await p.evaluate(()=>document.querySelector('#play').click());
await p.waitForFunction(()=>viewer.state.step>=3,{timeout:30000});
await p.evaluate(()=>{if(viewer.state.playing)document.querySelector('#play').click();});
await p.evaluate(()=>{document.querySelector('[data-field="solar"]').click();const s=document.querySelector('#solar-mode');s.value='shadow';s.dispatchEvent(new Event('change'));});await p.waitForFunction(()=>viewer.state.fields.shadow&&!viewer.state.loading,{timeout:180000});
assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);const report={passed:true,config,fields:reports,windSamples,errors,failed};fs.writeFileSync(out+'/report.json',JSON.stringify(report,null,2));
}finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1)});
