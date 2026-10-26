// Serpentine boathouses, north bank of the Serpentine, Hyde Park: the two gabled boat
// sheds standing at the water's edge east of the Old Police House, and the boat-hire
// boathouse and landing stage further east from which the lake's rowing boats and blue
// pedalos are let out. The north bank was also the site of the Royal Humane Society's
// receiving house (1794/1835, bombed in the Second World War).
export default {
  id: 'serpentine_boathouses',
  name: 'Serpentine Boathouses',
  claims: [
    '288fd68e-70b6-4776-aa9f-4cb3b9f582e0',
    '18d11f52-09a0-40ae-adf1-9f1b456639b2',
    'f4ffae48-13f9-4e99-9f12-736b282631f1',
  ],
  references: [
    {
      title: 'The Serpentine - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/The_Serpentine',
      used_for: 'boating on the lake, boathouses on the north bank',
    },
    {
      title:
        'Court blocks removal of Serpentine boathouse - Inner Temple Library / Law Society Gazette',
      url: 'https://www.innertemplelibrary.com/2021/08/court-blocks-removal-of-serpentine-boathouse-law-societys-gazette',
      used_for: 'wooden boathouse on the north bank built by the rowing and pedal boat operator',
    },
    {
      title: 'Victorian London - Royal Humane Society',
      url: 'https://www.victorianlondon.org/organisations/humanesociety.htm',
      used_for: 'receiving house on the north bank of the Serpentine (context)',
    },
    {
      title: 'Hidden in Hyde Park - Adam Yamey',
      url: 'https://adam-yamey-writes.com/tag/drowning/',
      used_for: 'stone marking the Royal Humane Society receiving house site, damaged in WW2',
    },
  ],
  notes:
    'No architectural description found. The two sheds (6 x 11 m footprints at the shoreline) are modelled as ' +
    'timber weatherboarded boat sheds with slate gable roofs and open lake ends; the boat-hire boathouse as a ' +
    'single-storey timber kiosk on a deck over the water with pontoons. Colours, heights (eaves 3.4 m, ridge ' +
    '6.3 m), the pontoon layout and the number of moored rowing boats and pedalos are assumptions.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const boards = kit.paintedMaterial(
      'serpentine_boathouses:boards',
      64,
      64,
      (c, w, h) => {
        c.fillStyle = '#3f5a48';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#2f4537';
        for (let i = 0; i < 4; i++) c.fillRect(0, (i * h) / 4, w, 2);
      },
      { roughness: 0.85 },
    );
    const trim = kit.mat('#ece7da');
    const slate = kit.mat('slate');
    const dark = kit.mat('#1f2326');
    const deck = kit.mat('#8b6e52', { roughness: 0.85 });
    const timberM = kit.mat('#7a5a3e');
    const kioskWall = kit.mat('#e8e2d2', { roughness: 0.8 });
    const glass = kit.mat('dark_glass');
    const pedalo = kit.mat('#2f6db3', { roughness: 0.5 });
    const pedaloW = kit.mat('#f1f1ee', { roughness: 0.5 });
    const rowing = kit.mat('#5b8a5a', { roughness: 0.6 });

    const ringOf = (id) => {
      const b = byId?.[id];
      if (!b) return null;
      const r = b.polys[0][0].slice();
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    // boxed UVs for the boards: walls() maps u per bay and v per 2 storeys of 3.2 m
    const shed = (ring) => {
      const fr = kit.ringFrame(ring);
      const EAVE = 3.4,
        RISE = 2.9;
      kit.walls(batch, boards, [[ring]], 0, EAVE, { bay: 1.0, storey: 0.4 });
      kit.pitchedRoof(batch, slate, boards, ring, fr.angle, EAVE, RISE, 'gabled', {
        overhang: 0.4,
      });
      // white bargeboards and the open lake-end doors (south end = water)
      const c = Math.cos(fr.angle),
        s = Math.sin(fr.angle);
      const ends = [-1, 1].map((sd) => [
        fr.cx + c * sd * (fr.length / 2 + 0.05),
        fr.cy + s * sd * (fr.length / 2 + 0.05),
      ]);
      ends.sort((p, q) => p[1] - q[1]);
      const [sx, sy] = ends[0];
      kit.box(batch, dark, sx, sy, 0, fr.width - 1.2, 0.1, EAVE - 0.4, fr.angle + Math.PI / 2);
      kit.box(batch, trim, sx, sy, EAVE - 0.4, fr.width - 0.8, 0.14, 0.3, fr.angle + Math.PI / 2);
      for (const [ex, ey] of ends) {
        for (const sd of [-1, 1]) {
          const len = Math.hypot(fr.width / 2 + 0.4, RISE);
          const geo = new THREE.BoxGeometry(len, 0.08, 0.25);
          const m = new THREE.Matrix4()
            .makeRotationZ(fr.angle + Math.PI / 2)
            .multiply(
              new THREE.Matrix4().makeRotationY(-sd * Math.atan2(RISE, fr.width / 2 + 0.4)),
            );
          m.setPosition(
            ex - s * sd * (fr.width / 4 + 0.1) * -1,
            ey + c * sd * (fr.width / 4 + 0.1) * -1,
            EAVE + RISE / 2,
          );
          batch.addGeometry(trim, geo, m);
          geo.dispose();
        }
      }
      // small windows on the long sides
      for (let k = 0; k < ring.length; k++) {
        const a = ring[k],
          b = ring[(k + 1) % ring.length];
        if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 9)
          kit.windowRow(batch, a, b, 1.3, {
            count: 3,
            width: 0.9,
            height: 1.0,
            bars: 1,
            glass,
            frame: trim,
            sill: trim,
          });
      }
      // slipway deck in front
      kit.box(batch, deck, sx - s * 0 + 0, sy - 3.0, 0.1, fr.width + 3, 6, 0.25, 0);
    };
    for (const id of [
      '288fd68e-70b6-4776-aa9f-4cb3b9f582e0',
      '18d11f52-09a0-40ae-adf1-9f1b456639b2',
    ]) {
      const r = ringOf(id);
      if (r) shed(r);
    }

    // boat-hire boathouse on its deck with pontoons
    const kr = ringOf('f4ffae48-13f9-4e99-9f12-736b282631f1');
    const rnd = kit.rng(1730);
    if (kr) {
      const fr = kit.ringFrame(kr);
      const c = Math.cos(fr.angle),
        s = Math.sin(fr.angle);
      const P = (u, v) => [fr.cx + u * c - v * s, fr.cy + u * s + v * c];
      const hl = fr.length / 2,
        hw = fr.width / 2;
      const deckR = [
        P(-hl - 2, -hw - 3),
        P(hl + 2, -hw - 3),
        P(hl + 2, hw + 1),
        P(-hl - 2, hw + 1),
      ];
      const dR = kit.ringArea(deckR) < 0 ? deckR.reverse() : deckR;
      kit.cap(batch, deck, [[dR]], 0.45);
      kit.walls(batch, timberM, [[dR]], 0.0, 0.45, { bay: 1e6 });
      const body = [
        P(-hl + 2, -hw + 1),
        P(hl - 2, -hw + 1),
        P(hl - 2, hw - 0.5),
        P(-hl + 2, hw - 0.5),
      ];
      const bR = kit.ringArea(body) < 0 ? body.reverse() : body;
      kit.walls(batch, kioskWall, [[bR]], 0.45, 3.4, { bay: 1e6 });
      kit.windowGrid(batch, bR, 1.3, 1, 3, {
        bay: 2.4,
        width: 1.8,
        height: 1.5,
        bars: 1,
        glass,
        frame: trim,
        sill: trim,
      });
      kit.pitchedRoof(batch, slate, kioskWall, bR, fr.angle, 3.4, 1.5, 'hipped', { overhang: 0.9 });
      // pontoons out into the lake (south of the boathouse) with moored boats
      const south = Math.sin(fr.angle + Math.PI / 2) < 0 ? 1 : -1;
      for (const pu of [-9, 0, 9]) {
        const a = P(pu, south * (hw + 3)),
          b = P(pu, south * (hw + 22));
        const mx = (a[0] + b[0]) / 2,
          my = (a[1] + b[1]) / 2;
        kit.box(batch, deck, mx, my, 0.05, 1.8, 19, 0.3, fr.angle);
        // boats either side
        for (let i = 0; i < 6; i++) {
          for (const sd of [-1, 1]) {
            const p = P(pu + sd * 2.1, south * (hw + 4.5 + i * 2.9));
            const isPedalo = (pu > 0) ^ (sd < 0);
            if (isPedalo) {
              kit.box(batch, pedalo, p[0], p[1], 0.05, 2.4, 1.5, 0.45, fr.angle);
              kit.box(batch, pedaloW, p[0], p[1], 0.5, 1.2, 1.3, 0.35, fr.angle);
            } else {
              const hull = new THREE.CylinderGeometry(
                0.62,
                0.45,
                3.6,
                8,
                1,
                false,
                Math.PI / 2,
                Math.PI,
              )
                .rotateZ(Math.PI)
                .scale(1, 1, 0.6);
              const m = new THREE.Matrix4()
                .makeRotationZ(fr.angle + (rnd() - 0.5) * 0.1)
                .multiply(new THREE.Matrix4().makeRotationZ(Math.PI / 2));
              m.setPosition(p[0], p[1], 0.38);
              batch.addGeometry(rowing, hull, m);
              hull.dispose();
            }
          }
        }
      }
    }

    g.add(batch.toGroup('serpentine_boathouses'));
    return g;
  },
};
