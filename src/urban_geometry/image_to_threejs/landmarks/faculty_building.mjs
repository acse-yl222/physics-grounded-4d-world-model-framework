// Faculty Building, Imperial College South Kensington (Foster and Partners, topped
// out September 2003, completed 2004). Four office storeys over two basements, set in
// Dalby Court enclosed by 1950s/60s college buildings. Its glass facades carry a
// seemingly random pattern of opaque panels in three shades of blue chosen with the
// Danish artist Per Arnoldi; blue-tinted vision panels show blood-orange columns
// along the internal ramp.
export default {
  id: 'faculty_building',
  name: 'Faculty Building',
  claims: ['8b822f3f-bb9b-44b8-902c-8cc0bc967893'],
  references: [
    {
      title: 'Topping out of Imperial College Faculty Building - Foster + Partners (5 Sept 2003)',
      url: 'https://www.fosterandpartners.com/news/topping-out-of-imperial-college-faculty-building',
      used_for: 'four office storeys over two basements; courtyard site; completion 2004',
    },
    {
      title: 'Imperial College Faculty Building - Foster + Partners',
      url: 'https://fosterandpartners.com/projects/imperial-college-faculty-building',
      used_for: 'project identity',
    },
    {
      title: 'Faculty Building - manchesterhistory.net',
      url: 'https://manchesterhistory.net/architecture/2000/facultybuilding.html',
      used_for:
        'random opaque panels in three shades of blue (Per Arnoldi), blue vision glass, orange columns along the ramp',
    },
    {
      title: 'Imperial College London Faculty Building - AEWORLDMAP',
      url: 'https://aeworldmap.com/2013/06/21/imperial-college-london-faculty-building-london-united-kingdom/',
      used_for: 'blue facades chosen partly to reduce solar gain',
    },
  ],
  notes:
    'Height set to ~18.5 m (four storeys plus a recessed plant level) instead of the 23 m footprint value, ' +
    'following the four-storey description. Panel distribution is a deterministic random pattern, not ' +
    'traced; position of the orange columns/ramp and the roof plant are approximate. Mullions follow the ' +
    '1.5 m panel module of the texture; entrance doors, steps, roof rail and condensers are indicative.',
  build({ THREE, kit, buildings, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0];
    const fr = kit.ringFrame(ring);
    const ca = Math.cos(fr.angle),
      sa = Math.sin(fr.angle);
    const at = (u, v) => [fr.cx + u * ca - v * sa, fr.cy + u * sa + v * ca];

    const ST = 4.0; // storey height
    const NS = 4; // office storeys
    const BAY = 1.5; // panel module
    const COLS = 64,
      ROWS = NS * 2; // canvas grid: 64 panels across x 2 panel rows per storey
    const blues = ['#1d4f8f', '#3f78bd', '#8bb5e0'];
    const facade = kit.paintedMaterial('faculty_building:arnoldi', 1024, 512, (c, w, h) => {
      const r = kit.rng(20040401);
      const pw = w / COLS,
        ph = h / ROWS;
      for (let row = 0; row < ROWS; row++)
        for (let col = 0; col < COLS; col++) {
          const x = col * pw,
            y = h - (row + 1) * ph;
          const q = r();
          if (q < 0.42) {
            c.fillStyle = blues[Math.floor(r() * 3)];
          } else {
            // blue-tinted vision glass, sometimes showing an orange column behind
            const gr = c.createLinearGradient(x, y, x, y + ph);
            gr.addColorStop(0, '#6f9cc4');
            gr.addColorStop(1, '#2d5578');
            c.fillStyle = gr;
          }
          c.fillRect(x, y, pw, ph);
          if (q > 0.97 && row % 2 === 0) {
            c.fillStyle = 'rgba(214,92,36,0.85)';
            c.fillRect(x + pw * 0.38, y, pw * 0.24, ph);
          }
        }
      // silver mullions and floor transoms
      c.fillStyle = '#c9d0d6';
      for (let col = 0; col <= COLS; col++) c.fillRect(col * pw - 1, 0, 2, h);
      for (let row = 0; row <= ROWS; row++)
        c.fillRect(0, row * ph - (row % 2 === 0 ? 3 : 1), w, row % 2 === 0 ? 6 : 2);
    });
    const plantMat = kit.mat('#c5cacd', { roughness: 0.5, metalness: 0.2 });
    const roofMat = kit.mat('#8e908f');
    const orange = kit.mat('#d65c24', { roughness: 0.5 });
    const soffit = kit.mat('#e8eaea');

    // Walls: one canvas covers COLS panels horizontally (continuous around the
    // perimeter) and all four storeys vertically.
    const z0 = 0,
      z1 = NS * ST;
    let run = 0;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      const u0 = run / (COLS * BAY),
        u1 = (run + len) / (COLS * BAY);
      batch.quad(
        facade,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [u0, 0],
        [u1, 0],
        [u1, 1],
        [u0, 1],
      );
      run += len;
    }
    // Thin projecting roof edge and roof.
    const edge = kit.offsetRing(ring, 0.6);
    kit.walls(batch, soffit, [[edge]], z1, z1 + 0.7);
    kit.cap(batch, soffit, [[edge]], z1 + 0.7);
    kit.cap(batch, soffit, [[edge]], z1, { down: true });
    // Recessed plant level with louvres.
    const L2 = fr.length / 2 - 4,
      W2 = fr.width / 2 - 3.5;
    const plantRing = [at(-L2, -W2), at(L2, -W2), at(L2, W2), at(-L2, W2)];
    if (kit.ringArea(plantRing) < 0) plantRing.reverse();
    const louvre = kit.paintedMaterial('faculty_building:louvre', 128, 128, (c, w, h) => {
      c.fillStyle = '#b5bbbf';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#7f878c';
      for (let y = 0; y < h; y += 8) c.fillRect(0, y, w, 3);
    });
    kit.walls(batch, louvre, [[plantRing]], z1 + 0.7, z1 + 3.4, { bay: 3, storey: 1.35 });
    kit.cap(batch, plantMat, [[plantRing]], z1 + 3.4);
    kit.cap(batch, roofMat, [[kit.offsetRing(ring, 0.3)]], z1 + 0.72);
    // Lift overrun.
    const [lx, ly] = at(-L2 + 3, 0);
    kit.box(batch, plantMat, lx, ly, z1 + 3.4, 4, 5, 1.6, fr.angle);
    // Ground-floor entrance recess with orange columns on one long side (north, towards Dalby Court).
    const ent = [at(-6, -fr.width / 2 - 0.02), at(6, -fr.width / 2 - 0.02)];
    const dark = kit.mat('#203241');
    batch.quad(
      dark,
      [ent[0][0], ent[0][1], 0],
      [ent[1][0], ent[1][1], 0],
      [ent[1][0], ent[1][1], 3.2],
      [ent[0][0], ent[0][1], 3.2],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    );
    const colGeo = new THREE.CylinderGeometry(0.3, 0.3, 3.4, 12).rotateX(Math.PI / 2);
    for (const u of [-6, -2, 2, 6]) {
      const [x, y] = at(u, -fr.width / 2 - 1.4);
      batch.addGeometry(orange, colGeo, new THREE.Matrix4().makeTranslation(x, y, 1.7));
    }
    const [cx, cy] = at(0, -fr.width / 2 - 1.1);
    kit.box(batch, soffit, cx, cy, 3.4, 14, 2.6, 0.3, fr.angle);
    // Silver curtain-wall mullions on the 1.5 m panel module, floor transoms and
    // intermediate panel transoms, all proud of the glass.
    const silver = kit.mat('#d3d9de', { roughness: 0.4, metalness: 0.1 });
    let run2 = 0;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      const dx = (b[0] - a[0]) / len,
        dy = (b[1] - a[1]) / len,
        ox = dy,
        oy = -dx;
      const an = Math.atan2(dy, dx);
      // mullions on the painted panel joints (texture runs continuously around the ring)
      for (let t = Math.ceil(run2 / BAY) * BAY - run2; t <= len + 1e-6; t += BAY)
        kit.box(
          batch,
          silver,
          a[0] + dx * t + ox * 0.08,
          a[1] + dy * t + oy * 0.08,
          0,
          0.08,
          0.16,
          z1,
          an,
        );
      run2 += len;
      const cx = (a[0] + b[0]) / 2 + ox * 0.1,
        cy = (a[1] + b[1]) / 2 + oy * 0.1;
      for (let row = 0; row <= ROWS; row++) {
        const z = (row * z1) / ROWS;
        const floor = row % 2 === 0;
        kit.box(
          batch,
          silver,
          cx,
          cy,
          z - (floor ? 0.1 : 0.03),
          len,
          floor ? 0.24 : 0.12,
          floor ? 0.2 : 0.06,
          an,
        );
      }
    }
    // Glazed entrance doors, steps and a roof-edge rail.
    {
      for (const u of [-3.5, 0, 3.5]) {
        const [x, y] = at(u, -fr.width / 2 - 0.08);
        kit.box(batch, kit.mat('dark_glass'), x, y, 0, 2.2, 0.06, 2.6, fr.angle);
        kit.box(batch, silver, x, y, 2.6, 2.4, 0.12, 0.12, fr.angle);
      }
      for (let st = 0; st < 2; st++) {
        const [x, y] = at(0, -fr.width / 2 - 3.2 + st * 0.5);
        kit.box(batch, kit.mat('#c9c4b8'), x, y, 0, 14, 1.4 - st * 0.4, 0.15 * (st + 1), fr.angle);
      }
    }
    const railR = kit.offsetRing(ring, -0.5);
    kit.balustrade(batch, silver, [...railR, railR[0]], z1 + 0.7, { height: 1.1, spacing: 2.0 });
    // Plant-level louvre fins and rooftop condensers.
    for (let k = 0; k < plantRing.length; k++) {
      const a = plantRing[k],
        b = plantRing[(k + 1) % plantRing.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const dx = (b[0] - a[0]) / len,
        dy = (b[1] - a[1]) / len;
      const an = Math.atan2(dy, dx);
      for (let t = 0.6; t < len; t += 1.2)
        kit.box(
          batch,
          plantMat,
          a[0] + dx * t + dy * 0.05,
          a[1] + dy * t - dx * 0.05,
          z1 + 0.7,
          0.08,
          0.15,
          2.7,
          an,
        );
    }
    for (const u of [-6, -1, 4, 9]) {
      const [x, y] = at(u, 2);
      kit.box(batch, kit.mat('#9ea3a6'), x, y, z1 + 3.4, 2.2, 1.2, 1.1, fr.angle);
      const fan = new THREE.CylinderGeometry(0.45, 0.45, 0.06, 12).rotateX(Math.PI / 2);
      batch.addGeometry(
        kit.mat('#3a3f42'),
        fan,
        new THREE.Matrix4().makeTranslation(x, y, z1 + 4.53),
      );
      fan.dispose();
    }
    g.add(batch.toGroup('faculty_building'));
    const benches = [-10, 10].map((u) => {
      const [x, y] = at(u, -fr.width / 2 - 5.5);
      return [x, y, fr.angle];
    });
    g.add(placeAssets('bench', benches));
    return g;
  },
};
