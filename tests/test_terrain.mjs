// Terrain sampling and draping of the image-to-three.js ground builders.
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';
import test from 'node:test';

// The browser modules import 'three' through an import map; map it to the vendored build.
const VENDOR = new URL('../src/visualization/vendor/three/', import.meta.url);
registerHooks({
  resolve(specifier, context, next) {
    if (specifier === 'three')
      return { url: new URL('build/three.module.js', VENDOR).href, shortCircuit: true };
    if (specifier.startsWith('three/addons/'))
      return {
        url: new URL(`examples/jsm/${specifier.slice('three/addons/'.length)}`, VENDOR).href,
        shortCircuit: true,
      };
    return next(specifier, context);
  },
});

const MODULES = process.env.IMAGE_TO_THREEJS_DIR ?? '../src/urban_geometry/image_to_threejs/';
const three = new URL(`${MODULES}three/`, import.meta.url);
const { elevation, terrainOf } = await import(new URL('terrain.mjs', three).href);
const { DRAPE_M, drapedCap, ribbon } = await import(new URL('ground.mjs', three).href);
const { MeshBatch } = await import(new URL('kit.mjs', three).href);

/** Scene terrain record as written by terrain.py (int16 centimetres, base64). */
function terrainRecord(fn, { x0 = -50, y0 = -40, dx = 10, nx = 12, ny = 10, base = -5 } = {}) {
  const raw = new Int16Array(nx * ny);
  for (let j = 0; j < ny; j++)
    for (let i = 0; i < nx; i++)
      raw[j * nx + i] = Math.round((fn(x0 + i * dx, y0 + j * dx) - base) / 0.01);
  const bytes = Buffer.from(raw.buffer);
  return {
    x0,
    y0,
    dx,
    nx,
    ny,
    base_m: base,
    scale_m: 0.01,
    encoding: 'int16le-base64',
    z: bytes.toString('base64'),
  };
}

test('elevation() is 0 without terrain and bilinear between grid nodes', () => {
  assert.equal(elevation({}, 12, 7), 0);
  assert.equal(elevation({ buildings: [] }, -1e6, 1e6), 0);
  const plane = (x, y) => 10 + 0.05 * x - 0.02 * y;
  const scene = { terrain: terrainRecord(plane) };
  // Nodes reproduce the encoded centimetres; a plane is reproduced exactly in between.
  assert.ok(Math.abs(elevation(scene, -50, -40) - plane(-50, -40)) < 0.006);
  for (const [x, y] of [
    [3.3, 7.1],
    [-44.9, 12.5],
    [55, 49],
  ])
    assert.ok(Math.abs(elevation(scene, x, y) - plane(x, y)) < 0.006, `${x},${y}`);
  // Outside the grid the edge value is held.
  assert.ok(Math.abs(elevation(scene, -500, -40) - plane(-50, -40)) < 0.006);
  // A saddle: the cell centre is the mean of its four corners.
  const saddle = { terrain: terrainRecord((x, y) => (x * y) / 100) };
  const g = terrainOf(saddle);
  const k = g.nx * 4 + 5;
  const mean = (g.h[k] + g.h[k + 1] + g.h[k + g.nx] + g.h[k + g.nx + 1]) / 4;
  assert.ok(Math.abs(elevation(saddle, g.x0 + 55, g.y0 + 45) - mean) < 1e-5);
  // Plain integer arrays are accepted as well as base64.
  const arr = { terrain: { ...scene.terrain, encoding: undefined, z: [...Array(120).keys()] } };
  assert.ok(Math.abs(elevation(arr, -40, -40) - (-5 + 0.01)) < 1e-6);
});

/** Every vertex of a batch's single bucket, as [x, y, z]. */
function vertices(batch) {
  const [bucket] = [...batch.buckets.values()];
  const out = [];
  for (let k = 0; k < bucket.p.length; k += 3) out.push(bucket.p.slice(k, k + 3));
  return { out, idx: bucket.i };
}

