// Diana, Princess of Wales Memorial Fountain, Hyde Park (Kathryn Gustafson with
// Gustafson Porter + Bowman, opened 2004). An oval ring-shaped stream of 545 pieces of
// Cornish granite, about 50 x 80 m, enclosing a lawn: water rises at the top of the
// slope and runs both ways round the ring over steps, swirls and cascades ("rock and
// roll", "chaos") into a calm pool at the bottom. Three small bridges cross the
// channel and a low railing encloses the site.
export default {
  id: 'diana_memorial_fountain',
  name: 'Diana, Princess of Wales Memorial Fountain',
  claims: [],
  references: [
    {
      title: 'Diana, Princess of Wales Memorial Fountain - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Diana,_Princess_of_Wales_Memorial_Fountain',
      used_for:
        'designer, opening 2004, ring-shaped stream of Cornish granite, location south-west of the Serpentine',
    },
    {
      title: 'Diana, Princess of Wales Memorial Fountain - Landscape Institute case study',
      url: 'https://my.landscapeinstitute.org/case-study/diana,-princess-of-wales-memorial-fountain/36156c22-d37b-e911-a99b-00224801ab04',
      used_for: '545 pieces of Cornish granite, digitally cut, varied channel textures',
    },
    {
      title: 'Diana Princess of Wales Memorial Fountain - Free Tours by Foot',
      url: 'https://freetoursbyfoot.com/diana-princess-wales-memorial-fountain/',
      used_for: 'oval about 50 m x 80 m around a grass area, channel ~3-6 m wide',
    },
    {
      title: 'Diana Memorial Fountain - Gustafson Porter + Bowman (PDF)',
      url: 'https://www.gp-b.com/s/Diana_A4_PORTRAIT.pdf',
      used_for:
        'stream flowing both ways from a high point to a still pool, bridges across the channel',
    },
  ],
  notes:
    'Channel plan taken from the scene water polygon (outer and inner ring) so it matches the map. The site is ' +
    'modelled flat (the real ring follows a gentle slope). Granite coping widths, channel depth, the positions of ' +
    'the three bridges, the cascade/step locations and the perimeter railing line (offset 5 m) are estimates.',
  build({ THREE, kit, scene }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // Locate the ring in the scene water layer (polygon with a hole near (2010,-200)).
    let poly = null;
    for (const w of scene.water ?? []) {
      if (!w.poly || w.poly.length < 2) continue;
      const r = w.poly[0];
      const cx = r.reduce((a, p) => a + p[0], 0) / r.length,
        cy = r.reduce((a, p) => a + p[1], 0) / r.length;
      if (Math.hypot(cx - 2010, cy - 200 * -1) < 30) poly = w.poly;
    }
    const fallback = (rx, ry) => {
      const r = [];
      for (let k = 0; k < 48; k++) {
        const a = (k / 48) * Math.PI * 2;
        r.push([2010.3 + rx * Math.cos(a), -200 + ry * Math.sin(a)]);
      }
      return r;
    };
    let outer = poly ? poly[0].slice() : fallback(25.7, 40.4);
    let inner = poly ? poly[1].slice() : fallback(21.5, 36);
    if (kit.ringArea(outer) < 0) outer.reverse();
    if (kit.ringArea(inner) < 0) inner.reverse();
    // resample a ring to ~1.5 m spacing for smooth copings
    const resample = (ring, step = 1.5) => {
      const out = [];
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const n = Math.max(1, Math.round(L / step));
        for (let i = 0; i < n; i++)
          out.push([a[0] + ((b[0] - a[0]) * i) / n, a[1] + ((b[1] - a[1]) * i) / n]);
      }
      return out;
    };
    outer = resample(outer);
    inner = resample(inner);

    const granite = kit.mat('#c9c4bb', { roughness: 0.75 });
    const graniteDark = kit.mat('#9e9a93', { roughness: 0.8 });
    const bed = kit.mat('#8a8780', { roughness: 0.85 });
    const water = kit.paintedMaterial(
      'diana_fountain:water',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#7fa3b4';
        c.fillRect(0, 0, w, h);
        const rnd = kit.rng(7);
        for (let i = 0; i < 260; i++) {
          c.strokeStyle = `rgba(235,245,250,${0.15 + rnd() * 0.35})`;
          c.lineWidth = 1 + rnd() * 2;
          const x = rnd() * w,
            y = rnd() * h;
          c.beginPath();
          c.moveTo(x, y);
          c.quadraticCurveTo(x + 10, y - 5 + rnd() * 10, x + 22 + rnd() * 10, y);
          c.stroke();
        }
      },
      { roughness: 0.15, metalness: 0.1, transparent: true, opacity: 0.9 },
    );
    const rail = kit.mat('#2b2f31', { roughness: 0.5, metalness: 0.4 });
    const paving = kit.mat('#d7d2c6', { roughness: 0.9 });

    const rev = (r) => r.slice().reverse();
    // Channel bed (slightly sunk), water surface, granite copings on both lips.
    const outerIn = kit.offsetRing(outer, -0.45),
      innerOut = kit.offsetRing(inner, 0.45);
    kit.cap(batch, bed, [[outerIn, rev(innerOut)]], 0.09);
    kit.cap(batch, water, [[outerIn, rev(innerOut)]], 0.2, { scale: 6 });
    const outerCope = kit.offsetRing(outer, 0.9),
      innerCope = kit.offsetRing(inner, -0.9);
    kit.cap(batch, granite, [[outerCope, rev(outerIn)]], 0.32);
    kit.walls(batch, granite, [[outerCope]], 0.05, 0.32, { bay: 1e6 });
    kit.walls(batch, graniteDark, [[rev(outerIn)]], 0.09, 0.32, { bay: 1e6 });
    kit.cap(batch, granite, [[innerOut, rev(innerCope)]], 0.32);
    kit.walls(batch, granite, [[rev(innerCope)]], 0.05, 0.32, { bay: 1e6 });
    kit.walls(batch, graniteDark, [[innerOut]], 0.09, 0.32, { bay: 1e6 });

    // Perimeter paved apron and low railing.
    const apron = kit.offsetRing(outer, 3.0);
    kit.cap(batch, paving, [[apron, rev(outerCope)]], 0.14);
    const fence = resample(kit.offsetRing(outer, 6.0), 2.4);
    const post = new THREE.CylinderGeometry(0.035, 0.035, 1.0, 5).rotateX(Math.PI / 2);
    for (let k = 0; k < fence.length; k++) {
      const a = fence[k],
        b = fence[(k + 1) % fence.length];
      // gaps for the entrances on the east and west sides
      const mx = (a[0] + b[0]) / 2;
      const my = (a[1] + b[1]) / 2;
      if (Math.abs(my + 200) < 3 && Math.abs(mx - 2010) > 20) continue;
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const an = Math.atan2(b[1] - a[1], b[0] - a[0]);
      kit.box(batch, rail, mx, my, 0.95, L, 0.05, 0.05, an);
      kit.box(batch, rail, mx, my, 0.15, L, 0.04, 0.04, an);
      batch.addGeometry(rail, post, new THREE.Matrix4().makeTranslation(a[0], a[1], 0.5));
    }
    post.dispose();

    // Cascades, steps and swirls: granite ribs across the channel on parts of the ring.
    const N = outerIn.length;
    const nearest = (p, ring) => {
      let best = 0,
        bd = Infinity;
      for (let i = 0; i < ring.length; i++) {
        const d = Math.hypot(ring[i][0] - p[0], ring[i][1] - p[1]);
        if (d < bd) ((bd = d), (best = i));
      }
      return ring[best];
    };
    const rnd = kit.rng(2004);
    for (let i = 0; i < N; i++) {
      const frac = i / N;
      // steps on the western run, rock-and-roll ribs on the south-east run
      const steps = frac > 0.1 && frac < 0.3;
      const ribs = frac > 0.55 && frac < 0.72;
      if (!(steps && i % 3 === 0) && !(ribs && i % 2 === 0)) continue;
      const a = outerIn[i],
        b = nearest(a, innerOut);
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const an = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const h = steps ? 0.18 : 0.08 + rnd() * 0.1;
      kit.box(
        batch,
        graniteDark,
        (a[0] + b[0]) / 2,
        (a[1] + b[1]) / 2,
        0.09,
        L,
        steps ? 0.5 : 0.25,
        h,
        an,
      );
    }

    // Three footbridges across the channel (north, south-west, east).
    const bridgeAt = (frac) => {
      const i = Math.floor(frac * N) % N;
      const a = kit.offsetRing(outer, 1.2)[Math.floor((frac * outer.length) % outer.length)];
      const b = nearest(a, innerCope);
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]) + 0.6;
      const an = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const cx = (a[0] + b[0]) / 2,
        cy = (a[1] + b[1]) / 2;
      kit.box(batch, granite, cx, cy, 0.32, L, 3.0, 0.18, an);
      void i;
    };
    bridgeAt(0.02);
    bridgeAt(0.4);
    bridgeAt(0.78);

    g.add(batch.toGroup('diana_memorial_fountain'));
    return g;
  },
};
