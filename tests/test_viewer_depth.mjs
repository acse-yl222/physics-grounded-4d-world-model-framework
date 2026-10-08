import test from 'node:test';
import assert from 'node:assert/strict';
import {nearPlaneForSceneBounds} from '../src/visualization/shared/camera-depth.mjs';
const bounds={min:[-20,30,-5],max:[80,230,55]};
test('near plane maps asymmetric ENU bounds into world coordinates',()=>{
 assert.equal(nearPlaneForSceneBounds([30,25,-130],bounds,[0,0,-1]),.02);
 assert.equal(nearPlaneForSceneBounds([100,25,-130],bounds,[-1,0,0]),5);
 assert.equal(nearPlaneForSceneBounds([30,75,-130],bounds,[0,-1,0]),5);
 assert.equal(nearPlaneForSceneBounds([30,25,-250],bounds,[0,0,1]),5);
});
test('approaching and entering scene lowers near plane to original floor',()=>{
 const positions=[[4080,25,-130],[480,25,-130],[120,25,-130],[80,25,-130],[30,25,-130]];
 assert.deepEqual(positions.map(p=>nearPlaneForSceneBounds(p,bounds,[-1,0,0])),[1000,100,10,.02,.02]);
});
test('near plane is before positive axial depths across adversarial view directions',()=>{
 for(const p of [[900,500,800],[-900,-500,-800],[80.01,25,-130]])
 for(const direction of [[-1,0,0],[0,0,-1],[1,.001,-.001],[-.01,-1,.01]]){
  const length=Math.hypot(...direction),forward=direction.map(v=>v/length);
  const near=nearPlaneForSceneBounds(p,bounds,forward);
  for(const x of [-20,30,80])for(const y of [-5,25,55])for(const z of [-230,-130,-30]){
   const depth=[x,y,z].reduce((sum,v,i)=>sum+(v-p[i])*forward[i],0);
   if(depth>0)assert.ok(near<=Math.max(.02,depth/4)+1e-10);
  }
 }
});
test('small and degenerate scenes preserve millimetre floor',()=>{
 assert.equal(nearPlaneForSceneBounds([0,0,0],{min:[0,0,0],max:[0,0,0]},[0,0,-1]),.001);
});

test('off-axis object inside wide frustum is not clipped by Euclidean near estimate',()=>{
 const b={min:[999,199,-1],max:[1001,201,1]},p=[0,0,0],forward=[0,0,-1];
 const oldNear=Math.hypot(999,199)/4,pointDepth=200;
 const aspect=13,tanHalfFov=Math.tan(45*Math.PI/360);
 assert.ok(1000/(pointDepth*tanHalfFov*aspect)<1,'Object is within horizontal FOV');
 assert.ok(oldNear>pointDepth,'Old Euclidean rule clips this visible object');
 const near=nearPlaneForSceneBounds(p,b,forward);assert.equal(near,199/4);assert.ok(near<199);
});
test('box crossing or behind eye plane retains floor instead of using positive corners',()=>{
 const b={min:[999,-201,-1],max:[1001,201,1]};
 assert.equal(nearPlaneForSceneBounds([0,0,0],b,[0,0,-1]),.0402);
 assert.equal(nearPlaneForSceneBounds([0,0,0],{min:[999,-201,-1],max:[1001,-199,1]},[0,0,-1]),.001);
});
