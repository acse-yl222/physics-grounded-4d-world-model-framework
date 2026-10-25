// Sir Michael Uren Hub, Imperial College White City Campus (Allies and Morrison,
// completed 2019-20). 13-storey, 54 m biomedical engineering research building on a
// triangular plot beside the elevated Westway (A40) at its junction with Wood Lane.
// A solid vertical plant tower occupies the thin (western) end of the triangle; the
// two long sides are screened by ~1,300 storey-high white precast concrete fins in
// seven permutations arranged in a randomised pattern in front of a glazed curtain
// wall; the wide eastern end is fully glazed.
export default {
  id: 'sir_michael_uren_hub',
  name: 'Sir Michael Uren Hub',
  claims: ['6aebd0ac-3cc5-40f8-85c6-624d5309c8bd'],
  references: [
    {
      title: 'Sir Michael Uren Hub - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Sir_Michael_Uren_Hub',
      used_for: '13 storeys, Allies and Morrison, ISG, opening dates',
    },
    {
      title: 'Sir Michael Uren Hub - Allies and Morrison',
      url: 'https://www.alliesandmorrison.com/projects/sir-michael-uren-hub',
      used_for:
        'triangular plot by the Westway, plant tower at the thin end, fins as shading and privacy screen',
    },
    {
      title: 'Research hub covered in precast concrete fins completed in London - CTBUH',
      url: 'https://www.ctbuh.org/news/research-hub-covered-in-precast-concrete-fins-completed-in-london',
      used_for:
        'two long sides covered in 1,300 precast fins, ~4 m high, seven variants in a randomised pattern',
    },
    {
      title: 'Sir Michael Uren Hub - RIBA London Award 2022',
      url: 'https://www.architecture.com/awards-and-competitions-landing-page/awards/riba-regional-awards/riba-london-award-winners/2022/sir-michael-uren-hub',
      used_for: 'white precast-concrete fins',
    },
    {
      title: 'Milestone building reaches heights - Imperial News',
      url: 'https://imperial.ac.uk/news/181806/milestone-building-reaches-heights',
      used_for: '54 m height',
    },
  ],
  notes:
    'Height 54 m from Imperial (Overture h=5.8 m is wrong). Storey split (5.5 m ground + 12 x 4.0 m) ' +
    'and fin spacing (1.5 m), depth and the exact seven fin permutations are estimated; the plant tower ' +
    'height above the roof and the glazing tint are assumptions. Fins start at level 1; the ground floor is ' +
    'a recessed glazed base.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const H = 54,
      G = 5.5,
      ST = 4.0,
      NST = 12;

    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return { a, b, len, dx: dx / len, dy: dy / len, nx: dy / len, ny: -dx / len };
      });
    const skin = (mat, r, z0, z1, tw, th, base = 0) => {
      let s = 0;
      for (const e of edgesOf(r)) {
        if (e.len < 0.05) continue;
        const v0 = (z0 - base) / th,
          v1 = (z1 - base) / th;
        batch.quad(
          mat,
          [e.a[0], e.a[1], z0],
          [e.b[0], e.b[1], z0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [s / tw, v0],
          [(s + e.len) / tw, v0],
          [(s + e.len) / tw, v1],
          [s / tw, v1],
        );
        s += e.len;
      }
    };

    // Curtain wall: blue-grey glass, 1.5 m mullions, white slab edge + spandrel per storey.
    const glass = kit.paintedMaterial(
      'uren:curtain',
      512,
      512,
      (c, w, h) => {
        const grd = c.createLinearGradient(0, 0, w, h);
        grd.addColorStop(0, '#41566a');
        grd.addColorStop(1, '#2c3b48');
        c.fillStyle = grd;
        c.fillRect(0, 0, w, h);
        for (let s = 0; s < 2; s++) {
          const y0 = (s * h) / 2;
          c.fillStyle = '#d9d7d0'; // slab edge
          c.fillRect(0, y0 + h / 2 - 26, w, 26);
          c.fillStyle = 'rgba(120,150,170,0.25)';
          c.fillRect(0, y0 + 10, w, 60);
        }
        c.fillStyle = '#8c949a';
        for (let k = 0; k < 4; k++) c.fillRect((k * w) / 4, 0, 5, h);
      },
      { roughness: 0.25, metalness: 0.3 },
    );
    const concrete = kit.mat('#e4e1d8', { roughness: 0.85 });
    const fin = kit.mat('#efede6', { roughness: 0.8 });
    const darkGlass = kit.mat('dark_glass');
    const plantMat = kit.paintedMaterial('uren:plant', 256, 256, (c, w, h) => {
      c.fillStyle = '#dcd9d0';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#9a9a95';
      for (let y = 6; y < h; y += 12) c.fillRect(20, y, w - 40, 5); // louvre bands
      c.fillStyle = '#e8e6df';
      c.fillRect(0, h / 2 - 6, w, 12);
    });

    // Ground floor: recessed glazed base under a concrete soffit.
    const inner = kit.offsetRing(ring, -1.2);
    skin(darkGlass, inner, 0, G - 0.6, 6, 8);
    kit.cap(batch, concrete, [[ring]], G - 0.6, { down: true });
    kit.walls(batch, concrete, [[ring]], G - 0.6, G);
    // Upper floors: curtain wall.
    skin(glass, ring, G, H - 1.2, 6, 2 * ST, G);
    // Parapet and roof.
    kit.walls(batch, concrete, [[ring]], H - 1.2, H);
    kit.cap(batch, kit.mat('#8d8f8c'), [[ring]], H - 0.4);
    kit.walls(batch, concrete, [[kit.offsetRing(ring, -0.4).reverse()]], H - 0.4, H);
    kit.cap(batch, concrete, [[ring, kit.offsetRing(ring, -0.4).reverse()]], H);

    // Identify the three sides of the triangle (merge short jogs into the longest edges).
    const E = edgesOf(ring)
      .filter((e) => e.len > 8)
      .sort((p, q) => q.len - p.len);
    const longSides = E.slice(0, 2);
    const endSide = E[2];

    const plantSkip = {};
    // Plant tower at the thin western apex: solid louvred shaft, full height, rising above the roof.
    {
      const [l1, l2] = longSides;
      // Apex end = the short edge joining the two long sides.
      const ends = [
        [l1.a, l2.b, l1, l2],
        [l2.a, l1.b, l2, l1],
      ];
      ends.sort(
        (p, q2) =>
          Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]) -
          Math.hypot(q2[0][0] - q2[1][0], q2[0][1] - q2[1][1]),
      );
      const [pa, pb, ea, eb] = ends[0]; // pa = start of ea, pb = end of eb
      const L = 11;
      const tr = [
        pb,
        [pb[0] + eb.dx * 0, pb[1]],
        pa,
        [pa[0] + ea.dx * L, pa[1] + ea.dy * L],
        [pb[0] - eb.dx * L, pb[1] - eb.dy * L],
      ];
      tr.splice(1, 1);
      const top = H + 4.5;
      const out = kit.offsetRing(tr, 0.25);
      skin(plantMat, out, 0, top, 6, 6, 0);
      kit.cap(batch, concrete, [[out]], top);
      plantSkip.ea = ea;
      plantSkip.eb = eb;
      plantSkip.L = L + 0.5;
    }
    // Precast fins on the two long sides: seven permutations (depth / twist / width).
    const perms = [
      [0.9, 0, 0.3],
      [0.7, 0.25, 0.3],
      [0.7, -0.25, 0.3],
      [1.1, 0.12, 0.35],
      [1.1, -0.12, 0.35],
      [0.55, 0.4, 0.25],
      [0.55, -0.4, 0.25],
    ];
    const r = kit.rng(0.4271);
    const finGeo = new THREE.BoxGeometry(1, 1, 1);
    const m4 = new THREE.Matrix4(),
      q = new THREE.Quaternion(),
      sc = new THREE.Vector3(),
      pos = new THREE.Vector3();
    for (const e of longSides) {
      const n = Math.floor((e.len - 1.5) / 1.5);
      const off = (e.len - n * 1.5) / 2;
      const ang = Math.atan2(e.dy, e.dx);
      for (let f = 0; f <= n; f++) {
        const s = off + f * 1.5;
        if (
          (e === plantSkip.ea && s < plantSkip.L) ||
          (e === plantSkip.eb && s > e.len - plantSkip.L)
        )
          continue;
        for (let k = 0; k < NST; k++) {
          const [d, tw, wd] = perms[Math.floor(r() * 7)];
          const z0 = G + k * ST;
          pos.set(
            e.a[0] + e.dx * s + e.nx * (d / 2 + 0.05),
            e.a[1] + e.dy * s + e.ny * (d / 2 + 0.05),
            z0 + ST / 2 - 0.02,
          );
          q.setFromAxisAngle(new THREE.Vector3(0, 0, 1), ang + Math.PI / 2 + tw);
          sc.set(d, wd, ST - 0.12);
          m4.compose(pos, q, sc);
          batch.addGeometry(fin, finGeo, m4);
        }
      }
      // Fins bear on slim horizontal bands at each floor line.
      const s0 = e === plantSkip.ea ? plantSkip.L : 0.3,
        s1 = e === plantSkip.eb ? e.len - plantSkip.L : e.len - 0.3;
      const sm = (s0 + s1) / 2;
      for (let k = 0; k <= NST; k++) {
        const z = G + k * ST - 0.1;
        const cx = e.a[0] + e.dx * sm + e.nx * 0.45,
          cy = e.a[1] + e.dy * sm + e.ny * 0.45;
        kit.box(batch, fin, cx, cy, z, s1 - s0, 0.9, 0.16, ang);
      }
    }
    // Wide east end: glazed, with deep slab-edge bands.
    {
      const e = endSide,
        ang = Math.atan2(e.dy, e.dx);
      const cx = (e.a[0] + e.b[0]) / 2 + e.nx * 0.3,
        cy = (e.a[1] + e.b[1]) / 2 + e.ny * 0.3;
      for (let k = 0; k <= NST; k++)
        kit.box(batch, concrete, cx, cy, G + k * ST - 0.3, e.len, 0.6, 0.45, ang);
      for (let s = 0; s <= e.len; s += e.len / 6)
        kit.box(
          batch,
          concrete,
          e.a[0] + e.dx * s + e.nx * 0.3,
          e.a[1] + e.dy * s + e.ny * 0.3,
          G,
          0.4,
          0.6,
          H - G - 1.2,
          ang,
        );
    }
    // Rooftop plant screen.
    {
      const roofRing = kit.offsetRing(ring, -7);
      if (kit.ringArea(roofRing) > 50) {
        skin(plantMat, roofRing, H - 0.4, H + 3, 6, 6, 0);
        kit.cap(batch, kit.mat('#9a9c99'), [[roofRing]], H + 3);
      }
    }
    finGeo.dispose();
    g.add(batch.toGroup('sir_michael_uren_hub'));
    return g;
  },
};
