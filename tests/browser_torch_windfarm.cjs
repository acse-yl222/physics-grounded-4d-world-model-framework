(async()=>{
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const assert=require('node:assert/strict'),fs=require('node:fs');
 const run=process.env.P4D_WIND_RUN;if(!/^[a-zA-Z0-9_-]+$/.test(run??''))throw Error('P4D_WIND_RUN required');
 const publicUrl=process.env.P4D_WIND_URL;
 const duration=Number(process.env.P4D_WIND_DURATION||60),frameCount=Number(process.env.P4D_WIND_FRAMES||61);
 const browser=await puppeteer.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1280,height:900});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(!publicUrl){await page.setRequestInterception(true);page.on('request',async request=>{
   if(request.url().endsWith('/windfarm-movie/resources.json'))await request.respond({status:200,contentType:'application/json',body:JSON.stringify({data_base:`/project/windfarm/runs/${run}/movie/`,default_run:'local_torch_run',runs:{local_torch_run:{label:`TorchRotor-RANS · ${duration} s`,data_base:`/project/windfarm/runs/${run}/movie/`},openfoam_10ms_v1:{label:'OpenFOAM URANS · 300 s',data_base:'https://acse-yl222.github.io/urban-world-model-models/project/windfarm/runs/openfoam_10ms_v1/'}},model:'https://acse-yl222.github.io/urban-world-model-models/project/windfarm/geometry/published_v1/region.glb'})});
   else await request.continue();
  });}
  await page.goto(publicUrl||'http://127.0.0.1:8876/src/visualization/legacy/viewer/windfarm-movie/');
  await page.waitForFunction(()=>window.movie?.metrics.renders>0,{timeout:120000});
  const state=await page.evaluate(()=>({times:movie.meta.times,inlet:movie.meta.inlet_m_s,turbines:movie.rotorSystem.rotors.length,title:document.querySelector('#wind-title').textContent,detail:document.querySelector('#wind-detail').textContent,comparisons:Object.keys(movie.comparison),cell:movie.meta.simulation_cell_m,notes:movie.meta.display_note,phaseSource:movie.rotorSystem.phaseSource,physicsNote:document.querySelector('#physics-limitations')?.textContent}));
  assert.equal(state.inlet,10);assert.equal(state.turbines,23);assert.equal(state.cell,8);assert.match(state.title,/TORCHROTOR-RANS/);
  assert.equal(state.times[0],0);assert.ok(Math.abs(state.times.at(-1)-duration)<1e-8);assert.equal(state.times.length,frameCount);assert.deepEqual(state.comparisons,[]);
  await page.evaluate(t=>{const slider=document.querySelector('#time');slider.value=t;slider.dispatchEvent(new Event('input'));},duration/2);
  await page.waitForFunction(t=>document.querySelector('#clock').textContent===t.toFixed(1)+' s',{},duration/2);
  if(process.env.P4D_WIND_ALM==='1'){
   assert.equal(state.phaseSource,'recorded_solver_kinematics');assert.match(state.physicsNote,/shaft torque/);
   assert.equal(await page.evaluate(()=>/[\u3400-\u9fff]/.test(document.body.innerText)),false);
   const error=await page.evaluate(t=>{movie.render(t);const r=movie.rotorSystem.rotors[0],angle=r.omega[0]*t,q=r.group.quaternion;return Math.max(Math.abs(q.w-Math.cos(angle/2)),Math.abs(q.x-r.axis.x*Math.sin(angle/2)),Math.abs(q.y-r.axis.y*Math.sin(angle/2)),Math.abs(q.z-r.axis.z*Math.sin(angle/2)));},duration/2);
   assert.ok(error<1e-6);state.recordedPhaseVerified=true;
  }
  const before=await page.evaluate(()=>movie.metrics.fieldUpdates);await page.click('#play');
  await page.waitForFunction(n=>movie.metrics.fieldUpdates>n+2,{},before);
  await page.evaluate(t=>{const slider=document.querySelector('#time');slider.value=t;slider.dispatchEvent(new Event('input'));},duration);
  await page.waitForFunction(t=>document.querySelector('#clock').textContent===t.toFixed(1)+' s',{},duration);
  fs.mkdirSync('cache/framework/browser/torch-rotor-rans',{recursive:true});
  await page.screenshot({path:`cache/framework/browser/torch-rotor-rans/${run}.png`});
  await page.setViewport({width:390,height:844});await page.waitForFunction(()=>movie.renderer.domElement.clientWidth<=390);
  await page.waitForFunction(()=>document.querySelector('.movie-hud').getBoundingClientRect().top>=document.querySelector('nav').getBoundingClientRect().bottom);
  await page.screenshot({path:`cache/framework/browser/torch-rotor-rans/${run}-mobile.png`});
  assert.deepEqual(errors,[]);
  const link=await page.$eval('a[href^="methods"]',a=>a.href);const methods=await page.goto(link);assert.equal(methods.status(),200);assert.match(await page.content(),/Poisson/);
  if(publicUrl){
   console.log('Checking run selector');await page.goto(publicUrl);await page.waitForFunction(()=>window.movie?.metrics.renders>0,{timeout:120000});
   for(const [key,title,end] of [['torch_rotor_rans_v01',/TORCHROTOR-RANS v0.1/,60],['torch_rotor_rans_v02',/TORCHROTOR-RANS v0.2/,600],['openfoam_10ms_v1',/OPENFOAM/,300]]){
    await Promise.all([page.waitForNavigation(),page.select('#run',key)]);
    await page.waitForFunction(()=>window.movie?.metrics.renders>0,{timeout:120000});
    assert.match(await page.$eval('#wind-title',x=>x.textContent),title);
    assert.equal(await page.evaluate(()=>movie.meta.times.at(-1)),end);
    if(key==='torch_rotor_rans_v01')assert.match(await page.$eval('a[href^="methods"]',a=>a.href),/methods-v01.html$/);
   }
   state.previousRunSwitchVerified=true;state.previousTorchSwitchVerified=true;
  }
  state.errors=errors;state.timelineVerified=true;
  fs.writeFileSync(`cache/framework/browser/torch-rotor-rans/${run}.json`,JSON.stringify(state,null,2));console.log(JSON.stringify(state));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
