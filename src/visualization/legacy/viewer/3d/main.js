import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { loadScene, sceneLink, ROOT } from '../scene.js';
import { getFrame, f16, loadMask, npy, DATA, setDataBase } from '../npy.js';
import { initFrames, hasLayer, layerMeta, getFrameF32, framesInfo } from '../frames.js';
import { ON_PAGES } from '../config.js';
import { fetchCityModel } from '../model-source.js';
import { buildProxyCity } from './proxy.js';
import { batchStaticCity } from '../../agents/demo_rev02/static-batches.js';
import { createReplay, applyCityFilter, timeString } from './replay.js';
import { TILE, placeTile, tileClipPlanes, setClipping, tileBuildingCentre, tileBuildingIds, hideReplaced, materialsOf } from './tile.js';
import { EXPANSION_BATCHES, installExpansion } from './expansion.js';
import { createTransport } from './transport.js';
import { createTraffic } from './traffic.js';

// ------------------------------------------------------------------ scene (scenes/<id>/scene.json)
// Everything site-specific comes from the scene file: the field grid and its placement in the model frame, the city model,
// the masks, the field layers (files, frame counts, clocks, display ranges) and the camera focus. South Kensington also
// switches on the traffic / UAV / bird replay, the station tile, the OSM supplement and the building refinements.
const SCENE = await loadScene();
setDataBase(SCENE.physics);
document.title = `${SCENE.title} · 3D`;
// Lite mode: phones, tablets and low-memory machines get a proxy city extruded from the voxel masks instead of the
// full model (which needs 1.5-2 GB of browser memory). ?lite=1 forces it, ?lite=0 forces the full model.
const qs0 = new URLSearchParams(location.search);
const LITE = qs0.get('lite') === '1' || (qs0.get('lite') !== '0' && (/iPhone|iPad|Android|Mobile/i.test(navigator.userAgent)
  || (navigator.maxTouchPoints > 1 && /Mac/.test(navigator.platform)) || (navigator.deviceMemory !== undefined && navigator.deviceMemory <= 4)));

// ------------------------------------------------------------------ grid <-> model alignment
// Field arrays: `cell_m` cells, `cols` columns (west->east) x `rows` rows (south->north). Model (glTF, Y up): column c
// starts at X = x0 + c*cell, row r (0 = south) spans Z from z_south - r*cell down to z_south - (r+1)*cell.
const G = SCENE.grid;
const W = G.cols, H = G.rows, CELL = G.cell_m;
const X0 = G.x0, ZS = G.z_south;
const SPAN_X = W * CELL, SPAN_Z = H * CELL;
const CX = X0 + SPAN_X / 2, CZ = ZS - SPAN_Z / 2;   // plane centre
const LAYERS = SCENE.layers, has = k => !!LAYERS[k];
const gridOf = cell => ({ w: Math.round(SPAN_X / cell), h: Math.round(SPAN_Z / cell), cell });
const LG = {};   // the grid of every layer (layers may be coarser or finer than the base grid)
for (const k of Object.keys(LAYERS)) LG[k] = gridOf(LAYERS[k].cell_m ?? CELL);
if (has('solar')) LG.shadow = gridOf(LAYERS.solar.shadow_cell_m ?? LAYERS.solar.cell_m ?? CELL);
const TL = SCENE.timeline ?? { step_s: 25, steps: 100 }, STEP_S = TL.step_s, STEPS = TL.steps;
const FOCUS = SCENE.focus;                          // {box: [[x, z], [x, z]], orbit_m, label}
const HAS_REPLAY = SCENE.replay === 'demo_rev02';   // the South Kensington traffic / UAV / bird replay
const MODEL = SCENE.model;
const PHASE_ORDER = (SCENE.phase_order ?? ['wind', 'temp', 'solar', 'diurnal', 'poll', 'flood']).filter(has);
const TAB_NAME = { wind: 'Wind', temp: 'Temperature', solar: 'Sunlight', diurnal: 'Day cycle', poll: 'Pollution', flood: 'Flooding' };
const TREE_NODE = /simplified canopy|simplified trunk|inherited tre|\btrees?\b|canopy|crown|hedge|planting|planter/i;
const TREE_MAT = /broadleaf|crown|tree bark|hedge|foliage|grass|substrate|shrub|lawn|leaves|planting/i;
const FILES = {
  wind: LAYERS.wind?.file, poll: LAYERS.poll?.file, temp: LAYERS.temp?.file,
  flood: LAYERS.flood?.file, floodMax: LAYERS.flood?.max,   // flood: own clock; the static maximum map is shown in overlay mode
  solar: {}, shadow: {},                                     // by date: irradiance frames and the fine shadow mask
  diurnal: LAYERS.diurnal?.files ?? {},                      // by display mode (ground / air0 / air12)
};
if (has('solar')) for (const [d, v] of Object.entries(LAYERS.solar.dates)) { FILES.solar[d] = v.ghi; FILES.shadow[d] = v.shadow; }
const LAYER_Y = { wind: LAYERS.wind?.y ?? 10, temp: LAYERS.temp?.y ?? 0.6, iso: LAYERS.temp?.iso_y ?? 12, poll: LAYERS.poll?.y ?? 14, particles: (LAYERS.wind?.y ?? 10) + 1,
  flood: LAYERS.flood?.y ?? 0.8, solar: 0.7, shadow: 0.75, diurnal: LAYERS.diurnal?.y ?? 0.6 };
const DIURNAL_RANGE = { ground: [8, 38], groundRel: [-12, 12], air0: [12, 30], air0Rel: [-3, 3], air12: [12, 30] };   // °C per display mode; *Rel = minus the hour's ambient air temperature
const ISO = LAYERS.temp?.iso ?? { from: 31.0, step: 0.1, n: 11 };
const ISO_LEVELS = Array.from({ length: ISO.n }, (_, i) => +(ISO.from + ISO.step * i).toFixed(3));
const ISO_COLORS = ['#ffffb2', '#fed976', '#feb24c', '#fd8d3c', '#f03b20', '#bd0026'];
const TEMP_RANGE = LAYERS.temp?.range ?? [31.2, 32.2];
const WIND_RANGE = LAYERS.wind?.range ?? [0, 1.6];
const FLOOD_RANGE = LAYERS.flood?.range ?? [0.02, 0.6];   // m of water; below the low end counts as dry, the high end saturates

// ------------------------------------------------------------------ DOM
const $ = id => document.getElementById(id);
const ui = {
  stage: $('stage'), loading: $('loading'), bar: $('bar'), pct: $('pct'), readout: $('readout'),
  lWind: $('l-wind'), lTemp: $('l-temp'), lPoll: $('l-poll'), lFlood: $('l-flood'), oFlood: $('o-flood'), lModel: $('l-model'), lGround: $('l-ground'), lTrees: $('l-trees'), lPart: $('l-part'),
  tempMode: $('temp-mode'), mode: $('mode'),
  lSolar: $('l-solar'), oSolar: $('o-solar'), solarDate: $('solar-date'), solarMode: $('solar-mode'), solarOpen: $('solar-open'),
  lDiurnal: $('l-diurnal'), oDiurnal: $('o-diurnal'), diurnalMode: $('diurnal-mode'), diurnalLo: $('diurnal-lo'), diurnalHi: $('diurnal-hi'), diurnalUnit: $('diurnal-unit'),
  oWind: $('o-wind'), oTemp: $('o-temp'), oPoll: $('o-poll'), nPart: $('n-part'),
  play: $('play'), step: $('step'), timeLabel: $('time-label'), rate: $('rate'), replay: $('replay'),
  info: $('info'), stats: $('stats'), auto: $('auto'),
  lCars: $('l-cars'), lUavs: $('l-uavs'), lSignals: $('l-signals'), lStations: $('l-stations'), lRoads: $('l-roads'), lMap: $('l-map'),
  lTile: $('l-tile'), lBirds: $('l-birds'),
};
// scene-driven page chrome: title, scene switcher, tabs, layer rows and legends
function setupSceneUI() {
  $('title').textContent = SCENE.title; $('title').title = SCENE.description ?? '';
  $('loading-title').textContent = `Loading the ${SCENE.title} 3D model`;
  const sel = $('scene-select');
  sel.replaceChildren(...SCENE.index.scenes.map(s => { const o = document.createElement('option'); o.value = s.id; o.textContent = s.short ?? s.title; return o; }));
  sel.value = SCENE.id; sel.addEventListener('change', () => { location.href = sceneLink(sel.value); });
  const tabs = $('tabs'), auto = $('auto').closest('label'), mk = (cls, data, key, text) => { const b = document.createElement('button'); b.className = 'tab ' + cls; b.dataset[data] = key; b.textContent = text; return b; };
  const shots = HAS_REPLAY ? [['overview', 'Campus'], ['junction', 'Junction'], ['traffic', 'Traffic'], ['uavs', 'UAVs'], ['birds', 'Birds']] : [['overview', 'Overview'], ...(SCENE.traffic ? [['trafficMap', 'Traffic map']] : [])];   // the close-up traffic and transport orbits stay reachable by ?shot=traffic|transport
  tabs.replaceChildren(...shots.map(([k, t]) => mk('shot', 'shot', k, t)), ...PHASE_ORDER.map(k => mk('field', 'field', k, TAB_NAME[k] ?? k)), auto);
  for (const el of document.querySelectorAll('[data-layer]')) el.style.display = has(el.dataset.layer) ? '' : 'none';
  const legend = (k, L) => { if (!L.legend) return; $(`lg-${k}-lo`).textContent = L.legend[0]; $(`lg-${k}-unit`).textContent = L.legend[1]; $(`lg-${k}-hi`).textContent = L.legend[2]; };
  for (const k of ['wind', 'temp', 'poll', 'flood', 'solar', 'diurnal']) if (has(k)) { $(`lbl-${k}`).textContent = LAYERS[k].label; if (k !== 'solar' && k !== 'diurnal') legend(k, LAYERS[k]); }
  if (has('temp')) $('temp-iso-option').textContent = LAYERS.temp.iso_label ?? `Isotherms (every ${ISO.step} °C)`;
  if (has('solar')) {
    ui.solarDate.replaceChildren(...Object.entries(LAYERS.solar.dates).map(([d, v]) => { const o = document.createElement('option'); o.value = d; o.textContent = v.label; return o; }));
    $('solar-ghi-option').textContent = LAYERS.solar.ghi_label ?? 'Irradiance'; $('solar-shadow-option').textContent = LAYERS.solar.shadow_label ?? 'Shadows';
  }
  $('replay-ctl').style.display = HAS_REPLAY ? '' : 'none';
  if (SCENE.traffic) $('traffic-title').textContent = SCENE.traffic.label ?? 'Traffic';
  if (SCENE.transport) { $('transport-title').textContent = SCENE.transport.label ?? 'Transport'; $('transport-attribution').textContent = SCENE.transport.attribution ?? ''; }
  $('attribution-hint').style.display = MODEL.expansion ? '' : 'none';
  if (MODEL.supplement) { $('supplement-ctl').style.display = ''; $('supplement-label').textContent = MODEL.supplement.label; $('supplement-ctl').title = MODEL.supplement.title ?? ''; }
  $('lite-link').href = sceneLink(SCENE.id) + '&lite=0';
  if (SCENE.limits?.length) { $('limits').replaceChildren(...SCENE.limits.map(t => { const d = document.createElement('div'); d.textContent = '· ' + t; return d; })); }
}
setupSceneUI();
const shotButtons = [...document.querySelectorAll('.shot[data-shot]')];
const fieldButtons = [...document.querySelectorAll('.field[data-field]')];
let section = 'campus';   // 'campus' (the site tour: replay shots, or the plain orbit) | 'fields' (overhead physics fields) | 'free'
let replayLayer = null;   // created after the city loads (South Kensington only)
let transport = null;     // TfL transport layer (transport.js), scenes with scene.transport
let traffic = null;       // SUMO traffic replay (traffic.js), scenes with scene.traffic

