// St Cuthbert with St Matthias, Philbeach Gardens, Earl's Court (Hugh Roumieu Gough,
// 1884-87; Grade II*). Austere late-12th-century Gothic in red brick with Bath stone
// dressings: sheer brick walls with plain lancets in the aisles, paired two-light
// Geometric windows in a very tall clerestory, a great east window, no tower - a
// slender flèche on the ridge instead.
export default {
  id: 'st_cuthberts_philbeach_gardens',
  name: "St Cuthbert's, Philbeach Gardens",
  claims: ['08d0a32e-3083-4266-97a6-09615874afc9'],
  references: [
    {
      title: "St Cuthbert's, Earls Court - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/St_Cuthbert%27s,_Earls_Court',
      used_for: 'Hugh Roumieu Gough, 1884-87; no tower intended, a slender flèche instead',
    },
    {
      title: 'Church of St Cuthbert and St Matthias - Historic England',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1266119',
      used_for:
        'red brick with Bath stone dressings, austere late-C12 Gothic, plain aisle lancets, paired two-light Geometric clerestory windows',
    },
    {
      title: 'St Cuthbert - National Churches Trust',
      url: 'https://www.nationalchurchestrust.org/church/st-cuthbert-earls-court',
      used_for: 'roof history (copper after war damage; later reslated)',
    },
    {
      title: "1887 - St. Cuthbert's Church, Kensington - Archiseek",
      url: 'https://www.archiseek.com/?p=569390',
      used_for: 'red and black brick',
    },
  ],
  notes:
    'Overture h=11 m is far too low; nave eave 17 m, ridge 25 m, aisle eave 7 m and flèche top ~39 m are ' +
    'estimates for the tall clerestoried church. Aisle widths, bay count (7) and the position of the flèche ' +
    '(at the chancel arch) are assumed; west porch and south chapel fitted to footprint bumps. Slate roof per ' +
    'the listing (c.2000 reslating).',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ang = (-172.78 * Math.PI) / 180,
      CX = -3.03,
      CY = -1693.35;
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    // u: towards the west end (u>0); v>0 is the south side
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca];
    const rect = (u0, u1, v0, v1) => [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];
    const brick = kit.paintedMaterial(
      'st_cuthberts:brick',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.771);
        c.fillStyle = '#b9ab97';
        c.fillRect(0, 0, w, h);
        const rows = 48,
          bw = 21;
        for (let i = 0; i < rows; i++) {
          const y0 = (i * h) / rows;
          for (let x = -(i % 2) * (bw / 2); x < w; x += bw) {
            const t = 0.82 + r() * 0.3;
            const dark = r() < 0.08 ? 0.55 : 1;
            c.fillStyle = `rgb(${Math.round(150 * t * dark)},${Math.round(62 * t * dark)},${Math.round(48 * t * dark)})`;
            c.fillRect(x + 0.6, y0 + 0.6, bw - 1.2, h / rows - 1.2);
          }
        }
      },
      { roughness: 0.9 },
    );
    const bath = kit.mat('#d8c9a3', { roughness: 0.8 });
    const slate = kit.mat('#56605c', { roughness: 0.75 });
    const glass = kit.mat('#2a333b', { roughness: 0.3, metalness: 0.2 });
    const lead = kit.mat('lead');
    const wopt = { bay: 1, storey: 2 };

    const block = (u0, u1, v0, v1, eave, rise, axis = 'u', kind = 'gabled', z0 = 0) => {
      const r = rect(u0, u1, v0, v1);
      kit.walls(batch, brick, [[r]], z0, eave, wopt);
      kit.cornice(batch, bath, r, eave - 0.3, { height: 0.3, projection: 0.12 });
      kit.cornice(batch, bath, r, z0, { height: 0.5, projection: 0.1 });
      return kit.pitchedRoof(
        batch,
        slate,
        brick,
        r,
        axis === 'u' ? ang : ang + Math.PI / 2,
        eave,
        rise,
        kind,
        {
          overhang: 0.25,
          storey: 2,
        },
      );
    };
    const win = (a, b, z, opts) =>
      kit.windowRow(batch, a, b, z, {
        glass,
        frame: bath,
        head: 'arch',
        bars: 1,
        depth: 0.2,
        ...opts,
      });
    const alongU = (ua, ub, v, z, opts) =>
      v < 0 ? win(L(ua, v), L(ub, v), z, opts) : win(L(ub, v), L(ua, v), z, opts);
    const alongV = (u, va, vb, z, opts) =>
      u > 0 ? win(L(u, va), L(u, vb), z, opts) : win(L(u, vb), L(u, va), z, opts);
    const geo = (m, gm, x, y, z, rz = 0) => {
      batch.addGeometry(m, gm, new THREE.Matrix4().makeRotationZ(rz).setPosition(x, y, z));
      gm.dispose();
    };

    const U0 = -20.6,
      U1 = 20.6,
      NV0 = -4.6,
      NV1 = 4.6;
    const EAVE = 17,
      RISE = 8;
    block(U0, U1, NV0, NV1, EAVE, RISE); // nave + chancel under one ridge
    block(U0 + 0.2, U1 - 0.4, -10.3, NV0, 7, 2.0); // north aisle
    block(U0 + 2.0, U1 - 0.8, NV1, 8.7, 7, 1.6); // south aisle
    block(-18.6, -7.8, 8.7, 10.2, 5.2, 1.2); // south chapel / vestries
    block(19.6, 20.6, 5.3, 8.7, 4.5, 1.0, 'v'); // west porch
    // clerestory: paired two-light Geometric windows per bay
    for (const v of [NV0, NV1])
      alongU(U0 + 2, U1 - 2, v, 9.5, { count: 14, width: 1.1, height: 5.2, margin: 0.4 });
    // aisle lancets
    alongU(U0 + 1, U1 - 1.5, -10.3, 2.2, { count: 8, width: 0.9, height: 3.4 });
    alongU(-7.5, U1 - 2, 8.7, 2.2, { count: 5, width: 0.9, height: 3.4 });
    // great east window (towards Philbeach Gardens) and west window
    alongV(U0, NV0 + 0.8, NV1 - 0.8, 6.0, { count: 1, width: 5.2, height: 9.0, bars: 4 });
    alongV(U1, NV0 + 0.8, NV1 - 0.8, 7.5, {
      count: 3,
      width: 1.4,
      height: 6.5,
      bars: 1,
      margin: 0.6,
    });
    // stepped brick buttresses on the aisle walls and the clerestory
    for (let k = 0; k <= 7; k++) {
      const u = U0 + 0.5 + (k * (U1 - U0 - 1)) / 7;
      for (const v of [-10.75, 9.1]) {
        if (v > 0 && u < -7.5) continue;
        const p = L(u, v);
        kit.box(batch, brick, p[0], p[1], 0, 0.7, 0.9, 5.5, ang);
        kit.box(batch, bath, p[0], p[1], 5.5, 0.72, 0.6, 0.25, ang);
      }
      for (const v of [NV0 - 0.35, NV1 + 0.35]) {
        const p = L(u, v);
        kit.box(batch, brick, p[0], p[1], 7, 0.6, 0.7, EAVE - 7.4, ang);
      }
    }
    // gable crosses
    for (const u of [U0 - 0.1, U1 + 0.1]) {
      const p = L(u, 0);
      kit.box(batch, bath, p[0], p[1], EAVE + RISE, 0.25, 0.25, 1.8, ang);
      kit.box(batch, bath, p[0], p[1], EAVE + RISE + 1.0, 0.25, 1.1, 0.25, ang);
    }
    // slender flèche on the ridge at the chancel arch: lead-clad octagonal lantern + needle
    {
      const c = L(-9.5, 0),
        zb = EAVE + RISE - 1.0;
      const base = new THREE.CylinderGeometry(1.2, 1.3, 3.2, 8).rotateX(Math.PI / 2);
      geo(lead, base, c[0], c[1], zb + 1.6, ang);
      for (let k = 0; k < 8; k++) {
        const a = ang + (k * Math.PI) / 4 + Math.PI / 8;
        kit.box(
          batch,
          kit.mat('#2a2a2a'),
          c[0] + Math.cos(a) * 1.22,
          c[1] + Math.sin(a) * 1.22,
          zb + 0.9,
          0.45,
          0.05,
          1.8,
          a + Math.PI / 2,
        );
      }
      const needle = new THREE.CylinderGeometry(0.03, 1.25, 10.5, 8).rotateX(Math.PI / 2);
      geo(lead, needle, c[0], c[1], zb + 3.2 + 5.25, ang);
      kit.box(batch, kit.mat('gold'), c[0], c[1], zb + 13.7, 0.08, 0.08, 1.2, ang);
    }

    g.add(batch.toGroup('st_cuthberts_philbeach_gardens'));
    return g;
  },
};
