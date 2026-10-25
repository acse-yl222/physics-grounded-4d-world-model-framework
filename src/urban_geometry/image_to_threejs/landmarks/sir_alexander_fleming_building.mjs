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
    'the footprint; forum length, saw-tooth count and service shaft positions are approximate. Height 23.2 m from the footprint.',
  build({ THREE, kit, buildings }) {
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
      for (let i = 0; i < 4; i++) {
        const t0 = 6 + i * 8,
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
    };
    // Positions relative to the forum frame: west and east of the forum on the north side,
    // and on the south facade. Pick t so the shafts sit on the building edges.
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
    // West and east of the forum on the north side, two on the south facade.
    shaftAt(halfW + 14, edgeT(halfW + 14, false) + 1.2);
    shaftAt(-halfW - 3, edgeT(-halfW - 3, false) + 1.2);
    shaftAt(halfW + 22, edgeT(halfW + 22, true) - 1.2);
    shaftAt(halfW + 52, edgeT(halfW + 52, true) - 1.2);
    // Rooftop plant enclosure over the west lab wing.
    {
      const p = F(halfW + 50, (edgeT(halfW + 50, false) + edgeT(halfW + 50, true)) / 2, 0);
      kit.box(batch, kit.mat('#b4b8b8'), p[0], p[1], H, 16, 12, 3, ang);
    }
    g.add(batch.toGroup('sir_alexander_fleming_building'));
    return g;
  },
};
