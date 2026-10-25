// Whiteleys / The Whiteley, Queensway, Bayswater. Edwardian department store by
// John Belcher and J. J. Joass (1911), extended north by W. Curtis Green
// (1925-27) in the same style; Grade II listed. Long Portland stone Queensway
// frontage with a giant colonnade framing large upper-floor glazing above the
// shopfronts, an attic and balustrade, the stone tower and cupola over the
// south-east corner entrance (Queensway / Porchester Gardens) and the
// re-modelled cupola at the northern corner. Behind the retained facade, Foster +
// Partners' 2016-25 scheme added residential/hotel storeys around a central
// courtyard, keeping the glass dome over the old atrium.
export default {
  id: 'whiteleys',
  name: 'Whiteleys (The Whiteley)',
  claims: ['bad19412-57bd-4789-b9cc-12a13f944ba4'],
  references: [
    {
      title: 'Whiteleys - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Whiteleys',
      used_for: 'Belcher & Joass 1911, extension 1925-27, retained 1911 facade',
    },
    {
      title: 'The Whiteley - Foster + Partners',
      url: 'https://fosterandpartners.com/projects/the-whiteley',
      used_for:
        'Grade II listed, Curtis Green phase, remodelled cupola on the northern corner, restored Queensway facade glazing',
    },
    {
      title: 'Whiteleys - AKT II',
      url: 'https://akt-uk.com/projects/whiteleys',
      used_for: 'listed south-eastern corner with stone cupola and stone tower over the entrance',
    },
    {
      title: 'The Whiteley - Radmat case study',
      url: 'https://radmat.com/?p=18745',
      used_for: 'colonnaded facade and rooftop cupolas',
    },
    {
      title: 'Whiteleys shopping centre report - GLA',
      url: 'https://data.london.gov.uk/download/2zw6q/5e02b63e-524f-44fc-8e61-938bf8699a15/whiteleys_shopping_centre_report.pdf',
      used_for:
        'retained facade, clock and glass dome, new central courtyard, up to 10 upper levels',
    },
  ],
  notes:
    'Overture height (14 m) replaced: facade cornice 22 m, attic 25.5 m, rear new-build blocks 30-36 m ' +
    '(storey counts from planning reports, exact profile unknown). Column rhythm, cupola proportions, ' +
    'dome position and the colour of the cupola roofs are estimates from textual descriptions only.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const O = [871.6, 827.92],
      A = (100 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    // u: north along Queensway, v: west, into the block
    const W = (u, v) => [O[0] + u * ca - v * sa, O[1] + u * sa + v * ca];
    const toL = ([x, y]) => [(x - O[0]) * ca + (y - O[1]) * sa, -(x - O[0]) * sa + (y - O[1]) * ca];
    const b = new kit.MeshBatch();
    const clip = (ring, f) => {
      const out = [];
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const fp = f(p),
          fq = f(q);
        if (fp >= 0) out.push(p);
        if (fp >= 0 !== fq >= 0) {
          const t = fp / (fp - fq);
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
      }
      return out;
    };
    const toW = (r) => {
      let w = r.map(([u, v]) => W(u, v));
      if (kit.ringArea(w) < 0) w = w.slice().reverse();
      return w;
    };
    const box = (u, v, z0, du, dv, h, m) => {
      const [x, y] = W(u, v);
      kit.box(b, m, x, y, z0, du, dv, h, A);
    };
    const add = (geo, m, u, v, z) => {
      const [x, y] = W(u, v);
      b.addGeometry(m, geo, new THREE.Matrix4().makeRotationZ(A).setPosition(x, y, z));
      geo.dispose();
    };
    const stone = kit.mat('#e3dccb');
    const stoneDark = kit.mat('#cfc6b2');
    const lead = kit.mat('#5f676b', { roughness: 0.6, metalness: 0.3 });
    const flat = kit.mat('#77766f');
    const glassDome = kit.mat('#9fb6c2', { roughness: 0.15, metalness: 0.3 });

    // Queensway elevation, one bay = 7.5 m: shopfront, giant columns with glazing, entablature, attic.
    const H = 22,
      ATT = 25.5;
    const facadeM = kit.paintedMaterial('whiteleys:queensway', 256, 768, (c, w, h) => {
      const zToY = (z) => h - (z / ATT) * h;
      c.fillStyle = '#e4ddcc';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.91);
      for (let k = 0; k < 1500; k++) {
        c.fillStyle = `rgba(120,110,90,${r() * 0.08})`;
        c.fillRect(r() * w, r() * h, 2, 2);
      }
      // shopfront
      c.fillStyle = '#1f2a30';
      c.fillRect(20, zToY(4.6), w - 40, zToY(0.2) - zToY(4.6));
      c.fillStyle = 'rgba(235,220,180,0.35)';
      c.fillRect(20, zToY(3.2), w - 40, zToY(0.2) - zToY(3.2));
      c.fillStyle = '#2a3b33';
      c.fillRect(20, zToY(5.4), w - 40, zToY(4.6) - zToY(5.4)); // fascia
      c.fillStyle = '#d3cab6';
      c.fillRect(0, zToY(6.2), w, zToY(5.4) - zToY(6.2)); // string course
      // giant order: two columns per bay framing a tall glazed opening with bronze transoms
      c.fillStyle = '#2b363d';
      c.fillRect(46, zToY(18.6), w - 92, zToY(6.6) - zToY(18.6));
      c.fillStyle = 'rgba(170,190,200,0.28)';
      c.fillRect(46, zToY(18.6), w - 92, (zToY(6.6) - zToY(18.6)) * 0.3);
      c.fillStyle = '#7b5b3a';
      for (const z of [10.3, 14.4]) c.fillRect(46, zToY(z), w - 92, 7);
      for (let x = 46 + (w - 92) / 4; x < w - 50; x += (w - 92) / 4)
        c.fillRect(x - 2, zToY(18.6), 4, zToY(6.6) - zToY(18.6));
      for (const x of [0, w]) {
        const g2 = c.createLinearGradient(x - 24, 0, x + 24, 0);
        g2.addColorStop(0, '#c9c0ab');
        g2.addColorStop(0.5, '#f1ebdc');
        g2.addColorStop(1, '#c4bba6');
        c.fillStyle = g2;
        c.fillRect(x - 24, zToY(19.2), 48, zToY(6.6) - zToY(19.2));
        c.fillStyle = '#d8cfbb';
        c.fillRect(x - 30, zToY(19.8), 60, 14);
        c.fillRect(x - 28, zToY(6.9), 56, 10);
      }
      // entablature and cornice
      c.fillStyle = '#d6cdb8';
      c.fillRect(0, zToY(21.2), w, zToY(19.8) - zToY(21.2));
      c.fillStyle = '#f2ecdf';
      c.fillRect(0, zToY(22), w, zToY(21.2) - zToY(22));
      // attic windows
      c.fillStyle = '#2b363d';
      for (const x of [56, 150]) c.fillRect(x, zToY(24.6), 50, zToY(22.8) - zToY(24.6));
      c.fillStyle = '#efe8da';
      c.fillRect(0, 0, w, zToY(25.1));
    });
    const sideM = kit.facade('portland_stone', 0);
    const rearM = kit.facade('modern_clad', 1);

    let lr = byId['bad19412-57bd-4789-b9cc-12a13f944ba4'].polys[0][0].map(toL);
    if (kit.ringArea(lr) < 0) lr = lr.slice().reverse();
    const FD = 22; // depth of the historic range behind the Queensway facade
    const front = clip(lr, (p) => FD - p[1]);
    // historic range walls: painted on the Queensway face, stone elsewhere
    for (let k = 0; k < front.length; k++) {
      const p = front[k],
        q = front[(k + 1) % front.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (len < 0.1) continue;
      const isFront = Math.abs(q[1] - p[1]) < 2 && p[1] < 3 && q[1] < 3;
      const isInner = p[1] > FD - 0.1 && q[1] > FD - 0.1;
      if (isInner) continue;
      const P = W(...p),
        Q = W(...q);
      const m = isFront ? facadeM : facadeM;
      const ur = Math.max(1, Math.round(len / 7.5));
      b.quad(
        m,
        [P[0], P[1], 0],
        [Q[0], Q[1], 0],
        [Q[0], Q[1], ATT],
        [P[0], P[1], ATT],
        [0, 0],
        [ur, 0],
        [ur, 1],
        [0, 1],
      );
      if (isFront)
        // giant-order columns standing proud of the facade at every bay division
        for (let j = 1; j < ur; j++) {
          const t = j / ur,
            cu = p[0] + (q[0] - p[0]) * t,
            cv = p[1] + (q[1] - p[1]) * t - 0.45;
          if (cu < 13 || cu > 159) continue;
          add(
            new THREE.CylinderGeometry(0.5, 0.56, 12.6, 10).rotateX(Math.PI / 2),
            stone,
            cu,
            cv,
            6.6 + 6.3,
          );
          box(cu, cv, 6.2, 1.5, 1.5, 0.5, stoneDark);
          box(cu, cv, 19.0, 1.6, 1.6, 0.7, stoneDark);
        }
    }
    kit.cap(b, flat, [[toW(front)]], ATT);
    // balustrade along the Queensway attic
    box(85.25, 0.2, ATT, 170.5, 0.4, 1.1, stone);
    for (let u = 3; u < 168; u += 7.5) box(u, 0.2, ATT, 1.2, 0.6, 1.6, stoneDark);
    // central entrance feature: pediment-like raised attic over the middle bays
    box(85, 1.5, ATT, 22, 3, 3.5, stone);
    box(85, 0.3, ATT + 3.5, 23, 3.6, 0.6, stoneDark);

    // Rear new-build blocks stepping up behind the facade, around a central courtyard.
    const rear = clip(lr, (p) => p[1] - FD);
    const blocks = [
      { f: (p) => 62 - p[0], h: 33 },
      { f: (p) => p[0] - 108, h: 36 },
      { f: (p) => ((p[0] - 62) * (108 - p[0]) >= 0 ? p[1] - 62 : -1), h: 30, mid: true },
    ];
    for (const bl of blocks) {
      let r;
      if (bl.mid)
        r = clip(
          clip(
            clip(rear, (p) => p[0] - 62),
            (p) => 108 - p[0],
          ),
          (p) => p[1] - 64,
        );
      else r = clip(rear, bl.f);
      if (r.length < 3) continue;
      const wr = toW(r);
      kit.walls(b, rearM, [[wr]], 0, bl.h - 3, { bay: 3.4, storey: 3.2 });
      kit.walls(b, kit.mat('#8f9599'), [[kit.offsetRing(wr, -2.0)]], bl.h - 3, bl.h);
      kit.cap(b, flat, [[wr]], bl.h - 3);
      kit.cap(b, flat, [[kit.offsetRing(wr, -2.0)]], bl.h);
    }
    // low courtyard infill (retail) between the rear blocks, with the retained glass dome
    {
      const r = clip(
        clip(
          clip(rear, (p) => p[0] - 62),
          (p) => 108 - p[0],
        ),
        (p) => 64 - p[1],
      );
      const wr = toW(r);
      kit.walls(b, sideM, [[wr]], 0, 12, { bay: 3.6, storey: 3.4 });
      kit.cap(b, kit.mat('#9aa39a'), [[wr]], 12);
      const R = 9.5;
      add(new THREE.CylinderGeometry(R, R, 2.4, 24).rotateX(Math.PI / 2), stone, 85, 43, 13.2);
      const dome = new THREE.SphereGeometry(R, 24, 8, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
        Math.PI / 2,
      );
      dome.scale(1, 1, 0.7);
      add(dome, glassDome, 85, 43, 14.4);
      for (let k = 0; k < 12; k++) {
        const a = (k / 12) * Math.PI * 2;
        const rib = new THREE.BoxGeometry(0.25, 0.25, 7).rotateY(-0.9);
        const m = new THREE.Matrix4()
          .makeRotationZ(a)
          .multiply(new THREE.Matrix4().makeTranslation(R * 0.55, 0, 3.2));
        rib.applyMatrix4(m);
        add(rib, lead, 85, 43, 14.4);
      }
      add(new THREE.CylinderGeometry(1.2, 1.4, 1.6, 12).rotateX(Math.PI / 2), lead, 85, 43, 21.8);
    }

    // Corner tower with cupola (south-east, over the entrance) and the northern cupola.
    const cupola = (u, v, s, base, scale, clock) => {
      // square stone tower rising above the attic
      box(u, v, 0, s, s, base, stone);
      box(u, v, base - 1.0, s + 1.2, s + 1.2, 1.0, stoneDark);
      for (const [du, dv] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ])
        box(
          u + (du * s) / 2.2,
          v + (dv * s) / 2.2,
          base,
          1.4 * scale,
          1.4 * scale,
          2.5 * scale,
          stoneDark,
        );
      if (clock) {
        const face = kit.paintedMaterial('whiteleys:clock', 128, 128, (c, w, h) => {
          c.fillStyle = '#e4ddcc';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#f5f1e6';
          c.beginPath();
          c.arc(64, 64, 56, 0, 7);
          c.fill();
          c.strokeStyle = '#1d2a33';
          c.lineWidth = 6;
          c.stroke();
          c.fillStyle = '#1d2a33';
          for (let k = 0; k < 12; k++) {
            const a = (k * Math.PI) / 6;
            c.fillRect(64 + Math.cos(a) * 46 - 3, 64 + Math.sin(a) * 46 - 3, 6, 6);
          }
          c.lineWidth = 5;
          c.beginPath();
          c.moveTo(64, 64);
          c.lineTo(64, 24);
          c.moveTo(64, 64);
          c.lineTo(92, 74);
          c.stroke();
        });
        for (const [pu, pv, du, dv] of [
          [u, v - s / 2 - 0.05, 3.6, 0.05],
          [u - s / 2 - 0.05, v, 0.05, 3.6],
        ])
          box(pu, pv, base - 6, du, dv, 3.6, face);
      }
      // drum with ring of columns, dome and lantern
      const R = (s / 2) * 0.82;
      add(
        new THREE.CylinderGeometry(R + 0.4, R + 0.4, 0.8, 24).rotateX(Math.PI / 2),
        stoneDark,
        u,
        v,
        base + 0.4,
      );
      add(
        new THREE.CylinderGeometry(R * 0.78, R * 0.78, 5.2 * scale, 16).rotateX(Math.PI / 2),
        kit.mat('#3a454c'),
        u,
        v,
        base + 0.8 + 2.6 * scale,
      );
      for (let k = 0; k < 8; k++) {
        const a = (k / 8) * Math.PI * 2;
        add(
          new THREE.CylinderGeometry(0.32 * scale, 0.36 * scale, 5.2 * scale, 8).rotateX(
            Math.PI / 2,
          ),
          stone,
          u + Math.cos(a) * R,
          v + Math.sin(a) * R,
          base + 0.8 + 2.6 * scale,
        );
      }
      const top = base + 0.8 + 5.2 * scale;
      add(
        new THREE.CylinderGeometry(R + 0.5, R + 0.5, 1.0, 24).rotateX(Math.PI / 2),
        stone,
        u,
        v,
        top + 0.5,
      );
      const dome = new THREE.SphereGeometry(R, 24, 10, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
        Math.PI / 2,
      );
      dome.scale(1, 1, 1.15);
      add(dome, lead, u, v, top + 1.0);
      add(
        new THREE.CylinderGeometry(0.8 * scale, 0.9 * scale, 2.2 * scale, 8).rotateX(Math.PI / 2),
        stone,
        u,
        v,
        top + 1 + R * 1.15 + 1.1 * scale,
      );
      add(
        new THREE.ConeGeometry(0.9 * scale, 1.6 * scale, 8).rotateX(Math.PI / 2),
        lead,
        u,
        v,
        top + 1 + R * 1.15 + 2.2 * scale + 0.8 * scale,
      );
      add(
        new THREE.SphereGeometry(0.35 * scale, 8, 6),
        kit.mat('gold'),
        u,
        v,
        top + 1 + R * 1.15 + 3.4 * scale,
      );
    };
    cupola(5.8, 5.8, 12.2, 32, 1.0, true);
    cupola(165, 5.3, 11, 29, 0.85, false);
    g.add(b.toGroup('whiteleys'));
    return g;
  },
};
