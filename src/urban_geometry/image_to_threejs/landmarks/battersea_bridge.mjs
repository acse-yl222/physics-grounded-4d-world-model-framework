// Battersea Bridge (Sir Joseph Bazalgette, 1886-90). Five iron arch spans of
// unequal radii rising to a distinct central apex, springing from granite-faced
// piers with pointed cutwaters; open iron spandrels, iron parapet railings and
// lamp standards over the piers.
export default {
  id: 'battersea_bridge',
  name: 'Battersea Bridge',
  claims: [],
  references: [
    {
      title: 'Battersea Bridge - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Battersea_Bridge',
      used_for: 'Bazalgette 1890 bridge, five spans, cast iron and granite, ~40 ft width',
    },
    {
      title: 'Battersea Bridge - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101080752-battersea-bridge-chelsea-riverside-ward',
      used_for:
        'listing: 5 spans of unequal radii rising to a central apex, iron spans springing from stone-faced piers',
    },
    {
      title: "Battersea's river crossings - Battersea Society",
      url: 'https://batterseasociety.org.uk/heritage-blog/batterseas-river-crossings',
      used_for: 'history and general appearance',
    },
  ],
  notes:
    'No footprint; centreline from the scene "Battersea Bridge" road, pier positions from the gaps in the scene Thames ' +
    'polygons along it (4 piers, 5 spans). Flat scene: deck rises to a 5 m apex and returns to road level at the ' +
    'banks. Dark green paint with gilt details is from general knowledge, not confirmed by a returned source.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const A = [1882.5, -2719],
      B = [1996, -2920];
    const L = Math.hypot(B[0] - A[0], B[1] - A[1]);
    const d = [(B[0] - A[0]) / L, (B[1] - A[1]) / L],
      n = [-d[1], d[0]];
    const ang = Math.atan2(d[1], d[0]);
    const P = (s, t, z) => [A[0] + d[0] * s + n[0] * t, A[1] + d[1] * s + n[1] * t, z];
    const proj = ([x, y]) => (x - A[0]) * d[0] + (y - A[1]) * d[1];
    const piers = [
      [1903, -2755.5],
      [1925.5, -2796],
      [1952.5, -2843],
      [1975, -2884],
    ].map(proj);
    const HM = 5.2,
      Z0 = 0.3;
    const deckZ = (s) => {
      if (s <= 0 || s >= L) return Z0;
      const u = Math.abs((2 * s) / L - 1);
      return Z0 + HM * (1 - u ** 1.6);
    };
    const W = 13.4,
      CW = 8.6;

    const green = kit.mat('#2f4a3a', { roughness: 0.55, metalness: 0.2 });
    const gilt = kit.mat('gold');
    const granite = kit.mat('#a7a49e', { roughness: 0.9 });
    const asphalt = kit.mat('asphalt');
    const paving = kit.mat('paving');
    const spandrel = kit.paintedMaterial(
      'battersea_bridge:spandrel',
      256,
      128,
      (c, w, h) => {
        c.fillStyle = '#2f4a3a';
        c.fillRect(0, 0, w, h);
        c.strokeStyle = '#1b2a21';
        c.lineWidth = 10;
        for (let k = 0; k < 4; k++) {
          c.beginPath();
          c.arc(k * 64 + 32, 64, 22, 0, Math.PI * 2);
          c.stroke();
        }
        c.strokeStyle = '#c9a548';
        c.lineWidth = 3;
        for (let k = 0; k < 4; k++) {
          c.beginPath();
          c.arc(k * 64 + 32, 64, 22, 0, Math.PI * 2);
          c.stroke();
        }
        c.fillStyle = '#c9a548';
        c.fillRect(0, 0, w, 5);
      },
      { roughness: 0.55 },
    );
    const m4 = new THREE.Matrix4();
    const up = new THREE.Vector3(0, 1, 0);
    const rod = (mat, p, q, r = 0.08, seg = 4) => {
      const a = new THREE.Vector3(...p),
        b = new THREE.Vector3(...q);
      const len = a.distanceTo(b);
      if (len < 0.01) return;
      const quat = new THREE.Quaternion().setFromUnitVectors(up, b.clone().sub(a).normalize());
      m4.compose(a.clone().add(b).multiplyScalar(0.5), quat, new THREE.Vector3(1, 1, 1));
      batch.addGeometry(mat, new THREE.CylinderGeometry(r, r, len, seg, 1, true), m4);
    };
    const put = (mat, geo, x, y, z, rz = ang) =>
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));

    // Deck surfaces and fascia.
    const N = 60,
      s0 = -6,
      s1 = L + 6;
    for (let k = 0; k < N; k++) {
      const sa = s0 + ((s1 - s0) * k) / N,
        sb = s0 + ((s1 - s0) * (k + 1)) / N;
      const za = deckZ(sa),
        zb = deckZ(sb);
      const strip = (mat, t0, t1, dz = 0) =>
        batch.quad(
          mat,
          P(sa, t0, za + dz),
          P(sb, t0, zb + dz),
          P(sb, t1, zb + dz),
          P(sa, t1, za + dz),
          [sa / 8, t0 / 8],
          [sb / 8, t0 / 8],
          [sb / 8, t1 / 8],
          [sa / 8, t1 / 8],
        );
      strip(asphalt, -CW / 2, CW / 2);
      strip(paving, CW / 2, W / 2, 0.15);
      strip(paving, -W / 2, -CW / 2, 0.15);
      for (const side of [-1, 1]) {
        const t = (side * W) / 2;
        const q =
          side > 0
            ? [P(sb, t, zb - 0.6), P(sa, t, za - 0.6), P(sa, t, za + 0.15), P(sb, t, zb + 0.15)]
            : [P(sa, t, za - 0.6), P(sb, t, zb - 0.6), P(sb, t, zb + 0.15), P(sa, t, za + 0.15)];
        batch.quad(green, ...q, [0, 0], [1, 0], [1, 1], [0, 1]);
        rod(green, P(sa, t, za + 1.15), P(sb, t, zb + 1.15), 0.08);
        rod(green, P(sa, t, za + 0.6), P(sb, t, zb + 0.6), 0.04);
        for (let j = 0; j < 3; j++) {
          const s = sa + ((sb - sa) * j) / 3;
          rod(green, P(s, t, deckZ(s) + 0.15), P(s, t, deckZ(s) + 1.15), 0.035, 3);
        }
      }
    }

    // Arches: outer spandrel faces, ribs and soffits between piers and abutments.
    const bounds = [0, ...piers, L];
    const PW = 4.2; // pier length along the bridge
    for (let k = 0; k < bounds.length - 1; k++) {
      const sa = bounds[k] + (k === 0 ? 0 : PW / 2),
        sb = bounds[k + 1] - (k === bounds.length - 2 ? 0 : PW / 2);
      const mid = (sa + sb) / 2,
        half = (sb - sa) / 2;
      const spring = 0.35;
      const crown = deckZ(mid) - 0.9;
      const arch = (s) => spring + (crown - spring) * (1 - ((s - mid) / half) ** 2);
      const M = 16;
      for (let j = 0; j < M; j++) {
        const a = sa + ((sb - sa) * j) / M,
          b = sa + ((sb - sa) * (j + 1)) / M;
        const za = arch(a),
          zb = arch(b),
          da = deckZ(a) - 0.6,
          db = deckZ(b) - 0.6;
        for (const side of [-1, 1]) {
          const t = side * (W / 2 - 0.3);
          const uv = [
            [a / 4, za / 2.5],
            [b / 4, zb / 2.5],
            [b / 4, db / 2.5],
            [a / 4, da / 2.5],
          ];
          const q = [P(a, t, za), P(b, t, zb), P(b, t, db), P(a, t, da)];
          if (side > 0) batch.quad(spandrel, q[1], q[0], q[3], q[2], uv[1], uv[0], uv[3], uv[2]);
          else batch.quad(spandrel, ...q, ...uv);
          // gilt arch-rib edge
          rod(gilt, P(a, t + side * 0.05, za), P(b, t + side * 0.05, zb), 0.12, 4);
        }
        // soffit (facing down)
        batch.quad(
          green,
          P(a, W / 2 - 0.3, za),
          P(b, W / 2 - 0.3, zb),
          P(b, -W / 2 + 0.3, zb),
          P(a, -W / 2 + 0.3, za),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }

    // Granite piers with pointed cutwaters, plus lamp standards above them.
    for (const s of piers) {
      const [x, y] = P(s, 0, 0);
      const h = 1.9;
      kit.box(batch, granite, x, y, 0, PW, W + 1.0, h, ang);
      for (const side of [-1, 1]) {
        const [cx, cy] = P(s, side * (W / 2 + 0.5), 0);
        put(
          granite,
          new THREE.CylinderGeometry((PW / 2) * 1.41, (PW / 2) * 1.41, h, 4).rotateX(Math.PI / 2),
          cx,
          cy,
          h / 2,
          ang + Math.PI / 4,
        );
        // pilaster up to the parapet and a lamp standard
        const [px, py] = P(s, side * (W / 2 + 0.2), 0);
        kit.box(batch, green, px, py, h, 2.2, 0.8, deckZ(s) + 1.3 - h, ang);
        const z = deckZ(s) + 1.3;
        put(
          green,
          new THREE.CylinderGeometry(0.12, 0.18, 4.2, 8).rotateX(Math.PI / 2),
          px,
          py,
          z + 2.1,
        );
        put(gilt, new THREE.SphereGeometry(0.45, 10, 6), px, py, z + 4.5, 0);
      }
      kit.box(batch, granite, x, y, h, PW + 0.4, W + 1.4, 0.35, ang);
    }
    // Abutments on the banks.
    for (const s of [-3, L + 3]) {
      const [x, y] = P(s, 0, 0);
      kit.box(batch, granite, x, y, 0, 6, W + 1.6, Z0 + 0.1, ang);
    }

    g.add(batch.toGroup('battersea_bridge'));
    return g;
  },
};
