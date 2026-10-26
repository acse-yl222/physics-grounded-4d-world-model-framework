// Scene terrain sampler shared by the ground, building, landmark and tree builders
// and by viewers (e.g. to place tunnels relative to the real surface).
//
// scene.terrain (prepare_scene.py --terrain, see terrain.py) is a node grid:
// height(i, j) = base_m + scale_m * int16[j * nx + i] at x = x0 + i*dx, y = y0 + j*dx
// (row-major from the south-west, little-endian int16 in base64). Scenes without
// terrain are flat at z = 0 and every function here returns 0 for them.

const decoded = new WeakMap();

function decodeBase64(text) {
  if (typeof atob === 'function') {
    const bin = atob(text);
    const bytes = new Uint8Array(bin.length);
    for (let k = 0; k < bin.length; k++) bytes[k] = bin.charCodeAt(k);
    return bytes;
  }
  return Uint8Array.from(globalThis.Buffer.from(text, 'base64'));
}

/** Decoded terrain grid {x0, y0, dx, nx, ny, h: Float32Array} of a scene, or null. */
export function terrainOf(scene) {
  const t = scene?.terrain;
  if (!t) return null;
  if (decoded.has(t)) return decoded.get(t);
  const n = t.nx * t.ny;
  const h = new Float32Array(n);
  if (Array.isArray(t.z)) {
    for (let k = 0; k < n; k++) h[k] = t.base_m + t.scale_m * t.z[k];
  } else {
    if ((t.encoding ?? 'int16le-base64') !== 'int16le-base64')
      throw new Error(`unknown terrain encoding ${t.encoding}`);
    const bytes = decodeBase64(t.z);
    if (bytes.length !== 2 * n) throw new Error(`terrain: ${bytes.length} bytes for ${n} nodes`);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let k = 0; k < n; k++) h[k] = t.base_m + t.scale_m * view.getInt16(2 * k, true);
  }
  const grid = { x0: t.x0, y0: t.y0, dx: t.dx, nx: t.nx, ny: t.ny, h };
  decoded.set(t, grid);
  return grid;
}

export const hasTerrain = (scene) => Boolean(scene?.terrain);

/** Bilinear height of a decoded grid at (x, y), clamped to the grid extent. */
export function sample(grid, x, y) {
  const { x0, y0, dx, nx, ny, h } = grid;
  const fx = Math.min(Math.max((x - x0) / dx, 0), nx - 1),
    fy = Math.min(Math.max((y - y0) / dx, 0), ny - 1);
  const i = Math.min(Math.floor(fx), nx - 2),
    j = Math.min(Math.floor(fy), ny - 2);
  const u = fx - i,
    v = fy - j,
    k = j * nx + i;
  return (
    h[k] * (1 - u) * (1 - v) +
    h[k + 1] * u * (1 - v) +
    h[k + nx] * (1 - u) * v +
    h[k + nx + 1] * u * v
  );
}

/** Terrain height (scene z, metres) at ENU (x, y); 0 when the scene has no terrain. */
export function elevation(scene, x, y) {
  const grid = terrainOf(scene);
  return grid ? sample(grid, x, y) : 0;
}

/** (x, y) => height for a scene, or null for flat scenes (so callers keep z = 0). */
export function elevationFn(scene) {
  const grid = terrainOf(scene);
  return grid ? (x, y) => sample(grid, x, y) : null;
}

/** Lowest and highest terrain over a box {x0, y0, x1, y1}, sampled every `step` m. */
export function boxRange(scene, box, step) {
  const grid = terrainOf(scene);
  if (!grid) return { min: 0, max: 0 };
  const s = step ?? grid.dx / 2;
  let min = Infinity,
    max = -Infinity;
  const nx = Math.max(1, Math.ceil((box.x1 - box.x0) / s)),
    ny = Math.max(1, Math.ceil((box.y1 - box.y0) / s));
  for (let a = 0; a <= nx; a++)
    for (let b = 0; b <= ny; b++) {
      const z = sample(
        grid,
        box.x0 + ((box.x1 - box.x0) * a) / nx,
        box.y0 + ((box.y1 - box.y0) * b) / ny,
      );
      if (z < min) min = z;
      if (z > max) max = z;
    }
  return { min, max };
}
