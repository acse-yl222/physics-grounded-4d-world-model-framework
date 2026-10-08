import * as THREE from 'three';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { DataWidget, registry } from './index.mjs';
import { assetURL } from '../shared/time.mjs';
import { NpySource, NpyFrameSeries } from '../shared/npy.mjs';
import { SparseTrajectories } from './trajectories.mjs';
import { batchStaticCity } from '../shared/static-batches.mjs';

class GlbWidget extends DataWidget {
  async load(context, layer, signal) {
    if (
      layer.kind !== 'mesh' ||
      layer.encoding?.coordinate_frame !== 'glTF-y-up' ||
      layer.sampling !== 'static'
    )
      throw new Error('Invalid GLB layer contract');
    if (layer.display.capabilities.some((c) => !['pick', 'opacity'].includes(c)))
      throw new Error('Unsupported GLB capability');
    this.context = context;
    this.layer = layer;
    this.data = {};
    this.visible = true;
    this.available = true;
    this.disposed = false;
    this.objects = [];
    this.current = true;
    const response = await fetch(assetURL(context.baseURL, layer.asset), { signal });
    if (!response.ok) throw new Error(`GLB load failed (${response.status})`);
    const bytes = await response.arrayBuffer();
    if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
    this.draco = new DRACOLoader().setDecoderPath(
      new URL('../vendor/three/examples/jsm/libs/draco/gltf/', import.meta.url).href,
    );
    const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).setDRACOLoader(this.draco);
    const gltf = await loader.parseAsync(bytes, '');
    this.group = gltf.scene;
    if (signal.aborted) {
      this.dispose();
      throw new DOMException('Aborted', 'AbortError');
    }
    // glTF is x-east/y-up/z-south; this matches the viewer's ENU -> Three mapping.
    const batches = await batchStaticCity(this.group);
    this.group.add(batches.object);
    const hidden = [];
    this.group.traverse((o) => {
      if (o.isMesh && !o.visible) hidden.push(o);
    });
    hidden.forEach((o) => {
      o.geometry.dispose();
      o.removeFromParent();
    });
    this.batchStats = batches.stats;
    if (signal.aborted) {
      this.dispose();
      throw new DOMException('Aborted', 'AbortError');
    }
    context.scene.add(this.group);
    context.availability(layer.id, true);
  }
  setTime() {
    if (!this.disposed) this.available = true;
  }
  dispose() {
    this.draco?.dispose();
    super.dispose();
  }
}
class GridWidget extends DataWidget {
  async load(context, layer, signal) {
    if (!['vector_field', 'scalar_field'].includes(layer.kind))
      throw new Error('Unsupported NPY layer kind');
    if (layer.display.capabilities.some((c) => !['pick', 'legend', 'opacity'].includes(c)))
      throw new Error('Unsupported grid capability');
    const e = layer.encoding,
      vector = layer.kind === 'vector_field',
      dynamic = layer.sampling !== 'static';
    const axes = (dynamic ? 'T' : '') + (vector ? 'C' : '') + 'YX';
    if (e.axes !== axes || e.coordinate_frame !== 'ENU' || e.sample_location !== 'cell_center')
      throw new Error('Unsupported grid encoding');
    if (dynamic && e.shape[0] !== context.manifest.time.samples.length)
      throw new Error('Grid time dimension mismatch');
    if (vector && e.shape[dynamic ? 1 : 0] !== 3) throw new Error('Grid needs three components');
    this.sourceLayer = layer;
    this.source =
      layer.format === 'npy_frames'
        ? new NpyFrameSeries(context.baseURL, e, signal, assetURL)
        : new NpySource(assetURL(context.baseURL, layer.asset), e, signal);
    await this.source.open();
    this.sequence = 0;
    const ny = e.shape.at(-2),
      nx = e.shape.at(-1),
      step = Math.max(1, Math.ceil(Math.sqrt((nx * ny) / (vector ? 600 : 4096))));
    let heights = null,
      mask = null;
    if (e.mask_asset) {
      const source = await new NpySource(
        assetURL(context.baseURL, e.mask_asset),
        { dtype: '|u1', shape: [ny, nx], axes: 'YX' },
        signal,
      ).open();
      mask = await source.frame(0);
      source.dispose();
      if (mask.some((v) => v !== 0 && v !== 1)) throw new Error('Invalid missing-value mask');
      this.source.invalidMask = mask;
    }
    if (e.height_asset) {
      const source = await new NpySource(
        assetURL(context.baseURL, e.height_asset),
        { dtype: e.height_dtype, shape: [ny, nx], axes: 'YX' },
        signal,
      ).open();
      heights = await source.frame(0);
      source.dispose();
    }
    this.indices = [];
    const positions = [];
    for (let y = Math.floor(step / 2); y < ny; y += step)
      for (let x = Math.floor(step / 2); x < nx; x += step) {
        if (mask?.[y * nx + x]) continue;
        this.indices.push(y * nx + x);
        positions.push([
          e.origin_m[0] + (x + 0.5) * e.spacing_m[0],
          e.origin_m[1] + (y + 0.5) * e.spacing_m[1],
          e.origin_m[2] + (heights?.[y * nx + x] || 0),
        ]);
      }
    this.plane = nx * ny;
    this.vector = vector;
    const first = await this.source.frame(0);
    const values = this.extract(first);
    const data = { positions, [vector ? 'vectors' : 'values']: values };
    this.initialize(context, { ...layer, format: 'json', sampling: 'static' }, data);
    this.layer = layer;
    this.scale = Math.min(...e.spacing_m) * step * 0.025;
    this.displayStep = step;
    this.loadedTime = context.manifest.time.samples[0] || 0;
    await this.setTime(this.loadedTime);
  }
  extract(frame) {
    return this.indices.map((i) =>
      this.vector ? [frame[i], frame[this.plane + i], frame[2 * this.plane + i]] : frame[i],
    );
  }
  async setTime(seconds) {
    if (this.disposed || !this.source) return;
    const times = this.context.manifest.time.samples;
    this.seconds = seconds;
    if (this.sourceLayer.sampling !== 'static' && (seconds < times[0] || seconds > times.at(-1))) {
      this.sequence++;
      this.pendingKey = null;
      this.renderedKey = null;
      this.available = false;
      this.group.visible = false;
      this.context.availability(this.layer.id, false);
      return;
    }
    let low = 0;
    while (
      this.sourceLayer.sampling !== 'static' &&
      low < times.length - 1 &&
      times[low + 1] <= seconds
    )
      low++;
    const high = this.sourceLayer.sampling === 'linear' ? Math.min(low + 1, times.length - 1) : low;
    const key = high === low ? String(low) : `${low}:${high}:${seconds}`;
    if (this.renderedKey === key) {
      this.sequence++;
      this.pendingKey = null;
      return;
    }
    if (this.pendingKey === key) return;
    const serial = ++this.sequence;
    this.pendingKey = key;
    try {
      const [a, b] = await Promise.all([this.source.frame(low), this.source.frame(high)]);
      if (this.disposed || serial !== this.sequence) return;
      const weight = high === low ? 0 : (seconds - times[low]) / (times[high] - times[low]);
      const first = this.extract(a),
        last = this.extract(b);
      this.data[this.vector ? 'vectors' : 'values'] = first.map((v, i) =>
        this.vector ? v.map((x, j) => x + (last[i][j] - x) * weight) : v + (last[i] - v) * weight,
      );
      const layer = this.layer;
      this.layer = { ...layer, sampling: 'static' };
      DataWidget.prototype.setTime.call(this, seconds);
      this.layer = layer;
      this.loadedTime = seconds;
      this.renderedKey = key;
    } catch (error) {
      if (!this.disposed && serial === this.sequence) {
        this.available = false;
        this.group.visible = false;
        this.context.availability(this.layer.id, false, error.message);
      }
    } finally {
      if (serial === this.sequence) this.pendingKey = null;
    }
  }
  pick(query) {
    const hit = super.pick(query);
    if (hit) hit.display_stride = this.displayStep;
    return hit;
  }
  dispose() {
    this.source?.dispose();
    super.dispose();
  }
}
export function createWidget(layer) {
  if (!registry.has(layer.display?.widget) || !registry.has(layer.kind))
    throw new Error(`Unsupported widget/kind: ${layer.display?.widget}/${layer.kind}`);
  if (layer.format === 'trajectory_frames') return new SparseTrajectories();
  if (layer.format === 'glb') return new GlbWidget();
  if (['npy', 'npy_frames'].includes(layer.format)) return new GridWidget();
  if (layer.format === 'json') return registry.get(layer.display.widget)();
  throw new Error(`Unsupported format: ${layer.format}`);
}
