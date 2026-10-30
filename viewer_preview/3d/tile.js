// Detailed South Kensington station tile: south_kensington_current.glb (Blender glTF export, Y up, a 390 x 400 m
// plate around the station: 245 OSM buildings with PBR facades, the station with its open railway cutting and
// platforms, roads / footways, gardens, trees, street lamps). Its local frame is rotated against the main model by
// the UTM grid convergence, so it is placed with a rigid transform fitted on the 237 buildings both files share
// (OSM ids); the residual is about 0.7 m (median). Inside the plate the main model's ground / roads / paths are
// clipped away and its copies of the tile's buildings (same OSM id), planting, parked cars and other street items
// are hidden; buildings that only the main model has stay. Outside the plate the tile is clipped.
import * as THREE from 'three';

export const TILE = {
  url: null,                            // set by main.js from scene.json (model.tile)
  bytes: 180338152,
  position: [901.85, 0.3, 689.57],      // tile origin in model coordinates; lifted 0.3 m above the main roads
  rotationY: 0.03799,                   // radians, about +Y
  rect: { min: [-195, -200], max: [195, 200] },   // the tile's ground plate, tile-local X / Z
};
const TILE_TREE = /tree[_ ](trunk|crown)/i;   // three.js turns the spaces of glTF names into underscores                          // "Inferred garden tree crown 12", "OSM tree trunk 3"
const TILE_FLAT = /^(District[_ ]ground|OSM[_ ]garden|[^|]+\|[_ ]\d+$)/;   // ground plate (with the railway cutting), gardens, "<street> | 4" road / footway pieces
const TILE_HIDDEN = /^Illustrative[_ ]vehicles/;                      // the tile's static cars: the SUMO replay draws the traffic
// main-model root names (glTF names sanitised by three.js: spaces -> "_") that are not buildings
const NON_BUILDING = /^(Traffic_road|Traffic_vehicle|Traffic_prediction|Bird|Site|Estimated_planting|AERIAL-VEHICLE|Entry_approaches)/;

const tileMatrix = new THREE.Matrix4().makeRotationY(TILE.rotationY).setPosition(...TILE.position);
const tileInverse = tileMatrix.clone().invert();
/** true when a model-space point lies inside the tile's built rectangle */
export function insideTile(p) {
  const q = p.clone().applyMatrix4(tileInverse);
  return q.x > TILE.rect.min[0] && q.x < TILE.rect.max[0] && q.z > TILE.rect.min[1] && q.z < TILE.rect.max[1];
}

/** Places the loaded tile scene, classifies its meshes (ground-like / trees / hidden), tones down the
 *  transmission glass and returns the group. `ground` and `trees` receive the meshes for the layer toggles. */
export function placeTile(gltf, { ground, trees }) {
  const group = new THREE.Group(); group.name = 'South Kensington detail tile';
  group.applyMatrix4(tileMatrix);
  group.add(gltf.scene); group.updateMatrixWorld(true);
  const box = new THREE.Box3(), size = new THREE.Vector3();
  let vehicles = 0;
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    let names = [];
    for (let a = o; a && a !== gltf.scene; a = a.parent) names.push(a.name || '');
    const root = names[names.length - 1];
    if (TILE_HIDDEN.test(root)) { o.visible = false; vehicles++; return; }
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    box.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld); box.getSize(size);
    if (TILE_TREE.test(root)) trees.push(o);
    else if (TILE_FLAT.test(root) || (size.y < 0.6 && Math.max(size.x, size.z) > 30)) ground.push(o);
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of mats) {
      if (m.transmission > 0) { m.transmission = 0; m.transparent = true; m.opacity = 0.45; m.depthWrite = false; m.needsUpdate = true; }
    }
  });
  console.log(`tile: ${vehicles} vehicle meshes hidden, ${ground.length} ground-like and ${trees.length} tree meshes classified`);
  return group;
}

