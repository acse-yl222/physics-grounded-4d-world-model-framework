import * as THREE from 'three';
import { GLTFLoader } from '/vendor/GLTFLoader.js';
import { OrbitControls } from '/vendor/OrbitControls.js';
import { renderPanel } from '/js/panel.js';

const params = new URLSearchParams(location.search);
const AREA = params.get('area');
document.getElementById('area-label').textContent = AREA || '';
fetch('/api/areas').then(r => r.json()).then(list => {
  const a = list.find(x => x.name === AREA);
  if (a && a.display) document.getElementById('area-label').textContent = `${a.display} (${AREA})`;
}).catch(() => {});

const holder = document.getElementById('canvas-holder');
const overlay = document.getElementById('loading-overlay');
const loadBar = document.getElementById('load-bar');

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
holder.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8fb4d9);
scene.fog = new THREE.Fog(0x8fb4d9, 900, 2600);

const camera = new THREE.PerspectiveCamera(50, 1, 0.5, 6000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI / 2 - 0.02;

scene.add(new THREE.HemisphereLight(0xdfeaf5, 0x5a5f52, 1.05));
const sun = new THREE.DirectionalLight(0xfff2dd, 2.2);
sun.position.set(300, 500, 200);
scene.add(sun);

function resize() {
  const w = holder.clientWidth, h = holder.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
resize();

// ---- building registry: osmid -> {kind, meshes[], root}
const buildings = new Map();
const RX = /^(Agent|Bldg)_(\d+)/;

function indexScene(root) {
  root.traverse(o => {
    const m = RX.exec(o.name);
    if (!m) return;
    const osmid = parseInt(m[2]);
    const kind = m[1] === 'Agent' ? 'agent' : 'lod1';
    let entry = buildings.get(osmid);
    if (!entry) { entry = { osmid, kind, meshes: [], roots: [] }; buildings.set(osmid, entry); }
    entry.roots.push(o);
    o.traverse(c => { if (c.isMesh) { entry.meshes.push(c); c.userData.osmid = osmid; } });
  });
}

// ---- selection / highlight
let selected = null;
const matCache = new Map();   // mesh.uuid -> original material

function setHighlight(entry, on) {
  for (const mesh of entry.meshes) {
    if (on) {
      if (!matCache.has(mesh.uuid)) matCache.set(mesh.uuid, mesh.material);
      const orig = matCache.get(mesh.uuid);
      const hl = Array.isArray(orig) ? orig.map(m => m.clone()) : orig.clone();
      for (const m of Array.isArray(hl) ? hl : [hl]) {
        if ('emissive' in m) { m.emissive = new THREE.Color(0x2f6fd0); m.emissiveIntensity = 0.55; }
      }
      mesh.material = hl;
    } else if (matCache.has(mesh.uuid)) {
      mesh.material = matCache.get(mesh.uuid);
      matCache.delete(mesh.uuid);
    }
  }
}

export async function selectBuilding(osmid) {
  const entry = buildings.get(osmid);
  if (selected) setHighlight(selected, false);
  selected = entry || null;
  const side = document.getElementById('side');
  if (!entry) {
    side.innerHTML = `<div class="placeholder">${t('viewer.placeholder')}</div>`;
    return;
  }
  setHighlight(entry, true);
  side.innerHTML = `<div class="placeholder"><span class="spin"></span> ${t('viewer.reading')}</div>`;
  try {
    const info = await (await fetch(`/api/areas/${AREA}/buildings/${osmid}`)).json();
    renderPanel(side, AREA, info, entry.kind, {
      onRebuilt: swapBuilding, live: livePreview,
      draft: drafts.get(osmid) || null,
      setDraft: (spec, unsaved) => {
        if (spec) drafts.set(osmid, { spec, unsaved });
        else drafts.delete(osmid);
      },
    });
  } catch (e) {
    side.innerHTML = `<div class="placeholder">${t('viewer.read_failed')}${e}</div>`;
  }
}

// ---- LIVE preview: instant client-side morphs while dragging (no rebuild).
// heightRatio scales the building about its own base; tint recolours matching
// wall/roof materials in place. The exact geometry lands on commit (rebuild).
const _liveState = new Map();   // osmid -> {ratio, baseMinY}
const drafts = new Map();       // osmid -> {spec, unsaved} — applied-but-unsaved edits survive reselect
function livePreview(osmid, kind, value) {
  const entry = buildings.get(osmid);
  if (!entry) return;
  if (kind === 'heightRatio') {
    let st = _liveState.get(osmid);
    if (!st) {
      const box = new THREE.Box3();
      for (const r of entry.roots) box.expandByObject(r);
      st = { ratio: 1, baseMinY: box.min.y };
      _liveState.set(osmid, st);
    }
    const f = value / st.ratio;
    st.ratio = value;
    for (const r of entry.roots) {
      r.scale.y *= f;
      r.updateMatrixWorld(true);
    }
    const box = new THREE.Box3();
    for (const r of entry.roots) box.expandByObject(r);
    const dy = st.baseMinY - box.min.y;
    for (const r of entry.roots) { r.position.y += dy; r.updateMatrixWorld(true); }
  } else if (kind === 'tint') {
    const { channel, rgb } = value;
    const PREFIX = { wall: ['brick', 'stucco', 'stone', 'white', 'slab'],
                     stucco: ['stucco'], roof: ['slate', 'roof'],
                     frame: ['white', 'mullion'] }[channel] || [];
    const col = new THREE.Color().setRGB(rgb[0], rgb[1], rgb[2]);   // linear
    for (const mesh of entry.meshes) {
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of mats) {
        const base = (m.name || '').split('.')[0].split('_')[0];
        if (PREFIX.includes(base) && m.color) m.color.copy(col);
      }
    }
  }
}

// ---- hot swap after a rebuild (M2): replace this building's meshes with a mini-glb
async function swapBuilding(osmid, glbUrl) {
  const entry = buildings.get(osmid);
  if (!entry) return;
  const gltf = await new GLTFLoader().loadAsync(glbUrl);
  for (const r of entry.roots) r.parent && r.parent.remove(r);
  for (const mesh of entry.meshes) matCache.delete(mesh.uuid);
  buildings.delete(osmid);
  scene.add(gltf.scene);
  indexScene(gltf.scene);
  _liveState.delete(osmid);
  const fresh = buildings.get(osmid);
  if (fresh) { selected = fresh; setHighlight(fresh, true); }
}

// ---- picking
const ray = new THREE.Raycaster();
const ptr = new THREE.Vector2();
let downAt = null;
renderer.domElement.addEventListener('pointerdown', e => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!downAt) return;
  const dx = e.clientX - downAt[0], dy = e.clientY - downAt[1];
  downAt = null;
  if (dx * dx + dy * dy > 25) return;          // it was a drag
  const rect = renderer.domElement.getBoundingClientRect();
  ptr.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  ptr.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  ray.setFromCamera(ptr, camera);
  const meshes = [];
  for (const b of buildings.values()) meshes.push(...b.meshes);
  const hit = ray.intersectObjects(meshes, false)[0];
  selectBuilding(hit ? hit.object.userData.osmid : null);
});

