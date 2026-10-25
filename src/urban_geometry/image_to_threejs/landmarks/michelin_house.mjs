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
    'schematic.',
  build({ THREE, kit, buildings }) {
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
      'michelin_house:side',
      256,
      256,
      (c, w, h) => {
        // tile = 2 bays (12 m) x 13 m
        c.fillStyle = faience;
        c.fillRect(0, 0, w, h);
        for (let k = 0; k < 2; k++) {
          const x = k * 128;
          // upper windows
          c.fillStyle = '#34414b';
          c.fillRect(x + 22, 40, 84, 110);
          c.fillStyle = '#e6e2d6';
          for (let j = 1; j < 4; j++) c.fillRect(x + 22 + j * 21, 40, 2, 110);
          c.fillRect(x + 22, 92, 84, 3);
          // open segmental pediment with a faience tyre
          c.strokeStyle = '#2b4f86';
          c.lineWidth = 5;
          c.beginPath();
          c.arc(x + 64, 40, 50, Math.PI * 1.1, Math.PI * 1.9);
          c.stroke();
          c.strokeStyle = '#3c3f40';
          c.lineWidth = 6;
          c.beginPath();
          c.arc(x + 64, 22, 9, 0, Math.PI * 2);
          c.stroke();
          // ground-floor race tile panel
          c.fillStyle = '#2b4f86';
          c.fillRect(x + 10, 176, 108, 64);
          c.fillStyle = '#e8d9a8';
          c.fillRect(x + 14, 180, 100, 56);
          c.fillStyle = ['#b33b2c', '#2f6b45'][k];
          c.fillRect(x + 36, 206, 52, 14);
          c.fillStyle = '#222';
          c.beginPath();
          c.arc(x + 44, 224, 7, 0, Math.PI * 2);
          c.arc(x + 80, 224, 7, 0, Math.PI * 2);
          c.fill();
          c.fillStyle = '#7aa3c9';
          c.fillRect(x + 14, 180, 100, 18);
        }
        c.fillStyle = '#d9a72b';
        c.fillRect(0, 160, w, 6);
        c.fillStyle = '#2b4f86';
        c.fillRect(0, 0, w, 8);
      },
      { roughness: 0.4 },
    );
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

    g.add(batch.toGroup('michelin_house'));
    return g;
  },
};
