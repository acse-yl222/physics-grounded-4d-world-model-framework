// Cassini, White City Living phase 3 (Patel Taylor for St James / Berkeley).
// 35-storey, 112 m residential tower with an undulating, curved plan: every floor
// is wrapped by continuous balconies that alternate between white precast
// concrete and laser-cut bronze metalwork, the curves shifting so the floors read
// as rippling bands. Faceted glazing behind, GRC/aluminium cladding, joined to a
// lower rectangular residential block with bolt-on steel balconies.
export default {
  id: 'cassini_tower',
  name: 'Cassini Tower, White City Living',
  claims: ['ce72c672-bebf-44f0-b062-79f7ed623d35'],
  references: [
    {
      title: 'Cassini Tower, White City Living Phase 3 - New London Architecture',
      url: 'https://nla.london/projects/cassini-tower-white-city-living-phase-3',
      used_for:
        'Patel Taylor; alternating white and patterned bronze wraparound balconies; precast concrete and laser-cut metal palette',
    },
    {
      title: 'White City, Cassini Tower - Interface Facades',
      url: 'https://www.interface-facades.com/?p=8123',
      used_for:
        '35 storeys / 112 m, undulating curved facade, alternating precast and laser-cut bronze balconies, faceted glazing, rectangular block with bolt-on balconies',
    },
    {
      title: 'Brogan Group - White City Phase 3',
      url: 'https://www.brogangroup.com/news/brogan-group-continue-temporary-works-at-white-city-phase-3/bp1315/',
      used_for: 'height 112 m, 35 storeys',
    },
  ],
  notes:
    'Tower plan is the curved part of the Overture outline, smoothed. The attached rectangular block is given 10 storeys (~33 m) as an estimate (the footprint carries the tower height for the whole outline). Balcony wave amplitude/phase is stylised.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const ring = buildings[0].polys[0][0];
    // Split: points north of the line between the two junction vertices form the block.
    const J0 = [-1464.8, 588.6],
      J1 = [-1447.5, 595.3];
    const near = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 0.5;
    const i0 = ring.findIndex((p) => near(p, J0)),
      i1 = ring.findIndex((p) => near(p, J1));
    const walk = (a, b) => {
      const out = [];
      for (let k = a; ; k = (k + 1) % ring.length) {
        out.push(ring[k]);
        if (k === b) break;
      }
      return out;
    };
    let tower = walk(i0, i1),
      block = walk(i1, i0);
    // Keep the one containing the southern curve as the tower.
    const minY = (r) => Math.min(...r.map((p) => p[1]));
    if (minY(tower) > minY(block)) [tower, block] = [block, tower];
    if (kit.ringArea(tower) < 0) tower.reverse();
    if (kit.ringArea(block) < 0) block.reverse();
    // Resample and smooth the tower outline.
    const resample = (r, n) => {
      const L = [];
      let tot = 0;
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length];
        L.push(tot);
        tot += Math.hypot(b[0] - a[0], b[1] - a[1]);
      }
      const out = [];
      let seg = 0;
      for (let j = 0; j < n; j++) {
        const t = (j / n) * tot;
        while (seg < r.length - 1 && L[seg + 1] <= t) seg++;
        const a = r[seg],
          b = r[(seg + 1) % r.length];
        const sl = (seg + 1 < r.length ? L[seg + 1] : tot) - L[seg];
        const f = sl > 0 ? (t - L[seg]) / sl : 0;
        out.push([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]);
      }
      return out;
    };
    let T = resample(tower, 72);
    for (let it = 0; it < 3; it++)
      T = T.map((p, k) => {
        const a = T[(k + T.length - 1) % T.length],
          b = T[(k + 1) % T.length];
        return [(a[0] + 2 * p[0] + b[0]) / 4, (a[1] + 2 * p[1] + b[1]) / 4];
      });
    let cx = 0,
      cy = 0;
    for (const p of T) {
      cx += p[0] / T.length;
      cy += p[1] / T.length;
    }

    const glassF = kit.paintedMaterial(
      'cassini:glass',
      256,
      256,
      (x, w, h) => {
        const gr = x.createLinearGradient(0, 0, 0, h);
        gr.addColorStop(0, '#4f6676');
        gr.addColorStop(1, '#2c3c48');
        x.fillStyle = gr;
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#b9bdbb';
        for (let k = 0; k < w; k += 32) x.fillRect(k, 0, 3, h);
        x.fillRect(0, 0, w, 10);
        x.fillStyle = 'rgba(230,225,210,0.35)';
        x.fillRect(5, 30, 20, 120);
        x.fillRect(101, 40, 24, 110);
      },
      DS,
    );
    const white = kit.mat('#ece9e1', { roughness: 0.6, side: THREE.DoubleSide });
    const bronze = kit.paintedMaterial(
      'cassini:bronze',
      256,
      64,
      (x, w, h) => {
        x.fillStyle = '#7d5a3a';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#a77d52';
        // Laser-cut leaf / lattice pattern.
        for (let k = 0; k < w; k += 16)
          for (let r = 6; r < h - 4; r += 14) {
            x.beginPath();
            x.ellipse(k + ((r / 14) % 2) * 8, r, 5, 3, 0.6, 0, Math.PI * 2);
            x.fill();
          }
        x.fillStyle = '#5c412a';
        x.fillRect(0, 0, w, 4);
      },
      { roughness: 0.45, metalness: 0.6, side: THREE.DoubleSide },
    );
    const soffit = kit.mat('#d9d6ce', DS);
    const dark = kit.mat('dark_steel', DS);

    const FL = 35,
      fh = 112 / FL;
    const ang = (p) => Math.atan2(p[1] - cy, p[0] - cx);
    // Perimeter lengths for UVs.
    const perim = (r) => {
      const out = [0];
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length];
        out.push(out[k] + Math.hypot(b[0] - a[0], b[1] - a[1]));
      }
      return out;
    };
    const band = (m, r, z0, z1, uScale, vRange = [0, 1]) => {
      const P = perim(r);
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length];
        batch.quad(
          m,
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [b[0], b[1], z1],
          [a[0], a[1], z1],
          [P[k] / uScale, vRange[0]],
          [P[k + 1] / uScale, vRange[0]],
          [P[k + 1] / uScale, vRange[1]],
          [P[k] / uScale, vRange[1]],
        );
      }
    };
    const core = kit.offsetRing(T, -1.6);
    // Double-height glazed lobby and the glazed core for the full height.
    band(glassF, core, 0, 112, 8, [0, 112 / 3.2]);
    for (let f = 1; f < FL; f++) {
      const z = f * fh;
      // Undulating slab edge: offset varies around the plan, phase shifts per floor.
      const slab = T.map((p) => {
        const t = ang(p);
        const d = -1.55 + 1.75 * (0.5 + 0.5 * Math.sin(2 * t + f * 0.55)) + 0.15;
        const ln = Math.hypot(p[0] - cx, p[1] - cy) || 1;
        return [p[0] + ((p[0] - cx) / ln) * d, p[1] + ((p[1] - cy) / ln) * d];
      });
      kit.cap(batch, soffit, [[slab]], z - 0.3, { down: true });
      kit.cap(batch, white, [[slab]], z);
      band(white, slab, z - 0.3, z, 30);
      // Balustrade: white precast and bronze laser-cut alternate floor by floor.
      if (f % 2) band(white, slab, z, z + 1.05, 30);
      else band(bronze, slab, z, z + 1.05, 4);
    }
    // Roof: parapet crown and plant screen.
    const top = kit.offsetRing(T, 0.2);
    kit.cap(batch, white, [[top]], 112);
    band(white, top, 111.6, 113.2, 30);
    const plant = kit.offsetRing(T, -6);
    band(bronze, plant, 112, 115.5, 4);
    kit.cap(batch, dark, [[plant]], 115.5);
    // Entrance canopy at ground level.
    band(white, kit.offsetRing(T, 0.6), 6.1, 6.6, 30);

    // Rectangular block: 10 storeys of cladding with bolt-on steel balconies.
    const BH = 33;
    kit.walls(batch, kit.facade('modern_clad', 2), [[block]], 0, BH, { bay: 3.4, storey: 3.3 });
    kit.cap(batch, kit.mat('concrete', DS), [[block]], BH);
    kit.walls(batch, white, [[kit.offsetRing(block, 0.15)]], BH, BH + 1);
    for (let k = 0; k < block.length; k++) {
      const a = block[k],
        b = block[(k + 1) % block.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 8) continue;
      const dx = (b[0] - a[0]) / len,
        dy = (b[1] - a[1]) / len;
      const nx = dy,
        ny = -dx; // outward for CCW ring
      const e = Math.atan2(dy, dx);
      for (let t = 3; t < len - 2.5; t += 6.8)
        for (let z = 3.3; z < BH - 1; z += 3.3) {
          const px = a[0] + dx * t + nx * 0.8,
            py = a[1] + dy * t + ny * 0.8;
          kit.box(batch, kit.mat('dark_steel', DS), px, py, z, 3.6, 1.5, 0.2, e);
          kit.box(
            batch,
            kit.mat('#9aa3a8', { transparent: true, opacity: 0.55, side: THREE.DoubleSide }),
            px + nx * 0.72,
            py + ny * 0.72,
            z + 0.2,
            3.6,
            0.06,
            1.0,
            e,
          );
        }
    }
    g.add(batch.toGroup('cassini_tower'));
    return g;
  },
};
