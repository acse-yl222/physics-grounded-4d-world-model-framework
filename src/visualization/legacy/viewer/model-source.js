/* City model in parts. On the GitHub Pages copy a large model lives in the companion repository acse-yl222/urban-world-model-models,
   split into parts under GitHub's 100 MB limit and served by that repository's Pages site (which sends Access-Control-Allow-Origin: *;
   release assets do not, which is why the model is not fetched from a release). scene.json names the parts manifest
   (model.parts_manifest); the parts are fetched in parallel and concatenated here. */

/** Fetch a model described by a parts manifest as one ArrayBuffer, reporting {loaded, total} like GLTFLoader's progress. */
export async function fetchCityModel(manifestUrl, onProgress = () => {}) {
  const man = await (await fetch(manifestUrl, { cache: 'no-cache' })).json();   // always revalidated: a stale manifest with old part sizes made the load fail after a model update
  const base = new URL('./', manifestUrl).href;
  const parts = man.parts, total = man.total_bytes, got = parts.map(() => 0);
  const report = () => onProgress({ loaded: got.reduce((a, b) => a + b, 0), total });
  const buffers = await Promise.all(parts.map(async (p, i) => {
    const r = await fetch(base + p.file + (p.sha256 ? '?v=' + p.sha256.slice(0, 12) : '')); if (!r.ok) throw new Error(`model part ${p.file}: HTTP ${r.status}`);
    const reader = r.body.getReader(), chunks = [];
    for (;;) { const { done, value } = await reader.read(); if (done) break; chunks.push(value); got[i] += value.byteLength; report(); }
    const out = new Uint8Array(p.bytes); let o = 0; for (const c of chunks) { out.set(c, o); o += c.byteLength; }
    if (o !== p.bytes) throw new Error(`model part ${p.file}: got ${o} of ${p.bytes} bytes`);
    return out;
  }));
  const all = new Uint8Array(total); let o = 0; for (const b of buffers) { all.set(b, o); o += b.byteLength; }
  return all.buffer;
}
