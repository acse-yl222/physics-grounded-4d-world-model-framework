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
    'Cladding colour and window pattern are NOT documented in the sources found: charcoal metal module ' +
    'cladding with light frames is an assumption. Atria are placed at equal spacing along the footprint; ' +
    'height 4 storeys (~18 m) replaces Overture h=9.5 m. The Invention Rooms could not be located in the ' +
    'footprint data and are not modelled separately.',
  build({ THREE, kit, buildings, frame }) {
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
        return { a, b, len, dx: dx / len, dy: dy / len, nx: dy / len, ny: -dx / len };
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

    // Materials.
    const modules = kit.paintedMaterial(
      'scale_space:modules',
      512,
      512,
      (c, w, h) => {
        // 6 m x 2 storeys: two 3 m modules per storey, each with a wide window.
        c.fillStyle = '#41474c';
        c.fillRect(0, 0, w, h);
        const mw = w / 2,
          sh = h / 2;
        for (let s = 0; s < 2; s++)
          for (let k = 0; k < 2; k++) {
            const x = k * mw,
              y = s * sh;
            c.fillStyle = '#d6d8d6'; // module frame / joint
            c.fillRect(x, y, mw, 6);
            c.fillRect(x, y, 6, sh);
            const grd = c.createLinearGradient(x, y, x, y + sh);
            grd.addColorStop(0, '#5b7383');
            grd.addColorStop(1, '#34444f');
            c.fillStyle = grd;
            c.fillRect(x + 26, y + 34, mw - 52, sh - 80);
            c.fillStyle = '#9aa0a3';
            c.fillRect(x + mw / 2 - 2, y + 34, 4, sh - 80);
          }
      },
      { roughness: 0.6, metalness: 0.2 },
    );
    const atriumGlass = kit.paintedMaterial(
      'scale_space:atrium',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#6f8fa0';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d0d4d6';
        for (let k = 0; k < 2; k++) c.fillRect((k * w) / 2, 0, 5, h);
        c.fillRect(0, h - 6, w, 6);
        c.fillStyle = 'rgba(255,255,255,0.15)';
        c.fillRect(10, 0, 30, h);
      },
      { roughness: 0.15, metalness: 0.4 },
    );
    const roofM = kit.mat('#8d8f8c');
    const white = kit.mat('#dcdedc');
    const skyGlass = kit.mat('#8fb2c4', { roughness: 0.1, metalness: 0.5 });

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
    for (const c of cuts) {
      const r = slab(c.u0, c.u1);
      if (r.length < 3 || Math.abs(kit.ringArea(r)) < 20) continue;
      if (kit.ringArea(r) < 0) r.reverse();
      if (c.kind === 'block') {
        // Ground floor: glazed shopfront-like base with a light fascia.
        skin(kit.mat('dark_glass'), kit.offsetRing(r, -0.3), 0, G - 0.6, 6, 8);
        kit.walls(batch, white, [[r]], G - 0.6, G);
        skin(modules, r, G, H, 6, 2 * ST, G);
        kit.walls(batch, white, [[r]], H, H + 0.8);
        kit.cap(batch, roofM, [[r]], H + 0.2);
        // rooftop plant
        const fr = kit.ringFrame(r);
        kit.box(
          batch,
          kit.mat('#a9adae'),
          fr.cx,
          fr.cy,
          H + 0.2,
          fr.length * 0.35,
          fr.width * 0.35,
          2.6,
          fr.angle,
        );
      } else {
        const hA = H + 1.6;
        skin(atriumGlass, r, 0, hA, 3, 4.2, 0);
        kit.cap(batch, skyGlass, [[r]], hA);
        // ridge of the rooflight
        const fr = kit.ringFrame(r);
        kit.box(batch, white, fr.cx, fr.cy, hA, fr.length, 0.4, 0.5, fr.angle);
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
