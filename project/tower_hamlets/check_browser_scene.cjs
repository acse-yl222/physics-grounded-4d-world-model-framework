// Scene-specific canonical-viewer audit; run while p4d serve is available.
(async()=>{
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {default:puppeteer}=await import(path.resolve(process.env.PUPPETEER_MODULE||'cache/framework/browser-tools/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js'));
const manifest=process.env.UWM_MANIFEST||'/project/tower_hamlets/runs/canary_wharf_appearance_credit_photo_001/manifest.json';
const output=process.env.UWM_BROWSER_OUTPUT||'cache/tower_hamlets/browser_review';fs.mkdirSync(output,{recursive:true});
const url=(process.env.UWM_SERVER||'http://127.0.0.1:8874')+'/src/visualization/viewer/?manifest='+manifest;
const browser=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
const report={url,started:new Date().toISOString(),errors:[],failedRequests:[],badResponses:[]};
try{
const page=await browser.newPage();await page.setViewport({width:1440,height:1000});page.on('pageerror',e=>report.errors.push(e.message));page.on('requestfailed',r=>report.failedRequests.push({url:r.url(),failure:r.failure()}));page.on('response',r=>{if(r.status()>=400)report.badResponses.push({url:r.url(),status:r.status()});});
await page.goto(url,{waitUntil:'networkidle0',timeout:180000});await page.waitForFunction(()=>window.urbanViewer?.widgets.length===1,{timeout:180000});
report.initial=await page.evaluate(()=>{const w=urbanViewer.widgets[0];let meshes=0,vertices=0,ids=0,names=[];const metadataCounts={building_id:0,research_object_id:0,source_owner_ids:0};w.group.traverse(o=>{for(const key of Object.keys(metadataCounts))if(o.userData?.[key])metadataCounts[key]++;if(o.isMesh){meshes++;vertices+=o.geometry.attributes.position?.count||0;if(o.userData?.entity_id||o.userData?.osm_id)ids++;if(names.length<8)names.push(o.name);}});return {status:document.getElementById('status').textContent,layer:w.layer.id,kind:w.layer.kind,meshes,vertices,meshesWithEntityMetadata:ids,metadataCounts,names,batchStats:w.batchStats,camera:w.context.camera.position.toArray()};});
const raw=await page.evaluate(async p=>await(await fetch(p)).text(),manifest);report.manifestSha256=crypto.createHash('sha256').update(raw).digest('hex');
await page.waitForFunction(()=>!document.querySelector('#viewport>canvas').getContext('webgl2').isContextLost());await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await page.screenshot({path:path.join(output,'initial.png')});
const rect=await page.$eval('#viewport>canvas',e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};});
await page.mouse.move(rect.x+rect.width*.5,rect.y+rect.height*.5);await page.mouse.down();await page.mouse.move(rect.x+rect.width*.62,rect.y+rect.height*.55,{steps:12});await page.mouse.up();await new Promise(r=>setTimeout(r,1000));
report.orbit=await page.evaluate(()=>urbanViewer.widgets[0].context.camera.position.toArray());report.orbitChanged=report.orbit.some((v,i)=>Math.abs(v-report.initial.camera[i])>1e-5);
await page.click('#layers input[type=checkbox]');report.hidden=await page.evaluate(()=>!urbanViewer.widgets[0].group.visible);await page.click('#layers input[type=checkbox]');report.shown=await page.evaluate(()=>urbanViewer.widgets[0].group.visible);
// Find an actual visible intersection, then dispatch a real canvas mouse click.
const target=await page.evaluate(async()=>{const THREE=await import('/src/visualization/vendor/three/build/three.module.js');const w=urbanViewer.widgets[0],ray=new THREE.Raycaster(),r=document.querySelector('#viewport>canvas').getBoundingClientRect();for(let y=-.6;y<=.6;y+=.1)for(let x=-.6;x<=.6;x+=.1){ray.setFromCamera(new THREE.Vector2(x,y),w.context.camera);const hit=w.pick({raycaster:ray});if(hit)return{x:r.left+(x+1)*r.width/2,y:r.top+(1-y)*r.height/2};}return null;});
if(target){await page.mouse.click(target.x,target.y);report.selection=await page.$eval('#selection',e=>e.textContent);}else report.selection='No ray intersection';
report.entityIdReturned=report.selection.includes('"entity_id"');await page.screenshot({path:path.join(output,'orbit-selection.png')});
if(process.env.UWM_CLOSEUP){
await page.evaluate(()=>{const c=urbanViewer.widgets[0].context.camera;c.near=5;c.updateProjectionMatrix();});await page.setViewport({width:1441,height:1000});await new Promise(r=>setTimeout(r,700));await page.screenshot({path:path.join(output,'overview-near5.png')});await page.evaluate(()=>{const c=urbanViewer.widgets[0].context.camera;c.near=.13506022338867188;c.updateProjectionMatrix();});
report.sourceGlb=await page.evaluate(async()=>{const w=urbanViewer.widgets[0],url=new URL(w.layer.asset,w.context.baseURL),bytes=await(await fetch(url)).arrayBuffer(),len=new DataView(bytes).getUint32(12,true),g=JSON.parse(new TextDecoder().decode(new Uint8Array(bytes,20,len)));const counts={building_id:0,research_object_id:0,source_owner_ids:0};for(const n of g.nodes||[])for(const k of Object.keys(counts))if(n.extras?.[k])counts[k]++;return{nodes:g.nodes.length,metadataCounts:counts,sourceOwnerIds:[...new Set(g.nodes.flatMap(n=>n.extras?.source_owner_ids||[]))],materials:g.materials.map(m=>({name:m.name,alphaMode:m.alphaMode,doubleSided:m.doubleSided,baseColor:m.pbrMetallicRoughness?.baseColorFactor})),creditNodes:g.nodes.filter(n=>/Credit/i.test(n.name||'')).slice(0,4)};});
report.closeup=await page.evaluate(()=>{const c=urbanViewer.widgets[0].context.camera;const originalLookAt=c.lookAt.bind(c);c.lookAt=()=>{c.position.set(-475,135,95);originalLookAt(-334,47,-69);};c.lookAt();c.updateMatrixWorld();return{camera:c.position.toArray(),near:c.near,far:c.far};});
// Trigger resize redraw without invoking OrbitControls, preserving diagnostic camera.
await page.setViewport({width:1441,height:1000});await new Promise(r=>setTimeout(r,700));await page.screenshot({path:path.join(output,'credit-closeup-original-depth.png')});
await page.evaluate(()=>{const c=urbanViewer.widgets[0].context.camera;c.near=5;c.updateProjectionMatrix();});await page.setViewport({width:1440,height:1000});await new Promise(r=>setTimeout(r,700));await page.screenshot({path:path.join(output,'credit-closeup-near5.png')});
}
if(process.env.UWM_WESTFERRY){
const recipe=JSON.parse(fs.readFileSync('project/tower_hamlets/input/canary_wharf_20261007/references/westferry_house_facade_study_003.json'));
report.westferry=await page.evaluate(async recipe=>{
 const THREE=await import('/src/visualization/vendor/three/build/three.module.js');const w=urbanViewer.widgets[0];w.group.updateMatrixWorld(true);
 const rays=recipe.visible_edges.map(e=>{const a=e.endpoints_enu_m[0],b=e.endpoints_enu_m[1],n=e.inward_normal,l=Math.hypot(b[0]-a[0],b[1]-a[1]),u=[(b[0]-a[0])/l,(b[1]-a[1])/l],win=recipe.upper_windows.find(v=>v.edge===e.edge_index&&v.bay===1&&v.row===3),s=win.s_interval[0]+.4,z=(win.z_interval[0]+win.z_interval[1])/2;
 const ray=new THREE.Raycaster(new THREE.Vector3(a[0]+u[0]*s-n[0]*.25,z,-(a[1]+u[1]*s-n[1]*.25)),new THREE.Vector3(n[0],0,-n[1]),0,2);const hits=ray.intersectObject(w.group,true).filter(h=>h.object.visible);return {edge:e.edge_index,hits:hits.slice(0,8).map(h=>({distance:h.distance,recess:h.distance-.25,material:Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]?.name:h.object.material.name})),recessRetained:hits.length>0&&hits[0].distance>.65&&hits[0].distance<.95};});
 const url=new URL(w.layer.asset,w.context.baseURL),bytes=await(await fetch(url)).arrayBuffer(),len=new DataView(bytes).getUint32(12,true),g=JSON.parse(new TextDecoder().decode(new Uint8Array(bytes,20,len)));const ownerNodes=g.nodes.filter(n=>n.extras?.building_id===recipe.building_id||(n.extras?.source_owner_ids||[]).includes(recipe.building_id));const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
 return {rays,allRecessesRetained:rays.every(r=>r.recessRetained),sourceOwnerNodes:ownerNodes.map(n=>({name:n.name,extras:n.extras})),sourceGlbSha256:digest,sourceGlbBytes:bytes.byteLength};
},recipe);
for(const view of [{name:'westferry-closeup',position:[-553,76,-22],target:[-466,27,-65],near:.2},{name:'westferry-window-depth',position:[-508,34,-57],target:[-486,29,-66],near:.2},{name:'westferry-window-depth-near5',position:[-508,34,-57],target:[-486,29,-66],near:5}]){
 await page.evaluate(v=>{const c=urbanViewer.widgets[0].context.camera,look=c.__auditLookAt||c.lookAt.bind(c);c.__auditLookAt=look;c.lookAt=()=>{c.position.set(...v.position);look(...v.target);};c.near=v.near;c.updateProjectionMatrix();c.lookAt();c.updateMatrixWorld();},view);
 await page.setViewport({width:view.name==='westferry-closeup'?1441:1440,height:1000});await new Promise(r=>setTimeout(r,900));await page.screenshot({path:path.join(output,view.name+'.png')});
}
}
report.disposal=await page.evaluate(()=>{const widgets=[...urbanViewer.widgets];urbanViewer.dispose();urbanViewer.dispose();return {count:widgets.length,allDisposed:widgets.every(w=>w.disposed),allDetached:widgets.every(w=>w.group.parent===null)};});
report.passed=report.orbitChanged&&report.hidden&&report.shown&&report.selection.includes('"layer_id"')&&report.disposal.allDisposed&&report.disposal.allDetached&&!report.errors.length&&(!report.westferry||report.westferry.allRecessesRetained);
} catch(e){report.error=e.stack;report.passed=false;} finally{await browser.close();report.finished=new Date().toISOString();fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}
if(!report.passed)process.exitCode=1;
})();
