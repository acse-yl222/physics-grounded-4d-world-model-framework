import * as THREE from 'three';
import { GLTFLoader } from '/vendor/GLTFLoader.js';
import { OrbitControls } from '/vendor/OrbitControls.js';
import { renderPanel } from '/js/panel.js';

const holder = document.getElementById('canvas-holder');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
holder.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8fb4d9);
const camera = new THREE.PerspectiveCamera(50, 1, 0.5, 4000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xdfeaf5, 0x5a5f52, 1.05));
const sun = new THREE.DirectionalLight(0xfff2dd, 2.2);
sun.position.set(150, 250, 100);
scene.add(sun);
const ground = new THREE.Mesh(
  new THREE.CircleGeometry(400, 48),
  new THREE.MeshLambertMaterial({ color: 0x9aa08f }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.08;
scene.add(ground);

function resize() {
  renderer.setSize(holder.clientWidth, holder.clientHeight);
  camera.aspect = holder.clientWidth / holder.clientHeight;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
resize();
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });

let current = null;   // current building root
let PID = null;

async function showGlb(url) {
  const gltf = await new GLTFLoader().loadAsync(url);
  if (current) scene.remove(current);
  current = gltf.scene;
  scene.add(current);
  const box = new THREE.Box3().setFromObject(current);
  const c = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(c);
  camera.position.set(c.x + size * 0.7, c.y + size * 0.55, c.z + size * 0.7);
  camera.updateProjectionMatrix();
}

function cardLabel(ty) {
  if (!ty || !(ty.cards || []).length) return t('upload.none_fits');
  return t('upload.card', { c: ty.cards.join(' + '), p: Math.round((ty.confidence || 0) * 100) });
}

function renderSide(info) {
  const side = document.getElementById('side');
  renderPanel(side, null, {
    osmid: 1,
    meta: { name: t('upload.name'), btype: cardLabel(info.typology) },
    spec: info.desc, refined: info.refined,
  }, 'agent', {
    rebuildUrl: `/api/photo/${PID}/rebuild`,
    onRebuilt: async (_osmid, glbUrl) => { await showGlb(glbUrl); },
  }).then(() => {
    // refine button under the panel
    const side2 = document.getElementById('side');
    const g = document.createElement('div');
    g.className = 'group';
    g.innerHTML = `<h4>${t('upload.refine_h')}</h4>
      <div class="sub">${t('upload.refine_desc')}</div>
      <button class="ghost" id="refine-btn">${t('upload.refine_btn')}</button>
      <div class="sub" id="refine-status"></div>`;
    side2.appendChild(g);
    document.getElementById('refine-btn').onclick = async () => {
      const btn = document.getElementById('refine-btn');
      btn.disabled = true;
      const st = document.getElementById('refine-status');
      st.innerHTML = `<span class="spin"></span> ${t('upload.starting')}`;
      const r = await fetch(`/api/photo/${PID}/refine`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      if (!r.ok) { st.textContent = t('upload.start_failed') + await r.text(); btn.disabled = false; return; }
      const { job } = await r.json();
      const timer = setInterval(async () => {
        const j = await (await fetch(`/api/jobs/${job}`)).json();
        st.innerHTML = `<span class="spin"></span> ${j.status}…<br><small>${(j.log_tail || '').split('\n').slice(-3).join('<br>')}</small>`;
        if (j.status === 'done') {
          clearInterval(timer);
          st.textContent = t('upload.refine_done');
          btn.disabled = false;
          const info2 = await (await fetch(`/api/photo/${PID}`)).json();
          await showGlb(`/api/photo/${PID}/file/${info2.glb}`);
          renderSide(info2);
        } else if (j.status === 'failed' || j.status === 'cancelled') {
          clearInterval(timer);
          st.textContent = j.status === 'failed' ? t('upload.refine_failed') + (j.error || '') : t('upload.refine_cancelled');
          btn.disabled = false;
        }
      }, 4000);
    };
  });
}

// ---- upload wiring
const drop = document.getElementById('drop');
const fi = document.getElementById('file-input');
drop.onclick = () => fi.click();
drop.ondragover = e => { e.preventDefault(); drop.classList.add('hover'); };
drop.ondragleave = () => drop.classList.remove('hover');
drop.ondrop = e => { e.preventDefault(); drop.classList.remove('hover'); if (e.dataTransfer.files[0]) doUpload(e.dataTransfer.files[0]); };
fi.onchange = () => fi.files[0] && doUpload(fi.files[0]);

async function doUpload(file) {
  const st = document.getElementById('up-status');
  st.innerHTML = `<span class="spin"></span> ${t('upload.uploading')}`;
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch('/api/photo', { method: 'POST', body: fd });
  if (!r.ok) { st.textContent = t('upload.failed') + await r.text(); return; }
  const info = await r.json();
  PID = info.id;
  document.getElementById('start-pane').style.display = 'none';
  document.getElementById('hud').style.display = '';
  await showGlb(`/api/photo/${PID}/file/${info.glb}`);
  renderSide(info);
}
