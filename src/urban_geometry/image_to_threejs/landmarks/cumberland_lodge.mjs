// Cumberland Lodge, Cumberland Gate (Marble Arch corner of Hyde Park), c.1825 by
// Decimus Burton, one of his series of Greek Revival park lodges contemporary with the
// Hyde Park Corner Screen. Portland stone ashlar, one storey and attic under a slate
// roof, three-bay front; the main east front has a central projection with Doric
// pilasters and columns rising to an attic carrying a clock face.
export default {
  id: 'cumberland_lodge',
  name: 'Cumberland Lodge',
  claims: ['c0a40a5e-5f0e-430f-9989-57368080ef11'],
  references: [
    {
      title: 'Cumberland Lodge, Marble Arch - British Listed Buildings (Historic England 1356752)',
      url: 'https://britishlistedbuildings.co.uk/101356752-cumberland-lodge-marble-arch-hyde-park-ward',
      used_for:
        'Grade II, c.1825, Decimus Burton; Portland stone ashlar, slate roof; one storey and attic, three-bay front, east front central projection with Doric pilasters and columns, attic with clock face; small Greek Revival composition',
    },
    {
      title: 'Hyde Park by Decimus Burton - Forgotten Victorians',
      url: 'https://fhpkg.forgottenvictorians.com/?p=264',
      used_for: "Burton's series of Hyde Park lodges and gates of the 1820s",
    },
    {
      title: 'Decimus Burton - Victorian Web',
      url: 'https://victorianweb.org/victorian/art/architecture/burton/1.html',
      used_for: 'Greek Revival lodges in Hyde Park',
    },
  ],
  notes:
    'Footprint 6.9 x 12.5 m with the east (long) side as the main front. Heights (4.4 m to the cornice, attic to ' +
    '6.3 m), the in-antis pair of Doric columns, window sizes and the shallow hipped roof are proportioned from ' +
    'the description; the clock dial is painted.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length,
      cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
    // long axis from (2696.8,667.2) to (2694.7,679.5) => u northwards, east = right
    const a = [2696.8, 667.2],
      b = [2694.7, 679.5];
    const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const U = [(b[0] - a[0]) / l, (b[1] - a[1]) / l];
    const E = [U[1], -U[0]];
    const ang = Math.atan2(U[1], U[0]);
    const L = (u, w) => [cx + U[0] * u + E[0] * w, cy + U[1] * u + E[1] * w];
    const lbox = (m, u, w, z0, du, dw, h) => {
      const p = L(u, w);
      kit.box(batch, m, p[0], p[1], z0, du, dw, h, ang);
    };
    const rect = (u0, u1, w0, w1) => {
      const r = [L(u0, w0), L(u1, w0), L(u1, w1), L(u0, w1)];
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };

    const stone = kit.mat('portland_stone');
    const shade = kit.mat('#cec7b4', { roughness: 0.85 });
    const slate = kit.mat('slate');
    const glass = kit.mat('dark_glass');
    const white = kit.mat('white');
    const door = kit.mat('#3a3d33');
    const clock = kit.paintedMaterial(
      'cumberland_lodge:clock',
      128,
      128,
      (c, w, h) => {
        c.fillStyle = '#ddd6c4';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#f4f1e6';
        c.beginPath();
        c.arc(w / 2, h / 2, w * 0.45, 0, Math.PI * 2);
        c.fill();
        c.strokeStyle = '#1c1c1c';
        c.lineWidth = 4;
        c.stroke();
        for (let k = 0; k < 12; k++) {
          const t = (k / 12) * Math.PI * 2;
          c.beginPath();
          c.moveTo(w / 2 + Math.cos(t) * w * 0.36, h / 2 + Math.sin(t) * h * 0.36);
          c.lineTo(w / 2 + Math.cos(t) * w * 0.42, h / 2 + Math.sin(t) * h * 0.42);
          c.stroke();
        }
        c.lineWidth = 5;
        c.beginPath();
        c.moveTo(w / 2, h / 2);
        c.lineTo(w / 2, h * 0.2);
        c.moveTo(w / 2, h / 2);
        c.lineTo(w * 0.68, h * 0.58);
        c.stroke();
      },
      { roughness: 0.6 },
    );

    const HU = 6.25,
      HW = 3.45,
      EAVE = 4.4;
    const body = rect(-HU, HU, -HW, HW);
    kit.walls(batch, stone, [[body]], 0, EAVE, { bay: 1e6 });
    kit.cornice(batch, shade, body, 0, { height: 0.5, projection: 0.1 });
    kit.cornice(batch, shade, body, EAVE - 0.6, { height: 0.6, projection: 0.35, steps: 3 });
    // windows: three bays on the long sides, one on each end
    for (let k = 0; k < 4; k++) {
      const p = body[k],
        q = body[(k + 1) % 4];
      const long = Math.hypot(q[0] - p[0], q[1] - p[1]) > 9;
      kit.windowRow(batch, p, q, 1.1, {
        count: long ? 3 : 1,
        margin: 0.8,
        width: 1.05,
        height: 2.0,
        head: 'lintel',
        bars: 1,
        glass,
        frame: white,
        sill: shade,
        surround: 0.15,
        surroundMat: shade,
      });
    }
    // central projection on the east front: pilasters, two Doric columns in antis, attic with clock
    const PW = 4.2,
      PD = 1.0;
    const proj = rect(-PW / 2, PW / 2, HW - 0.01, HW + PD);
    kit.walls(batch, stone, [[proj]], 0, EAVE, { bay: 1e6 });
    kit.cornice(batch, shade, proj, EAVE - 0.6, { height: 0.6, projection: 0.35, steps: 3 });
    kit.cap(batch, stone, [[proj]], EAVE);
    // recessed doorway behind the columns
    lbox(door, 0, HW + PD + 0.02, 0.5, 1.3, 0.06, 2.6);
    lbox(shade, 0, HW + PD + 0.05, 3.1, 1.6, 0.1, 0.25);
    for (const su of [-1, 1]) {
      lbox(shade, su * (PW / 2 - 0.3), HW + PD + 0.08, 0.5, 0.55, 0.16, EAVE - 1.1);
      lbox(shade, su * (PW / 2 - 0.3), HW + PD + 0.1, EAVE - 0.65, 0.7, 0.2, 0.12);
    }
    kit.colonnade(batch, stone, L(-0.9, HW + PD + 0.45), L(0.9, HW + PD + 0.45), 0.5, EAVE - 1.1, {
      count: 2,
      radius: 0.24,
      capital: 'doric',
    });
    lbox(stone, 0, HW + PD + 0.25, 0, PW, 0.9, 0.5);
    // attic over the projection with a clock dial
    const attic = rect(-PW / 2 + 0.2, PW / 2 - 0.2, HW - 1.2, HW + PD - 0.15);
    kit.walls(batch, stone, [[attic]], EAVE, EAVE + 1.9, { bay: 1e6 });
    kit.cornice(batch, shade, attic, EAVE + 1.6, { height: 0.3, projection: 0.2 });
    kit.cap(batch, stone, [[attic]], EAVE + 1.9);
    const dial = L(0, HW + PD - 0.13);
    const dg = new THREE.PlaneGeometry(1.1, 1.1);
    const dm = new THREE.Matrix4()
      .makeRotationZ(Math.atan2(E[1], E[0]) + Math.PI / 2)
      .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
    dm.setPosition(dial[0], dial[1], EAVE + 0.85);
    batch.addGeometry(clock, dg, dm);
    dg.dispose();
    // shallow hipped slate roof and a stack
    kit.pitchedRoof(batch, slate, stone, body, ang, EAVE, 1.4, 'hipped', { overhang: 0.2 });
    lbox(stone, -3.5, -1.2, EAVE + 0.4, 0.8, 0.6, 1.6);

    g.add(batch.toGroup('cumberland_lodge'));
    return g;
  },
};
