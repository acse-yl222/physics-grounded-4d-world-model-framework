/* SUMO traffic replay for scenes without the South Kensington demo package (scene.json `traffic`): cars from a one-hour
   SUMO run on the OSM road network and the recorded signal states, both already in the model frame
   (scenes/<id>/traffic/, built by scenes/white_city/tools/run_sumo.py + build_traffic.py). Reuses demo_rev02's instanced
   car layer, signal poles / heads and lane ribbons. Lanes whose OSM way the model builds as an elevated deck (meshes named
   "<road>_way-<id>_|_surface…" above ground) are lifted onto that deck by ray-casting the deck once at load, and the cars
   follow their lane's height. Synthetic demand and synthetic signal timings, not observed traffic. */
import * as THREE from 'three';
import { createActorLayer, carColorForId } from '../../agents/demo_rev02/actors/actor-layer.js';
import { createSignalLayerV2 } from '../../agents/demo_rev02/signals-v2.js';
import { addRoadSurfaces } from '../../agents/demo_rev02/stations.js';

const DEMO = new URL('../../agents/demo_rev02/', import.meta.url).href;
async function readJSON(url) { const r = await fetch(url); if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.json(); }
const REC = 6;   // int16 per vehicle record: id, x*10, z*10, yaw*10000, speed*100, lane index
function dotTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 32; const g = c.getContext('2d');
  g.beginPath(); g.arc(16, 16, 13, 0, Math.PI * 2); g.fillStyle = '#fff'; g.fill(); g.lineWidth = 3; g.strokeStyle = 'rgba(0,0,0,.55)'; g.stroke();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export async function createTraffic({ scene, base, elevated = [], onProgress = () => {} }) {
  onProgress('Traffic replay (SUMO)…');
  const manifest = await readJSON(base + 'replay.json');
  const group = new THREE.Group(); group.name = 'SUMO traffic'; scene.add(group);
  const [roads, layer, counts, buffer, tlsChanges] = await Promise.all([readJSON(base + 'roads.json'), readJSON(base + 'signal_layer.json'), readJSON(base + 'replay/frame_counts.json'),
    fetch(base + 'replay/traffic_flow.i16').then(r => { if (!r.ok) throw new Error('traffic_flow.i16 ' + r.status); return r.arrayBuffer(); }), readJSON(base + 'replay/tls_changes.json')]);
  // frame table from the per-second counts; signal rows expanded from the change points (one row per second, as signals-v2 expects)
  const frames = []; let acc = 0; for (let i = 0; i < counts.length; i++) { frames.push({ t_s: i, offset: acc * REC, count: counts[i] }); acc += counts[i]; }
  const tlsRows = []; { const ptr = {}, cur = {}; for (let t = 0; t < tlsChanges.seconds; t++) { for (const [k, rl] of Object.entries(tlsChanges.tls)) { ptr[k] ??= 0; while (ptr[k] < rl.length && rl[ptr[k]][0] <= t) { cur[k] = rl[ptr[k]][1]; ptr[k]++; } } tlsRows.push({ t, states: { ...cur } }); } }

  // ---- elevated decks: lanes on a way the model lifts follow the deck top (one ray per lane vertex, once)
  const decks = new Map();   // OSM way id -> meshes of its deck
  for (const m of elevated) { const id = /way-(\d+)/.exec(m.name)?.[1]; if (id) (decks.get(id) ?? decks.set(id, []).get(id)).push(m); }
  const ray = new THREE.Raycaster(), from = new THREE.Vector3(), down = new THREE.Vector3(0, -1, 0);
  let lifted = 0;
  for (const lane of roads.lanes) {
    const meshes = lane.way && decks.get(lane.way); lane.elevated = false;
    if (!meshes) continue;
    let hits = 0;
    for (const p of lane.world_xyz) {
      from.set(p[0], 80, p[2]); ray.set(from, down);
      const h = ray.intersectObjects(meshes, false)[0];
      if (h) { p[1] = h.point.y + 0.3; hits++; }
    }
    if (hits) { lane.elevated = true; lifted++; if (hits < lane.world_xyz.length) { // vertices the ray missed (deck ends): interpolate from their neighbours
        const pts = lane.world_xyz; for (let i = 0; i < pts.length; i++) if (pts[i][1] === 0.26) { const prev = pts.slice(0, i).reverse().find(q => q[1] !== 0.26), next = pts.slice(i + 1).find(q => q[1] !== 0.26); pts[i][1] = prev && next ? (prev[1] + next[1]) / 2 : (prev ?? next)[1]; } } }
  }
  // signal poles / heads on lifted lanes rise with the lane end
  const laneById = new Map(roads.lanes.map(l => [l.id, l]));
  for (const p of layer.poles) { const l = laneById.get(p.lane); if (l?.elevated) { const dy = l.world_xyz[l.world_xyz.length - 1][1] - 0.26; p.world_xyz[1] += dy; p.dy = dy; } }
  for (const h of layer.heads) { const dy = layer.poles[h.pole]?.dy; if (dy) h.world_xyz[1] += dy; }
  const roadMesh = addRoadSurfaces(group, roads);
  const ROAD_COLOR = roadMesh.material.color.clone();
  const signals = createSignalLayerV2(group, layer, tlsRows);
  signals.setPathsVisible(false);
  const binary = new Int16Array(buffer);
  const peak = Math.max(1, ...frames.map(f => f.count));
  const actors = await createActorLayer({ scene: group, carURL: DEMO + 'actors/sedan_4p5m.glb', uavURL: DEMO + 'assets/hexacopter_cargo.glb', carCapacity: Math.min(4000, peak + 50), uavCapacity: 1 });
  actors.uavs.group.visible = false;
  const duration = manifest.seconds;

  /** height of a lifted lane at the point nearest (x, z) */
  function laneHeight(lane, x, z) {
    const pts = lane.world_xyz; let best = Infinity, y = 0.26;
    for (let i = 0; i + 1 < pts.length; i++) {
      const a = pts[i], b = pts[i + 1], dx = b[0] - a[0], dz = b[2] - a[2], L2 = dx * dx + dz * dz || 1e-6;
      let t = ((x - a[0]) * dx + (z - a[2]) * dz) / L2; t = t < 0 ? 0 : t > 1 ? 1 : t;
      const px = a[0] + t * dx, pz = a[2] + t * dz, d = (px - x) * (px - x) + (pz - z) * (pz - z);
      if (d < best) { best = d; y = a[1] + t * (b[1] - a[1]); }
    }
    return y;
  }
  const frameMap = fr => { const m = new Map(); if (!fr) return m; const o = fr.offset; for (let i = 0; i < fr.count; i++) { const k = o + i * REC; m.set(binary[k], binary.subarray(k + 1, k + REC)); } return m; };
  let cur = new Map(), curIdx = -1;
  function carsAt(t) {
    const idx = Math.floor(t), a = frames[idx], b = frames[idx + 1], f = t - idx;
    if (!a) return [];
    if (curIdx !== idx) { cur = frameMap(a); curIdx = idx; }
    const nxt = f > 0 ? frameMap(b) : new Map(), out = [];
    for (const [id, v] of cur) {
      const w = nxt.get(id); let x = v[0] * 0.1, z = v[1] * 0.1, yaw = v[2] * 1e-4, sp = v[3] * 0.01;
      if (w) { x += (w[0] * 0.1 - x) * f; z += (w[1] * 0.1 - z) * f; let d = w[2] * 1e-4 - yaw; d = Math.atan2(Math.sin(d), Math.cos(d)); yaw += d * f; sp += (w[3] * 0.01 - sp) * f; }
      const lane = v[4] >= 0 ? roads.lanes[v[4]] : null;
      out.push({ nativeId: id, x, y: (lane?.elevated ? laneHeight(lane, x, z) : 0.26) + 0.015, z, headingRadians: yaw, speed: sp, color: carColorForId(id) });
    }
    out.sort((p, q) => p.nativeId - q.nativeId); out.forEach((r, i) => r.idIndex = i); return out;
  }

  // ---- overhead "traffic map": screen-space dots for cars (white moving / amber stopped) and signal heads (red / amber / green)
  const tex = dotTexture(), cap = Math.min(4000, peak + 50);
  const carDotGeom = new THREE.BufferGeometry();
  carDotGeom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(cap * 3), 3));
  carDotGeom.setAttribute('color', new THREE.BufferAttribute(new Float32Array(cap * 3), 3));
  const carDots = new THREE.Points(carDotGeom, new THREE.PointsMaterial({ size: 8, sizeAttenuation: false, map: tex, alphaTest: 0.3, vertexColors: true, depthTest: false, transparent: true }));
  carDots.frustumCulled = false; carDots.renderOrder = 21; carDots.visible = false; group.add(carDots);
  const heads = signals.heads;
  const sigDotGeom = new THREE.BufferGeometry();
  sigDotGeom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(Math.max(1, heads.length) * 3), 3));
  sigDotGeom.setAttribute('color', new THREE.BufferAttribute(new Float32Array(Math.max(1, heads.length) * 3), 3));
  heads.forEach((h, i) => sigDotGeom.attributes.position.setXYZ(i, h.world_xyz[0], h.world_xyz[1] + 1, h.world_xyz[2]));
  sigDotGeom.setDrawRange(0, heads.length);
  const sigDots = new THREE.Points(sigDotGeom, new THREE.PointsMaterial({ size: 10, sizeAttenuation: false, map: tex, alphaTest: 0.3, vertexColors: true, depthTest: false, transparent: true }));
  sigDots.frustumCulled = false; sigDots.renderOrder = 22; sigDots.visible = false; group.add(sigDots);
  const SIG = { r: new THREE.Color('#ff2a2a'), y: new THREE.Color('#ffb400'), g: new THREE.Color('#22e07a'), off: new THREE.Color('#6c7a82') };
  const WHITE = new THREE.Color('#ffffff'), AMBER = new THREE.Color('#ffb400');
  let sigSecond = -1;
  function updateDots(t, cars) {
    if (!carDots.visible) return;
    const p = carDotGeom.attributes.position, c = carDotGeom.attributes.color;
    cars.forEach((r, i) => { p.setXYZ(i, r.x, r.y + 2, r.z); const col = r.speed > 0.1 ? WHITE : AMBER; c.setXYZ(i, col.r, col.g, col.b); });
    carDotGeom.setDrawRange(0, cars.length); p.needsUpdate = true; c.needsUpdate = true;
    const second = Math.floor(t); if (second === sigSecond) return; sigSecond = second;
    const sc = sigDotGeom.attributes.color;
    heads.forEach((h, i) => { const v = (signals.stateAt(t, h) || '').toLowerCase(); const col = SIG[v] ?? SIG.off; sc.setXYZ(i, col.r, col.g, col.b); });
    sc.needsUpdate = true;
  }

  const T = {
    group, manifest, roadMesh, signals, actors, duration, t: 0, playing: true, speed: 1, count: 0, moving: 0, lifted,
    update(t) { const cars = carsAt(t); actors.updateCars(cars); signals.update(t); updateDots(t, cars); T.count = cars.length; T.moving = cars.filter(c => c.speed > 0.1).length; },
    tick(now, dt) { if (T.playing) { T.t += dt * T.speed; if (T.t >= duration - 1) T.t = 0; } T.update(T.t); },
    setVisible(v) { group.visible = v; },
    applyLayers({ cars = true, signals: sig = true, roads: rd = true, paths = false, map = false } = {}) {
      actors.cars.group.visible = cars; signals.setVisible(sig); roadMesh.visible = rd; signals.setPathsVisible(paths);
      carDots.visible = map; sigDots.visible = map && heads.length > 0; sigSecond = -1; T.highlightRoads(map);
    },
    highlightRoads(on) { roadMesh.material.color.copy(on ? new THREE.Color('#3d8be6') : ROAD_COLOR); roadMesh.material.emissive.set(on ? '#123a6e' : '#000000'); roadMesh.material.needsUpdate = true; },
    get stats() { return `SUMO replay · ${T.count} cars (${T.moving} moving) · ${layer.counts.tls} signalled junctions, ${layer.counts.heads} heads · ${roads.counts.lanes} lanes (${lifted} on elevated decks) · peak ${manifest.vehicles_peak} vehicles`; },
    get info() { return manifest.claim; },
  };
  T.update(0);
  return T;
}
