export function decodeTraffic(meta, buffer) {
  const stride = meta.binary.record_bytes ?? 16;
  if (![16, 24].includes(stride) || buffer.byteLength !== meta.binary.bytes)
    throw new Error('Unsupported or truncated traffic data');
  if (
    !(meta.dt > 0) ||
    !Number.isInteger(meta.frames) ||
    meta.frames < 1 ||
    !Array.isArray(meta.vehicles)
  )
    throw new Error('Invalid traffic metadata');
  const view = new DataView(buffer),
    frames = [];
  let offset = 0;
  for (let f = 0; f < meta.frames; f++) {
    if (offset + 4 > buffer.byteLength) throw new Error('Missing traffic frame');
    const count = view.getUint32(offset, true);
    offset += 4;
    if (offset + stride * count > buffer.byteLength) throw new Error('Truncated traffic frame');
    const idx = new Uint32Array(count),
      xyh = new Float32Array(count * 3),
      z = stride === 24 ? new Float32Array(count) : undefined,
      speed = stride === 24 ? new Float32Array(count) : undefined,
      seen = new Set();
    for (let j = 0; j < count; j++) {
      const id = view.getUint32(offset, true);
      if (id >= meta.vehicles.length || seen.has(id)) throw new Error('Invalid vehicle identity');
      seen.add(id);
      idx[j] = id;
      for (let k = 0; k < 3; k++) xyh[j * 3 + k] = view.getFloat32(offset + 4 + k * 4, true);
      if (z) {
        z[j] = view.getFloat32(offset + 16, true);
        speed[j] = view.getFloat32(offset + 20, true);
      }
      offset += stride;
    }
    if (
      !xyh.every(Number.isFinite) ||
      (z && !z.every(Number.isFinite)) ||
      (speed && !speed.every((v) => Number.isFinite(v) && v >= 0))
    )
      throw new Error('Invalid vehicle coordinates or speed');
    frames.push({ idx, xyh, ...(z ? { z, speed } : {}) });
  }
  if (offset !== buffer.byteLength) throw new Error('Trailing traffic bytes');
  return { meta, frames };
}
export async function loadTraffic(base, binaryName, metaName = 'traffic.json') {
  const response = await fetch(`${base}/${metaName}`);
  if (!response.ok) throw new Error(`Traffic metadata: ${response.status}`);
  const meta = await response.json();
  const data = await fetch(`${base}/${binaryName ?? meta.binary.asset}`);
  if (!data.ok) throw new Error(`Traffic frames: ${data.status}`);
  const buffer = await data.arrayBuffer();
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', buffer)), (b) =>
    b.toString(16).padStart(2, '0'),
  ).join('');
  if (hash !== meta.binary.sha256) throw new Error('Traffic checksum mismatch');
  return decodeTraffic(meta, buffer);
}
