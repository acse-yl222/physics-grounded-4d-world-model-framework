// Landmark module loader. A landmark module (landmarks/<id>.mjs) has no imports and
// default-exports { id, name, claims, references, notes, build(ctx) }. build()
// returns a THREE.Object3D in scene ENU metres that replaces the claimed footprints.
import * as THREE from 'three';
import * as kit from './kit.mjs';
import { buildGeneric } from './generic.mjs';

export async function loadLandmark(id, base = new URL('../landmarks/', import.meta.url)) {
  const mod = await import(new URL(`${id}.mjs`, base).href);
  const def = mod.default;
  if (!def || def.id !== id || typeof def.build !== 'function')
    throw new Error(`Landmark module ${id} must default-export { id: '${id}', build }`);
  return def;
}

export function buildLandmark(def, scene) {
  const claims = new Set(def.claims ?? []);
  const buildings = scene.buildings.filter((b) => claims.has(b.id));
  const missing = [...claims].filter((id) => !buildings.some((b) => b.id === id));
  if (missing.length) console.warn(`${def.id}: claimed ids not in scene: ${missing.join(', ')}`);
  const main = buildings.slice().sort((a, b) => area(b) - area(a))[0];
  const frame = main ? kit.ringFrame(main.polys[0][0]) : null;
  const ctx = {
    THREE,
    kit,
    buildings,
    byId: Object.fromEntries(buildings.map((b) => [b.id, b])),
    frame,
    scene,
    /** Generic fallback for a claimed footprint the module does not model in detail. */
    generic: (ids) =>
      buildGeneric({
        buildings: scene.buildings
          .filter((b) => ids.includes(b.id))
          .map((b) => ({ ...b, landmark: undefined })),
      }),
  };
  const object = def.build(ctx);
  object.name = `landmark:${def.id}`;
  object.userData.landmark = { id: def.id, name: def.name, claims: def.claims ?? [] };
  return object;
}

function area(b) {
  const ring = b.polys[0][0];
  let a = 0;
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    a += p[0] * q[1] - q[0] * p[1];
  }
  return Math.abs(a / 2);
}
