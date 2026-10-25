// Studio page: renders landmarks / city regions for review and exports GLB layers.
// Query parameters:
//   scene=<url>                      prepared scene JSON (default: repo cache)
//   landmark=<id>&context=<m>        one landmark plus generic surroundings
//   x=<m>&y=<m>&r=<m>                a city region centred on (x, y)
//   shadows=1                        enable sun shadows
// window.studio exposes ready, view(name), stats and exportLayers(spec).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { buildGeneric } from './three/generic.mjs';
import { assetObject, loadAssets } from './three/assets.mjs';
import { buildFurniture, buildGround, buildTrees } from './three/ground.mjs';
import { buildLandmark, loadLandmark } from './three/landmarks.mjs';

const params = new URLSearchParams(location.search);
const info = document.getElementById('info');
const say = (t) => (info.textContent = t);

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = params.get('shadows') === '1';
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene3 = new THREE.Scene();
scene3.background = new THREE.Color('#bcd3e6');
const world = new THREE.Group(); // ENU (z-up) content
world.rotation.x = -Math.PI / 2;
scene3.add(world);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.5, 30000);
const controls = new OrbitControls(camera, renderer.domElement);
scene3.add(new THREE.HemisphereLight('#e8f1ff', '#5b6150', 1.6));
const sun = new THREE.DirectionalLight('#fff4e0', 2.6);
scene3.add(sun, sun.target);
sun.castShadow = renderer.shadowMap.enabled;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.bias = -0.0005;

const enu = (x, y, z) => new THREE.Vector3(x, z, -y);
let focus = { x: 0, y: 0, z: 0, size: 1000 };

function placeSun() {
  const d = focus.size * 2;
  sun.position.copy(enu(focus.x - d * 0.5, focus.y - d * 0.8, d * 0.9));
  sun.target.position.copy(enu(focus.x, focus.y, 0));
  const s = sun.shadow.camera;
  s.left = s.bottom = -focus.size;
  s.right = s.top = focus.size;
  s.near = 1;
  s.far = d * 4;
  s.updateProjectionMatrix();
}

/** Named camera views around the focus: ne/nw/se/sw (aerial), top, street_<dir>. */
function view(name = 'ne') {
  const { x, y, z, size } = focus;
  const dirs = {
    n: [0, 1],
    s: [0, -1],
    e: [1, 0],
    w: [-1, 0],
    ne: [1, 1],
    nw: [-1, 1],
    se: [1, -1],
    sw: [-1, -1],
  };
  let eye,
    target = enu(x, y, z);
  if (name === 'top') eye = enu(x, y - 1, size * 2.2);
  else if (name.startsWith('street_')) {
    const [dx, dy] = dirs[name.slice(7)] ?? dirs.s;
    const l = Math.hypot(dx, dy);
    eye = enu(x + (dx / l) * size * 2.4, y + (dy / l) * size * 2.4, 1.7);
    target = enu(x, y, Math.max(z * 0.8, 8));
  } else {
    const [dx, dy] = dirs[name] ?? dirs.ne;
    const l = Math.hypot(dx, dy);
    eye = enu(x + (dx / l) * size * 2.1, y + (dy / l) * size * 2.1, z + size * 1.3);
  }
  camera.position.copy(eye);
  controls.target.copy(target);
  camera.near = Math.max(0.3, size / 2000);
  camera.far = size * 60;
  camera.updateProjectionMatrix();
  controls.update();
  renderer.render(scene3, camera);
}

async function loadScene() {
  const url = params.get('scene') ?? '../../../cache/imperial_corridor/image_to_threejs/scene.json';
  const res = await fetch(url);
  if (!res.ok) throw new Error(`scene ${url}: ${res.status}`);
  return res.json();
}

async function landmarkIndex() {
  const res = await fetch('./landmarks/index.json');
  return res.ok ? res.json() : [];
}

const stats = {};
/** ENU footprint box of an object built in the (z-up) world group. */
function enuBox(obj) {
  obj.updateMatrixWorld(true);
  const b = new THREE.Box3().setFromObject(obj);
  // three (x, y, z) = ENU (x, z, -y)
  return { x0: b.min.x, x1: b.max.x, y0: -b.max.z, y1: -b.min.z };
}

/**
 * Landmarks without claimed footprints (bridges, arches, memorials): built once to
 * learn where they are; their boxes become ground cutouts so mapped ways over
 * water do not duplicate a modelled bridge deck.
 */
async function freeStanding(index, scene, assets) {
  const out = [];
  for (const l of index.filter((e) => !e.claims?.length)) {
    const object = buildLandmark(await loadLandmark(l.id), scene, assets);
    const probe = new THREE.Group();
    probe.rotation.x = -Math.PI / 2;
    probe.add(object);
    out.push({ id: l.id, object, box: enuBox(probe) });
    probe.remove(object);
  }
  return out;
}

