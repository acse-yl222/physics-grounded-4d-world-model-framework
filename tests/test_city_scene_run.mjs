import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(
  new URL('../src/visualization/legacy/viewer/scene-run.js', import.meta.url),
  'utf8',
);
const { recordedFrame, loadRunScene } = await import(
  'data:text/javascript;base64,' + Buffer.from(source).toString('base64')
);

test('recorded time sampling preserves gaps and hides data outside the actual range', () => {
  const layer = { time_s: [0, 50, 120] };
  assert.equal(recordedFrame(layer, -1), null);
  assert.equal(recordedFrame(layer, 0), 0);
  assert.equal(recordedFrame(layer, 110), 1);
  assert.equal(recordedFrame(layer, 120), 2);
  assert.equal(recordedFrame(layer, 121), null);
});

function fixture() {
  const scene = {
    title: 'Fixture',
    model: { url: 'models/city.glb' },
    layers: { wind: { file: 'wind.npy', frames: 2, time_s: [50, 100] } },
    masks: { footprint: { 8: 'mask.npy' } },
  };
  const manifest = {
    schema_version: '1.1.0',
    status: 'complete',
    scene_id: 'test_city',
    run_id: 'preview_1',
    layers: [{ asset: 'data/models/city.glb' }],
    artifacts: [
      { id: 'city_scene', asset: 'data/scene.json' },
      { id: 'wind', asset: 'data/physics/wind.npy' },
      { id: 'mask', asset: 'data/physics/mask.npy' },
    ],
    spatial: { georeferenced: false },
  };
  return {
    scene,
    manifest,
    read: async (url) => (url.pathname.endsWith('manifest.json') ? manifest : scene),
  };
}
test('retained city adapter keeps model/data origins and does not enable unavailable actors', async () => {
  const f = fixture();
  const scene = await loadRunScene(
    new URLSearchParams('scene=test_city&run=preview_1'),
    new URL('http://localhost/src/visualization/legacy/'),
    f.read,
  );
  assert.equal(scene.physics, 'http://localhost/project/test_city/runs/preview_1/data/physics/');
  assert.equal(
    scene.url('models/city.glb'),
    'http://localhost/project/test_city/runs/preview_1/data/models/city.glb',
  );
  assert.equal(scene.protocol_display.spatial.georeferenced, false);
  assert.equal(scene.replay, undefined);
});
test('adapter rejects path traversal, undeclared data, and incomplete results', async () => {
  const root = new URL('http://localhost/src/visualization/legacy/');
  await assert.rejects(
    loadRunScene(new URLSearchParams('scene=../escape&run=preview_1'), root),
    /canonical/,
  );
  let f = fixture();
  f.scene.layers.wind.file = '../../outside.npy';
  await assert.rejects(
    loadRunScene(new URLSearchParams('scene=test_city&run=preview_1'), root, f.read),
    /Undeclared/,
  );
  f = fixture();
  f.manifest.status = 'running';
  await assert.rejects(
    loadRunScene(new URLSearchParams('scene=test_city&run=preview_1'), root, f.read),
    /Incomplete/,
  );
});

test('solar calendar assets are checked independently of relative wind time', async () => {
  const f = fixture();
  f.scene.layers.solar = {
    dates: { 20250621: { ghi: 'summer.npy', shadow: 'summer_shadow.npy' } },
  };
  f.manifest.artifacts.push(
    { id: 'ghi', asset: 'data/physics/summer.npy' },
    { id: 'shadow', asset: 'data/physics/summer_shadow.npy' },
  );
  const scene = await loadRunScene(
    new URLSearchParams('scene=test_city&run=preview_1'),
    new URL('http://localhost/src/visualization/legacy/'),
    f.read,
  );
  assert.equal(scene.layers.solar.dates[20250621].ghi, 'summer.npy');
  f.scene.layers.solar.dates[20250621].shadow = '../missing.npy';
  await assert.rejects(
    loadRunScene(
      new URLSearchParams('scene=test_city&run=preview_1'),
      new URL('http://localhost/src/visualization/legacy/'),
      f.read,
    ),
    /Undeclared/,
  );
});
