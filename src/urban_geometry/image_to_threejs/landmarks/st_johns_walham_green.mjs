// St John's Church, Walham Green (North End Road / Fulham Broadway), 1827-28 by
// J. H. (George Ledwell) Taylor; altered by E. P. Warren 1893; Grade II. A Commissioners'
// church in Early English Gothic: yellow stock brick with stone dressings, a broad
// gabled body with tall lancets between buttresses, a lower chancel and a pinnacled
// west tower on axis facing Fulham Broadway.
export default {
  id: 'st_johns_walham_green',
  name: "St John's, Walham Green",
  claims: ['016a4a5a-06ba-4b83-9598-a6ce4e287f58'],
  references: [
    {
      title: 'Church of St John - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101079751-church-of-st-john-fulham-broadway-ward',
      used_for:
        'Grade II, Early English Gothic, yellow brick with stone dressings, tower on axis at the west end, 1893 alterations by E P Warren',
    },
    {
      title: 'St John North End Road Walham Green - London Church Buildings',
      url: 'https://londonchurchbuildings.com/2018/01/21/st-john-north-end-road-walham-green/',
      used_for: 'J.H. Taylor, 1827-28',
    },
    {
      title: 'Walham Green - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Walham_Green',
      used_for: 'built on the site of the village pond',
    },
  ],
  notes:
    'Body, chancel and tower fitted to the Overture footprint; heights are estimates (eave 10.5 m, ridge 15 m, ' +
    'tower 28 m to the parapet plus 3.5 m pinnacles). Lancet count, buttress rhythm and the tower openings are ' +
    'typical of the type rather than surveyed; no galleries or interior modelled.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ang = (39.95 * Math.PI) / 180,
      CX = 118.64,
      CY = -2815.22;
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
          const rows = 44;
          for (let i = 0; i < rows; i++) {
            const y0 = (i * h) / rows;
            let x = -r() * 30;
            while (x < w) {
              const bw = 20;
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
    const rag = stoneTex('st_john_walham:stock', [196, 170, 118], '#b6a88c', 0.13);
    const ashlar = kit.mat('#d6ccb4', { roughness: 0.8 });
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

    // u > 0 towards the (north-east) chancel; the tower is at u < 0 facing the Broadway
    const EAVE = 10.5,
      RISE = 4.5;
    block(-13.3, 13.65, -9.6, 9.6, EAVE, RISE); // broad body
    block(13.65, 17.4, -8.5, 4.7, 7.0, 3.0); // chancel / vestry
    for (const v of [-9.6, 9.6])
      lancets(-12.3, 12.6, v, 2.4, { width: 1.3, height: 6.2, count: 6, bars: 1 });
    lancetsU(17.4, -6.5, 3.0, 2.5, { width: 1.1, height: 3.6, count: 3 });
    for (const v of [-10.0, 10.0])
      for (let k = 0; k <= 6; k++) {
        const u = -13.0 + (k * 26.4) / 6;
        const p = L(u, v);
        kit.box(batch, rag, p[0], p[1], 0, 0.8, 0.8, EAVE + 0.8, ang);
        const pin = new THREE.CylinderGeometry(0, 0.45, 1.6, 4).rotateX(Math.PI / 2);
        geo(ashlar, pin, p[0], p[1], EAVE + 0.8 + 0.8, ang + Math.PI / 4);
      }
    // ---- west tower ------------------------------------------------------------------
    {
      const u0 = -17.5,
        u1 = -13.3,
        TH = 28;
      const t = rect(u0, u1 + 0.5, -2.5, 2.5);
      kit.walls(batch, rag, [[t]], 0, TH, wopt);
      kit.cap(batch, slate, [[t]], TH);
      // clasping buttresses stepped to the footprint (u -15.5..-13.3, v +-4.9)
      for (const sv of [-1, 1]) {
        const b = rect(-15.5, -13.3, sv < 0 ? -4.9 : 2.5, sv < 0 ? -2.5 : 4.9);
        kit.walls(batch, rag, [[b]], 0, 9, wopt);
        kit.pitchedRoof(batch, slate, rag, b, ang + Math.PI / 2, 9, 1.0, 'gabled', {
          overhang: 0.05,
        });
      }
      for (const z of [9, 18.5])
        kit.cornice(batch, ashlar, t, z, { height: 0.35, projection: 0.15 });
      // parapet with corner pinnacles
      kit.cornice(batch, ashlar, t, TH - 1.1, { height: 1.1, projection: 0.2 });
      for (const [su, sv] of [
        [0, -1],
        [1, -1],
        [1, 1],
        [0, 1],
      ]) {
        const p = L(su ? u1 + 0.3 : u0 - 0.1, sv * 2.65);
        kit.box(batch, ashlar, p[0], p[1], TH - 1.0, 0.7, 0.7, 1.6, ang);
        const pin = new THREE.CylinderGeometry(0, 0.4, 2.4, 8).rotateX(Math.PI / 2);
        geo(ashlar, pin, p[0], p[1], TH + 0.6 + 1.2, ang);
      }
      // west door and window, belfry lancets
      const d = L(u0 - 0.05, 0);
      kit.box(batch, kit.mat('#3b2a1f'), d[0], d[1], 0, 0.1, 1.6, 3.4, ang);
      lancetsU(u0, -2.5, 2.5, 5.5, { width: 1.1, height: 4.0, count: 1 });
      for (let k = 0; k < 4; k++)
        kit.windowRow(batch, t[k], t[(k + 1) % 4], 20, {
          glass: kit.mat('#2a2622'),
          frame: ashlar,
          head: 'arch',
          count: 2,
          width: 0.7,
          height: 3.6,
          bars: 3,
          margin: 0.8,
        });
      // clock face on the west side
      const cf = L(u0 - 0.08, 0);
      const disc = new THREE.CylinderGeometry(0.9, 0.9, 0.08, 20);
      geo(kit.mat('#1d2a33'), disc, cf[0], cf[1], 15.5, ang + Math.PI / 2);
    }

    g.add(batch.toGroup('st_johns_walham_green'));
    return g;
  },
};
