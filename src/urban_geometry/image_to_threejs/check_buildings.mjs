#!/usr/bin/env node
// Headless geometry checks of the generic building generator (three/generic.mjs).
//
//   node check_buildings.mjs <scene.json> [--out report.json] [--modules DIR]
//        [--limit N] [--ids id1,id2] [--rays 48] [--examples 8]
//
// Every generic building (each building part separately) is built on its own with
// buildGeneric and its triangles are checked: no NaN, a non-empty roof, roof
// coverage of the footprint (flat caps match the footprint area, pitched roofs do
// not overhang it by much), outward-facing walls, and a closed shell (rays from
// outside towards points inside the wall prism must first hit a front face). Data
// classes (h <= minh, roofH > height, parts that leave the footprint uncovered or
// float, terrain above the eaves) are counted from the scene itself. `--modules`
// points at another copy of `three/` (e.g. a baseline) to compare generators.
import fs from 'node:fs';
import { registerHooks } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VENDOR = pathToFileURL(path.resolve(HERE, '../../visualization/vendor/three') + '/');
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

// Textures are drawn on canvases; a no-op 2D context is enough to build geometry.
const noop = new Proxy(function () {}, {
  get: (_, key) => (key === Symbol.toPrimitive ? () => 0 : noop),
  set: () => true,
  apply: () => noop,
});
globalThis.document ??= {
  createElement: () => ({ width: 0, height: 0, getContext: () => noop, style: {} }),
};

export const CLASSES = {
  nan: 'non-finite vertex coordinates',
  no_roof: 'no upward roof triangles',
  roof_gaps: 'roof leaves > 2% of the footprint uncovered',
  flat_cap_mismatch: 'flat cap area differs from the footprint by > 2%',
  pitched_overhang:
    'pitched roof overhangs a 0.5 m band around the outline by > 10% of the footprint area',
  inverted_walls: 'walls facing into the footprint (> 1% of wall area)',
  roof_wall_gap: 'gap > 0.5 m between wall tops and the roof above them (> 2% of the outline)',
  eave_slit: 'slit of 0.15-0.5 m under the eaves (walls stop below an overhanging roof)',
  leaky_shell: 'rays from outside reach the inside or hit a back face (>= 2 rays)',
  h_le_minh: 'height <= min_height (data)',
  roofh_gt_height: 'roofH > h - minh of a pitched roof (data, clamped)',
  parts_gap: 'parts leave > 10% of the outer footprint uncovered (data)',
  part_floating: 'part with minh > 1 m over nothing (data)',
  terrain_buried: 'terrain rises above the eaves (ground_max - ground_z > eave)',
};

const PITCHED = new Set([
  'gabled',
  'saltbox',
  'gambrel',
  'half_hipped',
  'hipped',
  'mansard',
  'pyramidal',
]);

/** Even-odd point in polygons (all rings), independent of winding. */
export function insidePolys(polys, x, y) {
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

function signedArea(ring) {
  let a = 0;
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    a += p[0] * q[1] - q[0] * p[1];
  }
  return a / 2;
}

export function footprintArea(polys) {
  let a = 0;
  for (const poly of polys)
    poly.forEach((ring, k) => (a += (k ? -1 : 1) * Math.abs(signedArea(ring))));
  return a;
}

function bbox(polys) {
  let x0 = Infinity,
    y0 = Infinity,
    x1 = -Infinity,
    y1 = -Infinity;
  for (const poly of polys)
    for (const ring of poly)
      for (const [x, y] of ring) {
        x0 = Math.min(x0, x);
        y0 = Math.min(y0, y);
        x1 = Math.max(x1, x);
        y1 = Math.max(y1, y);
      }
  return { x0, y0, x1, y1 };
}

