import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { LANDMARKS, collect } from '../src/urban_geometry/image_to_threejs/collect_landmarks.mjs';

test('landmark modules follow the contract and claim footprints once', async () => {
  const { index, problems } = await collect();
  assert.deepEqual(problems, []);
  assert.ok(index.length > 0);
  for (const entry of index) {
    assert.match(entry.id, /^[a-z][a-z0-9_]*$/);
    assert.ok(entry.name, `${entry.id} needs a name`);
  }
});

test('committed landmark index matches the modules', async () => {
  const { index } = await collect();
  const committed = JSON.parse(fs.readFileSync(path.join(LANDMARKS, 'index.json'), 'utf8'));
  assert.deepEqual(committed, index);
});
