// Shared three.js building kit: material library, batched mesh construction and
// footprint extrusion with storey-aligned facade UVs. Coordinates are scene ENU
// metres (x east, y north, z up); the exporter rotates the root into glTF y-up.
import * as THREE from 'three';
import {
  canvasTexture,
  facadeTexture,
  groundTexture,
  rng,
  roadTexture,
  roofTexture,
  shopTexture,
} from '../resources/materials/textures.mjs';

export { canvasTexture, rng };

const materials = new Map();

function standard(key, params) {
  if (materials.has(key)) return materials.get(key);
  const m = new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0, ...params });
  m.name = key;
  materials.set(key, m);
  return m;
}

// Plain colour materials for landmark detailing.
export const PALETTE = {
  portland_stone: ['#ddd6c4', 0.8],
  bath_stone: ['#d9c79e', 0.8],
  terracotta: ['#b8653f', 0.75],
  buff_terracotta: ['#cdb38a', 0.75],
  red_brick: ['#94503b', 0.9],
  london_stock: ['#b29c76', 0.9],
  white_render: ['#f1eee6', 0.7],
  concrete: ['#b3afa7', 0.9],
  dark_concrete: ['#7f7c77', 0.9],
  glass: ['#5d7484', 0.15, 0.2],
  dark_glass: ['#2e3d48', 0.1, 0.3],
  green_glass: ['#5f8a86', 0.12, 0.2],
  steel: ['#9aa1a6', 0.4, 0.7],
  dark_steel: ['#3d4347', 0.45, 0.6],
  white_steel: ['#e7e9ea', 0.45, 0.3],
  aluminium: ['#c4c9cc', 0.35, 0.6],
  copper_green: ['#6f9f8a', 0.6, 0.2],
  copper: ['#b0704a', 0.5, 0.6],
  lead: ['#7b8387', 0.6, 0.3],
  slate: ['#4d535a', 0.8],
  gold: ['#d6b04c', 0.3, 0.9],
  bronze: ['#7b5b3a', 0.45, 0.6],
  timber: ['#8a6a4a', 0.8],
  black: ['#222426', 0.6],
  white: ['#f7f7f5', 0.6],
  grass: ['#6f9152', 1],
  water: ['#4f7287', 0.2],
  asphalt: ['#47494c', 0.95],
  paving: ['#b9b2a4', 0.9],
  gravel: ['#b7a98a', 1],
  foliage: ['#4f7a3c', 0.95],
  dark_foliage: ['#3e6232', 0.95],
  bark: ['#5b4635', 0.95],
  red: ['#b4372f', 0.6],
  blue: ['#2f5d8c', 0.6],
};

/** Solid colour material by palette name, or by any CSS colour string. */
export function mat(name, opts = {}) {
  const p = PALETTE[name];
  const color = p ? p[0] : name;
  const key = `solid:${name}:${JSON.stringify(opts)}`;
  return standard(key, {
    color: new THREE.Color(color),
    roughness: p?.[1] ?? 0.8,
    metalness: p?.[2] ?? 0,
    ...opts,
  });
}

/** Windowed facade material (4 bays x 2 storeys per texture tile). */
export function facade(style, variant = 0) {
  return standard(`facade:${style}:${variant}`, {
    map: facadeTexture(style, variant),
    vertexColors: true,
  });
}
export const shopfront = (variant = 0) =>
  standard(`shop:${variant}`, { map: shopTexture(variant), vertexColors: true });
export const roof = (kind, variant = 0) =>
  standard(`roof:${kind}:${variant}`, { map: roofTexture(kind, variant), vertexColors: true });
export const ground = (kind) =>
  standard(`ground:${kind}`, {
    map: groundTexture(kind),
    roughness: kind === 'water' ? 0.25 : 0.95,
    metalness: kind === 'water' ? 0.1 : 0,
  });
export const road = (kind) => standard(`road:${kind}`, { map: roadTexture(kind), roughness: 0.95 });

/** Material from a custom canvas drawing (e.g. a facade traced from reference photos). */
export function paintedMaterial(key, w, h, draw, params = {}) {
  return standard(`painted:${key}`, {
    map: canvasTexture(`painted:${key}`, w, h, draw),
    ...params,
  });
}

