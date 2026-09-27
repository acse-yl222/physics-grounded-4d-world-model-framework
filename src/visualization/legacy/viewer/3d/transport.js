/* TfL transport layer (scenes/<id>/transport/transport.json, built by scenes/white_city/tools/build_transport.py from a
   snapshot of the TfL Unified API placed in the model frame with the scene's georeference): tube / rail lines and bus
   routes as fat lines on the ground, stations and bus stops as markers, road disruptions and JamCam traffic cameras as
   pickable markers, plus live arrivals fetched from api.tfl.gov.uk while the page is online (the API allows cross-origin
   reads). Nothing here is simulated: it is the network as TfL publishes it. */
import * as THREE from 'three';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';

const Y = { rail: 3.0, bus: 2.2, stop: 1.5, station: 4, cam: 6, disruption: 10 };
const API = 'https://api.tfl.gov.uk';

function label(text, colour = '#ffffff') {   // text sprite (canvas), sized in world units by the caller
  const c = document.createElement('canvas'), ctx = c.getContext('2d');
  ctx.font = '600 28px -apple-system, "Segoe UI", sans-serif';
  const w = Math.ceil(ctx.measureText(text).width) + 28; c.width = w; c.height = 48;
  ctx.font = '600 28px -apple-system, "Segoe UI", sans-serif';
  ctx.fillStyle = 'rgba(18,21,26,.85)'; ctx.beginPath(); ctx.roundRect(0, 0, w, 48, 10); ctx.fill();
  ctx.fillStyle = colour; ctx.textBaseline = 'middle'; ctx.fillText(text, 14, 25);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  s.scale.set(w / 48 * 22, 22, 1); s.renderOrder = 10;
  return s;
}
function fatLines(polylines, colour, width, y, opacity = 1) {
  const pos = [], col = [], c = new THREE.Color(colour);
  for (const p of polylines) for (let i = 0; i + 1 < p.length; i++) { pos.push(p[i][0], y, p[i][1], p[i + 1][0], y, p[i + 1][1]); col.push(c.r, c.g, c.b, c.r, c.g, c.b); }
  if (!pos.length) return null;
  const g = new LineSegmentsGeometry(); g.setPositions(pos); g.setColors(col);
  const m = new LineMaterial({ vertexColors: true, linewidth: width, transparent: opacity < 1, opacity, worldUnits: false, depthWrite: false });
  m.resolution.set(window.innerWidth, window.innerHeight);
  const l = new LineSegments2(g, m); l.frustumCulled = false; l.renderOrder = 5;
  return l;
}

