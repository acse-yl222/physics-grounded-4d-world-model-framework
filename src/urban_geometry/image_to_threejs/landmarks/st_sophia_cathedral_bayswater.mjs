// Greek Orthodox Cathedral of St Sophia, Moscow Road, Bayswater (John Oldrid Scott,
// 1877-79, consecrated 1882; Grade I). A neo-Byzantine Greek cross in yellow brick with
// red-brick banding and stone / red-brick dressings, under a central copper dome (lead
// until 1901) whose drum has twelve round-arched lights, topped by a gilded cross, with
// smaller copper semi-domes flanking the nave and terracotta bands round the arches.
export default {
  id: 'st_sophia_cathedral_bayswater',
  name: 'Greek Orthodox Cathedral of St Sophia',
  claims: ['2a3ce69b-72c3-4990-bc33-880fa6cd9513'],
  references: [
    {
      title: 'Saint Sophia Cathedral, London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Saint_Sophia_Cathedral,_London',
      used_for: 'John Oldrid Scott; neo-Byzantine Greek cross; dates',
    },
    {
      title: 'Cathedral of St Sophia - Historic England list entry 1223553',
      url: 'https://HistoricEngland.org.uk/listing/the-list/list-entry/1223553',
      used_for:
        'Grade I; 1878-9; yellow brick with red brick banding, stone and red brick dressings; copper dome with twelve round-arched lights (lead until 1901) and gilded cross; copper semi-domes',
    },
    {
      title: "St Sophia's Cathedral - Gilbert Scott",
      url: 'https://gilbertscott.org/st-sophias-cathedral',
      used_for: 'decorated terracotta banding around the arched doors and windows; modest exterior',
    },
    {
      title: 'St Sophia, Bayswater - Victorian Web',
      url: 'https://victorianweb.org/victorian/art/architecture/byzantine/1.html',
      used_for: 'built 1878-79, consecrated 1882, decoration completed 1892',
    },
  ],
  notes:
    'Dome diameter (~12 m) and heights (walls 14 m, drum to 19.5 m, dome crown ~26 m, cross ~29 m) are estimated from the footprint and photographs descriptions; the copper is shown with a green patina. Arm roofs are modelled as low gables behind parapets.',
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
    const ring = ringOf('2a3ce69b-72c3-4990-bc33-880fa6cd9513');
    const yellow = kit.mat('#d2b97f', { roughness: 0.9 });
    const red = kit.mat('#9a4a35', { roughness: 0.9 });
    const stone = kit.mat('#ddd3bb', { roughness: 0.85 });
    const copper = kit.mat('#5f9a86', { roughness: 0.55, metalness: 0.3 });
    const gold = kit.mat('gold');
    const glassW = kit.mat('#2d3a40', { roughness: 0.3, metalness: 0.2 });
    const roofM = kit.mat('#5a8f7d', { roughness: 0.6, metalness: 0.2 });
    const f = kit.ringFrame(ring);
    const ang = f.angle;
    const cx = f.cx,
      cy = f.cy;
    const W = 14;
    // walls with red-brick banding
    prism(yellow, ring, 0, W, roofM);
    for (let z = 1.0; z < W - 1; z += 1.6)
      kit.cornice(B, red, ring, z, { height: 0.35, projection: 0.04 });
    kit.cornice(B, stone, ring, 0, { height: 0.7, projection: 0.15 });
    kit.cornice(B, red, ring, W - 1.0, { height: 0.5, projection: 0.25 });
    kit.cornice(B, stone, ring, W - 0.5, { height: 0.5, projection: 0.35 });
    // round-arched windows with terracotta (red) arches; triple lights on the arm ends
    for (const e of edgesOf(ring)) {
      if (e.len < 3) continue;
      const n = e.len > 9 ? 3 : e.len > 5 ? 2 : 1;
      kit.windowRow(B, e.a, e.b, 6.0, {
        count: n,
        width: e.len > 9 ? 1.4 : 1.1,
        height: 3.6,
        head: 'arch',
        glass: glassW,
        frame: red,
        sill: stone,
        bars: 1,
        depth: 0.2,
        margin: 1.0,
      });
      if (e.len > 9)
        kit.windowRow(B, e.a, e.b, 1.8, {
          count: 2,
          width: 1.0,
          height: 2.0,
          head: 'arch',
          glass: glassW,
          frame: red,
          sill: stone,
          bars: 0,
          depth: 0.15,
          margin: 2.5,
        });
    }
    // low gabled roofs on the four arms (copper-green), meeting under the drum
    const armL = f.length / 2,
      armW = 10.5;
    for (const [w, d, a] of [
      [f.length - 2, armW, ang],
      [f.width - 2, armW, ang + Math.PI / 2],
    ]) {
      kit.pitchedRoof(B, roofM, yellow, rect(cx, cy, w, d, a), a, W, 3.6, 'gabled', {
        overhang: 0.1,
      });
    }
    // drum with twelve round-arched lights, dome, lantern and gilded cross
    const RD = 6.2,
      Z0 = W + 2.2,
      Z1 = 19.6;
    prism(yellow, rect(cx, cy, 13.6, 13.6, ang), W, Z0, roofM); // square base under the drum
    kit.cornice(B, stone, rect(cx, cy, 13.6, 13.6, ang), Z0 - 0.4, {
      height: 0.4,
      projection: 0.25,
    });
    cyl(yellow, cx, cy, Z0, Z1, RD, RD, 24);
    for (const z of [Z0 + 0.6, Z1 - 0.8]) cyl(red, cx, cy, z, z + 0.3, RD + 0.06, RD + 0.06, 24);
    for (let k = 0; k < 12; k++) {
      const a = ang + (k * Math.PI) / 6 + Math.PI / 12;
      const p0 = [cx + Math.cos(a) * RD, cy + Math.sin(a) * RD];
      const t = [-Math.sin(a), Math.cos(a)];
      // edge from a to b with outward normal = radial direction
      const A = [p0[0] - t[0] * 1.0, p0[1] - t[1] * 1.0],
        Bp = [p0[0] + t[0] * 1.0, p0[1] + t[1] * 1.0];
      kit.windowRow(B, A, Bp, Z0 + 1.2, {
        count: 1,
        width: 0.9,
        height: 1.8,
        head: 'arch',
        glass: glassW,
        frame: stone,
        sill: stone,
        bars: 0,
        depth: 0.15,
        margin: 0.2,
      });
    }
    kit.cornice(
      B,
      stone,
      Array.from({ length: 24 }, (_, k) => [
        cx + Math.cos((k * Math.PI) / 12) * RD,
        cy + Math.sin((k * Math.PI) / 12) * RD,
      ]),
      Z1,
      { height: 0.4, projection: 0.35 },
    );
    const prof = [];
    for (let i = 0; i <= 12; i++) {
      const t = (i / 12) * (Math.PI / 2);
      prof.push([Math.max(0.01, (RD + 0.1) * Math.cos(t)), Z1 + 0.4 + (RD - 0.2) * Math.sin(t)]);
    }
    const domeG = new THREE.LatheGeometry(
      prof.map(([r, z]) => new THREE.Vector2(r, z)),
      32,
    ).rotateX(Math.PI / 2);
    B.addGeometry(copper, domeG, new THREE.Matrix4().makeTranslation(cx, cy, 0));
    domeG.dispose();
    const top = Z1 + 0.4 + RD - 0.2;
    cyl(copper, cx, cy, top - 0.3, top + 1.0, 0.9, 0.7, 12);
    cyl(gold, cx, cy, top + 1.0, top + 1.6, 0.45, 0.1, 12);
    kit.box(B, gold, cx, cy, top + 1.5, 0.12, 0.12, 2.0, ang);
    kit.box(B, gold, cx, cy, top + 2.8, 1.0, 0.12, 0.12, ang);
    // copper semi-domes flanking the nave (on the lateral arms, against the drum base)
    for (const sgn of [-1, 1]) {
      const a = ang + Math.PI / 2 + (sgn < 0 ? Math.PI : 0);
      const px = cx + Math.cos(a) * 6.8,
        py = cy + Math.sin(a) * 6.8;
      cyl(yellow, px, py, W, W + 2.0, 3.8, 3.8, 16);
      const pr = [];
      for (let i = 0; i <= 8; i++) {
        const t = (i / 8) * (Math.PI / 2);
        pr.push(new THREE.Vector2(Math.max(0.01, 3.8 * Math.cos(t)), W + 2.0 + 3.4 * Math.sin(t)));
      }
      const g = new THREE.LatheGeometry(pr, 16, Math.PI / 2, Math.PI).rotateX(Math.PI / 2);
      B.addGeometry(
        copper,
        g,
        new THREE.Matrix4().makeRotationZ(a - Math.PI / 2).setPosition(px, py, 0),
      );
      g.dispose();
    }
    return B.toGroup('st_sophia_cathedral_bayswater');
  },
};
