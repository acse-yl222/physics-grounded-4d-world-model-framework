// Ground layers: base terrain, land use, water, roads, rails, walls and trees.
import * as THREE from 'three';
import { MeshBatch, box, cap, ground, mat, road } from './kit.mjs';

// Draw order by small vertical offsets (metres) so coplanar layers never z-fight.
const Z = { base: 0, area: 0.04, water: 0.06, pavement: 0.1, path: 0.13, rail: 0.14, road: 0.16 };
const ROAD_KIND = {
  motorway: 'major',
  trunk: 'major',
  primary: 'major',
  secondary: 'major',
  tertiary: 'minor',
  residential: 'minor',
  unclassified: 'minor',
  living_street: 'minor',
  unknown: 'minor',
  service: 'service',
  pedestrian: 'footway',
  footway: 'footway',
  path: 'path',
  track: 'path',
  bridleway: 'path',
  cycleway: 'cycleway',
  steps: 'steps',
};
const RANK = { major: 4, minor: 3, service: 2, cycleway: 1, footway: 0, path: 0, steps: 0 };
const AREA_RANK = {
  base: 0,
  residential: 0,
  bare: 1,
  railway: 1,
  parking: 2,
  plaza: 2,
  park: 3,
  grass: 4,
  cemetery: 4,
  allotments: 4,
  scrub: 5,
  wood: 5,
  wetland: 5,
  sand: 5,
  pitch: 6,
  playground: 6,
  track: 6,
};
export const DECK_M = 6.5; // elevation per OSM layer level for bridges / flyovers

function inside(p, b) {
  return !b || (p[0] >= b.x0 && p[0] < b.x1 && p[1] >= b.y0 && p[1] < b.y1);
}

/**
 * Ribbon along a polyline: u across (0..1), v along (metres / vScale).
 * Miter joins are clamped; z may be a number or a function of the vertex index.
 */
