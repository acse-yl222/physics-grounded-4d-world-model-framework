// Eighty-Eight Wood Lane, Imperial College White City Campus (PLP Architecture with
// Aukett Swanke masterplan; facade by Lindner, completed ~2018). 34-storey residential
// tower for Imperial staff / key workers at the corner of Wood Lane and the Westway,
// part of the Imperial West scheme with Wood Lane Studios. Unitised facade of ~1.5 m
// panels mixing glass and terracotta plates; clear horizontal bands split the tower
// into four stacked sections and the form tapers as it rises.
export default {
  id: 'eighty_eight_wood_lane',
  name: 'Eighty-Eight Wood Lane (Imperial West tower)',
  claims: ['afb20d8e-65e4-4afd-9763-e88e74c3c86f'],
  references: [
    {
      title: 'Eighty Eight Wood Lane - PLP Architecture',
      url: 'https://plparchitecture.com/?p=5788',
      used_for:
        '34-storey residential tower, glass and terracotta cladding, four sections divided by horizontal bands, tapering form, floor-to-ceiling glazing, glazed lift box running the full height',
    },
    {
      title: 'Imperial College White City Campus Block F - Lindner',
      url: 'https://www.lindner-group.com/en/references/imperial-college-white-city-campus-block-f',
      used_for:
        'facade panels mostly 1.5 m wide mixing glass and terracotta plates, 80 Wood Lane, 2018',
    },
    {
      title: 'Imperial West masterplan - Aukett Swanke',
      url: 'https://www.aukettswanke.com/projects/imperial-west-masterplan/',
      used_for: 'masterplan context with Wood Lane Studios',
    },
  ],
  notes:
    'Overture h=7.7 m is wrong; height 34 storeys x 3.15 m + crown = ~111 m (no metric height found). ' +
    'Taper modelled as four stepped sections (1.1 m inset per section, railed ledges) on the oriented ' +
    'rectangle of the footprint. Each 1.5 m unitised panel is real geometry (mullions, slab transoms, ' +
    'terracotta plates on ~45% of panels in a seeded random mix); the actual panel pattern, the lift box ' +
    'position (west face) and size, the louvred crown, canopy and forecourt are approximations.',
  build({ THREE, kit, buildings, frame, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring0 = buildings[0].polys[0][0];
    const e = kit.orientedExtent(ring0, frame.angle);
    const L = e.u1 - e.u0,
      W = e.v1 - e.v0;
    const uc = (e.u0 + e.u1) / 2,
      vc = (e.v0 + e.v1) / 2;
    const rect0 = (l, w) =>
      [
        e.at(uc - l / 2, vc - w / 2, 0),
        e.at(uc + l / 2, vc - w / 2, 0),
        e.at(uc + l / 2, vc + w / 2, 0),
        e.at(uc - l / 2, vc + w / 2, 0),
      ].map((p) => [p[0], p[1]]);
    const rect = (l, w) => {
      const r = rect0(l, w);
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const ST = 3.15,
      NS = 34,
      G = 5;

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
    const skin = (mat, r, z0, z1, tw, th, base = 0) => {
      let s = 0;
      for (const ed of edgesOf(r)) {
        const v0 = (z0 - base) / th,
          v1 = (z1 - base) / th;
        batch.quad(
          mat,
          [ed.a[0], ed.a[1], z0],
          [ed.b[0], ed.b[1], z0],
          [ed.b[0], ed.b[1], z1],
          [ed.a[0], ed.a[1], z1],
          [s / tw, v0],
          [(s + ed.len) / tw, v0],
          [(s + ed.len) / tw, v1],
          [s / tw, v1],
        );
        s += ed.len;
      }
    };

    const at = (ed, s, d) => [ed.a[0] + ed.dx * s + ed.nx * d, ed.a[1] + ed.dy * s + ed.ny * d];
    const ebox = (mat, ed, s0, s1, d0, d1, z0, z1) => {
      const c = at(ed, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, mat, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, ed.ang);
    };

    const glassTex = kit.paintedMaterial(
      '88wl:glass',
      128,
      256,
      (c, w, h) => {
        const grd = c.createLinearGradient(0, 0, 0, h);
        grd.addColorStop(0, '#93a2aa');
        grd.addColorStop(0.12, '#5a7385');
        grd.addColorStop(1, '#33475a');
        c.fillStyle = grd;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(200,220,235,0.16)';
        c.fillRect(w * 0.1, h * 0.2, w * 0.3, h * 0.7);
      },
      { roughness: 0.18, metalness: 0.35 },
    );
    // Terracotta plates: horizontal baguette-like plate joints, three tones.
    const terraMats = ['#b86a47', '#c27752', '#a95f3f'].map((col, k) =>
      kit.paintedMaterial(
        `88wl:terra${k}`,
        64,
        128,
        (c, w, h) => {
          c.fillStyle = col;
          c.fillRect(0, 0, w, h);
          c.fillStyle = 'rgba(0,0,0,0.16)';
          for (let y = 10; y < h; y += 16) c.fillRect(0, y, w, 2);
          c.fillStyle = 'rgba(255,255,255,0.06)';
          for (let y = 2; y < h; y += 16) c.fillRect(0, y, w, 2);
        },
        { roughness: 0.75 },
      ),
    );
    const band = kit.mat('#e2ded5', { roughness: 0.6 });
    const mullM = kit.mat('#cfcac0', { roughness: 0.4, metalness: 0.4 });
    const darkGlass = kit.mat('#26333c', { roughness: 0.12, metalness: 0.4 });
    const liftGlass = kit.mat('#88a7b6', {
      roughness: 0.1,
      metalness: 0.4,
      transparent: true,
      opacity: 0.55,
    });
    const roofM = kit.mat('#8f918e');
    const lou = kit.mat('#b9bdbd', { roughness: 0.5, metalness: 0.3 });
    const steel = kit.mat('steel');
    const paving = kit.mat('#c9c3b6', { roughness: 0.9 });

    // Glazed double-height base on the actual footprint.
    let br = ring0.slice();
    if (kit.ringArea(br) < 0) br.reverse();
    const brIn = kit.offsetRing(br, -0.8);
    for (const ed of edgesOf(brIn)) {
      if (ed.len < 0.05) continue;
      batch.quad(
        darkGlass,
        [ed.a[0], ed.a[1], 0],
        [ed.b[0], ed.b[1], 0],
        [ed.b[0], ed.b[1], G - 0.8],
        [ed.a[0], ed.a[1], G - 0.8],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      const n = Math.max(1, Math.round(ed.len / 1.5));
      for (let k = 0; k <= n; k++)
        ebox(mullM, ed, (k * ed.len) / n - 0.04, (k * ed.len) / n + 0.04, 0, 0.15, 0, G - 0.8);
      ebox(mullM, ed, 0, ed.len, 0, 0.12, 3.0, 3.1);
    }
    kit.walls(batch, band, [[br]], G - 0.8, G);
    kit.cap(batch, band, [[br]], G - 0.8, { down: true });
    kit.cornice(batch, kit.mat('#9a958c'), brIn, 0, { height: 0.15, projection: 0.12 });

    // Four stacked, tapering sections of unitised 1.5 m panels (glass or terracotta),
    // separated by recessed glazed bands with projecting white edges.
    const per = [9, 9, 8, 8];
    const rnd = kit.rng(0.8812);
    let z = G;
    let liftFace = null;
    for (let sct = 0; sct < 4; sct++) {
      const inset = sct * 1.1;
      const r = rect(L - 2 * inset, W - 2 * inset);
      const z1 = z + per[sct] * ST;
      const zf = z1 - 0.9;
      for (const ed of edgesOf(r)) {
        // glass line set back behind the panel frames
        const p = at(ed, 0, -0.2),
          q = at(ed, ed.len, -0.2);
        batch.quad(
          glassTex,
          [p[0], p[1], z],
          [q[0], q[1], z],
          [q[0], q[1], zf],
          [p[0], p[1], zf],
          [0, 0],
          [ed.len / 1.5, 0],
          [ed.len / 1.5, (zf - z) / ST],
          [0, (zf - z) / ST],
        );
        const n = Math.max(1, Math.round(ed.len / 1.5));
        const pw = ed.len / n;
        for (let k = 0; k <= n; k++)
          ebox(mullM, ed, k * pw - 0.05, k * pw + 0.05, -0.2, 0.08, z, zf);
        for (let f = 0; f < per[sct]; f++) {
          const zz = z + f * ST;
          ebox(mullM, ed, 0, ed.len, -0.2, 0.06, zz, zz + 0.25); // slab-line transom
          for (let k = 0; k < n; k++) {
            if (rnd() >= 0.45) continue;
            const m = terraMats[Math.floor(rnd() * 3)];
            const top = Math.min(zz + ST, zf);
            ebox(m, ed, k * pw + 0.05, (k + 1) * pw - 0.05, -0.15, 0.04, zz + 0.25, top);
          }
        }
        if (!liftFace && sct === 0 && ed.nx < -0.5) liftFace = ed;
      }
      // band: recessed storey-line with projecting white edge
      const rr = rect(L - 2 * inset - 0.8, W - 2 * inset - 0.8);
      skin(darkGlass, rr, zf, z1, 6, 4);
      const rb = rect(L - 2 * inset + 0.4, W - 2 * inset + 0.4);
      kit.walls(batch, band, [[rb]], z1 - 0.35, z1);
      kit.cap(batch, band, [[rb]], z1);
      kit.cap(batch, band, [[rb]], z1 - 0.35, { down: true });
      kit.cap(batch, band, [[r]], zf, { down: true });
      // terrace at each set-back: steel balustrade on the ledge
      if (sct > 0) {
        const lr = rect(L - 2 * inset + 1.0, W - 2 * inset + 1.0);
        for (const ed of edgesOf(lr)) {
          ebox(steel, ed, 0, ed.len, -0.03, 0.03, z + 0.95, z + 1.0);
          for (let s = 0; s <= ed.len; s += 1.5)
            ebox(steel, ed, s - 0.02, s + 0.02, -0.02, 0.02, z, z + 1.0);
        }
      }
      z = z1;
    }
    const zTop = z;
    // Glazed lift box running the full height on the west (Wood Lane) face.
    if (liftFace) {
      const ed = liftFace,
        sm = ed.len * 0.5;
      // the box hugs the top section's face (3.3 m in) and stands 1.3 m proud at the base
      const D0 = -3.3,
        D1 = 1.3;
      const c = at(ed, sm, (D0 + D1) / 2);
      kit.box(batch, liftGlass, c[0], c[1], G, 4.2, D1 - D0, zTop - G + 2, ed.ang);
      for (const ds of [-2.1, 2.1])
        ebox(mullM, ed, sm + ds - 0.08, sm + ds + 0.08, D1 - 0.16, D1, G, zTop + 2);
      for (let zz = G; zz <= zTop + 2; zz += ST) {
        ebox(mullM, ed, sm - 2.1, sm + 2.1, D1 - 0.16, D1, zz - 0.08, zz + 0.08);
        for (const ds of [-2.1, 2.1])
          ebox(mullM, ed, sm + ds - 0.08, sm + ds + 0.08, D0, D1, zz - 0.08, zz + 0.08);
      }
      ebox(band, ed, sm - 2.3, sm + 2.3, D0, D1 + 0.2, zTop + 2, zTop + 2.4);
      // entrance canopy and forecourt at the foot of the lift box
      const eb =
        edgesOf(brIn)
          .filter((q) => q.nx < -0.5)
          .sort((p, q) => q.len - p.len)[0] ?? ed;
      ebox(band, eb, eb.len / 2 - 4, eb.len / 2 + 4, 0, 3.2, 3.6, 3.9);
      const bol = [];
      for (let s = 0; s <= eb.len; s += 2.2) bol.push([...at(eb, s, 5.5), eb.ang]);
      g.add(placeAssets('bollard', bol));
      g.add(
        placeAssets(
          'london_plane',
          [
            [...at(eb, -3, 7.5), 1, 9],
            [...at(eb, eb.len + 3, 7.5), 2, 9],
          ],
          { scaleOf: (p) => p[3] },
        ),
      );
      const fc = [at(eb, -6, 0.8), at(eb, eb.len + 6, 0.8), at(eb, eb.len + 6, 9), at(eb, -6, 9)];
      if (kit.ringArea(fc) < 0) fc.reverse();
      kit.cap(batch, paving, [[fc]], 0.04);
    }
    // Crown: plant enclosure in real vertical aluminium louvres, BMU track, roof deck.
    const topR = rect(L - 2 * 3.3 - 6, W - 2 * 3.3 - 2);
    kit.walls(batch, kit.mat('#6c7073'), [[kit.offsetRing(topR, -0.3)]], zTop, zTop + 4.3);
    kit.cap(batch, roofM, [[kit.offsetRing(topR, -0.3)]], zTop + 4.3);
    for (const ed of edgesOf(topR)) {
      for (let s = 0; s <= ed.len; s += 0.4)
        ebox(lou, ed, s - 0.04, s + 0.04, -0.25, 0, zTop, zTop + 4.5);
      ebox(lou, ed, 0, ed.len, -0.3, 0.02, zTop + 4.4, zTop + 4.6);
    }
    kit.cap(batch, roofM, [[rect(L - 2 * 3.3 + 0.4, W - 2 * 3.3 + 0.4)]], zTop + 0.01);
    for (const ed of edgesOf(rect(L - 2 * 3.3 - 1.5, W - 2 * 3.3 - 1.5)))
      ebox(steel, ed, 0, ed.len, -0.1, 0.1, zTop + 0.01, zTop + 0.25);
    g.add(batch.toGroup('eighty_eight_wood_lane'));
    return g;
  },
};