/** Jittered grid of about n points inside the polygons. */
export function samplePoints(polys, n = 150) {
  const bb = bbox(polys);
  const area = Math.max(footprintArea(polys), 1e-3);
  const step = Math.max(0.15, Math.sqrt(area / n));
  const pts = [];
  let k = 0;
  for (let y = bb.y0 + step * 0.37; y < bb.y1; y += step)
    for (let x = bb.x0 + step * 0.41; x < bb.x1; x += step) {
      const jx = x + step * 0.2 * Math.sin(k * 12.9898),
        jy = y + step * 0.2 * Math.cos(k++ * 78.233);
      if (insidePolys(polys, jx, jy)) pts.push([jx, jy]);
    }
  return pts;
}

/** Triangles of a built group: {p: Float64Array(9n), kind: Uint8Array(n)}; 0 roof 1 wall 2 other. */
export function triangles(group) {
  const tris = [],
    kinds = [];
  group.traverse((o) => {
    if (!o.isMesh) return;
    const name = o.material.name ?? '';
    const kind = name.startsWith('roof:')
      ? 0
      : name.startsWith('facade:') || name.startsWith('shop:')
        ? 1
        : 2;
    const pos = o.geometry.attributes.position.array;
    const idx = o.geometry.index ? o.geometry.index.array : null;
    const n = idx ? idx.length : pos.length / 3;
    for (let t = 0; t < n; t += 3) {
      for (let v = 0; v < 3; v++) {
        const i = idx ? idx[t + v] : t + v;
        tris.push(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
      }
      kinds.push(kind);
    }
    o.geometry.dispose();
  });
  return { p: Float64Array.from(tris), kind: Uint8Array.from(kinds) };
}

function normalOf(p, t) {
  const o = 9 * t;
  const ux = p[o + 3] - p[o],
    uy = p[o + 4] - p[o + 1],
    uz = p[o + 5] - p[o + 2];
  const vx = p[o + 6] - p[o],
    vy = p[o + 7] - p[o + 1],
    vz = p[o + 8] - p[o + 2];
  const nx = uy * vz - uz * vy,
    ny = uz * vx - ux * vz,
    nz = ux * vy - uy * vx;
  const l = Math.hypot(nx, ny, nz);
  return [nx, ny, nz, l / 2];
}

function inTri2(p, t, x, y) {
  const o = 9 * t;
  const ax = p[o],
    ay = p[o + 1],
    bx = p[o + 3],
    by = p[o + 4],
    cx = p[o + 6],
    cy = p[o + 7];
  const d1 = (x - bx) * (ay - by) - (ax - bx) * (y - by);
  const d2 = (x - cx) * (by - cy) - (bx - cx) * (y - cy);
  const d3 = (x - ax) * (cy - ay) - (cx - ax) * (y - ay);
  const neg = d1 < -1e-9 || d2 < -1e-9 || d3 < -1e-9;
  const pos = d1 > 1e-9 || d2 > 1e-9 || d3 > 1e-9;
  return !(neg && pos);
}

/** First triangle hit by the ray o + t d (0 < t < tmax): [t, tri] or null. */
function cast(p, n, ox, oy, oz, dx, dy, dz, tmax) {
  let best = tmax,
    hit = -1;
  for (let t = 0; t < n; t++) {
    const k = 9 * t;
    const e1x = p[k + 3] - p[k],
      e1y = p[k + 4] - p[k + 1],
      e1z = p[k + 5] - p[k + 2];
    const e2x = p[k + 6] - p[k],
      e2y = p[k + 7] - p[k + 1],
      e2z = p[k + 8] - p[k + 2];
    const px = dy * e2z - dz * e2y,
      py = dz * e2x - dx * e2z,
      pz = dx * e2y - dy * e2x;
    const det = e1x * px + e1y * py + e1z * pz;
    if (Math.abs(det) < 1e-12) continue;
    const inv = 1 / det;
    const sx = ox - p[k],
      sy = oy - p[k + 1],
      sz = oz - p[k + 2];
    const u = (sx * px + sy * py + sz * pz) * inv;
    if (u < -1e-7 || u > 1 + 1e-7) continue;
    const qx = sy * e1z - sz * e1y,
      qy = sz * e1x - sx * e1z,
      qz = sx * e1y - sy * e1x;
    const v = (dx * qx + dy * qy + dz * qz) * inv;
    if (v < -1e-7 || u + v > 1 + 1e-7) continue;
    const d = (e2x * qx + e2y * qy + e2z * qz) * inv;
    if (d > 1e-6 && d < best) {
      best = d;
      hit = t;
    }
  }
  return hit < 0 ? null : [best, hit];
}

function rng(seed) {
  let s = (Math.floor(seed * 2 ** 31) % 2147483646) + 1;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

/**
 * Geometry checks of one built piece. `polys`, `h`, `minh` describe the piece; `tris`
 * from triangles(). Returns { flags: Set, metrics }.
 */
export function checkPiece(tris, polys, h, minh, { rays = 48, seed = 0.5 } = {}) {
  const flags = new Set();
  const { p, kind } = tris;
  const n = kind.length;
  for (let k = 0; k < p.length; k++)
    if (!Number.isFinite(p[k])) {
      flags.add('nan');
      break;
    }
  const area = footprintArea(polys);
  const pts = samplePoints(polys);
  const roofUp = [];
  let roofArea = 0,
    pitched = false,
    wallArea = 0,
    inverted = 0;
  for (let t = 0; t < n; t++) {
    const [nx, ny, nz, a] = normalOf(p, t);
    if (a < 1e-9) continue;
    const l = 2 * a;
    if (kind[t] === 0 && nz / l > 0.2) {
      roofUp.push(t);
      roofArea += Math.abs(nz) / 2;
      if (nz / l < 0.999) pitched = true;
    } else if (kind[t] === 1 && Math.abs(nz / l) < 0.2) {
      wallArea += a;
      const o = 9 * t;
      const cx = (p[o] + p[o + 3] + p[o + 6]) / 3,
        cy = (p[o + 1] + p[o + 4] + p[o + 7]) / 3;
      const hl = Math.hypot(nx, ny) || 1;
      const ex = (0.02 * nx) / hl,
        ey = (0.02 * ny) / hl;
      if (insidePolys(polys, cx + ex, cy + ey) && !insidePolys(polys, cx - ex, cy - ey))
        inverted += a;
    }
  }
  const metrics = { area: +area.toFixed(2), roofArea: +roofArea.toFixed(2), pitched };
  if (!roofUp.length) flags.add('no_roof');
  else if (pts.length) {
    let miss = 0;
    for (const [x, y] of pts) if (!roofUp.some((t) => inTri2(p, t, x, y))) miss++;
    metrics.uncovered = +(miss / pts.length).toFixed(3);
    if (miss / pts.length > 0.02) flags.add('roof_gaps');
  }
  if (roofUp.length && area > 0.5) {
    const ratio = roofArea / area;
    metrics.ratio = +ratio.toFixed(3);
    if (!pitched && Math.abs(ratio - 1) > 0.02) flags.add('flat_cap_mismatch');
    // Eaves overhang by ~0.35 m: allow a 0.5 m band around the outline.
    let perimeter = 0;
    for (const poly of polys)
      for (const ring of poly)
        for (let k = 0; k < ring.length; k++) {
          const a = ring[k],
            b = ring[(k + 1) % ring.length];
          perimeter += Math.hypot(b[0] - a[0], b[1] - a[1]);
        }
    const excess = roofArea - (area + 0.5 * perimeter + 1);
    if (pitched && excess > 0.1 * area) flags.add('pitched_overhang');
  }
  if (wallArea > 0 && inverted / wallArea > 0.01) {
    flags.add('inverted_walls');
    metrics.inverted = +(inverted / wallArea).toFixed(3);
  }
  // Closed shell: rays from outside (above the horizon; also from below for pieces
  // with a floor) to points inside the volume under the roof.
  const roofZ = (x, y) => {
    let z = -Infinity;
    for (const t of roofUp) {
      const o = 9 * t;
      const ax = p[o],
        ay = p[o + 1],
        bx = p[o + 3] - ax,
        by = p[o + 4] - ay,
        cx = p[o + 6] - ax,
        cy = p[o + 7] - ay;
      const d = bx * cy - by * cx;
      if (Math.abs(d) < 1e-12) continue;
      const u = ((x - ax) * cy - (y - ay) * cx) / d,
        v = (bx * (y - ay) - by * (x - ax)) / d;
      if (u < -1e-9 || v < -1e-9 || u + v > 1 + 1e-9) continue;
      z = Math.max(z, p[o + 2] + u * (p[o + 5] - p[o + 2]) + v * (p[o + 8] - p[o + 2]));
    }
    return z;
  };
  // Seal between walls and roof: along the outline, walls (incl. gables) must reach
  // the roof surface just inside them.
  if (roofUp.length) {
    const wallTris = [];
    for (let t = 0; t < n; t++) {
      const [, , nz, a] = kind[t] === 1 ? normalOf(p, t) : [0, 0, 1, 0];
      if (a > 1e-9 && Math.abs(nz) < 2e-3 * a) wallTris.push(t);
    }
    const wallTop = (x, y) => {
      let top = -Infinity;
      for (const t of wallTris) {
        const o = 9 * t;
        // Vertical line through (x, y) against the vertical triangle: z interval.
        const zs = [];
        for (const [i, j] of [
          [0, 1],
          [1, 2],
          [2, 0],
        ]) {
          const ax = p[o + 3 * i],
            ay = p[o + 3 * i + 1],
            az = p[o + 3 * i + 2];
          const bx = p[o + 3 * j],
            by = p[o + 3 * j + 1],
            bz = p[o + 3 * j + 2];
          const ex = bx - ax,
            ey = by - ay;
          const l2 = ex * ex + ey * ey;
          if (l2 < 1e-12) {
            if (Math.hypot(x - ax, y - ay) < 0.01) zs.push(az, bz);
            continue;
          }
          const s = ((x - ax) * ex + (y - ay) * ey) / l2;
          if (s < -1e-6 || s > 1 + 1e-6) continue;
          if (Math.abs((x - ax) * ey - (y - ay) * ex) / Math.sqrt(l2) > 0.01) continue;
          zs.push(az + (bz - az) * s);
        }
        if (zs.length) top = Math.max(top, ...zs);
      }
      return top;
    };
    let samples = 0,
      gaps = 0,
      slits = 0;
    for (const poly of polys)
      for (const ring of poly)
        for (let k = 0; k < ring.length; k++) {
          const a = ring[k],
            b = ring[(k + 1) % ring.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          if (len < 0.2) continue;
          const m = Math.min(20, Math.max(2, Math.round(len)));
          const nx = (a[1] - b[1]) / len,
            ny = (b[0] - a[0]) / len; // left normal
          for (let i = 0; i < m; i++) {
            const t = (i + 0.5) / m;
            const x = a[0] + (b[0] - a[0]) * t,
              y = a[1] + (b[1] - a[1]) * t;
            const sgn = insidePolys(polys, x + 0.05 * nx, y + 0.05 * ny) ? 1 : -1;
            const rz = roofZ(x + 0.01 * sgn * nx, y + 0.01 * sgn * ny);
            if (!Number.isFinite(rz)) continue;
            samples++;
            const gap = rz - wallTop(x, y);
            if (gap > 0.5) gaps++;
            else if (gap > 0.15) slits++;
          }
        }
    if (samples) metrics.wallGap = +(gaps / samples).toFixed(3);
    if (samples && gaps / samples > 0.02) flags.add('roof_wall_gap');
    else if (samples && (gaps + slits) / samples > 0.02) flags.add('eave_slit');
  }
  if (h - minh > 0.3 && pts.length && n) {
    const bb = bbox(polys);
    const R = Math.hypot(bb.x1 - bb.x0, bb.y1 - bb.y0) + h + 10;
    const rand = rng(seed);
    const floor = minh > 0.5;
    let leaks = 0;
    for (let r = 0; r < rays; r++) {
      const [tx, ty] = pts[Math.floor(rand() * pts.length)];
      const top = Math.min(h, roofZ(tx, ty));
      const tz = minh + (top > minh ? top - minh : h - minh) * (0.03 + 0.94 * rand());
      const az = rand() * 2 * Math.PI;
      // Half the rays look down from above, half up from street level (z >= 0.3, or
      // from anywhere below for pieces with a floor).
      const up = r % 2 === 1;
      const el = ((up ? -5 - 70 * rand() : 5 + 70 * rand()) * Math.PI) / 180;
      const dx = Math.cos(el) * Math.cos(az),
        dy = Math.cos(el) * Math.sin(az),
        dz = Math.sin(el);
      let dist = R;
      if (dz < 0 && !floor) dist = Math.min(R, (tz - 0.3) / -dz);
      let ox = tx + dx * dist,
        oy = ty + dy * dist,
        oz = tz + dz * dist;
      if (dist <= 0.05 || (oz < h && insidePolys(polys, ox, oy))) continue;
      // Walk along the ray; back faces of roof overhangs (outside the outline) are seen
      // from below by design and skipped.
      let left = dist,
        leak = false;
      for (let step = 0; step < 8; step++) {
        const hit = cast(p, n, ox, oy, oz, -dx, -dy, -dz, left);
        if (!hit) {
          leak = true;
          break;
        }
        const [nx, ny, nz] = normalOf(p, hit[1]);
        if (-dx * nx - dy * ny - dz * nz < 0) break;
        const [d] = hit;
        const hx = ox - dx * d,
          hy = oy - dy * d;
        if (kind[hit[1]] !== 0 || insidePolys(polys, hx, hy)) {
          leak = true;
          break;
        }
        ox = hx;
        oy = hy;
        oz -= dz * d;
        left -= d;
      }
      if (leak) leaks++;
    }
    metrics.leaks = leaks;
    if (leaks >= 2) flags.add('leaky_shell');
  }
  return { flags, metrics };
}

function args() {
  const a = process.argv.slice(2),
    o = { _: [] };
  for (let k = 0; k < a.length; k++)
    if (a[k].startsWith('--')) o[a[k].slice(2)] = a[++k];
    else o._.push(a[k]);
  return o;
}

async function main() {
  const o = args();
  if (!o._[0]) throw new Error('usage: check_buildings.mjs <scene.json> [--out report.json]');
  const modules = path.resolve(o.modules ?? path.join(HERE, 'three'));
  const { buildGeneric } = await import(pathToFileURL(path.join(modules, 'generic.mjs')).href);
  const scene = JSON.parse(fs.readFileSync(o._[0], 'utf8'));
  const ids = o.ids ? new Set(o.ids.split(',')) : null;
  const rays = Number(o.rays ?? 48);
  const keep = Number(o.examples ?? 8);
  const limit = Number(o.limit ?? Infinity);
  const counts = Object.fromEntries(Object.keys(CLASSES).map((k) => [k, 0]));
  const examples = Object.fromEntries(Object.keys(CLASSES).map((k) => [k, []]));
  const all = ids ? [] : null;
  let checked = 0,
    pieces = 0,
    flagged = 0;
  const t0 = Date.now();
  const note = (cls, b, area, extra = {}) => {
    const list = examples[cls];
    list.push({ id: b.id, c: b.c, area: +area.toFixed(1), roof: b.roof, h: b.h, ...extra });
    list.sort((x, y) => y.area - x.area);
    if (list.length > keep) list.pop();
  };
  for (const b of scene.buildings) {
    if (b.landmark || b.vessel) continue;
    if (ids && !ids.has(b.id)) continue;
    if (checked >= limit) break;
    checked++;
    const flags = new Set();
    const terrain = Number.isFinite(b.ground_z);
    const pieceList = b.parts?.length ? b.parts.map((p) => ({ part: p })) : [{ part: null }];
    const detail = [];
    for (const { part } of pieceList) {
      pieces++;
      const piece = part ?? b;
      const rec = { ...b, ground_z: terrain ? 0 : undefined, ground_plane: undefined };
      if (part) rec.parts = [part];
      const group = buildGeneric({ buildings: [rec] });
      const tris = triangles(group);
      const minh = piece.minh ?? 0;
      if (piece.h <= minh) flags.add('h_le_minh');
      if (PITCHED.has(piece.roof) && (piece.roofH ?? 0) > piece.h - minh)
        flags.add('roofh_gt_height');
      const r = checkPiece(tris, piece.polys, piece.h, minh, {
        rays,
        seed: b.seed ?? 0.5,
      });
      for (const f of r.flags) flags.add(f);
      if (r.flags.size || ids) detail.push({ part: part?.id, ...r.metrics, flags: [...r.flags] });
    }
    const area = footprintArea(b.polys);
    if (b.parts?.length) {
      const pts = samplePoints(b.polys, 100);
      const miss = pts.filter(([x, y]) => !b.parts.some((q) => insidePolys(q.polys, x, y)));
      if (pts.length && miss.length / pts.length > 0.1) flags.add('parts_gap');
      for (const q of b.parts) {
        if (!(q.minh > 1)) continue;
        const qp = samplePoints(q.polys, 40);
        const over = qp.filter(([x, y]) =>
          b.parts.some(
            (s) =>
              s !== q &&
              (s.minh ?? 0) < q.minh &&
              s.h >= q.minh - 0.5 &&
              insidePolys(s.polys, x, y),
          ),
        );
        if (qp.length && over.length / qp.length < 0.5) flags.add('part_floating');
      }
    }
    if (terrain && !b.ground_plane && Number.isFinite(b.ground_max)) {
      const minh = b.minh ?? 0;
      const rise = PITCHED.has(b.roof) ? Math.min(b.roofH || 3, (b.h - minh) * 0.6) : 0;
      if (b.ground_max - b.ground_z > b.h - rise) flags.add('terrain_buried');
    }
    if (flags.size) flagged++;
    for (const f of flags) {
      counts[f]++;
      note(
        f,
        b,
        area,
        detail.length ? { pieces: detail.filter((d) => d.flags.includes(f)).slice(0, 3) } : {},
      );
    }
    if (all) all.push({ id: b.id, c: b.c, roof: b.roof, flags: [...flags], detail });
    if (checked % 10000 === 0)
      process.stderr.write(`${checked} buildings, ${((Date.now() - t0) / 1000).toFixed(0)} s\n`);
  }
  const report = {
    scene: o._[0],
    modules,
    buildings: checked,
    pieces,
    flagged,
    seconds: Math.round((Date.now() - t0) / 1000),
    classes: CLASSES,
    counts,
    examples,
    ...(all ? { buildings_detail: all } : {}),
  };
  if (o.out) fs.writeFileSync(o.out, JSON.stringify(report, null, 2));
  console.log(`${checked} generic buildings (${pieces} pieces), ${flagged} flagged`);
  for (const [k, v] of Object.entries(counts)) {
    const ex = examples[k][0];
    console.log(
      `${k.padEnd(18)} ${String(v).padStart(6)}  ${ex ? `e.g. ${ex.id} at (${ex.c.join(', ')})` : ''}`,
    );
  }
  if (all) console.log(JSON.stringify(all, null, 1));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  await main();
