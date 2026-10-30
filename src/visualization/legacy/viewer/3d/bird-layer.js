// Scene bird replays (urban_geometry.birds.scene): project/<scene>/configs/bird_visualization.json names a
// bird_replay.json (schema uwm-bird-replay-2) with int16 records; they are decoded here into the float records
// the shared pigeon layer (agents/demo_rev02/birds.js) draws. The replay is a roost-to-roost day on the scene's
// own clock, held at its first / last frame outside that span (birds stay roosted rather than vanish).
import * as THREE from 'three';
import { createBirdLayer } from '../../agents/demo_rev02/birds.js';

const PROJECT_IDS = { south_kensington: 'south_ken', core008: 'south_ken' }; // viewer scene id -> project id
const PREFIX = import.meta.url.includes('/src/visualization/legacy/')
  ? '../../../../../'
  : '../../';

/** The scene's bird configuration ({config, url}) or null when the scene has none. */
export async function probeBirdConfig(sceneId) {
  const project = PROJECT_IDS[sceneId] ?? sceneId;
  const url = new URL(
    `${PREFIX}project/${project}/configs/bird_visualization.json`,
    import.meta.url,
  );
  try {
    const response = await fetch(url, { cache: 'no-cache' });
    if (!response.ok) return null;
    return { config: await response.json(), url };
  } catch {
    return null;
  }
}

/** {manifest, buffer (Float32Array, 6 floats per record), states, config} or null. */
export async function loadBirdReplay(sceneId, probed = null) {
  const found = probed ?? (await probeBirdConfig(sceneId));
  if (!found) return null;
  const manifestURL = new URL(found.config.replay, found.url);
  const response = await fetch(manifestURL);
  if (!response.ok) throw Error(`bird replay manifest: ${response.status}`);
  const manifest = await response.json();
  if (manifest.schema !== 'uwm-bird-replay-2')
    throw Error(`unsupported bird replay ${manifest.schema}`);
  const get = (name) =>
    fetch(new URL(name, manifestURL)).then((r) => {
      if (!r.ok) throw Error(`${name} ${r.status}`);
      return r.arrayBuffer();
    });
  const [records, stateBytes] = await Promise.all([get('bird_replay.i16'), get('bird_states.u8')]);
  const q = new Int16Array(records),
    states = new Uint8Array(stateBytes);
  if (
    q.length !== manifest.frames * manifest.birds * 6 ||
    states.length !== manifest.frames * manifest.birds
  )
    throw Error('bird replay size does not match its manifest');
  const e = manifest.encoding,
    [ox, oy, oz] = e.offset_m,
    ps = e.position_scale_m,
    as = e.angle_scale_rad,
    ss = e.speed_scale_mps;
  const buffer = new Float32Array(q.length);
  for (let k = 0; k < q.length; k += 6) {
    buffer[k] = ox + q[k] * ps;
    buffer[k + 1] = oy + q[k + 1] * ps;
    buffer[k + 2] = oz + q[k + 2] * ps;
    buffer[k + 3] = q[k + 3] * as;
    buffer[k + 4] = q[k + 4] * ss;
    buffer[k + 5] = q[k + 5] * as;
  }
  return { manifest, buffer, states, config: found.config };
}

/** Hold a bird layer at its first / last frame outside the replay span. */
export function holdAtEnds(layer, manifest) {
  const update = layer.update,
    lo = manifest.first_frame_t_s,
    hi = manifest.last_frame_t_s;
  layer.update = (t) => update(Math.min(hi, Math.max(lo, t)));
  return layer;
}

/** Local clock time (HH:MM) of replay time t, from the manifest's sun clock. */
export function birdLocalTime(manifest, t) {
  const c = manifest.clock;
  if (!c?.local_window) return '';
  const h = (s) => +s.slice(0, 2) + +s.slice(3, 5) / 60;
  const [a, b] = c.local_window.map(h),
    f = Math.min(1, Math.max(0, t / manifest.last_frame_t_s)),
    x = a + (b - a) * f;
  return `${String(Math.floor(x)).padStart(2, '0')}:${String(Math.floor((x % 1) * 60)).padStart(2, '0')}`;
}

/** The replay's flocks (manifest.flocks); a replay without them is one flock of all its birds. */
export function birdFlocks(manifest) {
  return manifest.flocks?.length
    ? manifest.flocks
    : [{ id: 1, first_bird: 0, birds: manifest.birds, moments: [] }];
}

/**
 * Bird panel controls, added above its readout: "Bird #" (1 to the replay's bird count: the bird the camera
 * follows), a flock picker (replays with flocks; picking a flock picks its first bird) and "Jump to" (start /
 * middle of each moment of the chosen bird's flock). onBird(index, 0-based) when a bird is picked, onJump(t)
 * with a moment's replay time. until: the end of the clock that plays the replay; later moments are left out.
 */
