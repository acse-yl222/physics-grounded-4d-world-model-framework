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
        'listing: 5 spans of unequal radii rising to a central apex, iron spans springing from stone-faced piers, channelled cutwaters with a stone pilaster rising to road level, stone pedestals between iron balustrades of coupled colonnettes with stilted arches',
    },
    {
      title: "Battersea Bridge - Grace's Guide",
      url: 'https://gracesguide.co.uk/Battersea_Bridge',
      used_for:
        'Moorish-Arabesque cornice and parapet of cast-iron panels, clustered columns and handrails',
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
    'banks. Dark green paint with gilt details is from general knowledge, not confirmed by a returned source. ' +
    'Balustrade arches are a cut-out painted panel plus 3D colonnette pairs; lamp standards on the pier pedestals, ' +
    'rib count (4) and spandrel posts are estimates.',
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
        // Moorish-arabesque cornice band along the fascia
        rod(gilt, P(sa, t + side * 0.06, za + 0.12), P(sb, t + side * 0.06, zb + 0.12), 0.06, 4);
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

    // Stone-faced piers with channelled pointed cutwaters; a stone pilaster rises
    // from each pier to road level and carries a parapet pedestal and lamp standard.
    const channel = kit.paintedMaterial('battersea_bridge:granite', 128, 128, (c, w, h) => {
      c.fillStyle = '#a7a49e';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.42);
      for (let y = 0; y < h; y += 32)
        for (let x = (y / 32) % 2 ? 0 : 32; x < w + 64; x += 64) {
          c.fillStyle = `rgb(${160 + r() * 20},${157 + r() * 20},${150 + r() * 20})`;
          c.fillRect(x - 64 + 2, y + 2, 60, 28);
        }
      c.fillStyle = '#6f6c67';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 3);
    });
    const lampGlass = kit.mat('#fff3d0', {
      emissive: new THREE.Color('#ffe7a8'),
      emissiveIntensity: 0.45,
      roughness: 0.25,
    });
    const pedestals = [];
    for (const s of piers) {
      const [x, y] = P(s, 0, 0);
      const h = 1.9;
      kit.box(batch, channel, x, y, 0, PW, W + 1.0, h, ang);
      for (const side of [-1, 1]) {
        const [cx, cy] = P(s, side * (W / 2 + 0.5), 0);
        put(
          channel,
          new THREE.CylinderGeometry((PW / 2) * 1.41, (PW / 2) * 1.41, h, 4).rotateX(Math.PI / 2),
          cx,
          cy,
          h / 2,
          ang + Math.PI / 4,
        );
        // cutwater cap (pyramidal)
        put(
          granite,
          new THREE.ConeGeometry((PW / 2) * 1.5, 0.9, 4).rotateX(Math.PI / 2),
          cx,
          cy,
          h + 0.45,
          ang + Math.PI / 4,
        );
        // stone pilaster up to road level, with moulded cap
        const [px, py] = P(s, side * (W / 2 + 0.35), 0);
        kit.box(batch, granite, px, py, h, 2.4, 1.0, deckZ(s) - h, ang);
        kit.box(batch, granite, px, py, deckZ(s) - 0.5, 2.8, 1.3, 0.35, ang);
        pedestals.push([s, side]);
      }
      kit.box(batch, granite, x, y, h, PW + 0.4, W + 1.4, 0.35, ang);
    }
    // parapet pedestals over the piers, at the abutments and at mid-span
    for (let k = 0; k < bounds.length - 1; k++)
      for (const side of [-1, 1]) pedestals.push([(bounds[k] + bounds[k + 1]) / 2, side]);
    for (const side of [-1, 1]) pedestals.push([-4, side], [L + 4, side]);
    for (const [s, side] of pedestals) {
      const z = deckZ(s);
      const [px, py] = P(s, side * (W / 2 - 0.1), 0);
      kit.box(batch, granite, px, py, z, 1.5, 0.8, 1.3, ang);
      kit.box(batch, granite, px, py, z + 1.3, 1.7, 0.95, 0.18, ang);
      if (bounds.some((b0) => Math.abs(b0 - s) < 1) || piers.some((p0) => Math.abs(p0 - s) < 1)) {
        // cast-iron lamp standard: fluted shaft, collar, lantern, crown
        const z0 = z + 1.48;
        put(
          green,
          new THREE.CylinderGeometry(0.22, 0.3, 0.7, 8).rotateX(Math.PI / 2),
          px,
          py,
          z0 + 0.35,
        );
        put(
          green,
          new THREE.CylinderGeometry(0.1, 0.15, 3.0, 8).rotateX(Math.PI / 2),
          px,
          py,
          z0 + 2.2,
        );
        put(
          gilt,
          new THREE.CylinderGeometry(0.22, 0.16, 0.2, 8).rotateX(Math.PI / 2),
          px,
          py,
          z0 + 3.8,
        );
        // cross-arm carrying twin lanterns
        kit.box(batch, green, px, py, z0 + 3.95, 1.5, 0.1, 0.1, ang + Math.PI / 2);
        for (const o of [-0.7, 0, 0.7]) {
          const lx = px + Math.cos(ang + Math.PI / 2) * o,
            ly = py + Math.sin(ang + Math.PI / 2) * o;
          const zz = z0 + 4.05 + (o === 0 ? 0.45 : 0);
          put(
            lampGlass,
            new THREE.CylinderGeometry(0.24, 0.17, 0.55, 6).rotateX(Math.PI / 2),
            lx,
            ly,
            zz + 0.28,
          );
          put(green, new THREE.ConeGeometry(0.3, 0.3, 6).rotateX(Math.PI / 2), lx, ly, zz + 0.7);
          put(gilt, new THREE.SphereGeometry(0.07, 6, 4), lx, ly, zz + 0.9, 0);
        }
      }
    }

    // Iron balustrade between the pedestals: coupled colonnettes under stilted arches.
    const arcBal = kit.paintedMaterial(
      'battersea_bridge:balustrade',
      256,
      64,
      (c, w, h) => {
        c.clearRect(0, 0, w, h);
        c.fillStyle = '#2f4a3a';
        c.fillRect(0, 0, w, 7);
        c.fillRect(0, h - 7, w, 7);
        for (let k = 0; k < 8; k++) {
          const x = k * 32;
          c.fillRect(x + 2, 0, 4, h);
          c.fillRect(x + 8, 0, 4, h);
          c.beginPath();
          c.moveTo(x + 12, 20);
          c.arc(x + 22, 20, 10, Math.PI, 0);
          c.lineTo(x + 34, 7);
          c.lineTo(x + 10, 7);
          c.fill();
        }
      },
      {
        transparent: true,
        alphaTest: 0.5,
        side: THREE.DoubleSide,
        roughness: 0.55,
        metalness: 0.2,
      },
    );
    for (const side of [-1, 1]) {
      const t = side * (W / 2 - 0.1);
      const M = 120;
      for (let k = 0; k < M; k++) {
        const sa = s0 + ((s1 - s0) * k) / M,
          sb = s0 + ((s1 - s0) * (k + 1)) / M;
        const za = deckZ(sa) + 0.15,
          zb = deckZ(sb) + 0.15;
        const u0 = sa / 1.6,
          u1 = sb / 1.6;
        batch.quad(
          arcBal,
          P(sa, t, za),
          P(sb, t, zb),
          P(sb, t, zb + 1.0),
          P(sa, t, za + 1.0),
          [u0, 0],
          [u1, 0],
          [u1, 1],
          [sa / 1.6, 1],
        );
      }
      // handrail
      for (let k = 0; k < M; k += 2) {
        const sa = s0 + ((s1 - s0) * k) / M,
          sb = s0 + ((s1 - s0) * (k + 2)) / M;
        rod(green, P(sa, t, deckZ(sa) + 1.22), P(sb, t, deckZ(sb) + 1.22), 0.07, 4);
      }
      // 3D colonnette pairs every 1.6 m (reads at street level)
      for (let s = s0 + 0.8; s < s1; s += 1.6) {
        const z = deckZ(s);
        for (const o of [-0.08, 0.08])
          rod(green, P(s + o, t, z + 0.15), P(s + o, t, z + 1.15), 0.03, 4);
      }
    }

    // Arch ribs across the width (seen from the river) with cross-bracing.
    for (let k = 0; k < bounds.length - 1; k++) {
      const sa = bounds[k] + (k === 0 ? 0 : PW / 2),
        sb = bounds[k + 1] - (k === bounds.length - 2 ? 0 : PW / 2);
      const mid = (sa + sb) / 2,
        half = (sb - sa) / 2;
      const crown = deckZ(mid) - 0.9;
      const arch = (s) => 0.35 + (crown - 0.35) * (1 - ((s - mid) / half) ** 2);
      const M = 12;
      for (const t of [-3.9, -1.3, 1.3, 3.9])
        for (let j = 0; j < M; j++) {
          const a = sa + ((sb - sa) * j) / M,
            b = sa + ((sb - sa) * (j + 1)) / M;
          rod(green, P(a, t, arch(a) - 0.05), P(b, t, arch(b) - 0.05), 0.22, 4);
        }
      for (let j = 1; j < M; j++) {
        const s = sa + ((sb - sa) * j) / M;
        const [x, y] = P(s, 0, 0);
        kit.box(batch, green, x, y, arch(s) - 0.2, 0.2, W - 1, 0.25, ang);
        // spandrel posts up to the deck
        for (const t of [-3.9, 3.9]) {
          const [qx, qy] = P(s, t, 0);
          kit.box(batch, green, qx, qy, arch(s), 0.18, 0.18, deckZ(s) - 0.6 - arch(s), ang);
        }
      }
    }
    // Deck cross-girders.
    for (let s = s0 + 1; s < s1; s += 3) {
      const [x, y] = P(s, 0, 0);
      kit.box(batch, green, x, y, deckZ(s) - 0.6, 0.3, W - 0.4, 0.55, ang);
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
