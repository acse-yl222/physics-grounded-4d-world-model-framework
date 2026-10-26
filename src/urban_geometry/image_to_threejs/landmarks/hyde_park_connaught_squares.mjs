// Hyde Park Square and Connaught Square terraces, Tyburnia (Bayswater). Tyburnia was
// planned in 1827 by Samuel Pepys Cockerell and laid out to a modified plan by George
// Gutch. Connaught Square (c. 1828-30, probably Gutch) was the first square of town houses
// in Bayswater: four-storey brown-brick houses over basements with channelled stucco
// ground floors, stucco plat bands and concealed slate roofs. Hyde Park Square, a garden
// square of 200 x 500 ft where Lancaster Gate and Connaught Village meet, is lined by
// stucco-fronted classical houses.
const HYDE_PARK_SQUARE = [
  'c86d26e5-d0e3-43c1-8a0c-9d1662b3b5de',
  '6f9fb5ec-5c49-4793-8d33-f9d6fe3c7b2a',
  '6d1910df-6f67-416c-818a-91a3582e966b',
  '873ec5b4-379c-4436-814f-82e9e80c08ce',
  '73b3071b-2fd4-49ad-80a6-534f6c151cce',
  'dc663202-cf3b-41de-8cc9-52f18a7252c5',
  '14cd2d3a-44cd-47bd-bae9-f0993b1e74ce',
  '4e05f06c-a588-493a-b1f8-3e924543d09e',
  '378f8d8e-ed11-4bc6-aa7c-56ed188a8424',
  'ae836a74-3de0-460f-bd12-12b0a958ef5b',
  'b215dd8d-1ebb-4dc3-9b35-1a2ddc15cd20',
  '9e6c1235-1e26-48a5-904c-a47f31870819',
  'ab36fd32-8654-47db-8df2-ba067d21b55d',
  '79fc9585-6f63-41be-9c7b-2198469eddc5',
  '091de08c-9f37-4a28-9e0c-16b3199f29cc',
  '9e062e5b-5389-4280-a394-75af3d439c73',
  'afa8ec95-3542-4ce5-a327-4c42f556e2af',
  'dc760552-09d3-4144-ab5f-e333c014def6',
  'c17f20ee-33a0-4bb8-9f84-b3c078ed6c63',
  '9b53cbc4-b424-4d68-a219-27a34c3c42c0',
  'c420146d-e233-486b-bfe5-78cb8165983b',
  '62a543a9-1694-4ba3-85ad-92af43c9b890',
  '7c9cde64-5dcb-4262-8c08-b300259e044c',
];
const CONNAUGHT_SQUARE = [
  '7bb2999d-e746-4dc9-932e-a6a3bdc091f5',
  '04a45ef0-544d-4284-91bd-22004b945ed8',
  '7c27c783-7959-4026-9ee3-0eb1b9854bd4',
  'a649c3bc-0ff3-42ae-bfb2-2518cc35208e',
  '71607da9-4071-45ce-b0bc-c22983ac550b',
  '3ed29c70-edcf-4922-a85f-fefc074535b7',
  'a6b10330-08b3-4ec1-88d2-25e3343d8b88',
  '2ba75174-9421-4ca4-a7fb-204b3daf462b',
  'ecbec7b5-1f3d-4c3d-9c41-6972c978834a',
  'c0febee5-d4d1-44e6-a479-b6a44383feba',
  '16f046c2-429f-44ed-aaa1-f76634553cc1',
  '99fa613d-0d01-4e47-a3c8-fd4ddb5ffb86',
  '5823f184-8544-48e1-a482-5e434bac2a67',
  'd39836fd-9635-49dc-93f2-cfa47222e560',
  '723f9dee-13d0-4f79-9489-888fff831aab',
  '079223ae-a79f-40a3-90af-d857dfbebfce',
  'a5612e2b-9fe7-4228-a4f4-58f6b45db04d',
  '2d6cc1cc-266d-40d0-bdb2-2cbde5e0a254',
  '2324fcc5-5b2d-4c52-af01-cf5c00229da1',
  '8f4b27ef-3889-4676-8207-54b31e7028a6',
  'd983b254-4a6c-4e36-9d92-b773cb5ae8e4',
  '0fda8876-10df-47ce-9224-65352690d69f',
  'df8c6d45-471a-4ade-ac6d-c63ddc4224f7',
  'daadca8d-cd53-444f-a851-e69e01c39888',
  'f1a0f339-a7da-48a8-a918-84be56febc4d',
  '707a99a2-248f-4181-9e79-1d0eefda1584',
  '4887bb06-6e37-4972-bab0-cd2667b66901',
  '844b79ec-f130-4171-b823-e8f3887c902d',
  '23b0fddb-fa4e-4366-b944-5572b0e8fa5d',
  'dce39eba-a166-4554-a2c5-995335d7e2a8',
  'b423ddbd-2114-497e-8565-3b9214b507bc',
  'cf0f85eb-c505-44c6-91ba-6d733214a4a7',
  'd140b6bb-631f-462d-a58e-32fcd1c31ab5',
  'f25aa64a-7aa5-4d7f-b8d3-8a46042ee30f',
  '0f187323-f107-4533-8a24-a3914494ebe1',
  'a283d91a-9dd1-4893-9a60-03b0f455446c',
  '29a55933-f5d4-48fb-92da-f31032879d22',
  '81c43016-c05d-4a8f-a679-11393c35a057',
  'd76570c0-5f1f-448d-b1e4-e9d877d55154',
  '10c431e3-f843-4ede-a48d-4614885211ec',
  '8e790919-fdc2-4734-af85-dc91812d64f3',
];
export default {
  id: 'hyde_park_connaught_squares',
  name: 'Hyde Park Square and Connaught Square terraces',
  claims: [...HYDE_PARK_SQUARE, ...CONNAUGHT_SQUARE],
  references: [
    {
      title: 'Hyde Park Square - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hyde_Park_Square',
      used_for:
        'garden square of 200 x 500 ft with listed classical buildings; Tyburnia plan by S. P. Cockerell (1827) laid out by George Gutch',
    },
    {
      title: 'Connaught Square - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Connaught_Square',
      used_for:
        'first square of town houses in Bayswater, predominantly four-storey terraced houses',
    },
    {
      title: '1-15 Connaught Square - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101219945-1-15-connaught-square-w2-hyde-park-ward',
      used_for:
        'brown brick with channelled stucco ground floors, concealed slate roofs, 4 storeys and basements, stucco plat bands over the ground floor and at third floor',
    },
    {
      title: '39-46 Connaught Square - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101219972-39-46-connaught-square-w2-hyde-park-ward',
      used_for: 'south side: same materials, attic storeys to nos 45 and 46',
    },
    {
      title: '23-37 Connaught Square - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101291228-23-37-connaught-square-w2-hyde-park-ward',
      used_for:
        'west side: brown brick in Flemish bond, channelled stucco ground floor; c. 1828-30, probably George Gutch',
    },
  ],
  notes:
    'Group module: footprints along Hyde Park Square (23, excluding the 9-storey post-war block and low mews buildings) and Connaught Square (41). Hyde Park Square houses are given generic stucco fronts with Doric porches and balconies (5 storeys, ~17 m); Connaught Square houses brown brick over a channelled stucco ground floor with plat bands, 4 storeys (~13 m) and a parapet hiding the roof. Individual doorcases, balconies and later attic storeys are not distinguished; rear faces use the stock-brick facade texture.',
  build(ctx) {
    // ---- local helpers (no imports: kept inline) ---------------------------------
    const { THREE, kit } = ctx;
    const B = new kit.MeshBatch();
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r.slice());
    const ringOf = (id) => ccw(ctx.byId[id].polys[0][0]);
    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1e-9;
        return {
          a,
          b,
          k,
          len,
          ux: dx / len,
          uy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
        };
      });
    const at = (e, s, d = 0) => [e.a[0] + e.ux * s + e.nx * d, e.a[1] + e.uy * s + e.ny * d];
    // Box on edge e: along-edge span s0..s1, outward offset d0..d1, height z0..z1.
    const ebox = (m, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(B, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const prism = (m, ring, z0, z1, topM = m) => {
      kit.walls(B, m, [[ring]], z0, z1, { bay: 1e6 });
      if (topM) kit.cap(B, topM, [[ring]], z1);
    };
    // Local rectangle (centre cx, cy, size w x d, rotated a) as a CCW ring.
    const rect = (cx, cy, w, d, a = 0) => {
      const c = Math.cos(a),
        s = Math.sin(a);
      return [
        [-w / 2, -d / 2],
        [w / 2, -d / 2],
        [w / 2, d / 2],
        [-w / 2, d / 2],
      ].map(([u, v]) => [cx + u * c - v * s, cy + u * s + v * c]);
    };
    const geo = (m, g, x, y, z, rz = 0, sx = 1, sy = 1, sz = 1) => {
      const M = new THREE.Matrix4().compose(
        new THREE.Vector3(x, y, z),
        new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), rz),
        new THREE.Vector3(sx, sy, sz),
      );
      B.addGeometry(m, g, M);
      g.dispose();
    };
    // Upright cylinder / cone / pyramid (axis +z) from z0 to z1.
    const cyl = (m, x, y, z0, z1, r0, r1 = r0, seg = 12, rz = 0) =>
      geo(
        m,
        new THREE.CylinderGeometry(r1, r0, z1 - z0, seg).rotateX(Math.PI / 2),
        x,
        y,
        (z0 + z1) / 2,
        rz,
      );
    // Curtain wall on every edge of ring: glass, vertical mullions and storey bands.
    const curtain = (ring, z0, z1, o = {}) => {
      const {
        glass = kit.mat('glass'),
        frame = kit.mat('aluminium'),
        mull = 1.5,
        storey = 3.6,
        fin = 0.12,
        band = 0.25,
        bandMat = frame,
        minLen = 0.3,
        finMat = frame,
        edgeFilter = () => true,
      } = o;
      for (const e of edgesOf(ring)) {
        if (e.len < minLen || !edgeFilter(e)) continue;
        B.quad(
          glass,
          [e.a[0], e.a[1], z0],
          [e.b[0], e.b[1], z0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        if (mull > 0) {
          const n = Math.max(1, Math.round(e.len / mull));
          for (let i = 0; i < n; i++) {
            const s = (i * e.len) / n;
            ebox(finMat, e, s - 0.04, s + 0.04, 0, fin, z0, z1);
          }
        }
        if (band > 0)
          for (let z = z0 + storey; z < z1 - 0.3; z += storey)
            ebox(bandMat, e, 0, e.len, 0, fin * 0.8, z - band / 2, z + band / 2);
      }
    };
    // Punched windows storey by storey on edges passing filter.
    const punched = (ring, z0, storeys, storey, opts, filter = (e) => e.len > 2.5) => {
      for (const e of edgesOf(ring)) {
        if (!filter(e)) continue;
        for (let s = 0; s < storeys; s++) {
          const o = typeof opts === 'function' ? opts(s, e) : opts;
          if (o) kit.windowRow(B, e.a, e.b, z0 + s * storey, o);
        }
      }
    };
    // Distance from point to the nearest named road centreline (scene roads).
    const roadSegs = (names) => {
      const out = [];
      for (const r of ctx.scene.roads || []) {
        if (r.cls === 'footway' || (names && !names.includes(r.name))) continue;
        for (let i = 1; i < r.line.length; i++) out.push([r.line[i - 1], r.line[i]]);
      }
      return out;
    };
    // Nearest point on the road centrelines: [distance, x, y].
    const segNearest = (p, segs) => {
      let best = [Infinity, 0, 0];
      for (const [a, b] of segs) {
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          l = dx * dx + dy * dy || 1;
        const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l));
        const x = a[0] + t * dx,
          y = a[1] + t * dy,
          d = Math.hypot(p[0] - x, p[1] - y);
        if (d < best[0]) best = [d, x, y];
      }
      return best;
    };
    // Does edge e face a road: the nearest road point lies within maxD and in front of the
    // edge (within ~50 degrees of its outward normal)?
    const facesRoad = (e, segs, maxD = 22, cosMin = 0.64) => {
      const m = at(e, e.len / 2, 0);
      const [d, x, y] = segNearest(m, segs);
      if (!(d < maxD) || d < 1e-6) return false;
      return ((x - m[0]) * e.nx + (y - m[1]) * e.ny) / d > cosMin;
    };
    // ------------------------------------------------------------------------------
    // ---- terrace helper: one footprint of a stucco / brick terrace -----------------
    // Street faces get real windows, cornices, porches and balconies; other faces get
    // the windowed facade texture. o: { h (cornice), storeys:[heights], front (edge => bool),
    // face: 'stucco'|'brick', attic, porch, balcony, rear }
    const wallQuad = (m, e, z0, z1, bay = 3.6, storey = 3.2) => {
      const n = Math.round(e.len / bay);
      const u1 = n >= 1 ? n / 4 : 0.03;
      B.quad(
        m,
        [e.a[0], e.a[1], z0],
        [e.b[0], e.b[1], z0],
        [e.b[0], e.b[1], z1],
        [e.a[0], e.a[1], z1],
        [0, z0 / (2 * storey)],
        [u1, z0 / (2 * storey)],
        [u1, z1 / (2 * storey)],
        [0, z1 / (2 * storey)],
      );
    };
    const TM = {
      stucco: kit.mat('#eee8da', { roughness: 0.75 }),
      brick: kit.mat('#8f7556', { roughness: 0.92 }),
      trim: kit.mat('#f4f0e6', { roughness: 0.7 }),
      glass: kit.mat('#2c3940', { roughness: 0.2, metalness: 0.3 }),
      frame: kit.mat('#f7f6f2', { roughness: 0.6 }),
      rail: kit.mat('#1f2326', { roughness: 0.5, metalness: 0.4 }),
      door: kit.mat('#1d2b24', { roughness: 0.5 }),
      roof: kit.mat('slate'),
      lead: kit.mat('lead'),
      rearTex: kit.facade('london_stock', 1),
      chimney: kit.mat('#9a8466', { roughness: 0.95 }),
    };
    const terrace = (ring, o) => {
      const st = o.storeys; // storey heights from the ground
      const zs = [0];
      for (const h of st) zs.push(zs[zs.length - 1] + h);
      const H = zs[zs.length - 1];
      const face = o.face === 'brick' ? TM.brick : TM.stucco;
      const E = edgesOf(ring);
      for (const e of E) {
        if (e.len < 0.2) continue;
        const front = o.front(e);
        if (!front) {
          wallQuad(o.rearMat || TM.rearTex, e, 0, H, 3.4, 3.1);
          continue;
        }
        // ground storey always stucco (channelled), upper storeys in the face material
        wallQuad(TM.stucco, e, 0, zs[1]);
        wallQuad(face, e, zs[1], H);
        if (e.len < 2.5) continue;
        for (let z = 0.6; z < zs[1] - 0.3; z += 0.55)
          ebox(TM.stucco, e, 0, e.len, 0, 0.05, z, z + 0.06);
        const houses = Math.max(1, Math.round(e.len / (o.houseW || 7.2)));
        const hw = e.len / houses;
        for (let hI = 0; hI < houses; hI++) {
          const s0 = hI * hw;
          const a = at(e, s0),
            b = at(e, s0 + hw);
          // door with fanlight + windows on the ground storey
          const doorS = s0 + hw * 0.25;
          ebox(TM.door, e, doorS - 0.6, doorS + 0.6, 0.02, 0.08, 0.6, 3.2);
          for (const t of [0.58, 0.82]) {
            ebox(TM.glass, e, s0 + hw * t - 0.6, s0 + hw * t + 0.6, 0.01, 0.05, 1.2, 3.4);
            ebox(TM.trim, e, s0 + hw * t - 0.72, s0 + hw * t + 0.72, 0, 0.16, 1.1, 1.2);
          }
          if (o.porch) {
            // paired Doric porch with a balustraded top (first-floor balcony)
            const pd = 1.8;
            for (const ds of [-1.05, 1.05]) {
              const c = at(e, doorS + ds, pd);
              cyl(TM.trim, c[0], c[1], 0.3, zs[1] - 0.7, 0.2, 0.18, 6);
            }
            ebox(TM.trim, e, doorS - 1.45, doorS + 1.45, 0, pd + 0.3, zs[1] - 0.7, zs[1] - 0.15);
            ebox(TM.trim, e, doorS - 1.45, doorS + 1.45, 0, pd + 0.3, 0, 0.3);
            ebox(
              TM.trim,
              e,
              doorS - 1.4,
              doorS + 1.4,
              pd + 0.05,
              pd + 0.25,
              zs[1] - 0.15,
              zs[1] + 0.75,
            );
          }
          // upper storeys
          for (let k = 1; k < st.length; k++) {
            const sh = st[k];
            const wh = Math.min(sh - 1.0, k === 1 ? 2.9 : sh * 0.62);
            const nW = hw > 6 ? 3 : 2;
            if (k >= 2) {
              // upper storeys: recessed sash panel with a sill (cheap)
              for (let i = 0; i < nW; i++) {
                const s = s0 + 0.7 + ((hw - 1.4) * (i + 0.5)) / nW;
                ebox(TM.glass, e, s - 0.52, s + 0.52, 0.01, 0.05, zs[k] + 0.6, zs[k] + 0.6 + wh);
                ebox(TM.trim, e, s - 0.65, s + 0.65, 0, 0.16, zs[k] + 0.5, zs[k] + 0.6);
                if (k === 2)
                  ebox(
                    TM.trim,
                    e,
                    s - 0.65,
                    s + 0.65,
                    0,
                    0.14,
                    zs[k] + 0.6 + wh,
                    zs[k] + 0.78 + wh,
                  );
              }
              continue;
            }
            const head = k === 1 ? 'pediment' : 'lintel';
            kit.windowRow(B, a, b, zs[k] + (k === 1 ? 0.35 : 0.6), {
              count: nW,
              width: k === 1 ? 1.25 : 1.1,
              height: wh,
              glass: TM.glass,
              frame: TM.frame,
              sill: TM.trim,
              head,
              bars: 0,
              margin: 0.7,
              surround: 0,
              surroundMat: TM.trim,
            });
          }
        }
        // first-floor balcony rail along the front (on top of the ground-floor cornice)
        if (o.balcony) {
          ebox(TM.trim, e, 0, e.len, 0, 0.9, zs[1] - 0.2, zs[1] + 0.05);
          ebox(TM.rail, e, 0, e.len, 0.82, 0.88, zs[1] + 0.05, zs[1] + 1.0);
        }
      }
      // string courses and the main cornice (front material is stucco either way)
      kit.cornice(B, TM.trim, ring, zs[1] - 0.25, { height: 0.25, projection: 0.15 });
      if (st.length > 3)
        kit.cornice(B, TM.trim, ring, zs[st.length - 1] - 0.2, { height: 0.2, projection: 0.1 });
      kit.cornice(B, TM.trim, ring, H - 0.55, { height: 0.55, projection: 0.45, steps: 2 });
      // parapet and roof: either an attic mansard with dormers or a parapet with a flat roof
      kit.walls(B, TM.trim, [[ring]], H, H + 0.9, { bay: 1e6 });
      if (o.attic) {
        const inner = kit.offsetRing(ring, -0.8);
        kit.cap(B, TM.roof, [[ring, inner.slice().reverse()]], H + 0.9);
        const top = kit.offsetRing(ring, -2.0);
        // mansard slope from the parapet line up to the attic flat
        for (let k = 0; k < inner.length; k++) {
          const a = inner[k],
            b = inner[(k + 1) % inner.length],
            c = top[(k + 1) % top.length],
            d = top[k];
          B.add(
            TM.roof,
            [
              [a[0], a[1], H + 0.9],
              [b[0], b[1], H + 0.9],
              [c[0], c[1], H + o.attic],
              [d[0], d[1], H + o.attic],
            ],
            [
              [0, 0],
              [1, 0],
              [1, 1],
              [0, 1],
            ],
            [0, 1, 2, 0, 2, 3],
          );
        }
        kit.cap(B, TM.lead, [[top]], H + o.attic);
        for (const e of edgesOf(inner)) {
          if (!o.front(e) || e.len < 4) continue;
          const n = Math.max(1, Math.round(e.len / 3.6));
          for (let i = 0; i < n; i++) {
            const s = ((i + 0.5) * e.len) / n;
            ebox(TM.trim, e, s - 0.7, s + 0.7, -0.6, 0.1, H + 0.9, H + 2.5);
            ebox(TM.glass, e, s - 0.45, s + 0.45, 0.1, 0.12, H + 1.1, H + 2.3);
            ebox(TM.lead, e, s - 0.8, s + 0.8, -0.7, 0.2, H + 2.5, H + 2.7);
          }
        }
      } else kit.cap(B, TM.lead, [[ring]], H + 0.4);
      // chimney stacks on the party walls
      if (o.chimneys !== false) {
        const f = kit.ringFrame(ring);
        const n = Math.max(1, Math.round(f.length / (o.houseW || 7.2)));
        for (let i = 0; i <= n; i++) {
          const u = -f.length / 2 + (i * f.length) / n;
          const x = f.cx + Math.cos(f.angle) * u,
            y = f.cy + Math.sin(f.angle) * u;
          if (i === 0 || i === n) continue;
          kit.box(
            B,
            TM.chimney,
            x,
            y,
            H,
            0.7,
            Math.min(3.2, f.width * 0.3),
            (o.attic || 0.9) + 1.6,
            f.angle,
          );
        }
      }
      return H;
    };
    // ------------------------------------------------------------------------------
    const hps = new Set(HYDE_PARK_SQUARE);
    const roadsH = roadSegs(['Hyde Park Square']);
    const roadsC = roadSegs(['Connaught Square']);
    for (const b of ctx.buildings) {
      const ring = ccw(b.polys[0][0]);
      if (hps.has(b.id))
        terrace(ring, {
          storeys: [3.8, 4.0, 3.4, 3.0, 2.8],
          front: (e) => e.len > 2 && facesRoad(e, roadsH, 25),
          porch: true,
          balcony: true,
          houseW: 7.2,
        });
      else
        terrace(ring, {
          storeys: [3.5, 3.6, 3.2, 2.9],
          face: 'brick',
          front: (e) => e.len > 2 && facesRoad(e, roadsC, 25),
          porch: false,
          balcony: true,
          houseW: 6.4,
        });
    }
    return B.toGroup('hyde_park_connaught_squares');
  },
};
