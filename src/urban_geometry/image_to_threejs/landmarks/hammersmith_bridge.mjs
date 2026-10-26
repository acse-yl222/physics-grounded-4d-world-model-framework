// Hammersmith Bridge (Sir Joseph Bazalgette, opened 1887), Grade II*. Suspension
// bridge over the Thames on Tierney Clark's original pier foundations: two towers of
// wrought-iron framing cased in ornamental cast iron, each a pair of pylons with
// French-chateau caps joined by a decorative portal carrying heraldic shields,
// suspension chains with vertical hangers, a lattice-parapet deck, all painted dark
// green with gilded details.
export default {
  id: 'hammersmith_bridge',
  name: 'Hammersmith Bridge',
  claims: [],
  references: [
    {
      title: 'Hammersmith Bridge - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_Bridge',
      used_for: 'Bazalgette 1887 suspension bridge, overall form, length',
    },
    {
      title: 'Hammersmith Bridge - Historic England list entry',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1080793',
      used_for: 'dark green and gold colour scheme of the original plans',
    },
    {
      title: 'Hammersmith Bridge - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101080793',
      used_for:
        'wrought-iron framed towers cased in ornamental cast iron, partly gilded; heraldic arms on the towers',
    },
    {
      title: 'Hammersmith Bridge - Historic England list entry 1079819',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1079819',
      used_for:
        'clustered Doric columns on the stone piers, wrought-iron parapets, cast-iron pedestals at the chain corners, heraldry on the towers',
    },
    {
      title: "Hammersmith Bridge - Grace's Guide",
      url: 'https://www.gracesguide.co.uk/Hammersmith_Bridge',
      used_for: 'eyebar chain links with pinned joints',
    },
    {
      title: 'Hammersmith Bridge - Historic Bridges',
      url: 'https://historicbridges.org/unitedkingdom/hammersmith/report.htm',
      used_for:
        'double suspension chains, wrought-iron hangers, timber deck on cross girders with stiffening girders',
    },
    {
      title: 'Hammersmith Bridge fun facts - Londonist',
      url: 'https://londonist.com/london/history/hammersmith-bridge-fun-facts',
      used_for: '700 ft length, repainted green in 2000',
    },
  ],
  notes:
    'Placed on the Overture bridge segment (224 m between abutments, 14.9 m deck outline). Main span taken as 129 m ' +
    '(422 ft, centred), tower tops ~13-15 m above the deck (Wikipedia gives 48 ft), deck camber and chain sag ' +
    'estimated. Two stacked eyebar chains per side with pins at ~4.4 m, hangers every 2.8 m with clamps, cross and ' +
    'stiffening girders under the deck, lattice parapet with posts, clustered Doric columns on the river piers and ' +
    'cast-iron chain pedestals at the abutment corners follow the listing; the footway position relative to the ' +
    'chains, lamp standards (generic resources street_lamp at 20 m), pylon panel ornament and heraldry (shields with ' +
    'a cross, roundels) are simplified - the actual Royal Arms and county/city crests are not reproduced. No building ' +
    'footprint is claimed.',
  build(ctx) {
    const { THREE, kit } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // Bridge axis from the north abutment to the south abutment (Overture segment
    // c00da92e/c7a8b8d8), shifted to the centre of the deck outline.
    const PN = [-2001.12, -1911.72],
      PS = [-2122.83, -2099.78];
    const L = Math.hypot(PS[0] - PN[0], PS[1] - PN[1]);
    const d = [(PS[0] - PN[0]) / L, (PS[1] - PN[1]) / L];
    const n = [-d[1], d[0]]; // left of travel (towards the east here)
    const shift = 1.7;
    const O = [PN[0] + n[0] * shift, PN[1] + n[1] * shift];
    const W = (s, v, z) => [O[0] + d[0] * s + n[0] * v, O[1] + d[1] * s + n[1] * v, z];
    const rot = Math.atan2(d[1], d[0]);
    const M = (s, v, z, extra) => {
      const m = new THREE.Matrix4().makeRotationZ(rot).setPosition(...W(s, v, z));
      return extra ? m.multiply(extra) : m;
    };
    const addGeo = (m, geo, mtx) => {
      batch.addGeometry(m, geo, mtx);
      geo.dispose();
    };
    const box = (m, s, v, z0, ds, dv, dz) =>
      addGeo(m, new THREE.BoxGeometry(ds, dv, dz), M(s, v, z0 + dz / 2));

    const green = kit.mat('#4b7a57', { roughness: 0.55, metalness: 0.15 });
    const paleGreen = kit.mat('#5f8f6a', { roughness: 0.55, metalness: 0.2 });
    const gold = kit.mat('gold');
    const stone = kit.mat('#bdb5a3', { roughness: 0.9 });
    const asphalt = kit.mat('asphalt');
    const paving = kit.mat('paving');
    const red = kit.mat('#9c2f2a', { roughness: 0.5 });
    const lattice = kit.paintedMaterial(
      'hammersmith_bridge:lattice',
      256,
      64,
      (c, w, h) => {
        c.clearRect(0, 0, w, h);
        c.strokeStyle = '#4b7a57';
        c.lineWidth = 5;
        c.strokeRect(2, 3, w - 4, h - 6);
        for (let x = -h; x < w; x += 32) {
          c.beginPath();
          c.moveTo(x, h);
          c.lineTo(x + h, 0);
          c.moveTo(x + h, h);
          c.lineTo(x, 0);
          c.stroke();
        }
        c.fillStyle = '#d6b04c';
        for (let x = 16; x < w; x += 32) c.fillRect(x - 2, 2, 4, 4);
      },
      { transparent: true, alphaTest: 0.4, side: THREE.DoubleSide, roughness: 0.55 },
    );

    const half = 7.2; // half deck width
    const S1 = L / 2 - 64.3,
      S2 = L / 2 + 64.3; // towers
    const deckZ = (s) => 0.6 + 4.6 * (1 - ((s - L / 2) / (L / 2)) ** 2);
    const towerTop = (s) => deckZ(s) + 13;

    // Deck: carriageway, footways, girder and lattice parapets, segment by segment.
    const NS = 56;
    for (let i = 0; i < NS; i++) {
      const sa = (L * i) / NS,
        sb = (L * (i + 1)) / NS;
      const za = deckZ(sa),
        zb = deckZ(sb);
      const top = (m, v0, v1, dz, uv) =>
        batch.quad(
          m,
          W(sa, v0, za + dz),
          W(sb, v0, zb + dz),
          W(sb, v1, zb + dz),
          W(sa, v1, za + dz),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      top(asphalt, -4.2, 4.2, 0);
      top(paving, 4.2, half, 0.2);
      top(paving, -half, -4.2, 0.2);
      // kerbs
      for (const v of [-4.2, 4.2]) {
        const sgn = Math.sign(v);
        // kerb face looking towards the carriageway centre
        const kq =
          sgn > 0
            ? [W(sa, v, za), W(sb, v, zb), W(sb, v, zb + 0.2), W(sa, v, za + 0.2)]
            : [W(sb, v, zb), W(sa, v, za), W(sa, v, za + 0.2), W(sb, v, zb + 0.2)];
        batch.quad(paving, ...kq, [0, 0], [1, 0], [1, 1], [0, 1]);
      }
      // underside and girder faces
      batch.quad(
        green,
        W(sa, -half, za - 1.3),
        W(sa, half, za - 1.3),
        W(sb, half, zb - 1.3),
        W(sb, -half, zb - 1.3),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      for (const v of [-half, half]) {
        const q =
          v < 0
            ? [W(sa, v, za - 1.3), W(sb, v, zb - 1.3), W(sb, v, zb + 0.2), W(sa, v, za + 0.2)]
            : [W(sb, v, zb - 1.3), W(sa, v, za - 1.3), W(sa, v, za + 0.2), W(sb, v, zb + 0.2)];
        batch.quad(green, ...q, [0, 0], [1, 0], [1, 1], [0, 1]);
        // lattice parapet (double sided, alpha tested)
        const seg = (sb - sa) / 8;
        batch.quad(
          lattice,
          W(sa, v, za + 0.2),
          W(sb, v, zb + 0.2),
          W(sb, v, zb + 1.5),
          W(sa, v, za + 1.5),
          [0, 0],
          [seg, 0],
          [seg, 1],
          [0, 1],
        );
        // handrail
        addGeo(
          green,
          new THREE.BoxGeometry(sb - sa + 0.05, 0.25, 0.18),
          M(
            (sa + sb) / 2,
            v,
            (za + zb) / 2 + 1.55,
            new THREE.Matrix4().makeRotationY(-Math.atan2(zb - za, sb - sa)),
          ),
        );
      }
    }
    // Abutments.
    for (const s of [0, L]) {
      box(stone, s, 0, -2, 8, 2 * half + 3, deckZ(s) + 1.6);
      for (const v of [-half - 1, half + 1]) box(stone, s, v, deckZ(s), 3, 2, 2.6);
    }

    // Suspension chains: two stacked eyebar chains per side; main span sag to just
    // above the deck at mid-span, back spans down to the abutment anchorages.
    const chainZ = (s, k) => {
      const t1 = towerTop(S1) - 0.8 - k * 0.9;
      if (s <= S1) {
        const z0 = deckZ(0) + 1.8;
        const t = s / S1;
        return z0 + (t1 - z0) * t * t * 0.55 + (t1 - z0) * t * 0.45;
      }
      if (s >= S2) {
        const z0 = deckZ(L) + 1.8;
        const t = (L - s) / (L - S2);
        return z0 + (t1 - z0) * t * t * 0.55 + (t1 - z0) * t * 0.45;
      }
      const sag = t1 - (deckZ(L / 2) + 1.2 + k * 0.4);
      const x = (s - L / 2) / (S2 - L / 2);
      return t1 - sag * (1 - x * x);
    };
    const chainV = half + 0.6;
    const CS = 96;
    for (const side of [-1, 1])
      for (const k of [0, 1]) {
        for (let i = 0; i < CS; i++) {
          const sa = (L * i) / CS,
            sb = (L * (i + 1)) / CS;
          const za = chainZ(sa, k),
            zb = chainZ(sb, k);
          const len = Math.hypot(sb - sa, zb - za);
          addGeo(
            green,
            new THREE.BoxGeometry(len + 0.05, 0.35, 0.55),
            M(
              (sa + sb) / 2,
              side * chainV,
              (za + zb) / 2,
              new THREE.Matrix4().makeRotationY(-Math.atan2(zb - za, sb - sa)),
            ),
          );
        }
      }
    // Hangers every 2.8 m from the lower chain to the deck girder.
    for (const side of [-1, 1])
      for (let s = 3; s < L - 3; s += 2.8) {
        if (Math.abs(s - S1) < 2.5 || Math.abs(s - S2) < 2.5) continue;
        const z0 = deckZ(s) + 0.2,
          z1 = chainZ(s, 1);
        if (z1 - z0 < 0.5) continue;
        box(paleGreen, s, side * chainV, z0, 0.14, 0.14, z1 - z0);
      }

    // Towers: river piers, paired pylons with chateau caps, portal with shields.
    for (const s of [S1, S2]) {
      const dz = deckZ(s);
      // stone pier with cutwaters
      box(stone, s, 0, -1.5, 7, 2 * half + 8, dz - 3.5 + 1.5);
      kit.cornice(
        batch,
        stone,
        [
          W(s - 3.5, -half - 4, 0),
          W(s + 3.5, -half - 4, 0),
          W(s + 3.5, half + 4, 0),
          W(s - 3.5, half + 4, 0),
        ].map((q) => [q[0], q[1]]),
        dz - 3.9,
        { height: 0.4, projection: 0.3 },
      );
      for (const v of [-(half + 4), half + 4]) {
        const cw = new THREE.CylinderGeometry(3.5, 3.5, dz - 2.0, 3).rotateX(Math.PI / 2);
        addGeo(
          stone,
          cw,
          M(
            s,
            v + Math.sign(v) * 0.6,
            -1.5 + (dz - 2.0) / 2,
            new THREE.Matrix4().makeRotationZ(v > 0 ? Math.PI / 2 : -Math.PI / 2),
          ),
        );
      }
      for (const side of [-1, 1]) {
        const v = side * (half + 1.6);
        // pylon base plinth (on the pier, beside the deck)
        box(green, s, v, dz - 1.3, 4.2, 3.0, 2.2);
        box(gold, s, v, dz + 0.9, 4.4, 3.2, 0.25);
        // shaft: a cluster of four cased columns
        for (const ds of [-1.25, 1.25])
          for (const dv of [-0.8, 0.8]) {
            const col = new THREE.CylinderGeometry(0.5, 0.6, 9.2, 10).rotateX(Math.PI / 2);
            addGeo(green, col, M(s + ds, v + dv, dz + 1.15 + 4.6));
          }
        box(green, s, v, dz + 1.15, 2.4, 1.4, 9.2);
        // capital band and gilded mouldings
        box(gold, s, v, dz + 10.3, 3.9, 2.7, 0.35);
        box(green, s, v, dz + 10.65, 3.6, 2.5, 1.6);
        box(gold, s, v, dz + 12.2, 4.0, 2.9, 0.3);
        // chain saddle housing
        box(green, s, v, dz + 12.5, 3.6, 2.6, 1.0);
        // chateau-style cap: steep four-sided roof with lantern and gilt finial
        const cap = new THREE.ConeGeometry(2.4, 3.6, 4).rotateX(Math.PI / 2);
        addGeo(
          green,
          cap,
          M(s, v, dz + 13.5 + 1.8, new THREE.Matrix4().makeRotationZ(Math.PI / 4)),
        );
        for (const ds of [-1.7, 1.7])
          for (const dv of [-1.15, 1.15]) {
            const tur = new THREE.ConeGeometry(0.45, 2.0, 6).rotateX(Math.PI / 2);
            addGeo(
              green,
              new THREE.CylinderGeometry(0.4, 0.4, 1.2, 6).rotateX(Math.PI / 2),
              M(s + ds, v + dv, dz + 13.1),
            );
            addGeo(green, tur, M(s + ds, v + dv, dz + 14.7));
            addGeo(gold, new THREE.SphereGeometry(0.18, 6, 4), M(s + ds, v + dv, dz + 15.8));
          }
        addGeo(
          gold,
          new THREE.CylinderGeometry(0.08, 0.12, 1.6, 6).rotateX(Math.PI / 2),
          M(s, v, dz + 17.8),
        );
        addGeo(gold, new THREE.SphereGeometry(0.32, 8, 6), M(s, v, dz + 17.2));
      }
      // portal beam over the carriageway with an ornamental arch, cresting and shields
      box(green, s, 0, dz + 10.65, 1.6, 2 * half + 0.6, 1.6);
      box(gold, s, 0, dz + 10.45, 1.7, 2 * half + 0.6, 0.2);
      box(gold, s, 0, dz + 12.25, 1.7, 2 * half + 0.6, 0.2);
      const arch = new THREE.TorusGeometry(half - 0.4, 0.28, 6, 20, Math.PI);
      addGeo(
        green,
        arch,
        M(
          s,
          0,
          dz + 10.4 - (half - 0.4) * 0.35,
          new THREE.Matrix4()
            .makeRotationZ(Math.PI / 2)
            .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2))
            .multiply(new THREE.Matrix4().makeScale(1, 0.35, 1)),
        ),
      );
      for (let v = -half + 0.8; v <= half - 0.8; v += 1.2) {
        addGeo(gold, new THREE.ConeGeometry(0.16, 0.7, 4).rotateX(Math.PI / 2), M(s, v, dz + 12.8));
      }
      for (const face of [-1, 1]) {
        // heraldic shield panels on both faces of the portal
        {
          // heater-shaped shield: red field with a gilt border and cross
          const sh = new THREE.Shape();
          sh.moveTo(-1.0, 0);
          sh.lineTo(1.0, 0);
          sh.lineTo(1.0, -0.9);
          sh.quadraticCurveTo(0.95, -1.7, 0, -2.1);
          sh.quadraticCurveTo(-0.95, -1.7, -1.0, -0.9);
          sh.closePath();
          const basis = new THREE.Matrix4().makeBasis(
            new THREE.Vector3(0, face, 0),
            new THREE.Vector3(0, 0, 1),
            new THREE.Vector3(face, 0, 0),
          );
          const border = new THREE.ExtrudeGeometry(sh, {
            depth: 0.08,
            bevelEnabled: false,
            curveSegments: 6,
          });
          addGeo(gold, border, M(s + face * 0.8, 0, dz + 12.3, basis));
          const field = new THREE.ExtrudeGeometry(sh, {
            depth: 0.06,
            bevelEnabled: false,
            curveSegments: 6,
          });
          field.scale(0.85, 0.88, 1);
          field.translate(0, -0.1, 0);
          addGeo(red, field, M(s + face * 0.86, 0, dz + 12.3, basis));
          addGeo(gold, new THREE.BoxGeometry(0.06, 0.22, 1.6), M(s + face * 0.94, 0, dz + 10.75));
          addGeo(gold, new THREE.BoxGeometry(0.06, 1.4, 0.22), M(s + face * 0.94, 0, dz + 11.4));
        }
        addGeo(gold, new THREE.BoxGeometry(0.1, 2.8, 0.25), M(s + face * 0.88, 0, dz + 12.6));
        for (const dv of [-4.2, 4.2])
          addGeo(
            gold,
            new THREE.CylinderGeometry(0.55, 0.55, 0.12, 12).rotateZ(Math.PI / 2),
            M(s + face * 0.86, dv, dz + 11.45),
          );
      }
    }

    // ---- Detailing ----
    const pinMat = kit.mat('#3f6a4b', { roughness: 0.5, metalness: 0.25 });
    // Eyebar chain pins / link plates at ~4.4 m pitch.
    for (const side of [-1, 1])
      for (const k of [0, 1])
        for (let sp = 2.2; sp < L - 2; sp += 4.4) {
          const z = chainZ(sp, k);
          addGeo(pinMat, new THREE.CylinderGeometry(0.3, 0.3, 0.8, 8), M(sp, side * chainV, z));
          addGeo(gold, new THREE.CylinderGeometry(0.12, 0.12, 0.84, 6), M(sp, side * chainV, z));
        }
    // Hanger clamps at the chain and the deck girder; parapet posts in line.
    for (const side of [-1, 1])
      for (let sp = 3; sp < L - 3; sp += 2.8) {
        if (Math.abs(sp - S1) < 2.5 || Math.abs(sp - S2) < 2.5) continue;
        const z0 = deckZ(sp) + 0.2,
          z1 = chainZ(sp, 1);
        if (z1 - z0 >= 0.5) {
          box(paleGreen, sp, side * chainV, z1 - 0.5, 0.3, 0.3, 0.5);
          box(paleGreen, sp, side * chainV, z0, 0.35, 0.35, 0.45);
        }
        box(green, sp, side * half, deckZ(sp) + 0.2, 0.16, 0.16, 1.45);
        addGeo(gold, new THREE.SphereGeometry(0.1, 5, 3), M(sp, side * half, deckZ(sp) + 1.75));
      }
    // Deck structure seen from the river: cross girders and stiffening girders.
    for (let sp = 1.4; sp < L; sp += 2.8)
      box(green, sp, 0, deckZ(sp) - 2.0, 0.3, 2 * half + 0.8, 0.7);
    for (const v of [-half + 0.2, -3.5, 0, 3.5, half - 0.2])
      for (let i = 0; i < 28; i++) {
        const sa = (L * i) / 28,
          sb = (L * (i + 1)) / 28;
        const za = deckZ(sa) - 1.6,
          zb = deckZ(sb) - 1.6;
        addGeo(
          green,
          new THREE.BoxGeometry(sb - sa + 0.05, 0.25, 0.6),
          M(
            (sa + sb) / 2,
            v,
            (za + zb) / 2,
            new THREE.Matrix4().makeRotationY(-Math.atan2(zb - za, sb - sa)),
          ),
        );
      }
    // Clustered Doric columns on the river piers carrying the deck (listing).
    for (const st of [S1, S2]) {
      const dz = deckZ(st);
      for (const v of [-(half + 1.6), -3.5, 0, 3.5, half + 1.6])
        for (const [ds, dv] of [
          [-0.6, -0.6],
          [0.6, -0.6],
          [-0.6, 0.6],
          [0.6, 0.6],
        ]) {
          addGeo(
            green,
            new THREE.CylinderGeometry(0.4, 0.46, 1.7, 10).rotateX(Math.PI / 2),
            M(st + ds * 2.2, v + dv, dz - 3.5 + 0.25 + 0.85),
          );
          box(green, st + ds * 2.2, v + dv, dz - 3.5, 1.1, 1.1, 0.25);
          box(gold, st + ds * 2.2, v + dv, dz - 1.55, 1.05, 1.05, 0.25);
        }
    }
    // Pylon dressing: gilded panel mouldings and blind arcading on the shafts.
    for (const st of [S1, S2]) {
      const dz = deckZ(st);
      for (const side of [-1, 1]) {
        const v = side * (half + 1.6);
        for (const f of [-1, 1]) {
          box(gold, st + f * 1.24, v, dz + 2.0, 0.06, 1.2, 0.12);
          box(gold, st + f * 1.24, v, dz + 9.2, 0.06, 1.2, 0.12);
          box(gold, st + f * 1.24, v - 0.6, dz + 2.0, 0.06, 0.1, 7.3);
          box(gold, st + f * 1.24, v + 0.6, dz + 2.0, 0.06, 0.1, 7.3);
          const arch = new THREE.TorusGeometry(0.55, 0.06, 4, 10, Math.PI);
          addGeo(
            gold,
            arch,
            M(
              st + f * 1.26,
              v,
              dz + 8.4,
              new THREE.Matrix4()
                .makeRotationZ(Math.PI / 2)
                .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2)),
            ),
          );
          // heraldic roundel on the outer face of each pylon cap
          addGeo(
            red,
            new THREE.CylinderGeometry(0.6, 0.6, 0.08, 12).rotateZ(Math.PI / 2),
            M(st + f * 1.85, v, dz + 11.4),
          );
          addGeo(
            gold,
            new THREE.TorusGeometry(0.62, 0.06, 4, 12).rotateY(Math.PI / 2),
            M(st + f * 1.88, v, dz + 11.4),
          );
        }
        // crocketed cresting around the saddle housing
        for (let k = -3; k <= 3; k++)
          for (const f of [-1, 1])
            addGeo(
              gold,
              new THREE.ConeGeometry(0.1, 0.45, 4).rotateX(Math.PI / 2),
              M(st + f * 1.8, v + k * 0.4, dz + 13.7),
            );
      }
    }
    // Cast-iron chain pedestals at the four abutment corners (listing).
    for (const sa of [0.5, L - 0.5]) {
      const dz = deckZ(sa);
      for (const side of [-1, 1]) {
        const v = side * chainV;
        box(green, sa, v, dz - 0.4, 3.0, 2.2, 2.6);
        box(gold, sa, v, dz + 2.2, 3.2, 2.4, 0.2);
        addGeo(
          green,
          new THREE.ConeGeometry(1.4, 1.3, 4).rotateX(Math.PI / 2),
          M(sa, v, dz + 3.05, new THREE.Matrix4().makeRotationZ(Math.PI / 4)),
        );
        addGeo(gold, new THREE.SphereGeometry(0.25, 8, 5), M(sa, v, dz + 3.8));
        addGeo(
          red,
          new THREE.CylinderGeometry(0.5, 0.5, 0.06, 12).rotateZ(Math.PI / 2),
          M(sa + (sa < L / 2 ? -1.52 : 1.52), v, dz + 0.9),
        );
      }
    }
    // Lamp standards along both parapets (resources street_lamp, arm over the road).
    for (let sp = 12; sp < L - 8; sp += 20) {
      if (Math.abs(sp - S1) < 8 || Math.abs(sp - S2) < 8) continue;
      const pl = [];
      for (const side of [-1, 1]) {
        const [x, y] = W(sp, side * (half - 0.35), 0);
        pl.push([x, y, side > 0 ? Math.atan2(-d[1], -d[0]) : rot]);
      }
      g.add(ctx.placeAssets('street_lamp', pl, { z: deckZ(sp) + 0.2 }));
    }
    g.add(batch.toGroup('hammersmith_bridge'));
    return g;
  },
};
