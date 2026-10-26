// Generic building generator for every footprint not replaced by a landmark module.
import * as THREE from 'three';
import {
  MeshBatch,
  box,
  cap,
  facade,
  fittedRoof,
  mat,
  normalisePolys,
  orientedExtent,
  ringArea,
  ringFrame,
  roof,
  roofWalls,
  shopfront,
  walls,
} from './kit.mjs';
import { FACADES } from '../resources/materials/textures.mjs';

const PITCHED = {
  gabled: 'gabled',
  saltbox: 'gabled',
  gambrel: 'gabled',
  half_hipped: 'hipped',
  hipped: 'hipped',
  mansard: 'mansard',
  pyramidal: 'pyramidal',
};
// Notting Hill / Chelsea pastel stucco terraces.
const PASTELS = [
  [1, 0.9, 0.9],
  [0.88, 0.94, 1],
  [1, 0.97, 0.82],
  [0.9, 1, 0.92],
  [0.98, 0.92, 1],
];
// Walls of buildings on terrain start this far below their ground (`ground_z`, or the
// `ground_plane` of sloping terraces).
export const FOOT_M = 0.5;
// Pitched roofs need a single ring that fills at least this share of the oriented
// rectangle the roof planes are laid out on, and at most PITCHED_MAX_VERTS vertices;
// other footprints get a flat roof.
export const PITCHED_MIN_FIT = 0.65;
export const PITCHED_MAX_VERTS = 64;
const BAY = { glass: 3.0, modern_clad: 3.3, concrete: 3.4, metal_clad: 5, ragstone: 5.5 };
const STOREY = { metal_clad: 4.5, ragstone: 6, glass: 3.6, portland_stone: 3.7 };

function tint(b, style) {
  if (b.facadeColor) {
    try {
      const c = new THREE.Color(b.facadeColor);
      const g = 0.6;
      return [1 - g + g * c.r * 1.3, 1 - g + g * c.g * 1.3, 1 - g + g * c.b * 1.3].map((v) =>
        Math.min(1.1, v),
      );
    } catch {
      /* unknown colour name */
    }
  }
  const k = 0.92 + 0.16 * ((b.seed * 7.31) % 1);
  if (
    style === 'stucco' &&
    b.c[0] > -1700 &&
    b.c[0] < 400 &&
    b.c[1] > 300 &&
    b.c[1] < 2600 &&
    b.seed < 0.35
  )
    return PASTELS[Math.floor(b.seed * 1000) % PASTELS.length];
  return [k, k, k];
}

function roofKind(b, style) {
  if (b.roofColor) {
    const c = b.roofColor.toLowerCase();
    if (/red|brown|#8|#9|#a/.test(c)) return 'clay';
    if (/green/.test(c)) return 'green';
  }
  if (b.roof === 'flat') return b.h > 30 || b.seed > 0.93 ? 'flat' : 'flat';
  if (style === 'red_brick' && b.c[0] < -1500 && b.seed > 0.5) return 'clay';
  return 'slate';
}

/** Share of the oriented rectangle along `angle` that the ring fills. */
export function rectFit(ring, angle) {
  const e = orientedExtent(ring, angle);
  const rect = (e.u1 - e.u0) * (e.v1 - e.v0);
  return rect > 0 ? Math.abs(ringArea(ring)) / rect : 0;
}

/**
 * Roof form actually built for a piece (normalised polygons): the pitched kind and
 * ridge angle, or null for a flat roof when the footprint has holes, several
 * polygons, too many vertices or does not fill its oriented rectangle.
 */
export function pitchedFor(piece, polys, fallbackRidge) {
  const kind = PITCHED[piece.roof];
  if (!kind || polys.length !== 1 || polys[0].length !== 1) return null;
  const ring = polys[0][0];
  if (ring.length > PITCHED_MAX_VERTS) return null;
  // The piece's own ridge, else the building's when it fits (parts of scenes prepared
  // without part ridges), else the piece's long axis.
  const candidates = Number.isFinite(piece.ridge)
    ? [piece.ridge]
    : [fallbackRidge, ringFrame(ring).angle].filter(Number.isFinite);
  for (const ridge of candidates)
    if (rectFit(ring, ridge) >= PITCHED_MIN_FIT) return { kind, ridge };
  return null;
}

/** Point in polygons (even-odd over every ring). */
function insidePolys(polys, x, y) {
  let inside = false;
  for (const poly of polys)
    for (const ring of poly)
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i],
          [xj, yj] = ring[j];
        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
      }
  return inside;
}