/**
 * Accumulates triangles per material and emits one mesh per material. Vertices
 * are never shared between faces, so flat normals can be derived on load and the
 * exported files omit the normal attribute.
 */
export class MeshBatch {
  constructor() {
    this.buckets = new Map();
  }
  bucket(material) {
    let b = this.buckets.get(material);
    if (!b) this.buckets.set(material, (b = { p: [], uv: [], c: [], i: [] }));
    return b;
  }
  /** Append a polygon fan/strip given vertices [[x,y,z]], uvs [[u,v]] and triangle indices. */
  add(material, verts, uvs, tris, color = [1, 1, 1]) {
    const b = this.bucket(material);
    const base = b.p.length / 3;
    for (let k = 0; k < verts.length; k++) {
      b.p.push(verts[k][0], verts[k][1], verts[k][2]);
      b.uv.push(uvs[k][0], uvs[k][1]);
      b.c.push(color[0], color[1], color[2]);
    }
    for (const t of tris) b.i.push(base + t);
  }
  quad(material, a, b, c, d, uva, uvb, uvc, uvd, color) {
    this.add(material, [a, b, c, d], [uva, uvb, uvc, uvd], [0, 1, 2, 0, 2, 3], color);
  }
  /** Add an arbitrary THREE.BufferGeometry (transformed by matrix) to the batch. */
  addGeometry(material, geometry, matrix, color = [1, 1, 1]) {
    const g = geometry.index ? geometry.toNonIndexed() : geometry.clone();
    if (matrix) g.applyMatrix4(matrix);
    const p = g.attributes.position,
      uv = g.attributes.uv;
    const verts = [],
      uvs = [],
      tris = [];
    for (let k = 0; k < p.count; k++) {
      verts.push([p.getX(k), p.getY(k), p.getZ(k)]);
      uvs.push(uv ? [uv.getX(k), uv.getY(k)] : [0, 0]);
      tris.push(k);
    }
    this.add(material, verts, uvs, tris, color);
    g.dispose();
  }
  toGroup(name = 'batch') {
    const group = new THREE.Group();
    group.name = name;
    for (const [material, b] of this.buckets) {
      if (!b.i.length) continue;
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(b.p, 3));
      g.setAttribute('uv', new THREE.Float32BufferAttribute(b.uv, 2));
      if (material.vertexColors) g.setAttribute('color', new THREE.Float32BufferAttribute(b.c, 3));
      g.setIndex(b.p.length / 3 > 65535 ? new THREE.Uint32BufferAttribute(b.i, 1) : b.i);
      g.computeVertexNormals();
      const mesh = new THREE.Mesh(g, material);
      mesh.name = `${name}:${material.name}`;
      group.add(mesh);
    }
    this.buckets.clear();
    return group;
  }
}

/**
 * Extrude walls of polygons (outer CCW, holes CW) between z0 and z1. UVs map one
 * texture tile to 4 bays x 2 storeys measured from z=uvBase, with an integer number
 * of bays per edge so windows never straddle corners.
 */
export function walls(
  batch,
  material,
  polys,
  z0,
  z1,
  { bay = 3.6, storey = 3.2, uvBase = 0, color } = {},
) {
  for (const poly of polys)
    for (const ring of poly)
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 0.05) continue;
        const n = Math.round(len / bay);
        // Short edges show only the pier at the left of the tile.
        const u1 = n >= 1 ? n / 4 : 0.03;
        const v0 = (z0 - uvBase) / (2 * storey),
          v1 = (z1 - uvBase) / (2 * storey);
        batch.quad(
          material,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [b[0], b[1], z1],
          [a[0], a[1], z1],
          [0, v0],
          [u1, v0],
          [u1, v1],
          [0, v1],
          color,
        );
      }
}

/** Triangulated horizontal cap of polygons at height z (normal +z or -z). */
export function cap(batch, material, polys, z, { scale = 8, down = false, color } = {}) {
  for (const poly of polys) {
    const contour = poly[0].map(([x, y]) => new THREE.Vector2(x, y));
    const holes = poly.slice(1).map((r) => r.map(([x, y]) => new THREE.Vector2(x, y)));
    let tris;
    try {
      tris = THREE.ShapeUtils.triangulateShape(contour, holes);
    } catch {
      continue;
    }
    const pts = [...contour, ...holes.flat()];
    const verts = pts.map((p) => [p.x, p.y, z]);
    const uvs = pts.map((p) => [p.x / scale, p.y / scale]);
    const idx = [];
    for (const t of tris) down ? idx.push(t[0], t[2], t[1]) : idx.push(t[0], t[1], t[2]);
    batch.add(material, verts, uvs, idx, color);
  }
}

