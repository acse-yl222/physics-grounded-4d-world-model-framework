// Interpolation and late frame completion must preserve the latest requested time.
(async()=>{
 const {default:puppeteer}=await import(process.env.PUPPETEER_MODULE||'puppeteer-core');
 const assert=require('node:assert/strict');
 const browser=await puppeteer.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(new URL('src/visualization/viewer/?manifest=../../../examples/contract-v1.1/manifest.json',process.env.P4D_SITE_URL||'http://127.0.0.1:8773/').href);
  await page.waitForFunction(()=>window.urbanViewer?.widgets.length===1);
  const result=await page.evaluate(async()=>{
   const w=urbanViewer.widgets[0];await w.setTime(0);const first=structuredClone(w.current);
   await w.setTime(1);const last=structuredClone(w.current);
   await w.setTime(.5);const middle=structuredClone(w.current);
   const frame=w.source.frame.bind(w.source);w.source.frame=async i=>{await new Promise(r=>setTimeout(r,100));return frame(i)};
   const pending=w.setTime(1);await w.setTime(.5);await pending;
   const held=structuredClone(w.current);
   await w.setTime(99);const unavailable=!w.available&&!w.group.visible;
   await w.setTime(.5);const recovered=w.available&&w.group.visible;
   return {first,last,middle,held,unavailable,recovered};
  });
  assert.deepEqual(result.middle,result.first.map((v,i)=>v.map((x,j)=>(x+result.last[i][j])/2)));
  assert.deepEqual(result.held,result.middle,'Late request must not replace the latest selection');
  assert.ok(result.unavailable&&result.recovered);assert.deepEqual(errors,[]);
  console.log('PASS: binary grid interpolation, late-frame race, out-of-range hiding and recovery');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
