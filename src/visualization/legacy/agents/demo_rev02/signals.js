import * as THREE from 'three';

// Each coloured path represents one controlled turning movement. These are
// model indicators, not surveyed traffic-light poles or live TfL phases.
export function createSignalLayer(scene, geometry, frames) {
  const positions = [], owners = [], colours = [];
  const movements = geometry.movements;
  for (let m = 0; m < movements.length; m++) {
    const points = movements[m].world_shape_xyz;
    for (let i = 1; i < points.length; i++) {
      for (const p of [points[i - 1], points[i]]) {
        positions.push(p[0], .39, p[2]); owners.push(m); colours.push(.3, .3, .3);
      }
    }
  }
  const geometryLines = new THREE.BufferGeometry();
  geometryLines.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometryLines.setAttribute('color', new THREE.Float32BufferAttribute(colours, 3));
  const paths = new THREE.LineSegments(geometryLines, new THREE.LineBasicMaterial({vertexColors: true}));
  const group = new THREE.Group(); group.name = 'Simulated movement signals'; group.add(paths); scene.add(group);
  let previous = -1, hasRecordedFrame = false, enabled = true;
  const red = new THREE.Color('#ef4545'), amber = new THREE.Color('#ffbf38'), green = new THREE.Color('#29d68f'), unknown = new THREE.Color('#687b83');
  return {
    group,
    movements,
    setVisible: value => {enabled = value; group.visible = enabled && hasRecordedFrame;},
    update(t) {
      const second = Math.floor(t); if (previous === second) return; previous = second;
      const frame = frames.find(f => f.t === second);
      // No fabricated state before the first recorded signal frame.
      hasRecordedFrame = !!frame;
      group.visible = hasRecordedFrame && enabled;
      if (!frame) return;
      const movementColours = movements.map(m => {
        const value = frame.states[m.tls_id]?.[m.link_index];
        return value === 'r' ? red : value === 'y' || value === 'Y' ? amber : value === 'g' || value === 'G' ? green : unknown;
      });
      const attribute = geometryLines.attributes.color;
      owners.forEach((owner, i) => {const c = movementColours[owner]; attribute.setXYZ(i, c.r, c.g, c.b);});
      attribute.needsUpdate = true;
    },
  };
}