async function main() {
  const scene = await loadScene();
  const index = await landmarkIndex();
  const assets = await loadAssets();
  const allClaims = new Set(index.flatMap((l) => l.claims ?? []));
  const free = await freeStanding(index, scene, assets);
  let bounds = null;
  if (params.get('gallery')) {
    // Asset library gallery: every resources/ asset in a row, vehicles and trees scaled.
    let x = 0;
    const gallery = new THREE.Group();
    for (const def of assets.values()) {
      const tall = def.kind === 'vegetation' ? 12 : 1;
      const o = assetObject(def);
      o.scale.setScalar(tall);
      o.position.x = x + (def.size[0] * tall) / 2;
      x += def.size[0] * tall + 2;
      gallery.add(o);
    }
    world.add(gallery);
    focus = { x: x / 2, y: 0, z: 2, size: x * 0.35 };
    bounds = { x0: -1e9, y0: -1e9, x1: -1e9 + 1, y1: -1e9 + 1 };
    stats.assets = [...assets.keys()];
  } else if (params.get('landmark')) {
    const id = params.get('landmark');
    const def = await loadLandmark(id);
    def.claims?.forEach((c) => allClaims.add(c));
    const obj = buildLandmark(def, scene, assets);
    world.add(obj);
    world.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(obj);
    const c = box.getCenter(new THREE.Vector3()),
      s = box.getSize(new THREE.Vector3());
    // Back to ENU: three (x, y, z) = ENU (x, z, -y)
    focus = { x: c.x, y: -c.z, z: s.y / 2, size: Math.max(s.x, s.z, s.y, 20) * 0.55 };
    const r = Number(params.get('context') ?? Math.max(120, focus.size * 2.5));
    bounds = { x0: focus.x - r, y0: focus.y - r, x1: focus.x + r, y1: focus.y + r };
    stats.landmark = { id, triangles: triangles(obj), size: [s.x, s.z, s.y] };
  } else {
    const x = Number(params.get('x') ?? 0),
      y = Number(params.get('y') ?? 0),
      r = Number(params.get('r') ?? 400);
    bounds = { x0: x - r, y0: y - r, x1: x + r, y1: y + r };
    focus = { x, y, z: 0, size: r * 0.55 };
    if (params.get('landmarks') !== '0') {
      for (const l of index) {
        const b = scene.buildings.find((q) => q.id === l.claims?.[0]);
        if (b && inside(b.c, bounds))
          world.add(buildLandmark(await loadLandmark(l.id), scene, assets));
      }
      for (const f of free)
        if (inside([(f.box.x0 + f.box.x1) / 2, (f.box.y0 + f.box.y1) / 2], bounds))
          world.add(f.object);
    }
  }
  if (params.get('context') !== '0') {
    world.add(buildGeneric(scene, { bounds, skip: allClaims }));
    world.add(buildGround(scene, { bounds, cutouts: free.map((f) => f.box) }));
    world.add(buildTrees(scene, { bounds, assets }));
    world.add(buildFurniture(scene, { bounds, assets }));
  }
  world.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  placeSun();
  view(params.get('view') ?? 'ne');
  say(`${params.get('landmark') ?? 'region'} · ${triangles(world).toLocaleString()} triangles`);
  stats.triangles = triangles(world);
}

function inside(p, b) {
  return p[0] >= b.x0 && p[0] < b.x1 && p[1] >= b.y0 && p[1] < b.y1;
}

function triangles(root) {
  let n = 0;
  root.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry;
    const t = (g.index ? g.index.count : g.attributes.position.count) / 3;
    n += o.isInstancedMesh ? t * o.count : t;
  });
  return n;
}

/**
 * Export layers for a region as GLB files PUT to /__out/<name>.glb.
 * spec: { bounds:{x0,y0,x1,y1}, layers:['buildings','ground','trees','landmarks'], prefix }
 */
async function exportLayers(spec) {
  const scene = await loadScene();
  const index = await landmarkIndex();
  const assets = await loadAssets();
  const claims = new Set(index.flatMap((l) => l.claims ?? []));
  const out = {};
  for (const layer of spec.layers) {
    const root = new THREE.Group();
    root.rotation.x = -Math.PI / 2; // ENU z-up -> glTF y-up
    root.name = `${spec.prefix ?? ''}${layer}`;
    if (layer === 'buildings') root.add(buildGeneric(scene, { bounds: spec.bounds, skip: claims }));
    if (layer === 'ground') {
      const cutouts = (await freeStanding(index, scene, assets)).map((f) => f.box);
      root.add(buildGround(scene, { bounds: spec.bounds, cutouts }));
    }
    if (layer === 'trees') root.add(buildTrees(scene, { bounds: spec.bounds, assets }));
    if (layer === 'street_furniture')
      root.add(buildFurniture(scene, { bounds: spec.bounds, assets }));
    if (layer === 'landmarks')
      for (const l of index) {
        try {
          root.add(buildLandmark(await loadLandmark(l.id), scene, assets));
        } catch (e) {
          out.errors = [...(out.errors ?? []), `${l.id}: ${e.message}`];
        }
      }
    root.traverse((o) => {
      if (o.isMesh && o.userData.flat) o.geometry.deleteAttribute('normal');
    });
    const bytes = await new GLTFExporter().parseAsync(root, { binary: true, maxTextureSize: 1024 });
    const name = `${root.name}.glb`;
    // Chunked upload keeps each request small for the driver's DevTools channel.
    const CHUNK = 8 << 20;
    for (let k = 0; k * CHUNK < bytes.byteLength || k === 0; k++) {
      const body = bytes.slice(k * CHUNK, (k + 1) * CHUNK);
      const res = await fetch(`/__out/${name}?part=${k}`, { method: 'PUT', body });
      if (!res.ok) throw new Error(`upload ${name}: ${res.status}`);
    }
    out[layer] = { file: name, bytes: bytes.byteLength, triangles: triangles(root) };
    root.traverse((o) => o.geometry?.dispose());
  }
  return out;
}

const ready = params.get('mode') === 'export' ? Promise.resolve() : main();
window.studio = { ready, view, stats, exportLayers };
ready.catch((e) => {
  say(`error: ${e.message}`);
  console.error(e);
});
addEventListener('resize', () => {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
});
controls.addEventListener('change', () => renderer.render(scene3, camera));
