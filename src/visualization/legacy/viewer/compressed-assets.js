/* Lossless resource transport, separate from the retained simulation encoding. */
const cache = new Map(),
  inflight = new Map();
let cacheBytes = 0;
const CAP = 64 * 1024 * 1024;
async function chunk(base, part) {
  const url = new URL(part.file, base);
  if (!url.href.startsWith(base.href)) throw new Error('Compressed asset escapes its resource');
  const key = url.href;
  if (cache.has(key)) {
    const bytes = cache.get(key);
    cache.delete(key);
    cache.set(key, bytes);
    return bytes;
  }
  if (inflight.has(key)) return inflight.get(key);
  const pending = (async () => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Compressed asset: HTTP ${response.status}`);
    const bytes = new Uint8Array(
      await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer(),
    );
    if (bytes.byteLength !== part.bytes) throw new Error('Invalid decoded resource size');
    cache.set(key, bytes);
    cacheBytes += bytes.byteLength;
    while (cacheBytes > CAP && cache.size > 1) {
      const first = cache.keys().next().value;
      cacheBytes -= cache.get(first).byteLength;
      cache.delete(first);
    }
    return bytes;
  })();
  inflight.set(key, pending);
  try {
    return await pending;
  } finally {
    inflight.delete(key);
  }
}
export async function readCompressedRange(base, asset, start, end) {
  if (
    !Number.isSafeInteger(start) ||
    !Number.isSafeInteger(end) ||
    start < 0 ||
    end < start ||
    end >= asset.total_bytes
  )
    throw new Error('Compressed resource range out of bounds');
  const output = new Uint8Array(end - start + 1);
  let filled = 0;
  for (const part of asset.parts) {
    const low = Math.max(start, part.offset),
      high = Math.min(end + 1, part.offset + part.bytes);
    if (low >= high) continue;
    const bytes = await chunk(new URL(base), part);
    output.set(bytes.subarray(low - part.offset, high - part.offset), low - start);
    filled += high - low;
  }
  if (filled !== output.byteLength) throw new Error('Missing compressed resource bytes');
  return output.buffer;
}