// ------------------------------------------------------------------ colour maps
function hex(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
function lut(stops) {
  const st = stops.map(hex), out = new Uint8Array(256 * 3);
  for (let i = 0; i < 256; i++) {
    const x = i / 255 * (st.length - 1), j = Math.min(st.length - 2, Math.floor(x)), f = x - j;
    for (let k = 0; k < 3; k++) out[i * 3 + k] = Math.round(st[j][k] * (1 - f) + st[j + 1][k] * f);
  }
  return out;
}
const TEMP_LUT = lut(['#ffffb2', '#fed976', '#feb24c', '#fd8d3c', '#f03b20', '#bd0026']);
const BLUES = lut(['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b']);
const FLOOD_LUT = lut(['#9fd8f2', '#4fb3e6', '#1e88d0', '#0d5fb0', '#083b85', '#041f52']);
const DIURNAL_LUT = lut(['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']);
const PURPLES = lut(['#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d', '#2c0060']);

// ------------------------------------------------------------------ renderer / scene
const renderer = new THREE.WebGLRenderer({ canvas: $('gl'), antialias: true, powerPreference: 'high-performance', logarithmicDepthBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.localClippingEnabled = true;   // the detail tile cuts a hole into the main model
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a2029);
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 5, 30000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI / 2 - 0.02;
controls.enabled = false;

scene.add(new THREE.HemisphereLight(0xdfe8f5, 0x3b3f46, 1.1));
const sun = new THREE.DirectionalLight(0xfff2e0, 2.2);
sun.position.set(-1200, 2200, 1500);
scene.add(sun);
scene.add(new THREE.AmbientLight(0xffffff, 0.25));

// dark base plate under the model so the field planes have a ground even outside the site mesh
const base = new THREE.Mesh(new THREE.PlaneGeometry(SPAN_X + 400, SPAN_Z + 400), new THREE.MeshStandardMaterial({ color: MODEL.plate_color ? new THREE.Color(MODEL.plate_color) : 0x2b2f35, roughness: 1 }));
base.rotation.x = -Math.PI / 2; base.position.set(CX, -0.5, CZ);
scene.add(base);

const model = new THREE.Group();
scene.add(model);

// ------------------------------------------------------------------ field planes (textures), one per layer on its own grid
const planes = {};
function makePlane(key, g, y, opacity, renderOrder, magFilter = THREE.LinearFilter) {
  const data = new Uint8Array(g.w * g.h * 4);
  const tex = new THREE.DataTexture(data, g.w, g.h, THREE.RGBAFormat);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearFilter; tex.magFilter = magFilter; tex.generateMipmaps = false;
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(SPAN_X, SPAN_Z), mat);
  mesh.rotation.x = -Math.PI / 2; mesh.position.set(CX, y, CZ); mesh.renderOrder = renderOrder;
  mesh.visible = false;
  scene.add(mesh);
  return (planes[key] = { mesh, tex, data, mat, fade: 0, target: 0, g });
}
const tempPlane = has('temp') ? makePlane('temp', LG.temp, LAYER_Y.temp, +ui.oTemp.value, 1) : null;
const windPlane = has('wind') ? makePlane('wind', LG.wind, LAYER_Y.wind, +ui.oWind.value, 2) : null;
const pollPlane = has('poll') ? makePlane('poll', LG.poll, LAYER_Y.poll, +ui.oPoll.value, 3) : null;
const floodPlane = has('flood') ? makePlane('flood', LG.flood, LAYER_Y.flood, +ui.oFlood.value, 1) : null;
const solarPlane = has('solar') ? makePlane('solar', LG.solar, LAYER_Y.solar, +ui.oSolar.value, 1) : null;
const diurnalPlane = has('diurnal') ? makePlane('diurnal', LG.diurnal, LAYER_Y.diurnal, +ui.oDiurnal.value, 1) : null;
// fine shadow mask: the uint8 frame (1 = shaded) is expanded into an RGBA texture of the full fine grid: a dark veil where
// shaded, a faint warm tint where sunlit, so the model's own streets show through. (A single-channel R8 texture sampled from a
// ShaderMaterial rendered nothing under the logarithmic depth buffer, so the plain textured plane is used, as for the other layers.)
const shadowPlane = has('solar') ? makePlane('shadow', LG.shadow, LAYER_Y.shadow, +ui.oSolar.value, 1, THREE.NearestFilter) : null;
const fadeOf = p => p ? p.fade : 0;
function uploadShadow(u8) {
  const d = shadowPlane.data, n = LG.shadow.w * LG.shadow.h;
  for (let i = 0, o = 0; i < n; i++, o += 4) {
    if (u8[i]) { d[o] = 18; d[o + 1] = 28; d[o + 2] = 96; d[o + 3] = 158; } else { d[o] = 255; d[o + 1] = 234; d[o + 2] = 150; d[o + 3] = 80; }   // shade: blue-violet veil; sun: warm wash
  }
  shadowPlane.tex.needsUpdate = true;
}
/** packed shadow rows (uint8 [rows, cols/8], numpy packbits axis 1) -> Uint8Array 0/1 of the fine grid */
function unpackBits(packed, g) {
  const out = new Uint8Array(g.w * g.h), bpr = g.w >> 3;
  for (let r = 0; r < g.h; r++) for (let b = 0; b < bpr; b++) { const v = packed[r * bpr + b], o = r * g.w + b * 8; for (let k = 0; k < 8; k++) out[o + k] = (v >> (7 - k)) & 1; }
  return out;
}

const footprints = {};   // building footprint masks by cell size (metres): each layer is masked at its own resolution
const fpFor = g => footprints[g.cell] ?? null;
let solidWind = null, studyArea = null;
function paintWind(uv) {
  const g = LG.wind, d = windPlane.data, n = g.w * g.h, inv = 255 / (WIND_RANGE[1] - WIND_RANGE[0]);
  for (let i = 0; i < n; i++) {
    const o = i * 4;
    if (solidWind && solidWind[i]) { d[o + 3] = 0; continue; }
    const u = uv[i], v = uv[n + i], w = uv[2 * n + i];
    let k = (Math.sqrt(u * u + v * v + w * w) - WIND_RANGE[0]) * inv; k = k < 0 ? 0 : k > 255 ? 255 : k | 0;
    d[o] = BLUES[k * 3]; d[o + 1] = BLUES[k * 3 + 1]; d[o + 2] = BLUES[k * 3 + 2]; d[o + 3] = 235;
  }
  windPlane.tex.needsUpdate = true;
}
// ------------------------------------------------------------------ isotherms (marching squares on a 2x-averaged grid)
const ISO_STRIDE = 2, TG = LG.temp ?? gridOf(CELL), NX = TG.w / ISO_STRIDE, NY = TG.h / ISO_STRIDE;
const isoGrid = new Float32Array(NX * NY);
const ISO_MAX_SEG = 600000;
const iso = { pos: new Float32Array(ISO_MAX_SEG * 6), col: new Float32Array(ISO_MAX_SEG * 6), geom: null, lines: null, count: 0 };
iso.material = new LineMaterial({ vertexColors: true, linewidth: 2, transparent: true, opacity: +ui.oTemp.value, depthWrite: false, worldUnits: false });
iso.material.resolution.set(window.innerWidth, window.innerHeight);
const ISO_LUT = lut(ISO_COLORS);
const ISO_RGB = ISO_LEVELS.map((_, L) => { const k = Math.round(L / (ISO_LEVELS.length - 1) * 255); return [ISO_LUT[k * 3] / 255, ISO_LUT[k * 3 + 1] / 255, ISO_LUT[k * 3 + 2] / 255]; });
function uploadIsotherms(n) {
  if (iso.lines) { scene.remove(iso.lines); iso.geom.dispose(); iso.lines = null; }
  if (!n) return;
  iso.geom = new LineSegmentsGeometry();
  iso.geom.setPositions(iso.pos.subarray(0, n * 6));
  iso.geom.setColors(iso.col.subarray(0, n * 6));
  iso.lines = new LineSegments2(iso.geom, iso.material);
  iso.lines.renderOrder = 3; iso.lines.frustumCulled = false;
  iso.lines.visible = fadeOf(tempPlane) > 0 && ui.tempMode.value === 'iso';
  scene.add(iso.lines);
}
function paintIsotherms(vals) {
  // average 2x2 blocks; blocks touching a building become NaN so contours stop at walls
  const w = TG.w, footprint = fpFor(TG);
  for (let j = 0; j < NY; j++) for (let i = 0; i < NX; i++) {
    const r0 = j * ISO_STRIDE, c0 = i * ISO_STRIDE;
    const a = r0 * w + c0, b = a + 1, c = a + w, d = c + 1;
    const blocked = (footprint && (footprint[a] || footprint[b] || footprint[c] || footprint[d])) || (studyArea && !(studyArea[a] && studyArea[b] && studyArea[c] && studyArea[d]));
    isoGrid[j * NX + i] = blocked ? NaN : (vals[a] + vals[b] + vals[c] + vals[d]) * 0.25;
  }
  const pos = iso.pos, col = iso.col;
  const y = LAYER_Y.iso, sx = ISO_STRIDE * TG.cell;
  let n = 0;
  const px = (i, j) => [X0 + (i * ISO_STRIDE + ISO_STRIDE / 2) * TG.cell, ZS - (j * ISO_STRIDE + ISO_STRIDE / 2) * TG.cell];
  const put = (x1, z1, x2, z2, rgb) => {
    if (n >= ISO_MAX_SEG) return;
    const o = n * 6;
    pos[o] = x1; pos[o + 1] = y; pos[o + 2] = z1; pos[o + 3] = x2; pos[o + 4] = y; pos[o + 5] = z2;
    col[o] = rgb[0]; col[o + 1] = rgb[1]; col[o + 2] = rgb[2]; col[o + 3] = rgb[0]; col[o + 4] = rgb[1]; col[o + 5] = rgb[2];
    n++;
  };
  for (let j = 0; j < NY - 1; j++) for (let i = 0; i < NX - 1; i++) {
    const v0 = isoGrid[j * NX + i], v1 = isoGrid[j * NX + i + 1], v2 = isoGrid[(j + 1) * NX + i + 1], v3 = isoGrid[(j + 1) * NX + i];
    if (v0 !== v0 || v1 !== v1 || v2 !== v2 || v3 !== v3) continue;
    const lo = Math.min(v0, v1, v2, v3), hi = Math.max(v0, v1, v2, v3);
    const [x0, z0] = px(i, j);
    for (let L = 0; L < ISO_LEVELS.length; L++) {
      const lv = ISO_LEVELS[L];
      if (lv < lo || lv >= hi) continue;
      const idx = (v0 >= lv ? 1 : 0) | (v1 >= lv ? 2 : 0) | (v2 >= lv ? 4 : 0) | (v3 >= lv ? 8 : 0);
      if (idx === 0 || idx === 15) continue;
      // edge points: e0 top (v0-v1, +x), e1 right (v1-v2, -z), e2 bottom (v3-v2), e3 left (v0-v3)
      const t01 = (lv - v0) / (v1 - v0), t12 = (lv - v1) / (v2 - v1), t32 = (lv - v3) / (v2 - v3), t03 = (lv - v0) / (v3 - v0);
      const e0 = [x0 + t01 * sx, z0], e1 = [x0 + sx, z0 - t12 * sx], e2 = [x0 + t32 * sx, z0 - sx], e3 = [x0, z0 - t03 * sx];
      const rgb = ISO_RGB[L];
      switch (idx) {
        case 1: case 14: put(e3[0], e3[1], e0[0], e0[1], rgb); break;
        case 2: case 13: put(e0[0], e0[1], e1[0], e1[1], rgb); break;
        case 3: case 12: put(e3[0], e3[1], e1[0], e1[1], rgb); break;
        case 4: case 11: put(e1[0], e1[1], e2[0], e2[1], rgb); break;
        case 5: case 10: put(e3[0], e3[1], e0[0], e0[1], rgb); put(e1[0], e1[1], e2[0], e2[1], rgb); break;
        case 6: case 9: put(e0[0], e0[1], e2[0], e2[1], rgb); break;
        case 7: case 8: put(e3[0], e3[1], e2[0], e2[1], rgb); break;
      }
    }
  }
  iso.count = n;
  uploadIsotherms(n);
}
function paintTemperature(vals) {
  const g = LG.temp, footprint = fpFor(g), d = tempPlane.data, inv = 255 / (TEMP_RANGE[1] - TEMP_RANGE[0]);
  for (let i = 0; i < g.w * g.h; i++) {
    const o = i * 4;
    if ((footprint && footprint[i]) || (studyArea && !studyArea[i])) { d[o + 3] = 0; continue; }
    let k = (vals[i] - TEMP_RANGE[0]) * inv; k = k < 0 ? 0 : k > 255 ? 255 : k | 0;
    d[o] = TEMP_LUT[k * 3]; d[o + 1] = TEMP_LUT[k * 3 + 1]; d[o + 2] = TEMP_LUT[k * 3 + 2]; d[o + 3] = 235;
  }
  tempPlane.tex.needsUpdate = true;
}
function paintFlood(vals) {
  const g = LG.flood, footprint = fpFor(g), d = floodPlane.data, inv = 255 / (FLOOD_RANGE[1] - FLOOD_RANGE[0]);
  for (let i = 0; i < g.w * g.h; i++) {
    const o = i * 4, h = vals[i];
    if (!(h > FLOOD_RANGE[0]) || (footprint && footprint[i])) { d[o + 3] = 0; continue; }
    let k = (h - FLOOD_RANGE[0]) * inv; k = k > 255 ? 255 : k | 0;
    d[o] = FLOOD_LUT[k * 3]; d[o + 1] = FLOOD_LUT[k * 3 + 1]; d[o + 2] = FLOOD_LUT[k * 3 + 2]; d[o + 3] = (150 + k * 0.4) | 0;
  }
  floodPlane.tex.needsUpdate = true;
}
// Sunlight: a lighting overlay rather than a heat map. Shade = 1 - GHI / open-sky GHI of the frame (99th percentile, roofs see the
// open sky) is painted as a dark veil, sunlit cells get a faint warm tint, so the model's own streets show through the shadows.
let solarOpen = 0;
function paintSolar(vals) {
  const g = LG.solar, d = solarPlane.data, n = g.w * g.h;
  const sorted = Float32Array.from(vals).sort(); solarOpen = sorted[Math.floor(n * 0.99)];
  const dusk = solarOpen < 15, inv = dusk ? 0 : 1 / solarOpen;
  for (let i = 0; i < n; i++) {
    const o = i * 4;
    let sh = dusk ? 1 : 1 - vals[i] * inv; sh = sh < 0 ? 0 : sh > 1 ? 1 : sh;
    // same look as the fine shadow layer: warm wash where the cell sees the full sky, blue-violet veil scaled by the shade fraction
    if (sh > 0.08) { const t = Math.pow(sh, 0.8); d[o] = 18; d[o + 1] = 28; d[o + 2] = 96; d[o + 3] = (158 * t) | 0; }
    else { d[o] = 255; d[o + 1] = 234; d[o + 2] = 150; d[o + 3] = 80; }
  }
  ui.solarOpen.textContent = dusk ? 'dusk' : `${solarOpen.toFixed(0)} open sky`;
  solarPlane.tex.needsUpdate = true;
}
const diurnalArray = () => FILES.diurnal[ui.diurnalMode.value.replace('Rel', '')];
const diurnalSeries = () => manifest?.temperature3d_solar?.diurnal?.[LAYERS.diurnal?.series ?? 'diurnal_2026-06-21'];
const diurnalAmbient = k => diurnalSeries()?.ambient_c?.[k];
function paintDiurnal(vals) {
  const g = LG.diurnal, footprint = fpFor(g);
  const mode = ui.diurnalMode.value, rel = /Rel$/.test(mode), d = diurnalPlane.data, [lo, hi] = DIURNAL_RANGE[mode], inv = 255 / (hi - lo), air = !/^ground/.test(mode);
  const ref = rel ? (diurnalAmbient(frameIndex(state.step).diurnal) ?? 0) : 0;
  for (let i = 0; i < g.w * g.h; i++) {
    const o = i * 4;
    if (footprint && footprint[i] && !air) { d[o + 3] = 0; continue; }   // the surface map has no value inside buildings; the air layers do
    let k = (vals[i] - ref - lo) * inv; k = k < 0 ? 0 : k > 255 ? 255 : k | 0;
    d[o] = DIURNAL_LUT[k * 3]; d[o + 1] = DIURNAL_LUT[k * 3 + 1]; d[o + 2] = DIURNAL_LUT[k * 3 + 2]; d[o + 3] = 235;
  }
  ui.diurnalLo.textContent = (rel && lo > 0 ? '+' : '') + lo; ui.diurnalHi.textContent = (rel ? '+' : '') + hi; ui.diurnalUnit.textContent = rel ? 'Δ°C vs ambient air' : '°C';
  diurnalPlane.tex.needsUpdate = true;
}
function paintPollution(vals) {
  const g = LG.poll, d = pollPlane.data;
  for (let i = 0; i < g.w * g.h; i++) {
    const o = i * 4, c = vals[i];
    if (!(c > 0.1)) { d[o + 3] = 0; continue; }
    let f = (Math.log10(c) + 1) / 4; f = f > 1 ? 1 : f;   // 0.1 -> 0, 1000 -> 1
    const k = (f * 255) | 0;
    d[o] = PURPLES[k * 3]; d[o + 1] = PURPLES[k * 3 + 1]; d[o + 2] = PURPLES[k * 3 + 2];
    d[o + 3] = Math.min(255, 40 + f * 260) | 0;
  }
  pollPlane.tex.needsUpdate = true;
}

// ------------------------------------------------------------------ wind particles (comet tails), on the wind layer's grid
const TAIL = 7, WG = LG.wind ?? gridOf(CELL);
const wind = { uv: null, n: 0, x: null, y: null, age: null, hist: null, geom: null, lines: null, fade: 0 };
function buildParticles(n) {
  if (wind.lines) { scene.remove(wind.lines); wind.geom.dispose(); }
  wind.n = n; wind.x = new Float32Array(n); wind.y = new Float32Array(n); wind.age = new Uint16Array(n);
  wind.hist = new Float32Array(n * TAIL * 2);
  const segs = n * (TAIL - 1);
  wind.geom = new THREE.BufferGeometry();
  wind.geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(segs * 2 * 3), 3));
  wind.geom.setAttribute('color', new THREE.BufferAttribute(new Float32Array(segs * 2 * 3), 3));
  const mat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false });
  wind.lines = new THREE.LineSegments(wind.geom, mat);
  wind.lines.renderOrder = 4; wind.lines.visible = false; wind.lines.frustumCulled = false;
  scene.add(wind.lines);
  for (let i = 0; i < n; i++) respawn(i, true);
}
function respawn(i, randomAge) {
  const x = Math.random() * WG.w, y = Math.random() * WG.h;
  wind.x[i] = x; wind.y[i] = y; wind.age[i] = randomAge ? (Math.random() * 100) | 0 : 0;
  for (let k = 0; k < TAIL; k++) { wind.hist[(i * TAIL + k) * 2] = x; wind.hist[(i * TAIL + k) * 2 + 1] = y; }
}
function stepParticles(dtSec) {
  if (!wind.uv) return;
  const n = WG.w * WG.h, uv = wind.uv, pos = wind.geom.attributes.position.array, col = wind.geom.attributes.color.array;
  const vis = dtSec * 60;             // visual seconds of physical time per real second, in cells: (m/s) * s / cell
  const invR = 1 / (WIND_RANGE[1] - WIND_RANGE[0]);
  for (let i = 0; i < wind.n; i++) {
    let x = wind.x[i], y = wind.y[i];
    const c = x | 0, r = y | 0, idx = r * WG.w + c;
    const u = uv[idx], v = uv[n + idx], sp = Math.hypot(u, v);
    wind.age[i]++;
    if (sp < 0.03 || wind.age[i] > 160) { respawn(i, false); continue; }
    x += u * vis / WG.cell; y += v * vis / WG.cell;
    if (x < 0 || x >= WG.w || y < 0 || y >= WG.h) { respawn(i, false); continue; }
    // shift history
    const h = i * TAIL * 2;
    for (let k = TAIL - 1; k > 0; k--) { wind.hist[h + k * 2] = wind.hist[h + (k - 1) * 2]; wind.hist[h + k * 2 + 1] = wind.hist[h + (k - 1) * 2 + 1]; }
    wind.hist[h] = x; wind.hist[h + 1] = y; wind.x[i] = x; wind.y[i] = y;
    const t = Math.min(1, (sp - WIND_RANGE[0]) * invR);
    const R = 0.45 + 0.55 * t, Gc = 0.65 + 0.35 * t, B = 1.0;
    for (let k = 0; k < TAIL - 1; k++) {
      const s = (i * (TAIL - 1) + k) * 6;
      const ax = wind.hist[h + k * 2], ay = wind.hist[h + k * 2 + 1], bx = wind.hist[h + (k + 1) * 2], by = wind.hist[h + (k + 1) * 2 + 1];
      pos[s] = X0 + ax * WG.cell; pos[s + 1] = LAYER_Y.particles; pos[s + 2] = ZS - ay * WG.cell;
      pos[s + 3] = X0 + bx * WG.cell; pos[s + 4] = LAYER_Y.particles; pos[s + 5] = ZS - by * WG.cell;
      const fa = 1 - k / (TAIL - 1), fb = 1 - (k + 1) / (TAIL - 1);
      col[s] = R * fa; col[s + 1] = Gc * fa; col[s + 2] = B * fa;
      col[s + 3] = R * fb; col[s + 4] = Gc * fb; col[s + 5] = B * fb;
    }
  }
  wind.geom.attributes.position.needsUpdate = true;
  wind.geom.attributes.color.needsUpdate = true;
}

