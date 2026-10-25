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
    'geometry of the outer glass skin, the extent of brass panels and the number of roof stacks are ' +
    'interpretations of the text descriptions, not measured.',
  build({ THREE, kit, buildings }) {
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
        return { a, b, len, dx: dx / len, dy: dy / len, nx: dy / len, ny: -dx / len };
      });
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

    // Materials.
    const inner = kit.paintedMaterial(
      'msrh:inner',
      512,
      512,
      (c, w, h) => {
        c.fillStyle = '#3d5160';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#b9bdbf';
        for (let k = 0; k < 4; k++) c.fillRect((k * w) / 4, 0, 6, h);
        for (let s = 0; s < 2; s++) c.fillRect(0, (s * h) / 2 + h / 2 - 30, w, 30);
        c.fillStyle = 'rgba(220,235,245,0.15)';
        for (let k = 0; k < 4; k++) c.fillRect((k * w) / 4 + 14, 0, 30, h);
      },
      { roughness: 0.25, metalness: 0.3 },
    );
    const stoneBrass = kit.paintedMaterial(
      'msrh:stone_brass',
      512,
      512,
      (c, w, h) => {
        // 6 m x 2 storeys: pale stone frame, tall perforated brass panels alternating with windows.
        c.fillStyle = '#d8d2c4';
        c.fillRect(0, 0, w, h);
        const sh = h / 2,
          bw = w / 4;
        for (let s = 0; s < 2; s++)
          for (let k = 0; k < 4; k++) {
            const x = k * bw + 12,
              y = s * sh + 16,
              ww = bw - 24,
              hh = sh - 50;
            if ((k + s) % 2 === 0) {
              c.fillStyle = '#8a6b43';
              c.fillRect(x, y, ww, hh);
              c.fillStyle = '#c8a76a'; // backlit perforations
              for (let yy = y + 4; yy < y + hh - 2; yy += 7)
                for (let xx = x + 3 + ((yy / 7) % 2) * 3; xx < x + ww - 2; xx += 7)
                  c.fillRect(xx, yy, 2, 2);
            } else {
              c.fillStyle = '#2f3f4b';
              c.fillRect(x, y, ww, hh);
              c.fillStyle = 'rgba(220,235,245,0.18)';
              c.fillRect(x + 4, y + 4, ww * 0.3, hh - 8);
            }
          }
      },
      { roughness: 0.7 },
    );
    const outerGlass = kit.mat('#9dbccc', {
      roughness: 0.08,
      metalness: 0.5,
      transparent: true,
      opacity: 0.42,
      side: THREE.DoubleSide,
    });
    const frame = kit.mat('#c9ccce', { roughness: 0.4, metalness: 0.5 });
    const stone = kit.mat('#d8d2c4');
    const roofM = kit.mat('#8f918e');
    const brass = kit.mat('#86683f', { roughness: 0.45, metalness: 0.6 });

    // Ground floor: glazed, recessed slightly.
    const gr = kit.offsetRing(ring, -0.8);
    let s = 0;
    for (const e of edgesOf(gr)) {
      face(kit.mat('dark_glass'), e.a, e.b, 0, G, s, e.len, 6, 8);
      s += e.len;
    }
    kit.cap(batch, stone, [[ring]], G, { down: true });

    // Upper floors by orientation.
    s = 0;
    const southEdges = [];
    for (const e of edgesOf(ring)) {
      if (e.len < 0.05) continue;
      const south = e.ny < -0.75,
        west = e.nx < -0.75;
      face(west ? stoneBrass : inner, e.a, e.b, G, H, s, e.len, 6, 2 * ST, G);
      if (south && e.len > 10) southEdges.push(e);
      s += e.len;
    }
    // Parapet + roof.
    kit.walls(batch, stone, [[ring]], H, H + 1.2);
    kit.cap(batch, roofM, [[ring]], H + 0.3);
    const pin = kit.offsetRing(ring, -0.35);
    kit.walls(batch, stone, [[pin.slice().reverse()]], H + 0.3, H + 1.2);
    kit.cap(batch, stone, [[ring, pin.slice().reverse()]], H + 1.2);
    // Stone floor bands on the single-skin north and east faces.
    for (const e of edgesOf(ring)) {
      if (e.len < 6 || e.ny < -0.75 || e.nx < -0.75) continue;
      const ang = Math.atan2(e.dy, e.dx);
      for (let k = 1; k <= 8; k++)
        kit.box(
          batch,
          stone,
          (e.a[0] + e.b[0]) / 2 + e.nx * 0.2,
          (e.a[1] + e.b[1]) / 2 + e.ny * 0.2,
          G + k * ST - 0.5,
          e.len,
          0.4,
          0.5,
          ang,
        );
    }

    // Twin-skin south elevation: outer skin of angled glass folds hung 1.0 m out,
    // panels tilted alternately (saw-tooth in plan), with aluminium fold mullions and
    // walkway grilles at each floor.
    for (const e of southEdges) {
      const ang = Math.atan2(e.dy, e.dx);
      const bay = 3.0,
        n = Math.max(1, Math.round(e.len / bay)),
        bl = e.len / n;
      const P = (t, d) => [e.a[0] + e.dx * t + e.nx * d, e.a[1] + e.dy * t + e.ny * d];
      for (let k = 0; k < n; k++) {
        const t0 = k * bl,
          t1 = (k + 1) * bl;
        const dA = 0.7,
          dB = 1.6; // fold: panel leans out from 0.7 m to 1.6 m
        const a = P(t0, dA),
          b = P(t1, dB);
        face(outerGlass, a, b, G, H + 1.2, 0, 1, 1, 1);
        // return of the fold
        const c2 = P(t1, dA);
        face(outerGlass, b, c2, G, H + 1.2, 0, 1, 1, 1);
        kit.box(batch, frame, b[0], b[1], G, 0.18, 0.18, H + 1.2 - G, ang);
        kit.box(batch, frame, c2[0], c2[1], G, 0.12, 0.12, H + 1.2 - G, ang);
      }
      for (let k = 0; k <= 8; k++) {
        const m = P(e.len / 2, 0.9);
        kit.box(batch, frame, m[0], m[1], G + k * ST - 0.15, e.len, 1.5, 0.15, ang);
      }
      // top capping
      const m = P(e.len / 2, 0.9);
      kit.box(batch, frame, m[0], m[1], H + 1.2, e.len, 1.9, 0.35, ang);
    }
    // Brass fins framing the Imperial Square (west) frontage.
    for (const e of edgesOf(ring)) {
      if (e.len < 6 || !(e.nx < -0.75)) continue;
      const ang = Math.atan2(e.dy, e.dx);
      for (let t = 1.5; t < e.len; t += 3)
        kit.box(
          batch,
          brass,
          e.a[0] + e.dx * t + e.nx * 0.3,
          e.a[1] + e.dy * t + e.ny * 0.3,
          G,
          0.25,
          0.6,
          H - G,
          ang,
        );
    }

    // Roof: plant enclosure and fume-cupboard extract stacks.
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
      let ss = 0;
      const lou = kit.paintedMaterial('msrh:louvre', 128, 128, (c, w, h) => {
        c.fillStyle = '#b4b8b9';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#7b8184';
        for (let y = 0; y < h; y += 10) c.fillRect(0, y, w, 4);
      });
      for (const e of edgesOf(pr)) {
        face(lou, e.a, e.b, H + 0.3, H + 5, ss, e.len, 3, 4.7, H);
        ss += e.len;
      }
      kit.cap(batch, roofM, [[pr]], H + 5);
      // stacks along the centre line of the plant area
      const fr = kit.ringFrame(pr);
      const stack = new THREE.CylinderGeometry(0.55, 0.55, 6, 10).rotateX(Math.PI / 2);
      const steelM = kit.mat('steel');
      for (let k = -3; k <= 3; k++) {
        const u = (k / 7) * fr.length;
        for (const v of [-0.18, 0.18]) {
          const x = fr.cx + Math.cos(fr.angle) * u - Math.sin(fr.angle) * v * fr.width;
          const y = fr.cy + Math.sin(fr.angle) * u + Math.cos(fr.angle) * v * fr.width;
          batch.addGeometry(steelM, stack, new THREE.Matrix4().makeTranslation(x, y, H + 5 + 3));
        }
      }
      stack.dispose();
    }
    g.add(batch.toGroup('imperial_msrh'));
    return g;
  },
};
