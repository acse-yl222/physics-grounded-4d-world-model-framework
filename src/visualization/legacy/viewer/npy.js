/* Minimal .npy reader over HTTP Range requests (ES module), used by the 3-D page. Paths are relative to the scene's
   physics/ folder (DATA, set by main.js from scene.json before any read). */
export let DATA = '';
export function setDataBase(url) { DATA = url; }

const F16 = new Float32Array(65536);
for (let h = 0; h < 65536; h++) {
  const s = (h >> 15) & 1, e = (h >> 10) & 0x1f, f = h & 0x3ff;
  let v;
  if (e === 0) v = f * Math.pow(2, -24);
  else if (e === 31) v = f ? NaN : Infinity;
  else v = (1 + f / 1024) * Math.pow(2, e - 15);
  F16[h] = s ? -v : v;
}
export function f16(u) {
  if (!(u instanceof Uint16Array)) return u;
  const out = new Float32Array(u.length);
  for (let i = 0; i < u.length; i++) out[i] = F16[u[i]];
  return out;
}

export class Npy {
  constructor(path) { this.path = path; this.meta = null; this._hdr = null; }
  async header() {
    if (this.meta) return this.meta;
    if (!this._hdr) this._hdr = (async () => {
      const r = await fetch(DATA + this.path, { headers: { Range: 'bytes=0-511' } });
      if (r.status !== 206) throw new Error('The server does not support Range requests - start it with python3 serve.py');
      const buf = new Uint8Array(await r.arrayBuffer());
      const major = buf[6];
      let hlen, off;
      if (major === 1) { hlen = buf[8] | (buf[9] << 8); off = 10; }
      else { hlen = (buf[8] | (buf[9] << 8) | (buf[10] << 16) | (buf[11] << 24)) >>> 0; off = 12; }
      const hdr = new TextDecoder('latin1').decode(buf.subarray(off, off + hlen));
      const descr = /'descr':\s*'([^']+)'/.exec(hdr)[1];
      const shape = /'shape':\s*\(([^)]*)\)/.exec(hdr)[1].split(',').map(s => s.trim()).filter(Boolean).map(Number);
      const itemsize = /f2/.test(descr) ? 2 : /b1|u1|i1/.test(descr) ? 1 : /f4|i4/.test(descr) ? 4 : 8;
      const block = shape.slice(1).reduce((a, b) => a * b, 1);
      this.meta = { descr, shape, itemsize, offset: off + hlen, block };
      return this.meta;
    })();
    return this._hdr;
  }
  async readAll() {
    const m = await this.header();
    const total = m.shape.reduce((a, b) => a * b, 1);
    return this._fetch(m, m.offset, m.offset + total * m.itemsize - 1);
  }
  async read(index) {
    const m = await this.header();
    const start = m.offset + index * m.block * m.itemsize;
    return this._fetch(m, start, start + m.block * m.itemsize - 1);
  }
  async _fetch(m, start, end) {
    const r = await fetch(DATA + this.path, { headers: { Range: `bytes=${start}-${end}` } });
    if (r.status !== 206) throw new Error('Range request failed: ' + this.path);
    const buf = await r.arrayBuffer();
    if (m.itemsize === 2) return new Uint16Array(buf);
    if (m.itemsize === 1) return new Uint8Array(buf);
    return new Float32Array(buf);
  }
}

const files = new Map();
export function npy(path) { if (!files.has(path)) files.set(path, new Npy(path)); return files.get(path); }

const cache = new Map(), inflight = new Map();
let cacheBytes = 0;
export const CACHE_CAP = 200 * 1024 * 1024;   // raw frames kept for scrubbing; 600 MB pushed low-memory machines into GC stalls
export function cacheInfo() { return { bytes: cacheBytes, frames: cache.size }; }
/** Cached, LRU-evicted frame read (raw bytes; decode with f16()). */
export async function getFrame(path, index) {
  const key = path + '#' + index;
  if (cache.has(key)) { const v = cache.get(key); cache.delete(key); cache.set(key, v); return v; }
  if (inflight.has(key)) return inflight.get(key);
  const p = (async () => {
    const arr = await npy(path).read(index);
    cache.set(key, arr); cacheBytes += arr.byteLength;
    while (cacheBytes > CACHE_CAP && cache.size > 1) {
      const k = cache.keys().next().value;
      cacheBytes -= cache.get(k).byteLength; cache.delete(k);
    }
    return arr;
  })();
  inflight.set(key, p);
  try { return await p; } finally { inflight.delete(key); }
}
const masks = {};
export async function loadMask(path) { if (!masks[path]) masks[path] = f16(await npy(path).readAll()); return masks[path]; }