/**
 * One volume (the building or one of its parts): walls, roof and, when it starts
 * above the ground, a floor. Returns whether it has a pitched roof.
 */
function shell(batch, b, piece, style, color, foot = 0) {
  const polys = normalisePolys(piece.polys);
  const minh = piece.minh ?? 0;
  if (!polys.length || !(piece.h > minh + 0.05)) return false;
  const variants = FACADES[style]?.colors.length ?? 1;
  const wall = facade(style, Math.floor(b.seed * 97) % variants);
  const bay = (BAY[style] ?? 3.6) * (0.9 + 0.25 * ((b.seed * 13.7) % 1));
  const storey = STOREY[style] ?? 3.2;
  const roofKey = roofKind(b, style);
  const rmat = roof(roofKey, Math.floor(b.seed * 31) % 3);
  const pitched = pitchedFor(piece, polys, b.ridge);
  const rise = pitched ? Math.min(piece.roofH || 3, (piece.h - minh) * 0.6) : 0;
  const eave = piece.h - rise;
  // On terrain (foot > 0) ground-level walls reach below the footprint's lowest point.
  const base = foot > 0 ? -foot : 0;
  let z = minh || base;
  // Shopfront band on commercial ground floors.
  if (!minh && (b.group === 'commercial' || b.cls === 'retail') && eave > 6) {
    walls(batch, shopfront(Math.floor(b.seed * 53) % 6), polys, base, 4.2, {
      bay: 4.2,
      storey: 4.2,
      uvBase: 0,
    });
    z = 4.2;
  }
  const uvBase = minh > 0 ? 0 : 0.6;
  if (minh > 0.5) cap(batch, rmat, polys, minh, { down: true });
  if (pitched) {
    const ring = polys[0][0];
    const r = fittedRoof(batch, rmat, ring, pitched.ridge, eave, rise, pitched.kind, {
      color: [1, 1, 1],
    });
    roofWalls(batch, wall, polys, z, r, { bay, storey, uvBase, color });
    if (b.group === 'house') {
      // Chimney stacks at the party walls (where they stand on the footprint).
      const brick = mat('london_stock');
      const [p0, p1] = r.ridge;
      const single = p0[0] === p1[0] && p0[1] === p1[1];
      for (const t of single ? [0.5] : [0.08, 0.92]) {
        const x = p0[0] + (p1[0] - p0[0]) * t;
        const y = p0[1] + (p1[1] - p0[1]) * t;
        if (!insidePolys(polys, x, y)) continue;
        box(batch, brick, x, y, r.zAt(x, y) - 1.2, 0.6, 1.6, 2.2, pitched.ridge + Math.PI / 2);
      }
    }
  } else {
    walls(batch, wall, polys, z, eave, { bay, storey, uvBase, color });
    cap(batch, rmat, polys, eave, { scale: 6 });
    // Parapet coping line and rooftop plant on larger flat roofs.
    const area = Math.abs(polyArea(polys));
    if (area > 600 && eave > 12) {
      const n = Math.min(4, Math.floor(area / 900) + 1);
      const ring = polys[0][0];
      const [cx, cy] = centroidOf(ring);
      for (let k = 0; k < n; k++) {
        const a = b.seed * 40 + k * 2.1,
          rr = Math.sqrt(area) * 0.15;
        const x = cx + Math.cos(a) * rr,
          y = cy + Math.sin(a) * rr;
        if (!insidePolys(polys, x, y)) continue;
        box(
          batch,
          mat('#9a9a95'),
          x,
          y,
          eave,
          2 + ((b.seed * (k + 3)) % 1) * 3,
          2 + ((b.seed * (k + 7)) % 1) * 2,
          1.6 + k * 0.4,
          b.ridge,
        );
      }
    }
  }
  return Boolean(pitched);
}

function polyArea(polys) {
  let a = 0;
  for (const poly of polys)
    for (const ring of poly)
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        a += (p[0] * q[1] - q[0] * p[1]) / 2;
      }
  return a;
}

function centroidOf(ring) {
  let x = 0,
    y = 0;
  for (const p of ring) {
    x += p[0];
    y += p[1];
  }
  return [x / ring.length, y / ring.length];
}

const HULLS = ['blue', 'red', 'black', 'dark_steel', 'timber'];

/**
 * Moored vessel (houseboat, narrowboat, pontoon cabin) fitted to the footprint's
 * minimum-area rectangle: hull in the water, a narrower cabin and a flat roof.
 */
