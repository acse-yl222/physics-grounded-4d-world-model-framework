import { test } from 'node:test';
import assert from 'node:assert/strict';
import { recordedSampler, advancePlayback } from '../src/visualization/corridor/replay.mjs';
import { solarPosition, londonInstant } from '../src/visualization/corridor/solar.mjs';
const frame = (ids, coords) => ({ idx: Uint32Array.from(ids), xyh: Float32Array.from(coords) });
test('preserve stops, exact samples, missing vehicles and teleport discontinuities', () => {
  const sample = recordedSampler(
    [
      frame([0, 1], [0, 0, 3.1, 100, 0, 0]),
      frame([0, 1], [0, 0, -3.1, 300, 0, 0]),
      frame([0], [10, 0, 0]),
    ],
    1,
  );
  assert.equal(sample(0)[1].x, 100);
  assert.equal(sample(0.5).length, 1);
  assert.equal(sample(0.5)[0].x, 0);
  assert.ok(Math.abs(sample(0.5)[0].heading - Math.PI) < 1e-6);
  assert.equal(sample(1)[1].x, 300);
  assert.equal(sample(1.5).length, 1);
  assert.equal(sample(1.5)[0].x, 5);
  assert.equal(sample(2)[0].x, 10);
});
test('end of playback holds last recorded sample', () => {
  assert.equal(advancePlayback(598.9, 0.25, 15, 599), 599);
});
test('London daylight saving and geographic sun direction', () => {
  assert.equal(londonInstant('2026-06-25', 13).toISOString(), '2026-06-25T12:00:00.000Z');
  assert.equal(londonInstant('2026-12-21', 12).toISOString(), '2026-12-21T12:00:00.000Z');
  const noon = solarPosition(londonInstant('2026-06-25', 13), 51.506427, -0.200473);
  const winter = solarPosition(londonInstant('2026-12-21', 12), 51.506427, -0.200473);
  assert.ok(noon.altitude > 60 && noon.altitude < 63);
  assert.ok(noon.north < 0 && Math.abs(noon.east) < 0.05);
  assert.ok(winter.altitude > 14 && winter.altitude < 16);
  assert.ok(solarPosition(londonInstant('2026-06-25', 0), 51.506427, -0.200473).up < 0);
});
