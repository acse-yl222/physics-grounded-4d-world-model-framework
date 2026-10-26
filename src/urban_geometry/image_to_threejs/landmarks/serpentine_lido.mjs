// Serpentine Lido, south bank of the Serpentine, Hyde Park. The bathing place was
// revamped in 1930 by George Lansbury, First Commissioner of Works, with a mixed-bathing
// pavilion ("Lansbury's Lido", the first British use of the word); the pavilion now
// houses the Lido Cafe Bar and changing rooms, with a plaque to Lansbury, a lakeside
// terrace, and a roped swimming area in the lake in front.
export default {
  id: 'serpentine_lido',
  name: 'Serpentine Lido and Lido Cafe',
  claims: ['24c98acf-e80d-4b80-b0a5-d142937836c3'],
  references: [
    {
      title: 'Lido (swimming pool) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Lido_(swimming_pool)',
      used_for:
        '1930 revamp under George Lansbury, mixed bathing, "Lansbury\'s Lido", Lansbury plaque on the pavilion',
    },
    {
      title: "London's lidos are swimming in history - London Museum",
      url: 'https://www.londonmuseum.org.uk/collections/london-stories/londons-lidos-swimming-history/',
      used_for: 'Serpentine Lido as the first British lido, opened 1930',
    },
    {
      title: "The Serpentine near Lansbury's Lido - Sarah Colegrave",
      url: 'https://sarahcolegrave.co.uk/generate/pdf/open/medium/oil/the-serpentine-near-landsburys-lido',
      used_for: 'mixed bathing pavilion on the banks of the Serpentine completed 1930',
    },
    {
      title: 'Cool pools, luxury London edition - Luxury Travel Advisor',
      url: 'https://www.luxurytraveladvisor.com/destinations/cool-pools-luxury-london-edition',
      used_for: 'Lido Cafe Bar alongside the lido with waterside tables',
    },
  ],
  notes:
    'No architectural description of the 1930 pavilion was found: the single-storey brick ranges with hipped ' +
    'tiled roofs, the raised central cafe block with a small clock lantern, the white timber veranda on the ' +
    'lake side, the terrace and the buoyed swimming area (placed in the scene lake in front, ~100 x 30 m) are ' +
    'plausible reconstructions, not documented. Walls follow the footprint at 3.6 m (Overture h=10.6 m not used).',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const brick = kit.mat('#8f5a45', { roughness: 0.9 });
    const stone = kit.mat('#ddd6c4');
    const tile = kit.mat('#8a4b38', { roughness: 0.85 });
    const white = kit.mat('white');
    const glass = kit.mat('dark_glass');
    const paving = kit.mat('#c9c1ae');
    const timber = kit.mat('#7d5e43');
    const buoyW = kit.mat('#f4f1ea');
    const buoyR = kit.mat('#d4552f');
    const rope = kit.mat('#d8d2c2');
    const H = 3.6;

    kit.walls(batch, brick, [[ring]], 0, H, { bay: 1e6 });
    kit.cornice(batch, stone, ring, 0, { height: 0.35, projection: 0.05 });
    kit.cornice(batch, stone, ring, H - 0.3, { height: 0.3, projection: 0.25 });
    kit.cap(batch, kit.mat('#6e6a64'), [[ring]], H);
    kit.windowGrid(batch, ring, 1.1, 1, 3, (s, k) => {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      return {
        count: len < 3 ? 0 : undefined,
        bay: 3.2,
        width: 1.4,
        height: 1.6,
        bars: 2,
        glass,
        frame: white,
        sill: stone,
      };
    });
    // hipped tiled roofs over the west and east ranges
    const west = [
      [2109.5, -194.5],
      [2146.5, -201.0],
      [2147.6, -205.4],
      [2108.8, -198.8],
    ];
    const east = [
      [2147.0, -203.0],
      [2172.5, -207.8],
      [2174.0, -213.5],
      [2146.2, -208.0],
    ];
    const angW = Math.atan2(-201.0 + 194.5, 2146.5 - 2109.5);
    for (const [r, ang] of [
      [west, angW],
      [east, Math.atan2(-207.8 + 203.0, 2172.5 - 2147.0)],
    ]) {
      const rr = kit.ringArea(r) < 0 ? r.slice().reverse() : r;
      kit.pitchedRoof(batch, tile, brick, rr, ang, H, 1.6, 'hipped', { overhang: 0.5 });
    }
    // raised central cafe block with clock lantern
    const C = [2135.0, -194.5];
    const cu = [Math.cos(angW), Math.sin(angW)],
      cv = [-Math.sin(angW), Math.cos(angW)];
    const L = (u, v) => [C[0] + cu[0] * u + cv[0] * v, C[1] + cu[1] * u + cv[1] * v];
    const cafe = [L(-7, -4), L(7, -4), L(7, 4), L(-7, 4)];
    kit.walls(batch, brick, [[cafe]], H, H + 2.2, { bay: 1e6 });
    kit.cornice(batch, stone, cafe, H + 1.9, { height: 0.3, projection: 0.3 });
    kit.windowRow(batch, cafe[2], cafe[3], H + 0.5, {
      count: 5,
      width: 1.3,
      height: 1.2,
      bars: 1,
      glass,
      frame: white,
      sill: stone,
    });
    kit.windowRow(batch, cafe[0], cafe[1], H + 0.5, {
      count: 5,
      width: 1.3,
      height: 1.2,
      bars: 1,
      glass,
      frame: white,
      sill: stone,
    });
    kit.pitchedRoof(batch, tile, brick, cafe, angW, H + 2.2, 2.0, 'hipped', { overhang: 0.5 });
    const lc = L(0, 0);
    kit.box(batch, white, lc[0], lc[1], H + 3.6, 1.6, 1.6, 1.4, angW);
    const capG = new THREE.ConeGeometry(1.2, 1.2, 4)
      .rotateX(Math.PI / 2)
      .rotateZ(Math.PI / 4 + angW);
    batch.addGeometry(tile, capG, new THREE.Matrix4().makeTranslation(lc[0], lc[1], H + 5.0 + 0.6));
    capG.dispose();
    const dial = new THREE.CylinderGeometry(0.45, 0.45, 0.06, 16).rotateZ(angW);
    for (const sd of [-1, 1]) {
      const p = L(0, sd * 0.84);
      batch.addGeometry(white, dial, new THREE.Matrix4().makeTranslation(p[0], p[1], H + 4.3));
    }
    dial.dispose();
    // white timber veranda along the lake (north) side of the west range
    const va = L(-24, 6.5),
      vb = L(10, 6.5);
    kit.colonnade(batch, white, va, vb, 0.15, 3.0, {
      count: 14,
      radius: 0.12,
      capital: 'doric',
      segments: 8,
    });
    const vm = L(-7, 5.3);
    kit.box(batch, white, vm[0], vm[1], 3.0, 34.5, 2.9, 0.25, angW);
    kit.box(batch, tile, vm[0], vm[1], 3.25, 34.8, 3.0, 0.12, angW);
    // lakeside terrace
    const terr = [L(-26, 4), L(14, 4), L(16, 16), L(-28, 15)];
    kit.cap(batch, paving, [[kit.ringArea(terr) < 0 ? terr.reverse() : terr]], 0.14, { scale: 3 });
    // timber jetty into the swimming area
    const j0 = L(-6, 15),
      j1 = L(-6, 30);
    kit.box(batch, timber, (j0[0] + j1[0]) / 2, (j0[1] + j1[1]) / 2, 0.3, 2.2, 15, 0.2, angW);
    // buoyed swimming area: lines of floats in the lake
    const area = [L(-40, 16), L(55, 16), L(55, 46), L(-40, 46)];
    const ball = new THREE.SphereGeometry(0.22, 8, 5);
    for (let k = 0; k < 4; k++) {
      if (k === 0) continue; // shore side
      const a = area[k],
        b = area[(k + 1) % 4];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const n = Math.round(len / 1.6);
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        batch.addGeometry(
          i % 5 ? buoyW : buoyR,
          ball,
          new THREE.Matrix4().makeTranslation(
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            0.12,
          ),
        );
      }
      kit.box(
        batch,
        rope,
        (a[0] + b[0]) / 2,
        (a[1] + b[1]) / 2,
        0.1,
        len,
        0.04,
        0.04,
        Math.atan2(b[1] - a[1], b[0] - a[0]),
      );
    }
    ball.dispose();

    g.add(batch.toGroup('serpentine_lido'));
    return g;
  },
};
