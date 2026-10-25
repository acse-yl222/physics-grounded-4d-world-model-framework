// Kensington Palace, Kensington Gardens (Wren / Hawksmoor 1689-1702, William Kent
// state apartments 1718-26) and the Orangery (Hawksmoor / Vanbrugh, 1704-05).
// Red brick palace of three storeys around three courts with stone-coped parapets,
// white-painted sash windows, hipped slate/lead roofs with tall chimney stacks, the
// eleven-bay south front (King's Gallery) with its central attic and urns, the
// clock-tower arch over Clock Court and the white marble Queen Victoria statue
// facing the Broad Walk. The Orangery is a long single-storey red/amber brick
// building with tall round-arched windows and a raised centre and end pavilions.
export default {
  id: 'kensington_palace',
  name: 'Kensington Palace and Orangery',
  claims: [
    'bb9186ea-2aa8-4013-937a-607071c25b42', // Kensington Palace (main ranges, three courts)
    '755e0c1f-1048-4ebf-b245-3b0f1c20c8db', // low range east of the north courts
    'e4f6979a-1775-4ba9-9785-42eed7a06a92', // low west range
    '20733963-5e33-4e82-b578-6041ba0b457a', // small east lean-to
    'e5dacc52-9a46-4e7a-b152-0f85bd654371', // The Orangery
  ],
  references: [
    {
      title: 'Kensington Palace - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Kensington_Palace',
      used_for:
        "Wren enlargement, south front with King's Gallery (Hawksmoor), brick rather than stone",
    },
    {
      title: 'Kensington Palace - Wren (All Souls College library)',
      url: 'https://library.asc.ox.ac.uk/wren/kensington_palace.html',
      used_for:
        "three-storey corner pavilions, cour d'honneur with clock-tower archway (Clock Court), 11-bay south block",
    },
    {
      title: 'Gardenvisit - Kensington Palace (London and its environs, 1927)',
      url: 'https://www.gardenvisit.com/book/london_and_its_environs_1927/11_hyde_park_and_kensington_gardens/kensington_palace',
      used_for: 'south front as Wren left it',
    },
    {
      title: 'The Orangery at Kensington Palace - Wallpaper',
      url: 'https://wallpaper.com/travel/the-orangery-at-kensington-palace-london-uk',
      used_for: 'English Baroque orangery by Hawksmoor 1704, enhanced by Vanbrugh',
    },
    {
      title: 'Grinling Gibbons carvings at Kensington Palace - Historic Royal Palaces',
      url: 'https://www.hrp.org.uk/blog/grinling-gibbons-carvings-at-kensington-palace/',
      used_for: 'Orangery as Vanbrugh/Hawksmoor collaboration',
    },
  ],
  notes:
    'Massing from the Overture outlines; parapet heights raised slightly over the 11.3 m footprint value for the ' +
    'state ranges (three tall storeys). Roofs are hipped per wing rectangle (approximate ridge layout); the ' +
    'position of the clock tower on the west range and of the Victoria statue east of the palace are estimated. ' +
    'Window rhythm is a generic painted Wren sash bay, not traced per elevation.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const rnd = kit.rng(0.4127);

    // ---- materials -------------------------------------------------------
    const brickMat = kit.mat('#8e4a36', { roughness: 0.92 });
    const stone = kit.mat('portland_stone');
    const white = kit.mat('white_render');
    const lead = kit.mat('lead');
    const slate = kit.roof('slate', 1);
    const leadRoof = kit.roof('lead', 0);
    const marble = kit.mat('#ecebe6', { roughness: 0.5 });
    const gold = kit.mat('gold');
    const dark = kit.mat('dark_glass');

    // Painted elevation: 4 bays x 2 storeys of red brick with rubbed-brick window
    // dressings, white sash frames with glazing bars and a stone string course.
    function brickBay(
      key,
      { arched = false, wall = '#93503a', storeyBand = true, sashRows = 4 } = {},
    ) {
      return kit.paintedMaterial(key, 512, 256, (c, w, h) => {
        const r = kit.rng(key.length * 0.0137 + 0.21);
        c.fillStyle = wall;
        c.fillRect(0, 0, w, h);
        // brick courses
        for (let y = 0; y < h; y += 4)
          for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
            const k = 0.85 + r() * 0.3;
            const col = new THREE.Color(wall).multiplyScalar(k);
            c.fillStyle = '#' + col.getHexString();
            c.fillRect(x + 0.5, y + 0.5, 11, 3);
          }
        const bw = w / 4,
          fh = h / 2;
        for (let f = 0; f < 2; f++) {
          if (storeyBand) {
            c.fillStyle = '#d8cfbd';
            c.fillRect(0, f * fh + fh - 5, w, 4);
          }
          for (let b = 0; b < 4; b++) {
            const ww = bw * 0.42,
              wh = fh * (arched ? 0.72 : 0.62),
              x0 = b * bw + (bw - ww) / 2,
              y0 = f * fh + fh * (arched ? 0.14 : 0.18);
            // rubbed brick dressing
            c.fillStyle = '#b5664a';
            c.fillRect(x0 - 4, y0 - 6, ww + 8, wh + 8);
            c.fillStyle = '#f1efe9';
            c.fillRect(x0 - 1, y0 - 1, ww + 2, wh + 2);
            c.fillStyle = '#34404a';
            if (arched) {
              c.beginPath();
              c.moveTo(x0 + 2, y0 + wh - 1);
              c.lineTo(x0 + 2, y0 + ww / 2);
              c.arc(x0 + ww / 2, y0 + ww / 2, ww / 2 - 2, Math.PI, 0);
              c.lineTo(x0 + ww - 2, y0 + wh - 1);
              c.fill();
            } else c.fillRect(x0 + 2, y0 + 2, ww - 4, wh - 4);
            // glazing bars
            c.fillStyle = '#f1efe9';
            for (let i = 1; i < 3; i++) c.fillRect(x0 + (ww * i) / 3 - 1, y0, 2, wh);
            for (let i = 1; i < sashRows; i++) c.fillRect(x0, y0 + (wh * i) / sashRows - 1, ww, 2);
            c.fillRect(x0, y0 + wh / 2 - 2, ww, 3);
          }
        }
      });
    }
    const palaceWall = brickBay('kensington_palace:sash');
    const orangeryWall = brickBay('kensington_palace:orangery', {
      arched: true,
      wall: '#9b5a3e',
      storeyBand: false,
      sashRows: 6,
    });

    // ---- helpers -----------------------------------------------------------
    const area = (ring) => kit.ringArea(ring);
    function band(ring, z0, z1, out, m) {
      // projecting band (cornice / plinth) with top and bottom caps
      const o = kit.offsetRing(ring, out);
      kit.walls(batch, m, [[o]], z0, z1);
      const poly = area(ring) > 0 ? [o, ring.slice().reverse()] : [ring.slice().reverse(), o];
      kit.cap(batch, m, [poly], z1);
      kit.cap(batch, m, [poly], z0, { down: true });
    }
    function parapet(ring, z0, h, t, wallM, capM) {
      const inner = kit.offsetRing(ring, -t);
      kit.walls(batch, wallM, [[ring]], z0, z0 + h);
      kit.walls(batch, wallM, [[inner.slice().reverse()]], z0, z0 + h);
      const poly =
        area(ring) > 0 ? [ring, inner.slice().reverse()] : [inner.slice().reverse(), ring];
      kit.cap(batch, capM, [poly], z0 + h);
    }
    const A = (16 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A),
      OX = 860,
      OY = -150;
    const L = (x, y) => [OX + x * ca - y * sa, OY + x * sa + y * ca];
    const rect = (x0, y0, x1, y1) => [L(x0, y0), L(x1, y0), L(x1, y1), L(x0, y1)];
    const localMesh = (geo, m, x, y, z, rz = 0) => {
      const p = L(x, y);
      const mesh = new THREE.Mesh(geo, m);
      mesh.position.set(p[0], p[1], z);
      mesh.rotation.z = A + rz;
      g.add(mesh);
      return mesh;
    };
    const lbox = (m, x, y, z0, w, d, h) => {
      const p = L(x, y);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, A);
    };

    // ---- palace ranges -----------------------------------------------------
    const main = byId['bb9186ea-2aa8-4013-937a-607071c25b42'];
    const EAVE = 12.2; // top of wall (stone cornice), three storeys
    for (const poly of main.polys) {
      kit.walls(batch, palaceWall, [poly], 0, EAVE, { bay: 3.3, storey: 4.1 });
      for (const ring of poly) {
        band(ring, 0, 0.6, 0.15, stone);
        band(ring, EAVE - 0.55, EAVE, 0.35, stone);
        parapet(ring, EAVE, 1.1, 0.4, brickMat, stone);
      }
      kit.cap(batch, lead, [poly], EAVE + 0.2);
    }
    // Hipped roofs per wing (local frame: x ~ east, y ~ north, rotated 16 deg).
    const wings = [
      // [x0, y0, x1, y1, ridge along x?, rise]
      [9.5, -33.4, 48.6, -18, true, 4.2], // south range (King's Gallery)
      [26.6, -33.4, 48.6, 9.0, false, 4.6], // east range (King's State Apartments)
      [-22.1, -30.2, 9.5, -18, true, 3.6], // south-centre range
      [9.5, -16, 24.6, 5.0, false, 3.6], // east side of the south court
      [-46.6, -47.8, -24.1, -29.7, false, 4.4], // south-west pavilion block
      [-50.9, -27.7, -24.7, -12.2, true, 3.8],
      [-40.1, -11.5, -24.7, 5.0, false, 3.6], // west side of the south court
      [-40.1, 7.0, -24.7, 60.0, false, 3.8], // west range
      [-22.7, 41.8, 24.6, 58.2, true, 3.6], // north range
      [-7.1, 15.4, 0.2, 40.8, false, 2.6], // spine between the north courts
      [-22.7, 7.0, 24.6, 13.4, true, 2.8], // range between south and north courts
      [16.4, 7.0, 24.6, 56.2, false, 3.0], // east of north-east court
    ];
    const roofTops = [];
    for (const [x0, y0, x1, y1, alongX, rise] of wings) {
      const ring = rect(x0, y0, x1, y1);
      const r = kit.pitchedRoof(
        batch,
        slate,
        brickMat,
        ring,
        alongX ? A : A + Math.PI / 2,
        EAVE + 0.2,
        rise,
        'hipped',
        {
          overhang: 0,
        },
      );
      roofTops.push({ x0, y0, x1, y1, alongX, top: r.top });
    }
    // Tall brick chimney stacks along the ridges.
    for (const w of roofTops) {
      const len = w.alongX ? w.x1 - w.x0 : w.y1 - w.y0;
      const n = Math.max(1, Math.round(len / 11));
      for (let k = 0; k < n; k++) {
        const t = (k + 0.5) / n;
        for (const side of [-1, 1]) {
          if (rnd() < 0.35) continue;
          const off = side * (w.alongX ? w.y1 - w.y0 : w.x1 - w.x0) * 0.22;
          const x = w.alongX ? w.x0 + len * t : (w.x0 + w.x1) / 2 + off;
          const y = w.alongX ? (w.y0 + w.y1) / 2 + off : w.y0 + len * t;
          const cw = 1.2 + rnd() * 1.6;
          lbox(brickMat, x, y, EAVE, w.alongX ? cw : 1.0, w.alongX ? 1.0 : cw, w.top - EAVE + 1.6);
          lbox(
            stone,
            x,
            y,
            w.top + 1.6,
            (w.alongX ? cw : 1.0) + 0.25,
            (w.alongX ? 1.0 : cw) + 0.25,
            0.3,
          );
        }
      }
    }
    // South front: central attic storey with urns over the King's Gallery.
    {
      const cx = 32,
        y = -34.4;
      lbox(brickMat, cx, y + 2.2, EAVE, 15, 4.4, 4.0);
      lbox(stone, cx, y + 2.2, EAVE + 4.0, 15.6, 5.0, 0.5);
      for (let k = 0; k < 4; k++) {
        const x = cx - 5.4 + k * 3.6;
        lbox(white, x, y - 0.05, EAVE + 0.9, 1.0, 0.1, 2.3);
        lbox(dark, x, y - 0.08, EAVE + 1.1, 0.7, 0.1, 1.9);
      }
      for (let k = 0; k < 6; k++) {
        const x = 15 + k * 6.8;
        const urn = new THREE.LatheGeometry(
          [
            [0, 0],
            [0.35, 0],
            [0.25, 0.25],
            [0.45, 0.7],
            [0.3, 1.1],
            [0.12, 1.2],
            [0.15, 1.45],
            [0, 1.5],
          ].map(([a, b]) => new THREE.Vector2(a, b)),
          10,
        ).rotateX(Math.PI / 2);
        localMesh(urn, stone, x, y + 0.2, EAVE + (Math.abs(x - cx) < 8 ? 4.5 : 1.1));
      }
      // Stone doorcase with segmental pediment at the centre of the ground floor.
      lbox(stone, cx, y - 0.2, 0, 3.6, 0.5, 4.6);
      lbox(dark, cx, y - 0.48, 0, 2.0, 0.1, 3.6);
    }
    // East front: Kent's state rooms - stone quoins at the corners and three-bay centre.
    for (const [x, y] of [
      [49.6, -34.4],
      [49.6, 10.0],
      [49.6, -12],
    ])
      lbox(stone, x - 0.3, y, 0, 0.8, 1.2, EAVE);

    // Clock tower over the Clock Court archway (west range).
    {
      const x = -32,
        y = -2;
      lbox(brickMat, x, y, EAVE, 5.2, 5.2, 4.2);
      lbox(stone, x, y, EAVE + 4.2, 5.8, 5.8, 0.5);
      for (const [dx, dy, rz] of [
        [0, -2.64, 0],
        [0, 2.64, Math.PI],
        [2.64, 0, Math.PI / 2],
        [-2.64, 0, -Math.PI / 2],
      ]) {
        const face = localMesh(
          new THREE.CircleGeometry(1.3, 20).rotateX(Math.PI / 2),
          kit.mat('#1f3550'),
          x + dx,
          y + dy,
          EAVE + 2.2,
          rz,
        );
        face.rotation.z += 0;
        localMesh(
          new THREE.TorusGeometry(1.3, 0.12, 4, 20).rotateX(Math.PI / 2),
          gold,
          x + dx * 1.01,
          y + dy * 1.01,
          EAVE + 2.2,
          rz,
        );
      }
      // white-painted timber cupola with lead dome and weather vane
      localMesh(
        new THREE.CylinderGeometry(1.6, 1.6, 2.6, 8).rotateX(Math.PI / 2),
        white,
        x,
        y,
        EAVE + 6.0,
        Math.PI / 8,
      );
      const dome = localMesh(
        new THREE.SphereGeometry(1.75, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(Math.PI / 2),
        lead,
        x,
        y,
        EAVE + 7.3,
      );
      dome.scale.z = 1.2;
      localMesh(
        new THREE.CylinderGeometry(0.06, 0.06, 2.2, 4).rotateX(Math.PI / 2),
        gold,
        x,
        y,
        EAVE + 10.1,
      );
      localMesh(new THREE.BoxGeometry(1.2, 0.05, 0.4), gold, x + 0.3, y, EAVE + 10.6);
    }
    // Arched gateway into Clock Court through the low west range.
    lbox(stone, -46.5, -2, 0, 0.6, 4.2, 4.2);

    // ---- low ranges (two storeys, brick, pitched roofs) ------------------------
    for (const id of [
      '755e0c1f-1048-4ebf-b245-3b0f1c20c8db',
      'e4f6979a-1775-4ba9-9785-42eed7a06a92',
      '20733963-5e33-4e82-b578-6041ba0b457a',
    ]) {
      const b = byId[id];
      if (!b) continue;
      const top = Math.max(b.h, 3.5);
      kit.walls(batch, b.h > 5 ? palaceWall : brickMat, b.polys, 0, top, {
        bay: 3.3,
        storey: Math.min(3.2, top / 2),
        uvBase: 0,
      });
      for (const poly of b.polys)
        for (const ring of poly) parapet(ring, top, 0.6, 0.3, brickMat, stone);
      kit.cap(batch, lead, b.polys, top + 0.1);
    }
    kit.pitchedRoof(
      batch,
      slate,
      brickMat,
      rect(26.4, -1.4, 35.4, 36.4),
      A + Math.PI / 2,
      6.3,
      2.4,
      'hipped',
      { overhang: 0 },
    );
    kit.pitchedRoof(
      batch,
      slate,
      brickMat,
      rect(-50, 3.2, -42.6, 48),
      A + Math.PI / 2,
      6.0,
      2.2,
      'hipped',
      { overhang: 0 },
    );

    // ---- Orangery ---------------------------------------------------------------
    {
      const b = byId['e5dacc52-9a46-4e7a-b152-0f85bd654371'];
      const H = 7.2;
      // local frame of the Orangery: long axis ~ local x from 38.3 to 92.2, y 152.3..163.9
      kit.walls(batch, orangeryWall, b.polys, 0, H, { bay: 4.0, storey: H * 0.98 });
      for (const ring of b.polys[0]) {
        band(ring, 0, 0.5, 0.15, stone);
        band(ring, H - 0.5, H, 0.35, stone);
        parapet(ring, H, 1.0, 0.35, brickMat, stone);
      }
      kit.cap(batch, lead, b.polys, H + 0.1);
      kit.pitchedRoof(
        batch,
        leadRoof,
        brickMat,
        rect(41, 153.4, 89.5, 162.8),
        A,
        H + 0.1,
        2.0,
        'hipped',
        { overhang: 0 },
      );
      // raised central frontispiece (three bays) and end pavilions on the south face
      const yS = 152.3;
      const pav = (cx, w, h) => {
        lbox(brickMat, cx, (yS + 163.9) / 2, 0, w, 11.9, h);
        lbox(stone, cx, (yS + 163.9) / 2, h, w + 0.6, 12.5, 0.5);
        lbox(brickMat, cx, (yS + 163.9) / 2, h + 0.5, w - 0.4, 11.5, 0.9);
        lbox(stone, cx, (yS + 163.9) / 2, h + 1.4, w, 11.9, 0.15);
        // rusticated stone surround / pilasters at the corners of the pavilion
        for (const s of [-1, 1]) lbox(stone, cx + (s * w) / 2, yS - 0.05, 0, 0.7, 0.5, h);
      };
      pav(65.25, 13.5, 9.0);
      pav(41.6, 6.5, 8.3);
      pav(88.9, 6.5, 8.3);
      // tall round-arched windows on the pavilions (south face)
      for (const [cx, n] of [
        [65.25, 3],
        [41.6, 1],
        [88.9, 1],
      ])
        for (let k = 0; k < n; k++) {
          const x = cx + (k - (n - 1) / 2) * 3.8;
          lbox(white, x, yS - 0.12, 1.0, 2.0, 0.2, 5.0);
          lbox(dark, x, yS - 0.2, 1.15, 1.6, 0.1, 4.7);
          localMesh(
            new THREE.CircleGeometry(1.0, 12, 0, Math.PI).rotateX(Math.PI / 2),
            white,
            x,
            yS - 0.23,
            6.0,
          );
          localMesh(
            new THREE.CircleGeometry(0.8, 12, 0, Math.PI).rotateX(Math.PI / 2),
            dark,
            x,
            yS - 0.26,
            5.85,
          );
        }
      // Doric columns flanking the central doorway
      for (const dx of [-2.8, 2.8])
        localMesh(
          new THREE.CylinderGeometry(0.35, 0.4, 6.4, 10).rotateX(Math.PI / 2),
          stone,
          65.25 + dx,
          yS - 0.7,
          3.2,
        );
    }

    // ---- Queen Victoria statue (Princess Louise, 1893) facing the Broad Walk ----------
    {
      const x = 72,
        y = -12;
      lbox(stone, x, y, 0, 4.4, 4.4, 0.6);
      lbox(marble, x, y, 0.6, 2.4, 2.4, 2.6);
      lbox(marble, x, y, 3.2, 2.8, 2.8, 0.3);
      localMesh(
        new THREE.CylinderGeometry(0.55, 0.9, 2.4, 10).rotateX(Math.PI / 2),
        marble,
        x,
        y,
        4.7,
      );
      localMesh(new THREE.SphereGeometry(0.32, 8, 6), marble, x, y, 6.1);
    }

    g.add(batch.toGroup('kensington_palace'));
    return g;
  },
};
