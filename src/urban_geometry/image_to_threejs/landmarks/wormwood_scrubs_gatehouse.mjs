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
  ],
  notes:
    'Plan from the Overture "Gate Lodge" outline (tower bays, gateway, rear lodges). Tower height (21 m to ' +
    'cornice, 26 m to finial), gateway height, band spacing and roof tile colour are estimates; the busts are ' +
    'shown as plain terracotta roundels. Prison perimeter wall not modelled (no footprint).',
  build({ THREE, kit, byId }) {
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
    const brickTex = (key, h, slits) =>
      kit.paintedMaterial(key, 512, 512, (c, w, hh) => {
        const r = kit.rng(0.55);
        c.fillStyle = '#8b4a35';
        c.fillRect(0, 0, w, hh);
        for (let y = 0; y < hh; y += 6)
          for (let x = (y / 6) % 2 ? 0 : -8; x < w; x += 16) {
            c.fillStyle = `rgba(${90 + r() * 50},${40 + r() * 20},${30 + r() * 15},0.55)`;
            c.fillRect(x, y, 15, 5);
          }
        // Portland stone bands every ~3 m
        c.fillStyle = '#ddd6c4';
        const per = hh / (h / 3);
        for (let y = hh; y > 0; y -= per) c.fillRect(0, y - 10, w, 10);
        if (slits) {
          c.fillStyle = '#1d2226';
          for (let k = 0; k < 8; k++) {
            if (k % 2) continue;
            const x = (k + 0.5) * (w / 8) - 6;
            for (let s = 1; s < h / 3 - 0.5; s += 2) {
              const y = hh - s * per - per * 0.75;
              c.fillRect(x, y, 12, per * 0.5);
              c.fillStyle = '#ddd6c4';
              c.fillRect(x - 3, y - 4, 18, 4);
              c.fillStyle = '#1d2226';
            }
          }
        }
      });
    const towerBrick = brickTex('wormwood_scrubs_gatehouse:tower', 18, true);
    const wallBrick = kit.facade('red_brick', 1);
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

    // --- Lodge ranges (rest of the outline) -------------------------------------
    const ring = byId['9a58d31d-e450-45e7-bf6e-c057663674fc'].polys[0][0];
    // walls of the outline except the tower bays and gate recess (modelled below)
    const toL = ([x, y]) => [(x - O[0]) * ca + (y - O[1]) * sa, -(x - O[0]) * sa + (y - O[1]) * ca];
    const hidden = (p) => {
      const [u, v] = toL(p);
      return v < -7.9 && u > -9 && u < 10;
    };
    const band = kit.offsetRing(ring, 0.15);
    for (let k = 0; k < ring.length; k++) {
      const k1 = (k + 1) % ring.length;
      if (hidden(ring[k]) && hidden(ring[k1])) continue;
      kit.walls(b, wallBrick, [[[ring[k], ring[k1]]]], 0, 8.5, { bay: 3.4, storey: 3.4 });
      kit.walls(b, stone, [[[band[k], band[k1]]]], 8.0, 8.6);
    }
    kit.cap(b, kit.mat('#5a5f63'), [[ring]], 8.6);

    // --- Gateway block between the towers --------------------------------------
    const gu0 = -2.6,
      gu1 = 3.6,
      gv0 = -9.2,
      gv1 = -1.5,
      GH = 14;
    box((gu0 + gu1) / 2, (gv0 + gv1) / 2, 0, gu1 - gu0, gv1 - gv0, GH, wallBrick);
    const gateFace = kit.paintedMaterial('wormwood_scrubs_gatehouse:gate', 256, 512, (c, w, h) => {
      c.fillStyle = '#8b4a35';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.2);
      for (let y = 0; y < h; y += 6)
        for (let x = (y / 6) % 2 ? 0 : -8; x < w; x += 16) {
          c.fillStyle = `rgba(${90 + r() * 50},${40 + r() * 20},${30 + r() * 15},0.5)`;
          c.fillRect(x, y, 15, 5);
        }
      const zy = (z) => h - (z / GH) * h;
      // stone voussoir arch with dark timber gates
      c.fillStyle = '#ddd6c4';
      c.beginPath();
      c.moveTo(22, h);
      c.lineTo(22, zy(6.0));
      c.arc(w / 2, zy(6.0), w / 2 - 22, Math.PI, 0);
      c.lineTo(w - 22, h);
      c.fill();
      c.fillStyle = '#3a2b22';
      c.beginPath();
      c.moveTo(44, h);
      c.lineTo(44, zy(6.0));
      c.arc(w / 2, zy(6.0), w / 2 - 44, Math.PI, 0);
      c.lineTo(w - 44, h);
      c.fill();
      c.fillStyle = '#251b16';
      for (let x = 52; x < w - 50; x += 18) c.fillRect(x, zy(8.5), 4, h - zy(8.5));
      c.fillRect(w / 2 - 2, zy(8.8), 4, h);
      // string course, panel and machicolated parapet band
      c.fillStyle = '#ddd6c4';
      c.fillRect(0, zy(10.4), w, 12);
      c.fillRect(0, zy(13.2), w, 14);
      c.fillStyle = '#6d3728';
      for (let x = 10; x < w; x += 34) c.fillRect(x, zy(12.9), 22, zy(10.8) - zy(12.9));
    });
    {
      const p = W(gu0, gv0 - 0.02),
        q = W(gu1, gv0 - 0.02);
      b.quad(
        gateFace,
        [p[0], p[1], 0],
        [q[0], q[1], 0],
        [q[0], q[1], GH],
        [p[0], p[1], GH],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    box((gu0 + gu1) / 2, (gv0 + gv1) / 2, GH, gu1 - gu0 + 0.6, gv1 - gv0 + 0.6, 0.6, stone);
    for (let u = gu0; u <= gu1 + 0.01; u += (gu1 - gu0) / 5)
      box(u, gv0, GH + 0.6, 0.7, 0.7, 0.9, stone); // crenellation

    // --- Twin octagonal towers -----------------------------------------------------
    const R = 3.85,
      TH = 18,
      UP = 3.2;
    const oct = (r, h) =>
      new THREE.CylinderGeometry(r, r, h, 8, 1, false, Math.PI / 8).rotateX(Math.PI / 2);
    for (const [tu, tv] of [
      [-5.0, -7.25],
      [6.1, -7.25],
    ]) {
      add(oct(R + 0.25, 1.2), stone, tu, tv, 0.6); // plinth
      add(oct(R, TH), towerBrick, tu, tv, TH / 2);
      add(oct(R + 0.2, 0.6), stone, tu, tv, TH + 0.3);
      add(oct(R, UP), upperM, tu, tv, TH + 0.6 + UP / 2);
      add(oct(R + 0.55, 0.8), stone, tu, tv, TH + 0.6 + UP + 0.4); // cornice
      const z0 = TH + 0.6 + UP + 0.8;
      add(
        new THREE.ConeGeometry(R + 0.45, 4.6, 8, 1, false, Math.PI / 8).rotateX(Math.PI / 2),
        tile,
        tu,
        tv,
        z0 + 2.3,
      );
      add(
        new THREE.CylinderGeometry(0.06, 0.12, 1.6, 6).rotateX(Math.PI / 2),
        kit.mat('dark_steel'),
        tu,
        tv,
        z0 + 5.2,
      );
      add(new THREE.SphereGeometry(0.22, 8, 6), kit.mat('dark_steel'), tu, tv, z0 + 4.7);
      // terracotta reformer roundel facing Du Cane Road, framed in stone
      const fr = R * Math.cos(Math.PI / 8);
      add(new THREE.CylinderGeometry(1.25, 1.25, 0.22, 20), stone, tu, tv - fr - 0.1, 11.5);
      add(new THREE.CylinderGeometry(1.0, 1.0, 0.3, 20), terracotta, tu, tv - fr - 0.15, 11.5);
      add(
        new THREE.SphereGeometry(0.5, 10, 8).scale(0.8, 0.45, 1.05),
        kit.mat('#c98658'),
        tu,
        tv - fr - 0.3,
        11.6,
      );
    }
    g.add(b.toGroup('wormwood_scrubs_gatehouse'));
    return g;
  },
};
