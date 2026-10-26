// Belgrave Square terraces, Belgravia (George Basevi for the Haldimand brothers, c.1825,
// built 1825-41). The four Grade I "grand terraces" facing the square: stucco
// Graeco-Roman palace-fronts of three storeys over basement with attics, giant (fluted)
// Corinthian columns through the first and second floors on the slightly projecting
// centre and end houses, porches, first-floor balconies and low slate mansards. The
// detached corner mansions are not part of this module.
const TERRACES = {
  nw: [
    'c26a3463-787e-4a43-9df9-0a924633958f',
    'f792fffb-3bb1-4aef-b083-76e56c946ccf',
    'fbb4af06-0396-4dbf-a7f1-197983d102a1',
    'd9fd6e9f-5411-4e2f-b435-375775ed5c88',
    'f33590c5-f3a0-45b4-89a3-13b4d71399e6',
    'a2ec0aa1-cc57-4c36-b0b1-cfbf3aa75a1b',
    'c1465d3a-8230-4fa2-97e6-006bc4716df6',
    '5544e22e-8131-46d7-90a5-7224249f8000',
    'b7ee817d-d05a-4db5-a17f-3afdd0556021',
    'eb0686b9-8941-4e04-b7f5-c060204cca63',
    '21063d87-d37f-4956-ba49-ef0c92b8a6a8',
    'e3b86330-eee6-4170-8b90-919e730572ba',
    'd988e48f-1e8b-4cbe-88a3-742194d19b86',
    'a7fb382b-83cd-4889-9b7e-a6439f684831',
    '8b0e5fb9-acbf-4f45-9814-1fc7279df2f2',
    'be39afb3-6408-4c49-bd03-5982dc516427',
    'dc7fc063-e040-4590-a38c-fdb162013a4c',
    '4c3b374e-94a4-46f9-9773-f9c5f5770047',
    '8b3add80-0fa0-4854-a851-1d67f869ad5c',
    '8d05c4b5-2490-4359-ba7c-a2193c121607',
    'f11fa731-0ed2-4727-972c-846a783d253a',
    '4b7d90e6-80e3-4e43-91c5-903061832676',
    '3df23af8-de38-4954-8e6d-cc02c365eb3c',
    '6e09fb55-1bdc-4e77-8574-89c4397a772f',
    '273cd657-4699-4a00-9325-0321e26db030',
  ],
  ne: [
    '60e6f2fe-49d6-4579-bee1-c68a96eb9f7f',
    '952d03e1-f59e-4160-8cef-40a0c1d41203',
    'c38b0705-7f3c-4a55-b766-e3db34bde817',
    'de290b4c-ec83-40e6-8274-b35460ad0892',
    '9ff27c62-a90a-4b12-9463-90a56ed3f27b',
    'e6761123-dc8a-4620-afd9-02f9a5a9c9cf',
    '9f037e8c-7a0e-4da3-82c9-ec0f725b55da',
    'e9f04c78-9067-462c-be84-57849c304f95',
    '45310088-ea95-4cb2-b1a7-84249832cbe4',
    '20b3a787-c5ab-4071-85cb-14211f84afc3',
    'ddfa05f2-7c06-4ab4-bef5-736187f84d7a',
    '8f028c24-75ba-4256-a0e3-9cfa133da38d',
    '3679e4fb-1c90-445e-a1e0-36487602cfbb',
    '98dbba26-cf33-48b8-9b64-f101bb57723e',
    'd593cb33-7d5e-4961-a96d-56b2398822c0',
    'd507ab96-6b8d-4eab-ae54-3551629b5e9c',
    'edc7d92d-23b1-422b-8e59-662f9f23fb5c',
    'fbc77db0-2206-4da8-bf04-52d3fa63badd',
    '3a42db65-537c-4a28-863c-a59eeeeec309',
    '589a2fa0-3aca-4e75-ad6f-e8b9da8e5294',
    'bab7d4bb-4b4c-4ede-a572-94c53465a93d',
  ],
  se: [
    '9f7b094b-029f-41a3-9836-c14866cef4a3',
    '9098a84a-696e-4dbf-bf4d-e7135f4cfa09',
    'bd8f3f59-d8e4-460d-bbcd-2e00a348b9e7',
    'afe7bcd9-0d96-475d-8c42-bb86c1ac4618',
    '0c65ac81-6c1f-429c-86b2-4a07effab767',
    '535f02fb-bc58-4a7a-adc5-1ca2e7b02c86',
    'ebad4450-795b-4a98-94ca-fed772b133c5',
    '9faad181-f0db-4999-b96b-73a169ca5557',
    '0fc9da3b-32ae-47f2-b58d-f4eb158e17ed',
    'ce51929f-69ac-4748-90d3-8a05ae4de4cf',
    '9e1f4311-142f-498f-a663-379a9b23e7f9',
    'd8cb111d-4087-42a8-a579-61538fce5072',
  ],
  sw: [
    '7a7d2ee6-c0a0-4b2a-a8d9-7c4deb57e31f',
    'ab5053dc-3ac1-4a2d-83a0-c23169c3652f',
    '8d7832c2-d8fd-4e4e-851e-2d5af4c9a69b',
    '12ae951f-ebd9-4845-b408-07d3765c2f0d',
    'df3639d6-e495-4e2f-8b90-ae0ad1ac6333',
    '17c6cc86-9dc9-4adf-bcbb-a803562993e6',
  ],
};
// Unit vectors from each terrace towards the centre of the square.
const S2 = Math.SQRT1_2;
const TOWARDS = { nw: [S2, -S2], ne: [-S2, -S2], se: [-S2, S2], sw: [S2, S2] };

