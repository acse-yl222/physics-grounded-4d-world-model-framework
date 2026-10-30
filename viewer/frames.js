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

/* Two caches.
   - Decoded frames (cache): Float32Array per frame, 12.6 MB for a 1024² rgb3 wind frame, 16.8 MB for a 2048² gray frame.
     150 MB holds ~11 wind or ~8 flood/sunlight frames: a rolling window around the play head, never a whole layer
     (301 wind frames decoded would be 3.8 GB, 181 flood frames 3.0 GB).
   - Compressed frames (bytes): the Blob as downloaded, ~1 MB each, so a whole layer fits (wind 333 MB, flood 237 MB,
     sunlight 118 MB). This is the buffer a layer is preloaded into before it plays. Blobs are paged by the browser, not
     held on the JS heap. BYTES_CAP bounds it; frames behind the play head are released by the player (releaseBefore). */
const cache = new Map(), inflight = new Map();
let cacheBytes = 0;
const CACHE_CAP = 150 * 1024 * 1024;
let canvas = null, ctx = null;

const bytes = new Map(), fetching = new Map(), queue = [];
let bytesTotal = 0, active = 0;
const BYTES_CAP = ((navigator.deviceMemory ?? 8) >= 8 ? 768 : 256) * 1024 * 1024;
const SOFT_CAP = 0.9 * BYTES_CAP;
/* Fetches run FETCH_PARALLEL at a time in queue order, so frames arrive one after another at the link's rate: a window of
   parallel fetches on a slow link delivers them in bunches, which plays as stop-and-go. net.bps is the delivered throughput
   over the last few seconds (0 until two fetches completed). */
const FETCH_PARALLEL = 2, NET_WINDOW_MS = 4000;
const done = [];
export const net = { bps: 0 };
const frameUrl = (key, k) => `${BASE}${key}/${String(k).padStart(3, '0')}.${index.layers[key].extension ?? 'png'}`;
function noteDone(size) {
  const now = performance.now();
  done.push([now, size]);
  while (done.length && done[0][0] < now - NET_WINDOW_MS) done.shift();
  if (done.length >= 2) net.bps = done.reduce((s, d) => s + d[1], 0) / Math.max(0.25, (now - done[0][0]) / 1000);
}
function pump() {
  for (let i = 0; i < queue.length && active < FETCH_PARALLEL;) {
    const job = queue[i];
    if (job.droppable && bytesTotal > SOFT_CAP) { i++; continue; }   // buffer full: preload waits until the player releases played frames
    queue.splice(i, 1);
    active++;
    fetch(job.url).then(r => { if (!r.ok) throw new Error('frame missing: ' + job.url); return r.blob(); })
      .then(b => {
        noteDone(b.size);
        bytes.set(job.id, b); bytesTotal += b.size;
        while (bytesTotal > BYTES_CAP && bytes.size > 1) { const first = bytes.keys().next().value; bytesTotal -= bytes.get(first).size; bytes.delete(first); }
        fetching.delete(job.id); job.res(b);
      }, err => {
        // one retry for transient edge errors (GitHub Pages occasionally answers without CORS headers)
        if (!job.retried) { job.retried = true; queue.unshift(job); return; }
        fetching.delete(job.id); job.rej(err);
      })
      .finally(() => { active--; pump(); });
  }
}
/** Compressed bytes of frame k (cached, at most FETCH_PARALLEL fetches in flight, in request order).
    urgent: the frame to show now, moved to the front of the queue. droppable: a preload nobody awaits (cancelBuffered may
    drop it while queued, and it waits while the buffer is full). */
