// Former Royal College of Organists, 1 Kensington Gore (Lt H. H. Cole RE, built 1874-75
// for the National Training School for Music). Four storeys and three main bays in
// stucco covered with sgraffito panels by F. W. Moody and his students: cream, pale
// blue and maroon friezes of putti carrying musical instruments and scrolls. Entrance in
// a full-height canted bay with oriels above, mullion-and-transom windows and a
// bracketed eaves cornice under a slate roof.
export default {
  id: 'royal_college_of_organists',
  name: 'Royal College of Organists (former)',
  claims: ['f4fa2cad-6f80-4d7f-9e80-67a3eee60414'],
  references: [
    {
      title: 'Royal College of Organists - British Listed Buildings (Historic England list entry)',
      url: 'https://britishlistedbuildings.co.uk/101217773-royal-college-of-organists-knightsbridge-and-belgravia-ward',
      used_for:
        'four storeys, three main bays, full-height canted entrance bay with oriels, mullion-and-transom windows, bracketed eaves cornice, stucco with sgraffito panels by F. W. Moody',
    },
    {
      title: 'Royal College of Organists - Survey of London (british-history.ac.uk)',
      url: 'https://www.british-history.ac.uk/node/40140',
      used_for:
        "built 1874-5 for the National Training School for Music; sgraffito executed by Moody's students",
    },
    {
      title: 'Organs and archaeology - Adam Yamey',
      url: 'https://adam-yamey-writes.com/tag/organ/',
      used_for:
        'cream, pale blue and maroon sgraffito; bands of putti carrying musical instruments',
    },
    {
      title: 'Royal College of Organists - victorianweb.org',
      url: 'https://www.victorianweb.org/art/architecture/misc/4.html',
      used_for: 'H. H. Cole as architect, Moody sgraffiti',
    },
  ],
  notes:
    'The Overture footprint is larger than the narrow street building and is decorated throughout; the canted bay is placed ' +
    'at the centre of the street (north) frontage. Sgraffito figures are abstracted to putti silhouettes and scrolls; ' +
    'slate roof pitch is assumed. Eaves at the data height (17.9 m less roof).',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const b = byId['f4fa2cad-6f80-4d7f-9e80-67a3eee60414'];
    if (!b) return g;
    let ring = b.polys[0][0];
    if (kit.ringArea(ring) < 0) ring = ring.slice().reverse();
    const H = Math.max(14, (b.h ?? 17.9) - 2.6);
    const CREAM = '#e9dcc0',
      MAROON = '#7a2e2c',
      BLUE = '#9db7c6',
      DARK = '#262d35';
    // Painted sgraffito facade: 4 bays (3.4 m) x full height (4 storeys).
    const mat = kit.paintedMaterial('royal_college_of_organists:sgraffito', 512, 512, (c, w, h) => {
      const P = h / H,
        Y = (m) => h - m * P,
        bw = w / 4;
      c.fillStyle = CREAM;
      c.fillRect(0, 0, w, h);
      const r = kit.rng(3.7);
      const st = [0, H * 0.27, H * 0.52, H * 0.76, H];
      // Storey friezes of putti on maroon / blue grounds.
      for (let s = 0; s < 4; s++) {
        const z = st[s + 1] - 1.0;
        c.fillStyle = s % 2 ? BLUE : MAROON;
        c.fillRect(0, Y(z + 0.9), w, 0.9 * P);
        c.fillStyle = CREAM;
        for (let x = 6; x < w; x += 22) {
          const y0 = Y(z + 0.15);
          c.beginPath();
          c.arc(x + 6, y0 - 18, 4, 0, Math.PI * 2); // head
          c.fill();
          c.fillRect(x + 3, y0 - 14, 7, 10); // body
          c.fillRect(x + (r() < 0.5 ? -2 : 10), y0 - 16, 6, 2); // instrument / scroll
        }
      }
      // Panels flanking the windows with scroll ornament.
      for (let s = 0; s < 4; s++)
        for (let bb = 0; bb < 4; bb++) {
          const x = bw * (bb + 0.5),
            z0 = st[s] + (s ? 0.4 : 1.0),
            z1 = st[s + 1] - 1.3;
          c.fillStyle = s ? MAROON : '#b98e6e';
          c.fillRect(x - 46, Y(z1), 92, (z1 - z0) * P);
          c.strokeStyle = CREAM;
          c.lineWidth = 2;
          for (const sx of [-38, 30]) {
            c.beginPath();
            c.arc(x + sx + 4, Y((z0 + z1) / 2), 5, 0, Math.PI * 1.6);
            c.stroke();
          }
          // mullion-and-transom window
          c.fillStyle = '#f1e8d2';
          c.fillRect(x - 28, Y(z1 - 0.15), 56, (z1 - z0 - 0.3) * P);
          c.fillStyle = DARK;
          c.fillRect(x - 24, Y(z1 - 0.35), 48, (z1 - z0 - 0.7) * P);
          c.fillStyle = '#f1e8d2';
          c.fillRect(x - 2, Y(z1 - 0.35), 4, (z1 - z0 - 0.7) * P);
          c.fillRect(x - 24, Y(z0 + (z1 - z0) * 0.66), 48, 4);
        }
      // Rusticated base.
      c.fillStyle = '#cbbd9e';
      c.fillRect(0, Y(0.8), w, 0.8 * P);
    });
    kit.walls(batch, mat, [[ring]], 0, H, { bay: 3.4, storey: H / 2 });
    // Bracketed eaves cornice.
    const ro = kit.offsetRing(ring, 0.6);
    const cornice = kit.mat('#ddd0b2');
    kit.walls(batch, cornice, [[ro]], H - 0.5, H);
    kit.cap(batch, cornice, [[ro, ring.slice().reverse()]], H - 0.5, { down: true });
    // Brackets along the cornice.
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        bb = ring[(k + 1) % ring.length];
      const l = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
      const ang = Math.atan2(bb[1] - a[1], bb[0] - a[0]);
      const n = Math.floor(l / 1.2);
      for (let j = 1; j < n; j++) {
        const t = j / n;
        const x = a[0] + (bb[0] - a[0]) * t + Math.sin(ang) * 0.3,
          y = a[1] + (bb[1] - a[1]) * t - Math.cos(ang) * 0.3;
        kit.box(batch, cornice, x, y, H - 1.1, 0.25, 0.6, 0.6, ang);
      }
    }
    // Slate roof: hipped over the oriented frame (low enough to stay under the data height).
    const fr = kit.ringFrame(ring);
    const slate = kit.mat('#545a61');
    // Slate roof following the footprint: slopes from the eaves to an inset flat top.
    const inner = kit.offsetRing(ring, -1.8);
    const rise = 2.5;
    for (let k = 0; k < ro.length; k++) {
      const j = (k + 1) % ro.length;
      batch.quad(
        slate,
        [ro[k][0], ro[k][1], H],
        [ro[j][0], ro[j][1], H],
        [inner[j][0], inner[j][1], H + rise],
        [inner[k][0], inner[k][1], H + rise],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    kit.cap(batch, kit.mat('#5d6268'), [[inner]], H + rise);
    // Chimney stacks.
    for (const t of [0.2, 0.6]) {
      const p = inner[Math.floor(t * inner.length)];
      kit.box(batch, kit.mat('#b7a789'), p[0], p[1], H + 1, 1.0, 2.2, rise + 1.6, fr.angle);
    }

    // Canted full-height entrance bay at the centre of the north (street) frontage.
    let best = null;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        bb = ring[(k + 1) % ring.length];
      const l = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
      const nx = (bb[1] - a[1]) / l,
        ny = -(bb[0] - a[0]) / l; // outward normal of a CCW ring
      if (l > 6 && ny > 0.8 && (!best || (a[1] + bb[1]) / 2 > best.my))
        best = { a, b: bb, l, nx, ny, my: (a[1] + bb[1]) / 2 };
    }
    if (best) {
      const { a, b: bb, l, nx, ny } = best;
      const tx = (bb[0] - a[0]) / l,
        ty = (bb[1] - a[1]) / l;
      const mx = (a[0] + bb[0]) / 2,
        my = (a[1] + bb[1]) / 2;
      const W = Math.min(4.6, l * 0.42),
        D = 1.3;
      const P = (s, d) => [mx + tx * s + nx * d, my + ty * s + ny * d];
      // CCW outline of the bay: wall base corners and the canted front.
      const bay = [
        P(-W / 2, -0.05),
        P(W / 2, -0.05),
        P(W / 2 - D * 0.8, D),
        P(-W / 2 + D * 0.8, D),
      ].reverse();
      let bayR = bay;
      if (kit.ringArea(bayR) < 0) bayR = bayR.slice().reverse();
      kit.walls(batch, mat, [[bayR]], 0, H - 0.5, { bay: 1.7, storey: H / 2 });
      kit.cap(batch, cornice, [[bayR]], H - 0.5);
      // Entrance door at the foot of the bay.
      const dp = P(0, D + 0.03);
      kit.box(batch, kit.mat('#3a2a22'), dp[0], dp[1], 0, 1.6, 0.06, 2.9, Math.atan2(ty, tx));
      kit.box(
        batch,
        cornice,
        P(0, D + 0.15)[0],
        P(0, D + 0.15)[1],
        3.0,
        2.6,
        0.3,
        0.35,
        Math.atan2(ty, tx),
      );
      // Small lead cap on the bay.
      const capGeo = new THREE.ConeGeometry(W * 0.45, 1.6, 6).rotateX(Math.PI / 2);
      const m = new THREE.Mesh(capGeo, kit.mat('lead'));
      const cp = P(0, D * 0.4);
      m.position.set(cp[0], cp[1], H - 0.5 + 0.8);
      m.rotation.z = Math.atan2(ty, tx) + Math.PI / 6;
      g.add(m);
    }
    g.add(batch.toGroup('royal_college_of_organists'));
    return g;
  },
};
