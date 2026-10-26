// Victoria and Albert Museum, Cromwell Road / Exhibition Road, South Kensington.
// Aston Webb's Cromwell Road front (1899-1909): a ~219 m range of red brick with
// Portland stone dressings and bands, a stone ground storey with round-arched
// windows, tall first-floor windows separated by niches holding statues of British
// artists and craftsmen, a cornice and balustrade, and raised pavilions; in the
// centre a stone frontispiece with the grand arched entrance (Edward VII and
// Alexandra flanking it, Prince Albert above) and, over it, the central tower:
// a square stage, a column-ringed octagonal drum and a statue stage carrying an open
// lantern in the outline of an imperial crown, topped by a figure of Fame.
// Exhibition Road side: the Aston Webb Screen opened up with entrances (AL_A, 2017)
// onto the porcelain-tiled Sackler Courtyard with its tile-roofed cafe pavilion.
// Behind: the 1860s brick and terracotta ranges around the John Madejski Garden
// (elliptical pool) and the top-lit Cast Courts.
// Local frame: u along Cromwell Road (east-north-east), v towards the north-north-west,
// origin at the main entrance.
const O = [1967, -1142],
  ANG = 0.2884;

export default {
  id: 'victoria_and_albert_museum',
  name: 'Victoria and Albert Museum',
  claims: [
    '9e8e12eb-0a6c-473a-9dbb-95da1d662ab7', // Victoria and Albert Museum
    '15e1d65d-685b-4897-83bb-92870507b04a', // V&A Patisserie (Sackler Courtyard cafe pavilion)
    '35d8865e-446a-4ec3-89b0-d6a1ba5ce494', // Aston Webb Screen on Exhibition Road
    '3ebbb048-b039-47cd-8cae-0ba1defa99bc', // infill in the north courtyard notch
  ],
  references: [
    {
      title:
        'Out of the shadows: the facade and decorative sculpture of the V&A, part 1 (V&A Online Journal)',
      url: 'https://www.vam.ac.uk/content/journals/research-journal/issue-no.-7-autumn-2015/out-of-the-shadows-the-faade-and-decorative-sculpture-of-the-victoria-and-albert-museum,-part-1',
      used_for:
        '219 m red brick and Portland stone front; open lantern in the outline of an imperial crown; statues in niches between first-floor windows along the whole front',
    },
    {
      title: 'A grand entrance on Cromwell Road (V&A)',
      url: 'https://www.vam.ac.uk/articles/a-grand-entrance-on-cromwell-road',
      used_for:
        'tower replanned as a three-storey octagonal structure; building brought forward onto Cromwell Road; entrance opened 1909',
    },
    {
      title: 'Victoria and Albert Museum - MIT Dome',
      url: 'https://dome.mit.edu/handle/1721.3/136858',
      used_for:
        'skyline broken by pavilion domes and campaniles; column-tiered tower supporting an open crown',
    },
    {
      title: 'Entrance, V&A Museum, London (Getty Images caption)',
      url: 'https://www.gettyimages.com.au/detail/photo/entrance-v-a-museum-london-england-royalty-free-image/2195561429',
      used_for:
        'Portland stone entrance facade; statues of Victoria, Albert, and Fame on the pinnacle of the tower crown',
    },
    {
      title: 'V&A facade - Queen Victoria (London Remembers)',
      url: 'https://www.londonremembers.com/memorials/v-a-facade-queen-victoria/other',
      used_for:
        'Albert and Victoria by the arch, Edward VII and Alexandra flanking the entrance; 36 statues on the two public facades, names on labels under the feet',
    },
    {
      title: 'Victoria and Albert Museum, the facade on Cromwell Road (RIBApix)',
      url: 'https://www.architecture.com/image-library/ribapix/image-information/poster/victoria-and-albert-museum-south-kensington-london-the-facade-on-cromwell-road/posterid/RIBA7582.html',
      used_for: 'general view of the Cromwell Road facade (caption)',
    },
    {
      title: 'AL_A completes tile-covered entrance and subterranean gallery for V&A (Dezeen)',
      url: 'https://www.dezeen.com/2017/06/28/ala-amanda-levete-v-a-victoria-albert-museum-exhibition-road-quarter-courtyard-gallery-london/',
      used_for:
        'Exhibition Road Quarter: porcelain-tiled Sackler Courtyard, cafe with tiled roof, refurbished Aston Webb Screen',
    },
    {
      title: 'Treasures of London - The Aston Webb Screen (Exploring London)',
      url: 'https://exploring-london.com/tag/sir-aston-webb/',
      used_for: 'screen built to hide boilers, opened up with entrances into the courtyard',
    },
    {
      title: 'Victoria and Albert Museum - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101190187-victoria-and-albert-museum-brompton-hans-town-ward',
      used_for: 'quadrangle facades (Fowke, Sykes terracotta) at the heart of the museum',
    },
  ],
  notes:
    'Footprint from Overture (courtyard garden kept as a hole). Overture h (13.6 m) is inferred; heights are estimates: ' +
    'Cromwell Road range 22 m to the balustrade, frontispiece 25 m, tower crown with Fame at ~58 m (no published height ' +
    'found). The Cromwell Road and Exhibition Road fronts are real geometry: brick-and-stone wall slabs with arched ' +
    'ground-floor windows, first-floor windows with architraves, pediments and glazing bars, statue niches with simplified ' +
    'standing figures between them, cornice and turned balustrade, quoins and raised pavilions with small open cupolas ' +
    '(the "pavilion domes"). Bay width (6.6 m) and storey heights are estimated from views, not drawings; statues are ' +
    'generic draped figures. Tower: square stage, column ring, statue stage and an eight-rib open crown with orb and ' +
    'Fame, all proportions estimated. Rear ranges, Cast Courts glazed roofs and the Henry Cole Wing block are schematic.',

  build({ THREE, kit }) {
    const root = new THREE.Group();
    root.position.set(O[0], O[1], 0);
    root.rotation.z = ANG;
    const B = new kit.MeshBatch();

    const BRICK = '#9b4b37',
      BRICK_D = '#83402f',
      STONE = '#e0d9c7',
      STONE_D = '#c8bfa9',
      WIN = '#29313a';
    const stone = kit.mat('portland_stone'),
      stoneD = kit.mat(STONE_D),
      stoneL = kit.mat('#e8e2d2', { roughness: 0.8 }),
      brick = kit.mat(BRICK, { roughness: 0.9 }),
      slateMat = kit.roof('slate', 2),
      lead = kit.mat('lead'),
      leadD = kit.mat('#6d767b', { roughness: 0.55, metalness: 0.35 }),
      glass = kit.mat('glass'),
      darkGlass = kit.mat('dark_glass'),
      winGlass = kit.mat('#2a323a', { roughness: 0.2, metalness: 0.3 }),
      sash = kit.mat('#ece9e1', { roughness: 0.6 }),
      bronze = kit.mat('bronze'),
      bronzeD = kit.mat('#4f3d2a', { roughness: 0.5, metalness: 0.5 }),
      gold = kit.mat('gold'),
      water = kit.mat('water'),
      paving = kit.mat('paving'),
      grass = kit.mat('grass'),
      brickF = kit.facade('red_brick', 1);

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
    const niche = (g, cx, yTop, w, yBot) => {
      fillArch(g, cx - w / 2, yTop, w, yBot, '#8f877a');
      g.fillStyle = STONE;
      const h = yBot - yTop;
      g.fillRect(cx - w * 0.18, yTop + h * 0.32, w * 0.36, h * 0.62);
      g.beginPath();
      g.arc(cx, yTop + h * 0.24, w * 0.16, 0, Math.PI * 2);
      g.fill();
      g.fillRect(cx - w * 0.45, yBot - h * 0.06, w * 0.9, h * 0.06);
    };

    // ---------- painted elevations (faces not modelled in 3D) ----------
    const RH = 22,
      BAY = 6.6;
    const rangeMat = kit.paintedMaterial('va:range', 256, 852, (g, W, H) => {
      const s = H / RH,
        Y = (z) => H - z * s,
        X = (m) => m * (W / BAY);
      g.fillStyle = BRICK;
      g.fillRect(0, 0, W, H);
      g.fillStyle = BRICK_D;
      for (let z = 0; z < RH; z += 0.3) g.fillRect(0, Y(z), W, 1);
      g.fillStyle = STONE;
      g.fillRect(0, Y(6.2), W, 6.2 * s);
      g.fillStyle = STONE_D;
      for (let z = 0.6; z < 6.2; z += 0.6) g.fillRect(0, Y(z), W, 2);
      fillArch(g, X(2.0), Y(5.3), X(2.6), Y(1.2), WIN);
      g.fillStyle = STONE;
      for (let z = 7.2; z < 19; z += 1.35) g.fillRect(0, Y(z), W, 0.42 * s);
      g.fillRect(0, Y(6.9), W, 0.7 * s);
      g.fillStyle = STONE;
      g.fillRect(X(1.7), Y(14.6), X(3.2), 7.2 * s);
      g.fillStyle = WIN;
      g.fillRect(X(2.1), Y(13.8), X(2.4), 6.2 * s);
      niche(g, X(0), Y(14.0), X(1.1), Y(8.4));
      niche(g, X(BAY), Y(14.0), X(1.1), Y(8.4));
      g.fillStyle = STONE;
      g.fillRect(X(2.0), Y(19.0), X(2.6), 3.0 * s);
      g.fillStyle = WIN;
      g.fillRect(X(2.3), Y(18.7), X(2.0), 2.5 * s);
      g.fillStyle = STONE;
      g.fillRect(0, Y(20.4), W, 1.0 * s);
      g.fillRect(0, Y(RH), W, 0.3 * s);
    });
    // Brick and stone wall for the modelled fronts: u = metres / 2.4, v = z / 25.6.
    const ZT = 25.6;
    const wall3d = kit.paintedMaterial('va:wall3d', 128, 1024, (g, W, H) => {
      const s = H / ZT,
        Y = (z) => H - z * s,
        px = W / 2.4;
      g.fillStyle = BRICK;
      g.fillRect(0, 0, W, H);
      const r = kit.rng(0.291);
      for (let z = 0; z < ZT; z += 0.075)
        for (let x = ((z / 0.075) % 2) * 0.1125; x < 2.4; x += 0.225) {
          const k = r();
          g.fillStyle = k < 0.3 ? '#8f4433' : k < 0.6 ? '#a3513b' : k < 0.8 ? '#94493a' : '#ad5a42';
          g.fillRect(x * px, Y(z + 0.075), 0.21 * px, 0.065 * s);
        }
      // Portland stone ground storey with channelled rustication
      g.fillStyle = STONE;
      g.fillRect(0, Y(6.4), W, 6.4 * s);
      g.fillStyle = STONE_D;
      for (let z = 0.6; z < 6.2; z += 0.6) g.fillRect(0, Y(z), W, 2);
      for (let z = 0; z < 6; z += 1.2) {
        g.fillRect(0, Y(z + 0.6), 2, 0.6 * s);
        g.fillRect(W / 2, Y(z + 1.2), 2, 0.6 * s);
      }
      // stone bands across the brickwork
      g.fillStyle = STONE;
      for (let z = 7.2; z < 19; z += 1.35) g.fillRect(0, Y(z + 0.42), W, 0.42 * s);
      g.fillRect(0, Y(7.1), W, 0.7 * s);
      g.fillRect(0, Y(ZT), W, (ZT - 19.2) * s);
      g.fillStyle = STONE_D;
      g.fillRect(0, Y(19.6), W, 2);
    });
    // Ashlar for the stone frontispiece and tower: u = metres / 2.4, v = metres / 6.4.
    const ashlar = kit.paintedMaterial('va:ashlar', 128, 320, (g, W, H) => {
      g.fillStyle = STONE;
      g.fillRect(0, 0, W, H);
      const r = kit.rng(0.517);
      const ch = H / 10;
      for (let j = 0; j < 10; j++)
        for (let i = 0; i < 3; i++) {
          g.fillStyle = `rgba(${r() < 0.5 ? '150,140,115' : '255,250,235'},${0.05 + r() * 0.08})`;
          g.fillRect(((i + (j % 2) * 0.5) * W) / 3, j * ch, W / 3, ch);
        }
      g.fillStyle = 'rgba(150,140,118,0.6)';
      for (let j = 0; j < 10; j++) {
        g.fillRect(0, j * ch, W, 1.5);
        for (let i = 0; i < 3; i++) g.fillRect(((i + (j % 2) * 0.5) * W) / 3, j * ch, 1.5, ch);
      }
    });
    const courtMat = kit.paintedMaterial('va:court', 128, 256, (g, W, H) => {
      g.fillStyle = BRICK;
      g.fillRect(0, 0, W, H);
      g.fillStyle = '#cdb38a';
      for (let y = 20; y < H; y += 64) g.fillRect(0, y, W, 7);
      fillArch(g, 36, 40, 56, 116, WIN);
      fillArch(g, 36, 168, 56, 244, WIN);
    });
    const tileMat = kit.paintedMaterial(
      'va:tiles',
      256,
      256,
      (g, W, H) => {
        g.fillStyle = '#eef0ea';
        g.fillRect(0, 0, W, H);
        const r = kit.rng(0.417);
        const n = 16,
          c = W / n;
        for (let i = 0; i < n; i++)
          for (let j = 0; j < n; j++) {
            const k = r();
            g.fillStyle = k < 0.33 ? '#e3e8e3' : k < 0.66 ? '#d6dfdd' : '#f6f6f2';
            g.fillRect(i * c + 0.5, j * c + 0.5, c - 1, c - 1);
            if (k > 0.85) {
              g.strokeStyle = '#a9bfbf';
              g.beginPath();
              g.moveTo(i * c + 2, j * c + 2);
              g.lineTo(i * c + c - 2, j * c + c - 2);
              g.stroke();
            }
          }
      },
      { roughness: 0.3 },
    );
    const inscription = kit.paintedMaterial('va:inscription', 1024, 64, (g, W, H) => {
      g.fillStyle = STONE;
      g.fillRect(0, 0, W, H);
      g.fillStyle = '#7d7464';
      g.font = 'bold 40px serif';
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.fillText('VICTORIA  AND  ALBERT  MUSEUM', W / 2, H / 2 + 2);
    });

    // ---------- helpers ----------
    const R = (u0, v0, u1, v1) => [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ];
    const texWalls = (m, ring, z0, z1, bayW, vr = [0, 1], closed = true, skip = []) => {
      const n0 = closed ? ring.length : ring.length - 1;
      for (let k = 0; k < n0; k++) {
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
    const flat = (m, polys, z, down = false) => kit.cap(B, m, polys, z, { down, scale: 4 });
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
    const octagon = (m, u, v, z0, r, h, rTop = r, open = false) =>
      geo(
        m,
        new THREE.CylinderGeometry(rTop, r, h, 8, 1, open).rotateX(Math.PI / 2),
        u,
        v,
        z0 + h / 2,
        Math.PI / 8,
      );
    const cyl = (m, u, v, z0, r, h, seg = 10, rTop = r) =>
      geo(m, new THREE.CylinderGeometry(rTop, r, h, seg).rotateX(Math.PI / 2), u, v, z0 + h / 2);
    /** Solid of revolution (profile [[r, z], ...]) batched at (u, v, z0). */
    const lathe = (m, prof, u, v, z0, seg = 16, rot = 0) =>
      geo(
        m,
        new THREE.LatheGeometry(
          prof.map(([r, z]) => new THREE.Vector2(Math.max(r, 0.0001), z)),
          seg,
        ).rotateX(Math.PI / 2),
        u,
        v,
        z0,
        rot,
      );
    const roof = (
      ring,
      angle,
      eave,
      rise,
      kind = 'gabled',
      m = slateMat,
      wall = brick,
      overhang = 0.3,
    ) => kit.pitchedRoof(B, m, wall, ring, angle, eave, rise, kind, { overhang });
    // Standing draped figure (statue) of height h facing heading `a` (radians from +x).
    const FIG = [
      [0, 0],
      [0.2, 0],
      [0.19, 0.08],
      [0.16, 0.42],
      [0.13, 0.6],
      [0.16, 0.7],
      [0.15, 0.8],
      [0.065, 0.835],
      [0.07, 0.87],
      [0.085, 0.92],
      [0.06, 0.985],
      [0, 1],
    ];
    const figure = (m, u, v, z0, h, a = 0) => {
      lathe(
        m,
        FIG.map(([r, z]) => [r * h * 1.1, z * h]),
        u,
        v,
        z0,
        8,
      );
      // a forward-leaning arm / attribute block gives each figure a front
      box(
        m,
        u + Math.cos(a) * 0.12 * h,
        v + Math.sin(a) * 0.12 * h,
        z0 + 0.5 * h,
        0.1 * h,
        0.1 * h,
        0.2 * h,
        a,
      );
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
    const rectOutline = (z0, z1) => (sh, L) => {
      sh.moveTo(0, z0);
      sh.lineTo(L, z0);
      sh.lineTo(L, z1);
      sh.lineTo(0, z1);
      sh.closePath();
    };
    const eb = (f, m, s0, s1, w0, w1, z0, z1) => {
      const [x, y] = f.P((s0 + s1) / 2, (w0 + w1) / 2);
      kit.box(B, m, x, y, z0, s1 - s0, w1 - w0, z1 - z0, f.ang);
    };
    const SG = (f, m, g, s, z, w, rot = 0, sc = [1, 1, 1]) => {
      const L = new THREE.Matrix4().compose(
        new THREE.Vector3(s, z, w),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, rot)),
        new THREE.Vector3(...sc),
      );
      B.addGeometry(m, g, f.M(0).multiply(L));
      g.dispose();
    };
    const voussoirs = (f, s, zs, rIn, rOut, n, w0, d, mats = [stone], key = null) => {
      for (let k = 0; k < n; k++) {
        const t0 = (k * Math.PI) / n,
          t1 = ((k + 1) * Math.PI) / n;
        const sh = new THREE.Shape();
        const ro = key && k === (n - 1) / 2 ? rOut + key : rOut;
        sh.moveTo(s + rIn * Math.cos(t0), zs + rIn * Math.sin(t0));
        sh.lineTo(s + ro * Math.cos(t0), zs + ro * Math.sin(t0));
        sh.absarc(s, zs, ro, t0, t1, false);
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
    /** Triangular pediment in the wall plane, base width bw at z, rise h, projecting d. */
    const pediment = (f, m, s, z, bw, h, w0, d) => {
      const sh = new THREE.Shape();
      sh.moveTo(s - bw / 2, z);
      sh.lineTo(s + bw / 2, z);
      sh.lineTo(s, z + h);
      sh.closePath();
      addSplit(new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false }), f.M(w0), m, m);
    };
    /** Segmental pediment: arc of radius r over chord bw. */
    const segPediment = (f, m, s, z, bw, h, w0, d) => {
      const r = (bw * bw) / (8 * h) + h / 2,
        zc = z + h - r,
        t = Math.asin(bw / 2 / r);
      const sh = new THREE.Shape();
      sh.moveTo(s - bw / 2, z);
      sh.lineTo(s + bw / 2, z);
      sh.absarc(s, zc, r, Math.PI / 2 - t, Math.PI / 2 + t, false);
      sh.closePath();
      addSplit(
        new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false, curveSegments: 4 }),
        f.M(w0),
        m,
        m,
      );
    };
    /** Sash window filling inside an opening: frame, meeting rail, glazing bars. */
    const sashBars = (f, s, w, z0, z1, rows = 3, cols = 2, wf = 0.06) => {
      eb(f, sash, s - w / 2, s + w / 2, wf, wf + 0.06, z0, z0 + 0.08);
      eb(f, sash, s - w / 2, s + w / 2, wf, wf + 0.06, z1 - 0.08, z1);
      for (const e of [-1, 1])
        eb(f, sash, s + e * (w / 2) - 0.05, s + e * (w / 2) + 0.05, wf, wf + 0.06, z0, z1);
      for (let i = 1; i < rows; i++) {
        const z = z0 + ((z1 - z0) * i) / rows;
        eb(
          f,
          sash,
          s - w / 2,
          s + w / 2,
          wf,
          wf + (i === rows / 2 ? 0.09 : 0.05),
          z - 0.025,
          z + 0.025,
        );
      }
      for (let i = 1; i < cols; i++) {
        const x = s - w / 2 + (w * i) / cols;
        eb(f, sash, x - 0.025, x + 0.025, wf, wf + 0.05, z0, z1);
      }
    };

    // ---------- footprint base (all ranges up to 15 m, garden kept open) ----------
    const OUTER = [
      [-70.9, 174.8],
      [-72.4, 165.7],
      [-71.5, 165.6],
      [-76.4, 134.5],
      [-77.8, 134.7],
      [-79.1, 125.9],
      [-78.5, 125.8],
      [-78.6, 124.5],
      [-49.5, 119.6],
      [-50.2, 112.8],
      [-38.7, 115.6],
      [-41.5, 86.1],
      [-83.5, 87.7],
      [-84.5, 87.9],
      [-86.9, 73.4],
      [-99.7, 3.2],
      [-86.6, 1.0],
      [-86.4, 1.9],
      [-54.7, -2.1],
      [-54.6, -2.8],
      [-40.5, -3.4],
      [-40.2, 0.4],
      [-38.3, 1.2],
      [-38.3, 2.5],
      [-11.2, 1.2],
      [-11.2, 0.0],
      [11.3, -0.4],
      [30.9, -1.0],
      [59.6, -0.1],
      [60.0, -3.5],
      [74.1, -2.0],
      [74.1, -0.8],
      [119.2, 3.4],
      [118.3, 15.8],
      [116.5, 17.3],
      [112.6, 16.9],
      [111.5, 24.1],
      [122.9, 25.5],
      [126.1, 26.1],
      [124.9, 35.2],
      [117.1, 34.5],
      [98.6, 165.2],
      [94.5, 164.7],
      [94.0, 171.0],
      [84.2, 169.6],
      [83.9, 172.9],
      [77.2, 171.9],
      [76.6, 176.1],
      [50.0, 179.7],
      [33.2, 178.7],
      [23.1, 178.5],
      [-32.9, 178.1],
      [-35.5, 153.4],
      [-47.4, 155.1],
      [-43.9, 177.3],
      [-67.7, 181.0],
      [-68.7, 174.5],
    ].reverse(); // listed clockwise in the source -> make CCW
    const GARDEN = [
      [4.6, 86.2],
      [-25.2, 86.1],
      [-21.8, 129.5],
      [-7.7, 129.2],
      [-7.1, 127.3],
      [9.2, 126.0],
      [27.2, 126.0],
      [27.2, 129.4],
      [39.9, 129.9],
      [44.9, 86.3],
      [15.5, 86.0],
      [15.5, 87.7],
      [10.3, 87.6],
      [4.6, 87.7],
    ];
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const outer = ccw(OUTER),
      hole = ccw(GARDEN).slice().reverse(); // holes clockwise
    const baseIn = kit.offsetRing(outer, -0.5);
    // base walls, leaving out the edges that lie behind the modelled street fronts
    texWalls(
      courtMat,
      baseIn,
      0,
      15,
      4.5,
      [0, 1],
      true,
      baseIn
        .map((p, k) => [p, baseIn[(k + 1) % baseIn.length], k])
        .filter(
          ([p, q]) =>
            (p[1] < 6 && q[1] < 6) || (p[0] < -70 && q[0] < -70 && p[1] < 90 && q[1] < 90),
        )
        .map(([, , k]) => k),
    );
    texWalls(courtMat, hole, 0, 15, 4.5);
    flat(lead, [[baseIn, hole]], 15);
    kit.cornice(B, stoneD, baseIn, 14.5, { height: 0.5, projection: 0.25 });
    // garden (quadrangle) facades: terracotta string courses, pilasters and cornice
    {
      const terra = kit.mat('buff_terracotta');
      for (let k = 0; k < hole.length; k++) {
        const f = EF(hole[k], hole[(k + 1) % hole.length]);
        if (f.L < 1) continue;
        for (const z of [0, 6.4, 10.6]) eb(f, terra, 0, f.L, 0, 0.18, z, z + (z ? 0.35 : 0.6));
        eb(f, terra, 0, f.L, 0, 0.45, 14.2, 15.0);
        for (let s = 0.4; s < f.L - 0.3; s += 4.5)
          eb(f, terra, s - 0.25, s + 0.25, 0, 0.12, 0.6, 14.2);
      }
    }
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
      addSplit(
        new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: false, curveSegments: 7 }),
        f.M(w0),
        m,
        m,
      );
    };

    // ---------- modelled brick-and-stone fronts ----------
    const WD = 0.45;
    /** Aston Webb elevation on edge a -> b: wall plane at the edge, slab outward. */
    const front = (a, b, o = {}) => {
      const f = EF(a, b);
      const n = f.L >= 5.5 ? Math.max(1, Math.round(f.L / BAY)) : 0;
      const bw = n ? f.L / n : f.L;
      const cs = Array.from({ length: n }, (_, k) => (k + 0.5) * bw);
      const ns = Array.from({ length: Math.max(0, n - 1) }, (_, k) => (k + 1) * bw);
      const holes = [];
      for (const c of cs)
        holes.push(
          { k: 'a', s: c, w: 2.6, z0: 1.2, zs: 4.0 },
          { k: 'r', s: c, w: 2.3, z0: 7.7, z1: 13.6 },
          { k: 'r', s: c, w: 1.9, z0: 16.3, z1: 18.6 },
        );
      for (const s of ns) holes.push({ k: 'a', s, w: 1.0, z0: 8.6, zs: 12.9 });
      slab(f, rectOutline(0, 20.4), holes, WD, wall3d, stoneL, { su: 1 / 2.4, sv: 1 / ZT });
      for (const [k, c] of cs.entries()) {
        // glazing behind each opening
        eb(f, winGlass, c - 1.4, c + 1.4, -0.06, -0.02, 1.1, 5.4);
        eb(f, winGlass, c - 1.25, c + 1.25, -0.06, -0.02, 7.6, 13.7);
        eb(f, winGlass, c - 1.05, c + 1.05, -0.06, -0.02, 16.2, 18.7);
        // ground storey: round-arched window with voussoirs and keystone
        voussoirs(f, c, 4.0, 1.3, 1.75, 9, WD, 0.1, [stone, stoneD], 0.35);
        sashBars(f, c, 2.6, 1.2, 4.0, 2, 2);
        for (let i = 0; i < 5; i++) {
          const t = (i * Math.PI) / 4;
          SG(
            f,
            sash,
            new THREE.BoxGeometry(1.3, 0.05, 0.05),
            c + Math.cos(t) * 0.65,
            4.0 + Math.sin(t) * 0.65,
            0.09,
            t,
          );
        }
        eb(f, stoneD, c - 1.55, c + 1.55, WD, WD + 0.2, 1.0, 1.2);
        // first floor: architrave, frieze, alternating pediments, sill on consoles
        for (const e of [-1, 1])
          eb(f, stone, c + e * 1.3 - 0.17, c + e * 1.3 + 0.17, WD, WD + 0.12, 7.6, 13.9);
        eb(f, stone, c - 1.47, c + 1.47, WD, WD + 0.12, 13.6, 14.1);
        eb(f, stoneD, c - 1.62, c + 1.62, WD, WD + 0.3, 14.1, 14.3);
        (k % 2 ? segPediment : pediment)(f, stone, c, 14.3, 3.2, 0.8, WD, 0.28);
        eb(f, stoneD, c - 1.6, c + 1.6, WD, WD + 0.28, 7.4, 7.65);
        for (const e of [-1, 1])
          eb(f, stoneD, c + e * 1.2 - 0.12, c + e * 1.2 + 0.12, WD, WD + 0.22, 7.0, 7.4);
        sashBars(f, c, 2.3, 7.7, 13.6, 4, 2);
        // second floor: plain stone surround and sill
        for (const e of [-1, 1])
          eb(f, stone, c + e * 1.1 - 0.15, c + e * 1.1 + 0.15, WD, WD + 0.1, 16.2, 18.85);
        eb(f, stone, c - 1.25, c + 1.25, WD, WD + 0.1, 18.6, 18.9);
        eb(f, stoneD, c - 1.3, c + 1.3, WD, WD + 0.22, 16.05, 16.3);
        sashBars(f, c, 1.9, 16.3, 18.6, 2, 2);
      }
      // statue niches between the first-floor windows
      for (const s of ns) {
        eb(f, stoneD, s - 0.6, s + 0.6, -0.42, -0.36, 8.5, 13.6);
        for (const e of [-1, 1])
          eb(f, stoneD, s + e * 0.52 - 0.04, s + e * 0.52 + 0.04, -0.42, 0.02, 8.5, 13.6);
        eb(f, stoneD, s - 0.6, s + 0.6, -0.42, 0.02, 13.4, 13.6);
        eb(f, stone, s - 0.7, s + 0.7, WD, WD + 0.32, 8.25, 8.6); // bracket / pedestal
        eb(f, stone, s - 0.32, s + 0.32, -0.36, 0.25, 8.6, 8.95);
        const [x, y] = f.P(s, -0.06);
        figure(stoneL, x, y, 8.95, 2.15, f.ang - Math.PI / 2);
        voussoirs(f, s, 12.9, 0.5, 0.72, 5, WD, 0.08, [stone]);
        segPediment(f, stoneD, s, 13.7, 1.6, 0.4, WD, 0.3);
        eb(f, stoneD, s - 0.8, s + 0.8, WD, WD + 0.3, 13.55, 13.7);
      }
      // plinth, ground-storey cornice, first-floor sill band, main cornice with dentils
      eb(f, stoneD, 0, f.L, WD, WD + 0.18, 0, 0.6);
      eb(f, stone, 0, f.L, WD, WD + 0.25, 6.4, 6.75);
      eb(f, stoneD, 0, f.L, WD, WD + 0.35, 6.75, 7.0);
      eb(f, stone, 0, f.L, WD, WD + 0.3, 19.0, 19.6);
      for (let s = 0.2; s < f.L - 0.1; s += 0.42)
        eb(f, stone, s - 0.1, s + 0.1, WD + 0.3, WD + 0.45, 19.4, 19.6);
      eb(f, stone, 0, f.L, WD, WD + 0.75, 19.6, 20.15);
      eb(f, stoneD, 0, f.L, WD, WD + 0.8, 20.15, 20.4);
      // balustrade with pedestals over each pier
      kit.balustrade(B, stone, [f.P(0, WD + 0.2), f.P(f.L, WD + 0.2)], 20.4, {
        height: 1.15,
        spacing: 0.34,
      });
      for (const s of [0.3, ...ns, f.L - 0.3])
        eb(f, stone, s - 0.32, s + 0.32, WD - 0.1, WD + 0.5, 20.4, 21.75);
      // stone quoins at both ends of the brick wall
      if (o.quoins !== false)
        for (const [s, d] of [
          [0, 1],
          [f.L, -1],
        ])
          for (let z = 7.0, k = 0; z < 19; z += 0.68, k++) {
            const l = k % 2 ? 0.6 : 1.05;
            eb(f, stone, Math.min(s, s + d * l), Math.max(s, s + d * l), WD, WD + 0.07, z, z + 0.6);
          }
      return f;
    };

    // ---------- Cromwell Road range ----------
    {
      const frontW = [
        [-99.7, 3.2],
        [-86.6, 1.0],
        [-54.7, -2.1],
        [-40.5, -3.4],
        [-38.3, 1.2],
        [-11.2, 1.2],
      ];
      const frontE = [
        [11.3, -0.4],
        [30.9, -1.0],
        [59.6, -0.1],
        [60.0, -3.5],
        [74.1, -2.0],
        [119.2, 3.4],
      ];
      const D = 19;
      const westRing = [...frontW, [-11.2, D], [-96.6, D]];
      const eastRing = [...frontE, [118.0, D], [11.3, D]];
      texWalls(rangeMat, westRing, 0, RH, BAY, [0, 1], true, [0, 1, 2, 3, 4, 7]);
      texWalls(rangeMat, eastRing, 0, RH, BAY, [0, 1], true, [0, 1, 2, 3, 4]);
      for (const ring of [westRing, eastRing]) flat(lead, [[ring]], 20.4);
      for (const line of [frontW, frontE])
        for (let k = 0; k + 1 < line.length; k++) front(line[k], line[k + 1]);
      front(westRing[7], westRing[0]);
      // slate roofs behind the balustrade
      roof(R(-96, 3.5, -12, D - 1), 0, 20.4, 4.5);
      roof(R(12, 2.5, 117, D - 1), 0, 20.4, 4.5);
      // end and intermediate pavilions raised above the balustrade, with open cupolas
      for (const [u, v] of [
        [-93.5, 7],
        [110.5, 9],
        [-46.5, 4],
        [67, 3],
      ]) {
        const r = R(u - 6.5, v - 6, u + 6.5, v + 6);
        texWalls(kit.facade('portland_stone', 3), kit.offsetRing(r, -0.2), RH - 0.6, RH + 3.2, 3.2);
        for (const [du, dv] of [
          [-1, -1],
          [1, -1],
          [-1, 1],
          [1, 1],
        ])
          box(stone, u + du * 6.3, v + dv * 5.8, RH - 0.6, 0.9, 0.9, 3.9);
        kit.cornice(B, stoneD, r, RH + 2.9, { height: 0.6, projection: 0.35, steps: 2 });
        roof(
          R(u - 6.3, v - 5.8, u + 6.3, v + 5.8),
          0,
          RH + 3.5,
          3.0,
          'hipped',
          slateMat,
          stone,
          0.25,
        );
        // cupola: octagonal base, eight colonnettes, entablature, lead dome and finial
        const zc = RH + 5.6;
        octagon(stone, u, v, zc, 1.6, 0.9);
        for (let k = 0; k < 8; k++) {
          const t = (k * Math.PI) / 4 + Math.PI / 8;
          cyl(stone, u + Math.cos(t) * 1.25, v + Math.sin(t) * 1.25, zc + 0.9, 0.12, 2.0, 6, 0.1);
        }
        octagon(stoneD, u, v, zc + 2.9, 1.55, 0.45);
        lathe(
          leadD,
          [
            [1.45, 0],
            [1.42, 0.35],
            [1.3, 0.8],
            [1.05, 1.25],
            [0.7, 1.6],
            [0.3, 1.82],
            [0.12, 1.9],
            [0.14, 2.2],
            [0.07, 2.5],
            [0.12, 2.65],
            [0.0, 2.9],
          ],
          u,
          v,
          zc + 3.35,
          12,
        );
        geo(gold, new THREE.SphereGeometry(0.14, 8, 6), u, v, zc + 6.35);
      }
      // dormers on the roof slopes
      for (const [u0, u1] of [
        [-88, -16],
        [17, 104],
      ])
        for (let u = u0 + 3; u < u1; u += 6.6) {
          if (Math.abs(u + 46.5) < 7.5 || Math.abs(u - 67) < 7.5) continue;
          const d = R(u - 0.9, 5.2, u + 0.9, 8.2);
          texWalls(stone, d, 20.4, 22.4, 3);
          const df = EF(d[0], d[1]);
          eb(df, winGlass, 0.35, 1.45, -0.01, 0.03, 20.7, 22.1);
          sashBars(df, 0.9, 1.1, 20.7, 22.1, 2, 2, 0.04);
          roof(d, Math.PI / 2, 22.4, 1, 'gabled', slateMat, stone, 0.12);
        }
      // chimney stacks on the ridges
      for (const u of [-80, -62, -28, 28, 46, 88, 100]) {
        box(brick, u, 10.5, 22, 1.4, 2.8, 4.8);
        box(stone, u, 10.5, 26.8, 1.6, 3.0, 0.35);
        for (const dv of [-0.8, 0, 0.8])
          cyl(kit.mat('terracotta'), u, 10.5 + dv, 27.15, 0.16, 0.6, 6);
      }
    }

    // ---------- Exhibition Road range (north of the corner) ----------
    {
      const r2 = [
        [-96.6, 19],
        [-81.6, 19],
        [-72, 87.3],
        [-84.5, 87.9],
        [-86.9, 73.4],
      ];
      texWalls(rangeMat, r2, 0, RH, BAY, [0, 1], true, [3, 4]);
      flat(lead, [[r2]], 20.4);
      front(r2[4], r2[0]);
      front(r2[3], r2[4], { quoins: false });
    }

    // ---------- entrance frontispiece and central tower ----------
    {
      const v0 = -1.6,
        D = 2.0,
        FW = 22,
        FH = 25;
      const f = EF([-11, v0 + D], [11, v0 + D]);
      const c = FW / 2;
      const PW = 9.2,
        PS = 9.8;
      const outerNiche = [2.3, FW - 2.3].map((s) => ({ k: 'a', s, w: 1.8, z0: 5.5, zs: 10.6 }));
      const upperWin = [2.3, FW - 2.3].map((s) => ({ k: 'r', s, w: 2.0, z0: 18.6, z1: 22.0 }));
      const albert = { k: 'a', s: c, w: 2.4, z0: 15.4, zs: 19.6 };
      slab(
        f,
        (sh, L) => {
          sh.moveTo(0, 0);
          sh.lineTo(c - PW / 2, 0);
          sh.lineTo(c - PW / 2, PS);
          sh.absarc(c, PS, PW / 2, Math.PI, 0, true);
          sh.lineTo(c + PW / 2, 0);
          sh.lineTo(L, 0);
          sh.lineTo(L, FH);
          sh.lineTo(0, FH);
          sh.closePath();
        },
        [...outerNiche, ...upperWin, albert],
        D,
        ashlar,
        stoneL,
        { su: 1 / 2.4, sv: 1 / 6.4, seg: 8 },
      );
      texWalls(
        ashlar,
        [
          [11, v0 + D],
          [11, 16],
          [-11, 16],
          [-11, v0 + D],
        ],
        0,
        FH,
        2.4,
        [0, FH / 6.4],
        false,
      );
      flat(lead, [[R(-11, v0, 11, 16)]], FH);
      // receding orders of the arch, bronze doors and glazed fanlight
      archOrder(f, c, PW + 0.02, 7.8, 0, PS, 0, 1.4, stoneD);
      archOrder(f, c, 7.8, 6.4, 0, PS, 0, 0.8, stone);
      voussoirs(f, c, PS, PW / 2, PW / 2 + 0.7, 13, D, 0.18, [stone], 0.6);
      voussoirs(f, c, PS, 3.9, 4.1, 13, 1.4, 0.1, [stoneL]);
      for (const sg of [-1, 1]) {
        lathe(
          stoneL,
          [
            [0.3, 0],
            [0.3, 0.5],
            [0.2, 0.6],
            [0.18, 7.9],
            [0.3, 8.3],
            [0.32, 8.5],
            [0, 8.5],
          ],
          ...f.P(c + sg * 4.1, 1.55),
          PS - 8.5,
          10,
        );
      }
      eb(f, bronzeD, c - 3.2, c + 3.2, 0.02, 0.14, 0, 5.8);
      for (const s of [c - 3.2, c - 1.6, c, c + 1.6, c + 3.2])
        eb(f, bronze, s - 0.07, s + 0.07, 0.14, 0.2, 0, 5.8);
      for (const z of [0.9, 2.9, 4.9]) eb(f, bronze, c - 3.2, c + 3.2, 0.14, 0.18, z, z + 0.08);
      eb(f, stone, c - 3.25, c + 3.25, 0.02, 0.45, 5.8, 6.4);
      eb(f, winGlass, c - 3.2, c + 3.2, -0.02, 0.02, 6.4, PS + 3.2);
      for (let k = 0; k <= 8; k++) {
        const t = (k * Math.PI) / 8;
        SG(
          f,
          bronze,
          new THREE.BoxGeometry(3.1, 0.06, 0.06),
          c + Math.cos(t) * 1.55,
          PS + Math.sin(t) * 1.55,
          0.05,
          t,
        );
      }
      for (const z of [7.6, 8.8]) eb(f, bronze, c - 3.2, c + 3.2, 0.03, 0.07, z, z + 0.06);
      // paired columns on pedestals flanking the arch, entablature
      for (const sc of [c - 6.6, c - 5.4, c + 5.4, c + 6.6]) {
        const [x, y] = f.P(sc, D + 0.45);
        box(stoneD, x, y, 0, 1.0, 1.0, 1.6, f.ang);
        lathe(
          stoneL,
          [
            [0.5, 0],
            [0.5, 0.2],
            [0.42, 0.35],
            [0.38, 0.5],
            [0.33, 10.6],
            [0.36, 10.75],
            [0.48, 11.2],
            [0.0001, 11.2],
          ],
          x,
          y,
          1.6,
          14,
        );
        box(stone, x, y, 12.8, 0.95, 0.95, 0.25, f.ang);
      }
      eb(f, stone, c - 7.3, c + 7.3, D, D + 0.95, 13.05, 14.0);
      eb(f, stoneD, c - 7.5, c + 7.5, D, D + 1.15, 14.0, 14.5);
      // niches with Edward VII and Queen Alexandra flanking the entrance
      for (const h of outerNiche) {
        eb(f, stoneD, h.s - 1.0, h.s + 1.0, 0.5, 0.6, h.z0, h.zs + 1.0);
        eb(f, stone, h.s - 0.5, h.s + 0.5, 0.6, 1.3, h.z0, h.z0 + 0.5);
        figure(stoneL, ...f.P(h.s, 1.0), h.z0 + 0.5, 3.0, f.ang - Math.PI / 2);
        voussoirs(f, h.s, h.zs, 0.9, 1.25, 7, D, 0.12, [stone], 0.2);
        eb(f, stone, h.s - 1.2, h.s + 1.2, D, D + 0.3, h.z0 - 0.4, h.z0);
      }
      // upper windows with architraves and pediments
      for (const h of upperWin) {
        eb(f, winGlass, h.s - 1.1, h.s + 1.1, -0.06, -0.02, h.z0, h.z1);
        sashBars(f, h.s, 2.0, h.z0, h.z1, 3, 2, 0.1);
        for (const e of [-1, 1])
          eb(
            f,
            stone,
            h.s + e * 1.15 - 0.15,
            h.s + e * 1.15 + 0.15,
            D,
            D + 0.12,
            h.z0 - 0.15,
            h.z1 + 0.2,
          );
        pediment(f, stoneD, h.s, h.z1 + 0.2, 2.9, 0.7, D, 0.25);
        eb(f, stoneD, h.s - 1.4, h.s + 1.4, D, D + 0.25, h.z0 - 0.35, h.z0 - 0.1);
      }
      // Prince Albert in the niche over the arch, with canopy
      eb(f, stoneD, c - 1.3, c + 1.3, 0.8, 0.9, albert.z0, albert.zs + 1.3);
      eb(f, stone, c - 0.7, c + 0.7, 0.9, 1.8, albert.z0, albert.z0 + 0.6);
      figure(stoneL, ...f.P(c, 1.3), albert.z0 + 0.6, 3.1, f.ang - Math.PI / 2);
      voussoirs(f, c, albert.zs, 1.2, 1.6, 9, D, 0.15, [stone], 0.3);
      for (const e of [-1, 1])
        lathe(
          stoneL,
          [
            [0.2, 0],
            [0.16, 0.2],
            [0.15, 4.0],
            [0.24, 4.3],
            [0, 4.3],
          ],
          ...f.P(c + e * 1.55, D + 0.25),
          albert.z0,
          8,
        );
      // inscription frieze, top cornice, balustrade and urns
      B.quad(
        inscription,
        [...f.P(1.5, D + 0.03), 22.6],
        [...f.P(FW - 1.5, D + 0.03), 22.6],
        [...f.P(FW - 1.5, D + 0.03), 23.5],
        [...f.P(1.5, D + 0.03), 23.5],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      eb(f, stoneD, 0, FW, D, D + 0.3, 22.2, 22.5);
      eb(f, stone, 0, FW, D, D + 0.6, 23.9, 24.5);
      eb(f, stoneD, -0.2, FW + 0.2, D, D + 0.8, 24.5, 25.0);
      eb(f, stoneD, 0, FW, D, D + 0.4, 0, 0.7);
      kit.balustrade(B, stone, [f.P(0.5, D + 0.3), f.P(FW - 0.5, D + 0.3)], 25, {
        height: 1.0,
        spacing: 0.32,
      });
      for (const s of [0.5, 7.5, 14.5, 21.5]) {
        eb(f, stone, s - 0.45, s + 0.45, D - 0.1, D + 0.7, 25, 26.4);
        lathe(
          stone,
          [
            [0.3, 0],
            [0.18, 0.15],
            [0.42, 0.55],
            [0.3, 0.95],
            [0.12, 1.05],
            [0.18, 1.2],
            [0, 1.35],
          ],
          ...f.P(s, D + 0.3),
          26.4,
          10,
        );
      }
      // Queen Victoria on the frontispiece, flanked by St George and St Michael
      for (const [s, h] of [
        [c - 3.2, 2.6],
        [c, 3.4],
        [c + 3.2, 2.6],
      ]) {
        box(stone, ...f.P(s, D - 0.6), 25.0, 1.2, 1.2, 0.8, f.ang);
        figure(stoneL, ...f.P(s, D - 0.6), 25.8, h, f.ang - Math.PI / 2);
      }
      // steps
      for (let k = 0; k < 3; k++)
        box(stone, 0, v0 - 0.55 - k * 0.55, 0, 15 - k * 0.6, 0.6, 0.45 - k * 0.15);

      // ---------- tower ----------
      const tc = [0, 8];
      // stage 1: square stone stage with corner piers and arched openings, over the frontispiece
      const z1 = FH + 9;
      const sq = R(tc[0] - 6.5, tc[1] - 6.5, tc[0] + 6.5, tc[1] + 6.5);
      const sqi = kit.offsetRing(sq, -0.6);
      for (let e = 0; e < 4; e++) {
        const tf = EF(sqi[e], sqi[(e + 1) % 4]);
        const m = tf.L / 2;
        slab(
          tf,
          rectOutline(FH, z1),
          [{ k: 'a', s: m, w: 3.0, z0: FH + 1.4, zs: FH + 5.8 }],
          0.6,
          ashlar,
          stoneL,
          {
            su: 1 / 2.4,
            sv: 1 / 6.4,
          },
        );
        eb(tf, kit.mat('#1f2429'), m - 1.6, m + 1.6, -0.3, -0.25, FH + 1.3, FH + 7.4);
        eb(tf, winGlass, m - 1.6, m + 1.6, 0.05, 0.08, FH + 1.3, FH + 7.4);
        sashBars(tf, m, 3.0, FH + 1.4, FH + 5.8, 3, 3, 0.1);
        voussoirs(tf, m, FH + 5.8, 1.5, 2.0, 9, 0.6, 0.15, [stone, stoneD], 0.35);
        for (const e2 of [-1, 1])
          lathe(
            stoneL,
            [
              [0.25, 0],
              [0.18, 0.2],
              [0.16, 4.2],
              [0.26, 4.4],
              [0, 4.4],
            ],
            ...tf.P(m + e2 * 1.85, 0.8),
            FH + 1.4,
            8,
          );
        eb(tf, stoneD, m - 2.2, m + 2.2, 0.6, 0.9, FH + 1.0, FH + 1.4);
      }
      for (const [du, dv] of [
        [-1, -1],
        [1, -1],
        [-1, 1],
        [1, 1],
      ]) {
        box(stoneD, tc[0] + du * 6.3, tc[1] + dv * 6.3, FH, 1.8, 1.8, 9.7);
        for (let z = FH + 0.6; z < z1; z += 1.2)
          box(stone, tc[0] + du * 6.3, tc[1] + dv * 6.3, z, 1.9, 1.9, 0.12);
        cyl(stone, tc[0] + du * 6.3, tc[1] + dv * 6.3, z1 + 0.7, 0.45, 0.9, 10, 0.2);
        geo(
          stone,
          new THREE.SphereGeometry(0.32, 10, 6),
          tc[0] + du * 6.3,
          tc[1] + dv * 6.3,
          z1 + 1.8,
        );
      }
      flat(lead, [[sq]], z1 - 0.01);
      kit.cornice(B, stoneD, sq, z1 - 0.3, { height: 1.0, projection: 0.6, steps: 2 });
      // stage 2: octagonal drum ringed by sixteen columns, entablature and balustrade
      const z2 = z1 + 0.7;
      lathe(
        stoneD,
        [
          [6.6, 0],
          [6.6, 0.4],
          [6.2, 0.7],
          [0, 0.7],
        ],
        tc[0],
        tc[1],
        z1,
        16,
      );
      octagon(stone, tc[0], tc[1], z2, 4.6, 7.5);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4 + Math.PI / 8;
        const x = tc[0] + Math.cos(a) * 4.27,
          y = tc[1] + Math.sin(a) * 4.27;
        box(darkGlass, x, y, z2 + 1.2, 1.4, 0.1, 4.0, a + Math.PI / 2);
        box(
          stoneD,
          tc[0] + Math.cos(a) * 4.4,
          tc[1] + Math.sin(a) * 4.4,
          z2 + 1.0,
          1.8,
          0.3,
          0.2,
          a + Math.PI / 2,
        );
      }
      for (let k = 0; k < 16; k++) {
        const a = (k * Math.PI) / 8;
        lathe(
          stoneL,
          [
            [0.42, 0],
            [0.42, 0.18],
            [0.34, 0.3],
            [0.3, 0.42],
            [0.26, 6.7],
            [0.3, 6.85],
            [0.42, 7.2],
            [0.0001, 7.2],
          ],
          tc[0] + Math.cos(a) * 5.6,
          tc[1] + Math.sin(a) * 5.6,
          z2,
          10,
        );
        box(
          stone,
          tc[0] + Math.cos(a) * 5.6,
          tc[1] + Math.sin(a) * 5.6,
          z2 + 7.2,
          0.9,
          0.9,
          0.2,
          a,
        );
      }
      lathe(
        stone,
        [
          [5.0, 0],
          [6.15, 0],
          [6.15, 0.5],
          [6.05, 0.55],
          [6.05, 0.85],
          [6.5, 1.05],
          [6.55, 1.25],
          [5.0, 1.25],
        ],
        tc[0],
        tc[1],
        z2 + 7.4,
        24,
      );
      const z3 = z2 + 8.65;
      const ringPts = Array.from({ length: 17 }, (_, k) => {
        const a = (k * Math.PI) / 8;
        return [tc[0] + Math.cos(a) * 6.0, tc[1] + Math.sin(a) * 6.0];
      });
      kit.balustrade(B, stone, ringPts, z3, { height: 0.95, spacing: 0.34 });
      flat(lead, [[ringPts.slice(0, 16).map((p) => [p[0], p[1]])]], z3 - 0.02);
      // stage 3: smaller octagon with arched lights and statues at the angles
      octagon(stone, tc[0], tc[1], z3, 3.4, 4.6);
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4 + Math.PI / 8;
        box(
          darkGlass,
          tc[0] + Math.cos(a) * 3.16,
          tc[1] + Math.sin(a) * 3.16,
          z3 + 1.0,
          1.0,
          0.1,
          2.4,
          a + Math.PI / 2,
        );
        const b = (k * Math.PI) / 4;
        const x = tc[0] + Math.cos(b) * 4.1,
          y = tc[1] + Math.sin(b) * 4.1;
        box(stone, x, y, z3, 0.8, 0.8, 0.7, b);
        figure(stoneL, x, y, z3 + 0.7, 2.0, b);
      }
      lathe(
        stoneD,
        [
          [3.3, 0],
          [3.9, 0.25],
          [3.95, 0.55],
          [3.3, 0.6],
          [0, 0.6],
        ],
        tc[0],
        tc[1],
        z3 + 4.6,
        16,
      );
      // stage 4: the open imperial crown - ring with crosses and fleurs, eight arched ribs
      const z4 = z3 + 5.2,
        cr = 3.4,
        ch = 6.0;
      lathe(
        stone,
        [
          [cr - 0.35, 0],
          [cr + 0.25, 0],
          [cr + 0.35, 0.25],
          [cr + 0.25, 0.6],
          [cr - 0.35, 0.6],
        ],
        tc[0],
        tc[1],
        z4,
        24,
      );
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        const pts = [];
        for (let t = 0; t <= 1.0001; t += 0.1) {
          const r =
            cr * (1 + 0.28 * Math.sin(Math.PI * t * 0.9)) * Math.cos((t * Math.PI) / 2) ** 0.8;
          pts.push(
            new THREE.Vector3(
              Math.cos(a) * r,
              Math.sin(a) * r,
              ch * Math.sin((t * Math.PI) / 2) * (1 - 0.12 * t * t),
            ),
          );
        }
        const curve = new THREE.CatmullRomCurve3(pts);
        geo(stone, new THREE.TubeGeometry(curve, 14, 0.24, 6, false), tc[0], tc[1], z4 + 0.6);
        // pearls along each rib
        for (let t = 0.12; t < 0.95; t += 0.12) {
          const p = curve.getPoint(t);
          geo(
            stoneL,
            new THREE.SphereGeometry(0.17, 6, 4),
            tc[0] + p.x * 1.04,
            tc[1] + p.y * 1.04,
            z4 + 0.6 + p.z + 0.18,
          );
        }
        // crosses pattée and fleurs-de-lis alternating around the ring
        const b = a + Math.PI / 8;
        const x = tc[0] + Math.cos(b) * cr,
          y = tc[1] + Math.sin(b) * cr;
        box(stone, x, y, z4 + 0.6, 0.18, 0.18, 1.1, b);
        box(stone, x, y, z4 + 1.2, 0.6, 0.16, 0.18, b + Math.PI / 2);
        const x2 = tc[0] + Math.cos(a) * cr,
          y2 = tc[1] + Math.sin(a) * cr;
        cyl(stone, x2, y2, z4 + 0.6, 0.22, 0.7, 6, 0.05);
      }
      // orb, cross-pedestal and the gilt figure of Fame with her trumpet
      const zt = z4 + 0.6 + ch * 0.88;
      geo(stone, new THREE.SphereGeometry(0.85, 14, 10), tc[0], tc[1], zt + 0.6);
      lathe(
        stone,
        [
          [0.5, 0],
          [0.32, 0.3],
          [0.28, 0.9],
          [0.45, 1.1],
          [0, 1.1],
        ],
        tc[0],
        tc[1],
        zt + 1.3,
        10,
      );
      figure(bronze, tc[0], tc[1], zt + 2.4, 3.0, -Math.PI / 2 + 0.3);
      for (const sg of [-1, 1]) {
        const wg = new THREE.BoxGeometry(0.08, 1.4, 0.7);
        geo(bronze, wg, tc[0] + sg * 0.45, tc[1] + 0.25, zt + 4.6, sg * 0.5);
      }
      const tr = new THREE.CylinderGeometry(0.05, 0.14, 1.5, 6).rotateX(Math.PI / 2).rotateY(0.8);
      geo(gold, tr, tc[0] + 0.55, tc[1] - 0.25, zt + 5.3);
    }

    // ---------- Aston Webb Screen and Sackler Courtyard (Exhibition Road Quarter) ----------
    {
      const a0 = [-84.0, 87.8],
        a1 = [-78.1, 124.4];
      const len = Math.hypot(a1[0] - a0[0], a1[1] - a0[1]),
        ang = Math.atan2(a1[1] - a0[1], a1[0] - a0[0]);
      const at = (t, off = 0) => [
        a0[0] + ((a1[0] - a0[0]) * t) / len - Math.sin(ang) * -off,
        a0[1] + ((a1[1] - a0[1]) * t) / len + Math.cos(ang) * -off,
      ];
      const H = 12.7;
      // piers between open bays, entablature, attic with balustrade
      const nb = 11;
      for (let k = 0; k <= nb; k++) {
        const [u, v] = at((k * len) / nb);
        box(stone, u, v, 0, 0.9, 1.4, 9.2, ang + Math.PI / 2);
        cyl(stone, ...at((k * len) / nb, -1.0), 0, 0.4, 8.8, 10, 0.36);
        box(stone, ...at((k * len) / nb, -1.0), 8.8, 1.0, 1.0, 0.4, ang);
      }
      const [mu, mv] = at(len / 2);
      box(stone, mu, mv, 9.2, 2.2, len + 1.4, 1.6, ang - Math.PI / 2);
      box(stoneD, mu, mv, 10.8, 2.5, len + 1.8, 0.5, ang - Math.PI / 2);
      box(stone, mu, mv, 11.3, 1.2, len + 1.0, H - 11.3, ang - Math.PI / 2);
      kit.balustrade(B, stone, [at(0.3, -0.1), at(len - 0.3, -0.1)], H, {
        height: 1.0,
        spacing: 0.34,
      });
      for (let k = 0; k <= nb; k += 2)
        box(stone, ...at((k * len) / nb, -0.1), H, 0.7, 0.7, 1.3, ang);
      // perforated aluminium gates in some openings
      const gate = kit.mat('#a9adb0', {
        metalness: 0.6,
        roughness: 0.4,
        transparent: true,
        opacity: 0.55,
      });
      for (const k of [1, 3, 7, 9]) {
        const [u, v] = at(((k + 0.5) * len) / nb);
        box(gate, u, v, 0, 0.08, len / nb - 1.4, 4.2, ang - Math.PI / 2);
      }
      // porcelain-tiled courtyard paving
      const court = ccw([
        [-83.5, 87.7],
        [-41.5, 86.1],
        [-38.7, 115.6],
        [-50.2, 112.8],
        [-49.5, 119.6],
        [-78.6, 124.5],
      ]);
      flat(tileMat, [[court]], 0.15);
      // glazed oculus / lantern lighting the gallery below
      const ov = [-56, 96];
      cyl(glass, ov[0], ov[1], 0.15, 3.2, 0.7, 20);
      // cafe pavilion: glazed walls under a faceted tiled roof
      const cafe = ccw([
        [-63.6, 111.2],
        [-50.2, 112.8],
        [-49.5, 119.6],
        [-77.6, 124.3],
      ]);
      texWalls(darkGlass, cafe, 0, 4.2, 3);
      const c = cafe.reduce(
        (s, p) => [s[0] + p[0] / cafe.length, s[1] + p[1] / cafe.length],
        [0, 0],
      );
      const top = [c[0] - 2, c[1] + 1.5, 7.2];
      for (let k = 0; k < cafe.length; k++) {
        const a = cafe[k],
          b = cafe[(k + 1) % cafe.length];
        B.add(
          tileMat,
          [[a[0], a[1], 4.2], [b[0], b[1], 4.2], top],
          [
            [0, 0],
            [2, 0],
            [1, 1],
          ],
          [0, 1, 2],
        );
      }
      // the main museum wall facing the courtyard: new entrance glazing
      box(darkGlass, -40.2, 100, 0, 0.3, 12, 4.5, Math.atan2(29.5, 2.8) - Math.PI / 2);
    }

    // ---------- higher ranges and top-lit halls behind ----------
    // Cast Courts: two great top-lit halls in the south-east of the site.
    for (const [u0, v0, u1, v1] of [
      [62, 24, 108, 52],
      [62, 55, 104, 84],
    ]) {
      const r = R(u0, v0, u1, v1);
      texWalls(courtMat, r, 15, 24, 4.5, [0.4, 1]);
      roof(r, 0, 24, 6, 'hipped', slateMat, brick);
      const mid = (v0 + v1) / 2;
      // glazed ridge lantern
      const g = R(u0 + 6, mid - 3.5, u1 - 6, mid + 3.5);
      texWalls(glass, g, 28.3, 30.4, 3);
      roof(g, 0, 30.4, 1.6, 'gabled', glass, glass, 0.2);
    }
    // western galleries behind the Cromwell Road range
    for (const [u0, v0, u1, v1] of [
      [-82, 22, -50, 58],
      [-46, 22, -28, 60],
      [-80, 62, -46, 84],
      [-6, 66, 50, 82],
    ]) {
      const r = R(u0, v0, u1, v1);
      texWalls(courtMat, r, 15, 18, 4.5, [0.6, 1]);
      const along = u1 - u0 > v1 - v0 ? 0 : Math.PI / 2;
      roof(r, along, 18, 4, 'hipped', slateMat, brick);
      const g =
        along === 0
          ? R(u0 + 4, (v0 + v1) / 2 - 2, u1 - 4, (v0 + v1) / 2 + 2)
          : R((u0 + u1) / 2 - 2, v0 + 4, (u0 + u1) / 2 + 2, v1 - 4);
      roof(g, along, 20.6, 1.4, 'gabled', glass, glass, 0.1);
    }
    // ranges around the garden (Fowke / Sykes): pitched roofs with roof lights
    for (const [r, a] of [
      [R(-30, 132, 45, 150), 0],
      [R(-40, 84, -26, 132), Math.PI / 2],
      [R(46, 84, 60, 132), Math.PI / 2],
    ]) {
      texWalls(courtMat, r, 15, 19, 4.5, [0.5, 1]);
      roof(r, a, 19, 4.2, 'gabled', slateMat, courtMat);
    }
    for (let u = -22; u < 40; u += 12) {
      const r = R(u, 28, u + 8, 62);
      texWalls(courtMat, r, 15, 17, 4, [0.7, 1]);
      roof(r, Math.PI / 2, 17, 2.4, 'gabled', glass, brick, 0.2);
    }
    // glazed roof lanterns and plant on the open flat roofs
    for (const [u0, v0, u1, v1] of [
      [47, 24, 58, 82],
      [-40, 62, -30, 82],
      [-25, 66, -8, 82],
      [-28, 134, 40, 148],
    ]) {
      const r = R(u0, v0, u1, v1);
      texWalls(stoneD, r, 15, 15.9, 3);
      roof(r, u1 - u0 > v1 - v0 ? 0 : Math.PI / 2, 15.9, 1.4, 'gabled', glass, stoneD, 0.15);
    }
    for (const [u, v, w, d] of [
      [-60, 104, 6, 4],
      [80, 120, 8, 5],
      [88, 140, 5, 3],
    ]) {
      box(kit.mat('concrete'), u, v, 15, w, d, 2.2);
      for (let k = 0; k < Math.floor(w / 0.6); k++)
        box(kit.mat('dark_steel'), u - w / 2 + 0.3 + k * 0.6, v, 15.6, 0.06, d + 0.05, 1.2);
    }
    // north ranges and the Henry Cole Wing block on Exhibition Road
    {
      const hc = ccw([
        [-79.1, 125.9],
        [-50, 121],
        [-46, 154.9],
        [-43.9, 177.3],
        [-67.7, 181.0],
        [-72.4, 165.7],
        [-76.4, 134.5],
      ]);
      const hcIn = kit.offsetRing(hc, -0.3);
      texWalls(kit.facade('red_brick', 3), hcIn, 15, 24, 4.5);
      flat(lead, [[hcIn]], 24);
      roof(R(-71, 130, -51, 176), Math.PI / 2, 24, 4, 'hipped', slateMat, brick);
      const nr = R(-32, 152, 92, 172);
      texWalls(courtMat, nr, 15, 20, 4.5, [0.5, 1]);
      roof(nr, 0, 20, 4.5, 'gabled', slateMat, courtMat);
      for (let u = -25; u < 90; u += 14) box(glass, u, 162, 24.3, 8, 3, 0.3);
    }
    // notch infill (claimed small footprint)
    {
      const r = ccw([
        [-33.9, 169.2],
        [-33.4, 174.0],
        [-44.1, 175.8],
        [-44.9, 171.0],
      ]);
      texWalls(brickF, r, 0, 13, 4);
      flat(lead, [[r]], 13);
    }

    // ---------- John Madejski Garden: lawn, paving and elliptical pool ----------
    {
      const g = ccw(GARDEN);
      flat(paving, [[g]], 0.08);
      flat(grass, [[kit.offsetRing(g, -6)]], 0.14);
      const pool = new THREE.CircleGeometry(1, 40);
      geo(water, pool, 9.5, 108, 0.2, 0, 14, 9, 1);
      geo(stone, new THREE.TorusGeometry(1, 0.03, 4, 40), 9.5, 108, 0.2, 0, 14, 9, 8);
    }

    root.add(B.toGroup('victoria_and_albert_museum'));
    return root;
  },
};
