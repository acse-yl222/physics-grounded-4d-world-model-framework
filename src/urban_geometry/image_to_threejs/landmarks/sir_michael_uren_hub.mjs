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
        'two long sides covered in 1,300 precast fins, ~4 m high, seven variants in a randomised pattern, GGBS-rich white concrete, glazed curtain walls behind',
    },
    {
      title: 'Sir Michael Uren Hub - RIBA London Award 2022',
      url: 'https://www.architecture.com/awards-and-competitions-landing-page/awards/riba-regional-awards/riba-london-award-winners/2022/sir-michael-uren-hub',
      used_for: 'white precast-concrete fins, full-height windows in a shallow plan',
    },
    {
      title: 'Sir Michael Uren Hub - New London Architecture',
      url: 'https://nla.london/projects/sir-michael-uren-hub',
      used_for: 'ground-floor main entrance with function / exhibition space',
    },
    {
      title: 'Milestone building reaches heights - Imperial News',
      url: 'https://imperial.ac.uk/news/181806/milestone-building-reaches-heights',
      used_for: '54 m height',
    },
  ],
  notes:
    'Height 54 m from Imperial (Overture h=5.8 m is wrong). Storey split (5.5 m ground + 12 x 4.0 m), the ' +
    'fin pitch (1.5 m), the seven fin permutations (tapered precast blades varying in depth, width and plan ' +
    'angle) and their random sequence are estimates of the described pattern, not measured. Curtain-wall ' +
    'mullion pitch, ground-floor colonnade, entrance position on the wide east end, rooftop plant screen, ' +
    'flues and the forecourt furniture/trees are assumptions; the plant tower height above the roof and ' +
    'the glazing tint are approximate.',
  build({ THREE, kit, buildings, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const H = 54,
      G = 5.5,
      ST = 4.0,
      NST = 12,
      TOP = H - 1.2; // top of curtain wall / start of parapet

    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return {
          a,
          b,
          len,
          dx: dx / len,
          dy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
        };
      });
    const at = (e, s, d) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    const quadUV = (mat, p, q, z0, z1, u0, u1, v0, v1) =>
      batch.quad(
        mat,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], z1],
        [p[0], p[1], z1],
        [u0, v0],
        [u1, v0],
        [u1, v1],
        [u0, v1],
      );
    // Box along edge e from s0 to s1, from offset d0 to d1 (outward), z0..z1.
    const ebox = (mat, e, s0, s1, d0, d1, z0, z1, color) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, mat, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang, color);
    };

    // ---- materials ---------------------------------------------------------------
    // Glass behind the mullions: dark interior with a pale ceiling soffit band per storey.
    const glass = kit.paintedMaterial(
      'uren:glass',
      256,
      512,
      (c, w, h) => {
        for (let s = 0; s < 2; s++) {
          const y0 = (s * h) / 2,
            sh = h / 2;
          const grd = c.createLinearGradient(0, y0, 0, y0 + sh);
          grd.addColorStop(0, '#9aa7ad'); // lit ceiling seen through the glass
          grd.addColorStop(0.1, '#566a77');
          grd.addColorStop(0.5, '#2f404c');
          grd.addColorStop(1, '#3a4d5a');
          c.fillStyle = grd;
          c.fillRect(0, y0, w, sh);
          c.fillStyle = 'rgba(210,225,235,0.10)';
          c.fillRect(w * 0.1, y0 + sh * 0.2, w * 0.25, sh * 0.7);
        }
      },
      { roughness: 0.18, metalness: 0.35 },
    );
    const fin = kit.mat('#f1efe8', { roughness: 0.78, vertexColors: true });
    const precast = kit.mat('#e8e5dc', { roughness: 0.82 });
    const mullion = kit.mat('#4d5458', { roughness: 0.45, metalness: 0.5 });
    const darkGlass = kit.mat('#26333c', { roughness: 0.12, metalness: 0.4 });
    const roofM = kit.mat('#8d8f8c');
    const louvreM = kit.mat('#b9bbb6', { roughness: 0.6, metalness: 0.3 });
    const steel = kit.mat('steel');
    const paving = kit.mat('#c9c3b6', { roughness: 0.9 });

    // ---- triangle sides -------------------------------------------------------------
    const E = edgesOf(ring)
      .filter((e) => e.len > 8)
      .sort((p, q) => q.len - p.len);
    const longSides = E.slice(0, 2);
    const endSide = E[2];
    const isLong = (e) => longSides.includes(e);

    // Plant tower at the thin western apex.
    const [l1, l2] = longSides;
    const ends = [
      [l1.a, l2.b, l1, l2],
      [l2.a, l1.b, l2, l1],
    ].sort(
      (p, q) =>
        Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]) -
        Math.hypot(q[0][0] - q[1][0], q[0][1] - q[1][1]),
    );
    const [pa, pb, ea, eb] = ends[0];
    const PL = 11; // plant tower length along each long side
    // Curtain wall span on each edge (skip the plant tower on the long sides).
    const span = (e) => {
      let s0 = 0,
        s1 = e.len;
      if (e === ea) s0 = PL + 0.4;
      if (e === eb) s1 = e.len - PL - 0.4;
      return [s0, s1];
    };

    // ---- ground floor: recessed double-height glazing behind a precast colonnade ----
    const GR = 1.6; // recess
    const inner = kit.offsetRing(ring, -GR);
    {
      let u = 0;
      for (const e of edgesOf(inner)) {
        if (e.len < 0.05) continue;
        quadUV(darkGlass, e.a, e.b, 0, G - 0.7, u / 6, (u + e.len) / 6, 0, 1);
        // mullions every 1.5 m and a transom at door-head height
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(mullion, e, s - 0.04, s + 0.04, 0, 0.16, 0, G - 0.7);
        }
        ebox(mullion, e, 0, e.len, 0, 0.14, 3.0, 3.09);
        u += e.len;
      }
      kit.cap(batch, precast, [[ring]], G - 0.7, { down: true });
      kit.walls(batch, precast, [[ring]], G - 0.7, G);
      // Precast columns under the edge of the upper floors.
      for (const e of edgesOf(ring)) {
        if (e.len < 6) continue;
        const [s0, s1] = span(e);
        if (s1 - s0 < 4) continue;
        const n = Math.max(1, Math.round((s1 - s0) / 7.5));
        for (let k = 0; k <= n; k++) {
          const s = s0 + 0.5 + ((s1 - s0 - 1) * k) / n;
          ebox(precast, e, s - 0.3, s + 0.3, -0.9, -0.3, 0, G - 0.7);
        }
      }
      // Stone plinth / step line and a paved apron around the base.
      kit.cornice(batch, precast, inner, 0, { height: 0.15, projection: 0.12 });
      const apron = kit.offsetRing(ring, 3.2);
      kit.cap(batch, paving, [[apron, inner.slice().reverse()]], 0.04);
    }

    // ---- upper floors: curtain wall, slab bands, mullions -----------------------------
    const GL = 0.3; // glass set back behind the face of the slab band
    for (const e of edgesOf(ring)) {
      if (e.len < 0.05) continue;
      const [s0, s1] = span(e);
      if (s1 - s0 < 0.3) continue;
      const p = at(e, s0, -GL),
        q = at(e, s1, -GL);
      quadUV(glass, p, q, G, TOP, s0 / 3, s1 / 3, 0, (TOP - G) / (2 * ST));
      // returns of the reveal at plant-tower junctions
      // Slab-edge bands (white precast) at every floor line.
      for (let k = 0; k <= NST; k++) {
        const z = G + k * ST;
        ebox(precast, e, s0, s1, -GL, isLong(e) ? 0.35 : 0.25, z - 0.3, z + 0.3);
      }
      // Aluminium mullions on a 1.5 m module and a cill transom at 0.9 m.
      if (e.len < 2) continue;
      const n = Math.max(1, Math.round((s1 - s0) / 1.5));
      for (let k = 0; k <= n; k++) {
        const s = s0 + ((s1 - s0) * k) / n;
        ebox(mullion, e, s - 0.04, s + 0.04, -GL, -GL + 0.2, G, TOP);
      }
      for (let k = 0; k < NST; k++)
        ebox(mullion, e, s0, s1, -GL, -GL + 0.14, G + k * ST + 1.0, G + k * ST + 1.07);
    }

    // ---- precast fins on the two long sides -------------------------------------------
    // Seven permutations of a tapered blade: [depth, plan angle, root width, tip width].
    const perms = [
      [1.0, 0.0, 0.32, 0.18],
      [0.8, 0.28, 0.3, 0.16],
      [0.8, -0.28, 0.3, 0.16],
      [1.2, 0.14, 0.36, 0.2],
      [1.2, -0.14, 0.36, 0.2],
      [0.6, 0.45, 0.26, 0.14],
      [0.6, -0.45, 0.26, 0.14],
    ];
    const FH = ST - 0.6; // fin height between slab bands
    const finGeo = perms.map(([d, , w0, w1]) => {
      const sh = new THREE.Shape();
      sh.moveTo(0, -w0 / 2);
      sh.lineTo(d, -w1 / 2);
      sh.lineTo(d, w1 / 2);
      sh.lineTo(0, w0 / 2);
      sh.closePath();
      return new THREE.ExtrudeGeometry(sh, { depth: FH, bevelEnabled: false });
    });
    const r = kit.rng(0.4271);
    const m4 = new THREE.Matrix4(),
      rot = new THREE.Matrix4();
    let finCount = 0;
    for (const e of longSides) {
      const [s0, s1] = span(e);
      const n = Math.floor((s1 - s0 - 0.75) / 1.5);
      const off = s0 + (s1 - s0 - n * 1.5) / 2;
      for (let f = 0; f <= n; f++) {
        const s = off + f * 1.5;
        for (let k = 0; k < NST; k++) {
          const pi = Math.floor(r() * 7);
          const [, tw] = perms[pi];
          const root = at(e, s, 0.32);
          // local x = outward normal rotated by the permutation's plan angle
          rot.makeRotationZ(Math.atan2(e.ny, e.nx) + tw);
          m4.makeTranslation(root[0], root[1], G + k * ST + 0.3).multiply(rot);
          const v = 0.93 + r() * 0.07;
          batch.addGeometry(fin, finGeo[pi], m4, [v, v, v * 0.985]);
          finCount++;
        }
      }
    }
    finGeo.forEach((x) => x.dispose());

    // ---- plant tower: precast frame with horizontal louvre slats ------------------------
    {
      const tr = [pb, pa, at(ea, PL, 0), at(eb, eb.len - PL, 0)];
      const out = kit.offsetRing(kit.ringArea(tr) < 0 ? tr.reverse() : tr, 0.25);
      const ptop = H + 4.5;
      const back = kit.offsetRing(out, -0.25);
      kit.walls(batch, kit.mat('#55595c'), [[back]], 0, ptop);
      kit.cap(batch, precast, [[out]], ptop);
      for (const e of edgesOf(out)) {
        if (e.len < 1) continue;
        // corner piers
        ebox(precast, e, 0, 0.6, -0.3, 0.05, 0, ptop);
        ebox(precast, e, e.len - 0.6, e.len, -0.3, 0.05, 0, ptop);
        // storey bands
        for (let z = G; z <= ptop - 0.5; z += ST)
          ebox(precast, e, 0, e.len, -0.3, 0.05, z - 0.3, z + 0.3);
        ebox(precast, e, 0, e.len, -0.3, 0.05, 0, 0.6);
        ebox(precast, e, 0, e.len, -0.3, 0.05, ptop - 0.8, ptop);
        // louvre slats between the bands
        for (let z = 0.9; z < ptop - 0.9; z += 0.32) {
          const zz = z - G;
          if (zz > -0.4 && ((zz % ST) + ST) % ST > ST - 0.45) continue; // under the bands
          if (zz > -0.4 && ((zz % ST) + ST) % ST < 0.4) continue;
          ebox(louvreM, e, 0.6, e.len - 0.6, -0.2, 0.0, z, z + 0.07);
        }
      }
    }

    // ---- wide east end: entrance canopy, revolving door, name plate ---------------------
    {
      const e = endSide;
      const sm = e.len / 2;
      // slender precast piers framing the glazed end, carried down to the colonnade
      for (let k = 0; k <= 6; k++) {
        const s = 0.4 + ((e.len - 0.8) * k) / 6;
        ebox(precast, e, s - 0.22, s + 0.22, -GL, 0.55, G - 0.7, TOP);
      }
      // cantilevered canopy over the entrance
      ebox(precast, e, sm - 6, sm + 6, -GR, 3.0, G - 1.5, G - 1.1);
      ebox(mullion, e, sm - 6, sm + 6, 2.95, 3.05, G - 1.6, G - 1.1);
      // revolving door drum in the recessed glazing
      const c = at(e, sm, -GR + 0.2);
      const drum = new THREE.CylinderGeometry(1.4, 1.4, 2.6, 16, 1, true).rotateX(Math.PI / 2);
      batch.addGeometry(darkGlass, drum, new THREE.Matrix4().makeTranslation(c[0], c[1], 1.3));
      drum.dispose();
      const lid = new THREE.CylinderGeometry(1.5, 1.5, 0.3, 16).rotateX(Math.PI / 2);
      batch.addGeometry(mullion, lid, new THREE.Matrix4().makeTranslation(c[0], c[1], 2.75));
      lid.dispose();
      for (const ds of [-3, 3])
        ebox(mullion, e, sm + ds - 0.9, sm + ds + 0.9, -GR, -GR + 0.25, 0, 2.6);
      const sign = kit.paintedMaterial(
        'uren:sign',
        512,
        64,
        (cx, w, h) => {
          cx.fillStyle = '#f1efe8';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#1f2a44';
          cx.font = 'bold 34px sans-serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('SIR MICHAEL UREN HUB', w / 2, h / 2 + 2);
        },
        { roughness: 0.6 },
      );
      const a = at(e, sm - 5, 3.08),
        b = at(e, sm + 5, 3.08);
      quadUV(sign, a, b, G - 1.5, G - 1.1, 0, 1, 0, 1);
      // Forecourt: bollards, benches and trees in front of the entrance.
      const bol = [],
        ben = [],
        tre = [];
      for (let s = 3; s < e.len - 2; s += 2.4)
        if (Math.abs(s - sm) > 4) bol.push([...at(e, s, 4.5), e.ang]);
      for (const s of [6, e.len - 6]) ben.push([...at(e, s, 6.5), e.ang + Math.PI]);
      for (const s of [3, sm - 9, sm + 9, e.len - 3]) tre.push([...at(e, s, 9), r() * 6]);
      g.add(placeAssets('bollard', bol));
      g.add(placeAssets('bench', ben));
      g.add(placeAssets('london_plane', tre, { scaleOf: () => 9 }));
      const fc = [at(e, -1, 3.1), at(e, e.len + 1, 3.1), at(e, e.len + 1, 11), at(e, -1, 11)];
      if (kit.ringArea(fc) < 0) fc.reverse();
      kit.cap(batch, paving, [[fc]], 0.04);
    }

    // ---- parapet, roof, plant screen, flues ---------------------------------------------
    kit.walls(batch, precast, [[ring]], TOP, H);
    kit.cap(batch, roofM, [[ring]], H - 0.4);
    const pin = kit.offsetRing(ring, -0.4);
    kit.walls(batch, precast, [[pin.slice().reverse()]], H - 0.4, H);
    kit.cap(batch, precast, [[ring, pin.slice().reverse()]], H);
    kit.cornice(batch, precast, ring, H - 0.25, { height: 0.25, projection: 0.12 });
    // safety rail set back from the parapet
    const rail = kit.offsetRing(ring, -1.6);
    for (const e of edgesOf(rail)) {
      if (e.len < 1) continue;
      ebox(steel, e, 0, e.len, -0.03, 0.03, H - 0.4 + 1.05, H - 0.4 + 1.1);
      for (let s = 0; s < e.len; s += 2.5)
        ebox(steel, e, s - 0.03, s + 0.03, -0.03, 0.03, H - 0.4, H + 0.7);
    }
    const roofRing = kit.offsetRing(ring, -7);
    if (kit.ringArea(roofRing) > 50) {
      const zr = H - 0.4,
        zt = H + 3.2;
      kit.walls(batch, kit.mat('#6b6f70'), [[kit.offsetRing(roofRing, -0.3)]], zr, zt - 0.2);
      kit.cap(batch, kit.mat('#9a9c99'), [[kit.offsetRing(roofRing, -0.3)]], zt - 0.2);
      for (const e of edgesOf(roofRing)) {
        if (e.len < 0.5) continue;
        const n = Math.floor(e.len / 0.35);
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / Math.max(1, n);
          ebox(louvreM, e, s - 0.03, s + 0.03, -0.18, 0.0, zr, zt);
        }
        ebox(louvreM, e, 0, e.len, -0.2, 0.02, zt - 0.12, zt);
      }
      // extract flues and AHU boxes on the plant deck
      const fr = kit.ringFrame(roofRing);
      const flue = new THREE.CylinderGeometry(0.45, 0.45, 5, 12).rotateX(Math.PI / 2);
      for (let k = -2; k <= 2; k++) {
        const u = (k / 5.5) * fr.length;
        const x = fr.cx + Math.cos(fr.angle) * u,
          y = fr.cy + Math.sin(fr.angle) * u;
        batch.addGeometry(steel, flue, new THREE.Matrix4().makeTranslation(x, y, zt + 2.3));
      }
      flue.dispose();
    }

    const out = batch.toGroup('sir_michael_uren_hub');
    out.userData.fins = finCount;
    g.add(out);
    return g;
  },
};
