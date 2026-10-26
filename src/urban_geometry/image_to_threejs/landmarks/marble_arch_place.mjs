// Marble Arch Place, Edgware Road / Bryanston Street (Rafael Viñoly Architects for
// Almacantar, completed 2021), on the site of the 1960s Marble Arch Tower (T. P. Bennett,
// 23 storeys, demolished). Two buildings in Portland-stone-faced precast with deep reveals
// and curved glass: The Bryanston, an 18-storey residential tower rising from a podium of
// curved terraces, and a 7-storey office building crowned by pre-stressed stone columns on
// its upper terrace, facing Marble Arch.
export default {
  id: 'marble_arch_place',
  name: 'Marble Arch Place (The Bryanston)',
  claims: ['6a24a710-3171-48f9-b037-d257df1c9f1b', 'ce690736-73de-46db-8733-8bbb73c6de23'],
  references: [
    {
      title: 'Marble Arch Place construction update - Rafael Viñoly Architects',
      url: 'https://vinoly.com/article/marble-arch-place-construction-update/',
      used_for:
        '18-storey residential tower (54 flats) and 7-storey commercial building, variable massing',
    },
    {
      title:
        "The Bryanston: Rafael Viñoly's Hyde Park residential development completes - Knight Frank",
      url: 'https://www.knightfrank.co.uk/blog/2021/12/16/the-bryanston-rafael-vinolys-iconic-hyde-park-residential-development-completes',
      used_for:
        'podium with curved terraces and the tower; curved full-height windows towards Hyde Park',
    },
    {
      title: 'Marble Arch Place - Interface Facades',
      url: 'https://interface-facades.com/?p=5664',
      used_for:
        'Portland stone facades of 3D precast units with deep reveals and curved elevations; office crown of pre-stressed stone columns on the upper terrace',
    },
    {
      title: 'Marble Arch Place - FMDC',
      url: 'https://fmdc.co.uk/marble-arch-place',
      used_for: 'about 850 stone-faced precast units and curved glass curtain walling',
    },
    {
      title: 'Marble Arch Tower - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1960/marblearch.html',
      used_for: 'the former 82 m Marble Arch Tower (1962-66) on the site',
    },
  ],
  notes:
    'Massing from the Overture parts (tower 64.8 m; podium terraces 23-36 m; office 26-33 m). Storey heights, the rhythm of stone fins and the terrace balustrades are approximate; the column crown of the office is shown as a colonnade on the top terrace.',
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
    const stone = kit.mat('#e3dccb', { roughness: 0.75 });
    const glass = kit.mat('#5b707d', { roughness: 0.06, metalness: 0.5 });
    const clear = kit.mat('#8ea4b0', {
      roughness: 0.05,
      metalness: 0.35,
      transparent: true,
      opacity: 0.6,
    });
    const roofM = kit.mat('#8d8c88');
    const near = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 0.08;
    const onRing = (p, r) => r.some((q) => near(p, q));
    const buildParts = (b, opts) => {
      const parts = (b.parts && b.parts.length ? b.parts : [{ polys: b.polys, h: b.h }])
        .map((p) => ({ ring: ccw(p.polys[0][0]), h: p.h }))
        .sort((a, c) => a.h - c.h);
      parts.forEach((p, i) => {
        const taller = parts.slice(i + 1);
        const ST = opts.storey;
        for (const e of edgesOf(p.ring)) {
          if (e.len < 0.15) continue;
          // the full-height wall belongs to the tallest part sharing this edge
          if (taller.some((t) => onRing(e.a, t.ring) && onRing(e.b, t.ring))) continue;
          // lower parts sharing this edge were skipped, so this wall runs from the ground
          const z0 = 0;
          B.quad(
            glass,
            [e.a[0], e.a[1], z0],
            [e.b[0], e.b[1], z0],
            [e.b[0], e.b[1], p.h],
            [e.a[0], e.a[1], p.h],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
          // stone floor edges (deep reveals) and vertical stone fins
          for (let z = Math.ceil((z0 + 0.01) / ST) * ST; z <= p.h - 0.4; z += ST)
            ebox(stone, e, 0, e.len, 0, opts.slab, z - 0.45, z + 0.25);
          const n = Math.max(1, Math.round(e.len / opts.fin));
          for (let k = 0; k < n; k++)
            ebox(
              stone,
              e,
              (k * e.len) / n - 0.14,
              (k * e.len) / n + 0.14,
              0,
              opts.slab * 0.8,
              z0,
              p.h,
            );
          if (opts.terrace)
            for (let z = Math.ceil((z0 + 0.01) / ST) * ST; z <= p.h - 0.4; z += ST)
              ebox(clear, e, 0, e.len, opts.slab - 0.06, opts.slab, z + 0.25, z + 1.3);
        }
        kit.cap(B, roofM, [[p.ring]], p.h);
        kit.cornice(B, stone, p.ring, p.h - 0.2, { height: 0.6, projection: 0.4 });
      });
      return parts;
    };
    // The Bryanston: curved terraces on the podium and tower (balconies with glass rails)
    const res = ctx.byId['6a24a710-3171-48f9-b037-d257df1c9f1b'];
    const rp = buildParts(res, { storey: 3.45, slab: 1.3, fin: 2.2, terrace: true });
    const tw = rp[rp.length - 1];
    {
      const f = kit.ringFrame(tw.ring);
      prism(
        stone,
        rect(f.cx, f.cy, f.length * 0.45, f.width * 0.45, f.angle),
        tw.h,
        tw.h + 3.0,
        roofM,
      );
    }
    // office: stone grid, top terrace with a crown of stone columns
    const off = ctx.byId['ce690736-73de-46db-8733-8bbb73c6de23'];
    const op = buildParts(off, { storey: 4.0, slab: 0.7, fin: 1.6, terrace: false });
    const top = op[op.length - 1];
    {
      const inner = kit.offsetRing(top.ring, -1.5);
      for (const e of edgesOf(inner)) {
        if (e.len < 1.2) continue;
        const n = Math.max(1, Math.round(e.len / 2.4));
        for (let k = 0; k < n; k++) {
          const p = at(e, (k + 0.5) * (e.len / n));
          cyl(stone, p[0], p[1], top.h, top.h + 4.2, 0.32, 0.32, 8);
        }
      }
      const blade = kit.offsetRing(top.ring, -0.6);
      prism(stone, blade, top.h + 4.2, top.h + 5.0, roofM);
      curtain(kit.offsetRing(top.ring, -4.0), top.h, top.h + 4.0, {
        glass,
        frame: stone,
        mull: 2.0,
        band: 0,
      });
    }
    return B.toGroup('marble_arch_place');
  },
};
