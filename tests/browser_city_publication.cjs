// Exercise the real published shell, protocol widgets, clocks, picking and disposal.
(async()=>{
 const fs=require('node:fs');
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const base=process.env.CITY_PUBLIC_URL||'http://127.0.0.1:8783/';
 const output=process.env.CITY_PUBLIC_OUTPUT||'cache/framework/city-publication-browser';fs.mkdirSync(output,{recursive:true});
 const browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const results=[];
 try{
  for(const scene of ['south_kensington','white_city']){
   const page=await browser.newPage();await page.setViewport({width:1440,height:1000});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   if(base.includes('127.0.0.1')){await page.setRequestInterception(true);page.on('request',r=>r.url().endsWith('/viewer/config.js')?r.respond({status:200,contentType:'application/javascript',body:'export const ON_PAGES=true;'}):r.continue());}
   await page.goto(`${base}viewer/3d/?scene=${scene}&lite=${process.env.CITY_FULL==='1'?'0':'1'}&module=traffic&pose=campus&play=0`,{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>window.cityTools?.widgets.length>=3&&document.querySelector('#city-status').textContent.includes('ready'),{timeout:240000});
   for(const module of ['traffic','diurnal','transport']){
    await page.evaluate(async m=>{await cityTools.selectModule(m);await cityTools.setTime(m==='traffic'?150:m==='diurnal'?43200:0);},module);
    const result=await page.evaluate(()=>({module:cityTools.current,status:document.querySelector('#city-status').textContent,layers:cityTools.widgets.map(w=>({id:w.layer.id,available:w.available,loadedTime:w.loadedTime,visible:w.group?.visible})),modelChildren:viewer.model.children.length}));
    if(!result.status.includes('ready')||result.layers.some(l=>!l.available)||!result.modelChildren)throw Error(JSON.stringify(result));
    if(module==='diurnal'&&!await page.evaluate(()=>cityTools.widgets.every(w=>{w.instances.geometry.computeBoundingSphere();return w.instances.geometry.boundingSphere.radius<Math.min(...w.layer.encoding.spacing_m)*w.displayStep/2;})))throw Error('Scalar markers obscure neighbouring samples');
    const visibility=await page.evaluate(()=>{const t=document.querySelector('#city-layer-controls input[type=checkbox]');t.click();const hidden=!cityTools.widgets[0].group.visible;t.click();return hidden&&cityTools.widgets[0].group.visible;});if(!visibility)throw Error('Visibility did not toggle');
    await page.screenshot({path:`${output}/${scene}-${module}.png`});results.push({scene,...result});console.log(scene,module,'passed');
   }
   const disposed=await page.evaluate(async()=>{const old=[...cityTools.widgets];await cityTools.selectModule('diurnal');return old.every(w=>w.disposed);});if(!disposed)throw Error('Previous widgets not disposed');
   await page.evaluate(async()=>{await Promise.all([cityTools.selectModule('diurnal'),cityTools.selectModule('transport')]);});
   if(!await page.evaluate(()=>cityTools.current==='transport'&&cityTools.widgets.length===2))throw Error('Rapid module switch failed');
   await page.click('[data-field="wind"]');
   if(!await page.evaluate(()=>!cityTools.current&&!cityTools.widgets.length&&!document.getElementById('play').disabled))throw Error('Legacy field switching failed');
   if(errors.length)throw Error(errors.join('\n'));await page.close();
  }
  fs.writeFileSync(`${output}/report.json`,JSON.stringify(results,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
