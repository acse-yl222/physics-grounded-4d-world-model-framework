// Natural History Museum, South Kensington (Alfred Waterhouse, 1873-1881) with the
// Darwin Centre (C.F. Moller, 2009) and the Earth Galleries / Red Zone (former
// Geological Museum, Allison & Markham, 1935).
//
// Waterhouse building: symmetrical Romanesque front of buff and blue-grey banded
// terracotta on Cromwell Road, ~207 m long, 27 bays; a three-bay centrepiece set
// forward with the great round-arched entrance of receding orders between two spired
// towers (~58 m); wings with square-headed basement and ground-floor windows and
// round-headed first-floor windows, each holding coupled round-headed lights, between
// banded buttress piers; end pavilions with octagonal corner turrets and steep
// pavilion roofs; pitched slate roofs; behind the front the cathedral-like Hintze Hall
// with its long glazed roof and top-lit gallery wings. Darwin Centre: an eight-storey
// white "cocoon" inside a glass box. Earth Galleries: stripped-classical Portland
// stone block on Exhibition Road with a glazed atrium, linked north to the Science
// Museum by a bridge over an arched gateway. In front: lawns, the raised entrance
// terrace with its long flight of steps, and Waterhouse's railings on octagonal
// Portland stone piers along Cromwell Road with lantern-topped gate piers.
//
// Everything is built in a local frame aligned with the Cromwell Road front
// (u east along the front, v north), origin at the centre of the main entrance.
const O = [1668, -1167],
  ANG = 0.1247;