test('a draped ribbon stays within 5 cm of the terrain plus its offset', () => {
  const hills = (x, y) => 20 + 0.03 * x + 3 * Math.sin(x / 90) * Math.cos(y / 120);
  const scene = { terrain: terrainRecord(hills, { x0: -300, y0: -300, dx: 10, nx: 61, ny: 61 }) };
  const drape = (x, y) => elevation(scene, x, y);
  const batch = new MeshBatch();
  const material = { name: 'test' };
  const line = [
    [-250, -200],
    [-100, -150],
    [40, 60],
    [220, 230],
  ];
  const offset = 0.16;
  ribbon(batch, material, line, 9, offset, { drape });
  const { out, idx } = vertices(batch);
  // Segments are split to at most DRAPE_M (left/right edges may be a little longer at miters).
  for (let t = 0; t < idx.length; t += 6) {
    const [a, b] = [out[idx[t]], out[idx[t + 1]]];
    assert.ok(Math.hypot(b[0] - a[0], b[1] - a[1]) <= DRAPE_M * 1.01);
  }
  // Vertices, and points along every triangle edge, follow the terrain.
  let worst = 0;
  for (let t = 0; t < idx.length; t += 3)
    for (const [p, q] of [
      [idx[t], idx[t + 1]],
      [idx[t + 1], idx[t + 2]],
      [idx[t + 2], idx[t]],
    ])
      for (const s of [0, 0.25, 0.5, 0.75]) {
        const a = out[p],
          b = out[q];
        const x = a[0] + (b[0] - a[0]) * s,
          y = a[1] + (b[1] - a[1]) * s,
          z = a[2] + (b[2] - a[2]) * s;
        worst = Math.max(worst, Math.abs(z - (drape(x, y) + offset)));
      }
  assert.ok(worst <= 0.05, `max deviation ${worst.toFixed(3)} m`);
  // Without a drape function the ribbon is flat at its offset, as before.
  const flat = new MeshBatch();
  ribbon(flat, material, line, 9, offset);
  assert.ok(vertices(flat).out.every((v) => v[2] === Math.fround(offset) || v[2] === offset));
});

test('a draped cap is subdivided without cracks and follows the terrain', () => {
  const slope = (x, y) => 5 + 0.04 * x + 0.01 * y;
  const scene = { terrain: terrainRecord(slope, { x0: -200, y0: -200, dx: 10, nx: 41, ny: 41 }) };
  const drape = (x, y) => elevation(scene, x, y);
  const batch = new MeshBatch();
  const ring = [
    [-150, -120],
    [140, -100],
    [120, 130],
    [-130, 110],
  ];
  const hole = [
    [-20, -20],
    [-20, 20],
    [20, 20],
    [20, -20],
  ];
  drapedCap(batch, { name: 'area' }, [[ring, hole]], 0.05, drape);
  const { out, idx } = vertices(batch);
  const edges = new Map();
  for (let t = 0; t < idx.length; t += 3)
    for (const [a, b] of [
      [idx[t], idx[t + 1]],
      [idx[t + 1], idx[t + 2]],
      [idx[t + 2], idx[t]],
    ]) {
      const pa = out[a],
        pb = out[b];
      assert.ok(Math.hypot(pb[0] - pa[0], pb[1] - pa[1]) <= DRAPE_M + 1e-6);
      const key = a < b ? `${a},${b}` : `${b},${a}`;
      edges.set(key, (edges.get(key) ?? 0) + 1);
    }
  // Interior edges are shared by exactly two triangles (no T-junctions); the rest
  // form the outline of the ring and the hole.
  const counts = [...edges.values()];
  assert.ok(counts.every((c) => c <= 2));
  const boundary = counts.filter((c) => c === 1).length;
  const perimeter = (r) =>
    r.reduce((s, p, k) => {
      const q = r[(k + 1) % r.length];
      return s + Math.ceil(Math.hypot(q[0] - p[0], q[1] - p[1]) / DRAPE_M);
    }, 0);
  assert.equal(boundary, perimeter(ring) + perimeter(hole));
  for (const v of out) assert.ok(Math.abs(v[2] - (slope(v[0], v[1]) + 0.05)) < 0.01);
});
