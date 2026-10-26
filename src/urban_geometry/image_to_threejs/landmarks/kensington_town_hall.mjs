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
      title: 'Kensington Town Hall - Manchester History (Spence)',
      url: 'https://manchesterhistory.net/architecture/1970/kensingtontownhall.html',
      used_for:
        'civic suite on the south side facing the Library; blind brick great hall (west) and council chamber raised to first floor (east), both with canted corners; pool beneath the chamber later a garden',
    },
    {
      title: 'Kensington Town Hall - C20 Society',
      url: 'https://c20society.org.uk/?p=7704',
      used_for: 'general description of the brick civic centre',
    },
    {
      title: '1977 - Kensington and Chelsea Town Hall - Archiseek',
      url: 'https://www.archiseek.com/1977-kensington-and-chelsea-town-hall-london/',
      used_for: 'general appearance and date',
    },
  ],
  notes:
    'Terracing applied to every outer face of the main block (sources only describe it for Hornton Street); ' +
    'storey heights (3.5 m) and the 5-level section to ~17 m exceed the Overture 13.9 m. The two south lobes ' +
    'of the outline are taken as the blind great hall (west) and the council chamber raised on piers over a ' +
    'garden (east); the north-west lobe is modelled as a brick pavilion of unknown use. Window bands are ' +
    'recessed glazing with 3D mullions, sills and white concrete fascias; mullion spacing (1.5 m), the ' +
    'terrace handrails, the Hornton Street entrance canopy position and all pavilion heights are estimated.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const all = byId['eea6f92f-97c4-47b6-a227-7deb66a08c4e'];
    const main = byId['8f3feda0-c629-43c8-827b-f1972ffef70b'];
    const brickC = '#9b4f3c';
    const brickTex = kit.paintedMaterial(
      'kensington_town_hall:brick',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.1976);
        c.fillStyle = '#7d5246';
        c.fillRect(0, 0, w, h);
        // long thin 'Roman' format bricks to match the library
        for (let y = 0, row = 0; y < h; y += 3, row++)
          for (let x = row % 2 ? -8 : 0; x < w; x += 16) {
            const col = new THREE.Color(brickC).multiplyScalar(0.84 + r() * 0.26);
            c.fillStyle = '#' + col.getHexString();
            c.fillRect(x + 0.5, y + 0.5, 15, 2.2);
          }
      },
      { vertexColors: true, roughness: 0.95 },
    );
    const brick = kit.mat(brickC, { roughness: 0.95 });
    const conc = kit.mat('#e6e2d8', { roughness: 0.9 });
    const concD = kit.mat('#cfcac0', { roughness: 0.9 });
    const lead = kit.mat('#6f6f6c');
    const glassM = kit.mat('#34434d', { roughness: 0.15, metalness: 0.35 });
    const mull = kit.mat('#2a2d30', { roughness: 0.5, metalness: 0.4 });
    const green = kit.mat('#5d7a45');
    const shrub = kit.mat('dark_foliage');
    const steel = kit.mat('dark_steel');
    const paving = kit.mat('#b9b2a4');
    const ST = 3.5;
    const BRICK = { bay: 1, storey: 1.5 }; // 4 m x 3 m per texture tile

    // Projecting band on an outer (CCW) or courtyard (CW) ring, capped top and bottom.
    const band = (ring, z0, z1, d, m) => {
      const o = kit.offsetRing(ring, d);
      kit.walls(batch, m, [[o]], z0, z1, { bay: 1e6 });
      const poly =
        kit.ringArea(ring) > 0 ? [o, ring.slice().reverse()] : [ring.slice().reverse(), o];
      kit.cap(batch, m, [poly], z1);
      kit.cap(batch, m, [poly], z0, { down: true });
    };
    // One office storey on a ring: brick spandrel, recessed window band with mullions,
    // white concrete fascia projecting at the slab edge.
    const storey = (ring, z0, z1, { fascia = true } = {}) => {
      const zs = z0 + 1.05,
        zh = z1 - 0.5;
      kit.walls(batch, brickTex, [[ring]], z0, zs, { ...BRICK, color: [1, 1, 1] });
      const inset = kit.offsetRing(ring, -0.55);
      kit.walls(batch, glassM, [[inset]], zs, zh, { bay: 1e6 });
      // reveal: sill (top of spandrel) and head soffit
      const sillPoly =
        kit.ringArea(ring) > 0 ? [ring, inset.slice().reverse()] : [inset.slice().reverse(), ring];
      kit.cap(batch, concD, [sillPoly], zs);
      kit.cap(batch, concD, [sillPoly], zh, { down: true });
      // mullions every 1.5 m
      for (let k = 0; k < inset.length; k++) {
        const a = inset[k],
          b = inset[(k + 1) % inset.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const n = Math.max(1, Math.round(len / 1.5));
        const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        for (let i = 0; i < n; i++) {
          const t = i / n;
          kit.box(
            batch,
            mull,
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            zs,
            i % 4 === 0 ? 0.35 : 0.09,
            0.14,
            zh - zs,
            ang,
          );
        }
        kit.box(
          batch,
          mull,
          (a[0] + b[0]) / 2,
          (a[1] + b[1]) / 2,
          zs + (zh - zs) * 0.72,
          len,
          0.1,
          0.07,
          ang,
        );
      }
      if (fascia) band(ring, zh, z1, 0.25, conc);
    };

    // ---- main block: terraced levels around the courtyard -------------------------------
    const outer = main.polys[0][0];
    const holes = main.polys[0].slice(1);
    const levels = [
      [ST, 2 * ST, 0], // first floor on the full outline (cantilevered over the ground floor)
      [2 * ST, 3 * ST, -2.6],
      [3 * ST, 4 * ST, -5.2],
      [4 * ST, 5 * ST, -7.8],
    ];
    for (const [z0, z1, d] of levels) {
      const ring = d ? kit.offsetRing(outer, d) : outer;
      storey(ring, z0, z1);
      const nextD = d - 2.6;
      const top = kit.offsetRing(outer, nextD);
      const o = kit.offsetRing(ring, 0.25);
      if (z1 < 5 * ST) {
        kit.cap(batch, paving, [[o, top.slice().reverse()]], z1);
        // planter strip with shrubs along the terrace edge, and a steel handrail
        const pl = kit.offsetRing(ring, -0.3),
          pl2 = kit.offsetRing(ring, -1.2);
        kit.walls(batch, conc, [[pl]], z1, z1 + 0.6, { bay: 1e6 });
        kit.cap(batch, green, [[pl, pl2.slice().reverse()]], z1 + 0.6);
        const rr = kit.rng(z1 * 0.137);
        for (let k = 0; k < pl.length; k++) {
          const a = pl[k],
            b = pl[(k + 1) % pl.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          const n = Math.floor(len / 2.2);
          const ux = (b[0] - a[0]) / len,
            uy = (b[1] - a[1]) / len;
          for (let i = 0; i < n; i++) {
            const t = (i + 0.5) * (len / n);
            const sg = new THREE.IcosahedronGeometry(0.45 + rr() * 0.3, 0);
            batch.addGeometry(
              shrub,
              sg,
              new THREE.Matrix4().makeTranslation(
                a[0] + ux * t - uy * 0.45,
                a[1] + uy * t + ux * 0.45,
                z1 + 0.75,
              ),
            );
            sg.dispose();
          }
        }
        const rail = kit.offsetRing(ring, -1.4);
        for (let k = 0; k < rail.length; k++) {
          const a = rail[k],
            b = rail[(k + 1) % rail.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
          kit.box(
            batch,
            steel,
            (a[0] + b[0]) / 2,
            (a[1] + b[1]) / 2,
            z1 + 1.05,
            len,
            0.06,
            0.06,
            ang,
          );
          const n = Math.floor(len / 2);
          for (let i = 0; i <= n; i++) {
            const t = n ? i / n : 0;
            kit.box(
              batch,
              steel,
              a[0] + (b[0] - a[0]) * t,
              a[1] + (b[1] - a[1]) * t,
              z1,
              0.05,
              0.05,
              1.05,
              ang,
            );
          }
        }
      } else {
        kit.cap(batch, lead, [[o, ...holes.map((h) => kit.offsetRing(h, -0.25))]], z1);
      }
    }
    // courtyard elevations (full height), paving, pool and planting
    for (const h of holes) {
      for (let s = 1; s < 5; s++) storey(h, s * ST, (s + 1) * ST);
      storey(h, 0, ST, { fascia: true });
      kit.cap(batch, kit.mat('paving'), [[h.slice().reverse()]], 0.05);
      const inner = kit.offsetRing(h.slice().reverse(), -4);
      kit.cap(batch, kit.mat('water'), [[inner]], 0.12);
      kit.walls(batch, conc, [[inner]], 0, 0.45, { bay: 1e6 });
    }
    // ground floor recessed under the cantilever (glazed), soffit and brick piers
    {
      const gr = kit.offsetRing(outer, -1.5);
      kit.walls(batch, glassM, [[gr]], 0, ST - 0.3, { bay: 1e6 });
      kit.walls(batch, brickTex, [[gr]], ST - 0.3, ST, { ...BRICK, color: [1, 1, 1] });
      for (let k = 0; k < gr.length; k++) {
        const a = gr[k],
          b = gr[(k + 1) % gr.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const n = Math.max(1, Math.round(len / 1.8));
        const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        for (let i = 0; i < n; i++)
          kit.box(
            batch,
            mull,
            a[0] + ((b[0] - a[0]) * i) / n,
            a[1] + ((b[1] - a[1]) * i) / n,
            0,
            0.08,
            0.12,
            ST - 0.3,
            ang,
          );
      }
      kit.cap(batch, conc, [[outer, gr.slice().reverse()]], ST, { down: true });
    }
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
          ST,
          ang,
        );
      }
    }
    // Hornton Street entrance: concrete canopy on brick piers and glazed doors
    {
      let best = null;
      for (let k = 0; k < outer.length; k++) {
        const p = outer[k],
          q = outer[(k + 1) % outer.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        const mx = (p[0] + q[0]) / 2,
          my = (p[1] + q[1]) / 2;
        // Hornton Street lies to the north-east: maximise x + y
        if (len > 20 && (!best || mx + my > best.s)) best = { p, q, len, s: mx + my };
      }
      if (best) {
        const { p, q, len } = best;
        const ux = (q[0] - p[0]) / len,
          uy = (q[1] - p[1]) / len,
          ang = Math.atan2(uy, ux);
        const nx = uy,
          ny = -ux;
        const m = [p[0] + ux * len * 0.5, p[1] + uy * len * 0.5];
        const at = (s, d) => [m[0] + ux * s + nx * d, m[1] + uy * s + ny * d];
        let c = at(0, 2.2);
        kit.box(batch, conc, c[0], c[1], ST - 0.6, 12, 5.0, 0.5, ang);
        kit.box(batch, concD, c[0], c[1], ST - 0.7, 11.6, 4.6, 0.1, ang);
        for (const s of [-5.4, 5.4]) {
          c = at(s, 4.2);
          kit.box(batch, brick, c[0], c[1], 0, 0.7, 0.7, ST - 0.6, ang);
        }
        c = at(0, -1.45);
        kit.box(batch, kit.mat('#1b2328'), c[0], c[1], 0, 6, 0.1, 2.6, ang);
        c = at(0, 1.5);
        kit.cap(batch, paving, [[[at(-6, 0), at(6, 0), at(6, 6), at(-6, 6)]]], 0.03);
        const lettering = kit.paintedMaterial('kensington_town_hall:sign', 512, 64, (cx, w, h) => {
          cx.fillStyle = '#e6e2d8';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#2b2b2b';
          cx.font = 'bold 30px sans-serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('KENSINGTON TOWN HALL', w / 2, h / 2 + 2);
        });
        c = at(0, 4.72);
        const pl = new THREE.PlaneGeometry(9, 0.45).rotateX(Math.PI / 2).rotateZ(Math.PI);
        batch.addGeometry(
          lettering,
          pl,
          new THREE.Matrix4().makeRotationZ(ang).setPosition(c[0], c[1], ST - 0.35),
        );
        pl.dispose();
      }
    }

    // ---- pavilions from the complex outline: great hall, council chamber, NW pavilion -----
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
      { pts: slice([343.4, -443.2], [331.6, -450.3]), h: 16.5, z0: 0, kind: 'nw' },
      { pts: slice([367.3, -515.2], [378.0, -508.9]), h: 15.5, z0: 0, kind: 'hall' },
      { pts: slice([395.6, -498.2], [406.3, -491.8]), h: 16.5, z0: 4.5, kind: 'chamber' },
    ];
    for (const p of pav) {
      let r = p.pts;
      if (kit.ringArea(r) < 0) r = r.slice().reverse();
      const c = r.reduce((s, q) => [s[0] + q[0] / r.length, s[1] + q[1] / r.length], [0, 0]);
      // blind brick drum, white concrete crown and brick coping
      kit.walls(batch, brickTex, [[r]], p.z0, p.h - 1.2, { ...BRICK, color: [0.97, 0.97, 0.97] });
      kit.cornice(batch, conc, r, p.h - 1.2, { height: 1.2, projection: 0.2 });
      const rimIn = kit.offsetRing(r, -0.8);
      kit.walls(batch, conc, [[rimIn.slice().reverse()]], p.h - 0.6, p.h, { bay: 1e6 });
      kit.cap(batch, conc, [[kit.offsetRing(r, 0.2), rimIn.slice().reverse()]], p.h);
      kit.cap(batch, lead, [[rimIn]], p.h - 0.6);
      // brick string course (soldier band) at first-floor level
      kit.cornice(batch, brick, r, p.z0 + 4.4, { height: 0.35, projection: 0.06 });
      if (p.kind === 'chamber') {
        // raised on piers over the memorial garden: soffit, piers, planting
        kit.cap(batch, conc, [[r]], p.z0, { down: true });
        const inner = kit.offsetRing(r, -1.2);
        for (const q of inner)
          kit.box(batch, brickTex, q[0], q[1], 0, 1.1, 1.1, p.z0, 0, [0.95, 0.95, 0.95]);
        kit.cap(batch, green, [[kit.offsetRing(r, -2)]], 0.08);
        const rr = kit.rng(0.77);
        for (let k = 0; k < 14; k++) {
          const a = rr() * Math.PI * 2,
            d = rr() * 6;
          const sg = new THREE.IcosahedronGeometry(0.5 + rr() * 0.5, 0);
          batch.addGeometry(
            shrub,
            sg,
            new THREE.Matrix4().makeTranslation(
              c[0] + Math.cos(a) * d,
              c[1] + Math.sin(a) * d,
              0.5,
            ),
          );
          sg.dispose();
        }
        // glazed stair/lobby core up to the chamber
        kit.box(batch, glassM, c[0], c[1], 0, 4, 4, p.z0, 0);
      }
      if (p.kind === 'hall') {
        // clear-span roof: shallow faceted lead roof with a glazed lantern ring
        const roof = new THREE.ConeGeometry(9, 2.2, 8).rotateX(Math.PI / 2);
        batch.addGeometry(
          kit.mat('#8a8f92'),
          roof,
          new THREE.Matrix4().makeTranslation(c[0], c[1], p.h - 0.6 + 1.1),
        );
        roof.dispose();
      }
      if (p.kind === 'nw') {
        // narrow vertical slit windows
        for (let k = 0; k < r.length; k++) {
          const a = r[k],
            q = r[(k + 1) % r.length];
          const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
          if (len < 4) continue;
          const ang = Math.atan2(q[1] - a[1], q[0] - a[0]);
          const nx = (q[1] - a[1]) / len,
            ny = -(q[0] - a[0]) / len;
          const n = Math.max(1, Math.floor(len / 3.5));
          for (let i = 0; i < n; i++) {
            const t = (i + 0.5) / n;
            const x = a[0] + (q[0] - a[0]) * t + nx * 0.05,
              y = a[1] + (q[1] - a[1]) * t + ny * 0.05;
            kit.box(batch, glassM, x, y, 5, 0.9, 0.1, p.h - 8, ang);
            kit.box(batch, conc, x + nx * 0.05, y + ny * 0.05, 4.8, 1.2, 0.25, 0.2, ang);
          }
        }
      }
    }
    g.add(batch.toGroup('kensington_town_hall'));
    return g;
  },
};
