// Sir Alexander Fleming Building, Imperial College South Kensington (Foster and
// Partners, 1994-98, opened by the Queen October 1998). Medical-school and biology
// laboratories wrapped around a multi-level "research forum" that forms the hub of
// circulation; the forum is fully glazed at its northern end, the site's only open
// aspect, looking onto Imperial College Road, Queen's Lawn and Queen's Tower, and is
// lit by sculpted saw-tooth rooflights (north light plus controlled sun). Service
// shafts stand along the main facades.
export default {
  id: 'sir_alexander_fleming_building',
  name: 'Sir Alexander Fleming Building',
  claims: ['858f0054-96ac-4038-81cb-964a28cdf4cc'],
  references: [
    {
      title: 'Imperial College Sir Alexander Fleming Building - Foster + Partners',
      url: 'https://www.fosterandpartners.com/projects/imperial-college-sir-alexander-fleming-building',
      used_for:
        "forum on five levels, labs wrapped around it, glazed north end onto Queen's Lawn, sculpted rooflights",
    },
    {
      title:
        'Sir Alexander Fleming Building, Imperial College - Design Build Technology (Braun/Groemling)',
      url: 'https://bdt.degruyter.com/?p=19080',
      used_for: 'saw-tooth roof with north light; service shafts along main facades; 1994-98',
    },
    {
      title: 'The Sir Alexander Fleming Building, Imperial College - Building Design',
      url: 'https://bdonline.co.uk/the-sir-alexander-fleming-building-imperial-college/2155.article',
      used_for: 'six-storey glazed atrium',
    },
    {
      title: 'Buildings and Centres: One - Imperial College video archive',
      url: 'https://blogs.imperial.ac.uk/videoarchive/buildings-and-centres-one/',
      used_for: 'opening by the Queen, 21 October 1998',
    },
  ],
  notes:
    'Cladding material of the lab elevations was not found in the sources; modelled as pale grey metal panels ' +
    'with ribbon glazing and sun-shading blades. The glazed forum end is placed on the projecting north bay of ' +
    'the footprint; forum length, saw-tooth count and service shaft positions are approximate. Height 23.2 m from the footprint. ' +
    'Sun-shading blades over every window band, the mullion module (1.8 m), glazing bars, shaft grilles, ' +
    'entrance doors/steps/sign and the cycle stands are indicative.',
  build({ THREE, kit, buildings, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0];
    const H = 23.2;

    const labs = kit.paintedMaterial('sir_alexander_fleming_building:labs', 512, 512, (c, w, h) => {
      c.fillStyle = '#d3d6d6';
      c.fillRect(0, 0, w, h);
      const sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        const wy = y0 + sh * 0.12,
          wh = sh * 0.5;
        const gr = c.createLinearGradient(0, wy, 0, wy + wh);
        gr.addColorStop(0, '#6f8796');
        gr.addColorStop(1, '#2f3f4a');
        c.fillStyle = gr;
        c.fillRect(0, wy, w, wh);
        c.fillStyle = '#aeb4b7';
        for (let k = 0; k <= 8; k++) c.fillRect((k * w) / 8 - 2, wy, 4, wh);
        // sun-shading blade above window
        c.fillStyle = '#f0f1f0';
        c.fillRect(0, wy - 8, w, 8);
        c.fillStyle = '#8f9597';
        c.fillRect(0, wy, w, 4);
        // panel joints
        c.fillStyle = '#b9bdbe';
        for (let k = 0; k <= 4; k++) c.fillRect((k * w) / 4 - 1, wy + wh, 2, sh - wh - sh * 0.12);
        c.fillRect(0, wy + wh + (sh - wh) * 0.45, w, 2);
      }
    });
    const forumGlass = kit.paintedMaterial(
      'sir_alexander_fleming_building:forum',
      512,
      512,
      (c, w, h) => {
        const gr = c.createLinearGradient(0, 0, 0, h);
        gr.addColorStop(0, '#a9c0cc');
        gr.addColorStop(1, '#4d6878');
        c.fillStyle = gr;
        c.fillRect(0, 0, w, h);
        // visible floor edges of the forum galleries
        c.fillStyle = 'rgba(235,235,228,0.85)';
        for (let k = 0; k < 2; k++) c.fillRect(0, (k * h) / 2 + h * 0.4, w, 10);
        c.fillStyle = '#e4e7e8';
        for (let k = 0; k <= 4; k++) c.fillRect((k * w) / 4 - 4, 0, 8, h);
        for (let k = 0; k <= 4; k++) c.fillRect(0, (k * h) / 4 - 2, w, 4);
      },
      { roughness: 0.1, metalness: 0.3 },
    );
    const panel = kit.mat('#d3d6d6');
    const shaft = kit.mat('#bfc3c3');
    const roofMat = kit.mat('#9a9b98');
    const sky = kit.mat('#8fb3c6', { roughness: 0.1, metalness: 0.3 });
    const white = kit.mat('#eff0ee');

    // Identify the glazed forum end: the longest edge on the northernmost side.
    let fe = null;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 8) continue;
      const my = (a[1] + b[1]) / 2;
      if (!fe || my > fe.my) fe = { k, a, b, len, my };
    }
    // Walls: forum edge (and the short returns either side) glazed, others lab facade.
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      const n = ring.length;
      const glazed = k === fe.k || ((k === (fe.k + 1) % n || k === (fe.k - 1 + n) % n) && len < 6);
      const m = glazed ? forumGlass : labs;
      const uL = glazed ? len / 8 : Math.max(Math.round(len / 3.6), 1) / 4;
      const vs = glazed ? 8 : 6.6;
      batch.quad(
        m,
        [a[0], a[1], 0],
        [b[0], b[1], 0],
        [b[0], b[1], H],
        [a[0], a[1], H],
        [0, 0],
        [uL, 0],
        [uL, H / vs],
        [0, H / vs],
      );
    }
    // Parapet and roof.
    kit.walls(batch, panel, [[kit.offsetRing(ring, 0.2)]], H, H + 1.0);
    kit.cap(batch, roofMat, [[ring]], H + 0.6);
    // Ground-floor dark recess band.
    kit.walls(batch, kit.mat('#2b363d'), [[kit.offsetRing(ring, 0.05)]], 0, 0.6);

    // Forum frame: s along the glazed edge, t inward (south).
    const ex = (fe.b[0] - fe.a[0]) / fe.len,
      ey = (fe.b[1] - fe.a[1]) / fe.len;
    const nx = ey,
      ny = -ex; // outward
    const mx = (fe.a[0] + fe.b[0]) / 2,
      my = (fe.a[1] + fe.b[1]) / 2;
    const F = (s, t, z) => [mx + ex * s - nx * t, my + ey * s - ny * t, z];
    const halfW = fe.len / 2;
    // t of the building edge crossed by the line s = const (min = north side, max = south side).
    const edgeT = (sv, south) => {
      let best = null;
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const sa = (a[0] - mx) * ex + (a[1] - my) * ey,
          sb = (b[0] - mx) * ex + (b[1] - my) * ey;
        if ((sa - sv) * (sb - sv) > 0 || sa === sb) continue;
        const f = (sv - sa) / (sb - sa);
        const px = a[0] + (b[0] - a[0]) * f,
          py = a[1] + (b[1] - a[1]) * f;
        const t = -((px - mx) * nx + (py - my) * ny);
        if (best === null || (south ? t > best : t < best)) best = t;
      }
      return best ?? 0;
    };
    // Glazed end: projecting fins / mullion frame and a canopy at the entrance.
    for (let s = -halfW; s <= halfW + 0.01; s += fe.len / 4) {
      const p = F(s, -0.35, 0);
      kit.box(batch, white, p[0], p[1], 0, 0.3, 0.7, H + 1, Math.atan2(ey, ex));
    }
    {
      const p = F(0, -2, 0);
      kit.box(batch, white, p[0], p[1], 3.8, fe.len - 1, 4, 0.35, Math.atan2(ey, ex));
    }
    // Saw-tooth rooflights over the forum: glazed north faces, solid sloping backs.
    const TL = 6.5,
      rise = 3.2,
      teeth = 6;
    for (let i = 0; i < teeth; i++) {
      const t0 = 1 + i * TL,
        t1 = t0 + TL;
      const z0 = H + 0.6,
        z1 = H + rise;
      const s0 = -halfW + 0.8,
        s1 = halfW - 0.8;
      // north-facing glass (vertical)
      batch.quad(
        sky,
        F(s0, t0, z0),
        F(s1, t0, z0),
        F(s1, t0, z1),
        F(s0, t0, z1),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      // glazing bars on the north light
      for (let sv = s0 + 1.5; sv < s1; sv += 1.5) {
        const q = F(sv, t0 - 0.05, 0);
        kit.box(
          batch,
          kit.mat('#9ea5a8', { roughness: 0.4, metalness: 0.4 }),
          q[0],
          q[1],
          z0,
          0.08,
          0.12,
          z1 - z0,
          Math.atan2(ey, ex),
        );
      }
      {
        const q = F((s0 + s1) / 2, t0 - 0.05, 0);
        kit.box(
          batch,
          kit.mat('#9ea5a8', { roughness: 0.4, metalness: 0.4 }),
          q[0],
          q[1],
          (z0 + z1) / 2,
          s1 - s0,
          0.1,
          0.08,
          Math.atan2(ey, ex),
        );
      }
      // sloping back
      batch.quad(
        white,
        F(s0, t0, z1),
        F(s1, t0, z1),
        F(s1, t1, z0),
        F(s0, t1, z0),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      // side triangles
      batch.add(
        white,
        [F(s0, t1, z0), F(s0, t0, z0), F(s0, t0, z1)],
        [
          [0, 0],
          [1, 0],
          [0, 1],
        ],
        [0, 1, 2],
      );
      batch.add(
        white,
        [F(s1, t0, z0), F(s1, t1, z0), F(s1, t0, z1)],
        [
          [0, 0],
          [1, 0],
          [0, 1],
        ],
        [0, 1, 2],
      );
    }
    // Lab-wing rooflight strips parallel to the forum (lower, also north-lit).
    for (const s of [halfW + 12, halfW + 34]) {
      const tN = edgeT(s, false),
        tS = edgeT(s, true);
      for (let i = 0; i < 4; i++) {
        const t0 = tN + 3 + i * ((tS - tN - 8) / 4),
          t1 = t0 + 5;
        const z0 = H + 0.6,
          z1 = H + 1.6;
        const s0 = s - 3,
          s1 = s + 3;
        batch.quad(
          sky,
          F(s0, t0, z0),
          F(s1, t0, z0),
          F(s1, t0, z1),
          F(s0, t0, z1),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.quad(
          panel,
          F(s0, t0, z1),
          F(s1, t0, z1),
          F(s1, t1, z0),
          F(s0, t1, z0),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.add(
          panel,
          [F(s0, t1, z0), F(s0, t0, z0), F(s0, t0, z1)],
          [
            [0, 0],
            [1, 0],
            [0, 1],
          ],
          [0, 1, 2],
        );
        batch.add(
          panel,
          [F(s1, t0, z0), F(s1, t1, z0), F(s1, t0, z1)],
          [
            [0, 0],
            [1, 0],
            [0, 1],
          ],
          [0, 1, 2],
        );
      }
    }
    // Service shafts along the long north and south facades, rising above the roof.
    const ang = Math.atan2(ey, ex);
    const shaftAt = (s, t) => {
      const p = F(s, t, 0);
      kit.box(batch, shaft, p[0], p[1], 0, 4.2, 4.2, H + 3.2, ang);
      kit.box(batch, kit.mat('#7d8486'), p[0], p[1], H + 1.6, 4.3, 4.3, 1.2, ang); // louvre band
      for (let z = H + 1.7; z < H + 2.8; z += 0.22)
        kit.box(batch, shaft, p[0], p[1], z, 4.36, 4.36, 0.06, ang);
      // panel joints and a grille band at every floor
      for (let z = 3.3; z < H; z += 3.3)
        kit.box(batch, kit.mat('#aeb2b2'), p[0], p[1], z - 0.06, 4.26, 4.26, 0.12, ang);
      for (const [cu, cv] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ]) {
        const q = [
          p[0] + (cu * Math.cos(ang) - cv * Math.sin(ang)) * 2.1,
          p[1] + (cu * Math.sin(ang) + cv * Math.cos(ang)) * 2.1,
        ];
        kit.box(batch, kit.mat('#aeb2b2'), q[0], q[1], 0, 0.2, 0.2, H + 3.2, ang);
      }
      kit.box(batch, kit.mat('#eff0ee'), p[0], p[1], H + 3.2, 4.6, 4.6, 0.2, ang);
    };
    // Positions relative to the forum frame: west and east of the forum on the north side,
    // and on the south facade. Pick t so the shafts sit on the building edges.
    // West and east of the forum on the north side, two on the south facade.
    shaftAt(halfW + 14, edgeT(halfW + 14, false) + 1.2);
    shaftAt(-halfW - 3, edgeT(-halfW - 3, false) + 1.2);
    shaftAt(halfW + 22, edgeT(halfW + 22, true) - 1.2);
    shaftAt(halfW + 52, edgeT(halfW + 52, true) - 1.2);
    // Rooftop plant enclosure over the west lab wing.
    {
      const p = F(halfW + 50, (edgeT(halfW + 50, false) + edgeT(halfW + 50, true)) / 2, 0);
      kit.box(batch, kit.mat('#b4b8b8'), p[0], p[1], H, 16, 12, 3, ang);
      for (let z = H + 0.9; z < H + 2.8; z += 0.25)
        kit.box(batch, kit.mat('#8d9293'), p[0], p[1], z, 16.06, 12.06, 0.06, ang);
      kit.box(batch, kit.mat('#eff0ee'), p[0], p[1], H + 3, 16.3, 12.3, 0.2, ang);
    }
    // Lab elevations: horizontal sun-shading blades over each window band and slim
    // mullions; the forum glazing gets proud transoms and intermediate mullions.
    const blade = kit.mat('#eceeed', { roughness: 0.5 });
    const mullion = kit.mat('#9ea5a8', { roughness: 0.4, metalness: 0.4 });
    const ST = 3.3;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 2) continue;
      const n = ring.length;
      const glazed = k === fe.k || ((k === (fe.k + 1) % n || k === (fe.k - 1 + n) % n) && len < 6);
      const dx = (b[0] - a[0]) / len,
        dy = (b[1] - a[1]) / len,
        ox = dy,
        oy = -dx;
      const an = Math.atan2(dy, dx);
      const at2 = (t, o) => [a[0] + dx * t + ox * o, a[1] + dy * t + oy * o];
      if (glazed) {
        for (let z = 2; z < H; z += 2) {
          const [x, y] = at2(len / 2, 0.06);
          kit.box(batch, mullion, x, y, z - 0.04, len, 0.12, 0.08, an);
        }
        for (let t = 1; t < len; t += 1) {
          const [x, y] = at2(t, 0.05);
          kit.box(batch, mullion, x, y, 0, 0.06, 0.1, H, an);
        }
        continue;
      }
      const m = Math.max(Math.round(len / 3.6), 1) * 2;
      for (let st = 0; st < 7; st++) {
        const z = st * ST;
        const [x, y] = at2(len / 2, 0.38);
        kit.box(batch, blade, x, y, z + 2.95, len, 0.75, 0.07, an);
        for (let i = 0; i <= m; i++) {
          const [mx2, my2] = at2((len * i) / m, 0.04);
          kit.box(batch, mullion, mx2, my2, z + 1.25, 0.07, 0.1, 1.65, an);
        }
      }
    }
    // Roof-edge safety rail.
    const railR = kit.offsetRing(ring, -0.7);
    kit.balustrade(
      batch,
      kit.mat('#9aa0a3', { metalness: 0.5, roughness: 0.4 }),
      [...railR, railR[0]],
      H + 0.6,
      {
        height: 1.1,
        spacing: 2.0,
      },
    );
    // Forum entrance on Imperial College Road / Queen's Lawn side: glazed doors, steps, sign.
    const fAng = Math.atan2(ey, ex);
    const signM = kit.paintedMaterial(
      'sir_alexander_fleming_building:sign',
      1024,
      96,
      (c, w, h) => {
        c.fillStyle = '#f0f1f0';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#003e74';
        c.font = 'bold 52px sans-serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText('Sir Alexander Fleming Building', w / 2, h / 2 + 3);
      },
    );
    {
      const p0 = F(-halfW + 0.8, -4.05, 0),
        p1 = F(halfW - 0.8, -4.05, 0);
      // fascia faces outward: travel so the outside is on the right (reverse of the s axis)
      batch.quad(
        signM,
        [p1[0], p1[1], 3.85],
        [p0[0], p0[1], 3.85],
        [p0[0], p0[1], 4.4],
        [p1[0], p1[1], 4.4],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      for (const sv of [-3, 0, 3]) {
        const q = F(sv, -0.15, 0);
        kit.box(batch, kit.mat('dark_glass'), q[0], q[1], 0, 2.6, 0.08, 3.0, fAng);
        kit.box(batch, mullion, q[0], q[1], 3.0, 2.8, 0.12, 0.1, fAng);
      }
      for (let st = 0; st < 3; st++) {
        const q = F(0, -4.6 - st * 0.0, 0);
        kit.box(
          batch,
          kit.mat('#c9c4b8'),
          q[0],
          q[1],
          0,
          fe.len - 1 - st * 0.0,
          3.0 - st * 0.9,
          0.15 * (st + 1),
          fAng,
        );
      }
    }
    g.add(batch.toGroup('sir_alexander_fleming_building'));
    const benches = [F(-halfW - 3, -7, 0), F(halfW + 3, -7, 0)].map((p) => [p[0], p[1], fAng]);
    g.add(placeAssets('bench', benches));
    const stands = [];
    for (let i = 0; i < 6; i++) {
      const p = F(halfW + 6 + i * 1.1, -3.0, 0);
      stands.push([p[0], p[1], fAng + Math.PI / 2]);
    }
    g.add(placeAssets('bicycle_stand', stands));
    return g;
  },
};
