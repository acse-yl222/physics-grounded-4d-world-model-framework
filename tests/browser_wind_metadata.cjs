(async()=>{
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const assert=require('node:assert/strict');
 const browser=await puppeteer.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();const errors=[],comparisons=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.setRequestInterception(true);
  page.on('request',async request=>{
   if(request.url().includes('/comparison/'))comparisons.push(request.url());
   if(request.url().endsWith('/metadata.json')){
    const response=await fetch(request.url());const meta=await response.json();
    // Existing recorded fields serve only as an adapter fixture, not new physics.
    Object.assign(meta,{comparison_keys:[],default_model:'mac_live',
      wind_chunks:['u-0.bin','u-1.bin','u-2.bin','u-3.bin'],
      model_labels:{mac_live:'ADAPTER TEST / RECORDED FIELDS'},
      model_details:{mac_live:'Metadata-provided solver description'},display_note:'Adapter fixture'});
    await request.respond({status:200,contentType:'application/json',body:JSON.stringify(meta)});
   }else await request.continue();
  });
  await page.goto(new URL('viewer/windfarm-movie/',process.env.P4D_SITE_URL||'http://127.0.0.1:8876/src/visualization/legacy/').href);
  await page.waitForFunction(()=>window.movie?.metrics.renders>0,{timeout:120000});
  const state=await page.evaluate(()=>({title:document.querySelector('#wind-title').textContent,
   detail:document.querySelector('#wind-detail').textContent,note:document.querySelector('#sampling-detail').textContent,
   options:[...document.querySelector('#model').options].map(x=>x.value)}));
  assert.equal(state.title,'ADAPTER TEST / RECORDED FIELDS');assert.equal(state.detail,'Metadata-provided solver description');
  assert.equal(state.note,'Adapter fixture');assert.deepEqual(state.options,['mac_live']);assert.deepEqual(comparisons,[]);assert.deepEqual(errors,[]);
  console.log('PASS: metadata-driven live-only dataset loads without legacy comparisons or labels');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
