import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

// revision_02 bird layer. Trajectories come from Akira's flock model (run unchanged on the campus voxel
// geometry) via bird_replay.json / bird_replay.f32 / bird_states.u8 (see build_bird_replay_v2.py).
// Display model: a low-poly feral pigeon built procedurally as a GLB (actors/pigeon.glb, real scale:
// ~0.39 m beak-to-tail, 0.66 m wingspan) with three nodes - body, wing_L, wing_R - so the wings can flap
// per instance. Wing flap, pitch and roll are DISPLAY ONLY: they are derived from the recorded velocity,
// bank and state and never change a position. If the GLB cannot be loaded the old placeholder shape is used.
// Not Akira's art: a stand-in asset that can be swapped for a nicer pigeon without touching the replay adapter.
const STATE_COLOURS = {0: '#f2c14e', 1: '#3aa0d8', 2: '#9b5de5', 3: '#f28c28', 4: '#6b7c85'};
const STATE_NAMES = {0: 'Foraging', 1: 'Transit flight', 2: 'Murmuration', 3: 'Descending to roost', 4: 'Roosting'};
const FLAP_HZ = 4.5, FLAP_AMPLITUDE = .62, FLAP_OFFSET = .12;          // pigeon-like flapping (display only); positive = wing tips up
const FOLD_DROP = .25, FOLD_SWEEP = 1.45, FOLD_ROLL = 1.3, FOLD_RATE = 3;  // folded wing: tip slightly down, swept back ~83deg, surface rolled onto the flank; blend 3/s

function placeholderBirdGeometry() {
  // +Z forward, +Y up, +X right (viewer heading convention: 0 = +Z, PI/2 = +X)
  const v = [];
  const tri = (a, b, c) => v.push(...a, ...b, ...c);
  tri([0, 0, .5], [-.08, 0, -.1], [0, .07, -.05]); tri([0, 0, .5], [0, .07, -.05], [.08, 0, -.1]);
  tri([0, 0, .5], [.08, 0, -.1], [0, -.05, -.05]); tri([0, 0, .5], [0, -.05, -.05], [-.08, 0, -.1]);
  tri([-.08, 0, -.1], [0, -.05, -.05], [0, .07, -.05]); tri([.08, 0, -.1], [0, .07, -.05], [0, -.05, -.05]);
  tri([-.08, 0, -.1], [.08, 0, -.1], [0, .01, -.4]);
  tri([0, .02, .15], [-.7, .12, -.25], [0, 0, -.08]); tri([0, .02, .15], [0, 0, -.08], [.7, .12, -.25]);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
  g.computeVertexNormals();
  return g;
}

async function loadPigeonParts(url) {
  const gltf = await new GLTFLoader().loadAsync(url);
  const parts = {body: [], wing_L: [], wing_R: []};
  const pivots = {body: new THREE.Vector3(), wing_L: new THREE.Vector3(), wing_R: new THREE.Vector3()};
  for (const name of Object.keys(parts)) {
    const node = gltf.scene.getObjectByName(name);
    if (!node) throw new Error(`pigeon.glb: node ${name} missing`);
    pivots[name].copy(node.position);
    node.traverse(o => { if (o.isMesh) parts[name].push({geometry: o.geometry, material: o.material}); });
    if (!parts[name].length) throw new Error(`pigeon.glb: node ${name} has no mesh`);
  }
  return {parts, pivots, triangles: Object.values(parts).flat().reduce((s, p) => s + p.geometry.getAttribute('position').count / 3, 0)};
}

