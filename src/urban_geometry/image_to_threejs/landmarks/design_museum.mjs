// Design Museum, Kensington High Street - the former Commonwealth Institute (RMJM,
// 1962; Grade II*), converted by OMA / Allies and Morrison with John Pawson interiors
// (2016). A 55.8 m (183 ft) square "tent in the park": a copper-clad hyperbolic
// paraboloid roof - central saddle section (28 m square) flanked by four outer warps -
// rising from about 9 m at the side edges to 24 m peaks over the front and back,
// carried by concrete legs at the front and back; walls of sky-blue glazing on a
// rich grid of mullions and transoms recalling the original turquoise skin.
export default {
  id: 'design_museum',
  name: 'Design Museum (former Commonwealth Institute)',
  claims: ['5c24def6-8f83-48a5-88be-dee535a9d67a'],
  references: [
    {
      title: "Creating the Design Museum's new home - Building",
      url: 'https://building.co.uk/buildings/creating-the-design-museums-new-home/5067505.article',
      used_for:
        '183 ft square plan, 93 ft central section, heights 30 ft lowest to 80 ft peaks, central concrete shell plus four outer warps',
    },
    {
      title: 'Commonwealth Institute - RBKC listed buildings',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=1227441',
      used_for: 'listing: central hyperbolic paraboloids flanked by four warps',
    },
    {
      title: 'The Design Museum - London Gardens Trust',
      url: 'https://londongardenstrust.org/conservation/inventory/site-record?ID=KAC044',
      used_for: 'RMJM 1962, hyperbolic paraboloid copper roof; re-clad curtain wall',
    },
    {
      title: 'Design Museum - Allies and Morrison',
      url: 'https://alliesandmorrison.com/projects/design-museum',
      used_for:
        'sky-blue dot-on-dot frit recalling the turquoise facades, replicated grid of mullions and transoms',
    },
    {
      title: 'New Design Museum: raising the roof - Building',
      url: 'https://building.co.uk/buildings/new-design-museum-raising-the-roof/5084994.article',
      used_for: 'original blue glass and blockwork skin',
    },
    {
      title: 'The Design Museum - IStructE awards',
      url: 'https://istructe.org/structural-awards/projects/2017/the-design-museum',
      used_for: '55 m x 55 m roof retained during conversion',
    },
  ],
  notes:
    'Roof modelled as a ruled saddle surface (straight rulings across, smooth quadratic profile along the axis) through a profile of 17 m at the centre, 24.4 m peaks ' +
    'at the edges of the central section and 21 m at the front/back edge mid-points, falling to 9.1 m at the sides; ' +
    'the true form of the two central hypars and the warps is approximated. Front assumed to face Kensington ' +
    'High Street (north). Facade grid is a painted pattern, not traced.',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0];
    // Identify corners: front edge = the edge whose midpoint is furthest north.
    let best = -Infinity,
      k0 = 0;
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const my = (p[1] + q[1]) / 2;
      if (my > best) ((best = my), (k0 = k));
    }
    // ring is CCW: front edge runs from NE corner (k0) to NW corner (k0+1)
    const n = ring.length;
    const NE = ring[k0],
      NW = ring[(k0 + 1) % n],
      SW = ring[(k0 + 2) % n],
      SE = ring[(k0 + 3) % n];
    const P = (s, t) => {
      // s: 0 west .. 1 east, t: 0 back (south) .. 1 front (north)
      const bx = (1 - s) * SW[0] + s * SE[0],
        by = (1 - s) * SW[1] + s * SE[1],
        fx = (1 - s) * NW[0] + s * NE[0],
        fy = (1 - s) * NW[1] + s * NE[1];
      return [(1 - t) * bx + t * fx, (1 - t) * by + t * fy];
    };
    const C = 0.507; // central section half-width as a fraction of the half-side
    // smooth profile through 17 m (centre), 24.4 m (edge of the central section) and 21 m (facade)
    const qb = (7.4 - 4 * C) / (C * C - C),
      qa = 4 - qb;
    const Zu = (su) => 17 + qa * su + qb * su * su;
    const Z = (s, t) => {
      const su = Math.min(1, Math.abs(2 * t - 1)),
        sv = Math.min(1, Math.abs(2 * s - 1));
      return 9.1 + (Zu(su) - 9.1) * (1 - sv);
    };

    const copper = kit.paintedMaterial(
      'design_museum:copper',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.771);
        c.fillStyle = '#8d5d40';
        c.fillRect(0, 0, w, h);
        // standing-seam copper strips with slight weathering
        for (let x = 0; x < w; x += 16) {
          const k = 0.88 + r() * 0.22;
          const col = new THREE.Color('#9b6a4a').multiplyScalar(k);
          c.fillStyle = '#' + col.getHexString();
          c.fillRect(x + 1, 0, 14, h);
          c.fillStyle = '#6e4630';
          c.fillRect(x, 0, 1.5, h);
        }
        for (let i = 0; i < 40; i++) {
          c.fillStyle = 'rgba(90,130,110,0.10)';
          c.fillRect(r() * w, r() * h, 6 + r() * 30, 3 + r() * 12);
        }
      },
      { roughness: 0.55, metalness: 0.45, side: THREE.DoubleSide },
    );
    const fascia = kit.mat('#6d4834', { roughness: 0.6, metalness: 0.4 });
    const soffit = kit.mat('#d9d6cf');
    const concrete = kit.mat('concrete');
    // Blue glazed curtain wall: 1.5 m panels with deep mullions, a spandrel band
    // per floor and a sky-blue frit.
    const wallMat = kit.paintedMaterial('design_museum:glazing', 512, 512, (c, w, h) => {
      c.fillStyle = '#7fa6c4';
      c.fillRect(0, 0, w, h);
      const cols = 8,
        rows = 8;
      for (let i = 0; i < cols; i++)
        for (let j = 0; j < rows; j++) {
          const x = (i * w) / cols,
            y = (j * h) / rows;
          const opaque = j % 4 === 3;
          c.fillStyle = opaque ? '#4f7591' : j % 2 ? '#8db6d2' : '#9cc2dc';
          c.fillRect(x + 3, y + 3, w / cols - 6, h / rows - 6);
          // dot frit
          c.fillStyle = 'rgba(235,245,250,0.35)';
          for (let a = 6; a < w / cols - 6; a += 6)
            for (let b = 6; b < h / rows - 6; b += 6) c.fillRect(x + a, y + b, 1.5, 1.5);
        }
      c.fillStyle = '#e4e7e8';
      for (let i = 0; i <= cols; i++) c.fillRect((i * w) / cols - 2, 0, 4, h);
      for (let j = 0; j <= rows; j++)
        c.fillRect(0, (j * h) / rows - (j % 4 === 0 ? 4 : 1.5), w, j % 4 === 0 ? 8 : 3);
    });
    const TILE = 12; // metres per wall texture tile (8 x 1.5 m panels)

    // ---- roof surface -----------------------------------------------------
    const N = 28,
      ov = 0.022; // overhang ~1.2 m
    const RT = 0.9; // roof thickness at the edge
    const grid = [];
    for (let j = 0; j <= N; j++) {
      const row = [];
      for (let i = 0; i <= N; i++) {
        const s = -ov + ((1 + 2 * ov) * i) / N,
          t = -ov + ((1 + 2 * ov) * j) / N;
        const [x, y] = P(s, t);
        row.push([x, y, Z(Math.min(1, Math.max(0, s)), Math.min(1, Math.max(0, t))) + 0.4]);
      }
      grid.push(row);
    }
    const uvOf = (p) => [p[0] / 6, p[1] / 6];
    for (let j = 0; j < N; j++)
      for (let i = 0; i < N; i++) {
        const a = grid[j][i],
          b = grid[j][i + 1],
          c = grid[j + 1][i + 1],
          d = grid[j + 1][i];
        batch.quad(copper, a, b, c, d, uvOf(a), uvOf(b), uvOf(c), uvOf(d));
        const dn = (p) => [p[0], p[1], p[2] - RT];
        batch.quad(soffit, dn(a), dn(d), dn(c), dn(b), [0, 0], [0, 1], [1, 1], [1, 0]);
      }
    // fascia around the roof edge
    const edge = [];
    for (let i = 0; i < N; i++) edge.push(grid[0][i]);
    for (let j = 0; j < N; j++) edge.push(grid[j][N]);
    for (let i = N; i > 0; i--) edge.push(grid[N][i]);
    for (let j = N; j > 0; j--) edge.push(grid[j][0]);
    for (let k = 0; k < edge.length; k++) {
      const a = edge[k],
        b = edge[(k + 1) % edge.length];
      batch.quad(
        fascia,
        [a[0], a[1], a[2] - RT],
        [b[0], b[1], b[2] - RT],
        b,
        a,
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }

    // ---- glazed walls under the roof edge --------------------------------
    const sides = [
      [(u) => [u, 0]], // south: s 0..1 at t=0  (SW -> SE)
      [(u) => [1, u]], // east: t 0..1 at s=1 (SE -> NE)
      [(u) => [1 - u, 1]], // north: NE -> NW
      [(u) => [0, 1 - u]], // west: NW -> SW
    ];
    const M = 20;
    for (const [f] of sides) {
      let dist = 0;
      for (let k = 0; k < M; k++) {
        const [s0, t0] = f(k / M),
          [s1, t1] = f((k + 1) / M);
        const a = P(s0, t0),
          b = P(s1, t1);
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const za = Z(s0, t0) + 0.4 - RT - 0.2,
          zb = Z(s1, t1) + 0.4 - RT - 0.2;
        batch.quad(
          wallMat,
          [a[0], a[1], 0],
          [b[0], b[1], 0],
          [b[0], b[1], zb],
          [a[0], a[1], za],
          [dist / TILE, 0],
          [(dist + len) / TILE, 0],
          [(dist + len) / TILE, zb / TILE],
          [dist / TILE, za / TILE],
        );
        dist += len;
      }
    }
    // plinth / ground-floor band (darker, recessed entrance glazing)
    kit.walls(batch, kit.mat('dark_glass'), [[kit.offsetRing(ring, 0.05)]], 0, 0.15);

    // ---- concrete legs under the front and back peaks -------------------
    for (const t of [0, 1]) {
      for (const s of [0.5 - C / 2 + 0.02, 0.5 + C / 2 - 0.02]) {
        const tOut = t === 0 ? -0.035 : 1.035;
        const [x0, y0] = P(s, t),
          [x1, y1] = P(s, tOut);
        const zTop = Z(s, t) - 0.6;
        // raking strut from the ground outside the wall up to the roof edge
        const dx = x0 - x1,
          dy = y0 - y1,
          L = Math.hypot(dx, dy, zTop);
        const geo = new THREE.BoxGeometry(1.2, 1.2, L);
        const dir = new THREE.Vector3(dx, dy, zTop).normalize();
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
        const m = new THREE.Matrix4().compose(
          new THREE.Vector3((x0 + x1) / 2, (y0 + y1) / 2, zTop / 2),
          q,
          new THREE.Vector3(1, 1, 1),
        );
        batch.addGeometry(concrete, geo, m);
        geo.dispose();
      }
    }
    g.add(batch.toGroup('design_museum'));
    return g;
  },
};