/** OSM ids of the buildings modelled in the tile (node extras osm_id = "way/<id>/0" or "relation/<id>/0"). */
export function tileBuildingIds(scene) {
  const ids = new Set(); scene.traverse(o => { const m = /^(?:way|relation)\/(\d+)/.exec(o.userData?.osm_id || ''); if (m) ids.add(m[1]); }); return ids;
}

/** Hides the meshes of `scene` (main model or the supplementary buildings) that the tile replaces: buildings the tile
 *  also has (same OSM id in the root node name) and, inside the tile rectangle, everything that is not a building
 *  (roads, planting, parked cars, unnamed parts) - or every mesh when `buildingsByCentre` is set. Wide flat meshes
 *  (site ground, road network) are left alone: they get the clipping hole instead. Returns the hidden meshes.
 *  Call before batching so the hidden meshes stay out of the merged batches. */
export function hideReplaced(scene, ids, { buildingsByCentre = false } = {}) {
  scene.updateMatrixWorld(true);
  const hidden = [], box = new THREE.Box3(), size = new THREE.Vector3(), centre = new THREE.Vector3();
  scene.traverse(o => {
    if (!o.isMesh || !o.visible) return;
    let root = o;
    while (root.parent && root.parent !== scene) root = root.parent;
    const name = root.name || '';
    const m = /(?:way|relation)-(\d+)/.exec(name);
    let hide = !!m && ids.has(m[1]);
    if (!hide) {
      if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
      box.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld); box.getSize(size); box.getCenter(centre);
      const wide = size.y < 3 && Math.max(size.x, size.z) > 30;
      const building = !buildingsByCentre && name !== '' && !NON_BUILDING.test(name);
      hide = !wide && !building && insideTile(centre);
    }
    if (hide) { o.visible = false; hidden.push(o); }
  });
  return hidden;
}

/** Four vertical planes along the edges of the tile rectangle, in world space.
 *  `inward` = true: normals point into the rectangle (keep inside, for the tile);
 *  `inward` = false: normals point outwards (with clipIntersection = true this cuts a hole into the main model's ground). */
export function tileClipPlanes(inward) {
  const local = [
    [[1, 0, 0], [TILE.rect.min[0], 0, 0]], [[-1, 0, 0], [TILE.rect.max[0], 0, 0]],
    [[0, 0, 1], [0, 0, TILE.rect.min[1]]], [[0, 0, -1], [0, 0, TILE.rect.max[1]]],
  ];
  return local.map(([n, p]) => {
    const normal = new THREE.Vector3(...n).transformDirection(tileMatrix).multiplyScalar(inward ? 1 : -1);
    const point = new THREE.Vector3(...p).applyMatrix4(tileMatrix);
    return new THREE.Plane().setFromNormalAndCoplanarPoint(normal, point);
  });
}

/** Collects the materials of the given meshes (for the clipping hole in the main model's ground layers). */
export function materialsOf(meshes, into = new Set()) {
  for (const o of meshes) for (const m of Array.isArray(o.material) ? o.material : [o.material]) if (m) into.add(m);
  return into;
}

/** Assigns (or removes, planes = null) clipping planes to materials, or to every material below an Object3D. */
export function setClipping(target, planes, intersection) {
  const mats = target instanceof Set ? target : materialsOf((() => { const l = []; target.traverse(o => { if (o.isMesh || o.isLine || o.isPoints) l.push(o); }); return l; })());
  for (const m of mats) { m.clippingPlanes = planes; m.clipIntersection = !!planes && intersection; m.needsUpdate = true; }
}

/** Model-space bounding box centre of the tile's copy of an OSM building (for the alignment check in the console). */
export function tileBuildingCentre(scene, osmId) {
  let o = null; scene.traverse(x => { if (!o && new RegExp('^(way|relation)/' + osmId + '/').test(x.userData?.osm_id || '')) o = x; }); if (!o) return null;
  return new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
}