/** Oriented rectangle of a ring along a given axis angle: {c, s, u0, u1, v0, v1}. */
export function orientedExtent(ring, angle) {
  const c = Math.cos(angle),
    s = Math.sin(angle);
  let u0 = Infinity,
    u1 = -Infinity,
    v0 = Infinity,
    v1 = -Infinity;
  for (const [x, y] of ring) {
    const u = x * c + y * s,
      v = -x * s + y * c;
    u0 = Math.min(u0, u);
    u1 = Math.max(u1, u);
    v0 = Math.min(v0, v);
    v1 = Math.max(v1, v);
  }
  const at = (u, v, z) => [u * c - v * s, u * s + v * c, z];
  return { c, s, u0, u1, v0, v1, at };
}

/**
 * Pitched roof over the oriented rectangle of `ring`, ridge along `angle`.
 * kind: gabled | hipped | pyramidal | mansard. Gable ends use the wall material.
 */
export function pitchedRoof(
  batch,
  roofMat,
  wallMat,
  ring,
  angle,
  eave,
  rise,
  kind = 'gabled',
  opts = {},
) {
  const { overhang = 0.35, color, wallColor, storey = 3.2 } = opts;
  const e = orientedExtent(ring, angle);
  const u0 = e.u0 - overhang,
    u1 = e.u1 + overhang,
    v0 = e.v0 - overhang,
    v1 = e.v1 + overhang;
  const vm = (v0 + v1) / 2,
    half = (v1 - v0) / 2,
    top = eave + rise;
  let r0 = u0,
    r1 = u1;
  if (kind === 'hipped' || kind === 'mansard') {
    const inset = Math.min(half, (u1 - u0) / 2 - 0.01);
    r0 = u0 + inset;
    r1 = u1 - inset;
  } else if (kind === 'pyramidal') {
    r0 = r1 = (u0 + u1) / 2;
  }
  const P = (u, v, z) => e.at(u, v, z);
  const slope = Math.hypot(half, rise);
  const s = 3; // roof texture metres per tile is ~3 m
  // Two long slopes.
  batch.add(
    roofMat,
    [P(u0, v0, eave), P(u1, v0, eave), P(r1, vm, top), P(r0, vm, top)],
    [
      [u0 / s, 0],
      [u1 / s, 0],
      [r1 / s, slope / s],
      [r0 / s, slope / s],
    ],
    [0, 1, 2, 0, 2, 3],
    color,
  );
  batch.add(
    roofMat,
    [P(u1, v1, eave), P(u0, v1, eave), P(r0, vm, top), P(r1, vm, top)],
    [
      [-u1 / s, 0],
      [-u0 / s, 0],
      [-r0 / s, slope / s],
      [-r1 / s, slope / s],
    ],
    [0, 1, 2, 0, 2, 3],
    color,
  );
  if (r0 > u0 + 1e-3) {
    // Hipped ends.
    const hs = Math.hypot(r0 - u0, rise);
    batch.add(
      roofMat,
      [P(u0, v1, eave), P(u0, v0, eave), P(r0, vm, top)],
      [
        [v1 / s, 0],
        [v0 / s, 0],
        [vm / s, hs / s],
      ],
      [0, 1, 2],
      color,
    );
    batch.add(
      roofMat,
      [P(u1, v0, eave), P(u1, v1, eave), P(r1, vm, top)],
      [
        [v0 / s, 0],
        [v1 / s, 0],
        [vm / s, hs / s],
      ],
      [0, 1, 2],
      color,
    );
  } else {
    // Gable triangles in the wall material.
    const g0 = eave / (2 * storey),
      g1 = top / (2 * storey);
    const gu = (v) => (v - v0) / (4 * 3.6);
    batch.add(
      wallMat,
      [P(e.u0, v1, eave), P(e.u0, v0, eave), P(e.u0, vm, top)],
      [
        [gu(v1), g0],
        [gu(v0), g0],
        [gu(vm), g1],
      ],
      [0, 1, 2],
      wallColor,
    );
    batch.add(
      wallMat,
      [P(e.u1, v0, eave), P(e.u1, v1, eave), P(e.u1, vm, top)],
      [
        [gu(v0), g0],
        [gu(v1), g0],
        [gu(vm), g1],
      ],
      [0, 1, 2],
      wallColor,
    );
    // Close the overhang soffit triangles under the verge.
  }
  return { e, ridge: [P(r0, vm, top), P(r1, vm, top)], top };
}

