(async()=>{
const fs=require('node:fs'),assert=require('node:assert/strict');const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
const out=process.env.DENSITY_REPORT_DIR||'cache/framework/city-density026';fs.mkdirSync(out,{recursive:true});
const browser=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
const reports=[];
try{for(const id of (process.env.DENSITY_SCENES||'south_kensington,white_city,tower_hamlets').split(',')){
const page=await browser.newPage();await page.setViewport({width:1440,height:1000});const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});
if(process.env.DENSITY_PAGES_MODE==='1'){await page.setRequestInterception(true);page.on('request',r=>new URL(r.url()).pathname.endsWith('/viewer/config.js')?r.respond({status:200,contentType:'application/javascript',body:'export const ON_PAGES = true;'}):r.continue());}
const url=(process.env.DENSITY_BASE||'http://127.0.0.1:8893/src/visualization/legacy/viewer/3d/')+`?scene=${id}&lite=${process.env.DENSITY_LITE??1}&pose=campus&shot=uavs&hold=1&play=0&t=300`;
await page.goto(url,{waitUntil:'domcontentloaded',timeout:180000});await page.waitForFunction(()=>window.viewer&&(viewer.uavs||viewer.replay)&&document.querySelector('#loading').classList.contains('hide'),{timeout:240000});
await page.evaluate(()=>document.querySelector('[data-shot="uavs"]').click());
await new Promise(r=>setTimeout(r,4000));
await page.evaluate(()=>{const u=viewer.uavs||viewer.replay;u.playing=false;if(viewer.traffic)viewer.traffic.playing=false;u.update(300);});
const report=await page.evaluate(()=>{const u=viewer.uavs||viewer.replay;u.update(60);const a=u.uavs.map(x=>[x.x,x.y,x.z]);u.update(80);const b=u.uavs.map(x=>[x.x,x.y,x.z]);u.update(60);return{scene:viewer.SCENE.id,count:u.uavs.length,routes:u.flightData.routes.length,stations:u.flightData.stations.length,lineWidth:u.corridors.material.linewidth,thick:u.corridors.isLineSegments2,moved:JSON.stringify(a)!==JSON.stringify(b),repeatable:JSON.stringify(a)===JSON.stringify(u.uavs.map(x=>[x.x,x.y,x.z])),active:u.actors.uavs.activeCount,contextLost:viewer.renderer.getContext().isContextLost(),cameraFinite:viewer.camera.position.toArray().every(Number.isFinite),cameraPosition:viewer.camera.position.toArray()};});
assert.equal(report.contextLost,false);assert.ok(report.cameraFinite);assert.ok(report.cameraPosition[1]>0&&Math.hypot(...report.cameraPosition)<20000);assert.equal(report.count,600);assert.equal(report.active,600);assert.equal(report.routes,100);assert.equal(report.stations,id==='tower_hamlets'?20:30);assert.ok(report.lineWidth>=2&&report.thick&&report.moved&&report.repeatable);
await page.evaluate(()=>document.querySelector('#l-uavs').click());assert.ok(await page.evaluate(()=>{const u=viewer.uavs||viewer.replay;return !u.corridors.visible&&!u.markers.visible;}));await page.evaluate(()=>document.querySelector('#l-uavs').click());
await new Promise(r=>setTimeout(r,2800));await page.screenshot({path:`${out}/${id}-uavs.png`});
if(process.env.DENSITY_CHECK_TRAFFIC==='1'){
 await page.waitForFunction(()=>viewer.traffic||viewer.replay?.traffic,{timeout:180000});
 const t=await page.evaluate(()=>{if(viewer.traffic){const t=viewer.traffic;t.playing=false;t.t=600;t.update(600);return{count:t.count,peak:t.manifest.vehicles_peak,end:t.end};}const r=viewer.replay;r.playing=false;r.update(600);return{count:r.cars.length,peak:Math.max(...r.traffic.frames.map(f=>f.count)),end:r.traffic.lastTime};});
 assert.ok(t.peak>({south_kensington:1500,white_city:1060,tower_hamlets:1055}[id]));assert.equal(t.end,1200);assert.ok(t.count>({south_kensington:1500,white_city:1060,tower_hamlets:1055}[id]));report.traffic=t;
}
assert.deepEqual(errors,[]);report.errors=errors;reports.push(report);console.log(JSON.stringify(report));await page.close();
}fs.writeFileSync(out+'/report.json',JSON.stringify({passed:true,scenes:reports},null,2));}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
