// Generic building generator for every footprint not replaced by a landmark module.
import * as THREE from 'three';
import {
  MeshBatch,
  box,
  cap,
  facade,
  mat,
  orientedExtent,
  pitchedRoof,
  roof,
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

function shell(batch, b, piece, style, color) {
  const variants = FACADES[style]?.colors.length ?? 1;
  const wall = facade(style, Math.floor(b.seed * 97) % variants);
  const bay = (BAY[style] ?? 3.6) * (0.9 + 0.25 * ((b.seed * 13.7) % 1));
  const storey = STOREY[style] ?? 3.2;
  const roofKey = roofKind(b, style);
  const rmat = roof(roofKey, Math.floor(b.seed * 31) % 3);
  const minh = piece.minh ?? 0;
  const kind = PITCHED[piece.roof];
  const rise = kind ? Math.min(piece.roofH || 3, (piece.h - minh) * 0.6) : 0;
  const eave = piece.h - rise;
  let z = minh;
  // Shopfront band on commercial ground floors.
  if (!minh && (b.group === 'commercial' || b.cls === 'retail') && eave > 6) {
    walls(batch, shopfront(Math.floor(b.seed * 53) % 6), piece.polys, 0, 4.2, {
      bay: 4.2,
      storey: 4.2,
      uvBase: 0,
    });
    z = 4.2;
  }
  walls(batch, wall, piece.polys, z, eave, { bay, storey, uvBase: minh > 0 ? 0 : 0.6, color });
  if (minh > 0.5) cap(batch, rmat, piece.polys, minh, { down: true });
  if (kind && piece.polys.length === 1) {
    const r = pitchedRoof(batch, rmat, wall, piece.polys[0][0], b.ridge, eave, rise, kind, {
      color: [1, 1, 1],
      wallColor: color,
      storey,
    });
    if (b.group === 'house' && r.ridge) {
      // Chimney stacks at the party walls.
      const brick = mat('london_stock');
      for (const t of [0.08, 0.92]) {
        const x = r.ridge[0][0] + (r.ridge[1][0] - r.ridge[0][0]) * t;
        const y = r.ridge[0][1] + (r.ridge[1][1] - r.ridge[0][1]) * t;
        if (r.ridge[0][0] === r.ridge[1][0] && r.ridge[0][1] === r.ridge[1][1] && t > 0.5) break;
        box(batch, brick, x, y, r.top - 1.2, 0.6, 1.6, 2.2, b.ridge + Math.PI / 2);
      }
    }
  } else {
    cap(batch, rmat, piece.polys, eave, { scale: 6 });
    // Parapet coping line and rooftop plant on larger flat roofs.
    const area = Math.abs(polyArea(piece.polys));
    if (area > 600 && eave > 12) {
      const n = Math.min(4, Math.floor(area / 900) + 1);
      const ring = piece.polys[0][0];
      const [cx, cy] = centroidOf(ring);
      for (let k = 0; k < n; k++) {
        const a = b.seed * 40 + k * 2.1,
          rr = Math.sqrt(area) * 0.15;
        box(
          batch,
          mat('#9a9a95'),
          cx + Math.cos(a) * rr,
          cy + Math.sin(a) * rr,
          eave,
          2 + ((b.seed * (k + 3)) % 1) * 3,
          2 + ((b.seed * (k + 7)) % 1) * 2,
          1.6 + k * 0.4,
          b.ridge,
        );
      }
    }
  }
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

/**
 * Build all generic buildings whose centroid falls inside `bounds`
 * ({x0,y0,x1,y1}); landmark-claimed footprints are skipped.
 */
export function buildGeneric(scene, { bounds, skip = new Set() } = {}) {
  const batch = new MeshBatch();
  let count = 0;
  for (const b of scene.buildings) {
    if (b.landmark || skip.has(b.id)) continue;
    const [x, y] = b.c;
    if (bounds && (x < bounds.x0 || x >= bounds.x1 || y < bounds.y0 || y >= bounds.y1)) continue;
    if (b.vessel) {
      vessel(batch, b);
      count++;
      continue;
    }
    const style = b.style;
    const color = tint(b, style);
    if (b.parts?.length)
      for (const p of b.parts) shell(batch, b, { ...p, roof: p.roof }, p.style ?? style, color);
    else shell(batch, b, b, style, color);
    count++;
  }
  const group = batch.toGroup('generic_buildings');
  group.traverse((o) => {
    if (o.isMesh) o.userData.flat = true;
  });
  group.userData.count = count;
  return group;
}