function vessel(batch, b) {
  const ring = b.polys[0][0];
  let best = null;
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    const e = orientedExtent(ring, Math.atan2(q[1] - p[1], q[0] - p[0]));
    const area = (e.u1 - e.u0) * (e.v1 - e.v0);
    if (!best || area < best.area) best = { e, area };
  }
  let { e } = best;
  let angle = Math.atan2(e.s, e.c);
  let len = e.u1 - e.u0,
    beam = e.v1 - e.v0;
  if (beam > len) {
    [len, beam] = [beam, len];
    angle += Math.PI / 2;
  }
  const [x, y] = e.at((e.u0 + e.u1) / 2, (e.v0 + e.v1) / 2, 0);
  const hull = mat(HULLS[Math.floor((b.seed ?? 0.5) * HULLS.length) % HULLS.length]);
  const along = (t) => [x + Math.cos(angle) * t, y + Math.sin(angle) * t];
  box(batch, hull, x, y, -0.4, len * 0.92, beam, 1.1, angle);
  // Tapered bow block.
  const [bx, by] = along(len * 0.46);
  box(batch, hull, bx, by, -0.4, len * 0.08, beam * 0.6, 1.0, angle);
  const cabinH = Math.min(2.2, Math.max(1.4, (b.h ?? 3) - 1));
  const [cx, cy] = along(-len * 0.04);
  box(batch, mat('white'), cx, cy, 0.7, len * 0.72, beam * 0.82, cabinH, angle);
  box(
    batch,
    mat('dark_glass'),
    cx,
    cy,
    0.7 + cabinH * 0.45,
    len * 0.7,
    beam * 0.84,
    cabinH * 0.3,
    angle,
  );
  box(batch, mat('dark_steel'), cx, cy, 0.7 + cabinH, len * 0.75, beam * 0.86, 0.12, angle);
}

/** Vertex counts per material bucket, to lift what is added after this point. */
function mark(batch) {
  return new Map([...batch.buckets].map(([m, bk]) => [m, bk.p.length]));
}

/** Raise every vertex added to the batch since `marks` by dz(x, y, z). */
function lift(batch, marks, dz) {
  for (const [m, bk] of batch.buckets)
    for (let k = marks.get(m) ?? 0; k < bk.p.length; k += 3)
      bk.p[k + 2] += dz(bk.p[k], bk.p[k + 1], bk.p[k + 2]);
}

/**
 * Build all generic buildings whose centroid falls inside `bounds`
 * ({x0,y0,x1,y1}); landmark-claimed footprints are skipped. Buildings with a
 * `ground_z` (scenes with terrain) stand on it, walls extended FOOT_M lower, and
 * vessels float at it (their water level).
 */
export function buildGeneric(scene, { bounds, skip = new Set() } = {}) {
  const batch = new MeshBatch();
  let count = 0;
  for (const b of scene.buildings) {
    if (b.landmark || skip.has(b.id)) continue;
    const [x, y] = b.c;
    if (bounds && (x < bounds.x0 || x >= bounds.x1 || y < bounds.y0 || y >= bounds.y1)) continue;
    const ground = Number.isFinite(b.ground_z) ? b.ground_z : null;
    const marks = ground === null ? null : mark(batch);
    const foot = ground === null || b.vessel ? 0 : FOOT_M;
    let pitched = false;
    if (b.vessel) vessel(batch, b);
    else {
      const style = b.style;
      const color = tint(b, style);
      if (b.parts?.length)
        for (const p of b.parts)
          pitched = shell(batch, b, p, p.style ?? style, color, foot) || pitched;
      else pitched = shell(batch, b, b, style, color, foot);
    }
    if (marks && b.ground_plane) {
      // Long footprints on an even slope (terraces) are sheared onto it. Flat roofs stay
      // level: only the wall feet follow the plane, the rest is lifted to its height
      // under the centroid (kept within half the height of the uphill end).
      const [z0, gx, gy] = b.ground_plane,
        [cx, cy] = b.c;
      const plane = (x, y) => z0 + gx * (x - cx) + gy * (y - cy);
      if (pitched || b.vessel) lift(batch, marks, plane);
      else {
        let top = -Infinity;
        for (const poly of b.polys) for (const [x, y] of poly[0]) top = Math.max(top, plane(x, y));
        const level = Math.max(z0, top - 0.5 * (b.h - (b.minh ?? 0)));
        lift(batch, marks, (x, y, z) => (z <= 0.01 ? plane(x, y) : level));
      }
    } else if (marks && ground) lift(batch, marks, () => ground);
    count++;
  }
  const group = batch.toGroup('generic_buildings');
  group.traverse((o) => {
    if (o.isMesh) o.userData.flat = true;
  });
  group.userData.count = count;
  return group;
}