export default {
  id: 'natural_history_museum',
  name: 'Natural History Museum',
  claims: [
    '879ff4e2-4778-4c8b-8535-f252df2bc0b1', // Natural History Museum (Waterhouse + Earth Galleries)
    'f26c3834-e72f-4603-8dd1-28315210b0db', // Darwin Centre
    '9e33528c-5619-48da-85c7-6fd332e30473', // Lodge (Queen's Gate side)
    '5f2a364a-3a51-4fd6-b40a-799f15fbff37', // bridge over the gateway to the Science Museum
  ],
  references: [
    {
      title: 'Natural History Museum, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Natural_History_Museum,_London',
      used_for:
        'Waterhouse, Romanesque terracotta building, buff and blue-grey terracotta, Gibbs and Canning tiles',
    },
    {
      title: 'Listed Buildings Search (RBKC) - Natural History Museum',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=203737',
      used_for:
        'listing: 27 bays, buff and grey terracotta, pitched slated roof, projecting three-bay centrepiece with two spired towers, end bays with octagonal towers and steep pavilion roofs, square-headed basement and ground floor and round-headed first floor windows with coupled subsidiary round-headed lights, animal figures on first-floor sills',
    },
    {
      title: 'Natural History Museum London, England (GoHistoric listing mirror)',
      url: 'https://gohistoric.com/places/249431-natural-history-museum-london/listed',
      used_for: 'listing text cross-check (bays, storeys, window heads)',
    },
    {
      title:
        'Natural History Museum, Front Lodge and Gates, Gatepiers and Railings (Historic England)',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1080675',
      used_for: 'gates, piers and railings by Waterhouse erected by 1881',
    },
    {
      title: 'Gates, Gatepiers and Railings to Natural History Museum (GoHistoric)',
      url: 'https://gohistoric.com/places/652730-gates-gatepiers-railings-natural-history-museum-london/listed',
      used_for:
        'Portland stone piers of octagonal section carrying wrought-iron railings; larger square Cromwell Road gate piers topped by lanterns; openwork wrought-iron centre piers with gilded lions',
    },
    {
      title: 'Natural History Museum - Gardenvisit (London and its environs, 1927)',
      url: 'https://www.gardenvisit.com/book/london_and_its_environs_1927/41_the_natural_history_museum/natural_history_museum',
      used_for: 'central block with two towers 192 ft high, wings ending in pavilions',
    },
    {
      title: 'Natural History Museum - TripExpert',
      url: 'https://www.tripexpert.com/london/attractions/natural-history-museum',
      used_for: 'central towers 58 m over the arched entrance',
    },
    {
      title: 'Natural History Museum (Bluffton University architecture notes)',
      url: 'https://homepages.bluffton.edu/~sullivanm/england/london/scimuseum/waterhouse.html',
      used_for: 'terracotta in yellowish brown with bands of bluish grey',
    },
    {
      title: 'Alfred Waterhouse: museum building, cathedral to nature (NHM)',
      url: 'https://www.nhm.ac.uk/discover/alfred-waterhouse-museum-building-cathedral-to-nature.html',
      used_for: 'terracotta over iron and steel frame, cathedral-like Hintze Hall',
    },
    {
      title: '1880 - Natural History Museum, Kensington, London (Archiseek)',
      url: 'https://www.archiseek.com/?p=3558',
      used_for: 'terracotta supplied by Gibbs and Canning of Tamworth',
    },
    {
      title: 'Darwin Centre - architravel',
      url: 'https://architravel.com/project/darwin-centre',
      used_for: 'eight-storey concrete cocoon inside a glass atrium (C.F. Moller)',
    },
    {
      title: "Danish cocoon completed for London's insects - C.F. Moller",
      url: 'https://www.cfmoller.com/g/Danish-cocoon-completed-for-Londons-insects-i12627.html',
      used_for: 'cocoon form, completion 2008/2009',
    },
    {
      title: 'Geological Museum - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Geological_Museum',
      used_for:
        'Allison and Markham building on Exhibition Road (1935), now the Red Zone / Earth Galleries',
    },
    {
      title: 'Nature (1935) on the new Geological Museum',
      url: 'https://www.nature.com/articles/1351060a0',
      used_for: 'linked to the Science Museum by corridors over an arched gateway',
    },
  ],
  notes:
    'Footprint from Overture (front measured 207 m). Heights are estimates from descriptions: towers 58 m (192 ft), ' +
    'front eaves 19 m, pavilions 24 m + steep roofs, Hintze Hall ridge 34 m; the Overture h (13.7 m) is inferred and ' +
    'ignored. The Cromwell Road front (wings, pavilions, centrepiece, towers) is real geometry: wall slabs with ' +
    'through openings and reveals, plate-tracery panels with coupled round-headed lights, colonnettes, banded ' +
    'voussoirs, banded buttress piers, string courses and corbel tables; the receding orders of the portal and the ' +
    'rose window are modelled; terracotta animal figures and foliage carving are omitted. Bay rhythm (10 bays per ' +
    'wing, 2 per pavilion face) and opening sizes are estimated from the listing and general views, not drawings. ' +
    'Entrance terrace raised 2.4 m over the forecourt (steps from the mapped OSM steps line). Plan behind the front ' +
    '(gallery wings, light courts, north range) is schematic and painted. Darwin Centre height (28 m) assumed from its ' +
    'eight storeys; Earth Galleries height (22 m + attic) and window grid estimated. Railing, pier spacing and gate ' +
    'positions follow the mapped fence lines; lion and lantern finials are simplified.',

  build({ THREE, kit, placeAssets }) {
    const outer = new THREE.Group();
    const root = new THREE.Group();
    root.position.set(O[0], O[1], 0);
    root.rotation.z = ANG;
    outer.add(root);
    const B = new kit.MeshBatch();

    // ---------- palette ----------
    const BUFF = '#d6c096',
      BUFF_D = '#c4ab80',
      BLUE = '#838f9b',
      BLUE_D = '#5f6b75',
      WIN = '#2a3036';
    const buff = kit.mat(BUFF, { roughness: 0.8 }),
      buffD = kit.mat(BUFF_D, { roughness: 0.8 }),
      buffL = kit.mat('#dfcca5', { roughness: 0.8 }),
      blue = kit.mat(BLUE, { roughness: 0.8 }),
      blueD = kit.mat(BLUE_D, { roughness: 0.8 }),
      slateMat = kit.roof('slate', 1),
      slate = kit.mat('#4e555d', { roughness: 0.75 }),
      glass = kit.mat('glass'),
      darkGlass = kit.mat('dark_glass'),
      winGlass = kit.mat('#2b3239', { roughness: 0.2, metalness: 0.3 }),
      bar = kit.mat('#4b4f4c', { roughness: 0.6 }),
      iron = kit.mat('dark_steel'),
      railIron = kit.mat('#23272a', { roughness: 0.55, metalness: 0.5 }),
      gold = kit.mat('gold'),
      lead = kit.mat('lead'),
      stone = kit.mat('portland_stone'),
      stoneD = kit.mat('#cbc3ae'),
      paving = kit.mat('paving'),
      timber = kit.mat('#5a4126', { roughness: 0.7 }),
      white = kit.mat('#efebe2', { roughness: 0.7 }),
      clearGlass = kit.mat('#9fb8c4', {
        roughness: 0.1,
        metalness: 0.2,
        transparent: true,
        opacity: 0.38,
      });

    // ---------- canvas helpers ----------
    const archPath = (g, x, yTop, w, yBot) => {
      g.beginPath();
      g.moveTo(x, yBot);
      g.lineTo(x, yTop + w / 2);
      g.arc(x + w / 2, yTop + w / 2, w / 2, Math.PI, 0);
      g.lineTo(x + w, yBot);
      g.closePath();
    };
    const fillArch = (g, x, yTop, w, yBot, col) => {
      archPath(g, x, yTop, w, yBot);
      g.fillStyle = col;
      g.fill();
    };
    const bandedArch = (g, x, yTop, w, yBot, ring, col = WIN) => {
      const cx = x + w / 2,
        cy = yTop + w / 2;
      const n = 11;
      for (let k = 0; k < n; k++) {
        g.beginPath();
        g.arc(cx, cy, w / 2 + ring, Math.PI + (k * Math.PI) / n, Math.PI + ((k + 1) * Math.PI) / n);
        g.arc(cx, cy, w / 2, Math.PI + ((k + 1) * Math.PI) / n, Math.PI + (k * Math.PI) / n, true);
        g.closePath();
        g.fillStyle = k % 2 ? BLUE : BUFF_D;
        g.fill();
      }
      fillArch(g, x, yTop, w, yBot, col);
    };
    const stripes = (g, w, y0, y1, step, thick) => {
      g.fillStyle = BLUE;
      for (let y = y1; y > y0; y -= step) g.fillRect(0, y - thick, w, thick);
    };

    // Banded terracotta for the modelled front walls: UV u = metres / 1.2 along the
    // wall, v = height / 25.6 m. Plinth, dense blue-grey courses on the lower storeys,
    // sparser above, fine block joints.
    const ZT = 25.6;
    const front3d = kit.paintedMaterial('nhm:front3d', 64, 1024, (g, W, Hp) => {
      const s = Hp / ZT,
        Y = (z) => Hp - z * s;
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      const r = kit.rng(0.733);
      for (let y = 0; y < Hp; y += 6)
        for (let x = 0; x < W; x += 16) {
          g.fillStyle = `rgba(${r() < 0.5 ? '120,100,70' : '250,240,215'},${0.05 + r() * 0.06})`;
          g.fillRect(x, y, 16, 6);
        }
      g.fillStyle = 'rgba(110,95,70,0.35)';
      for (let z = 0; z < ZT; z += 0.31) g.fillRect(0, Y(z), W, 1);
      for (let y = 0; y < Hp; y += 12) g.fillRect(((y / 12) % 2) * 32, y, 1, 12);
      stripes(g, W, Y(7.6), Y(1.0), 0.62 * s, 0.22 * s);
      stripes(g, W, Y(ZT), Y(7.6), 1.25 * s, 0.18 * s);
      g.fillStyle = BLUE_D;
      g.fillRect(0, Y(1.0), W, 1.0 * s);
    });

    // Plain banded terracotta for blind gallery walls, courts and backs.
    const bandMat = kit.paintedMaterial('nhm:bands', 128, 256, (g, W, Hp) => {
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      g.fillStyle = BLUE;
      for (let y = 0; y < Hp; y += 32) g.fillRect(0, y, W, 9);
      g.fillStyle = WIN;
      fillArch(g, 48, 40, 32, 110, WIN);
    });
    // Back elevation: banded with windows in two rows.
    const backMat = kit.paintedMaterial('nhm:back', 128, 256, (g, W, Hp) => {
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      g.fillStyle = BLUE;
      for (let y = 0; y < Hp; y += 22) g.fillRect(0, y, W, 6);
      fillArch(g, 40, 30, 48, 100, WIN);
      fillArch(g, 40, 140, 48, 220, WIN);
    });
    // Painted pavilion bay (inner side faces of the pavilions).
    const pavMat = kit.paintedMaterial('nhm:pavilion', 256, 888, (g, W, Hp) => {
      const Hm = 24,
        s = Hp / Hm,
        Y = (z) => Hp - z * s,
        X = (m) => m * (W / 7);
      g.fillStyle = BUFF;
      g.fillRect(0, 0, W, Hp);
      stripes(g, W, Y(7.5), Y(0), 0.62 * s, 0.22 * s);
      stripes(g, W, Y(Hm), Y(7.5), 1.25 * s, 0.18 * s);
      g.fillStyle = BLUE_D;
      g.fillRect(0, Y(1.0), W, 1.0 * s);
      g.fillStyle = WIN;
      g.fillRect(X(1.6), Y(6.4), X(3.8), 3.6 * s);
      bandedArch(g, X(1.5), Y(13.4), X(4.0), Y(8.1), X(0.4), WIN);
      bandedArch(g, X(1.9), Y(19.0), X(3.2), Y(15.0), X(0.3), WIN);
      for (let k = 0; k < 3; k++) fillArch(g, X(1.3 + k * 1.6), Y(22.3), X(1.0), Y(20.3), WIN);
    });

    // ---------- geometry helpers ----------
    const R = (u0, v0, u1, v1) => [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ];
    /** Walls of a CCW ring with one texture tile per `bayW` metres; `skip` lists edges left out. */
    const texWalls = (m, ring, z0, z1, bayW, vr = [0, 1], skip = []) => {
      for (let k = 0; k < ring.length; k++) {
        if (skip.includes(k)) continue;
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 0.05) continue;
        const n = Math.max(1, Math.round(len / bayW));
        B.quad(
          m,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [b[0], b[1], z1],
          [a[0], a[1], z1],
          [0, vr[0]],
          [n, vr[0]],
          [n, vr[1]],
          [0, vr[1]],
        );
      }
    };
    const flat = (m, ring, z, down = false) => kit.cap(B, m, [[ring]], z, { down });
    const box = (m, u, v, z0, w, d, h, a = 0) => kit.box(B, m, u, v, z0, w, d, h, a);
    const geo = (m, g, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1) => {
      const M = new THREE.Matrix4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, rz)),
        new THREE.Vector3(sx, sy, sz),
      );
      B.addGeometry(m, g, M);
      g.dispose();
    };
    const pyramid = (m, u, v, z0, w, d, h) => {
      const g = new THREE.ConeGeometry(Math.SQRT1_2, 1, 4, 1, true)
        .rotateX(Math.PI / 2)
        .rotateZ(Math.PI / 4);
      geo(m, g, u, v, z0 + h / 2, 0, w, d, h);
    };
    const octagon = (m, u, v, z0, r, h, rTop = r, open = false) => {
      const g = new THREE.CylinderGeometry(rTop, r, h, 8, 1, open).rotateX(Math.PI / 2);
      geo(m, g, u, v, z0 + h / 2, Math.PI / 8);
    };
    const roof = (
      ring,
      angle,
      eave,
      rise,
      kind = 'gabled',
      m = slateMat,
      wall = bandMat,
      overhang = 0.4,
    ) => kit.pitchedRoof(B, m, wall, ring, angle, eave, rise, kind, { overhang });
    const slopeStripU = (m, v0, v1, uEave, uRidge, zE, zR, f0, f1, lift = 0.06) => {
      const P = (v, f) => [uEave + (uRidge - uEave) * f, v, zE + (zR - zE) * f + lift];
      const pts = [P(v0, f0), P(v1, f0), P(v1, f1), P(v0, f1)];
      if (uRidge > uEave) pts.reverse();
      B.add(
        m,
        pts,
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    };
    const cresting = (u0, v0, u1, v1, z) => {
      const len = Math.hypot(u1 - u0, v1 - v0),
        a = Math.atan2(v1 - v0, u1 - u0);
      box(iron, (u0 + u1) / 2, (v0 + v1) / 2, z, len, 0.12, 0.9, a);
      for (let t = 0; t <= len; t += 1.6)
        box(iron, u0 + ((u1 - u0) * t) / len, v0 + ((v1 - v0) * t) / len, z, 0.12, 0.12, 1.4, a);
    };

    // --- wall-plane frame: edge a -> b (outward normal on the right), s along the
    // edge, w outward from the edge line, z up. Shape coordinates are (s, z).
    const EF = (a, b) => {
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        L = Math.hypot(dx, dy),
        ux = dx / L,
        uy = dy / L;
      const M = (w = 0) =>
        new THREE.Matrix4().set(
          ux,
          0,
          uy,
          a[0] + uy * w,
          uy,
          0,
          -ux,
          a[1] - ux * w,
          0,
          1,
          0,
          0,
          0,
          0,
          0,
          1,
        );
      const P = (s, w) => [a[0] + ux * s + uy * w, a[1] + uy * s - ux * w];
      return { L, ux, uy, ang: Math.atan2(dy, dx), M, P };
    };
    /** Opening spec -> path: rect {k:'r',s,w,z0,z1}, arch {k:'a',s,w,z0,zs}, circle {k:'c',s,z,r}. */
    const drawSpec = (p, h, grow = 0) => {
      if (h.k === 'c') {
        p.absarc(h.s, h.z, h.r + grow, 0, Math.PI * 2, false);
        return p;
      }
      const w = h.w / 2 + grow,
        z0 = h.z0 - grow;
      p.moveTo(h.s - w, z0);
      p.lineTo(h.s + w, z0);
      if (h.k === 'r') {
        p.lineTo(h.s + w, h.z1 + grow);
        p.lineTo(h.s - w, h.z1 + grow);
      } else {
        p.lineTo(h.s + w, h.zs);
        p.absarc(h.s, h.zs, w, 0, Math.PI, false);
      }
      p.closePath();
      return p;
    };
    /** Add an ExtrudeGeometry, caps with capMat (UV scaled by su, sv) and sides with sideMat. */
    const addSplit = (g, M, capMat, sideMat, su = 1, sv = 1) => {
      const pos = g.attributes.position.array,
        uv = g.attributes.uv.array;
      const groups = g.groups.length
        ? g.groups
        : [{ start: 0, count: pos.length / 3, materialIndex: 0 }];
      for (const gr of groups) {
        const m = gr.materialIndex === 0 ? capMat : sideMat;
        if (!m || !gr.count) continue;
        const sub = new THREE.BufferGeometry();
        sub.setAttribute(
          'position',
          new THREE.Float32BufferAttribute(pos.slice(gr.start * 3, (gr.start + gr.count) * 3), 3),
        );
        const u = uv.slice(gr.start * 2, (gr.start + gr.count) * 2);
        for (let i = 0; i < u.length; i += 2) {
          u[i] *= su;
          u[i + 1] *= sv;
        }
        sub.setAttribute('uv', new THREE.Float32BufferAttribute(u, 2));
        B.addGeometry(m, sub, M);
        sub.dispose();
      }
      g.dispose();
    };
    /** Wall slab on edge frame f with openings, from w0 outward by depth. */
    const slab = (f, outline, holes, depth, capMat, sideMat, o = {}) => {
      const sh = new THREE.Shape();
      outline(sh, f.L);
      for (const h of holes) sh.holes.push(drawSpec(new THREE.Path(), h));
      const g = new THREE.ExtrudeGeometry(sh, {
        depth,
        bevelEnabled: false,
        curveSegments: o.seg ?? 5,
      });
      addSplit(g, f.M(o.w0 ?? 0), capMat, sideMat, o.su ?? 1, o.sv ?? 1);
    };
    const rectOutline =
      (z0, z1, s0 = 0, s1 = null) =>
      (sh, L) => {
        const e = s1 ?? L;
        sh.moveTo(s0, z0);
        sh.lineTo(e, z0);
        sh.lineTo(e, z1);
        sh.lineTo(s0, z1);
        sh.closePath();
      };
    const specOutline = (h, grow) => (sh) => drawSpec(sh, h, grow);
    /** Box in an edge frame. */
    const eb = (f, m, s0, s1, w0, w1, z0, z1) => {
      const [x, y] = f.P((s0 + s1) / 2, (w0 + w1) / 2);
      kit.box(B, m, x, y, z0, s1 - s0, w1 - w0, z1 - z0, f.ang);
    };
    /** Geometry placed in shape coordinates (x = s, y = z, z = w) of an edge frame. */
    const SG = (f, m, g, s, z, w, rot = 0, sc = [1, 1, 1]) => {
      const L = new THREE.Matrix4().compose(
        new THREE.Vector3(s, z, w),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, rot)),
        new THREE.Vector3(...sc),
      );
      B.addGeometry(m, g, f.M(0).multiply(L));
      g.dispose();
    };
    /** Colonnette standing in the wall plane: base, shaft, cushion capital. */
    const colonnette = (f, s, w, z0, z1, r, shaftMat = blue, capMat = buffD) => {
      const h = z1 - z0;
      SG(f, capMat, new THREE.BoxGeometry(r * 2.6, 0.16, r * 2.6), s, z0 + 0.08, w);
      SG(
        f,
        shaftMat,
        new THREE.CylinderGeometry(r, r, h - 0.42, 8),
        s,
        z0 + 0.16 + (h - 0.42) / 2,
        w,
      );
      SG(f, capMat, new THREE.CylinderGeometry(r * 1.6, r * 1.05, 0.2, 8), s, z1 - 0.16, w);
      SG(f, capMat, new THREE.BoxGeometry(r * 3, 0.1, r * 3), s, z1 - 0.03, w);
    };
    /** Banded voussoir ring of an arch (alternate buff / blue blocks). */
    const voussoirs = (f, s, zs, rIn, rOut, n, w0, d, mats = [buffD, blue]) => {
      for (let k = 0; k < n; k++) {
        const t0 = (k * Math.PI) / n,
          t1 = ((k + 1) * Math.PI) / n;
        const sh = new THREE.Shape();
        sh.moveTo(s + rIn * Math.cos(t0), zs + rIn * Math.sin(t0));
        sh.lineTo(s + rOut * Math.cos(t0), zs + rOut * Math.sin(t0));
        sh.absarc(s, zs, rOut, t0, t1, false);
        sh.lineTo(s + rIn * Math.cos(t1), zs + rIn * Math.sin(t1));
        sh.absarc(s, zs, rIn, t1, t0, true);
        const g = new THREE.ExtrudeGeometry(sh, {
          depth: d,
          bevelEnabled: false,
          curveSegments: 1,
        });
        const m = mats[k % mats.length];
        addSplit(g, f.M(w0), m, m);
      }
    };
    /** U-shaped arch order (jambs + arch) between widths wOut and wIn. */
    const archOrder = (f, s, wOut, wIn, z0, zs, w0, d, m) => {
      const sh = new THREE.Shape();
      sh.moveTo(s - wOut / 2, z0);
      sh.lineTo(s - wOut / 2, zs);
      sh.absarc(s, zs, wOut / 2, Math.PI, 0, true);
      sh.lineTo(s + wOut / 2, z0);
      sh.lineTo(s + wIn / 2, z0);
      sh.lineTo(s + wIn / 2, zs);
      sh.absarc(s, zs, wIn / 2, 0, Math.PI, false);
      sh.lineTo(s - wIn / 2, z0);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false, curveSegments: 7 });
      addSplit(g, f.M(w0), m, m);
    };
    /** Buttress pier with projecting blue-grey bands. */
    const bandedPier = (f, s, wid, w0, w1, z0, z1, step = 0.9) => {
      eb(f, buffD, s - wid / 2, s + wid / 2, w0, w1, z0, z1);
      for (let z = z0 + 1.0; z < z1 - 0.3; z += step)
        eb(f, blue, s - wid / 2 - 0.03, s + wid / 2 + 0.03, w0, w1 + 0.03, z, z + 0.28);
      eb(f, blueD, s - wid / 2 - 0.08, s + wid / 2 + 0.08, w0, w1 + 0.1, z1, z1 + 0.3);
    };

    // ---------- the Cromwell Road elevation: openings and their fillings ----------
    const WD = 0.6; // depth of the front wall slab (window reveals)
    const LV = {
      base: (c) => [
        { k: 'r', s: c - 1.35, w: 1.2, z0: 0.9, z1: 2.0 },
        { k: 'r', s: c + 1.35, w: 1.2, z0: 0.9, z1: 2.0 },
      ],
      ground: (c) => [{ k: 'r', s: c, w: 3.9, z0: 2.8, z1: 6.4 }],
      first: (c) => [{ k: 'a', s: c, w: 4.0, z0: 8.1, zs: 11.4 }],
      second: (c) => [{ k: 'a', s: c, w: 3.2, z0: 15.0, zs: 17.4 }],
      attic: (c, z) =>
        [-1.4, 0, 1.4].map((d) => ({ k: 'a', s: c + d, w: 0.95, z0: z, zs: z + 1.5 })),
    };
    /** Fillings for one bay: tracery panels, colonnettes, voussoirs, sills, bars. */
    const fillBay = (f, c, levels, atticZ) => {
      const fw = WD; // front face of the slab
      if (levels.includes('base'))
        for (const h of LV.base(c)) {
          for (const d of [-0.3, 0, 0.3])
            eb(f, railIron, h.s + d - 0.03, h.s + d + 0.03, 0.2, 0.26, 0.9, 2.0);
          eb(f, blueD, h.s - 0.75, h.s + 0.75, fw, fw + 0.12, 0.75, 0.9);
        }
      if (levels.includes('ground')) {
        const h = LV.ground(c)[0];
        const lights = [-0.95, 0.95].map((d) => ({ k: 'a', s: c + d, w: 1.55, z0: 2.9, zs: 5.2 }));
        slab(
          f,
          specOutline(h, 0.03),
          [...lights, { k: 'c', s: c, z: 6.0, r: 0.25 }],
          0.2,
          buffL,
          buffL,
          {
            w0: 0.15,
            seg: 4,
          },
        );
        colonnette(f, c, 0.42, 2.9, 5.2, 0.13);
        for (const l of lights) eb(f, bar, l.s - 0.78, l.s + 0.78, 0.08, 0.12, 4.0, 4.06);
        for (const l of lights) eb(f, bar, l.s - 0.025, l.s + 0.025, 0.08, 0.12, 2.9, 5.2);
        eb(f, buffD, c - 2.15, c + 2.15, fw, fw + 0.22, 2.6, 2.8); // sill
        // flat arch of alternating voussoir blocks over the square head
        for (let k = 0; k < 7; k++) {
          const s0 = c - 2.25 + (k * 4.5) / 7;
          eb(f, k % 2 ? blue : buffD, s0, s0 + 4.5 / 7, fw, fw + 0.08, 6.4, 7.0);
        }
      }
      if (levels.includes('first')) {
        const h = LV.first(c)[0];
        const lights = [-0.95, 0.95].map((d) => ({ k: 'a', s: c + d, w: 1.6, z0: 8.2, zs: 10.9 }));
        slab(
          f,
          specOutline(h, 0.03),
          [...lights, { k: 'c', s: c, z: 12.35, r: 0.55 }],
          0.2,
          buffL,
          buffL,
          {
            w0: 0.15,
            seg: 5,
          },
        );
        colonnette(f, c, 0.42, 8.2, 10.9, 0.14);
        for (const l of lights) eb(f, bar, l.s - 0.8, l.s + 0.8, 0.08, 0.12, 9.6, 9.66);
        voussoirs(f, c, 11.4, 2.0, 2.45, 11, fw, 0.12);
        // sill with a crouching terracotta beast at each end (block massing)
        eb(f, buffD, c - 2.3, c + 2.3, fw, fw + 0.28, 7.85, 8.1);
        for (const d of [-2.0, 2.0])
          eb(f, buffL, c + d - 0.22, c + d + 0.22, fw, fw + 0.3, 8.1, 8.55);
      }
      if (levels.includes('second')) {
        const h = LV.second(c)[0];
        const lights = [-0.75, 0.75].map((d) => ({ k: 'a', s: c + d, w: 1.2, z0: 15.1, zs: 17.2 }));
        slab(f, specOutline(h, 0.03), lights, 0.2, buffL, buffL, { w0: 0.15, seg: 4 });
        colonnette(f, c, 0.42, 15.1, 17.2, 0.11);
        voussoirs(f, c, 17.4, 1.6, 1.98, 9, fw, 0.12);
        eb(f, buffD, c - 1.9, c + 1.9, fw, fw + 0.22, 14.8, 15.0);
      }
      if (atticZ != null) {
        for (const d of [-0.7, 0.7]) colonnette(f, c + d, fw + 0.06, atticZ, atticZ + 1.5, 0.09);
        eb(f, buffD, c - 2.1, c + 2.1, fw, fw + 0.18, atticZ - 0.2, atticZ);
      }
    };
    const bayHoles = (c, levels, atticZ) => [
      ...levels.flatMap((l) => (l === 'attic' ? [] : LV[l](c))),
      ...(atticZ != null ? LV.attic(c, atticZ) : []),
    ];
    /** A full modelled elevation on edge a -> b (wall plane at the edge, slab outward). */
    const elevation = (a, b, z1, centres, levels, atticZ, o = {}) => {
      const f = EF(a, b);
      const holes = centres.flatMap((c) => bayHoles(c, levels, atticZ));
      slab(f, rectOutline(0, z1), holes, WD, front3d, buff, { su: 1 / 1.2, sv: 1 / ZT });
      eb(f, winGlass, 0, f.L, -0.06, -0.02, 0, z1); // glazing seen through the openings
      for (const c of centres) fillBay(f, c, levels, atticZ);
      // plinth, string courses, corbel table and cornice
      eb(f, blueD, 0, f.L, WD, WD + 0.25, 0, 0.75);
      eb(f, blueD, 0, f.L, WD, WD + 0.2, 0.75, 1.0);
      for (const z of o.strings ?? [7.2, 14.3]) eb(f, blue, 0, f.L, WD, WD + 0.2, z, z + 0.38);
      const zc = z1 - 1.0;
      for (let s = 0.35; s < f.L - 0.2; s += 0.7)
        eb(f, buffD, s - 0.14, s + 0.14, WD, WD + 0.24, zc - 0.4, zc);
      eb(f, blue, 0, f.L, WD, WD + 0.3, zc, zc + 0.35);
      eb(f, buffD, 0, f.L, WD, WD + 0.45, zc + 0.35, z1);
      for (const s of o.piers ?? []) bandedPier(f, s, 1.2, WD, WD + 0.45, 0, z1 + 0.1);
      return f;
    };

    // ---------- base infill (single-storey galleries filling the light courts) ----------
    const FOOT = [
      [-103.2, 2.7],
      [-86.4, 2.3],
      [-86.1, 5.0],
      [-15.5, 5.0],
      [-15.3, -2.8],
      [16.2, -2.6],
      [16.3, 5.3],
      [87.2, 4.9],
      [87.5, 2.3],
      [104.3, 2.5],
      [104.9, 24.6],
      [104.9, 91.8],
      [102.4, 91.8],
      [102.5, 93.2],
      [78.0, 93.0],
      [78.0, 87.1],
      [53.5, 87.8],
      [53.3, 118.3],
      [-27.3, 118.4],
      [-31.5, 118.6],
      [-31.6, 124.2],
      [-40.4, 124.2],
      [-40.5, 118.2],
      [-79.4, 118.6],
      [-79.6, 121.4],
      [-101.0, 121.2],
      [-101.2, 93.8],
      [-102.6, 35.4],
    ];
    const inner = kit.offsetRing(FOOT, -0.6);
    texWalls(bandMat, inner, 0, 6.5, 4);
    flat(lead, inner, 6.5);

    // ---------- front range wings ----------
    const EAVE = 19;
    for (const [u0, u1] of [
      [-86.1, -15.5],
      [16.3, 87.2],
    ]) {
      const r = R(u0, 5.2, u1, 27);
      texWalls(backMat, r, 0, EAVE, 4.2, [0, 1], [0]);
      const nb = 10,
        bw = (u1 - u0) / nb;
      const centres = Array.from({ length: nb }, (_, k) => (k + 0.5) * bw);
      const piers = Array.from({ length: nb + 1 }, (_, k) => k * bw);
      elevation([u0, 5.2], [u1, 5.2], EAVE, centres, ['base', 'ground', 'first'], 15.4, { piers });
      kit.pitchedRoof(B, slateMat, bandMat, R(u0, 5.2, u1, 27), 0, EAVE, 6.5, 'gabled', {
        overhang: 0.75,
      });
      cresting(u0, 16.1, u1, 16.1, EAVE + 6.5);
      // gabled dormers with an arched light on the front slope
      for (let u = u0 + 1.5 * bw; u < u1 - bw; u += 2 * bw) {
        const df = EF([u - 1.4, 5.9], [u + 1.4, 5.9]);
        slab(
          df,
          (sh) => {
            sh.moveTo(0, EAVE - 0.5);
            sh.lineTo(2.8, EAVE - 0.5);
            sh.lineTo(2.8, EAVE + 2.6);
            sh.lineTo(1.4, EAVE + 4.1);
            sh.lineTo(0, EAVE + 2.6);
            sh.closePath();
          },
          [{ k: 'a', s: 1.4, w: 1.1, z0: EAVE + 0.5, zs: EAVE + 1.8 }],
          0.35,
          front3d,
          buff,
          { su: 1 / 1.2, sv: 1 / ZT },
        );
        eb(df, winGlass, 0.2, 2.6, -0.05, -0.01, EAVE, EAVE + 2.6);
        texWalls(bandMat, R(u - 1.4, 5.9, u + 1.4, 9), EAVE, EAVE + 2.6, 3, [0, 1], [0]);
        roof(
          R(u - 1.4, 5.55, u + 1.4, 9),
          Math.PI / 2,
          EAVE + 2.6,
          1.5,
          'gabled',
          slateMat,
          buff,
          0.15,
        );
        octagon(buffD, u, 5.6, EAVE + 4.1, 0.15, 0.9, 0.04);
      }
      // ventilation stacks on the ridge
      for (let u = u0 + 10; u < u1 - 5; u += 21) {
        box(buff, u, 16, EAVE + 4, 1.6, 1.6, 4.5);
        for (const z of [EAVE + 5.5, EAVE + 7.2]) box(blue, u, 16, z, 1.72, 1.72, 0.3);
        box(buffD, u, 16, EAVE + 8.5, 1.9, 1.9, 0.35);
      }
    }

    // ---------- end pavilions with octagonal turrets and steep pavilion roofs ----------
    for (const [u0, u1, west] of [
      [-103.2, -86.1, true],
      [87.2, 104.6, false],
    ]) {
      const r = R(u0, 3.0, u1, 20.5);
      // painted inner side and back faces; front and outer side are modelled
      texWalls(pavMat, r, 0, 24, 5.8, [0, 1], west ? [0, 3] : [0, 1]);
      const pc = (u1 - u0) / 2;
      elevation(
        [u0, 3.0],
        [u1, 3.0],
        24,
        [pc - 3.3, pc + 3.3],
        ['base', 'ground', 'first', 'second'],
        20.3,
        {
          piers: [pc],
          strings: [7.2, 14.3, 19.6],
        },
      );
      const side = west
        ? [
            [u0, 20.5],
            [u0, 3.0],
          ]
        : [
            [u1, 3.0],
            [u1, 20.5],
          ];
      const sf = EF(...side);
      elevation(
        side[0],
        side[1],
        24,
        [sf.L / 2 - 3.4, sf.L / 2 + 3.4],
        ['base', 'ground', 'first', 'second'],
        20.3,
        {
          piers: [sf.L / 2],
          strings: [7.2, 14.3, 19.6],
        },
      );
      box(blue, (u0 + u1) / 2, 11.75, 23.6, u1 - u0 + 1.6, 18.9, 0.6);
      const cu = (u0 + u1) / 2;
      // truncated steep pavilion roof with iron cresting, small lantern
      const g = new THREE.CylinderGeometry(Math.SQRT1_2 * 0.38, Math.SQRT1_2, 1, 4, 1, false)
        .rotateX(Math.PI / 2)
        .rotateZ(Math.PI / 4);
      geo(slate, g, cu, 11.75, 24.2 + 6.5, 0, u1 - u0 + 1.2, 18.5, 13);
      // lead hips
      for (const [du, dv] of [
        [-1, -1],
        [1, -1],
        [-1, 1],
        [1, 1],
      ]) {
        const p0 = [cu + du * ((u1 - u0) / 2 + 0.6), 11.75 + dv * 9.25, 24.2],
          p1 = [cu + du * ((u1 - u0) / 2 + 0.6) * 0.38, 11.75 + dv * 9.25 * 0.38, 37.2];
        const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]);
        const bg = new THREE.BoxGeometry(0.25, 0.25, len);
        const q = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]).normalize(),
        );
        B.addGeometry(
          lead,
          bg,
          new THREE.Matrix4().compose(
            new THREE.Vector3((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2 + 0.05),
            q,
            new THREE.Vector3(1, 1, 1),
          ),
        );
        bg.dispose();
      }
      cresting(cu - 3.25, 11.75 - 3.5, cu + 3.25, 11.75 - 3.5, 37.2);
      cresting(cu - 3.25, 11.75 + 3.5, cu + 3.25, 11.75 + 3.5, 37.2);
      cresting(cu - 3.25, 11.75 - 3.5, cu - 3.25, 11.75 + 3.5, 37.2);
      cresting(cu + 3.25, 11.75 - 3.5, cu + 3.25, 11.75 + 3.5, 37.2);
      octagon(buff, cu, 11.75, 37.2, 1.5, 2.4);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4 + Math.PI / 8;
        box(
          darkGlass,
          cu + Math.cos(a) * 1.4,
          11.75 + Math.sin(a) * 1.4,
          37.6,
          0.5,
          0.1,
          1.5,
          a + Math.PI / 2,
        );
      }
      octagon(blue, cu, 11.75, 39.6, 1.7, 0.3);
      pyramid(slate, cu, 11.75, 39.9, 3.2, 3.2, 3.4);
      geo(
        iron,
        new THREE.CylinderGeometry(0.04, 0.07, 1.8, 6).rotateX(Math.PI / 2),
        cu,
        11.75,
        43.9,
      );
      // octagonal corner turrets at the front corners, banded, with spirelets
      for (const uc of [u0 + 1.1, u1 - 1.1]) {
        octagon(buff, uc, 3.1, 0, 1.4, 26.5);
        for (let z = 1.6; z < 26; z += 1.2) octagon(blue, uc, 3.1, z, 1.46, 0.32);
        for (const z of [8.6, 15.8, 21.8]) {
          for (let k = 0; k < 3; k++) {
            const a =
              -Math.PI / 2 + ((k - 1) * Math.PI) / 4 + (uc < cu ? -Math.PI / 4 : Math.PI / 4);
            box(
              winGlass,
              uc + Math.cos(a) * 1.4,
              3.1 + Math.sin(a) * 1.4,
              z,
              0.45,
              0.12,
              1.6,
              a + Math.PI / 2,
            );
          }
        }
        octagon(blueD, uc, 3.1, 26.5, 1.65, 0.45);
        for (let k = 0; k < 8; k++) {
          const a = (k * Math.PI) / 4 + Math.PI / 8;
          box(
            buffD,
            uc + Math.cos(a) * 1.5,
            3.1 + Math.sin(a) * 1.5,
            26.95,
            0.35,
            0.25,
            0.7,
            a + Math.PI / 2,
          );
        }
        octagon(slate, uc, 3.1, 26.95, 1.5, 5.2, 0.05, true);
        geo(
          iron,
          new THREE.CylinderGeometry(0.03, 0.05, 1.4, 6).rotateX(Math.PI / 2),
          uc,
          3.1,
          32.7,
        );
      }
      // gabled dormer on the pavilion roof front
      const df = EF([cu - 2.2, 4.0], [cu + 2.2, 4.0]);
      slab(
        df,
        (sh) => {
          sh.moveTo(0, 24);
          sh.lineTo(4.4, 24);
          sh.lineTo(4.4, 28);
          sh.lineTo(2.2, 30.4);
          sh.lineTo(0, 28);
          sh.closePath();
        },
        [-0.75, 0.75].map((d) => ({ k: 'a', s: 2.2 + d, w: 1.0, z0: 25.0, zs: 26.9 })),
        0.4,
        front3d,
        buff,
        { su: 1 / 1.2, sv: 1 / ZT },
      );
      eb(df, winGlass, 0.3, 4.1, -0.05, -0.01, 24.5, 28.5);
      texWalls(bandMat, R(cu - 2.2, 4.0, cu + 2.2, 7.5), 24, 28, 3, [0, 1], [0]);
      roof(R(cu - 2.2, 3.6, cu + 2.2, 7.5), Math.PI / 2, 28, 2.4, 'gabled', slateMat, buff, 0.2);
    }

    // ---------- side ranges and north range ----------
    const ranges = [
      [R(-102.6, 20.5, -88.5, 121.0), Math.PI / 2],
      [R(89.5, 20.5, 104.6, 91.6), Math.PI / 2],
      [R(-88.5, 98, 53.2, 118.2), 0],
    ];
    for (const [r, a] of ranges) {
      texWalls(backMat, r, 0, 17, 4.2);
      kit.cornice(B, buffD, r, 16.3, { height: 0.7, projection: 0.35 });
      roof(r, a, 17, 5, 'gabled');
    }
    // Queen's Gate (west) elevation of the west range: modelled windows
    {
      const f = EF([-102.6, 121.0], [-102.6, 20.5]);
      for (let s = 3; s < f.L - 2; s += 4.2) {
        eb(f, buffD, s - 0.9, s + 0.9, 0, 0.22, 4.4, 4.6);
        eb(f, buffD, s - 0.9, s + 0.9, 0, 0.22, 10.4, 10.6);
      }
      for (const z of [1.0, 7.4, 13.6]) eb(f, blue, 0, f.L, 0, 0.15, z, z + 0.3);
    }

    // ---------- Hintze Hall: central hall with long glazed roof ----------
    {
      const r = R(-14.5, 20, 14.5, 98);
      texWalls(backMat, r, 0, 22, 4.2);
      for (let v = 30; v < 96; v += 6.5)
        for (const u of [-14.9, 14.9]) {
          box(buff, u, v, 0, 0.9, 1.2, 22.5);
          for (let z = 3; z < 22; z += 2.4) box(blue, u, v, z, 0.96, 1.26, 0.3);
        }
      kit.cornice(B, buffD, r, 21.4, { height: 0.6, projection: 0.4 });
      roof(r, Math.PI / 2, 22, 12, 'gabled');
      for (const [ue, ur] of [
        [-14.9, 0],
        [14.9, 0],
      ])
        slopeStripU(glass, 24, 95, ue, ur, 22, 34, 0.22, 0.86);
      cresting(0, 24, 0, 95, 34);
      for (let v = 24; v <= 95; v += 3.55)
        for (const ue of [-14.9, 14.9]) {
          const len = Math.hypot(14.9 * 0.64, 12 * 0.64),
            sg = Math.sign(ue);
          const um = ue * (1 - 0.54),
            zm = 22 + 12 * 0.54;
          const m = new THREE.Matrix4().compose(
            new THREE.Vector3(um, v, zm + 0.1),
            new THREE.Quaternion().setFromEuler(new THREE.Euler(0, sg * Math.atan2(12, 14.9), 0)),
            new THREE.Vector3(1, 1, 1),
          );
          const g = new THREE.BoxGeometry(len, 0.18, 0.18);
          B.addGeometry(iron, g, m);
          g.dispose();
        }
    }

    // ---------- centrepiece: portal block and twin spired towers ----------
    const ZT0 = 2.4; // entrance terrace level
    {
      const u0 = -7.4,
        u1 = 8.1,
        vw = -0.35, // wall plane behind the portal slab
        D = 2.4, // slab depth: front at v = -2.75
        zG = 22.3,
        zA = 31;
      const f = EF([u0, vw], [u1, vw]);
      const c = f.L / 2;
      // side and back walls of the centre block, roof behind the gable slab
      texWalls(bandMat, R(u0, vw, u1, 21), 0, zG, 4, [0, 1], [0]);
      roof(R(u0, vw + 0.3, u1, 21), Math.PI / 2, zG, zA - zG - 0.4, 'gabled', slateMat, buff, 0.3);
      // front slab: gable pentagon with the portal notch, gallery arcade and rose window
      const PW = 9.6,
        PS = ZT0 + 7.2; // portal width and springing
      const arcade = Array.from({ length: 7 }, (_, k) => ({
        k: 'a',
        s: c + (k - 3) * 1.9,
        w: 1.2,
        z0: 15.6,
        zs: 17.9,
      }));
      const rose = { k: 'c', s: c, z: 25.4, r: 2.2 };
      slab(
        f,
        (sh, L) => {
          sh.moveTo(0, 0);
          sh.lineTo(c - PW / 2, 0);
          sh.lineTo(c - PW / 2, PS);
          sh.absarc(c, PS, PW / 2, Math.PI, 0, true);
          sh.lineTo(c + PW / 2, 0);
          sh.lineTo(L, 0);
          sh.lineTo(L, zG);
          sh.lineTo(c, zA);
          sh.lineTo(0, zG);
          sh.closePath();
        },
        [...arcade, rose],
        D,
        front3d,
        buff,
        { su: 1 / 1.2, sv: 1 / ZT, seg: 8 },
      );
      eb(f, winGlass, 0.3, f.L - 0.3, -0.06, -0.02, 14, 28);
      // receding orders of the great portal (alternating buff and blue-grey)
      const orders = [9.6, 8.7, 7.8, 6.9, 6.0, 5.2];
      for (let k = 0; k + 1 < orders.length; k++) {
        const d = D - 0.4 * (k + 1);
        archOrder(f, c, orders[k] + 0.02, orders[k + 1], ZT0, PS, 0, d, k % 2 ? buff : blue);
        // colonnette in each re-entrant angle, on a common plinth
        for (const sg of [-1, 1]) {
          const s = c + sg * (orders[k + 1] / 2 - 0.19);
          colonnette(f, s, d - 0.21, ZT0 + 0.6, PS, 0.17, k % 2 ? blue : buffD, buffD);
          eb(f, blueD, s - 0.22, s + 0.22, Math.max(0.02, d - 0.45), d - 0.02, ZT0, ZT0 + 0.6);
        }
        // banded roll moulding on the arch of each order
        voussoirs(
          f,
          c,
          PS,
          orders[k + 1] / 2,
          orders[k + 1] / 2 + 0.22,
          13,
          d,
          0.12,
          k % 2 ? [buffD, blue] : [blue, buffD],
        );
      }
      voussoirs(f, c, PS, PW / 2, PW / 2 + 0.55, 15, D, 0.15);
      // doors, transom and glazed tympanum with radial bars
      eb(f, timber, c - 2.2, c + 2.2, 0.02, 0.12, ZT0, ZT0 + 4.6);
      for (const s of [c - 2.2, c, c + 2.2])
        eb(f, bar, s - 0.06, s + 0.06, 0.12, 0.18, ZT0, ZT0 + 4.6);
      for (const z of [ZT0 + 1.2, ZT0 + 3.0])
        eb(f, kit.mat('#4a3520'), c - 2.2, c + 2.2, 0.12, 0.16, z, z + 0.08);
      eb(f, buffD, c - 2.6, c + 2.6, 0.02, 0.3, ZT0 + 4.6, ZT0 + 5.0);
      eb(f, winGlass, c - 2.6, c + 2.6, -0.02, 0.02, ZT0 + 5.0, PS + 2.6);
      for (let k = 0; k <= 6; k++) {
        const t = (k * Math.PI) / 6;
        SG(
          f,
          bar,
          new THREE.BoxGeometry(2.5, 0.08, 0.08),
          c + Math.cos(t) * 1.25,
          PS + Math.sin(t) * 1.25,
          0.06,
          t,
        );
      }
      for (let k = 0; k < 3; k++)
        eb(f, bar, c - 2.6, c + 2.6, 0.03, 0.07, ZT0 + 5.0 + k * 0.7, ZT0 + 5.06 + k * 0.7);
      // gallery over the portal: sill course, colonnettes between the arches, string course
      eb(f, blue, 0, f.L, D, D + 0.3, 15.0, 15.5);
      for (let k = 0; k < 8; k++) colonnette(f, c + (k - 3.5) * 1.9, D + 0.16, 15.5, 17.9, 0.14);
      for (const h of arcade) voussoirs(f, h.s, h.zs, 0.6, 0.85, 5, D, 0.1);
      eb(f, blueD, 0, f.L, D, D + 0.35, 19.4, 19.8);
      for (let s = 0.4; s < f.L; s += 0.75)
        eb(f, buffD, s - 0.15, s + 0.15, D, D + 0.25, 19.8, 20.2);
      eb(f, blue, 0, f.L, D, D + 0.4, 20.2, 20.55);
      // rose window: spokes, hub and banded ring
      for (let k = 0; k < 8; k++) {
        const t = (k * Math.PI) / 4;
        SG(
          f,
          buffD,
          new THREE.BoxGeometry(2.2, 0.16, 0.25),
          c + Math.cos(t) * 1.1,
          25.4 + Math.sin(t) * 1.1,
          D - 0.2,
          t,
        );
      }
      SG(
        f,
        buffD,
        new THREE.CylinderGeometry(0.4, 0.4, 0.35, 10).rotateX(Math.PI / 2),
        c,
        25.4,
        D - 0.15,
      );
      for (let k = 0; k < 2; k++) {
        const sh = new THREE.Shape();
        sh.absarc(c, 25.4, 2.75, 0, Math.PI * 2, false);
        sh.holes.push(new THREE.Path().absarc(c, 25.4, 2.2, 0, Math.PI * 2, true));
        const g = new THREE.ExtrudeGeometry(sh, {
          depth: 0.15,
          bevelEnabled: false,
          curveSegments: 10,
        });
        addSplit(g, f.M(D + k * 0.0001), k ? blue : buffD, buffD);
      }
      for (let k = 0; k < 16; k += 2) {
        const t0 = (k * Math.PI) / 8;
        const sh = new THREE.Shape();
        sh.moveTo(c + 2.2 * Math.cos(t0), 25.4 + 2.2 * Math.sin(t0));
        sh.absarc(c, 25.4, 2.76, t0, t0 + Math.PI / 8, false);
        sh.absarc(c, 25.4, 2.2, t0 + Math.PI / 8, t0, true);
        const g = new THREE.ExtrudeGeometry(sh, {
          depth: 0.17,
          bevelEnabled: false,
          curveSegments: 2,
        });
        addSplit(g, f.M(D), blue, blue);
      }
      // gable coping and apex figure on its pedestal
      const rake = Math.atan2(zA - zG, c),
        rl = Math.hypot(c, zA - zG) + 0.6;
      for (const [sc, rot] of [
        [c / 2, rake],
        [1.5 * c, -rake],
      ])
        SG(
          f,
          blueD,
          new THREE.BoxGeometry(rl, 0.55, D + 0.3),
          sc,
          (zG + zA) / 2 + 0.2,
          (D + 0.3) / 2 - 0.15,
          rot,
        );
      for (const s of [0.3, f.L - 0.3]) {
        eb(f, buffD, s - 0.5, s + 0.5, D - 0.6, D + 0.3, zG - 0.5, zG + 1.6);
        pyramid(slate, ...f.P(s, D - 0.15), zG + 1.6, 0.9, 0.9, 1.4);
      }
      const [ax, ay] = f.P(c, D - 0.6);
      octagon(buffD, ax, ay, zA - 0.5, 0.7, 1.2);
      geo(
        stone,
        new THREE.CylinderGeometry(0.3, 0.42, 2.0, 8).rotateX(Math.PI / 2),
        ax,
        ay,
        zA + 1.7,
      );
      geo(stone, new THREE.SphereGeometry(0.26, 8, 6), ax, ay, zA + 2.95);
      // statue niches flanking the arcade on the slab face
      for (const s of [1.0, f.L - 1.0]) {
        eb(f, blueD, s - 0.45, s + 0.45, D, D + 0.25, 15.0, 15.4);
        geo(
          stone,
          new THREE.CylinderGeometry(0.2, 0.28, 1.6, 8).rotateX(Math.PI / 2),
          ...f.P(s, D + 0.15),
          16.2,
        );
      }

      // ---------- twin towers ----------
      for (const tu of [-11.6, 12.3]) {
        const tw = 8.4,
          tv = 1.5;
        const tr = R(tu - tw / 2, tv - tw / 2, tu + tw / 2, tv + tw / 2);
        const ti = kit.offsetRing(tr, -0.5);
        for (let e = 0; e < 4; e++) {
          const tf = EF(ti[e], ti[(e + 1) % 4]);
          const m = tf.L / 2;
          const upper = [
            ...[23, 28].flatMap((z) =>
              [-1.15, 1.15].map((d) => ({ k: 'a', s: m + d, w: 1.4, z0: z, zs: z + 2.5 })),
            ),
          ];
          const lower =
            e === 0
              ? [
                  { k: 'a', s: m, w: 2.0, z0: ZT0 + 0.4, zs: ZT0 + 3.6 },
                  { k: 'a', s: m, w: 3.2, z0: 8.5, zs: 12.0 },
                  { k: 'a', s: m, w: 2.6, z0: 15.5, zs: 18.8 },
                ]
              : [];
          slab(tf, rectOutline(0, 36), [...lower, ...upper], 0.5, front3d, buff, {
            su: 1 / 1.2,
            sv: 1 / ZT,
          });
          eb(tf, winGlass, 0, tf.L, -0.06, -0.02, 0, 36);
          for (const h of upper) {
            voussoirs(tf, h.s, h.zs, 0.7, 0.95, 5, 0.5, 0.1);
            eb(tf, buffD, h.s - 0.85, h.s + 0.85, 0.5, 0.7, h.z0 - 0.18, h.z0);
            eb(tf, bar, h.s - 0.03, h.s + 0.03, 0.08, 0.12, h.z0, h.zs);
          }
          for (const z of [21.4, 26.8, 32.4])
            eb(tf, blue, -0.5, tf.L + 0.5, 0.5, 0.72, z, z + 0.38);
          if (e === 0) {
            // ground light, then large coupled lights above
            voussoirs(tf, m, ZT0 + 3.6, 1.0, 1.35, 7, 0.5, 0.12);
            const l1 = [-0.8, 0.8].map((d) => ({ k: 'a', s: m + d, w: 1.25, z0: 8.6, zs: 11.4 }));
            slab(
              tf,
              specOutline(lower[1], 0.03),
              [...l1, { k: 'c', s: m, z: 12.55, r: 0.4 }],
              0.2,
              buffL,
              buffL,
              {
                w0: 0.12,
                seg: 4,
              },
            );
            colonnette(tf, m, 0.38, 8.6, 11.4, 0.13);
            voussoirs(tf, m, 12.0, 1.6, 2.0, 9, 0.5, 0.12);
            const l2 = [-0.65, 0.65].map((d) => ({ k: 'a', s: m + d, w: 1.0, z0: 15.6, zs: 18.3 }));
            slab(tf, specOutline(lower[2], 0.03), l2, 0.2, buffL, buffL, { w0: 0.12, seg: 4 });
            colonnette(tf, m, 0.38, 15.6, 18.3, 0.11);
            voussoirs(tf, m, 18.8, 1.3, 1.65, 9, 0.5, 0.12);
            for (const z of [7.2, 14.3]) eb(tf, blue, -0.5, tf.L + 0.5, 0.5, 0.72, z, z + 0.38);
            eb(tf, blueD, -0.5, tf.L + 0.5, 0.5, 0.78, 0, 1.0);
          }
          // corbel table under the belfry
          for (let s = -0.1; s < tf.L + 0.2; s += 0.62)
            eb(tf, buffD, s - 0.13, s + 0.13, 0.5, 0.75, 34.6, 35.2);
        }
        flat(lead, tr, 36);
        // corner buttresses with blue bands, stepping back at the set-offs
        for (const [du, dv] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ]) {
          const bu = tu + du * (tw / 2),
            bv = tv + dv * (tw / 2);
          box(buff, bu, bv, 0, 1.4, 1.4, 21.4);
          box(buff, bu - du * 0.1, bv - dv * 0.1, 21.4, 1.2, 1.2, 15.1);
          for (let z = 1.8; z < 36; z += 1.5) {
            const wz = z < 21.4 ? 1.48 : 1.28;
            box(
              blue,
              bu - (z < 21.4 ? 0 : du * 0.1),
              bv - (z < 21.4 ? 0 : dv * 0.1),
              z,
              wz,
              wz,
              0.3,
            );
          }
          box(blueD, bu, bv, 21.1, 1.6, 1.6, 0.35);
        }
        box(blue, tu, tv, 35.8, tw + 1.5, tw + 1.5, 0.7);
        // belfry stage: two tall arched openings per face with louvres and colonnettes
        const br = kit.offsetRing(tr, -0.4),
          bi = kit.offsetRing(tr, -0.9);
        for (let e = 0; e < 4; e++) {
          const bf = EF(bi[e], bi[(e + 1) % 4]);
          const m = bf.L / 2;
          const ops = [-1.65, 1.65].map((d) => ({ k: 'a', s: m + d, w: 1.9, z0: 37.4, zs: 41.4 }));
          slab(bf, rectOutline(36.5, 44.5), ops, 0.5, front3d, buff, { su: 1 / 1.2, sv: 1 / ZT });
          eb(bf, kit.mat('#1d2125'), 0, bf.L, -0.5, -0.45, 36.5, 44.5);
          for (const h of ops) {
            for (let z = 37.6; z < 41.6; z += 0.4)
              eb(bf, slate, h.s - 0.95, h.s + 0.95, -0.2, -0.1, z, z + 0.08);
            voussoirs(bf, h.s, h.zs, 0.95, 1.25, 7, 0.5, 0.12);
            for (const d of [-1.05, 1.05]) colonnette(bf, h.s + d, 0.62, 37.4, 41.4, 0.13);
          }
          eb(bf, blueD, -0.4, bf.L + 0.4, 0.5, 0.75, 36.5, 37.2);
          // arcaded corbel table and parapet at the top of the belfry
          for (let s = 0.2; s < bf.L; s += 0.55)
            eb(bf, buffD, s - 0.12, s + 0.12, 0.5, 0.72, 43.2, 43.7);
        }
        flat(lead, br, 44.5);
        box(blue, tu, tv, 43.7, tw + 0.5, tw + 0.5, 0.5);
        box(buffD, tu, tv, 44.2, tw + 0.7, tw + 0.7, 0.4);
        // corner pinnacles with spirelets
        for (const [du, dv] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ]) {
          const pu = tu + du * (tw / 2 - 0.1),
            pv = tv + dv * (tw / 2 - 0.1);
          octagon(buff, pu, pv, 44.6, 0.6, 3.0);
          for (const z of [45.3, 46.5]) octagon(blue, pu, pv, z, 0.64, 0.22);
          for (let k = 0; k < 4; k++) {
            const a = (k * Math.PI) / 2;
            box(
              winGlass,
              pu + Math.cos(a) * 0.58,
              pv + Math.sin(a) * 0.58,
              45.7,
              0.3,
              0.05,
              1.2,
              a + Math.PI / 2,
            );
          }
          octagon(blueD, pu, pv, 47.6, 0.72, 0.25);
          octagon(slate, pu, pv, 47.85, 0.66, 3.2, 0.02, true);
          geo(
            iron,
            new THREE.CylinderGeometry(0.02, 0.04, 0.9, 5).rotateX(Math.PI / 2),
            pu,
            pv,
            51.4,
          );
        }
        // tall slate spire with lead bands, gabled lucarnes and iron finial
        pyramid(slate, tu, tv, 45.2, tw - 0.6, tw - 0.6, 12.6);
        for (const t of [0.22, 0.45, 0.68]) {
          const wv = (tw - 0.6) * (1 - t) + 0.12;
          box(lead, tu, tv, 45.2 + 12.6 * t - 0.1, wv, wv, 0.18);
        }
        for (let k = 0; k < 4; k++) {
          const a = (k * Math.PI) / 2;
          const cu = tu + Math.sin(a) * 2.25,
            cv = tv - Math.cos(a) * 2.25;
          const lr = R(-0.65, -0.6, 0.65, 0.6).map(([x, y]) => [
            cu + x * Math.cos(a) - y * Math.sin(a),
            cv + x * Math.sin(a) + y * Math.cos(a),
          ]);
          const lf = EF(lr[0], lr[1]);
          slab(
            lf,
            (sh) => {
              sh.moveTo(0, 46.6);
              sh.lineTo(1.3, 46.6);
              sh.lineTo(1.3, 48.6);
              sh.lineTo(0.65, 49.6);
              sh.lineTo(0, 48.6);
              sh.closePath();
            },
            [{ k: 'a', s: 0.65, w: 0.6, z0: 47.0, zs: 48.0 }],
            0.15,
            buff,
            buffD,
          );
          eb(lf, kit.mat('#1d2125'), 0.1, 1.2, -0.1, -0.05, 46.6, 48.6);
          texWalls(slate, lr, 46.6, 48.6, 3, [0, 1], [0]);
          kit.pitchedRoof(B, slate, buff, lr, a + Math.PI / 2, 48.6, 1.0, 'gabled', {
            overhang: 0.1,
          });
        }
        geo(iron, new THREE.CylinderGeometry(0.05, 0.1, 2.6, 6).rotateX(Math.PI / 2), tu, tv, 59.0);
        geo(gold, new THREE.SphereGeometry(0.22, 8, 6), tu, tv, 58.2);
        for (const a of [0, Math.PI / 2]) box(iron, tu, tv, 59.3, 1.2, 0.05, 0.05, a);
        box(gold, tu + 0.25, tv, 59.8, 0.8, 0.03, 0.35);
      }

      // ---------- entrance terrace, steps and ramps ----------
      const TU0 = -7.4,
        TU1 = 8.1;
      // raised landing in front of the portal
      box(stone, (TU0 + TU1) / 2, -4.4, 0, TU1 - TU0 + 1.6, 3.4, ZT0);
      box(stoneD, (TU0 + TU1) / 2, -4.4, ZT0 - 0.15, TU1 - TU0 + 1.8, 3.6, 0.15);
      // broad flight of steps down to the forecourt (OSM steps v -5.7 .. -19.3)
      const nSt = 15,
        rise = ZT0 / nSt,
        tread = (19.3 - 6.1) / nSt;
      for (let k = 0; k < nSt; k++) {
        const v1 = -6.1 - k * tread;
        box(
          k % 5 === 4 ? stoneD : stone,
          0.75,
          v1 - tread / 2,
          0,
          16.0,
          tread + 0.02,
          ZT0 - k * rise,
        );
      }
      // stone cheek walls with lamp pedestals
      for (const su of [-7.6, 9.1]) {
        const g = new THREE.Shape();
        g.moveTo(-2.75, 0);
        g.lineTo(-19.3, 0);
        g.lineTo(-19.3, 0.7);
        g.lineTo(-6.1, ZT0 + 0.9);
        g.lineTo(-2.75, ZT0 + 0.9);
        g.closePath();
        const eg = new THREE.ExtrudeGeometry(g, { depth: 0.7, bevelEnabled: false });
        // shape x -> v, shape y -> z, extrude -> u
        B.addGeometry(
          buffD,
          eg,
          new THREE.Matrix4().set(0, 0, 1, su - 0.35, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1),
        );
        eg.dispose();
        box(blueD, su, -19.0, 0, 1.1, 1.1, 1.2);
        box(blueD, su, -5.8, 0, 1.1, 1.1, ZT0 + 1.4);
      }
      // dry area railings in front of the basement windows
      for (const [a0, a1] of [
        [-103.2, -15.6],
        [16.3, 104.4],
      ]) {
        box(stone, (a0 + a1) / 2, -1.5, 0, a1 - a0, 0.4, 0.5);
        box(railIron, (a0 + a1) / 2, -1.5, 1.4, a1 - a0, 0.06, 0.06);
        box(railIron, (a0 + a1) / 2, -1.5, 0.6, a1 - a0, 0.06, 0.06);
        for (let u = a0 + 0.1; u < a1; u += 0.22) box(railIron, u, -1.5, 0.5, 0.025, 0.025, 1.05);
        box(kit.mat('#8f8a80'), (a0 + a1) / 2, (-1.3 + 4.6) / 2, 0.02, a1 - a0, 5.6, 0.04);
      }
    }

    // ---------- Cromwell Road railings, gate piers and gates ----------
    {
      const VR = -32.5;
      const runs = [
        [-107.6, -36.6],
        [38.6, 165.8],
      ];
      for (const [a0, a1] of runs) {
        box(stoneD, (a0 + a1) / 2, VR, 0, a1 - a0, 0.55, 0.45);
        const n = Math.max(1, Math.round((a1 - a0) / 5.5));
        for (let k = 0; k <= n; k++) {
          const u = a0 + ((a1 - a0) * k) / n;
          octagon(stone, u, VR, 0, 0.42, 1.55);
          octagon(stoneD, u, VR, 1.55, 0.5, 0.18);
          octagon(stone, u, VR, 1.73, 0.34, 0.35, 0.05);
        }
        box(railIron, (a0 + a1) / 2, VR, 1.75, a1 - a0, 0.07, 0.07);
        box(railIron, (a0 + a1) / 2, VR, 0.6, a1 - a0, 0.06, 0.06);
        for (let u = a0 + 0.15; u < a1; u += 0.2) {
          box(railIron, u, VR, 0.45, 0.025, 0.025, 1.55);
          box(gold, u, VR, 2.0, 0.05, 0.05, 0.08);
        }
      }
      // large square Cromwell Road gate piers topped by lanterns, either side of the forecourt
      for (const u of [-35.5, 37.5]) {
        box(stone, u, VR, 0, 1.5, 1.5, 3.2);
        box(buffD, u, VR - 0.76, 1.2, 0.9, 0.04, 1.2); // inset terracotta relief panel
        box(stoneD, u, VR, 3.2, 1.8, 1.8, 0.3);
        box(stone, u, VR, 3.5, 1.3, 1.3, 0.25);
        box(railIron, u, VR, 3.75, 0.25, 0.25, 0.9);
        box(
          kit.mat('#f3e6b8', { emissive: new THREE.Color('#6a5a2a'), emissiveIntensity: 0.6 }),
          u,
          VR,
          4.65,
          0.55,
          0.55,
          0.75,
        );
        pyramid(railIron, u, VR, 5.4, 0.75, 0.75, 0.5);
      }
      // openwork wrought-iron centre piers with gilded lions, and the wide gates
      for (const u of [-6.2, 7.7]) {
        for (const [du, dv] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ])
          box(railIron, u + du * 0.35, VR + dv * 0.35, 0, 0.08, 0.08, 3.4);
        for (const z of [0.3, 1.5, 2.7, 3.3]) box(railIron, u, VR, z, 0.8, 0.8, 0.07);
        // recumbent gilded lion facing the street
        box(railIron, u, VR, 3.37, 0.95, 0.95, 0.1);
        geo(gold, new THREE.SphereGeometry(1, 10, 6), u, VR + 0.08, 3.62, 0, 0.2, 0.42, 0.17);
        geo(gold, new THREE.SphereGeometry(1, 10, 6), u, VR - 0.24, 3.78, 0, 0.17, 0.15, 0.2);
        geo(gold, new THREE.SphereGeometry(1, 8, 6), u, VR - 0.36, 3.8, 0, 0.09, 0.1, 0.09);
        for (const du of [-0.09, 0.09]) box(gold, u + du, VR - 0.38, 3.47, 0.07, 0.3, 0.08);
        box(gold, u + 0.12, VR + 0.45, 3.47, 0.04, 0.3, 0.04);
      }
      for (const [g0, g1] of [
        [-35.5, -6.2],
        [7.7, 37.5],
      ]) {
        const mid = (g0 + g1) / 2;
        for (const [a0, a1] of [
          [g0 + 0.9, mid - 3.5],
          [mid + 3.5, g1 - 0.6],
        ]) {
          box(railIron, (a0 + a1) / 2, VR, 2.0, a1 - a0, 0.06, 0.06);
          box(railIron, (a0 + a1) / 2, VR, 0.3, a1 - a0, 0.06, 0.06);
          for (let u = a0 + 0.1; u < a1; u += 0.16) box(railIron, u, VR, 0.3, 0.025, 0.025, 1.9);
        }
        // the gate leaves, standing open against the forecourt
        for (const sg of [-1, 1]) {
          const hu = mid + sg * 3.5;
          box(railIron, hu, VR, 0, 0.12, 0.12, 2.6);
          for (let k = 0; k < 14; k++)
            box(railIron, hu, VR + 0.25 + k * 0.22, 0.15, 0.025, 0.025, 2.2);
          box(railIron, hu, VR + 1.6, 2.3, 0.05, 3.1, 0.06);
          box(railIron, hu, VR + 1.6, 0.15, 0.05, 3.1, 0.06);
        }
      }
    }

    // ---------- top-lit gallery wings in the courts ----------
    const wingsW = [
      [-80, -69],
      [-59, -48],
      [-38, -27],
    ];
    const wingsE = [
      [27, 38],
      [48, 59],
      [69, 80],
    ];
    for (const [u0, u1, v1] of [
      ...wingsW.map((w) => [...w, 98]),
      ...wingsE.map((w) => [...w, 87.5]),
    ]) {
      const r = R(u0, 27, u1, v1);
      texWalls(bandMat, r, 6.5, 13, 4, [0.2, 1]);
      kit.cornice(B, buffD, r, 12.6, { height: 0.4, projection: 0.25 });
      roof(r, Math.PI / 2, 13, 3.5, 'gabled');
      for (const ue of [u0 - 0.3, u1 + 0.3])
        slopeStripU(glass, 28, v1 - 1, ue, (u0 + u1) / 2, 13, 16.5, 0.5, 0.95);
    }
    // octagonal stair turrets at the Hintze Hall north end
    for (const u of [-16, 16]) {
      octagon(buff, u, 98, 0, 2.2, 27);
      for (let z = 2; z < 27; z += 1.8) octagon(blue, u, 98, z, 2.28, 0.35);
      for (const z of [8, 14, 20])
        for (let k = 0; k < 8; k += 2) {
          const a = (k * Math.PI) / 4 + Math.PI / 8;
          box(
            winGlass,
            u + Math.cos(a) * 2.12,
            98 + Math.sin(a) * 2.12,
            z,
            0.6,
            0.12,
            1.8,
            a + Math.PI / 2,
          );
        }
      octagon(blueD, u, 98, 27, 2.5, 0.4);
      octagon(slate, u, 98, 27.4, 2.4, 6, 0.05, true);
      geo(iron, new THREE.CylinderGeometry(0.03, 0.06, 1.6, 6).rotateX(Math.PI / 2), u, 98, 34.2);
    }

    // ---------- Earth Galleries / Red Zone (former Geological Museum) ----------
    {
      const r = [
        [104.9, 24.6],
        [171.9, 24.6],
        [172.2, 74.5],
        [172.9, 91.6],
        [104.9, 91.8],
      ];
      const stoneF = kit.facade('portland_stone', 1);
      // painted back faces; south (garden) and east (Exhibition Road) faces modelled
      for (let k = 3; k < 5; k++)
        kit.walls(B, stoneF, [[[r[k], r[(k + 1) % 5]]]], 0, 22, { bay: 3.8, storey: 4.3 });
      const stoneP = kit.mat('#dcd5c2', { roughness: 0.85 });
      for (let k = 0; k < 3; k++) {
        const a = r[k],
          b = r[k + 1];
        const f = EF(a, b);
        kit.walls(B, stoneP, [[[a, b]]], 0, 22);
        // rusticated ground storey: channelled joints
        for (let z = 0.55; z < 5.4; z += 0.55) eb(f, stoneD, 0, f.L, 0, 0.06, z, z + 0.06);
        eb(f, stoneD, 0, f.L, 0, 0.3, 0, 0.7);
        eb(f, stone, 0, f.L, 0, 0.35, 5.4, 6.0);
        const skipE = k === 1 ? [21, 34] : null; // keep the entrance bay clear
        const opts = (st) => ({
          width: st === 0 ? 1.6 : 1.5,
          height: st === 0 ? 2.8 : st === 3 ? 2.0 : 2.9,
          bay: 3.8,
          margin: 1.2,
          depth: 0.18,
          glass: winGlass,
          frame: kit.mat('#3c4248', { roughness: 0.5, metalness: 0.4 }),
          sill: stone,
          head: st === 1 ? 'pediment' : 'lintel',
          bars: 1,
          surround: st === 1 ? 0.22 : 0,
          surroundMat: stone,
        });
        const zs = [1.6, 7.0, 11.6, 16.8];
        const segs = skipE
          ? [
              [0, skipE[0] - 0.5],
              [skipE[1] + 0.5, f.L],
            ]
          : [[0, f.L]];
        for (const [s0, s1] of segs)
          for (let st = 0; st < 4; st++) kit.windowRow(B, f.P(s0, 0), f.P(s1, 0), zs[st], opts(st));
        for (const z of [10.6, 15.9]) eb(f, stone, 0, f.L, 0, 0.18, z, z + 0.25);
      }
      texWalls(stone, r, 0, 1.6, 4);
      // cornice and attic
      kit.cornice(B, stone, r, 20.6, { height: 1.6, projection: 0.7, steps: 3 });
      const at = kit.offsetRing(r, -2.5);
      kit.walls(B, kit.facade('portland_stone', 2), [[at]], 22.2, 26, { bay: 3.8, storey: 3.8 });
      kit.cornice(B, stone, at, 25.6, { height: 0.4, projection: 0.3 });
      flat(lead, kit.offsetRing(r, 0.0), 22.2);
      // atrium (Earth Hall) with glazed roof
      const ar = R(122, 38, 156, 80);
      flat(lead, at, 26);
      texWalls(stone, ar, 26, 27.4, 4);
      roof(ar, Math.PI / 2, 27.4, 2.5, 'gabled', glass, stone, 0.2);
      for (let v = 39; v < 80; v += 3) box(iron, 139, v, 27.4, 34, 0.15, 0.3);
      for (const [pu, pv, w, d] of [
        [113, 50, 6, 4],
        [113, 70, 4, 6],
        [164, 62, 5, 8],
      ]) {
        box(kit.mat('concrete'), pu, pv, 26, w, d, 2.2);
        for (let k = 0; k < Math.floor(w / 0.6); k++)
          box(kit.mat('dark_steel'), pu - w / 2 + 0.3 + k * 0.6, pv, 26.6, 0.06, d + 0.05, 1.2);
      }
      // Exhibition Road entrance: tall recessed portal with flanking piers
      const eu = 172.3;
      box(darkGlass, eu + 0.1, 52, 0, 0.4, 9, 10.5);
      for (let z = 0.6; z < 10.5; z += 2.2) box(stone, eu + 0.2, 52, z, 0.3, 9, 0.2);
      for (let v = 48; v <= 56; v += 2) box(kit.mat('#3c4248'), eu + 0.32, v, 0, 0.12, 0.12, 10.5);
      for (const v of [46.5, 57.5]) {
        box(stone, eu + 0.5, v, 0, 1.4, 2.0, 12.5);
        for (let z = 0.6; z < 12; z += 0.6) box(stoneD, eu + 1.21, v, z, 0.04, 2.0, 0.05);
      }
      box(stone, eu + 0.5, 52, 10.5, 1.0, 13, 2.0);
      box(stoneD, eu + 0.7, 52, 12.5, 1.4, 13.6, 0.4);
      box(kit.mat('red'), eu + 1.05, 52, 11, 0.1, 7, 1.0);
      for (let k = 0; k < 3; k++)
        box(stone, eu + 1.2 + k * 0.45, 52, 0, 0.45, 15 - k * 0.6, 0.45 - k * 0.15);
      // south entrance pavilion (rounded) towards the east garden
      geo(stone, new THREE.CylinderGeometry(6.2, 6.2, 7, 28).rotateX(Math.PI / 2), 160, 18.6, 3.5);
      geo(
        darkGlass,
        new THREE.CylinderGeometry(
          6.25,
          6.25,
          4.4,
          28,
          1,
          true,
          Math.PI * 0.15,
          Math.PI * 0.7,
        ).rotateX(Math.PI / 2),
        160,
        18.6,
        3.2,
      );
      geo(
        stoneD,
        new THREE.CylinderGeometry(6.5, 6.5, 0.4, 28).rotateX(Math.PI / 2),
        160,
        18.6,
        7.0,
      );
      flat(lead, kit.offsetRing(R(154, 12.4, 166, 24.6), -0.2), 7.05);
    }

    // ---------- bridge over the arched gateway to the Science Museum ----------
    {
      const v0 = 91.8,
        v1 = 123.3,
        L = v1 - v0,
        H = 18,
        span = 11;
      const sh = new THREE.Shape();
      sh.moveTo(0, 0);
      sh.lineTo(L / 2 - span / 2, 0);
      sh.lineTo(L / 2 - span / 2, 6);
      sh.absarc(L / 2, 6, span / 2, Math.PI, 0, true);
      sh.lineTo(L / 2 + span / 2, 0);
      sh.lineTo(L, 0);
      sh.lineTo(L, H);
      sh.lineTo(0, H);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: 8, bevelEnabled: false, curveSegments: 12 });
      const m = new THREE.Matrix4().set(0, 0, 1, 137.4, 1, 0, 0, v0, 0, 1, 0, 0, 0, 0, 0, 1);
      B.addGeometry(stone, g, m);
      g.dispose();
      for (const v of [v0 + 6, v1 - 6]) box(darkGlass, 145.45, v, 9, 0.1, 3.5, 6);
      for (const v of [v0 + 6, v1 - 6]) box(darkGlass, 137.35, v, 9, 0.1, 3.5, 6);
      box(stone, 141.4, (v0 + v1) / 2, H, 8.6, L, 0.6);
      for (const u of [137.2, 145.6]) box(stoneD, u, (v0 + v1) / 2, 6, 0.3, L, 0.4);
      // keystone and archivolt on both faces
      for (const u of [137.2, 145.6]) box(stoneD, u, (v0 + v1) / 2, 10.4, 0.35, 1.2, 1.4);
    }

    // ---------- Darwin Centre: white cocoon in a glass box ----------
    {
      const r = R(-154.2, 94.0, -101.1, 121.8);
      const H = 28;
      texWalls(clearGlass, r, 0, H, 4);
      const ru = -127.6,
        rv = 107.9;
      for (let u = -154.2; u <= -101; u += 4.42) {
        box(white, u, 94.0, 0, 0.16, 0.3, H);
        box(white, u, 121.8, 0, 0.16, 0.3, H);
      }
      for (let v = 94; v <= 122; v += 4.63) {
        box(white, -154.2, v, 0, 0.3, 0.16, H);
        box(white, -101.1, v, 0, 0.3, 0.16, H);
      }
      for (let z = 7; z < H; z += 7) {
        texWalls(white, kit.offsetRing(r, 0.15), z, z + 0.18, 30);
      }
      flat(clearGlass, r, H);
      for (let u = -152; u < -101; u += 4) box(white, u, rv, H, 0.4, 27.8, 0.6);
      kit.walls(B, white, [[kit.offsetRing(r, 0.3)]], H, H + 1.2);
      const cg = new THREE.SphereGeometry(1, 40, 22);
      geo(white, cg, ru, rv - 0.5, 13.8, 0.02, 24.5, 10.5, 13.6);
      // slot windows in the cocoon skin and the walkways to it
      for (let k = 0; k < 6; k++)
        box(darkGlass, ru - 16 + k * 6.4, rv - 10.9, 9 + (k % 3) * 3, 1.6, 0.4, 0.25, 0.02);
      for (const z of [7, 14, 21]) box(white, ru, rv + 9.5, z, 6, 4.5, 0.3);
      box(darkGlass, ru, rv, 0, 50, 25, 0.3);
      box(clearGlass, -100.9, 108, 0, 1.2, 10, 18);
    }

    // ---------- lodge on the Queen's Gate side ----------
    {
      const r = R(-165.9, 69.7, -157.7, 84.6);
      texWalls(backMat, r, 0, 6.5, 3.2);
      kit.cornice(B, buffD, r, 6.1, { height: 0.4, projection: 0.25 });
      roof(r, Math.PI / 2, 6.5, 4.5, 'hipped', slateMat, buff, 0.4);
      for (const v of [73, 81]) {
        box(buff, -161.8, v, 9.5, 1.0, 1.0, 3.5);
        box(blue, -161.8, v, 12.4, 1.15, 1.15, 0.3);
      }
    }

    root.add(B.toGroup('natural_history_museum'));

    // ---------- reused street furniture on the forecourt ----------
    const W = (u, v, h = 0) => [
      O[0] + u * Math.cos(ANG) - v * Math.sin(ANG),
      O[1] + u * Math.sin(ANG) + v * Math.cos(ANG),
      ANG + h,
    ];
    if (placeAssets) {
      outer.add(
        placeAssets('street_lamp', [
          W(-10.5, -14, -Math.PI / 2),
          W(12, -14, Math.PI / 2),
          W(-10.5, -26, -Math.PI / 2),
          W(12, -26, Math.PI / 2),
          W(-36, -12, -Math.PI / 2),
          W(38, -12, Math.PI / 2),
        ]),
      );
      outer.add(
        placeAssets(
          'bollard',
          [-3.5, -1, 1.5, 4, 6.5].map((u) => W(u, -31.2, 0)),
        ),
      );
    }
    return outer;
  },
};
