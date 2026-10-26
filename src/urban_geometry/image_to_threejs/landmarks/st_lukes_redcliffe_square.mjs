// St Luke's Church, Redcliffe Square / Redcliffe Gardens, West Brompton (George and
// Henry Godwin, 1872-73; Grade II). Aisled Gothic church of rock-faced snecked Kentish
// ragstone with Bath/Ham Hill ashlar dressings, slate roofs, an apsidal east end
// towards Redcliffe Gardens, an octagonal baptistery and a north-west tower with a
// tall broach spire that marks Redcliffe Square.
export default {
  id: 'st_lukes_redcliffe_square',
  name: "St Luke's, Redcliffe Square",
  claims: ['03972549-1bd0-452b-9098-f077585625ff'],
  references: [
    {
      title: "St Luke's Church, Redcliffe Gardens - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Luke%27s_Church,_Redcliffe_Gardens',
      used_for:
        'George and Henry Godwin, 1872-73, Grade II, Pevsner: grandest of the Godwins’ Kensington churches',
    },
    {
      title: 'Listed Buildings Search - RBKC',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=491328',
      used_for:
        'rock-faced snecked Kentish ragstone, ashlar dressings, slate roofs with terracotta cresting, octagonal baptistery roof',
    },
    {
      title: "Plate 96: St. Luke's Church, Redcliffe Square, exteriors - Survey of London",
      url: 'https://www.british-history.ac.uk/survey-london/vol41/plate-96',
      used_for: 'exterior views (titles only available): tower and spire, apse',
    },
  ],
  notes:
    'Plan zones (nave, aisles, chancel, apse, tower, baptistery) fitted to the Overture footprint; Overture h=8.7 m ' +
    'is too low. Eave/ridge heights (aisles 7 m, clerestory 14 m, ridge 21 m), tower position (north-west), baptistery position (south-east of the chancel), tower ' +
    'height 27 m and spire tip ~48 m are estimates; window counts and tracery are simplified to lancets and ' +
    'two-light windows with circular heads. Terracotta cresting omitted.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ang = (215.32 * Math.PI) / 180,
      CX = 770.04,
      CY = -2080.34;
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca];
    const rect = (u0, u1, v0, v1) => [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];

    const stoneTex = (key, base, joint, seed) =>
      kit.paintedMaterial(
        key,
        256,
        256,
        (c, w, h) => {
          const r = kit.rng(seed);
          c.fillStyle = joint;
          c.fillRect(0, 0, w, h);
          const rows = 14;
          for (let i = 0; i < rows; i++) {
            const y0 = (i * h) / rows;
            let x = -r() * 30;
            while (x < w) {
              const bw = 14 + r() * 26;
              const t = 0.85 + r() * 0.3;
              const col = base.map((v) => Math.min(255, Math.round(v * t)));
              c.fillStyle = `rgb(${col[0]},${col[1]},${col[2]})`;
              c.fillRect(x + 1, y0 + 1, bw - 2, h / rows - 2);
              x += bw;
            }
          }
        },
        { roughness: 0.92 },
      );
    const rag = stoneTex('st_lukes_rs:rag', [150, 146, 128], '#8c8676', 0.31);
    const ashlar = kit.mat('#cdbf9c', { roughness: 0.8 });
    const slate = kit.mat('#4f5459', { roughness: 0.75 });
    const glass = kit.mat('#2c3640', { roughness: 0.3, metalness: 0.2 });
    const wopt = { bay: 1, storey: 2 };

    const block = (u0, u1, v0, v1, eave, rise, axis = 'u', kind = 'gabled', z0 = 0) => {
      const r = rect(u0, u1, v0, v1);
      kit.walls(batch, rag, [[r]], z0, eave, wopt);
      kit.cornice(batch, ashlar, r, eave - 0.35, { height: 0.35, projection: 0.15 });
      kit.cornice(batch, ashlar, r, z0, { height: 0.6, projection: 0.12 });
      return kit.pitchedRoof(
        batch,
        slate,
        rag,
        r,
        axis === 'u' ? ang : ang + Math.PI / 2,
        eave,
        rise,
        kind,
        {
          overhang: 0.3,
          storey: 2,
        },
      );
    };
    const lancets = (ua, ub, v, z, opts) => {
      // wall edge along u at side v; outward normal must be on the right of a->b
      const a = v < 0 ? L(ua, v) : L(ub, v),
        b = v < 0 ? L(ub, v) : L(ua, v);
      kit.windowRow(batch, a, b, z, {
        glass,
        frame: ashlar,
        head: 'arch',
        bars: 1,
        depth: 0.18,
        ...opts,
      });
    };
    const lancetsU = (u, va, vb, z, opts) => {
      const a = u > 0 ? L(u, va) : L(u, vb),
        b = u > 0 ? L(u, vb) : L(u, va);
      kit.windowRow(batch, a, b, z, {
        glass,
        frame: ashlar,
        head: 'arch',
        bars: 1,
        depth: 0.18,
        ...opts,
      });
    };
    const geo = (m, gm, x, y, z, rz = 0) => {
      batch.addGeometry(m, gm, new THREE.Matrix4().makeRotationZ(rz).setPosition(x, y, z));
      gm.dispose();
    };

    // ---- nave with clerestory, aisles, chancel -------------------------------------
    const NU0 = -17.8,
      NU1 = 21.8;
    block(NU0, NU1, -4.6, 5.2, 14, 7); // nave
    block(NU0 + 0.4, NU1, -11.0, -4.6, 7.5, 1.8); // south-east aisle (gabled low roof)
    block(NU0 + 0.4, 13.8, 5.2, 11.0, 7.5, 1.8); // north-west aisle
    block(-12.4, -3.9, -13.2, -10.6, 6, 3, 'v'); // side chapel / porch (SE)
    block(-10.0, -5.7, 11.0, 13.3, 6, 2.5, 'v'); // porch (NW)
    // clerestory: paired two-light windows
    for (const v of [-4.6, 5.2])
      lancets(NU0 + 3, NU1 - 2, v, 10.2, { width: 1.0, height: 2.8, count: 7 });
    // aisle windows
    lancets(NU0 + 1, NU1 - 1, -11.0, 2.0, { width: 1.3, height: 3.4, count: 7 });
    lancets(NU0 + 1, 13.0, 11.0, 2.0, { width: 1.3, height: 3.4, count: 6 });
    // west front (SW): big traceried window over a gabled doorway
    lancetsU(NU1, -4.6, 5.2, 6.5, { width: 3.4, height: 6.5, count: 1, bars: 3 });
    lancetsU(NU1, -11.0, -4.6, 2.2, { width: 1.4, height: 3.2, count: 1 });
    {
      const r = rect(NU1, NU1 + 1.4, -1.4, 2.0);
      kit.walls(batch, ashlar, [[r]], 0, 4.2, wopt);
      kit.pitchedRoof(batch, ashlar, ashlar, r, ang + Math.PI / 2, 4.2, 1.6, 'gabled', {
        overhang: 0.1,
      });
      const d = L(NU1 + 1.42, 0.3);
      kit.box(batch, kit.mat('#3b2a1f'), d[0], d[1], 0, 1.6, 0.05, 3.2, ang + Math.PI / 2);
    }
    // apse (NE, towards Redcliffe Gardens): polygonal, same height as the chancel
    {
      const n = 7,
        r0 = 4.9,
        cu = NU0,
        cv = 0.3;
      const pts = [];
      for (let k = 0; k <= n; k++) {
        const t = Math.PI / 2 + (k / n) * Math.PI; // half polygon towards -u
        pts.push(L(cu + Math.cos(t) * r0 * 1.0, cv + Math.sin(t) * r0));
      }
      const ring = pts.slice().reverse();
      const rr = kit.ringArea(ring) < 0 ? ring.reverse() : ring;
      kit.walls(batch, rag, [[rr]], 0, 13, wopt);
      kit.cornice(batch, ashlar, rr, 12.65, { height: 0.35, projection: 0.15 });
      // conical half-roof
      const apex = L(cu, cv);
      for (let k = 0; k < n; k++) {
        const p = pts[k],
          q = pts[k + 1];
        batch.add(
          slate,
          [
            [p[0], p[1], 13],
            [q[0], q[1], 13],
            [apex[0], apex[1], 19],
          ],
          [
            [0, 0],
            [1, 0],
            [0.5, 1],
          ],
          [0, 1, 2],
        );
      }
      for (let k = 0; k < n; k++) {
        const t = Math.PI / 2 + ((k + 0.5) / n) * Math.PI;
        const p0 = L(cu + Math.cos(t) * (r0 + 0.12), cv + Math.sin(t) * (r0 + 0.12));
        kit.box(batch, glass, p0[0], p0[1], 5.5, 1.1, 0.06, 4.8, ang + t + Math.PI / 2);
        // buttress between windows
        const tb = Math.PI / 2 + (k / n) * Math.PI;
        const pb = L(cu + Math.cos(tb) * (r0 + 0.4), cv + Math.sin(tb) * (r0 + 0.4));
        kit.box(batch, rag, pb[0], pb[1], 0, 0.7, 0.8, 10, ang + tb);
      }
    }
    // buttresses along the aisles
    for (let u = NU0 + 2.5; u < 13; u += 5.2)
      for (const v of [-11.4, 11.4]) {
        const p = L(u, v);
        kit.box(batch, rag, p[0], p[1], 0, 0.8, 0.9, 6.2, ang);
      }

    // ---- octagonal baptistery by the chancel (SE side) ------------------------------
    {
      const c = L(-15.2, -9.4);
      const oct = new THREE.CylinderGeometry(2.6, 2.6, 6.5, 8).rotateX(Math.PI / 2);
      geo(rag, oct, c[0], c[1], 3.25, Math.PI / 8);
      const cone = new THREE.CylinderGeometry(0, 3.0, 3.6, 8).rotateX(Math.PI / 2);
      geo(slate, cone, c[0], c[1], 6.5 + 1.9, Math.PI / 8);
    }

    // ---- north-west tower and broach spire ---------------------------------------------
    {
      const tu = 17.3,
        tv = 9.7,
        TS = 6.6,
        TH = 27;
      const t = rect(tu - TS / 2, tu + TS / 2, tv - TS / 2, tv + TS / 2);
      kit.walls(batch, rag, [[t]], 0, TH, wopt);
      kit.cap(batch, slate, [[t]], TH);
      for (const z of [7, 15, TH - 0.5])
        kit.cornice(batch, ashlar, t, z, { height: 0.4, projection: 0.15 });
      // angle buttresses stepping in
      for (const [su, sv] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ]) {
        const p = L(tu + su * (TS / 2 + 0.3), tv + sv * (TS / 2 + 0.3));
        kit.box(batch, rag, p[0], p[1], 0, 1.0, 1.0, TH - 6, ang);
        kit.box(batch, ashlar, p[0], p[1], TH - 6, 0.8, 0.8, 4.5, ang);
      }
      // belfry: paired louvred openings on each face; lower lancets
      for (let k = 0; k < 4; k++) {
        const e = [t[k], t[(k + 1) % 4]];
        kit.windowRow(batch, e[0], e[1], TH - 6.5, {
          glass: kit.mat('#2a2622'),
          frame: ashlar,
          head: 'arch',
          count: 2,
          width: 1.0,
          height: 4.0,
          bars: 3,
          margin: 1.2,
        });
        kit.windowRow(batch, e[0], e[1], 9.5, {
          glass,
          frame: ashlar,
          head: 'arch',
          count: 1,
          width: 0.8,
          height: 3,
        });
      }
      // octagonal broach spire
      const c = L(tu, tv),
        SH = 21;
      const sp = new THREE.CylinderGeometry(0.15, TS / 2 / Math.cos(Math.PI / 8), SH, 8).rotateX(
        Math.PI / 2,
      );
      geo(slate, sp, c[0], c[1], TH + SH / 2, ang + Math.PI / 8);
      // broaches over the corners
      for (const [su, sv] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ]) {
        const p = L(tu + su * (TS / 2 - 0.9), tv + sv * (TS / 2 - 0.9));
        const b = new THREE.CylinderGeometry(0, 1.3, 3.5, 4).rotateX(Math.PI / 2);
        geo(slate, b, p[0], p[1], TH + 1.75, ang + Math.PI / 4);
      }
      // spire lucarnes
      for (let k = 0; k < 4; k++) {
        const a = ang + (k * Math.PI) / 2;
        const p = [c[0] + Math.cos(a) * 2.6, c[1] + Math.sin(a) * 2.6];
        kit.box(batch, ashlar, p[0], p[1], TH + 3.5, 1.1, 0.5, 2.2, a + Math.PI / 2);
      }
      // finial cross
      kit.box(batch, kit.mat('gold'), c[0], c[1], TH + SH, 0.12, 0.12, 2.2, ang);
      kit.box(batch, kit.mat('gold'), c[0], c[1], TH + SH + 1.4, 1.0, 0.12, 0.12, ang);
    }
    // gable crosses
    for (const u of [NU1 + 0.3]) {
      const p = L(u, 0.3);
      kit.box(batch, ashlar, p[0], p[1], 21, 0.2, 0.2, 1.6, ang);
      kit.box(batch, ashlar, p[0], p[1], 21.9, 0.2, 1.0, 0.2, ang);
    }

    g.add(batch.toGroup('st_lukes_redcliffe_square'));
    return g;
  },
};
