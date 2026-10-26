// Reusable asset library loader. Assets live in resources/<kind>/<id>.mjs, have no
// imports and default-export { id, kind, name, size, references, notes, build(ctx) }.
// build() returns a THREE.Group in local metres: origin at the base centre, z up,
// front facing +y. Prototypes are merged per material once and then placed many
// times as InstancedMesh (exported with EXT_mesh_gpu_instancing). build() receives
// ctx.detail = 'high' | 'low'; assets may return a lighter model for 'low', used
// for distant instances and for exported layers that hold tens of thousands.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import * as kit from './kit.mjs';

const RESOURCES = new URL('../resources/', import.meta.url);
const prototypes = new Map();

export async function loadAssets() {
  const res = await fetch(new URL('index.json', RESOURCES));
  if (!res.ok) throw new Error(`resources/index.json: ${res.status}`);
  const index = await res.json();
  const defs = new Map();
  for (const entry of index.assets) {
    const def = (await import(new URL(entry.file, RESOURCES).href)).default;
    if (def?.id !== entry.id) throw new Error(`Asset ${entry.file} must export id '${entry.id}'`);
    defs.set(def.id, def);
  }
  return defs;
}

function normalise(geometry, matrix) {
  let g = geometry.index ? geometry.toNonIndexed() : geometry.clone();
  g.applyMatrix4(matrix);
  if (!g.attributes.normal) g.computeVertexNormals();
  if (!g.attributes.uv)
    g.setAttribute(
      'uv',
      new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2),
    );
  for (const name of Object.keys(g.attributes))
    if (!['position', 'normal', 'uv'].includes(name)) g.deleteAttribute(name);
  return g;
}

/** Asset prototype as [{ geometry, material }] with one merged geometry per material. */
export function prototype(def, detail = 'high') {
  const key = `${def.id}:${detail}`;
  if (prototypes.has(key)) return prototypes.get(key);
  const root = def.build({ THREE, kit, detail });
  root.updateMatrixWorld(true);
  const byMaterial = new Map();
  root.traverse((o) => {
    if (!o.isMesh) return;
    if (!byMaterial.has(o.material)) byMaterial.set(o.material, []);
    byMaterial.get(o.material).push(normalise(o.geometry, o.matrixWorld));
  });
  const parts = [...byMaterial].map(([material, geos]) => {
    const geometry = mergeGeometries(geos, false);
    geos.forEach((g) => g.dispose());
    return { geometry, material };
  });
  prototypes.set(key, parts);
  return parts;
}

/** A standalone copy of an asset (e.g. for a landmark module to place a few). */
export function assetObject(def, detail = 'high') {
  const group = new THREE.Group();
  group.name = `asset:${def.id}`;
  for (const { geometry, material } of prototype(def, detail))
    group.add(new THREE.Mesh(geometry, material));
  return group;
}

/**
 * Instance an asset at placements [[x, y, heading, ...], ...] in scene ENU metres.
 * scaleOf(placement) may return a number (uniform) or [sx, sy, sz].
 */
export function instance(
  def,
  placements,
  { scaleOf = () => 1, z = 0, name, detail = 'high' } = {},
) {
  const group = new THREE.Group();
  group.name = name ?? `assets:${def.id}`;
  if (!placements.length) return group;
  const m = new THREE.Matrix4(),
    q = new THREE.Quaternion(),
    s = new THREE.Vector3(),
    up = new THREE.Vector3(0, 0, 1);
  for (const { geometry, material } of prototype(def, detail)) {
    const mesh = new THREE.InstancedMesh(geometry, material, placements.length);
    mesh.name = `${group.name}:${material.name}`;
    placements.forEach((p, k) => {
      const sc = scaleOf(p);
      Array.isArray(sc) ? s.set(...sc) : s.setScalar(sc);
      q.setFromAxisAngle(up, p[2] ?? 0);
      m.compose(new THREE.Vector3(p[0], p[1], z), q, s);
      mesh.setMatrixAt(k, m);
    });
    mesh.computeBoundingSphere();
    group.add(mesh);
  }
  group.userData.asset = { id: def.id, count: placements.length, detail };
  return group;
}
