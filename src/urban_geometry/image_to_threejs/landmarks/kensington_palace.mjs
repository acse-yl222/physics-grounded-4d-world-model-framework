// Kensington Palace, Kensington Gardens (Wren / Hawksmoor 1689-1702, William Kent
// state apartments 1718-26) and the Orangery (Hawksmoor / Vanbrugh, 1704-05).
// Red brick palace of three storeys around three courts with stone string courses,
// a stone cornice and brick parapet with stone coping, white-painted six-over-six
// sash windows in rubbed-brick surrounds, hipped slate/lead roofs with tall chimney
// stacks, the south front (King's Gallery) with its central attic and urns, the
// clock-tower arch over Clock Court, the white marble Queen Victoria statue facing
// the Broad Walk and the bronze William III statue before the south front. The
// Orangery is a long single-storey red/amber brick building of 13 bays with tall
// round-arched windows; the three centre bays are set forward under a split
// segmental pediment.
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
      title: 'Gardenvisit - Kensington Gardens (London and its environs, 1927)',
      url: 'https://www.gardenvisit.com/book/london_and_its_environs_1927/11_hyde_park_and_kensington_gardens/kensington_gardens',
      used_for: 'William III statue (Baucke, 1907) in front of the south side; Broad Walk',
    },
    {
      title: 'Treasures of London - Queen Victoria outside Kensington Palace (Exploring London)',
      url: 'https://exploring-london.com/2019/07/26/treasures-of-london-queen-victoria-outside-kensington-palace/',
      used_for: 'seated marble Queen Victoria by Princess Louise (1893) on the east front',
    },
    {
      title: 'Orangery at Kensington Palace - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101223783-orangery-at-kensington-palace-campden-ward',
      used_for:
        'one storey, red and amber brick, 13 bays, three centre bays set forward with split segmental pediment',
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
    'position of the clock tower on the west range, of the Victoria statue east of the palace and of the ' +
    "William III statue south of the King's Gallery are estimated. Sash windows are real geometry (frames, " +
    'glazing bars, rubbed-brick surrounds, stone sills) at a regular 3.3 m bay on every elevation, not traced ' +
    'per elevation; storey heights estimated. Statues are simplified figures. Orangery end pavilions estimated.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const rnd = kit.rng(0.4127);

    // ---- materials -------------------------------------------------------
    const brickMat = kit.mat('#8e4a36', { roughness: 0.92 });
    const rubbed = kit.mat('#b0603f', { roughness: 0.85 });
    const stone = kit.mat('portland_stone');
    const stoneD = kit.mat('#cfc6b1', { roughness: 0.85 });
    const white = kit.mat('#f2f0ea', { roughness: 0.55 });
    const lead = kit.mat('lead');
    const slate = kit.roof('slate', 1);
    const leadRoof = kit.roof('lead', 0);
    const marble = kit.mat('#ecebe6', { roughness: 0.45 });
    const bronze = kit.mat('#5b4a33', { roughness: 0.45, metalness: 0.6 });
    const gold = kit.mat('gold');
    const sashGlass = kit.mat('#3a4a57', { roughness: 0.2, metalness: 0.15 });
    const door = kit.mat('#2a2622', { roughness: 0.6 });
    const iron = kit.mat('#1d1f22', { roughness: 0.5, metalness: 0.4 });
    const pot = kit.mat('#a85a3a', { roughness: 0.9 });
    const gravel = kit.mat('gravel');
    const paving = kit.mat('#c6bfae', { roughness: 0.95 });

    // Plain brick elevation (Flemish bond with burnt headers, slight variation); the
    // windows are real geometry.
    const brickTex = (key, wall) =>
      kit.paintedMaterial(
        key,
        512,
        256,
        (c, w, h) => {
          const r = kit.rng(key.length * 0.0137 + 0.21);
          c.fillStyle = '#9d8f7d';
          c.fillRect(0, 0, w, h);
          for (let y = 0, row = 0; y < h; y += 4, row++)
            for (let x = row % 2 ? -4 : 0, i = 0; x < w; x += 8, i++) {
              const header = i % 2 === 1;
              const k = (header ? 0.72 : 0.9) + r() * 0.22;
              const col = new THREE.Color(wall).multiplyScalar(k);
              c.fillStyle = '#' + col.getHexString();
              c.fillRect(x + 0.5, y + 0.5, header ? 3 : 7, 3);
            }
          for (let i = 0; i < 60; i++) {
            c.fillStyle = `rgba(40,20,10,${0.03 + r() * 0.05})`;
            c.fillRect(r() * w, r() * h, 10 + r() * 50, 4 + r() * 20);
          }
        },
        { vertexColors: true, roughness: 0.92 },
      );
    const palaceWall = brickTex('kensington_palace:brick2', '#93503a');
    const orangeryWall = brickTex('kensington_palace:orangery2', '#a8673f');
    const tint = () => {
      const k = 0.92 + rnd() * 0.08;
      return [k, k * (0.98 + rnd() * 0.03), k * (0.97 + rnd() * 0.03)];
    };

    // ---- helpers -----------------------------------------------------------
    const area = (ring) => kit.ringArea(ring);
    function band(ring, z0, z1, out, m) {
      const o = kit.offsetRing(ring, out);
      kit.walls(batch, m, [[o]], z0, z1, { bay: 1e6 });
      const poly = area(ring) > 0 ? [o, ring.slice().reverse()] : [ring.slice().reverse(), o];
      kit.cap(batch, m, [poly], z1);
      kit.cap(batch, m, [poly], z0, { down: true });
    }
    function parapet(ring, z0, h, t, wallM, capM) {
      const inner = kit.offsetRing(ring, -t);
      kit.walls(batch, wallM, [[ring]], z0, z0 + h, { bay: 1e6 });
      kit.walls(batch, wallM, [[inner.slice().reverse()]], z0, z0 + h, { bay: 1e6 });
      const co = kit.offsetRing(ring, 0.08),
        ci = kit.offsetRing(ring, -t - 0.06);
      const poly = area(ring) > 0 ? [co, ci.slice().reverse()] : [ci.slice().reverse(), co];
      kit.cap(batch, capM, [poly], z0 + h + 0.12);
      kit.walls(batch, capM, [[co]], z0 + h, z0 + h + 0.12, { bay: 1e6 });
    }
    const A = (16 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A),
      OX = 860,
      OY = -150;
    const L = (x, y) => [OX + x * ca - y * sa, OY + x * sa + y * ca];
    const rect = (x0, y0, x1, y1) => [L(x0, y0), L(x1, y0), L(x1, y1), L(x0, y1)];
    const lbox = (m, x, y, z0, w, d, h, rz = 0) => {
      const p = L(x, y);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, A + rz);
    };
    const lgeo = (geo, m, x, y, z, rz = 0) => {
      const p = L(x, y);
      batch.addGeometry(
        m,
        geo,
        new THREE.Matrix4().makeRotationZ(A + rz).setPosition(p[0], p[1], z),
      );
      geo.dispose();
    };
    const lathe = (m, prof, x, y, z, seg = 16) =>
      lgeo(
        new THREE.LatheGeometry(
          prof.map(([r, h]) => new THREE.Vector2(r, h)),
          seg,
        ).rotateX(Math.PI / 2),
        m,
        x,
        y,
        z,
      );
    const cyl = (m, r0, r1, h, x, y, z, seg = 12) =>
      lgeo(new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2), m, x, y, z + h / 2);
    // Round-arched window row: kit.windowRow for the rectangular part, plus the arch
    // frame ring and a half-disc of glass in the wall plane for the head.
    const archRow = (a, b, z, o) => {
      kit.windowRow(batch, a, b, z, { ...o, head: 'none' });
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy),
        ux = dx / len,
        uy = dy / len,
        ang = Math.atan2(dy, dx);
      const margin = o.margin ?? 0.6,
        bay = o.bay ?? 3.6,
        depth = o.depth ?? 0.12;
      const usable = len - 2 * margin;
      const n = o.count ?? Math.max(0, Math.floor(usable / bay + 0.35));
      const r = o.width / 2;
      const rot = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      for (let k = 0; k < n; k++) {
        const t = margin + (usable * (k + 0.5)) / n;
        const cx = a[0] + ux * t,
          cy = a[1] + uy * t;
        const disc = new THREE.CircleGeometry(r, 12, 0, Math.PI).rotateX(Math.PI / 2);
        batch.addGeometry(
          o.glass,
          disc,
          new THREE.Matrix4()
            .makeRotationZ(ang)
            .setPosition(cx + uy * 0.03, cy - ux * 0.03, z + o.height),
        );
        disc.dispose();
        const ringG = new THREE.TorusGeometry(r + 0.04, 0.07, 4, 12, Math.PI);
        const m = rot
          .clone()
          .setPosition(cx + uy * depth * 0.9, cy - ux * depth * 0.9, z + o.height);
        batch.addGeometry(o.sill ?? o.frame, ringG, m);
        ringG.dispose();
        if (o.bars) {
          kit.box(
            batch,
            o.frame,
            cx + uy * depth * 0.5,
            cy - ux * depth * 0.5,
            z + o.height,
            0.05,
            depth * 0.6,
            r,
            ang,
          );
        }
        if (o.surround) {
          const sr = new THREE.TorusGeometry(
            r + o.surround * 0.6,
            o.surround * 0.5,
            3,
            12,
            Math.PI,
          );
          batch.addGeometry(
            o.surroundMat,
            sr,
            rot.clone().setPosition(cx + uy * depth * 0.5, cy - ux * depth * 0.5, z + o.height),
          );
          sr.dispose();
        }
      }
    };
    const urnProf = [
      [0, 0],
      [0.35, 0],
      [0.3, 0.15],
      [0.18, 0.3],
      [0.42, 0.65],
      [0.38, 0.95],
      [0.2, 1.1],
      [0.26, 1.2],
      [0.12, 1.35],
      [0.15, 1.5],
      [0, 1.6],
    ];

    // Sash windows: per storey of the three-storey ranges.
    const EAVE = 12.2;
    const storeyWin = [
      { z: 1.0, height: 2.4, width: 1.25 },
      { z: 5.0, height: 2.8, width: 1.3 },
      { z: 9.15, height: 1.9, width: 1.2 },
    ];
    const sash = (s, court) => ({
      width: storeyWin[s].width,
      height: storeyWin[s].height,
      bay: 3.3,
      margin: 1.0,
      depth: 0.12,
      glass: sashGlass,
      frame: white,
      sill: stone,
      head: court ? 'none' : s === 1 ? 'lintel' : 'none',
      bars: court ? 1 : 2,
      surround: court ? 0 : 0.18,
      surroundMat: rubbed,
    });

    // ---- palace ranges -----------------------------------------------------
    const main = byId['bb9186ea-2aa8-4013-937a-607071c25b42'];
    for (const poly of main.polys) {
      poly.forEach((ring, ri) => {
        // walls edge by edge with a per-edge tint
        for (let k = 0; k < ring.length; k++) {
          const a = ring[k],
            b = ring[(k + 1) % ring.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          if (len < 0.05) continue;
          const c = tint();
          batch.quad(
            palaceWall,
            [a[0], a[1], 0],
            [b[0], b[1], 0],
            [b[0], b[1], EAVE],
            [a[0], a[1], EAVE],
            [0, 0],
            [len / 12, 0],
            [len / 12, EAVE / 6],
            [0, EAVE / 6],
            c,
          );
        }
        band(ring, 0, 0.7, 0.18, stoneD); // plinth
        band(ring, 4.15, 4.4, 0.1, stone); // string courses
        band(ring, 8.35, 8.6, 0.1, stone);
        band(ring, EAVE - 0.6, EAVE - 0.35, 0.18, stone); // architrave / frieze
        band(ring, EAVE - 0.35, EAVE, 0.42, stone); // cornice
        parapet(ring, EAVE, 1.0, 0.4, brickMat, stone);
      });
      kit.cap(batch, lead, [poly], EAVE + 0.2);
    }

    // Hipped roofs per wing (local frame: x ~ east, y ~ north, rotated 16 deg).
    const wings = [
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
        { overhang: 0 },
      );
      roofTops.push({ x0, y0, x1, y1, alongX, top: r.top });
      // lead ridge roll
      const [p0, p1] = r.ridge;
      const rl = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
      if (rl > 0.5)
        kit.box(
          batch,
          lead,
          (p0[0] + p1[0]) / 2,
          (p0[1] + p1[1]) / 2,
          r.top - 0.08,
          rl,
          0.22,
          0.16,
          Math.atan2(p1[1] - p0[1], p1[0] - p0[0]),
        );
    }
    // Tall brick chimney stacks along the ridges, with oversailing caps and pots.
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
          const sw = w.alongX ? cw : 1.0,
            sd = w.alongX ? 1.0 : cw;
          const top = w.top + 1.6;
          lbox(brickMat, x, y, EAVE, sw, sd, top - EAVE);
          lbox(brickMat, x, y, top - 0.6, sw + 0.18, sd + 0.18, 0.18);
          lbox(stone, x, y, top, sw + 0.25, sd + 0.25, 0.25);
          const np = Math.max(1, Math.round(cw / 0.55));
          for (let i = 0; i < np; i++) {
            const u = (i + 0.5) / np - 0.5;
            cyl(
              pot,
              0.15,
              0.12,
              0.65,
              x + (w.alongX ? u * cw : 0),
              y + (w.alongX ? 0 : u * cw),
              top + 0.25,
              6,
            );
          }
        }
      }
    }

    // ---- real sash windows on every elevation of the main block ----------------
    for (const poly of main.polys)
      poly.forEach((ring, ri) => {
        for (let k = 0; k < ring.length; k++)
          for (let s = 0; s < 3; s++)
            kit.windowRow(
              batch,
              ring[k],
              ring[(k + 1) % ring.length],
              storeyWin[s].z,
              sash(s, ri > 0),
            );
      });

    // South front (King's Gallery): central attic with urns, stone doorcase.
    {
      const cx = 32,
        y = -34.4;
      lbox(brickMat, cx, y + 2.2, EAVE, 15, 4.4, 4.0);
      lbox(stone, cx, y + 2.2, EAVE + 3.6, 15.6, 5.0, 0.4);
      lbox(stone, cx, y + 2.2, EAVE + 4.0, 15.2, 4.6, 0.2);
      for (const sx of [-7.5, 7.5]) lbox(stone, cx + sx, y + 0.02, EAVE, 0.7, 0.4, 3.6);
      for (let k = 0; k < 4; k++) {
        const p = L(cx - 5.4 + k * 3.6, y - 0.02);
        kit.box(batch, rubbed, p[0], p[1], EAVE + 0.75, 1.5, 0.12, 2.5, A);
        kit.box(batch, white, p[0] - sa * -0.07, p[1] + ca * -0.07, EAVE + 0.9, 1.15, 0.08, 2.2, A);
        kit.box(
          batch,
          sashGlass,
          p[0] - sa * -0.1,
          p[1] + ca * -0.1,
          EAVE + 1.0,
          0.95,
          0.05,
          2.0,
          A,
        );
        kit.box(
          batch,
          white,
          p[0] - sa * -0.13,
          p[1] + ca * -0.13,
          EAVE + 1.95,
          0.95,
          0.05,
          0.06,
          A,
        );
        kit.box(batch, stone, p[0] - sa * -0.15, p[1] + ca * -0.15, EAVE + 0.8, 1.4, 0.25, 0.1, A);
      }
      // urns on the attic and along the parapet
      for (let k = 0; k < 6; k++) {
        const x = 15 + k * 6.8;
        const onAttic = Math.abs(x - cx) < 8;
        lbox(stone, x, y + 0.25, EAVE + (onAttic ? 4.2 : 1.12), 0.8, 0.8, 0.35);
        lathe(stone, urnProf, x, y + 0.25, EAVE + (onAttic ? 4.55 : 1.47), 10);
      }
      // Stone doorcase: Doric pilasters, entablature and segmental pediment.
      const dy = y - 0.2;
      lbox(stone, cx, dy, 0, 4.2, 0.45, 0.25);
      for (const s of [-1, 1]) lbox(stone, cx + s * 1.7, dy - 0.05, 0.25, 0.55, 0.5, 3.9);
      lbox(stone, cx, dy - 0.1, 4.15, 4.4, 0.6, 0.55);
      const arc = new THREE.Shape();
      arc.moveTo(-2.3, 0);
      arc.absarc(0, -2.4, Math.hypot(2.3, 2.4), Math.atan2(2.4, -2.3), Math.atan2(2.4, 2.3), true);
      arc.lineTo(-2.3, 0);
      const pedG = new THREE.ExtrudeGeometry(arc, {
        depth: 0.6,
        bevelEnabled: false,
        curveSegments: 10,
      })
        .rotateX(Math.PI / 2)
        .translate(0, 0.3, 0);
      lgeo(pedG, stone, cx, dy - 0.1, 4.7);
      lbox(door, cx, dy - 0.02, 0.25, 2.3, 0.1, 3.6);
      lbox(white, cx, dy - 0.05, 2.9, 2.3, 0.06, 0.08);
      // steps
      lbox(stoneD, cx, y - 1.6, 0, 6.0, 2.6, 0.17);
      lbox(stoneD, cx, y - 1.2, 0.17, 5.2, 1.8, 0.17);
    }
    // East front (Kent's state rooms): stone quoins and a central doorcase with steps.
    for (const [x, y] of [
      [49.6, -34.4],
      [49.6, 10.0],
      [49.6, -12],
    ])
      for (let z = 0.7; z < EAVE - 0.7; z += 0.6)
        lbox(stone, x - 0.25, y, z, 0.8, Math.round(z / 0.6) % 2 ? 1.5 : 1.0, 0.48);
    {
      const x = 49.75,
        y = -23;
      lbox(stone, x + 0.1, y, 0, 0.45, 4.2, 4.6);
      lbox(door, x + 0.35, y, 0.3, 0.1, 2.2, 3.4);
      lbox(stone, x + 0.3, y, 4.3, 0.7, 4.6, 0.5);
      lbox(stoneD, x + 1.6, y, 0, 2.6, 6.0, 0.17);
      lbox(stoneD, x + 1.2, y, 0.17, 1.8, 5.2, 0.17);
    }

    // ---- Clock tower over the Clock Court archway (west range) ----------------
    {
      const x = -32,
        y = -2;
      lbox(brickMat, x, y, EAVE, 5.2, 5.2, 4.2);
      lbox(stone, x, y, EAVE + 3.9, 5.8, 5.8, 0.3);
      lbox(stone, x, y, EAVE + 4.2, 5.5, 5.5, 0.35);
      for (const [dx, dy] of [
        [-2.6, -2.6],
        [2.6, -2.6],
        [2.6, 2.6],
        [-2.6, 2.6],
      ])
        lbox(stone, x + dx, y + dy, EAVE, 0.5, 0.5, 3.9);
      const face = kit.paintedMaterial('kensington_palace:clock', 128, 128, (c, w, h) => {
        c.fillStyle = '#1f3550';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d6b04c';
        c.font = 'bold 13px serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        const nums = ['XII', 'I', 'II', 'III', 'IIII', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
        nums.forEach((n, i) => {
          const a = (i / 12) * Math.PI * 2;
          c.fillText(n, w / 2 + Math.sin(a) * 48, h / 2 - Math.cos(a) * 48);
        });
        c.strokeStyle = '#d6b04c';
        c.lineWidth = 4;
        c.beginPath();
        c.moveTo(w / 2, h / 2);
        c.lineTo(w / 2, h / 2 - 34);
        c.moveTo(w / 2, h / 2);
        c.lineTo(w / 2 + 24, h / 2 + 8);
        c.stroke();
      });
      for (let s = 0; s < 4; s++) {
        const rz = (s * Math.PI) / 2;
        const ox = Math.sin(rz) * 2.63,
          oy = -Math.cos(rz) * 2.63;
        const disc = new THREE.CircleGeometry(1.3, 24).rotateX(Math.PI / 2).rotateZ(Math.PI);
        lgeo(disc, face, x + ox, y + oy, EAVE + 2.1, rz);
        lgeo(
          new THREE.TorusGeometry(1.32, 0.1, 4, 24).rotateX(Math.PI / 2),
          gold,
          x + ox * 1.01,
          y + oy * 1.01,
          EAVE + 2.1,
          rz,
        );
      }
      // white-painted timber cupola: octagonal arcaded stage, lead ogee dome, vane
      const zc = EAVE + 4.55;
      lathe(
        white,
        [
          [0, 0],
          [2.1, 0],
          [2.1, 0.35],
          [1.9, 0.4],
          [0, 0.4],
        ],
        x,
        y,
        zc,
        8,
      );
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4 + Math.PI / 8;
        cyl(white, 0.13, 0.11, 2.4, x + Math.cos(a) * 1.65, y + Math.sin(a) * 1.65, zc + 0.4, 6);
      }
      cyl(kit.mat('#3a3f44'), 1.25, 1.25, 2.4, x, y, zc + 0.4, 8);
      lathe(
        white,
        [
          [0, 0],
          [2.0, 0],
          [2.05, 0.3],
          [1.85, 0.45],
          [0, 0.45],
        ],
        x,
        y,
        zc + 2.8,
        8,
      );
      lathe(
        lead,
        [
          [0, 0],
          [1.8, 0],
          [1.75, 0.5],
          [1.4, 1.0],
          [0.7, 1.5],
          [0.35, 2.0],
          [0.3, 2.3],
          [0.15, 2.5],
          [0, 2.6],
        ],
        x,
        y,
        zc + 3.25,
        16,
      );
      lathe(
        gold,
        [
          [0, 0],
          [0.22, 0.05],
          [0.25, 0.25],
          [0.1, 0.45],
          [0, 0.5],
        ],
        x,
        y,
        zc + 5.85,
        10,
      );
      cyl(gold, 0.04, 0.04, 2.0, x, y, zc + 6.3, 4);
      lbox(gold, x + 0.3, y, zc + 7.6, 1.2, 0.04, 0.4);
      lbox(gold, x, y, zc + 7.1, 1.0, 0.04, 0.04);
      lbox(gold, x, y, zc + 7.1, 0.04, 1.0, 0.04, 0);
    }
    // Arched gateway into Clock Court through the low west range (stone surround).
    {
      const arc = new THREE.Shape();
      arc.moveTo(-2.4, 0);
      arc.lineTo(-2.4, 5.2);
      arc.lineTo(2.4, 5.2);
      arc.lineTo(2.4, 0);
      arc.lineTo(1.6, 0);
      arc.lineTo(1.6, 2.8);
      arc.absarc(0, 2.8, 1.6, 0, Math.PI, false);
      arc.lineTo(-1.6, 0);
      arc.lineTo(-2.4, 0);
      const ge = new THREE.ExtrudeGeometry(arc, {
        depth: 0.5,
        bevelEnabled: false,
        curveSegments: 10,
      })
        .rotateX(Math.PI / 2)
        .translate(0, 0.25, 0);
      lgeo(ge, stone, -49.15, -2, 0, -Math.PI / 2);
      lbox(door, -48.9, -2, 0, 0.1, 3.2, 4.3);
    }

    // ---- low ranges (two storeys, brick, pitched roofs) ------------------------
    for (const id of [
      '755e0c1f-1048-4ebf-b245-3b0f1c20c8db',
      'e4f6979a-1775-4ba9-9785-42eed7a06a92',
      '20733963-5e33-4e82-b578-6041ba0b457a',
    ]) {
      const b = byId[id];
      if (!b) continue;
      const top = Math.max(b.h, 3.5);
      kit.walls(batch, palaceWall, b.polys, 0, top, { bay: 3, storey: 3, color: tint() });
      for (const poly of b.polys)
        for (const ring of poly) {
          band(ring, 0, 0.5, 0.12, stoneD);
          band(ring, top - 0.3, top, 0.25, stone);
          parapet(ring, top, 0.6, 0.3, brickMat, stone);
          if (top > 5)
            for (let k = 0; k < ring.length; k++)
              for (const z of [0.9, 3.6])
                kit.windowRow(batch, ring[k], ring[(k + 1) % ring.length], z, {
                  width: 1.1,
                  height: 1.9,
                  bay: 3.2,
                  margin: 0.8,
                  glass: sashGlass,
                  frame: white,
                  sill: stone,
                  head: 'none',
                  bars: 1,
                  surround: 0.14,
                  surroundMat: rubbed,
                });
        }
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
      {
        overhang: 0,
      },
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
      {
        overhang: 0,
      },
    );

    // ---- Orangery ---------------------------------------------------------------
    {
      const b = byId['e5dacc52-9a46-4e7a-b152-0f85bd654371'];
      const ring = b.polys[0][0];
      const H = 7.2;
      kit.walls(batch, orangeryWall, b.polys, 0, H, { bay: 3, storey: 3, color: tint() });
      band(ring, 0, 0.55, 0.15, stoneD);
      band(ring, H - 0.7, H - 0.4, 0.12, stone);
      band(ring, H - 0.4, H, 0.4, stone);
      parapet(ring, H, 1.0, 0.35, brickMat, stone);
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
        {
          overhang: 0,
        },
      );
      // ring corners: NE, NW, SW, SE (CCW). South face SW -> SE.
      const [NE, NW, SW, SE] = ring;
      const lerp = (p, q, t, d = 0) => {
        const dx = q[0] - p[0],
          dy = q[1] - p[1],
          l = Math.hypot(dx, dy);
        return [p[0] + dx * t + (dy / l) * d, p[1] + dy * t - (dx / l) * d];
      };
      const sLen = Math.hypot(SE[0] - SW[0], SE[1] - SW[1]);
      const bay = sLen / 13;
      const sAng = Math.atan2(SE[1] - SW[1], SE[0] - SW[0]);
      const arched = {
        width: 2.0,
        height: 4.3,
        count: 1,
        margin: 0,
        depth: 0.16,
        glass: sashGlass,
        frame: white,
        sill: stone,
        head: 'arch',
        bars: 3,
        surround: 0.3,
        surroundMat: rubbed,
      };
      // 13 bays on the south front; centre three on the projecting frontispiece.
      for (let i = 0; i < 13; i++) {
        const proj = i >= 5 && i <= 7 ? 0.7 : 0;
        if (i === 6) continue; // central doorway
        const a = lerp(SW, SE, (i + 0.1) / 13, proj),
          c = lerp(SW, SE, (i + 0.9) / 13, proj);
        archRow(a, c, 0.9, arched);
        // rubbed-brick pilaster strip between bays
        const p = lerp(SW, SE, i / 13, proj + 0.06);
        if (i > 0) kit.box(batch, rubbed, p[0], p[1], 0.55, 0.55, 0.14, H - 1.25, sAng);
      }
      // north front: plainer, same rhythm
      for (let i = 0; i < 13; i++) {
        const a = lerp(NE, NW, (i + 0.15) / 13),
          c = lerp(NE, NW, (i + 0.85) / 13);
        archRow(a, c, 1.2, { ...arched, height: 3.6, bars: 2, surround: 0.2 });
      }
      // end walls: one arched window each
      archRow(NW, SW, 0.9, { ...arched, count: 1, margin: 3.5 });
      archRow(SE, NE, 0.9, { ...arched, count: 1, margin: 3.5 });
      // Frontispiece: three bays set forward, raised parapet and split segmental pediment.
      const f0 = lerp(SW, SE, 5 / 13, 0),
        f1 = lerp(SW, SE, 8 / 13, 0);
      const fc = [(f0[0] + f1[0]) / 2, (f0[1] + f1[1]) / 2];
      const nx = Math.sin(sAng),
        ny = -Math.cos(sAng);
      const at = (u, d) => [
        fc[0] + Math.cos(sAng) * u + nx * d,
        fc[1] + Math.sin(sAng) * u + ny * d,
      ];
      const fw = 3 * bay;
      let q = at(0, 0.35);
      kit.box(batch, orangeryWall, q[0], q[1], 0, fw, 0.7, H + 1.4, sAng, tint());
      kit.box(batch, stone, q[0], q[1], H - 0.4, fw + 0.5, 1.4, 0.4, sAng);
      kit.box(batch, stone, q[0], q[1], H + 1.4, fw + 0.3, 1.1, 0.3, sAng);
      for (const s of [-1, 1]) {
        q = at((s * fw) / 2, 0.72);
        for (let z = 0.55; z < H - 0.5; z += 0.55)
          kit.box(
            batch,
            stone,
            q[0],
            q[1],
            z,
            Math.round(z / 0.55) % 2 ? 0.9 : 0.6,
            0.1,
            0.5,
            sAng,
          );
        // split segmental pediment halves
        const arc = new THREE.Shape();
        const R = fw / 2 + 0.6;
        arc.moveTo(s * 1.2, 0);
        arc.lineTo(s * R * 0.98, 0);
        arc.lineTo(s * R * 0.98, 0.6);
        for (let k = 0; k <= 8; k++) {
          const t = 0.98 - (k / 8) * (0.98 - 1.2 / R);
          const xx = s * R * t;
          arc.lineTo(xx, 0.6 + 1.6 * (1 - t * t));
        }
        arc.lineTo(s * 1.2, 0);
        const pg = new THREE.ExtrudeGeometry(arc, { depth: 0.9, bevelEnabled: false })
          .rotateX(Math.PI / 2)
          .translate(0, 0.45, 0);
        q = at(0, 0.5);
        batch.addGeometry(
          stone,
          pg,
          new THREE.Matrix4().makeRotationZ(sAng).setPosition(q[0], q[1], H + 1.7),
        );
        pg.dispose();
      }
      // vase on the pediment break
      q = at(0, 0.5);
      kit.box(batch, stone, q[0], q[1], H + 1.7, 1.0, 1.0, 0.6, sAng);
      const vg = new THREE.LatheGeometry(
        urnProf.map(([r, h]) => new THREE.Vector2(r * 1.3, h * 1.3)),
        12,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(stone, vg, new THREE.Matrix4().makeTranslation(q[0], q[1], H + 2.3));
      vg.dispose();
      // central doorway with Doric columns and steps
      const dw = at(0, 0.72);
      kit.box(batch, door, dw[0], dw[1], 0.4, 2.2, 0.06, 4.2, sAng);
      const dArc = new THREE.CircleGeometry(1.1, 12, 0, Math.PI)
        .rotateX(Math.PI / 2)
        .rotateZ(Math.PI);
      batch.addGeometry(
        door,
        dArc,
        new THREE.Matrix4()
          .makeRotationZ(sAng)
          .setPosition(dw[0] + nx * 0.02, dw[1] + ny * 0.02, 4.6),
      );
      dArc.dispose();
      kit.colonnade(batch, stone, at(-1.9, 1.2), at(1.9, 1.2), 0.4, H - 1.1, {
        count: 2,
        radius: 0.32,
        capital: 'doric',
      });
      for (let k = 0; k < 3; k++) {
        q = at(0, 1.4 + k * 0.4);
        kit.box(
          batch,
          stoneD,
          q[0],
          q[1],
          0,
          6.5 - k * 0.6,
          0.45 + (2 - k) * 0.4,
          0.4 - k * 0.13,
          sAng,
        );
      }
      // end pavilions: raised brick attic with stone coping and urns
      for (const t of [0.5 / 13, 12.5 / 13]) {
        const p = lerp(SW, SE, t, 0);
        const c = [p[0] - nx * 5.8, p[1] - ny * 5.8];
        kit.box(batch, brickMat, c[0], c[1], H, bay * 0.95, 11.2, 1.2, sAng);
        kit.box(batch, stone, c[0], c[1], H + 1.2, bay * 0.95 + 0.3, 11.5, 0.2, sAng);
        for (const d of [-5.4, 5.4]) {
          const u = [c[0] - nx * d, c[1] - ny * d];
          const ug = new THREE.LatheGeometry(
            urnProf.map(([r, h]) => new THREE.Vector2(r, h)),
            10,
          ).rotateX(Math.PI / 2);
          batch.addGeometry(stone, ug, new THREE.Matrix4().makeTranslation(u[0], u[1], H + 1.4));
          ug.dispose();
        }
      }
      // terrace in front of the south face
      const t0 = lerp(SW, SE, 0, 0),
        t1 = lerp(SW, SE, 1, 0);
      const terr = [t0, t1, lerp(SW, SE, 1, 4.5), lerp(SW, SE, 0, 4.5)];
      kit.cap(batch, paving, [[terr.slice().reverse()]], 0.04);
      kit.cap(batch, paving, [[terr]], 0.04);
      // clipped bay / bay-tree tubs along the terrace
      for (let i = 0; i < 13; i += 2) {
        const p = lerp(SW, SE, (i + 0.5) / 13, 3.2);
        kit.box(batch, kit.mat('#3d4a3a'), p[0], p[1], 0, 0.8, 0.8, 0.7, sAng);
        const tg = new THREE.SphereGeometry(0.7, 8, 6);
        batch.addGeometry(
          kit.mat('dark_foliage'),
          tg,
          new THREE.Matrix4().makeTranslation(p[0], p[1], 1.6),
        );
        tg.dispose();
      }
    }

    // ---- Queen Victoria statue (Princess Louise, 1893) facing the Broad Walk ----------
    {
      const x = 72,
        y = -12;
      // gravel circle and low railings
      const R = 5.2;
      lathe(
        gravel,
        [
          [0, 0],
          [R + 0.8, 0],
          [R + 0.8, 0.04],
          [0, 0.04],
        ],
        x,
        y,
        0,
        24,
      );
      for (let k = 0; k < 40; k++) {
        const a = (k / 40) * Math.PI * 2;
        cyl(iron, 0.03, 0.03, 1.0, x + Math.cos(a) * R, y + Math.sin(a) * R, 0, 4);
      }
      lgeo(new THREE.TorusGeometry(R, 0.04, 3, 40).rotateX(0), iron, x, y, 0.95);
      lgeo(new THREE.TorusGeometry(R, 0.04, 3, 40), iron, x, y, 0.2);
      // stepped pedestal
      lbox(stoneD, x, y, 0, 4.4, 4.4, 0.35);
      lbox(stoneD, x, y, 0.35, 3.7, 3.7, 0.3);
      lbox(marble, x, y, 0.65, 2.9, 2.9, 0.4);
      lbox(marble, x, y, 1.05, 2.4, 2.4, 2.3);
      lbox(marble, x, y, 3.35, 2.9, 2.9, 0.35);
      // seated figure facing east (local +x): throne, robes, torso, head, crown
      lbox(marble, x - 0.45, y, 3.7, 1.0, 1.6, 2.3);
      lathe(
        marble,
        [
          [0, 0],
          [0.95, 0],
          [0.85, 0.5],
          [0.6, 1.0],
          [0.45, 1.3],
          [0, 1.35],
        ],
        x + 0.1,
        y,
        3.7,
        14,
      );
      lbox(marble, x + 0.55, y, 3.7, 0.8, 1.2, 0.9);
      lathe(
        marble,
        [
          [0, 0],
          [0.42, 0],
          [0.38, 0.5],
          [0.28, 0.8],
          [0.16, 0.95],
          [0, 0.95],
        ],
        x + 0.05,
        y,
        5.0,
        12,
      );
      lgeo(new THREE.SphereGeometry(0.2, 10, 8), marble, x + 0.08, y, 6.1);
      cyl(marble, 0.15, 0.17, 0.18, x + 0.08, y, 6.25, 10);
      lgeo(new THREE.SphereGeometry(0.06, 6, 4), marble, x + 0.08, y, 6.47);
      // sceptre arm
      lbox(marble, x + 0.5, y + 0.45, 4.5, 0.6, 0.18, 0.18);
      cyl(marble, 0.03, 0.03, 1.2, x + 0.75, y + 0.45, 4.3, 5);
    }

    // ---- William III statue (Heinrich Baucke, 1907) before the south front ---------
    {
      const x = 32,
        y = -50;
      lbox(stoneD, x, y, 0, 3.4, 3.4, 0.4);
      lbox(stone, x, y, 0.4, 2.6, 2.6, 0.5);
      lbox(stone, x, y, 0.9, 2.0, 2.0, 2.4);
      lbox(stone, x, y, 3.3, 2.5, 2.5, 0.4);
      // standing bronze figure in robes, facing south
      lathe(
        bronze,
        [
          [0, 0],
          [0.5, 0],
          [0.42, 0.8],
          [0.32, 1.4],
          [0.36, 1.7],
          [0.2, 1.85],
          [0, 1.9],
        ],
        x,
        y,
        3.7,
        12,
      );
      lgeo(new THREE.SphereGeometry(0.17, 10, 8), bronze, x, y, 5.75);
      lbox(bronze, x + 0.3, y - 0.2, 4.8, 0.14, 0.5, 0.14);
      cyl(bronze, 0.03, 0.03, 1.4, x - 0.45, y - 0.1, 3.7, 4);
    }

    // ---- street furniture: lamps and benches on the paths round the palace -------
    const lamps = [];
    for (let k = 0; k < 5; k++) {
      const p = L(62, -40 + k * 18);
      lamps.push([p[0], p[1], A - Math.PI / 2]);
    }
    for (const [lx, ly] of [
      [16, -44],
      [48, -44],
    ]) {
      const p = L(lx, ly);
      lamps.push([p[0], p[1], A]);
    }
    g.add(ctx.placeAssets('street_lamp', lamps, { name: 'kensington_palace:lamps' }));
    const benches = [];
    for (const [bx, by, h] of [
      [72, -19.5, 0],
      [72, -4.5, Math.PI],
      [79.5, -12, Math.PI / 2],
      [26, -52, 0],
      [38, -52, 0],
    ]) {
      const p = L(bx, by);
      benches.push([p[0], p[1], A + h]);
    }
    g.add(ctx.placeAssets('bench', benches, { name: 'kensington_palace:benches' }));

    g.add(batch.toGroup('kensington_palace'));
    return g;
  },
};
