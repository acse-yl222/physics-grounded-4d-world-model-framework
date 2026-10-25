// Loftus Road, Shepherd's Bush: home of Queens Park Rangers since 1917.
// A tight four-sided enclosed ground: South Africa Road Stand (north, 1968, two
// tiers with a row of executive boxes between), Ellerslie Road / Stanley Bowles
// Stand (south, 1972, single tier, lowest), Loftus Road Stand (east) and School
// End (west), both two tightly packed overhung tiers. All four roofs meet at the
// corners so the pitch is fully enclosed. Blue seats, blue/white cladding.
export default {
  id: 'loftus_road',
  name: 'Loftus Road Stadium',
  claims: [
    'eed8691a-a296-4fb6-ab31-e8ff31a76854', // South Africa Road Stand
    '10295b67-3690-414e-9c19-383852d30d01', // The Stanley Bowles (Ellerslie Road) Stand
    '6168b63b-8605-4e7c-aa86-c4b35bc061c3', // Loftus Road Stand
    'e4054561-c075-4796-9657-3f81cb797bba', // School End
  ],
  references: [
    {
      title: 'Loftus Road - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Loftus_Road',
      used_for: 'stand names and dates (South Africa Road 1968, Ellerslie Road 1972)',
    },
    {
      title: 'Queens Park Rangers stadium - Premier League',
      url: 'https://www.premierleague.com/clubs/17/Queens-Park-Rangers/stadium',
      used_for: 'all four stands roughly the same height, roofs meet at all four corners',
    },
    {
      title: 'Loftus Road - StadiumGuide',
      url: 'https://stadiumguide.com/?p=1343',
      used_for:
        'two overhung tiers at School End and Loftus Road end, executive boxes between South Africa Road tiers, Ellerslie Road single tier',
    },
  ],
  notes:
    'Stands modelled as oriented rectangles fitted to the Overture footprints. Heights raised from the OSM values (6-11 m) to 12-15 m so the roofs meet as described; exact tier rake, floodlight and column positions are approximate. Pitch drawn between the stands (no footprint).',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const ids = this.claims;
    const N = byId[ids[0]],
      S = byId[ids[1]],
      E = byId[ids[2]],
      W = byId[ids[3]];
    // Stadium axis from the long South Africa Road Stand.
    const fr = kit.ringFrame(N.polys[0][0]);
    const a = fr.angle;
    const c = Math.cos(a),
      s = Math.sin(a);
    const toL = ([x, y]) => [x * c + y * s, -x * s + y * c];
    const ext = (b) => {
      let u0 = 1e9,
        u1 = -1e9,
        v0 = 1e9,
        v1 = -1e9;
      for (const p of b.polys[0][0]) {
        const [u, v] = toL(p);
        u0 = Math.min(u0, u);
        u1 = Math.max(u1, u);
        v0 = Math.min(v0, v);
        v1 = Math.max(v1, v);
      }
      return { u0, u1, v0, v1 };
    };
    const en = ext(N),
      es = ext(S),
      ee = ext(E),
      ew = ext(W);
    // Pitch side: N stand faces -v, S +v, E -u, W +u. Ensure N is at larger v.
    const flip = en.v0 < es.v0 ? -1 : 1; // if stand N lies at smaller v, flip v axis
    const P = (u, v, z) => [u * c - v * flip * s, u * s + v * flip * c, z];
    const fix = (e) => (flip === 1 ? e : { u0: e.u0, u1: e.u1, v0: -e.v1, v1: -e.v0 });
    const eN = fix(en),
      eS = fix(es);
    let eE = fix(ee),
      eW = fix(ew);
    if (eE.u0 < eW.u0) [eE, eW] = [eW, eE];
    // Inner pitch box.
    const pu0 = eW.u1,
      pu1 = eE.u0,
      pv0 = eS.v1,
      pv1 = eN.v0;
    const outer = { u0: eW.u0, u1: eE.u1, v0: eS.v0, v1: eN.v1 };

    const seat = kit.paintedMaterial(
      'loftus_road:seats',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#1f4fa8';
        x.fillRect(0, 0, w, h);
        for (let r = 0; r < 16; r++) {
          x.fillStyle = '#163a7c';
          x.fillRect(0, r * 16 + 11, w, 5);
        }
        x.fillStyle = '#9aa3ad';
        x.fillRect(w / 2 - 5, 0, 10, h); // gangway
      },
      { roughness: 0.8, side: THREE.DoubleSide },
    );
    const seatWhite = kit.paintedMaterial(
      'loftus_road:seats_w',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#e8ecf0';
        x.fillRect(0, 0, w, h);
        for (let r = 0; r < 16; r++) {
          x.fillStyle = '#c0c6cc';
          x.fillRect(0, r * 16 + 11, w, 5);
        }
      },
      { roughness: 0.8, side: THREE.DoubleSide },
    );
    const clad = kit.paintedMaterial(
      'loftus_road:clad',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#e9ecef';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#1d4a9c';
        x.fillRect(0, h * 0.55, w, h * 0.45);
        x.fillStyle = 'rgba(0,0,0,0.08)';
        for (let k = 0; k < w; k += 8) x.fillRect(k, 0, 2, h);
        x.fillStyle = '#2b3036';
        for (let k = 16; k < w; k += 64) x.fillRect(k, h * 0.62, 30, h * 0.2);
      },
      DS,
    );
    // Long back elevations with club lettering (one texture across the stand).
    const backFacade = (key, text, brick) =>
      kit.paintedMaterial(
        'loftus_road:' + key,
        1024,
        128,
        (x, w, h) => {
          x.fillStyle = '#e9ecef';
          x.fillRect(0, 0, w, h);
          x.fillStyle = 'rgba(0,0,0,0.07)';
          for (let k = 0; k < w; k += 4) x.fillRect(k, 0, 1, h);
          x.fillStyle = brick ? '#8e4a36' : '#1d4a9c';
          x.fillRect(0, h * 0.62, w, h * 0.38);
          if (brick) {
            x.fillStyle = 'rgba(255,255,255,0.12)';
            for (let r = h * 0.62; r < h; r += 3) x.fillRect(0, r, w, 1);
          }
          x.fillStyle = '#1d4a9c';
          x.fillRect(0, h * 0.04, w, h * 0.05);
          // Turnstile doors and steel columns.
          for (let k = 20; k < w; k += 60) {
            x.fillStyle = '#2a3138';
            x.fillRect(k, h * 0.72, 22, h * 0.28);
            x.fillStyle = '#6f7880';
            x.fillRect(k - 18, h * 0.1, 3, h * 0.52);
          }
          x.fillStyle = '#1d4a9c';
          x.font = `bold ${Math.round(h * 0.22)}px sans-serif`;
          x.textAlign = 'center';
          x.textBaseline = 'middle';
          x.fillText(text, w / 2, h * 0.35);
          // Hooped crest blocks either side of the lettering.
          for (const cx of [w * 0.12, w * 0.88]) {
            x.fillStyle = '#ffffff';
            x.fillRect(cx - 18, h * 0.16, 36, 40);
            x.fillStyle = '#1d4a9c';
            for (let k = 0; k < 5; k++) x.fillRect(cx - 18, h * 0.16 + k * 8, 36, 4);
          }
        },
        DS,
      );
    const roofM = kit.mat('#c9cdd1', { roughness: 0.6, metalness: 0.3, side: THREE.DoubleSide });
    const roofUnder = kit.mat('#7d858c', { roughness: 0.7, side: THREE.DoubleSide });
    const fascia = kit.mat('white_steel', DS);
    const glass = kit.mat('dark_glass', DS);
    const steel = kit.mat('dark_steel', DS);
    const grassA = kit.mat('#5f9a45', { roughness: 1, side: THREE.DoubleSide });
    const grassB = kit.mat('#6ead52', { roughness: 1, side: THREE.DoubleSide });
    const concrete = kit.mat('concrete', DS);

    const quad = (m, a1, b1, c1, d1, uvs) =>
      batch.quad(
        m,
        a1,
        b1,
        c1,
        d1,
        ...(uvs ?? [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ]),
      );
    // Generic local box (u, v ranges).
    const lbox = (m, u0, u1, v0, v1, z0, z1) => {
      const p = [P(u0, v0, 0), P(u1, v0, 0), P(u1, v1, 0), P(u0, v1, 0)];
      for (let k = 0; k < 4; k++) {
        const A = p[k],
          B = p[(k + 1) % 4];
        quad(m, [A[0], A[1], z0], [B[0], B[1], z0], [B[0], B[1], z1], [A[0], A[1], z1]);
      }
      quad(
        m,
        [p[0][0], p[0][1], z1],
        [p[1][0], p[1][1], z1],
        [p[2][0], p[2][1], z1],
        [p[3][0], p[3][1], z1],
      );
    };

    // A stand defined in its own axis: t along the stand (t0..t1), d depth from
    // pitch edge (0) to back (D); map(t, d) -> local (u, v).
    const stand = (map, t0, t1, D, H, tiers, seatM, backM) => {
      const L = t1 - t0;
      const Q = (t, d, z) => {
        const [u, v] = map(t, d);
        return P(u, v, z);
      };
      const rect = (m, ta, tb, da, za, db, zb, uv) =>
        quad(m, Q(ta, da, za), Q(tb, da, za), Q(tb, db, zb), Q(ta, db, zb), uv);
      const uvS = (len, dep) => [
        [0, 0],
        [len / 6, 0],
        [len / 6, dep / 4],
        [0, dep / 4],
      ];
      // Pitch-side wall (low front wall) and back facade.
      rect(concrete, t0, t1, 0, 0, 0, 1.2);
      const back = D - 0.2;
      const uvB = [
        [0, 0],
        [L / 16, 0],
        [L / 16, 1],
        [0, 1],
      ];
      if (backM)
        quad(backM, Q(t1, D, 0), Q(t0, D, 0), Q(t0, D, H), Q(t1, D, H), [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ]);
      else quad(clad, Q(t1, D, 0), Q(t0, D, 0), Q(t0, D, H), Q(t1, D, H), uvB);
      // Ends.
      for (const t of [t0, t1]) {
        const A = Q(t, 0, 0),
          B = Q(t, D, 0);
        quad(
          clad,
          [A[0], A[1], 0],
          [B[0], B[1], 0],
          [B[0], B[1], H],
          [A[0], A[1], H],
          [
            [0, 0],
            [D / 16, 0],
            [D / 16, 1],
            [0, 1],
          ],
        );
      }
      if (tiers === 1) {
        const rd = back * 0.95;
        rect(seatM, t0, t1, 0.3, 1.2, rd, H * 0.62, uvS(L, Math.hypot(rd, H * 0.6)));
        rect(concrete, t0, t1, rd, H * 0.62, back, H * 0.62);
        rect(glass, t0, t1, back, H * 0.62, back, H - 0.6);
      } else {
        const d1 = back * 0.45,
          z1 = H * 0.34;
        rect(seatM, t0, t1, 0.3, 1.2, d1, z1, uvS(L, Math.hypot(d1, z1)));
        // Executive boxes band (glass), overhung upper tier above.
        const d2 = d1 - 2.5;
        rect(glass, t0, t1, d1, z1, d1, z1 + 2.6);
        rect(concrete, t0, t1, d1, z1 + 2.6, d2, z1 + 2.6);
        rect(fascia, t0, t1, d2, z1 + 2.6, d2, z1 + 3.6);
        rect(seatM, t0, t1, d2, z1 + 3.6, back, H - 1.5, uvS(L, Math.hypot(back - d2, H - z1 - 5)));
      }
      // Underside of the roof and roof slab, cantilevered ~1.5 m past the front.
      const zr = H,
        zf = H - 1.6,
        df = -1.5;
      rect(roofUnder, t1, t0, df, zf, D, zr);
      rect(roofM, t0, t1, df, zf + 0.5, D, zr + 0.5, [
        [0, 0],
        [L / 8, 0],
        [L / 8, 2],
        [0, 2],
      ]);
      rect(fascia, t0, t1, df, zf, df, zf + 0.5);
      // Corrugation ribs on the roof.
      for (let t = t0 + 3; t < t1; t += 6) {
        const A = Q(t, df, zf + 0.5),
          B = Q(t, D, zr + 0.5);
        const A2 = Q(t + 0.4, df, zf + 0.5),
          B2 = Q(t + 0.4, D, zr + 0.5);
        quad(
          steel,
          [A[0], A[1], A[2] + 0.12],
          [A2[0], A2[1], A2[2] + 0.12],
          [B2[0], B2[1], B2[2] + 0.12],
          [B[0], B[1], B[2] + 0.12],
        );
      }
      // Floodlight gantry along the roof front.
      for (let t = t0 + 6; t < t1 - 3; t += 12) {
        const [u, v] = map(t, df + 0.6);
        const pp = P(u, v, 0);
        kit.box(batch, steel, pp[0], pp[1], zf - 0.9, 2.4, 0.6, 0.7, a);
      }
    };

    const H = { N: 15, S: 12.5, E: 14, W: 14 };
    // North: South Africa Road (pitch edge at v = pv1, back at outer.v1). t = u.
    stand(
      (t, d) => [t, pv1 + d],
      outer.u0,
      outer.u1,
      outer.v1 - pv1,
      H.N,
      2,
      seat,
      backFacade('sar', 'SOUTH AFRICA ROAD STAND', false),
    );
    // South: Ellerslie Road (single tier, lowest).
    stand(
      (t, d) => [-t, pv0 - d],
      -outer.u1,
      -outer.u0,
      pv0 - outer.v0,
      H.S,
      1,
      seat,
      backFacade('ell', 'QUEENS PARK RANGERS  -  LOFTUS ROAD STADIUM', true),
    );
    // East: Loftus Road end; t runs along -v.
    stand((t, d) => [pu1 + d, -t], -pv1, -pv0, outer.u1 - pu1, H.E, 2, seat);
    // West: School End (away end, white seats block).
    stand((t, d) => [pu0 - d, t], pv0, pv1, pu0 - outer.u0, H.W, 2, seatWhite);
    // Corner infill (roofs meet at the corners).
    for (const [u0, u1] of [
      [outer.u0, pu0],
      [pu1, outer.u1],
    ])
      for (const [v0, v1] of [
        [outer.v0, pv0],
        [pv1, outer.v1],
      ]) {
        lbox(clad, u0, u1, v0, v1, 0, 11);
        lbox(roofM, u0, u1, v0, v1, 11, 14.5);
      }

    // Pitch with mowing stripes and markings.
    const n = 12;
    for (let k = 0; k < n; k++) {
      const u0 = pu0 + ((pu1 - pu0) * k) / n,
        u1 = pu0 + ((pu1 - pu0) * (k + 1)) / n;
      quad(
        k % 2 ? grassA : grassB,
        P(u0, pv0, 0.35),
        P(u1, pv0, 0.35),
        P(u1, pv1, 0.35),
        P(u0, pv1, 0.35),
      );
    }
    const lineM = kit.mat('white', DS);
    const m = 3.5,
      lu0 = pu0 + m,
      lu1 = pu1 - m,
      lv0 = pv0 + m,
      lv1 = pv1 - m,
      w = 0.15;
    const line = (u0, v0, u1, v1) => {
      const du = u1 - u0,
        dv = v1 - v0,
        l = Math.hypot(du, dv),
        nu = (-dv / l) * w,
        nv = (du / l) * w;
      quad(
        lineM,
        P(u0 - nu, v0 - nv, 0.4),
        P(u1 - nu, v1 - nv, 0.4),
        P(u1 + nu, v1 + nv, 0.4),
        P(u0 + nu, v0 + nv, 0.4),
      );
    };
    line(lu0, lv0, lu1, lv0);
    line(lu1, lv0, lu1, lv1);
    line(lu1, lv1, lu0, lv1);
    line(lu0, lv1, lu0, lv0);
    const mu = (lu0 + lu1) / 2,
      mv = (lv0 + lv1) / 2;
    line(mu, lv0, mu, lv1);
    for (let k = 0; k < 24; k++) {
      const t0 = (k / 24) * Math.PI * 2,
        t1 = ((k + 1) / 24) * Math.PI * 2;
      line(
        mu + 9.15 * Math.cos(t0),
        mv + 9.15 * Math.sin(t0),
        mu + 9.15 * Math.cos(t1),
        mv + 9.15 * Math.sin(t1),
      );
    }
    for (const [ue, sg] of [
      [lu0, 1],
      [lu1, -1],
    ]) {
      const bu = ue + sg * 16.5,
        su = ue + sg * 5.5;
      line(ue, mv - 20.15, bu, mv - 20.15);
      line(bu, mv - 20.15, bu, mv + 20.15);
      line(bu, mv + 20.15, ue, mv + 20.15);
      line(ue, mv - 9.16, su, mv - 9.16);
      line(su, mv - 9.16, su, mv + 9.16);
      line(su, mv + 9.16, ue, mv + 9.16);
      // Goals.
      for (const dv of [-3.66, 3.66]) {
        const pp = P(ue - sg * 0.6, mv + dv, 0);
        kit.box(batch, lineM, pp[0], pp[1], 0, 0.15, 0.15, 2.44, a);
      }
      const pc = P(ue - sg * 0.6, mv, 0);
      kit.box(batch, lineM, pc[0], pc[1], 2.36, 0.15, 7.4, 0.15, a);
    }
    g.add(batch.toGroup('loftus_road'));
    return g;
  },
};
