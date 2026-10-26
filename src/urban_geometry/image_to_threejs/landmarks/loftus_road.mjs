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
        'two overhung tiers at School End and Loftus Road end, executive boxes between South Africa Road tiers, Ellerslie Road single tier; post-and-beam roof with posts at each end and two between; four slim floodlight pylons behind the School End and Loftus Road end; fascias painted the same blue',
    },
    {
      title: 'Loftus Road - Around the Grounds',
      url: 'https://www.aroundthegrounds.org/grounds-hub/loftus-road/',
      used_for:
        'South Africa Road Stand with the larger upper tier and only a couple of supporting pillars',
    },
  ],
  notes:
    'Stands modelled as oriented rectangles fitted to the Overture footprints. Heights raised from the OSM values (6-11 m) to 12-15 m so the roofs meet as described. Seating is stepped geometry (0.8 m rows, one seat back per 0.5 m, gangways every ~11 m); tier rakes, box depth, roof girder spacing, pylon height (~36 m) and advertising boards are approximate. Pitch drawn between the stands (no footprint).',
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

    const stepM = kit.mat('#9ea3a6', { roughness: 0.9, side: THREE.DoubleSide });
    const seatBlue = kit.mat('#1f4fa8', { roughness: 0.6, side: THREE.DoubleSide });
    const seatWhiteM = kit.mat('#eef1f4', { roughness: 0.6, side: THREE.DoubleSide });
    const fasciaBlue = kit.paintedMaterial(
      'loftus_road:fascia',
      1024,
      64,
      (x, w, h) => {
        x.fillStyle = '#1d4a9c';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#ffffff';
        x.fillRect(0, h - 6, w, 3);
        x.font = 'bold 40px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        for (let k = 0; k < 4; k++) x.fillText('Q P R', (k + 0.5) * (w / 4), h / 2);
      },
      DS,
    );
    // A stand defined in its own axis: t along the stand (t0..t1), d depth from
    // pitch edge (0) to back (D); map(t, d) -> local (u, v).
    // opts.tiers: [{ d0, z0, d1, z1 }] seating decks; opts.boxes: executive box
    // band between tiers; opts.posts: front roof columns (t values).
    const stand = (map, t0, t1, D, H, opts) => {
      const L = t1 - t0;
      const Q = (t, d, z) => {
        const [u, v] = map(t, d);
        return P(u, v, z);
      };
      const rect = (m, ta, tb, da, za, db, zb, uv) =>
        quad(m, Q(ta, da, za), Q(tb, da, za), Q(tb, db, zb), Q(ta, db, zb), uv);
      // Pitch-side wall (low front wall) and back facade.
      rect(concrete, t0, t1, 0, 0, 0, 1.2);
      const back = D - 0.2;
      if (opts.backM)
        quad(opts.backM, Q(t1, D, 0), Q(t0, D, 0), Q(t0, D, H), Q(t1, D, H), [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ]);
      else
        quad(clad, Q(t1, D, 0), Q(t0, D, 0), Q(t0, D, H), Q(t1, D, H), [
          [0, 0],
          [L / 16, 0],
          [L / 16, 1],
          [0, 1],
        ]);
      // Back elevation in relief: turnstile doors, concourse windows and the
      // steel stanchions of the frame.
      {
        const A = Q(t1, D, 0),
          B = Q(t0, D, 0);
        const ab = [
          [A[0], A[1]],
          [B[0], B[1]],
        ];
        kit.windowRow(batch, ab[0], ab[1], 0.05, {
          glass: kit.mat('#23292f'),
          frame: steel,
          sill: steel,
          bay: 7,
          width: 1.6,
          height: 2.5,
          margin: 3,
          head: 'lintel',
          bars: 1,
          depth: 0.18,
        });
        kit.windowRow(batch, ab[0], ab[1], H * 0.41, {
          glass,
          frame: fascia,
          sill: fascia,
          bay: 3.5,
          width: 2.8,
          height: 1.1,
          margin: 2,
          head: 'none',
          bars: 1,
          depth: 0.12,
        });
        for (let t = t0; t <= t1 + 0.01; t += L / Math.max(1, Math.round(L / 6))) {
          const p = Q(t, D + 0.15, 0);
          kit.box(batch, steel, p[0], p[1], 0, 0.3, 0.3, H, a);
        }
      }
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
      // Stepped seating decks: concrete risers and treads, a seat back per
      // seat (0.5 m pitch) and a seat pan strip per block, gangways every ~11 m.
      const gang = [];
      const ng = Math.max(2, Math.round(L / 11));
      for (let k = 0; k <= ng; k++) gang.push(t0 + (L * k) / ng);
      const deck = ({ d0, z0, d1, z1, white }) => {
        const rd = 0.8;
        const n = Math.max(1, Math.round((d1 - d0) / rd));
        const dd = (d1 - d0) / n,
          dz = (z1 - z0) / n;
        const sm = white ? seatWhiteM : seatBlue;
        for (let k = 0; k < n; k++) {
          const da = d0 + k * dd,
            za = z0 + k * dz;
          rect(concrete, t0, t1, da, za, da, za + dz);
          rect(stepM, t0, t1, da, za + dz, da + dd, za + dz);
          const zs = za + dz;
          for (let gi = 0; gi < gang.length - 1; gi++) {
            const ta = gang[gi] + 0.6,
              tb = gang[gi + 1] - 0.6;
            // Seat pans.
            rect(sm, ta, tb, da + 0.15, zs + 0.42, da + 0.5, zs + 0.42);
            // Seat backs.
            const ns = Math.floor((tb - ta) / 0.5);
            for (let s = 0; s < ns; s++) {
              const sa = ta + s * 0.5 + 0.04,
                sb = sa + 0.42;
              rect(sm, sa, sb, da + 0.55, zs + 0.38, da + 0.62, zs + 0.82);
            }
          }
        }
        // Gangway handrails.
        for (const t of gang.slice(1, -1)) {
          const A = Q(t, d0, z0 + 1),
            B = Q(t, d1, z1 + 1);
          const len = Math.hypot(B[0] - A[0], B[1] - A[1], B[2] - A[2]);
          const geo = new THREE.CylinderGeometry(0.03, 0.03, len, 4);
          const dir = new THREE.Vector3(B[0] - A[0], B[1] - A[1], B[2] - A[2]).normalize();
          const m = new THREE.Matrix4().makeRotationFromQuaternion(
            new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir),
          );
          m.setPosition((A[0] + B[0]) / 2, (A[1] + B[1]) / 2, (A[2] + B[2]) / 2);
          batch.addGeometry(steel, geo, m);
          geo.dispose();
        }
        // Underside of the deck (seen from the concourse behind).
        rect(concrete, t1, t0, d0, z0 - 0.3, d1, z1 - 0.3);
        return { n };
      };
      for (const tier of opts.tiers) deck(tier);
      if (opts.boxes) {
        // Executive boxes between the tiers: glazed fronts with mullions, a
        // concrete balcony slab and the white fascia of the upper tier.
        const { d, z } = opts.boxes;
        rect(glass, t0, t1, d, z, d, z + 2.6);
        rect(concrete, t0, t1, d - 1.4, z, d, z);
        for (let t = t0 + 2; t < t1; t += 3.6) {
          const p = Q(t, d - 0.05, 0);
          kit.box(batch, fascia, p[0], p[1], z, 0.12, 0.12, 2.6, a);
        }
        // Balcony rail.
        rect(glass, t0, t1, d - 1.4, z, d - 1.4, z + 1.0);
        rect(fascia, t0, t1, d - 1.6, z + 2.6, d - 1.6, z + 3.6);
      }
      // Rear concourse wall above the top tier.
      const top = opts.tiers[opts.tiers.length - 1];
      rect(concrete, t0, t1, top.d1, top.z1, back, top.z1);
      rect(glass, t0, t1, back, top.z1, back, H - 0.6);
      // Roof: sheeted deck on girders, cantilevered past the front.
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
      rect(fasciaBlue, t0, t1, df, zf - 0.4, df, zf + 0.5, [
        [0, 0],
        [L / 40, 0],
        [L / 40, 1],
        [0, 1],
      ]);
      // Roof girders (deep lattice beams read as solid webs with chords).
      for (let t = t0 + 3; t < t1; t += 6) {
        for (const [d0, d1] of [[df, D]]) {
          const A = Q(t, d0, zf),
            B = Q(t, d1, zr);
          const A2 = Q(t, d0, zf - 0.1),
            B2 = Q(t, d1, zr - 1.1);
          quad(
            steel,
            [A[0], A[1], A[2]],
            [B[0], B[1], B[2]],
            [B2[0], B2[1], B2[2]],
            [A2[0], A2[1], A2[2]],
          );
        }
        // Corrugation ribs on top.
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
      // Front roof columns.
      for (const t of opts.posts ?? []) {
        const p = Q(t, 0.4, 0);
        kit.box(batch, steel, p[0], p[1], 1.2, 0.45, 0.45, zf - 1.2, a);
      }
      // Floodlight / PA gantry along the roof front.
      for (let t = t0 + 6; t < t1 - 3; t += 12) {
        const pp = Q(t, df + 0.6, 0);
        kit.box(batch, steel, pp[0], pp[1], zf - 0.9, 2.4, 0.6, 0.7, a);
        kit.box(batch, lamp, pp[0], pp[1], zf - 1.0, 2.0, 0.5, 0.1, a);
      }
      // Stair cores / turnstile blocks against the back elevation.
      for (const t of [t0 + L * 0.2, t0 + L * 0.8]) {
        const [u, v] = map(t, D + 2.2);
        const p = P(u, v, 0);
        kit.box(batch, clad, p[0], p[1], 0, 6, 4.2, H * 0.75, a);
        const [u2, v2] = map(t, D + 4.35);
        const p2 = P(u2, v2, 0);
        kit.box(batch, glass, p2[0], p2[1], 0.2, 4.6, 0.1, 2.5, a);
      }
    };
    const lamp = kit.mat('#fffbe8', { emissive: '#d9d3b8' });

    const H = { N: 15, S: 12.5, E: 14, W: 14 };
    // North: South Africa Road (two tiers with executive boxes between). t = u.
    {
      const D = outer.v1 - pv1;
      stand((t, d) => [t, pv1 + d], outer.u0, outer.u1, D, H.N, {
        tiers: [
          { d0: 0.3, z0: 1.2, d1: D * 0.42, z1: 5.0 },
          { d0: D * 0.42 - 1.5, z0: 8.4, d1: D - 2.2, z1: H.N - 2.6 },
        ],
        boxes: { d: D * 0.42 + 0.6, z: 5.3 },
        posts: [
          outer.u0 + 0.5,
          outer.u0 + (outer.u1 - outer.u0) / 3,
          outer.u0 + (2 * (outer.u1 - outer.u0)) / 3,
          outer.u1 - 0.5,
        ],
        backM: backFacade('sar', 'SOUTH AFRICA ROAD STAND', false),
      });
    }
    // South: Ellerslie Road (single tier, lowest).
    {
      const D = pv0 - outer.v0;
      stand((t, d) => [-t, pv0 - d], -outer.u1, -outer.u0, D, H.S, {
        tiers: [{ d0: 0.3, z0: 1.2, d1: D * 0.9, z1: H.S * 0.62 }],
        posts: [
          -outer.u1 + 0.5,
          -outer.u1 + (outer.u1 - outer.u0) * 0.25,
          -outer.u1 + (outer.u1 - outer.u0) * 0.5,
          -outer.u1 + (outer.u1 - outer.u0) * 0.75,
          -outer.u0 - 0.5,
        ],
        backM: backFacade('ell', 'QUEENS PARK RANGERS  -  LOFTUS ROAD STADIUM', true),
      });
    }
    // East: Loftus Road end; two tightly packed overhung tiers; t runs along -v.
    {
      const D = outer.u1 - pu1;
      stand((t, d) => [pu1 + d, -t], -pv1, -pv0, D, H.E, {
        tiers: [
          { d0: 0.3, z0: 1.2, d1: D * 0.5, z1: 5.2 },
          { d0: D * 0.38, z0: 6.6, d1: D - 1.8, z1: H.E - 2.4 },
        ],
        posts: [-pv1 + 0.5, (-pv1 - pv0) / 2, -pv0 - 0.5],
      });
    }
    // West: School End (away end).
    {
      const D = pu0 - outer.u0;
      stand((t, d) => [pu0 - d, t], pv0, pv1, D, H.W, {
        tiers: [
          { d0: 0.3, z0: 1.2, d1: D * 0.5, z1: 5.2 },
          { d0: D * 0.38, z0: 6.6, d1: D - 1.8, z1: H.W - 2.4 },
        ],
        posts: [pv0 + 0.5, (pv0 + pv1) / 2, pv1 - 0.5],
      });
    }
    // Corner infill (roofs meet at the corners): stepped corner seating under a
    // sloping corner roof.
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
        // Corner signal / TV gantry.
        const cu = (u0 + u1) / 2,
          cv = (v0 + v1) / 2;
        const pc = P(cu, cv, 0);
        kit.box(batch, steel, pc[0], pc[1], 14.5, 2, 2, 1.2, a);
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
    // Goal nets (back frame and net panels) behind each goal line.
    const net = kit.mat('#f4f4f4', {
      transparent: true,
      opacity: 0.35,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    for (const [ue, sg] of [
      [lu0, 1],
      [lu1, -1],
    ]) {
      const ub = ue - sg * 2.0;
      quad(
        net,
        P(ub, mv - 3.66, 0.4),
        P(ub, mv + 3.66, 0.4),
        P(ub, mv + 3.66, 2.0),
        P(ub, mv - 3.66, 2.0),
      );
      quad(
        net,
        P(ue, mv - 3.66, 2.44),
        P(ue, mv + 3.66, 2.44),
        P(ub, mv + 3.66, 2.0),
        P(ub, mv - 3.66, 2.0),
      );
      for (const dv of [-3.66, 3.66])
        quad(
          net,
          P(ue, mv + dv, 0.4),
          P(ub, mv + dv, 0.4),
          P(ub, mv + dv, 2.0),
          P(ue, mv + dv, 2.44),
        );
      // Penalty spot and arc.
      const ps = P(ue + sg * 11, mv, 0);
      kit.box(batch, lineM, ps[0], ps[1], 0.36, 0.3, 0.3, 0.05, a);
      for (let k = 0; k < 10; k++) {
        const t0 = -0.93 + (1.86 * k) / 10,
          t1 = -0.93 + (1.86 * (k + 1)) / 10;
        line(
          ue + sg * 11 + sg * 9.15 * Math.cos(t0),
          mv + 9.15 * Math.sin(t0),
          ue + sg * 11 + sg * 9.15 * Math.cos(t1),
          mv + 9.15 * Math.sin(t1),
        );
      }
    }
    // Corner flags.
    for (const [cu, cv] of [
      [lu0, lv0],
      [lu0, lv1],
      [lu1, lv0],
      [lu1, lv1],
    ]) {
      const p = P(cu, cv, 0);
      kit.box(batch, lineM, p[0], p[1], 0.35, 0.05, 0.05, 1.5, a);
      kit.box(batch, kit.mat('#f2c230'), p[0] + 0.2, p[1], 1.5, 0.4, 0.02, 0.3, a);
    }
    // Centre spot.
    {
      const p = P(mu, mv, 0);
      kit.box(batch, lineM, p[0], p[1], 0.36, 0.3, 0.3, 0.05, a);
    }
    // Perimeter advertising boards round the pitch.
    const boards = kit.paintedMaterial(
      'loftus_road:boards',
      1024,
      64,
      (x, w, h) => {
        const cols = ['#1d4a9c', '#ffffff', '#0b2a5c', '#c8102e', '#1d4a9c', '#f2c230'];
        for (let k = 0; k < 8; k++) {
          x.fillStyle = cols[k % cols.length];
          x.fillRect((k * w) / 8, 0, w / 8, h);
          x.fillStyle = k % cols.length === 1 || k % cols.length === 5 ? '#1d4a9c' : '#ffffff';
          x.font = 'bold 30px sans-serif';
          x.textAlign = 'center';
          x.textBaseline = 'middle';
          x.fillText(k % 2 ? 'QPR' : 'R s', ((k + 0.5) * w) / 8, h / 2 + 2);
        }
      },
      DS,
    );
    {
      const bo = 1.6,
        bu0 = pu0 + bo,
        bu1 = pu1 - bo,
        bv0 = pv0 + bo,
        bv1 = pv1 - bo;
      const side = (A, B) => {
        const len = Math.hypot(B[0] - A[0], B[1] - A[1]);
        quad(
          boards,
          [A[0], A[1], 0.35],
          [B[0], B[1], 0.35],
          [B[0], B[1], 1.25],
          [A[0], A[1], 1.25],
          [
            [0, 0],
            [len / 40, 0],
            [len / 40, 1],
            [0, 1],
          ],
        );
      };
      side(P(bu0, bv0, 0), P(bu1, bv0, 0));
      side(P(bu1, bv1, 0), P(bu0, bv1, 0));
      side(P(bu1, bv0, 0), P(bu1, bv1, 0));
      side(P(bu0, bv1, 0), P(bu0, bv0, 0));
    }
    // Dugouts and tunnel in front of the South Africa Road Stand.
    {
      const perspex = kit.mat('#9fb6c4', {
        transparent: true,
        opacity: 0.5,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      for (const du of [-9, 9]) {
        const c = P(mu + du, pv1 - 1.2, 0);
        kit.box(batch, kit.mat('#1d4a9c'), c[0], c[1], 0.35, 7, 1.6, 0.5, a);
        const geo = new THREE.CylinderGeometry(1.4, 1.4, 7, 12, 1, true, 0, Math.PI).rotateZ(
          Math.PI / 2,
        );
        const m = new THREE.Matrix4().makeRotationZ(a);
        m.multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
        m.setPosition(c[0], c[1], 0.4);
        batch.addGeometry(perspex, geo, m);
        geo.dispose();
      }
      const t = P(mu, pv1 - 1.6, 0);
      kit.box(batch, kit.mat('#e9ecef'), t[0], t[1], 0.35, 3.2, 3.2, 2.4, a);
    }
    // Four slim floodlight pylons rising from behind the School End and the
    // Loftus Road end, heads tilted towards the pitch.
    {
      const lampHead = kit.mat('#fffbe8', { emissive: '#e8e2c0' });
      const pylon = (u, v, towardsU) => {
        const p = P(u, v, 0);
        const shaft = new THREE.CylinderGeometry(0.35, 0.7, 34, 8).rotateX(Math.PI / 2);
        batch.addGeometry(steel, shaft, new THREE.Matrix4().makeTranslation(p[0], p[1], 17));
        shaft.dispose();
        const head = new THREE.BoxGeometry(1.2, 5.5, 3.2);
        const m = new THREE.Matrix4().makeRotationZ(a);
        m.multiply(new THREE.Matrix4().makeRotationY(towardsU * 0.45));
        m.setPosition(p[0], p[1], 35.2);
        batch.addGeometry(steel, head, m);
        head.dispose();
        const face = new THREE.BoxGeometry(0.1, 5.0, 2.8);
        const m2 = new THREE.Matrix4().makeRotationZ(a);
        m2.multiply(new THREE.Matrix4().makeRotationY(towardsU * 0.45));
        const off = P(u + towardsU * 0.65, v, 0);
        m2.setPosition(off[0], off[1], 35.2);
        batch.addGeometry(lampHead, face, m2);
        face.dispose();
      };
      for (const [u, sg] of [
        [outer.u0 - 2.5, 1],
        [outer.u1 + 2.5, -1],
      ])
        for (const v of [pv0 + 6, pv1 - 6]) pylon(u, v, sg);
    }
    g.add(batch.toGroup('loftus_road'));
    return g;
  },
};
