(async()=>{
 const fs=require('node:fs'),path=require('node:path');
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const base=process.env.UWM_VIEWER_URL||'http://127.0.0.1:8782/src/visualization/viewer/';
 const output='cache/framework/city-parity-browser';fs.mkdirSync(output,{recursive:true});
 const browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const results=[];
 try{
  for(const scene of ['south_ken','white_city']){
   const config=path.join('project',scene,'configs'),read=n=>JSON.parse(fs.readFileSync(path.join(config,n)));
   const entries=Object.entries(read('city_fields.json'));
   for(const [name,file] of [['traffic','traffic_result.json'],['diurnal','diurnal_result.json'],['transport','transport_snapshot.json']])entries.push([name,read(file)]);
   for(const [module,entry] of entries){
    const page=await browser.newPage();await page.setViewport({width:1200,height:800});const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const manifestPath=path.join('project',scene,'runs',entry.run_id,'manifest.json'),manifest=JSON.parse(fs.readFileSync(manifestPath));
    const url=new URL(base);url.searchParams.set('manifest','/'+manifestPath);
    await page.goto(url.href,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(n=>window.urbanViewer?.widgets.length===n,{timeout:90000},manifest.layers.length);
    const times=manifest.time.samples,target=times.length?times[Math.floor(times.length/2)]:0;
    await page.evaluate(t=>urbanViewer.setTime(t),target);
    await page.waitForFunction(()=>urbanViewer.widgets.every(w=>!['npy','npy_frames'].includes(w.layer.format)||w.layer.sampling==='static'||w.loadedTime!==undefined),{timeout:30000});
    const result=await page.evaluate(()=>({status:document.getElementById('status').textContent,layers:urbanViewer.widgets.map(w=>({id:w.layer.id,available:w.available,count:w.current?.length||0,position:w.data?.positions?.[0],value:w.current?.[0]}))}));
    if(errors.length)throw Error(errors.join('\n'));
    if(module==='traffic')await page.screenshot({path:path.join(output,scene+'-traffic.png')});
    const disposed=await page.evaluate(()=>{urbanViewer.dispose();return urbanViewer.widgets.every(w=>w.disposed);});
    if(!disposed)throw Error('Disposal failed');
    results.push({scene,module,run_id:entry.run_id,time_s:target,...result,errors,disposed});
    await page.close();console.log(scene,module,'passed');
   }
   const traffic=read('traffic_result.json'),page=await browser.newPage();const url=new URL(base);url.searchParams.set('scene',scene);url.searchParams.set('view',traffic.view_id);
   await page.goto(url.href,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.urbanViewer?.widgets.some(w=>w.layer.id==='geometry')&&urbanViewer.widgets.some(w=>w.layer.id==='traffic'),{timeout:180000});
   await page.evaluate(()=>urbanViewer.setTime(150));await page.screenshot({path:path.join(output,scene+'-integrated.png')});await page.close();
  }
  fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(results,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