// ------------------------------------------------------------------ time / frames / sequencing
// Timeline = the wind run: steps 1..STEPS of STEP_S seconds (scene.json timeline). Layers on that clock (wind, pollution,
// temperature) map a step to their frame through t0_s / step_s; a layer can start later (South Kensington's 2-D temperature
// run starts at 1000 s). Layers with their own clock (flood, sunlight, day cycle) play their own frames in sequence mode;
// in overlay mode they follow the timeline (flood shows its static maximum-depth map instead).
const clamp = (v, lo, hi) => v < lo ? lo : v > hi ? hi : v;
const mapped = (L, step) => clamp(Math.floor((step * STEP_S - L.t0_s) / L.step_s + 1e-6), 0, L.frames - 1);
function phaseSpan(key) {
  const L = LAYERS[key];
  if (key === 'solar') return { start: 1, end: L.frames ?? 99 };
  if (L.own_clock) return { start: 1, end: L.frames };
  return { start: Math.max(1, Math.ceil(L.t0_s / STEP_S - 1e-6)), end: Math.min(STEPS, Math.floor((L.t0_s + (L.frames - 1) * L.step_s) / STEP_S + 1e-6)) };
}
const PHASES = {};
for (const k of PHASE_ORDER) PHASES[k] = { ...phaseSpan(k), rate: LAYERS[k].rate, label: LAYERS[k].title ?? LAYERS[k].label };
const OVERLAY_LABEL = 'Overlay · ' + PHASE_ORDER.map(k => (TAB_NAME[k] ?? k).toLowerCase()).join(' / ');
const state = { step: 1, playing: false, timer: null, token: 0, loading: false, fields: { wind: null, temp: null, poll: null, flood: null, solar: null, shadow: null, diurnal: null }, introDone: false, phase: PHASE_ORDER[0] };
let floodMeta = null, manifest = null;   // manifest entry of the flood array (time_s, rain_mm_h); the whole manifest (solar / diurnal frame times)
fetch(DATA + 'manifest.json').then(r => r.json()).then(m => { manifest = m; floodMeta = m.arrays?.[FILES.flood] ?? null; solarPhaseSetup(); }).catch(() => {});
const solarFile = () => (ui.solarMode.value === 'shadow' ? FILES.shadow : FILES.solar)[ui.solarDate.value];
const solarKey = () => (ui.solarMode.value === 'shadow' ? 'shadow_' : 'solar_') + ui.solarDate.value;
const solarDayLabel = () => LAYERS.solar?.dates?.[ui.solarDate.value]?.label ?? ui.solarDate.value;
// Decoded frame of a layer: the pre-rendered PNG (physics/web/, ~100 KB) when present, else the raw .npy Range read.
// Both give the same array layout (wind: [u..., v..., w...]; shadow: Uint8Array 0/1, unpacked when the array stores packed bits).
function frame(key, file, k, raw = false) {
  if (hasLayer(key)) return getFrameF32(key, k);
  return getFrame(file, k).then(a => raw ? (LAYERS.solar?.shadow_packed && /^shadow_/.test(key) ? unpackBits(a, LG.shadow) : a) : f16(a));
}
function prefetch(key, file, k) { if (hasLayer(key)) getFrameF32(key, k); else getFrame(file, k); }
const solarMeta = () => manifest?.arrays?.[solarFile()];
function solarPhaseSetup() {   // frame count and rate of the solar phase follow the chosen day and display mode
  if (!has('solar')) return;
  const S = LAYERS.solar, meta = solarMeta(), shadow = ui.solarMode.value === 'shadow';
  PHASES.solar.end = meta?.shape?.[0] ?? layerMeta(solarKey())?.frames ?? PHASES.solar.end;
  PHASES.solar.rate = shadow ? (S.shadow_rate ?? 2) : (S.ghi_rate ?? 12);
  PHASES.solar.label = `Sunlight · ${solarDayLabel()} · ${shadow ? (S.shadow_label ?? 'shadows') : (S.ghi_label ?? 'clear-sky irradiance')}`;
}
// the scene's sun follows the real sun position of the solar frame (azimuth 0 = north, clockwise; model north = -Z)
const SUN_DEFAULT = { pos: sun.position.clone(), intensity: sun.intensity };
function placeSun(altDeg, azDeg) {
  if (altDeg === undefined) { sun.position.copy(SUN_DEFAULT.pos); sun.intensity = SUN_DEFAULT.intensity; return; }
  const alt = THREE.MathUtils.degToRad(Math.max(altDeg, 2)), az = THREE.MathUtils.degToRad(azDeg), r = 3000;
  sun.position.set(r * Math.cos(alt) * Math.sin(az), r * Math.sin(alt), -r * Math.cos(alt) * Math.cos(az));
  sun.intensity = SUN_DEFAULT.intensity * (0.35 + 0.65 * Math.min(1, Math.max(0, altDeg) / 40));
}
function frameIndex(step) {
  const own = ph => seqMode() && state.phase === ph, fi = {};
  for (const k of Object.keys(LAYERS)) {
    const L = LAYERS[k];
    if (k === 'solar') fi.solar = Math.min(PHASES.solar.end - 1, Math.max(0, step - 1));               // overlay: the timeline runs through the day
    else if (L.own_clock) fi[k] = own(k) ? Math.min(L.frames - 1, step - 1) : (L.max ? null : mapped(L, step));   // null = static maximum map
    else fi[k] = mapped(L, step);
  }
  return fi;
}
function seqMode() { return ui.mode.value === 'seq'; }
function activeLayers() {
  const chk = { wind: ui.lWind, temp: ui.lTemp, poll: ui.lPoll, flood: ui.lFlood, solar: ui.lSolar, diurnal: ui.lDiurnal }, act = {};
  for (const k of Object.keys(chk)) act[k] = has(k) && (seqMode() ? state.phase === k : chk[k].checked);
  return act;
}
function repaint() {
  const f = state.fields, act = activeLayers();
  if (has('wind') && !f.wind) return;
  if (has('wind') && (act.wind || windPlane.fade > 0)) paintWind(f.wind);
  if (has('poll') && (act.poll || pollPlane.fade > 0) && f.poll) paintPollution(f.poll);
  if (has('flood') && (act.flood || floodPlane.fade > 0) && f.flood) paintFlood(f.flood);
  if (has('solar') && (act.solar || solarPlane.fade > 0) && f.solar && ui.solarMode.value !== 'shadow') paintSolar(f.solar);
  if (has('diurnal') && (act.diurnal || diurnalPlane.fade > 0) && f.diurnal) paintDiurnal(f.diurnal);
  if (has('temp') && (act.temp || tempPlane.fade > 0) && f.temp) {
    if (ui.tempMode.value === 'iso') { paintIsotherms(f.temp); } else { paintTemperature(f.temp); }
  }
}
async function loadStep(step) {
  try { return await loadStepInner(step); } catch (e) { state.loading = false; console.error('frame load failed', e); }
}
async function loadStepInner(step) {
  const token = ++state.token, fi = frameIndex(step);
  const act = activeLayers();
  const wantFlood = has('flood') && (act.flood || floodPlane.fade > 0), wantSolar = has('solar') && (act.solar || solarPlane.fade > 0), wantDiurnal = has('diurnal') && (act.diurnal || diurnalPlane.fade > 0);
  const shadowMode = ui.solarMode.value === 'shadow';
  // fetch only what is shown or fading (plus a first frame of each field for the readout); every other layer keeps its last frame
  const wantWind = has('wind') && (act.wind || windPlane.fade > 0 || !state.fields.wind), wantPoll = has('poll') && (act.poll || pollPlane.fade > 0 || !state.fields.poll), wantTemp = has('temp') && (act.temp || tempPlane.fade > 0 || !state.fields.temp);
  state.loading = true;
  const dKey = 'diurnal_' + ui.diurnalMode.value.replace('Rel', '');
  const [wr, pr, tr, fr, sr, dr] = await Promise.all([wantWind ? frame('wind', FILES.wind, fi.wind) : null, wantPoll ? frame('poll', FILES.poll, fi.poll) : null, wantTemp ? frame('temp', FILES.temp, fi.temp) : null,
    wantFlood ? (fi.flood === null ? (hasLayer('floodMax') ? getFrameF32('floodMax', 0) : npy(FILES.floodMax).readAll().then(f16)) : frame('flood', FILES.flood, fi.flood)) : null,
    wantSolar ? frame(solarKey(), solarFile(), fi.solar, shadowMode) : null,
    wantDiurnal ? frame(dKey, diurnalArray(), fi.diurnal) : null]);
  if (token === state.token) state.loading = false;
  if (token !== state.token) return;
  if (sr) { if (shadowMode) { state.fields.shadow = sr; state.fields.solar = null; uploadShadow(sr); } else { state.fields.solar = sr; state.fields.shadow = null; } }
  if (dr) state.fields.diurnal = dr;
  // decode only what is shown (the raw frames stay cached for the readout)
  if (wr) state.fields.wind = wr;
  if (pr) state.fields.poll = pr;
  if (tr) state.fields.temp = tr;
  if (fr) state.fields.flood = fr;
  wind.uv = state.fields.wind;
  repaint();
  const ph = PHASES[state.phase];
  const sm = wantSolar ? solarMeta() : null, sAlt = sm?.altitude_deg?.[fi.solar], sAz = sm?.azimuth_deg?.[fi.solar];
  placeSun(seqMode() && state.phase === 'solar' && sAlt !== undefined ? sAlt : undefined, sAz);
  if (seqMode() && state.phase === 'flood') {
    const k = fi.flood, ts = floodMeta?.time_s?.[k], rain = floodMeta?.rain_mm_h?.[k];
    ui.timeLabel.textContent = `Flooding · frame ${k + 1} / ${ph.end} · t = ${ts !== undefined ? Math.round(ts / 60) : k * 10} min` + (rain !== undefined ? ` · rain ${rain.toFixed(1)} mm/h` : '');
  } else if (seqMode() && state.phase === 'solar') {
    const k = fi.solar, tl = sm?.time_local?.[k];
    ui.timeLabel.textContent = `${solarDayLabel()} · ${tl ?? `frame ${k + 1}`} local · sun altitude ${sAlt !== undefined ? sAlt.toFixed(0) + '°' : '–'} · ${k + 1} / ${ph.end}`;
  } else if (seqMode() && state.phase === 'diurnal') {
    const k = fi.diurnal, dm = diurnalSeries(), hr = dm?.hours_local?.[k], amb = dm?.ambient_c?.[k];
    ui.timeLabel.textContent = `${LAYERS.diurnal.day_label ?? ''} · ${hr !== undefined ? String(hr).padStart(2, '0') + ':00' : `hour ${k + 1}`} local · ambient ${amb !== undefined ? amb.toFixed(1) + ' °C' : '–'} · ${k + 1} / ${ph.end}`;
  } else ui.timeLabel.textContent = seqMode()
    ? `${ph.label} · frame ${step - ph.start + 1} / ${ph.end - ph.start + 1} · t = ${step * STEP_S} s`
    : `Step ${step} · t = ${step * STEP_S} s` + (has('temp') && step < PHASES.temp?.start ? ' · temperature run not started' : '') + (act.flood && LAYERS.flood?.max ? ' · flood layer = maximum depth of the event' : '');
  for (let k = 1; k <= 4; k++) { const n = step + k; if (n <= ph.end) { const f = frameIndex(n); if (act.wind) prefetch('wind', FILES.wind, f.wind); if (act.poll) prefetch('poll', FILES.poll, f.poll); if (act.temp) prefetch('temp', FILES.temp, f.temp); if (act.flood && f.flood !== null) prefetch('flood', FILES.flood, f.flood); if (act.solar) prefetch(solarKey(), solarFile(), f.solar); if (act.diurnal) prefetch(dKey, diurnalArray(), f.diurnal); } }
}
function setStep(s) {
  const lo = seqMode() ? PHASES[state.phase].start : 1, hi = seqMode() ? PHASES[state.phase].end : STEPS;
  state.step = Math.max(lo, Math.min(hi, s)); ui.step.min = lo; ui.step.max = hi; ui.step.value = state.step;
  loadStep(state.step);
}
function setPhase(phase) {
  state.phase = phase;
  ui.stage.textContent = seqMode() ? `Sequence · ${PHASES[phase].label}` : OVERLAY_LABEL;
  if (section === 'fields' && state.introDone && seqMode()) ui.lGround.checked = ui.lTrees.checked = phase === 'flood' || phase === 'solar';   // flood and sunlight read better with the streets and green areas under them; the other fields hide them
  applyLayers();
  setStep(PHASES[phase].start);
  if (state.playing) setPlaying(true);   // phases can have their own rate (flood plays at 2 frames/s)
  setSectionUI();
}
function tick() {
  if (state.loading) return;   // previous frame still loading: wait for it rather than cancelling it (that starved the painter)
  if (state.step < (seqMode() ? PHASES[state.phase].end : STEPS)) { setStep(state.step + 1); return; }
  if (seqMode()) {
    const i = PHASE_ORDER.indexOf(state.phase);
    if (i === PHASE_ORDER.length - 1 && ui.auto.checked && section === 'fields') { runCampus(); return; }
    setPhase(PHASE_ORDER[(i + 1) % PHASE_ORDER.length]);
  } else setStep(1);
}
function setPlaying(p) {
  state.playing = p; if (section !== 'campus') ui.play.textContent = p ? '❚❚' : '▶';
  clearInterval(state.timer); state.timer = null;
  const rate = section === 'campus' ? 12 : (seqMode() && PHASES[state.phase].rate) || +ui.rate.value;
  if (p) state.timer = setInterval(tick, 1000 / rate);
}
const RATES = { replay: [[0.5, '0.5×'], [1, '1×'], [2, '2×'], [4, '4×'], [10, '10×']], fields: [[2, '2 steps/s'], [4, '4 steps/s'], [8, '8 steps/s'], [12, '12 steps/s'], [20, '20 steps/s']] };
function setRateOptions(kind, value) {
  ui.rate.replaceChildren(...RATES[kind].map(([v, l]) => { const o = document.createElement('option'); o.value = v; o.textContent = l; return o; }));
  ui.rate.value = String(value);
}
ui.play.addEventListener('click', () => {
  if (section === 'campus' && replayLayer) { replayLayer.playing = !replayLayer.playing; ui.play.textContent = replayLayer.playing ? '❚❚' : '▶'; }
  else if (section === 'campus' && tour.active) { tour.paused = !tour.paused; if (traffic) traffic.playing = !tour.paused; ui.play.textContent = tour.paused ? '▶' : '❚❚'; }
  else setPlaying(!state.playing);
});
ui.rate.addEventListener('change', () => { if (section === 'campus' && replayLayer) replayLayer.speed = +ui.rate.value; else if (section === 'campus' && traffic) traffic.speed = +ui.rate.value; else if (state.playing) setPlaying(true); });
ui.step.addEventListener('input', () => { if (section === 'campus' && replayLayer) { replayLayer.t = +ui.step.value; replayLayer.update(replayLayer.t); } else if (section === 'campus' && traffic) { traffic.t = +ui.step.value; traffic.update(traffic.t); } else if (section !== 'campus') setStep(+ui.step.value); });
ui.mode.addEventListener('change', () => { if (seqMode()) setPhase(state.phase); else { ui.stage.textContent = OVERLAY_LABEL; applyLayers(); setStep(state.step); } });
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.key === ' ') { e.preventDefault(); setPlaying(!state.playing); }
  else if (e.key === 'ArrowLeft') setStep(state.step - 1);
  else if (e.key === 'ArrowRight') setStep(state.step + 1);
});

