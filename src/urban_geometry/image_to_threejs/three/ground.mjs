// Ground layers: base terrain, land use, water, roads, rails, walls and trees.
import * as THREE from 'three';
import { instance } from './assets.mjs';
import { MeshBatch, box, cap, ground, mat, road } from './kit.mjs';

// Draw order by small vertical offsets (metres) so coplanar layers never z-fight.
const Z = { base: 0, area: 0.04, water: 0.075, pavement: 0.1, path: 0.13, rail: 0.14, road: 0.16 };
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

/**
 * Split polylines into runs that avoid `cutouts` (boxes of landmark structures such
 * as bridges): a segment is dropped when both ends lie in a cutout and its midpoint
 * is over mapped water, so riverside roads inside the same box are kept.
 */
function avoidCutouts(ways, cutouts, water) {
  if (!cutouts?.length) return ways;
  const inBox = (p) =>
    cutouts.some((c) => p[0] >= c.x0 && p[0] <= c.x1 && p[1] >= c.y0 && p[1] <= c.y1);
  const wet = (p) => water.some((w) => w.poly && pointIn(w.poly[0], p[0], p[1]));
  const out = [];
  for (const way of ways) {
    let run = [way.line[0]];
    for (let k = 1; k < way.line.length; k++) {
      const a = way.line[k - 1],
        b = way.line[k];
      const cut = inBox(a) && inBox(b) && wet([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
      if (cut) {
        if (run.length > 1) out.push({ ...way, line: run });
        run = [b];
      } else run.push(b);
    }
    if (run.length > 1) out.push({ ...way, line: run });
  }
  return out;
}

export function buildGround(scene, { bounds, cutouts } = {}) {
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
  const roads = avoidCutouts(scene.roads, cutouts, scene.water)
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
  for (const r of avoidCutouts(scene.rails, cutouts, scene.water)) {
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

/**
 * Cell grids of building rings and road segments, cached per scene, so scattered
 * trees stay out of footprints and off roads and paths.
 */
const exclusionCache = new WeakMap();
function exclusionGrids(scene) {
  if (exclusionCache.has(scene)) return exclusionCache.get(scene);
  const cell = 50,
    grid = new Map();
  for (const b of scene.buildings)
    for (const poly of b.polys) {
      const xs = poly[0].map((p) => p[0]),
        ys = poly[0].map((p) => p[1]);
      for (let i = Math.floor(Math.min(...xs) / cell); i <= Math.floor(Math.max(...xs) / cell); i++)
        for (
          let j = Math.floor(Math.min(...ys) / cell);
          j <= Math.floor(Math.max(...ys) / cell);
          j++
        ) {
          const key = `${i},${j}`;
          if (!grid.has(key)) grid.set(key, []);
          grid.get(key).push(poly[0]);
        }
    }
  const ways = new Map();
  for (const r of scene.roads)
    for (let k = 1; k < r.line.length; k++) {
      const a = r.line[k - 1],
        b = r.line[k];
      for (
        let i = Math.floor(Math.min(a[0], b[0]) / cell);
        i <= Math.floor(Math.max(a[0], b[0]) / cell);
        i++
      )
        for (
          let j = Math.floor(Math.min(a[1], b[1]) / cell);
          j <= Math.floor(Math.max(a[1], b[1]) / cell);
          j++
        ) {
          const key = `${i},${j}`;
          if (!ways.has(key)) ways.set(key, []);
          ways.get(key).push([a, b, r.w / 2 + 1.5]);
        }
    }
  const out = { cell, grid, ways };
  exclusionCache.set(scene, out);
  return out;
}

/** Instanced trees from mapped points plus scattered trees in parks and woods. */
export function buildTrees(scene, { bounds, assets, detail = 'high', cutouts } = {}) {
  const pts = scene.trees.filter((t) => inside(t, bounds)).map(([x, y, s]) => [x, y, s]);
  let seed = 1;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const { cell, grid, ways } = exclusionGrids(scene);
  const onWay = (x, y) =>
    (ways.get(`${Math.floor(x / cell)},${Math.floor(y / cell)}`) ?? []).some(([a, b, clear]) => {
      const dx = b[0] - a[0],
        dy = b[1] - a[1];
      const t = Math.max(
        0,
        Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy || 1)),
      );
      return Math.hypot(x - a[0] - t * dx, y - a[1] - t * dy) < clear;
    });
  const keepOut = (x, y) =>
    (cutouts ?? []).some((c) => x >= c.x0 && x <= c.x1 && y >= c.y0 && y <= c.y1);
  const built = (x, y) =>
    (grid.get(`${Math.floor(x / cell)},${Math.floor(y / cell)}`) ?? []).some((ring) =>
      pointIn(ring, x, y),
    );
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
        if (built(px, py) || onWay(px, py) || keepOut(px, py)) continue;
        pts.push([px, py, rand()]);
      }
  }
  // Species mix from the resources/vegetation library (shares sum to 1; heights in m).
  const species = [
    { id: 'london_plane', share: 0.4, h: [13, 26] },
    { id: 'lime_tree', share: 0.18, h: [11, 20] },
    { id: 'horse_chestnut', share: 0.14, h: [10, 18] },
    { id: 'silver_birch', share: 0.1, h: [9, 16] },
    { id: 'english_oak', share: 0.08, h: [10, 19] },
    { id: 'conifer', share: 0.1, h: [8, 15] },
  ];
  const group = new THREE.Group();
  group.name = 'trees';
  const buckets = species.map(() => []);
  for (const p of pts) {
    let r = (p[2] * 997) % 1,
      k = 0;
    while (k < species.length - 1 && r >= species[k].share) r -= species[k++].share;
    buckets[k].push([p[0], p[1], p[2] * 6.283, p[2]]);
  }
  buckets.forEach((list, k) => {
    const sp = species[k];
    group.add(
      instance(assets.get(sp.id), list, {
        name: `trees:${sp.id}`,
        detail,
        scaleOf: (p) => sp.h[0] + (sp.h[1] - sp.h[0]) * ((p[3] * 7.13) % 1),
      }),
    );
  });
  group.userData.count = pts.length;
  return group;
}

/** Street furniture: mapped (and procedural lamp) placements from the library. */
export function buildFurniture(scene, { bounds, assets, detail = 'high' } = {}) {
  const group = new THREE.Group();
  group.name = 'street_furniture';
  for (const [id, list] of Object.entries(scene.placements ?? {})) {
    const def = assets.get(id);
    if (!def) throw new Error(`No resources asset for placement '${id}'`);
    group.add(
      instance(
        def,
        list.filter((p) => inside(p, bounds)),
        { name: `furniture:${id}`, detail },
      ),
    );
  }
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
