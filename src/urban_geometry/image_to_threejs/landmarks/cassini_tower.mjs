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
        'Patel Taylor; alternating white and patterned bronze wraparound balconies; precast concrete and laser-cut metal palette; balconies re-join into a soft D-shaped plan tapering back towards the apex',
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
    'Tower plan is the curved part of the Overture outline, smoothed; floors 25-35 are inset by up to 2.4 m to suggest the taper towards the apex (amount assumed). The attached rectangular block is given 10 storeys (~33 m) as an estimate (the footprint carries the tower height for the whole outline). Balcony wave amplitude/phase, mullion pitch, the double-height lobby, the bronze-finned plant screen and maintenance gantry on the roof, and the landscaped podium (trees, benches) are stylised.',
  build({ THREE, kit, buildings, placeAssets }) {
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
    // Upper floors taper back towards the apex (the balconies re-join into a
    // softer D-shaped plan).
    const inset = (f) => (f > 24 ? ((f - 24) / (FL - 24)) * 2.4 : 0);
    const mullion = kit.mat('#aeb3b3', { roughness: 0.4, metalness: 0.6 });
    const rail = kit.mat('#5c412a', { roughness: 0.45, metalness: 0.6 });
    const lobbyGlass = kit.mat('#6d8796', { roughness: 0.08, metalness: 0.3 });
    const ringAt = (f) => (inset(f) > 0 ? kit.offsetRing(T, -inset(f)) : T);
    // Glazed core, floor by floor, with faceted mullions at every facet joint.
    for (let f = 0; f < FL; f++) {
      const z0 = f * fh,
        z1 = (f + 1) * fh;
      const core = kit.offsetRing(ringAt(f), -1.6);
      if (f < 2) {
        // Double-height lobby: taller glass with heavier mullions.
        if (f === 0) {
          band(lobbyGlass, core, 0, 2 * fh, 8, [0, 1]);
          for (let k = 0; k < core.length; k += 2)
            kit.box(batch, mullion, core[k][0], core[k][1], 0, 0.18, 0.18, 2 * fh, 0);
        }
        continue;
      }
      band(glassF, core, z0, z1, 8, [0, 1]);
      for (let k = 0; k < core.length; k += 1)
        kit.box(
          batch,
          mullion,
          core[k][0],
          core[k][1],
          z0,
          0.08,
          0.08,
          fh - 0.3,
          ang(core[k]) + Math.PI / 2,
        );
    }
    // Revolving door drum and entrance canopy on the park (south) side.
    {
      let best = T[0];
      for (const p of T) if (p[1] < best[1]) best = p;
      const dx = best[0] - cx,
        dy = best[1] - cy,
        dl = Math.hypot(dx, dy);
      const ex = cx + (dx / dl) * (dl - 1.1),
        ey = cy + (dy / dl) * (dl - 1.1);
      const drum = new THREE.CylinderGeometry(1.4, 1.4, 2.6, 16, 1, true).rotateX(Math.PI / 2);
      batch.addGeometry(lobbyGlass, drum, new THREE.Matrix4().makeTranslation(ex, ey, 1.3));
      drum.dispose();
      kit.box(
        batch,
        white,
        ex + (dx / dl) * 1.8,
        ey + (dy / dl) * 1.8,
        5.2,
        9,
        5,
        0.4,
        Math.atan2(dy, dx) + Math.PI / 2,
      );
    }
    for (let f = 2; f < FL; f++) {
      const z = f * fh;
      // Undulating slab edge: offset varies around the plan, phase shifts per floor.
      const Tf = ringAt(f);
      const slab = Tf.map((p) => {
        const t = ang(p);
        const d = -1.55 + 1.75 * (0.5 + 0.5 * Math.sin(2 * t + f * 0.55)) + 0.15;
        const ln = Math.hypot(p[0] - cx, p[1] - cy) || 1;
        return [p[0] + ((p[0] - cx) / ln) * d, p[1] + ((p[1] - cy) / ln) * d];
      });
      const inner = kit.offsetRing(slab, -0.18);
      kit.cap(batch, soffit, [[slab]], z - 0.3, { down: true });
      kit.cap(batch, white, [[slab]], z);
      band(white, slab, z - 0.3, z, 30);
      // Balustrade: white precast and bronze laser-cut alternate floor by floor,
      // given a real thickness and a capping rail.
      const bronzeFloor = f % 2 === 0;
      band(bronzeFloor ? bronze : white, slab, z, z + 1.05, bronzeFloor ? 4 : 30);
      band(bronzeFloor ? bronze : white, inner, z, z + 1.05, bronzeFloor ? 4 : 30);
      kit.cap(
        batch,
        bronzeFloor ? rail : white,
        [[slab, inner.slice().reverse()]],
        z + (bronzeFloor ? 1.1 : 1.05),
      );
      if (bronzeFloor) band(rail, slab, z + 1.05, z + 1.1, 30);
    }
    // Roof: parapet crown and plant enclosure behind vertical bronze fins.
    const top = kit.offsetRing(ringAt(FL), 0.2);
    kit.cap(batch, white, [[top]], 112);
    band(white, top, 111.6, 113.2, 30);
    band(white, kit.offsetRing(top, -0.25), 112, 113.2, 30);
    kit.cap(batch, white, [[top, kit.offsetRing(top, -0.25).slice().reverse()]], 113.2);
    const plant = kit.offsetRing(ringAt(FL), -6);
    band(kit.mat('#3b3f42', DS), plant, 112, 115.2, 6);
    {
      const P = perim(plant);
      const tot = P[P.length - 1];
      for (let s0 = 0; s0 < tot; s0 += 0.9) {
        let k = 0;
        while (k < plant.length - 1 && P[k + 1] < s0) k++;
        const a = plant[k],
          b = plant[(k + 1) % plant.length];
        const t = (s0 - P[k]) / (P[k + 1] - P[k] || 1);
        const x = a[0] + (b[0] - a[0]) * t,
          y = a[1] + (b[1] - a[1]) * t;
        const ex = x + ((x - cx) / (Math.hypot(x - cx, y - cy) || 1)) * 0.25,
          ey = y + ((y - cy) / (Math.hypot(x - cx, y - cy) || 1)) * 0.25;
        kit.box(batch, rail, ex, ey, 112, 0.08, 0.45, 3.8, ang([x, y]));
      }
    }
    kit.cap(batch, dark, [[plant]], 115.2);
    // Building maintenance unit (cleaning cradle gantry) on the roof.
    kit.box(batch, kit.mat('white_steel'), cx, cy, 115.2, 2.2, 2.2, 1.6, 0);
    kit.box(batch, kit.mat('white_steel'), cx + 3, cy, 116.8, 9, 0.6, 0.6, 0.3);
    // Entrance canopy ring at the top of the lobby.
    band(white, kit.offsetRing(T, 0.6), 6.1, 6.6, 30);
    kit.cap(
      batch,
      white,
      [[kit.offsetRing(T, 0.6), kit.offsetRing(T, -1.6).slice().reverse()]],
      6.6,
    );
    kit.cap(
      batch,
      soffit,
      [[kit.offsetRing(T, 0.6), kit.offsetRing(T, -1.6).slice().reverse()]],
      6.1,
      { down: true },
    );

    // Rectangular block: 10 storeys of GRC panels with framed windows and
    // bolt-on steel balconies.
    const BH = 33;
    const grc = kit.paintedMaterial(
      'cassini:grc',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#d9d3c6';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(0,0,0,0.08)';
        for (let k = 0; k < w; k += 64) x.fillRect(k, 0, 2, h);
        for (let k = 0; k < h; k += 85) x.fillRect(0, k, w, 2);
      },
      DS,
    );
    {
      const P = perim(block);
      for (let k = 0; k < block.length; k++) {
        const a = block[k],
          b = block[(k + 1) % block.length];
        batch.quad(
          grc,
          [a[0], a[1], 0],
          [b[0], b[1], 0],
          [b[0], b[1], BH],
          [a[0], a[1], BH],
          [P[k] / 4, 0],
          [P[k + 1] / 4, 0],
          [P[k + 1] / 4, BH / 4],
          [P[k] / 4, BH / 4],
        );
      }
    }
    const junction = (k) => {
      const a = block[k],
        b = block[(k + 1) % block.length];
      return (near(a, J0) || near(a, J1)) && (near(b, J0) || near(b, J1));
    };
    kit.windowGrid(batch, block, 0.9, 10, 3.3, (s, k) => ({
      count: junction(k) ? 0 : undefined,
      glass: kit.mat('dark_glass'),
      frame: kit.mat('#4a4d4f', { roughness: 0.5, metalness: 0.4 }),
      sill: kit.mat('#c9c2b3'),
      bay: 3.4,
      width: s === 0 ? 2.6 : 1.7,
      height: s === 0 ? 2.6 : 2.2,
      margin: 1.0,
      head: 'none',
      bars: 1,
      depth: 0.15,
    }));
    kit.cap(batch, kit.mat('concrete', DS), [[block]], BH);
    kit.walls(batch, white, [[kit.offsetRing(block, 0.15)]], BH, BH + 1);
    kit.cornice(batch, white, block, 3.2, { height: 0.35, projection: 0.12 });
    for (let k = 0; k < block.length; k++) {
      const a = block[k],
        b = block[(k + 1) % block.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 8 || junction(k)) continue;
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
          kit.box(
            batch,
            kit.mat('dark_steel', DS),
            px + nx * 0.72,
            py + ny * 0.72,
            z + 1.15,
            3.6,
            0.08,
            0.06,
            e,
          );
          // Hanger rods back to the wall.
          for (const sg of [-1, 1])
            kit.box(
              batch,
              kit.mat('dark_steel', DS),
              px + dx * sg * 1.7,
              py + dy * sg * 1.7,
              z + 0.2,
              0.05,
              1.5,
              0.05,
              e,
            );
        }
    }

    // Landscaped podium around the base: paving, trees and benches.
    kit.cap(batch, kit.mat('#c9c1b2', DS), [[kit.offsetRing(T, 7)]], 0.04, { scale: 3 });
    {
      const trees = [],
        benches = [];
      const R0 = kit.offsetRing(T, 10);
      const RB = kit.offsetRing(T, 5.5);
      for (let k = 0; k < R0.length; k += 6) {
        const p = R0[k];
        if (p[1] > cy + 6) continue; // keep the block side clear
        trees.push([p[0], p[1], k, 7 + (k % 3)]);
        const q = RB[(k + 3) % RB.length];
        benches.push([q[0], q[1], ang(q) + Math.PI / 2]);
      }
      g.add(placeAssets('london_plane', trees, { scaleOf: (p) => p[3] }));
      g.add(placeAssets('bench', benches));
    }
    g.add(batch.toGroup('cassini_tower'));
    return g;
  },
};
