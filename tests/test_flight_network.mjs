import test from 'node:test';
import assert from 'node:assert/strict';
import {selectFlightNetwork} from '../src/visualization/legacy/viewer/3d/flight-network.mjs';
test('a 100-route selection preserves computed paths and connects all 30 stations',()=>{
 const routes=[];for(let a=0;a<30;a++)for(let b=0;b<30;b++)if(a!==b)routes.push({from_station:`S${a}`,to_station:`S${b}`,duration_s:Math.abs(a-b)+1});
 const chosen=selectFlightNetwork(routes,100);assert.equal(chosen.length,100);assert.ok(chosen.every(r=>routes.includes(r)));
 for(const start of ['S0','S15','S29']){const seen=new Set([start]);for(let i=0;i<30;i++)for(const r of chosen)if(seen.has(r.from_station))seen.add(r.to_station);assert.equal(seen.size,30);}
 assert.deepEqual(selectFlightNetwork(routes,100),chosen);assert.equal(selectFlightNetwork(routes),routes);
});
test('inadequate limits and incomplete connected networks fail explicitly',()=>{
 assert.throws(()=>selectFlightNetwork(Array.from({length:10},()=>({from_station:'a',to_station:'b',duration_s:1})),2));
});
