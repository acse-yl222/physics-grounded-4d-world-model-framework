// Kensington Gardens Bandstand, north-west of Queen's Gate (J. H. Markham, Chief
// Architect to the Office of Works, 1930-31). A fanciful neo-Regency metal bandstand:
// a canted octagonal pedestal carrying eight slender columns, an octagonal canopy with a
// convex painted sounding board beneath, and a copper tented roof with a polygonal
// finial.
export default {
  id: 'kensington_gardens_bandstand',
  name: 'Kensington Gardens Bandstand',
  claims: ['1ff9c3db-dc4c-462a-a578-00441e43336d'],
  references: [
    {
      title: "Bandstand to north west of Queen's Gate - Historic England",
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1275317',
      used_for:
        'Grade II, 1930, J H Markham; neo-Regency metal composition, canted pedestal, eight slender columns, octagonal canopy with convex painted sounding board, copper tented roof with polygonal finial',
    },
    {
      title: "Bandstand to North West of Queen's Gate - British Listed Buildings",
      url: 'https://britishlistedbuildings.co.uk/101275317-bandstand-to-north-west-of-queens-gate-knightsbridge-and-belgravia-ward',
      used_for: 'listing text and location',
    },
    {
      title: 'Kensington Bandstand, Kensington Park Gardens - Dulux contractor listing',
      url: 'https://connectdirectory.dulux.co.uk/contractor-listing/349/1009',
      used_for: 'installed 1931, J. Markham of the Office of Works, repainting',
    },
  ],
  notes:
    'Octagon fitted to the scene footprint (Overture h=14.6 m ignored). Pedestal 1.2 m, columns 3.3 m, roof ' +
    'rise and finial are proportioned, not measured; white/cream metalwork and the blue sounding-board colour ' +
    'are assumptions; the copper is shown weathered green.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring0 = buildings[0].polys[0][0];
    const cx = ring0.reduce((s, p) => s + p[0], 0) / ring0.length,
      cy = ring0.reduce((s, p) => s + p[1], 0) / ring0.length;
    const R = Math.min(
      5.2,
      ring0.reduce((s, p) => s + Math.hypot(p[0] - cx, p[1] - cy), 0) / ring0.length,
    );
    const a0 = Math.PI / 8;
    const oct = (r) => {
      const out = [];
      for (let k = 0; k < 8; k++) {
        const a = a0 + (k * Math.PI) / 4;
        out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
      }
      return out;
    };
    const stone = kit.mat('#d8d2c4', { roughness: 0.85 });
    const metal = kit.mat('#efece2', { roughness: 0.45, metalness: 0.2 });
    const copper = kit.mat('copper_green');
    const board = kit.mat('#7d9bb5', { roughness: 0.6 });
    const floorM = kit.mat('#8a6a4a');
    const PH = 1.2,
      COL = 3.3;
    // canted pedestal: frustum of an octagon
    const ped = new THREE.CylinderGeometry(R * 1.0, R * 1.08, PH, 8).rotateX(Math.PI / 2);
    const pm = new THREE.Matrix4()
      .makeRotationZ(a0 + Math.PI / 2 + Math.PI / 8)
      .setPosition(cx, cy, PH / 2);
    batch.addGeometry(stone, ped, pm);
    ped.dispose();
    kit.cornice(batch, stone, oct(R * 0.98), PH - 0.15, { height: 0.15, projection: 0.12 });
    kit.cap(batch, floorM, [[oct(R * 0.97)]], PH + 0.005);
    // steps
    const sAng = -Math.PI / 2;
    for (let i = 0; i < 4; i++) {
      const d = R + 0.3 * (4 - i) - 0.1;
      kit.box(
        batch,
        stone,
        cx + Math.cos(sAng) * d,
        cy + Math.sin(sAng) * d,
        0,
        2.0,
        0.32,
        (PH * (i + 1)) / 4,
        sAng + Math.PI / 2,
      );
    }
    // slender columns, lattice railing
    const cr = oct(R - 0.3);
    const colG = new THREE.CylinderGeometry(0.07, 0.08, COL, 8).rotateX(Math.PI / 2);
    const capG = new THREE.CylinderGeometry(0.17, 0.08, 0.25, 8).rotateX(Math.PI / 2);
    for (let k = 0; k < 8; k++) {
      const [x, y] = cr[k];
      batch.addGeometry(metal, colG, new THREE.Matrix4().makeTranslation(x, y, PH + COL / 2));
      batch.addGeometry(metal, capG, new THREE.Matrix4().makeTranslation(x, y, PH + COL - 0.1));
      const a = cr[k],
        b = cr[(k + 1) % 8];
      const mid = Math.atan2((a[1] + b[1]) / 2 - cy, (a[0] + b[0]) / 2 - cx);
      if (Math.abs(mid - sAng) > 0.3)
        kit.balustrade(batch, metal, [a, b], PH, { height: 0.85, spacing: 0.2 });
      // arched frieze between column heads
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        l = Math.hypot(dx, dy);
      const arc = new THREE.TorusGeometry(l / 2, 0.04, 3, 10, Math.PI);
      const m = new THREE.Matrix4()
        .makeRotationZ(Math.atan2(dy, dx))
        .multiply(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
      m.setPosition((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, PH + COL - 0.05);
      // hanging arc (rotated so it bows downwards)
      batch.addGeometry(metal, arc, m);
      arc.dispose();
    }
    colG.dispose();
    capG.dispose();
    // canopy: deep fascia, convex sounding board below, copper tent roof, finial
    const top = PH + COL;
    const fr = oct(R + 0.2);
    kit.walls(batch, metal, [[fr]], top - 0.05, top + 0.55, { bay: 1e6 });
    kit.cornice(batch, metal, fr, top + 0.5, { height: 0.15, projection: 0.15 });
    const sb = new THREE.SphereGeometry(R + 0.2, 8, 4, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2)
      .rotateX(Math.PI / 2)
      .scale(1, 1, 0.22);
    const sbm = new THREE.Matrix4().makeRotationZ(a0 + Math.PI / 2).setPosition(cx, cy, top);
    batch.addGeometry(board, sb, sbm);
    sb.dispose();
    // tented roof: concave profile lathe with 8 sides
    const roof = new THREE.LatheGeometry(
      [
        [R + 0.45, 0],
        [R * 0.75, 0.5],
        [R * 0.45, 1.2],
        [R * 0.2, 2.1],
        [0.05, 2.6],
      ].map(([r, h]) => new THREE.Vector2(r, h)),
      8,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(
      copper,
      roof,
      new THREE.Matrix4().makeRotationZ(a0 + Math.PI / 2).setPosition(cx, cy, top + 0.65),
    );
    roof.dispose();
    const fin = new THREE.LatheGeometry(
      [
        [0.25, 0],
        [0.3, 0.2],
        [0.15, 0.45],
        [0.22, 0.65],
        [0.05, 1.0],
        [0.0, 1.05],
      ].map(([r, h]) => new THREE.Vector2(r, h)),
      8,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(metal, fin, new THREE.Matrix4().makeTranslation(cx, cy, top + 0.65 + 2.5));
    fin.dispose();

    g.add(batch.toGroup('kensington_gardens_bandstand'));
    return g;
  },
};
