// White City station (Central line), opened 23 November 1947; designed by
// A. D. McGill and Keith Seymour under London Transport chief architect Thomas
// Bilbow; Festival of Britain architecture award 1951 (Abram Games plaque left of
// the entrance). A Holden-style brick ticket hall with large glass windows and a
// coloured roundel: tall steel-framed glazed screens to Wood Lane under a thin
// projecting concrete canopy, a raised clerestory over the booking hall, then a
// long low brick range beside the surface platforms with their canopies.
export default {
  id: 'white_city_station',
  name: 'White City station',
  claims: [
    '94e1a43b-8a3e-4bac-a268-f372c89310ae', // station building
    'cb7942c6-3c67-49dc-bfeb-208dda30c112', // platform canopies
  ],
  references: [
    {
      title: 'White City tube station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/White_City_tube_station',
      used_for: 'opening 1947, replaced Wood Lane, plaque beside the entrance',
    },
    {
      title: 'White City Station - Modernism in Metro-Land',
      url: 'https://www.modernism-in-metroland.co.uk/white-city.html',
      used_for:
        'architects McGill and Seymour under Bilbow; Holden-style brick ticket hall with large glass windows and a coloured roundel; Festival of Britain award 1951, Abram Games plaque left of the entrance',
    },
    {
      title: 'White City Underground Station - Structurae',
      url: 'https://structurae.net/en/structures/white-city-underground-station',
      used_for: 'structure type / dates',
    },
  ],
  notes:
    'Ticket hall / platform range split of the footprint at y = 602 m is inferred from the outline. Brick colour, the steel window grid, clerestory, canopy depth and the platform layout (two island platforms between three tracks under butterfly canopies, at grade) are reconstructed from period descriptions without photographs. Tracks are drawn only inside the canopy footprint.',
  build({ THREE, kit, byId, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const st = byId['94e1a43b-8a3e-4bac-a268-f372c89310ae'];
    const cn = byId['cb7942c6-3c67-49dc-bfeb-208dda30c112'];
    const ring = st.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const clip = (r, f) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length],
          fa = f(a),
          fb = f(b);
        if (fa >= 0) out.push(a);
        if (fa >= 0 !== fb >= 0) {
          const t = fa / (fa - fb);
          out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
        }
      }
      return out;
    };
    const Y = 602.3;
    const hall = ccw(clip(ring, (p) => p[1] - Y));
    const range = ccw(clip(ring, (p) => Y - p[1]));

    // ---------- materials ----------
    const brick = kit.paintedMaterial(
      'white_city_stn:brick2',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#b8aa94';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.47);
        for (let row = 0; row < 32; row++)
          for (let k = (row % 2) * -8; k < w; k += 16) {
            const t = 0.82 + r() * 0.3;
            x.fillStyle = `rgb(${Math.round(150 * t)},${Math.round(100 * t)},${Math.round(72 * t)})`;
            x.fillRect(k + 1, row * 8 + 1, 14, 6);
          }
      },
      DS,
    );
    const concrete = kit.mat('#ddd8cc', DS);
    const roofM = kit.roof('flat', 1);
    const glass = kit.mat('#2f3e48', { roughness: 0.12, metalness: 0.3 });
    const warmGlass = kit.mat('#6e7766', { roughness: 0.15, metalness: 0.2, emissive: '#3a3420' });
    const frame = kit.mat('#e8e4d8', { roughness: 0.6 });
    const steelDk = kit.mat('#2e4038', { roughness: 0.5, metalness: 0.3 });
    const dark = kit.mat('dark_steel', DS);
    const plat = kit.mat('#b7b1a5', DS);
    const ballast = kit.mat('#6e675e', { roughness: 1, side: THREE.DoubleSide });
    const rail = kit.mat('steel');
    const yellow = kit.mat('#e2c02c', DS);
    const canopyM = kit.mat('#d5d3cc', DS);
    const soffit = kit.mat('#f1eee6', { emissive: '#3a3a36', side: THREE.DoubleSide });

    const wallQ = (m, a, b, z0, z1, su = 4, sv = 4) => {
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      batch.quad(
        m,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [0, z0 / sv],
        [len / su, z0 / sv],
        [len / su, z1 / sv],
        [0, z1 / sv],
      );
    };
    const edgesOf = (r) =>
      r
        .map((a, k) => {
          const b = r[(k + 1) % r.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          return {
            a,
            b,
            len,
            nx: len ? (b[1] - a[1]) / len : 0,
            ny: len ? -(b[0] - a[0]) / len : 0,
          };
        })
        .filter((e) => e.len > 0.05);
    const roundelMat = kit.paintedMaterial(
      'white_city_stn:roundel',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#ffffff';
        x.fillRect(0, 0, w, h);
        x.strokeStyle = '#dc241f';
        x.lineWidth = 40;
        x.beginPath();
        x.arc(w / 2, h / 2, 90, 0, Math.PI * 2);
        x.stroke();
        x.fillStyle = '#0019a8';
        x.fillRect(10, h / 2 - 26, w - 20, 52);
        x.fillStyle = '#ffffff';
        x.font = 'bold 34px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText('WHITE CITY', w / 2, h / 2 + 2);
      },
      DS,
    );
    const roundel = (x, y, z, f, d, twoSided = false) => {
      const geo = new THREE.CylinderGeometry(d / 2, d / 2, 0.04, 28).rotateY(Math.PI / 2);
      for (const k of twoSided ? [0, 1] : [0]) {
        const a = f + k * Math.PI;
        const m = new THREE.Matrix4().makeRotationZ(a);
        const o = twoSided ? 0.025 : 0;
        m.setPosition(x + Math.sin(a) * o, y - Math.cos(a) * o, z + d / 2);
        batch.addGeometry(roundelMat, geo, m);
      }
      geo.dispose();
    };

    // ---------- ticket hall ----------
    const Hh = 5.6;
    const hallEdges = edgesOf(hall);
    let mainScreen = null;
    for (const e of hallEdges) {
      const onSplit = Math.abs(e.a[1] - Y) < 0.05 && Math.abs(e.b[1] - Y) < 0.05;
      if (onSplit) continue;
      const screen = e.nx < -0.6 && e.len > 6;
      wallQ(concrete, e.a, e.b, 0, 0.45);
      if (screen) {
        if (!mainScreen || e.len > mainScreen.len) mainScreen = e;
        // Brick piers at the ends, full-height steel-framed glazing between.
        wallQ(brick, e.a, e.b, Hh - 0.5, Hh);
        wallQ(glass, e.a, e.b, 0.45, Hh - 0.5);
        const f = Math.atan2(e.b[1] - e.a[1], e.b[0] - e.a[0]);
        const n = Math.max(2, Math.round(e.len / 1.6));
        for (let i = 0; i <= n; i++) {
          const t = (e.len * i) / n;
          const big = i === 0 || i === n || i % 4 === 0;
          const p = [
            e.a[0] + Math.cos(f) * t + e.nx * 0.08,
            e.a[1] + Math.sin(f) * t + e.ny * 0.08,
          ];
          kit.box(
            batch,
            big ? brick : steelDk,
            p[0],
            p[1],
            0.45,
            big ? 0.6 : 0.08,
            big ? 0.35 : 0.12,
            Hh - 0.95,
            f,
          );
        }
        const mid = [(e.a[0] + e.b[0]) / 2 + e.nx * 0.08, (e.a[1] + e.b[1]) / 2 + e.ny * 0.08];
        for (const z of [0.45, 2.75, 3.65, 4.4, Hh - 0.55])
          kit.box(batch, steelDk, mid[0], mid[1], z, e.len, 0.12, 0.08, f);
        // Glazed doors at the foot of the screen.
        kit.windowRow(batch, e.a, e.b, 0.45, {
          glass: warmGlass,
          frame: steelDk,
          sill: steelDk,
          count: Math.max(1, Math.round(e.len / 6)),
          width: 2.2,
          height: 2.3,
          margin: 1.5,
          head: 'none',
          bars: 1,
          depth: 0.2,
        });
        continue;
      }
      wallQ(brick, e.a, e.b, 0.45, Hh);
      // Brick flanks: a band of tall steel windows high up.
      if (e.len > 3.5)
        kit.windowRow(batch, e.a, e.b, 2.4, {
          glass,
          frame,
          sill: concrete,
          bay: 2.6,
          width: 1.7,
          height: 2.3,
          margin: 0.8,
          head: 'none',
          bars: 2,
        });
    }
    // Thin projecting concrete roof slab / canopy and fascia band.
    const slab = kit.offsetRing(hall, 1.6);
    kit.cap(batch, roofM, [[slab]], Hh + 0.45, { scale: 4 });
    kit.cap(batch, soffit, [[slab]], Hh, { down: true });
    kit.walls(batch, concrete, [[slab]], Hh, Hh + 0.45, { bay: 1e6 });
    // Raised clerestory over the booking hall.
    const hf = kit.ringFrame(hall);
    const hc = Math.cos(hf.angle),
      hs = Math.sin(hf.angle);
    const hl = hf.length * 0.28,
      hw2 = hf.width * 0.26;
    const cl = ccw(
      [
        [-hl, -hw2],
        [hl, -hw2],
        [hl, hw2],
        [-hl, hw2],
      ].map(([u, v]) => [hf.cx + u * hc - v * hs, hf.cy + u * hs + v * hc]),
    );
    const CZ = Hh + 0.45,
      CT = 8.0;
    for (const e of edgesOf(cl)) {
      wallQ(concrete, e.a, e.b, CZ, CZ + 0.3);
      wallQ(glass, e.a, e.b, CZ + 0.3, CT - 0.35);
      wallQ(concrete, e.a, e.b, CT - 0.35, CT);
      kit.windowRow(batch, e.a, e.b, CZ + 0.3, {
        glass,
        frame,
        sill: concrete,
        bay: 1.2,
        width: 1.1,
        height: CT - CZ - 0.65,
        margin: 0.1,
        head: 'none',
        bars: 1,
        depth: 0.08,
      });
    }
    const cl2 = kit.offsetRing(cl, 0.6);
    kit.cap(batch, roofM, [[cl2]], CT + 0.35, { scale: 4 });
    kit.cap(batch, concrete, [[cl2]], CT, { down: true });
    kit.walls(batch, concrete, [[cl2]], CT, CT + 0.35, { bay: 1e6 });

    // Name band on the canopy fascia facing Wood Lane, coloured roundel in the
    // glazed screen and the Festival of Britain plaque left of the entrance.
    const name = kit.paintedMaterial(
      'white_city_stn:name',
      512,
      64,
      (x, w, h) => {
        x.fillStyle = '#f4f1e8';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#0019a8';
        x.font = 'bold 34px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText('WHITE  CITY  STATION', w / 2, h / 2 + 2);
        for (const cx of [40, w - 40]) {
          x.strokeStyle = '#dc241f';
          x.lineWidth = 9;
          x.beginPath();
          x.arc(cx, h / 2, 20, 0, Math.PI * 2);
          x.stroke();
          x.fillStyle = '#0019a8';
          x.fillRect(cx - 30, h / 2 - 5, 60, 10);
        }
      },
      DS,
    );
    if (mainScreen) {
      const e = mainScreen;
      const f = Math.atan2(e.b[1] - e.a[1], e.b[0] - e.a[0]);
      const ox = e.nx * 1.63,
        oy = e.ny * 1.63;
      const m0 = 0.12 * e.len,
        m1 = 0.88 * e.len;
      const A = [e.a[0] + Math.cos(f) * m0 + ox, e.a[1] + Math.sin(f) * m0 + oy],
        B = [e.a[0] + Math.cos(f) * m1 + ox, e.a[1] + Math.sin(f) * m1 + oy];
      batch.quad(
        name,
        [A[0], A[1], Hh + 0.02],
        [B[0], B[1], Hh + 0.02],
        [B[0], B[1], Hh + 0.43],
        [A[0], A[1], Hh + 0.43],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const rp = [(e.a[0] + e.b[0]) / 2 + e.nx * 0.2, (e.a[1] + e.b[1]) / 2 + e.ny * 0.2];
      roundel(rp[0], rp[1], 2.9, f, 2.2);
      // Abram Games plaque: small enamel panel on the pier left of the doors.
      const pp = [e.a[0] + Math.cos(f) * 0.3 + e.nx * 0.2, e.a[1] + Math.sin(f) * 0.3 + e.ny * 0.2];
      const plaque = kit.paintedMaterial(
        'white_city_stn:plaque',
        128,
        128,
        (x, w, h) => {
          x.fillStyle = '#f2ede0';
          x.fillRect(0, 0, w, h);
          x.fillStyle = '#c0392b';
          x.beginPath();
          x.moveTo(w / 2, 14);
          x.lineTo(w - 18, h / 2);
          x.lineTo(w / 2, h - 14);
          x.lineTo(18, h / 2);
          x.fill();
          x.fillStyle = '#1f3a7a';
          x.fillRect(30, h / 2 - 6, w - 60, 12);
        },
        DS,
      );
      kit.box(batch, plaque, pp[0], pp[1], 1.6, 0.6, 0.05, 0.6, f);
      // Forecourt: bollards and cycle stands on the Wood Lane pavement.
      const bol = [];
      for (let t = 1; t < e.len; t += 2.2)
        bol.push([e.a[0] + Math.cos(f) * t + e.nx * 3.2, e.a[1] + Math.sin(f) * t + e.ny * 3.2, f]);
      g.add(placeAssets('bollard', bol));
    }

    // ---------- low platform range ----------
    const RH = 3.9;
    for (const e of edgesOf(range)) {
      if (Math.abs(e.a[1] - Y) < 0.05 && Math.abs(e.b[1] - Y) < 0.05) continue;
      wallQ(concrete, e.a, e.b, 0, 0.4);
      wallQ(brick, e.a, e.b, 0.4, RH);
      if (e.len > 4) {
        const toRoad = e.nx < -0.6;
        kit.windowRow(batch, e.a, e.b, 1.3, {
          glass,
          frame,
          sill: concrete,
          bay: toRoad ? 3.6 : 4.8,
          width: 1.8,
          height: 1.6,
          margin: 1.2,
          head: 'none',
          bars: 2,
        });
        if (!toRoad && e.len > 20)
          kit.windowRow(batch, e.a, e.b, 0.4, {
            glass: warmGlass,
            frame: steelDk,
            sill: steelDk,
            bay: 14,
            width: 1.6,
            height: 2.4,
            margin: 6,
            head: 'none',
            bars: 1,
          });
      }
    }
    const rslab = kit.offsetRing(range, 0.5);
    kit.cap(batch, roofM, [[rslab]], RH + 0.3, { scale: 4 });
    kit.walls(batch, concrete, [[rslab]], RH, RH + 0.3, { bay: 1e6 });
    // Rooftop vents.
    {
      const fr = kit.ringFrame(range);
      for (const off of [-0.3, 0, 0.3]) {
        const x = fr.cx + Math.cos(fr.angle) * fr.length * off,
          y = fr.cy + Math.sin(fr.angle) * fr.length * off;
        kit.box(batch, dark, x, y, RH + 0.3, 1.2, 1.2, 0.9, fr.angle);
      }
    }

    // ---------- platforms, tracks and canopies (footprint cb7942) ----------
    const pr = cn.polys[0][0];
    const fr = kit.ringFrame(pr);
    const e = kit.orientedExtent(pr, fr.angle);
    const Pt = (u, v, z) => e.at(u, v, z);
    const W = e.v1 - e.v0;
    const u0 = e.u0 + 1,
      u1 = e.u1 - 1;
    const LU = u1 - u0;
    // Track bed over the whole footprint.
    {
      const pc = Pt((e.u0 + e.u1) / 2, (e.v0 + e.v1) / 2, 0);
      kit.box(batch, ballast, pc[0], pc[1], 0, e.u1 - e.u0, W, 0.12, fr.angle);
    }
    // T I T I T layout across the width.
    const tw = W * 0.15,
      iw = W * 0.275;
    const islands = [e.v0 + tw + iw / 2, e.v0 + 2 * tw + 1.5 * iw];
    const tracks = [e.v0 + tw / 2, e.v0 + 1.5 * tw + iw, e.v0 + 2.5 * tw + 2 * iw];
    for (const tv of tracks)
      for (const off of [-0.72, 0.72]) {
        const pc = Pt((e.u0 + e.u1) / 2, tv + off, 0);
        kit.box(batch, rail, pc[0], pc[1], 0.12, e.u1 - e.u0, 0.08, 0.16, fr.angle);
      }
    // Sleepers.
    for (const tv of tracks)
      for (let u = e.u0 + 0.5; u < e.u1; u += 1.8) {
        const pc = Pt(u, tv, 0);
        kit.box(batch, kit.mat('#5a4c3e'), pc[0], pc[1], 0.1, 0.25, 2.5, 0.06, fr.angle);
      }
    const benchPts = [];
    for (const vc of islands) {
      const pc = Pt((u0 + u1) / 2, vc, 0);
      kit.box(batch, plat, pc[0], pc[1], 0, LU, iw, 1.0, fr.angle);
      for (const sg of [-1, 1]) {
        const ep = Pt((u0 + u1) / 2, vc + sg * (iw / 2 - 0.45), 0);
        kit.box(batch, yellow, ep[0], ep[1], 1.0, LU, 0.15, 0.01, fr.angle);
        // Coping edge.
        const cp = Pt((u0 + u1) / 2, vc + sg * (iw / 2 - 0.1), 0);
        kit.box(batch, concrete, cp[0], cp[1], 0.95, LU, 0.3, 0.07, fr.angle);
      }
      // Butterfly canopy: low in the middle, raised edges, on a central row of columns.
      const half = iw / 2 + 0.3;
      const cu0 = u0 + 3,
        cu1 = u1 - 3;
      for (const sgn of [-1, 1]) {
        batch.quad(
          canopyM,
          Pt(cu0, vc, 4.0),
          Pt(cu1, vc, 4.0),
          Pt(cu1, vc + sgn * half, 4.7),
          Pt(cu0, vc + sgn * half, 4.7),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.quad(
          soffit,
          Pt(cu0, vc, 3.85),
          Pt(cu1, vc, 3.85),
          Pt(cu1, vc + sgn * half, 4.55),
          Pt(cu0, vc + sgn * half, 4.55),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        const fp = Pt((cu0 + cu1) / 2, vc + sgn * half, 0);
        kit.box(batch, concrete, fp[0], fp[1], 4.45, cu1 - cu0, 0.15, 0.45, fr.angle);
      }
      // Central gutter beam, columns with raking brackets.
      const gp = Pt((cu0 + cu1) / 2, vc, 0);
      kit.box(batch, dark, gp[0], gp[1], 3.6, cu1 - cu0, 0.35, 0.3, fr.angle);
      for (let u = cu0 + 2; u < cu1; u += 7.5) {
        const p = Pt(u, vc, 0);
        kit.box(batch, dark, p[0], p[1], 1.0, 0.3, 0.3, 2.7, fr.angle);
        kit.box(batch, dark, p[0], p[1], 3.3, 0.25, iw * 0.7, 0.18, fr.angle);
        // Platform name boards hung under the canopy.
        if (Math.round((u - cu0) / 7.5) % 3 === 1) {
          const q = Pt(u + 3.7, vc, 0);
          roundel(q[0], q[1], 2.3, fr.angle, 1.1, true);
        } else benchPts.push(Pt(u + 3.7, vc + 1.2, 0), Pt(u + 3.7, vc - 1.2, 0));
      }
      // Lamps along the uncovered platform ends.
      for (const uu of [u0 + 1.5, u1 - 1.5]) {
        const p = Pt(uu, vc, 0);
        kit.box(batch, dark, p[0], p[1], 1.0, 0.15, 0.15, 3.5, fr.angle);
        kit.box(
          batch,
          kit.mat('#fff3d0', { emissive: '#8a7a50' }),
          p[0],
          p[1],
          4.4,
          0.4,
          0.4,
          0.35,
          fr.angle,
        );
      }
    }
    if (benchPts.length) {
      const z1 = benchPts.map((p) => [p[0], p[1], fr.angle]);
      g.add(placeAssets('bench', z1, { z: 1.0 }));
    }

    g.add(batch.toGroup('white_city_station'));
    return g;
  },
};