export async function createTransport({ scene, url, onProgress = () => {} }) {
  onProgress('TfL transport snapshot…');
  const r = await fetch(url); if (!r.ok) throw new Error(`transport: ${url} HTTP ${r.status}`);
  const data = await r.json();
  const group = new THREE.Group(); group.name = 'TfL transport'; scene.add(group);
  const sub = {}; for (const k of ['rail', 'bus', 'stations', 'stops', 'disruptions', 'cams']) { sub[k] = new THREE.Group(); sub[k].name = 'TfL ' + k; group.add(sub[k]); }
  const pick = [];   // pickable meshes with .userData.info
  const materials = [];

  // ---- routes
  const railRoutes = data.routes.filter(r => r.mode !== 'bus'), busRoutes = data.routes.filter(r => r.mode === 'bus');
  for (const rt of railRoutes) { const l = fatLines(rt.polylines, rt.colour, 5, Y.rail); if (l) { sub.rail.add(l); materials.push(l.material); } }
  const busLines = fatLines(busRoutes.flatMap(r => r.polylines), '#E32017', 2, Y.bus, 0.55); if (busLines) { sub.bus.add(busLines); materials.push(busLines.material); }

  // ---- stations (tube / rail): a disc in the line colour with the name above
  const stations = new Map();
  for (const rt of railRoutes) for (const s of rt.stations) { const e = stations.get(s.id) ?? { ...s, lines: [] }; e.lines.push(rt); stations.set(s.id, e); }
  const discGeom = new THREE.CylinderGeometry(11, 11, 3, 24), ringGeom = new THREE.CylinderGeometry(14, 14, 2, 24);
  for (const s of stations.values()) {
    const disc = new THREE.Mesh(discGeom, new THREE.MeshBasicMaterial({ color: s.lines[0].colour })); disc.position.set(s.x, Y.station, s.z);
    const ring = new THREE.Mesh(ringGeom, new THREE.MeshBasicMaterial({ color: 0xffffff })); ring.position.set(s.x, Y.station - 1, s.z);
    const arr = data.arrivals?.[s.id];
    disc.userData.info = `${s.name}\n${s.lines.map(l => l.name + (l.status?.[0] ? ` · ${l.status[0].description}` : '')).join('\n')}` + (arr?.length ? `\n${arr.slice(0, 4).map(a => `${a.line} → ${a.destination} · ${Math.round(a.seconds / 60)} min`).join('\n')}` : '');
    disc.userData.stationId = s.id; disc.userData.name = s.name;
    const lab = label(s.name.replace(/ (Underground|Rail) Station$/, ''), '#ffffff'); lab.position.set(s.x, Y.station + 30, s.z);
    sub.stations.add(disc, ring, lab); pick.push(disc);
  }
  // ---- bus stops: small red / white discs (instanced), pickable through one merged hit list
  const busStops = data.stops.filter(s => s.type === 'NaptanPublicBusCoachTram');
  if (busStops.length) {
    const g = new THREE.CylinderGeometry(3.2, 3.2, 1.6, 12), m = new THREE.MeshBasicMaterial({ color: 0xE32017 });
    const inst = new THREE.InstancedMesh(g, m, busStops.length), M = new THREE.Matrix4();
    busStops.forEach((s, i) => { M.makeTranslation(s.x, Y.stop, s.z); inst.setMatrixAt(i, M); });
    inst.instanceMatrix.needsUpdate = true; inst.userData.stops = busStops; inst.name = 'bus stops';
    sub.stops.add(inst); pick.push(inst);
  }
  // ---- road disruptions (points: orange cones; lines / polygons: orange fat lines)
  for (const d of data.road_disruptions) {
    const info = `Road · ${d.category}${d.subCategory ? ' / ' + d.subCategory : ''} · ${d.severity}\n${d.location ?? ''}\n${(d.comments ?? '').slice(0, 220)}${d.endDateTime ? '\nuntil ' + d.endDateTime.slice(0, 10) : ''}`;
    const g = d.geometry;
    if (g.type === 'Point') { const m = new THREE.Mesh(new THREE.ConeGeometry(7, 18, 12), new THREE.MeshBasicMaterial({ color: 0xff8c1a })); m.position.set(g.xz[0], Y.disruption, g.xz[1]); m.rotation.x = Math.PI; m.userData.info = info; sub.disruptions.add(m); pick.push(m); }
    else { const poly = g.type === 'Polygon' ? [...g.xz, g.xz[0]] : g.xz; const l = fatLines([poly], '#ff8c1a', 4, Y.rail + 0.5); if (l) { sub.disruptions.add(l); materials.push(l.material); } const c = poly[Math.floor(poly.length / 2)]; const m = new THREE.Mesh(new THREE.ConeGeometry(7, 18, 12), new THREE.MeshBasicMaterial({ color: 0xff8c1a })); m.position.set(c[0], Y.disruption, c[1]); m.rotation.x = Math.PI; m.userData.info = info; sub.disruptions.add(m); pick.push(m); }
  }
  // ---- JamCams: yellow octahedra; the readout shows the camera name and the still-image URL
  for (const c of data.jamcams) {
    const m = new THREE.Mesh(new THREE.OctahedronGeometry(6), new THREE.MeshBasicMaterial({ color: 0xffd34d })); m.position.set(c.x, Y.cam, c.z);
    m.userData.info = `JamCam · ${c.name}${c.view ? ' · ' + c.view : ''}${c.available === 'false' ? ' (offline)' : ''}\n${c.imageUrl ?? ''}`; m.userData.cam = c;
    sub.cams.add(m); pick.push(m);
  }

  const raycaster = new THREE.Raycaster();
  const T = {
    data, group, sub, pick, stations: [...stations.values()],
    taken: data.snapshot?.taken_utc,
    counts: { rail: railRoutes.length, bus: busRoutes.length, stations: stations.size, stops: busStops.length, disruptions: data.road_disruptions.length, cams: data.jamcams.length },
    setLayers({ rail = true, bus = true, stations = true, stops = true, disruptions = true, cams = true } = {}) { sub.rail.visible = rail; sub.bus.visible = bus; sub.stations.visible = stations; sub.stops.visible = stops; sub.disruptions.visible = disruptions; sub.cams.visible = cams; },
    setVisible(v) { group.visible = v; },
    resize(w, h) { for (const m of materials) m.resolution.set(w, h); },
    /** info text of the marker under the pointer (NDC), or null */
    hover(ndc, camera) {
      if (!group.visible) return null;
      raycaster.setFromCamera(ndc, camera);
      const hits = raycaster.intersectObjects(pick.filter(o => o.parent.visible), false);
      if (!hits.length) return null;
      const h = hits[0];
      if (h.object.userData.stops) { const s = h.object.userData.stops[h.instanceId]; return `Bus stop ${s.letter ? s.letter + ' · ' : ''}${s.name}${s.towards ? ' → ' + s.towards : ''}\nroutes ${s.lines.join(', ')}`; }
      return h.object.userData.info ?? null;
    },
    /** live arrivals for a station (TfL API; falls back to the snapshot) */
    async arrivals(stationId) {
      try {
        const r = await fetch(`${API}/StopPoint/${stationId}/Arrivals`, { cache: 'no-store' }); if (!r.ok) throw new Error(r.status);
        const a = (await r.json()).sort((x, y) => x.timeToStation - y.timeToStation).slice(0, 12);
        return { live: true, list: a.map(x => ({ line: x.lineName, platform: x.platformName, destination: x.destinationName || x.towards, seconds: x.timeToStation })) };
      } catch { return { live: false, list: data.arrivals?.[stationId] ?? [] }; }
    },
  };
  T.summary = `TfL snapshot ${T.taken ? T.taken.replace('T', ' ').slice(0, 16) + ' UTC' : ''} · ${T.counts.rail} tube / rail lines, ${T.counts.bus} bus routes, ${T.counts.stations} stations, ${T.counts.stops} bus stops, ${T.counts.disruptions} road disruptions, ${T.counts.cams} JamCams`;
  T.statusLines = data.line_status.map(l => `${l.name}: ${l.status.join(', ')}`);
  return T;
}
