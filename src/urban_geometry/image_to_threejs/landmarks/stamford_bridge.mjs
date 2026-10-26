// Stamford Bridge, Fulham Road - home of Chelsea FC since 1905. Four roofed stands
// close around the pitch: the three-tier East Stand (1970s, the only one to survive
// the 1990s rebuild), the two-tier Matthew Harding (North) Stand (1994) and Shed End
// (1990s), and the largest, three-tier West Stand (completed 2001) with executive
// boxes and a polycarbonate-clad steel roof. Blue seating, grey/blue clad exteriors.
export default {
  id: 'stamford_bridge',
  name: 'Stamford Bridge (Chelsea FC)',
  claims: [
    '86c51da0-ca51-4c0b-af84-ad5642b6138f', // West Stand
    '89551eed-b17f-49a4-a165-1aa9af9550a6', // East Stand
    'a89e22dc-242d-488a-97bf-90dcbdbd2f07', // Shed End
    'e4d88631-8795-425b-af2d-e603d2ea4b67', // Matthew Harding Stand
    '12884a42-26b5-4bb5-be9d-b2e7137aaed8', // small link block at the Matthew Harding stand
  ],
  references: [
    {
      title: 'Stamford Bridge (stadium) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Stamford_Bridge_(stadium)',
      used_for: 'stand names and history, capacity ~40,000',
    },
    {
      title: 'Stamford Bridge - Multiplex',
      url: 'https://www.multiplex.global/projects/stamford-bridge/',
      used_for: 'West Stand: three tiers, row of executive boxes, polycarbonate-clad steel roof',
    },
    {
      title: 'Stamford Bridge Football Stadium - Event Masters',
      url: 'https://www.eventmasters.co.uk/stamford-bridge.html',
      used_for: 'East Stand 1973 three tiers, only stand surviving the 1990s redevelopment',
    },
    {
      title: 'Stamford Bridge tickets - Tiqets',
      url: 'https://tiqets.com/en/stamford-bridge-tickets-l145956',
      used_for: 'photo caption: blue seating spelling CHELSEA under a large roof',
    },
    {
      title: 'Stamford Bridge: Chelsea FC - Football Stadiums',
      url: 'https://www.football-stadiums.co.uk/?p=14',
      used_for:
        'two-tier Shed End and Matthew Harding Stand, three-tier West Stand with near-transparent roof',
    },
    {
      title: 'Stamford Bridge - Football Ground Guide',
      url: 'https://footballgroundguide.com/leagues/england/premier-league/stamford-bridge-chelsea.html',
      used_for: 'stand layout and tiering (upper and lower tiers all round)',
    },
    {
      title: 'Matthew Harding remembered - Chelsea FC',
      url: 'https://www.chelseafc.com/en/news/article/matthew-harding-remembered---his-chelsea-timeline',
      used_for: 'North (Matthew Harding) Stand opened November 1994',
    },
  ],
  notes:
    'Stand roof heights estimated (West 31 m, East 30 m, Matthew Harding 23 m, Shed End 21 m; Overture gives 7-9 m). ' +
    'Seating is modelled as stepped concrete rows (0.8 m treads) with blue seat strips broken by gangways: two tiers ' +
    'for the Matthew Harding and Shed End, three for the East and West Stands, upper tiers cantilevered over glazed ' +
    'hospitality / box bands; row counts and rakes are fitted to the footprint depth and roof height, not surveyed. ' +
    'Roofs carry a lattice front truss with floodlight luminaires and a translucent leading edge (wider on the West ' +
    'Stand); exterior cladding, the CHELSEA seat lettering on the East Stand lower tier, the dugout / tunnel position ' +
    'in front of the West Stand and the big screens (omitted) are approximate. The Millennium hotel footprint is ' +
    'left to the generic layer.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const addGeo = (m, geo, mtx) => {
      batch.addGeometry(m, geo, mtx);
      geo.dispose();
    };
    // Bowl corners (pitch-side vertices of the stand outlines).
    const Wc = [598.3, -2727.9],
      Nc = [659.0, -2686.9],
      Ec = [721.0, -2771.8],
      Sc = [660.0, -2816.0];
    const cx = (Wc[0] + Nc[0] + Ec[0] + Sc[0]) / 4,
      cy = (Wc[1] + Nc[1] + Ec[1] + Sc[1]) / 4;
    const A = Math.atan2((Ec[1] - Nc[1] + Sc[1] - Wc[1]) / 2, (Ec[0] - Nc[0] + Sc[0] - Wc[0]) / 2); // towards the Shed
    const ca = Math.cos(A),
      sa = Math.sin(A);
    const L = ([x, y]) => [(x - cx) * ca + (y - cy) * sa, -(x - cx) * sa + (y - cy) * ca];
    const Wd = (u, v, z) => [cx + u * ca - v * sa, cy + u * sa + v * ca, z];
    const [uW, vW] = L(Wc),
      [uN, vN] = L(Nc),
      [uE, vE] = L(Ec),
      [uS, vS] = L(Sc);
    const uMH = (uW + uN) / 2,
      uSh = (uE + uS) / 2,
      vEa = (vN + vE) / 2,
      vWe = (vW + vS) / 2;

    // Materials.
    const clad = kit.paintedMaterial('stamford_bridge:clad', 512, 256, (c, w, h) => {
      c.fillStyle = '#b9bec2';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(80,90,100,0.25)';
      for (let x = 0; x < w; x += 16) c.fillRect(x, 0, 2, h);
      c.fillStyle = '#1f4e9c';
      c.fillRect(0, 96, w, 30); // Chelsea blue band
      c.fillStyle = '#2d3b46';
      c.fillRect(0, 140, w, 40); // glazed concourse level
      c.fillStyle = '#8a9095';
      for (let x = 0; x < w; x += 64) c.fillRect(x, 140, 4, 40);
      c.fillStyle = '#e8e9ea';
      c.fillRect(0, h - 40, w, 40);
      c.fillStyle = '#2d3b46';
      for (let x = 20; x < w; x += 128) c.fillRect(x, h - 36, 60, 36); // turnstiles / shops
    });
    const seats = kit.paintedMaterial('stamford_bridge:seats', 256, 256, (c, w, h) => {
      c.fillStyle = '#1b4aa0';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#123577';
      for (let y = 0; y < h; y += 8) c.fillRect(0, y, w, 3);
      c.fillStyle = '#c9ccd0';
      for (let x = 0; x < w; x += 64) c.fillRect(x, 0, 4, h); // gangways
    });
    const seatsName = kit.paintedMaterial(
      'stamford_bridge:seats_name',
      1024,
      256,
      (c, w, h) => {
        c.fillStyle = '#1b4aa0';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#123577';
        for (let y = 0; y < h; y += 8) c.fillRect(0, y, w, 3);
        c.fillStyle = '#f2f2f2';
        c.font = 'bold 150px sans-serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('CHELSEA', w / 2, h / 2 + 8);
        c.fillStyle = '#123577';
        for (let y = 0; y < h; y += 8) c.fillRect(0, y, w, 2);
      },
      {},
    );
    const roofMat = kit.mat('#c7cbce', { roughness: 0.6, metalness: 0.3 });
    const polyc = kit.mat('#e8eef0', {
      roughness: 0.3,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
    });
    const truss = kit.mat('white_steel');
    const boxes = kit.mat('dark_glass');
    const conc = kit.mat('concrete');
    const pitch = kit.paintedMaterial('stamford_bridge:pitch', 512, 256, (c, w, h) => {
      for (let i = 0; i < 16; i++) {
        c.fillStyle = i % 2 ? '#4f8f3d' : '#5d9e48';
        c.fillRect((i * w) / 16, 0, w / 16 + 1, h);
      }
      c.strokeStyle = '#f4f4f0';
      c.lineWidth = 3;
      const mx = 18,
        my = 14;
      c.strokeRect(mx, my, w - 2 * mx, h - 2 * my);
      c.beginPath();
      c.moveTo(w / 2, my);
      c.lineTo(w / 2, h - my);
      c.stroke();
      c.beginPath();
      c.arc(w / 2, h / 2, 34, 0, Math.PI * 2);
      c.stroke();
      for (const s of [0, 1]) {
        const x0 = s ? w - mx : mx,
          d = s ? -1 : 1;
        c.strokeRect(Math.min(x0, x0 + d * 80), h / 2 - 76, 80, 152);
        c.strokeRect(Math.min(x0, x0 + d * 28), h / 2 - 34, 28, 68);
      }
    });

    // Pitch and surrounds inside the bowl.
    const corners = [Wc, Sc, Ec, Nc];
    batch.add(
      kit.mat('#4b7f3a'),
      corners.map((p) => [p[0], p[1], 0.06]),
      corners.map(() => [0, 0]),
      [0, 1, 2, 0, 2, 3],
    );
    {
      const pu = 52.5 * 0.98,
        pv = 34;
      const q = [Wd(-pu, -pv, 0.1), Wd(pu, -pv, 0.1), Wd(pu, pv, 0.1), Wd(-pu, pv, 0.1)];
      batch.add(
        pitch,
        q,
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }

    // Stand definitions in the local frame: dist(u, v) = distance outward from the
    // pitch-side line; lat(u, v) = coordinate along it.
    const stands = [
      {
        id: 'e4d88631-8795-425b-af2d-e603d2ea4b67',
        H: 23,
        dist: (u) => uMH - u,
        lat: (u, v) => v,
        l0: vWe,
        l1: vEa,
        out: [-1, 0],
      },
      {
        id: 'a89e22dc-242d-488a-97bf-90dcbdbd2f07',
        H: 21,
        dist: (u) => u - uSh,
        lat: (u, v) => v,
        l0: vWe,
        l1: vEa,
        out: [1, 0],
      },
      {
        id: '89551eed-b17f-49a4-a165-1aa9af9550a6',
        H: 30,
        dist: (u, v) => v - vEa,
        lat: (u) => u,
        l0: uMH,
        l1: uSh,
        out: [0, 1],
        name: true,
      },
      {
        id: '86c51da0-ca51-4c0b-af84-ad5642b6138f',
        H: 31,
        dist: (u, v) => vWe - v,
        lat: (u) => u,
        l0: uMH,
        l1: uSh,
        out: [0, -1],
      },
    ];
    const hOf = new Map(stands.map((s) => [s.id, s.H]));
    hOf.set('12884a42-26b5-4bb5-be9d-b2e7137aaed8', 9);
    // point on a stand: from dist / lat back to world
    const at = (s, lat, dist, z) => {
      if (s.out[0]) {
        const u = s.out[0] < 0 ? uMH - dist : uSh + dist;
        return Wd(u, lat, z);
      }
      const v = s.out[1] > 0 ? vEa + dist : vWe - dist;
      return Wd(lat, v, z);
    };
    // Ring clipping by a predicate on dist (Sutherland-Hodgman against dist = d0).
    const clip = (ring, s, keepAbove, d0) => {
      const out = [];
      const f = (p) => {
        const [u, v] = L(p);
        return (s.dist(u, v) - d0) * (keepAbove ? 1 : -1);
      };
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const fp = f(p),
          fq = f(q);
        if (fp >= 0) out.push(p);
        if (fp >= 0 !== fq >= 0) {
          const t = fp / (fp - fq);
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
      }
      return out.length >= 3 ? out : null;
    };
    const allEdges = [];
    for (const id of hOf.keys()) {
      const b = byId[id];
      if (!b) continue;
      const ring = b.polys[0][0];
      for (let k = 0; k < ring.length; k++)
        allEdges.push({ id, p: ring[k], q: ring[(k + 1) % ring.length] });
    }
    const near = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]) < 0.6;
    const inBowl = (p) => {
      const [u, v] = L(p);
      return u > uMH - 2.5 && u < uSh + 2.5 && v > vWe - 2.5 && v < vEa + 2.5;
    };

    // Exterior walls: skip pitch-side edges; shared edges only above the lower stand.
    for (const e of allEdges) {
      if (inBowl(e.p) && inBowl(e.q)) continue;
      const H = hOf.get(e.id);
      let z0 = 0;
      const other = allEdges.find(
        (o) =>
          o.id !== e.id &&
          ((near(o.p, e.q) && near(o.q, e.p)) || (near(o.p, e.p) && near(o.q, e.q))),
      );
      if (other) {
        const Ho = hOf.get(other.id);
        if (Ho >= H) continue;
        z0 = Ho;
      }
      const len = Math.hypot(e.q[0] - e.p[0], e.q[1] - e.p[1]);
      if (len < 0.05) continue;
      const nb = Math.max(1, Math.round(len / 6));
      batch.quad(
        clad,
        [e.p[0], e.p[1], z0],
        [e.q[0], e.q[1], z0],
        [e.q[0], e.q[1], H],
        [e.p[0], e.p[1], H],
        [0, z0 / H],
        [nb / 4, z0 / H],
        [nb / 4, 1],
        [0, 1],
      );
    }
    // Small link block.
    {
      const b = byId['12884a42-26b5-4bb5-be9d-b2e7137aaed8'];
      if (b) kit.cap(batch, roofMat, b.polys, 9);
    }

    const DS = { side: THREE.DoubleSide };
    const seatBlue = kit.paintedMaterial(
      'stamford_bridge:seatrow',
      64,
      64,
      (c, w, h) => {
        c.fillStyle = '#1d4fa8';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#163e86';
        for (let x = 0; x < w; x += 8) c.fillRect(x, 0, 2, h);
      },
      DS,
    );
    const seatLetters = kit.paintedMaterial(
      'stamford_bridge:seat_letters',
      1024,
      256,
      (c, w, h) => {
        c.fillStyle = '#1d4fa8';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#f2f2f2';
        c.font = 'bold 190px sans-serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('CHELSEA', w / 2, h / 2 + 10);
      },
      DS,
    );
    const treadMat = kit.mat('#9a9c9e', { roughness: 0.9, ...DS });
    const riserMat = kit.mat('#7f8285', { roughness: 0.9, ...DS });
    const fasciaWhite = kit.mat('#eef0f2', { roughness: 0.6, ...DS });
    const ledMat = kit.mat('#1a3d7a', {
      emissive: new THREE.Color('#2456b0'),
      roughness: 0.4,
      ...DS,
    });
    const boxGlass = kit.mat('#26323c', { roughness: 0.15, metalness: 0.3, ...DS });
    const soffit = kit.mat('#d7dadc', { roughness: 0.8, ...DS });
    const floodMat = kit.mat('#fffbe8', { emissive: new THREE.Color('#fff2c0'), roughness: 0.3 });
    const steelDS = kit.mat('white_steel', DS);
    const tierCfg = {
      'e4d88631-8795-425b-af2d-e603d2ea4b67': [0.5, 0.5],
      'a89e22dc-242d-488a-97bf-90dcbdbd2f07': [0.55, 0.45],
      '89551eed-b17f-49a4-a165-1aa9af9550a6': [0.36, 0.22, 0.42],
      '86c51da0-ca51-4c0b-af84-ad5642b6138f': [0.36, 0.22, 0.42],
    };
    for (const s of stands) {
      const b = byId[s.id];
      if (!b) continue;
      const ring = b.polys[0][0];
      const H = s.H;
      kit.cap(batch, conc, b.polys, 0.05);
      let dmax = 0;
      for (const p of ring) {
        const [u, v] = L(p);
        const lt = s.lat(u, v);
        if (lt > s.l0 + 5 && lt < s.l1 - 5) dmax = Math.max(dmax, s.dist(u, v));
      }
      const D = Math.min(Math.max(14, dmax - 1.5), 40);
      // Roof: translucent leading strip, opaque behind; soffit underneath.
      const front = s.id.startsWith('86c5') ? 16 : 9;
      const opaque1 = clip(ring, s, true, front),
        opaque2 = clip(ring, s, false, 0.01);
      const strip = clip(ring, s, true, 0.01);
      const strip2 = strip && clip(strip, s, false, front);
      for (const r of [opaque1, opaque2])
        if (r) {
          kit.cap(batch, roofMat, [[r]], H, { scale: 6 });
          kit.cap(batch, soffit, [[r]], H - 0.6, { scale: 6, down: true });
        }
      if (r2(strip2)) kit.cap(batch, polyc, [[strip2]], H - 0.3);

      const l0 = s.l0 + 1,
        l1 = s.l1 - 1;
      const span = l1 - l0;
      const rotLat = s.out[0] ? A + Math.PI / 2 : A;
      const rotDist = s.out[0] ? A : A + Math.PI / 2;
      // Quad in stand coordinates [lat, dist, z].
      const Q = (m, a, bb, c2, d2, uv) =>
        batch.add(
          m,
          [at(s, ...a), at(s, ...bb), at(s, ...c2), at(s, ...d2)],
          uv || [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      const latBox = (m, lt, d, z0, wl, wd, h) =>
        addGeo(
          m,
          new THREE.BoxGeometry(wl, wd, h),
          new THREE.Matrix4().makeRotationZ(rotLat).setPosition(...at(s, lt, d, z0 + h / 2)),
        );
      // Gangway positions along the stand.
      const nSeg = Math.max(3, Math.round(span / 11));
      const gw = 1.3;
      const segs = [];
      for (let k = 0; k < nSeg; k++) {
        const a0 = l0 + (span * k) / nSeg + (k ? gw / 2 : 0),
          a1 = l0 + (span * (k + 1)) / nSeg - (k < nSeg - 1 ? gw / 2 : 0);
        segs.push([a0, a1]);
      }
      // Tier layout: fractions of the depth; rises scaled to fit under the roof.
      const fr = tierCfg[s.id] || [0.5, 0.5];
      const gapH = fr.length === 3 ? 3.0 : 3.4,
        overhang = 3.5,
        d0 = 2.5,
        z0 = 1.1;
      const tread = 0.8;
      const usable = D - d0 + overhang * (fr.length - 1);
      const tiers = fr.map((f, i) => ({
        rows: Math.max(4, Math.floor((usable * f) / tread)),
        rise: 0.3 + 0.12 * i,
      }));
      const sumRise = tiers.reduce((a, t) => a + t.rows * t.rise, 0);
      const k = Math.min(1, (H - 4.5 - z0 - gapH * (tiers.length - 1)) / sumRise);
      tiers.forEach((t) => (t.rise *= k));
      let d = d0,
        z = z0;
      const profile = [];
      quadLat0(conc, 0, 0, d0, z0);
      function quadLat0(m, da, za, db, zb) {
        Q(m, [l0, da, za], [l1, da, za], [l1, db, zb], [l0, db, zb]);
      }
      tiers.forEach((t, ti) => {
        const tz0 = z,
          td0 = d;
        // front wall / balcony fascia of the tier
        if (ti === 0) {
          Q(
            fasciaWhite,
            [l0, d - 0.15, 0],
            [l1, d - 0.15, 0],
            [l1, d - 0.15, z + 1.0],
            [l0, d - 0.15, z + 1.0],
          );
        } else {
          Q(fasciaWhite, [l0, d, z - 1.6], [l1, d, z - 1.6], [l1, d, z + 1.0], [l0, d, z + 1.0]);
          Q(
            ledMat,
            [l0, d - 0.03, z - 1.3],
            [l1, d - 0.03, z - 1.3],
            [l1, d - 0.03, z - 0.3],
            [l0, d - 0.03, z - 0.3],
            [
              [0, 0],
              [span / 4, 0],
              [span / 4, 1],
              [0, 1],
            ],
          );
          Q(
            soffit,
            [l0, d, z - 1.6],
            [l1, d, z - 1.6],
            [l1, d + overhang + 2, z - 0.6],
            [l0, d + overhang + 2, z - 0.6],
          );
        }
        for (let r = 0; r < t.rows; r++) {
          const zr = z + t.rise;
          // riser and tread (concrete), continuous across the stand
          Q(riserMat, [l0, d, z], [l1, d, z], [l1, d, zr], [l0, d, zr]);
          Q(treadMat, [l0, d, zr], [l1, d, zr], [l1, d + tread, zr], [l0, d + tread, zr]);
          // seat row: back face and seat top, split by gangways
          const lettered = s.name && ti === 0;
          const vv0 = r / t.rows,
            vv1 = (r + 0.8) / t.rows;
          for (const [a0, a1] of segs) {
            const m = lettered ? seatLetters : seatBlue;
            const uA = lettered ? (a0 - l0) / span : (a0 - l0) / 2,
              uB = lettered ? (a1 - l0) / span : (a1 - l0) / 2;
            Q(
              m,
              [a0, d + 0.55, zr],
              [a1, d + 0.55, zr],
              [a1, d + 0.62, zr + 0.48],
              [a0, d + 0.62, zr + 0.48],
              [
                [uA, vv0],
                [uB, vv0],
                [uB, vv1],
                [uA, vv1],
              ],
            );
            Q(
              m,
              [a0, d + 0.12, zr + 0.42],
              [a1, d + 0.12, zr + 0.42],
              [a1, d + 0.55, zr + 0.42],
              [a0, d + 0.55, zr + 0.42],
              [
                [uA, vv0],
                [uB, vv0],
                [uB, vv1],
                [uA, vv1],
              ],
            );
          }
          profile.push([d, zr]);
          d += tread;
          z = zr;
        }
        // vomitory openings in the tier (dark portals at mid-depth)
        const vr = Math.floor(t.rows * 0.45);
        const vd = td0 + vr * tread,
          vz = tz0 + vr * t.rise;
        for (let kk = 1; kk < nSeg; kk += 2) {
          const lt = l0 + (span * kk) / nSeg;
          latBox(boxGlass, lt, vd + 1.2, vz - 0.05, 2.4, 2.4, 0.12);
          latBox(fasciaWhite, lt - 1.3, vd + 1.2, vz, 0.15, 2.4, 1.0);
          latBox(fasciaWhite, lt + 1.3, vd + 1.2, vz, 0.15, 2.4, 1.0);
        }
        // hospitality / box band between tiers
        if (ti < tiers.length - 1) {
          const zb = z + gapH;
          Q(fasciaWhite, [l0, d, z], [l1, d, z], [l1, d, z + 0.25], [l0, d, z + 0.25]);
          Q(
            boxGlass,
            [l0, d + 0.2, z + 0.25],
            [l1, d + 0.2, z + 0.25],
            [l1, d + 0.2, zb - 0.4],
            [l0, d + 0.2, zb - 0.4],
          );
          for (let kk = 0; kk <= Math.round(span / 4); kk++)
            latBox(
              fasciaWhite,
              l0 + (span * kk) / Math.round(span / 4),
              d + 0.25,
              z + 0.25,
              0.12,
              0.12,
              gapH - 0.65,
            );
          // box balconies with glass balustrades
          Q(
            treadMat,
            [l0, d - 1.4, z + 0.2],
            [l1, d - 1.4, z + 0.2],
            [l1, d, z + 0.2],
            [l0, d, z + 0.2],
          );
          Q(
            polyc,
            [l0, d - 1.4, z + 0.2],
            [l1, d - 1.4, z + 0.2],
            [l1, d - 1.4, z + 1.2],
            [l0, d - 1.4, z + 1.2],
          );
          for (let kk = 0; kk <= Math.round(span / 4); kk++)
            latBox(
              fasciaWhite,
              l0 + (span * kk) / Math.round(span / 4),
              d - 0.7,
              z + 0.2,
              0.1,
              1.4,
              1.0,
            );
          d -= overhang;
          z = zb;
        }
      });
      // gangway steps (lighter concrete strips) through the seating
      for (const [, a1] of segs.slice(0, -1))
        for (const [pd, pz] of profile)
          latBox(treadMat, a1 + gw / 2, pd + tread / 2, pz, gw, tread, 0.04);
      // back wall from the top row to the roof, with a walkway rail
      Q(riserMat, [l0, d, z], [l1, d, z], [l1, d, H - 0.6], [l0, d, H - 0.6]);
      Q(
        boxGlass,
        [l0, d - 0.05, z + 1.4],
        [l1, d - 0.05, z + 1.4],
        [l1, d - 0.05, z + 2.4],
        [l0, d - 0.05, z + 2.4],
      );
      // end screens: fan from the bottom of the back wall through the profile
      for (const lt of [l0, l1]) {
        const verts = [at(s, lt, d, 0), at(s, lt, 0, 0)];
        for (const [pd, pz] of profile) verts.push(at(s, lt, pd, pz));
        verts.push(at(s, lt, d, z), at(s, lt, d, H - 0.6));
        const tris = [];
        for (let i = 1; i < verts.length - 1; i++) tris.push(0, i, i + 1);
        batch.add(
          kit.mat('#c3c6c9', { roughness: 0.85, ...DS }),
          verts,
          verts.map(() => [0, 0]),
          tris,
        );
      }
      // advertising boards along the pitch edge
      Q(
        ledMat,
        [l0, -0.5, 0],
        [l1, -0.5, 0],
        [l1, -0.5, 1.0],
        [l0, -0.5, 1.0],
        [
          [0, 0],
          [span / 6, 0],
          [span / 6, 1],
          [0, 1],
        ],
      );
      // Roof front: lattice truss with floodlight strip beneath.
      const tz1 = H - 0.3,
        tz0 = H - 2.6;
      latBox(steelDS, (l0 + l1) / 2, 0.6, tz1 - 0.35, span + 2, 0.5, 0.35);
      latBox(steelDS, (l0 + l1) / 2, 0.6, tz0, span + 2, 0.5, 0.35);
      latBox(fasciaWhite, (l0 + l1) / 2, 0.2, tz0 + 0.35, span + 2, 0.1, tz1 - tz0 - 0.7);
      const nd = Math.round(span / 3);
      for (let kk = 0; kk <= nd; kk++) {
        const lt = l0 - 1 + ((span + 2) * kk) / nd;
        latBox(steelDS, lt, 0.9, tz0, 0.18, 0.18, tz1 - tz0);
        if (kk < nd) {
          const lt2 = l0 - 1 + ((span + 2) * (kk + 0.5)) / nd;
          const dl = (span + 2) / nd,
            dh = tz1 - tz0;
          const geo = new THREE.BoxGeometry(Math.hypot(dl, dh), 0.14, 0.14);
          const m = new THREE.Matrix4()
            .makeRotationZ(rotLat)
            .multiply(new THREE.Matrix4().makeRotationY((kk % 2 ? 1 : -1) * Math.atan2(dh, dl)))
            .setPosition(...at(s, lt2, 0.9, (tz0 + tz1) / 2));
          addGeo(steelDS, geo, m);
        }
        if (kk % 2 === 0) {
          // floodlight luminaires angled at the pitch
          const geo = new THREE.BoxGeometry(0.9, 0.5, 0.6);
          const m = new THREE.Matrix4()
            .makeRotationZ(rotLat)
            .multiply(
              new THREE.Matrix4().makeRotationX((s.out[0] < 0 || s.out[1] > 0 ? -1 : 1) * 0.6),
            )
            .setPosition(...at(s, lt, 0.4, tz0 - 0.4));
          addGeo(floodMat, geo, m);
        }
      }
      // rafters under the roof, from the front truss to the back
      const nr = Math.round(span / 8);
      for (let kk = 0; kk <= nr; kk++) {
        const lt = l0 + (span * kk) / nr;
        const geo = new THREE.BoxGeometry(D + 2, 0.4, 1.2);
        addGeo(
          steelDS,
          geo,
          new THREE.Matrix4()
            .makeRotationZ(rotDist)
            .setPosition(...at(s, lt, (D + 2) / 2, H - 1.2)),
        );
      }
      // roof support columns at the back of the seats
      for (let kk = 0; kk <= 4; kk++) {
        const p = at(s, l0 + (span * kk) / 4, d + 0.6, 0);
        addGeo(
          truss,
          new THREE.BoxGeometry(0.8, 0.8, H),
          new THREE.Matrix4().setPosition(p[0], p[1], H / 2),
        );
      }
      // exposed cantilever trusses over the roof of the tall stands
      if (s.H >= 30)
        for (let kk = 0; kk <= 6; kk++) {
          const lt = l0 + (span * kk) / 6;
          const p0 = at(s, lt, D + 4, H),
            p1 = at(s, lt, 2, H);
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          addGeo(
            truss,
            new THREE.BoxGeometry(len, 0.6, 0.5),
            new THREE.Matrix4()
              .makeRotationZ(Math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
              .setPosition((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, H + 2.6),
          );
          for (let j = 0; j <= 5; j++) {
            const dd = 2 + ((D + 2) * j) / 5;
            latBox(truss, lt, dd, H, 0.35, 0.35, 2.4);
            if (j < 5) {
              const geo = new THREE.BoxGeometry(Math.hypot((D + 2) / 5, 2.4), 0.25, 0.25);
              const m = new THREE.Matrix4()
                .makeRotationZ(rotDist)
                .multiply(
                  new THREE.Matrix4().makeRotationY(
                    (j % 2 ? 1 : -1) * Math.atan2(2.4, (D + 2) / 5),
                  ),
                )
                .setPosition(...at(s, lt, dd + (D + 2) / 10, H + 1.3));
              addGeo(truss, geo, m);
            }
          }
        }
    }
    function r2(r) {
      return r && r.length >= 3;
    }

    // Exterior: structural columns and concourse fins on the outside walls.
    for (const e of allEdges) {
      if (inBowl(e.p) && inBowl(e.q)) continue;
      const len = Math.hypot(e.q[0] - e.p[0], e.q[1] - e.p[1]);
      if (len < 8) continue;
      const H = hOf.get(e.id);
      const ux = (e.q[0] - e.p[0]) / len,
        uy = (e.q[1] - e.p[1]) / len;
      const rot = Math.atan2(uy, ux);
      const n = Math.round(len / 7.5);
      for (let i = 0; i <= n; i++) {
        const t = (len * i) / n;
        addGeo(
          truss,
          new THREE.BoxGeometry(0.7, 0.7, H),
          new THREE.Matrix4()
            .makeRotationZ(rot)
            .setPosition(e.p[0] + ux * t + uy * 0.35, e.p[1] + uy * t - ux * 0.35, H / 2),
        );
      }
      // mullions and transom over the glazed concourse band of the cladding
      const nmul = Math.round(len / 2);
      for (let i = 1; i < nmul; i++) {
        const t = (len * i) / nmul;
        addGeo(
          fasciaWhite,
          new THREE.BoxGeometry(0.12, 0.25, H * 0.16),
          new THREE.Matrix4()
            .makeRotationZ(rot)
            .setPosition(e.p[0] + ux * t + uy * 0.12, e.p[1] + uy * t - ux * 0.12, H * 0.375),
        );
      }
      addGeo(
        fasciaWhite,
        new THREE.BoxGeometry(len, 0.25, 0.12),
        new THREE.Matrix4()
          .makeRotationZ(rot)
          .setPosition(
            (e.p[0] + e.q[0]) / 2 + uy * 0.12,
            (e.p[1] + e.q[1]) / 2 - ux * 0.12,
            H * 0.4,
          ),
      );
      for (const zf of [H * 0.156, H * 0.5])
        addGeo(
          fasciaWhite,
          new THREE.BoxGeometry(len, 0.9, 0.3),
          new THREE.Matrix4()
            .makeRotationZ(rot)
            .setPosition((e.p[0] + e.q[0]) / 2 + uy * 0.45, (e.p[1] + e.q[1]) / 2 - ux * 0.45, zf),
        );
      addGeo(
        roofMat,
        new THREE.BoxGeometry(len + 0.4, 1.2, 0.8),
        new THREE.Matrix4()
          .makeRotationZ(rot)
          .setPosition((e.p[0] + e.q[0]) / 2 + uy * 0.5, (e.p[1] + e.q[1]) / 2 - ux * 0.5, H + 0.2),
      );
    }

    // Pitch furniture: goals with nets, corner flags, dugouts, tunnel.
    {
      const post = kit.mat('white');
      const net = kit.paintedMaterial(
        'stamford_bridge:net',
        64,
        64,
        (c, w, h) => {
          c.clearRect(0, 0, w, h);
          c.strokeStyle = 'rgba(255,255,255,0.9)';
          c.lineWidth = 2;
          for (let x = 0; x <= w; x += 8) {
            c.beginPath();
            c.moveTo(x, 0);
            c.lineTo(x, h);
            c.stroke();
            c.beginPath();
            c.moveTo(0, x);
            c.lineTo(w, x);
            c.stroke();
          }
        },
        { transparent: true, alphaTest: 0.3, side: THREE.DoubleSide },
      );
      const P = (u, v, z, r = A) =>
        new THREE.Matrix4().makeRotationZ(r).setPosition(...Wd(u, v, z));
      const pu = 52.5 * 0.98;
      for (const sg of [-1, 1]) {
        const u = sg * pu;
        for (const v of [-3.66, 3.66])
          addGeo(
            post,
            new THREE.CylinderGeometry(0.06, 0.06, 2.44, 8).rotateX(Math.PI / 2),
            P(u, v, 1.22),
          );
        addGeo(post, new THREE.BoxGeometry(0.12, 7.44, 0.12), P(u, 0, 2.44));
        const ub = u + sg * 2;
        const nv = [
          [u, -3.66, 2.44],
          [u, 3.66, 2.44],
          [ub, 3.66, 1.6],
          [ub, -3.66, 1.6],
        ];
        batch.add(
          net,
          nv.map((p) => Wd(...p)),
          [
            [0, 0],
            [8, 0],
            [8, 3],
            [0, 3],
          ],
          [0, 1, 2, 0, 2, 3],
        );
        batch.add(
          net,
          [Wd(ub, -3.66, 0), Wd(ub, 3.66, 0), Wd(ub, 3.66, 1.6), Wd(ub, -3.66, 1.6)],
          [
            [0, 0],
            [8, 0],
            [8, 2],
            [0, 2],
          ],
          [0, 1, 2, 0, 2, 3],
        );
        for (const v of [-3.66, 3.66])
          batch.add(
            net,
            [Wd(u, v, 0), Wd(ub, v, 0), Wd(ub, v, 1.6), Wd(u, v, 2.44)],
            [
              [0, 0],
              [2, 0],
              [2, 2],
              [0, 3],
            ],
            [0, 1, 2, 0, 2, 3],
          );
        for (const v of [-34, 34]) {
          addGeo(
            kit.mat('#e8d84a'),
            new THREE.CylinderGeometry(0.03, 0.03, 1.5, 6).rotateX(Math.PI / 2),
            P(u, v, 0.75),
          );
          addGeo(
            kit.mat('#d23a2e', { side: THREE.DoubleSide }),
            new THREE.BoxGeometry(0.02, 0.45, 0.35),
            P(u, v + 0.22, 1.3),
          );
        }
      }
      // Dugouts and tunnel on the West Stand side.
      const vD = vWe + 1.2;
      for (const u of [-9, 9]) {
        addGeo(kit.mat('#2b3a4a'), new THREE.BoxGeometry(10, 2.2, 0.3), P(u, vD - 0.9, 0));
        addGeo(polyc, new THREE.BoxGeometry(10, 2.4, 0.1), P(u, vD, 2.2));
        addGeo(polyc, new THREE.BoxGeometry(10, 0.1, 2.2), P(u, vD - 1.15, 1.1));
        addGeo(kit.mat('#1d4fa8'), new THREE.BoxGeometry(9.6, 0.5, 0.9), P(u, vD - 0.7, 0.3));
      }
      addGeo(fasciaWhite, new THREE.BoxGeometry(4, 6, 2.6), P(0, vD - 2.0, 0));
      addGeo(boxGlass, new THREE.BoxGeometry(3, 0.1, 2.2), P(0, vD + 1.05, 0.05));
    }

    g.add(batch.toGroup('stamford_bridge'));
    return g;
  },
};