/** Axis-aligned box centred at (x, y) with base z0, rotated by angle about z. */
export function box(batch, material, x, y, z0, w, d, h, angle = 0, color) {
  const g = new THREE.BoxGeometry(w, d, h);
  const m = new THREE.Matrix4().makeRotationZ(angle).setPosition(x, y, z0 + h / 2);
  batch.addGeometry(material, g, m, color);
  g.dispose();
}

/** Signed area of a ring (positive = CCW). */
export function ringArea(ring) {
  let a = 0;
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    a += p[0] * q[1] - q[0] * p[1];
  }
  return a / 2;
}

/** Offset a simple ring by d metres (positive grows a CCW ring); miter clamped. */
export function offsetRing(ring, d) {
  const n = ring.length,
    out = [];
  for (let k = 0; k < n; k++) {
    const a = ring[(k - 1 + n) % n],
      b = ring[k],
      c = ring[(k + 1) % n];
    let e1x = b[0] - a[0],
      e1y = b[1] - a[1],
      e2x = c[0] - b[0],
      e2y = c[1] - b[1];
    const l1 = Math.hypot(e1x, e1y) || 1,
      l2 = Math.hypot(e2x, e2y) || 1;
    const n1 = [e1y / l1, -e1x / l1],
      n2 = [e2y / l2, -e2x / l2];
    let mx = n1[0] + n2[0],
      my = n1[1] + n2[1];
    const ml = Math.hypot(mx, my) || 1;
    mx /= ml;
    my /= ml;
    const cos = Math.max(0.35, mx * n1[0] + my * n1[1]);
    out.push([b[0] + (mx * d) / cos, b[1] + (my * d) / cos]);
  }
  return out;
}

/** Ring centroid and principal (oriented bounding box) axis. */
export function ringFrame(ring) {
  let best = null;
  for (let k = 0; k < ring.length; k++) {
    const a = ring[k],
      b = ring[(k + 1) % ring.length];
    const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const e = orientedExtent(ring, ang);
    const area = (e.u1 - e.u0) * (e.v1 - e.v0);
    if (!best || area < best.area) best = { area, ang, e };
  }
  const { e, ang } = best;
  const L = e.u1 - e.u0,
    W = e.v1 - e.v0;
  const centre = e.at((e.u0 + e.u1) / 2, (e.v0 + e.v1) / 2, 0);
  return L >= W
    ? { cx: centre[0], cy: centre[1], angle: ang, length: L, width: W }
    : { cx: centre[0], cy: centre[1], angle: ang + Math.PI / 2, length: W, width: L };
}

// ---------------------------------------------------------------------------
// Detailing helpers: real geometry for elements that read at street level.
// Edges run a -> b along a wall; for an outer CCW ring the outward normal is on
// the right of a -> b. All helpers add to a MeshBatch.
// ---------------------------------------------------------------------------

function edgeFrame(a, b) {
  const dx = b[0] - a[0],
    dy = b[1] - a[1];
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len,
    uy = dy / len;
  return { len, ux, uy, nx: uy, ny: -ux, angle: Math.atan2(dy, dx) };
}

/**
 * A row of windows on wall edge a -> b at sill height z: glass panel proud of the
 * wall plus frame, sill, lintel (or a round/segmental arch head) and optional
 * glazing bars. Returns the window centres.
 */
