// Ground layers: base terrain, land use, water, roads, rails, walls and trees.
import * as THREE from 'three';
import { instance } from './assets.mjs';
import { MeshBatch, box, cap, ground, mat, road } from './kit.mjs';
import { elevationFn, terrainOf } from './terrain.mjs';

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
// Terrain draping (scenes with scene.terrain only): maximum edge length of draped
// ribbons, caps and walls, how far the base heightfield sits under the draped layers
// and how far it is lowered below a water body's level.
export const DRAPE_M = 10;
// Walls and hedges are cut into boxes of at most this length on terrain.
export const WALL_DRAPE_M = 20;
// Draped area caps are refined until they are within this of the terrain surface.
export const CAP_TOLERANCE_M = 0.03;
const BASE_DROP_M = 0.3;
const WATER_DEPTH_M = 0.4;

function inside(p, b) {
  return !b || (p[0] >= b.x0 && p[0] < b.x1 && p[1] >= b.y0 && p[1] < b.y1);
}

/**
 * Ribbon along a polyline: u across (0..1), v along (metres / vScale).
 * Miter joins are clamped; z may be a number or a function of the vertex index.
 * `left`/`right` give per-vertex half widths on each side (overriding `width`);
 * segments listed in `skip` are left out.
 */
export function ribbon(
  batch,
  material,
  line,
  width,
  z,
  {
    vScale = 16,
    side = null,
    left: wl = null,
    right: wr = null,
    skip = null,
    drape = null,
    step = DRAPE_M,
    inner = null,
    centre = true,
  } = {},
) {
  const n = line.length;
  if (n < 2) return;
  if (drape)
    return drapedRibbon(
      batch,
      material,
      line,
      width,
      z,
      drape,
      step,
      vScale,
      wl,
      wr,
      skip,
      inner,
      centre,
    );
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
    const hl = wl ? wl[k] : width / 2,
      hr = wr ? wr[k] : width / 2;
    left.push([b[0] + (mx * hl) / cos, b[1] + (my * hl) / cos, zz]);
    right.push([b[0] - (mx * hr) / cos, b[1] - (my * hr) / cos, zz]);
    if (k > 0) vs.push(vs[k - 1] + Math.hypot(b[0] - line[k - 1][0], b[1] - line[k - 1][1]));
  }
  for (let k = 0; k < n - 1; k++) {
    if (skip?.has(k)) continue;
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
    for (const [edge, reversed] of [
      [left, false],
      [right.slice().reverse(), true],
    ]) {
      for (let k = 0; k < edge.length - 1; k++) {
        if (skip?.has(reversed ? n - 2 - k : k)) continue;
        const a = edge[k],
          b = edge[k + 1];
        // Skirt depth per vertex index (a number, or a function for decks over terrain).
        const da =
            typeof side.depth === 'function' ? side.depth(reversed ? n - 1 - k : k) : side.depth,
          db =
            typeof side.depth === 'function'
              ? side.depth(reversed ? n - 2 - k : k + 1)
              : side.depth;
        batch.quad(
          side.material,
          [a[0], a[1], a[2] + 0.9],
          [b[0], b[1], b[2] + 0.9],
          [b[0], b[1], b[2] - db],
          [a[0], a[1], a[2] - da],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
  }
}

/**
 * Ribbon draped on the terrain: the same miter outline as `ribbon`, cut at stations
 * at most `step` metres apart along the centreline, with cross-sections bending at
 * the centreline (unless `centre` is false, for narrow ways) and at the `inner` half widths ({left, right} per vertex or a
 * width), so a pavement shares every vertex of the carriageway drawn over it
 * (`inner.hollow` leaves out the pavement under the carriageway). Each
 * vertex sits at drape(x, y) + offset (z: number or function of the vertex index).
 */
function drapedRibbon(
  batch,
  material,
  line,
  width,
  z,
  drape,
  step,
  vScale,
  wl,
  wr,
  skip,
  inner,
  centre = true,
) {
  const n = line.length;
  const normal = [],
    vs = [0],
    off = [],
    cuts = [];
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
    normal.push([mx / cos, my / cos]);
    const hl = wl ? wl[k] : width / 2,
      hr = wr ? wr[k] : width / 2;
    // Signed offsets across the ribbon (left positive), right edge first.
    const il = Math.min(hl, inner ? (inner.left ? inner.left[k] : inner.width / 2) : hl),
      ir = Math.min(hr, inner ? (inner.right ? inner.right[k] : inner.width / 2) : hr);
    cuts.push(inner ? [-hr, -ir, 0, il, hl] : centre ? [-hr, 0, hl] : [-hr, hl]);
    off.push(typeof z === 'function' ? z(k) : z);
    if (k > 0) vs.push(vs[k - 1] + Math.hypot(b[0] - line[k - 1][0], b[1] - line[k - 1][1]));
  }
  const at = (k, d) => [line[k][0] + normal[k][0] * d, line[k][1] + normal[k][1] * d];
  for (let k = 0; k < n - 1; k++) {
    if (skip?.has(k)) continue;
    const m = Math.max(1, Math.ceil((vs[k + 1] - vs[k]) / step));
    const cs = cuts[k].length;
    const station = (t) => {
      const o = off[k] + (off[k + 1] - off[k]) * t,
        v = (vs[k] + (vs[k + 1] - vs[k]) * t) / vScale;
      const hl = cuts[k][cs - 1] + (cuts[k + 1][cs - 1] - cuts[k][cs - 1]) * t,
        hr = -(cuts[k][0] + (cuts[k + 1][0] - cuts[k][0]) * t);
      return cuts[k].map((d0, c) => {
        const p = at(k, d0),
          q = at(k + 1, cuts[k + 1][c]);
        const x = p[0] + (q[0] - p[0]) * t,
          y = p[1] + (q[1] - p[1]) * t;
        const d = d0 + (cuts[k + 1][c] - d0) * t;
        return { p: [x, y, drape(x, y) + o], u: hl + hr > 0 ? (hl - d) / (hl + hr) : 0.5, v };
      });
    };
    let s0 = station(0);
    for (let s = 1; s <= m; s++) {
      const s1 = station(s / m);
      for (let c = 0; c < cs - 1; c++) {
        // Zero-width bands (carriageway as wide as its pavement) are left out, and
        // so is the part of a pavement under its carriageway (inner.hollow).
        if (s0[c].u === s0[c + 1].u && s1[c].u === s1[c + 1].u) continue;
        if (inner?.hollow && (c === 1 || c === 2)) continue;
        batch.quad(
          material,
          s0[c].p,
          s1[c].p,
          s1[c + 1].p,
          s0[c + 1].p,
          [s0[c].u, s0[c].v],
          [s1[c].u, s1[c].v],
          [s1[c + 1].u, s1[c + 1].v],
          [s0[c + 1].u, s0[c + 1].v],
        );
      }
      s0 = s1;
    }
  }
}

/** Polyline with extra vertices so no segment is longer than `step`. */
export function densify(line, step = DRAPE_M, closed = false) {
  const out = [];
  const m = closed ? line.length : line.length - 1;
  for (let k = 0; k < m; k++) {
    const a = line[k],
      b = line[(k + 1) % line.length];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step));
    for (let s = 0; s < n; s++)
      out.push([a[0] + ((b[0] - a[0]) * s) / n, a[1] + ((b[1] - a[1]) * s) / n]);
  }
  if (!closed) out.push(line[line.length - 1]);
  return out;
}

