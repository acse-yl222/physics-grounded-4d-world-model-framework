/** Assemble the published GLB directly into one buffer, without duplicate part buffers. */
export async function fetchCityModel(manifestUrl, onProgress = () => {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(new Error('Model download timed out. Please retry.')), 180000);
  try {
    const response = await fetch(manifestUrl, {cache: 'no-cache', signal: controller.signal});
    if (!response.ok) throw new Error(`Model manifest: HTTP ${response.status}`);
    const man = await response.json(), parts = man.parts, total = man.total_bytes;
    if (!Number.isSafeInteger(total) || total <= 0 || !Array.isArray(parts) || !parts.length ||
        parts.some(p => !Number.isSafeInteger(p.bytes) || p.bytes <= 0 || typeof p.file !== 'string') ||
        parts.reduce((n,p) => n+p.bytes,0) !== total) throw new Error('Invalid model chunk sizes');
    const all = new Uint8Array(total), received = parts.map(() => 0);
    let offset = 0;
    await Promise.all(parts.map(async (part, index) => {
      const start = offset; offset += part.bytes;
      const url = new URL(part.file, new URL('./', manifestUrl));
      if (part.sha256) url.searchParams.set('v', part.sha256.slice(0,12));
      const r = await fetch(url, {signal: controller.signal});
      if (!r.ok) throw new Error(`Model part ${part.file}: HTTP ${r.status}`);
      const reader = r.body.getReader();
      try {
        for (;;) {
          const {done,value} = await reader.read(); if (done) break;
          if (received[index]+value.byteLength > part.bytes) throw new Error(`Model part ${part.file} is larger than declared`);
          all.set(value,start+received[index]);received[index]+=value.byteLength;
          onProgress({loaded:received.reduce((a,b)=>a+b,0),total});
        }
        if (received[index] !== part.bytes) throw new Error(`Model part ${part.file}: got ${received[index]} of ${part.bytes} bytes`);
      } finally { reader.releaseLock(); }
    }));
    return all.buffer;
  } catch(error) {
    controller.abort(); // Stop sibling downloads if a part fails.
    throw error;
  } finally { clearTimeout(timeout); }
}
