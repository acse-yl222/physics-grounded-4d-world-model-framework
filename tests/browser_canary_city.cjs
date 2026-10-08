(async()=>{
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
const out=process.env.UWM_BROWSER_OUTPUT||'cache/tower_hamlets/city022_browser';fs.mkdirSync(out,{recursive:true});
const browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
try{
const page=await browser.newPage();await page.setViewport({width:1600,height:1050});const errors=[],failures=[];page.on('pageerror',x=>errors.push(x.message));page.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))failures.push([r.status(),r.url()]);});
await page.goto('http://127.0.0.1:8878/src/visualization/legacy/viewer/3d/?scene=tower_hamlets&lite=0&expansion=0&cam=2900,4200,3600,0,20,0&t=300&play=0',{waitUntil:'domcontentloaded',timeout:180000});
await page.waitForFunction(()=>window.viewer&&document.querySelector('#loading').classList.contains('hide')&&viewer.traffic,{timeout:180000});
assert.equal(await page.$eval('#scene-select',x=>x.value),'tower_hamlets');
await page.evaluate(()=>{viewer.traffic.t=300;viewer.traffic.playing=false;viewer.traffic.update(300);});await page.screenshot({path:path.join(out,'overview.png')});
await page.evaluate(()=>{window.auditGround=[];viewer.model.traverse(o=>{if(o.isMesh&&o.userData.building_id==='site-support'){o.geometry.computeBoundingBox();const b=o.geometry.boundingBox;if(b.min.x < -1900&&b.max.x>1900&&b.max.y<0){auditGround.push(o);o.visible=false;}}});viewer.renderer.render(viewer.scene,viewer.camera);});await page.screenshot({path:path.join(out,'diagnostic-ground-hidden.png')});await page.evaluate(()=>{auditGround.forEach(o=>o.visible=true);viewer.renderer.render(viewer.scene,viewer.camera);});
const fields=[];
for(const key of ['wind','temp']){
await page.click('.tab[data-field="'+key+'"]');
await page.evaluate(()=>{document.querySelector('#auto').checked=false;if(viewer.state.playing)document.querySelector('#play').click();const s=document.querySelector('#step');s.value=s.max;s.dispatchEvent(new Event('input',{bubbles:true}));});
await page.waitForFunction(k=>viewer.state.phase===k&&!viewer.state.loading&&viewer.state.fields[k]&&viewer.state.step===31,{},key);
const check=await page.evaluate(async key=>{
const L=viewer.LAYERS[key],{getFrame,f16}=await import('/src/visualization/legacy/viewer/npy.js');const raw=f16(await getFrame(L.file,L.frames-1)),display=viewer.state.fields[key];let error=0;for(let i=0;i<raw.length;i++)error=Math.max(error,Math.abs(raw[i]-display[i]));
const plane=viewer.planes[key];return{key,error,length:display.length,finite:display.every(Number.isFinite),clock:document.querySelector('#time-label').textContent,grid:viewer.LG[key],planePosition:plane.mesh.position.toArray()};},key);
assert.equal(check.error,0);assert.ok(check.finite);assert.ok(check.clock.includes('600 s'));fields.push(check);
if(key==='wind'){await page.$eval('#l-part',x=>{x.checked=true;x.dispatchEvent(new Event('change',{bubbles:true}));});}
await new Promise(r=>setTimeout(r,600));await page.screenshot({path:path.join(out,key+'.png')});if(key==='wind')await page.$eval('#l-part',x=>{x.checked=false;x.dispatchEvent(new Event('change',{bubbles:true}));});
if(key==='temp'){await page.select('#temp-mode','iso');await new Promise(r=>setTimeout(r,500));const iso=await page.evaluate(()=>{const line=viewer.scene.children.find(o=>o.isLineSegments2&&o.renderOrder===3);const a=line?.geometry.attributes.instanceStart;return{count:a?.count,finite:a?.data.array.every(Number.isFinite)}});assert.ok(iso.count>0&&iso.finite);fields.at(-1).isotherms=iso;await page.screenshot({path:path.join(out,'isotherms.png')});}
}
const traffic=await page.evaluate(()=>{const T=viewer.traffic;T.playing=false;T.update(300);const count=T.count;T.t=599.9;T.playing=true;T.tick(performance.now(),1);return{start:T.start,end:T.end,countAt300:count,stoppedAt:T.t,playing:T.playing};});assert.equal(traffic.start,1);assert.equal(traffic.end,600);assert.ok(traffic.countAt300>0);assert.equal(traffic.stoppedAt,600);assert.equal(traffic.playing,false);
await page.click('.tab[data-shot="trafficMap"]');await page.evaluate(()=>{viewer.traffic.playing=false;viewer.traffic.t=300;viewer.traffic.update(300);});await new Promise(r=>setTimeout(r,1200));await page.screenshot({path:path.join(out,'traffic.png')});
assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({passed:true,fields,traffic,errors,failures},null,2));console.log(JSON.stringify({passed:true,fields,traffic}));
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
