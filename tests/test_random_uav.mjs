import test from 'node:test';
import assert from 'node:assert/strict';
import {randomFlights} from '../src/visualization/legacy/viewer/3d/random-uav.mjs';
const routes=[
 {from_station:1,to_station:2,duration_s:15,points_m:[[0,0,0],[0,30,0],[150,30,0]],times_s:[0,5,15]},
 {from_station:2,to_station:1,duration_s:17.5,points_m:[[150,30,0],[0,30,0],[0,0,0]],times_s:[0,10,17.5]},
];
test('fixed seed, seeking and independent random flight count are reproducible',()=>{
 const a=randomFlights(routes,{count:8,seed:12,duration:300}),b=randomFlights(routes,{count:8,seed:12,duration:300});
 assert.deepEqual(a.sample(140),b.sample(140));a.sample(200);assert.deepEqual(a.sample(10),b.sample(10));assert.equal(a.sample(0).length,8);
 assert.notDeepEqual(a.flights[0],a.flights[1]);
});
test('route transitions stay at the same station without teleporting',()=>{
 const a=randomFlights(routes,{count:4,duration:300});
 for(const legs of a.flights)for(let i=1;i<legs.length;i++){
  assert.equal(legs[i-1].route.to_station,legs[i].route.from_station);
  assert.deepEqual(legs[i-1].route.points_m.at(-1),legs[i].route.points_m[0]);
 }
 const t=a.flights[0][1].start;const before=a.sample(t-1e-6)[0],after=a.sample(t+1e-6)[0];
 assert.ok(Math.hypot(before.x-after.x,before.y-after.y,before.z-after.z)<1e-3);
});
test('vertical segments use elapsed model time, not uniform path-length speed',()=>{
 const a=randomFlights(routes,{count:1,duration:300});const leg=a.flights[0].find(l=>l.start>=0&&l.route.from_station===1);
 const p=a.sample(leg.start+2)[0];assert.equal(p.x,0);assert.ok(Math.abs(p.y-12)<1e-8);
});
test('invalid timing and disconnected routes are rejected',()=>{
 assert.throws(()=>randomFlights([{...routes[0],times_s:[0,5,5]}]));
 assert.throws(()=>randomFlights([routes[0]]));assert.throws(()=>randomFlights(routes,{count:301}));
});
