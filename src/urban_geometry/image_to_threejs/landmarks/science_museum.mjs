// Science Museum, Exhibition Road, South Kensington.
// East Block (Sir Richard Allison, 1913-1928): neoclassical Portland stone front on
// Exhibition Road with a banded-rusticated ground storey, a recessed giant colonnade
// of Ionic columns between solid end bays, entablature, attic and parapet; the main
// entrance with its glazed doors and lettered canopy at the centre. Centre Block
// infill (1960s-1980) in stone-faced concrete, and the Wellcome Wing (MacCormac
// Jamieson Prichard, 2000) at the west end whose west elevation is a vast wall of blue
// glass hung from brackets on two stair towers by V-shaped diagonal rods.
// Built in a local frame shared with the Natural History Museum (u east along
// Cromwell Road, v north).
const O = [1668, -1167],
  ANG = 0.1247;

export default {
  id: 'science_museum',
  name: 'Science Museum',
  claims: [
    '7d12ef9f-bee4-4c64-8bed-eadb621be38d', // Science Museum
    'a79d76d6-b1e1-427e-b57c-857aebf62dde', // service range on Museum Lane between the museums
  ],
  references: [
    {
      title: 'Science Museum, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Science_Museum,_London',
      used_for:
        "East Block by Sir Richard Allison (1913-1928), Centre Block infill 1980, Wellcome Wing 2000 extending to Queen's Gate",
    },
    {
      title: 'Science Museum, London (Wikishire)',
      url: 'https://wikishire.co.uk/wiki/Science_Museum,_London',
      used_for: 'substantial neoclassical building on Exhibition Road',
    },
    {
      title: 'Richard Allison (architect) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Richard_Allison_(architect)',
      used_for: 'Office of Works chief architect; East Block among his public buildings',
    },
    {
      title: 'Survey of London vol. 38, plate 75 (British History Online)',
      url: 'https://www.british-history.ac.uk/survey-london/vol38/plate-75',
      used_for:
        'Science Museum eastern block 1914-28 by (Sir) R. J. Allison, exterior photo caption',
    },
    {
      title: 'Photo showing the facade for the East Block (Science Museum Group)',
      url: 'https://collection.sciencemuseumgroup.org.uk/documents/aa110146247',
      used_for: 'East Block facade record (caption)',
    },
    {
      title: 'Photo showing the construction of the East Block of the Science Museum',
      url: 'https://collection.sciencemuseumgroup.org.uk/documents/aa110146179',
      used_for: 'East Block as a steel-framed stone-faced block on Exhibition Road',
    },
    {
      title: 'Listed Buildings Search (RBKC) - Exhibition Road subway',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=493237',
      used_for: 'neighbouring 1915 Portland stone work with banded rustication (style of the base)',
    },
    {
      title: 'Glowing panes - Building',
      url: 'https://building.co.uk/focus/glowing-panes/8923.article',
      used_for:
        'blue glass wall fills the west elevation of the Wellcome Wing; V-shaped diagonal rods carry it to brackets at the top of the two stair towers from which it is hung',
    },
    {
      title: 'The appliance of science (Design Week)',
      url: 'https://www.designweek.co.uk/issues/21-january-1999/the-appliance-of-science/',
      used_for: 'Wellcome Wing as tiers stepping back from a central atrium, blue light',
    },
    {
      title: "Science Museum's Wellcome Wing - Heritage Fund",
      url: 'https://heritagefund.org.uk/projects/science-museums-wellcome-wing',
      used_for: 'Wellcome Wing opening 2000',
    },
  ],
  notes:
    'Footprint from Overture; Overture height (12.9 m, inferred) replaced by estimates: East Block 24 m cornice + attic ' +
    'to 28 m (six public floors), Centre Block 24 m, Wellcome Wing 28 m. The Exhibition Road elevation is real geometry ' +
    '(banded-rusticated base with window openings, end bays with framed windows, a recessed giant order of eleven Ionic ' +
    'columns before metal-framed glazing with spandrel panels, entablature with dentils, attic windows and parapet), ' +
    'reconstructed from general descriptions, not measured drawings: column count, order and window rhythm are ' +
    'approximate; the north and south return elevations of the East Block carry framed windows. Wellcome Wing: stair towers, hanging brackets and V rods are schematic. The Museum Lane service range ' +
    'and the rear elevations are painted.',

  build({ THREE, kit }) {
    const root = new THREE.Group();
    root.position.set(O[0], O[1], 0);
    root.rotation.z = ANG;
    const B = new kit.MeshBatch();
    const STONE = '#ddd6c4',
      STONE_D = '#c9c1ad';
    const stone = kit.mat('portland_stone'),
      stoneD = kit.mat(STONE_D),
      stoneL = kit.mat('#e6e0cf', { roughness: 0.8 }),
      lead = kit.mat('lead'),
      darkGlass = kit.mat('dark_glass'),
      winGlass = kit.mat('#2b333b', { roughness: 0.2, metalness: 0.3 }),
      glass = kit.mat('glass'),
      steel = kit.mat('steel'),
      frameM = kit.mat('#3a3f44', { roughness: 0.5, metalness: 0.5 }),
      bronze = kit.mat('#5a4a36', { roughness: 0.5, metalness: 0.5 }),
      alu = kit.mat('aluminium'),
      stoneF = kit.facade('portland_stone', 0),
      concreteF = kit.facade('concrete', 1);

    const R = (u0, v0, u1, v1) => [
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
    ];
    const texWalls = (m, ring, z0, z1, bayW, vr = [0, 1]) => {
      for (let k = 0; k < ring.length; k++) {
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
    const geo = (m, g, x, y, z, sx = 1, sy = 1, sz = 1) => {
      const M = new THREE.Matrix4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion(),
        new THREE.Vector3(sx, sy, sz),
      );
      B.addGeometry(m, g, M);
      g.dispose();
    };
    const cyl = (m, u, v, z0, r, h, seg = 12, rTop = r) =>
      geo(m, new THREE.CylinderGeometry(rTop, r, h, seg).rotateX(Math.PI / 2), u, v, z0 + h / 2);
    const lathe = (m, prof, u, v, z0, seg = 16) =>
      geo(
        m,
        new THREE.LatheGeometry(
          prof.map(([r, z]) => new THREE.Vector2(Math.max(r, 0.0001), z)),
          seg,
        ).rotateX(Math.PI / 2),
        u,
        v,
        z0,
      );
    /** Thin rod between two 3D points. */
    const rod = (m, p, q, r = 0.05) => {
      const d = new THREE.Vector3(q[0] - p[0], q[1] - p[1], q[2] - p[2]);
      const g = new THREE.CylinderGeometry(r, r, d.length(), 5);
      B.addGeometry(
        m,
        g,
        new THREE.Matrix4().compose(
          new THREE.Vector3((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2),
          new THREE.Quaternion().setFromUnitVectors(
            new THREE.Vector3(0, 1, 0),
            d.clone().normalize(),
          ),
          new THREE.Vector3(1, 1, 1),
        ),
      );
      g.dispose();
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
    const drawSpec = (p, h) => {
      p.moveTo(h.s - h.w / 2, h.z0);
      p.lineTo(h.s + h.w / 2, h.z0);
      p.lineTo(h.s + h.w / 2, h.z1);
      p.lineTo(h.s - h.w / 2, h.z1);
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
    /** Stone wall slab on frame f between s0..s1, z0..z1, with rectangular openings. */
    const slab = (f, s0, s1, z0, z1, holes, depth, capMat, sideMat, o = {}) => {
      const sh = new THREE.Shape();
      sh.moveTo(s0, z0);
      sh.lineTo(s1, z0);
      sh.lineTo(s1, z1);
      sh.lineTo(s0, z1);
      sh.closePath();
      for (const h of holes) sh.holes.push(drawSpec(new THREE.Path(), h));
      const g = new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: false });
      addSplit(g, f.M(o.w0 ?? 0), capMat, sideMat, o.su ?? 1, o.sv ?? 1);
    };
    const eb = (f, m, s0, s1, w0, w1, z0, z1) => {
      const [x, y] = f.P((s0 + s1) / 2, (w0 + w1) / 2);
      kit.box(B, m, x, y, z0, s1 - s0, w1 - w0, z1 - z0, f.ang);
    };
    /** Metal window frame with mullions and transoms inside an opening. */
    const metalWin = (f, s, w, z0, z1, cols, rows, wf = 0.08) => {
      eb(f, winGlass, s - w / 2 - 0.05, s + w / 2 + 0.05, -0.06, -0.02, z0 - 0.05, z1 + 0.05);
      for (let i = 0; i <= cols; i++) {
        const x = s - w / 2 + (w * i) / cols;
        eb(f, frameM, x - 0.04, x + 0.04, wf, wf + 0.06, z0, z1);
      }
      for (let j = 0; j <= rows; j++) {
        const z = z0 + ((z1 - z0) * j) / rows;
        eb(f, frameM, s - w / 2, s + w / 2, wf, wf + 0.06, z - 0.035, z + 0.035);
      }
    };

    // Ashlar with banded rustication for the ground storey: u = m / 2.4, v = m / 3.6.
    const ashlar = kit.paintedMaterial('sm:ashlar', 128, 192, (g, W, H) => {
      g.fillStyle = STONE;
      g.fillRect(0, 0, W, H);
      const r = kit.rng(0.613);
      for (let j = 0; j < 6; j++)
        for (let i = 0; i < 2; i++) {
          g.fillStyle = `rgba(${r() < 0.5 ? '150,140,115' : '255,250,235'},${0.04 + r() * 0.07})`;
          g.fillRect(((i + (j % 2) * 0.5) * W) / 2, (j * H) / 6, W / 2, H / 6);
        }
      g.fillStyle = 'rgba(150,140,118,0.55)';
      for (let j = 0; j < 6; j++) {
        g.fillRect(0, (j * H) / 6, W, 1.5);
        for (let i = 0; i < 2; i++)
          g.fillRect(((i + (j % 2) * 0.5) * W) / 2, (j * H) / 6, 1.5, H / 6);
      }
    });
    const ashlarW = kit.paintedMaterial(
      'sm:ashlarw',
      128,
      192,
      (g, W, H) => {
        g.fillStyle = STONE;
        g.fillRect(0, 0, W, H);
        g.fillStyle = 'rgba(150,140,118,0.5)';
        for (let j = 0; j < 6; j++) {
          g.fillRect(0, (j * H) / 6, W, 1.5);
          for (let i = 0; i < 2; i++)
            g.fillRect(((i + (j % 2) * 0.5) * W) / 2, (j * H) / 6, 1.5, H / 6);
        }
      },
      { vertexColors: true },
    );
    // Wellcome Wing west wall: deep blue glass with fine mullions (one 3 m x 28 m strip).
    const blueMat = kit.paintedMaterial(
      'sm:blue',
      64,
      512,
      (g, W, H) => {
        const gr = g.createLinearGradient(0, 0, 0, H);
        gr.addColorStop(0, '#2e5fae');
        gr.addColorStop(0.5, '#1f4f9e');
        gr.addColorStop(1, '#163a7a');
        g.fillStyle = gr;
        g.fillRect(0, 0, W, H);
        g.fillStyle = 'rgba(120,170,235,0.55)';
        for (let y = 0; y < H; y += 18) g.fillRect(0, y, W, 1.5);
        g.fillStyle = '#0f2a5c';
        g.fillRect(0, 0, 2, H);
      },
      {
        roughness: 0.15,
        metalness: 0.3,
        emissive: new THREE.Color('#0d2a66'),
        emissiveIntensity: 0.35,
      },
    );

    // ---------- East Block on Exhibition Road ----------
    const EU = 174.3; // front plane
    {
      const ring = [
        [111.2, 123.3],
        [137.6, 123.3],
        [173.8, 123.0],
        [174.2, 190.8],
        [160.5, 190.9],
        [160.4, 182.1],
        [111.2, 182.4],
      ];
      for (let k = 0; k < ring.length; k++) {
        if (k === 2) continue;
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        if (k !== 1 && k !== 3) {
          kit.walls(B, stoneF, [[[a, b]]], 0, 24, { bay: 3.6, storey: 4.0 });
          continue;
        }
        // return elevations seen from Exhibition Road: ashlar with framed windows
        kit.walls(B, ashlarW, [[[a, b]]], 0, 24, { bay: 0.6, storey: 1.8 });
        const rf = EF(a, b);
        for (let z = 0.6; z < 6.4; z += 0.6) eb(rf, stoneD, 0, rf.L, 0, 0.02, z - 0.04, z);
        eb(rf, stone, 0, rf.L, 0, 0.3, 6.4, 7.0);
        eb(rf, stoneD, 0, rf.L, 0, 0.6, 21.9, 22.6);
        eb(rf, stone, 0, rf.L, 0, 0.8, 22.6, 23.2);
        for (const [z, h] of [
          [1.6, 3.4],
          [8.4, 3.0],
          [12.8, 3.0],
          [17.2, 3.0],
        ])
          kit.windowRow(B, a, b, z, {
            width: 2.0,
            height: h,
            bay: 4.5,
            margin: 2.0,
            depth: 0.15,
            glass: winGlass,
            frame: frameM,
            sill: stone,
            head: z === 12.8 ? 'pediment' : 'lintel',
            bars: 2,
            surround: z > 2 ? 0.2 : 0,
            surroundMat: stone,
          });
      }
      const WD = 0.5;
      const V0 = 123.0,
        V1 = 190.8,
        C0 = 134.5,
        C1 = 179.3; // recessed colonnade between end bays
      const f = EF([EU - WD, V0], [EU - WD, V1]); // faces +u (east, Exhibition Road)
      const S = (v) => v - V0;
      const ev = (C0 + C1) / 2;
      // rusticated ground storey with windows and the central entrance
      const gWin = [];
      for (let v = V0 + 2.6; v < V1 - 2; v += 4.5) {
        if (Math.abs(v - ev) < 9) continue;
        gWin.push({ s: S(v), w: 1.9, z0: 1.4, z1: 5.2 });
      }
      const ent = { s: S(ev), w: 16.2, z0: 0.0001, z1: 5.6 };
      slab(f, 0, f.L, 0, 7, [...gWin, { ...ent, z0: 0.4 }], WD, ashlar, stoneL, {
        su: 1 / 2.4,
        sv: 1 / 3.6,
      });
      eb(f, stoneL, ent.s - ent.w / 2, ent.s + ent.w / 2, 0, WD, 0, 0.4);
      for (const h of gWin) {
        metalWin(f, h.s, h.w, h.z0, h.z1, 2, 3);
        eb(f, stoneD, h.s - 1.2, h.s + 1.2, WD, WD + 0.2, h.z0 - 0.2, h.z0);
        // voussoir-like keystone over each opening
        eb(f, stone, h.s - 0.3, h.s + 0.3, WD, WD + 0.12, h.z1, h.z1 + 0.8);
      }
      for (let z = 0.6; z < 6.4; z += 0.6) eb(f, stoneD, 0, f.L, WD, WD + 0.02, z - 0.04, z);
      eb(f, stoneD, 0, f.L, WD, WD + 0.25, 0, 0.5);
      eb(f, stone, 0, f.L, WD, WD + 0.35, 6.4, 7.0);
      eb(f, stoneD, 0, f.L, WD, WD + 0.5, 7.0, 7.3);
      // end bays: solid walls with three tiers of framed windows and quoin strips
      for (const [a, b] of [
        [V0, C0],
        [C1, V1],
      ]) {
        const wins = [];
        for (const v of [a + (b - a) * 0.3, a + (b - a) * 0.7])
          for (const [z0, z1] of [
            [8.4, 11.4],
            [12.8, 15.8],
            [17.2, 20.2],
          ])
            wins.push({ s: S(v), w: 2.0, z0, z1 });
        slab(f, S(a), S(b), 7.3, 22, wins, WD, ashlar, stoneL, { su: 1 / 2.4, sv: 1 / 3.6 });
        for (const h of wins) {
          metalWin(f, h.s, h.w, h.z0, h.z1, 2, 3);
          for (const e of [-1, 1])
            eb(
              f,
              stone,
              h.s + e * 1.15 - 0.15,
              h.s + e * 1.15 + 0.15,
              WD,
              WD + 0.12,
              h.z0 - 0.15,
              h.z1 + 0.15,
            );
          eb(f, stone, h.s - 1.3, h.s + 1.3, WD, WD + 0.12, h.z1, h.z1 + 0.3);
          eb(f, stoneD, h.s - 1.35, h.s + 1.35, WD, WD + 0.22, h.z0 - 0.35, h.z0 - 0.15);
          if (h.z0 === 12.8)
            eb(f, stoneD, h.s - 1.5, h.s + 1.5, WD, WD + 0.35, h.z1 + 0.3, h.z1 + 0.55);
        }
        for (const v of [a + 0.6, b - 0.6])
          eb(f, stoneD, S(v) - 0.6, S(v) + 0.6, WD, WD + 0.25, 7.3, 22);
      }
      // recessed centre: glazed back wall with spandrel panels, giant Ionic columns in front
      const back = EF([EU - 2.4, C0], [EU - 2.4, C1]);
      const nCol = 11,
        sp = (C1 - C0) / nCol;
      const bays = Array.from({ length: nCol + 1 }, (_, k) => {
        const s0 = k === 0 ? 0 : (k - 0.5) * sp,
          s1 = k === nCol ? C1 - C0 : (k + 0.5) * sp;
        return [s0, s1];
      });
      const rh = bays.map(([s0, s1]) => ({
        s: (s0 + s1) / 2,
        w: Math.max(0.8, s1 - s0 - 1.3),
        z0: 8.0,
        z1: 21.0,
      }));
      slab(back, 0, back.L, 7.3, 22, rh, 0.4, ashlar, stoneL, { su: 1 / 2.4, sv: 1 / 3.6 });
      for (const h of rh) {
        metalWin(back, h.s, h.w, h.z0, h.z1, 3, 9);
        for (const z of [11.9, 16.4])
          eb(back, bronze, h.s - h.w / 2, h.s + h.w / 2, 0.02, 0.1, z, z + 1.0);
      }
      flat(stone, R(EU - 2.4, C0, EU, C1), 7.3);
      for (const v of [C0, C1]) {
        const q = v === C0 ? [EU - WD, v, EU - 2.0, v] : [EU - 2.0, v, EU - WD, v];
        B.quad(
          stone,
          [q[0], q[1], 7.3],
          [q[2], q[3], 7.3],
          [q[2], q[3], 22],
          [q[0], q[1], 22],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      const ionic = [
        [0.95, 0],
        [0.95, 0.3],
        [0.82, 0.42],
        [0.86, 0.55],
        [0.74, 0.7],
        [0.72, 0.85],
        [0.66, 7],
        [0.6, 12.2],
        [0.66, 12.3],
        [0.62, 12.42],
        [0.78, 12.6],
        [0.82, 12.75],
        [0.0001, 12.75],
      ];
      for (let k = 0; k < nCol; k++) {
        const v = C0 + (k + 0.5) * sp,
          u = EU - 0.9;
        box(stone, u, v, 7.3, 2.0, 2.0, 0.5);
        lathe(stoneL, ionic, u, v, 7.8, 18);
        // fluting suggested by thin vertical fillets
        for (let i = 0; i < 12; i++) {
          const t = (i * Math.PI) / 6;
          box(stone, u + Math.cos(t) * 0.66, v + Math.sin(t) * 0.66, 8.8, 0.06, 0.06, 10.6, t);
        }
        // Ionic capital: volutes and abacus
        for (const sg of [-1, 1]) {
          const g = new THREE.CylinderGeometry(0.32, 0.32, 1.6, 10).rotateZ(Math.PI / 2);
          geo(stone, g, u + 0.02, v + sg * 0.68, 20.35);
        }
        box(stone, u, v, 20.55, 1.9, 1.9, 0.3);
      }
      // entablature: architrave, frieze, dentilled cornice
      eb(f, stone, 0, f.L, -1.9, WD + 0.05, 20.85, 21.9);
      eb(f, stoneL, 0, f.L, -1.9, WD + 0.1, 21.9, 23.1);
      for (let s = 0.2; s < f.L; s += 0.45)
        eb(f, stone, s - 0.11, s + 0.11, WD + 0.1, WD + 0.3, 22.9, 23.15);
      eb(f, stoneD, -0.3, f.L + 0.3, -1.9, WD + 0.85, 23.15, 23.7);
      eb(f, stone, -0.3, f.L + 0.3, -1.9, WD + 0.95, 23.7, 24.1);
      // attic storey with windows, and a parapet
      const attic = R(113, 124.6, EU - 1.4, 189.4);
      kit.walls(B, stone, [[attic]], 24, 27.8);
      const af = EF([EU - 1.4, 124.6], [EU - 1.4, 189.4]);
      for (let s = 2.2; s < af.L - 1; s += 4.5) {
        eb(af, winGlass, s - 0.8, s + 0.8, 0.0, 0.03, 24.8, 26.8);
        for (const e of [-1, 0, 1])
          eb(af, frameM, s + e * 0.8 - 0.04, s + e * 0.8 + 0.04, 0.03, 0.08, 24.8, 26.8);
        eb(af, stone, s - 1.0, s + 1.0, 0, 0.12, 24.6, 24.8);
        for (const e of [-1, 1])
          eb(af, stoneD, s + e * 2.25 - 0.3, s + e * 2.25 + 0.3, 0, 0.15, 24.0, 27.8);
      }
      kit.cornice(B, stoneD, attic, 27.4, { height: 0.4, projection: 0.3 });
      flat(lead, attic, 27.8);
      kit.walls(B, stone, [[kit.offsetRing(attic, 0.3)]], 27.8, 28.5);
      flat(lead, ring, 24.1);
      // entrance: glazed doors, revolving door drums and the lettered canopy
      const ef = EF([EU - WD + 0.2, ev - 8], [EU - WD + 0.2, ev + 8]);
      eb(ef, darkGlass, 0, 16, -0.05, 0.05, 0.4, 5.6);
      for (let s = 0; s <= 16.01; s += 1.6) eb(ef, alu, s - 0.06, s + 0.06, 0.05, 0.15, 0.4, 5.6);
      eb(ef, alu, 0, 16, 0.05, 0.15, 3.2, 3.3);
      for (const s of [4, 12]) {
        const [x, y] = ef.P(s, 0.6);
        cyl(glass, x, y, 0.4, 1.3, 2.8, 16);
        cyl(alu, x, y, 3.2, 1.38, 0.25, 16);
      }
      box(kit.mat('#30353a'), EU + 2.2, ev, 5.4, 4.4, 20, 0.5);
      for (const v of [ev - 9.5, ev + 9.5]) box(steel, EU + 4.1, v, 0.4, 0.18, 0.18, 5.0);
      const sign = kit.paintedMaterial('sm:sign', 1024, 64, (g, W, H) => {
        g.fillStyle = '#30353a';
        g.fillRect(0, 0, W, H);
        g.fillStyle = '#f2f2f2';
        g.font = 'bold 44px sans-serif';
        g.textAlign = 'center';
        g.textBaseline = 'middle';
        g.fillText('SCIENCE MUSEUM', W / 2, H / 2 + 2);
      });
      B.quad(
        sign,
        [EU + 4.45, ev - 10, 5.4],
        [EU + 4.45, ev + 10, 5.4],
        [EU + 4.45, ev + 10, 5.9],
        [EU + 4.45, ev - 10, 5.9],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      // entrance steps and paving apron
      for (let k = 0; k < 2; k++) box(stone, EU + 0.6 + k * 0.4, ev, 0, 0.5, 18 - k, 0.4 - k * 0.2);
      box(kit.mat('paving'), EU + 3, (V0 + V1) / 2, 0, 6, V1 - V0, 0.1);
      // flagpoles on the parapet
      for (const v of [V0 + 5, V1 - 5]) {
        cyl(kit.mat('white_steel'), EU - 2.5, v, 28.5, 0.07, 7, 6, 0.04);
        box(kit.mat('#2f5d8c'), EU - 2.5, v + 0.9, 33.2, 0.03, 1.7, 1.1);
      }
    }

    // ---------- Centre Block ----------
    {
      const ring = [
        [-35.9, 124.3],
        [33.6, 124.3],
        [33.6, 118.4],
        [38.4, 118.4],
        [38.4, 124.3],
        [45.3, 124.5],
        [45.4, 127.3],
        [66.2, 127.2],
        [66.2, 123.7],
        [102.1, 123.5],
        [111.2, 123.3],
        [111.2, 157.9],
        [103.9, 158.0],
        [103.8, 149.9],
        [59.1, 150.1],
        [59.1, 152.6],
        [46.2, 152.7],
        [46.2, 155.9],
        [-35.9, 156.0],
      ];
      kit.walls(B, stoneF, [[ring]], 0, 23, { bay: 3.6, storey: 3.83 });
      kit.cornice(B, stoneD, ring, 3.6, { height: 0.35, projection: 0.15 });
      kit.walls(B, stone, [[kit.offsetRing(ring, 0.35)]], 23, 24);
      flat(lead, kit.offsetRing(ring, 0.35), 24);
      // rooftop plant with louvres and roof lights
      for (const [u, v, w, d, h] of [
        [20, 140, 18, 10, 3.5],
        [80, 136, 12, 8, 2.8],
      ]) {
        box(kit.mat('concrete'), u, v, 24, w, d, h);
        for (let k = 0; k < Math.floor(w / 0.7); k++)
          box(
            kit.mat('dark_steel'),
            u - w / 2 + 0.35 + k * 0.7,
            v - d / 2 - 0.02,
            24.4,
            0.08,
            0.06,
            h - 0.8,
          );
        for (const du of [-w / 4, w / 4]) cyl(kit.mat('steel'), u + du, v, 24 + h, 0.9, 1.0, 12);
      }
      for (let u = -28; u < 10; u += 7)
        kit.pitchedRoof(B, glass, stone, R(u, 132, u + 5, 150), Math.PI / 2, 24, 1.6, 'gabled', {
          overhang: 0,
        });
      for (const u of [-40.2, 42.6]) {
        cyl(stone, u, 155.8, 0, 3.6, 25.5, 20);
        for (let z = 3.5; z < 24; z += 3.83) box(winGlass, u, 159.42, z, 0.9, 0.08, 1.8);
        cyl(stoneD, u, 155.8, 25.5, 3.75, 0.4, 20);
      }
    }
    // ---------- link between Centre Block and Wellcome Wing ----------
    {
      const ring = R(-51.5, 125.3, -35.9, 155.9);
      kit.walls(B, concreteF, [[ring]], 0, 24, { bay: 3.6, storey: 4 });
      flat(lead, ring, 24);
    }
    // ---------- Wellcome Wing ----------
    {
      const W0 = -113.4,
        W1 = -51.5,
        H = 28;
      const ring = [
        [W0, 127.7],
        [-78.3, 127.8],
        [-78.3, 125.2],
        [W1, 125.3],
        [W1, 170.9],
        [W0, 170.6],
      ];
      kit.walls(B, kit.facade('metal_clad', 2), [[ring]], 0, H, { bay: 3.6, storey: 4.6 });
      for (let z = 4.6; z < H; z += 4.6)
        kit.cornice(B, kit.mat('dark_steel'), ring, z, { height: 0.2, projection: 0.12 });
      // the blue glass west wall hung between two stair towers
      const u = W0 - 0.35,
        va = 131.2,
        vb = 167.2;
      B.quad(
        blueMat,
        [u, vb, 0.5],
        [u, va, 0.5],
        [u, va, H + 1],
        [u, vb, H + 1],
        [0, 0],
        [12, 0],
        [12, 1],
        [0, 1],
      );
      for (let v = va; v <= vb + 0.01; v += 3) box(steel, u - 0.12, v, 0.5, 0.12, 0.12, H + 0.5);
      for (let z = 0.5; z <= H + 1; z += 2.75)
        box(steel, u - 0.12, (va + vb) / 2, z, 0.1, vb - va, 0.08);
      // stair towers at both ends with the hanging brackets on top
      for (const [v0, v1] of [
        [127.4, va],
        [vb, 170.9],
      ]) {
        const tr = R(W0 - 1.2, v0, W0 + 2.5, v1);
        kit.walls(B, kit.mat('#4f565c', { roughness: 0.5, metalness: 0.4 }), [[tr]], 0, H + 3);
        for (let z = 2; z < H; z += 4.6)
          box(winGlass, W0 - 1.22, (v0 + v1) / 2, z, 0.05, (v1 - v0) * 0.6, 2.4);
        flat(lead, tr, H + 3);
        const vm = (v0 + v1) / 2;
        box(kit.mat('dark_steel'), W0 - 1.8, vm, H + 1, 1.6, 1.0, 1.2);
      }
      // V-shaped diagonal rods carrying the wall to the brackets
      const nV = 6,
        rodM = kit.mat('white_steel');
      for (let k = 0; k < nV; k++) {
        const vL = va + ((vb - va) * k) / nV,
          vR = va + ((vb - va) * (k + 1)) / nV,
          vM = (vL + vR) / 2;
        for (let z = 0.5; z < H; z += 9.3) {
          rod(rodM, [u - 0.45, vL, z + 9.3], [u - 0.45, vM, z], 0.05);
          rod(rodM, [u - 0.45, vR, z + 9.3], [u - 0.45, vM, z], 0.05);
        }
      }
      rod(rodM, [u - 0.45, va, H + 0.5], [W0 - 1.8, 129.3, H + 1.5], 0.09);
      rod(rodM, [u - 0.45, vb, H + 0.5], [W0 - 1.8, 169.0, H + 1.5], 0.09);
      box(kit.mat('dark_steel'), u - 0.45, (va + vb) / 2, H + 0.4, 0.3, vb - va, 0.4);
      box(darkGlass, u - 0.2, 149, 0, 0.4, 36, 0.6);
      // stepped tiers on the roof and a light roof deck
      flat(lead, ring, H);
      kit.walls(B, alu, [[kit.offsetRing(ring, 0.2)]], H, H + 1);
      box(kit.mat('white_steel'), -82, 148, H, 50, 36, 0.6);
      box(glass, -82, 148, H + 0.6, 40, 26, 0.3);
      for (let v = 136; v <= 160; v += 4)
        box(kit.mat('white_steel'), -82, v, H + 0.9, 40, 0.25, 0.35);
      box(darkGlass, -51.3, 148, 0, 0.3, 40, 26);
    }
    // ---------- service range on Museum Lane ----------
    {
      const ring = R(-1.8, 118.4, 33.6, 124.3);
      kit.walls(B, stoneF, [[ring]], 0, 14.9, { bay: 3.6, storey: 3.7 });
      kit.cornice(B, stoneD, ring, 14.3, { height: 0.6, projection: 0.3 });
      flat(lead, ring, 14.9);
    }

    root.add(B.toGroup('science_museum'));
    return root;
  },
};
