// Queen Anne's Alcove, Kensington Gardens (attributed to Sir Christopher Wren, 1705;
// moved here from the palace gardens in the 1860s). A tall, free-standing pedimented
// garden shelter open to the south: a giant semi-domed niche, panelled inside, framed by
// paired fluted Corinthian pilasters with shell niches between them and carved swags
// above, a monogrammed cartouche on the keystone; Portland stone front, brick flanks
// and a lead roof.
export default {
  id: 'queen_annes_alcove',
  name: "Queen Anne's Alcove",
  claims: ['4b6e2d30-048f-45a4-9f1c-c8adb4c8dee5'],
  references: [
    {
      title: 'Shelter (Alcove) opposite the north end of the Serpentine - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101217602-shelter-alcove-opposite-the-north-end-of-the-serpentine-hyde-park-ward',
      used_for:
        'Grade II*, early C18, Wren; Portland stone with brick flanks, lead roof; tall pedimented structure open to the south with giant semi-domed panelled niche, paired fluted Corinthian pilasters, shell niches, swags, monogram cartouche on keystone',
    },
    {
      title: "Queen Anne's Alcove, Kensington Gardens - Look Up London",
      url: 'https://lookup.london/queen-annes-alcove-kensington-gardens/',
      used_for: '1705 date, Wren design, large pedimental niche beside the Italian Gardens',
    },
    {
      title: 'Kensington Gardens - A View on Cities',
      url: 'https://aviewoncities.com/london/kensington-gardens',
      used_for: 'moved from the palace gardens to the edge of Kensington Gardens in 1867',
    },
  ],
  notes:
    'Built on the 10.4 x 6.0 m footprint, open face on its south-south-east long side. Height (7.4 m to the top of ' +
    'the cornice, 9.4 m to the pediment apex), niche width (4.4 m) and pilaster/shell-niche positions are ' +
    'proportioned from the description, not measured. Carving (capitals, swags, cartouche, panelling) is reduced ' +
    'to simple solids; interior painted decoration is omitted.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring0 = buildings[0].polys[0][0];
    // long edge facing south-south-east is the open front
    let best = null;
    for (let k = 0; k < ring0.length; k++) {
      const a = ring0[k],
        b = ring0[(k + 1) % ring0.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const nrm = [(b[1] - a[1]) / len, -(b[0] - a[0]) / len];
      const area = kit.ringArea(ring0);
      const out = area > 0 ? nrm : [-nrm[0], -nrm[1]];
      if (len > 6 && (!best || out[1] < best.out[1])) best = { a, b, len, out };
    }
    const cx = ring0.reduce((s, p) => s + p[0], 0) / ring0.length,
      cy = ring0.reduce((s, p) => s + p[1], 0) / ring0.length;
    // local frame: u along the front (left to right seen from outside), v backwards
    const V = [-best.out[0], -best.out[1]];
    const U = [V[1], -V[0]];
    const ang = Math.atan2(U[1], U[0]);
    const Wd = 10.4,
      D = 6.0;
    const L = (u, v) => [cx + U[0] * u + V[0] * v, cy + U[1] * u + V[1] * v];
    const lbox = (m, u, v, z0, w, d, h) => {
      const p = L(u, v);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, ang);
    };
    const F = -D / 2; // front plane

    const stone = kit.mat('portland_stone');
    const stoneShade = kit.mat('#cfc7b3', { roughness: 0.85 });
    const niche = kit.mat('#e6dfcd', { roughness: 0.85, side: THREE.DoubleSide });
    const brick = kit.mat('red_brick');
    const lead = kit.mat('lead');
    const dark = kit.mat('#5a5850', { roughness: 0.9 });
    const timber = kit.mat('#6b5440');

    const H = 6.6, // top of pilasters / bottom of entablature
      ENT = 0.85,
      NR = 2.2,
      SPRING = 4.1;
    // plinth & steps
    lbox(stone, 0, 0, 0, Wd + 0.3, D + 0.3, 0.45);
    lbox(stone, 0, F - 0.55, 0, NR * 2 + 0.8, 0.8, 0.22);
    // brick flanks and back
    lbox(brick, -Wd / 2 + 0.3, 0.4, 0.45, 0.6, D - 0.8, H + ENT - 0.45);
    lbox(brick, Wd / 2 - 0.3, 0.4, 0.45, 0.6, D - 0.8, H + ENT - 0.45);
    lbox(brick, 0, D / 2 - 0.3, 0.45, Wd, 0.6, H + ENT - 0.45);
    // front slab with the arched niche opening
    const sh = new THREE.Shape();
    sh.moveTo(-Wd / 2, 0.45);
    sh.lineTo(-NR, 0.45);
    sh.lineTo(-NR, SPRING);
    for (let i = 0; i <= 16; i++) {
      const a = Math.PI - (i / 16) * Math.PI;
      sh.lineTo(NR * Math.cos(a), SPRING + NR * Math.sin(a));
    }
    sh.lineTo(NR, 0.45);
    sh.lineTo(Wd / 2, 0.45);
    sh.lineTo(Wd / 2, H + ENT);
    sh.lineTo(-Wd / 2, H + ENT);
    sh.closePath();
    const fg = new THREE.ExtrudeGeometry(sh, { depth: 0.8, bevelEnabled: false, curveSegments: 8 });
    const fm = new THREE.Matrix4().makeBasis(
      new THREE.Vector3(U[0], U[1], 0),
      new THREE.Vector3(0, 0, 1),
      new THREE.Vector3(-V[0], -V[1], 0),
    );
    const fo = L(0, F + 0.8);
    fm.setPosition(fo[0], fo[1], 0);
    batch.addGeometry(stone, fg, fm);
    fg.dispose();
    // niche: half-cylinder and quarter-sphere semidome behind the opening
    const nc = L(0, F + 0.8);
    const cyl = new THREE.CylinderGeometry(NR, NR, SPRING - 0.45, 20, 1, true, Math.PI / 2, Math.PI)
      .rotateX(Math.PI / 2)
      .translate(0, 0, (SPRING - 0.45) / 2 + 0.45);
    // local +y of the cylinder half must point backwards (+V)
    const nm = new THREE.Matrix4()
      .makeRotationZ(Math.atan2(V[1], V[0]) - Math.PI / 2)
      .setPosition(nc[0], nc[1], 0);
    batch.addGeometry(niche, cyl, nm);
    cyl.dispose();
    const dome = new THREE.SphereGeometry(NR, 20, 6, Math.PI, Math.PI, 0, Math.PI / 2)
      .rotateX(Math.PI / 2)
      .translate(0, 0, SPRING);
    batch.addGeometry(niche, dome, nm);
    dome.dispose();
    // panelling ribs inside the niche
    for (let k = 1; k < 6; k++) {
      const a = (k / 6) * Math.PI;
      const p = [
        nc[0] + (Math.cos(a) * U[0] + Math.sin(a) * V[0]) * (NR - 0.05),
        nc[1] + (Math.cos(a) * U[1] + Math.sin(a) * V[1]) * (NR - 0.05),
      ];
      kit.box(batch, stoneShade, p[0], p[1], 0.45, 0.12, 0.12, SPRING - 0.45, ang + a);
    }
    kit.cap(
      batch,
      kit.mat('paving'),
      [[[L(-NR, F + 0.8), L(NR, F + 0.8), L(NR, F + 0.8 + NR), L(-NR, F + 0.8 + NR)]]],
      0.46,
    );
    // bench in the niche
    lbox(timber, 0, F + 0.8 + NR - 0.5, 0.45, NR * 1.6, 0.5, 0.45);
    // archivolt and keystone cartouche
    const tor = new THREE.TorusGeometry(NR + 0.14, 0.14, 4, 16, Math.PI);
    const tm = new THREE.Matrix4()
      .makeRotationZ(ang)
      .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
    const tp = L(0, F - 0.05);
    tm.setPosition(tp[0], tp[1], SPRING);
    batch.addGeometry(stoneShade, tor, tm);
    tor.dispose();
    lbox(stoneShade, 0, F - 0.12, SPRING + NR - 0.25, 0.8, 0.3, 0.95);
    // paired fluted Corinthian pilasters with shell niches between each pair
    for (const su of [-1, 1]) {
      for (const pu of [2.75, 4.75]) {
        const u = su * pu;
        lbox(stone, u, F - 0.12, 0.45, 0.62, 0.24, 0.35);
        for (let f = -2; f <= 2; f++)
          lbox(stoneShade, u + f * 0.11, F - 0.13, 0.8, 0.05, 0.24, H - 1.25);
        lbox(stone, u, F - 0.1, 0.8, 0.55, 0.2, H - 1.25);
        lbox(stoneShade, u, F - 0.16, H - 0.55, 0.72, 0.32, 0.55);
      }
      const nu = su * 3.75;
      lbox(dark, nu, F + 0.02, 2.2, 0.9, 0.05, 1.5);
      const shell = new THREE.CylinderGeometry(
        0.45,
        0.45,
        0.06,
        10,
        1,
        false,
        -Math.PI / 2,
        Math.PI,
      );
      const smx = new THREE.Matrix4().makeRotationZ(ang);
      const sp = L(nu, F - 0.02);
      smx.setPosition(sp[0], sp[1], 3.7);
      batch.addGeometry(stoneShade, shell, smx);
      shell.dispose();
      // carved swag over the niche
      const sw = new THREE.TorusGeometry(0.5, 0.1, 4, 8, Math.PI);
      const swm = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
      const swp = L(nu, F - 0.08);
      swm.setPosition(swp[0], swp[1], 5.3);
      batch.addGeometry(stoneShade, sw, swm);
      sw.dispose();
    }
    // entablature and cornice
    const rect = (w, d, dv = 0) => [
      L(-w / 2, -d / 2 + dv),
      L(w / 2, -d / 2 + dv),
      L(w / 2, d / 2 + dv),
      L(-w / 2, d / 2 + dv),
    ];
    kit.cornice(batch, stoneShade, rect(Wd, D), H, { height: 0.3, projection: 0.15 });
    kit.cornice(batch, stone, rect(Wd, D), H + ENT - 0.35, {
      height: 0.35,
      projection: 0.45,
      steps: 2,
    });
    kit.cap(batch, lead, [[rect(Wd, D)]], H + ENT);
    // pediment on the front: gabled lead roof running front-to-back
    const rise = 2.0;
    kit.pitchedRoof(
      batch,
      lead,
      stone,
      rect(Wd + 0.6, D + 0.6),
      Math.atan2(V[1], V[0]),
      H + ENT,
      rise,
      'gabled',
      {
        overhang: 0.05,
      },
    );
    // raking cornices of the pediment
    for (const su of [-1, 1]) {
      const a = L((su * (Wd + 0.8)) / 2, F - 0.35),
        b = L(0, F - 0.35);
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const geo = new THREE.BoxGeometry(Math.hypot(len, rise), 0.5, 0.3);
      const m = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationY(su * Math.atan2(rise, len)));
      const mid = L((su * (Wd + 0.8)) / 4, F - 0.35);
      m.setPosition(mid[0], mid[1], H + ENT + rise / 2 + 0.1);
      batch.addGeometry(stoneShade, geo, m);
      geo.dispose();
    }
    // cartouche in the tympanum
    lbox(stoneShade, 0, F - 0.32, H + ENT + 0.35, 1.0, 0.15, 0.9);

    g.add(batch.toGroup('queen_annes_alcove'));
    return g;
  },
};
