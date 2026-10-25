// Royal College of Art, Darwin Building, Kensington Gore (H. T. Cadbury-Brown with Hugh
// Casson and Robert Goodden, 1960-63; Grade II). Eight-storey block of glass and
// sombre purple-brown brick with an exposed-aggregate concrete frame opposite the Royal
// Albert Hall: a dense grid of brick piers and concrete floor bands framing large
// studio windows, a glazed top-floor studio storey and north-light roof glazing.
export default {
  id: 'rca_darwin_building',
  name: 'Royal College of Art – Darwin Building',
  claims: ['fbe9fd1c-d1c5-4d60-b6cc-7e8668ed3fd0'],
  references: [
    {
      title: 'Royal College of Art - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_College_of_Art',
      used_for:
        'designed by RCA staff Cadbury-Brown, Casson and Goodden, 1960-63, Grade II listed 2001',
    },
    {
      title: 'Darwin Building, RCA, seen from the north-east - RIBApix',
      url: 'https://www.architecture.com/image-library/RIBApix/licensed-image/poster/darwin-building-royal-college-of-art-kensington-gore-london-seen-from-the-northeast/posterid/RIBA4149.html',
      used_for: 'concrete frame and brickwork massing on Kensington Gore',
    },
    {
      title: 'Royal College of Art - Modernism in Metro-Land',
      url: 'https://www.modernism-in-metroland.co.uk/royal-college-of-art.html',
      used_for: 'Nairn: sombre purple-toned facing brick with concrete aggregate',
    },
    {
      title: 'Darwin Building, Royal College of Art - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/1960/collegeofart.html',
      used_for:
        'eight-storey building of glass and dark brick for workshops and studios, opposite the Albert Hall',
    },
  ],
  notes:
    'Height from the data (26.4 m). Pier/bay rhythm and the glazed top storey with north-light roof glazing are approximations ' +
    'from descriptions; the staggered internal section is not modelled.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const b = byId['fbe9fd1c-d1c5-4d60-b6cc-7e8668ed3fd0'];
    if (!b) return g;
    let ring = b.polys[0][0];
    if (kit.ringArea(ring) < 0) ring = ring.slice().reverse();
    const H = b.h ?? 26.4;
    const top = H - 3.4;
    const BRICK = '#4d3431',
      CONC = '#a39e93';
    const facade = kit.paintedMaterial('rca_darwin_building:bay', 512, 256, (c, w, h) => {
      // 4 bays (3.2 m) x 2 storeys (3.25 m)
      c.fillStyle = BRICK;
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.04)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
      const bw = w / 4,
        sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        c.fillStyle = CONC;
        c.fillRect(0, y0 + sh - 16, w, 16); // exposed aggregate floor band
        c.fillStyle = 'rgba(80,75,70,0.35)';
        for (let x = 0; x < w; x += 6) c.fillRect(x, y0 + sh - 14 + ((x * 7) % 11), 2, 2);
        for (let b2 = 0; b2 < 4; b2++) {
          const x = b2 * bw;
          c.fillStyle = '#2a3540';
          c.fillRect(x + 26, y0 + 22, bw - 52, sh - 48);
          c.fillStyle = '#7d858a';
          c.fillRect(x + 26, y0 + 22 + (sh - 48) * 0.3, bw - 52, 3);
          c.fillRect(x + bw / 2 - 1, y0 + 22, 3, sh - 48);
        }
      }
    });
    kit.walls(batch, facade, [[ring]], 0, top, { bay: 3.2, storey: 3.25 });
    // Recessed ground-floor glazing line and concrete plinth.
    kit.walls(batch, kit.mat(CONC), [[kit.offsetRing(ring, 0.05)]], 0, 0.6);
    // Concrete roof band.
    const o = kit.offsetRing(ring, 0.3);
    const conc = kit.mat(CONC);
    kit.walls(batch, conc, [[o]], top - 0.7, top);
    kit.cap(batch, conc, [[o, ring.slice().reverse()]], top);
    kit.cap(batch, kit.mat('#6f6c68'), [[ring]], top);
    // Glazed top studio storey set back from the frontage.
    const inner = kit.offsetRing(ring, -1.2);
    const studio = kit.paintedMaterial('rca_darwin_building:studio', 256, 64, (c, w, h) => {
      c.fillStyle = '#3b4d5a';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#c9ccc9';
      for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 3, h);
      c.fillRect(0, 0, w, 4);
      c.fillRect(0, h - 4, w, 4);
    });
    kit.walls(batch, studio, [[inner]], top, H - 0.6, { bay: 3.2, storey: (H - 0.6 - top) / 2 });
    kit.cap(batch, kit.mat('#5f5e5c'), [[inner]], H - 0.6);
    // North-light roof glazing ridges across the top.
    const fr = kit.ringFrame(ring);
    let ang = fr.angle;
    if (Math.cos(ang) < 0) ang += Math.PI; // +v points north
    const e = kit.orientedExtent(inner, ang);
    const glass = kit.mat('#56707e', { roughness: 0.2, metalness: 0.3 });
    const z0 = H - 0.6,
      z1 = H + 1.1;
    const span = e.v1 - e.v0 - 3;
    const n = Math.max(1, Math.floor(span / 4.0));
    const step = span / n;
    const u0 = e.u0 + 2,
      u1 = e.u1 - 2;
    for (let k = 0; k < n; k++) {
      const va = e.v0 + 1.5 + k * step,
        vb = va + step;
      // solid back slope rising from the south (va) to the ridge (vb), vertical glazing facing north
      const A = e.at(u0, va, z0),
        B = e.at(u1, va, z0),
        Ct = e.at(u1, vb, z1),
        Dt = e.at(u0, vb, z1),
        C = e.at(u1, vb, z0),
        D = e.at(u0, vb, z0);
      batch.quad(conc, A, B, Ct, Dt, [0, 0], [1, 0], [1, 1], [0, 1]);
      batch.quad(glass, C, D, Dt, Ct, [0, 0], [1, 0], [1, 1], [0, 1]);
      batch.add(
        conc,
        [D, A, Dt],
        [
          [0, 0],
          [1, 0],
          [1, 1],
        ],
        [0, 1, 2],
      );
      batch.add(
        conc,
        [B, C, Ct],
        [
          [0, 0],
          [1, 0],
          [1, 1],
        ],
        [0, 1, 2],
      );
    }
    g.add(batch.toGroup('rca_darwin_building'));
    return g;
  },
};
