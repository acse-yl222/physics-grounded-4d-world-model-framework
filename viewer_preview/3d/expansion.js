import * as THREE from 'three';
import { batchStaticCity } from '../../agents/demo_rev02/static-batches.js';

export const EXPANSION_URL = '../../geometry/expansion/output/kensington_gore_23_v1/replacement.glb';
export const EXPANSION_ID = 'way-117417431';
export const EXPANSION_BATCHES = [
  {url: EXPANSION_URL, ids: [EXPANSION_ID], projectionM: 0.75},
  {url: '../../geometry/expansion/output/batch03_v1/retained_batch02.glb?v=74dba832b28c', ids: ['way-117417421', 'way-117010286'], projectionM: 1.5},
  {url: '../../geometry/expansion/output/batch03_v1/replacement.glb?v=4498dbd5a5d5', ids: ['way-641757059', 'way-641603104', 'way-117010283', 'way-492431542'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch04_v1/replacement.glb?v=e03387bf2a98', ids: ["way-117010293", "way-27917475", "way-642055723"], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch05_v1/replacement.glb?v=1a5159ee6297', ids: ["way-1154608369", "way-642055721", "way-642055722"], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch06_v1/replacement.glb?v=0a4b19e6042e', ids: ["way-1154608372", "way-788306098", "way-640976478"], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch07_v1/replacement.glb?v=89ff5b030428', ids: ["way-703836510", "way-1133279024"], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch08_v1/replacement.glb?v=28beab20615a', ids: ["way-850528335", "way-850528336"], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch09_v1/replacement.glb?v=c03c3bedd044', ids: ['way-809238777', 'way-809238778', 'way-809238779'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch10_v1/replacement.glb?v=b303bf2121c3', ids: ['way-809238783', 'way-809238784', 'way-809238780'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch11_v1/replacement.glb?v=4f56f4a7ef2c', ids: ['way-851362854', 'way-851362855', 'way-851362835'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/princes_gate_27_v2/retained_batch12.glb?v=26e66c0e2e98', ids: ['way-640808103', 'way-810633525'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/princes_gate_27_v2/replacement.glb?v=05703a7f481e', ids: ['way-640097053'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch13_v1/replacement.glb?v=c2f1654603d6', ids: ['way-809238785', 'way-640097054', 'way-640808101'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch14_v1/replacement.glb?v=4c05f7561661', ids: ['way-810633524', 'way-810633526', 'way-851362836'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch18_v1/replacement.glb?v=0075c3f6819c', ids: ['way-810633522', 'way-810633528', 'way-851362838'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch17_v1/replacement.glb?v=c1177aa3d25c', ids: ['way-640097056', 'way-809238787', 'way-851362852'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch16_v1/replacement.glb?v=a4ad546493ca', ids: ['way-810633523', 'way-810633527', 'way-851362837'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch15_v1/replacement.glb?v=b5b51ad4b240', ids: ['way-640097055', 'way-640808105', 'way-809238786'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch19_v1/replacement.glb?v=bb59e7115568', ids: ['way-392603602', 'way-809238788', 'way-640457472'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch20_v1/replacement.glb?v=8d79cca4e455', ids: ['way-809386116', 'way-810633521', 'way-851362839'], projectionM: 1.65},
  {url: '../../geometry/expansion/output/batch21_v1/replacement.glb?v=ad747da31b73', ids: ['way-640097057', 'way-809238789', 'way-640457473'], projectionM: 1.65},
];

// Called before main-city batching. Keep the original exterior unbatched so
// comparison remains reversible; the existing entrance support stays in place.
export async function installExpansion(originalScene, replacementScene, ids = [EXPANSION_ID], projectionM = 0.75) {
  const expectedIds = new Set(ids);
  if (!expectedIds.size || expectedIds.size !== ids.length) throw new Error('Expansion: invalid ID list');
  const originals = [];
  originalScene.traverse(o => {
    if (expectedIds.has(o.userData.building_id) && /exterior/.test(o.name)) originals.push(o);
  });
  for (const id of ids) if (originals.filter(o => o.userData.building_id === id).length !== 1) throw new Error(`Expansion: expected one original exterior for ${id}`);
  const replacementIds = new Set();
  replacementScene.traverse(o => { if (o.userData.building_id) replacementIds.add(o.userData.building_id); });
  if (replacementIds.size !== ids.length || ids.some(id => !replacementIds.has(id))) throw new Error('Expansion building identity mismatch');
  originalScene.updateMatrixWorld(true); replacementScene.updateMatrixWorld(true);
  for (const original of originals) {
    const id = original.userData.building_id;
    const a = new THREE.Box3().setFromObject(original), b = new THREE.Box3();
    replacementScene.traverse(o => { if (o.userData.building_id === id) b.union(new THREE.Box3().setFromObject(o)); });
    if (b.isEmpty() || Math.max(Math.abs(a.min.x-b.min.x), Math.abs(a.max.x-b.max.x), Math.abs(a.min.z-b.min.z), Math.abs(a.max.z-b.max.z)) > projectionM) throw new Error(`Expansion footprint alignment mismatch: ${id}`);
  }
  const merged = await batchStaticCity(replacementScene);
  const object = new THREE.Group(); object.name = `Building refinements | ${ids.join(', ')}`;
  object.add(replacementScene, merged.object);
  for (const o of originals) o.visible = false;
  return { object, originals, setEnabled(on) { object.visible = on; for (const o of originals) o.visible = !on; } };
}