export async function createBirdLayer({scene, manifest, buffer, states, modelURL = './actors/pigeon.glb'}) {
  const N = manifest.birds, F = manifest.frames, dt = manifest.frame_dt_s, t0 = manifest.first_frame_t_s;
  const R = manifest.record.length;   // floats per record (5 or 6)
  const hasBank = manifest.record.includes('bank_rad');
  const group = new THREE.Group(); group.name = 'Bird layer';
  let model = null, modelError = null;
  try { model = await loadPigeonParts(modelURL); } catch (e) { modelError = String(e); console.warn('bird layer: pigeon model unavailable, using placeholder shape', e); }
  // instanced meshes: one per GLB primitive, grouped by part so every instance shares the part transform
  const instanced = {body: [], wing_L: [], wing_R: []};
  function makeInstanced(geometry, material, label) {
    const m = new THREE.InstancedMesh(geometry, material, N);
    m.name = label; m.frustumCulled = false; m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    group.add(m); return m;
  }
  const legMeshes = [];                                     // legs are drawn only when the wings are folded (a flying pigeon tucks them away)
  if (model) {
    for (const part of Object.keys(instanced)) model.parts[part].forEach((p, k) => {
      const m = makeInstanced(p.geometry, p.material, `Birds pigeon ${part} ${k}`);
      instanced[part].push(m);
      if (part === 'body' && /legs/i.test(p.material?.name ?? '')) legMeshes.push(m);
    });
  } else {
    instanced.body.push(makeInstanced(placeholderBirdGeometry(), new THREE.MeshStandardMaterial({color: 0xbfc4cc, roughness: .8, metalness: 0, side: THREE.DoubleSide}), 'Birds (placeholder shape)'));
  }
  const markers = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({size: 2.5, sizeAttenuation: false, vertexColors: true, depthTest: false, depthWrite: false, transparent: true, opacity: .9}));
  markers.geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
  markers.geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
  markers.frustumCulled = false; markers.renderOrder = 19; group.add(markers);
  scene.add(group);

  const mBody = new THREE.Matrix4(), mWing = new THREE.Matrix4(), mLocal = new THREE.Matrix4(), mHidden = new THREE.Matrix4(), q = new THREE.Quaternion(), qTmp = new THREE.Quaternion();
  const pos = new THREE.Vector3(), one = new THREE.Vector3(1, 1, 1), zero = new THREE.Vector3(0, 0, 0), colour = new THREE.Color();
  const UP = new THREE.Vector3(0, 1, 0), FWD = new THREE.Vector3(0, 0, 1), RIGHT = new THREE.Vector3(1, 0, 0);
  const current = new Array(N);
  const phase = new Float32Array(N); for (let i = 0; i < N; i++) phase[i] = (i * 2.399) % (2 * Math.PI);   // golden-angle spread of flap phases
  const foldLevel = new Float32Array(N);                    // 0 = flying pose, 1 = wings folded (blended so a state change does not pop)
  let stateCounts = [0, 0, 0, 0, 0], present = 0, lastWall = null;

  function record(f, i) { const k = (f * N + i) * R; return buffer.subarray(k, k + R); }
  function angleLerp(a, b, s) { const d = Math.atan2(Math.sin(b - a), Math.cos(b - a)); return a + d * s; }
  // Wing-node conventions (from build_pigeon.mjs): the node origin is the shoulder, the left wing extends to -X, the right to +X,
  // the upper surface faces +Y and the leading edge +Z. s = +1 for the left wing, -1 for the right wing mirrors every angle.
  // Flap: rotation about the body's forward axis, positive = tips up.  Fold (constant, computed once per wing): drop the tip a
  // little, sweep it back along the flank (~83deg) and roll the wing about its own swept axis so the surface lies on the flank.
  const wingSign = {wing_L: 1, wing_R: -1};
  const qFold = {};
  for (const part of Object.keys(wingSign)) {
    const s = wingSign[part];
    const qDrop = new THREE.Quaternion().setFromAxisAngle(FWD, s * FOLD_DROP);
    const qSweep = new THREE.Quaternion().setFromAxisAngle(UP, -s * FOLD_SWEEP);
    const swept = new THREE.Quaternion().multiplyQuaternions(qSweep, qDrop);
    const axis = new THREE.Vector3(-s, 0, 0).applyQuaternion(swept).normalize();      // the swept wing's own span axis
    const qRoll = new THREE.Quaternion().setFromAxisAngle(axis, -s * FOLD_ROLL);
    qFold[part] = new THREE.Quaternion().multiplyQuaternions(qRoll, swept);
  }
  function wingMatrix(part, fold, flap) {
    qTmp.setFromAxisAngle(FWD, -wingSign[part] * flap);                 // flying pose (flap)
    if (fold > 0) q.slerpQuaternions(qTmp, qFold[part], fold); else q.copy(qTmp);
    return mLocal.compose(model.pivots[part], q, one);
  }

  function update(t) {
    let f = (t - t0) / dt; if (!(f >= 0)) f = 0; if (f > F - 1) f = F - 1;
    const f0 = Math.floor(f), f1 = Math.min(F - 1, f0 + 1), s = f - f0;
    const inRange = t >= t0 - dt && t <= manifest.last_frame_t_s + dt;
    present = inRange ? N : 0;
    stateCounts = [0, 0, 0, 0, 0];
    const cp = markers.geometry.attributes.position, cc = markers.geometry.attributes.color;
    const wall = performance.now() / 1000;
    const dWall = lastWall === null ? 1 : Math.min(.25, Math.max(0, wall - lastWall)); lastWall = wall;   // first call: jump straight to the pose
    for (let i = 0; i < N; i++) {
      const a = record(f0, i), b = record(f1, i);
      const x = a[0] + (b[0] - a[0]) * s, y = a[1] + (b[1] - a[1]) * s, z = a[2] + (b[2] - a[2]) * s;
      const yaw = angleLerp(a[3], b[3], s), speed = a[4] + (b[4] - a[4]) * s, bank = hasBank ? a[5] + (b[5] - a[5]) * s : 0;
      const st = states[f0 * N + i];
      stateCounts[st] = (stateCounts[st] ?? 0) + 1;
      const vy = f1 > f0 ? (b[1] - a[1]) / dt : 0;                       // vertical speed from consecutive frames (display pitch only)
      const pitch = Math.max(-.6, Math.min(.6, Math.atan2(vy, Math.max(.5, speed))));
      current[i] = {idIndex: i, x, y, z, headingRadians: yaw, speed, bank, pitch, state: st, stateName: STATE_NAMES[st] ?? String(st), airborne: st !== 4, visible: inRange};
      pos.set(x, y, z);
      q.setFromAxisAngle(UP, yaw);
      if (pitch) { qTmp.setFromAxisAngle(RIGHT, -pitch); q.multiply(qTmp); }
      if (bank) { qTmp.setFromAxisAngle(FWD, -bank); q.multiply(qTmp); }
      mBody.compose(pos, q, inRange ? one : zero);
      const target = (st === 4 || st === 0 || speed < .8) ? 1 : 0;     // roosting, foraging or slow: wings folded, legs out
      const step = FOLD_RATE * dWall, diff = target - foldLevel[i];
      foldLevel[i] += Math.abs(diff) <= step ? diff : Math.sign(diff) * step;
      const legsOut = foldLevel[i] > .5;
      for (const m of instanced.body) m.setMatrixAt(i, (!legsOut && legMeshes.includes(m)) ? mHidden.compose(pos, q, zero) : mBody);
      if (model) {
        const flap = FLAP_OFFSET + FLAP_AMPLITUDE * Math.sin(2 * Math.PI * FLAP_HZ * wall + phase[i]);
        for (const part of ['wing_L', 'wing_R']) {
          mWing.multiplyMatrices(mBody, wingMatrix(part, foldLevel[i], flap));
          for (const m of instanced[part]) m.setMatrixAt(i, mWing);
        }
      }
      colour.set(STATE_COLOURS[st] ?? '#ffffff');
      cp.setXYZ(i, x, y + .5, z); cc.setXYZ(i, colour.r, colour.g, colour.b);
    }
    for (const list of Object.values(instanced)) for (const m of list) m.instanceMatrix.needsUpdate = true;
    cp.needsUpdate = true; cc.needsUpdate = true;
    markers.visible = markersWanted && group.visible && inRange;
    return {present, stateCounts, frame: f0};
  }
  let markersWanted = true;
  return {
    group, mesh: instanced.body[0], update,
    getState: i => current[i] ?? null,
    setVisible: v => { group.visible = v; },
    setMarkers: v => { markersWanted = v; markers.visible = v && group.visible; },
    stats: {birds: N, frames: F, frame_dt_s: dt, first_t_s: t0, last_t_s: manifest.last_frame_t_s, model: model ? 'procedural low-poly pigeon GLB (actors/pigeon.glb), display only' : 'placeholder shape (pigeon.glb failed to load)',
            model_triangles: model ? model.triangles : null, model_error: modelError, placeholder_model: !model},
    STATE_NAMES, STATE_COLOURS,
  };
}
