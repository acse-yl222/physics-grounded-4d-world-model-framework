// Fulham Broadway shopping centre, Fulham Road (opened 2002-03 over and beside Fulham
// Broadway station, whose ticket hall it now contains). About 200,000 sq ft anchored by
// Sainsbury's and a nine-screen Vue cinema on the first floor (opened as Warner Village
// in 2002). A large flat-roofed retail block with a glazed entrance on Fulham Road.
export default {
  id: 'fulham_broadway_centre',
  name: 'Fulham Broadway Centre',
  claims: ['7fb535a0-0f8e-4a1d-b01b-d19a16e07604'],
  references: [
    {
      title: 'Fulham Broadway tube station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Fulham_Broadway_tube_station',
      used_for:
        'shopping centre built over the station, new ticket hall opened 2003 with access through the centre',
    },
    {
      title: 'Vue Fulham Broadway - Cinema Treasures',
      url: 'https://www.cinematreasures.org/theaters/9875',
      used_for: 'cinema on the first floor, opened October 2002 as Warner Village, Vue from 2004',
    },
    {
      title: 'Fulham Broadway, Fulham SW6 1BW - GCW',
      url: 'https://gcw.co.uk/project/194/fulham-broadway-fulham-sw6-1bw',
      used_for: 'c. 200,000 sq ft, Sainsbury’s and nine-screen Vue as anchors',
    },
  ],
  notes:
    'No architectural description was found: the massing follows the Overture footprint at 14.8 m; the ' +
    'cladding (buff brick base, grey panel and glazed bands above), the double-height glazed entrance on ' +
    'Fulham Road, signage and roof plant are generic interpretations, not surveyed.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const H = 14.8;
    const brick = kit.mat('#b69a72', { roughness: 0.9 });
    const panel = kit.mat('#9aa1a4', { roughness: 0.6, metalness: 0.2 });
    const glass = kit.mat('#3c5260', { roughness: 0.12, metalness: 0.5 });
    const glassL = kit.mat('#7d9aab', { roughness: 0.12, metalness: 0.45 });
    const alu = kit.mat('#c9cdcf', { roughness: 0.4, metalness: 0.6 });
    const roofM = kit.mat('#868a8b');
    const dark = kit.mat('#2a2f33');
    const edges = ring.map((a, k) => {
      const b = ring[(k + 1) % ring.length];
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy) || 1;
      return {
        a,
        b,
        len,
        dx: dx / len,
        dy: dy / len,
        nx: dy / len,
        ny: -dx / len,
        ang: Math.atan2(dy, dx),
        my: (a[1] + b[1]) / 2,
      };
    });
    const at = (e, s, d) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    const ebox = (m, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const quad = (m, p, q, z0, z1) =>
      batch.quad(
        m,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], z1],
        [p[0], p[1], z1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );

    // Fulham Road frontage: long edges along the south side facing south
    const front = (e) => e.my < -2918 && e.ny < -0.8 && e.len > 6;
    kit.walls(batch, brick, [[ring]], 0, 5.0, { bay: 1e6 });
    kit.walls(batch, panel, [[ring]], 5.0, H, { bay: 1e6 });
    kit.cap(batch, roofM, [[ring]], H);
    kit.cornice(batch, alu, ring, H - 0.6, { height: 0.6, projection: 0.25 });
    kit.cornice(batch, alu, ring, 5.0, { height: 0.3, projection: 0.2 });
    for (const e of edges) {
      if (e.len < 4) continue;
      if (front(e)) {
        // glazed shopfronts with fascia, curtain-wall band above
        quad(glass, at(e, 0.4, 0.06), at(e, e.len - 0.4, 0.06), 0.3, 4.4);
        for (let s = 0.4; s <= e.len - 0.4; s += 3)
          ebox(alu, e, s - 0.06, s + 0.06, 0, 0.15, 0.3, 4.4);
        ebox(dark, e, 0.2, e.len - 0.2, 0, 0.25, 4.4, 5.0);
        quad(glassL, at(e, 0.5, 0.06), at(e, e.len - 0.5, 0.06), 6.2, H - 1.4);
        for (let s = 0.5; s <= e.len - 0.5; s += 1.5)
          ebox(alu, e, s - 0.04, s + 0.04, 0, 0.12, 6.2, H - 1.4);
        for (const z of [6.2, 10.1, H - 1.4])
          ebox(alu, e, 0.5, e.len - 0.5, 0, 0.18, z - 0.1, z + 0.1);
      } else {
        // service and side elevations: brick base, high-level strip windows
        if (e.len > 8) {
          quad(dark, at(e, 1, 0.05), at(e, e.len - 1, 0.05), 11.2, 12.4);
          for (let s = 1; s <= e.len - 1; s += 2.5)
            ebox(alu, e, s - 0.04, s + 0.04, 0, 0.1, 11.2, 12.4);
        }
        // vertical panel joints
        for (let s = 2.4; s < e.len - 1; s += 2.4)
          ebox(alu, e, s - 0.03, s + 0.03, 0, 0.05, 5.0, H - 0.6);
      }
    }
    // main entrance: double-height glazed box projecting on the longest Fulham Road edge
    const fe = edges.filter(front).sort((p, q) => q.len - p.len)[0];
    if (fe) {
      const s0 = Math.max(1, fe.len / 2 - 7),
        s1 = Math.min(fe.len - 1, fe.len / 2 + 7);
      const p = at(fe, s0, 2.8),
        q = at(fe, s1, 2.8);
      const box = [at(fe, s0, 0), at(fe, s1, 0), q, p].reverse();
      const br = kit.ringArea(box) < 0 ? box.slice().reverse() : box;
      kit.walls(batch, glassL, [[br]], 0, 9.5, { bay: 1e6 });
      kit.cap(batch, alu, [[br]], 9.5);
      for (let s = s0; s <= s1 + 0.01; s += 1.75)
        ebox(alu, fe, s - 0.06, s + 0.06, 0, 2.95, 9.3, 9.5);
      for (let s = s0; s <= s1 + 0.01; s += 1.75)
        ebox(alu, fe, s - 0.05, s + 0.05, 2.75, 2.9, 0, 9.5);
      ebox(alu, fe, s0, s1, 2.75, 2.95, 4.6, 4.75);
      ebox(alu, fe, s0 - 1, s1 + 1, 0, 4.5, 9.5, 10.0); // canopy roof edge
      const sign = kit.paintedMaterial(
        'fulham_broadway_centre:sign',
        1024,
        128,
        (c, w, h) => {
          c.fillStyle = '#1f2a33';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#ffffff';
          c.font = 'bold 64px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('fulham broadway', w * 0.38, h / 2 + 3);
          c.fillStyle = '#e8b400';
          c.font = 'bold 78px sans-serif';
          c.fillText('vue', w * 0.85, h / 2 + 4);
        },
        { roughness: 0.5 },
      );
      quad(sign, at(fe, s0 - 1, 4.55), at(fe, s1 + 1, 4.55), 9.5, 10.9);
      // tube roundel on a post at the entrance
      const rp = at(fe, s0 - 2.5, 4.0);
      kit.box(batch, dark, rp[0], rp[1], 0, 0.15, 0.15, 3.2, fe.ang);
      const disc = new THREE.CylinderGeometry(0.6, 0.6, 0.06, 24);
      batch.addGeometry(
        kit.mat('#c8102e'),
        disc,
        new THREE.Matrix4().makeRotationZ(fe.ang).setPosition(rp[0], rp[1], 3.6),
      );
      disc.dispose();
      kit.box(batch, kit.mat('#10239e'), rp[0], rp[1], 3.45, 1.5, 0.08, 0.3, fe.ang);
    }
    // roof: plant enclosures, rooflights over the mall
    const fr = kit.ringFrame(ring);
    const rr = kit.rng(0.517);
    const inside = ([x, y], r = kit.offsetRing(ring, -5)) => {
      let c = false;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++)
        if (
          r[i][1] > y !== r[j][1] > y &&
          x < ((r[j][0] - r[i][0]) * (y - r[i][1])) / (r[j][1] - r[i][1]) + r[i][0]
        )
          c = !c;
      return c;
    };
    const cxy = (u, v) => [
      fr.cx + Math.cos(fr.angle) * u - Math.sin(fr.angle) * v,
      fr.cy + Math.sin(fr.angle) * u + Math.cos(fr.angle) * v,
    ];
    for (let k = -2; k <= 2; k++) {
      const p = cxy((k * fr.length) / 6.5, 0);
      if (!inside(p)) continue;
      kit.box(batch, glassL, p[0], p[1], H, 9, 4, 1.2, fr.angle);
      kit.box(batch, alu, p[0], p[1], H + 1.2, 9.2, 0.25, 0.6, fr.angle);
    }
    for (let k = 0; k < 6; k++) {
      const p = cxy(
        (rr() - 0.5) * fr.length * 0.6,
        (rr() > 0.5 ? 1 : -1) * fr.width * (0.18 + rr() * 0.1),
      );
      if (!inside(p)) continue;
      kit.box(
        batch,
        kit.mat('#a4a8aa'),
        p[0],
        p[1],
        H,
        4 + rr() * 4,
        3 + rr() * 2,
        2.2 + rr(),
        fr.angle,
      );
    }
    g.add(batch.toGroup('fulham_broadway_centre'));
    return g;
  },
};
