const HALF = new Float32Array(65536);
for (let h = 0; h < 65536; h++) {
  const sign = h & 32768 ? -1 : 1,
    e = (h >> 10) & 31,
    f = h & 1023;
  HALF[h] =
    sign *
    (e === 0 ? f * 2 ** -24 : e === 31 ? (f ? NaN : Infinity) : (1 + f / 1024) * 2 ** (e - 15));
}
export class NpySource {
  constructor(url, encoding, signal) {
    this.url = url;
    this.encoding = encoding;
    this.signal = signal;
    this.frames = new Map();
  }
  async range(start, end) {
    const response = await fetch(this.url, {
      headers: { Range: `bytes=${start}-${end}` },
      signal: this.signal,
    });
    if (response.status !== 206) throw new Error('NPY requires the uwm serve HTTP range server');
    const buffer = await response.arrayBuffer();
    if (buffer.byteLength !== end - start + 1) throw new Error('Truncated NPY range');
    return buffer;
  }
  async open() {
    const first = new Uint8Array(await this.range(0, 11));
    if (String.fromCharCode(...first.slice(0, 6)) !== '\x93NUMPY')
      throw new Error('Invalid NPY magic');
    const view = new DataView(first.buffer),
      major = first[6];
    if (![1, 2, 3].includes(major)) throw new Error('Unsupported NPY version');
    const offset = major === 1 ? 10 : 12,
      length = major === 1 ? view.getUint16(8, true) : view.getUint32(8, true);
    if (length > 65536) throw new Error('NPY header too large');
    const header = new TextDecoder().decode(await this.range(offset, offset + length - 1));
    const dtype = /'descr'\s*:\s*'([^']+)'/.exec(header)?.[1],
      shape = /'shape'\s*:\s*\(([^)]*)\)/
        .exec(header)?.[1]
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean)
        .map(Number);
    if (
      /'fortran_order'\s*:\s*True/.test(header) ||
      dtype !== this.encoding.dtype ||
      JSON.stringify(shape) !== JSON.stringify(this.encoding.shape)
    )
      throw new Error('NPY encoding differs from manifest');
    this.offset = offset + length;
    this.itemSize = Number(dtype.slice(2));
    this.dynamic = this.encoding.axes.startsWith('T');
    this.frameSize = shape.slice(this.dynamic ? 1 : 0).reduce((a, b) => a * b, 1);
    return this;
  }
  frame(index) {
    if (!this.dynamic) index = 0;
    if (this.frames.has(index)) return this.frames.get(index);
    const start = this.offset + index * this.frameSize * this.itemSize;
    const promise = this.range(start, start + this.frameSize * this.itemSize - 1).then((buffer) => {
      const view = new DataView(buffer),
        result = new Float32Array(this.frameSize);
      for (let i = 0; i < result.length; i++) {
        const v =
          this.encoding.dtype === '|u1'
            ? view.getUint8(i)
            : this.itemSize === 2
              ? HALF[view.getUint16(i * 2, true)]
              : this.itemSize === 4
                ? view.getFloat32(i * 4, true)
                : view.getFloat64(i * 8, true);
        if (!Number.isFinite(v) && !this.invalidMask?.[i % this.invalidMask.length])
          throw new Error('Non-finite NPY value');
        result[i] = v;
      }
      return result;
    });
    this.frames.set(index, promise);
    while (this.frames.size > 3) this.frames.delete(this.frames.keys().next().value);
    promise.catch(() => this.frames.delete(index));
    return promise;
  }
  dispose() {
    this.frames.clear();
  }
}
export class NpyFrameSeries {
  constructor(base, encoding, signal, urlFor) {
    this.base = base;
    this.encoding = encoding;
    this.signal = signal;
    this.urlFor = urlFor;
    this.sources = new Map();
  }
  async open() {
    if (this.encoding.frame_assets.length !== this.encoding.shape[0])
      throw new Error('Frame index/shape mismatch');
    return this;
  }
  async frame(index) {
    if (!this.sources.has(index)) {
      const encoding = { ...this.encoding, shape: [1, ...this.encoding.shape.slice(1)] };
      const source = new NpySource(
        this.urlFor(this.base, this.encoding.frame_assets[index]),
        encoding,
        this.signal,
      );
      source.invalidMask = this.invalidMask;
      this.sources.set(
        index,
        source.open().then(() => source),
      );
      while (this.sources.size > 3) {
        const key = this.sources.keys().next().value;
        this.sources
          .get(key)
          .then((s) => s.dispose())
          .catch(() => {});
        this.sources.delete(key);
      }
    }
    return (await this.sources.get(index)).frame(0);
  }
  dispose() {
    this.sources.forEach((p) => p.then((s) => s.dispose()).catch(() => {}));
    this.sources.clear();
  }
}
