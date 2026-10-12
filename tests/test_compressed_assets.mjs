import test from 'node:test';
import assert from 'node:assert/strict';
import { gzipSync } from 'node:zlib';
import { readFile } from 'node:fs/promises';
const moduleURL = async (file) =>
  'data:text/javascript;base64,' +
  Buffer.from(
    await readFile(new URL('../src/visualization/legacy/viewer/' + file, import.meta.url)),
  ).toString('base64');
const { readCompressedRange } = await import(await moduleURL('compressed-assets.js'));
const { fetchCityModel } = await import(await moduleURL('model-source.js'));
const { loadPublishedScene } = await import(await moduleURL('scene-public.js'));
test('lossless resource reads cross gzip chunk boundaries and reject missing/out-of-bounds bytes', async () => {
  const original = globalThis.fetch;
  const asset = {
    total_bytes: 8,
    parts: [
      { file: 'a.gz', offset: 0, bytes: 4 },
      { file: 'b.gz', offset: 4, bytes: 4 },
    ],
  };
  globalThis.fetch = async (url) =>
    new Response(gzipSync(Buffer.from(String(url).endsWith('a.gz') ? [0, 1, 2, 3] : [4, 5, 6, 7])));
  try {
    assert.deepEqual(
      [...new Uint8Array(await readCompressedRange('https://example.org/physics/', asset, 2, 6))],
      [2, 3, 4, 5, 6],
    );
    await assert.rejects(
      readCompressedRange('https://example.org/physics/', asset, 0, 8),
      /bounds/,
    );
    await assert.rejects(
      readCompressedRange(
        'https://example.org/physics/',
        { ...asset, parts: [asset.parts[0]] },
        2,
        6,
      ),
      /Missing/,
    );
    await assert.rejects(
      readCompressedRange(
        'https://example.org/physics/',
        { total_bytes: 2, parts: [{ file: '../escape.gz', offset: 0, bytes: 2 }] },
        0,
        1,
      ),
      /escapes/,
    );
  } finally {
    globalThis.fetch = original;
  }
});
test('gzip model chunks assemble exactly without changing legacy chunk behavior', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (url) =>
    String(url).endsWith('manifest.json')
      ? new Response(
          JSON.stringify({
            total_bytes: 4,
            parts: [{ file: 'model.gz', bytes: 4, encoding: 'gzip' }],
          }),
        )
      : new Response(gzipSync(Buffer.from([1, 2, 3, 4])));
  try {
    assert.deepEqual(
      [...new Uint8Array(await fetchCityModel('https://example.org/manifest.json'))],
      [1, 2, 3, 4],
    );
  } finally {
    globalThis.fetch = original;
  }
});
test('published selection uses the catalogue and recorded source identity', async () => {
  const scene = {
    id: 'test_city',
    title: 'Test',
    model: { parts_manifest: 'model/manifest.json' },
    layers: { wind: { file: 'wind.npy', frames: 2, time_s: [50, 100] } },
  };
  const catalog = {
    resources_url: 'https://example.org/',
    scenes: [
      {
        scene_id: 'test_city',
        presentation: {
          version: 'preview_1',
          descriptor: 'project/test_city/previews/preview_1/scene.json',
        },
      },
    ],
  };
  const read = async (url) =>
    String(url).endsWith('public-scenes.json')
      ? catalog
      : String(url).endsWith('scene.json')
        ? structuredClone(scene)
        : String(url).endsWith('transport.json')
          ? { schema_version: '1.0.0', npy: { 'wind.npy': {} } }
          : {
              status: 'complete',
              scene_id: 'test_city',
              run_id: 'preview_1',
              spatial: { georeferenced: false },
            };
  const selected = await loadPublishedScene(
    new URLSearchParams('scene=test_city&presentation=preview_1'),
    new URL('https://site.org/viewer/../'),
    read,
  );
  assert.equal(selected.protocol_display.published, true);
  assert.equal(selected.protocol_display.spatial.georeferenced, false);
  assert.equal(
    selected.model.parts_manifest,
    'https://example.org/project/test_city/previews/preview_1/model/manifest.json',
  );
  await assert.rejects(
    loadPublishedScene(
      new URLSearchParams('scene=unknown&presentation=preview_1'),
      new URL('https://site.org/'),
      read,
    ),
    /Unknown/,
  );
  scene.model.parts_manifest = '../escape.json';
  await assert.rejects(
    loadPublishedScene(
      new URLSearchParams('scene=test_city&presentation=preview_1'),
      new URL('https://site.org/'),
      read,
    ),
    /escapes/,
  );
});
