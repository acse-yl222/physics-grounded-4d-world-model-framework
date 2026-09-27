(async()=>{
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');const fs=require('node:fs'),path=require('node:path');
 const base=process.env.UWM_VIEWER_URL||'http://127.0.0.1:8770/';const output='cache/framework/browser';fs.mkdirSync(output,{recursive:true});
 const browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1280,height:900});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const url=new URL(base);url.search='?scene=south_ken&view=traffic';await page.goto(url.href,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>window.urbanViewer?.widgets.length===3,{timeout:240000});
  await page.evaluate(()=>urbanViewer.setTime(100));await page.waitForFunction(()=>urbanViewer.widgets.find(w=>w.layer.id==='wind')?.loadedTime===100,{timeout:60000});
  const report=await page.evaluate(()=>{const traffic=urbanViewer.widgets.find(w=>w.layer.id==='traffic'),wind=urbanViewer.widgets.find(w=>w.layer.id==='wind'),city=urbanViewer.widgets.find(w=>w.layer.id==='geometry');return{status:document.getElementById('status').textContent,firstTrafficId:traffic.data.ids[0],firstTrafficPosition:traffic.current[0],trafficCount:traffic.current.length,windPosition:wind.data.positions[0],windValue:wind.current[0],batchStats:city.batchStats,sceneOptions:[...document.querySelector('#scene').options].map(x=>x.value)};});
  const replay='project/south_ken/runs/legacy_agents/data/traffic/replay';const index=JSON.parse(fs.readFileSync(path.join(replay,'frames_index.json'))).find(f=>f.t_s===100);const file=fs.readFileSync(path.join(replay,'traffic_flow.f32'));const offset=index.offset_bytes;const expected=[file.readFloatLE(offset+4)-2912.594719173,file.readFloatLE(offset+8)-1704.705026026,.275];
  if(report.firstTrafficId!==String(file.readFloatLE(offset))||report.firstTrafficPosition.some((v,i)=>Math.abs(v-expected[i])>1e-8))throw Error('Recorded traffic coordinates changed');
  if(report.trafficCount!==index.count)throw Error('Recorded traffic count changed');
  if(!report.sceneOptions.includes('white_city'))throw Error('Scene selector did not load the registry');
  if(errors.length)throw Error(errors.join('\n'));
  await page.screenshot({path:path.join(output,'south-ken-traffic.png')});
  report.errors=errors;report.expectedTrafficPosition=expected;fs.writeFileSync(path.join(output,'city-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