export function windowRow(batch, a, b, z, opts = {}) {
  const {
    width = 1.2,
    height = 2.0,
    count,
    bay = 3.6,
    margin = 0.6,
    depth = 0.12,
    glass = mat('dark_glass'),
    frame = mat('white'),
    sill = frame,
    head = 'lintel', // lintel | arch | segment | pediment | none
    bars = 1, // glazing bars each way
    surround = 0, // stone surround width (0 = none)
    surroundMat = mat('portland_stone'),
  } = opts;
  const f = edgeFrame(a, b);
  const usable = f.len - 2 * margin;
  const n = count ?? Math.max(0, Math.floor(usable / bay + 0.35));
  const centres = [];
  for (let k = 0; k < n; k++) {
    const t = margin + (usable * (k + 0.5)) / n;
    const cx = a[0] + f.ux * t,
      cy = a[1] + f.uy * t;
    const out = (d) => [cx + f.nx * d, cy + f.ny * d];
    const [gx, gy] = out(0.03);
    box(batch, glass, gx, gy, z, width, 0.04, height, f.angle);
    if (surround > 0) {
      const [sx, sy] = out(depth * 0.5);
      for (const s of [-1, 1])
        box(
          batch,
          surroundMat,
          sx + f.ux * s * (width / 2 + surround / 2),
          sy + f.uy * s * (width / 2 + surround / 2),
          z - 0.05,
          surround,
          depth,
          height + 0.1,
          f.angle,
        );
    }
    const [fx, fy] = out(depth * 0.5);
    for (const s of [-1, 1])
      box(
        batch,
        frame,
        fx + f.ux * s * (width / 2),
        fy + f.uy * s * (width / 2),
        z,
        0.08,
        depth,
        height,
        f.angle,
      );
    if (bars)
      for (let i = 1; i <= bars; i++) {
        box(
          batch,
          frame,
          fx,
          fy,
          z + (height * i) / (bars + 1) - 0.025,
          width,
          depth * 0.6,
          0.05,
          f.angle,
        );
        box(
          batch,
          frame,
          fx + f.ux * (width * (i / (bars + 1) - 0.5)),
          fy + f.uy * (width * (i / (bars + 1) - 0.5)),
          z,
          0.05,
          depth * 0.6,
          height,
          f.angle,
        );
      }
    const [ox, oy] = out(depth * 0.9);
    box(batch, sill, ox, oy, z - 0.1, width + 0.25, depth * 1.8, 0.1, f.angle);
    if (head === 'lintel')
      box(batch, sill, ox, oy, z + height, width + 0.2, depth * 1.4, 0.18, f.angle);
    else if (head === 'pediment') {
      box(batch, sill, ox, oy, z + height, width + 0.3, depth * 1.6, 0.14, f.angle);
      const g = new THREE.CylinderGeometry(width * 0.62, width * 0.62, depth * 1.4, 3, 1).rotateX(
        Math.PI / 2,
      );
      g.scale(1, 0.32, 1);
      const m = new THREE.Matrix4()
        .makeRotationZ(f.angle)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      m.setPosition(ox, oy, z + height + 0.14 + width * 0.12);
      batch.addGeometry(sill, g, m);
      g.dispose();
    } else if (head === 'arch' || head === 'segment') {
      const r = width / 2,
        seg = head === 'arch' ? Math.PI : Math.PI / 2.5;
      const g = new THREE.CylinderGeometry(r, r, 0.04, 10, 1, false, Math.PI / 2 - seg / 2, seg);
      const m = new THREE.Matrix4()
        .makeRotationZ(f.angle)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      m.setPosition(gx, gy, z + height - (head === 'segment' ? r * Math.cos(seg / 2) : 0));
      batch.addGeometry(glass, g, m);
      const ring = new THREE.TorusGeometry(r + 0.05, 0.07, 4, 10, seg).rotateZ(
        Math.PI / 2 - seg / 2,
      );
      const m2 = new THREE.Matrix4()
        .makeRotationZ(f.angle)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      m2.setPosition(ox, oy, z + height - (head === 'segment' ? r * Math.cos(seg / 2) : 0));
      batch.addGeometry(sill, ring, m2);
      g.dispose();
      ring.dispose();
    }
    centres.push([cx, cy]);
  }
  return centres;
}

/** Windows on every edge of a ring, storey by storey (z0 = first sill, storey height). */
export function windowGrid(batch, ring, z0, storeys, storey, opts = {}) {
  for (let s = 0; s < storeys; s++)
    for (let k = 0; k < ring.length; k++)
      windowRow(
        batch,
        ring[k],
        ring[(k + 1) % ring.length],
        z0 + s * storey,
        typeof opts === 'function' ? opts(s, k) : opts,
      );
}

