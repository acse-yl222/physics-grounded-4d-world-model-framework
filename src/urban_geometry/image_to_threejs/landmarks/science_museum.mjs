// Science Museum, Exhibition Road, South Kensington.
// East Block (Sir Richard Allison, 1913-1928): Portland stone classical front on
// Exhibition Road with a rusticated ground storey, a recessed giant colonnade between
// end bays, entablature and attic. Centre Block infill (1960s-1980) in stone-faced
// concrete, and the Wellcome Wing (MacCormac Jamieson Prichard, 2000) at the west
// end whose west elevation is a vast wall of blue glass.
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
      title: 'Glowing panes - Building',
      url: 'https://building.co.uk/focus/glowing-panes/8923.article',
      used_for:
        'blue glass wall fills the west elevation of the Wellcome Wing (MacCormac Jamieson Prichard)',
    },
    {
      title: "Science Museum's Wellcome Wing - Heritage Fund",
      url: 'https://heritagefund.org.uk/projects/science-museums-wellcome-wing',
      used_for: 'Wellcome Wing opening 2000',
    },
    {
      title: 'Photo showing the construction of the East Block of the Science Museum',
      url: 'https://collection.sciencemuseumgroup.org.uk/documents/aa110146179',
      used_for: 'East Block as a steel-framed stone-faced block on Exhibition Road',
    },
  ],
  notes:
    'Footprint from Overture; Overture height (12.9 m, inferred) replaced by estimates: East Block 24 m cornice + attic ' +
    'to 28 m (six public floors), Centre Block 24 m, Wellcome Wing 28 m. The Exhibition Road elevation (rusticated base, ' +
    'recessed giant colonnade, attic) is reconstructed from general descriptions, not measured drawings; column count ' +
    'and window rhythm are approximate. The Museum Lane service range is a schematic stone block.',

  build({ THREE, kit }) {
    const root = new THREE.Group();
    root.position.set(O[0], O[1], 0);
    root.rotation.z = ANG;
    const B = new kit.MeshBatch();
    const STONE = '#ddd6c4',
      STONE_D = '#c9c1ad',
      WIN = '#2b3540';
    const stone = kit.mat('portland_stone'),
      stoneD = kit.mat(STONE_D),
      lead = kit.mat('lead'),
      darkGlass = kit.mat('dark_glass'),
      glass = kit.mat('glass'),
      steel = kit.mat('steel'),
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

    // ---------- painted elevations ----------
    // Rusticated ground storey (one 4.5 m bay, 7 m high).
    const rustMat = kit.paintedMaterial('sm:rust', 128, 200, (g, W, H) => {
      const s = H / 7,
        Y = (z) => H - z * s;
      g.fillStyle = STONE;
      g.fillRect(0, 0, W, H);
      g.fillStyle = STONE_D;
      for (let z = 0.6; z < 7; z += 0.6) g.fillRect(0, Y(z), W, 2);
      g.fillStyle = WIN;
      g.fillRect(W * 0.27, Y(5.6), W * 0.46, 4.4 * s);
      g.fillStyle = STONE_D;
      g.fillRect(W * 0.24, Y(5.9), W * 0.52, 0.3 * s);
      g.fillRect(W * 0.47, Y(5.6), W * 0.06, 0.6 * s);
    });
    // Tall windows between the giant columns (one 4.5 m bay, 7..22 m).
    const colBayMat = kit.paintedMaterial('sm:colbay', 128, 420, (g, W, H) => {
      const s = H / 15,
        Y = (z) => H - z * s;
      g.fillStyle = STONE;
      g.fillRect(0, 0, W, H);
      g.fillStyle = WIN;
      for (const [z0, z1] of [
        [0.8, 4.6],
        [5.8, 9.6],
        [10.8, 14.0],
      ])
        g.fillRect(W * 0.2, Y(z1), W * 0.6, (z1 - z0) * s);
      g.fillStyle = '#4b5662';
      for (const z of [4.6, 9.6]) g.fillRect(W * 0.2, Y(z + 1.2), W * 0.6, 1.2 * s);
      g.fillStyle = STONE_D;
      for (const z of [0.8, 5.8, 10.8]) g.fillRect(W * 0.17, Y(z), W * 0.66, 0.25 * s);
      g.fillStyle = '#56606a';
      for (let k = 1; k < 3; k++) g.fillRect(W * (0.2 + k * 0.2), 0, 1.5, H);
    });
    // Attic storey (one 4.5 m bay, 3.8 m).
    const atticMat = kit.paintedMaterial('sm:attic', 128, 108, (g, W, H) => {
      g.fillStyle = STONE;
      g.fillRect(0, 0, W, H);
      g.fillStyle = WIN;
      g.fillRect(W * 0.3, H * 0.25, W * 0.4, H * 0.5);
    });
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
      // back and side walls (the Exhibition Road edge is built separately below)
      for (let k = 0; k < ring.length; k++) {
        if (k === 2) continue;
        kit.walls(B, stoneF, [[[ring[k], ring[(k + 1) % ring.length]]]], 0, 24, {
          bay: 3.6,
          storey: 4.0,
        });
      }
      // painted Exhibition Road front (overlaid, slightly proud)
      const f = (m, v0, v1, z0, z1, u = EU + 0.05) => {
        const n = Math.max(1, Math.round((v1 - v0) / 4.5));
        B.quad(
          m,
          [u, v0, z0],
          [u, v1, z0],
          [u, v1, z1],
          [u, v0, z1],
          [0, 0],
          [n, 0],
          [n, 1],
          [0, 1],
        );
      };
      const V0 = 123.0,
        V1 = 190.8,
        C0 = 134.5,
        C1 = 179.3; // recessed colonnade between end bays
      f(rustMat, V0, V1, 0, 7);
      // end bays: windows in plain wall, with quoins
      f(colBayMat, V0, C0, 7, 22);
      f(colBayMat, C1, V1, 7, 22);
      for (const v of [V0 + 0.6, C0 - 0.6, C1 + 0.6, V1 - 0.6])
        box(stoneD, EU + 0.3, v, 7, 0.6, 1.2, 15);
      // recessed centre: wall set back 2 m, giant columns standing at the front plane
      const back = EU - 2.2;
      B.quad(
        colBayMat,
        [back, C0, 7],
        [back, C1, 7],
        [back, C1, 22],
        [back, C0, 22],
        [0, 0],
        [10, 0],
        [10, 1],
        [0, 1],
      );
      flat(stone, R(back, C0, EU, C1), 7);
      B.quad(
        stone,
        [EU, C0, 7],
        [back, C0, 7],
        [back, C0, 22],
        [EU, C0, 22],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      B.quad(
        stone,
        [back, C1, 7],
        [EU, C1, 7],
        [EU, C1, 22],
        [back, C1, 22],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const nCol = 11;
      for (let k = 0; k < nCol; k++) {
        const v = C0 + ((k + 0.5) * (C1 - C0)) / nCol;
        cyl(stone, EU - 0.7, v, 7.8, 0.75, 13.4, 14, 0.66);
        box(stone, EU - 0.7, v, 7, 1.9, 1.9, 0.8); // base
        box(stone, EU - 0.7, v, 21.2, 1.9, 1.9, 0.8); // capital
      }
      // entablature, cornice, attic, parapet
      box(stone, EU - 0.5, (V0 + V1) / 2, 22, 1.4, V1 - V0 + 0.8, 2.3);
      box(stoneD, EU + 0.2, (V0 + V1) / 2, 24, 1.4, V1 - V0 + 1.4, 0.7);
      const attic = R(113, 124.6, EU - 1.4, 189.4);
      texWalls(atticMat, attic, 24, 27.8, 4.5);
      flat(lead, attic, 27.8);
      kit.walls(B, stone, [[kit.offsetRing(attic, 0.3)]], 27.8, 28.4);
      flat(lead, ring, 24);
      // string course over the rustication
      box(stoneD, EU + 0.15, (V0 + V1) / 2, 6.6, 0.6, V1 - V0, 0.5);
      // entrance: glazed doors and canopy with signage at the centre
      const ev = (C0 + C1) / 2;
      box(darkGlass, EU + 0.12, ev, 0, 0.3, 16, 5.4);
      for (let v = ev - 8; v <= ev + 8; v += 2.67) box(alu, EU + 0.3, v, 0, 0.2, 0.15, 5.4);
      box(kit.mat('#30353a'), EU + 2.2, ev, 5.4, 4.4, 20, 0.5);
      // "SCIENCE MUSEUM" lettering band
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
      // paving apron
      box(kit.mat('paving'), EU + 3, (V0 + V1) / 2, 0, 6, V1 - V0, 0.1);
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
      kit.walls(B, stone, [[kit.offsetRing(ring, 0.35)]], 23, 24);
      flat(lead, kit.offsetRing(ring, 0.35), 24);
      // rooftop plant and roof lights
      box(kit.mat('concrete'), 20, 140, 24, 18, 10, 3.5);
      box(kit.mat('concrete'), 80, 136, 24, 12, 8, 2.8);
      for (let u = -28; u < 10; u += 7)
        kit.pitchedRoof(B, glass, stone, R(u, 132, u + 5, 150), Math.PI / 2, 24, 1.6, 'gabled', {
          overhang: 0,
        });
      // rounded stair towers on the north side
      for (const u of [-40.2, 42.6]) cyl(stone, u, 155.8, 0, 3.6, 25.5, 20);
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
      // side walls: dark metal cladding and glazing bands
      kit.walls(B, kit.facade('metal_clad', 2), [[ring]], 0, H, { bay: 3.6, storey: 4.6 });
      // the blue glass west wall, standing proud of the frame
      const u = W0 - 0.35;
      B.quad(
        blueMat,
        [u, 170.9, 0.5],
        [u, 127.4, 0.5],
        [u, 127.4, H + 1],
        [u, 170.9, H + 1],
        [0, 0],
        [14, 0],
        [14, 1],
        [0, 1],
      );
      for (let v = 127.4; v <= 171; v += 6.2) box(steel, u - 0.3, v, 0, 0.5, 0.25, H + 1);
      box(darkGlass, u - 0.2, 149, 0, 0.4, 43.5, 0.6);
      // stepped tiers on the roof and a light roof deck
      flat(lead, ring, H);
      kit.walls(B, alu, [[kit.offsetRing(ring, 0.2)]], H, H + 1);
      box(kit.mat('white_steel'), -82, 148, H, 50, 36, 0.6);
      box(glass, -82, 148, H + 0.6, 40, 26, 0.3);
      box(darkGlass, -51.3, 148, 0, 0.3, 40, 26); // glazed junction with the centre block
    }
    // ---------- service range on Museum Lane ----------
    {
      const ring = R(-1.8, 118.4, 33.6, 124.3);
      kit.walls(B, stoneF, [[ring]], 0, 14.9, { bay: 3.6, storey: 3.7 });
      flat(lead, ring, 14.9);
    }

    root.add(B.toGroup('science_museum'));
    return root;
  },
};
