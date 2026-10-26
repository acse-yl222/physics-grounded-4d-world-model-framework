// Michelin House, 81 Fulham Road (François Espinasse, opened 1911): Michelin's first
// UK headquarters and tyre depot, ferro-concrete (Hennebique) clad in white faience
// with blue, yellow and green detailing. The Fulham Road front has large arched
// ground-floor bays under the big stained-glass Bibendum window and is framed by
// two corner towers crowned by glass cupolas shaped like stacks of tyres. Side
// elevations carry open segmental pediments with faience tyres and, at ground
// floor, Gilardoni tile panels of early motor races.
export default {
  id: 'michelin_house',
  name: 'Michelin House',
  claims: ['57fd7837-1170-4d19-a554-f6c80be4b670'],
  references: [
    {
      title: 'Michelin House - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Michelin_House',
      used_for:
        'Espinasse 1911, Bibendum stained glass, corner towers with tyre-stack glass cupolas, faience, tile panels',
    },
    {
      title: 'Michelin House - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101080656-michelin-house-the-main-part-facing-the-fulham-road-brompton-hans-town-ward',
      used_for: 'listing of the main part facing Fulham Road',
    },
    {
      title: 'Michelin House, Chelsea, London - Manchester History',
      url: 'https://manchesterhistory.net/architecture/1920/michelin.html',
      used_for: 'faience facade and Art Nouveau / Art Deco character',
    },
    {
      title: 'Memories of Michelin House - David Adrian Smith',
      url: 'https://davidadriansmith.com/2023/10/05/memories-of-michelin-house-a-london-marvel/',
      used_for: 'general appearance of the front and side elevations',
    },
  ],
  notes:
    'Overture gives a simplified trapezoid (15 m Fulham Road front widening to 35 m at the rear) and an inferred 9.3 m ' +
    "height; walls are raised to 13 m (towers 15 m + cupolas) from the building's three tall storeys. Facades are " +
    'painted reconstructions from descriptions (no photos available here); the Bibendum window and race tiles are ' +
    'schematic. Side elevations now carry 3D pilasters, metal-framed windows, segmental pediments with faience ' +
    'tyres and inset tile panels on a 6 m bay rhythm (estimated); front arch reveal, window mullions and name ' +
    'panel are schematic.',
  build({ THREE, kit, buildings, placeAssets }) {
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = b.polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const H = 13;
    // front edge = shortest edge (Fulham Road)
    let fi = 0,
      fl = Infinity;
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length];
      const l = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (l < fl) {
        fl = l;
        fi = k;
      }
    }

    const faience = '#f2efe6';
    const front = kit.paintedMaterial(
      'michelin_house:front',
      512,
      512,
      (c, w, h) => {
        c.fillStyle = faience;
        c.fillRect(0, 0, w, h);
        // ground floor: three arched bays
        for (let k = 0; k < 3; k++) {
          const x = 30 + k * 160;
          c.fillStyle = '#2b4f86';
          c.fillRect(x - 6, 330, 132, 182);
          c.fillStyle = '#3a3f44';
          c.fillRect(x, 370, 120, 142);
          c.beginPath();
          c.arc(x + 60, 372, 60, Math.PI, 0);
          c.fill();
          c.fillStyle = '#c7d3da';
          for (let j = 1; j < 4; j++) c.fillRect(x + j * 30, 330, 3, 182);
        }
        // big Bibendum stained-glass window
        c.fillStyle = '#d9a72b';
        c.fillRect(110, 70, 292, 250);
        c.fillStyle = '#2a5a9e';
        c.fillRect(122, 82, 268, 226);
        c.beginPath();
        c.arc(256, 84, 134, Math.PI, 0);
        c.fillStyle = '#d9a72b';
        c.fill();
        c.beginPath();
        c.arc(256, 84, 122, Math.PI, 0);
        c.fillStyle = '#2a5a9e';
        c.fill();
        // Bibendum: stacked white tyre rings
        c.fillStyle = '#ffffff';
        c.strokeStyle = '#9aa6b5';
        c.lineWidth = 2;
        const rings = [
          [256, 60, 34, 26],
          [256, 108, 46, 18],
          [256, 140, 54, 18],
          [256, 172, 58, 18],
          [256, 204, 56, 18],
          [256, 236, 50, 18],
          [256, 268, 42, 16],
        ];
        for (const [x, y, rx, ry] of rings) {
          c.beginPath();
          c.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
          c.fill();
          c.stroke();
        }
        c.fillStyle = '#c03a2b';
        c.fillRect(196, 160, 30, 10);
        // lettering
        c.fillStyle = '#2b4f86';
        c.font = 'bold 44px sans-serif';
        c.textAlign = 'center';
        c.fillText('MICHELIN', 256, 40);
        c.fillStyle = '#d9a72b';
        c.fillRect(0, 0, w, 10);
        c.fillRect(0, 322, w, 8);
      },
      { roughness: 0.4 },
    );
    const side = kit.paintedMaterial(
      'michelin_house:side2',
      128,
      128,
      (c, w, h) => {
        // tile = 2 bays (12 m) x 13 m of white faience blocks with fine joints
        c.fillStyle = faience;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(120,120,110,0.18)';
        for (let y = 0; y < h; y += 6) c.fillRect(0, y, w, 1);
        for (let y = 0; y < h; y += 12)
          for (let x = (y / 12) % 2 ? 0 : 8; x < w; x += 16) c.fillRect(x, y, 1, 6);
        for (let y = 6; y < h; y += 12)
          for (let x = (y / 6) % 2 ? 0 : 8; x < w; x += 16) c.fillRect(x, y, 1, 6);
        c.fillStyle = '#d9a72b';
        c.fillRect(0, 82, w, 3);
        c.fillStyle = '#2b4f86';
        c.fillRect(0, 0, w, 4);
      },
      { roughness: 0.4 },
    );
    const raceTile = kit.paintedMaterial('michelin_house:race', 256, 128, (c, w, h) => {
      // Gilardoni tile panel of an early motor race: border, sky, road, car
      c.fillStyle = '#2b4f86';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#e8d9a8';
      c.fillRect(8, 8, w - 16, h - 16);
      c.fillStyle = '#8fb3d6';
      c.fillRect(8, 8, w - 16, 44);
      c.fillStyle = '#c9b27a';
      c.fillRect(8, 86, w - 16, 34);
      c.fillStyle = '#b33b2c';
      c.fillRect(70, 62, 110, 26);
      c.fillRect(110, 48, 40, 16);
      c.fillStyle = '#222';
      c.beginPath();
      c.arc(92, 92, 14, 0, Math.PI * 2);
      c.arc(160, 92, 14, 0, Math.PI * 2);
      c.fill();
      c.fillStyle = '#fff';
      c.fillRect(124, 52, 10, 8);
      c.strokeStyle = '#d9a72b';
      c.lineWidth = 3;
      c.strokeRect(10, 10, w - 20, h - 20);
      for (let x = 16; x < w - 16; x += 16) {
        c.fillStyle = 'rgba(0,0,0,0.12)';
        c.fillRect(x, 8, 1, h - 16);
      }
    });
    const white = kit.mat(faience, { roughness: 0.4 });
    const blue = kit.mat('#2b4f86', { roughness: 0.5 });
    const cupola = kit.mat('#9fb7c4', { roughness: 0.15, metalness: 0.3 });
    const roofM = kit.mat('#8d8a83');

    const wall = (mat, a, bq, z0, z1, tw, th) => {
      const len = Math.hypot(bq[0] - a[0], bq[1] - a[1]);
      const u1 = tw ? len / tw : 1;
      batch.quad(
        mat,
        [a[0], a[1], z0],
        [bq[0], bq[1], z0],
        [bq[0], bq[1], z1],
        [a[0], a[1], z1],
        [0, z0 / th],
        [u1, z0 / th],
        [u1, z1 / th],
        [0, z1 / th],
      );
    };
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        bq = ring[(k + 1) % ring.length];
      if (k === fi) wall(front, a, bq, 0, H, 0, H);
      else wall(side, a, bq, 0, H, 12, H);
    }
    // cornice and roof
    kit.walls(batch, blue, [[kit.offsetRing(ring, 0.25)]], H - 0.6, H, {});
    kit.cap(batch, white, [[kit.offsetRing(ring, 0.25)]], H);
    const inner = kit.offsetRing(ring, -2.5);
    kit.walls(batch, white, [[inner]], H, H + 2.6, { bay: 3, storey: 3 });
    kit.cap(batch, roofM, [[inner]], H + 2.6);

    // Front gable with MICHELIN parapet between the corner towers.
    const fa = ring[fi],
      fb = ring[(fi + 1) % ring.length];
    const fd = [(fb[0] - fa[0]) / fl, (fb[1] - fa[1]) / fl],
      fn = [fd[1], -fd[0]]; // outward normal
    const fang = Math.atan2(fd[1], fd[0]);
    const m4 = new THREE.Matrix4();
    const put = (mat, geo, x, y, z, rz = fang) =>
      batch.addGeometry(mat, geo, m4.makeRotationZ(rz).setPosition(x, y, z));
    {
      const mx = (fa[0] + fb[0]) / 2 + fn[0] * 0.3,
        my = (fa[1] + fb[1]) / 2 + fn[1] * 0.3;
      // half-disc pediment rising above the cornice
      const sh = new THREE.Shape();
      sh.absarc(0, 0, fl * 0.32, 0, Math.PI, false);
      const pg = new THREE.ExtrudeGeometry(sh, {
        depth: 0.6,
        bevelEnabled: false,
        curveSegments: 16,
      });
      pg.rotateX(Math.PI / 2);
      put(white, pg, mx, my, H);
    }
    // Corner towers with tyre-stack glass cupolas.
    for (const [p, sgn] of [
      [fa, 1],
      [fb, -1],
    ]) {
      const x = p[0] + fd[0] * sgn * 2.2 - fn[0] * 2.2,
        y = p[1] + fd[1] * sgn * 2.2 - fn[1] * 2.2;
      kit.box(batch, white, x, y, 0, 5, 5, H + 2.2, fang);
      kit.box(batch, blue, x, y, H + 2.2, 5.4, 5.4, 0.5, fang);
      const tyres = [
        [2.0, 0.55],
        [1.85, 0.5],
        [1.65, 0.45],
        [1.4, 0.42],
        [1.1, 0.38],
        [0.75, 0.32],
      ];
      let z = H + 3.1;
      for (const [R, r] of tyres) {
        put(cupola, new THREE.TorusGeometry(R - r, r, 8, 20), x, y, z, 0);
        z += r * 1.7;
      }
      put(blue, new THREE.SphereGeometry(0.35, 8, 6), x, y, z + 0.1, 0);
    }

    // ---------------------------------------------------------------- detail pass
    const steelW = kit.mat('#2e3a44', { roughness: 0.4, metalness: 0.3 });
    const glass = kit.mat('#3a4a56', { roughness: 0.15, metalness: 0.3 });
    const tyreM = kit.mat('#4a4c4e', { roughness: 0.5 });
    const yellow = kit.mat('#d9a72b', { roughness: 0.45 });
    const green = kit.mat('#2f6b45', { roughness: 0.5 });
    // geometry in a wall plane: local x along a -> b, y up, z outward
    const onWall = (mat, geo, a, q, t, out, z) => {
      const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
      const ux = (q[0] - a[0]) / len,
        uy = (q[1] - a[1]) / len;
      const m = new THREE.Matrix4().makeBasis(
        new THREE.Vector3(ux, uy, 0),
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(uy, -ux, 0),
      );
      m.setPosition(a[0] + ux * t + uy * out, a[1] + uy * t - ux * out, z);
      batch.addGeometry(mat, geo, m);
      geo.dispose();
    };
    for (let k = 0; k < ring.length; k++) {
      if (k === fi) continue;
      const a = ring[k],
        q = ring[(k + 1) % ring.length];
      const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
      const ux = (q[0] - a[0]) / len,
        uy = (q[1] - a[1]) / len;
      const ang = Math.atan2(uy, ux);
      const n = Math.max(1, Math.round(len / 6));
      const bay = len / n;
      // faience plinth and the blue / yellow bands
      for (let i = 0; i < n; i++) {
        const t0 = i * bay,
          tm = t0 + bay / 2;
        const A0 = [a[0] + ux * (t0 + 0.5), a[1] + uy * (t0 + 0.5)],
          A1 = [a[0] + ux * (t0 + bay - 0.5), a[1] + uy * (t0 + bay - 0.5)];
        // pilaster at the bay start with a blue capital
        kit.box(
          batch,
          white,
          a[0] + ux * t0 + uy * 0.2,
          a[1] + uy * t0 - ux * 0.2,
          0,
          0.8,
          0.4,
          H - 0.6,
          ang,
        );
        kit.box(
          batch,
          blue,
          a[0] + ux * t0 + uy * 0.25,
          a[1] + uy * t0 - ux * 0.25,
          H - 2.4,
          0.95,
          0.5,
          0.35,
          ang,
        );
        // ground floor: alternate race-tile panels and shop windows / doors
        if (i % 2 === 0)
          onWall(raceTile, new THREE.PlaneGeometry(bay - 2, 2.4), a, q, tm, 0.06, 2.4);
        else
          kit.windowRow(batch, A0, A1, 0.4, {
            count: 1,
            width: bay - 2.4,
            height: 3.4,
            margin: 0,
            glass,
            frame: steelW,
            sill: blue,
            head: 'segment',
            bars: 2,
          });
        // first floor: large metal-framed window with glazing bars
        kit.windowRow(batch, A0, A1, 5.0, {
          count: 1,
          width: bay - 2.0,
          height: 4.4,
          margin: 0,
          glass,
          frame: steelW,
          sill: white,
          head: 'none',
          bars: 3,
          depth: 0.16,
          surround: 0.25,
          surroundMat: blue,
        });
        // attic windows
        kit.windowRow(batch, A0, A1, 9.9, {
          count: 2,
          width: 1.3,
          height: 1.2,
          margin: 0.6,
          glass,
          frame: steelW,
          sill: white,
          head: 'none',
          bars: 1,
        });
        // open segmental pediment with a faience tyre at the parapet
        onWall(
          blue,
          new THREE.TorusGeometry(2.3, 0.16, 4, 14, Math.PI * 0.62).rotateZ(Math.PI * 0.19),
          a,
          q,
          tm,
          0.25,
          H - 1.6,
        );
        onWall(tyreM, new THREE.TorusGeometry(0.55, 0.22, 6, 18), a, q, tm, 0.3, H + 0.15);
        onWall(white, new THREE.CircleGeometry(0.4, 12), a, q, tm, 0.3, H + 0.15);
      }
      // string course (yellow) over the ground floor and blue cornice band
      kit.box(
        batch,
        yellow,
        (a[0] + q[0]) / 2 + uy * 0.12,
        (a[1] + q[1]) / 2 - ux * 0.12,
        4.55,
        len,
        0.25,
        0.2,
        ang,
      );
      kit.box(
        batch,
        white,
        (a[0] + q[0]) / 2 + uy * 0.2,
        (a[1] + q[1]) / 2 - ux * 0.2,
        4.75,
        len,
        0.4,
        0.2,
        ang,
      );
    }

    // Front: deep arched reveal round the central ground-floor bay, frame and
    // mullions over the Bibendum window, raised MICHELIN name panel.
    {
      const t = fl / 2;
      onWall(blue, new THREE.TorusGeometry(2.6, 0.3, 6, 18, Math.PI), fa, fb, t, 0.35, 5.6);
      for (const o of [-2.6, 2.6])
        onWall(blue, new THREE.BoxGeometry(0.6, 5.2, 0.6), fa, fb, t + o, 0.35, 2.6);
      onWall(steelW, new THREE.BoxGeometry(fl * 0.62, 0.12, 0.2), fa, fb, t, 0.4, 6.4);
      onWall(steelW, new THREE.BoxGeometry(fl * 0.62, 0.15, 0.2), fa, fb, t, 0.4, 12.4);
      for (let k = -3; k <= 3; k++)
        onWall(steelW, new THREE.BoxGeometry(0.1, 5.8, 0.15), fa, fb, t + k * 1.3, 0.38, 9.4);
      onWall(
        yellow,
        new THREE.TorusGeometry(fl * 0.31, 0.18, 4, 20, Math.PI),
        fa,
        fb,
        t,
        0.42,
        12.4,
      );
      const name = kit.paintedMaterial('michelin_house:name', 512, 96, (c, w, h) => {
        c.fillStyle = faience;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#2b4f86';
        c.font = 'bold 72px sans-serif';
        c.textAlign = 'center';
        c.fillText('MICHELIN', w / 2, 74);
        c.fillStyle = '#d9a72b';
        c.fillRect(0, 0, w, 6);
        c.fillRect(0, h - 6, w, 6);
      });
      onWall(name, new THREE.BoxGeometry(fl * 0.5, 1.3, 0.3), fa, fb, t, 1.05, H + 0.75);
      // green-tiled forecourt kerb and the flower / oyster stall canopy
      onWall(green, new THREE.BoxGeometry(fl * 0.6, 0.15, 3.5), fa, fb, t, 2.0, 0.07);
    }
    // Corner towers: glazed slots, blue and yellow bands, ring under the tyre-stack cupolas.
    for (const [p, sgn] of [
      [fa, 1],
      [fb, -1],
    ]) {
      const x = p[0] + fd[0] * sgn * 2.2 - fn[0] * 2.2,
        y = p[1] + fd[1] * sgn * 2.2 - fn[1] * 2.2;
      // faience panels and a window slot in each tower face
      for (let k = 0; k < 4; k++) {
        const a2 = fang + (k * Math.PI) / 2;
        const ox = Math.cos(a2 - Math.PI / 2) * 2.52,
          oy = Math.sin(a2 - Math.PI / 2) * 2.52;
        kit.box(batch, glass, x + ox, y + oy, 5.2, 1.4, 0.06, 6.5, a2);
        kit.box(batch, blue, x + ox, y + oy, 11.9, 2.0, 0.1, 0.3, a2);
        kit.box(batch, yellow, x + ox, y + oy, 4.6, 3.4, 0.1, 0.25, a2);
      }
      // blue ring at the foot of the glass tyre stack
      put(blue, new THREE.TorusGeometry(2.05, 0.12, 4, 24), x, y, H + 2.75, 0);
    }
    // Street furniture on Fulham Road: lamps and bollards along the front.
    {
      const lp = [],
        bl = [];
      for (const t of [-3, fl + 3])
        lp.push([fa[0] + fd[0] * t + fn[0] * 4, fa[1] + fd[1] * t + fn[1] * 4, fang + Math.PI]);
      for (let t = 1; t < fl; t += 2.5)
        bl.push([fa[0] + fd[0] * t + fn[0] * 3.6, fa[1] + fd[1] * t + fn[1] * 3.6, 0]);
      g.add(placeAssets('street_lamp', lp, { name: 'michelin_house:lamps' }));
      g.add(placeAssets('bollard', bl, { name: 'michelin_house:bollards' }));
    }

    g.add(batch.toGroup('michelin_house'));
    return g;
  },
};
