// Kensington (Olympia) station, Olympia Way (West London Line; District line terminus).
// Opened as Addison Road in 1844/1862; its weatherboarded Victorian buildings and canopies
// were wrecked by bombing in 1940 and the station reopened, renamed Kensington (Olympia),
// in 1946. Today: low station buildings on the west side by the exhibition centre, long
// platform canopies along the tracks, a footbridge and a small entrance pavilion on
// Olympia Way.
export default {
  id: 'kensington_olympia_station',
  name: 'Kensington (Olympia) station',
  claims: [
    '71ed838c-bc33-4a9e-9f75-2ebf317c1be9',
    'fb40e347-d270-4f5b-a2c3-eff00aa98c2a',
    '953b70b1-506f-4ef2-b49a-5ea7322c5697',
  ],
  references: [
    {
      title: 'Kensington (Olympia) station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Kensington_(Olympia)_station',
      used_for: 'history, renaming 1946, services, location on Olympia Way',
    },
    {
      title: 'Kensington Olympia - Subterranea Britannica',
      url: 'https://www.subbrit.org.uk/sb-sites/stations/k/kensington_olympia/index2.shtml',
      used_for: 'original weatherboarded buildings and canopies, 1940 bomb damage, forecourt',
    },
    {
      title: 'Olympia: entrance hall to Addison Road Station - RIBApix',
      url: 'https://www.architecture.com/image-library/ribapix/image-information/poster/olympia-london-the-entrance-hall-from-the-exhibition-centre-to-addison-road-station-and-the-garage-i/posterid/RIBA73985.html',
      used_for: 'Joseph Emberton’s 1937 Modern Movement link hall (context)',
    },
    {
      title: 'Kensington Olympia railway station in the 1980s - urban75',
      url: 'https://www.urban75.org/railway/kensington-olympia-station.html',
      used_for: 'platform canopies and footbridge (photo captions)',
    },
  ],
  notes:
    'No architectural description of the present buildings was found: the west building is modelled as a ' +
    'single-storey brick range (claimed footprint) with a platform canopy, the two small footprints as ' +
    'entrance/ancillary pavilions. Platform positions follow the mapped tracks; canopy length (110 m), ' +
    'footbridge position and all heights are estimates. Platforms, canopies and the footbridge are unclaimed.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ringOf = (id) => {
      const r = byId[id].polys[0][0].slice();
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const brick = kit.mat('#8b5a45', { roughness: 0.9 });
    const roofM = kit.mat('#6f7476');
    const glass = kit.mat('#2b3640', { roughness: 0.3, metalness: 0.2 });
    const green = kit.mat('#2f5a43', { roughness: 0.5 });
    const steel = kit.mat('#5d6a6f', { roughness: 0.5, metalness: 0.5 });
    const canopyM = kit.mat('#d9dcdc', { roughness: 0.5, metalness: 0.2 });
    const paving = kit.mat('#bdb6a8', { roughness: 0.9 });
    const white = kit.mat('#efefea');

    // Track frame: d along the line (towards south-east), n across (east positive).
    const d = [0.614, -0.79],
      n = [0.79, 0.614];
    const A = [-679.0, -930.4];
    const P = (s, o) => [A[0] + d[0] * s + n[0] * o, A[1] + d[1] * s + n[1] * o];
    const ang = Math.atan2(d[1], d[0]);
    const S0 = -18,
      S1 = 92; // canopy extent along the line
    const plat = (o0, o1, z = 0.95) => {
      const c = P((S0 + S1) / 2 + 5, (o0 + o1) / 2);
      kit.box(batch, paving, c[0], c[1], 0, S1 - S0 + 30, o1 - o0, z, ang);
      kit.box(
        batch,
        white,
        ...P((S0 + S1) / 2 + 5, o0 < 0 ? o1 - 0.15 : o0 + 0.15),
        0,
        S1 - S0 + 30,
        0.3,
        z + 0.02,
        ang,
      );
    };
    const canopy = (o0, o1, zc = 4.6) => {
      const om = (o0 + o1) / 2,
        w = o1 - o0;
      const c = P((S0 + S1) / 2, om);
      kit.box(batch, canopyM, c[0], c[1], zc, S1 - S0, w, 0.2, ang);
      const r = new THREE.CylinderGeometry(w * 0.55, w * 0.55, S1 - S0, 3, 1).rotateZ(Math.PI / 2);
      r.scale(1, 1, 0.18);
      batch.addGeometry(
        roofM,
        r,
        new THREE.Matrix4().makeRotationZ(ang).setPosition(c[0], c[1], zc + 0.35),
      );
      r.dispose();
      for (const side of [o0, o1])
        kit.box(batch, green, ...P((S0 + S1) / 2, side), zc - 0.5, S1 - S0, 0.06, 0.6, ang);
      for (let s = S0 + 3; s <= S1 - 3; s += 7.5) {
        kit.box(batch, steel, ...P(s, om), 0.95, 0.25, 0.25, zc - 0.95, ang);
        kit.box(batch, steel, ...P(s, om), zc - 0.4, 0.2, w - 0.4, 0.3, ang);
      }
    };
    // platforms: west (District bay / platform 1) and east (platforms 2-3) of the tracks
    plat(-11.5, -6.2);
    plat(7.6, 13.0);
    canopy(-11.5, -6.6);
    canopy(8.0, 13.0);

    // west station building (claimed) with a canopy over the platform side
    {
      const r = ringOf('71ed838c-bc33-4a9e-9f75-2ebf317c1be9');
      kit.walls(batch, brick, [[r]], 0, 4.6, { bay: 1e6 });
      kit.cap(batch, roofM, [[r]], 4.6);
      kit.cornice(batch, kit.mat('#d8d2c2'), r, 4.2, { height: 0.4, projection: 0.25 });
      for (let k = 0; k < r.length; k++) {
        const p = r[k],
          q = r[(k + 1) % r.length];
        if (Math.hypot(q[0] - p[0], q[1] - p[1]) < 4) continue;
        kit.windowRow(batch, p, q, 1.0, {
          glass,
          frame: white,
          head: 'none',
          width: 1.6,
          height: 2.2,
          bay: 3.2,
          margin: 1.0,
          bars: 1,
        });
      }
    }
    // entrance pavilion on Olympia Way and the east-side pavilion
    for (const id of [
      'fb40e347-d270-4f5b-a2c3-eff00aa98c2a',
      '953b70b1-506f-4ef2-b49a-5ea7322c5697',
    ]) {
      const r = ringOf(id);
      kit.walls(batch, brick, [[r]], 0, 3.8, { bay: 1e6 });
      kit.cap(batch, roofM, [[r]], 3.8);
      kit.cornice(batch, white, r, 3.4, { height: 0.4, projection: 0.4 });
      for (let k = 0; k < r.length; k++) {
        const p = r[k],
          q = r[(k + 1) % r.length];
        if (Math.hypot(q[0] - p[0], q[1] - p[1]) < 3) continue;
        kit.windowRow(batch, p, q, 0.9, {
          glass,
          frame: white,
          head: 'none',
          width: 1.6,
          height: 2.0,
          bay: 2.6,
          margin: 0.6,
          bars: 1,
        });
      }
    }
    // station sign with roundel on the entrance pavilion
    {
      const c = byId['fb40e347-d270-4f5b-a2c3-eff00aa98c2a'].c;
      const sign = kit.paintedMaterial(
        'kensington_olympia:sign',
        512,
        64,
        (cx, w, h) => {
          cx.fillStyle = '#10239e';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#ffffff';
          cx.font = 'bold 30px sans-serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('KENSINGTON (OLYMPIA)', w / 2, h / 2 + 2);
        },
        { roughness: 0.5 },
      );
      const p0 = [c[0] - d[0] * 4 - n[0] * 5.4, c[1] - d[1] * 4 - n[1] * 5.4];
      const p1 = [c[0] + d[0] * 4 - n[0] * 5.4, c[1] + d[1] * 4 - n[1] * 5.4];
      batch.quad(
        sign,
        [p1[0], p1[1], 4.0],
        [p0[0], p0[1], 4.0],
        [p0[0], p0[1], 4.9],
        [p1[0], p1[1], 4.9],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        sign,
        [p0[0], p0[1], 4.0],
        [p1[0], p1[1], 4.0],
        [p1[0], p1[1], 4.9],
        [p0[0], p0[1], 4.9],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // footbridge over the tracks near the south end
    {
      const s = 62,
        z = 7.0;
      const c = P(s, 0.5);
      kit.box(batch, steel, c[0], c[1], z, 3.0, 26, 0.4, ang);
      kit.box(batch, canopyM, c[0], c[1], z + 2.8, 3.4, 26.4, 0.2, ang);
      for (const side of [-1.5, 1.5]) {
        kit.box(
          batch,
          kit.mat('#8fa3ab', { transparent: true, opacity: 0.6 }),
          ...P(s + side, 0.5),
          z + 0.4,
          0.05,
          26,
          2.4,
          ang,
        );
        for (const o of [-12, 0.5, 13])
          kit.box(batch, steel, ...P(s + side, o), 0, 0.3, 0.3, z + 3.0, ang);
      }
      // stair towers onto both platforms
      for (const o of [-9, 10.5]) {
        const st = P(s - 3.5, o);
        kit.box(batch, steel, st[0], st[1], 0.95, 4.0, 2.0, z - 0.95, ang);
        kit.box(batch, canopyM, st[0], st[1], z + 2.8, 4.4, 2.4, 0.2, ang);
      }
    }
    g.add(batch.toGroup('kensington_olympia_station'));
    return g;
  },
};
