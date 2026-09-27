// Traffic + UAV replay layer for the integrated page. Reuses demo_rev02's actor / signal / station /
// parking / follow-camera modules and data files unchanged (SUMO traffic sample, NVMF UAV schedule).
import * as THREE from 'three';
import { createActorLayer, sumoHeadingToWorldYaw, carColorForId } from '../../agents/demo_rev02/actors/actor-layer.js';
import { addStations, addRoadSurfaces } from '../../agents/demo_rev02/stations.js';
import { createSignalLayerV2 } from '../../agents/demo_rev02/signals-v2.js';
import { allocateHubParking } from '../../agents/demo_rev02/parking.js';
import { createFollowCamera } from '../../agents/demo_rev02/follow-camera.js';
import { createBirdLayer } from '../../agents/demo_rev02/birds.js';

export const DEMO = new URL('../../agents/demo_rev02/', import.meta.url).href;
const SUMO_OX = 2912.594719173, SUMO_OZ = 1704.705026026;   // SUMO -> world: X = x - OX, Z = OZ - y
const CAR_STOPPED = 0.1;
const CAMPUS_BOX = { min: [514, -9], max: [897, 324] };      // Imperial College buildings (X, Z)
const JUNCTION_MAX_M = 165;                                   // junctions at most this far from the campus box (its ring roads)
function distToCampusBox(x, z) { return Math.hypot(Math.max(CAMPUS_BOX.min[0] - x, 0, x - CAMPUS_BOX.max[0]), Math.max(CAMPUS_BOX.min[1] - z, 0, z - CAMPUS_BOX.max[1])); }
async function readJSON(url, optional = false) { const r = await fetch(url); if (!r.ok) { if (optional && r.status === 404) return null; throw new Error(`${url}: ${r.status}`); } return r.json(); }
export const timeString = s => { const t = Math.max(0, Math.floor(s)); return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`; };

/** Same display filter as the demo viewer: hide the GLB's own animated traffic / prediction / bird layers,
 *  show aerial-photo parked cars only where they do not sit on a drivable lane. */
export async function applyCityFilter(cityScene) {
  const staticFilter = await readJSON(DEMO + 'data/static-vehicle-filter.json', true);
  const sanitise = n => n.replace(/\s/g, '_').replace(/[\[\]\.:\/]/g, '');
  const parkedShow = new Set((staticFilter?.aerial_vehicles ?? []).filter(a => a.show).map(a => sanitise(a.name)));
  cityScene.traverse(o => {
    if (['traffic_vehicle', 'traffic_prediction', 'bird'].includes(o.userData.layer)) o.visible = false;
    if (o.name.startsWith('AERIAL-VEHICLE')) o.visible = parkedShow.has(o.name) || parkedShow.has(o.name.replace(/_\d+$/, ''));
  });
}

export const SHOTS = {
  overview: { label: 'Imperial College campus · traffic and UAV overview', dur: 11, speed: 2 },
  junction: { label: 'Busiest signalised junction around the campus', dur: 14, speed: 1 },
  traffic: { label: 'Traffic · overhead (drivable lanes, cars, signals)', dur: 14, speed: 2 },
  uavs: { label: 'UAVs · wide view (campus, nearby hubs and stations)', dur: 14, speed: 2 },
  birds: { label: 'Birds · tracking the flock (Akira flock model replay)', dur: 16, speed: 1 },
};
export const SHOT_ORDER = ['overview', 'junction', 'traffic', 'uavs', 'birds'];
const BIRD_STATES = ['foraging', 'transit', 'murmuration', 'descending', 'roosting'];
const UAV_MACRO_SCALE = 4;   // cargo UAVs are 1.3 m wide; enlarged only in the wide shot so they stay visible

export async function createReplay({ scene, camera, controls, campusCentre, campusPose, flyTo, onProgress = () => {} }) {
  const group = new THREE.Group(); group.name = 'Replay layers'; scene.add(group);
  const stationById = new Map(), routeByKey = new Map(), parkingById = new Map(), carIdentities = new Map();
  const nearStations = new Set();
  let actors, stationLayer, signalLayer, roadMesh, hubParking, replay = null, traffic = null, stations = [], parking = [], bayLibrary = null, birdLayer = null;

  onProgress('Reading stations and routes…');
  let routes;
  [stations, parking, routes, bayLibrary] = await Promise.all([readJSON(DEMO + 'data/stations.json'), readJSON(DEMO + 'data/parking.json'), readJSON(DEMO + 'data/routes.json'), readJSON(DEMO + 'data/hub-bays.json')]);
  parking = parking.parking; stations.forEach(s => stationById.set(s.station_id, s)); parking.forEach(p => parkingById.set(p.uav_id, p)); routes.routes.forEach(r => routeByKey.set(r.from_station + '-' + r.to_station, r));
  for (const s of stations) if (Math.hypot(s.x_m - campusCentre.x, s.z_m - campusCentre.z) < 650) nearStations.add(s.station_id);

  onProgress('Cars, UAVs, stations, lanes…');
  actors = await createActorLayer({ scene: group, carCapacity: 1800, uavCapacity: 300, uavURL: DEMO + 'assets/hexacopter_cargo.glb' });
  stationLayer = addStations(group, stations, parking);
  // screen-space dots for airborne UAVs (the demo does the same for far views)
  const markerGeom = new THREE.BufferGeometry();
  markerGeom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(300 * 3), 3));
  markerGeom.setAttribute('color', new THREE.BufferAttribute(new Float32Array(300 * 3), 3));
  const dot = document.createElement('canvas'); dot.width = dot.height = 32;
  { const g = dot.getContext('2d'); g.beginPath(); g.arc(16, 16, 13, 0, Math.PI * 2); g.fillStyle = '#fff'; g.fill(); g.lineWidth = 4; g.strokeStyle = 'rgba(0,0,0,0.85)'; g.stroke(); }
  const dotTex = new THREE.CanvasTexture(dot); dotTex.colorSpace = THREE.SRGBColorSpace;
  const markers = new THREE.Points(markerGeom, new THREE.PointsMaterial({ size: 13, sizeAttenuation: false, map: dotTex, alphaTest: 0.3, vertexColors: true, depthTest: false, transparent: true }));
  markers.frustumCulled = false; markers.renderOrder = 20; markers.visible = false; group.add(markers);
  // flight corridors (the certified route centrelines) - shown only in the wide UAV shot
  const corridorPos = [];
  for (const r of routes.routes) for (let i = 1; i < r.points_m.length; i++) corridorPos.push(...r.points_m[i - 1], ...r.points_m[i]);
  const corridorGeom = new THREE.BufferGeometry(); corridorGeom.setAttribute('position', new THREE.Float32BufferAttribute(corridorPos, 3));
  const corridors = new THREE.LineSegments(corridorGeom, new THREE.LineBasicMaterial({ color: 0xffb347, transparent: true, opacity: 0.35, depthWrite: false }));
  corridors.visible = false; corridors.renderOrder = 19; group.add(corridors);
  let uavScale = 1;
  function setUavScale(k) { if (k === uavScale) return; for (const m of actors.uavs.meshes) m.geometry.scale(k / uavScale, k / uavScale, k / uavScale); uavScale = k; }
  roadMesh = addRoadSurfaces(group, await readJSON(DEMO + 'data/roads.json'));
  // birds: Akira's flock model (demo_rev02 v3 wrapper), same clock as the traffic; low-poly pigeons, instanced.
  // data/birds_southken/ = our run focused on South Kensington station (roost on the station roof); data/birds/ = the colleague's campus run.
  onProgress('Birds (flock model replay)…');
  try {
    let birdDir = DEMO + 'data/birds_southken/', manifest = await readJSON(birdDir + 'bird_replay.json', true);
    if (!manifest) { birdDir = DEMO + 'data/birds/'; manifest = await readJSON(birdDir + 'bird_replay.json', true); }
    if (manifest) {
      const [buf, st] = await Promise.all([fetch(birdDir + 'bird_replay.f32').then(r => { if (!r.ok) throw new Error('bird_replay.f32 ' + r.status); return r.arrayBuffer(); }), fetch(birdDir + 'bird_states.u8').then(r => { if (!r.ok) throw new Error('bird_states.u8 ' + r.status); return r.arrayBuffer(); })]);
      const buffer = new Float32Array(buf), states = new Uint8Array(st);
      if (buffer.length !== manifest.frames * manifest.birds * manifest.record.length || states.length !== manifest.frames * manifest.birds) throw new Error('bird replay size does not match its manifest');
      birdLayer = await createBirdLayer({ scene: group, manifest, buffer, states, modelURL: DEMO + 'actors/pigeon.glb' });
      console.log('bird layer:', birdLayer.stats);
    }
  } catch (e) { console.error('bird layer failed', e); birdLayer = null; }
  const schedule = await readJSON(DEMO + 'data/schedule.json');

  // ---- UAV geometry along the certified routes (ported from the demo viewer, unchanged semantics)
  function routePoints(from, to, owner, segment) {
    const key = Math.min(from, to) + '-' + Math.max(from, to); const route = routeByKey.get(key); if (!route) throw new Error(`Missing flight path ${from}→${to}`);
    let points = route.points_m.map(p => p.slice()); if (from > to) points.reverse();
    const h = points[1][1];
    if (stationById.get(from).role === 'hub') { const c = stationById.get(from), base = parkingById.get(owner), off = segment?._departureOffset ?? base.offset_from_station_m; const bay = [c.x_m + off[0], c.y_m, c.z_m + off[2]]; points = [bay, [bay[0], h, bay[2]], ...points.slice(1)]; }
    if (stationById.get(to).role === 'hub') { const c = stationById.get(to), base = parkingById.get(owner), off = segment?._arrivalOffset ?? base.offset_from_station_m; const bay = [c.x_m + off[0], c.y_m, c.z_m + off[2]]; points = [...points.slice(0, -1), [bay[0], h, bay[2]], bay]; }
    const lengths = []; let total = 0; for (let i = 1; i < points.length; i++) { total += Math.hypot(...points[i].map((x, k) => x - points[i - 1][k])); lengths.push(total); }
    return { points, lengths, total };
  }
  function pointAlong(path, fraction) {
    const d = Math.min(1, Math.max(0, fraction)) * path.total; let i = path.lengths.findIndex(v => v >= d); if (i < 0) i = path.points.length - 2;
    const prev = i ? path.lengths[i - 1] : 0, len = path.lengths[i] - prev, r = len > 1e-8 ? (d - prev) / len : 0;
    const a = path.points[i], b = path.points[i + 1];
    return { x: a[0] + (b[0] - a[0]) * r, y: a[1] + (b[1] - a[1]) * r, z: a[2] + (b[2] - a[2]) * r, headingRadians: Math.atan2(b[0] - a[0], b[2] - a[2]) };
  }
  function stationaryPose(stationId, owner, t = 0) {
    const s = stationById.get(stationId), p = { x: s.x_m, y: s.y_m, z: s.z_m, headingRadians: 0 };
    if (s.role === 'hub') { const off = hubParking?.offset(owner, stationId, t) ?? parkingById.get(owner).offset_from_station_m; p.x += off[0]; p.z += off[2]; }
    return p;
  }
  hubParking = allocateHubParking(schedule, stations, parking, bayLibrary);
  for (const u of schedule.uavs) for (const seg of u.segments) if (seg.from_station !== seg.to_station) seg._path = routePoints(seg.from_station, seg.to_station, u.id, seg);
  replay = schedule;
  function uavStates(t) {
    return replay.uavs.map(u => {
      const seg = u.segments.find(s => t >= s.t0_s && t < s.t1_s) ?? u.segments[u.segments.length - 1];
      if (!seg) return { idIndex: u.id, ...stationaryPose(u.birth_station, u.id), activity: 'HOLD', airborne: false, station: u.birth_station, opacity: 1 };
      const f = Math.min(1, Math.max(0, (t - seg.t0_s) / Math.max(1e-8, seg.t1_s - seg.t0_s))), airborne = !!seg._path;
      const pose = airborne ? pointAlong(seg._path, f) : stationaryPose(seg.from_station, u.id, t);
      const swap = seg.kind.includes('SWAP');
      const dockedHidden = !airborne && hubParking.isReturnedStay(u.id, seg.from_station, t);
      const fade = Math.min(1.2, (seg.t1_s - seg.t0_s) / 2);
      let opacity = dockedHidden ? 0 : 1;
      if (airborne && fade > 0) { if (seg._fadeIntoHub) opacity = Math.min(opacity, Math.max(0, (seg.t1_s - t) / fade)); if (seg._fadeOutOfHub) opacity = Math.min(opacity, Math.max(0, (t - seg.t0_s) / fade)); }
      return { idIndex: u.id, ...pose, activity: seg.display_kind ?? seg.kind, order_id: seg.order_id, airborne, to: airborne ? seg.to_station : null, from: seg.from_station,
        station: airborne ? null : seg.from_station, color: swap ? '#2563eb' : (seg.payload0 ? '#f2924b' : '#ffffff'), opacity, visible: !dockedHidden };
    });
  }
  /** Replay clock -> traffic-sample time. The UAV schedule and the birds cover the full hour; the traffic files in the
   *  repository are a 300 s sample, so the cars and signals loop inside that window (t mod window) while the clock goes on. */
  function trafficTime(t) {
    if (!traffic) return t;
    const span = traffic.lastTime - traffic.firstTime; if (span <= 0 || (t >= traffic.firstTime && t <= traffic.lastTime)) return t;
    return traffic.firstTime + ((((t - traffic.firstTime) % span) + span) % span);
  }
  function carStates(t) {
    if (!traffic) return [];
    t = trafficTime(t);
    const idx = Math.floor(t) - traffic.firstTime, a = traffic.frames[idx], b = traffic.frames[idx + 1], f = t - Math.floor(t);
    if (!a) return [];
    const frameMap = fr => { const m = new Map(); if (!fr) return m; const o = fr.offset_bytes / 4; for (let i = 0; i < fr.count; i++) { const k = o + i * 5; m.set(traffic.binary[k], traffic.binary.subarray(k + 1, k + 5)); } return m; };
    const cur = frameMap(a), nxt = f > 0 ? frameMap(b) : new Map(), out = [];
    for (const [id, v] of cur) {
      const w = nxt.get(id); let x = v[0], y = v[1], ang = v[2], sp = v[3];
      if (w) { x += (w[0] - x) * f; y += (w[1] - y) * f; const d = ((w[2] - ang + 540) % 360) - 180; ang += d * f; sp += (w[3] - sp) * f; }
      out.push({ nativeId: id, x: x - SUMO_OX, y: 0.275, z: SUMO_OZ - y, headingRadians: sumoHeadingToWorldYaw(ang * Math.PI / 180), speed: sp, color: carColorForId(id) });
    }
    out.sort((p, q) => p.nativeId - q.nativeId); out.forEach((r, i) => r.idIndex = i); return out;
  }

  onProgress('Traffic replay and signals…');
  const manifest = await readJSON(DEMO + 'data/traffic/current_replay.json', true);
  if (manifest) {
    const base = DEMO + 'data/traffic/replay/';
    const [frames, buffer] = await Promise.all([readJSON(base + 'frames_index.json'), fetch(base + 'traffic_flow.f32').then(r => r.arrayBuffer())]);
    traffic = { frames: Array.isArray(frames) ? frames : frames.frames, binary: new Float32Array(buffer) };
    traffic.firstTime = traffic.frames[0].t_s; traffic.lastTime = traffic.frames[traffic.frames.length - 1].t_s;
    const identities = await readJSON(base + 'actors.json'); for (const [k, v] of Object.entries(identities)) carIdentities.set(Number(k), v);
    const [layer, tlsText] = await Promise.all([readJSON(DEMO + 'data/traffic/signal_layer_v2.json'), fetch(base + 'tls_frames.jsonl').then(r => r.text())]);
    signalLayer = createSignalLayerV2(group, layer, tlsText.trim().split('\n').filter(Boolean).map(l => JSON.parse(l)));
  }
  // ---- overhead "traffic map": screen-space dots for cars and signal heads, highlighted lane ribbons
  const ROAD_COLOR = roadMesh.material.color.clone();
  const carDotGeom = new THREE.BufferGeometry();
  carDotGeom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(1800 * 3), 3));
  carDotGeom.setAttribute('color', new THREE.BufferAttribute(new Float32Array(1800 * 3), 3));
  const carDots = new THREE.Points(carDotGeom, new THREE.PointsMaterial({ size: 9, sizeAttenuation: false, map: dotTex, alphaTest: 0.3, vertexColors: true, depthTest: false, transparent: true }));
  carDots.frustumCulled = false; carDots.renderOrder = 21; carDots.visible = false; group.add(carDots);
  const heads = signalLayer?.heads ?? [];
  const sigDotGeom = new THREE.BufferGeometry();
  sigDotGeom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(Math.max(1, heads.length) * 3), 3));
  sigDotGeom.setAttribute('color', new THREE.BufferAttribute(new Float32Array(Math.max(1, heads.length) * 3), 3));
  heads.forEach((h, i) => sigDotGeom.attributes.position.setXYZ(i, h.world_xyz[0], h.world_xyz[1] + 1, h.world_xyz[2]));
  sigDotGeom.setDrawRange(0, heads.length);
  const sigDots = new THREE.Points(sigDotGeom, new THREE.PointsMaterial({ size: 11, sizeAttenuation: false, map: dotTex, alphaTest: 0.3, vertexColors: true, depthTest: false, transparent: true }));
  sigDots.frustumCulled = false; sigDots.renderOrder = 22; sigDots.visible = false; group.add(sigDots);
  const SIG = { r: new THREE.Color('#ff2a2a'), y: new THREE.Color('#ffb400'), g: new THREE.Color('#22e07a'), off: new THREE.Color('#6c7a82') };
  let sigSecond = -1;
  function updateSignalDots(t) {
    const second = Math.floor(t); if (second === sigSecond || !signalLayer) return; sigSecond = second;
    const c = sigDotGeom.attributes.color;
    heads.forEach((h, i) => { const v = (signalLayer.stateAt(t, h) || '').toLowerCase(); const col = SIG[v] ?? SIG.off; c.setXYZ(i, col.r, col.g, col.b); });
    c.needsUpdate = true;
  }
  let mapManual = false, mapShot = false;
  function applyTrafficMap() {
    const on = mapManual || mapShot;
    carDots.visible = on; sigDots.visible = on && heads.length > 0;
    roadMesh.material.color.copy(on ? new THREE.Color('#3d8be6') : ROAD_COLOR);
    roadMesh.material.emissive.set(on ? '#123a6e' : '#000000');
    roadMesh.material.needsUpdate = true;
  }

  // ---- state
  const R = {
    group, traffic, duration: replay.metadata.duration_s, t: traffic ? Math.min(traffic.lastTime, traffic.firstTime + 30) : 0, playing: false, speed: 1,
    cars: [], uavs: [], lastDraw: -Infinity, followKind: null, followId: null, shot: null, shotUntil: 0, cycleDone: false, info: '', label: '', orbit: null,
    stats: '',
  };
  const followCamera = createFollowCamera({ camera, controls });
  
  function update(t) {
    R.uavs = uavStates(t); R.cars = carStates(t);
    const seen = new Set(), ground = new Map();
    for (const u of R.uavs) if (!u.airborne) ground.set(u.station, (ground.get(u.station) ?? 0) + 1);
    stationLayer.setGroundCounts(ground);
    const displayed = R.uavs.map(u => {
      if (u.airborne || stationById.get(u.station)?.role === 'hub') return u;
      const show = (R.followKind === 'uav' && u.idIndex === R.followId) || !seen.has(u.station); if (show) seen.add(u.station); return { ...u, visible: show };
    });
    actors.updateUavs(displayed); actors.updateCars(R.cars); signalLayer?.update(trafficTime(t));
    const birds = birdLayer ? birdLayer.update(t) : null;
    let n = 0; const mp = markerGeom.attributes.position.array, mc = markerGeom.attributes.color.array, col = new THREE.Color();
    for (const u of R.uavs) { if (!u.airborne || u.opacity < 0.3) continue; mp[n * 3] = u.x; mp[n * 3 + 1] = u.y + 3; mp[n * 3 + 2] = u.z; col.set(u.color === '#f2924b' ? '#ff7a1a' : u.color === '#2563eb' ? '#4f8cff' : '#ffd23c'); mc[n * 3] = col.r; mc[n * 3 + 1] = col.g; mc[n * 3 + 2] = col.b; n++; }
    markerGeom.setDrawRange(0, n); markerGeom.attributes.position.needsUpdate = true; markerGeom.attributes.color.needsUpdate = true;
    if (carDots.visible) {
      const cp = carDotGeom.attributes.position.array, cc = carDotGeom.attributes.color.array; let m = 0;
      for (const c of R.cars) { if (m >= 1800) break; cp[m * 3] = c.x; cp[m * 3 + 1] = c.y + 2; cp[m * 3 + 2] = c.z; const stopped = c.speed <= CAR_STOPPED; cc[m * 3] = 1; cc[m * 3 + 1] = stopped ? 0.62 : 1; cc[m * 3 + 2] = stopped ? 0.1 : 1; m++; }
      carDotGeom.setDrawRange(0, m); carDotGeom.attributes.position.needsUpdate = true; carDotGeom.attributes.color.needsUpdate = true;
    }
    if (sigDots.visible) updateSignalDots(trafficTime(t));
    const moving = R.cars.filter(c => c.speed > CAR_STOPPED).length;
    const near = R.cars.filter(c => Math.hypot(c.x - campusCentre.x, c.z - campusCentre.z) < 450).length;
    const air = R.uavs.filter(u => u.airborne).length;
    const done = replay.deliveries.filter(d => d.dropoff_s <= t).length;
    R.stats = `Cars on the network ${R.cars.length} (${moving} moving) · ${near} within 450 m of campus\nUAVs airborne ${air} · delivered ${done}/600` + (traffic && traffic.lastTime < 3600 ? `\nTraffic: ${traffic.lastTime - traffic.firstTime} s sample looping (at ${timeString(trafficTime(t))}); full-hour files not placed in demo_rev02` : '');
    if (birds && birds.present) { const names = ['foraging', 'transit', 'murmuration', 'descending', 'roosting']; R.stats += `\nBirds ${birds.present} (flock model replay): ` + birds.stateCounts.map((n, k) => n ? `${n} ${names[k]}` : '').filter(Boolean).join(' · '); }
  }
  function junctionCandidates(maxDist = JUNCTION_MAX_M) {
    const byTls = new Map();
    for (const m of signalLayer?.movements ?? []) { if (!byTls.has(m.tls_id)) byTls.set(m.tls_id, []); byTls.get(m.tls_id).push(m); }
    const list = [];
    for (const [tls, ms] of byTls) {
      const cx = ms.reduce((s, m) => s + m.world_stop_point_xyz[0], 0) / ms.length, cz = ms.reduce((s, m) => s + m.world_stop_point_xyz[2], 0) / ms.length;
      const d = distToCampusBox(cx, cz); if (d > maxDist) continue;
      const cars = R.cars.filter(c => Math.hypot(c.x - cx, c.z - cz) < 70), moving = cars.filter(c => c.speed > CAR_STOPPED).length;
      list.push({ tls, ms, cx, cz, d, cars: cars.length, moving, score: cars.length + 2 * moving + ms.length });
    }
    if (!list.length && maxDist < 700) return junctionCandidates(700);   // fallback: widen the search
    return list.sort((a, b) => b.score - a.score);
  }
  function orbitPose(o, k) {
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    const az = THREE.MathUtils.degToRad(o.az0 + (o.az1 - o.az0) * e), el = THREE.MathUtils.degToRad(o.el0 + (o.el1 - o.el0) * e), d = o.d0 + (o.d1 - o.d0) * e;
    const ty = o.y ?? campusCentre.y;
    return { pos: new THREE.Vector3(campusCentre.x + d * Math.cos(el) * Math.sin(az), ty + d * Math.sin(el), campusCentre.z + d * Math.cos(el) * Math.cos(az)), target: new THREE.Vector3(campusCentre.x, ty, campusCentre.z) };
  }
  function cancelCamera() {
    if (R.orbit) { R.orbit = null; controls.enabled = true; }
    if (birdTrack.target === 'flock' && birdTrack.mode === 'auto') { birdTrack.mode = 'free'; controls.enabled = true; }   // user drag: keep following, stop rotating
  }

  // ---- bird tracker: follow the flock centroid (auto-rotating or free orbit) or one bird (behind / free orbit)
  const birdTrack = { target: null, mode: 'auto', az: -120, centroid: null, flying: false };
  /** Centroid, spread, mean speed and state counts of the birds present at the current time. */
  function flockSummary() {
    if (!birdLayer) return null;
    let x = 0, y = 0, z = 0, sp = 0, n = 0; const counts = [0, 0, 0, 0, 0], pts = [];
    for (let i = 0; i < birdLayer.stats.birds; i++) { const b = birdLayer.getState(i); if (!b || !b.visible) continue; x += b.x; y += b.y; z += b.z; sp += b.speed; counts[b.state] = (counts[b.state] ?? 0) + 1; n++; pts.push(b); }
    if (!n) return null;
    x /= n; y /= n; z /= n; let radius = 0; for (const b of pts) radius = Math.max(radius, Math.hypot(b.x - x, b.z - z));
    return { x, y, z, n, radius, speed: sp / n, counts };
  }
  function flockPose(f, azDeg) {
    const d = Math.min(180, Math.max(45, 2.2 * f.radius + 30)), el = THREE.MathUtils.degToRad(18), az = THREE.MathUtils.degToRad(azDeg);
    return { pos: new THREE.Vector3(f.x + d * Math.cos(el) * Math.sin(az), f.y + d * Math.sin(el), f.z + d * Math.cos(el) * Math.cos(az)), target: new THREE.Vector3(f.x, f.y, f.z) };
  }
  const stateText = counts => counts.map((n, k) => n ? `${n} ${BIRD_STATES[k]}` : '').filter(Boolean).join(' · ');
  /** target: 'flock' | bird index | null. mode: 'auto' (rotate around the flock / behind the bird) | 'free' (orbit controls, camera moves with the target). */
  function trackBirds(target, mode = 'auto') {
    clearFollow(); if (R.orbit) { R.orbit = null; } birdTrack.target = null; birdTrack.flying = false; controls.enabled = true;
    if (target === null || target === undefined || !birdLayer) { R.birdInfo = ''; return; }
    birdTrack.mode = mode;
    if (target === 'flock') {
      const f = flockSummary(); if (!f) { R.birdInfo = 'No birds present at this time'; return; }
      birdTrack.target = 'flock'; birdTrack.az = -120; birdTrack.centroid = new THREE.Vector3(f.x, f.y, f.z); birdTrack.flying = true;
      flyTo(flockPose(f, birdTrack.az), 2200, () => { birdTrack.flying = false; if (birdTrack.target === 'flock' && birdTrack.mode === 'auto') controls.enabled = false; });
    } else {
      const b = birdLayer.getState(target); if (!b) return;
      birdTrack.target = target; followCamera.select({ kind: 'bird', id: target }, b); followCamera.setMode(mode === 'free' ? 'orbit' : 'behind');
      R.followKind = 'bird'; R.followId = target;
    }
  }
  function updateBirdTracking(dt) {
    if (birdTrack.target === null || !birdLayer) return;
    if (birdTrack.target === 'flock') {
      const f = flockSummary(); if (!f) { R.birdInfo = 'No birds present at this time'; return; }
      const c = birdTrack.centroid, a = 1 - Math.exp(-3 * dt), prev = c.clone();
      c.x += (f.x - c.x) * a; c.y += (f.y - c.y) * a; c.z += (f.z - c.z) * a;
      if (!birdTrack.flying) {
        if (birdTrack.mode === 'auto') { birdTrack.az += 6 * dt; const p = flockPose({ ...f, x: c.x, y: c.y, z: c.z }, birdTrack.az); camera.position.lerp(p.pos, a); controls.target.copy(p.target); camera.lookAt(controls.target); }
        else { const d = c.clone().sub(prev); camera.position.add(d); controls.target.add(d); }
      }
      R.birdInfo = `Flock · ${f.n} birds · centroid ${f.y.toFixed(0)} m above ground · spread ${f.radius.toFixed(0)} m · mean speed ${f.speed.toFixed(1)} m/s
${stateText(f.counts)}`;
    } else {
      const b = birdLayer.getState(birdTrack.target);
      followCamera.update(b && b.visible ? b : null, dt);
      R.birdInfo = b ? `Bird ${String(birdTrack.target + 1).padStart(3, '0')} · ${b.stateName} · altitude ${b.y.toFixed(1)} m · ${b.speed.toFixed(1)} m/s · heading ${((THREE.MathUtils.radToDeg(b.headingRadians) % 360 + 360) % 360).toFixed(0)}°` + (b.visible ? '' : ' · not present at this time') : '';
    }
    if (R.shot === 'birds') R.info = R.birdInfo;
  }
  const activityLabel = k => ({ RETURN_TO_HUB: 'returning to hub', INFLIGHT_TO_C: 'flying to collection', INFLIGHT_C_TO_D: 'delivering', INFLIGHT_TO_HUB: 'returning to hub' }[k] ?? k);
  function clearFollow() { followCamera.clear(); R.followKind = null; R.followId = null; }
  function startShot(id) {
    const shot = SHOTS[id]; R.shot = id; R.shotUntil = performance.now() + shot.dur * 1000; R.cycleDone = false;
    R.label = shot.label; R.info = ''; R.speed = shot.speed;
    clearFollow(); cancelCamera(); trackBirds(null); setUavScale(1); markers.visible = false; corridors.visible = false; mapShot = false; applyTrafficMap();
    if (id === 'birds') {
      if (!birdLayer) { R.info = 'No bird replay in agents/demo_rev02/data/birds'; return; }
      trackBirds('flock', 'auto');
      const f = flockSummary(); R.info = f ? `Flock · ${f.n} birds · ${stateText(f.counts)}` : 'No birds present at this time';
    } else if (id === 'overview') {
      // sweep around the campus while descending, staying close to the Imperial buildings
      const orbit = { az0: -160, az1: -95, el0: 36, el1: 22, d0: 520, d1: 330 };
      const start = orbitPose(orbit, 0), lead = 2200;
      const begin = () => { R.orbit = { ...orbit, t0: performance.now(), dur: shot.dur * 1000 - lead - 100 }; controls.enabled = false; };
      if (camera.position.distanceTo(start.pos) > 40) flyTo(start, lead, begin); else begin();
      R.info = 'Cars: SUMO replay · UAVs: NVMF schedule replay · signals: recorded states';
    } else if (id === 'junction') {
      const j = junctionCandidates()[0];
      if (!j) { R.info = 'No signal data'; return; }
      const m = j.ms.reduce((best, mm) => { const n = R.cars.filter(c => Math.hypot(c.x - mm.world_stop_point_xyz[0], c.z - mm.world_stop_point_xyz[2]) < 40).length; return n > best.n ? { n, m: mm } : best; }, { n: -1, m: j.ms[0] }).m;
      const fwd = m.world_forward_xz ?? [1, 0];
      flyTo({ pos: new THREE.Vector3(j.cx - fwd[0] * 62, 30, j.cz - fwd[1] * 62), target: new THREE.Vector3(j.cx, 2, j.cz) }, 2600);
      const dx = j.cx - campusCentre.x, dz = j.cz - campusCentre.z, dir = Math.abs(dx) > Math.abs(dz) ? (dx > 0 ? 'east' : 'west') : (dz > 0 ? 'south' : 'north');
      R.info = `Junction on the ${dir} side of campus (${j.d.toFixed(0)} m from the buildings) · ${j.ms.length} controlled movements · ${j.cars} cars within 70 m (${j.moving} moving)`;
    } else if (id === 'traffic') {
      // map view over the campus ring roads: straight down and north up (camera due south of the centre), so it reads like a
      // map from any seat; the only motion is a slow zoom from the whole ring-road area towards the campus
      mapShot = true; applyTrafficMap(); sigSecond = -1; update(R.t);
      const orbit = { az0: 0, az1: 0, el0: 88, el1: 88, d0: 1350, d1: 1050, y: 0 };
      const start = orbitPose(orbit, 0), lead = 2600;
      const begin = () => { R.orbit = { ...orbit, t0: performance.now(), dur: shot.dur * 1000 - lead - 100 }; controls.enabled = false; };
      if (camera.position.distanceTo(start.pos) > 40) flyTo(start, lead, begin); else begin();
      const moving = R.cars.filter(c => c.speed > CAR_STOPPED).length;
      R.info = `${R.cars.length} cars on the network (${moving} moving) · white dots = moving, amber dots = stopped · signal heads shown as red / amber / green dots · blue ribbons = drivable lanes of the SUMO network`;
    } else if (id === 'uavs') {
      // wide, high sweep over the campus: the nearby hubs (H2 north, H3 south) and rooftop stations come into view
      setUavScale(UAV_MACRO_SCALE); markers.visible = true; corridors.visible = true;
      const orbit = { az0: -140, az1: -100, el0: 52, el1: 44, d0: 1000, d1: 820, y: 30 };
      const start = orbitPose(orbit, 0), lead = 2600;
      const begin = () => { R.orbit = { ...orbit, t0: performance.now(), dur: shot.dur * 1000 - lead - 100 }; controls.enabled = false; };
      if (camera.position.distanceTo(start.pos) > 40) flyTo(start, lead, begin); else begin();
      const air = R.uavs.filter(u => u.airborne).length;
      const nearNames = [...nearStations].map(id => stationById.get(id)).filter(Boolean).map(st => st.label).join(' / ');
      R.info = `${air} UAVs airborne (dots; models enlarged ${UAV_MACRO_SCALE}×; yellow = empty, returning to hub, orange = carrying cargo) · thin orange lines are the flight corridors · stations near campus: ${nearNames}`;
    }
  }
  function nextShot() {
    const i = R.shot ? SHOT_ORDER.indexOf(R.shot) : -1;
    if (i === SHOT_ORDER.length - 1) { R.cycleDone = true; return; }
    startShot(SHOT_ORDER[i + 1]);
  }
  /** Advance the replay clock and camera tracking. Returns true when a shot boundary was crossed. */
  function tick(now, dt) {
    if (R.playing) {
      R.t += dt * R.speed;
      const end = R.duration || 3600;
      if (R.t >= end) R.t = traffic ? traffic.firstTime + 10 : 0;   // full-hour loop (UAV schedule); the traffic sample loops on its own inside carStates
    }
    if ((R.playing && now - R.lastDraw >= 35) || R.lastDraw === -Infinity) { update(R.t); R.lastDraw = now; }
    updateBirdTracking(dt);
    if (R.orbit) {
      const k = Math.min(1, (now - R.orbit.t0) / R.orbit.dur), p = orbitPose(R.orbit, k);
      camera.position.copy(p.pos); controls.target.copy(p.target); camera.lookAt(p.target);
      if (k >= 1) cancelCamera();
    }
    for (const sprite of stationLayer.labels.children) { const mpp = 2 * camera.position.distanceTo(sprite.position) * Math.tan(camera.fov * Math.PI / 360) / window.innerHeight; sprite.scale.set(48 * mpp, 48 / (sprite.userData.aspect ?? (48 / 22)) * mpp, 1); }
    if (R.shot && now >= R.shotUntil) { nextShot(); return true; }
    return false;
  }
  function applyLayers({ cars = true, uavs = true, signals = true, stations = true, roads = true, trafficMap = false, birds = true } = {}) {
    actors.setVisible({ cars, uavs }); signalLayer?.setVisible(signals); stationLayer.setVisible(stations); roadMesh.visible = roads; birdLayer?.setVisible(birds);
    mapManual = trafficMap; applyTrafficMap(); if (carDots.visible) update(R.t);
  }
  function setVisible(v) { group.visible = v; }
  function stopShots() { R.shot = null; clearFollow(); cancelCamera(); trackBirds(null); setUavScale(1); markers.visible = false; corridors.visible = false; mapShot = false; applyTrafficMap(); }
  Object.defineProperties(R, { birds: { get: () => birdLayer }, birdTarget: { get: () => birdTrack.target } });   // live getters (Object.assign would copy the values)
  return Object.assign(R, { update, tick, startShot, nextShot, stopShots, clearFollow, cancelCamera, applyLayers, setVisible, followCamera, timeString, trackBirds, flockSummary });
}
