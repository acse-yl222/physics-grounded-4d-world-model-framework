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