export function fetchFrameBytes(key, k, { urgent = false, droppable = false } = {}) {
  const id = key + '#' + k;
  if (bytes.has(id)) return Promise.resolve(bytes.get(id));
  if (fetching.has(id)) {
    const i = queue.findIndex(j => j.id === id);
    if (i >= 0 && urgent) { const [j] = queue.splice(i, 1); j.droppable = false; queue.unshift(j); pump(); }
    else if (i >= 0 && !droppable) queue[i].droppable = false;
    return fetching.get(id);
  }
  const p = new Promise((res, rej) => { const job = { id, url: frameUrl(key, k), res, rej, droppable }; urgent ? queue.unshift(job) : queue.push(job); });
  fetching.set(id, p);
  pump();
  return p;
}
/** Drop queued (not started) preloads, e.g. before buffering from a new position. */
export function cancelBuffered() {
  for (let i = queue.length - 1; i >= 0; i--) if (queue[i].droppable) { fetching.delete(queue[i].id); queue.splice(i, 1); }
}
/** Preload frames from..to of a layer, in play order, into the compressed buffer. */
export function bufferLayer(key, from, to) { for (let k = from; k <= to; k++) fetchFrameBytes(key, k, { droppable: true }); }
/** true when frame k is decoded or downloaded: showing it will not wait on the network. */
export function frameReady(key, k) { const id = key + '#' + k; return cache.has(id) || bytes.has(id); }
/** How far the contiguous buffer of a layer reaches from frame `from`: frontier = last frame with every frame from..frontier ready. */
export function bufferState(key, from, to) {
  let frontier = from - 1;
  while (frontier < to && frameReady(key, frontier + 1)) frontier++;
  return { frontier, have: frontier - from + 1, total: to - from + 1, heldBytes: bytesTotal, cap: BYTES_CAP, fps: layerNetFps(key) };
}
/** Release the compressed bytes of frames of a layer below k - keep (already played), so the preload can continue. */
export function releaseBefore(key, k, keep = 2) {
  for (const id of [...bytes.keys()]) { const h = id.lastIndexOf('#'); if (id.slice(0, h) === key && +id.slice(h + 1) < k - keep) { bytesTotal -= bytes.get(id).size; bytes.delete(id); } }
  pump();
}
/** Frames per second the link delivered recently for this layer (Infinity until measured). */
export function layerNetFps(key) { const kb = index?.layers?.[key]?.avg_kb; return net.bps && kb ? net.bps / (kb * 1024) : Infinity; }

async function decode(key, k, urgent) {
  const meta = index.layers[key], [h, w] = meta.shape_yx;
  const blob = await fetchFrameBytes(key, k, { urgent });
  const bmp = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  if (!canvas || canvas.width !== w || canvas.height !== h) { canvas = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(w, h) : Object.assign(document.createElement('canvas'), { width: w, height: h }); ctx = canvas.getContext('2d', { willReadFrequently: true }); }
  ctx.drawImage(bmp, 0, 0); bmp.close();
  const px = ctx.getImageData(0, 0, w, h).data, n = w * h;
  if (meta.kind === 'bit') { const out = new Uint8Array(n); for (let i = 0; i < n; i++) out[i] = px[i * 4] > 127 ? 1 : 0; return out; }
  const [lo, hi] = meta.range, s = (hi - lo) / 255;
  if (meta.kind === 'rgb3') { const out = new Float32Array(3 * n); for (let i = 0; i < n; i++) { const o = i * 4; out[i] = lo + px[o] * s; out[n + i] = lo + px[o + 1] * s; out[2 * n + i] = lo + px[o + 2] * s; } return out; }
  const out = new Float32Array(n), log = meta.value_transform === 'log10' || (meta.value_transform == null && key === 'poll');
  for (let i = 0; i < n; i++) { const v = lo + px[i * 4] * s; out[i] = meta.value_transform === 'log1p' ? meta.value_scale * (Math.pow(10, v) - 1) : log ? Math.pow(10, v) : v; }
  return out;
}

/** Decoded frame k of a pre-rendered layer (cached, LRU by bytes). urgent = the frame to show now (fetched first). */
export function getFrameF32(key, k, urgent = false) {
  const id = key + '#' + k;
  if (cache.has(id)) { const v = cache.get(id); cache.delete(id); cache.set(id, v); return Promise.resolve(v); }
  if (inflight.has(id)) { if (urgent) fetchFrameBytes(key, k, { urgent: true }); return inflight.get(id); }
  const p = decode(key, k, urgent).then(arr => {
    cache.set(id, arr); cacheBytes += arr.byteLength;
    while (cacheBytes > CACHE_CAP && cache.size > 1) { const first = cache.keys().next().value; cacheBytes -= cache.get(first).byteLength; cache.delete(first); }
    return arr;
  }).finally(() => inflight.delete(id));
  inflight.set(id, p);
  return p;
}