/**
 * Horizontal cap of polygons draped on the terrain: rings densified to `step`,
 * triangulated, then triangles bisected along their longest edge (midpoints shared
 * between neighbours, so the surface has no cracks) until every edge is at most
 * `step`; vertices sit at drape(x, y) + z.
 */
export function drapedCap(
  batch,
  material,
  polys,
  z,
  drape,
  { scale = 8, step = DRAPE_M, tolerance = null, maxEdge = 40, minEdge = 2.5 } = {},
) {
  for (const poly of polys) {
    const rings = poly.map((r) => densify(r, step, true));
    const contour = rings[0].map(([x, y]) => new THREE.Vector2(x, y));
    const holes = rings.slice(1).map((r) => r.map(([x, y]) => new THREE.Vector2(x, y)));
    let tris;
    try {
      tris = THREE.ShapeUtils.triangulateShape(contour, holes);
    } catch {
      continue;
    }
    const pts = [...contour, ...holes.flat()].map((p) => [p.x, p.y]);
    const mid = new Map();
    const midpoint = (a, b) => {
      const key = a < b ? `${a},${b}` : `${b},${a}`;
      let m = mid.get(key);
      if (m === undefined) {
        m = pts.length;
        pts.push([(pts[a][0] + pts[b][0]) / 2, (pts[a][1] + pts[b][1]) / 2]);
        mid.set(key, m);
      }
      return m;
    };
    const d2 = (a, b) => (pts[a][0] - pts[b][0]) ** 2 + (pts[a][1] - pts[b][1]) ** 2;
    // With a tolerance, triangles are split only while they deviate from the terrain
    // (at edge midpoints and centroid) by more than it, or exceed maxEdge.
    const zOf = new Map();
    const h = (k) => {
      let v = zOf.get(k);
      if (v === undefined) zOf.set(k, (v = drape(pts[k][0], pts[k][1])));
      return v;
    };
    const off = (p, q, r, w) => {
      const x = w[0] * pts[p][0] + w[1] * pts[q][0] + w[2] * pts[r][0],
        y = w[0] * pts[p][1] + w[1] * pts[q][1] + w[2] * pts[r][1];
      return Math.abs(drape(x, y) - (w[0] * h(p) + w[1] * h(q) + w[2] * h(r)));
    };
    const W = [
      [0.5, 0.5, 0],
      [0, 0.5, 0.5],
      [0.5, 0, 0.5],
      [1 / 3, 1 / 3, 1 / 3],
    ];
    const needsSplit = (a, b, c, longest) =>
      longest > maxEdge * maxEdge ||
      (longest > minEdge * minEdge && W.some((w) => off(a, b, c, w) > tolerance));
    const limit = step * step,
      idx = [],
      stack = tris.map((t) => [t[0], t[1], t[2]]);
    while (stack.length) {
      const [a, b, c] = stack.pop();
      const ab = d2(a, b),
        bc = d2(b, c),
        ca = d2(c, a);
      const longest = Math.max(ab, bc, ca);
      if (tolerance === null ? longest <= limit : !needsSplit(a, b, c, longest)) {
        idx.push(a, b, c);
        continue;
      }
      if (longest === ab) {
        const m = midpoint(a, b);
        stack.push([a, m, c], [m, b, c]);
      } else if (longest === bc) {
        const m = midpoint(b, c);
        stack.push([a, b, m], [a, m, c]);
      } else {
        const m = midpoint(c, a);
        stack.push([a, b, m], [m, b, c]);
      }
    }
    const verts = pts.map(([x, y]) => [x, y, drape(x, y) + z]);
    const uvs = pts.map(([x, y]) => [x / scale, y / scale]);
    batch.add(material, verts, uvs, idx);
  }
}

