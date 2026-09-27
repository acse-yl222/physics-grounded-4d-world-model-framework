import * as THREE from 'three';

// revision_02 signal layer: coloured movement paths (as in v1) plus instanced
// poles and three-aspect heads at SUMO stop lines. Every head reads the recorded
// state of its own controlled connection: states[tls_id][link_index]. Positions
// are demo placements derived from the simulation network, not surveyed TfL poles.
const RED = new THREE.Color('#ff2a2a'), AMBER = new THREE.Color('#ffb400'), GREEN = new THREE.Color('#22e07a');
const OFF_RED = new THREE.Color('#3a0a0a'), OFF_AMBER = new THREE.Color('#3a2a06'), OFF_GREEN = new THREE.Color('#0a2a16');
const LINE_RED = new THREE.Color('#ef4545'), LINE_AMBER = new THREE.Color('#ffbf38'), LINE_GREEN = new THREE.Color('#29d68f'), LINE_UNKNOWN = new THREE.Color('#687b83');

function stateOf(frame, head) {
  const s = frame?.states?.[head.tls_id];
  return s ? s[head.link_index] : undefined;
}

export function createSignalLayerV2(scene, layer, frames) {
  const group = new THREE.Group(); group.name = 'Simulated signals (revision_02)';
  // --- movement paths -------------------------------------------------------
  const positions = [], owners = [], colours = [];
  const movements = layer.movements;
  for (let m = 0; m < movements.length; m++) {
    const points = movements[m].world_shape_xyz;
    for (let i = 1; i < points.length; i++) {
      for (const p of [points[i - 1], points[i]]) { positions.push(p[0], .39, p[2]); owners.push(m); colours.push(.3, .3, .3); }
    }
  }
  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  lineGeometry.setAttribute('color', new THREE.Float32BufferAttribute(colours, 3));
  const paths = new THREE.LineSegments(lineGeometry, new THREE.LineBasicMaterial({vertexColors: true}));
  paths.name = 'Controlled movement paths'; group.add(paths);
  // --- poles ----------------------------------------------------------------
  const poles = layer.poles, heads = layer.heads;
  const poleGeometry = new THREE.CylinderGeometry(.07, .09, 1, 8); poleGeometry.translate(0, .5, 0);
  const poleMesh = new THREE.InstancedMesh(poleGeometry, new THREE.MeshStandardMaterial({color: '#5b6166', roughness: .8}), poles.length);
  poleMesh.name = 'Signal poles'; poleMesh.frustumCulled = false;
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), s = new THREE.Vector3();
  poles.forEach((p, i) => { m4.compose(v.set(p.world_xyz[0], p.world_xyz[1], p.world_xyz[2]), q.identity(), s.set(1, p.height_m, 1)); poleMesh.setMatrixAt(i, m4); });
  poleMesh.instanceMatrix.needsUpdate = true; group.add(poleMesh);
  // bracket arm from the pole to each head (thin box)
  const armGeometry = new THREE.BoxGeometry(1, .05, .05); armGeometry.translate(.5, 0, 0);
  const armMesh = new THREE.InstancedMesh(armGeometry, new THREE.MeshStandardMaterial({color: '#5b6166', roughness: .8}), heads.length);
  armMesh.name = 'Signal brackets'; armMesh.frustumCulled = false;
  // --- heads: housing + three lamps -----------------------------------------
  const housingGeometry = new THREE.BoxGeometry(.36, 1.02, .28);
  const housingMesh = new THREE.InstancedMesh(housingGeometry, new THREE.MeshStandardMaterial({color: '#23272b', roughness: .6}), heads.length);
  housingMesh.name = 'Signal heads'; housingMesh.frustumCulled = false;
  const lampGeometry = new THREE.CircleGeometry(.12, 14);
  const lampMaterial = () => new THREE.MeshBasicMaterial({color: '#ffffff', toneMapped: false});
  const lamps = [0, 1, 2].map(k => { const mesh = new THREE.InstancedMesh(lampGeometry, lampMaterial(), heads.length); mesh.name = ['Red lamps', 'Amber lamps', 'Green lamps'][k]; mesh.frustumCulled = false; return mesh; });
  const up = new THREE.Vector3(0, 1, 0), tmp = new THREE.Vector3();
  heads.forEach((h, i) => {
    const pole = poles[h.pole];
    q.setFromAxisAngle(up, h.yaw_rad);
    m4.compose(v.set(h.world_xyz[0], h.world_xyz[1], h.world_xyz[2]), q, s.set(1, 1, 1)); housingMesh.setMatrixAt(i, m4);
    // lamps sit just in front of the housing face (+Z local faces approaching traffic)
    [.32, 0, -.32].forEach((dy, k) => {
      tmp.set(0, dy, .15).applyQuaternion(q);
      m4.compose(v.set(h.world_xyz[0] + tmp.x, h.world_xyz[1] + tmp.y, h.world_xyz[2] + tmp.z), q, s.set(1, 1, 1)); lamps[k].setMatrixAt(i, m4);
      lamps[k].setColorAt(i, [OFF_RED, OFF_AMBER, OFF_GREEN][k]);
    });
    // bracket: from the pole axis to the head, horizontal
    const dx = h.world_xyz[0] - pole.world_xyz[0], dz = h.world_xyz[2] - pole.world_xyz[2], len = Math.hypot(dx, dz) || .01;
    q.setFromAxisAngle(up, Math.atan2(-dz, dx));
    m4.compose(v.set(pole.world_xyz[0], h.world_xyz[1] + .45, pole.world_xyz[2]), q, s.set(len, 1, 1)); armMesh.setMatrixAt(i, m4);
  });
  housingMesh.instanceMatrix.needsUpdate = true; armMesh.instanceMatrix.needsUpdate = true;
  for (const l of lamps) { l.instanceMatrix.needsUpdate = true; l.instanceColor.needsUpdate = true; }
  group.add(armMesh, housingMesh, ...lamps); scene.add(group);
  let previous = -1, hasRecordedFrame = false, enabled = true, showPaths = true;
  const sorted = frames.slice().sort((a, b) => a.t - b.t);
  function frameAt(second) { // latest recorded row with t <= second
    let lo = 0, hi = sorted.length - 1, best = null;
    while (lo <= hi) { const mid = (lo + hi) >> 1; if (sorted[mid].t <= second) { best = sorted[mid]; lo = mid + 1; } else hi = mid - 1; }
    return best;
  }
  const stats = {heads: heads.length, poles: poles.length, movements: movements.length, lastFrameT: null};
  return {
    group, movements, heads, poles, stats,
    setVisible: value => { enabled = value; group.visible = enabled && hasRecordedFrame; },
    setPathsVisible: value => { showPaths = value; paths.visible = showPaths; },
    stateAt(t, head) { return stateOf(frameAt(Math.floor(t)), head); },
    update(t) {
      const second = Math.floor(t); if (previous === second) return; previous = second;
      const frame = frameAt(second);
      hasRecordedFrame = !!frame && second >= sorted[0]?.t;
      group.visible = hasRecordedFrame && enabled;
      if (!frame) return;
      stats.lastFrameT = frame.t;
      const attribute = lineGeometry.attributes.color;
      const movementColours = movements.map(m => {
        const value = frame.states[m.tls_id]?.[m.link_index];
        return value === 'r' || value === 'R' ? LINE_RED : value === 'y' || value === 'Y' ? LINE_AMBER : value === 'g' || value === 'G' ? LINE_GREEN : LINE_UNKNOWN;
      });
      owners.forEach((owner, i) => { const c = movementColours[owner]; attribute.setXYZ(i, c.r, c.g, c.b); });
      attribute.needsUpdate = true;
      heads.forEach((h, i) => {
        const value = stateOf(frame, h);
        const red = value === 'r' || value === 'R', amber = value === 'y' || value === 'Y', green = value === 'g' || value === 'G';
        lamps[0].setColorAt(i, red ? RED : OFF_RED); lamps[1].setColorAt(i, amber ? AMBER : OFF_AMBER); lamps[2].setColorAt(i, green ? GREEN : OFF_GREEN);
      });
      for (const l of lamps) l.instanceColor.needsUpdate = true;
    },
  };
}
