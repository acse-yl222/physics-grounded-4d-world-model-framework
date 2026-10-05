// map.js -- region selection (center + width/height -> bbox) and the
// existing-area / full-generation flow.

const map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: {
      osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
             tileSize: 256, attribution: '© OpenStreetMap' },
    },
    layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
  },
  center: [-0.1735, 51.4958],
  zoom: 14.5,
});

// a geographic bbox is axis-aligned, so the selection overlay is only correct
// while the map is north-up; rotation would tilt the box away from the bbox.
map.dragRotate.disable();
map.touchZoomRotate.disableRotation();

// Centre indicator only. It used to be the one way to move the selection; the
// box body and the centre field do that now, and leaving it draggable meant a
// drag aimed at the box grabbed the pin instead.
const marker = new maplibregl.Marker({ draggable: false, color: '#4da3ff' })
  .setLngLat([-0.1735, 51.4958]).addTo(map);

const $ = id => document.getElementById(id);

function bboxNow() {
  const { lat, lng } = marker.getLngLat();
  const w = +$('w-m').value || 400, h = +$('h-m').value || 400;
  const dlat = h / 2 / 110540;
  const dlng = w / 2 / (111320 * Math.cos(lat * Math.PI / 180));
  return [lat - dlat, lng - dlng, lat + dlat, lng + dlng];   // s,w,n,e
}

function rectCoords(b) {
  return [[[b[1], b[0]], [b[3], b[0]], [b[3], b[2]], [b[1], b[2]], [b[1], b[0]]]];
}

map.on('load', async () => {
  map.addSource('sel', { type: 'geojson', data: { type: 'Feature', geometry: { type: 'Polygon', coordinates: rectCoords(bboxNow()) } } });
  map.addLayer({ id: 'sel-line', type: 'line', source: 'sel',
    paint: { 'line-color': '#fbbf24', 'line-width': 2, 'line-dasharray': [2, 2] } });
  map.addLayer({ id: 'sel-fill', type: 'fill', source: 'sel',
    paint: { 'fill-color': '#fbbf24', 'fill-opacity': 0.07 } });

  // existing generated areas
  const areasList = await (await fetch('/api/areas')).json();
  const feats = areasList.filter(a => a.has_blend && !a.stale).map(a => ({
    type: 'Feature', properties: { name: a.name },
    geometry: { type: 'Polygon', coordinates: rectCoords(a.bbox) },
  }));
  map.addSource('areas', { type: 'geojson', data: { type: 'FeatureCollection', features: feats } });
  map.addLayer({ id: 'areas-line', type: 'line', source: 'areas',
    paint: { 'line-color': '#4da3ff', 'line-width': 2 } });
  map.addLayer({ id: 'areas-label', type: 'symbol', source: 'areas',
    layout: { 'text-field': ['get', 'name'], 'text-size': 12 },
    paint: { 'text-color': '#4da3ff', 'text-halo-color': '#fff', 'text-halo-width': 1.5 } });
  map.on('click', 'areas-line', e => {
    location.href = `/viewer.html?area=${e.features[0].properties.name}`;
  });
  refreshRect();
});

function refreshRect() {
  const b = bboxNow();
  const src = map.getSource('sel');
  if (src) src.setData({ type: 'Feature', geometry: { type: 'Polygon', coordinates: rectCoords(b) } });
  $('bbox-label').textContent = `bbox: ${b.map(v => v.toFixed(5)).join(', ')}`;
  const c = $('centre');
  if (c && document.activeElement !== c) {
    const { lat, lng } = marker.getLngLat();
    c.value = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  }
  syncOverlay();
}
$('w-m').oninput = refreshRect;
$('h-m').oninput = refreshRect;

// Centre field: accepts "lat, lng" as pasted from a map site. Only written back
// while the user is not typing in it, so an in-progress edit is never clobbered.
$('centre').oninput = () => {
  const m = $('centre').value.match(/(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)/);
  if (!m) return;
  const lat = +m[1], lng = +m[2];
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return;
  marker.setLngLat([lng, lat]);
  refreshRect();
};

// ---------------- resolve / generate flow
let pollTimer = null;

