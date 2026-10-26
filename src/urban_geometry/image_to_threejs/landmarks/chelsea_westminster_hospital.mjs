// Chelsea and Westminster Hospital, 369 Fulham Road (Sheppard Robson, 1989-93, on
// the St Stephen's Hospital site). A deep-plan block of office-like construction
// wrapped round a full-height central "street" and atrium under one of the first
// ETFE cushion roofs; light clad elevations with continuous window bands and a
// glazed entrance on Fulham Road.
export default {
  id: 'chelsea_westminster_hospital',
  name: 'Chelsea and Westminster Hospital',
  claims: ['3348b0f2-e92b-4e04-860b-bdf95db229df'],
  references: [
    {
      title: 'Chelsea and Westminster Hospital - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Chelsea_and_Westminster_Hospital',
      used_for: "Sheppard Robson design, St Stephen's site, opened May 1993",
    },
    {
      title: 'Art and surgery - Building magazine',
      url: 'https://www.building.co.uk/focus/art-surgery/1014174.article',
      used_for:
        '(search summary only) central street and atrium, early ETFE membrane roof, office-type construction',
    },
    {
      title: 'Chapel, Chelsea and Westminster Hospital - London Church Buildings',
      url: 'https://londonchurchbuildings.com/2024/04/18/chapel-chelsea-westminster-hospital-fulham-road-chelsea/',
      used_for: 'building context on Fulham Road',
    },
    {
      title: 'Atrium lights - Historic England Archive',
      url: 'https://images.historicenglandservices.org.uk/industry/engineering-construction-building-hospitals/atrium-lights-jlp01-10-55176-24318220.html',
      used_for: 'existence of the large atrium (Laing construction photo record, caption only)',
    },
  ],
  notes:
    'Footprint and 16.9 m height from Overture; atrium position/size (about 120 x 28 m along the long axis) and the ' +
    'vaulted ETFE roof are inferred from descriptions, not measured. Cladding colour (light panels with blue-grey ' +
    'window bands) is approximate: no returned source specified the materials. Ribbon-window module (1.75 m), ' +
    'spandrel bands, atrium galleries, plant louvres, entrance canopy/revolving door/sign and the atrium trees are ' +
    'schematic.',
  build({ THREE, kit, buildings, frame, placeAssets }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const H = b.h;
    const ca = Math.cos(frame.angle),
      sa = Math.sin(frame.angle);
    const W = (u, v) => [frame.cx + u * ca - v * sa, frame.cy + u * sa + v * ca];

    const ground = kit.facade('glass', 2);
    const white = kit.mat('#ecebe6', { roughness: 0.6 });
    const roofM = kit.mat('#9a9893', { roughness: 0.95 });
    const glassM = kit.mat('glass');
    const etfe = kit.paintedMaterial(
      'chelsea_westminster_hospital:etfe',
      128,
      128,
      (c, w, h) => {
        c.fillStyle = '#7f8d96';
        c.fillRect(0, 0, w, h);
        for (let y = 0; y < 2; y++)
          for (let x = 0; x < 2; x++) {
            const grd = c.createRadialGradient(
              x * 64 + 32,
              y * 64 + 32,
              4,
              x * 64 + 32,
              y * 64 + 32,
              34,
            );
            grd.addColorStop(0, '#e8eef1');
            grd.addColorStop(1, '#a9b8c0');
            c.fillStyle = grd;
            c.fillRect(x * 64 + 3, y * 64 + 3, 58, 58);
          }
      },
      { roughness: 0.3, metalness: 0.1 },
    );

    // Perimeter walls: glazed ground floor, clad upper storeys with 3D ribbon
    // windows, projecting spandrel bands, parapet with coping.
    const panels = kit.paintedMaterial(
      'chelsea_westminster_hospital:panels',
      128,
      128,
      (c, w, h) => {
        c.fillStyle = '#e6e3da';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#cfcbc0';
        for (let x = 0; x < w; x += 32) c.fillRect(x, 0, 2, h);
        for (let y = 0; y < h; y += 64) c.fillRect(0, y, w, 2);
      },
      { roughness: 0.6 },
    );
    const alu = kit.mat('#c4c9cc', { roughness: 0.35, metalness: 0.6 });
    const ribbon = kit.mat('#4f6878', { roughness: 0.15, metalness: 0.3 });
    let outerRing = b.polys[0][0].slice();
    if (kit.ringArea(outerRing) < 0) outerRing.reverse();
    kit.walls(batch, ground, [[outerRing]], 0, 4.6, { bay: 3.6, storey: 4.6 });
    kit.walls(batch, panels, [[outerRing]], 4.6, H - 0.9, { bay: 3.6, storey: 3.6, uvBase: 4.6 });
    kit.walls(batch, white, [[outerRing]], H - 0.9, H + 0.4, {});
    kit.cornice(batch, white, outerRing, 0, { height: 0.5, projection: 0.15 });
    kit.cornice(batch, white, outerRing, 4.3, { height: 0.5, projection: 0.6 }); // canopy band over the ground floor
    kit.cornice(batch, alu, outerRing, H + 0.3, { height: 0.15, projection: 0.12 });
    const FL = Math.max(1, Math.floor((H - 0.9 - 4.6) / 3.6));
    const fh = (H - 0.9 - 4.6) / FL;
    for (let f = 0; f < FL; f++) {
      const z = 4.6 + f * fh;
      for (let k = 0; k < outerRing.length; k++) {
        const p = outerRing[k],
          q = outerRing[(k + 1) % outerRing.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 2.5) continue;
        kit.windowRow(batch, p, q, z + 1.0, {
          width: 1.5,
          height: 1.7,
          bay: 1.75,
          margin: 0.3,
          depth: 0.1,
          glass: ribbon,
          frame: alu,
          sill: alu,
          head: 'none',
          bars: 0,
        });
      }
      if (f > 0) kit.cornice(batch, white, outerRing, z - 0.1, { height: 0.25, projection: 0.2 });
    }

    // Roof with the atrium cut out.
    const AU = Math.min(60, frame.length / 2 - 18),
      AV = Math.min(14, frame.width / 2 - 18);
    const atrium = [W(-AU, -AV), W(AU, -AV), W(AU, AV), W(-AU, AV)];
    const outer = b.polys[0][0];
    const ccw = kit.ringArea(outer) > 0;
    const outerCCW = ccw ? outer : outer.slice().reverse();
    kit.cap(batch, roofM, [[outerCCW, atrium.slice().reverse()]], H);
    // atrium inner glazed walls (facing inward)
    kit.walls(batch, kit.facade('glass', 0), [[atrium.slice().reverse()]], 0, H, {
      bay: 3.6,
      storey: 3.6,
    });
    kit.cap(batch, kit.mat('paving'), [[atrium]], 0.2);

    // Vaulted ETFE roof over the atrium (barrel along the long axis) with steel ribs.
    const rise = 6.5,
      M = 10;
    const prof = [];
    for (let k = 0; k <= M; k++) {
      const v = -AV + (2 * AV * k) / M;
      prof.push([v, H + 0.4 + rise * (1 - (v / AV) ** 2)]);
    }
    for (let k = 0; k < M; k++) {
      const [v0, z0] = prof[k],
        [v1, z1] = prof[k + 1];
      const a = W(-AU, v0),
        bq = W(AU, v0),
        c = W(AU, v1),
        d = W(-AU, v1);
      batch.quad(
        etfe,
        [...a, z0],
        [...bq, z0],
        [...c, z1],
        [...d, z1],
        [0, v0 / 4],
        [AU / 2, v0 / 4],
        [AU / 2, v1 / 4],
        [0, v1 / 4],
      );
    }
    // gable ends
    for (const u of [-AU, AU]) {
      const verts = prof.map(([v, z]) => [...W(u, v), z]);
      const base = [
        [...W(u, AV), H + 0.4],
        [...W(u, -AV), H + 0.4],
      ];
      const all = [...verts, ...base];
      const tris = [];
      const ci = all.length - 1; // fan from one base corner
      for (let k = 0; k < verts.length - 1; k++) tris.push(ci, k, k + 1);
      tris.push(ci, verts.length - 1, verts.length);
      const back = [];
      for (let i = 0; i < tris.length; i += 3) back.push(tris[i], tris[i + 2], tris[i + 1]);
      batch.add(
        glassM,
        all,
        all.map(() => [0, 0]),
        [...tris, ...back],
      );
    }
    for (let u = -AU; u <= AU + 1e-6; u += 7.5) {
      for (let k = 0; k < M; k++) {
        const [v0, z0] = prof[k],
          [v1, z1] = prof[k + 1];
        const p = new THREE.Vector3(...W(u, v0), z0 + 0.15),
          q = new THREE.Vector3(...W(u, v1), z1 + 0.15);
        const len = p.distanceTo(q);
        const geo = new THREE.BoxGeometry(0.35, len, 0.35);
        const m = new THREE.Matrix4().compose(
          p.clone().add(q).multiplyScalar(0.5),
          new THREE.Quaternion().setFromUnitVectors(
            new THREE.Vector3(0, 1, 0),
            q.clone().sub(p).normalize(),
          ),
          new THREE.Vector3(1, 1, 1),
        );
        batch.addGeometry(white, geo, m);
      }
    }

    // Atrium galleries: white balcony edges with handrails on each floor.
    for (let f = 1; f <= FL; f++) {
      const z = 4.6 + (f - 1) * fh;
      const inner = atrium.slice().reverse();
      kit.cornice(batch, white, inner, z - 0.6, { height: 0.6, projection: 0.8 });
      kit.balustrade(
        batch,
        alu,
        [...kit.offsetRing(inner, 0.7), kit.offsetRing(inner, 0.7)[0]],
        z,
        {
          height: 1.1,
          spacing: 1.2,
        },
      );
    }
    // atrium planting and seating on the floor of the "street"
    {
      const tr = [],
        bn = [];
      for (let u = -AU + 8; u < AU - 4; u += 14) {
        tr.push([...W(u, 0), u]);
        bn.push([...W(u + 4, 3), frame.angle], [...W(u + 4, -3), frame.angle + Math.PI]);
      }
      g.add(
        placeAssets('lime_tree', tr, {
          z: 0.2,
          scaleOf: () => 6,
          name: 'chelsea_westminster_hospital:atrium_trees',
        }),
      );
      g.add(
        placeAssets('bench', bn, { z: 0.2, name: 'chelsea_westminster_hospital:atrium_benches' }),
      );
    }

    // Rooftop plant enclosures (louvred) and lift overruns, with roof-edge handrail.
    const louvre = kit.paintedMaterial('chelsea_westminster_hospital:louvre', 64, 64, (c, w, h) => {
      c.fillStyle = '#b7b4ac';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#8e8b84';
      for (let y = 4; y < h; y += 8) c.fillRect(0, y, w, 3);
    });
    const r = kit.rng(0.4242);
    for (const [u, v, lw, lv] of [
      [-AU - 9, 0, 10, 22],
      [AU + 9, 0, 10, 22],
      [0, AV + 10, 26, 7],
      [0, -AV - 10, 26, 7],
      [-40, AV + 10, 12, 6],
      [40, -AV - 10, 12, 6],
    ]) {
      const [x, y] = W(u, v);
      const hh = 2.8 + r() * 1.2;
      kit.box(batch, louvre, x, y, H, lw, lv, hh, frame.angle);
      kit.box(batch, kit.mat('#9a9893'), x, y, H + hh, lw + 0.4, lv + 0.4, 0.2, frame.angle);
      for (let k = 0; k < 2; k++) {
        const [fx, fy] = W(u - lw / 4 + (k * lw) / 2, v);
        batch.addGeometry(
          kit.mat('#7d7b76'),
          new THREE.CylinderGeometry(1.0, 1.0, 0.6, 12).rotateX(Math.PI / 2),
          new THREE.Matrix4().makeTranslation(fx, fy, H + hh + 0.5),
        );
      }
    }
    kit.balustrade(
      batch,
      alu,
      [...kit.offsetRing(outerRing, -1.0), kit.offsetRing(outerRing, -1.0)[0]],
      H,
      {
        height: 1.1,
        spacing: 3,
      },
    );

    // Glazed main entrance on the Fulham Road (north-west) front: canopy on
    // columns, signage, revolving door, bollards, lamps and trees.
    {
      const uEnd =
        W(frame.length / 2, 0)[1] > W(-frame.length / 2, 0)[1]
          ? frame.length / 2
          : -frame.length / 2;
      const sgn = Math.sign(uEnd);
      const rz = frame.angle;
      const [x, y] = W(uEnd + sgn * 3, 0);
      kit.box(batch, glassM, x, y, 4.6, 6, 24, 0.2, rz);
      kit.box(batch, white, x, y, 4.8, 6.4, 24.4, 0.45, rz);
      for (const v of [-11, -5.5, 5.5, 11]) {
        const [px, py] = W(uEnd + sgn * 5.6, v);
        batch.addGeometry(
          white,
          new THREE.CylinderGeometry(0.22, 0.22, 4.6, 12).rotateX(Math.PI / 2),
          new THREE.Matrix4().makeTranslation(px, py, 2.3),
        );
      }
      const [ex, ey] = W(uEnd + sgn * 0.15, 0);
      kit.box(batch, kit.mat('dark_glass'), ex, ey, 0, 0.4, 16, 4.4, rz);
      for (let k = -8; k <= 8; k += 1.6) {
        const [mx, my] = W(uEnd + sgn * 0.4, k);
        kit.box(batch, alu, mx, my, 0, 0.12, 0.12, 4.4, rz);
      }
      // revolving door drum
      const [dx, dy] = W(uEnd + sgn * 1.4, 0);
      batch.addGeometry(
        glassM,
        new THREE.CylinderGeometry(1.4, 1.4, 2.6, 16).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeTranslation(dx, dy, 1.3),
      );
      batch.addGeometry(
        alu,
        new THREE.CylinderGeometry(1.5, 1.5, 0.3, 16).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeTranslation(dx, dy, 2.75),
      );
      // NHS-blue name sign on the canopy fascia
      const sign = kit.paintedMaterial('chelsea_westminster_hospital:sign', 512, 64, (c, w, h) => {
        c.fillStyle = '#005eb8';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#ffffff';
        c.font = 'bold 30px sans-serif';
        c.textAlign = 'center';
        c.fillText('Chelsea and Westminster Hospital', w / 2, 43);
      });
      const [sx, sy] = W(uEnd + sgn * 6.25, 0);
      kit.box(batch, sign, sx, sy, 4.75, 0.08, 14, 0.55, rz);
      const bol = [],
        lp = [],
        tr = [];
      for (let v = -14; v <= 14; v += 2) bol.push([...W(uEnd + sgn * 8, v), 0]);
      for (const v of [-20, 20])
        lp.push([...W(uEnd + sgn * 9, v), rz + (sgn > 0 ? Math.PI / 2 : -Math.PI / 2)]);
      for (const v of [-30, -24, 24, 30]) tr.push([...W(uEnd + sgn * 9, v), v]);
      g.add(placeAssets('bollard', bol, { name: 'chelsea_westminster_hospital:bollards' }));
      g.add(placeAssets('street_lamp', lp, { name: 'chelsea_westminster_hospital:lamps' }));
      g.add(
        placeAssets('london_plane', tr, {
          scaleOf: () => 10,
          name: 'chelsea_westminster_hospital:trees',
        }),
      );
    }

    g.add(batch.toGroup('chelsea_westminster_hospital'));
    return g;
  },
};