// ------------------------------------------------------------------ layer controls (with per-layer fades)
const groundMeshes = [];   // flat, wide meshes of the model (site ground, roads, paving)
const elevatedMeshes = []; // road decks the model lifts above the ground ("<road>_way-<id>_|_surface…" with a top above 1 m): the SUMO lanes on those ways follow them
const treeMeshes = [];     // canopies, trunks, hedges, planters
// South Kensington detail tile (tile.js): the main model is clipped inside the tile's plate, the tile outside it
let mainScene = null, mainBatches = null, tileGroup = null, tileBatches = null, tileIds = new Set();
const tileHidden = new Set();          // main / supplementary meshes the tile replaces (hidden while the tile is on)
const holeMaterials = new Set();       // materials of the main model's ground / road layers: clipped inside the tile
const tileHole = tileClipPlanes(false), tileKeep = tileClipPlanes(true);
let supplementBatches = null;
const expansions = [];
function applyTile() {
  if (!tileGroup) return;
  const on = ui.lTile.checked;
  tileGroup.visible = on; tileBatches.visible = on;
  for (const o of tileHidden) o.visible = !on;
  setClipping(holeMaterials, on ? tileHole : null, true);
  applyLayers();   // ground / tree toggles respect the hidden set
}
const replaced = m => tileGroup && ui.lTile.checked && tileHidden.has(m);
ui.lTile.addEventListener('input', applyTile);
$('l-supplement').addEventListener('input', applyLayers);
$('l-expansion').checked = new URLSearchParams(location.search).get('expansion') !== '0';
$('l-expansion').addEventListener('input', applyLayers);
const FADE_SEC = 0.6;
function applyLayers() {
  const on = state.introDone, act = activeLayers();
  if (windPlane) windPlane.target = on && act.wind ? 1 : 0;
  if (tempPlane) tempPlane.target = on && act.temp ? 1 : 0;
  if (pollPlane) pollPlane.target = on && act.poll ? 1 : 0;
  if (floodPlane) floodPlane.target = on && act.flood ? 1 : 0;
  if (solarPlane) solarPlane.target = on && act.solar && ui.solarMode.value !== 'shadow' ? 1 : 0;
  if (shadowPlane) shadowPlane.target = on && act.solar && ui.solarMode.value === 'shadow' ? 1 : 0;
  if (diurnalPlane) diurnalPlane.target = on && act.diurnal ? 1 : 0;
  model.visible = ui.lModel.checked;
  if (supplementBatches) supplementBatches.visible = $('l-supplement').checked;
  for (const expansion of expansions) expansion.setEnabled($('l-expansion').checked);
  base.visible = ui.lGround.checked;
  for (const m of groundMeshes) m.visible = ui.lGround.checked && !replaced(m);
  for (const m of treeMeshes) m.visible = ui.lTrees.checked && !replaced(m);
  updateFades(0);
}
function updateFades(dt) {
  let changed = false;
  for (const L of Object.values(planes)) {
    const t = L.target ?? 0;
    if (L.fade !== t) { L.fade = dt > 0 ? (L.fade < t ? Math.min(t, L.fade + dt / FADE_SEC) : Math.max(t, L.fade - dt / FADE_SEC)) : L.fade; changed = true; }
  }
  const isoMode = ui.tempMode.value === 'iso';
  if (windPlane) {
    windPlane.mesh.visible = windPlane.fade > 0;
    windPlane.mat.opacity = +ui.oWind.value * windPlane.fade;
    wind.lines.visible = windPlane.fade > 0 && ui.lPart.checked;
    wind.lines.material.opacity = 0.9 * windPlane.fade;
  }
  if (tempPlane) {
    tempPlane.mesh.visible = tempPlane.fade > 0 && !isoMode;
    tempPlane.mat.opacity = +ui.oTemp.value * tempPlane.fade;
    if (iso.lines) iso.lines.visible = tempPlane.fade > 0 && isoMode;
    iso.material.opacity = +ui.oTemp.value * tempPlane.fade;
  }
  if (pollPlane) { pollPlane.mesh.visible = pollPlane.fade > 0; pollPlane.mat.opacity = +ui.oPoll.value * pollPlane.fade; }
  if (floodPlane) { floodPlane.mesh.visible = floodPlane.fade > 0 && !!state.fields.flood; floodPlane.mat.opacity = +ui.oFlood.value * floodPlane.fade; }
  if (solarPlane) { solarPlane.mesh.visible = solarPlane.fade > 0 && !!state.fields.solar; solarPlane.mat.opacity = +ui.oSolar.value * solarPlane.fade; }
  if (shadowPlane) { shadowPlane.mesh.visible = shadowPlane.fade > 0 && !!state.fields.shadow; shadowPlane.mat.opacity = +ui.oSolar.value * shadowPlane.fade; }
  if (diurnalPlane) { diurnalPlane.mesh.visible = diurnalPlane.fade > 0 && !!state.fields.diurnal; diurnalPlane.mat.opacity = +ui.oDiurnal.value * diurnalPlane.fade; }
  return changed;
}
for (const el of [ui.lWind, ui.lTemp, ui.lPoll, ui.lFlood, ui.lSolar, ui.lDiurnal]) el.addEventListener('input', () => {
  if (seqMode()) { ui.mode.value = 'overlay'; ui.stage.textContent = OVERLAY_LABEL; }
  applyLayers(); repaint(); setStep(state.step);
});
for (const el of [ui.lModel, ui.lGround, ui.lTrees, ui.lPart, ui.oWind, ui.oTemp, ui.oPoll, ui.oFlood, ui.oSolar, ui.oDiurnal]) el.addEventListener('input', applyLayers);
for (const el of [ui.solarDate, ui.solarMode]) el.addEventListener('change', () => {   // new day / display: the phase gets its frame count and rate, then restarts
  solarPhaseSetup(); state.fields.solar = state.fields.shadow = null; applyLayers();
  if (seqMode() && state.phase === 'solar') { ui.stage.textContent = `Sequence · ${PHASES.solar.label}`; setStep(PHASES.solar.start); if (state.playing) setPlaying(true); } else setStep(state.step);
});
ui.diurnalMode.addEventListener('change', () => { state.fields.diurnal = null; setStep(state.step); });
ui.tempMode.addEventListener('input', () => { applyLayers(); repaint(); });
function applyReplayLayers() { replayLayer?.applyLayers({ cars: ui.lCars.checked, uavs: ui.lUavs.checked, signals: ui.lSignals.checked, stations: ui.lStations.checked, roads: ui.lRoads.checked, trafficMap: ui.lMap.checked, birds: ui.lBirds.checked }); }
for (const el of [ui.lCars, ui.lUavs, ui.lSignals, ui.lStations, ui.lRoads, ui.lMap, ui.lBirds]) el.addEventListener('input', applyReplayLayers);
// ---- bird tracker module (panel): follow the flock centroid or a single bird; holds the "Birds" view until another tab is chosen
const birdUI = { box: $('bird-tracker'), target: $('bird-target'), mode: $('bird-mode'), readout: $('bird-readout') };
function setupBirdTracker() {
  if (!replayLayer?.birds) return;
  for (let i = 0; i < replayLayer.birds.stats.birds; i++) { const o = document.createElement('option'); o.value = i; o.textContent = `Bird ${String(i + 1).padStart(3, '0')}`; birdUI.target.append(o); }
  birdUI.box.style.display = '';
}
function applyBirdTracking() {
  if (!replayLayer?.birds) return;
  const v = birdUI.target.value;
  if (v === '') { replayLayer.trackBirds(null); if (replayLayer.shot === 'birds') replayLayer.shotUntil = performance.now(); return; }
  if (section !== 'campus') runCampus();
  replayLayer.stopShots(); flight = null; controls.enabled = true;
  replayLayer.shot = 'birds'; replayLayer.shotUntil = Infinity; replayLayer.label = SHOTS_BIRDS_LABEL; setSectionUI();
  replayLayer.trackBirds(v === 'flock' ? 'flock' : +v, birdUI.mode.value);
}
const SHOTS_BIRDS_LABEL = 'Birds · tracking (hold; pick another view to resume the tour)';
birdUI.target.addEventListener('change', applyBirdTracking);
birdUI.mode.addEventListener('change', applyBirdTracking);
ui.nPart.addEventListener('change', () => { buildParticles(+ui.nPart.value); applyLayers(); });

