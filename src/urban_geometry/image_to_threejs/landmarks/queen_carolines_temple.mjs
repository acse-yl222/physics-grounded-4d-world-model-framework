// Queen Caroline's Temple, Kensington Gardens (William Kent, 1734-35). A small
// Palladian summer house of Bath stone near the Long Water: single storey, three bays,
// each with a rusticated arched recess and its own pediment, the centre bay raised with
// an attic; open on the east face; apses with leaded semidomes on the side returns and
// low-pitched slate roofs.
export default {
  id: 'queen_carolines_temple',
  name: "Queen Caroline's Temple",
  claims: ['3de42fa5-2432-4a0a-a735-88fb5d9ce7f8'],
  references: [
    {
      title: 'The Temple - British Listed Buildings (Historic England list entry)',
      url: 'https://britishlistedbuildings.co.uk/101275724-the-temple-knightsbridge-and-belgravia-ward',
      used_for:
        'single storey, three bays each with rusticated arched recess and pediment, centre bay higher with attic, open east face, apses with leaded semidomes on the returns, Bath stone, low pitched polygonal slate roof',
    },
    {
      title: "Treasures of London - Queen Caroline's Temple - Exploring London",
      url: 'https://exploring-london.com/2014/11/21/treasures-of-london-queen-carolines-temple/',
      used_for:
        'William Kent design of 1734-35, sight lines from the Round Pond avenues, restoration in 1976',
    },
    {
      title: "Queen Caroline's Temple - VoiceMap",
      url: 'https://voicemap.me/tour/london/hyde-park-and-kensington-gardens-royalty-relaxation-and-rebellion/sites/queen-caroline-s-temple',
      used_for: 'setting beside the Long Water, summer-house use',
    },
  ],
  notes:
    'Footprint (11.4 x 4.2 m with the centre bay projecting) is followed in plan; heights (4.6 m to the side-bay ' +
    'cornices, 6.0 m to the attic cornice, pediments 1.0 / 1.2 m) are proportioned from the listing, not ' +
    'measured (Overture h=12.6 m is far too high). Rustication is a painted texture on the arched faces; apse ' +
    'size and the hipped forms of the "polygonal" roofs are estimates.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const S = [1695.85, -15.65],
      N = [1698.25, -4.45];
    const len = Math.hypot(N[0] - S[0], N[1] - S[1]);
    const U = [(N[0] - S[0]) / len, (N[1] - S[1]) / len];
    const E = [U[1], -U[0]]; // outward to the east (open front)
    const C = [(S[0] + N[0]) / 2, (S[1] + N[1]) / 2];
    const ang = Math.atan2(U[1], U[0]);
    const L = (u, w) => [C[0] + U[0] * u + E[0] * w, C[1] + U[1] * u + E[1] * w];
    const lbox = (m, u, w, z0, du, dw, h) => {
      const p = L(u, w);
      kit.box(batch, m, p[0], p[1], z0, du, dw, h, ang);
    };

    const stone = kit.mat('bath_stone');
    const stoneShade = kit.mat('#c9b68f', { roughness: 0.85 });
    const rust = kit.paintedMaterial(
      'queen_carolines_temple:rustication',
      128,
      128,
      (c, w, h) => {
        c.fillStyle = '#d9c79e';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#a89470';
        for (let k = 0; k < 2; k++) {
          c.fillRect(0, (k * h) / 2, w, 4);
          const x = k % 2 ? w / 2 : 0;
          c.fillRect(x, (k * h) / 2, 3, h / 2);
        }
      },
      { roughness: 0.85 },
    );
    const slate = kit.mat('slate');
    const lead = kit.mat('lead');
    const dark = kit.mat('#4e4a42', { roughness: 0.9 });
    const floor = kit.mat('#bfb39a');

    const SIDE_H = 4.6,
      ATTIC_H = 6.0,
      T = 0.45;
    const blocks = [
      { u0: -4.9, u1: -1.9, w: 2.1, top: SIDE_H, rise: 1.0, archW: 1.7, spring: 2.5 },
      { u0: -1.9, u1: 1.9, w: 2.9, top: ATTIC_H, rise: 1.2, archW: 2.3, spring: 3.0 },
      { u0: 1.9, u1: 4.9, w: 2.1, top: SIDE_H, rise: 1.0, archW: 1.7, spring: 2.5 },
    ];
    // plinth
    lbox(stone, 0, 0, 0, 11.6, 6.2, 0.3);
    kit.cap(batch, floor, [[[L(-4.9, -2.1), L(4.9, -2.1), L(4.9, 2.1), L(-4.9, 2.1)]]], 0.32);

    // arched slab in the u-z plane at offset w (faces +E when sgn=1, -E when -1)
    const archSlab = (B, w, sgn, open) => {
      const W = B.u1 - B.u0,
        r = B.archW / 2;
      const sh = new THREE.Shape();
      sh.moveTo(-W / 2, 0.3);
      if (open) {
        sh.lineTo(-r, 0.3);
        sh.lineTo(-r, B.spring);
        for (let i = 0; i <= 12; i++) {
          const a = Math.PI - (i / 12) * Math.PI;
          sh.lineTo(r * Math.cos(a), B.spring + r * Math.sin(a));
        }
        sh.lineTo(r, 0.3);
      }
      sh.lineTo(W / 2, 0.3);
      sh.lineTo(W / 2, B.top);
      sh.lineTo(-W / 2, B.top);
      sh.closePath();
      const geo = new THREE.ExtrudeGeometry(sh, {
        depth: T,
        bevelEnabled: false,
        curveSegments: 6,
      });
      const ax = sgn > 0 ? U : [-U[0], -U[1]];
      const out = sgn > 0 ? E : [-E[0], -E[1]];
      const m = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(ax[0], ax[1], 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(out[0], out[1], 0),
      );
      const uc = (B.u0 + B.u1) / 2;
      const p = L(uc, w - sgn * T);
      m.setPosition(p[0], p[1], 0);
      batch.addGeometry(rust, geo, m);
      geo.dispose();
      // archivolt & keystone, impost band
      const tor = new THREE.TorusGeometry(r + 0.1, 0.1, 4, 12, Math.PI);
      const tm = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      const tp = L(uc, w + sgn * 0.04);
      tm.setPosition(tp[0], tp[1], B.spring);
      batch.addGeometry(stoneShade, tor, tm);
      tor.dispose();
      lbox(stoneShade, uc, w + sgn * 0.08, B.spring + r - 0.1, 0.4, 0.2, 0.5);
      if (!open) {
        // blind recess
        const recess = new THREE.Shape();
        recess.moveTo(-r, 0.3);
        recess.lineTo(-r, B.spring);
        for (let i = 0; i <= 10; i++) {
          const a = Math.PI - (i / 10) * Math.PI;
          recess.lineTo(r * Math.cos(a), B.spring + r * Math.sin(a));
        }
        recess.lineTo(r, 0.3);
        recess.closePath();
        const rg = new THREE.ShapeGeometry(recess, 4);
        const m2 = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(ax[0], ax[1], 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(out[0], out[1], 0),
        );
        const p2 = L(uc, w + sgn * 0.01);
        m2.setPosition(p2[0], p2[1], 0);
        batch.addGeometry(dark, rg, m2);
        rg.dispose();
      }
    };
    // pediment: triangular prism on the face at offset w
    const pediment = (B, w, sgn) => {
      const W = B.u1 - B.u0 + 0.3;
      const tri = new THREE.Shape([
        new THREE.Vector2(-W / 2, 0),
        new THREE.Vector2(W / 2, 0),
        new THREE.Vector2(0, B.rise),
      ]);
      const geo = new THREE.ExtrudeGeometry(tri, { depth: 0.9, bevelEnabled: false });
      const ax = sgn > 0 ? U : [-U[0], -U[1]];
      const out = sgn > 0 ? E : [-E[0], -E[1]];
      const m = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(ax[0], ax[1], 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(out[0], out[1], 0),
      );
      const p = L((B.u0 + B.u1) / 2, w + sgn * 0.25 - sgn * 0.9);
      m.setPosition(p[0], p[1], B.top + 0.35);
      batch.addGeometry(stone, geo, m);
      geo.dispose();
    };

    for (const B of blocks) {
      const uc = (B.u0 + B.u1) / 2,
        W = B.u1 - B.u0;
      archSlab(B, B.w, 1, true);
      archSlab(B, -B.w, -1, false);
      // end walls of the block
      for (const ue of [B.u0 + T / 2, B.u1 - T / 2])
        lbox(stone, ue, 0, 0.3, T, 2 * B.w, B.top - 0.3);
      // cornice and roof
      const ring = [L(B.u0, -B.w), L(B.u1, -B.w), L(B.u1, B.w), L(B.u0, B.w)];
      kit.cornice(batch, stoneShade, ring, B.top, { height: 0.35, projection: 0.25, steps: 2 });
      kit.pitchedRoof(
        batch,
        slate,
        stone,
        ring,
        ang + Math.PI / 2,
        B.top + 0.35,
        B.rise * 0.9,
        'hipped',
        {
          overhang: 0.1,
        },
      );
      pediment(B, B.w, 1);
      pediment(B, -B.w, -1);
      // attic band on the raised centre bay
      if (B.top > SIDE_H) {
        lbox(stoneShade, uc, B.w + 0.05, SIDE_H, W, 0.15, 0.3);
        lbox(stoneShade, uc, -B.w - 0.05, SIDE_H, W, 0.15, 0.3);
        // attic panel
        lbox(stoneShade, uc, B.w + 0.04, SIDE_H + 0.45, W * 0.6, 0.1, 0.8);
      }
    }
    // apses with leaded semidomes on the north and south returns
    for (const su of [-1, 1]) {
      const p = L(su * 4.9, 0);
      const r = 1.3,
        h = 3.4;
      const rz = Math.atan2(U[1], U[0]) + (su > 0 ? -Math.PI / 2 : Math.PI / 2);
      const m = new THREE.Matrix4().makeRotationZ(rz).setPosition(p[0], p[1], 0);
      const cyl = new THREE.CylinderGeometry(r, r, h - 0.3, 16, 1, false, Math.PI / 2, Math.PI)
        .rotateX(Math.PI / 2)
        .translate(0, 0, 0.3 + (h - 0.3) / 2);
      batch.addGeometry(stone, cyl, m);
      cyl.dispose();
      const dome = new THREE.SphereGeometry(r + 0.08, 16, 5, Math.PI, Math.PI, 0, Math.PI / 2)
        .rotateX(Math.PI / 2)
        .translate(0, 0, h);
      batch.addGeometry(lead, dome, m);
      dome.dispose();
      const band = new THREE.CylinderGeometry(
        r + 0.12,
        r + 0.12,
        0.25,
        16,
        1,
        false,
        Math.PI / 2,
        Math.PI,
      )
        .rotateX(Math.PI / 2)
        .translate(0, 0, h - 0.12);
      batch.addGeometry(stoneShade, band, m);
      band.dispose();
    }
    // steps in front of the open east face
    lbox(stone, 0, 3.3, 0, 4.4, 0.8, 0.16);

    g.add(batch.toGroup('queen_carolines_temple'));
    return g;
  },
};
