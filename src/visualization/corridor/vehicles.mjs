import { recordedSampler } from './replay.mjs';
// Illustrative dimensions, shared with rebuild_corridor.VEHICLES; not measured fleet data.
export const vehicleSpecs = {
  car: { length: 4.5, width: 1.8, height: 1.5, color: 0x355d89 },
  taxi: { length: 4.8, width: 1.9, height: 1.9, color: 0x24272a },
  bus: { length: 10.5, width: 2.55, height: 4.4, color: 0xc72b2b },
  lgv: { length: 5.5, width: 2, height: 2.5, color: 0xd9ddd9 },
  hgv: { length: 10.5, width: 2.55, height: 3.6, color: 0xe1bb72 },
  motorcycle: { length: 2.2, width: 0.8, height: 1.4, color: 0x35424a },
};
function parts(THREE, type, spec) {
  const { length: l, width: w, height: h, color } = spec;
  const result = [];
  function box(width, length, height, x, y, z, c) {
    const geometry = new THREE.BoxGeometry(width, length, height);
    geometry.translate(x, y, z);
    result.push({
      geometry,
      material: new THREE.MeshStandardMaterial({ color: c, roughness: 0.65 }),
    });
  }
  if (type === 'motorcycle') {
    box(0.32, l * 0.58, 0.45, 0, 0, 0.62, color);
    box(0.45, 0.5, 0.65, 0, -0.1, 1.02, 0x242a32); // rider
    box(0.28, 0.28, 0.27, 0, 0.02, h - 0.135, 0xf1ca56); // helmet
  } else if (type === 'bus') {
    box(w, l, h - 0.45, 0, 0, (h + 0.45) / 2, color);
    for (const z of [1.5, 3.2])
      for (const x of [-1, 1]) box(0.025, l * 0.85, 0.8, (x * w) / 2, 0, z, 0x263d4d);
    box(w * 0.88, 0.03, 1.05, 0, l / 2, 1.6, 0x263d4d);
  } else if (type === 'lgv' || type === 'hgv') {
    box(w, l * 0.7, h - 0.5, 0, -l * 0.15, (h + 0.5) / 2, color);
    box(
      w * 0.95,
      l * 0.27,
      h * 0.62,
      0,
      l * 0.35,
      h * 0.31 + 0.4,
      type === 'hgv' ? 0x31628d : color,
    );
    box(w * 0.8, 0.03, 0.65, 0, l * 0.486, h * 0.62, 0x263d4d);
  } else {
    box(w, l, 0.65, 0, 0, 0.7, color);
    box(w * 0.85, l * 0.55, h - 0.9, 0, -0.05, (h + 0.9) / 2, 0x263d4d);
    box(w * 0.87, l * 0.55, 0.08, 0, -0.05, h, color);
  }
  const radius = type === 'motorcycle' ? 0.32 : type === 'bus' || type === 'hgv' ? 0.45 : 0.32;
  const wheelY = type === 'motorcycle' ? [-l * 0.35, l * 0.35] : [-l * 0.32, l * 0.32];
  for (const y of wheelY)
    for (const x of type === 'motorcycle' ? [0] : [-w / 2 + 0.1, w / 2 - 0.1]) {
      const geometry = new THREE.CylinderGeometry(
        radius,
        radius,
        type === 'motorcycle' ? 0.17 : 0.2,
        8,
      );
      geometry.rotateZ(Math.PI / 2);
      geometry.translate(x, y, radius);
      result.push({
        geometry,
        material: new THREE.MeshStandardMaterial({ color: 0x191c20, roughness: 0.9 }),
      });
    }
  return result;
}
export function createVehicles(THREE, data, groundHeight) {
  const { meta, frames } = data,
    group = new THREE.Group(),
    sets = {};
  group.name = 'traffic';
  const types = meta.vehicles.map((vehicle) => vehicle.type);
  const capacities = {};
  for (const frame of frames) {
    const count = {};
    for (const id of frame.idx) {
      const type = types[id];
      count[type] = (count[type] || 0) + 1;
    }
    for (const [type, n] of Object.entries(count))
      capacities[type] = Math.max(capacities[type] || 0, n);
  }
  for (const [type, n] of Object.entries(capacities)) {
    const spec = vehicleSpecs[type];
    if (!spec) throw new Error(`Unsupported vehicle type ${type}`);
    sets[type] = parts(THREE, type, spec).map(({ geometry, material }) => {
      const mesh = new THREE.InstancedMesh(geometry, material, n);
      mesh.frustumCulled = false;
      mesh.count = 0;
      mesh.userData.vehicleType = type;
      group.add(mesh);
      return mesh;
    });
  }
  const sample = recordedSampler(frames, meta.dt),
    matrix = new THREE.Matrix4(),
    position = new THREE.Vector3(),
    rotation = new THREE.Quaternion(),
    axis = new THREE.Vector3(0, 0, 1),
    scale = new THREE.Vector3(1, 1, 1);
  const duration = (frames.length - 1) * meta.dt;
  let visibleSamples = {};
  return {
    group,
    dispose() {
      for (const mesh of group.children) {
        mesh.dispose();
        mesh.geometry.dispose();
        mesh.material.dispose();
      }
    },
    meta,
    duration,
    pick(raycaster) {
      const hit = raycaster.intersectObjects(group.children, false)[0];
      if (!hit) return null;
      const point = visibleSamples[hit.object.userData.vehicleType]?.[hit.instanceId];
      return point
        ? { ...point, ...meta.vehicles[point.id], spec: vehicleSpecs[meta.vehicles[point.id].type] }
        : null;
    },
    update(time) {
      const counts = {};
      visibleSamples = {};
      for (const point of sample(time)) {
        const type = types[point.id],
          spec = vehicleSpecs[type],
          index = counts[type] || 0;
        const x = point.x - (Math.cos(point.heading) * spec.length) / 2,
          y = point.y - (Math.sin(point.heading) * spec.length) / 2;
        position.set(x, y, (point.z ?? groundHeight(x, y)) + 0.08);
        rotation.setFromAxisAngle(axis, point.heading - Math.PI / 2);
        matrix.compose(position, rotation, scale);
        for (const mesh of sets[type]) mesh.setMatrixAt(index, matrix);
        counts[type] = index + 1;
        (visibleSamples[type] ??= []).push(point);
      }
      for (const [type, meshes] of Object.entries(sets))
        for (const mesh of meshes) {
          mesh.count = counts[type] || 0;
          mesh.instanceMatrix.needsUpdate = true;
        }
      return {
        time: meta.t0 + time,
        count: Object.values(counts).reduce((a, b) => a + b, 0),
        counts,
      };
    },
  };
}
