/* Pre-rendered field frames (scenes/<id>/physics/web/<layer>/NNN.png, written by scenes/tools/export_web_frames.py).
   ~100 KB per frame instead of 1-9 MB of raw float16, so the fields also play over a slow link. Decoded back to the same
   Float32Array layout the raw path produces (gray: N values; rgb3: [u..., v..., w...]; bit: Uint8Array 0/1), quantised to
   1/255 of the layer's range. When web/index.json is missing the viewer keeps reading the raw .npy files. */
import { DATA } from './npy.js';

let BASE = '', index = null;
export async function initFrames() {
  BASE = DATA + 'web/';
  try { const r = await fetch(BASE + 'index.json', { cache: 'no-cache' }); index = r.ok ? await r.json() : null; } catch { index = null; }
  return !!index;
}
export function hasLayer(key) { return !!index?.layers?.[key]; }
export function layerMeta(key) { return index?.layers?.[key] ?? null; }
export function framesInfo() { return index ? `pre-rendered frames (${Object.keys(index.layers).length} layers)` : 'raw .npy frames'; }

const cache = new Map(), inflight = new Map();
let cacheBytes = 0;
const CACHE_CAP = 150 * 1024 * 1024;
let canvas = null, ctx = null;

async function decode(key, k) {
  const meta = index.layers[key], [h, w] = meta.shape_yx;
  const url = `${BASE}${key}/${String(k).padStart(3, '0')}.png`;
  const r = await fetch(url); if (!r.ok) throw new Error('frame missing: ' + url);
  const bmp = await createImageBitmap(await r.blob(), { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  if (!canvas || canvas.width !== w || canvas.height !== h) { canvas = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(w, h) : Object.assign(document.createElement('canvas'), { width: w, height: h }); ctx = canvas.getContext('2d', { willReadFrequently: true }); }
  ctx.drawImage(bmp, 0, 0); bmp.close();
  const px = ctx.getImageData(0, 0, w, h).data, n = w * h;
  if (meta.kind === 'bit') { const out = new Uint8Array(n); for (let i = 0; i < n; i++) out[i] = px[i * 4] > 127 ? 1 : 0; return out; }
  const [lo, hi] = meta.range, s = (hi - lo) / 255;
  if (meta.kind === 'rgb3') { const out = new Float32Array(3 * n); for (let i = 0; i < n; i++) { const o = i * 4; out[i] = lo + px[o] * s; out[n + i] = lo + px[o + 1] * s; out[2 * n + i] = lo + px[o + 2] * s; } return out; }
  const out = new Float32Array(n), log = key === 'poll';
  for (let i = 0; i < n; i++) { const v = lo + px[i * 4] * s; out[i] = log ? Math.pow(10, v) : v; }
  return out;
}

/** Decoded frame k of a pre-rendered layer (cached, LRU by bytes). */
export function getFrameF32(key, k) {
  const id = key + '#' + k;
  if (cache.has(id)) { const v = cache.get(id); cache.delete(id); cache.set(id, v); return Promise.resolve(v); }
  if (inflight.has(id)) return inflight.get(id);
  const p = decode(key, k).then(arr => {
    cache.set(id, arr); cacheBytes += arr.byteLength;
    while (cacheBytes > CACHE_CAP && cache.size > 1) { const first = cache.keys().next().value; cacheBytes -= cache.get(first).byteLength; cache.delete(first); }
    return arr;
  }).finally(() => inflight.delete(id));
  inflight.set(id, p);
  return p;
}
