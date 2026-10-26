// 1 Wood Crescent, Television Centre, White City (Morris+Company with Arup for Stanhope,
// Mitsui Fudosan and AIMCo; Laing O'Rourke, 2021-23). Nine-storey, 112,000 sq ft office
// building on the west side of the Television Centre campus; PVH (Calvin Klein / Tommy
// Hilfiger) UK HQ on the top five floors. The curved east front follows Wood Crescent;
// the massing drops to six storeys on the crescent side and rises to nine on the west.
// ---- shared modelling helpers (inlined per module; no imports) -------------------
function mkHelpers(THREE, kit, batch, tag) {
  const H = {};
  H.ccw = (r) => {
    const q = r.slice();
    if (kit.ringArea(q) < 0) q.reverse();
    return q;
  };
  H.edges = (r, min = 0.05) =>
    r
      .map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return {
          k,
          a,
          b,
          len,
          dx: dx / len,
          dy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
          mid: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2],
        };
      })
      .filter((e) => e.len >= min);
  H.at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  H.ebox = (m, e, s0, s1, d0, d1, z0, z1, col) => {
    const c = H.at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(batch, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang, col);
  };
  H.quad = (m, p, q, z0, z1, u0 = 0, u1 = 1, v0 = 0, v1 = 1, col) =>
    batch.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0],
      [q[0], q[1], z1],
      [p[0], p[1], z1],
      [u0, v0],
      [u1, v0],
      [u1, v1],
      [u0, v1],
      col,
    );
  // Closed prism (walls + top cap; bottom optional).
  H.prism = (m, ring, z0, z1, { top = m, bottom = false, bay = 1e6, storey = 3.2, color } = {}) => {
    kit.walls(batch, m, [[ring]], z0, z1, { bay, storey, uvBase: z0, color });
    if (top) kit.cap(batch, top, [[ring]], z1, { color });
    if (bottom) kit.cap(batch, m, [[ring]], z0, { down: true, color });
  };
  // Box in a local frame (origin o, angle ang): centre (u, v), size (w, d), z0..z1.
  H.lbox = (m, o, ang, u, v, w, d, z0, z1, col) => {
    const c = Math.cos(ang),
      s = Math.sin(ang);
    kit.box(batch, m, o[0] + u * c - v * s, o[1] + u * s + v * c, z0, w, d, z1 - z0, ang, col);
  };
  H.cyl = (m, x, y, z0, h, r, seg = 16, r2 = r) => {
    const g = new THREE.CylinderGeometry(r2, r, h, seg).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z0 + h / 2));
    g.dispose();
  };
  H.lathe = (m, prof, x, y, z, seg = 24) => {
    const g = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(r, h)),
      seg,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, new THREE.Matrix4().makeTranslation(x, y, z));
    g.dispose();
  };
  // Glass seen from outside: one storey per texture tile (v), `w` metres per tile (u).
  H.glassMat = (
    key,
    {
      ceil = '#a5b0b5',
      top = '#5b6d78',
      mid = '#33444f',
      bot = '#3d505c',
      rough = 0.15,
      metal = 0.35,
      frames = 0,
      frameCol = '#555',
    } = {},
  ) =>
    kit.paintedMaterial(
      `${tag}:${key}`,
      128,
      128,
      (c, w, h) => {
        const g = c.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, ceil);
        g.addColorStop(0.12, top);
        g.addColorStop(0.55, mid);
        g.addColorStop(1, bot);
        c.fillStyle = g;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(220,230,240,0.08)';
        c.fillRect(w * 0.15, h * 0.2, w * 0.2, h * 0.75);
        if (frames) {
          c.fillStyle = frameCol;
          for (let k = 0; k < frames; k++) c.fillRect((k * w) / frames, 0, 3, h);
        }
      },
      { roughness: rough, metalness: metal },
    );
  // Brick / panel texture: `tile` metres square per repeat (use with H.tiled()).
  H.brickMat = (
    key,
    { base = '#8f4e3a', mortar = '#b9a99a', vary = 0.12, courses = 52, seed = 1 } = {},
  ) =>
    kit.paintedMaterial(
      `${tag}:${key}`,
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(seed);
        c.fillStyle = mortar;
        c.fillRect(0, 0, w, h);
        const bh = h / courses,
          bw = bh * 3.4;
        const col = new THREE.Color(base);
        for (let y = 0; y < courses; y++)
          for (let x = -1; x < w / bw + 1; x++) {
            const k = 1 + (r() - 0.5) * 2 * vary;
            c.fillStyle = '#' + col.clone().multiplyScalar(k).getHexString();
            c.fillRect((x + (y % 2) * 0.5) * bw + 0.6, y * bh + 0.6, bw - 1.2, bh - 1.2);
          }
      },
      { roughness: 0.9 },
    );
  // Walls with world-metre UVs: `tile` metres per texture repeat.
  H.tiled = (m, ring, z0, z1, tile = 4, color) =>
    kit.walls(batch, m, [[ring]], z0, z1, { bay: tile / 4, storey: tile / 2, uvBase: 0, color });
  H.tquad = (m, e, s0, s1, d, z0, z1, tile = 4, col) =>
    H.quad(
      m,
      H.at(e, s0, d),
      H.at(e, s1, d),
      z0,
      z1,
      s0 / tile,
      s1 / tile,
      z0 / tile,
      z1 / tile,
      col,
    );
  // Curtain wall: glass set back `set`, mullions every `mod`, slab bands every storey.
  H.curtain = (ring, z0, z1, o = {}) => {
    const {
      storey = 3.6,
      glass,
      mull = kit.mat('#4b5257', { roughness: 0.4, metalness: 0.5 }),
      mod = 1.5,
      set = 0.2,
      band = null, // material of slab-edge band
      bandH = 0.5,
      bandD = 0.15,
      transom = 0.9,
      skip = () => false,
      span = (e) => [0, e.len],
      mullD = 0.15,
    } = o;
    for (const e of H.edges(ring, 0.3)) {
      if (skip(e)) continue;
      const [s0, s1] = span(e);
      if (s1 - s0 < 0.3) continue;
      H.quad(
        glass,
        H.at(e, s0, -set),
        H.at(e, s1, -set),
        z0,
        z1,
        s0 / 3,
        s1 / 3,
        0,
        (z1 - z0) / storey,
      );
      const n = Math.max(1, Math.round((s1 - s0) / mod));
      if (mod < 50)
        for (let k = 0; k <= n; k++) {
          const s = s0 + ((s1 - s0) * k) / n;
          H.ebox(mull, e, s - 0.04, s + 0.04, -set, -set + mullD, z0, z1);
        }
      const ns = Math.round((z1 - z0) / storey);
      for (let k = 0; k <= ns; k++) {
        const z = z0 + k * storey;
        if (band && k > 0 && k <= ns)
          H.ebox(band, e, s0, s1, -set, bandD, z - bandH / 2, Math.min(z1, z + bandH / 2));
        if (transom && k < ns)
          H.ebox(mull, e, s0, s1, -set, -set + 0.08, z + transom, z + transom + 0.06);
      }
    }
  };
  // Ribbon facade: solid spandrel (wall material) + recessed glazing band per storey.
  H.ribbon = (ring, z0, nst, storey, o = {}) => {
    const {
      wall,
      glass,
      sp = 1.1, // spandrel height
      set = 0.25,
      mod = 1.5,
      mull = kit.mat('#3f454a', { roughness: 0.4, metalness: 0.5 }),
      skip = () => false,
      wallCol,
    } = o;
    for (const e of H.edges(ring, 0.3)) {
      if (skip(e)) continue;
      for (let k = 0; k < nst; k++) {
        const z = z0 + k * storey;
        H.ebox(wall, e, 0, e.len, -set, 0, z, z + sp, wallCol);
        H.quad(
          glass,
          H.at(e, 0, -set),
          H.at(e, e.len, -set),
          z + sp,
          z + storey,
          0,
          e.len / 3,
          0,
          1,
        );
        if (mod && e.len > mod) {
          const n = Math.max(1, Math.round(e.len / mod));
          for (let j = 1; j < n; j++) {
            const s = (e.len * j) / n;
            H.ebox(mull, e, s - 0.04, s + 0.04, -set, -set + 0.12, z + sp, z + storey);
          }
        }
      }
    }
  };
  // Punched windows in a wall (wall faces as tiled quads, simple boxed windows).
  H.punched = (ring, z0, nst, storey, o = {}) => {
    const {
      wall,
      tile = 4,
      winW = 1.4,
      winH = 1.8,
      sill = 0.9,
      bay = 3.0,
      margin = 0.8,
      glass = kit.mat('dark_glass'),
      frame = kit.mat('#d9d9d4'),
      reveal = 0.18,
      skip = () => false,
      pattern = null, // (e, k, j) => false to omit a window
      top = z0 + nst * storey,
      wallCol,
      surround = null,
    } = o;
    for (const e of H.edges(ring, 0.05)) {
      // wall face
      H.tquad(wall, e, 0, e.len, 0, 0, top, tile, wallCol);
      if (skip(e) || e.len < winW + 2 * margin * 0.5) continue;
      const usable = e.len - 2 * margin;
      const n = Math.max(1, Math.floor(usable / bay + 0.35));
      for (let k = 0; k < nst; k++) {
        const z = z0 + k * storey + sill;
        for (let j = 0; j < n; j++) {
          if (pattern && pattern(e, k, j, n) === false) continue;
          const s = margin + (usable * (j + 0.5)) / n;
          // glass + frame/sill proud of the wall plane
          H.ebox(glass, e, s - winW / 2, s + winW / 2, 0, 0.03, z, z + winH);
          H.ebox(frame, e, s - winW / 2 - 0.08, s + winW / 2 + 0.08, 0, reveal, z - 0.1, z);
          H.ebox(frame, e, s - winW / 2 - 0.08, s - winW / 2, 0, reveal * 0.6, z, z + winH);
          H.ebox(frame, e, s + winW / 2, s + winW / 2 + 0.08, 0, reveal * 0.6, z, z + winH);
          H.ebox(
            frame,
            e,
            s - winW / 2 - 0.08,
            s + winW / 2 + 0.08,
            0,
            reveal * 0.6,
            z + winH,
            z + winH + 0.08,
          );
          if (surround) {
            H.ebox(surround, e, s - winW / 2 - 0.2, s - winW / 2 - 0.08, 0, 0.1, z, z + winH);
            H.ebox(surround, e, s + winW / 2 + 0.08, s + winW / 2 + 0.2, 0, 0.1, z, z + winH);
            H.ebox(
              surround,
              e,
              s - winW / 2 - 0.2,
              s + winW / 2 + 0.2,
              0,
              0.1,
              z + winH + 0.08,
              z + winH + 0.2,
            );
          }
        }
      }
    }
  };
  // Flat roof with parapet and coping.
  H.roof = (
    ring,
    z,
    { parapet = 1.0, wall, roof = kit.mat('#8e8f8b'), coping = null, inset = 0.35 } = {},
  ) => {
    kit.cap(batch, roof, [[ring]], z);
    if (parapet > 0) {
      const inner = kit.offsetRing(ring, -inset);
      kit.walls(batch, wall, [[ring]], z, z + parapet, { bay: 1e6 });
      kit.walls(batch, wall, [[inner.slice().reverse()]], z, z + parapet, { bay: 1e6 });
      kit.cap(batch, coping || wall, [[ring, inner.slice().reverse()]], z + parapet);
    }
  };
  // Rooftop plant enclosure with louvre stripes.
  H.plant = (
    ring,
    z,
    h,
    {
      mat = kit.mat('#8a8d8e'),
      louvre = kit.mat('#a7aaab', { metalness: 0.3, roughness: 0.6 }),
      pitch = 0.35,
    } = {},
  ) => {
    if (kit.ringArea(ring) < 4) return;
    H.prism(mat, ring, z, z + h);
    for (const e of H.edges(ring, 1)) {
      for (let zz = z + 0.3; zz < z + h - 0.2; zz += pitch)
        H.ebox(louvre, e, 0.1, e.len - 0.1, 0, 0.06, zz, zz + 0.06);
    }
  };
  // Painted text sign material.
  H.signMat = (
    key,
    text,
    {
      w = 512,
      h = 96,
      bg = '#ffffff',
      fg = '#111111',
      font = 'bold 56px sans-serif',
      transparent = false,
    } = {},
  ) =>
    kit.paintedMaterial(
      `${tag}:${key}`,
      w,
      h,
      (c, W, Hh) => {
        if (!transparent) {
          c.fillStyle = bg;
          c.fillRect(0, 0, W, Hh);
        }
        c.fillStyle = fg;
        c.font = font;
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText(text, W / 2, Hh / 2 + 2);
      },
      { roughness: 0.6, transparent },
    );
  H.sign = (m, e, sm, width, d, z0, z1) =>
    H.quad(m, H.at(e, sm - width / 2, d), H.at(e, sm + width / 2, d), z0, z1);
  // Longest edges first.
  H.byLen = (ring) => H.edges(ring).sort((p, q) => q.len - p.len);
  // Edge whose outward normal best matches a direction (radians from east).
  H.facing = (ring, dir, min = 3) => {
    let best = null,
      bd = -2;
    for (const e of H.edges(ring, min)) {
      const d = e.nx * Math.cos(dir) + e.ny * Math.sin(dir);
      if (d * Math.sqrt(e.len) > bd) {
        bd = d * Math.sqrt(e.len);
        best = e;
      }
    }
    return best;
  };
  H.dirOf = (e) => Math.atan2(e.ny, e.nx);
  // Straight member between two 3D points with a w x d cross-section.
  H.beam = (m, A, B, w = 0.4, d = 0.4) => {
    const a = new THREE.Vector3(...A),
      b = new THREE.Vector3(...B);
    const dir = b.clone().sub(a);
    const len = dir.length();
    if (len < 1e-3) return;
    const geo = new THREE.BoxGeometry(len, w, d);
    const q = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(1, 0, 0),
      dir.normalize(),
    );
    const mm = new THREE.Matrix4().compose(
      a.clone().add(b).multiplyScalar(0.5),
      q,
      new THREE.Vector3(1, 1, 1),
    );
    batch.addGeometry(m, geo, mm);
    geo.dispose();
  };
  // Clip ring to the band u0 <= (p . (ux, uy)) <= u1.
  H.clipBand = (ring, ux, uy, u0, u1) => {
    const clip = (r, sx, sy, c) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const p = r[k],
          q = r[(k + 1) % r.length];
        const dp = sx * p[0] + sy * p[1] - c,
          dq = sx * q[0] + sy * q[1] - c;
        if (dp <= 0) out.push(p);
        if (dp * dq < 0) {
          const t = dp / (dp - dq);
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
      }
      return out;
    };
    return clip(clip(ring, ux, uy, u1), -ux, -uy, -u0);
  };
  // Saw-tooth (north-light) roof over `ring` at zt: teeth of width `period` across the
  // direction `dir` (unit vector of increasing v); each tooth rises by `rise` towards +v and
  // ends in a vertical glazed face looking along +v.
  H.sawtooth = (ring, dir, zt, period, rise, { roof, glass, wall }) => {
    const vx = Math.cos(dir),
      vy = Math.sin(dir);
    const vOf = (p) => p[0] * vx + p[1] * vy;
    let v0 = Infinity,
      v1 = -Infinity;
    for (const p of ring) {
      v0 = Math.min(v0, vOf(p));
      v1 = Math.max(v1, vOf(p));
    }
    const n = Math.max(1, Math.round((v1 - v0) / period));
    const P = (v1 - v0) / n;
    for (let k = 0; k < n; k++) {
      const a = v0 + k * P,
        b = a + P;
      const strip = H.clipBand(ring, vx, vy, a, b);
      if (strip.length < 3) continue;
      const sr = H.ccw(strip);
      const z = (p) => zt + (rise * (vOf(p) - a)) / P;
      let tris;
      try {
        tris = THREE.ShapeUtils.triangulateShape(
          sr.map(([x, y]) => new THREE.Vector2(x, y)),
          [],
        );
      } catch {
        continue;
      }
      batch.add(
        roof,
        sr.map((p) => [p[0], p[1], z(p)]),
        sr.map((p) => [p[0] / 3, p[1] / 3]),
        tris.flat(),
      );
      for (let i = 0; i < sr.length; i++) {
        const p = sr[i],
          q = sr[(i + 1) % sr.length];
        const onA = Math.abs(vOf(p) - a) < 1e-3 && Math.abs(vOf(q) - a) < 1e-3;
        const onB = Math.abs(vOf(p) - b) < 1e-3 && Math.abs(vOf(q) - b) < 1e-3;
        if (onA) continue;
        if (onB) {
          H.quad(glass, p, q, zt, zt + rise, 0, Math.hypot(q[0] - p[0], q[1] - p[1]) / 3, 0, 1);
          continue;
        }
        batch.add(
          wall,
          [
            [p[0], p[1], zt],
            [q[0], q[1], zt],
            [q[0], q[1], z(q)],
            [p[0], p[1], z(p)],
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
    }
  };
  // Drop vertices whose triangle with their neighbours is smaller than minArea (m2).
  H.simplify = (ring, minArea = 1) => {
    let r = ring.slice();
    for (let guard = 0; guard < 1000 && r.length > 3; guard++) {
      let best = -1,
        ba = Infinity;
      for (let i = 0; i < r.length; i++) {
        const a = r[(i - 1 + r.length) % r.length],
          b = r[i],
          c = r[(i + 1) % r.length];
        const ar = Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2;
        if (ar < ba) {
          ba = ar;
          best = i;
        }
      }
      if (ba >= minArea) break;
      r.splice(best, 1);
    }
    return r;
  };
  // Folded roof over the real footprint: z = f(v) piecewise linear along direction `dir`
  // (profile [[v, z], ...] in metres along dir, sorted); walls from z0 up to the roof line.
  H.foldRoof = (ring, dir, profile, z0, { roof, wall, wallTile = 4 }) => {
    const vx = Math.cos(dir),
      vy = Math.sin(dir);
    const vOf = (p) => p[0] * vx + p[1] * vy;
    const f = (v) => {
      if (v <= profile[0][0]) return profile[0][1];
      for (let k = 1; k < profile.length; k++)
        if (v <= profile[k][0] + 1e-9) {
          const [a, za] = profile[k - 1],
            [b, zb] = profile[k];
          return za + ((zb - za) * (v - a)) / (b - a || 1);
        }
      return profile[profile.length - 1][1];
    };
    for (const e of H.edges(ring, 0.05)) {
      const va = vOf(e.a),
        vb = vOf(e.b);
      const ss = [0, e.len];
      for (const [v] of profile) {
        const t = (v - va) / (vb - va || 1e-9);
        if (t > 1e-3 && t < 1 - 1e-3) ss.push(t * e.len);
      }
      ss.sort((a, b) => a - b);
      for (let k = 1; k < ss.length; k++) {
        const p = H.at(e, ss[k - 1]),
          q = H.at(e, ss[k]);
        const zp = f(vOf(p)),
          zq = f(vOf(q));
        batch.add(
          wall,
          [
            [p[0], p[1], z0],
            [q[0], q[1], z0],
            [q[0], q[1], zq],
            [p[0], p[1], zp],
          ],
          [
            [ss[k - 1] / wallTile, z0 / wallTile],
            [ss[k] / wallTile, z0 / wallTile],
            [ss[k] / wallTile, zq / wallTile],
            [ss[k - 1] / wallTile, zp / wallTile],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      }
    }
    for (let k = 1; k < profile.length; k++) {
      const strip = H.clipBand(ring, vx, vy, profile[k - 1][0], profile[k][0]);
      if (strip.length < 3) continue;
      const sr = H.ccw(strip);
      let tris;
      try {
        tris = THREE.ShapeUtils.triangulateShape(
          sr.map(([x, y]) => new THREE.Vector2(x, y)),
          [],
        );
      } catch {
        continue;
      }
      batch.add(
        roof,
        sr.map((p) => [p[0], p[1], f(vOf(p)) + 0.02]),
        sr.map((p) => [p[0] / 4, p[1] / 4]),
        tris.flat(),
      );
    }
    return f;
  };
  return H;
}

export default {
  id: 'one_wood_crescent',
  name: '1 Wood Crescent',
  claims: ['77563a15-968a-474e-9dc6-e463ebd28b3a'],
  references: [
    {
      title: '1 Wood Crescent completed at Television Centre - Stanhope',
      url: 'https://www.stanhopeplc.com/latest/1-wood-crescent-completed-at-television-centre',
      used_for:
        "nine storeys, 112,247 sq ft, west side of the Television Centre campus, Morris+Company / Arup / Laing O'Rourke",
    },
    {
      title: "1 Wood Crescent tops out - Laing O'Rourke",
      url: 'https://laingorourke.com/company/news/2022/1-wood-crescent-tops-out',
      used_for: 'construction from March 2021, topped out May 2022',
    },
    {
      title: 'White City scheme designed by Morris + Company - Building',
      url: 'https://building.co.uk/news/laing-orourke-to-start-work-on-calvin-kleins-new-uk-hq/5110982.article',
      used_for: 'PVH / Calvin Klein UK HQ; architect Morris+Company',
    },
  ],
  notes:
    'Storey split 4.5 m ground + 3.8 m upper floors gives 35 m for nine storeys, matching the ' +
    'Overture part heights (24 m crescent wing = six storeys, 35 m west block). The facade - a ' +
    'grid of terracotta-red precast piers and spandrels with deep reveals, bronze window frames and ' +
    'a recessed double-height ground floor - and the roof terrace on the six-storey wing are ' +
    'assumptions; no photographs or facade descriptions were available.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const H = mkHelpers(THREE, kit, batch, 'one_wood_crescent');
    const b = buildings[0];
    const ring = H.ccw(b.polys[0][0]);
    const parts = (b.parts || []).slice().sort((p, q) => p.h - q.h);
    const tall = parts.length > 1 ? H.ccw(parts[parts.length - 1].polys[0][0]) : null;
    const G = 4.5,
      ST = 3.8;
    const glass = H.glassMat('glass', {
      ceil: '#c2c4bf',
      top: '#6f7f86',
      mid: '#36454f',
      bot: '#45535c',
    });
    const pier = kit.mat('#a9573f', { roughness: 0.75 });
    const pierLt = kit.mat('#b86a50', { roughness: 0.75 });
    const bronze = kit.mat('#5d4a37', { roughness: 0.4, metalness: 0.6 });
    const darkGlass = kit.mat('#25313a', { roughness: 0.1, metalness: 0.4 });
    const roofM = kit.mat('#8e8f8b');
    const green = kit.mat('foliage');

    const facade = (r, z0, nst, skip = () => false) => {
      const zt = z0 + nst * ST;
      for (const e of H.edges(r, 0.5)) {
        if (skip(e)) continue;
        H.quad(glass, H.at(e, 0, -0.5), H.at(e, e.len, -0.5), z0, zt, 0, e.len / 3, 0, nst);
        const nb = Math.max(1, Math.round(e.len / 3.0));
        for (let k = 0; k <= nb; k++) {
          const s = (k * e.len) / nb;
          H.ebox(k % 2 ? pierLt : pier, e, s - 0.32, s + 0.32, -0.5, 0.15, z0, zt); // piers
          if (k < nb) {
            const s2 = ((k + 1) * e.len) / nb;
            H.ebox(bronze, e, (s + s2) / 2 - 0.04, (s + s2) / 2 + 0.04, -0.5, -0.38, z0, zt);
          }
        }
        for (let f = 0; f <= nst; f++)
          H.ebox(pier, e, 0, e.len, -0.5, 0.1, z0 + f * ST - 0.55, z0 + f * ST + 0.05);
        for (let f = 0; f < nst; f++)
          H.ebox(bronze, e, 0, e.len, -0.5, -0.4, z0 + f * ST + 1.0, z0 + f * ST + 1.08);
      }
    };
    // ground floor: recessed double-height glazing behind the pier line
    for (const e of H.edges(kit.offsetRing(ring, -1.2), 0.5)) {
      H.quad(darkGlass, e.a, e.b, 0, G, 0, e.len / 3);
      const n = Math.max(1, Math.round(e.len / 3));
      for (let k = 0; k <= n; k++)
        H.ebox(bronze, e, (k * e.len) / n - 0.06, (k * e.len) / n + 0.06, 0, 0.15, 0, G);
    }
    for (const e of H.edges(ring, 2)) {
      const n = Math.max(1, Math.round(e.len / 6));
      for (let k = 0; k <= n; k++) {
        const s = Math.min(e.len - 0.35, Math.max(0.35, (k * e.len) / n));
        H.ebox(pier, e, s - 0.35, s + 0.35, -0.5, 0.15, 0, G);
      }
    }
    kit.cap(batch, pier, [[ring]], G - 0.01, { down: true });
    // six-storey wing (whole footprint) and nine-storey west block
    facade(ring, G, 5, (e) => false);
    const z6 = G + 5 * ST;
    H.roof(ring, z6, { parapet: 1.1, wall: pier, roof: roofM });
    // roof terrace planting on the crescent wing
    const terr = kit.offsetRing(ring, -3);
    for (const e of H.edges(terr, 6)) H.ebox(green, e, 1, e.len - 1, -1.2, 0, z6, z6 + 0.6);
    if (tall) {
      const t = kit.offsetRing(tall, -0.2);
      facade(t, z6, 3);
      const z9 = z6 + 3 * ST;
      H.roof(t, z9, { parapet: 1.2, wall: pier, roof: roofM });
      const pr = kit.offsetRing(t, -6);
      if (kit.ringArea(pr) > 30) H.plant(H.ccw(pr), z9, 2.8, { mat: kit.mat('#6f6c68') });
    }
    // entrance and name on the crescent (curved east) face
    const ce = H.facing(ring, 0, 10);
    H.ebox(bronze, ce, ce.len / 2 - 5, ce.len / 2 + 5, -1.2, 1.6, G - 0.4, G);
    const sign = H.signMat('sign', '1 WOOD CRESCENT', {
      bg: '#5d4a37',
      fg: '#efe7da',
      font: 'bold 52px sans-serif',
    });
    H.sign(sign, ce, ce.len / 2, 7, 1.62, G - 0.38, G - 0.02);
    g.add(batch.toGroup('one_wood_crescent'));
    return g;
  },
};