export function mountBirdControls({ box, manifest, onBird, onJump, until = Infinity }) {
  const flocks = birdFlocks(manifest);
  const flockOf = (i) =>
    Math.max(
      0,
      flocks.findIndex((f) => i >= f.first_bird && i < f.first_bird + f.birds),
    );
  const rows = [document.createElement('div'), document.createElement('div')];
  for (const row of rows) row.className = 'grid2';
  const birdInput = document.createElement('input'),
    flockSelect = document.createElement('select'),
    momentSelect = document.createElement('select');
  Object.assign(birdInput, {
    type: 'number',
    min: 1,
    max: manifest.birds,
    step: 1,
    value: 1,
    title: `Bird the camera follows (1-${manifest.birds}); press Enter`,
  });
  birdInput.style.width = '100%';
  flockSelect.title = 'Flock (picks its first bird)';
  momentSelect.title = "Jump to a moment of this bird's flock's day";
  flocks.forEach((f, k) =>
    flockSelect.add(
      new Option(`Flock ${f.id} · birds ${f.first_bird + 1}-${f.first_bird + f.birds}`, k),
    ),
  );
  const fillMoments = () => {
    momentSelect.replaceChildren(new Option('Jump to…', ''));
    for (const m of flocks[+flockSelect.value].moments ?? []) {
      if (m.start_s >= until) continue;
      const group = document.createElement('optgroup');
      group.label = m.label;
      group.append(
        new Option(`${m.label} · start ${birdLocalTime(manifest, m.start_s)}`, m.start_s),
      );
      if (m.mid_s < until)
        group.append(
          new Option(`${m.label} · middle ${birdLocalTime(manifest, m.mid_s)}`, m.mid_s),
        );
      momentSelect.append(group);
    }
    momentSelect.style.display = momentSelect.options.length > 1 ? '' : 'none';
  };
  const setBird = (i) => {
    i = Math.min(manifest.birds - 1, Math.max(0, Math.round(i) || 0));
    birdInput.value = i + 1;
    if (flockOf(i) !== +flockSelect.value) {
      flockSelect.value = flockOf(i);
      fillMoments();
    }
    onBird(i);
  };
  fillMoments();
  birdInput.addEventListener('change', () => setBird(+birdInput.value - 1));
  flockSelect.addEventListener('change', () => {
    fillMoments();
    setBird(flocks[+flockSelect.value].first_bird);
  });
  momentSelect.addEventListener('change', () => {
    if (momentSelect.value === '') return;
    const t = +momentSelect.value;
    momentSelect.value = '';
    onJump(t);
  });
  if (flocks.length < 2) flockSelect.style.display = 'none';
  rows[0].append(birdInput, flockSelect);
  rows[1].append(momentSelect);
  const readout = box.querySelector('#bird-readout');
  for (const row of rows) box.insertBefore(row, readout);
  return { rows, birdInput, flockSelect, momentSelect, setBird };
}

/** Stand-alone bird layer for scenes without the South Kensington replay (own clock, like the UAV layer). */
export async function createSceneBirdLayer({ scene, sceneId, probed = null }) {
  const data = await loadBirdReplay(sceneId, probed);
  if (!data) throw Error(`no bird replay for ${sceneId}`);
  const { manifest, config } = data;
  const group = new THREE.Group();
  group.name = `${sceneId} birds`;
  scene.add(group);
  const layer = holdAtEnds(
    await createBirdLayer({
      scene: group,
      manifest,
      buffer: data.buffer,
      states: data.states,
      modelURL: new URL('../../agents/demo_rev02/actors/pigeon.glb', import.meta.url).href,
    }),
    manifest,
  );
  const target = new THREE.Vector3(),
    flocks = birdFlocks(manifest);
  let radius = 200,
    focused = false;
  const R = {
    group,
    layer,
    manifest,
    t: manifest.first_frame_t_s,
    speed: config.speed ?? 10,
    playing: true,
    duration: manifest.last_frame_t_s,
    counts: [0, 0, 0, 0, 0],
    stats: `${manifest.birds} birds${flocks.length > 1 ? ` in ${flocks.length} flocks` : ''} · ${config.label ?? 'roost-to-roost day'} · ${manifest.clock?.date ?? ''}`,
    flocks,
    follow: 0, // the bird the camera follows
    get flock() {
      return (
        flocks.find((f) => R.follow >= f.first_bird && R.follow < f.first_bird + f.birds) ??
        flocks[0]
      );
    },
    selectBird(i) {
      R.follow = i;
      focused = false; // cut to the new bird rather than pan across the city
    },
    jump(t) {
      R.update(t);
      focused = false;
    },
    update(t) {
      R.t = Math.max(0, Math.min(R.duration, t));
      R.counts = layer.update(R.t).stateCounts;
    },
    tick(dt) {
      if (R.playing) R.update((R.t + dt * R.speed) % R.duration);
    },
    /** Camera target / orbit radius: the followed bird (closer while it is on the ground). */
    focus() {
      const b = layer.getState(R.follow);
      if (!b) return { target, radius };
      target.set(b.x, b.y, b.z);
      const r = b.state === 0 || b.state === 4 ? 18 : 35;
      if (!focused) {
        radius = r;
        focused = true;
      } else radius += (r - radius) * 0.03;
      return { target, radius };
    },
    localTime: (t = R.t) => birdLocalTime(manifest, t),
    summary() {
      const b = layer.getState(R.follow);
      if (!b) return '';
      return (
        `bird ${R.follow + 1}` +
        (flocks.length > 1 ? ` (flock ${R.flock.id})` : '') +
        ` · ${b.stateName.toLowerCase()} · ${b.y.toFixed(0)} m up · ${b.speed.toFixed(1)} m/s`
      );
    },
    setVisible(value) {
      group.visible = value;
    },
    dispose() {
      group.removeFromParent();
      group.traverse((o) => {
        o.geometry?.dispose();
        for (const m of Array.isArray(o.material) ? o.material : o.material ? [o.material] : [])
          m.dispose();
      });
    },
  };
  R.update(R.t);
  return R;
}
