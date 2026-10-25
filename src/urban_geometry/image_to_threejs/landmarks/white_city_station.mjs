// White City station (Central line), opened 23 November 1947; designed by
// A. D. McGill and Keith Seymour under London Transport chief architect Thomas
// Bilbow; Festival of Britain architecture award 1951 (Abram Games plaque left of
// the entrance). Post-war modernist ticket hall: brick walls, a tall glazed
// screen to Wood Lane under a thin projecting concrete canopy, raised clerestory
// roof, then a long low range beside the surface platforms with their canopies.
export default {
  id: 'white_city_station',
  name: 'White City station',
  claims: [
    '94e1a43b-8a3e-4bac-a268-f372c89310ae', // station building
    'cb7942c6-3c67-49dc-bfeb-208dda30c112', // platform canopies
  ],
  references: [
    {
      title: 'White City tube station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/White_City_tube_station',
      used_for: 'opening 1947, replaced Wood Lane, plaque beside the entrance',
    },
    {
      title: 'White City Station - Modernism in Metro-Land',
      url: 'https://www.modernism-in-metroland.co.uk/white-city.html',
      used_for:
        'architects McGill and Seymour under Bilbow; Festival of Britain award 1951, Abram Games plaque',
    },
    {
      title: 'White City Underground Station - Structurae',
      url: 'https://structurae.net/en/structures/white-city-underground-station',
      used_for: 'structure type / dates',
    },
  ],
  notes:
    'Ticket hall / platform range split of the footprint at y = 602 m is inferred from the outline. Brick colour, glazing pattern, clerestory and canopy forms are reconstructed from period descriptions without photographs; platform canopy roof is a simplified butterfly roof.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const st = byId['94e1a43b-8a3e-4bac-a268-f372c89310ae'];
    const cn = byId['cb7942c6-3c67-49dc-bfeb-208dda30c112'];
    const ring = st.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    // Half-plane clip (keep side where f(p) >= 0).
    const clip = (r, f) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length],
          fa = f(a),
          fb = f(b);
        if (fa >= 0) out.push(a);
        if (fa >= 0 !== fb >= 0) {
          const t = fa / (fa - fb);
          out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
        }
      }
      return out;
    };
    const Y = 602.3;
    const hall = clip(ring, (p) => p[1] - Y);
    const range = clip(ring, (p) => Y - p[1]);
    const brick = kit.paintedMaterial(
      'white_city_stn:brick',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#9a6b4c';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(240,225,200,0.16)';
        for (let r = 0; r < h; r += 5) x.fillRect(0, r, w, 1);
        for (let k = 0; k < 4; k++) {
          x.fillStyle = '#e2dccd';
          x.fillRect(k * 128 + 20, 150, 88, 70);
          x.fillStyle = '#2f3d47';
          x.fillRect(k * 128 + 24, 154, 80, 62);
          x.fillStyle = '#e2dccd';
          x.fillRect(k * 128 + 62, 154, 4, 62);
        }
        x.fillStyle = '#d8d2c2';
        x.fillRect(0, 0, w, 12);
      },
      DS,
    );
    const screen = kit.paintedMaterial(
      'white_city_stn:screen',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#3d505d';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(255,240,200,0.18)';
        x.fillRect(0, h * 0.5, w, h * 0.5);
        x.fillStyle = '#e9e6dc';
        for (let k = 0; k <= w; k += 32) x.fillRect(k - 2, 0, 4, h);
        for (let k = 0; k <= h; k += 42) x.fillRect(0, k - 2, w, 4);
      },
      DS,
    );
    const concrete = kit.mat('#d9d5ca', DS);
    const roofM = kit.mat('#8b8f91', DS);
    const dark = kit.mat('dark_steel', DS);

    // Ticket hall: brick walls with a full-height glazed screen on the west side.
    const Hh = 5.2;
    for (let k = 0; k < hall.length; k++) {
      const a = hall[k],
        b = hall[(k + 1) % hall.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      const west = (a[0] + b[0]) / 2 < -1672 && Math.abs(b[1] - a[1]) > 6;
      const m = west ? screen : brick;
      const n = Math.max(1, Math.round(len / 3.6));
      batch.quad(
        m,
        [a[0], a[1], 0],
        [b[0], b[1], 0],
        [b[0], b[1], Hh],
        [a[0], a[1], Hh],
        [0, 0],
        [n / 4, 0],
        [n / 4, Hh / 6.4],
        [0, Hh / 6.4],
      );
    }
    // Thin projecting concrete roof slab / canopy.
    const slab = kit.offsetRing(hall, 1.6);
    kit.cap(batch, concrete, [[slab]], Hh + 0.45);
    kit.cap(batch, concrete, [[slab]], Hh, { down: true });
    kit.walls(batch, concrete, [[slab]], Hh, Hh + 0.45);
    // Raised clerestory over the booking hall.
    const hf = kit.ringFrame(hall);
    const hc = Math.cos(hf.angle),
      hs = Math.sin(hf.angle);
    const hl = hf.length * 0.28,
      hw2 = hf.width * 0.25;
    const cl = [
      [-hl, -hw2],
      [hl, -hw2],
      [hl, hw2],
      [-hl, hw2],
    ].map(([u, v]) => [hf.cx + u * hc - v * hs, hf.cy + u * hs + v * hc]);
    for (let k = 0; k < cl.length; k++) {
      const a = cl[k],
        b = cl[(k + 1) % cl.length];
      batch.quad(
        screen,
        [a[0], a[1], Hh + 0.45],
        [b[0], b[1], Hh + 0.45],
        [b[0], b[1], 7.6],
        [a[0], a[1], 7.6],
        [0, 0],
        [Math.hypot(b[0] - a[0], b[1] - a[1]) / 6, 0],
        [Math.hypot(b[0] - a[0], b[1] - a[1]) / 6, 0.35],
        [0, 0.35],
      );
    }
    const cl2 = kit.offsetRing(cl, 0.6);
    kit.cap(batch, concrete, [[cl2]], 8.0);
    kit.walls(batch, concrete, [[cl2]], 7.6, 8.0);
    // Name band and roundels on the canopy fascia facing Wood Lane.
    const name = kit.paintedMaterial(
      'white_city_stn:name',
      512,
      64,
      (x, w, h) => {
        x.fillStyle = '#f4f1e8';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#0019a8';
        x.font = 'bold 34px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText('WHITE  CITY  STATION', w / 2, h / 2 + 2);
        for (const cx of [40, w - 40]) {
          x.strokeStyle = '#dc241f';
          x.lineWidth = 9;
          x.beginPath();
          x.arc(cx, h / 2, 20, 0, Math.PI * 2);
          x.stroke();
          x.fillStyle = '#0019a8';
          x.fillRect(cx - 30, h / 2 - 5, 60, 10);
        }
      },
      DS,
    );
    {
      // Westmost long slab edge.
      let best = null;
      for (let k = 0; k < slab.length; k++) {
        const a = slab[k],
          b = slab[(k + 1) % slab.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const mx = (a[0] + b[0]) / 2;
        if (len > 8 && (!best || mx < best.mx)) best = { a, b, mx, len };
      }
      if (best) {
        const { a, b } = best;
        const dx = (b[0] - a[0]) / best.len,
          dy = (b[1] - a[1]) / best.len;
        const ox = dy * 0.05,
          oy = -dx * 0.05;
        const m0 = 0.15 * best.len,
          m1 = 0.85 * best.len;
        const A = [a[0] + dx * m0 + ox, a[1] + dy * m0 + oy],
          B = [a[0] + dx * m1 + ox, a[1] + dy * m1 + oy];
        batch.quad(
          name,
          [A[0], A[1], Hh - 0.05],
          [B[0], B[1], Hh - 0.05],
          [B[0], B[1], Hh + 0.5],
          [A[0], A[1], Hh + 0.5],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    // Low platform range (single storey brick) with flat concrete roof.
    kit.walls(batch, brick, [[range]], 0, 3.8, { bay: 3.6, storey: 3.2 });
    kit.cap(batch, concrete, [[kit.offsetRing(range, 0.5)]], 4.1);
    kit.walls(batch, concrete, [[kit.offsetRing(range, 0.5)]], 3.8, 4.1);

    // Platform canopies over the island platforms (footprint cb7942).
    const pr = cn.polys[0][0];
    const fr = kit.ringFrame(pr);
    const e = kit.orientedExtent(pr, fr.angle);
    const plat = kit.mat('#b7b1a5', DS);
    const Pt = (u, v, z) => e.at(u, v, z);
    const vm = (e.v0 + e.v1) / 2,
      hw = (e.v1 - e.v0) / 2;
    for (const vc of [vm - hw * 0.5, vm + hw * 0.5]) {
      const w2 = hw * 0.48;
      const pc = Pt((e.u0 + e.u1) / 2, vc, 0);
      kit.box(batch, plat, pc[0], pc[1], 0, e.u1 - e.u0 - 2, hw * 0.55, 1.0, fr.angle);
      // Butterfly roof: low in the middle, raised edges.
      for (const sgn of [-1, 1]) {
        const v0 = vc,
          v1 = vc + sgn * w2;
        batch.quad(
          roofM,
          Pt(e.u0 + 2, v0, 4.0),
          Pt(e.u1 - 2, v0, 4.0),
          Pt(e.u1 - 2, v1, 4.6),
          Pt(e.u0 + 2, v1, 4.6),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.quad(
          concrete,
          Pt(e.u0 + 2, v1, 4.4),
          Pt(e.u1 - 2, v1, 4.4),
          Pt(e.u1 - 2, v1, 4.7),
          Pt(e.u0 + 2, v1, 4.7),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      for (let u = e.u0 + 4; u < e.u1 - 2; u += 7) {
        const p = Pt(u, vc, 0);
        kit.box(batch, dark, p[0], p[1], 1.0, 0.3, 0.3, 3.0, fr.angle);
      }
    }
    g.add(batch.toGroup('white_city_station'));
    return g;
  },
};
