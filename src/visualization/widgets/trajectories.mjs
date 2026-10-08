import * as THREE from 'three';
import { DataWidget } from './index.mjs';
import { assetURL, enuToWorld, sampleTrajectories } from '../shared/time.mjs';
export class SparseTrajectories extends DataWidget {
  async load(context, layer, signal) {
    if (layer.kind !== 'trajectories' || !['step', 'linear'].includes(layer.sampling))
      throw new Error('Invalid sparse trajectory layer');
    if (layer.display.capabilities.some((c) => !['pick', 'opacity'].includes(c)))
      throw new Error('Unsupported trajectory capability');
    this.context = context;
    this.layer = layer;
    this.visible = true;
    this.disposed = false;
    this.objects = [];
    const response = await fetch(assetURL(context.baseURL, layer.asset), { signal });
    if (!response.ok) throw new Error('Trajectory asset unavailable');
    const data = await response.json();
    this.frames = data.frames;
    if (!Array.isArray(this.frames) || this.frames.length !== context.manifest.time.samples.length)
      throw new Error('Trajectory frame count mismatch');
    let capacity = 1;
    for (const frame of this.frames) {
      if (
        !Array.isArray(frame.ids) ||
        !frame.ids.every((id) => typeof id === 'string' && id) ||
        new Set(frame.ids).size !== frame.ids.length ||
        !Array.isArray(frame.positions) ||
        frame.positions.length !== frame.ids.length ||
        !frame.positions.every(
          (p) => Array.isArray(p) && p.length === 3 && p.every(Number.isFinite),
        )
      )
        throw new Error('Invalid trajectory frame');
      capacity = Math.max(capacity, frame.ids.length);
    }
    this.group = new THREE.Group();
    this.instances = new THREE.InstancedMesh(
      new THREE.BoxGeometry(3, 1.5, 3),
      new THREE.MeshStandardMaterial({ color: 0xffbe66 }),
      capacity,
    );
    this.group.add(this.instances);
    context.scene.add(this.group);
    this.setTime(context.manifest.time.samples[0]);
  }
  setTime(seconds) {
    if (this.disposed) return;
    const frame = sampleTrajectories(
      this.frames,
      this.context.manifest.time.samples,
      seconds,
      this.layer.sampling,
    );
    this.available = Boolean(frame);
    this.group.visible = this.visible && this.available;
    this.context.availability(this.layer.id, this.available);
    if (!frame) return;
    this.data = { ids: frame.ids };
    this.current = frame.positions;
    this.instances.count = frame.ids.length;
    frame.positions.forEach((position, i) =>
      this.instances.setMatrixAt(i, new THREE.Matrix4().makeTranslation(...enuToWorld(position))),
    );
    this.instances.instanceMatrix.needsUpdate = true;
    this.instances.computeBoundingSphere();
  }
  dispose() {
    this.frames = [];
    super.dispose();
  }
}