// ------------------------------------------------------------------ camera choreography
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const campusCentre = new THREE.Vector3((FOCUS.box[0][0] + FOCUS.box[1][0]) / 2, 15, (FOCUS.box[0][1] + FOCUS.box[1][1]) / 2);
const domainCentre = new THREE.Vector3(CX, 0, CZ);
function fitDistance() {
  const vFov = THREE.MathUtils.degToRad(camera.fov), hFov = 2 * Math.atan(Math.tan(vFov / 2) * camera.aspect);
  return 1.08 * Math.max((SPAN_Z / 2) / Math.tan(vFov / 2), (SPAN_X / 2) / Math.tan(hFov / 2));
}
function campusPose(azimuth) {
  const dist = FOCUS.orbit_m ?? 480, elev = THREE.MathUtils.degToRad(32);
  const pos = new THREE.Vector3(
    campusCentre.x + dist * Math.cos(elev) * Math.sin(azimuth),
    campusCentre.y + dist * Math.sin(elev),
    campusCentre.z + dist * Math.cos(elev) * Math.cos(azimuth));
  return { pos, target: campusCentre.clone() };
}
function overheadPose() {
  // near-overhead (5 deg tilt towards the south keeps the orbit controls well-defined)
  const tilt = THREE.MathUtils.degToRad(5), d = fitDistance();
  const target = new THREE.Vector3(domainCentre.x, LAYER_Y.wind, domainCentre.z);
  return { pos: new THREE.Vector3(target.x, target.y + d * Math.cos(tilt), target.z + d * Math.sin(tilt)), target };
}
let flight = null;   // { from, to, t0, dur, onDone }
function flyTo(pose, dur, onDone) {
  flight = { from: { pos: camera.position.clone(), target: controls.target.clone() }, to: pose, t0: performance.now(), dur, onDone };
  controls.enabled = false;
}
function updateFlight(now) {
  if (!flight) return;
  const k = Math.min(1, (now - flight.t0) / flight.dur), e = ease(k);
  camera.position.lerpVectors(flight.from.pos, flight.to.pos, e);
  controls.target.lerpVectors(flight.from.target, flight.to.target, e);
  camera.lookAt(controls.target);
  if (k >= 1) { const f = flight; flight = null; controls.enabled = true; controls.update(); if (f.onDone) f.onDone(); }
}
function campusPoseDeg(azDeg) { return campusPose(THREE.MathUtils.degToRad(azDeg)); }
// Plain site tour for scenes without a replay: a slow orbit around the focus (then, with a transport layer, a wide orbit
// over the network), then (auto loop) the fields.
const TOUR_SHOTS = { overview: { dist: 1, elev: 32, dur: 16000, label: () => `${FOCUS.label ?? SCENE.title} · overview`, time: () => `Overview · orbiting ${FOCUS.label ?? SCENE.title}` },
  traffic: { dist: 0.55, elev: 48, dur: 18000, label: () => `${SCENE.traffic?.label ?? 'Traffic'} · cars and signal states of the SUMO run`, time: () => traffic ? `Replay ${trafficTime(traffic.t)} · ${traffic.speed}×` : 'Traffic' },
  trafficMap: { fixed: () => overheadPose(), dur: 16000, label: () => `${SCENE.traffic?.label ?? 'Traffic'} · whole area: cars as white (moving) / amber (stopped) dots, signal heads as red / amber / green dots`, time: () => traffic ? `Replay ${trafficTime(traffic.t)} · ${traffic.speed}×` : 'Traffic' },
  transport: { dist: 2.4, elev: 52, dur: 14000, label: () => `${SCENE.transport?.label ?? 'Transport'} · tube, rail and bus network, road disruptions and traffic cameras`, time: () => transport?.summary ?? 'Transport' } };
