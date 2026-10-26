// Landmark module loader. A landmark module (landmarks/<id>.mjs) has no imports and
// default-exports { id, name, claims, references, notes, build(ctx) }. build()
// returns a THREE.Object3D in scene ENU metres that replaces the claimed footprints.
// Modules model flat ground at z = 0; on scenes with terrain buildLandmark lifts the
// whole object to its ground level (see landmarkGround) and pulls vertices at its
// base down to the terrain where that is lower, so modules need no change.
import * as THREE from 'three';
import * as kit from './kit.mjs';
import { assetObject, instance } from './assets.mjs';
import { buildGeneric } from './generic.mjs';
import { elevation, elevationFn, hasTerrain } from './terrain.mjs';

export async function loadLandmark(id, base = new URL('../landmarks/', import.meta.url)) {
  const mod = await import(new URL(`${id}.mjs`, base).href);
  const def = mod.default;
  if (!def || def.id !== id || typeof def.build !== 'function')
    throw new Error(`Landmark module ${id} must default-export { id: '${id}', build }`);
  return def;
}

export function buildLandmark(def, scene, assets = new Map()) {
  const asset = (id) => {
    if (!assets.has(id)) throw new Error(`${def.id}: unknown resources asset '${id}'`);
    return assets.get(id);
  };
  const claims = new Set(def.claims ?? []);
  const buildings = scene.buildings.filter((b) => claims.has(b.id));
  const missing = [...claims].filter((id) => !buildings.some((b) => b.id === id));
  if (missing.length) console.warn(`${def.id}: claimed ids not in scene: ${missing.join(', ')}`);
  const main = buildings.slice().sort((a, b) => area(b) - area(a))[0];
  const frame = main ? kit.ringFrame(main.polys[0][0]) : null;
  const terrain = hasTerrain(scene);
  // Ground of a landmark with claimed footprints: their lowest ground point.
  const grounds = buildings.map((b) => b.ground_z).filter(Number.isFinite);
  const claimedGround = terrain && grounds.length ? Math.min(...grounds) : null;
  const ctx = {
    THREE,
    kit,
    buildings,
    byId: Object.fromEntries(buildings.map((b) => [b.id, b])),
    frame,
    scene,
    /** Copy of a resources/ asset (street furniture, vehicles, trees) to place by hand. */
    asset: (id) => assetObject(asset(id)),
    /** Instanced copies of an asset at [[x, y, heading], ...] scene coordinates. */
    placeAssets: (id, placements, opts) => instance(asset(id), placements, opts),
    /** Generic fallback for a claimed footprint the module does not model in detail. */
    generic: (ids) =>
      buildGeneric({
        buildings: scene.buildings
          .filter((b) => ids.includes(b.id))
          .map((b) => ({
            ...b,
            landmark: undefined,
            // Relative to the landmark, which is lifted as a whole.
            ...(terrain && Number.isFinite(b.ground_z)
              ? {
                  ground_z: claimedGround === null ? undefined : b.ground_z - claimedGround,
                  ground_plane:
                    claimedGround === null || !b.ground_plane
                      ? undefined
                      : [b.ground_plane[0] - claimedGround, ...b.ground_plane.slice(1)],
                }
              : {}),
          })),
      }),
    /** Terrain height at ENU (x, y) in scene metres (0 on flat scenes). */
    elevation: (x, y) => elevation(scene, x, y),
    /** Ground level the object is lifted to (null on flat scenes / before build). */
    ground: claimedGround,
  };
  const object = def.build(ctx);
  if (terrain) placeOnTerrain(object, def, scene, claimedGround);
  object.name = `landmark:${def.id}`;
  object.userData.landmark = { id: def.id, name: def.name, claims: def.claims ?? [] };
  return object;
}

/**
 * Ground level for a landmark: the lowest ground of its claimed footprints; for
 * free-standing objects the lowest terrain under their box, except bridges over
 * mapped water, which meet the roads on the banks (median terrain of the box
 * outside water).
 */
export function landmarkGround(def, scene, box, claimedGround = null) {
  const at = elevationFn(scene);
  if (!at) return 0;
  const water = (scene.water ?? []).filter((w) => w.poly);
  const wet = (x, y) =>
    water.some((w) => pointIn(w.poly[0], x, y) && !w.poly.slice(1).some((h) => pointIn(h, x, y)));
  const cx = (box.x0 + box.x1) / 2,
    cy = (box.y0 + box.y1) / 2;
  const samples = [];
  const n = 24;
  for (let a = 0; a <= n; a++)
    for (let b = 0; b <= n; b++) {
      const x = box.x0 + ((box.x1 - box.x0) * a) / n,
        y = box.y0 + ((box.y1 - box.y0) * b) / n;
      samples.push([x, y, at(x, y)]);
    }
  if (/_bridge$/.test(def.id) && wet(cx, cy)) {
    const dry = samples.filter(([x, y]) => !wet(x, y)).map((p) => p[2]);
    if (dry.length) return dry.sort((p, q) => p - q)[Math.floor(dry.length / 2)];
  }
  if (claimedGround !== null) return claimedGround;
  return Math.min(...samples.map((p) => p[2]));
}

/**
 * Lift a landmark built on flat ground to its terrain level and extend its base:
 * vertices at the modelled ground (|z| <= 5 cm) move down to the terrain (less a
 * small margin) wherever the terrain is lower than the object's level.
 */
function placeOnTerrain(object, def, scene, claimedGround) {
  object.updateMatrixWorld(true);
  const b3 = new THREE.Box3().setFromObject(object);
  if (b3.isEmpty()) return;
  const box = { x0: b3.min.x, y0: b3.min.y, x1: b3.max.x, y1: b3.max.y };
  const ground = landmarkGround(def, scene, box, claimedGround);
  const at = elevationFn(scene);
  const v = new THREE.Vector3(),
    inv = new THREE.Matrix4();
  object.traverse((o) => {
    if (!o.isMesh || o.isInstancedMesh || !o.geometry?.attributes?.position) return;
    inv.copy(o.matrixWorld).invert();
    let pos = o.geometry.attributes.position,
      copied = false;
    for (let k = 0; k < pos.count; k++) {
      v.fromBufferAttribute(pos, k).applyMatrix4(o.matrixWorld);
      if (Math.abs(v.z) > 0.05) continue;
      const d = at(v.x, v.y) - ground;
      if (d > -0.05) continue;
      if (!copied) {
        // Geometry may be shared (asset prototypes): change a copy.
        o.geometry = o.geometry.clone();
        pos = o.geometry.attributes.position;
        copied = true;
      }
      v.z = d - 0.6;
      v.applyMatrix4(inv);
      pos.setXYZ(k, v.x, v.y, v.z);
    }
    if (copied) {
      o.geometry.computeBoundingBox();
      o.geometry.computeBoundingSphere();
    }
  });
  object.position.z += ground;
  object.userData.ground = ground;
}

function pointIn(ring, x, y) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i],
      [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
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
