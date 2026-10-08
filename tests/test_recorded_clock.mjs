import test from 'node:test';
import assert from 'node:assert/strict';
import {timelineTime, layerSpan} from '../src/visualization/legacy/viewer/recorded-clock.mjs';
test('legacy clock keeps its first interval and delayed thermal range', () => {
  const timeline = {step_s: 25, steps: 100};
  assert.equal(timelineTime(timeline, 1), 25);
  assert.deepEqual(layerSpan(timeline, {t0_s: 1000, step_s: 25, frames: 61}), {start: 40, end: 100});
});
test('recorded zero-origin wind and thermal clocks share exact endpoints', () => {
  const timeline = {t0_s: 0, step_s: 20, steps: 31};
  assert.equal(timelineTime(timeline, 1), 0);
  assert.equal(timelineTime(timeline, 31), 600);
  assert.deepEqual(layerSpan(timeline, {t0_s: 0, step_s: 60, frames: 11}), {start: 1, end: 31});
});