const TOUR_ORDER = ['overview', ...(SCENE.traffic ? ['trafficMap'] : [])];
const trafficTime = s => { const t = Math.max(0, Math.floor(s)); return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`; };
const tour = { active: false, paused: false, az: 0, t0: 0, dur: 16000, shot: 'overview', hold: false };
function tourPose(az, shot = tour.shot) {
  const s = TOUR_SHOTS[shot]; if (s.fixed) return s.fixed();
  const dist = (FOCUS.orbit_m ?? 480) * s.dist, elev = THREE.MathUtils.degToRad(s.elev);
  return { pos: new THREE.Vector3(campusCentre.x + dist * Math.cos(elev) * Math.sin(az), campusCentre.y + dist * Math.sin(elev), campusCentre.z + dist * Math.cos(elev) * Math.cos(az)), target: campusCentre.clone() };
}
function startTour(shot = 'overview') {
  const first = !tour.active || tour.shot === shot;
  tour.active = true; tour.paused = false; tour.shot = shot; tour.t0 = performance.now(); tour.dur = TOUR_SHOTS[shot].dur;
  if (first) tour.az = THREE.MathUtils.degToRad(-150);
  ui.stage.textContent = TOUR_SHOTS[shot].label(); ui.info.textContent = shot === 'overview' ? (SCENE.description ?? '') : shot === 'traffic' ? (traffic?.info ?? '') : (transport?.statusLines?.slice(0, 4).join(' · ') ?? '');
  applyTrafficLayers(); applyTransportLayers(); if (shot === 'traffic') traffic?.highlightRoads(true);
  const p = tourPose(tour.az);
  if (camera.position.distanceTo(p.pos) > 50) { flyTo(p, 2600, () => { controls.enabled = false; tour.t0 = performance.now(); }); }
  else { controls.enabled = false; flight = null; }
  setSectionUI();
}
function updateTour(now, dt) {
  if (!tour.active || flight) return;
  if (!tour.paused && !TOUR_SHOTS[tour.shot].fixed) tour.az += dt * (tour.shot === 'overview' ? 0.09 : 0.05);
  const p = tourPose(tour.az);
  camera.position.copy(p.pos); controls.target.copy(p.target); camera.lookAt(p.target);
  ui.timeLabel.textContent = TOUR_SHOTS[tour.shot].time();
  if (traffic) { ui.step.value = traffic.t; ui.stats.textContent = traffic.stats; }
  if (!tour.paused && !tour.hold && now - tour.t0 > tour.dur) {
    const i = TOUR_ORDER.indexOf(tour.shot), rest = TOUR_ORDER.slice(i + 1).filter(k => traffic || !/^traffic/.test(k));
    if (rest.length) startTour(rest[0]);
    else if (ui.auto.checked) { tour.active = false; runFields(); }
    else startTour(TOUR_ORDER[0]);
  }
}
function setSectionUI() {
  shotButtons.forEach(b => b.classList.toggle('active', section === 'campus' && (replayLayer ? replayLayer.shot === b.dataset.shot : tour.active && tour.shot === b.dataset.shot)));
  fieldButtons.forEach(b => b.classList.toggle('active', section === 'fields' && (seqMode() ? state.phase === b.dataset.field : true)));
}
/** Site section: ground, trees and (South Kensington) the traffic / UAV replay visible; the physics fields hidden; the shot tour runs. */
function runCampus(shot = 'overview') {
  section = 'campus'; placeSun();
  setPlaying(false); state.introDone = false; applyLayers();            // fields fade out
  ui.lGround.checked = true; ui.lTrees.checked = true; applyLayers();
  if (replayLayer) { replayLayer.setVisible(true); replayLayer.playing = true; }
  applyTransportLayers(); applyTrafficLayers();
  setRateOptions('replay', replayLayer?.speed ?? traffic?.speed ?? 1); ui.play.textContent = '❚❚';
  if (replayLayer) { ui.step.min = replayLayer.traffic?.firstTime ?? 0; ui.step.max = replayLayer.duration || 3600; ui.step.step = 0.1; ui.step.disabled = false; ui.rate.disabled = false; }
  else if (traffic) { traffic.playing = true; ui.step.min = 0; ui.step.max = traffic.duration; ui.step.step = 0.1; ui.step.disabled = false; ui.rate.disabled = false; }
  else { ui.step.disabled = true; ui.rate.disabled = true; }
  if (replayLayer) replayLayer.startShot(shot); else startTour(TOUR_SHOTS[shot] ? shot : 'overview');
  setSectionUI();
}
// ---- SUMO traffic replay controls (panel)
const tfUI = { box: $('traffic-ctl'), on: $('l-traffic'), cars: $('l-tf-cars'), signals: $('l-tf-signals'), roads: $('l-tf-roads'), paths: $('l-tf-paths'), map: $('l-tf-map'), stats: $('traffic-stats') };
function applyTrafficLayers() {
  if (!traffic) return;
  traffic.setVisible(tfUI.on.checked && section !== 'fields');
  traffic.applyLayers({ cars: tfUI.cars.checked, signals: tfUI.signals.checked, roads: tfUI.roads.checked, paths: tfUI.paths.checked && tour.shot === 'traffic', map: tfUI.map.checked || (section === 'campus' && tour.active && tour.shot === 'trafficMap') });
}
function setupTrafficUI() {
  if (!traffic) return;
  tfUI.box.style.display = ''; tfUI.stats.textContent = traffic.stats;
  for (const el of [tfUI.on, tfUI.cars, tfUI.signals, tfUI.roads, tfUI.paths, tfUI.map]) el.addEventListener('input', applyTrafficLayers);
  applyTrafficLayers();
}
// ---- transport layer controls (panel): sub-layer toggles, snapshot summary, live arrivals at a chosen station
const trUI = { box: $('transport-ctl'), on: $('l-transport'), rail: $('l-tr-rail'), bus: $('l-tr-bus'), stations: $('l-tr-stations'), stops: $('l-tr-stops'), disruptions: $('l-tr-disruptions'), cams: $('l-tr-cams'), stats: $('transport-stats'), station: $('tr-station'), live: $('tr-live'), arrivals: $('tr-arrivals') };
function applyTransportLayers() {
  if (!transport) return;
  transport.setVisible(trUI.on.checked && section !== 'fields' && !(section === 'campus' && tour.active && tour.shot === 'trafficMap'));   // the traffic map keeps only the dots and lanes
  transport.setLayers({ rail: trUI.rail.checked, bus: trUI.bus.checked, stations: trUI.stations.checked, stops: trUI.stops.checked, disruptions: trUI.disruptions.checked, cams: trUI.cams.checked });
}
let arrivalsTimer = null;
async function refreshArrivals() {
  if (!transport || !trUI.station.value) return;
  const id = trUI.station.value, r = await transport.arrivals(id);
  if (trUI.station.value !== id) return;
  trUI.live.textContent = r.live ? `live · ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'snapshot (offline)';
  trUI.arrivals.textContent = r.list.length ? r.list.map(a => `${String(Math.max(0, Math.round((a.seconds ?? 0) / 60))).padStart(2, ' ')} min · ${a.line} → ${a.destination ?? ''}${a.platform ? ' · ' + a.platform.replace('Platform ', 'pl. ') : ''}`).join('\n') : 'no arrivals listed';
}
function setupTransportUI() {
  if (!transport) return;
  trUI.box.style.display = '';
  trUI.stats.textContent = transport.summary + (transport.statusLines.length ? '\n' + transport.statusLines.join('\n') : '');
  trUI.station.replaceChildren(...transport.stations.sort((a, b) => a.name.localeCompare(b.name)).map(s => { const o = document.createElement('option'); o.value = s.id; o.textContent = s.name.replace(/ (Underground|Rail) Station$/, ''); return o; }));
  const first = transport.stations.find(s => /White City/.test(s.name)) ?? transport.stations[0]; if (first) trUI.station.value = first.id;
  for (const el of [trUI.on, trUI.rail, trUI.bus, trUI.stations, trUI.stops, trUI.disruptions, trUI.cams]) el.addEventListener('input', applyTransportLayers);
  trUI.station.addEventListener('change', refreshArrivals);
  refreshArrivals(); clearInterval(arrivalsTimer); arrivalsTimer = setInterval(refreshArrivals, 45000);
  applyTransportLayers();
}
/** Fields section: climb to the overhead view, hide ground / trees / replay, play the fields in sequence. */
function runFields(phase = PHASE_ORDER[0]) {
  if (section === 'fields' && state.introDone) { ui.mode.value = 'seq'; setPhase(phase); setPlaying(true); return; }   // already overhead: jump to that field
  section = 'fields'; tour.active = false;
  replayLayer?.stopShots(); if (replayLayer) replayLayer.playing = false;
  ui.stage.textContent = `Climbing to the overhead view · aligned with the ${CELL} m simulation grid (${G.size_note ?? `${SPAN_X} × ${SPAN_Z} m`})`; ui.info.textContent = '';
  ui.step.disabled = false; ui.rate.disabled = false;
  setSectionUI();
  flyTo(overheadPose(), 3800, () => {
    state.introDone = true;
    ui.lGround.checked = false; ui.lTrees.checked = false;
    replayLayer?.setVisible(false); applyTransportLayers(); applyTrafficLayers();
    setRateOptions('fields', 12); ui.step.step = 1;
    setPhase(seqMode() ? phase : state.phase); setPlaying(true);
  });
}
function playIntro() {
  state.introDone = false; for (const L of Object.values(planes)) L.fade = 0; placeSun();
  const a0 = campusPoseDeg(-150);
  camera.position.copy(a0.pos); controls.target.copy(a0.target); camera.lookAt(a0.target);
  runCampus();
}
shotButtons.forEach(b => b.addEventListener('click', () => {
  if (replayLayer) { if (section !== 'campus') runCampus(); replayLayer.startShot(b.dataset.shot); }
  else runCampus(b.dataset.shot);
  setSectionUI();
}));
fieldButtons.forEach(b => b.addEventListener('click', () => runFields(b.dataset.field)));
ui.replay.addEventListener('click', playIntro);