/**
 * Projecting band around a ring (cornice, string course, plinth): outer face at
 * offset `projection`, from z to z + height, with top and bottom caps.
 */
export function cornice(
  batch,
  material,
  ring,
  z,
  { height = 0.5, projection = 0.4, steps = 1 } = {},
) {
  for (let s = 0; s < steps; s++) {
    const p = projection * ((s + 1) / steps);
    const h = height / steps;
    const zz = z + s * h;
    const outer = offsetRing(ring, p);
    walls(batch, material, [[outer]], zz, zz + h, { bay: 1e6 });
    cap(batch, material, [[outer, ring.slice().reverse()]], zz + h);
    cap(batch, material, [[outer, ring.slice().reverse()]], zz, { down: true });
  }
}

/** Evenly spaced round columns (with base and capital) from a to b. */
export function colonnade(
  batch,
  material,
  a,
  b,
  z0,
  height,
  { count, radius = 0.35, offset = 0, capital = 'doric', segments = 12 } = {},
) {
  const f = edgeFrame(a, b);
  const n = count ?? Math.max(2, Math.round(f.len / (radius * 8)) + 1);
  const shaft = new THREE.CylinderGeometry(radius * 0.88, radius, height * 0.86, segments).rotateX(
    Math.PI / 2,
  );
  const base = new THREE.CylinderGeometry(
    radius * 1.25,
    radius * 1.3,
    height * 0.05,
    segments,
  ).rotateX(Math.PI / 2);
  const capG =
    capital === 'corinthian'
      ? new THREE.CylinderGeometry(radius * 1.35, radius * 0.95, height * 0.09, segments).rotateX(
          Math.PI / 2,
        )
      : new THREE.BoxGeometry(radius * 2.5, radius * 2.5, height * 0.05);
  for (let k = 0; k < n; k++) {
    const t = n === 1 ? 0.5 : k / (n - 1);
    const x = a[0] + (b[0] - a[0]) * t + f.nx * offset,
      y = a[1] + (b[1] - a[1]) * t + f.ny * offset;
    const m = new THREE.Matrix4();
    batch.addGeometry(material, base, m.makeTranslation(x, y, z0 + height * 0.025));
    batch.addGeometry(material, shaft, m.makeTranslation(x, y, z0 + height * 0.05 + height * 0.43));
    batch.addGeometry(
      material,
      capG,
      m.makeTranslation(x, y, z0 + height * (capital === 'corinthian' ? 0.955 : 0.975)),
    );
  }
  [shaft, base, capG].forEach((g) => g.dispose());
}

/** Balustrade along a polyline: top rail, bottom rail and turned balusters. */
export function balustrade(batch, material, line, z, { height = 1.0, spacing = 0.3 } = {}) {
  const post = new THREE.CylinderGeometry(0.05, 0.07, height * 0.75, 6).rotateX(Math.PI / 2);
  for (let k = 1; k < line.length; k++) {
    const a = line[k - 1],
      b = line[k];
    const f = edgeFrame(a, b);
    const mx = (a[0] + b[0]) / 2,
      my = (a[1] + b[1]) / 2;
    box(batch, material, mx, my, z + height * 0.85, f.len, 0.25, height * 0.15, f.angle);
    box(batch, material, mx, my, z, f.len, 0.25, height * 0.1, f.angle);
    const n = Math.floor(f.len / spacing);
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n;
      batch.addGeometry(
        material,
        post,
        new THREE.Matrix4().makeTranslation(
          a[0] + (b[0] - a[0]) * t,
          a[1] + (b[1] - a[1]) * t,
          z + height * 0.475,
        ),
      );
    }
  }
  post.dispose();
}

/** Solid of revolution about z from a profile [[radius, z], ...] (domes, drums, finials). */
export function lathe(material, profile, { segments = 32, x = 0, y = 0, z = 0 } = {}) {
  const g = new THREE.LatheGeometry(
    profile.map(([r, h]) => new THREE.Vector2(r, h)),
    segments,
  ).rotateX(Math.PI / 2);
  const mesh = new THREE.Mesh(g, material);
  mesh.position.set(x, y, z);
  return mesh;
}