$('resolve-btn').onclick = async () => {
  const b = bboxNow();
  const res = await (await fetch('/api/generate/resolve', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bbox: b }),
  })).json();
  const holder = $('result');
  if (res.too_small) {
    holder.innerHTML = `<div class="group"><h4>${t('map.too_small_h')}</h4>
      <div class="sub">${t('map.too_small', { w: res.extent_m[0], h: res.extent_m[1] })}</div></div>`;
    return;
  }
  if (res.match) {
    holder.innerHTML = `<div class="group"><h4>${t('map.covered')}</h4>
      <div class="sub">${res.match.display ? res.match.display + ' · ' : ''}${res.match.name} · ${t('index.meta', { n: res.match.buildings, s: res.match.specs })}</div>
      ${res.match.preview ? `<div class="sub" style="color:var(--warn)">${t('map.preview_hint')}</div>` : ''}
      <button onclick="location.href='/viewer.html?area=${res.match.name}'">${t('map.open_viewer')}</button>
      ${res.match.preview ? `<button class="ghost" onclick="location.href='/jobs.html'">${t('map.to_jobs')}</button>` : ''}</div>`;
  } else {
    const def = 'web_' + new Date().toISOString().slice(2, 10).replace(/-/g, '')
      + '_' + Math.abs(b[0] * 1000 | 0);
    holder.innerHTML = `<div class="group"><h4>${t('map.not_generated')}</h4>
      <div class="sub">${t('map.pipeline_desc')}</div>
      <label>${t('map.area_name')}</label><input type="text" id="area-name" value="${def}">
      <label>${t('map.display_name')}</label><input type="text" id="area-display" placeholder="e.g. South Kensington">
      <label style="display:flex;align-items:center;gap:7px;margin-top:10px;cursor:pointer">
        <input type="checkbox" id="skip-refine" style="width:auto;margin:0">
        <span>${t('map.skip_refine')}</span></label>
      <div class="sub">${t('map.skip_refine_hint')}</div>
      <div style="margin-top:8px"><button id="start-btn">${t('map.start')}</button></div>
      </div><div id="job-box"></div>`;
    $('start-btn').onclick = async () => {
      $('start-btn').disabled = true;
      const r = await fetch('/api/generate/start', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bbox: b, name: $('area-name').value.trim(),
                               display: $('area-display').value.trim(),
                               skip_refine: $('skip-refine').checked }),
      });
      if (!r.ok) { alert(await r.text()); $('start-btn').disabled = false; return; }
      const { job } = await r.json();
      pollJob(job);
    };
  }
};

async function pollJob(jid) {
  clearInterval(pollTimer);
  const tick = async () => {
    const j = await (await fetch(`/api/jobs/${jid}`)).json();
    const box = $('job-box');
    if (!box) { clearInterval(pollTimer); return; }
    box.innerHTML = jobCardHTML(j);
    bindJobActions(box, jid);
  };
  await tick();
  pollTimer = setInterval(tick, 2500);
}


// ---------------- screenshot-style selection box
// The bbox stays defined by the marker centre + the width/height inputs; the
// overlay only writes back into those, so the numeric fields, the dashed map
// rect and the box can never disagree.

const MIN_M = +$('w-m').min || 100, MAX_M = +$('w-m').max || 1500;
const M_PER_LAT = 110540;
const mPerLng = lat => 111320 * Math.cos(lat * Math.PI / 180);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const DIRS = ['nw', 'n', 'ne', 'w', 'e', 'sw', 's', 'se'];
const HPOS = { nw: [0, 0], n: [.5, 0], ne: [1, 0], w: [0, .5],
               e: [1, .5], sw: [0, 1], s: [.5, 1], se: [1, 1] };

const ov = document.createElement('div');
ov.id = 'sel-ov';
ov.innerHTML = '<div class="body"></div>'
  + DIRS.map(d => `<div class="h ${d}" data-dir="${d}"></div>`).join('');
$('map').appendChild(ov);