export default {
  id: 'belgrave_square_terraces',
  name: 'Belgrave Square terraces',
  claims: [...TERRACES.nw, ...TERRACES.ne, ...TERRACES.se, ...TERRACES.sw],
  references: [
    {
      title: 'Belgrave Square - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Belgrave_Square',
      used_for: 'George Basevi for William and George Haldimand, building 1825-41',
    },
    {
      title: '1-11, Belgrave Square SW1 - Historic England list entry 1066455',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1066455',
      used_for:
        'Grade I grand terrace c.1825, stucco Graeco-Roman, three storeys over attic and basement, centre five bays and three-bay ends, giant Corinthian columns on first and second floors',
    },
    {
      title: '13-23, Belgrave Square SW1 - Historic England list entry 1066457',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1066457',
      used_for:
        'one of four grand terraces facing the square; low slate mansard roofs; projecting centre and end houses',
    },
    {
      title: '38-48 Belgrave Square - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101292022-38-48-belgrave-square-sw1-knightsbridge-and-belgravia-ward',
      used_for: 'fluted giant Corinthian columns, extra attic storey in some mansards',
    },
  ],
  notes:
    'Footprints grouped by position into the four terraces (front houses plus their rear wings; the ' +
    'detached corner villas, mews and rows behind are left generic). Front houses: cornice 15.4 m, parapet ' +
    'and slate mansard to ~18.8 m; rear wings use min(Overture h, 10 m). Pavilion zones (centre 24 % and ' +
    'ends 10 % of each terrace front) carry giant Corinthian columns; porches, balconies, window sizes, ' +
    'rustication and the rear facades are generic Belgravia details, not traced per house.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // ---- local helpers (modules have no imports) -----------------------------------
    const ccw = (r) => {
      const o = r.slice();
      if (kit.ringArea(o) < 0) o.reverse();
      return o;
    };
    const edges = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return {
          a,
          b,
          k,
          len,
          dx: dx / len,
          dy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
          mx: (a[0] + b[0]) / 2,
          my: (a[1] + b[1]) / 2,
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    // Box on edge e from s0..s1 along it, d0..d1 outward, z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
      const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, p[0], p[1], z0, Math.abs(s1 - s0), Math.abs(d1 - d0), z1 - z0, e.ang, c);
    };
    const prism = (m, ring, z0, z1, top = m) => {
      kit.walls(batch, m, [[ring]], z0, z1);
      if (top) kit.cap(batch, top, [[ring]], z1);
    };
    const wins = (e, s0, s1, z, o) => kit.windowRow(batch, at(e, s0), at(e, s1), z, o);
    const cyl = (m, x, y, z0, r0, r1, h, seg = 12) => {
      const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
      g.dispose();
    };
    const lathe = (m, prof, x, y, z, seg = 24) => {
      const g = new THREE.LatheGeometry(
        prof.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z));
      g.dispose();
    };
    // Rectangle ring (CCW) centred at (cx, cy), long axis at angle ang.
    const rect = (cx, cy, ang, L, W) => {
      const c = Math.cos(ang),
        s = Math.sin(ang);
      return [
        [-L / 2, -W / 2],
        [L / 2, -W / 2],
        [L / 2, W / 2],
        [-L / 2, W / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    // Triangular gable (pediment) standing on edge e between s0..s1, base z, rise, from d0..d1.
    const gable = (m, e, s0, s1, z, rise, d0 = 0, d1 = 0.4) => {
      const sh = new THREE.Shape();
      sh.moveTo(s0, 0);
      sh.lineTo(s1, 0);
      sh.lineTo((s0 + s1) / 2, rise);
      sh.closePath();
      const g = new THREE.ExtrudeGeometry(sh, { depth: d1 - d0, bevelEnabled: false });
      // shape x along edge, y up, extrude z outward -> map to world
      const m4 = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(e.dx, e.dy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(e.nx, e.ny, 0),
      );
      m4.setPosition(e.a[0] + e.nx * d0, e.a[1] + e.ny * d0, z);
      batch.addGeometry(m, g, m4);
      g.dispose();
    };
    // Facing test: cosine between an edge's outward normal and a direction (dx, dy).
    const facing = (e, dx, dy) => (e.nx * dx + e.ny * dy) / (Math.hypot(dx, dy) || 1);
    // Sloped band (mansard / hipped roof) from ring at z0 to the ring inset by `inset` at z1.
    // Returns the inner ring; capped with topMat unless topMat is null.
    const mansard = (m, ring, z0, inset, z1, topMat = m) => {
      const inner = kit.offsetRing(ring, -inset);
      for (let k = 0; k < ring.length; k++) {
        const j = (k + 1) % ring.length;
        const a = ring[k],
          b = ring[j],
          c = inner[j],
          d = inner[k];
        const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        batch.quad(
          m,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [d[0], d[1], z1],
          [0, 0],
          [l / 3, 0],
          [l / 3, 1],
          [0, 1],
        );
      }
      if (topMat) kit.cap(batch, topMat, [[inner]], z1);
      return inner;
    };
    // Rows of windows on edge e at each sill height in zs.
    const rows = (e, s0, s1, zs, o) => {
      for (const z of zs)
        kit.windowRow(batch, at(e, s0), at(e, s1), z, typeof o === 'function' ? o(z) : o);
    };
    // ---------------------------------------------------------------------------------
    const stucco = kit.mat('#efe8d8', { roughness: 0.75 });
    const stucco2 = kit.mat('#e4dcc8', { roughness: 0.8 });
    const rearM = kit.facade('stucco', 1);
    const slate = kit.mat('#545b63', { roughness: 0.75 });
    const lead = kit.mat('#868c8f', { roughness: 0.6 });
    const glass = kit.mat('#2c3842', { roughness: 0.15, metalness: 0.3 });
    const frame = kit.mat('#f7f6f1');
    const iron = kit.mat('#1f2224', { roughness: 0.5, metalness: 0.5 });
    const door = kit.mat('#1d2125', { roughness: 0.4 });
    const C = [3252, -790];
    const G1 = 4.4,
      F1 = 8.6,
      F2 = 12.2,
      CORN = 15.4;
    const byIdLocal = new Map(buildings.map((b) => [b.id, b]));
    for (const [t, ids] of Object.entries(TERRACES)) {
      const n = TOWARDS[t];
      const tan = [-n[1], n[0]];
      const recs = ids.map((id) => byIdLocal.get(id)).filter(Boolean);
      // frontmost line: edges facing the square
      const cand = [];
      for (const b of recs) {
        const ring = ccw(b.polys[0][0]);
        for (const e of edges(ring)) {
          if (e.len < 3 || facing(e, n[0], n[1]) < 0.9) continue;
          const d = -((e.mx - C[0]) * n[0] + (e.my - C[1]) * n[1]);
          cand.push({ b, e, d });
        }
      }
      const dmin = Math.min(...cand.map((c) => c.d));
      const fronts = cand.filter((c) => c.d < dmin + 3.5);
      const frontIds = new Set(fronts.map((c) => c.b.id));
      const tpos = (p) => (p[0] - C[0]) * tan[0] + (p[1] - C[1]) * tan[1];
      const ts = fronts.flatMap((c) => [tpos(c.e.a), tpos(c.e.b)]);
      const t0 = Math.min(...ts),
        t1 = Math.max(...ts),
        span = t1 - t0,
        tm = (t0 + t1) / 2;
      const zone = (s) =>
        Math.abs(s - tm) < 0.12 * span || s - t0 < 0.1 * span || t1 - s < 0.1 * span;

      for (const b of recs) {
        const ring = ccw(b.polys[0][0]);
        if (!frontIds.has(b.id)) {
          const h = Math.min(b.h, 10);
          kit.walls(batch, rearM, [[ring]], 0, h, { color: [0.97, 0.95, 0.9] });
          kit.cap(batch, lead, [[ring]], h);
          kit.cornice(batch, stucco2, ring, h - 0.4, { height: 0.4, projection: 0.15 });
          continue;
        }
        kit.walls(batch, stucco, [[ring]], 0, CORN + 1.0);
        kit.cornice(batch, stucco2, ring, G1 - 0.3, { height: 0.35, projection: 0.15 });
        kit.cornice(batch, stucco, ring, CORN - 0.5, { height: 0.7, projection: 0.6, steps: 2 });
        mansard(slate, kit.offsetRing(ring, -0.4), CORN + 0.8, 1.8, CORN + 3.4, lead);
      }
      for (const { e } of fronts) {
        const L = e.len;
        const nb = Math.max(2, Math.round(L / 3.5));
        const mid = tpos([e.mx, e.my]);
        const giant = zone(mid);
        // rusticated ground floor
        for (let z = 0.5; z < G1 - 0.5; z += 0.55) ebox(stucco2, e, 0, L, 0, 0.06, z, z + 0.44);
        wins(e, 0, L, 0.9, {
          count: nb,
          margin: 0.4,
          width: 1.2,
          height: 2.4,
          head: 'arch',
          frame,
          sill: stucco,
          glass,
          bars: 1,
          depth: 0.1,
        });
        // porch: two Doric columns and an entablature before the door (at the left end)
        {
          const s = 1.6;
          kit.colonnade(batch, stucco, at(e, s - 1.2, 1.8), at(e, s + 1.2, 1.8), 0.3, 3.5, {
            count: 2,
            radius: 0.24,
            capital: 'doric',
            segments: 8,
          });
          ebox(stucco, e, s - 1.6, s + 1.6, 0, 2.2, 3.8, 4.4);
          ebox(stucco2, e, s - 1.7, s + 1.7, 0, 2.4, 0, 0.3);
          ebox(door, e, s - 0.6, s + 0.6, 0, 0.06, 0.3, 3.2);
          // porch-top balustrade
          ebox(iron, e, s - 1.5, s + 1.5, 2.05, 2.15, 4.4, 5.3);
        }
        // first-floor balcony on consoles with iron railing
        ebox(stucco, e, 0.2, L - 0.2, 0, 0.9, G1 + 0.05, G1 + 0.3);
        ebox(iron, e, 0.2, L - 0.2, 0.82, 0.88, G1 + 0.3, G1 + 1.25);
        ebox(iron, e, 0.2, L - 0.2, 0.8, 0.9, G1 + 1.2, G1 + 1.3);
        const zc = giant ? 1.0 : 0.15;
        wins(e, 0, L, G1 + 0.4, {
          count: nb,
          margin: 0.4,
          width: 1.25,
          height: 3.0,
          head: 'pediment',
          frame,
          sill: stucco,
          glass,
          bars: 1,
          depth: 0.12,
          surround: 0.14,
          surroundMat: stucco2,
        });
        wins(e, 0, L, F1 + 0.6, {
          count: nb,
          margin: 0.4,
          width: 1.2,
          height: 2.3,
          head: 'lintel',
          frame,
          sill: stucco,
          glass,
          bars: 1,
          depth: 0.12,
          surround: 0.12,
          surroundMat: stucco2,
        });
        wins(e, 0, L, F2 + 0.7, {
          count: nb,
          margin: 0.4,
          width: 1.05,
          height: 1.6,
          head: 'none',
          frame,
          sill: stucco,
          glass,
          bars: 1,
          depth: 0.1,
        });
        // band over the first-floor windows
        ebox(stucco2, e, 0, L, 0, 0.18, F1 + 0.1, F1 + 0.35);
        if (giant) {
          // giant fluted Corinthian columns through first and second floors + entablature
          kit.colonnade(
            batch,
            stucco,
            at(e, 0.5, zc),
            at(e, L - 0.5, zc),
            G1 + 0.3,
            F2 - G1 - 0.3,
            { count: nb + 1, radius: 0.36, capital: 'corinthian', segments: 10 },
          );
          ebox(stucco, e, 0, L, 0, zc + 0.5, F2, F2 + 0.75);
          ebox(stucco2, e, 0, L, 0, zc + 0.6, F2 + 0.6, F2 + 0.75);
          // attic balustrade above the main cornice
          kit.balustrade(batch, stucco, [at(e, 0.2, 0.2), at(e, L - 0.2, 0.2)], CORN + 0.9, {
            height: 0.9,
            spacing: 0.42,
          });
        } else {
          ebox(stucco2, e, 0, L, 0, 0.3, F2, F2 + 0.35);
        }
        // party-wall chimney stacks
        const cp = at(e, 0.1, -3.2);
        kit.box(batch, stucco2, cp[0], cp[1], CORN + 0.8, 0.9, 3.0, 3.8, e.ang);
        for (let k = 0; k < 4; k++) {
          const p = at(e, 0.1, -2.0 - k * 0.75);
          cyl(kit.mat('#b4553f'), p[0], p[1], CORN + 4.6, 0.16, 0.14, 0.6, 6);
        }
      }
    }
    g.add(batch.toGroup('belgrave_square_terraces'));
    return g;
  },
};
