(async()=>{
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const assert=require('node:assert/strict'),fs=require('node:fs');
 const run=process.env.P4D_WIND_RUN;if(!/^[a-zA-Z0-9_-]+$/.test(run??''))throw Error('P4D_WIND_RUN required');
 const publicUrl=process.env.P4D_WIND_URL;
 const browser=await puppeteer.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1280,height:900});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(!publicUrl) await page.setRequestInterception(true);
  if(!publicUrl) page.on('request',async request=>{
   if(request.url().endsWith('/windfarm-movie/resources.json')){
    const response=await fetch(request.url());const config=await response.json();
    config.data_base=`/project/windfarm/runs/${run}/movie/`;
    await request.respond({status:200,contentType:'application/json',body:JSON.stringify(config)});
   }else await request.continue();
  });
  await page.goto(publicUrl||'http://127.0.0.1:8876/src/visualization/legacy/viewer/windfarm-movie/');
  await page.waitForFunction(()=>window.movie?.metrics.renders>0,{timeout:120000});
  const state=await page.evaluate(()=>({times:movie.meta.times,inlet:movie.meta.inlet_m_s,
   turbines:movie.rotorSystem.rotors.length,title:document.querySelector('#wind-title').textContent,
   detail:document.querySelector('#wind-detail').textContent,comparisons:Object.keys(movie.comparison)}));
  assert.equal(state.inlet,10);assert.equal(state.turbines,23);assert.equal(state.title,'OPENFOAM URANS / TIME EVOLUTION');
  assert.deepEqual(state.comparisons,[]);assert.deepEqual(errors,[]);
  if(state.times.length>1){
   assert.equal(state.times.at(-1),300);
   await page.evaluate(()=>{const slider=document.querySelector('#time');slider.value=150;slider.dispatchEvent(new Event('input'));});
   await page.waitForFunction(()=>document.querySelector('#clock').textContent==='150.0 s');
   const before=await page.evaluate(()=>movie.metrics.fieldUpdates);
   await page.click('#play');
   await page.waitForFunction(n=>movie.metrics.fieldUpdates>n+2,{},before);
   await page.evaluate(()=>{const slider=document.querySelector('#time');slider.value=300;slider.dispatchEvent(new Event('input'));});
   await page.waitForFunction(()=>document.querySelector('#clock').textContent==='300.0 s');
   state.timelineVerified=true;
  }
  fs.mkdirSync('cache/framework/browser/windfarm-uran',{recursive:true});
  await page.screenshot({path:`cache/framework/browser/windfarm-uran/${run}.png`});
  await page.setViewport({width:390,height:844});
  await page.waitForFunction(()=>movie.renderer.domElement.clientWidth<=390);
  await page.screenshot({path:`cache/framework/browser/windfarm-uran/${run}-mobile.png`});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(`cache/framework/browser/windfarm-uran/${run}.json`,JSON.stringify(state,null,2));
  console.log(JSON.stringify(state));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
