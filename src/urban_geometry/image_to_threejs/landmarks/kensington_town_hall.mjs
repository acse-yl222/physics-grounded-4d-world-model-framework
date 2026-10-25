// Kensington Town Hall, Hornton Street (Sir Basil Spence, completed 1976, opened
// 1977; Grade II*). Brutalist red-brick civic centre around a courtyard: the office
// ranges step back at each upper level (on the Hornton Street flank it is cantilevered
// over the pavement at first floor and then terraces back), deep-set horizontal window
// bands between brick spandrels, white textured concrete fascias, and polygonal brick
// pavilions (assembly hall and stair/service towers) attached to the main block.
export default {
  id: 'kensington_town_hall',
  name: 'Kensington Town Hall',
  claims: [
    'eea6f92f-97c4-47b6-a227-7deb66a08c4e', // whole complex incl. pavilions
    '8f3feda0-c629-43c8-827b-f1972ffef70b', // main block with courtyard (overlapping outline)
  ],
  references: [
    {
      title: 'Kensington Town Hall, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Kensington_Town_Hall,_London',
      used_for: 'Basil Spence, Brutalist, completed 1976, opened 1977, Hornton Street, Grade II*',
    },
    {
      title: 'Kensington and Chelsea Town Hall - Mainstream Modern',
      url: 'https://www.mainstreammodern.co.uk/case-study/kensington-and-chelsea-town-hall/',
      used_for:
        'red-brick civic centre around a courtyard; brickwork and white textured concrete echoing the library',
    },
    {
      title: 'Kensington Town Hall - Modernism in Metro-land',
      url: 'https://www.modernism-in-metroland.co.uk/kensington-town-hall.html',
      used_for:
        'Hornton Street flank cantilevered at first floor and stepping back at each higher level',
    },
    {
      title: '1977 - Kensington and Chelsea Town Hall - Archiseek',
      url: 'https://www.archiseek.com/1977-kensington-and-chelsea-town-hall-london/',
      used_for: 'general appearance and date',
    },
  ],
  notes:
    'Terracing applied to every outer face of the main block (sources only describe it for Hornton Street); ' +
    'storey heights (3.5 m) and the 5-level section to ~17 m exceed the Overture 13.9 m. Pavilions are taken ' +
    'from the polygonal lobes of the Overture outline; their use and exact heights are estimated.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const all = byId['eea6f92f-97c4-47b6-a227-7deb66a08c4e'];
    const main = byId['8f3feda0-c629-43c8-827b-f1972ffef70b'];
    const brickC = '#9b4f3c';
    const brick = kit.mat(brickC, { roughness: 0.95 });
    const conc = kit.mat('#e6e2d8', { roughness: 0.9 });
    const lead = kit.mat('#6f6f6c');
    const dark = kit.mat('dark_glass');
    const green = kit.mat('#5d7a45');
    const ST = 3.5;
    // Office elevation: brick spandrel, white concrete sill band, deep window band.
    const band = kit.paintedMaterial('kensington_town_hall:bands', 512, 256, (c, w, h) => {
      const r = kit.rng(0.1976);
      c.fillStyle = brickC;
      c.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
          const col = new THREE.Color(brickC).multiplyScalar(0.86 + r() * 0.25);
          c.fillStyle = '#' + col.getHexString();
          c.fillRect(x + 0.5, y + 0.5, 11, 3);
        }
      const fh = h / 2;
      for (let f = 0; f < 2; f++) {
        const y0 = f * fh;
        // window band in the upper 55 % of the storey (deep reveal = darker)
        c.fillStyle = '#1f262c';
        c.fillRect(0, y0 + fh * 0.08, w, fh * 0.5);
        c.fillStyle = '#3a4a56';
        c.fillRect(0, y0 + fh * 0.12, w, fh * 0.42);
        c.fillStyle = '#8c4434';
        for (let k = 0; k <= 8; k++) c.fillRect((k * w) / 8 - 5, y0 + fh * 0.08, 10, fh * 0.5);
        // white concrete sill / fascia
        c.fillStyle = '#e6e2d8';
        c.fillRect(0, y0 + fh * 0.58, w, fh * 0.08);
      }
    });

    // ---- main block: terraced levels around the courtyard -------------------------------
    const outer = main.polys[0][0];
    const holes = main.polys[0].slice(1);
    const levels = [
      [0, 2 * ST, 0], // ground + first floor on the full outline
      [2 * ST, 3 * ST, -2.6],
      [3 * ST, 4 * ST, -5.2],
      [4 * ST, 5 * ST, -7.8],
    ];
    for (const [z0, z1, d] of levels) {
      const ring = d ? kit.offsetRing(outer, d) : outer;
      kit.walls(batch, band, [[ring]], z0, z1, { bay: 3.0, storey: ST });
      // white concrete fascia at the level edge
      const o = kit.offsetRing(ring, 0.25);
      kit.walls(batch, conc, [[o]], z1 - 0.5, z1);
      // terrace floor between this level and the next (planted / paved)
      const nextD = d - 2.6;
      const top = kit.offsetRing(outer, nextD);
      if (z1 < 5 * ST) {
        kit.cap(batch, kit.mat('#b9b2a4'), [[o, top.slice().reverse()]], z1);
        // planter strip along the terrace edge
        const pl = kit.offsetRing(ring, -0.3),
          pl2 = kit.offsetRing(ring, -1.2);
        kit.walls(batch, conc, [[pl]], z1, z1 + 0.6);
        kit.cap(batch, green, [[pl, pl2.slice().reverse()]], z1 + 0.6);
      } else kit.cap(batch, lead, [[o, ...holes.map((h) => kit.offsetRing(h, -0.25))]], z1);
    }
    // courtyard walls full height
    for (const h of holes) {
      kit.walls(batch, band, [[h]], 0, 5 * ST, { bay: 3.0, storey: ST });
      kit.walls(batch, conc, [[kit.offsetRing(h, -0.25)]], 5 * ST - 0.5, 5 * ST);
      kit.cap(batch, kit.mat('paving'), [[h.slice().reverse()]], 0.05);
      // courtyard pool / planting
      const inner = kit.offsetRing(h.slice().reverse(), -4);
      kit.cap(batch, kit.mat('water'), [[inner]], 0.12);
    }
    // ground floor recessed under the cantilever (dark glazed band)
    kit.walls(batch, dark, [[kit.offsetRing(outer, -1.5)]], 0, 3.2);
    kit.cap(batch, conc, [[outer, kit.offsetRing(outer, -1.5).slice().reverse()]], 3.2, {
      down: true,
    });
    // brick piers under the cantilever
    for (let k = 0; k < outer.length; k++) {
      const p = outer[k],
        q = outer[(k + 1) % outer.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
      const nx = (q[1] - p[1]) / len,
        ny = -(q[0] - p[0]) / len;
      const n = Math.floor(len / 6);
      for (let i = 1; i < n; i++) {
        const t = i / n;
        kit.box(
          batch,
          brick,
          p[0] + (q[0] - p[0]) * t - nx * 0.9,
          p[1] + (q[1] - p[1]) * t - ny * 0.9,
          0,
          0.8,
          0.8,
          3.2,
          ang,
        );
      }
    }

    // ---- polygonal pavilions from the complex outline --------------------------------------
    const ring = all.polys[0][0];
    const idx = (x, y) => ring.findIndex((p) => Math.hypot(p[0] - x, p[1] - y) < 0.3);
    const slice = (a, b) => {
      const i0 = idx(...a),
        i1 = idx(...b);
      const out = [];
      for (let i = i0; ; i = (i + 1) % ring.length) {
        out.push(ring[i]);
        if (i === i1) break;
      }
      return out;
    };
    const pav = [
      { pts: slice([343.4, -443.2], [331.6, -450.3]), h: 16.5, hall: true }, // assembly hall lobe (NW)
      { pts: slice([367.3, -515.2], [378.0, -508.9]), h: 18.5 }, // south tower
      { pts: slice([395.6, -498.2], [406.3, -491.8]), h: 18.5 }, // south-east tower
    ];
    for (const p of pav) {
      let r = p.pts;
      if (kit.ringArea(r) < 0) r = r.slice().reverse();
      // brick drum with vertical slit windows, white concrete crown
      kit.walls(batch, brick, [[r]], 0, p.h - 1.2);
      kit.walls(batch, conc, [[kit.offsetRing(r, 0.2)]], p.h - 1.2, p.h);
      const rim = kit.offsetRing(r, 0.2),
        rimIn = kit.offsetRing(r, -0.8);
      kit.cap(batch, conc, [[rim, rimIn.slice().reverse()]], p.h);
      kit.walls(batch, conc, [[rimIn.slice().reverse()]], p.h - 0.6, p.h);
      kit.cap(batch, lead, [[rimIn]], p.h - 0.6);
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          q = r[(k + 1) % r.length];
        const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
        if (len < 4) continue;
        const ang = Math.atan2(q[1] - a[1], q[0] - a[0]);
        const nx = (q[1] - a[1]) / len,
          ny = -(q[0] - a[0]) / len;
        const n = p.hall ? Math.max(1, Math.floor(len / 3.5)) : 1;
        for (let i = 0; i < n; i++) {
          const t = (i + 0.5) / n;
          const x = a[0] + (q[0] - a[0]) * t + nx * 0.05,
            y = a[1] + (q[1] - a[1]) * t + ny * 0.05;
          kit.box(
            batch,
            dark,
            x,
            y,
            p.hall ? 5 : 3,
            p.hall ? 0.9 : 1.2,
            0.1,
            p.h - (p.hall ? 8 : 6),
            ang,
          );
        }
      }
      if (p.hall) {
        // shallow hipped roof light over the hall
        const c = r.reduce((s, q) => [s[0] + q[0] / r.length, s[1] + q[1] / r.length], [0, 0]);
        const roof = new THREE.ConeGeometry(9, 2.5, 6).rotateX(Math.PI / 2);
        batch.addGeometry(
          kit.mat('#8a8f92'),
          roof,
          new THREE.Matrix4().setPosition(c[0], c[1], p.h - 0.6 + 1.25),
        );
        roof.dispose();
      }
    }
    g.add(batch.toGroup('kensington_town_hall'));
    return g;
  },
};
