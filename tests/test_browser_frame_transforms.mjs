import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

test('PNG pollution preserves zero with log1p while legacy logarithmic frames remain compatible',async()=>{
 const source=(await readFile(new URL('../src/visualization/legacy/viewer/frames.js',import.meta.url),'utf8')).replace("import { DATA } from './npy.js';", "const DATA = '/physics/';");
 const old={fetch:globalThis.fetch,createImageBitmap:globalThis.createImageBitmap,OffscreenCanvas:globalThis.OffscreenCanvas};
 try{
  globalThis.createImageBitmap=async()=>({close(){}});
  globalThis.OffscreenCanvas=class{constructor(w,h){this.width=w;this.height=h;}getContext(){return{drawImage(){},getImageData(){return{data:new Uint8ClampedArray([0,0,0,255,255,255,255,255])}}};}};
  for(const [transform,range,scale,expected] of [['log1p',[0,4],.001,[0,9.999]],[undefined,[-1,4],undefined,[.1,10000]],['linear',[0,20],undefined,[0,20]]]){
   globalThis.fetch=async url=>String(url).endsWith('index.json')?{ok:true,json:async()=>({layers:{poll:{kind:'gray',shape_yx:[1,2],range,value_transform:transform,value_scale:scale}}})}:{ok:true,blob:async()=>({})};
   const module=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64')+'#'+String(transform));
   await module.initFrames();const a=await module.getFrameF32('poll',0);
   expected.forEach((v,i)=>assert.ok(Math.abs(a[i]-v)<Math.max(1e-7,Math.abs(v)*1e-6)));
  }
 }finally{Object.assign(globalThis,old);}
});
