import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(
  new URL('../src/visualization/legacy/viewer/model-source.js', import.meta.url),
  'utf8',
);
const { fetchCityModel } = await import(
  'data:text/javascript;base64,' + Buffer.from(source).toString('base64')
);
for (const mode of ['success', 'manifest404', 'truncated', 'oversize', 'invalid'])
  test(`chunk loader: ${mode}`, async () => {
    const original = globalThis.fetch;
    let signal;
    globalThis.fetch = async (url, options) => {
      signal = options.signal;
      if (String(url).endsWith('manifest.json'))
        return new Response(
          JSON.stringify({
            total_bytes: mode === 'invalid' ? 9 : 4,
            parts: [
              { file: 'a', bytes: 2 },
              { file: 'b', bytes: 2 },
            ],
          }),
          { status: mode === 'manifest404' ? 404 : 200 },
        );
      return new Response(
        new Uint8Array(
          String(url).endsWith('/a')
            ? [1, 2]
            : mode === 'truncated'
              ? [3]
              : mode === 'oversize'
                ? [3, 4, 5]
                : [3, 4],
        ),
      );
    };
    try {
      if (mode === 'success') {
        const progress = [];
        assert.deepEqual(
          [
            ...new Uint8Array(
              await fetchCityModel('https://example.org/manifest.json', (p) => progress.push(p)),
            ),
          ],
          [1, 2, 3, 4],
        );
        assert.equal(progress.at(-1).loaded, 4);
      } else {
        await assert.rejects(fetchCityModel('https://example.org/manifest.json'));
        assert.equal(signal.aborted, true);
      }
    } finally {
      globalThis.fetch = original;
    }
  });
