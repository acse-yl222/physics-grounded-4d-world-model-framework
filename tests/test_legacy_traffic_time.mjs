import test from 'node:test';
import assert from 'node:assert/strict';
import { recordedTrafficTime } from '../src/visualization/legacy/viewer/3d/traffic-time.mjs';

// The retained South Kensington SUMO sample: frames at t = 1 … 300 s on a one-hour replay clock.
const traffic = { firstTime: 1, lastTime: 300 };

test('replay times inside the recorded traffic range map to themselves', () => {
  for (const t of [1, 1.25, 31, 150.5, 299.9, 300])
    assert.equal(recordedTrafficTime(t, traffic), t);
});

test('replay times outside the recorded traffic range have no traffic data', () => {
  for (const t of [0, 0.5, 300.5, 301, 600, 1800, 3599.9, 3600])
    assert.equal(recordedTrafficTime(t, traffic), null, `t = ${t} s must not wrap into the sample`);
});

test('a replay without recorded traffic has no traffic data', () => {
  assert.equal(recordedTrafficTime(42, null), null);
});
