// Kingdom Street offices, Paddington Central: One Kingdom Street (Sheppard Robson, 2008),
// whose glass fins seem to change colour with the viewing angle; Two Kingdom Street (KPF),
// a 10-storey speculative office block with steel mullions fixed to full-height glazing;
// and Four Kingdom Street, the square 10-storey block approved in 2010 at the west end.
export default {
  id: 'kingdom_street_offices',
  name: 'One, Two and Four Kingdom Street',
  claims: [
    '69d17f41-0f43-4bab-bb52-23fcee721044',
    '8aea86f3-d0f3-4535-beb7-eb0d28d3728c',
    '29eb3704-9440-4cc8-8684-df40fcbe449c',
  ],
  references: [
    {
      title: 'Paddington Waterside - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Paddington_Waterside',
      used_for:
        'Two Kingdom Street (KPF) 10 storeys; Four Kingdom Street square 10-storey block approved 2010; One Kingdom Street by Sheppard Robson',
    },
    {
      title: '1 Kingdom Street - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/2000/1kingdom.html',
      used_for:
        '260,000 sq ft, 2008, Sheppard Robson; glass fins whose colour appears to shift with the viewing angle',
    },
    {
      title: 'Two Kingdom Street - RIBA Find an Architect (KPF)',
      url: 'https://find-an-architect.architecture.com/kpf-kohn-pedersen-fox-associates-int-pa/london/two-kingdom-street-',
      used_for: 'steel mullions fixed to full-height glazing panels giving a shimmering effect',
    },
    {
      title: 'Paddington Waterside - chrismrogers.net',
      url: 'https://www.chrismrogers.net/architecturepaddingtonwate1',
      used_for:
        'International Modernist treatment of narrow channelled mullions (Two Kingdom Street)',
    },
  ],
  notes:
    'Heights from storey counts at office storey height (~4 m): One KS 10 storeys (40 m), Two KS 10 storeys (40 m), Four KS 10 storeys (40 m); the Overture heights (20-33 m) look low. Dichroic fins are approximated by alternating tinted fin materials. Setbacks / roof plant are approximate.',
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
    const glass = kit.mat('#4b5f6c', { roughness: 0.08, metalness: 0.5 });
    const clear = kit.mat('#6f8794', { roughness: 0.06, metalness: 0.45 });
    const steel = kit.mat('#8f979c', { roughness: 0.35, metalness: 0.7 });
    const white = kit.mat('#e4e5e2', { roughness: 0.5 });
    const dark = kit.mat('dark_steel');
    const roofM = kit.mat('#8d8c88');
    const plant = (ring, z, w = 0.5, h = 3.2) => {
      const f = kit.ringFrame(ring);
      const p = rect(f.cx, f.cy, f.length * w, f.width * w, f.angle);
      prism(kit.mat('#a7a8a6'), p, z, z + h, roofM);
      for (const e of edgesOf(p)) {
        const n = Math.round(e.len / 0.7);
        for (let i = 1; i < n; i++)
          ebox(
            dark,
            e,
            (i * e.len) / n - 0.03,
            (i * e.len) / n + 0.03,
            0,
            0.08,
            z + 0.3,
            z + h - 0.3,
          );
      }
    };
    const base = (ring, z1) => {
      for (const e of edgesOf(ring)) {
        if (e.len < 0.3) continue;
        B.quad(
          dark,
          [e.a[0], e.a[1], 0],
          [e.b[0], e.b[1], 0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        ebox(clear, e, 0.2, e.len - 0.2, 0.01, 0.05, 0.1, z1 - 0.4);
        const n = Math.max(1, Math.round(e.len / 3));
        for (let i = 0; i <= n; i++)
          ebox(steel, e, (i * e.len) / n - 0.08, (i * e.len) / n + 0.08, 0, 0.2, 0, z1);
      }
    };

    // --- One Kingdom Street: colour-shifting glass fins -----------------------------
    {
      const ring = ringOf('69d17f41-0f43-4bab-bb52-23fcee721044');
      const ST = 4.0,
        H = 1.0 + 10 * ST;
      const tints = ['#7fa6b8', '#b48fb3', '#c9b77c', '#8fb39a'].map((c) =>
        kit.mat(c, { roughness: 0.1, metalness: 0.5, transparent: true, opacity: 0.85 }),
      );
      base(ring, 5.0);
      let fi = 0;
      for (const e of edgesOf(ring)) {
        if (e.len < 0.3) continue;
        B.quad(
          glass,
          [e.a[0], e.a[1], 5.0],
          [e.b[0], e.b[1], 5.0],
          [e.b[0], e.b[1], H],
          [e.a[0], e.a[1], H],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        for (let z = 5.0; z < H; z += ST) ebox(white, e, 0, e.len, 0, 0.3, z - 0.25, z + 0.15);
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let i = 0; i < n; i++) {
          const s = ((i + 0.5) * e.len) / n;
          ebox(tints[fi++ % 4], e, s - 0.03, s + 0.03, 0.1, 0.75, 5.0, H);
        }
      }
      kit.cornice(B, white, ring, H, { height: 0.8, projection: 0.8 });
      kit.cap(B, roofM, [[ring]], H + 0.8);
      plant(ring, H + 0.8, 0.45);
    }

    // --- Two Kingdom Street: deep channelled steel mullions --------------------------
    {
      const ring = ringOf('8aea86f3-d0f3-4535-beb7-eb0d28d3728c');
      const ST = 4.0,
        H = 1.0 + 10 * ST;
      base(ring, 5.0);
      for (const e of edgesOf(ring)) {
        if (e.len < 0.3) continue;
        B.quad(
          glass,
          [e.a[0], e.a[1], 5.0],
          [e.b[0], e.b[1], 5.0],
          [e.b[0], e.b[1], H - ST],
          [e.a[0], e.a[1], H - ST],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        if (e.len < 4) continue;
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let i = 0; i <= n; i++) {
          const s = (i * e.len) / n;
          ebox(steel, e, s - 0.06, s + 0.06, 0, 0.45, 5.0, H - ST);
          ebox(steel, e, s - 0.18, s + 0.18, 0.4, 0.5, 5.0, H - ST);
        }
        for (let z = 5.0 + ST; z < H - ST; z += ST) ebox(dark, e, 0, e.len, 0, 0.12, z - 0.35, z);
      }
      // recessed top storey (residential / penthouse floor) and roof blade
      const top = kit.offsetRing(
        ccw([
          [1342.7, 1442.4],
          [1343.2, 1494.6],
          [1268.2, 1479.4],
          [1260.5, 1464.7],
          [1260.5, 1443.5],
        ]),
        -2.5,
      );
      kit.cap(B, roofM, [[ring, top.slice().reverse()]], H - ST);
      kit.balustrade(B, steel, [...ring, ring[0]], H - ST, { height: 1.1, spacing: 2.0 });
      curtain(top, H - ST, H, {
        glass: clear,
        frame: steel,
        mull: 1.5,
        storey: ST,
        fin: 0.1,
        band: 0,
      });
      kit.cornice(B, white, top, H, { height: 0.6, projection: 1.6 });
      kit.cap(B, roofM, [[top]], H + 0.6);
      plant(top, H + 0.6, 0.4);
    }

    // --- Four Kingdom Street: square 10-storey block ---------------------------------
    {
      const ring = ringOf('29eb3704-9440-4cc8-8684-df40fcbe449c');
      const ST = 3.9,
        H = 1.0 + 10 * ST;
      base(ring, 5.0);
      for (const e of edgesOf(ring)) {
        if (e.len < 0.3) continue;
        B.quad(
          glass,
          [e.a[0], e.a[1], 5.0],
          [e.b[0], e.b[1], 5.0],
          [e.b[0], e.b[1], H],
          [e.a[0], e.a[1], H],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        const n = Math.max(1, Math.round(e.len / 3.0));
        for (let i = 0; i <= n; i++)
          ebox(white, e, (i * e.len) / n - 0.3, (i * e.len) / n + 0.3, 0, 0.6, 5.0, H);
        for (let z = 5.0; z <= H; z += ST) ebox(white, e, 0, e.len, 0, 0.55, z - 0.4, z + 0.2);
      }
      kit.cap(B, roofM, [[ring]], H + 0.2);
      plant(ring, H + 0.2, 0.4);
    }
    return B.toGroup('kingdom_street_offices');
  },
};
