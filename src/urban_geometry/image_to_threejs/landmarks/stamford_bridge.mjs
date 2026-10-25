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
      title: 'Matthew Harding remembered - Chelsea FC',
      url: 'https://www.chelseafc.com/en/news/article/matthew-harding-remembered---his-chelsea-timeline',
      used_for: 'North (Matthew Harding) Stand opened November 1994',
    },
  ],
  notes:
    'Stand roof heights estimated (West 31 m, East 30 m, Matthew Harding 23 m, Shed End 21 m; Overture gives 7-9 m). ' +
    'Seating rakes are single sloped planes with a glazed box band instead of separate tiers; exterior cladding and ' +
    'signage approximate; floodlights in the roof edges not modelled. The Millennium hotel (Stamford Bridge Hotel) ' +
    'footprint is left to the generic layer.',
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

    for (const s of stands) {
      const b = byId[s.id];
      if (!b) continue;
      const ring = b.polys[0][0];
      const H = s.H;
      kit.cap(batch, conc, b.polys, 0.05);
      // depth of the stand behind the seated side
      let dmax = 0;
      for (const p of ring) {
        const [u, v] = L(p);
        const lt = s.lat(u, v);
        if (lt > s.l0 + 5 && lt < s.l1 - 5) dmax = Math.max(dmax, s.dist(u, v));
      }
      const D = Math.min(Math.max(14, dmax * 0.8), 34);
      // Roof: translucent leading strip (0..9 m), opaque behind and over the corners.
      const front = 9;
      const opaque1 = clip(ring, s, true, front),
        opaque2 = clip(ring, s, false, 0.01);
      const strip = clip(ring, s, true, 0.01);
      const strip2 = strip && clip(strip, s, false, front);
      for (const r of [opaque1, opaque2]) if (r) kit.cap(batch, roofMat, [[r]], H, { scale: 6 });
      if (r2(strip2)) kit.cap(batch, polyc, [[strip2]], H - 0.3);
      // seating rake with a glazed box band two-thirds up
      const l0 = s.l0 + 1,
        l1 = s.l1 - 1;
      const zf = 1.2,
        zb = H - 5;
      const quadLat = (m, d0, z0, d1, z1, u0, u1) => {
        const pts = [at(s, l0, d0, z0), at(s, l1, d0, z0), at(s, l1, d1, z1), at(s, l0, d1, z1)];
        const flip = s.out[0] < 0 || s.out[1] > 0; // keep winding facing up / towards the pitch
        batch.add(
          m,
          flip ? pts : pts.slice().reverse(),
          flip
            ? [
                [u0, 0],
                [u1, 0],
                [u1, 1],
                [u0, 1],
              ]
            : [
                [u0, 1],
                [u1, 1],
                [u1, 0],
                [u0, 0],
              ],
          [0, 1, 2, 0, 2, 3],
        );
      };
      const span = l1 - l0;
      const dB = D * 0.62,
        zB = zf + (zb - zf) * 0.58;
      quadLat(s.name ? seatsName : seats, 2, zf, dB, zB, 0, s.name ? 1 : span / 20);
      quadLat(boxes, dB, zB, dB + 0.3, zB + 2.6, 0, 1);
      quadLat(seats, dB + 0.3, zB + 2.6, D, zb + 1.5, 0, span / 20);
      quadLat(conc, 0, 0, 2, zf, 0, 1);
      quadLat(boxes, D, zb + 1.5, D + 0.2, H - 0.4, 0, 1);
      // advertising boards along the pitch edge
      quadLat(
        kit.mat('#16324f', { emissive: new THREE.Color('#0b1d33') }),
        -0.5,
        0,
        -0.4,
        1.1,
        0,
        1,
      );
      // roof front truss
      const mid = at(s, (l0 + l1) / 2, 0.6, H - 1.1);
      const rot = s.out[0] ? A + Math.PI / 2 : A;
      addGeo(
        truss,
        new THREE.BoxGeometry(span + 2, 1.0, 1.6),
        new THREE.Matrix4().makeRotationZ(rot).setPosition(...mid),
      );
      // roof support columns at the back of the seats
      for (let k = 0; k <= 4; k++) {
        const p = at(s, l0 + (span * k) / 4, D + 0.6, 0);
        addGeo(
          truss,
          new THREE.BoxGeometry(0.8, 0.8, H),
          new THREE.Matrix4().setPosition(p[0], p[1], H / 2),
        );
      }
      // cantilever trusses over the roof (East Stand's exposed frame)
      if (s.H >= 30)
        for (let k = 0; k <= 6; k++) {
          const lt = l0 + (span * k) / 6;
          const p0 = at(s, lt, D + 4, H),
            p1 = at(s, lt, 2, H);
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          const geo = new THREE.BoxGeometry(len, 0.6, 1.8);
          addGeo(
            truss,
            geo,
            new THREE.Matrix4()
              .makeRotationZ(Math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
              .setPosition((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, H + 0.9),
          );
        }
    }
    function r2(r) {
      return r && r.length >= 3;
    }
    g.add(batch.toGroup('stamford_bridge'));
    return g;
  },
};