/** Node coordinates of the terrain grid within [a, b], with a and b themselves. */
function axisNodes(a, b, x0, dx) {
  const out = [a];
  for (let k = Math.floor((a - x0) / dx) + 1; x0 + k * dx < b - 1e-6; k++)
    if (x0 + k * dx > a + 1e-6) out.push(x0 + k * dx);
  out.push(b);
  return out;
}

/**
 * Heightfield of the scene terrain over bounds {x0, y0, x1, y1}: one vertex per grid
 * node (plus the bounds edges), BASE_DROP_M under the draped layers and lowered under
 * mapped water bodies to WATER_DEPTH_M below their level. Empty for flat scenes.
 */
export function buildTerrain(scene, { bounds } = {}) {
  const batch = new MeshBatch();
  const grid = terrainOf(scene);
  const H = scene.half_m;
  const b = bounds ?? { x0: -H, y0: -H, x1: H, y1: H };
  if (grid) {
    const drape = elevationFn(scene);
    const xs = axisNodes(b.x0, b.x1, grid.x0, grid.dx),
      ys = axisNodes(b.y0, b.y1, grid.y0, grid.dx);
    const nx = xs.length,
      z = new Float32Array(nx * ys.length);
    ys.forEach((y, j) => xs.forEach((x, i) => (z[j * nx + i] = drape(x, y) - BASE_DROP_M)));
    for (const w of scene.water)
      if (w.poly && Number.isFinite(w.level))
        lowerUnder(w.poly, w.level - WATER_DEPTH_M, xs, ys, z);
    // Rows in chunks keep each batch.add call (and its index arrays) moderate.
    const rows = 64;
    for (let j0 = 0; j0 < ys.length - 1; j0 += rows) {
      const j1 = Math.min(ys.length - 1, j0 + rows);
      const verts = [],
        uvs = [],
        idx = [];
      for (let j = j0; j <= j1; j++)
        for (let i = 0; i < nx; i++) {
          verts.push([xs[i], ys[j], z[j * nx + i]]);
          uvs.push([xs[i] / 40, ys[j] / 40]);
        }
      for (let j = 0; j < j1 - j0; j++)
        for (let i = 0; i < nx - 1; i++) {
          const a = j * nx + i;
          idx.push(a, a + 1, a + nx + 1, a, a + nx + 1, a + nx);
        }
      batch.add(ground('base'), verts, uvs, idx);
    }
  }
  const group = batch.toGroup('terrain');
  group.traverse((o) => {
    if (o.isMesh) o.userData.flat = true;
  });
  return group;
}

