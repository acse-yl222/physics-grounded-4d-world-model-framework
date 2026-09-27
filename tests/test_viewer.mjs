import test from 'node:test';
import assert from 'node:assert/strict';
import {sample,enuToWorld,worldToEnu,assetURL} from '../src/visualization/shared/time.mjs';
test('ENU conversion preserves handedness and round trips',()=>{
 assert.deepEqual(enuToWorld([1,2,3]),[1,3,-2]);assert.deepEqual(worldToEnu(enuToWorld([-3,9,2])),[-3,9,2]);
});
test('time samples interpolate and never wrap out of range',()=>{
 const frames=[[[0,0,0]],[[10,20,30]]];assert.deepEqual(sample(frames,[10,20],15,'linear'),[[5,10,15]]);
 assert.deepEqual(sample(frames,[10,20],15,'step'),frames[0]);assert.deepEqual(sample(frames,[10,20],20,'linear'),frames[1]);
 assert.equal(sample(frames,[10,20],9,'linear'),null);assert.equal(sample(frames,[10,20],21,'step'),null);
});
test('static layer remains available independently of time',()=>assert.deepEqual(sample([1,2],[],200,'static'),[1,2]));
test('run assets cannot escape through browser URL normalization',()=>{
 const base='http://localhost/project/south_ken/runs/example/manifest.json';
 assert.equal(assetURL(base,'data/mesh.json'),'http://localhost/project/south_ken/runs/example/data/mesh.json');
 for(const bad of ['../outside','/absolute','%2e%2e/outside','https://other/a','data/a?redirect=1','data\\a'])assert.throws(()=>assetURL(base,bad));
});
import {sampleTrajectories} from '../src/visualization/shared/time.mjs';
test('sparse replay interpolates identities and handles arrivals/departures',()=>{
 const frames=[{ids:['a','departing'],positions:[[0,0,0],[1,1,0]]},{ids:['new','a'],positions:[[9,9,0],[4,2,0]]}];
 assert.deepEqual(sampleTrajectories(frames,[0,2],1,'linear'),{ids:['a','departing'],positions:[[2,1,0],[1,1,0]]});
 assert.deepEqual(sampleTrajectories(frames,[0,2],2,'linear'),frames[1]);assert.equal(sampleTrajectories(frames,[0,2],3,'step'),null);
});
