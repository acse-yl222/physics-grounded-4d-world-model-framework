// The Italian Gardens, Kensington Gardens (c.1860, laid out by James Pennethorne for
// Prince Albert; pumphouse by Sir Charles Barry with Robert Richardson Banks). A formal
// water garden at the head of the Long Water: four main basins with carved
// Carrara-marble rosette fountains round a central round basin, Portland stone
// copings, balustraded terrace edges with urns and vases, the Tazza fountain (bowl
// carried by mermen) overlooking the Long Water, and at the north end the ornate
// Italianate pumphouse whose roof "pillar" is the disguised chimney of the steam
// engine that once worked the fountains.
export default {
  id: 'italian_gardens',
  name: 'Italian Gardens and Pumphouse',
  claims: ['29bfc20d-a259-4bc7-bae6-c5526007ac6c'],
  references: [
    {
      title: 'Kensington Gardens - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Kensington_Gardens',
      used_for: 'Italian Gardens c.1860, gift of Prince Albert, at the north end of the Long Water',
    },
    {
      title: 'Italian Gardens - The Royal Parks',
      url: 'https://www.royalparks.org.uk/node/1051',
      used_for:
        'four main basins with Carrara marble rosettes, Tazza fountain of Portland stone and marble on mermen, pumphouse steam engine and disguised flue in the roof pillar, Grade II',
    },
    {
      title: 'The Italian Gardens - Victorian Web',
      url: 'https://www.victorianweb.org/victorian/art/parks/11b.html',
      used_for: 'pumphouse/shelter by Sir Charles Barry and R. R. Banks; Pennethorne layout',
    },
    {
      title: 'CWO restores Italian Gardens for Royal Parks project - Stone Specialist',
      url: 'https://www.stonespecialist.com/news/stone-projects/cwo-restores-italian-gardens-royal-parks-project',
      used_for: 'Portland stone and marble fabric of the basins, urns and Tazza',
    },
    {
      title: 'List of public art in Kensington Gardens - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/List_of_public_art_in_Kensington_Gardens',
      used_for: 'reliefs and statuary of the gardens by John Thomas',
    },
  ],
  notes:
    'Basin outlines are read from the scene water layer so they match the map; the garden axis (8.6 deg west of ' +
    'north) and terrace extent follow them. Pumphouse built on its 12 m footprint at 6.2 m to the cornice with a ' +
    '3-bay arcaded south loggia, balustraded parapet, low hipped lead roof and an 11 m chimney column with an urn; ' +
    'arcade spans, parapet and chimney proportions are estimates. Rosette, Tazza mermen and urn forms are ' +
    'simplified lathes; jets are drawn as translucent spouts. Overture h=13 m for the pumphouse is not used.',
  build({ THREE, kit, scene, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const th = (8.6 * Math.PI) / 180;
    const U = [Math.cos(th), Math.sin(th)],
      V = [-Math.sin(th), Math.cos(th)];
    const C = [1731.5, 458.0];
    const L = (u, v) => [C[0] + U[0] * u + V[0] * v, C[1] + U[1] * u + V[1] * v];
    const toLocal = ([x, y]) => [
      (x - C[0]) * U[0] + (y - C[1]) * U[1],
      (x - C[0]) * V[0] + (y - C[1]) * V[1],
    ];
    const ang = th;

    const portland = kit.mat('portland_stone');
    const marble = kit.mat('#eeece6', { roughness: 0.5 });
    const coping = kit.mat('#e3ddcf', { roughness: 0.8 });
    const paving = kit.mat('#d8d0bc', { roughness: 0.95 });
    const gravel = kit.mat('gravel');
    const lead = kit.mat('lead');
    const stucco = kit.mat('#e8e1d2', { roughness: 0.8 });
    const glassD = kit.mat('dark_glass');
    const jet = kit.mat('#e9f4f8', { transparent: true, opacity: 0.6, roughness: 0.1 });
    const waterM = kit.ground('water');
    const lawn = kit.mat('grass');

    const lbox = (m, u, v, z0, w, d, h, rz = 0) => {
      const p = L(u, v);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, ang + rz);
    };
    const turn = (m, prof, u, v, z, seg = 16) => {
      const p = L(u, v);
      const geo = new THREE.LatheGeometry(
        prof.map(([r, h]) => new THREE.Vector2(r, h)),
        seg,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(m, geo, new THREE.Matrix4().makeTranslation(p[0], p[1], z));
      geo.dispose();
    };
    const rev = (r) => r.slice().reverse();
    const ringL = (pts) => pts.map(([u, v]) => L(u, v));

    // ---- terrace: paved platform with lawn panels ---------------------------------------
    const U0 = -28,
      U1 = 28,
      V0 = -41,
      V1 = 39;
    const terrace = ringL([
      [U0, V0],
      [U1, V0],
      [U1, V1],
      [U0, V1],
    ]);
    kit.cap(batch, paving, [[terrace]], 0.18, { scale: 4 });
    kit.walls(batch, coping, [[terrace]], 0.0, 0.18, { bay: 1e6 });

    // ---- basins from the scene water layer --------------------------------------------
    const basins = [];
    for (const w of scene.water ?? []) {
      if (!w.poly) continue;
      const r = w.poly[0];
      const cx = r.reduce((a, p) => a + p[0], 0) / r.length,
        cy = r.reduce((a, p) => a + p[1], 0) / r.length;
      const [lu, lv] = toLocal([cx, cy]);
      if (Math.abs(lu) < 30 && lv > -50 && lv < 40) {
        let ring = r.slice();
        if (kit.ringArea(ring) < 0) ring.reverse();
        basins.push({ ring, c: [cx, cy], lu, lv, area: Math.abs(kit.ringArea(ring)) });
      }
    }
    for (const b of basins) {
      const big = b.area > 200;
      const inside = kit.offsetRing(b.ring, -0.1);
      // water surface raised to terrace level, coping kerb round it
      kit.cap(batch, waterM, [[inside]], 0.26, { scale: 20 });
      const out = kit.offsetRing(b.ring, big ? 0.75 : 0.5);
      kit.cap(batch, coping, [[out, rev(inside)]], 0.55);
      kit.walls(batch, coping, [[out]], 0.15, 0.55, { bay: 1e6 });
      kit.walls(batch, portland, [[rev(inside)]], 0.26, 0.55, { bay: 1e6 });
      const [x, y] = b.c;
      if (big) {
        // carved marble rosette with a low jet
        const geo = new THREE.LatheGeometry(
          [
            [0, 0],
            [1.3, 0],
            [1.4, 0.15],
            [1.0, 0.35],
            [0.5, 0.45],
            [0.25, 0.6],
            [0, 0.62],
          ].map(([r, h]) => new THREE.Vector2(r, h)),
          16,
        ).rotateX(Math.PI / 2);
        batch.addGeometry(marble, geo, new THREE.Matrix4().makeTranslation(x, y, 0.2));
        geo.dispose();
        const sp = new THREE.ConeGeometry(0.35, 2.2, 8, 1, true).rotateX(Math.PI / 2);
        batch.addGeometry(jet, sp, new THREE.Matrix4().makeTranslation(x, y, 0.8 + 1.1));
        sp.dispose();
      } else if (b.lv > -40) {
        // central round basin: tiered marble fountain
        turn(
          marble,
          [
            [0, 0],
            [0.5, 0],
            [0.35, 0.3],
            [0.28, 1.2],
            [1.4, 1.35],
            [1.5, 1.55],
            [0.3, 1.6],
            [0.2, 2.2],
            [0.6, 2.3],
            [0.65, 2.45],
            [0, 2.5],
          ],
          b.lu,
          b.lv,
          0.26,
        );
        const sp = new THREE.ConeGeometry(0.25, 1.6, 8, 1, true).rotateX(Math.PI / 2);
        batch.addGeometry(jet, sp, new THREE.Matrix4().makeTranslation(x, y, 2.75 + 0.8));
        sp.dispose();
      } else {
        // Tazza fountain at the head of the Long Water: bowl on a merman pedestal
        turn(
          portland,
          [
            [0, 0],
            [1.6, 0],
            [1.6, 0.6],
            [1.2, 0.7],
            [0.7, 0.9],
            [0.55, 1.8],
            [0.8, 2.0],
            [0, 2.0],
          ],
          b.lu,
          b.lv,
          0.1,
        );
        for (let k = 0; k < 4; k++) {
          // seated mermen round the shaft
          const a = (k / 4) * Math.PI * 2 + Math.PI / 4;
          const px = x + Math.cos(a) * 0.95,
            py = y + Math.sin(a) * 0.95;
          const body = new THREE.SphereGeometry(0.38, 8, 6).scale(1, 1, 1.6);
          batch.addGeometry(marble, body, new THREE.Matrix4().makeTranslation(px, py, 1.35));
          body.dispose();
        }
        turn(
          marble,
          [
            [0, 0],
            [0.3, 0],
            [1.1, 0.25],
            [2.0, 0.55],
            [2.15, 0.75],
            [1.9, 0.78],
            [0, 0.5],
          ],
          b.lu,
          b.lv,
          2.1,
          24,
        );
        turn(
          portland,
          [
            [0, 0],
            [0.25, 0],
            [0.2, 0.6],
            [0.45, 0.7],
            [0, 0.85],
          ],
          b.lu,
          b.lv,
          2.6,
        );
        const sp = new THREE.ConeGeometry(0.22, 1.4, 8, 1, true).rotateX(Math.PI / 2);
        batch.addGeometry(jet, sp, new THREE.Matrix4().makeTranslation(x, y, 3.45 + 0.7));
        sp.dispose();
      }
    }

    // ---- lawn strips beside the basins, gravel cross walk -------------------------------
    for (const su of [-1, 1]) {
      const lr = ringL([
        [su > 0 ? 25 : -27, -36],
        [su > 0 ? 27 : -25, -36],
        [su > 0 ? 27 : -25, 36],
        [su > 0 ? 25 : -27, 36],
      ]);
      kit.cap(batch, lawn, [[lr]], 0.2);
    }
    kit.cap(
      batch,
      gravel,
      [
        [
          ringL([
            [-3, 33],
            [3, 33],
            [3, 39],
            [-3, 39],
          ]),
        ],
      ],
      0.19,
    );

    // ---- balustrades with piers and urns along the Long Water side ---------------------
    const urn = (u, v, z, s = 1) =>
      turn(
        portland,
        [
          [0, 0],
          [0.28 * s, 0],
          [0.18 * s, 0.15 * s],
          [0.16 * s, 0.3 * s],
          [0.42 * s, 0.55 * s],
          [0.45 * s, 0.75 * s],
          [0.3 * s, 0.95 * s],
          [0.36 * s, 1.0 * s],
          [0, 1.05 * s],
        ],
        u,
        v,
        z,
        12,
      );
    const balLine = (a, b) => {
      kit.balustrade(batch, portland, [L(a[0], a[1]), L(b[0], b[1])], 0.18, {
        height: 0.95,
        spacing: 0.32,
      });
    };
    // south terrace edge, broken in the centre for the Tazza steps
    balLine([U0 + 0.5, V0 + 0.4], [-4, V0 + 0.4]);
    balLine([4, V0 + 0.4], [U1 - 0.5, V0 + 0.4]);
    // east and west edges
    balLine([U1 - 0.4, V0 + 0.5], [U1 - 0.4, V1 - 6]);
    balLine([U0 + 0.4, V0 + 0.5], [U0 + 0.4, V1 - 6]);
    const piers = [];
    for (let u = U0 + 0.5; u <= U1 - 0.4; u += 7) piers.push([u, V0 + 0.4]);
    for (let v = V0 + 7.5; v < V1 - 5; v += 7) piers.push([U0 + 0.4, v], [U1 - 0.4, v]);
    piers.push([-4, V0 + 0.4], [4, V0 + 0.4]);
    for (const [u, v] of piers) {
      lbox(portland, u, v, 0.18, 0.6, 0.6, 1.15);
      lbox(coping, u, v, 1.33, 0.75, 0.75, 0.12);
      urn(u, v, 1.45, 0.75);
    }
    // four large marble vases at the corners of the basin group
    for (const [u, v] of [
      [-21, -37.5],
      [21, -37.5],
      [-21, 32.5],
      [21, 32.5],
    ]) {
      lbox(portland, u, v, 0.18, 1.3, 1.3, 1.2);
      lbox(coping, u, v, 1.38, 1.5, 1.5, 0.15);
      turn(
        marble,
        [
          [0, 0],
          [0.45, 0],
          [0.3, 0.25],
          [0.28, 0.45],
          [0.75, 0.85],
          [0.85, 1.25],
          [0.6, 1.55],
          [0.7, 1.62],
          [0, 1.66],
        ],
        u,
        v,
        1.53,
        16,
      );
    }

    // ---- pumphouse ------------------------------------------------------------------
    const ph = byId?.['29bfc20d-a259-4bc7-bae6-c5526007ac6c'];
    let pc = [1724.9, 503.3];
    if (ph) {
      const r = ph.polys[0][0];
      pc = [r.reduce((a, p) => a + p[0], 0) / r.length, r.reduce((a, p) => a + p[1], 0) / r.length];
    }
    const [pu, pv] = toLocal(pc);
    const PW = 11.8,
      PD = 11.8,
      EAVE = 6.2;
    const pring = (pad = 0) =>
      ringL([
        [pu - PW / 2 - pad, pv - PD / 2 - pad],
        [pu + PW / 2 + pad, pv - PD / 2 - pad],
        [pu + PW / 2 + pad, pv + PD / 2 + pad],
        [pu - PW / 2 - pad, pv + PD / 2 + pad],
      ]);
    // plinth, walls, cornice, parapet
    kit.walls(batch, portland, [[pring(0.25)]], 0, 0.6, { bay: 1e6 });
    kit.cap(batch, portland, [[pring(0.25)]], 0.6);
    // walls in four piers-and-panels, south face opened as an arcaded loggia
    const wallT = 0.6;
    const south = pv - PD / 2;
    // north, east, west solid walls
    lbox(stucco, pu, pv + PD / 2 - wallT / 2, 0.6, PW, wallT, EAVE - 0.6);
    lbox(stucco, pu - PW / 2 + wallT / 2, pv, 0.6, wallT, PD, EAVE - 0.6);
    lbox(stucco, pu + PW / 2 - wallT / 2, pv, 0.6, wallT, PD, EAVE - 0.6);
    // south arcade: 4 piers, 3 round arches
    const spans = 3,
      pierW = 1.3,
      openW = (PW - (spans + 1) * pierW) / spans;
    for (let k = 0; k <= spans; k++) {
      const uc = pu - PW / 2 + pierW / 2 + k * (pierW + openW);
      lbox(stucco, uc, south + wallT / 2, 0.6, pierW, wallT, EAVE - 0.6);
      // pilaster strips
      lbox(portland, uc, south - 0.08, 0.6, pierW * 0.7, 0.16, EAVE - 1.2);
    }
    for (let k = 0; k < spans; k++) {
      const uc = pu - PW / 2 + pierW + openW / 2 + k * (pierW + openW);
      const springZ = 3.6,
        r = openW / 2;
      // spandrel above the arch as an extruded shape with a semicircular cut
      const sh = new THREE.Shape();
      sh.moveTo(-r, springZ);
      for (let i = 0; i <= 12; i++) {
        const a = Math.PI - (i / 12) * Math.PI;
        sh.lineTo(r * Math.cos(a), springZ + r * Math.sin(a));
      }
      sh.lineTo(r, EAVE);
      sh.lineTo(-r, EAVE);
      sh.closePath();
      const sg = new THREE.ExtrudeGeometry(sh, {
        depth: wallT,
        bevelEnabled: false,
        curveSegments: 6,
      });
      const p = L(uc, south);
      const m = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(U[0], U[1], 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(-V[0], -V[1], 0),
      );
      // extrusion runs towards -V (outwards); start at the inner face
      const q = L(uc, south + wallT);
      m.setPosition(q[0], q[1], 0);
      batch.addGeometry(stucco, sg, m);
      sg.dispose();
      void p;
      // archivolt and keystone
      const tor = new THREE.TorusGeometry(r + 0.12, 0.12, 4, 12, Math.PI);
      const mt = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      const pt = L(uc, south - 0.05);
      mt.setPosition(pt[0], pt[1], springZ);
      batch.addGeometry(portland, tor, mt);
      tor.dispose();
      lbox(portland, uc, south - 0.1, springZ + r - 0.15, 0.45, 0.2, 0.6);
    }
    // inner back wall glazing hint and floor
    kit.cap(batch, paving, [[pring(-0.3)]], 0.62);
    // windows on the east/west faces: tall round-headed blind niches
    for (const su of [-1, 1]) {
      const a = L(pu + su * (PW / 2), pv + (su > 0 ? -PD / 2 + 1.5 : PD / 2 - 1.5));
      const b = L(pu + su * (PW / 2), pv + (su > 0 ? PD / 2 - 1.5 : -PD / 2 + 1.5));
      kit.windowRow(batch, a, b, 1.6, {
        count: 2,
        width: 1.3,
        height: 2.6,
        head: 'arch',
        glass: glassD,
        frame: portland,
        bars: 0,
        surround: 0.2,
        surroundMat: portland,
      });
    }
    // cornice + balustraded parapet + low hipped lead roof
    const top = pring(0);
    kit.cornice(batch, portland, top, EAVE, { height: 0.55, projection: 0.45, steps: 2 });
    const pr = pring(0.1);
    for (let k = 0; k < 4; k++) {
      kit.balustrade(batch, portland, [pr[k], pr[(k + 1) % 4]], EAVE + 0.55, {
        height: 0.85,
        spacing: 0.32,
      });
      kit.box(batch, portland, pr[k][0], pr[k][1], EAVE + 0.55, 0.6, 0.6, 1.0, ang);
      const p = pr[k];
      const geo = new THREE.LatheGeometry(
        [
          [0, 0],
          [0.2, 0],
          [0.3, 0.3],
          [0.22, 0.55],
          [0, 0.6],
        ].map(([r, h]) => new THREE.Vector2(r, h)),
        10,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(
        portland,
        geo,
        new THREE.Matrix4().makeTranslation(p[0], p[1], EAVE + 1.55),
      );
      geo.dispose();
    }
    kit.pitchedRoof(batch, lead, stucco, pring(-0.4), ang, EAVE + 0.55, 1.6, 'pyramidal', {
      overhang: 0,
    });
    // disguised chimney: tall column on a pedestal with capital and urn finial
    turn(
      portland,
      [
        [0, 0],
        [0.9, 0],
        [0.9, 1.2],
        [0.75, 1.35],
        [0.55, 1.5],
        [0.48, 5.0],
        [0.42, 8.6],
        [0.7, 8.8],
        [0.75, 9.1],
        [0.35, 9.2],
        [0.5, 9.6],
        [0.55, 10.0],
        [0.3, 10.4],
        [0.12, 10.8],
        [0, 10.9],
      ],
      pu,
      pv,
      EAVE + 0.6,
      16,
    );

    g.add(batch.toGroup('italian_gardens'));
    return g;
  },
};
