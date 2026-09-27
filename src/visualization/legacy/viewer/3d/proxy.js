import * as THREE from 'three';

/* Lite city: extruded 4 m voxel columns built from the building footprint and roof-height masks (2 MB of data instead of the
   254 MB packed model). Used on phones / tablets / low-memory machines (?lite=1 forces it, ?lite=0 forces the full model).
   Same frame as everything else: column c -> X = X0 + c*CELL, row r (0 = south) -> Z from ZS - r*CELL down to ZS - (r+1)*CELL.
   Cells in a row with the same height are merged into one box; the bottom face is skipped. */
export function buildProxyCity({ footprint, roof, W, H, CELL, X0, ZS }) {
  const pos = [], nrm = [], col = [], idx = [];
  let boxes = 0;
  const shade = () => 0.58 + Math.random() * 0.12;
  function box(x0, x1, z0, z1, h, g) {
    const b = pos.length / 3;
    // 8 corners: bottom 0-3 (y=0), top 4-7 (y=h); z0 < z1
    const P = [[x0, 0, z0], [x1, 0, z0], [x1, 0, z1], [x0, 0, z1], [x0, h, z0], [x1, h, z0], [x1, h, z1], [x0, h, z1]];
    const faces = [ // [corner ids], normal
      [[4, 5, 6, 7], [0, 1, 0]],        // top
      [[0, 1, 5, 4], [0, 0, -1]],       // north wall (z0 side)
      [[1, 2, 6, 5], [1, 0, 0]],        // east
      [[2, 3, 7, 6], [0, 0, 1]],        // south (z1 side)
      [[3, 0, 4, 7], [-1, 0, 0]],       // west
    ];
    for (const [ids, n] of faces) {
      const s = pos.length / 3, top = n[1] === 1, gg = top ? g * 1.06 : g;
      for (const i of ids) { pos.push(...P[i]); nrm.push(...n); col.push(gg * 0.98, gg, gg * 1.02); }
      idx.push(s, s + 1, s + 2, s, s + 2, s + 3);
    }
    boxes++;
  }
  for (let r = 0; r < H; r++) {
    const z1 = ZS - r * CELL, z0 = z1 - CELL;   // z0 north edge, z1 south edge
    let c = 0;
    while (c < W) {
      const i = r * W + c;
      if (!footprint[i]) { c++; continue; }
      const h = Math.max(3, roof[i] || 0); let c1 = c;
      while (c1 + 1 < W && footprint[r * W + c1 + 1] && Math.abs((roof[r * W + c1 + 1] || 0) - (roof[i] || 0)) < 0.5) c1++;
      box(X0 + c * CELL, X0 + (c1 + 1) * CELL, z0, z1, h, shade());
      c = c1 + 1;
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  const mesh = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true }));
  mesh.name = `Lite city · ${boxes} voxel columns`;
  mesh.userData.proxy = true;
  return { mesh, boxes, triangles: idx.length / 3 };
}
