// Fulham Town Hall, Fulham Road at Harwood Road, Walham Green (George Edwards for the
// Fulham Vestry, 1888-90; extended along Harwood Road by Francis Wood, 1904-5, and along
// Fulham Road by Walter Cave, 1934; Grade II*). Italianate front of rusticated Portland
// stone with extensive carved decoration: seven bays arranged 2-3-2, the centre projecting
// slightly and rising to an attic, an entrance with a carved tympanum under a cast- and
// wrought-iron canopy with lamps. Other elevations of stock brick; a drum clock over
// the Harwood Road entrance.
export default {
  id: 'fulham_town_hall',
  name: 'Fulham Town Hall',
  claims: [
    '86110e9b-1d5d-4b5c-90af-5f567720a800',
    'c2e811c6-82fa-416e-8945-faee676f97cf',
    'c7637656-af8f-45cb-ab85-7799ccf244ea',
    '389aa5dd-2236-4481-86d2-faf1c9f3b886',
  ],
  references: [
    {
      title: 'Fulham Town Hall - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Fulham_Town_Hall',
      used_for: 'George Edwards, foundation stone 1888, completed 1890, Grade II*',
    },
    {
      title: 'Fulham Town Hall (original building and 1904-5 extension) - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101191939-fulham-town-hall-original-building-and-1904-5-extension-parsons-green-and-walham-ward',
      used_for:
        'Portland stone facades, stock brick elsewhere; seven bays 2-3-2 with projecting centre rising to an attic; carved tympanum; iron canopy with lamps; Francis Wood 1904-5 extension',
    },
    {
      title: '1890- Old Town Hall, Fulham - Archiseek',
      url: 'https://www.archiseek.com/?p=21781',
      used_for: '1934 Fulham Road extension by Walter Cave',
    },
    {
      title: 'The Harwood Road elevation of Fulham Town Hall - Historic England',
      url: 'https://historicengland.org.uk/images-books/photos/item/BL19372',
      used_for: 'Harwood Road elevation (caption)',
    },
  ],
  notes:
    'Overture heights (9-11 m) are too low: three storeys of 5.0/4.6/4.2 m plus a 1.4 m balustrade (~15 m), ' +
    'central attic to ~19.5 m. Window forms (arched ground floor, pedimented first floor, lintelled second ' +
    'floor), column positions and carving are interpretive; the drum clock is placed over the middle of the ' +
    'Harwood Road range. Which claimed rear blocks belong to which phase is assumed.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ringOf = (id) => {
      const r = byId[id].polys[0][0].slice();
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const frameOf = (deg, cx, cy) => {
      const a = (deg * Math.PI) / 180,
        c = Math.cos(a),
        s = Math.sin(a);
      return { a, L: (u, v) => [cx + u * c - v * s, cy + u * s + v * c] };
    };
    const portland = kit.mat('#e6e0d0', { roughness: 0.78 });
    const portlandD = kit.mat('#d3ccb9', { roughness: 0.82 });
    const stock = kit.mat('#b7a47e', { roughness: 0.9 });
    const roofM = kit.mat('#7b7f80', { roughness: 0.8 });
    const slate = kit.mat('#4f555b', { roughness: 0.75 });
    const glass = kit.mat('#29343d', { roughness: 0.3, metalness: 0.2 });
    const frameW = kit.mat('#f1ede4');
    const iron = kit.mat('#23292b', { roughness: 0.5, metalness: 0.5 });
    const Z1 = 5.0,
      Z2 = 9.6,
      Z3 = 13.8,
      ZP = 15.2;

    const plainBlock = (ring, h, mat, frameMat) => {
      kit.walls(batch, mat, [[ring]], 0, h, { bay: 1e6 });
      kit.cap(batch, roofM, [[ring]], h);
      kit.cornice(batch, portlandD, ring, h - 0.5, { height: 0.5, projection: 0.25 });
      const storeys = Math.max(1, Math.floor(h / 4.4));
      kit.windowGrid(batch, ring, 1.1, storeys, h / storeys, (s, k) => ({
        glass,
        frame: frameMat,
        sill: portlandD,
        head: 'lintel',
        width: 1.2,
        height: 2.2,
        bay: 3.4,
        margin: 1.0,
        bars: 1,
      }));
    };

    // ---- main 1888-90 block -------------------------------------------------------------
    const F = frameOf(-83.25, 400.1, -2961.02); // u: south, away from Fulham Road; v: east
    const main = ringOf('86110e9b-1d5d-4b5c-90af-5f567720a800');
    kit.walls(batch, stock, [[main]], 0, ZP, { bay: 1e6 });
    kit.cap(batch, roofM, [[main]], ZP);
    {
      // slate mansard-ish roof over the front range
      const fr = [F.L(-16.6, -14.2), F.L(-8.5, -14.2), F.L(-8.5, 13.0), F.L(-16.6, 13.0)];
      kit.pitchedRoof(batch, slate, stock, fr, F.a + Math.PI / 2, ZP, 3.2, 'hipped', {
        overhang: -0.6,
      });
    }
    // Fulham Road front: edge u = -16.8 from v = 13.2 to v = -14.5 (outward normal north)
    const U = -16.85;
    const A = F.L(U, 13.2),
      B = F.L(U, -14.5);
    const flen = Math.hypot(B[0] - A[0], B[1] - A[1]);
    const ex = (B[0] - A[0]) / flen,
      ey = (B[1] - A[1]) / flen;
    const nx = ey,
      ny = -ex; // outward
    const P = (s, d) => [A[0] + ex * s + nx * d, A[1] + ey * s + ny * d];
    const fang = Math.atan2(ey, ex);
    const ebox = (m, s0, s1, d0, d1, z0, z1) => {
      const c = P((s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, m, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, fang);
    };
    // bays 2-3-2: centre three bays project 0.6 m
    const bayW = flen / 7;
    const cs0 = 2 * bayW,
      cs1 = 5 * bayW;
    ebox(portland, 0, flen, -0.2, 0.3, 0, ZP); // stone facing slab
    ebox(portland, cs0, cs1, 0.3, 0.9, 0, ZP);
    // rusticated ground floor: channelled joints
    for (let z = 0.7; z < Z1; z += 0.55) {
      ebox(portlandD, 0, cs0, 0.3, 0.36, z, z + 0.06);
      ebox(portlandD, cs1, flen, 0.3, 0.36, z, z + 0.06);
      ebox(portlandD, cs0, cs1, 0.9, 0.96, z, z + 0.06);
    }
    ebox(portlandD, -0.1, flen + 0.1, 0.3, 1.1, 0, 0.7); // plinth
    // string courses and main cornice (with the centre returning forward)
    for (const [z, h, p] of [
      [Z1, 0.35, 0.35],
      [Z2 - 0.2, 0.25, 0.25],
      [Z3, 0.6, 0.6],
    ]) {
      ebox(portlandD, -0.1, flen + 0.1, 0.3, 0.3 + p, z, z + h);
      ebox(portlandD, cs0 - 0.1, cs1 + 0.1, 0.9, 0.9 + p, z, z + h);
    }
    // balustraded parapet
    kit.balustrade(batch, portland, [P(0, 0.6), P(cs0, 0.6)], Z3 + 0.6, {
      height: 1.0,
      spacing: 0.35,
    });
    kit.balustrade(batch, portland, [P(cs1, 0.6), P(flen, 0.6)], Z3 + 0.6, {
      height: 1.0,
      spacing: 0.35,
    });
    // central attic with segmental pediment and urns
    ebox(portland, cs0 + 0.3, cs1 - 0.3, -0.5, 1.0, Z3 + 0.6, Z3 + 3.6);
    ebox(portlandD, cs0 + 0.1, cs1 - 0.1, -0.5, 1.2, Z3 + 3.6, Z3 + 4.0);
    {
      const c = P(flen / 2, 1.0);
      const pw = cs1 - cs0 - 1.0;
      const ped = new THREE.CylinderGeometry(pw * 0.58, pw * 0.58, 0.7, 3, 1).rotateX(Math.PI / 2);
      ped.scale(1, 0.26, 1);
      const pm = new THREE.Matrix4()
        .makeRotationZ(fang)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      pm.setPosition(c[0], c[1], Z3 + 4.0 + pw * 0.075);
      batch.addGeometry(portland, ped, pm);
      ped.dispose();
      const sign = kit.paintedMaterial(
        'fulham_town_hall:attic',
        512,
        96,
        (cx, w, h) => {
          cx.fillStyle = '#e6e0d0';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#6b6252';
          cx.font = 'bold 40px serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('VESTRY HALL', w / 2, h / 2 + 2);
        },
        { roughness: 0.8 },
      );
      const a = P(cs0 + 1.0, 1.02),
        b = P(cs1 - 1.0, 1.02);
      batch.quad(
        sign,
        [a[0], a[1], Z3 + 1.2],
        [b[0], b[1], Z3 + 1.2],
        [b[0], b[1], Z3 + 3.0],
        [a[0], a[1], Z3 + 3.0],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    for (const s of [0.3, cs0 - 0.2, cs1 + 0.2, flen - 0.3]) {
      const c = P(s, 0.6);
      const urn = new THREE.LatheGeometry(
        [
          [0.01, 0],
          [0.32, 0],
          [0.22, 0.3],
          [0.38, 0.75],
          [0.12, 1.1],
          [0.01, 1.2],
        ].map(([r, z]) => new THREE.Vector2(r, z)),
        10,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(portland, urn, new THREE.Matrix4().makeTranslation(c[0], c[1], Z3 + 1.6));
      urn.dispose();
    }
    // windows: ground floor arched, first floor pedimented with paired columns, second lintel
    for (let k = 0; k < 7; k++) {
      const s = (k + 0.5) * bayW;
      const d = k >= 2 && k <= 4 ? 0.9 : 0.3;
      const a = P(s - 0.9, d),
        b = P(s + 0.9, d);
      if (k !== 3)
        kit.windowRow(batch, a, b, 1.2, {
          glass,
          frame: frameW,
          sill: portland,
          head: 'arch',
          count: 1,
          width: 1.5,
          height: 2.6,
          margin: 0.15,
          bars: 2,
        });
      kit.windowRow(batch, a, b, Z1 + 0.9, {
        glass,
        frame: frameW,
        sill: portland,
        head: 'pediment',
        count: 1,
        width: 1.4,
        height: 2.6,
        margin: 0.2,
        bars: 2,
        surround: 0.22,
        surroundMat: portland,
      });
      kit.windowRow(batch, a, b, Z2 + 0.8, {
        glass,
        frame: frameW,
        sill: portland,
        head: 'lintel',
        count: 1,
        width: 1.3,
        height: 2.2,
        margin: 0.25,
        bars: 1,
        surround: 0.18,
        surroundMat: portland,
      });
      // pilasters / attached columns between bays on the upper floors
      for (const ds of [-0.5, 0.5]) {
        const sp = s + ds * bayW;
        const c = P(sp, d + 0.25);
        const col = new THREE.CylinderGeometry(0.2, 0.23, Z3 - Z1 - 0.4, 10).rotateX(Math.PI / 2);
        batch.addGeometry(
          portland,
          col,
          new THREE.Matrix4().makeTranslation(c[0], c[1], (Z1 + 0.35 + Z3) / 2),
        );
        col.dispose();
      }
    }
    // central entrance: doorway with carved tympanum, iron and glass canopy with lamps
    {
      const s = 3.5 * bayW;
      const c = P(s, 0.95);
      kit.box(batch, kit.mat('#3b2a1f'), c[0], c[1], 0, 2.0, 0.08, 3.4, fang);
      const tymp = new THREE.CylinderGeometry(1.2, 1.2, 0.12, 14, 1, false, -Math.PI / 2, Math.PI);
      batch.addGeometry(
        portlandD,
        tymp,
        new THREE.Matrix4().makeRotationZ(fang).setPosition(c[0], c[1], 3.4),
      );
      tymp.dispose();
      const cp = P(s, 2.4);
      kit.box(batch, iron, cp[0], cp[1], 3.9, 4.2, 3.0, 0.12, fang);
      kit.box(
        batch,
        kit.mat('#9fb3bb', { roughness: 0.2, metalness: 0.3 }),
        cp[0],
        cp[1],
        4.02,
        4.0,
        2.8,
        0.06,
        fang,
      );
      for (const ds of [-1.9, 1.9]) {
        const q = P(s + ds, 3.7);
        kit.box(batch, iron, q[0], q[1], 0, 0.14, 0.14, 3.9, fang);
        const lamp = new THREE.SphereGeometry(0.22, 8, 6);
        batch.addGeometry(
          kit.mat('#f4e8b8', { emissive: '#6b5a2a' }),
          lamp,
          new THREE.Matrix4().makeTranslation(q[0], q[1], 4.4),
        );
        lamp.dispose();
      }
    }
    // side elevations of the main block (stock brick): simple windows
    for (let k = 0; k < main.length; k++) {
      const a = main[k],
        b = main[(k + 1) % main.length];
      const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      const um = (mid[0] - 400.1) * Math.cos(F.a) + (mid[1] + 2961.02) * Math.sin(F.a);
      if (um < -15) continue; // skip the stone front
      if (Math.hypot(b[0] - a[0], b[1] - a[1]) < 5) continue;
      for (const z of [1.2, Z1 + 0.9, Z2 + 0.8])
        kit.windowRow(batch, a, b, z, {
          glass,
          frame: frameW,
          sill: portlandD,
          head: 'segment',
          width: 1.2,
          height: 2.3,
          bay: 3.4,
          margin: 1.2,
          bars: 1,
        });
    }

    // ---- Harwood Road range (Francis Wood, 1904-5) with the drum clock ----------------------
    {
      const r = ringOf('c2e811c6-82fa-416e-8945-faee676f97cf');
      const H = 14.6;
      kit.walls(batch, stock, [[r]], 0, H, { bay: 1e6 });
      kit.cap(batch, roofM, [[r]], H);
      const Fh = frameOf(218.99, 386.68, -2983.7); // u: south-west, towards Harwood Road
      const a = Fh.L(14.25, -11.5),
        b = Fh.L(12.95, 12.2);
      // stone front on Harwood Road
      const fr = [Fh.L(13.9, -11.6), Fh.L(14.4, -11.6), Fh.L(13.1, 12.3), Fh.L(12.6, 12.3)];
      kit.walls(batch, portland, [[fr]], 0, H, { bay: 1e6 });
      kit.cap(batch, portland, [[fr]], H);
      kit.cornice(batch, portlandD, r, H - 0.6, { height: 0.6, projection: 0.4 });
      kit.cornice(batch, portlandD, r, 4.6, { height: 0.3, projection: 0.15 });
      for (const [z, head] of [
        [1.1, 'arch'],
        [5.6, 'pediment'],
        [10.0, 'lintel'],
      ])
        kit.windowRow(batch, a, b, z, {
          glass,
          frame: frameW,
          sill: portland,
          head,
          width: 1.4,
          height: z < 5 ? 2.4 : 2.5,
          bay: 3.4,
          margin: 1.4,
          bars: 2,
          surround: 0.18,
          surroundMat: portland,
        });
      // drum clock over the central entrance
      const m = Fh.L(14.0, 0.35);
      const n = [Math.cos(Fh.a) * 0.5, Math.sin(Fh.a) * 0.5];
      const drum = new THREE.CylinderGeometry(1.25, 1.25, 1.0, 24);
      batch.addGeometry(
        portland,
        drum,
        new THREE.Matrix4()
          .makeRotationZ(Fh.a + Math.PI / 2)
          .setPosition(m[0] + n[0], m[1] + n[1], H + 0.9),
      );
      drum.dispose();
      const face = kit.paintedMaterial(
        'fulham_town_hall:clock',
        128,
        128,
        (c, w, h) => {
          c.fillStyle = '#f4f1e6';
          c.beginPath();
          c.arc(w / 2, h / 2, w / 2 - 2, 0, Math.PI * 2);
          c.fill();
          c.strokeStyle = '#1d1d1d';
          c.lineWidth = 3;
          for (let k = 0; k < 12; k++) {
            const t = (k / 12) * Math.PI * 2;
            c.beginPath();
            c.moveTo(w / 2 + Math.cos(t) * 50, h / 2 + Math.sin(t) * 50);
            c.lineTo(w / 2 + Math.cos(t) * 58, h / 2 + Math.sin(t) * 58);
            c.stroke();
          }
          c.lineWidth = 4;
          c.beginPath();
          c.moveTo(w / 2, h / 2);
          c.lineTo(w / 2, h / 2 - 38);
          c.moveTo(w / 2, h / 2);
          c.lineTo(w / 2 + 26, h / 2 + 10);
          c.stroke();
        },
        { roughness: 0.5 },
      );
      const fc = [m[0] + n[0] * 2.03, m[1] + n[1] * 2.03];
      const disc = new THREE.CircleGeometry(1.05, 24)
        .rotateX(-Math.PI / 2)
        .rotateZ(Fh.a - Math.PI / 2);
      batch.addGeometry(face, disc, new THREE.Matrix4().makeTranslation(fc[0], fc[1], H + 0.9));
      disc.dispose();
      kit.box(batch, portland, m[0] + n[0], m[1] + n[1], H + 2.1, 0.9, 0.9, 0.9, Fh.a);
      const ent = Fh.L(14.45, 0.35);
      kit.box(batch, kit.mat('#3b2a1f'), ent[0], ent[1], 0, 0.08, 2.4, 3.4, Fh.a);
    }
    // ---- rear hall block and the 1934 Fulham Road extension ------------------------------
    plainBlock(ringOf('c7637656-af8f-45cb-ab85-7799ccf244ea'), 13.2, stock, frameW);
    {
      const r = ringOf('389aa5dd-2236-4481-86d2-faf1c9f3b886');
      kit.walls(batch, portland, [[r]], 0, 13.8, { bay: 1e6 });
      kit.cap(batch, roofM, [[r]], 13.8);
      kit.cornice(batch, portlandD, r, 13.2, { height: 0.6, projection: 0.3 });
      kit.windowGrid(batch, r, 1.1, 3, 4.4, () => ({
        glass,
        frame: kit.mat('#3c4446'),
        sill: portlandD,
        head: 'none',
        width: 1.6,
        height: 2.6,
        bay: 2.8,
        margin: 0.8,
        bars: 2,
      }));
    }

    g.add(batch.toGroup('fulham_town_hall'));
    return g;
  },
};
