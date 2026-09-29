import test from 'node:test';
import assert from 'node:assert/strict';
import {createTimeline} from '../src/visualization/legacy/viewer/windfarm-movie/timeline.mjs';

test('irregular recorded frames and nonzero start interpolate without inventing frames',()=>{
  const timeline=createTimeline([10,10.25,12,17]);
  assert.deepEqual(timeline.sample(11.125),{a:1,b:2,mix:.5});
  assert.deepEqual(timeline.sample(10),{a:0,b:0,mix:0});
  assert.deepEqual(timeline.sample(17),{a:3,b:3,mix:0});
  assert.deepEqual(timeline.sample(100),{a:3,b:3,mix:0});
  assert.deepEqual(timeline.sample(-10),{a:0,b:0,mix:0});
  assert.equal(timeline.advance(16,1,2),11);
});
test('single frame is static and invalid times fail explicitly',()=>{
  const timeline=createTimeline([5]);
  assert.deepEqual(timeline.sample(20),{a:0,b:0,mix:0});
  assert.equal(timeline.advance(5,100,12.5),5);
  for(const times of [[],[0,0],[2,1],[0,NaN]])assert.throws(()=>createTimeline(times));
  assert.throws(()=>timeline.sample(NaN));
});
test('legacy two-second frame sampling remains unchanged',()=>{
  const timeline=createTimeline(Array.from({length:151},(_,i)=>i*2));
  assert.deepEqual(timeline.sample(137),{a:68,b:69,mix:.5});
  assert.equal(timeline.advance(299,1,12.5),11.5);
});
