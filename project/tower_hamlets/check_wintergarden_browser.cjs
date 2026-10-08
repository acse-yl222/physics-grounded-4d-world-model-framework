// Regression: an idle on-demand canvas must repaint after WebGL restoration.
(async()=>{
 const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const output=process.env.UWM_BROWSER_OUTPUT||'cache/framework/context-restore';fs.mkdirSync(output,{recursive:true});
 const browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1440,height:1000});const errors=[],consoleErrors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')consoleErrors.push({text:m.text(),location:m.location()});});
  await page.goto(process.env.UWM_VIEWER_URL||'http://127.0.0.1:8874/src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json',{waitUntil:'networkidle0',timeout:180000});
  await page.waitForFunction(()=>window.urbanViewer?.widgets.length>0,{timeout:180000});
  // Event/state based synchronization, without changing camera, time or visibility.
  await page.waitForFunction(()=>!document.querySelector('#viewport>canvas').getContext('webgl2').isContextLost());
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  async function capture(name){
   const canvas=await page.$('#viewport>canvas'),png=await canvas.screenshot({path:path.join(output,name+'.png')});
   return page.evaluate(async data=>{const img=new Image();img.src=data;await img.decode();const c=document.createElement('canvas');c.width=img.width;c.height=img.height;const ctx=c.getContext('2d');ctx.drawImage(img,0,0);const bytes=ctx.getImageData(0,0,c.width,c.height).data;let nonBackground=0;for(let i=0;i<bytes.length;i+=4)if(Math.abs(bytes[i]-17)+Math.abs(bytes[i+1]-25)+Math.abs(bytes[i+2]-35)>15)nonBackground++;return{width:c.width,height:c.height,nonBackground};},'data:image/png;base64,'+Buffer.from(png).toString('base64'));
  }
  const manifest=await page.evaluate(async()=>{const url=new URL(new URLSearchParams(location.search).get('manifest'),location.href),bytes=await(await fetch(url)).arrayBuffer();return {url:url.href,sha256:Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('')};});
  const initial=await capture('initial');assert.ok(initial.nonBackground>100,'Initial loaded canvas must contain scene pixels');
  const before=await page.evaluate(()=>urbanViewer.performanceStats.renders);
  await page.evaluate(()=>{const canvas=document.querySelector('#viewport>canvas'),gl=canvas.getContext('webgl2'),extension=gl.getExtension('WEBGL_lose_context');if(!extension)throw Error('WEBGL_lose_context unavailable');window.__restoreTest={lost:false,restored:false};canvas.addEventListener('webglcontextrestored',()=>{__restoreTest.restored=true;},{once:true});canvas.addEventListener('webglcontextlost',()=>{__restoreTest.lost=true;setTimeout(()=>extension.restoreContext(),0);},{once:true});extension.loseContext();});
  await page.waitForFunction(n=>__restoreTest.lost&&__restoreTest.restored&&urbanViewer.performanceStats.renders>n,{},before);
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const restored=await capture('restored');assert.ok(restored.nonBackground>100,'Restored canvas must repaint without user interaction');
  const state=await page.evaluate(()=>({events:__restoreTest,renders:urbanViewer.performanceStats.renders}));
  const closeups=[];
  for(const view of [{name:'twenty-cabot-closeup',position:[-258,95,155],target:[-258,30,90]},{name:'wintergarden-closeup',position:[-50,65,430],target:[5,20,310]}]){
   const beforeView=await page.evaluate(()=>urbanViewer.performanceStats.renders);
   await page.evaluate(v=>{const c=urbanViewer.widgets[0].context.camera,look=c.__auditLook||c.lookAt.bind(c);c.__auditLook=look;c.lookAt=()=>{c.position.set(...v.position);look(...v.target);};c.lookAt();c.updateMatrixWorld();urbanViewer.setTime(0);},view);
   await page.waitForFunction(n=>urbanViewer.performanceStats.renders>n,{},beforeView);
   await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   const pixels=await capture(view.name);closeups.push({...view,pixels,...await page.evaluate(()=>{const c=urbanViewer.widgets[0].context.camera;return {actualPosition:c.position.toArray(),near:c.near,far:c.far};})});
  }
  state.renders=await page.evaluate(()=>urbanViewer.performanceStats.renders);
  await page.evaluate(()=>{urbanViewer.dispose();urbanViewer.dispose();document.querySelector('#viewport>canvas').dispatchEvent(new Event('webglcontextrestored'));});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert.equal(await page.evaluate(()=>urbanViewer.performanceStats.renders),state.renders,'Disposed viewer must not repaint');assert.deepEqual(errors,[]);assert.ok(consoleErrors.every(e=>e.location.url.endsWith('/favicon.ico')),'Only separately recorded favicon404 allowed');
  const report={passed:true,manifest,initial,restored,before,...state,closeups,errors,consoleErrors};fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
