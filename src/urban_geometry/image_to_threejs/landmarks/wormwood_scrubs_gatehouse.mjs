// Gatehouse of HM Prison Wormwood Scrubs, Du Cane Road (Sir Edmund Du Cane,
// built by convict labour 1874-91; Grade II*). A round-arched gateway flanked by
// a pair of symmetrical octagonal towers "in the manner of a medieval
// gatehouse", in red-brown brick with Portland stone bands and dressings; each
// tower's upper stage has a moulded frieze, shallow blind arcading and a
// cornice under an octagonal tiled roof, and carries a terracotta roundel with
// the bust of a prison reformer (John Howard, Elizabeth Fry). Lower brick lodge
// ranges sit behind and either side.
export default {
  id: 'wormwood_scrubs_gatehouse',
  name: 'Wormwood Scrubs prison gatehouse',
  claims: ['9a58d31d-e450-45e7-bf6e-c057663674fc'],
  references: [
    {
      title: 'HM Prison Wormwood Scrubs - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/HM_Prison_Wormwood_Scrubs',
      used_for:
        'Du Cane design, convict-built 1874-91, Howard and Fry medallions on the gate towers',
    },
    {
      title: 'Gatehouse at HMP Wormwood Scrubs - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101393182',
      used_for:
        'red-brown brick in English bond, Portland stone, terracotta medallions, octagonal towers, frieze, blind arcade, cornice, octagonal tile roof',
    },
    {
      title: 'The gatehouse at HMP Wormwood Scrubs - Historic England',
      url: 'https://live.historicengland.org.uk/images-books/photos/item/DES01/23/09/06',
      used_for: 'photo record title confirming the twin-tower gatehouse',
    },
    {
      title: 'Listed Building Status for Wormwood Scrubs',
      url: 'https://fulhamsw6.com/page/shared/common/sbwormwoodscrubs1.htm',
      used_for: 'Grade II* chapel and gatehouse; terracotta busts of John Howard and Elizabeth Fry',
    },
    {
      title: 'Wormwood Scrubs, Hammersmith - The Prison',
      url: 'https://theprison.org.uk/LondonWormwood/',
      used_for: 'context for the Du Cane gatehouse and its towers',
    },
  ],
  notes:
    'Plan from the Overture "Gate Lodge" outline (tower bays, gateway, rear lodges). Tower height (21 m to ' +
    'cornice, 26 m to finial), gateway height, band spacing and roof tile colour are estimates. Modelled in 3D: ' +
    'round-arched entrance cut through the gateway wall with alternating stone voussoirs, slender shafts with ' +
    'capitals, stone soffit, recessed strapped timber gates with wicket, heavy corbel table under a flat moulded ' +
    'parapet (per the listing); octagonal towers in English-bond brick with stone bands, narrow round-headed ' +
    'windows, a corbel table and colonnettes on the blind-arcaded upper stage, hip rolls on the tiled roofs; ' +
    'lodges with round-headed sash windows and chimney stacks. The busts are simplified terracotta reliefs, window ' +
    'counts and the flagpole are assumptions; the prison perimeter wall is not modelled (no footprint)',
  build({ THREE, kit, byId, placeAssets }) {
    const g = new THREE.Group();
    const O = [-2758, 1094],
      A = (5.6 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    // u: east along Du Cane Road, v: north into the prison; front faces -v (south)
    const W = (u, v) => [O[0] + u * ca - v * sa, O[1] + u * sa + v * ca];
    const b = new kit.MeshBatch();
    const add = (geo, m, u, v, z, rot = 0) => {
      const [x, y] = W(u, v);
      b.addGeometry(m, geo, new THREE.Matrix4().makeRotationZ(A + rot).setPosition(x, y, z));
      geo.dispose();
    };
    const box = (u, v, z0, du, dv, h, m) => {
      const [x, y] = W(u, v);
      kit.box(b, m, x, y, z0, du, dv, h, A);
    };
    const stone = kit.mat('portland_stone');
    const tile = kit.mat('#8a4632', { roughness: 0.8 });
    const dark = kit.mat('#1d2226');
    const terracotta = kit.mat('#b5683f');
    // upper stage: frieze + blind arcade per octagon face
    const upperM = kit.paintedMaterial('wormwood_scrubs_gatehouse:upper', 512, 128, (c, w, h) => {
      c.fillStyle = '#8b4a35';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#ddd6c4';
      c.fillRect(0, 0, w, 14);
      c.fillRect(0, h - 12, w, 12);
      for (let k = 0; k < 8; k++) {
        const x0 = (k * w) / 8;
        for (let j = 0; j < 3; j++) {
          const ax = x0 + 8 + j * ((w / 8 - 16) / 3),
            aw = (w / 8 - 16) / 3 - 4;
          c.fillStyle = '#6d3728';
          c.beginPath();
          c.moveTo(ax, h - 16);
          c.lineTo(ax, 44);
          c.arc(ax + aw / 2, 44, aw / 2, Math.PI, 0);
          c.lineTo(ax + aw, h - 16);
          c.fill();
        }
      }
      c.fillStyle = '#c9c1ad';
      for (let x = 0; x < w; x += 8) c.fillRect(x, 16, 5, 8); // dentil frieze
    });

    // --- shared detailing -------------------------------------------------------------
    const plainBrick = kit.paintedMaterial(
      'wormwood_scrubs_gatehouse:brick',
      256,
      256,
      (c, w, hh) => {
        const r = kit.rng(0.83);
        c.fillStyle = '#7a3f2e';
        c.fillRect(0, 0, w, hh);
        // English bond: alternate courses of headers and stretchers (one tile = 4 m)
        for (let y = 0, row = 0; y < hh; y += 4.75, row++)
          for (let x = row % 2 ? -3 : 0; x < w; x += row % 2 ? 6 : 12) {
            c.fillStyle = `rgba(${120 + r() * 40},${55 + r() * 20},${40 + r() * 15},0.9)`;
            c.fillRect(x, y, row % 2 ? 5 : 11, 4);
          }
      },
    );
    const timber = kit.mat('#3b2a20', { roughness: 0.8 });
    const iron = kit.mat('#23272a', { roughness: 0.5, metalness: 0.5 });
    const glassW = kit.mat('#2a343a', { roughness: 0.15, metalness: 0.3 });
    const sashW = kit.mat('#ece8de');
    const X3 = (u, v, z) => {
      const [x, y] = W(u, v);
      return new THREE.Vector3(x, y, z);
    };
    const uW = new THREE.Vector3(ca, sa, 0),
      vW = new THREE.Vector3(-sa, ca, 0),
      zW = new THREE.Vector3(0, 0, 1);
    // geometry authored in a facade plane (x along u, y up, z out of the front, i.e. -v)
    const onFront = (geo, m, u, v, z) => {
      const mx = new THREE.Matrix4()
        .makeBasis(uW, zW, vW.clone().negate())
        .setPosition(X3(u, v, z));
      b.addGeometry(m, geo, mx);
      geo.dispose();
    };
    // kit.windowRow with round heads as vertical glass sectors and stone archivolts
    const archRow = (a, c, z, opts) => {
      const cs = kit.windowRow(b, a, c, z, { ...opts, head: 'none' });
      const w = opts.width,
        h = opts.height,
        d = opts.depth ?? 0.12;
      const L = Math.hypot(c[0] - a[0], c[1] - a[1]);
      const X = new THREE.Vector3((c[0] - a[0]) / L, (c[1] - a[1]) / L, 0),
        Z = new THREE.Vector3(X.y, -X.x, 0);
      const gl = new THREE.CircleGeometry(w / 2, 10, 0, Math.PI);
      const tor = new THREE.TorusGeometry(w / 2 + 0.08, 0.1, 4, 10, Math.PI);
      const m = new THREE.Matrix4();
      for (const [cx, cy] of cs) {
        m.makeBasis(X, zW, Z).setPosition(cx + Z.x * 0.03, cy + Z.y * 0.03, z + h);
        b.addGeometry(opts.glass, gl, m);
        m.makeBasis(X, zW, Z).setPosition(cx + Z.x * d * 0.8, cy + Z.y * d * 0.8, z + h);
        b.addGeometry(opts.sill, tor, m);
      }
      gl.dispose();
      tor.dispose();
    };

    // --- Lodge ranges (rest of the outline) -------------------------------------
    const ring = byId['9a58d31d-e450-45e7-bf6e-c057663674fc'].polys[0][0];
    const toL = ([x, y]) => [(x - O[0]) * ca + (y - O[1]) * sa, -(x - O[0]) * sa + (y - O[1]) * ca];
    const hidden = (p) => {
      const [u, v] = toL(p);
      return v < -7.9 && u > -9 && u < 10;
    };
    const ringC = kit.ringArea(ring) < 0 ? ring.slice().reverse() : ring;
    const band = kit.offsetRing(ringC, 0.15);
    for (let k = 0; k < ringC.length; k++) {
      const k1 = (k + 1) % ringC.length;
      if (hidden(ringC[k]) && hidden(ringC[k1])) continue;
      const a = ringC[k],
        c = ringC[k1];
      const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
      kit.walls(b, plainBrick, [[[a, c]]], 0, 8.5, { bay: 4, storey: 2 });
      kit.walls(b, stone, [[[band[k], band[k1]]]], 8.0, 8.6);
      kit.walls(b, stone, [[[band[k], band[k1]]]], 0, 0.5);
      kit.walls(b, stone, [[[band[k], band[k1]]]], 4.0, 4.25);
      if (len > 3.5)
        for (const z of [1.1, 4.8])
          archRow(a, c, z, {
            bay: 2.6,
            margin: 0.7,
            width: 1.0,
            height: 1.9,
            bars: 2,
            glass: glassW,
            frame: sashW,
            sill: stone,
            depth: 0.14,
          });
    }
    kit.cap(b, kit.mat('#5a5f63'), [[ringC]], 8.6);
    // brick chimney stacks with stone caps on the lodge roofs
    for (const [cu, cv] of [
      [-12.5, 0],
      [11.5, 2],
      [11.5, 8.5],
      [-4, 9.5],
    ]) {
      box(cu, cv, 8.6, 1.0, 2.2, 2.4, plainBrick);
      box(cu, cv, 11.0, 1.3, 2.5, 0.3, stone);
      for (const dv of [-0.6, 0, 0.6])
        add(
          new THREE.CylinderGeometry(0.16, 0.2, 0.7, 8).rotateX(Math.PI / 2),
          kit.mat('#9a5236'),
          cu,
          cv + dv,
          11.65,
        );
    }

    // --- Gateway block between the towers --------------------------------------
    const gu0 = -2.6,
      gu1 = 3.6,
      gv0 = -9.2,
      gv1 = -1.5,
      GH = 14;
    const gc = (gu0 + gu1) / 2;
    const AR = 2.3,
      SPR = 5.6; // arch radius and springing height
    box(gc, (gv0 + gv1) / 2 + 0.6, 0, gu1 - gu0, gv1 - gv0 - 1.2, GH, plainBrick);
    {
      // front wall with the round-arched opening cut out (shape in the facade plane)
      const sh = new THREE.Shape();
      const hw = (gu1 - gu0) / 2;
      sh.moveTo(-hw, 0);
      sh.lineTo(hw, 0);
      sh.lineTo(hw, GH);
      sh.lineTo(-hw, GH);
      sh.lineTo(-hw, 0);
      const hole = new THREE.Path();
      hole.moveTo(-AR, 0);
      hole.lineTo(-AR, SPR);
      hole.absarc(0, SPR, AR, Math.PI, 0, true);
      hole.lineTo(AR, 0);
      hole.lineTo(-AR, 0);
      sh.holes.push(hole);
      const fg = new THREE.ExtrudeGeometry(sh, {
        depth: 1.2,
        bevelEnabled: false,
        curveSegments: 16,
      });
      fg.translate(0, 0, -1.2);
      const uv = fg.attributes.uv;
      for (let k = 0; k < uv.count; k++) uv.setXY(k, uv.getX(k) / 4, uv.getY(k) / 4);
      onFront(fg, plainBrick, gc, gv0, 0);
      // stone voussoirs alternating with brick, keystone, impost blocks
      for (let k = 0; k < 13; k++) {
        const a0 = Math.PI - (k / 13) * Math.PI,
          a1 = Math.PI - ((k + 1) / 13) * Math.PI;
        const ex = new THREE.ExtrudeGeometry(
          new THREE.Shape([
            new THREE.Vector2(Math.cos(a0) * AR, Math.sin(a0) * AR),
            new THREE.Vector2(
              Math.cos(a0) * (AR + (k % 2 ? 0.6 : 0.8)),
              Math.sin(a0) * (AR + (k % 2 ? 0.6 : 0.8)),
            ),
            new THREE.Vector2(
              Math.cos(a1) * (AR + (k % 2 ? 0.6 : 0.8)),
              Math.sin(a1) * (AR + (k % 2 ? 0.6 : 0.8)),
            ),
            new THREE.Vector2(Math.cos(a1) * AR, Math.sin(a1) * AR),
          ]),
          { depth: 0.12, bevelEnabled: false },
        );
        onFront(ex, k === 6 ? stone : k % 2 ? kit.mat('#c9c0aa') : stone, gc, gv0, SPR);
      }
      for (const s2 of [-1, 1]) {
        box(gc + s2 * (AR + 0.35), gv0 - 0.08, SPR - 0.4, 0.9, 0.3, 0.45, stone); // impost
        // slender shafts with capitals and bases in the reveals
        add(
          new THREE.CylinderGeometry(0.14, 0.14, SPR - 0.9, 10).rotateX(Math.PI / 2),
          kit.mat('#8f8a82', { roughness: 0.4 }),
          gc + s2 * (AR + 0.12),
          gv0 - 0.12,
          0.45 + (SPR - 0.9) / 2,
        );
        box(gc + s2 * (AR + 0.12), gv0 - 0.12, SPR - 0.45, 0.42, 0.42, 0.3, stone);
        box(gc + s2 * (AR + 0.12), gv0 - 0.12, 0, 0.42, 0.42, 0.45, stone);
      }
      // arch soffit (half cylinder) and jambs through the wall thickness
      onFront(
        new THREE.CylinderGeometry(AR, AR, 1.2, 16, 1, true, Math.PI / 2, Math.PI).rotateX(
          Math.PI / 2,
        ),
        kit.mat('portland_stone', { side: THREE.DoubleSide }),
        gc,
        gv0 + 0.6,
        SPR,
      );
      for (const s2 of [-1, 1]) box(gc + s2 * (AR + 0.05), gv0 + 0.6, 0, 0.1, 1.2, SPR, stone);
      // recessed timber gates with iron straps and a wicket door
      box(gc, gv0 + 1.15, 0, 2 * AR, 0.15, SPR, timber);
      const tymp = new THREE.CircleGeometry(AR, 16, 0, Math.PI);
      onFront(tymp, timber, gc, gv0 + 1.07, SPR);
      for (let z = 0.8; z < SPR + 1.5; z += 1.3) {
        const wz =
          z < SPR ? 2 * AR - 0.1 : 2 * Math.sqrt(Math.max(0, AR * AR - (z - SPR) ** 2)) - 0.2;
        if (wz > 0.3) box(gc, gv0 + 1.05, z, wz, 0.06, 0.12, iron);
      }
      for (let u = gc - AR + 0.3; u < gc + AR; u += 0.32)
        box(u, gv0 + 1.06, 0, 0.03, 0.04, SPR, kit.mat('#2a1e17'));
      box(gc, gv0 + 1.05, 0, 0.08, 0.08, SPR + AR - 0.1, iron);
      box(gc + 1.0, gv0 + 1.03, 0, 1.0, 0.04, 2.1, kit.mat('#2e2219'));
    }
    // string course, panel and the heavy corbel table under a flat moulded parapet
    box(gc, gv0 - 0.12, 9.0, gu1 - gu0 + 0.2, 0.3, 0.35, stone);
    box(gc, gv0 - 0.05, 9.7, 3.2, 0.12, 1.4, kit.mat('#c9c0aa')); // tablet
    for (let u = gu0 + 0.35; u < gu1 - 0.2; u += 0.7) {
      box(u, gv0 - 0.25, 11.2, 0.36, 0.5, 0.35, stone);
      box(u, gv0 - 0.4, 11.55, 0.36, 0.8, 0.35, stone);
    }
    box(gc, gv0 - 0.45, 11.9, gu1 - gu0 + 0.6, 0.9, 0.35, stone);
    box(gc, gv0 - 0.25, 12.25, gu1 - gu0 + 0.5, 0.5, GH - 12.65, plainBrick);
    box(gc, (gv0 + gv1) / 2 - 0.25, GH - 0.4, gu1 - gu0 + 0.7, gv1 - gv0 + 0.5, 0.25, stone);
    box(gc, (gv0 + gv1) / 2 - 0.25, GH - 0.15, gu1 - gu0 + 0.9, gv1 - gv0 + 0.7, 0.45, stone);
    box(gc, (gv0 + gv1) / 2, GH + 0.3, gu1 - gu0 + 0.4, gv1 - gv0 + 0.2, 0.3, kit.mat('#5a5f63'));
    // flagpole on the gateway parapet
    add(
      new THREE.CylinderGeometry(0.05, 0.08, 6, 8).rotateX(Math.PI / 2),
      kit.mat('white'),
      gc,
      (gv0 + gv1) / 2,
      GH + 3.3,
    );

    // --- Twin octagonal towers -----------------------------------------------------
    const R = 3.85,
      TH = 18,
      UP = 3.2;
    const oct = (r, h) =>
      new THREE.CylinderGeometry(r, r, h, 8, 1, false, Math.PI / 8).rotateX(Math.PI / 2);
    // octagon face k (k = 0 faces Du Cane Road) as a local edge a -> c, outward on the right
    const face = (tu, tv, k, r) => {
      const t1 = (k * Math.PI) / 4 - Math.PI / 8,
        t2 = (k * Math.PI) / 4 + Math.PI / 8;
      return [
        W(tu + r * Math.sin(t1), tv - r * Math.cos(t1)),
        W(tu + r * Math.sin(t2), tv - r * Math.cos(t2)),
      ];
    };
    const ap = R * Math.cos(Math.PI / 8);
    for (const [tu, tv, side] of [
      [-5.0, -7.25, -1],
      [6.1, -7.25, 1],
    ]) {
      // octagonal brick shaft with brick texture mapped per metre
      const shaft = oct(R, TH);
      const uv = shaft.attributes.uv;
      for (let k = 0; k < uv.count; k++)
        uv.setXY(k, uv.getX(k) * ((2 * Math.PI * R) / 4), (uv.getY(k) * TH) / 4);
      add(shaft, plainBrick, tu, tv, TH / 2);
      add(oct(R + 0.3, 0.9), stone, tu, tv, 0.45); // plinth
      for (const z of [3.4, 7.0, 13.8]) add(oct(R + 0.1, 0.32), stone, tu, tv, z); // stone bands
      add(oct(R + 0.2, 0.6), stone, tu, tv, TH + 0.3);
      add(oct(R, UP), upperM, tu, tv, TH + 0.6 + UP / 2);
      // corbel table under the cornice on every face
      for (let k = 0; k < 8; k++) {
        const th = (k * Math.PI) / 4;
        for (let j = -2; j <= 2; j++) {
          const tt = th + (j * Math.PI) / 4 / 5.5;
          const rr = ap / Math.cos(tt - th);
          add(
            new THREE.BoxGeometry(0.3, 0.45, 0.4).rotateZ(tt),
            stone,
            tu + (rr + 0.15) * Math.sin(tt),
            tv - (rr + 0.15) * Math.cos(tt),
            TH + 0.6 + UP - 0.2,
          );
        }
        // blind arcade colonnettes on the upper stage
        const [a, c] = face(tu, tv, k, R + 0.05);
        for (let j = 0; j <= 3; j++) {
          const t = 0.12 + (0.76 * j) / 3;
          kit.box(
            b,
            stone,
            a[0] + (c[0] - a[0]) * t,
            a[1] + (c[1] - a[1]) * t,
            TH + 0.75,
            0.12,
            0.12,
            UP - 1.0,
            A + th,
          );
        }
      }
      add(oct(R + 0.6, 0.8), stone, tu, tv, TH + 0.6 + UP + 0.4); // cornice
      const z0 = TH + 0.6 + UP + 0.8;
      add(
        new THREE.ConeGeometry(R + 0.45, 4.6, 8, 1, false, Math.PI / 8).rotateX(Math.PI / 2),
        tile,
        tu,
        tv,
        z0 + 2.3,
      );
      // hip rolls along the eight arrises of the roof
      for (let k = 0; k < 8; k++) {
        const t = (k * Math.PI) / 4 + Math.PI / 8;
        const p = X3(tu + (R + 0.45) * Math.sin(t), tv - (R + 0.45) * Math.cos(t), z0);
        const q = X3(tu, tv, z0 + 4.6);
        const g2 = new THREE.CylinderGeometry(0.07, 0.07, p.distanceTo(q), 5);
        const mid = p.clone().add(q).multiplyScalar(0.5);
        const quat = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          q.clone().sub(p).normalize(),
        );
        b.addGeometry(
          kit.mat('#6b3324'),
          g2,
          new THREE.Matrix4().compose(mid, quat, new THREE.Vector3(1, 1, 1)),
        );
        g2.dispose();
      }
      add(
        new THREE.CylinderGeometry(0.06, 0.12, 1.6, 6).rotateX(Math.PI / 2),
        kit.mat('dark_steel'),
        tu,
        tv,
        z0 + 5.2,
      );
      add(new THREE.SphereGeometry(0.22, 8, 6), kit.mat('dark_steel'), tu, tv, z0 + 4.7);
      // narrow round-headed windows with stone dressings on the outer faces
      for (const k of [0, side, 2 * side]) {
        const [a, c] = face(tu, tv, k, R);
        for (const z of [1.6, 4.4, 8.0, 14.6]) {
          if (k === 0 && z === 8.0) continue; // roundel stage on the road face
          if (k === 2 * side && z < 8) continue; // lower side faces abut the lodges
          archRow(a, c, z, {
            count: 1,
            margin: 0.4,
            width: 0.55,
            height: z === 14.6 ? 2.0 : 1.9,
            bars: 0,
            glass: dark,
            frame: stone,
            sill: stone,
            depth: 0.14,
          });
        }
      }
      // terracotta reformer roundel facing Du Cane Road, framed in stone
      const fr = R * Math.cos(Math.PI / 8);
      add(new THREE.CylinderGeometry(1.25, 1.25, 0.22, 20), stone, tu, tv - fr - 0.1, 11.5);
      add(
        new THREE.TorusGeometry(1.3, 0.12, 6, 24).rotateX(Math.PI / 2),
        stone,
        tu,
        tv - fr - 0.2,
        11.5,
      );
      add(new THREE.CylinderGeometry(1.0, 1.0, 0.3, 20), terracotta, tu, tv - fr - 0.15, 11.5);
      add(
        new THREE.SphereGeometry(0.5, 10, 8).scale(0.8, 0.45, 1.05),
        kit.mat('#c98658'),
        tu,
        tv - fr - 0.3,
        11.6,
      );
      add(
        new THREE.SphereGeometry(0.55, 10, 6).scale(1.1, 0.35, 0.5),
        kit.mat('#c98658'),
        tu,
        tv - fr - 0.25,
        10.95,
      ); // shoulders
    }

    // --- Forecourt on Du Cane Road ---------------------------------------------
    if (placeAssets) {
      const hd = Math.atan2(-sa, -ca); // arm towards the road (-v)
      g.add(
        placeAssets(
          'street_lamp',
          [
            [...W(-12, -13), hd],
            [...W(13, -13), hd],
          ],
          { name: 'wormwood_scrubs_gatehouse:lamps' },
        ),
      );
      g.add(
        placeAssets(
          'bollard',
          [-1.6, -0.6, 1.7, 2.7].map((u) => [...W(u, -12.4), hd]),
          { name: 'wormwood_scrubs_gatehouse:bollards' },
        ),
      );
    }
    g.add(b.toGroup('wormwood_scrubs_gatehouse'));
    return g;
  },
};
