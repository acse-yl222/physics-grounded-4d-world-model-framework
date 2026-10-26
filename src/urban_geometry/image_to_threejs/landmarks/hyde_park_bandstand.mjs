// Hyde Park Bandstand, north side of Serpentine Road near its east end. First put up in
// Kensington Gardens in 1869 and moved here in 1886 (one of the oldest bandstands in
// Britain): an octagonal stock-brick platform with stone dressings over a basement,
// cast-iron decorative columns with foliated brackets carrying a tent roof with a
// timber valance, topped by a blind lantern with a spike finial.
export default {
  id: 'hyde_park_bandstand',
  name: 'Hyde Park Bandstand',
  claims: ['bf387034-7616-4b7a-b8d6-ac018f8f3093'],
  references: [
    {
      title: 'Bandstand on north side of Serpentine Road - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101231392-bandstand-on-north-side-of-serpentine-road-near-east-end-of-serpentine-road-knightsbridge-and-belgravia-ward',
      used_for:
        'octagonal stock brick stone-dressed platform with basement; cast iron decorative columns with foliated brackets, tent roof with wooden valance, blind lantern with spike finial; location',
    },
    {
      title: "Where's London's oldest...bandstand? - Exploring London",
      url: 'https://exploring-london.com/tag/bandstand/',
      used_for: 'built 1869 in Kensington Gardens near Mount Gate, moved to Hyde Park in 1886',
    },
    {
      title: 'Hyde Park Bandstand - Time Out',
      url: 'https://www.timeout.com/london/attractions/hyde-park-bandstand',
      used_for: 'concerts since the 1890s, general appearance',
    },
  ],
  notes:
    'Octagon fitted to the 95 m2 footprint (circumradius ~5.6 m). Platform height (1.5 m), column height ' +
    '(3.4 m), roof rise and lantern size are estimates; dark green ironwork, cream valance and grey roof ' +
    'colours are assumptions (not stated in the listing). Steps assumed on the Serpentine Road (south) side.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring0 = buildings[0].polys[0][0];
    const cx = ring0.reduce((s, p) => s + p[0], 0) / ring0.length,
      cy = ring0.reduce((s, p) => s + p[1], 0) / ring0.length;
    const R = ring0.reduce((s, p) => s + Math.hypot(p[0] - cx, p[1] - cy), 0) / ring0.length;
    const a0 = Math.atan2(ring0[0][1] - cy, ring0[0][0] - cx);
    const oct = (r, z = 0) => {
      const out = [];
      for (let k = 0; k < 8; k++) {
        const a = a0 + (k * Math.PI) / 4;
        out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
      }
      return kit.ringArea(out) < 0 ? out.reverse() : out;
    };
    const brick = kit.facade('london_stock', 0);
    const stockM = kit.mat('london_stock');
    const stone = kit.mat('portland_stone');
    const iron = kit.mat('#2c4a3a', { roughness: 0.5, metalness: 0.3 });
    const cream = kit.mat('#e9e1c9', { roughness: 0.7 });
    const roofM = kit.mat('#59656a', { roughness: 0.6, metalness: 0.2 });
    const boards = kit.mat('#8a6a4a');
    const dark = kit.mat('#2d2a26');
    const PH = 1.5,
      COL = 3.4;

    // platform with basement vents, stone plinth & coping
    const base = oct(R);
    kit.walls(batch, stockM, [[base]], 0, PH - 0.2, { bay: 1e6 });
    kit.cornice(batch, stone, base, 0, { height: 0.25, projection: 0.08 });
    kit.cornice(batch, stone, base, PH - 0.22, { height: 0.22, projection: 0.12 });
    kit.cap(batch, boards, [[oct(R + 0.1)]], PH);
    for (let k = 0; k < 8; k++) {
      const a = base[k],
        b = base[(k + 1) % 8];
      kit.windowRow(batch, a, b, 0.4, {
        count: 1,
        width: 0.9,
        height: 0.5,
        head: 'none',
        bars: 3,
        glass: dark,
        frame: iron,
        sill: stone,
      });
    }
    void brick;
    // steps on the south face
    let south = 0,
      sy = Infinity;
    for (let k = 0; k < 8; k++) {
      const my = (base[k][1] + base[(k + 1) % 8][1]) / 2;
      if (my < sy) ((sy = my), (south = k));
    }
    const sa = base[south],
      sb = base[(south + 1) % 8];
    const sang = Math.atan2(sb[1] - sa[1], sb[0] - sa[0]);
    const snx = (sb[1] - sa[1]) / Math.hypot(sb[0] - sa[0], sb[1] - sa[1]),
      sny = -(sb[0] - sa[0]) / Math.hypot(sb[0] - sa[0], sb[1] - sa[1]);
    const smx = (sa[0] + sb[0]) / 2,
      smy = (sa[1] + sb[1]) / 2;
    for (let i = 0; i < 5; i++) {
      const d = 0.35 * (5 - i);
      kit.box(
        batch,
        stone,
        smx + snx * (d - 0.15),
        smy + sny * (d - 0.15),
        0,
        2.2,
        0.35,
        (PH * (i + 1)) / 5,
        sang,
      );
    }

    // columns with foliated brackets and railings between them
    const cr = oct(R - 0.35);
    const colG = new THREE.CylinderGeometry(0.09, 0.11, COL, 8).rotateX(Math.PI / 2);
    const capG = new THREE.CylinderGeometry(0.2, 0.1, 0.3, 8).rotateX(Math.PI / 2);
    const baseG = new THREE.CylinderGeometry(0.15, 0.17, 0.35, 8).rotateX(Math.PI / 2);
    for (let k = 0; k < 8; k++) {
      const [x, y] = cr[k];
      batch.addGeometry(iron, colG, new THREE.Matrix4().makeTranslation(x, y, PH + COL / 2));
      batch.addGeometry(iron, capG, new THREE.Matrix4().makeTranslation(x, y, PH + COL - 0.1));
      batch.addGeometry(iron, baseG, new THREE.Matrix4().makeTranslation(x, y, PH + 0.17));
      // brackets: quarter rings to the neighbours
      const nb = cr[(k + 1) % 8],
        pb = cr[(k + 7) % 8];
      for (const q of [nb, pb]) {
        const dx = q[0] - x,
          dy = q[1] - y,
          l = Math.hypot(dx, dy);
        const br = new THREE.TorusGeometry(0.55, 0.035, 3, 6, Math.PI / 2);
        const m = new THREE.Matrix4()
          .makeRotationZ(Math.atan2(dy, dx))
          .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2))
          .multiply(new THREE.Matrix4().makeRotationZ(Math.PI / 2));
        m.setPosition(x + (dx / l) * 0.55, y + (dy / l) * 0.55, PH + COL - 0.6);
        batch.addGeometry(iron, br, m);
        br.dispose();
      }
      // railing panel (leave the step side open)
      if (k !== south) {
        const a = cr[k],
          b = cr[(k + 1) % 8];
        kit.balustrade(batch, iron, [a, b], PH, { height: 0.9, spacing: 0.16 });
      }
    }
    [colG, capG, baseG].forEach((x) => x.dispose());

    // eaves beam, valance, tent roof, blind lantern, spike finial
    const eave = PH + COL;
    const er = oct(R + 0.25);
    kit.walls(batch, cream, [[er]], eave - 0.55, eave + 0.05, { bay: 1e6 });
    // scalloped valance: small hanging teeth
    for (let k = 0; k < 8; k++) {
      const a = er[k],
        b = er[(k + 1) % 8];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]),
        an = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const n = Math.round(L / 0.35);
      for (let i = 0; i < n; i++) {
        const t = (i + 0.5) / n;
        kit.box(
          batch,
          cream,
          a[0] + (b[0] - a[0]) * t,
          a[1] + (b[1] - a[1]) * t,
          eave - 0.78,
          0.18,
          0.05,
          0.23,
          an,
        );
      }
    }
    kit.cap(batch, cream, [[er]], eave - 0.55, { down: true });
    const roofG = new THREE.ConeGeometry(R + 0.45, 2.3, 8, 1, true, 0).rotateX(Math.PI / 2);
    const rm = new THREE.Matrix4()
      .makeRotationZ(a0 - Math.PI / 2)
      .setPosition(cx, cy, eave + 0.05 + 1.15);
    // ConeGeometry radial vertices sit at angles measured from +z before rotation; align roughly
    batch.addGeometry(roofM, roofG, rm);
    roofG.dispose();
    const lan = new THREE.CylinderGeometry(0.75, 0.85, 0.9, 8).rotateX(Math.PI / 2);
    batch.addGeometry(cream, lan, new THREE.Matrix4().makeTranslation(cx, cy, eave + 1.6 + 0.45));
    lan.dispose();
    const lr = new THREE.ConeGeometry(1.0, 0.7, 8).rotateX(Math.PI / 2);
    batch.addGeometry(
      roofM,
      lr,
      new THREE.Matrix4().makeTranslation(cx, cy, eave + 2.05 + 0.35 + 0.1),
    );
    lr.dispose();
    const sp = new THREE.ConeGeometry(0.06, 1.3, 6).rotateX(Math.PI / 2);
    batch.addGeometry(iron, sp, new THREE.Matrix4().makeTranslation(cx, cy, eave + 2.75 + 0.65));
    sp.dispose();
    const ball = new THREE.SphereGeometry(0.16, 8, 6);
    batch.addGeometry(iron, ball, new THREE.Matrix4().makeTranslation(cx, cy, eave + 2.8));
    ball.dispose();

    g.add(batch.toGroup('hyde_park_bandstand'));
    return g;
  },
};
