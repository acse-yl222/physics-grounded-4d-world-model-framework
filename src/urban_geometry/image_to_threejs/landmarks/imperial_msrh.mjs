// Molecular Sciences Research Hub (MSRH), Imperial College White City Campus
// (Aukett Swanke, shell and core 2016, Department of Chemistry from 2019). Nine
// storeys of chemistry laboratories beside the Hammersmith & City line. Main south
// elevation: bespoke twin-skin, triple-glazed ventilated curtain wall (Kawneer AA201)
// drawn here as an outer skin of angled (folded) glass; frontage to Imperial Square in
// pale stone/concrete with backlit perforated brass panels (Proteus, TECU Brass);
// single-skin curtain wall to the north; laboratory extract stacks on the roof.
export default {
  id: 'imperial_msrh',
  name: 'Molecular Sciences Research Hub',
  claims: ['2e9ddde6-d87e-4465-a01f-7d3cc82f1dac'],
  references: [
    {
      title: 'Molecular Sciences Research Hub - Aukett Swanke',
      url: 'https://www.aukettswanke.com/projects/molecular-sciences-research-hub/',
      used_for:
        'main facade of stone and backlit perforated bronze cladding plus triple-glazed ventilated curtain wall facing Imperial Square; nine laboratory floors',
    },
    {
      title: 'Imperial College installation - Glass Times',
      url: 'https://glasstimes.co.uk/projects/imperial-college-installation/',
      used_for:
        'twin-skin triple-glazed curtain wall on the south elevation, single-skin on the north facade',
    },
    {
      title:
        'Kawneer glazing systems get under the skin of a new city campus - Specification Online',
      url: 'https://www.specificationonline.co.uk/articles/2018-09-21/kawneer-glazing-systems-get-under-the-skin-of-a-new-city-campus',
      used_for: 'unitised AA201 twin-skin curtain walling',
    },
    {
      title: 'Molecular Sciences Research Hub, Imperial College - Proteus Facades',
      url: 'https://proteusfacades.com/project/molecular-sciences-research-hub-imperial-college/',
      used_for: 'perforated TECU Brass panels with patinated finish on a flat concrete facade',
    },
  ],
  notes:
    'Overture h=11.9 m is wrong; 9 storeys at 5.5 m + 8 x 4.2 m = ~39 m plus plant (estimate). The fold ' +
    'geometry of the outer glass skin, the stone grid / brass panel rhythm on the Imperial Square (west) ' +
    'frontage, the entrance position and canopy, the roof stack count and bracing are interpretations of the ' +
    'text descriptions, not measured. Imperial Square is represented only by the paved strip, tree pits, ' +
    'benches and lamps directly in front of the west elevation; its real layout was not found.',
  build({ THREE, kit, buildings, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const G = 5.5,
      ST = 4.2,
      H = G + 8 * ST; // 39.1

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
    const ebox = (mat, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, mat, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const face = (mat, a, b, z0, z1, s0, len, tw, th, base = 0) => {
      const v0 = (z0 - base) / th,
        v1 = (z1 - base) / th;
      batch.quad(
        mat,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [s0 / tw, v0],
        [(s0 + len) / tw, v0],
        [(s0 + len) / tw, v1],
        [s0 / tw, v1],
      );
    };

    // ---- materials ---------------------------------------------------------------
    const inner = kit.paintedMaterial(
      'msrh:glass',
      256,
      512,
      (c, w, h) => {
        for (let s = 0; s < 2; s++) {
          const y0 = (s * h) / 2,
            sh = h / 2;
          const grd = c.createLinearGradient(0, y0, 0, y0 + sh);
          grd.addColorStop(0, '#a3b0b5'); // lit lab ceilings
          grd.addColorStop(0.12, '#566c79');
          grd.addColorStop(0.6, '#33454f');
          grd.addColorStop(1, '#40525d');
          c.fillStyle = grd;
          c.fillRect(0, y0, w, sh);
          c.fillStyle = 'rgba(225,235,240,0.12)';
          c.fillRect(w * 0.1, y0 + sh * 0.25, w * 0.3, sh * 0.6);
        }
      },
      { roughness: 0.2, metalness: 0.3 },
    );
    const brassPanel = kit.paintedMaterial(
      'msrh:brass',
      256,
      512,
      (c, w, h) => {
        // perforated patinated brass, lit from behind at the perforations
        c.fillStyle = '#93744a';
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.733);
        for (let y = 4; y < h; y += 8)
          for (let x = 3 + ((y / 8) % 2) * 4; x < w; x += 8) {
            const k = 0.5 + 0.5 * Math.sin(y / 40 + x / 90) + (r() - 0.5) * 0.3;
            c.fillStyle = k > 0.55 ? '#d8b979' : '#b08f58';
            c.fillRect(x, y, 3, 3);
          }
      },
      { roughness: 0.45, metalness: 0.55 },
    );
    const outerGlass = kit.mat('#9dbccc', {
      roughness: 0.08,
      metalness: 0.5,
      transparent: true,
      opacity: 0.38,
      side: THREE.DoubleSide,
    });
    const frame = kit.mat('#c9ccce', { roughness: 0.4, metalness: 0.5 });
    const mull = kit.mat('#555c60', { roughness: 0.4, metalness: 0.5 });
    const stone = kit.mat('#d8d2c4', { roughness: 0.8 });
    const stone2 = kit.mat('#cfc8b8', { roughness: 0.85 });
    const roofM = kit.mat('#8f918e');
    const brass = kit.mat('#a07e4c', { roughness: 0.4, metalness: 0.45 });
    const darkGlass = kit.mat('#26333c', { roughness: 0.12, metalness: 0.4 });
    const steelM = kit.mat('steel');
    const lou = kit.mat('#b4b8b9', { roughness: 0.5, metalness: 0.3 });
    const paving = kit.mat('#cbc5b8', { roughness: 0.9 });
    const paving2 = kit.mat('#b3ada0', { roughness: 0.9 });

    const kind = (e) => (e.ny < -0.75 ? 'south' : e.nx < -0.75 ? 'west' : 'plain');
    const all = edgesOf(ring).filter((e) => e.len > 0.05);

    // ---- ground floor: recessed glazing, stone piers, soffit ------------------------
    const GR = 1.0;
    const gr = kit.offsetRing(ring, -GR);
    for (const e of edgesOf(gr)) {
      if (e.len < 0.05) continue;
      face(darkGlass, e.a, e.b, 0, G - 0.6, 0, e.len, 6, 8);
      const n = Math.max(1, Math.round(e.len / 1.5));
      for (let k = 0; k <= n; k++)
        ebox(mull, e, (k * e.len) / n - 0.04, (k * e.len) / n + 0.04, 0, 0.15, 0, G - 0.6);
      ebox(mull, e, 0, e.len, 0, 0.12, 3.1, 3.2);
    }
    kit.cap(batch, stone, [[ring]], G - 0.6, { down: true });
    kit.walls(batch, stone, [[ring]], G - 0.6, G);
    kit.cornice(batch, stone2, gr, 0, { height: 0.2, projection: 0.15 });
    for (const e of all) {
      if (e.len < 7) continue;
      const n = Math.round(e.len / 6);
      for (let k = 0; k <= n; k++) {
        const s = 0.4 + ((e.len - 0.8) * k) / n;
        ebox(stone, e, s - 0.35, s + 0.35, -0.7, 0, 0, G - 0.6);
      }
    }

    // ---- upper floors --------------------------------------------------------------
    const southEdges = [];
    for (const e of all) {
      const kd = kind(e);
      const GL = kd === 'west' ? -0.45 : -0.25;
      const p = at(e, 0, GL),
        q = at(e, e.len, GL);
      face(inner, p, q, G, H, 0, e.len, 3, 2 * ST, G);
      if (kd === 'south' && e.len > 10) southEdges.push(e);
      if (e.len < 1) {
        ebox(stone, e, 0, e.len, GL, 0, G, H);
        continue;
      }
      if (kd === 'west') {
        // Imperial Square frontage: pale stone grid, deep reveals, perforated brass panels
        // alternating with full-height windows.
        const n = Math.max(1, Math.round(e.len / 3));
        const bw = e.len / n;
        for (let k = 0; k <= n; k++) {
          const s = Math.min(e.len - 0.3, Math.max(0.3, k * bw));
          ebox(stone, e, s - 0.3, s + 0.3, GL, 0.1, G, H);
        }
        for (let f = 0; f <= 8; f++)
          ebox(stone, e, 0, e.len, GL, 0.15, G + f * ST - 0.35, G + f * ST + 0.35);
        for (let f = 0; f < 8; f++)
          for (let k = 0; k < n; k++) {
            if ((k + f) % 3 === 0) continue; // window bay
            const s0 = k * bw + 0.3,
              s1 = (k + 1) * bw - 0.3;
            const a = at(e, s0, -0.25),
              b = at(e, s1, -0.25);
            face(brassPanel, a, b, G + f * ST + 0.35, G + (f + 1) * ST - 0.35, 0, 1, 1, 1);
          }
        // window frames / mullions in the open bays
        for (let k = 0; k < n; k++) {
          const sm = (k + 0.5) * bw;
          ebox(mull, e, sm - 0.04, sm + 0.04, GL, GL + 0.12, G, H);
        }
      } else {
        // curtain wall with mullions on 1.5 m and stone floor bands (north / east), or
        // inner skin of the twin-skin facade (south)
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(mull, e, s - 0.04, s + 0.04, GL, GL + 0.18, G, H);
        }
        for (let f = 0; f < 8; f++)
          ebox(mull, e, 0, e.len, GL, GL + 0.12, G + f * ST + 1.0, G + f * ST + 1.07);
        if (kd !== 'south')
          for (let f = 1; f <= 8; f++)
            ebox(stone, e, 0, e.len, GL, 0.2, G + f * ST - 0.5, G + f * ST);
      }
    }
    // Parapet + roof.
    kit.walls(batch, stone, [[ring]], H, H + 1.2);
    kit.cap(batch, roofM, [[ring]], H + 0.3);
    const pin = kit.offsetRing(ring, -0.35);
    kit.walls(batch, stone, [[pin.slice().reverse()]], H + 0.3, H + 1.2);
    kit.cap(batch, stone, [[ring, pin.slice().reverse()]], H + 1.2);
    kit.cornice(batch, stone2, ring, H + 1.0, { height: 0.2, projection: 0.12 });

    // ---- twin-skin south elevation ---------------------------------------------------
    for (const e of southEdges) {
      const bay = 3.0,
        n = Math.max(1, Math.round(e.len / bay)),
        bl = e.len / n;
      for (let k = 0; k < n; k++) {
        const t0 = k * bl,
          t1 = (k + 1) * bl;
        const dA = 0.7,
          dB = 1.6;
        const a = at(e, t0, dA),
          b = at(e, t1, dB),
          c2 = at(e, t1, dA);
        face(outerGlass, a, b, G, H + 1.2, 0, 1, 1, 1);
        face(outerGlass, b, c2, G, H + 1.2, 0, 1, 1, 1);
        kit.box(batch, frame, b[0], b[1], G, 0.18, 0.18, H + 1.2 - G, e.ang);
        kit.box(batch, frame, c2[0], c2[1], G, 0.12, 0.12, H + 1.2 - G, e.ang);
        kit.box(batch, frame, a[0], a[1], G, 0.12, 0.12, H + 1.2 - G, e.ang);
        // horizontal fold transoms at each floor
        for (let f = 0; f <= 8; f++) {
          const z = G + f * ST;
          const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          kit.box(
            batch,
            frame,
            m[0],
            m[1],
            z + 1.0,
            len,
            0.1,
            0.08,
            Math.atan2(b[1] - a[1], b[0] - a[0]),
          );
        }
      }
      for (let f = 0; f <= 8; f++)
        ebox(frame, e, 0, e.len, 0.05, 1.5, G + f * ST - 0.15, G + f * ST);
      ebox(frame, e, 0, e.len, -0.1, 1.8, H + 1.2, H + 1.55);
    }
    // Brass fins framing the Imperial Square (west) frontage.
    for (const e of all) {
      if (e.len < 6 || kind(e) !== 'west') continue;
      const n = Math.max(1, Math.round(e.len / 3));
      for (let k = 0; k < n; k++) {
        const t = ((k + 0.5) * e.len) / n;
        ebox(brass, e, t - 0.06, t + 0.06, 0.1, 0.75, G, H);
      }
    }

    // ---- west entrance: canopy, doors, name, Imperial Square --------------------------
    const westEdges = all.filter((e) => kind(e) === 'west').sort((p, q) => q.len - p.len);
    if (westEdges.length) {
      const e = westEdges[0],
        sm = e.len / 2;
      ebox(stone, e, sm - 5, sm + 5, -GR, 2.8, G - 1.4, G - 1.0);
      ebox(brass, e, sm - 5, sm + 5, 2.7, 2.85, G - 1.5, G - 1.0);
      for (const ds of [-1.8, 0, 1.8])
        ebox(mull, e, sm + ds - 0.8, sm + ds + 0.8, -GR, -GR + 0.2, 0, 2.7);
      const sign = kit.paintedMaterial(
        'msrh:sign',
        512,
        64,
        (cx, w, h) => {
          cx.fillStyle = '#86683f';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#f3ead6';
          cx.font = 'bold 28px sans-serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('MOLECULAR SCIENCES RESEARCH HUB', w / 2, h / 2 + 2);
        },
        { roughness: 0.5, metalness: 0.3 },
      );
      const a = at(e, sm - 4.5, 2.87),
        b = at(e, sm + 4.5, 2.87);
      face(sign, a, b, G - 1.45, G - 1.05, 0, 1, 1, 1);

      // Imperial Square: paving with a grid of joints, tree pits, benches and lamps.
      const sq = [at(e, -8, 0.2), at(e, e.len + 6, 0.2), at(e, e.len + 6, 15), at(e, -8, 15)];
      if (kit.ringArea(sq) < 0) sq.reverse();
      kit.cap(batch, paving, [[sq]], 0.05, { scale: 3 });
      for (let d = 2.5; d < 15; d += 2.5) {
        const p = at(e, -8, d),
          q = at(e, e.len + 6, d);
        const m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
        kit.box(batch, paving2, m[0], m[1], 0.05, e.len + 14, 0.08, 0.012, e.ang);
      }
      const trees = [],
        benches = [],
        lamps = [];
      const rr = kit.rng(0.1906);
      for (let s = -4; s <= e.len + 3; s += 8) {
        trees.push([...at(e, s, 11), rr() * 6, 8 + rr() * 3]);
        kit.cap(
          batch,
          kit.mat('#5b4a3a'),
          [
            [
              [-0.9, -0.9],
              [0.9, -0.9],
              [0.9, 0.9],
              [-0.9, 0.9],
            ].map(([u, v]) => {
              const c = at(e, s + u, 11 + v);
              return c;
            }),
          ].map((r) => (kit.ringArea(r) < 0 ? [r.reverse()] : [r])),
          0.07,
        );
        if (s + 4 < e.len + 3) benches.push([...at(e, s + 4, 11), e.ang + Math.PI]);
      }
      for (const s of [-6, sm, e.len + 4]) lamps.push([...at(e, s, 6.5), e.ang]);
      g.add(placeAssets('london_plane', trees, { scaleOf: (p) => p[3] }));
      g.add(placeAssets('bench', benches));
      g.add(placeAssets('street_lamp', lamps));
      g.add(placeAssets('waste_basket', [[...at(e, sm + 7, 3.5), 0]]));
      g.add(
        placeAssets(
          'bicycle_stand',
          [0, 1, 2, 3, 4].map((k) => [...at(e, e.len + 1 + k, 2.5), e.ang + Math.PI / 2]),
        ),
      );
    }

    // ---- roof: louvred plant enclosure and fume-cupboard extract stacks ----------------
    const rf = kit.ringFrame(ring);
    const pr = [
      [-0.32, -0.3],
      [0.32, -0.3],
      [0.32, 0.3],
      [-0.32, 0.3],
    ].map(([u, v]) => [
      rf.cx + Math.cos(rf.angle) * u * rf.length - Math.sin(rf.angle) * v * rf.width,
      rf.cy + Math.sin(rf.angle) * u * rf.length + Math.cos(rf.angle) * v * rf.width,
    ]);
    if (kit.ringArea(pr) < 0) pr.reverse();
    {
      const prIn = kit.offsetRing(pr, -0.3);
      kit.walls(batch, kit.mat('#6a6f72'), [[prIn]], H + 0.3, H + 4.8);
      kit.cap(batch, roofM, [[prIn]], H + 4.8);
      for (const e of edgesOf(pr)) {
        for (let z = H + 0.5; z < H + 5; z += 0.3) ebox(lou, e, 0, e.len, -0.2, 0, z, z + 0.06);
        for (let s = 0; s <= e.len; s += 3)
          ebox(mull, e, s - 0.05, s + 0.05, -0.25, 0.02, H + 0.3, H + 5.1);
      }
      const fr = kit.ringFrame(pr);
      const stack = new THREE.CylinderGeometry(0.55, 0.55, 6, 12).rotateX(Math.PI / 2);
      const capG = new THREE.CylinderGeometry(0.75, 0.6, 0.4, 12).rotateX(Math.PI / 2);
      const pos = [];
      for (let k = -3; k <= 3; k++) {
        const u = (k / 7) * fr.length;
        for (const v of [-0.18, 0.18]) {
          const x = fr.cx + Math.cos(fr.angle) * u - Math.sin(fr.angle) * v * fr.width;
          const y = fr.cy + Math.sin(fr.angle) * u + Math.cos(fr.angle) * v * fr.width;
          batch.addGeometry(steelM, stack, new THREE.Matrix4().makeTranslation(x, y, H + 4.8 + 3));
          batch.addGeometry(mull, capG, new THREE.Matrix4().makeTranslation(x, y, H + 4.8 + 6.2));
          pos.push([x, y]);
        }
      }
      // steel bracing frame tying the stacks together
      for (const v of [-0.18, 0.18])
        for (const z of [H + 8, H + 10]) {
          const p = (u) => [
            fr.cx + Math.cos(fr.angle) * u - Math.sin(fr.angle) * v * fr.width,
            fr.cy + Math.sin(fr.angle) * u + Math.cos(fr.angle) * v * fr.width,
          ];
          const c = p(0);
          kit.box(batch, mull, c[0], c[1], z, (6 / 7) * fr.length, 0.15, 0.15, fr.angle);
        }
      stack.dispose();
      capG.dispose();
    }
    g.add(batch.toGroup('imperial_msrh'));
    return g;
  },
};
