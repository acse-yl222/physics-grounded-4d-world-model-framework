(async()=>{
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const assert=require('node:assert/strict'),fs=require('node:fs');
 const browser=await puppeteer.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1280,height:900});
  await page.evaluateOnNewDocument(()=>{window.canvasCopies=0;const original=CanvasRenderingContext2D.prototype.drawImage;CanvasRenderingContext2D.prototype.drawImage=function(...args){window.canvasCopies++;return original.apply(this,args)};});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(new URL('viewer/windfarm-movie/',process.env.P4D_SITE_URL||'http://127.0.0.1:8773/').href);
  await page.waitForFunction(()=>window.movie?.metrics.renders>0,{timeout:120000});
  const read=()=>page.evaluate(()=>({...movie.metrics,copies:window.canvasCopies,drawCalls:movie.renderer.info.render.calls,triangles:movie.renderer.info.render.triangles,batches:movie.staticBatchStats,time:Number(document.querySelector('#time').value)}));
  const before=await read();await new Promise(r=>setTimeout(r,1500));const idle=await read();
  assert.equal(idle.renders,before.renders,'Static comparison must not redraw');assert.equal(idle.copies,0);
  await page.select('#model','jensen04');await page.waitForFunction(n=>movie.metrics.fieldUpdates>n,{},idle.fieldUpdates);
  const changed=await read();assert.equal(changed.fieldUpdates,idle.fieldUpdates+1);
  await page.select('#model','mac_live');await new Promise(r=>setTimeout(r,1500));const live=await read();
  assert.ok(live.time>0);assert.ok(live.renders>changed.renders);assert.equal(live.copies,0,'Live playback must not copy WebGL frames to Canvas2D');
  await page.click('#play');await new Promise(r=>setTimeout(r,200));const paused=await read();
  await new Promise(r=>setTimeout(r,1000));const held=await read();assert.equal(held.time,paused.time);assert.equal(held.renders,paused.renders);
  await page.click('#play');
  const background=await browser.newPage();await background.bringToFront();await page.waitForFunction(()=>document.hidden);
  const hidden=await read();await new Promise(r=>setTimeout(r,600));assert.deepEqual(await read(),hidden,'Hidden windfarm must stop rendering and advancing time');
  await page.bringToFront();await page.waitForFunction(n=>movie.metrics.renders>n,{},hidden.renders);await background.close();
  await page.click('#play');await page.waitForFunction(()=>document.querySelector('#play').textContent==='Play');
  await page.setViewport({width:800,height:600});await page.waitForFunction(()=>document.querySelector('#annotations').width===800&&document.querySelector('#view').width===800);
  const image=await page.evaluate(()=>movie.frame(3,10));assert.ok(image.startsWith('/9j/'),'Export must remain a composited JPEG');
  assert.equal(await page.evaluate(()=>window.canvasCopies),2,'Only explicit export should perform the two compositing copies');
  assert.deepEqual(errors,[]);
  const dir='cache/framework/browser/performance';fs.mkdirSync(dir,{recursive:true});await page.screenshot({path:dir+'/wind-optimized.png'});
  fs.writeFileSync(dir+'/wind-optimized.json',JSON.stringify({before,idle,changed,live,paused,held},null,2));
  console.log('PASS: idle has zero draws, live has zero canvas copies, model switching, pause, resize and composited JPEG export');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
