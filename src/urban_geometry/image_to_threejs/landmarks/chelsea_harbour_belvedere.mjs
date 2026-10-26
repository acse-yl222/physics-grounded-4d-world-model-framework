// The Belvedere, Chelsea Harbour (Moxley Jenner & Partners, 1986-89): the ~200 ft
// residential tower that is the focal point of the Chelsea Harbour development.
// Bronze-coloured cladding with rows of dark blue metal balconies, a metallic
// pagoda-like roof and a mast carrying the gilded ball (which rises and falls with
// the tide).
export default {
  id: 'chelsea_harbour_belvedere',
  name: 'The Belvedere, Chelsea Harbour',
  claims: ['b949d968-5c44-48f1-a104-b7d8cf7521bf'],
  references: [
    {
      title: 'Chelsea Harbour - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Chelsea_Harbour',
      used_for: 'Moxley Jenner & Partners, 1986-89 development, 18-storey Belvedere tower',
    },
    {
      title: 'Belvedere Tower, Chelsea Harbour, London - Manchester History',
      url: 'https://manchesterhistory.net/architecture/1980/belvedere.html',
      used_for:
        '200 ft tower, bronze cladding, dark blue metal balconies, metallic pagoda-like roof',
    },
    {
      title: 'The Belvedere - Buildington',
      url: 'https://www.buildington.co.uk/buildings/images/10273',
      used_for: 'building record',
    },
    {
      title: 'The Belvedere residential development, Chelsea Harbour (1999) - London Museum',
      url: 'https://londonmuseum.org.uk/collections/v/object-743457/the-belvedere-residential-development-chelsea-harbour',
      used_for: 'photograph record (caption only)',
    },
  ],
  notes:
    'Square Overture footprint chamfered into an octagon; body to 52 m and pagoda roof to ~61 m (200 ft), mast and ' +
    'gilded ball above. The tide ball is drawn at mid height on its mast; it is named in the brief but no returned ' +
    'source confirmed it. 18 storeys per the Chelsea Harbour history (lobby + 16 typical floors + roof storey here). ' +
    'Balcony rhythm, window counts per face, corner fins, standing seams and roof tier proportions estimated; ' +
    'street furniture round the base is reused assets placed schematically.',
  build({ THREE, kit, buildings, frame, placeAssets }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = b.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const { cx, cy } = frame;
    const ang = frame.angle;
    const S = Math.min(frame.length, frame.width); // ~16.6 m
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    const W = (u, v) => [cx + u * ca - v * sa, cy + u * sa + v * ca];
    const half = S / 2,
      ch = S * 0.2;
    const octL = [
      [-half + ch, -half],
      [half - ch, -half],
      [half, -half + ch],
      [half, half - ch],
      [half - ch, half],
      [-half + ch, half],
      [-half, half - ch],
      [-half, -half + ch],
    ];
    const oct = octL.map(([u, v]) => W(u, v));
    const BODY = 52,
      G = 4.5,
      FLOORS = 16,
      ST = (BODY - 1.2 - G) / FLOORS;

    const clad = kit.paintedMaterial(
      'chelsea_harbour_belvedere:clad2',
      128,
      128,
      (c, w, h) => {
        // bronze-coloured panels with recessed joints (tile = 4 bays x 2 storeys)
        c.fillStyle = '#9a7a55';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#7d6142';
        for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 2);
        for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 2, h);
        c.fillStyle = 'rgba(255,230,190,0.12)';
        for (let y = 2; y < h; y += 32) c.fillRect(0, y, w, 2);
      },
      { roughness: 0.5, metalness: 0.3 },
    );
    const bronze = kit.mat('#8d6d4b', { roughness: 0.45, metalness: 0.5 });
    const navy = kit.mat('#1f2f52', { roughness: 0.5, metalness: 0.3 });
    const roofMetal = kit.mat('#8f9a9c', { roughness: 0.35, metalness: 0.6 });
    const gold = kit.mat('#e0b43a', { roughness: 0.35, metalness: 0.25 });
    const glass = kit.mat('#2f3b44', { roughness: 0.15, metalness: 0.3 });
    const m4 = new THREE.Matrix4();
    const put = (mat, geo, x, y, z, rz = ang) => {
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));
      geo.dispose();
    };

    // Ground-floor glazed lobby with bronze mullions, plinth and entrance canopy.
    kit.walls(batch, kit.mat('#3a4650', { roughness: 0.2, metalness: 0.3 }), [[oct]], 0, G, {});
    kit.cornice(batch, bronze, oct, 0, { height: 0.4, projection: 0.15 });
    for (let k = 0; k < 8; k++) {
      const a = oct[k],
        q = oct[(k + 1) % 8];
      const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
      const n = Math.max(2, Math.round(len / 1.5));
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        kit.box(
          batch,
          bronze,
          a[0] + (q[0] - a[0]) * t,
          a[1] + (q[1] - a[1]) * t,
          0,
          0.14,
          0.14,
          G,
          Math.atan2(q[1] - a[1], q[0] - a[0]),
        );
      }
    }
    kit.cornice(batch, bronze, oct, G - 0.5, { height: 0.5, projection: 0.6 });
    {
      const [ex, ey] = W(0, -half - 2.2);
      kit.box(batch, bronze, ex, ey, 3.3, 6.5, 4.4, 0.35, ang);
      for (const o of [-3, 3]) {
        const [px, py] = W(o, -half - 4.1);
        kit.box(batch, bronze, px, py, 0, 0.2, 0.2, 3.3, ang);
      }
    }

    // Tower shaft: bronze cladding with framed windows on every floor.
    kit.walls(batch, clad, [[oct]], G, BODY, { bay: 2.6, storey: ST, uvBase: G });
    kit.windowGrid(batch, oct, G + 0.7, FLOORS, ST, (s, k) =>
      k % 2 === 0
        ? {
            count: 3,
            width: 2.2,
            height: 2.0,
            margin: 0.8,
            glass,
            frame: bronze,
            sill: bronze,
            head: 'none',
            bars: 1,
            depth: 0.12,
          }
        : {
            count: 1,
            width: 1.6,
            height: 2.0,
            margin: 0.6,
            glass,
            frame: bronze,
            sill: bronze,
            head: 'none',
            bars: 1,
            depth: 0.12,
          },
    );
    // floor bands
    for (let s = 1; s <= FLOORS; s++)
      kit.cornice(batch, bronze, oct, G + s * ST - 0.12, { height: 0.12, projection: 0.06 });
    // vertical fins at the eight corners
    for (const p of oct) kit.box(batch, bronze, p[0], p[1], G, 0.35, 0.35, BODY - G, 0);
    kit.cornice(batch, bronze, oct, BODY - 1.2, { height: 1.2, projection: 0.6, steps: 2 });
    kit.cap(batch, bronze, [[kit.offsetRing(oct, 0.6)]], BODY);

    // Rows of dark blue metal balconies on the four main faces: slab, fascia, railing.
    for (let s = 1; s < FLOORS; s++) {
      const z = G + s * ST;
      for (let k = 0; k < 8; k += 2) {
        const a = octL[k],
          q = octL[(k + 1) % 8];
        const dx = q[0] - a[0],
          dy = q[1] - a[1];
        const len = Math.hypot(dx, dy);
        const nx = dy / len,
          ny = -dx / len;
        const d = 1.4;
        const p0 = [a[0] + (dx / len) * 0.3 + nx * d, a[1] + (dy / len) * 0.3 + ny * d],
          p1 = [q[0] - (dx / len) * 0.3 + nx * d, q[1] - (dy / len) * 0.3 + ny * d];
        const [mx, my] = W((a[0] + q[0]) / 2 + nx * d * 0.5, (a[1] + q[1]) / 2 + ny * d * 0.5);
        const rz = ang + Math.atan2(dy, dx);
        kit.box(batch, navy, mx, my, z - 0.2, len - 0.6, d, 0.2, rz);
        kit.balustrade(batch, navy, [W(...p0), W(...p1)], z, { height: 1.05, spacing: 0.45 });
        // side returns
        for (const e0 of [a, q]) {
          const sgn = e0 === a ? 1 : -1;
          const r0 = [e0[0] + (dx / len) * 0.3 * sgn, e0[1] + (dy / len) * 0.3 * sgn];
          kit.balustrade(batch, navy, [W(...r0), W(r0[0] + nx * d, r0[1] + ny * d)], z, {
            height: 1.05,
            spacing: 0.45,
          });
        }
      }
    }

    // Pagoda-like stepped metal roof: flared skirts with soffits, bronze fascias,
    // corner finials, a pyramidal cap and the mast with the gilded tide ball.
    const tiers = [
      [S * 0.62, BODY, 3.2],
      [S * 0.44, BODY + 3.6, 2.6],
      [S * 0.3, BODY + 6.6, 2.6],
    ];
    for (const [hs, z, rise] of tiers) {
      const sq = [W(-hs, -hs), W(hs, -hs), W(hs, hs), W(-hs, hs)];
      const inner = hs * 0.62;
      const sqi = [W(-inner, -inner), W(inner, -inner), W(inner, inner), W(-inner, inner)];
      for (let k = 0; k < 4; k++) {
        const a = sq[k],
          bq = sq[(k + 1) % 4],
          c = sqi[(k + 1) % 4],
          d = sqi[k];
        batch.quad(
          roofMetal,
          [...a, z],
          [...bq, z],
          [...c, z + rise],
          [...d, z + rise],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        // standing seams
        for (let j = 1; j < 8; j++) {
          const t = j / 8;
          const p0 = [a[0] + (bq[0] - a[0]) * t, a[1] + (bq[1] - a[1]) * t, z + 0.05];
          const p1 = [d[0] + (c[0] - d[0]) * t, d[1] + (c[1] - d[1]) * t, z + rise + 0.05];
          const v0 = new THREE.Vector3(...p0),
            v1 = new THREE.Vector3(...p1);
          const mm = new THREE.Matrix4().compose(
            v0.clone().add(v1).multiplyScalar(0.5),
            new THREE.Quaternion().setFromUnitVectors(
              new THREE.Vector3(0, 1, 0),
              v1.clone().sub(v0).normalize(),
            ),
            new THREE.Vector3(1, 1, 1),
          );
          batch.addGeometry(
            kit.mat('#a7b1b3', { roughness: 0.3, metalness: 0.6 }),
            new THREE.BoxGeometry(0.08, v0.distanceTo(v1), 0.08),
            mm,
          );
        }
      }
      kit.cap(batch, kit.mat('#5d6466'), [[sq]], z - 0.02, { down: true });
      kit.walls(batch, bronze, [[sq]], z - 0.35, z, {});
      kit.walls(batch, bronze, [[sqi]], z + rise, z + rise + 0.8, {});
      kit.cap(batch, roofMetal, [[sqi]], z + rise + 0.8);
      for (const p of sq) {
        put(gold, new THREE.SphereGeometry(0.22, 8, 6), p[0], p[1], z + 0.15, 0);
      }
    }
    const ztop = BODY + 6.6 + 2.6 + 0.8;
    const rr = S * 0.3 * 0.62;
    const pyr = [W(-rr, -rr), W(rr, -rr), W(rr, rr), W(-rr, rr)];
    kit.pitchedRoof(batch, roofMetal, roofMetal, pyr, ang, ztop, 2.6, 'pyramidal', {
      overhang: 0.1,
    });
    put(
      kit.mat('white_steel'),
      new THREE.CylinderGeometry(0.14, 0.22, 10, 8).rotateX(Math.PI / 2),
      cx,
      cy,
      ztop + 2.6 + 5,
      0,
    );
    put(
      kit.mat('white_steel'),
      new THREE.CylinderGeometry(0.4, 0.5, 0.6, 12).rotateX(Math.PI / 2),
      cx,
      cy,
      ztop + 2.6,
      0,
    );
    put(gold, new THREE.SphereGeometry(1.0, 20, 14), cx, cy, ztop + 2.6 + 4.5, 0);
    put(gold, new THREE.TorusGeometry(1.02, 0.05, 4, 24), cx, cy, ztop + 2.6 + 4.5, 0);
    put(gold, new THREE.SphereGeometry(0.25, 8, 6), cx, cy, ztop + 2.6 + 10.1, 0);

    // Harbour-side street furniture round the base.
    const lamps = [],
      bollards = [];
    for (let k = 0; k < 8; k++) {
      const a = ang + Math.PI / 8 + (k * Math.PI) / 4;
      const R = half + 5.5;
      if (k % 2 === 0) lamps.push([cx + Math.cos(a) * R, cy + Math.sin(a) * R, a + Math.PI / 2]);
      for (const o of [-0.25, 0.25]) {
        const R2 = half + 3.2;
        bollards.push([cx + Math.cos(a + o) * R2, cy + Math.sin(a + o) * R2, 0]);
      }
    }
    g.add(placeAssets('street_lamp', lamps, { name: 'chelsea_harbour_belvedere:lamps' }));
    g.add(placeAssets('bollard', bollards, { name: 'chelsea_harbour_belvedere:bollards' }));

    g.add(batch.toGroup('chelsea_harbour_belvedere'));
    return g;
  },
};