/** Lower heightfield nodes inside a polygon (even-odd, holes excluded) to at most `top`. */
function lowerUnder(poly, top, xs, ys, z) {
  let y0 = Infinity,
    y1 = -Infinity;
  for (const [, y] of poly[0]) {
    y0 = Math.min(y0, y);
    y1 = Math.max(y1, y);
  }
  const nx = xs.length;
  ys.forEach((y, j) => {
    if (y < y0 || y > y1) return;
    const cuts = [];
    for (const ring of poly)
      for (let k = 0, m = ring.length - 1; k < ring.length; m = k++) {
        const [ax, ay] = ring[m],
          [bx, by] = ring[k];
        if (ay > y !== by > y) cuts.push(ax + ((y - ay) * (bx - ax)) / (by - ay));
      }
    cuts.sort((p, q) => p - q);
    for (let c = 0; c + 1 < cuts.length; c += 2)
      for (let i = 0; i < nx; i++)
        if (xs[i] > cuts[c] && xs[i] < cuts[c + 1]) z[j * nx + i] = Math.min(z[j * nx + i], top);
  });
}

/** Disc at junction ends so road ribbons join without notches. */
function disc(batch, material, p, r, z, segments = 10, drape = null) {
  if (drape) {
    const verts = [[p[0], p[1], drape(p[0], p[1]) + z]],
      uvs = [[0.5, 0]],
      idx = [];
    for (let k = 0; k <= segments; k++) {
      const a = (k / segments) * Math.PI * 2;
      const x = p[0] + Math.cos(a) * r,
        y = p[1] + Math.sin(a) * r;
      verts.push([x, y, drape(x, y) + z]);
      uvs.push([0.5, 0]);
      if (k) idx.push(0, k, k + 1);
    }
    batch.add(material, verts, uvs, idx);
    return;
  }
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
/** Sub-polyline of a way from vertex i0 to i1, with its per-vertex/segment fields. */
function sliceWay(way, i0, i1) {
  const out = { ...way, line: way.line.slice(i0, i1 + 1) };
  for (const key of ['wl', 'wr', 'pl', 'pr']) if (way[key]) out[key] = way[key].slice(i0, i1 + 1);
  for (const key of ['covered', 'wet'])
    if (way[key]) out[key] = way[key].filter((k) => k >= i0 && k < i1).map((k) => k - i0);
  return out;
}

function avoidCutouts(ways, cutouts, water) {
  if (!cutouts?.length) return ways;
  const inBox = (p) =>
    cutouts.some((c) => p[0] >= c.x0 && p[0] <= c.x1 && p[1] >= c.y0 && p[1] <= c.y1);
  const wet = (p) => water.some((w) => w.poly && pointIn(w.poly[0], p[0], p[1]));
  const out = [];
  for (const way of ways) {
    let start = 0;
    for (let k = 1; k < way.line.length; k++) {
      const a = way.line[k - 1],
        b = way.line[k];
      const cut = inBox(a) && inBox(b) && wet([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
      if (cut) {
        if (k - 1 > start) out.push(sliceWay(way, start, k - 1));
        start = k;
      }
    }
    if (way.line.length - 1 > start) out.push(sliceWay(way, start, way.line.length - 1));
  }
  return out;
}

/**
 * Ground layer for bounds {x0, y0, x1, y1}. On scenes with terrain every feature is
 * draped (z = elevation + layer offset), water bodies are flat at their level and
 * decks are interpolated between the terrain at their ends; `base: false` leaves out
 * the base surface (exported separately as the `terrain` layer).
 */
export function buildGround(scene, { bounds, cutouts, base = true } = {}) {
  const batch = new MeshBatch();
  const H = scene.half_m;
  const b = bounds ?? { x0: -H, y0: -H, x1: H, y1: H };
  const drape = elevationFn(scene);
  const group = new THREE.Group();
  if (!drape)
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
  else if (base) group.add(buildTerrain(scene, { bounds: b }));
  // Flat scenes keep the original constant heights; on terrain z is an offset.
  const at = drape ?? (() => 0);
  const opt = (o) => (drape ? { ...o, drape } : o);
  const surface = (material, polys, z, o) =>
    drape
      ? drapedCap(batch, material, polys, z, drape, { ...o, tolerance: CAP_TOLERANCE_M })
      : cap(batch, material, polys, z, o);

  const areas = scene.areas
    .filter((a) => a.poly[0].some((p) => inside(p, bounds)))
    .sort((p, q) => (AREA_RANK[p.kind] ?? 1) - (AREA_RANK[q.kind] ?? 1));
  for (const a of areas) {
    const z = Z.area + (AREA_RANK[a.kind] ?? 1) * 0.004;
    surface(ground(a.kind), [a.poly], z, { scale: a.kind === 'pitch' ? 30 : 20 });
  }
  for (const w of scene.water) {
    if (w.poly && w.poly[0].some((p) => inside(p, bounds))) {
      if (drape && Number.isFinite(w.level))
        cap(batch, ground('water'), [w.poly], w.level + Z.water, { scale: 30 });
      else surface(ground('water'), [w.poly], Z.water, { scale: 30 });
    } else if (w.line && clipLine(w.line, bounds))
      ribbon(batch, ground('water'), w.line, w.w, Z.water, opt({ centre: false }));
  }

  const deck = mat('dark_concrete');
  // Deck height along a lifted way: level offset above the line joining the terrain
  // at its two ends (constant level * DECK_M on flat scenes).
  const deckHeights = (line, level) => {
    if (!drape) return () => level * DECK_M;
    const s = [0];
    for (let k = 1; k < line.length; k++)
      s.push(s[k - 1] + Math.hypot(line[k][0] - line[k - 1][0], line[k][1] - line[k - 1][1]));
    const L = s[s.length - 1] || 1;
    const e0 = at(...line[0]),
      e1 = at(...line[line.length - 1]);
    return (k) => e0 + ((e1 - e0) * s[k]) / L + level * DECK_M;
  };
  const roads = avoidCutouts(scene.roads, cutouts, scene.water)
    .filter((r) => clipLine(r.line, bounds))
    .sort((p, q) => (RANK[ROAD_KIND[p.cls]] ?? 0) - (RANK[ROAD_KIND[q.cls]] ?? 0));
  // Pavements first, under carriageways.
  for (const r of roads) {
    const kind = ROAD_KIND[r.cls] ?? 'minor';
    if (r.level || !['major', 'minor'].includes(kind)) continue;
    // Pavements stop at building faces (widths from resolve_conflicts.py).
    const skip = r.covered ? new Set(r.covered) : null;
    ribbon(
      batch,
      road('pavement'),
      r.line,
      r.w + 5,
      Z.pavement,
      opt({
        vScale: 8,
        left: r.pl,
        right: r.pr,
        skip,
        // On terrain the pavement bends where the carriageway edges lie on it.
        // Its middle is always under the carriageway and is not drawn.
        ...(drape ? { inner: { left: r.wl, right: r.wr, width: r.w, hollow: true } } : {}),
      }),
    );
  }
  const parapet = mat('portland_stone');
  for (const r of roads) {
    const kind = ROAD_KIND[r.cls] ?? 'minor';
    const rank = RANK[kind] ?? 0;
    const lifted = r.level > 0 && ['major', 'minor', 'service'].includes(kind);
    const zBase = lifted ? r.level * DECK_M : rank > 1 ? Z.road + rank * 0.004 : Z.path;
    const deckZ = lifted && drape ? deckHeights(r.line, r.level) : null;
    ribbon(batch, road(kind), r.line, r.w, deckZ ?? zBase, {
      vScale: kind === 'steps' ? 4 : 16,
      side: lifted ? { material: deck, depth: 1.2 } : null,
      left: r.wl,
      right: r.wr,
      skip: r.covered ? new Set(r.covered) : null,
      ...(drape && !lifted ? { drape, centre: rank > 1 } : {}),
    });
    // Parapets where a way crosses water without a mapped bridge structure.
    for (const k of r.wet ?? []) {
      const p = r.line[k],
        q = r.line[k + 1];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 0.2) continue;
      const ux = (q[0] - p[0]) / len,
        uy = (q[1] - p[1]) / len;
      const z0 = deckZ
        ? (deckZ(k) + deckZ(k + 1)) / 2
        : zBase + (drape ? Math.max(at(...p), at(...q)) : 0);
      for (const [sgn, w] of [
        [1, r.wl],
        [-1, r.wr],
      ]) {
        const half = (w ? Math.min(w[k], w[k + 1]) : r.w / 2) + 0.2;
        box(
          batch,
          parapet,
          (p[0] + q[0]) / 2 - uy * half * sgn,
          (p[1] + q[1]) / 2 + ux * half * sgn,
          z0,
          len + 0.1,
          0.35,
          1.05,
          Math.atan2(uy, ux),
        );
      }
    }
    if (lifted) {
      // Piers every ~35 m along flyovers.
      let acc = 0;
      for (let k = 1; k < r.line.length; k++) {
        const p = r.line[k - 1],
          q = r.line[k];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        for (let t = (35 - acc) / len; t < 1; t += 35 / len)
          if (t >= 0) {
            const x = p[0] + (q[0] - p[0]) * t,
              y = p[1] + (q[1] - p[1]) * t;
            const foot = drape ? at(x, y) - 0.3 : 0;
            const top = deckZ ? deckZ(k - 1) + (deckZ(k) - deckZ(k - 1)) * t : zBase;
            if (top - 1.2 - foot > 0.1)
              box(
                batch,
                deck,
                x,
                y,
                foot,
                1.6,
                Math.min(r.w * 0.6, 8),
                top - 1.2 - foot,
                Math.atan2(q[1] - p[1], q[0] - p[0]),
              );
          }
        acc = (acc + len) % 35;
      }
    } else if (rank >= 3) {
      for (const [end, k] of [
        [r.line[0], 0],
        [r.line[r.line.length - 1], r.line.length - 1],
      ])
        disc(
          batch,
          road(kind),
          end,
          r.wl ? Math.min(r.wl[k], r.wr[k]) : r.w / 2,
          zBase - 0.002,
          10,
          drape,
        );
    }
  }
  for (const r of avoidCutouts(scene.rails, cutouts, scene.water)) {
    if (!clipLine(r.line, bounds)) continue;
    const z = r.level ? r.level * DECK_M : Z.rail;
    if (drape && r.level) {
      // Viaduct: deck between the terrain at its ends, walls down to the terrain.
      const deckZ = deckHeights(r.line, r.level);
      ribbon(batch, road('rail'), r.line, 3.4, deckZ, {
        vScale: 6,
        side: {
          material: mat('london_stock'),
          depth: (k) => Math.max(0, deckZ(k) - at(...r.line[k]) + 0.3),
        },
      });
      continue;
    }
    ribbon(
      batch,
      road('rail'),
      r.line,
      3.4,
      z,
      opt({
        vScale: 6,
        side: r.level ? { material: mat('london_stock'), depth: z } : null,
        centre: false,
      }),
    );
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
      const pts = drape ? densify(line, WALL_DRAPE_M) : line;
      for (let k = 1; k < pts.length; k++) {
        const p = pts[k - 1],
          q = pts[k];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 0.3) continue;
        // On terrain the segment starts below its lower end and keeps its height
        // above the ground at its middle.
        const z0 = drape ? Math.min(at(...p), at(...q)) - 0.2 : 0;
        const top = drape ? at((p[0] + q[0]) / 2, (p[1] + q[1]) / 2) + h : h;
        box(
          batch,
          material,
          (p[0] + q[0]) / 2,
          (p[1] + q[1]) / 2,
          z0,
          len + t * 0.5,
          t,
          top - z0,
          Math.atan2(q[1] - p[1], q[0] - p[0]),
        );
      }
    }
  const layer = batch.toGroup('ground');
  layer.traverse((o) => {
    if (o.isMesh) o.userData.flat = true;
  });
  if (!group.children.length) return layer;
  for (const child of [...layer.children]) group.add(child);
  group.name = 'ground';
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
  // ... and not in lakes, ponds or the river.
  const pools = scene.water
    .filter((w) => w.poly)
    .map((w) => {
      const xs = w.poly[0].map((p) => p[0]),
        ys = w.poly[0].map((p) => p[1]);
      return {
        ring: w.poly[0],
        x0: Math.min(...xs),
        x1: Math.max(...xs),
        y0: Math.min(...ys),
        y1: Math.max(...ys),
      };
    });
  const wet = (x, y) =>
    pools.some((w) => x >= w.x0 && x <= w.x1 && y >= w.y0 && y <= w.y1 && pointIn(w.ring, x, y));
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
        if (built(px, py) || onWay(px, py) || keepOut(px, py) || wet(px, py)) continue;
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
  const drape = elevationFn(scene);
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
        ...(drape ? { zOf: (p) => drape(p[0], p[1]) - 0.1 } : {}),
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
  const drape = elevationFn(scene);
  for (const [id, list] of Object.entries(scene.placements ?? {})) {
    const def = assets.get(id);
    if (!def) throw new Error(`No resources asset for placement '${id}'`);
    group.add(
      instance(
        def,
        list.filter((p) => inside(p, bounds)),
        {
          name: `furniture:${id}`,
          detail,
          ...(drape ? { zOf: (p) => drape(p[0], p[1]) } : {}),
        },
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
