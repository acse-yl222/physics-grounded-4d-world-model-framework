// Victoria Lodge and Victoria Gate, Hyde Park (Bayswater Road entrance of North
// Carriage Drive), mid-19th century. The lodge is a single-storey square pavilion in
// white brick with pilasters between three windows on each side under a slate roof;
// the gateway has six openwork wrought-iron piers between wrought-iron gates, framed by
// two taller Portland stone piers with finials.
export default {
  id: 'victoria_gate_lodge',
  name: 'Victoria Gate Lodge',
  claims: ['4f480c23-72fe-4a81-b3a2-423151588aca'],
  references: [
    {
      title: 'Victoria Lodge and Adjoining Gate and Gate Piers - Historic England',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1275316',
      used_for:
        'Grade II, mid C19; white brick, slate roof; single storey, square plan, three windows each side with pilasters; six openwork wrought iron piers and two taller Portland stone piers with finials, wrought iron gates',
    },
    {
      title: 'Victoria Lodge and adjoining gate and gate piers - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101275316-victoria-lodge-and-adjoining-gate-and-gate-piers-hyde-park-ward',
      used_for: 'listing text, formerly listed as Victoria Gate',
    },
    {
      title: 'Hyde Park: Victoria Gate, Bayswater Road - The National Archives',
      url: 'https://beta.nationalarchives.gov.uk/catalogue/id/C553706',
      used_for: 'gate position on Bayswater Road',
    },
  ],
  notes:
    'Lodge body fitted to the main 8.6 m square of the footprint (the small west wing kept as a lower ' +
    'annexe); eaves 3.9 m, hipped roof rise 2.2 m, sash proportions and the central stack are estimates. Gate ' +
    'line placed across North Carriage Drive on the Bayswater Road boundary from the scene roads; pier spacing ' +
    '(two carriage and two side gates) is an assumption consistent with six iron and two stone piers.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    // main square: (1938.8,592.9) (1946.5,595.8) (1946.0,604.4) (1936.7,603.1)
    const fr = kit.ringFrame(ring);
    const ang = Math.atan2(595.8 - 592.9, 1946.5 - 1938.8) * 0 + (7.5 * Math.PI) / 180;
    const C = [1941.6, 598.8];
    const U = [Math.cos(ang), Math.sin(ang)],
      V = [-Math.sin(ang), Math.cos(ang)];
    const L = (u, v) => [C[0] + U[0] * u + V[0] * v, C[1] + U[1] * u + V[1] * v];
    const sq = (hw, hd, du = 0, dv = 0) => [
      L(du - hw, dv - hd),
      L(du + hw, dv - hd),
      L(du + hw, dv + hd),
      L(du - hw, dv + hd),
    ];
    void fr;

    const brick = kit.mat('#e6dfcc', { roughness: 0.9 }); // white (gault) brick
    const stone = kit.mat('portland_stone');
    const slate = kit.mat('slate');
    const iron = kit.mat('#1e2224', { roughness: 0.45, metalness: 0.45 });
    const gilt = kit.mat('gold');
    const glass = kit.mat('dark_glass');
    const white = kit.mat('white');
    const chimney = kit.mat('london_stock');

    const HW = 4.3,
      EAVE = 3.9;
    const body = sq(HW, HW);
    kit.walls(batch, brick, [[body]], 0, EAVE, { bay: 1e6 });
    kit.cornice(batch, stone, body, 0, { height: 0.45, projection: 0.12 });
    kit.cornice(batch, stone, body, EAVE - 0.45, { height: 0.45, projection: 0.35, steps: 2 });
    // pilasters at the corners and between the bays; three sashes per side
    for (let k = 0; k < 4; k++) {
      const a = body[k],
        b = body[(k + 1) % 4];
      const dx = (b[0] - a[0]) / (2 * HW),
        dy = (b[1] - a[1]) / (2 * HW);
      const nx = dy,
        ny = -dx;
      for (const t of [0.15, 2.9, 5.7, 8.45]) {
        const x = a[0] + dx * t + nx * 0.1,
          y = a[1] + dy * t + ny * 0.1;
        kit.box(batch, brick, x, y, 0.45, 0.45, 0.2, EAVE - 0.9, Math.atan2(dy, dx));
      }
      kit.windowRow(batch, a, b, 1.0, {
        count: 3,
        margin: 0.4,
        width: 1.0,
        height: 1.9,
        head: 'lintel',
        bars: 1,
        glass,
        frame: white,
        sill: stone,
      });
    }
    // door on the drive (east) side between the windows is replaced by the middle sash; porch annexe west
    const ann = sq(1.3, 1.9, -HW - 1.3, 0.2);
    kit.walls(batch, brick, [[ann]], 0, 3.0, { bay: 1e6 });
    kit.cornice(batch, stone, ann, 2.7, { height: 0.3, projection: 0.2 });
    kit.cap(batch, slate, [[ann]], 3.0);
    kit.windowRow(batch, ann[3], ann[0], 0.9, {
      count: 1,
      width: 0.9,
      height: 1.7,
      glass,
      frame: white,
      sill: stone,
    });
    // hipped (near pyramidal) slate roof and central chimney stack
    kit.pitchedRoof(batch, slate, brick, body, ang, EAVE, 2.2, 'pyramidal', { overhang: 0.45 });
    kit.box(batch, chimney, C[0], C[1], EAVE + 1.0, 0.9, 0.9, 2.4, ang);
    kit.box(batch, stone, C[0], C[1], EAVE + 3.4, 1.1, 1.1, 0.18, ang);
    for (const s of [-0.2, 0.2]) {
      const p = [C[0] + U[0] * s, C[1] + U[1] * s];
      const pot = new THREE.CylinderGeometry(0.12, 0.14, 0.5, 8).rotateX(Math.PI / 2);
      batch.addGeometry(
        kit.mat('terracotta'),
        pot,
        new THREE.Matrix4().makeTranslation(p[0], p[1], EAVE + 3.83),
      );
      pot.dispose();
    }

    // ---- gateway across North Carriage Drive at Bayswater Road ----------------------
    const G0 = [1953.0, 612.4];
    const GL = (s, t = 0) => [G0[0] + U[0] * s + V[0] * t, G0[1] + U[1] * s + V[1] * t];
    const stonePier = (s) => {
      const p = GL(s);
      kit.box(batch, stone, p[0], p[1], 0, 1.3, 1.3, 0.5, ang);
      kit.box(batch, stone, p[0], p[1], 0.5, 1.05, 1.05, 3.6, ang);
      kit.box(batch, stone, p[0], p[1], 4.1, 1.35, 1.35, 0.3, ang);
      const geo = new THREE.LatheGeometry(
        [
          [0, 0],
          [0.45, 0],
          [0.35, 0.2],
          [0.5, 0.6],
          [0.35, 0.95],
          [0.12, 1.1],
          [0.15, 1.3],
          [0, 1.45],
        ].map(([r, h]) => new THREE.Vector2(r, h)),
        10,
      ).rotateX(Math.PI / 2);
      batch.addGeometry(stone, geo, new THREE.Matrix4().makeTranslation(p[0], p[1], 4.4));
      geo.dispose();
    };
    const ironPier = (s) => {
      const p = GL(s);
      // openwork: four corner bars with lattice rings, cap and gilt finial
      for (const [du, dv] of [
        [-0.25, -0.25],
        [0.25, -0.25],
        [0.25, 0.25],
        [-0.25, 0.25],
      ]) {
        const q = [p[0] + U[0] * du + V[0] * dv, p[1] + U[1] * du + V[1] * dv];
        kit.box(batch, iron, q[0], q[1], 0, 0.07, 0.07, 3.6, ang);
      }
      for (let z = 0.4; z < 3.5; z += 0.45)
        kit.box(batch, iron, p[0], p[1], z, 0.6, 0.6, 0.05, ang);
      kit.box(batch, iron, p[0], p[1], 3.6, 0.75, 0.75, 0.12, ang);
      const fin = new THREE.ConeGeometry(0.18, 0.7, 8).rotateX(Math.PI / 2);
      batch.addGeometry(gilt, fin, new THREE.Matrix4().makeTranslation(p[0], p[1], 4.07));
      fin.dispose();
    };
    const gate = (s0, s1, h) => {
      const a = GL(s0),
        b = GL(s1);
      const len = s1 - s0;
      const m = GL((s0 + s1) / 2);
      kit.box(batch, iron, m[0], m[1], 0.12, len, 0.06, 0.08, ang);
      kit.box(batch, iron, m[0], m[1], h - 0.1, len, 0.06, 0.08, ang);
      kit.box(batch, iron, m[0], m[1], h * 0.75, len, 0.05, 0.05, ang);
      const n = Math.round(len / 0.14);
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        const x = a[0] + (b[0] - a[0]) * t,
          y = a[1] + (b[1] - a[1]) * t;
        kit.box(batch, iron, x, y, 0.12, 0.025, 0.025, h - 0.1 + 0.25 * Math.sin(Math.PI * t), ang);
      }
    };
    stonePier(-11);
    stonePier(11);
    for (const s of [-9.2, -7.4, -0.45, 0.45, 7.4, 9.2]) ironPier(s);
    gate(-10.35, -9.5, 2.2);
    gate(9.5, 10.35, 2.2);
    gate(-7.1, -0.75, 2.6);
    gate(0.75, 7.1, 2.6);
    gate(-8.9, -7.7, 2.2);
    gate(7.7, 8.9, 2.2);

    g.add(batch.toGroup('victoria_gate_lodge'));
    return g;
  },
};