function syncOverlay() {
  const b = bboxNow();                      // s, w, n, e
  const p1 = map.project([b[1], b[2]]);     // NW corner
  const p2 = map.project([b[3], b[0]]);     // SE corner
  const w = p2.x - p1.x, h = p2.y - p1.y;
  ov.style.left = `${p1.x}px`; ov.style.top = `${p1.y}px`;
  ov.style.width = `${w}px`;   ov.style.height = `${h}px`;
  for (const el of ov.querySelectorAll('.h')) {
    const [fx, fy] = HPOS[el.dataset.dir];
    el.style.left = `${fx * w}px`;
    el.style.top = `${fy * h}px`;
  }
}
map.on('move', syncOverlay);
map.on('resize', syncOverlay);

function commitBbox(b) {
  const lat = (b[0] + b[2]) / 2, lng = (b[1] + b[3]) / 2;
  marker.setLngLat([lng, lat]);
  $('w-m').value = Math.round((b[3] - b[1]) * mPerLng(lat));
  $('h-m').value = Math.round((b[2] - b[0]) * M_PER_LAT);
  refreshRect();
}

function dragStart(ev, dir) {
  ev.preventDefault(); ev.stopPropagation();
  map.dragPan.disable();
  ov.classList.add('busy');
  const b0 = bboxNow();
  const at = e => {
    const r = map.getContainer().getBoundingClientRect();
    return map.unproject([e.clientX - r.left, e.clientY - r.top]);
  };
  const p0 = at(ev);

  let seen = null;
  const onMove = e => {
    if (e === seen) return;        // captured target and window both deliver it
    seen = e;
    const p = at(e), b = b0.slice();
    if (dir === 'move') {
      const dLat = p.lat - p0.lat, dLng = p.lng - p0.lng;
      b[0] += dLat; b[2] += dLat; b[1] += dLng; b[3] += dLng;
    } else {
      // the dragged side follows the pointer, the opposite side stays put --
      // clamping re-derives the moving side so the box cannot invert or run
      // past the limits the numeric inputs already enforce
      if (dir.includes('n')) b[2] = p.lat;
      if (dir.includes('s')) b[0] = p.lat;
      if (dir.includes('e')) b[3] = p.lng;
      if (dir.includes('w')) b[1] = p.lng;
      if (dir.includes('n') || dir.includes('s')) {
        const hM = clamp((b[2] - b[0]) * M_PER_LAT, MIN_M, MAX_M);
        if (dir.includes('n')) b[2] = b[0] + hM / M_PER_LAT;
        else b[0] = b[2] - hM / M_PER_LAT;
      }
      if (dir.includes('e') || dir.includes('w')) {
        const mL = mPerLng((b[0] + b[2]) / 2);
        const wM = clamp((b[3] - b[1]) * mL, MIN_M, MAX_M);
        if (dir.includes('e')) b[3] = b[1] + wM / mL;
        else b[1] = b[3] - wM / mL;
      }
    }
    commitBbox(b);
  };
  const el = ev.currentTarget;
  const onUp = () => {
    el.removeEventListener('pointermove', onMove);
    el.removeEventListener('pointerup', onUp);
    el.removeEventListener('pointercancel', onUp);
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
    try { el.releasePointerCapture(ev.pointerId); } catch (_) {}
    map.dragPan.enable();
    ov.classList.remove('busy');
  };
  // Pointer capture keeps the gesture bound to the handle even once the pointer
  // has left it -- and the handle moves out from under the cursor on every
  // frame of a resize. The window listeners stay as a fallback for pointer
  // implementations that refuse the capture.
  try { el.setPointerCapture(ev.pointerId); } catch (_) {}
  el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerup', onUp);
  el.addEventListener('pointercancel', onUp);
  window.addEventListener('pointermove', onMove);
  window.addEventListener('pointerup', onUp);
}

ov.querySelector('.body').addEventListener('pointerdown', e => dragStart(e, 'move'));
for (const el of ov.querySelectorAll('.h')) {
  el.addEventListener('pointerdown', e => dragStart(e, el.dataset.dir));
}

// Draw the box straight away rather than waiting for map 'load'. Only the
// dashed GeoJSON rect needs the style to be ready (refreshRect skips it until
// then); the overlay and the bbox readout do not. On a slow tile fetch the
// selection UI used to be invisible until the basemap arrived, which looks
// exactly like the box being missing.
refreshRect();
