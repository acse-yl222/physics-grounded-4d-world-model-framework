import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createNeuralWind } from './wind.js';
const $ = (id) => document.getElementById(id),
  status = $('status');
const renderer = new THREE.WebGLRenderer({ canvas: $('view'), antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color('#101b27');
const camera = new THREE.PerspectiveCamera(45, 1, 1, 25000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxDistance = 13000;
function cameraAt(position, target) {
  camera.position.set(...position);
  controls.target.set(...target);
  controls.update();
}
const overview = () => cameraAt([3200, 2600, 3900], [0, 170, 0]);
overview();
const material = new THREE.ShaderMaterial({
  side: THREE.DoubleSide,
  uniforms: { edges: { value: 1 } },
  vertexShader: `attribute float kind; attribute float light; varying vec2 faceUV; varying float type; varying float shade; varying float height;
 void main(){faceUV=uv;type=kind;shade=light;height=position.y;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader: `uniform float edges; varying vec2 faceUV; varying float type; varying float shade; varying float height;
 void main(){vec3 base=mix(vec3(.19,.48,.48),vec3(.42,.72,.59),clamp(height/350.,0.,1.));base=mix(base,vec3(.97,.65,.28),type);
 vec2 width=max(fwidth(faceUV),vec2(.00001));vec2 distanceToEdge=min(faceUV,1.-faceUV)/width;
 float line=1.-smoothstep(.35,1.1,min(distanceToEdge.x,distanceToEdge.y));
 float fade=1.-smoothstep(.22,.55,max(width.x,width.y));
 gl_FragColor=vec4(mix(base*shade,vec3(.07,.15,.19),line*edges*fade*.8),1.);}`,
});
let mesh,
  worker,
  timer,
  revision = 0,
  busy = false,
  pending = null;
function options() {
  return { xcut: +$('x-cut').value, zcut: +$('z-cut').value, padding: $('padding').checked };
}
const wind = createNeuralWind(scene, options);
function rebuild() {
  $('x-value').textContent = Math.round((+$('x-cut').value / 768) * 100) + '%';
  $('z-value').textContent = +$('z-cut').value * 8 + ' m';
  pending = { id: ++revision, options: options() };
  status.textContent = 'Extracting the sliced voxel surface…';
  dispatch();
  wind.refresh();
}
function dispatch() {
  if (busy || !pending || !worker) return;
  busy = true;
  worker.postMessage(pending);
  pending = null;
}
for (const id of ['x-cut', 'z-cut', 'padding'])
  $(id).addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(rebuild, 100);
  });
$('edges').onchange = () => (material.uniforms.edges.value = $('edges').checked ? 1 : 0);
$('overview').onclick = overview;
$('closeup').onclick = () => cameraAt([-420, 340, -140], [-518, 205, -335]);
$('section').onclick = () => {
  $('x-cut').value = 384;
  cameraAt([1300, 900, 1900], [-350, 180, 0]);
  rebuild();
};
function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
resize();
renderer.setAnimationLoop((now) => {
  wind.update(now);
  controls.update();
  renderer.render(scene, camera);
});
try {
  const base = '../../scenes/region/voxels/';
  const fetchOK = async (name) => {
    const r = await fetch(base + name);
    if (!r.ok) throw Error(`${name}: HTTP ${r.status}`);
    return r;
  };
  const [meta, bits, study, terrain] = await Promise.all([
    (await fetchOK('metadata.json')).json(),
    (await fetchOK('solid.bits')).arrayBuffer(),
    (await fetchOK('study.bits')).arrayBuffer(),
    (await fetchOK('terrain.f32')).arrayBuffer(),
  ]);
  const [nz, ny, nx] = meta.shape_zyx,
    [ox, oy] = meta.source_region_origin_xyz_m;
  if (
    bits.byteLength !== Math.ceil((nx * ny * nz) / 8) ||
    terrain.byteLength !== nx * ny * 4 ||
    study.byteLength !== Math.ceil((nx * ny) / 8)
  )
    throw Error('Grid data dimensions do not match');
  worker = new Worker('./worker.js', { type: 'module' });
  worker.onerror = (e) => {
    status.textContent = 'Grid generation failed: ' + e.message;
  };
  worker.onmessage = ({ data: r }) => {
    busy = false;
    if (r.error) {
      status.textContent = r.error;
      dispatch();
      return;
    }
    if (r.id === revision) {
      const geometry = new THREE.BufferGeometry();
      for (const [name, size] of [
        ['position', 3],
        ['uv', 2],
        ['kind', 1],
        ['light', 1],
      ])
        geometry.setAttribute(name, new THREE.BufferAttribute(r[name], size));
      geometry.setIndex(new THREE.BufferAttribute(r.index, 1));
      geometry.computeBoundingSphere();
      if (mesh) {
        scene.remove(mesh);
        mesh.geometry.dispose();
      }
      mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);
      status.textContent = `Current extent: ${r.occupied.toLocaleString()} solid cells · ${r.faces.toLocaleString()} exposed cell faces`;
    }
    dispatch();
  };
  busy = true;
  worker.postMessage(
    {
      id: revision,
      data: {
        bits: new Uint8Array(bits),
        study: new Uint8Array(study),
        terrain: new Float32Array(terrain),
        nx,
        ny,
        nz,
        cell: 8,
        ox,
        oy,
      },
      options: options(),
    },
    [bits, study, terrain],
  );
} catch (error) {
  status.textContent = 'Loading failed: ' + error.message;
  console.error(error);
}