// ------------------------------------------------------------------ hover readout
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit = new THREE.Vector3();
const cellOf = g => { const c = Math.floor((hit.x - X0) / g.cell), r = Math.floor((ZS - hit.z) / g.cell); return c < 0 || c >= g.w || r < 0 || r >= g.h ? -1 : r * g.w + c; };
renderer.domElement.addEventListener('pointermove', e => {
  ndc.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
  const tInfo = transport?.hover(ndc, camera);   // TfL markers: stations, bus stops, road disruptions, JamCams
  if (!state.introDone) { ui.readout.hidden = !tInfo; if (tInfo) ui.readout.textContent = tInfo; return; }
  ray.setFromCamera(ndc, camera);
  if (!ray.ray.intersectPlane(groundPlane, hit)) { ui.readout.hidden = true; return; }
  const c = Math.floor((hit.x - X0) / CELL), r = Math.floor((ZS - hit.z) / CELL);
  if (c < 0 || c >= W || r < 0 || r >= H) { ui.readout.hidden = true; return; }
  const f = state.fields, [ox, oy] = G.domain_origin_xy_m ?? [0, 0];
  const lines = [...(tInfo ? [tInfo, ''] : []), `${G.origin_label ?? 'Domain'} x ${ox + c * CELL} m, y ${oy + r * CELL} m · cell (${c}, ${r})`];
  if (f.wind) { const i = cellOf(LG.wind), n = LG.wind.w * LG.wind.h; if (i >= 0) { const u = f.wind[i], v = f.wind[n + i], w = f.wind[2 * n + i]; lines.push(`Wind |V| ${Math.hypot(u, v, w).toFixed(2)} m/s  (u ${u.toFixed(2)}, v ${v.toFixed(2)}, w ${w.toFixed(2)})`); } }
  if (f.temp) { const i = cellOf(LG.temp), fp = fpFor(LG.temp); if (i >= 0) lines.push(`Temperature ${f.temp[i].toFixed(2)} °C` + (fp && fp[i] ? ' (building cell)' : '')); }
  if (f.poll) { const i = cellOf(LG.poll); if (i >= 0) lines.push(`Concentration ${f.poll[i] < 10 ? f.poll[i].toFixed(2) : f.poll[i].toFixed(0)}`); }
  if (f.flood) { const i = cellOf(LG.flood); if (i >= 0) lines.push(`Flood depth ${f.flood[i] > FLOOD_RANGE[0] ? f.flood[i].toFixed(2) + ' m' : 'dry'}` + (seqMode() && state.phase === 'flood' ? '' : ' (maximum of the event)')); }
  if (f.solar) { const i = cellOf(LG.solar); if (i >= 0) lines.push(`Sunlight GHI ${f.solar[i].toFixed(0)} W/m²` + (solarOpen >= 15 ? ` (${(100 * f.solar[i] / solarOpen).toFixed(0)} % of open sky)` : '')); }
  if (f.shadow) { const i = cellOf(LG.shadow); if (i >= 0) lines.push(`Sunlight · ${LG.shadow.cell} m cell ${f.shadow[i] ? 'in shadow' : 'sunlit'}`); }
  if (f.diurnal) { const i = cellOf(LG.diurnal); const amb = diurnalAmbient(frameIndex(state.step).diurnal); if (i >= 0) lines.push(`Day cycle ${({ ground: 'ground surface', air0: 'air 0–4 m', air12: 'air 12–16 m' })[ui.diurnalMode.value.replace('Rel', '')]} ${f.diurnal[i].toFixed(1)} °C` + (amb !== undefined ? ` (${(f.diurnal[i] - amb >= 0 ? '+' : '')}${(f.diurnal[i] - amb).toFixed(1)} vs ambient ${amb.toFixed(1)})` : '')); }
  ui.readout.textContent = lines.join('\n'); ui.readout.hidden = false;
});
renderer.domElement.addEventListener('pointerleave', () => { ui.readout.hidden = true; });

// ------------------------------------------------------------------ render loop
let last = performance.now();
function animate(now) {
  requestAnimationFrame(animate);
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (replayLayer && section === 'campus') {
    const boundary = replayLayer.tick(now, dt);
    ui.stage.textContent = replayLayer.label; ui.info.textContent = replayLayer.info; ui.stats.textContent = replayLayer.stats;
    birdUI.readout.textContent = replayLayer.birdInfo || '';
    if (replayLayer.shot === 'birds' && replayLayer.shotUntil !== Infinity && replayLayer.birdTarget === 'flock' && birdUI.target.value !== 'flock') { birdUI.target.value = 'flock'; }   // the tour's own flock shot
    else if (replayLayer.shot !== 'birds' && birdUI.target.value !== '') birdUI.target.value = '';
    ui.timeLabel.textContent = `Replay ${timeString(replayLayer.t)} · ${replayLayer.speed}×`; ui.step.value = replayLayer.t;
    if (ui.rate.value !== String(replayLayer.speed)) ui.rate.value = String(replayLayer.speed);
    if (boundary) { setSectionUI(); if (replayLayer.cycleDone) { if (ui.auto.checked) runFields(); else replayLayer.startShot('overview'); } }
  } else if (section === 'campus') updateTour(now, dt);
  if (traffic && !replayLayer && section !== 'fields' && traffic.group.visible) { traffic.tick(now, dt); if ((now | 0) % 500 < 20) tfUI.stats.textContent = traffic.stats; }
  updateFlight(now);
  if (controls.enabled) controls.update();
  updateFades(dt);
  if (state.introDone && wind.lines.visible) stepParticles(dt);
  renderer.render(scene, camera);
}
renderer.domElement.addEventListener('pointerdown', () => { if (section === 'campus') { if (flight) { flight = null; controls.enabled = true; } replayLayer?.cancelCamera(); if (tour.active) { tour.active = false; controls.enabled = true; setSectionUI(); } } });
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  iso.material.resolution.set(window.innerWidth, window.innerHeight);
  transport?.resize(window.innerWidth, window.innerHeight);
});

// ------------------------------------------------------------------ memory: drop the source geometry of batched meshes
// batchStaticCity merges the visible city meshes into a few float32 batches and hides the sources. The hidden sources kept
// their (quantised) attribute arrays: ~1.5 GB of JS heap for the 36k geometries, which pushed the tab into constant garbage
// collection and made the field playback stall. The sources that can be shown again (the originals behind "Building
// refinements", the meshes the station tile replaces, ground / trees) keep their geometry; everything else hidden gets an
// empty one.
const EMPTY_GEOMETRY = new THREE.BufferGeometry();
function releaseBatchedGeometry() {
  const keep = new Set([...groundMeshes, ...treeMeshes, ...tileHidden, ...elevatedMeshes]);
  for (const e of expansions) for (const o of e.originals) keep.add(o);
  if (tileGroup) tileGroup.traverse(o => keep.add(o));
  let n = 0, bytes = 0;
  model.traverse(o => {
    if (!o.isMesh || o.visible || keep.has(o) || o.geometry === EMPTY_GEOMETRY) return;
    for (const a of Object.values(o.geometry.attributes)) bytes += a.array.byteLength; if (o.geometry.index) bytes += o.geometry.index.array.byteLength;
    o.geometry.dispose(); o.geometry = EMPTY_GEOMETRY; n++;
  });
  console.log(`released ${n} batched source geometries, ${(bytes / 1048576).toFixed(0)} MB`);
}