// ---- load
async function main() {
  if (!AREA) { overlay.textContent = t('viewer.missing_area'); return; }
  const r = await fetch(`/api/areas/${AREA}/map.json`);
  if (!r.ok) {
    overlay.innerHTML = `<div>${t('viewer.exporting')}</div><div class="bar"><div id="load-bar2" style="width:30%"></div></div>`;
    const rr = await fetch(`/api/areas/${AREA}/export`, { method: 'POST' });
    if (!rr.ok) { overlay.textContent = t('viewer.export_failed') + await rr.text(); return; }
  }
  const loader = new GLTFLoader();
  const gltf = await loader.loadAsync(`/api/areas/${AREA}/scene.glb`, ev => {
    if (ev.total) loadBar.style.width = (100 * ev.loaded / ev.total).toFixed(0) + '%';
  });
  scene.add(gltf.scene);
  indexScene(gltf.scene);
  // traffic: the glb carries one clip per animated vehicle (export_glb
  // --animations); play them all, looping, so the partner's predicted tracks
  // drive in the browser exactly as in the .blend
  if (gltf.animations && gltf.animations.length) {
    mixer = new THREE.AnimationMixer(gltf.scene);
    for (const clip of gltf.animations) mixer.clipAction(clip).play();
    window.__traffic = { clips: gltf.animations.length, mixer };   // debug hook
  }

  // frame the whole block
  const box = new THREE.Box3().setFromObject(gltf.scene);
  const c = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(c);
  camera.position.set(c.x + size * 0.28, c.y + size * 0.30, c.z + size * 0.28);
  camera.near = size / 1000; camera.far = size * 6;
  camera.updateProjectionMatrix();
  overlay.remove();

  // deep link: ?osmid=<id> selects that building and frames the camera on
  // its front (-y side), so a demo can open straight onto one building
  const want = parseInt(params.get('osmid') || '', 10);
  if (want && buildings.has(want)) {
    const entry = buildings.get(want);
    const bb = new THREE.Box3();
    for (const m of entry.meshes) bb.expandByObject(m);
    const bc = bb.getCenter(new THREE.Vector3());
    const bs = bb.getSize(new THREE.Vector3()).length();
    controls.target.copy(bc);
    // high three-quarter view from far enough that neighbours do not occlude
    camera.position.set(bc.x + bs * 1.3, bc.y + bs * 1.1, bc.z + bs * 1.3);
    camera.updateProjectionMatrix();
    selectBuilding(want);
  }
}

let mixer = null;
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  if (mixer) mixer.update(clock.getDelta());
  controls.update(); renderer.render(scene, camera);
});
main().catch(e => { overlay.textContent = t('viewer.load_failed') + e; console.error(e); });
