// Hyde Park Barracks, Knightsbridge (Sir Basil Spence, Glover & Ferguson; built by Sir
// Robert McAlpine 1967-70). Home of the Household Cavalry Mounted Regiment. A 33-storey,
// 94 m married-quarters tower stands at the west end of a long, low range of red brick
// and concrete buildings (officers' mess, troopers' quarters, stables) along the south
// edge of Hyde Park; the scheme is unified by red brick, exposed concrete and concrete
// arches.
export default {
  id: 'hyde_park_barracks',
  name: 'Hyde Park Barracks',
  claims: [
    '7a6d46a3-ee6d-4d1f-b4e3-4aabbc1c8f27',
    'baca7b8b-45fe-4534-b29f-836644304879',
    '1e43aa8f-c40f-495f-a6b8-c397d512b96e',
    '9b42cc87-17f1-4400-8d01-9dacefa6df7e',
  ],
  references: [
    {
      title: 'Hyde Park Barracks, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hyde_Park_Barracks,_London',
      used_for: '33-storey 94 m residential tower, McAlpine 1967-70, prominence from Hyde Park',
    },
    {
      title: 'Hyde Park Cavalry Barracks - Mainstream Modern',
      url: 'https://mainstreammodern.co.uk/casestudies.aspx/Detail/253/hyde-park-cavalry-barracks',
      used_for: 'structural concrete finished in red brick to complement surrounding buildings',
    },
    {
      title: 'Canmore - Basil Spence archive, Hyde Park Barracks',
      url: 'https://canmore.org.uk/site/284764',
      used_for:
        'unity through red brick, concrete and concrete arches; married soldiers tower block',
    },
    {
      title: 'Hyde Park Barracks - Structurae',
      url: 'https://structurae.net/en/structures/hyde-park-barracks',
      used_for: 'tower height 94 m',
    },
  ],
  notes:
    'Tower height 94 m from Wikipedia/Structurae (Overture footprint kept). Floor-to-floor 2.75 m, the ' +
    'pier rhythm (corner piers plus two intermediate piers per face), brick spandrels and the ribbed plant ' +
    'crown are simplified from general descriptions, not measured. Which low footprints belong to the ' +
    'barracks is inferred from position (the four blocks between Rutland Gate and Albert Gate along the ' +
    'park edge); their storey heights follow Overture. The barrel-roofed riding school position on the ' +
    'east block and the ground-floor concrete arcade along the park front are approximations.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // ---- local helpers (modules have no imports) -----------------------------------
    const ccw = (r) => {
      const o = r.slice();
      if (kit.ringArea(o) < 0) o.reverse();
      return o;
    };
    const edges = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return {
          a,
          b,
          k,
          len,
          dx: dx / len,
          dy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
          mx: (a[0] + b[0]) / 2,
          my: (a[1] + b[1]) / 2,
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    // Box on edge e from s0..s1 along it, d0..d1 outward, z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
      const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, p[0], p[1], z0, Math.abs(s1 - s0), Math.abs(d1 - d0), z1 - z0, e.ang, c);
    };
    const prism = (m, ring, z0, z1, top = m) => {
      kit.walls(batch, m, [[ring]], z0, z1);
      if (top) kit.cap(batch, top, [[ring]], z1);
    };
    const wins = (e, s0, s1, z, o) => kit.windowRow(batch, at(e, s0), at(e, s1), z, o);
    const cyl = (m, x, y, z0, r0, r1, h, seg = 12) => {
      const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      g.dispose();
    };
    const lathe = (m, prof, x, y, z, seg = 24) => {
      const g = new THREE.LatheGeometry(
        prof.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z));
      g.dispose();
    };
    // Rectangle ring (CCW) centred at (cx, cy), long axis at angle ang.
    const rect = (cx, cy, ang, L, W) => {
      const c = Math.cos(ang),
        s = Math.sin(ang);
      return [
        [-L / 2, -W / 2],
        [L / 2, -W / 2],
        [L / 2, W / 2],
        [-L / 2, W / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    // Triangular gable (pediment) standing on edge e between s0..s1, base z, rise, from d0..d1.
    const gable = (m, e, s0, s1, z, rise, d0 = 0, d1 = 0.4) => {
      const sh = new THREE.Shape();
      sh.moveTo(s0, 0);
      sh.lineTo(s1, 0);
      sh.lineTo((s0 + s1) / 2, rise);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: d1 - d0, bevelEnabled: false });
      // shape x along edge, y up, extrude z outward -> map to world
      const m4 = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(e.dx, e.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(e.nx, e.ny, 0),
      );
      m4.setPosition(e.a[0] + e.nx * d0, e.a[1] + e.ny * d0, z);
      batch.addGeometry(m, g, m4);
      g.dispose();
    };
    // Facing test: cosine between an edge's outward normal and a direction (dx, dy).
    const facing = (e, dx, dy) => (e.nx * dx + e.ny * dy) / (Math.hypot(dx, dy) || 1);
    // ---------------------------------------------------------------------------------
    const B = (p) => buildings.find((b) => b.id.startsWith(p));
    const brick = kit.mat('#8c4b37', { roughness: 0.9 });
    const conc = kit.mat('#aaa398', { roughness: 0.88 });
    const darkConc = kit.mat('#857f76', { roughness: 0.9 });
    const glass = kit.mat('#2d3a44', { roughness: 0.15, metalness: 0.4 });
    const frame = kit.mat('#3a3d40', { roughness: 0.5, metalness: 0.4 });
    const roofM = kit.mat('#6f6c66');
    const lead = kit.mat('lead');

    // ---- tower ------------------------------------------------------------------------
    {
      const ring = ccw(B('7a6d46a3').polys[0][0]);
      const H = 94,
        G = 4.5,
        ST = 2.75,
        NF = 28,
        TOP = G + NF * ST; // 81.5 m top of habitable floors
      // core (recessed) volume
      const core = kit.offsetRing(ring, -0.4);
      prism(darkConc, core, 0, TOP, null);
      for (const e of edges(ring)) {
        if (e.len < 3) continue;
        // full-height piers: corners + two intermediate
        const piers = [0, e.len / 3, (2 * e.len) / 3, e.len];
        for (const s of piers) {
          const s0 = Math.max(0, s - 0.55),
            s1 = Math.min(e.len, s + 0.55);
          ebox(conc, e, s0, s1, -0.4, 0.35, 0, TOP + 1.2);
        }
        // ground floor: recessed glazed lobby
        ebox(glass, e, 0.6, e.len - 0.6, -1.6, -1.5, 0.2, G - 0.5);
        ebox(conc, e, 0, e.len, -0.4, 0.25, G - 0.5, G);
        // floors: concrete slab band, brick spandrel, ribbon window with mullions
        for (let f = 0; f < NF; f++) {
          const z = G + f * ST;
          ebox(conc, e, 0, e.len, -0.4, 0.2, z, z + 0.3);
          for (let b = 0; b < 3; b++) {
            const s0 = (b * e.len) / 3 + 0.55,
              s1 = ((b + 1) * e.len) / 3 - 0.55;
            ebox(brick, e, s0, s1, -0.4, -0.05, z + 0.3, z + 1.15);
            ebox(glass, e, s0, s1, -0.4, -0.2, z + 1.15, z + ST);
            for (let m = 1; m < 2; m++) {
              const s = s0 + ((s1 - s0) * m) / 2;
              ebox(frame, e, s - 0.05, s + 0.05, -0.4, -0.12, z + 1.15, z + ST);
            }
          }
        }
        ebox(conc, e, 0, e.len, -0.4, 0.45, TOP, TOP + 1.2);
      }
      kit.cap(batch, roofM, [[ring]], TOP + 1.2);
      // plant crown: set-back box wrapped in vertical concrete fins
      const crown = kit.offsetRing(ring, -2.2);
      prism(darkConc, crown, TOP + 1.2, H - 0.6, roofM);
      for (const e of edges(crown)) {
        if (e.len < 2) continue;
        const n = Math.round(e.len / 1.4);
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(conc, e, s - 0.14, s + 0.14, 0, 0.9, TOP + 1.2, H);
        }
        ebox(conc, e, 0, e.len, 0, 1.0, H - 0.6, H);
      }
      // aerials / lift motor room
      const fr = kit.ringFrame(ring);
      kit.box(batch, darkConc, fr.cx, fr.cy, H - 0.6, 5, 4, 2.4, fr.angle);
      cyl(kit.mat('steel'), fr.cx + 1.5, fr.cy, H + 1.8, 0.08, 0.05, 5, 6);
    }

    // ---- low ranges: red brick with concrete floor bands --------------------------------
    const low = [
      ['baca7b8b', 3.4],
      ['1e43aa8f', 3.4],
      ['9b42cc87', 2.9],
    ];
    for (const [id, st] of low) {
      const b = B(id);
      const ring = ccw(b.polys[0][0]);
      const H = b.h;
      const n = Math.max(2, Math.round(H / st));
      const sh = H / n;
      kit.walls(batch, brick, [[ring]], 0, H - 0.6);
      kit.walls(batch, conc, [[ring]], H - 0.6, H);
      kit.cap(batch, roofM, [[ring]], H - 0.1);
      kit.cornice(batch, conc, ring, H - 0.7, { height: 0.7, projection: 0.3 });
      kit.cornice(batch, darkConc, ring, 0, { height: 0.5, projection: 0.15 });
      for (let f = 1; f < n; f++)
        kit.cornice(batch, conc, ring, f * sh - 0.15, { height: 0.3, projection: 0.08 });
      for (const e of edges(ring)) {
        if (e.len < 6) continue;
        for (let f = 1; f < n; f++)
          wins(e, 0, e.len, f * sh + 0.75, {
            width: 1.6,
            height: sh - 1.4,
            bay: 3.0,
            margin: 1.2,
            bars: 0,
            head: 'none',
            frame,
            sill: conc,
            glass,
          });
        // ground floor: concrete arches (arcade) on the park front, plain windows elsewhere
        const park = facing(e, 0, 1) > 0.8;
        wins(e, 0, e.len, 0.5, {
          width: park ? 2.4 : 1.6,
          height: park ? sh - 1.9 : sh - 1.5,
          bay: park ? 3.6 : 3.0,
          margin: 1.2,
          bars: 0,
          head: park ? 'arch' : 'none',
          frame: conc,
          sill: conc,
          glass,
        });
      }
      // roof plant / stair housings
      const fr = kit.ringFrame(ring);
      kit.box(
        batch,
        darkConc,
        fr.cx,
        fr.cy,
        H,
        Math.min(10, fr.length / 4),
        Math.min(5, fr.width / 2),
        2.2,
        fr.angle,
      );
    }
    // riding school: shallow barrel vault over the north-east block
    {
      const cx = 2506.5,
        cy = -488,
        L = 38,
        W = 21,
        z = B('1e43aa8f').h;
      const R = W / 1.6;
      const seg = 16,
        th0 = Math.asin(W / 2 / R);
      const zc = z - R * Math.cos(th0);
      for (let k = 0; k < seg; k++) {
        const t0 = -th0 + (2 * th0 * k) / seg,
          t1 = -th0 + (2 * th0 * (k + 1)) / seg;
        const x0 = cx + R * Math.sin(t0),
          x1 = cx + R * Math.sin(t1);
        const z0 = zc + R * Math.cos(t0),
          z1 = zc + R * Math.cos(t1);
        batch.quad(
          lead,
          [x0, cy - L / 2, z0],
          [x1, cy - L / 2, z1],
          [x1, cy + L / 2, z1],
          [x0, cy + L / 2, z0],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        // end walls (brick lunettes)
        for (const yy of [cy - L / 2, cy + L / 2])
          batch.add(
            brick,
            [
              [x0, yy, z0],
              [x1, yy, z1],
              [x1, yy, z],
              [x0, yy, z],
            ],
            [
              [0, 0],
              [1, 0],
              [1, 1],
              [0, 1],
            ],
            yy < cy ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3],
          );
      }
    }

    g.add(batch.toGroup('hyde_park_barracks'));
    return g;
  },
};
