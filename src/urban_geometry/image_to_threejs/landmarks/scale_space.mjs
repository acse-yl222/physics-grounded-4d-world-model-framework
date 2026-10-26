// Scale Space, 58 Wood Lane, Imperial College White City Campus (CJCT for Imperial
// College / Blenheim Chalcot, modular construction, c.2019-21). ~25,500 m2 of flexible
// offices, R&D and clean-room labs for scale-up companies, now also home to the
// Imperial White City Incubator and Business School spaces. Three four-storey blocks
// of stacked prefabricated modules linked by full-height glazed atria, on the strip
// between Wood Lane and the Hammersmith & City line just south of the Westway.
export default {
  id: 'scale_space',
  name: 'Scale Space (incl. Imperial White City Incubator)',
  claims: ['6d4f0959-8460-45cb-81bb-f2e2e948279f'],
  references: [
    {
      title: 'Scale Space - CJCT',
      url: 'https://cjctstudios.com/portfolio-item/scale-space/',
      used_for:
        'three 4-storey buildings, prefabricated modules assembled in situ, modules stacked around atria',
    },
    {
      title: 'Scale Space - New London Architecture',
      url: 'https://www.nla.london/index.php/projects/scale-space-london',
      used_for: '25,500 m2 for R&D, technology and education firms; Imperial + Blenheim Chalcot',
    },
    {
      title: 'Phase B, Scale Space - JLL',
      url: 'https://property.jll.co.uk/rent-office/office-rent-london-w12-7rz-45809',
      used_for: 'atriums with full-height glazing, modular construction',
    },
    {
      title: 'White City Incubator - Imperial',
      url: 'https://imperial.ac.uk/stories/white-city-incubator',
      used_for: 'incubator moved into Scale Space, 58 Wood Lane',
    },
  ],
  notes:
    'Cladding colour and window pattern are NOT documented in the sources found: charcoal metal cassette ' +
    'cladding with light module joints every 3 m and one framed window per module is an assumption, as are the ' +
    'rooftop PV arrays and louvred plant enclosures. Atria are placed at equal spacing along the footprint ' +
    'with ridged rooflights and entrance canopies on their outer faces; height 4 storeys (~18 m) replaces ' +
    'Overture h=9.5 m. The Invention Rooms could not be located in the footprint data and are not modelled ' +
    'separately.',
  build({ THREE, kit, buildings, frame, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const G = 4.6,
      ST = 4.2,
      H = G + 3 * ST; // 17.2

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
      for (const e of edgesOf(r)) {
        if (e.len < 0.05) continue;
        const v0 = (z0 - base) / th,
          v1 = (z1 - base) / th;
        batch.quad(
          mat,
          [e.a[0], e.a[1], z0],
          [e.b[0], e.b[1], z0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [s / tw, v0],
          [(s + e.len) / tw, v0],
          [(s + e.len) / tw, v1],
          [s / tw, v1],
        );
        s += e.len;
      }
    };
    const clip = (r, nx, ny, d) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const p = r[k],
          q = r[(k + 1) % r.length];
        const fp = nx * p[0] + ny * p[1] - d,
          fq = nx * q[0] + ny * q[1] - d;
        if (fp >= 0) out.push(p);
        if (fp * fq < 0) {
          const t = fp / (fp - fq);
          out.push([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])]);
        }
      }
      return out;
    };
    const ux = Math.cos(frame.angle),
      uy = Math.sin(frame.angle);
    const ex = kit.orientedExtent(ring, frame.angle);
    const slab = (u0, u1) => clip(clip(ring, ux, uy, u0), -ux, -uy, -u1);

    const at = (e, s, d) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    const ebox = (mat, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, mat, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };

    // Materials.
    const cladding = kit.paintedMaterial(
      'scale_space:cladding',
      256,
      256,
      (c, w, h) => {
        // charcoal flat-lock metal cassettes, 1.5 m x 0.75 m
        c.fillStyle = '#42484d';
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.58);
        for (let y = 0; y < h; y += 32)
          for (let x = (y / 32) % 2 ? -32 : 0; x < w; x += 64) {
            const v = 62 + Math.floor(r() * 10);
            c.fillStyle = `rgb(${v},${v + 6},${v + 12})`;
            c.fillRect(x + 1, y + 1, 62, 30);
          }
      },
      { roughness: 0.55, metalness: 0.35 },
    );
    const glassTex = kit.paintedMaterial(
      'scale_space:glass',
      256,
      256,
      (c, w, h) => {
        const grd = c.createLinearGradient(0, 0, 0, h);
        grd.addColorStop(0, '#9aa8ae');
        grd.addColorStop(0.15, '#5b7383');
        grd.addColorStop(1, '#34444f');
        c.fillStyle = grd;
        c.fillRect(0, 0, w, h);
      },
      { roughness: 0.18, metalness: 0.35 },
    );
    const atriumGlass = kit.mat('#7fa0b2', {
      roughness: 0.12,
      metalness: 0.4,
      transparent: true,
      opacity: 0.6,
    });
    const roofM = kit.mat('#8d8f8c');
    const white = kit.mat('#dcdedc', { roughness: 0.5, metalness: 0.2 });
    const frameM = kit.mat('#c9cdcf', { roughness: 0.4, metalness: 0.5 });
    const darkGlass = kit.mat('#26333c', { roughness: 0.12, metalness: 0.4 });
    const skyGlass = kit.mat('#8fb2c4', {
      roughness: 0.1,
      metalness: 0.5,
      transparent: true,
      opacity: 0.75,
    });
    const lou = kit.mat('#a9adae', { roughness: 0.5, metalness: 0.3 });
    const pv = kit.mat('#1f2b3a', { roughness: 0.25, metalness: 0.4 });

    // Three module blocks linked by two full-height glazed atria.
    const L = ex.u1 - ex.u0,
      A = 11;
    const bl = (L - 2 * A) / 3;
    const cuts = [];
    let u = ex.u0;
    for (let k = 0; k < 3; k++) {
      cuts.push({ kind: 'block', u0: u, u1: u + bl });
      u += bl;
      if (k < 2) cuts.push({ kind: 'atrium', u0: u, u1: u + A });
      u += A;
    }
    // Edges lying on a cut line are internal (block / atrium party walls).
    const onCut = (e) => {
      const ua = ux * e.a[0] + uy * e.a[1],
        ub = ux * e.b[0] + uy * e.b[1];
      return cuts.some((c) =>
        [c.u0, c.u1].some((v) => Math.abs(ua - v) < 0.05 && Math.abs(ub - v) < 0.05),
      );
    };
    const rr = kit.rng(0.913);
    const winOpts = {
      width: 2.2,
      height: 2.3,
      bay: 3.0,
      margin: 0.4,
      depth: 0.22,
      glass: glassTex,
      frame: frameM,
      sill: white,
      head: 'none',
      bars: 0,
    };
    for (const c of cuts) {
      const r = slab(c.u0, c.u1);
      if (r.length < 3 || Math.abs(kit.ringArea(r)) < 20) continue;
      if (kit.ringArea(r) < 0) r.reverse();
      if (c.kind === 'block') {
        // Ground floor: recessed glazed base with mullions under a light fascia.
        const gr = kit.offsetRing(r, -0.5);
        for (const e of edgesOf(gr)) {
          if (e.len < 0.05) continue;
          batch.quad(
            darkGlass,
            [e.a[0], e.a[1], 0],
            [e.b[0], e.b[1], 0],
            [e.b[0], e.b[1], G - 0.6],
            [e.a[0], e.a[1], G - 0.6],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
          if (onCut(e)) continue;
          const n = Math.max(1, Math.round(e.len / 1.5));
          for (let k = 0; k <= n; k++)
            ebox(frameM, e, (k * e.len) / n - 0.04, (k * e.len) / n + 0.04, 0, 0.14, 0, G - 0.6);
          ebox(frameM, e, 0, e.len, 0, 0.12, 2.9, 3.0);
        }
        kit.cap(batch, white, [[r]], G - 0.6, { down: true });
        kit.walls(batch, white, [[r]], G - 0.6, G);
        // Upper module storeys: cassette cladding with real windows per 3 m module.
        skin(cladding, r, G, H, 6, 6, G);
        for (const e of edgesOf(r)) {
          if (e.len < 0.5 || onCut(e)) continue;
          // module joints: light vertical posts every 3 m and floor-line bands
          const n = Math.max(1, Math.round(e.len / 3));
          for (let k = 0; k <= n; k++) {
            const s = Math.min(e.len - 0.08, Math.max(0.08, (k * e.len) / n));
            ebox(white, e, s - 0.08, s + 0.08, -0.02, 0.1, G, H);
          }
          for (let f = 1; f < 3; f++)
            ebox(white, e, 0, e.len, -0.02, 0.12, G + f * ST - 0.1, G + f * ST + 0.1);
          if (e.len < 2.6) continue;
          for (let f = 0; f < 3; f++)
            kit.windowRow(batch, e.a, e.b, G + f * ST + 0.9, { ...winOpts, count: n, margin: 0 });
        }
        kit.walls(batch, white, [[r]], H, H + 0.8);
        kit.cap(batch, roofM, [[r]], H + 0.2);
        kit.cornice(batch, white, r, H + 0.8, { height: 0.08, projection: 0.06 });
        // Rooftop: louvred plant enclosure and PV arrays.
        const fr = kit.ringFrame(r);
        const pl = [
          [-0.18, -0.18],
          [0.18, -0.18],
          [0.18, 0.18],
          [-0.18, 0.18],
        ].map(([p, q]) => [
          fr.cx + Math.cos(fr.angle) * p * fr.length - Math.sin(fr.angle) * q * fr.width,
          fr.cy + Math.sin(fr.angle) * p * fr.length + Math.cos(fr.angle) * q * fr.width,
        ]);
        if (kit.ringArea(pl) < 0) pl.reverse();
        kit.walls(batch, kit.mat('#6c7073'), [[kit.offsetRing(pl, -0.3)]], H + 0.2, H + 2.6);
        kit.cap(batch, roofM, [[kit.offsetRing(pl, -0.3)]], H + 2.6);
        for (const e of edgesOf(pl)) {
          for (let z = H + 0.4; z < H + 2.9; z += 0.3)
            ebox(lou, e, 0, e.len, -0.18, 0, z, z + 0.06);
        }
        // PV rows tilted south on the rest of the roof
        const pvGeo = new THREE.BoxGeometry(1.7, 1.0, 0.05);
        const inner = kit.offsetRing(r, -2.5);
        const ie = kit.orientedExtent(inner, fr.angle);
        const inside = (ring2, p) => {
          let c2 = false;
          for (let i = 0, j = ring2.length - 1; i < ring2.length; j = i++) {
            const [xi, yi] = ring2[i],
              [xj, yj] = ring2[j];
            if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi)
              c2 = !c2;
          }
          return c2;
        };
        const plOut = kit.offsetRing(pl, 1.5);
        for (let vv = ie.v0 + 1; vv < ie.v1 - 0.5; vv += 2.2)
          for (let uu = ie.u0 + 1; uu < ie.u1 - 1; uu += 1.8) {
            const pt = ie.at(uu, vv, 0);
            if (!inside(inner, pt) || inside(plOut, pt)) continue;
            const m = new THREE.Matrix4()
              .makeTranslation(pt[0], pt[1], H + 0.55)
              .multiply(new THREE.Matrix4().makeRotationZ(fr.angle))
              .multiply(new THREE.Matrix4().makeRotationX(0.26));
            batch.addGeometry(pv, pvGeo, m);
          }
        pvGeo.dispose();
        rr();
      } else {
        const hA = H + 1.6;
        for (const e of edgesOf(r)) {
          if (e.len < 0.05 || onCut(e)) continue;
          batch.quad(
            atriumGlass,
            [e.a[0], e.a[1], 0],
            [e.b[0], e.b[1], 0],
            [e.b[0], e.b[1], hA],
            [e.a[0], e.a[1], hA],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
          const n = Math.max(1, Math.round(e.len / 1.5));
          for (let k = 0; k <= n; k++)
            ebox(frameM, e, (k * e.len) / n - 0.05, (k * e.len) / n + 0.05, -0.05, 0.2, 0, hA);
          for (const z of [G, G + ST, G + 2 * ST, hA - 0.1])
            ebox(frameM, e, 0, e.len, -0.05, 0.18, z - 0.08, z + 0.08);
          // entrance doors and canopy on the outer atrium faces
          if (e.len > 6) {
            const sm = e.len / 2;
            ebox(white, e, sm - 3.5, sm + 3.5, 0, 2.5, 3.2, 3.45);
            for (const ds of [-1, 1])
              ebox(
                kit.mat('#3b4348'),
                e,
                sm + ds * 0.95 - 0.9,
                sm + ds * 0.95 + 0.9,
                0,
                0.1,
                0,
                2.6,
              );
          }
        }
        // ridged rooflight with glazing bars
        const fr = kit.ringFrame(r);
        const rb = kit.orientedExtent(r, fr.angle);
        const P = (uu, vv, z) => rb.at(uu, vv, z);
        const vm = (rb.v0 + rb.v1) / 2;
        const uv4 = [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ];
        batch.quad(
          skyGlass,
          P(rb.u0, rb.v0, hA),
          P(rb.u1, rb.v0, hA),
          P(rb.u1, vm, hA + 1.6),
          P(rb.u0, vm, hA + 1.6),
          ...uv4,
        );
        batch.quad(
          skyGlass,
          P(rb.u1, rb.v1, hA),
          P(rb.u0, rb.v1, hA),
          P(rb.u0, vm, hA + 1.6),
          P(rb.u1, vm, hA + 1.6),
          ...uv4,
        );
        for (const uu of [rb.u0, rb.u1]) {
          const tri = [P(uu, rb.v0, hA), P(uu, rb.v1, hA), P(uu, vm, hA + 1.6)];
          batch.add(
            skyGlass,
            tri,
            [
              [0, 0],
              [1, 0],
              [0.5, 1],
            ],
            [0, 1, 2, 0, 2, 1],
          );
        }
        kit.box(batch, white, fr.cx, fr.cy, hA + 1.5, fr.length, 0.3, 0.25, fr.angle);
        for (
          let uu = rb.u0;
          uu <= rb.u1 + 0.01;
          uu += (rb.u1 - rb.u0) / Math.max(1, Math.round((rb.u1 - rb.u0) / 1.5))
        )
          for (const s of [-1, 1]) {
            const a = P(uu, vm + s * (rb.v1 - rb.v0) * 0.25, hA + 0.8);
            const len = Math.hypot((rb.v1 - rb.v0) / 2, 1.6);
            const geo = new THREE.BoxGeometry(0.08, len, 0.1);
            const m = new THREE.Matrix4()
              .makeTranslation(a[0], a[1], a[2] + 0.05)
              .multiply(new THREE.Matrix4().makeRotationZ(fr.angle))
              .multiply(
                new THREE.Matrix4().makeRotationX(-s * Math.atan2(1.6, (rb.v1 - rb.v0) / 2)),
              );
            batch.addGeometry(frameM, geo, m);
            geo.dispose();
          }
        // bike stands and benches in front of the atrium entrances
        const outer = edgesOf(r).filter((e) => !onCut(e) && e.len > 6);
        for (const e of outer) {
          g.add(
            placeAssets(
              'bicycle_stand',
              [0, 1, 2, 3, 4].map((k) => [...at(e, 0.8 + k * 1.0, 3.5), e.ang + Math.PI / 2]),
            ),
          );
          g.add(placeAssets('bench', [[...at(e, e.len - 1.2, 3.2), e.ang + Math.PI]]));
        }
      }
    }
    // Name sign on the northern end facing the Westway.
    {
      const sign = kit.paintedMaterial(
        'scale_space:sign',
        512,
        128,
        (c, w, h) => {
          c.fillStyle = '#41474c';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#ffffff';
          c.font = 'bold 64px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('SCALE SPACE', w / 2, h / 2 + 4);
        },
        { roughness: 0.5 },
      );
      const top =
        edgesOf(ring)
          .filter((e) => e.nx * ux + e.ny * uy > 0.8)
          .sort((p, q) => q.len - p.len)[0] ??
        edgesOf(ring)
          .filter((e) => e.nx * ux + e.ny * uy < -0.8)
          .sort((p, q) => q.len - p.len)[0];
      if (top) {
        const m = [
          (top.a[0] + top.b[0]) / 2 + top.nx * 0.35,
          (top.a[1] + top.b[1]) / 2 + top.ny * 0.35,
        ];
        const w = Math.min(14, top.len - 2);
        const a = [m[0] - (top.dx * w) / 2, m[1] - (top.dy * w) / 2],
          b = [m[0] + (top.dx * w) / 2, m[1] + (top.dy * w) / 2];
        batch.quad(
          sign,
          [a[0], a[1], H - 3.2],
          [b[0], b[1], H - 3.2],
          [b[0], b[1], H - 0.2],
          [a[0], a[1], H - 0.2],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    g.add(batch.toGroup('scale_space'));
    return g;
  },
};