// ------------------------------------------------------------------ boot
async function boot() {
  buildParticles(+ui.nPart.value);
  const a0 = campusPose(THREE.MathUtils.degToRad(-150));
  camera.position.copy(a0.pos); controls.target.copy(a0.target); camera.lookAt(a0.target);
  requestAnimationFrame(animate);

  // data first (small), then the model
  const M = SCENE.masks ?? {};
  const dataReady = (async () => {
    await initFrames(); console.log('field frames:', framesInfo());
    for (const [cell, file] of Object.entries(M.footprint ?? {})) footprints[+cell] = await loadMask(file);
    if (M.solid_wind && has('wind')) solidWind = await npy(M.solid_wind.file).read(M.solid_wind.layer ?? 0);
    if (M.study_area) studyArea = await loadMask(M.study_area);
    await loadStep(Math.round(STEPS * 0.6));
  })().catch(e => { ui.stage.textContent = 'Data error: ' + e.message; console.error(e); });

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  if (MODEL.compression === 'draco') { const d = new DRACOLoader(); d.setDecoderPath(ROOT + 'vendor/three/examples/jsm/libs/draco/gltf/'); loader.setDRACOLoader(d); }
  // the detail tile downloads alongside the main model and is placed once the main model is batched
  // The station detail tile is off by default (its colours stand out against the main model); ?tile=1 loads it.
  let tileMB = '';
  if (MODEL.tile) { TILE.url = SCENE.url(MODEL.tile); TILE.bytes = MODEL.tile_bytes ?? TILE.bytes; }
  const tileLoad = !MODEL.tile || new URLSearchParams(location.search).get('tile') !== '1' ? Promise.resolve(null)
    : new Promise((resolve, reject) => loader.load(TILE.url, resolve, ev => { tileMB = ` · tile ${(ev.loaded / 1048576).toFixed(0)} / ${(TILE.bytes / 1048576).toFixed(0)} MB`; }, reject))
      .catch(e => { console.error('detail tile failed to load', e); return null; });
  const onCity = (gltf, resolve) => {
      // scene.json model.recolor: [{match: <regex on the material name>, color}] - e.g. the White City GLB paints its parks a
      // muted sage that reads as grey next to the roads; the viewer shows vegetation in a clearer green (the file is untouched).
      // model.lift: [{match, dy}] raises meshes whose material matches (the same GLB buries its park grass 7 cm under the ground plate).
      const recolor = (MODEL.recolor ?? []).map(r => ({ re: new RegExp(r.match, 'i'), color: new THREE.Color(r.color) })), lift = (MODEL.lift ?? []).map(r => ({ re: new RegExp(r.match, 'i'), dy: r.dy }));
      if (recolor.length || lift.length) {
        const done = new Set(); let n = 0, m2 = 0;
        gltf.scene.traverse(o => {
          if (!o.isMesh) return;
          const mats = Array.isArray(o.material) ? o.material : [o.material], name = mats.map(m => m?.name || '').join(' | ');
          const L = lift.find(r => r.re.test(name)); if (L) { o.position.y += L.dy; m2++; }
          for (const m of mats) { if (!m || done.has(m)) continue; done.add(m); const rule = recolor.find(r => r.re.test(m.name || '')); if (rule) { m.color.copy(rule.color); n++; } }
        });
        console.log('recoloured', n, 'materials, lifted', m2, 'meshes');
      }
      gltf.scene.updateMatrixWorld(true);
      const box = new THREE.Box3(), size = new THREE.Vector3();
      gltf.scene.traverse(o => {
        if (!o.isMesh) return;
        if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
        box.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld); box.getSize(size);
        // ground-like: thinner than 3 m and wider than 30 m (site ground, roads, paths, paving, kerbs)
        if (size.y < 3 && Math.max(size.x, size.z) > 30) groundMeshes.push(o);
        if (/way-\d+_\|_surface/.test(o.name) && box.max.y > 1) elevatedMeshes.push(o);
        // trees / vegetation: by node (or ancestor) name, or by material name
        let names = '';
        for (let a = o; a && a !== gltf.scene; a = a.parent) names += (a.name || '') + ' | ';
        const matName = Array.isArray(o.material) ? o.material.map(m => m.name).join(' | ') : (o.material && o.material.name) || '';
        if (TREE_NODE.test(names) || (TREE_MAT.test(matName) && !/tree wells/i.test(matName))) treeMeshes.push(o);
      });
      model.add(gltf.scene);
      resolve(gltf);
  };
  const onCityProgress = ev => {
    const total = ev.total || MODEL.bytes || 1, pct = Math.min(100, ev.loaded / total * 100);
    ui.bar.style.width = pct.toFixed(1) + '%';
    ui.pct.textContent = `${(ev.loaded / 1048576).toFixed(0)} / ${(total / 1048576).toFixed(0)} MB · ${pct.toFixed(0)} %${tileMB}`;
  };
  if (LITE) {
    // proxy city from the masks (already needed for the fields), then the replay layers
    ui.pct.textContent = 'Lite mode · building the voxel city…';
    await dataReady;
    const lite = SCENE.lite, lg = gridOf(lite.cell_m ?? CELL);
    const footprint = footprints[lg.cell] ?? await loadMask(lite.footprint), roof = await loadMask(lite.roof);
    const proxy = buildProxyCity({ footprint, roof, W: lg.w, H: lg.h, CELL: lg.cell, X0, ZS });
    model.add(proxy.mesh);
    base.material.color.set(0x8f938c);   // the proxy city has no ground layer: a lighter plate stands in for it
    console.log('lite city:', proxy.boxes, 'columns,', proxy.triangles, 'triangles');
    $('lite-hint').style.display = ''; $('supplement-ctl').style.display = 'none';
    if (HAS_REPLAY) {
      ui.pct.textContent = 'Traffic and UAV replay…';
      replayLayer = await createReplay({ scene, camera, controls, campusCentre, campusPose: campusPoseDeg, flyTo, onProgress: t => { ui.pct.textContent = t; } })
        .catch(e => { console.error('replay unavailable', e); return null; });
      applyReplayLayers(); setupBirdTracker();
    }
  } else {
  await new Promise((resolve, reject) => {
    if (ON_PAGES && MODEL.parts_manifest) fetchCityModel(MODEL.parts_manifest, onCityProgress).then(buf => loader.parse(buf, '', gltf => onCity(gltf, resolve), reject)).catch(reject);   // GitHub Pages: parts from the models repository
    else loader.load(SCENE.url(MODEL.url), gltf => onCity(gltf, resolve), onCityProgress, err => reject(err));
  }).then(async gltf => {
    // demo_rev02's display filter (hide the GLB's own animated traffic / birds; parked-car filter), then merge the
    // static buildings into a few draw calls. Ground and trees stay separate meshes so their toggles keep working.
    ui.pct.textContent = 'Merging static buildings…';
    if (MODEL.demo_filter) await applyCityFilter(gltf.scene);
    if (MODEL.expansion) for (const batch of EXPANSION_BATCHES) {
      try {
        const refined = await loader.loadAsync(batch.url);
        const expansion = await installExpansion(gltf.scene, refined.scene, batch.ids, batch.projectionM);
        expansions.push(expansion); model.add(expansion.object);
        $('expansion-ctl').style.display = '';
        $('expansion-label').textContent = `Building refinements · ${expansions.reduce((n, e) => n + e.originals.length, 0)}`;
      } catch (error) { console.warn('Building refinement unavailable; original retained', error); }
    }
    const tile = await tileLoad;   // its building ids decide which main-model meshes stay out of the batches
    if (tile) {
      tileIds = tileBuildingIds(tile.scene);
      for (const o of hideReplaced(gltf.scene, tileIds)) tileHidden.add(o);
      // hole materials: the ground layers (site ground, paving, grass, water, road network) and the traffic roads. Materials
      // that any non-flat mesh also uses (roof slates, trims: thin wide building parts land in groundMeshes) are left out so
      // that the main-model buildings kept inside the rectangle are not sliced.
      const flat = new Set(groundMeshes), usedElsewhere = new Set();
      gltf.scene.traverse(o => { if (o.isMesh && o.visible && !flat.has(o) && !/^Traffic_road/.test(o.name)) materialsOf([o], usedElsewhere); });
      for (const m of materialsOf(groundMeshes)) if (!usedElsewhere.has(m)) holeMaterials.add(m);
      holeMaterials.add(base.material);   // the dark base plate would otherwise cut through the tile's railway cutting
      gltf.scene.traverse(o => { if (o.isMesh && o.visible && /^Traffic_road/.test(o.name)) materialsOf([o], holeMaterials); });
      console.log('tile: hole clipping on', holeMaterials.size, 'ground materials:', [...holeMaterials].map(m => m.name).join('; '));
    }
    for (const m of [...groundMeshes, ...treeMeshes]) m.visible = false;
    const batches = await batchStaticCity(gltf.scene); model.add(batches.object);
    for (const m of [...groundMeshes, ...treeMeshes]) if (!tileHidden.has(m)) m.visible = true;
    mainScene = gltf.scene; mainBatches = batches.object;
    console.log('city batches:', batches.stats);
    if (tile) ui.pct.textContent = 'South Kensington detail tile…';
    $('tile-ctl').style.display = tile ? 'contents' : 'none';
    if (tile) {
      const tGround = [], tTrees = [];
      tileGroup = placeTile(tile, { ground: tGround, trees: tTrees }); model.add(tileGroup);
      // the tile's own ground colour is not wanted: its paving (plate top, footways) takes the main model's ground material
      let paving = null; mainScene.traverse(o => { if (!paving && o.isMesh && /^Site_\|_ground$/.test(o.name)) paving = o.material; });
      if (paving) { const g = paving.clone(); g.clippingPlanes = null; tile.scene.traverse(o => { if (o.isMesh && o.material?.name === 'Warm stone paving') o.material = g; }); }
      else console.warn('tile: main ground material not found, tile paving keeps its own colour');
      for (const m of [...tGround, ...tTrees]) m.visible = false;
      tileBatches = (await batchStaticCity(tile.scene)).object; model.add(tileBatches);   // batches are in world space
      for (const m of [...tGround, ...tTrees]) m.visible = true;
      groundMeshes.push(...tGround); treeMeshes.push(...tTrees);
      setClipping(tileGroup, tileKeep, false); setClipping(tileBatches, tileKeep, false);
      applyTile();
      // alignment check: the same OSM building in both files should land on the same spot
      let ref = null; mainScene.traverse(o => { if (!ref && /way-107039270_exterior/.test(o.name)) ref = o; });
      const c = tileBuildingCentre(tile.scene, '107039270');
      if (ref && c) console.log('tile alignment (19 Exhibition Road) tile centre', c.toArray().map(v => v.toFixed(1)).join(', '), '| main centre', new THREE.Box3().setFromObject(ref).getCenter(new THREE.Vector3()).toArray().map(v => v.toFixed(1)).join(', '));
    }
    if (MODEL.supplement) {
      ui.pct.textContent = 'Supplementary buildings…';
      const supplement = await loader.loadAsync(SCENE.url(MODEL.supplement.url));
      supplement.scene.updateMatrixWorld(true);
      if (tileGroup) for (const o of hideReplaced(supplement.scene, tileIds, { buildingsByCentre: true })) tileHidden.add(o);   // the tile models its own area
      const supplementMerged = (await batchStaticCity(supplement.scene)).object;
      supplementBatches = new THREE.Group();
      supplementBatches.add(supplement.scene, supplementMerged);
      supplementBatches.name = 'OSM missing buildings · estimated heights';
      model.add(supplementBatches);
    }
    applyTile(); applyLayers();
    if (HAS_REPLAY) {
      ui.pct.textContent = 'Traffic and UAV replay…';
      replayLayer = await createReplay({ scene, camera, controls, campusCentre, campusPose: campusPoseDeg, flyTo, onProgress: t => { ui.pct.textContent = t; } });
      applyReplayLayers(); setupBirdTracker();
    }
  }).catch(e => { ui.pct.textContent = 'Loading failed: ' + (e.message || e); console.error(e); throw e; });
  releaseBatchedGeometry();
  }
  if (SCENE.traffic) {   // loads in the background (34 MB of vehicle records): the page opens without it and the layer appears when ready
    tfUI.box.style.display = ''; tfUI.stats.textContent = 'Loading the SUMO replay…';
    createTraffic({ scene, base: SCENE.url(SCENE.traffic.dir ?? 'traffic/'), elevated: elevatedMeshes }).then(T => { traffic = T; setupTrafficUI(); const q = new URLSearchParams(location.search); if (q.has('t')) { T.t = +q.get('t'); T.update(T.t); } if (q.get('play') === '0') T.playing = false; if (section === 'campus' && tour.active) startTour(tour.shot); })
      .catch(e => { console.error('traffic replay unavailable', e); tfUI.stats.textContent = 'Traffic replay unavailable: ' + (e.message || e); });
  }
  if (SCENE.transport) {
    transport = await createTransport({ scene, url: SCENE.url(SCENE.transport.file), onProgress: t => { ui.pct.textContent = t; } }).catch(e => { console.error('transport layer unavailable', e); return null; });
    setupTransportUI();
  }
  await dataReady;
  ui.loading.classList.add('hide');
  // ?pose=campus|overhead jumps straight to that view (no intro); ?step=N picks the time step
  const qs = new URLSearchParams(location.search), pose = qs.get('pose');
  if (qs.has('cam')) {   // ?cam=px,py,pz,tx,ty,tz : fixed free camera over the site (debug / screenshots)
    const v = qs.get('cam').split(',').map(Number);
    ui.auto.checked = false; runCampus(); replayLayer?.stopShots(); flight = null; tour.active = false; if (replayLayer) replayLayer.playing = false;
    ui.stage.textContent = 'Free camera';
    if (qs.get('replay') === '0') replayLayer?.setVisible(false);
    if (qs.has('t') && replayLayer) { replayLayer.t = +qs.get('t'); replayLayer.update(replayLayer.t); }
    if (qs.has('t') && traffic) { traffic.t = +qs.get('t'); traffic.update(traffic.t); if (qs.get('play') === '0') traffic.playing = false; }
    camera.position.set(v[0], v[1], v[2]); controls.target.set(v[3], v[4], v[5]); camera.lookAt(controls.target);
    controls.enabled = true; section = 'free'; setSectionUI(); return;
  }
  if (pose === 'campus' && qs.get('fields') !== '1') {
    const p = campusPoseDeg(-135); camera.position.copy(p.pos); controls.target.copy(p.target); camera.lookAt(p.target);
    runCampus(); if (qs.has('t') && replayLayer) { replayLayer.t = +qs.get('t'); replayLayer.update(replayLayer.t); } if (qs.has('t') && traffic) { traffic.t = +qs.get('t'); traffic.update(traffic.t); }
    if (qs.has('shot')) { if (replayLayer) replayLayer.startShot(qs.get('shot')); else if (TOUR_SHOTS[qs.get('shot')]) startTour(qs.get('shot')); }
    if (qs.get('hold') === '1') { if (replayLayer) replayLayer.shotUntil = Infinity; tour.hold = true; }
    if (qs.get('play') === '0') { if (replayLayer) replayLayer.playing = false; if (traffic) traffic.playing = false; tour.paused = true; }
    setSectionUI(); return;
  }
  if (pose === 'overhead' || pose === 'campus') {
    section = 'fields'; replayLayer?.setVisible(false); setRateOptions('fields', 12); ui.step.step = 1;
    const p = pose === 'overhead' ? overheadPose() : campusPose(THREE.MathUtils.degToRad(-135));
    camera.position.copy(p.pos); controls.target.copy(p.target); camera.lookAt(p.target); controls.enabled = true;
    state.introDone = pose === 'overhead' || qs.get('fields') === '1';
    if (state.introDone) { ui.lGround.checked = false; ui.lTrees.checked = false; }
    if (qs.has('mode')) ui.mode.value = qs.get('mode');
    if (qs.has('phase') && has(qs.get('phase'))) state.phase = qs.get('phase');
    if (qs.has('solar')) ui.solarMode.value = qs.get('solar');       // ?solar=shadow|ghi
    if (qs.has('day')) ui.solarDate.value = qs.get('day');           // ?day=20260621|20261221
    if (qs.has('diurnal')) ui.diurnalMode.value = qs.get('diurnal'); // ?diurnal=ground|air0|air12
    solarPhaseSetup();
    if (state.introDone && seqMode() && (state.phase === 'flood' || state.phase === 'solar')) ui.lGround.checked = ui.lTrees.checked = true;
    applyLayers(); for (const L of Object.values(planes)) L.fade = L.target; updateFades(0);
    if (qs.has('step')) setStep(+qs.get('step')); else setStep(state.step);
    ui.stage.textContent = pose === 'overhead' ? 'Overhead view · ' + PHASE_ORDER.map(k => (TAB_NAME[k] ?? k).toLowerCase()).join(' / ') : (FOCUS.label ?? SCENE.title);
    return;
  }
  setTimeout(playIntro, 400);
}
boot();
window.viewer = { THREE, scene, camera, controls, model, state, renderer, planes, SCENE, LAYERS, PHASES, LG, get replay() { return replayLayer; }, get transport() { return transport; }, get traffic() { return traffic; }, get tile() { return tileGroup; }, get tileBatches() { return tileBatches; } };   // console / debugging access