export function ribbon(batch, material, line, width, z, { vScale = 16, side = null } = {}) {
  const n = line.length;
  if (n < 2) return;
  const half = width / 2;
  const left = [],
    right = [],
    vs = [0];
  for (let k = 0; k < n; k++) {
    const a = line[Math.max(0, k - 1)],
      b = line[k],
      c = line[Math.min(n - 1, k + 1)];
    let d1x = b[0] - a[0],
      d1y = b[1] - a[1],
      d2x = c[0] - b[0],
      d2y = c[1] - b[1];
    const l1 = Math.hypot(d1x, d1y) || 1,
      l2 = Math.hypot(d2x, d2y) || 1;
    if (k === 0) [d1x, d1y] = [d2x, d2y];
    if (k === n - 1) [d2x, d2y] = [d1x, d1y];
    const n1 = [-d1y / (k === 0 ? l2 : l1), d1x / (k === 0 ? l2 : l1)];
    const n2 = [-d2y / (k === n - 1 ? l1 : l2), d2x / (k === n - 1 ? l1 : l2)];
    let mx = n1[0] + n2[0],
      my = n1[1] + n2[1];
    const ml = Math.hypot(mx, my) || 1;
    mx /= ml;
    my /= ml;
    const cos = Math.max(0.5, mx * n1[0] + my * n1[1]);
    const zz = typeof z === 'function' ? z(k) : z;
    left.push([b[0] + (mx * half) / cos, b[1] + (my * half) / cos, zz]);
    right.push([b[0] - (mx * half) / cos, b[1] - (my * half) / cos, zz]);
    if (k > 0) vs.push(vs[k - 1] + Math.hypot(b[0] - line[k - 1][0], b[1] - line[k - 1][1]));
  }
  for (let k = 0; k < n - 1; k++) {
    const v0 = vs[k] / vScale,
      v1 = vs[k + 1] / vScale;
    batch.quad(
      material,
      right[k],
      right[k + 1],
      left[k + 1],
      left[k],
      [1, v0],
      [1, v1],
      [0, v1],
      [0, v0],
    );
  }
  if (side) {
    // Vertical side skirts for elevated decks (to `side.bottom`).
    for (const edge of [left, right.slice().reverse()]) {
      for (let k = 0; k < edge.length - 1; k++) {
        const a = edge[k],
          b = edge[k + 1];
        batch.quad(
          side.material,
          [a[0], a[1], a[2] + 0.9],
          [b[0], b[1], b[2] + 0.9],
          [b[0], b[1], b[2] - side.depth],
          [a[0], a[1], a[2] - side.depth],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
  }
}

/** Disc at junction ends so road ribbons join without notches. */
function disc(batch, material, p, r, z, segments = 10) {
  const verts = [[p[0], p[1], z]],
    uvs = [[0.5, 0]],
    idx = [];
  for (let k = 0; k <= segments; k++) {
    const a = (k / segments) * Math.PI * 2;
    verts.push([p[0] + Math.cos(a) * r, p[1] + Math.sin(a) * r, z]);
    uvs.push([0.5, 0]);
    if (k) idx.push(0, k, k + 1);
  }
  batch.add(material, verts, uvs, idx);
}

function clipLine(line, b) {
  return !b || line.some((p) => inside(p, b));
}

export function buildGround(scene, { bounds } = {}) {
  const batch = new MeshBatch();
  const H = scene.half_m;
  const b = bounds ?? { x0: -H, y0: -H, x1: H, y1: H };
  cap(
    batch,
    ground('base'),
    [
      [
        [
          [b.x0, b.y0],
          [b.x1, b.y0],
          [b.x1, b.y1],
          [b.x0, b.y1],
        ],
      ],
    ],
    Z.base,
    { scale: 40 },
  );

  const areas = scene.areas
    .filter((a) => a.poly[0].some((p) => inside(p, bounds)))
    .sort((p, q) => (AREA_RANK[p.kind] ?? 1) - (AREA_RANK[q.kind] ?? 1));
  for (const a of areas) {
    const z = Z.area + (AREA_RANK[a.kind] ?? 1) * 0.004;
    cap(batch, ground(a.kind), [a.poly], z, { scale: a.kind === 'pitch' ? 30 : 20 });
  }
  for (const w of scene.water) {
    if (w.poly && w.poly[0].some((p) => inside(p, bounds)))
      cap(batch, ground('water'), [w.poly], Z.water, { scale: 30 });
    else if (w.line && clipLine(w.line, bounds))
      ribbon(batch, ground('water'), w.line, w.w, Z.water);
  }

  const deck = mat('dark_concrete');
  const roads = scene.roads
    .filter((r) => clipLine(r.line, bounds))
    .sort((p, q) => (RANK[ROAD_KIND[p.cls]] ?? 0) - (RANK[ROAD_KIND[q.cls]] ?? 0));
  // Pavements first, under carriageways.
  for (const r of roads) {
    const kind = ROAD_KIND[r.cls] ?? 'minor';
    if (r.level || !['major', 'minor'].includes(kind)) continue;
    ribbon(batch, road('pavement'), r.line, r.w + 5, Z.pavement, { vScale: 8 });
  }
  for (const r of roads) {
    const kind = ROAD_KIND[r.cls] ?? 'minor';
    const rank = RANK[kind] ?? 0;
    const lifted = r.level > 0 && ['major', 'minor', 'service'].includes(kind);
    const zBase = lifted ? r.level * DECK_M : rank > 1 ? Z.road + rank * 0.004 : Z.path;
    ribbon(batch, road(kind), r.line, r.w, zBase, {
      vScale: kind === 'steps' ? 4 : 16,
      side: lifted ? { material: deck, depth: 1.2 } : null,
    });
    if (lifted) {
      // Piers every ~35 m along flyovers.
      let acc = 0;
      for (let k = 1; k < r.line.length; k++) {
        const p = r.line[k - 1],
          q = r.line[k];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        for (let t = (35 - acc) / len; t < 1; t += 35 / len)
          if (t >= 0)
            box(
              batch,
              deck,
              p[0] + (q[0] - p[0]) * t,
              p[1] + (q[1] - p[1]) * t,
              0,
              1.6,
              Math.min(r.w * 0.6, 8),
              zBase - 1.2,
              Math.atan2(q[1] - p[1], q[0] - p[0]),
            );
        acc = (acc + len) % 35;
      }
    } else if (rank >= 3) {
      for (const end of [r.line[0], r.line[r.line.length - 1]])
        disc(batch, road(kind), end, r.w / 2, zBase - 0.002);
    }
  }
  for (const r of scene.rails) {
    if (!clipLine(r.line, bounds)) continue;
    const z = r.level ? r.level * DECK_M : Z.rail;
    ribbon(batch, road('rail'), r.line, 3.4, z, {
      vScale: 6,
      side: r.level ? { material: mat('london_stock'), depth: z } : null,
    });
  }
  // Boundary walls and hedges.
  const fx = scene.fixtures ?? {};
  const wallMat = mat('london_stock'),
    hedgeMat = mat('dark_foliage');
  for (const [cls, material, h, t] of [
    ['wall', wallMat, 1.8, 0.3],
    ['retaining_wall', mat('concrete'), 1.2, 0.4],
    ['hedge', hedgeMat, 1.5, 0.9],
  ])
    for (const line of fx[cls] ?? []) {
      if (!clipLine(line, bounds)) continue;
      for (let k = 1; k < line.length; k++) {
        const p = line[k - 1],
          q = line[k];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 0.3) continue;
        box(
          batch,
          material,
          (p[0] + q[0]) / 2,
          (p[1] + q[1]) / 2,
          0,
          len + t * 0.5,
          t,
          h,
          Math.atan2(q[1] - p[1], q[0] - p[0]),
        );
      }
    }
  const group = batch.toGroup('ground');
  group.traverse((o) => {
    if (o.isMesh) o.userData.flat = true;
  });
  return group;
}

/** Instanced trees from mapped points plus scattered trees in parks and woods. */
export function buildTrees(scene, { bounds, skipNear = [] } = {}) {
  const pts = scene.trees.filter((t) => inside(t, bounds)).map(([x, y, s]) => [x, y, s]);
  let seed = 1;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  for (const a of scene.areas) {
    const spacing = { wood: 9, park: 24, cemetery: 20, scrub: 14, grass: 45 }[a.kind];
    if (!spacing) continue;
    const ring = a.poly[0];
    let x0 = Infinity,
      y0 = Infinity,
      x1 = -Infinity,
      y1 = -Infinity;
    for (const [x, y] of ring) {
      x0 = Math.min(x0, x);
      y0 = Math.min(y0, y);
      x1 = Math.max(x1, x);
      y1 = Math.max(y1, y);
    }
    if (bounds && (x1 < bounds.x0 || x0 >= bounds.x1 || y1 < bounds.y0 || y0 >= bounds.y1))
      continue;
    const contour = ring.map(([x, y]) => new THREE.Vector2(x, y));
    const holes = a.poly.slice(1).map((r) => r.map(([x, y]) => new THREE.Vector2(x, y)));
    const shape = new THREE.Shape(contour);
    shape.holes = holes.map((h) => new THREE.Path(h));
    for (let x = x0; x < x1; x += spacing)
      for (let y = y0; y < y1; y += spacing) {
        const px = x + rand() * spacing,
          py = y + rand() * spacing;
        if (rand() < 0.35 || !inside([px, py], bounds)) continue;
        if (!pointIn(ring, px, py) || a.poly.slice(1).some((h) => pointIn(h, px, py))) continue;
        pts.push([px, py, rand()]);
      }
  }
  const species = [
    { crown: mat('foliage'), scale: 1 },
    { crown: mat('dark_foliage'), scale: 1.15 },
    { crown: mat('#5d8a45'), scale: 0.85 },
  ];
  const crownGeo = new THREE.IcosahedronGeometry(1, 1);
  const trunkGeo = new THREE.CylinderGeometry(0.18, 0.28, 1, 6)
    .rotateX(Math.PI / 2)
    .translate(0, 0, 0.5);
  const group = new THREE.Group();
  group.name = 'trees';
  const m = new THREE.Matrix4(),
    q = new THREE.Quaternion(),
    up = new THREE.Vector3(0, 0, 1);
  const buckets = species.map(() => []);
  for (const p of pts) buckets[Math.floor(p[2] * 997) % species.length].push(p);
  buckets.forEach((list, si) => {
    if (!list.length) return;
    const crowns = new THREE.InstancedMesh(crownGeo, species[si].crown, list.length);
    const trunks = new THREE.InstancedMesh(trunkGeo, mat('bark'), list.length);
    crowns.name = `tree_crowns_${si}`;
    trunks.name = `tree_trunks_${si}`;
    list.forEach(([x, y, s], k) => {
      const h = (8 + s * 10) * species[si].scale,
        r = h * 0.32;
      q.setFromAxisAngle(up, s * 6.28);
      m.compose(new THREE.Vector3(x, y, h - r * 0.9), q, new THREE.Vector3(r, r, r * 1.1));
      crowns.setMatrixAt(k, m);
      m.compose(new THREE.Vector3(x, y, 0), q, new THREE.Vector3(1, 1, h - r * 1.4));
      trunks.setMatrixAt(k, m);
    });
    group.add(crowns, trunks);
  });
  group.userData.count = pts.length;
  return group;
}

function pointIn(ring, x, y) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i],
      [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}
